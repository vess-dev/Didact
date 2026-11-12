"""What the players know: secret records, secret sections and fields, rumors.

- A record's `knowledge` is `known` (the default), `rumor` (heard of, unverified) or `secret`
  (GM only: the PCs don't know it exists).
- Body sections headed `## Secrets`, `## Secret: …` or `## GM notes` are GM only.
- Sheet fields with `secret: true` are GM only.
- A record's `details` are the GM's notes, except `looks` (what anyone who has seen it knows).

Player views (the default for `show`, `find`, `sheet`, `map` and `brief`) leave all of that
out, and `--gm` shows everything. They also never name a secret record, by id or by name:
not in a link, an inventory, or a field that points at one. Nor do they show bookkeeping
(`extra`), paths marked hidden, or values from a system whose sheet isn't loaded (without it,
which of them are secret can't be told). `reveal` makes a record known, or moves one secret line (or
a detail) into a `## Revealed` section.
"""

import copy
import re
from dataclasses import dataclass, field
from functools import reduce
from typing import cast

from didact.core.errors import InvalidError
from didact.core.i18n import _, ngettext
from didact.core.ids import normalize_name
from didact.core.output import JSON
from didact.schema.sheet import Sheet
from didact.store.entity import Entity
from didact.store.index import Row
from didact.store.repo import Repo

SECRET_HEADING = re.compile(r"^(#{1,6})\s+(secrets?|gm(\s+(notes|only))?)\b", re.IGNORECASE)
HEADING = re.compile(r"^(#{1,6})\s+\S")
REVEALED = "## Revealed"
KNOWN_DETAILS = frozenset({"looks"})  # details players see; the rest are the GM's notes
ENTRY_KEYS = ("ref", "name", "id", "to")  # what a list entry (an item, a link) is about


@dataclass(slots=True)
class Hidden:
    """What a player view left out, so the GM knows there's more."""

    lines: int = 0
    fields: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)

    def note(self, ref: str) -> str | None:
        parts: list[str] = []
        if self.lines:
            parts.append(ngettext("{n} secret line", "{n} secret lines", self.lines))
        if self.fields:
            parts.append(ngettext("secret field", "secret fields", len(self.fields)))
        if self.details:
            parts.append(ngettext("GM detail", "GM details", len(self.details)))
        if not parts:
            return None
        hidden = reduce(
            lambda first, second: _("{first} and {second}", first=first, second=second), parts
        )
        return _("({hidden} hidden: `didact show {ref} --gm` shows them)", hidden=hidden, ref=ref)


def _sections(body: str) -> list[tuple[bool, list[str]]]:
    """The body as (secret?, lines) runs. A secret section ends at a heading as high as its own."""
    runs: list[tuple[bool, list[str]]] = [(False, [])]
    level: int | None = None  # the open secret section's heading level
    for line in body.splitlines():
        heading = HEADING.match(line)
        if heading:
            depth = len(heading.group(1))
            if level is not None and depth <= level:
                level = None
            secret = SECRET_HEADING.match(line)
            if secret and level is None:
                level = depth
                runs.append((True, [line]))
                continue
            if level is None and runs[-1][0]:
                runs.append((False, []))
        runs[-1][1].append(line)
    return [(secret, lines) for secret, lines in runs if lines]


def player_body(body: str) -> tuple[str, int]:
    """The body without GM-only sections, and how many non-blank lines were left out."""
    kept: list[str] = []
    hidden = 0
    for secret, lines in _sections(body):
        if secret:
            hidden += sum(1 for line in lines[1:] if line.strip())
        else:
            kept.extend(lines)
    return "\n".join(kept).strip() + ("\n" if kept else ""), hidden


def secret_lines(body: str) -> list[str]:
    return [
        line for secret, lines in _sections(body) if secret for line in lines[1:] if line.strip()
    ]


def reveal_line(body: str, text: str) -> tuple[str, str]:
    """Move the first secret line containing `text` into `## Revealed`. Returns (body, line)."""
    wanted = text.strip().casefold()
    runs = _sections(body)
    for run_index, (secret, lines) in enumerate(runs):
        if not secret:
            continue
        for line_index, line in enumerate(lines[1:], start=1):
            if line.strip() and wanted in line.casefold():
                del lines[line_index]
                if not any(item.strip() for item in lines[1:]):
                    runs[run_index] = (True, [])  # the section is empty now: drop its heading
                return _with_revealed(runs, line), line.strip()
    known = secret_lines(body)
    hint = (
        _("its secret lines: {lines}", lines="; ".join(s.strip()[:60] for s in known))
        if known
        else _("it has no `## Secrets` section")
    )
    raise InvalidError(_("no secret line mentions {text}", text=repr(text)), hint=hint)


