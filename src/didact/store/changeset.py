"""Changesets: every write goes through one. Plan → preview → (stage) → apply → one event → undo.

Applying happens under the data-home lock. The event (with full before/after text) is written
before any file, so the log doubles as a write-ahead log: a change cut short by a crash or a
full disk is taken back from it, whole (`store/recovery.py`).
"""

import difflib
import json
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from didact.core.errors import ConflictError, InvalidError, NotFoundError, StorageError
from didact.core.i18n import N_, _, ngettext
from didact.core.output import JSON
from didact.core.phrases import Phrase, english, phrase
from didact.store import frontmatter, recovery
from didact.store.events import (
    RESTORED,
    SAY,
    Cleared,
    Event,
    EventKind,
    FileChange,
    said,
    undone_seqs,
)
from didact.store.fsutil import atomic_write, fix_for, reason, remove_file
from didact.store.repo import Repo

MAX_PREVIEW_FILES = 25


@dataclass(slots=True)
class Changeset:
    repo: Repo
    summary: str
    command: str | None = None
    reason: str | None = None
    forced: bool = False
    kind: EventKind = "change"
    undoes: int | None = None
    turn: str | None = None  # the open turn group (`undo --turn`), if any
    phrase: Phrase | None = None  # the summary's words, to show it in any language
    _changes: dict[str, FileChange] = field(default_factory=dict)
    _entities: list[str] = field(default_factory=list)

    def say(self, message: str | Phrase, /, **values: JSON) -> Changeset:
        """Set the summary from `message` (marked with `N_`) and its values, or from a phrase:
        English in the log, and kept as a phrase so that `history` can show it in the reader's
        language."""
        self.phrase = message if isinstance(message, dict) else phrase(message, **values)
        self.summary = english(self.phrase)
        return self

    # ------------------------------------------------------------------ planning

    def write(self, path: Path, text: str) -> None:
        rel = self.repo.layout.rel(path)
        before = self._changes[rel].before if rel in self._changes else self.repo.read_text(path)
        self._changes[rel] = FileChange(rel, before, text)

    def append(self, path: Path, text: str) -> None:
        """Add text to the end of a file (created if absent). Logged as just the new text."""
        rel = self.repo.layout.rel(path)
        planned = self._changes.get(rel)
        if planned is not None and planned.append is None:
            base = planned.after if planned.after is not None else ""
            self._changes[rel] = FileChange(rel, planned.before, base + text)
        elif planned is not None:
            self._changes[rel] = FileChange(
                rel, planned.before, None, (planned.append or "") + text
            )
        else:
            existed = self.repo.read_text(path) is not None
            self._changes[rel] = FileChange(rel, "" if existed else None, None, text)

    def delete(self, path: Path) -> None:
        rel = self.repo.layout.rel(path)
        before = self._changes[rel].before if rel in self._changes else self.repo.read_text(path)
        if before is None and rel not in self._changes:
            return
        self._changes[rel] = FileChange(rel, before, None)

    def planned_text(self, path: Path) -> str | None:
        """The text a file will have after this changeset (its current text if untouched)."""
        rel = self.repo.layout.rel(path)
        if rel in self._changes:
            change = self._changes[rel]
            if change.append is not None:
                return (self.repo.read_text(path) or "") + change.append
            return change.after
        return self.repo.read_text(path)

    def mention(self, *entity_ids: str) -> None:
        for entity_id in entity_ids:
            if entity_id not in self._entities:
                self._entities.append(entity_id)

    @property
    def files(self) -> tuple[FileChange, ...]:
        return tuple(
            c for c in self._changes.values() if c.append is not None or c.before != c.after
        )

    @property
    def entities(self) -> tuple[str, ...]:
        return tuple(self._entities)

    def is_empty(self) -> bool:
        return not self.files

    # ------------------------------------------------------------------ preview

    def preview(self, *, full: bool = False) -> str:
        files = self.files
        if not files:
            return _("no changes")
        lines = [ngettext("{n} file(s) would change:", "{n} file(s) would change:", len(files))]
        for change in files[:MAX_PREVIEW_FILES]:
            lines.extend(describe_change(change, full=full))
        if len(files) > MAX_PREVIEW_FILES:
            lines.append(
                _(
                    "… and {count} more (`--detail full` or `--format json`)",
                    count=len(files) - MAX_PREVIEW_FILES,
                )
            )
        return "\n".join(lines)

    def to_data(self) -> dict[str, JSON]:
        data: dict[str, JSON] = {
            "summary": self.summary,
            "command": self.command,
            "reason": self.reason,
            "forced": self.forced,
            "entities": list(self._entities),
            "files": [c.to_data() for c in self.files],
        }
        if self.phrase is not None:
            data[SAY] = self.phrase
        return data

    # ------------------------------------------------------------------ staging

    def stage(self) -> str:
        """Save for a later `didact apply <id>`; returns the changeset id (e.g. `x3f9a2c1`)."""
        change_id = "x" + uuid.uuid4().hex[:7]
        path = self.repo.layout.staging_dir / f"{change_id}.json"
        atomic_write(path, json.dumps(self.to_data(), ensure_ascii=False, indent=1))
        return change_id

    @classmethod
    def load_staged(cls, repo: Repo, change_id: str) -> Changeset:
        path = repo.layout.staging_dir / f"{change_id.lstrip('#')}.json"
        if not path.is_file():
            raise NotFoundError(
                _("no staged changeset {change}", change=repr(change_id)),
                hint=_("see `didact staged`"),
            )
        data = json.loads(path.read_text(encoding="utf-8"))
        said = data.get(SAY)
        changeset = cls(
            repo,
            summary=str(data["summary"]),
            command=data.get("command"),
            reason=data.get("reason"),
            forced=bool(data.get("forced", False)),
            phrase=said if isinstance(said, dict) else None,
        )
        for raw in data["files"]:
            change = FileChange.from_data(cast(dict[str, JSON], raw))
            changeset._changes[change.path] = change
        changeset._entities = [str(e) for e in data.get("entities", [])]
        return changeset

    # ------------------------------------------------------------------ applying

    def apply(self) -> Event:
        files = self.files
        if not files:
            raise InvalidError(_("nothing to change"), hint=_("the record already looks like that"))
        repo = self.repo
        repo.require_init()
        with repo.writing():
            for change in files:
                if change.append is not None:
                    continue  # appends go on top of whatever is there
                current = repo.read_text(repo.layout.abs(change.path))
                if current != change.before:
                    raise ConflictError(
                        _("{path} changed since this change was planned", path=change.path),
                        hint=_("re-run the command to plan it again"),
                    )
            data: dict[str, JSON] = {}
            if self.turn and self.kind == "change":
                data["turn"] = self.turn
            if self.phrase is not None:
                data[SAY] = self.phrase
            try:
                recovery.begin(repo.layout, repo.log.last_seq() + 1, files)
                event = repo.log.append(
                    kind=self.kind,
                    summary=self.summary,
                    command=self.command,
                    reason=self.reason,
                    forced=self.forced,
                    entities=self.entities,
                    files=files,
                    undoes=self.undoes,
                    data=data or None,
                )
                for change in files:
                    path = repo.layout.abs(change.path)
                    if change.append is not None:
                        atomic_write(path, (repo.read_text(path) or "") + change.append)
                    elif change.after is None:
                        remove_file(path)
                    else:
                        atomic_write(path, change.after)
                recovery.end(repo.layout)
            except OSError as exc:
                raise _refused(repo, exc) from exc
            repo.refresh_index([c.path for c in files])
        return event


