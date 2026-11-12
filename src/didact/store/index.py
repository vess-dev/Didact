"""The disposable SQLite index: full-text search, name lookup and backlinks.

Files are the truth; this index is rebuilt from them (`didact reindex`) and kept in sync
incrementally by comparing file size and mtime. Sync is one-way: files → index.
"""

import hashlib
import json
import re
import sqlite3
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from didact.core.errors import ConflictError, InvalidError
from didact.core.i18n import DEFAULT, _, use
from didact.core.ids import Scope, normalize_name
from didact.core.output import JSON
from didact.store import triggers
from didact.store.entity import Entity

INDEX_SCHEMA = "4"

_DDL = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS files(
    path TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    id TEXT NOT NULL,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    archived INTEGER NOT NULL,
    knowledge TEXT NOT NULL,
    tags TEXT NOT NULL,
    data TEXT NOT NULL,
    mtime_ns INTEGER NOT NULL,
    size INTEGER NOT NULL,
    hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS files_id ON files(id);
CREATE INDEX IF NOT EXISTS files_scope ON files(scope, type);
CREATE TABLE IF NOT EXISTS names(path TEXT NOT NULL, norm TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS names_norm ON names(norm);
CREATE INDEX IF NOT EXISTS names_path ON names(path);
CREATE TABLE IF NOT EXISTS links(path TEXT NOT NULL, rel TEXT NOT NULL, target TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS links_target ON links(target);
CREATE INDEX IF NOT EXISTS links_path ON links(path);
CREATE TABLE IF NOT EXISTS broken(
    path TEXT PRIMARY KEY, message TEXT NOT NULL, mtime_ns INTEGER NOT NULL, size INTEGER NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(
    path UNINDEXED, name, keys, body, tokenize='porter unicode61'
);
CREATE VIRTUAL TABLE IF NOT EXISTS fts_vocab USING fts5vocab(fts, 'row');
CREATE VIRTUAL TABLE IF NOT EXISTS tri USING fts5(path UNINDEXED, names, tokenize='trigram');
CREATE TABLE IF NOT EXISTS triggers(
    path TEXT NOT NULL, scope TEXT NOT NULL, word TEXT NOT NULL, phrase TEXT NOT NULL,
    kind TEXT NOT NULL, source TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS triggers_word ON triggers(word, scope);
CREATE INDEX IF NOT EXISTS triggers_path ON triggers(path);
"""

_TABLES = ("files", "names", "links", "broken", "fts", "tri", "triggers")


@dataclass(frozen=True, slots=True)
class Row:
    """An indexed entity: enough to list it, plus the full data for `show`."""

    path: str
    scope: Scope
    id: str
    type: str
    name: str
    status: str
    archived: bool
    knowledge: str
    tags: tuple[str, ...]
    data: dict[str, JSON]

    @property
    def body(self) -> str:
        body = self.data.get("body")
        return body if isinstance(body, str) else ""

    def entity(self) -> Entity:
        """The record as indexed: no file read (the index is kept in step with the files)."""
        meta = {k: v for k, v in self.data.items() if k != "body"}
        return Entity.from_meta(meta, self.body, where=self.path)


@dataclass(frozen=True, slots=True)
class Hit:
    row: Row
    snippet: str
    rank: float


@dataclass(frozen=True, slots=True)
class Trigger:
    """One key of a record that can come up in a lore scan (see `didact.store.triggers`)."""

    path: str
    scope: Scope
    phrase: str  # words joined by spaces; a `/regex/`; or "" for a constant entry
    kind: str  # key | regex | constant
    source: str  # lore | ruling | card


@dataclass(frozen=True, slots=True)
class Backlink:
    source: Row
    rel: str
    target: str


@dataclass(frozen=True, slots=True)
class SyncReport:
    updated: int
    removed: int
    broken: tuple[tuple[str, str], ...]  # (path, message)


type Parser = Callable[[str, str], Entity]  # (text, where) → entity
BUSY_WAIT = 30.0  # seconds to wait for another process using the index


def _patiently(step: Callable[[], None], wait: float = BUSY_WAIT) -> None:
    """Run `step`, trying again while another process has the index busy (two Didacts at
    once: the browser app and the command line, say)."""
    deadline = time.monotonic() + wait
    while True:
        try:
            step()
            return
        except sqlite3.OperationalError as exc:
            busy = "locked" in str(exc) or "busy" in str(exc)
            if not busy or time.monotonic() > deadline:
                if busy:
                    raise ConflictError(
                        _("the search index is busy: another didact process is using it"),
                        hint=_("wait a moment and retry"),
                    ) from exc
                raise
            time.sleep(0.05)


class Index:
    def __init__(self, db_path: Path, home: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.path = db_path
        self.home = home
        self.db = sqlite3.connect(db_path, timeout=BUSY_WAIT)
        _patiently(self._open)

    def _open(self) -> None:
        # Switching to WAL needs the database to itself, and SQLite may refuse that at once
        # rather than wait: only switch when it isn't WAL already (it stays WAL on disk).
        if str(self.db.execute("PRAGMA journal_mode").fetchone()[0]).lower() != "wal":
            self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self._ensure_schema()

    def close(self) -> None:
        self.db.close()

    def _ensure_schema(self) -> None:
        self.db.executescript(_DDL)
        row = self.db.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
        home_row = self.db.execute("SELECT value FROM meta WHERE key='home'").fetchone()
        if (
            row is None
            or row[0] != INDEX_SCHEMA
            or home_row is None
            or home_row[0] != str(self.home)
        ):
            self.db.execute("DROP TABLE IF EXISTS fts_vocab")  # reads fts: goes first
            self.db.executescript(";".join(f"DROP TABLE IF EXISTS {t}" for t in _TABLES) + ";")
            self.db.executescript(_DDL)
            self.db.execute("INSERT OR REPLACE INTO meta VALUES('schema', ?)", (INDEX_SCHEMA,))
            self.db.execute("INSERT OR REPLACE INTO meta VALUES('home', ?)", (str(self.home),))
            self.db.commit()

    # ------------------------------------------------------------------ maintenance

    def sync(self, files: Iterable[tuple[Scope, str]], parse: Parser) -> SyncReport:
        """Bring the index in line with the given entity files (scope, home-relative path)."""
        known: dict[str, tuple[int, int]] = {
            path: (mtime, size)
            for path, mtime, size in self.db.execute("SELECT path, mtime_ns, size FROM files")
        }
        known.update(
            {
                path: (mtime, size)
                for path, mtime, size in self.db.execute("SELECT path, mtime_ns, size FROM broken")
            }
        )
        seen: set[str] = set()
        updated = 0
        for scope, rel in files:
            seen.add(rel)
            stat = (self.home / rel).stat()
            if known.get(rel) == (stat.st_mtime_ns, stat.st_size):
                continue
            self._index_file(scope, rel, parse)
            updated += 1
        stale = [p for p in known if p not in seen]
        for rel in stale:
            self._forget(rel)
        self.db.commit()
        broken = tuple(self.db.execute("SELECT path, message FROM broken ORDER BY path"))
        return SyncReport(updated=updated, removed=len(stale), broken=broken)

    def refresh(self, changes: Iterable[tuple[str, Scope | None]], parse: Parser) -> None:
        """Re-index specific paths after a write.

        A scope of None means the file was removed or isn't an entity.
        """
        for rel, scope in changes:
            if scope is None or not (self.home / rel).exists():
                self._forget(rel)
            else:
                self._index_file(scope, rel, parse)
        self.db.commit()

    def clear(self) -> None:
        for table in _TABLES:
            self.db.execute(f"DELETE FROM {table}")
        self.db.commit()

    def _forget(self, rel: str) -> None:
        for table in _TABLES:
            self.db.execute(f"DELETE FROM {table} WHERE path = ?", (rel,))

    def _index_file(self, scope: Scope, rel: str, parse: Parser) -> None:
        path = self.home / rel
        raw = path.read_bytes()
        stat = path.stat()
        self._forget(rel)
        try:
            with use(DEFAULT):  # a broken file's message is stored in the index: English
                entity = parse(raw.decode("utf-8"), rel)
        except (InvalidError, UnicodeDecodeError) as exc:
            message = exc.message if isinstance(exc, InvalidError) else str(exc)
            self.db.execute(
                "INSERT INTO broken VALUES(?, ?, ?, ?)",
                (rel, message, stat.st_mtime_ns, stat.st_size),
            )
            return
        data = entity.to_data()
        self.db.execute(
            "INSERT INTO files VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                rel,
                str(scope),
                str(entity.id),
                entity.type,
                entity.name,
                entity.status,
                int(entity.archived),
                entity.knowledge,
                json.dumps(entity.tags),
                json.dumps(data, ensure_ascii=False),
                stat.st_mtime_ns,
                stat.st_size,
                hashlib.sha256(raw).hexdigest(),
            ),
        )
        norms = {
            normalize_name(n)
            for n in (entity.name, *entity.aliases, entity.id.slug, str(entity.id))
        }
        self.db.executemany("INSERT INTO names VALUES(?, ?)", [(rel, n) for n in norms if n])
        self.db.executemany(
            "INSERT INTO links VALUES(?, ?, ?)", [(rel, link.rel, link.to) for link in entity.links]
        )
        keys = " ".join([str(entity.id), *entity.aliases, *entity.tags])
        self.db.execute(
            "INSERT INTO fts VALUES(?, ?, ?, ?)", (rel, entity.name, keys, _searchable_text(entity))
        )
        self.db.execute(
            "INSERT INTO tri VALUES(?, ?)", (rel, " | ".join([entity.name, *entity.aliases]))
        )
        if not entity.archived:
            self.db.executemany(
                "INSERT INTO triggers VALUES(?, ?, ?, ?, ?, ?)",
                [(rel, str(scope), *row) for row in triggers.rows_for(entity)],
            )

    # ------------------------------------------------------------------ queries

    def rows(
        self,
        scopes: Sequence[Scope] | None = None,
        *,
        types: Sequence[str] = (),
        include_archived: bool = False,
    ) -> list[Row]:
        sql, params = self._filtered("SELECT * FROM files f", scopes, types, include_archived)
        return [self._row(r) for r in self.db.execute(sql + " ORDER BY f.type, f.name", params)]

    def by_id(self, entity_id: str, scopes: Sequence[Scope] | None = None) -> list[Row]:
        sql, params = self._filtered("SELECT * FROM files f", scopes, (), True)
        sql += " AND f.id = ?"
        return [self._row(r) for r in self.db.execute(sql, [*params, entity_id])]

    def by_paths(self, rels: Iterable[str]) -> list[Row]:
        wanted = sorted(set(rels))
        found: list[Row] = []
        for start in range(0, len(wanted), 500):  # SQLite caps bound parameters
            chunk = wanted[start : start + 500]
            marks = ",".join("?" for _unused in chunk)
            found += [
                self._row(r)
                for r in self.db.execute(f"SELECT * FROM files WHERE path IN ({marks})", chunk)
            ]
        return found

    def by_path(self, rel: str) -> Row | None:
        found = self.db.execute("SELECT * FROM files WHERE path = ?", (rel,)).fetchone()
        return self._row(found) if found else None

    def by_name(self, text: str, scopes: Sequence[Scope] | None = None) -> list[Row]:
        sql, params = self._filtered(
            "SELECT DISTINCT f.* FROM files f JOIN names n ON n.path = f.path", scopes, (), True
        )
        sql += " AND n.norm = ?"
        return [self._row(r) for r in self.db.execute(sql, [*params, normalize_name(text)])]

    def similar_names(
        self, text: str, scopes: Sequence[Scope] | None = None, limit: int = 5
    ) -> list[Row]:
        """Substring matches on names and aliases (trigram), for suggestions."""
        needle = normalize_name(text)
        if len(needle) < 3:
            return []
        sql, params = self._filtered(
            "SELECT DISTINCT f.* FROM tri t JOIN files f ON f.path = t.path", scopes, (), False
        )
        sql += " AND t.names LIKE ? LIMIT ?"
        return [self._row(r) for r in self.db.execute(sql, [*params, f"%{needle}%", limit])]

    def search(
        self,
        query: str,
        scopes: Sequence[Scope] | None = None,
        *,
        types: Sequence[str] = (),
        include_archived: bool = False,
        limit: int = 20,
        loose: bool = False,
    ) -> list[Hit]:
        """Records with every word (else any word). `loose`: a word also finds its synonyms
        and, when no record has it as typed, its near spellings (`didact.core.words`)."""
        tokens = re.findall(r"\w+", query.casefold())
        if not tokens:
            return []
        groups = [self._forms(t) if loose else [f'"{t}"*'] for t in tokens]
        hits = self._search(
            " AND ".join(f"({' OR '.join(g)})" for g in groups),
            scopes,
            types,
            include_archived,
            limit,
        )
        if not hits and len(tokens) > 1:
            hits = self._search(
                " OR ".join(f for g in groups for f in g), scopes, types, include_archived, limit
            )
        return hits

    def _forms(self, token: str) -> list[str]:
        """What a loose search for `token` matches: it, its synonyms, and its near spellings
        when no record has it as typed."""
        from didact.core import words

        forms = [token, *words.synonyms(token)]
        if not self._matches(f'"{token}"*'):
            vocabulary = {str(r[0]) for r in self.db.execute("SELECT term FROM fts_vocab")}
            for (norm,) in self.db.execute("SELECT DISTINCT norm FROM names"):  # unstemmed
                vocabulary |= words.tokens(str(norm))
            forms += words.near(token, vocabulary)
        quoted = (" ".join(re.findall(r"\w+", f)) for f in forms)
        return list(dict.fromkeys(f'"{q}"*' for q in quoted if q))

    def _matches(self, match: str) -> bool:
        return (
            self.db.execute("SELECT 1 FROM fts WHERE fts MATCH ? LIMIT 1", (match,)).fetchone()
            is not None
        )

    def _search(
        self,
        match: str,
        scopes: Sequence[Scope] | None,
        types: Sequence[str],
        include_archived: bool,
        limit: int,
    ) -> list[Hit]:
        base = (
            "SELECT f.*, bm25(fts, 0.0, 10.0, 5.0, 1.0) AS rank, "
            "snippet(fts, 3, '[', ']', '…', 10) AS snip "
            "FROM fts JOIN files f ON f.path = fts.path"
        )
        sql, params = self._filtered(base, scopes, types, include_archived)
        sql += " AND fts MATCH ? ORDER BY rank LIMIT ?"
        hits: list[Hit] = []
        for record in self.db.execute(sql, [*params, match, limit]):
            *columns, rank, snip = record
            hits.append(Hit(self._row(tuple(columns)), str(snip or ""), float(rank)))
        return hits

    def triggered(self, words: Iterable[str], scopes: Sequence[Scope]) -> list[Trigger]:
        """Keys whose first word is among `words`, plus every regex and constant key."""
        wanted = sorted(set(words))
        where = [str(s) for s in scopes]
        if not where:
            return []
        scope_marks = ",".join("?" for _unused in where)
        query = (
            "SELECT t.path, t.scope, t.phrase, t.kind, t.source FROM triggers t "
            f"WHERE t.scope IN ({scope_marks}) AND (t.word = ''"
        )
        params: list[str] = [*where]
        for start in range(0, len(wanted), 500):  # SQLite caps bound parameters
            chunk = wanted[start : start + 500]
            query += f" OR t.word IN ({','.join('?' for _unused in chunk)})"
            params += chunk
        query += ")"
        return [
            Trigger(str(p), Scope.parse(str(sc)), str(ph), str(k), str(src))
            for p, sc, ph, k, src in self.db.execute(query, params)
        ]

    def backlinks(self, targets: Iterable[str]) -> list[Backlink]:
        wanted = sorted(set(targets))
        if not wanted:
            return []
        marks = ",".join("?" for _unused in wanted)
        query = (
            "SELECT f.*, l.rel, l.target FROM links l JOIN files f ON f.path = l.path "
            f"WHERE l.target IN ({marks}) "
            f"OR substr(l.target, 1, instr(l.target || '@', '@') - 1) IN ({marks})"
        )
        results: list[Backlink] = []
        for record in self.db.execute(query, [*wanted, *wanted]):
            *columns, rel, target = record
            results.append(Backlink(self._row(tuple(columns)), str(rel), str(target)))
        return results

    def broken(self) -> list[tuple[str, str]]:
        return [
            (str(p), str(m))
            for p, m in self.db.execute("SELECT path, message FROM broken ORDER BY path")
        ]

    def dump(self) -> list[tuple[object, ...]]:
        """A canonical snapshot of the index contents (for rebuild-equals-incremental checks)."""
        snapshot: list[tuple[object, ...]] = []
        for table in ("files", "names", "links", "broken"):
            snapshot.extend(
                (table, *r) for r in self.db.execute(f"SELECT * FROM {table} ORDER BY 1, 2")
            )
        snapshot.extend(("fts", *r) for r in self.db.execute("SELECT * FROM fts ORDER BY path"))
        return snapshot

    def _filtered(
        self,
        base: str,
        scopes: Sequence[Scope] | None,
        types: Sequence[str],
        include_archived: bool,
    ) -> tuple[str, list[object]]:
        clauses: list[str] = ["1=1"]
        params: list[object] = []
        if scopes is not None:
            clauses.append(f"f.scope IN ({','.join('?' for _unused in scopes) or 'NULL'})")
            params.extend(str(s) for s in scopes)
        if types:
            clauses.append(f"f.type IN ({','.join('?' for _unused in types)})")
            params.extend(types)
        if not include_archived:
            clauses.append("f.archived = 0")
        return f"{base} WHERE {' AND '.join(clauses)}", params

    @staticmethod
    def _row(record: tuple[object, ...]) -> Row:
        path, scope, id_, type_, name, status, archived, knowledge, tags, data = record[:10]
        return Row(
            path=str(path),
            scope=Scope.parse(str(scope)),
            id=str(id_),
            type=str(type_),
            name=str(name),
            status=str(status),
            archived=bool(archived),
            knowledge=str(knowledge),
            tags=tuple(json.loads(str(tags))),
            data=cast(dict[str, JSON], json.loads(str(data))),
        )


def _searchable_text(entity: Entity) -> str:
    """Body text plus every string value in fields, details, mechanics and extra."""
    parts = [entity.body]

    def walk(value: JSON) -> None:
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                parts.append(key)
                walk(item)

    walk(entity.fields)
    walk(dict[str, JSON](entity.details))
    walk(entity.mechanics)
    walk(entity.extra)
    return "\n".join(p for p in parts if p)