def reveal_detail(entity: Entity, name: str) -> str:
    """Move a GM detail into the record's `## Revealed` section. Returns the line."""
    found = next((k for k in entity.details if k.casefold() == name.strip().casefold()), None)
    if found is None:
        hint = ", ".join(entity.details) or _("none yet")
        raise InvalidError(
            _("{record} has no detail {name}", record=entity.name, name=repr(name)),
            hint=_("its details: {details}", details=hint),
        )
    line = f"- {found}: {entity.details.pop(found)}"
    entity.body = _with_revealed(_sections(entity.body), line)
    return line.removeprefix("- ")


def _with_revealed(runs: list[tuple[bool, list[str]]], line: str) -> str:
    public = [item for secret, lines in runs if not secret for item in lines]
    secret = [item for is_secret, lines in runs if is_secret for item in lines]
    bullet = line if line.lstrip().startswith(("-", "*")) else f"- {line.strip()}"
    heads = [i for i, item in enumerate(public) if item.strip() == REVEALED]
    if heads:
        end = next(
            (i for i in range(heads[0] + 1, len(public)) if HEADING.match(public[i])), len(public)
        )
        while end > heads[0] + 1 and not public[end - 1].strip():
            end -= 1
        public.insert(end, bullet)
    else:
        while public and not public[-1].strip():
            public.pop()
        public += (["", REVEALED] if public else [REVEALED]) + [bullet]
    text = "\n".join(public).strip()
    if secret:
        text += "\n\n" + "\n".join(secret).strip()
    return text + "\n"


def secret_fields(sh: Sheet) -> list[tuple[str, ...]]:
    """Paths of the sheet's `secret: true` fields: ("fields", "true_name"), ("mechanics", …)."""
    found: list[tuple[str, ...]] = []
    for schema in sh.schemas:
        for spec in schema.fields.values():
            if spec.opt("secret"):
                found.append(
                    ("fields", spec.name)
                    if schema.pack == "core"
                    else ("mechanics", schema.pack, spec.name)
                )
    return found


def secret_keys(entity: Entity) -> list[str]:
    """Paths this record keeps secret (`extra.secret_keys`, e.g. `fields.parent`)."""
    raw = entity.extra.get("secret_keys")
    return [str(k) for k in raw] if isinstance(raw, list) else []


def _drop(entity: Entity, path: tuple[str, ...]) -> bool:
    """Remove the value at a path (`fields.x`, `mechanics.<pack>.x`); True if it was there."""
    block: object = getattr(entity, path[0]) if path[0] in ("fields", "mechanics") else None
    for part in path[1:-1]:
        block = block.get(part) if isinstance(block, dict) else None
    if isinstance(block, dict) and path[-1] in block:
        del block[path[-1]]
        return True
    return False


@dataclass(frozen=True, slots=True)
class Unknown:
    """The records the players don't know, by id and by name. A name that a known record
    shares isn't a secret."""

    ids: frozenset[str] = frozenset()
    names: frozenset[str] = frozenset()

    def names_one(self, text: str) -> bool:
        """Does this text name one of them (its id, or its name or an alias, exactly)?"""
        return text.strip().partition("@")[0] in self.ids or normalize_name(text) in self.names


NOTHING = Unknown()  # for the GM: nothing is unknown


def unknown(repo: Repo) -> Unknown:
    """The records a player view here must not name: the secret ones, archived ones too."""
    rows = repo.index().rows(repo.chain(), include_archived=True)
    ids = frozenset(row.id for row in rows if not visible(row.knowledge, gm=False))
    public = {normalize_name(name) for row in rows if row.id not in ids for name in _names(row)}
    secret = {normalize_name(name) for row in rows if row.id in ids for name in _names(row)}
    return Unknown(ids, frozenset(secret - public))


def _names(row: Row) -> list[str]:
    raw = row.data.get("aliases")
    return (
        [row.name, *(a for a in raw if isinstance(a, str))] if isinstance(raw, list) else [row.name]
    )


def secret_path(how: str) -> bool:
    """A link marked hidden (`hidden-path`): a way the players haven't found."""
    return how.startswith("hidden")