def _refused(repo: Repo, exc: OSError) -> StorageError:
    """The error for a change the disk refused, having taken back what it did write."""
    try:
        recovery.take_back(repo.layout, repo.log)
    except OSError:
        return StorageError(
            _("couldn't finish this change ({why}), and part of it is written", why=reason(exc)),
            hint=_("fix that, then run any `didact` command: it takes the change back"),
        )
    return StorageError(
        _("couldn't save this change ({why}), so nothing was changed", why=reason(exc)),
        hint=fix_for(exc),
    )


def undo(
    repo: Repo,
    event: Event,
    *,
    force: bool = False,
    reason: str | None = None,
    command: str | None = None,
) -> Event:
    """Revert an event's file changes exactly (byte for byte)."""
    if event.kind not in ("change", "undo") or not event.files:
        restored = event.data.get(RESTORED)
        if isinstance(restored, dict):
            hint = _(
                "it marks a restore: `didact snapshot --restore {safety}` goes back to before it",
                safety=restored.get("safety"),
            )
        elif Cleared.of(event) is not None:
            hint = _("a cleared history can't come back")
        else:
            hint = _("`didact history` lists the changes")
        raise InvalidError(_("{event} has no file changes to undo", event=event.label), hint=hint)
    changeset = Changeset(
        repo,
        summary="",
        command=command,
        reason=reason,
        forced=force,
        kind="undo",
        undoes=event.seq,
    ).say(N_("undo {event}: {what}"), event=event.label, what=said(event))
    for change in event.files:
        path = repo.layout.abs(change.path)
        current = repo.read_text(path)
        if change.append is not None:
            text = current or ""
            if not text.endswith(change.append) and not force:
                raise ConflictError(
                    _("{path} was changed after {event}", path=change.path, event=event.label),
                    hint=_("undo the later changes first, or pass --force"),
                )
            rest = text[: len(text) - len(change.append)] if text.endswith(change.append) else text
            restored = None if change.before is None and not rest else rest
            changeset._changes[change.path] = FileChange(change.path, current, restored)
            continue
        if current != change.after and not force:
            raise ConflictError(
                _("{path} was changed after {event}", path=change.path, event=event.label),
                hint=_("undo the later changes first, or pass --force to overwrite them"),
            )
        changeset._changes[change.path] = FileChange(change.path, current, change.before)
    changeset.mention(*event.entities)
    return changeset.apply()


