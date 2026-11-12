"""The reference desk: rules text, glossary terms, and "what is this?" for anything."""

from dataclasses import dataclass
from typing import cast

from didact.core.i18n import _
from didact.core.output import JSON
from didact.core.words import Matcher
from didact.packs.library import PackSet

MAX_BODY = 900


@dataclass(frozen=True, slots=True)
class Section:
    pack: str
    id: str
    title: str
    body: str
    meta: dict[str, JSON]
    source: str

    @property
    def qualified(self) -> str:
        return f"{self.pack}.{self.id}"

    @property
    def page(self) -> str:
        page = self.meta.get("page")
        return f"p. {page}" if page is not None else ""

    @property
    def mechanics(self) -> list[str]:
        raw = self.meta.get("mechanics")
        return [str(m) for m in raw] if isinstance(raw, list) else []


def sections(packs: PackSet) -> list[Section]:
    """The sections in play: a hack's section stands in for its base's of the same id, and the
    base's sections it hides are left out."""
    found: list[Section] = []
    for pack in packs.packs:
        for section_id, raw in pack.section("reference").items():
            if packs.superseded(pack.id, "reference", section_id):
                continue
            entry = cast(dict[str, JSON], raw)
            found.append(
                Section(
                    pack.id,
                    section_id,
                    str(entry.get("title") or section_id),
                    str(entry.get("body") or ""),
                    cast(dict[str, JSON], entry.get("meta") or {}),
                    str(entry.get("source") or ""),
                )
            )
    return found


def lookup(
    packs: PackSet, words: list[str], limit: int = 3, *, whole: bool = False
) -> list[tuple[float, Section]]:
    """Sections for a topic: every word must match (as typed, a synonym or a near spelling:
    `didact.core.words`, a near spelling only for a word no section has as typed). A word in
    the title beats one in the tags, which beats the body however often it's there; how often
    only breaks ties. The section named for the topic comes first. `whole`: each word only as a
    word (a quoted phrase's words, tried when it isn't there: `fallout 3 clocks`)."""
    wanted = [w.casefold() for w in words if w.strip()]
    first = Matcher(wanted, typed=frozenset(wanted), whole=whole)  # as typed first, as `search`
    found = _scored(packs, wanted, first)
    if first.unseen() and not whole:  # a word no section has as typed: near spellings (typos)
        found = _scored(packs, wanted, Matcher(wanted, typed=frozenset(first.seen)))
    found.sort(key=lambda s: (-s[0], s[1].title))
    return found[:limit]


def _scored(packs: PackSet, wanted: list[str], match: Matcher) -> list[tuple[float, Section]]:
    scored: list[tuple[float, Section]] = []
    for section in sections(packs):
        title = f"{section.title} {section.id}".casefold()
        tags = " ".join(str(t) for t in cast(list[JSON], section.meta.get("tags") or [])).casefold()
        body = section.body.casefold()
        match.see(title, tags, body)
        score = 0.0
        for word in wanted:
            best = 0.0
            for worth, place in ((6.0, title), (4.0, tags), (1.0, body)):
                weight, form = match.weight(word, place)
                if weight:
                    best = max(best, (worth + min(body.count(form), 4) / 2) * weight)
                    if weight == 1.0:
                        break
            if not best:
                score = -1
                break
            score += best
        if score > 0 and section.title.casefold().rstrip("s") == " ".join(wanted).rstrip("s"):
            score += 3
        if score > 0:
            scored.append((score, section))
    return scored


@dataclass(frozen=True, slots=True)
class Term:
    pack: str
    term: str
    definition: str
    aliases: list[str]
    see: list[str]
    source: str


def terms(packs: PackSet) -> list[Term]:
    """The terms in play: a hack's term stands in for its base's, and the base's terms it
    hides are left out."""
    found: list[Term] = []
    for pack in packs.packs:
        for key, raw in pack.section("glossary").items():
            if packs.superseded(pack.id, "term", key):
                continue
            entry = cast(dict[str, JSON], raw)
            aliases = entry.get("aliases")
            see = entry.get("see")
            found.append(
                Term(
                    pack.id,
                    str(entry.get("term")),
                    str(entry.get("definition")),
                    [str(a) for a in aliases] if isinstance(aliases, list) else [],
                    [str(s) for s in see] if isinstance(see, list) else ([str(see)] if see else []),
                    str(entry.get("source") or ""),
                )
            )
    return found


def define(packs: PackSet, word: str) -> list[Term]:
    wanted = word.strip().casefold()
    return [
        t
        for t in terms(packs)
        if t.term.casefold() == wanted or wanted in (a.casefold() for a in t.aliases)
    ]


def excerpt(body: str, full: bool) -> str:
    text = body.strip()
    if full or len(text) <= MAX_BODY:
        return text
    return _("{text}… (`--detail full` for the rest)", text=text[:MAX_BODY].rsplit(" ", 1)[0])