def without_secrets(value: JSON, unknown: Unknown) -> tuple[JSON, bool]:
    """`value` with everything that names an unknown record taken out: an inventory item that
    is one, an id or name in a list, a field pointing at one. The flag is False when `value`
    itself names one, and should go."""
    if isinstance(value, str):
        return value, not unknown.names_one(value)
    if isinstance(value, dict):
        if any(
            isinstance(value.get(k), str) and unknown.names_one(str(value[k])) for k in ENTRY_KEYS
        ):
            return value, False
        kept: dict[str, JSON] = {}
        for key, item in value.items():
            new, keep = without_secrets(item, unknown)
            if keep:
                kept[key] = new
        return kept, True
    if isinstance(value, list):
        items: list[JSON] = []
        for item in value:
            new, keep = without_secrets(item, unknown)
            if keep:
                items.append(new)
        return items, True
    return value, True


def player_copy(entity: Entity, sh: Sheet, unknown: Unknown = NOTHING) -> tuple[Entity, Hidden]:
    """The record as the players may see it, and what was left out. `unknown`: the records
    it mustn't name (`unknown(repo)`)."""
    shown = copy.deepcopy(entity)
    hidden = Hidden()
    shown.body, hidden.lines = player_body(entity.body)
    loaded = {schema.pack for schema in sh.schemas}
    for pack in [p for p in shown.mechanics if p not in loaded]:
        del shown.mechanics[pack]  # without its sheet, its secret fields can't be told apart
    paths = [*secret_fields(sh), *(tuple(k.split(".")) for k in secret_keys(entity))]
    for path in paths:
        if _drop(shown, path):
            hidden.fields.append(path[-1])
    shown.extra, shown.other = {}, {}  # bookkeeping, and keys Didact doesn't know
    for name in [n for n in shown.details if n not in KNOWN_DETAILS]:
        del shown.details[name]  # the GM's notes: only what anyone can see stays
        hidden.details.append(name)
    shown.links = [
        link for link in shown.links if not secret_path(link.rel) and not unknown.names_one(link.to)
    ]
    if unknown != NOTHING:
        shown.fields = cast(dict[str, JSON], without_secrets(shown.fields, unknown)[0])
        for pack, block in list(shown.mechanics.items()):
            shown.mechanics[pack] = cast(dict[str, JSON], without_secrets(block, unknown)[0])
    return shown, hidden


def visible(knowledge: str, gm: bool) -> bool:
    return gm or knowledge != "secret"


def player_text(entity: Entity, sh: Sheet, unknown: Unknown = NOTHING) -> str:
    """Everything a player view shows, as one searchable text."""
    from didact.core.output import flatten, plain

    shown, _unused = player_copy(entity, sh, unknown)
    parts = [shown.body, shown.name, *shown.aliases, *shown.tags]
    parts += [f"{k} {v}" for k, v in shown.details.items()]
    for container in (shown.fields, shown.mechanics):
        parts += [f"{k} {plain(v)}" for k, v in flatten(container) if v not in ({}, [], None, "")]
    return "\n".join(str(p) for p in parts if p)


def snippet(text: str, words: list[str], width: int = 60) -> str:
    folded = text.casefold()
    at = min((folded.find(w.casefold()) for w in words if w.casefold() in folded), default=0)
    start = max(at - width // 2, 0)
    piece = " ".join(text[start : start + width * 2].split())
    return ("…" if start else "") + piece + ("…" if start + width * 2 < len(text) else "")


def player_hits(
    repo: Repo, found: list[tuple[Row, str]], words: list[str]
) -> tuple[list[tuple[Row, str]], int]:
    """Search hits a player may see: no secret records, and no match that only a secret
    section or field made. Returns the hits (with player-safe snippets) and how many hid."""
    from didact.services import sheets

    kept: list[tuple[Row, str]] = []
    hidden = 0
    from didact.core.words import Matcher

    hid = unknown(repo) if words else NOTHING
    match = Matcher([w.casefold() for w in words])
    for row, found_snippet in found:
        if row.knowledge == "secret":
            hidden += 1
            continue
        if not words:
            kept.append((row, found_snippet))
            continue
        entity = repo.located(row).entity
        text = player_text(entity, sheets.sheet(repo, entity.type), hid)
        if not match.found(text):  # matched only in what the player can't see
            hidden += 1
            continue
        kept.append((row, snippet(text, match.forms(text) or words)))
    return kept, hidden