def undoable(repo: Repo) -> list[Event]:
    """Change events whose effects are in place, newest first."""
    events = repo.log.all()
    undone = undone_seqs(events)
    return [e for e in reversed(events) if e.kind == "change" and e.seq not in undone and e.files]


def redoable(repo: Repo) -> list[Event]:
    """Undos that are in effect, newest first; undoing one of them redoes its change.

    Only undos of real changes count. A redo is itself an undo of an undo, so without this
    filter a second `redo` would pick the first redo and revert it.
    """
    events = repo.log.all()
    undone = undone_seqs(events)
    kinds = {e.seq: e.kind for e in events}
    return [
        e
        for e in reversed(events)
        if e.kind == "undo"
        and e.seq not in undone
        and e.undoes is not None
        and kinds.get(e.undoes) == "change"
    ]


# ---------------------------------------------------------------------- describing changes


def describe_change(change: FileChange, *, full: bool = False) -> list[str]:
    """Human/LLM-readable lines for one file change: key-level for front matter and YAML."""
    if change.append is not None:
        added = len(change.append.splitlines())
        return [
            ngettext(
                "+ append {path} (+{n} line)",
                "+ append {path} (+{n} lines)",
                added,
                path=change.path,
            )
        ]
    heads = {
        "create": _("+ create {path}", path=change.path),
        "delete": _("- delete {path}", path=change.path),
        "update": _("~ update {path}", path=change.path),
    }
    lines = [heads[change.action]]
    if change.action == "delete":
        gone = _parse_for_diff(change.path, change.before)
        if gone is not None and "id" in gone[0]:
            lines[0] += f" ({_short(gone[0]['id'])}: {_short(gone[0].get('name', ''))})"
        return lines
    before, after = (
        _parse_for_diff(change.path, change.before),
        _parse_for_diff(change.path, change.after),
    )
    if before is None and after is None:
        lines.extend(_text_diff(change, full))
        return lines
    old_meta, old_body = before or ({}, "")
    new_meta, new_body = after or ({}, "")
    flat_old, flat_new = _flatten(old_meta), _flatten(new_meta)
    skip = {"updated"} if change.action == "update" else set()
    for key in sorted(set(flat_old) | set(flat_new)):
        if key in skip or flat_old.get(key) == flat_new.get(key):
            continue
        if key not in flat_old:
            lines.append(f"    {key}: {_short(flat_new[key])}")
        elif key not in flat_new:
            lines.append("    " + _("{key}: {old} → (removed)", key=key, old=_short(flat_old[key])))
        else:
            lines.append(f"    {key}: {_short(flat_old[key])} → {_short(flat_new[key])}")
    if old_body != new_body and change.action == "update":
        if full:
            lines.extend("    " + line for line in _unified(old_body, new_body))
        else:
            added = sum(
                1
                for d in difflib.ndiff(old_body.splitlines(), new_body.splitlines())
                if d.startswith("+ ")
            )
            removed = sum(
                1
                for d in difflib.ndiff(old_body.splitlines(), new_body.splitlines())
                if d.startswith("- ")
            )
            lines.append(
                "    " + _("body: +{added} / -{removed} line(s)", added=added, removed=removed)
            )
    return lines


def _parse_for_diff(path: str, text: str | None) -> tuple[dict[str, JSON], str] | None:
    if text is None:
        return None
    try:
        if path.endswith(".md"):
            yaml_text, body = frontmatter.split(text, where=path)
            data = frontmatter.to_plain(frontmatter.load(yaml_text, where=path))
            return (data if isinstance(data, dict) else {}), body
        if path.endswith((".yaml", ".yml")):
            data = frontmatter.to_plain(frontmatter.load(text, where=path))
            return (data if isinstance(data, dict) else {}), ""
    except InvalidError:
        return None
    return None


def _flatten(data: dict[str, JSON], prefix: str = "") -> dict[str, JSON]:
    flat: dict[str, JSON] = {}
    for key, value in data.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict) and value:
            flat.update(_flatten(value, f"{name}."))
        else:
            flat[name] = value
    return flat


def _short(value: JSON, limit: int = 80) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = text.replace("\n", "⏎")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _unified(old: str, new: str) -> Iterable[str]:
    return (
        line.rstrip("\n")
        for line in difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=1)
    )


def _text_diff(change: FileChange, full: bool) -> list[str]:
    if change.action != "update" or not full:
        return []
    return ["    " + line for line in _unified(change.before or "", change.after or "")]
