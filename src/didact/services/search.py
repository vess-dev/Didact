"""`search`: one ranked list across everything Didact knows here.

Sources (`--in`):
- `rules`: the packs' rules text (reference sections);
- `terms`: glossary terms;
- `mechanics`: rules you can run, and generators;
- `tables`: random and lookup tables (titles, descriptions and entries);
- `compendium`: monsters, items and other pack entries;
- `records`: the world's and campaign's records (NPCs, places, lore, sessions and scenes);
- `transcript`: what was said in play;
- `docs`: Didact's guides and command help, and the packs' guides.

Every word must match: as typed, as a synonym or as a near spelling (`didact.core.words`; a
near spelling only for a word no source has as typed, a typo). A hit in a title counts most,
then ids, tags and names, then the text; an exact word counts more than a near spelling, and
a near spelling more than a synonym.
"""

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import cast

from didact.core import labels
from didact.core.i18n import _
from didact.core.output import JSON, plain
from didact.core.words import Matcher
from didact.packs.library import PackSet
from didact.store.repo import Repo

SOURCES = ("rules", "terms", "mechanics", "tables", "compendium", "records", "transcript", "docs")
SNIPPET = 160


@dataclass(frozen=True, slots=True)
class Doc:
    """A piece of documentation to search (the commands' help comes from the command layer)."""

    id: str
    title: str
    body: str
    next: str


@dataclass(frozen=True, slots=True)
class Hit:
    source: str
    id: str
    title: str
    snippet: str
    score: float
    next: str  # the command that shows it

    def to_data(self) -> dict[str, JSON]:
        return {
            "source": self.source,
            "id": self.id,
            "title": self.title,
            "snippet": self.snippet,
            "score": round(self.score, 2),
            "next": self.next,
        }


def score(match: Matcher, title: str, keys: str, body: str) -> float:
    """How well a thing matches: every word must match; titles count most, then keys."""
    title, keys, body = title.casefold(), keys.casefold(), body.casefold()
    match.see(title, keys, body)  # the words that are here as typed get no near spellings
    total = 0.0
    for word in match.words:
        best = 0.0
        for place, folded in enumerate((title, keys, body)):
            weight, form = match.weight(word, folded)
            if weight:
                worth = (5.0, 3.0, 1 + min(folded.count(form), 4) / 2)[place]
                best = max(best, worth * weight)
                if weight == 1.0:
                    break
        if not best:
            return -1
        total += best
    return total


def snippet(text: str, words: Matcher | list[str]) -> str:
    """The text around the first word found, on one line."""
    if isinstance(words, Matcher):
        words = words.forms(text) or words.words
    flat = " ".join(text.split())
    folded = flat.casefold()
    at = min((i for w in words if (i := folded.find(w.casefold())) >= 0), default=0)
    start = max(0, at - SNIPPET // 3)
    piece = flat[start : start + SNIPPET]
    return ("…" if start else "") + piece + ("…" if start + SNIPPET < len(flat) else "")


def search(
    repo: Repo | None,
    packs: PackSet,
    query: str,
    *,
    sources: Iterable[str] = SOURCES,
    gm: bool = False,
    limit: int = 10,
    docs: Iterable[Doc] = (),
) -> tuple[list[Hit], int]:
    """Ranked hits across the sources, and how many secret matches were left out. The words as
    typed (and their synonyms) first; a word nothing has as typed then finds its near
    spellings too."""
    words = [w for w in re.split(r"\s+", query.strip().casefold()) if w]
    if not words:
        return [], 0
    shown, sources = list(docs), list(sources)  # (read twice)
    match = Matcher(words, typed=frozenset(words))
    hits, hidden = _gather(repo, packs, match, sources, gm=gm, limit=limit, docs=shown)
    if match.unseen():
        again = Matcher(words, typed=frozenset(match.seen))
        hits, hidden = _gather(repo, packs, again, sources, gm=gm, limit=limit, docs=shown)
    hits.sort(key=lambda h: (-h.score, SOURCES.index(h.source), h.title.casefold()))
    return hits[:limit], hidden


def _gather(
    repo: Repo | None,
    packs: PackSet,
    match: Matcher,
    sources: Iterable[str],
    *,
    gm: bool,
    limit: int,
    docs: list[Doc],
) -> tuple[list[Hit], int]:
    finders: dict[str, Callable[[], list[Hit]]] = {
        "rules": lambda: _rules(packs, match),
        "terms": lambda: _terms(packs, match),
        "mechanics": lambda: _mechanics(packs, match),
        "tables": lambda: _tables(packs, match),
        "compendium": lambda: _compendium(packs, match),
        "docs": lambda: _docs(packs, match, docs),
    }
    hits: list[Hit] = []
    hidden = 0
    for source in sources:
        if source in finders:
            hits += finders[source]()
        elif source == "records" and repo is not None and repo.initialized():
            found, hidden = _records(repo, match, gm=gm, limit=limit)
            hits += found
        elif source == "transcript" and repo is not None and repo.initialized():
            hits += _transcript(repo, match)
    return hits, hidden


def _rules(packs: PackSet, match: Matcher) -> list[Hit]:
    from didact.services import reference

    found: list[Hit] = []
    for section in reference.sections(packs):
        tags = " ".join(str(t) for t in cast(list[JSON], section.meta.get("tags") or []))
        points = score(match, section.title, f"{section.id} {tags}", section.body)
        if points > 0:
            page = f" ({section.page})" if section.page else ""
            found.append(
                Hit(
                    "rules",
                    section.qualified,
                    section.title + page,
                    snippet(section.body, match),
                    points + 0.5,  # the rules text is what people most often want
                    f"didact rules lookup {' '.join(match.words)}",
                )
            )
    return found


def _terms(packs: PackSet, match: Matcher) -> list[Hit]:
    from didact.services import reference

    found: list[Hit] = []
    for term in reference.terms(packs):
        points = score(match, term.term, " ".join(term.aliases), term.definition)
        if points > 0:
            found.append(
                Hit(
                    "terms",
                    f"{term.pack}.{term.term}",
                    term.term,
                    snippet(term.definition, match),
                    points + 1,  # a defined term is a precise answer
                    f"didact define '{term.term}'",
                )
            )
    return found


def _mechanics(packs: PackSet, match: Matcher) -> list[Hit]:
    from didact.services import rules

    found: list[Hit] = []
    for rule in rules.all_rules(packs):
        title = str(rule.data.get("title") or rule.id)
        help_text = " ".join(str(rule.data.get("help") or "").split())
        points = score(match, title, rule.id, help_text)
        if points > 0:
            found.append(
                Hit(
                    "mechanics",
                    rule.id,
                    f"{title} ({rule.kind})",
                    snippet(help_text, match) if help_text else "",
                    points,
                    f"didact explain {rule.id}",
                )
            )
    for kind in ("generator", "chargen"):
        for item in packs.all(kind):
            title = str(item.data.get("title") or item.id)
            help_text = " ".join(str(item.data.get("help") or "").split())
            points = score(match, title, item.qualified, help_text)
            if points > 0:
                verb = "gen run" if kind == "generator" else "char new"
                found.append(
                    Hit(
                        "mechanics",
                        item.qualified,
                        f"{title} ({kind})",
                        snippet(help_text, match) if help_text else "",
                        points,
                        f"didact {verb} {item.qualified}",
                    )
                )
    return found


def _tables(packs: PackSet, match: Matcher) -> list[Hit]:
    found: list[Hit] = []
    for item in packs.all("table"):
        data = item.data
        title = str(data.get("title") or item.id)
        description = " ".join(str(data.get("description") or "").split())
        entries = " · ".join(_entry_texts(data.get("entries")))
        points = score(match, title, item.id, f"{description} {entries}")
        if points > 0:
            text = description if match.forms(description) else entries
            found.append(
                Hit(
                    "tables",
                    item.qualified,
                    title,
                    snippet(text, match),
                    points - 0.5,  # entries are many and short: a weaker signal
                    f"didact table show {item.qualified}",
                )
            )
    return found


def _entry_texts(entries: JSON) -> list[str]:
    values = entries.values() if isinstance(entries, dict) else entries
    texts: list[str] = []
    for value in values if isinstance(values, Iterable) and not isinstance(values, str) else []:
        if isinstance(value, dict):
            if "text" in value:
                texts.append(str(value["text"]))
            else:
                texts += _entry_texts(cast(JSON, value))  # a lookup level
        elif isinstance(value, list):
            texts.append(" / ".join(str(v) for v in value))
        elif value is not None:
            texts.append(str(value))
    return texts


def _compendium(packs: PackSet, match: Matcher) -> list[Hit]:
    found: list[Hit] = []
    for item in packs.all("entry"):
        data = item.data
        name = str(data.get("name") or item.id)
        kind = str(data.get("type") or "entry")
        text = " · ".join(
            _described(k, v) for k, v in data.items() if k not in ("id", "name", "type", "source")
        )
        points = score(match, name, f"{item.id} {kind}", text)
        if points > 0:
            found.append(
                Hit(
                    "compendium",
                    item.qualified,
                    f"{name} ({kind})",
                    snippet(text, match),
                    points,
                    f"didact compendium show {item.qualified}",
                )
            )
    return found


def _described(key: str, value: JSON) -> str:
    """A compendium entry's value for its snippet: prose as it is, anything else named by its
    key (`price 5`, not a bare `5`)."""
    if isinstance(value, str) and " " in value.strip():
        return value
    return f"{key.replace('_', ' ')} {plain(value)}"


def _records(repo: Repo, match: Matcher, *, gm: bool, limit: int) -> tuple[list[Hit], int]:
    from didact.services import knowledge

    index = repo.index()
    rows = index.search(" ".join(match.words), repo.chain(), limit=limit * 3, loose=True)
    found = [(h.row, h.snippet) for h in rows]
    hidden = 0
    if not gm:
        found, hidden = knowledge.player_hits(repo, found, match.words)
    hits: list[Hit] = []
    for position, (row, text) in enumerate(found):
        points = score(match, row.name, f"{row.id} {' '.join(row.tags)}", text)
        points = (
            max(points, len(match.words)) + 1 - position * 0.05
        )  # the index ranked them already
        hits.append(
            Hit(
                "records",
                row.id,
                f"{row.name} ({labels.type_inline(row.type)})",
                " ".join(text.split()),
                points,
                f"didact show {row.id}",
            )
        )
    return hits, hidden


def _transcript(repo: Repo, match: Matcher) -> list[Hit]:
    from didact.services import play

    if repo.active_campaign() is None:
        return []
    folder = play.campaign_dir(repo) / "transcripts"
    hits: list[Hit] = []
    for path in sorted(folder.glob("session-*.md")) if folder.is_dir() else []:
        session = int(path.stem.rpartition("-")[2])
        for paragraph in path.read_text(encoding="utf-8").split("\n\n"):
            if match.found(paragraph):
                hits.append(
                    Hit(
                        "transcript",
                        f"session {session}",
                        _("Session {n} transcript", n=session),
                        snippet(paragraph, match),
                        len(match.words) * 1.5,
                        f"didact transcript --session {session}",
                    )
                )
    return hits


def _docs(packs: PackSet, match: Matcher, docs: list[Doc]) -> list[Hit]:
    from didact import guides
    from didact.core.i18n import current

    found: list[Hit] = []
    for topic in guides.topics():  # in the reader's language, where it's translated
        for heading, text in _sections(guides.translated(topic, current().code).text):
            points = score(match, heading, topic, text)
            if points > 0:
                found.append(
                    Hit(
                        "docs",
                        f"guide:{topic}",
                        _("{topic} guide: {heading}", topic=topic, heading=heading),
                        snippet(text, match),
                        points,
                        f"didact guide {topic}",
                    )
                )
    for pack in packs.packs:
        text = str(pack.bundle.get("guide") or "")
        for heading, body in _sections(text):
            points = score(match, heading, pack.id, body)
            if points > 0:
                found.append(
                    Hit(
                        "docs",
                        f"guide:{pack.id}",
                        _("{topic} guide: {heading}", topic=pack.id, heading=heading),
                        snippet(body, match),
                        points,
                        f"didact guide {pack.id}",
                    )
                )
    for doc in docs:
        points = score(match, doc.title, doc.id, doc.body)
        if points > 0:
            found.append(Hit("docs", doc.id, doc.title, snippet(doc.body, match), points, doc.next))
    return found


def _sections(text: str) -> list[tuple[str, str]]:
    """A Markdown text split at its headings: (heading, body)."""
    parts: list[tuple[str, str]] = []
    heading, lines = "", list[str]()
    for line in text.splitlines():
        if line.startswith("#"):
            if lines:
                parts.append((heading, "\n".join(lines)))
            heading, lines = line.lstrip("#").strip(), []
        else:
            lines.append(line)
    if lines:
        parts.append((heading, "\n".join(lines)))
    return parts
