"""The campaign as a small website of what the players know, to share or read on a phone.

`didact export --as site --to <folder>` writes it: static pages that open from disk
(`index.html`) with no server, no network and no JavaScript.

- **The index:** the world and campaign, the party with their numbers and looks, the latest
  session's summary, and every record the players know, by type.
- **A page per record:** its text, looks, public fields and numbers, links to other pages,
  where it is, what it holds, and its chronicle (the public beats about it).
- **The journal:** each session's summary, scenes and public beats. Never the transcript.
- **The map:** the places the party knows and their exits (`?` for a place not found yet).

It is always player-safe. It reads through the player views' own filters: `knowledge.visible`
and `knowledge.player_copy` for records (no secret records, `## Secrets` or `## GM notes`,
secret fields, GM details or bookkeeping), `play.visible` for beats, `maps.lines(gm=False)`
for the map. On top of that, a reference shows only when it points at a page of the site, and
a value naming a secret record is left out, so no secret record's name or id gets in. Every
text is escaped, and Markdown is rendered with raw HTML and images off.

The folder belongs to the export: `.didact-site` lists the files it wrote. A folder that isn't
empty is refused unless it holds that list, and the next export replaces those files (and
removes the ones it no longer writes) without touching anything else in the folder.
"""

import hashlib
import html
import json
import re
import secrets
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from string.templatelib import Template

from markdown_it import MarkdownIt

from didact.core import i18n, labels
from didact.core.errors import ConflictError, InvalidError
from didact.core.i18n import _, ngettext, pgettext
from didact.core.ids import normalize_name
from didact.core.output import JSON, flatten
from didact.schema import fields as kinds
from didact.schema.sheet import Sheet
from didact.services import details, inventory, knowledge, maps, party, play, sheets
from didact.store.entity import Entity
from didact.store.index import Row
from didact.store.repo import Repo

MARKER = ".didact-site"  # the list of files an export wrote: what the next one may replace
RECORDS = "records"  # the folder of record pages
JOURNAL_TYPES = frozenset({"session", "scene", "summary"})  # the journal shows these
OS_FILES = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})  # they don't make a folder used
FIRST = ("pc", "npc", "loc", "item", "faction", "quest")  # the index lists these types first
ENTRY_KEYS = ("ref", "name", "id", "to")  # what a list entry (an item, say) is about
LINK_KINDS = frozenset({"ref", "refs"})  # sheet fields that hold record ids
PAGE_NAME = re.compile(r"[a-z0-9-]+_[a-z0-9-]+\.html")
LISTED = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*){0,2}")
CSP = "script-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"

_MARKDOWN = (
    MarkdownIt("commonmark", {"html": False, "breaks": True})
    .enable(["table", "strikethrough"])
    .disable("image")  # a picture would load from the network: it shows as a link instead
)


@dataclass(frozen=True, slots=True)
class Written:
    """What an export wrote: where, how many pages and files, and how many old files went."""

    folder: Path
    pages: int
    files: int
    records: int
    removed: int


def export(repo: Repo, folder: Path) -> Written:
    """Build the site of the active world and campaign and write it to `folder`."""
    given = folder.expanduser()
    if given.is_symlink() and not given.exists():
        raise InvalidError(
            _("{path} is a link to nothing", path=given), hint=_("give --to a real folder")
        )
    root = given.resolve()
    previous = _previous(root)  # before any work: refuse a folder that isn't the site's
    site = _Site(repo)
    files = site.files()
    removed = _write(root, files, previous)
    pages = sum(1 for rel in files if rel.endswith(".html"))
    return Written(root, pages, len(files) + 1, len(site.rows), removed)


def page_name(record_id: str) -> str:
    """A record's page: `npc:old-tom` → `npc_old-tom.html`. Ids hold only lowercase letters,
    digits, dashes and one colon, so the name is safe, stable and unique; anything else gets
    a name from its hash."""
    type_, _colon, slug = record_id.partition(":")
    name = f"{type_}_{slug}.html"
    if PAGE_NAME.fullmatch(name):
        return name
    return f"record-{hashlib.sha256(record_id.encode()).hexdigest()[:16]}.html"


# ---------------------------------------------------------------------------- safe HTML


class Markup(str):
    """HTML that is safe as it is: what `h` and the renderers return."""

    __slots__ = ()


def h(template: Template) -> Markup:
    """A t-string as HTML: every value in it is escaped, unless it's `Markup` already."""
    return Markup("".join(p if isinstance(p, str) else _html(p.value) for p in template))


def _html(value: object) -> str:
    if isinstance(value, Markup):
        return value
    if value is None or value is False:
        return ""
    if isinstance(value, str):
        return html.escape(value, quote=True)
    if isinstance(value, Iterable):
        return "".join(_html(item) for item in value)
    return html.escape(str(value), quote=True)


def _fill(message: str, /, **values: object) -> Markup:
    """A translated message (`_()` with no values: its `{name}`s still in it), escaped, with
    each value filled in as HTML (`Markup` as it is, anything else escaped)."""
    escaped = html.escape(message, quote=True)
    return Markup(escaped.format(**{name: _html(value) for name, value in values.items()}))


def _join(items: Iterable[object], sep: str) -> Markup:
    return Markup(sep.join(_html(item) for item in items))


def _markdown(text: str) -> Markup | None:
    if not text.strip():
        return None
    return h(t'<div class="prose">{Markup(_MARKDOWN.render(text))}</div>')


def _inline(text: str) -> Markup:
    return Markup(_MARKDOWN.renderInline(text))


def _section(title: str, body: object) -> Markup:
    return h(t'<section class="group"><h2>{title}</h2>{body}</section>')


def _current(on: bool) -> Markup:
    return Markup(' aria-current="page"' if on else "")


def _chip(text: str, kind: str = "") -> Markup:
    return h(t'<span class="chip{" is-" + kind if kind else ""}">{text}</span>')


# ---------------------------------------------------------------------------- the site


@dataclass(frozen=True, slots=True)
class _Held:
    """An entry in what a record holds: its name, how many, its page, and what it holds."""

    name: str
    count: int
    page: str | None
    inner: list[_Held]


class _Site:
    """Everything the players know, read once, then rendered page by page."""

    def __init__(self, repo: Repo) -> None:
        self.repo = repo
        self.world = repo.require_world()
        self.campaign = repo.active_campaign()
        self.brand = self.campaign.name if self.campaign is not None else self.world.name
        self._sheets: dict[str, Sheet] = {}
        self._read_records()
        self._read_journal()
        self.places = self._read_map()

    # ------------------------------------------------------------------ reading

    def sheet(self, type_: str) -> Sheet:
        if type_ not in self._sheets:
            self._sheets[type_] = sheets.sheet(self.repo, type_)
        return self._sheets[type_]

    def _read_records(self) -> None:
        """The records the players know (one page each), and what must never be named."""
        chain = self.repo.chain()
        everything = self.repo.index().rows(chain, include_archived=True)
        hidden = [row for row in everything if not knowledge.visible(row.knowledge, gm=False)]
        self.secret = set(knowledge.unknown(self.repo).ids) | {row.id for row in hidden}
        order = {scope: i for i, scope in enumerate(chain)}
        nearest: dict[str, Row] = {}  # the record an id means here: the narrowest scope wins
        for row in everything:
            known = nearest.get(row.id)
            if known is None or order[row.scope] < order[known.scope]:
                nearest[row.id] = row
        self.nearest = nearest
        public = {
            normalize_name(name)
            for row in everything
            if row.id not in self.secret
            for name in _names(row)
        }
        self.secret_names = {normalize_name(name) for row in hidden for name in _names(row)}
        self.secret_names -= public  # a name a known record shares isn't a secret
        ours = {scope for scope in chain if scope.kind in ("world", "campaign")}
        self.rows = {
            i: row
            for i, row in sorted(nearest.items())
            if row.scope in ours
            and not row.archived
            and i not in self.secret
            and row.type not in JOURNAL_TYPES
        }
        self.pages = {i: page_name(i) for i in self.rows}
        self.shown = {i: self._player_copy(row.entity()) for i, row in self.rows.items()}
        self.names = {i: entity.name for i, entity in self.shown.items()}
        self.holders: dict[str, list[str]] = {}  # record → the pages whose inventory holds it
        for record_id, entity in self.shown.items():
            if not self._bag(entity):
                continue
            for held in dict.fromkeys(details.held_ids(self.repo, entity)):
                if held in self.pages and held != record_id:
                    self.holders.setdefault(held, []).append(record_id)
        self.backlinks: dict[str, list[tuple[str, str]]] = {}
        for link in self.repo.index().backlinks(self.pages):
            source, target = link.source, link.target.partition("@")[0]
            if target in self.pages and self._is_page(source) and source.id != target:
                self.backlinks.setdefault(target, []).append((link.rel, source.id))

    def _is_page(self, row: Row) -> bool:
        return row.id in self.rows and self.rows[row.id].path == row.path

    def _player_copy(self, entity: Entity) -> Entity:
        """What a player view shows of a record (`knowledge.player_copy`), less any value
        that names a secret record by name, and no bookkeeping at all. Of its mechanics, only
        the active system's block stays, and only when that system's sheet is there to say
        which of its fields are secret."""
        sh = self.sheet(entity.type)
        entity.fields = self._clean(entity.fields)
        block = entity.mechanics.get(sh.mechanics.pack) if sh.mechanics is not None else None
        entity.mechanics = {}
        if sh.mechanics is not None and isinstance(block, dict):
            entity.mechanics[sh.mechanics.pack] = self._clean(block)
        unknown = knowledge.Unknown(frozenset(self.secret), frozenset(self.secret_names))
        shown, _hidden = knowledge.player_copy(entity, sh, unknown)
        shown.extra, shown.other = {}, {}
        shown.links = [link for link in shown.links if self._page_of(link.to) is not None]
        return shown

    def _clean(self, block: dict[str, JSON]) -> dict[str, JSON]:
        kept = {key: self._scrub(value) for key, value in block.items()}
        return {key: value for key, value in kept.items() if value is not None}

    def _scrub(self, value: JSON) -> JSON:
        """The value without what names a secret record, by id or by name; None when it is
        one. An entry about one (an item in an inventory, say) goes whole."""
        if isinstance(value, str):
            return None if self._names_secret(value) else value
        if isinstance(value, list):
            return [kept for item in value if (kept := self._scrub(item)) is not None]
        if isinstance(value, dict):
            named = [value.get(key) for key in ENTRY_KEYS]
            if any(isinstance(item, str) and self._names_secret(item) for item in named):
                return None
            return self._clean(value)
        return value

    def _names_secret(self, text: str) -> bool:
        ref = text.strip().partition("@")[0]
        return ref in self.secret or normalize_name(text) in self.secret_names

    def _page_of(self, ref: str) -> str | None:
        found = ref.strip().partition("@")[0]
        return found if found in self.pages else None

    def _bag(self, entity: Entity) -> inventory.Bag | None:
        bag = inventory.find_bag(entity, self.sheet(entity.type))
        return bag if bag.items else None

    def _read_journal(self) -> None:
        """The public beats of every session, and which records each one is about."""
        self.current = play.load(self.repo)
        self.sessions: list[tuple[int, list[dict[str, JSON]]]] = []
        self.chronicles: dict[str, list[dict[str, JSON]]] = {}
        for number in range(1, self.current.session + 1):
            beats = [b for b in play.beats(self.repo, number) if play.visible(b, gm=False)]
            self.sessions.append((number, beats))
            for beat in beats:
                for ref in dict.fromkeys(_about(beat)):
                    self.chronicles.setdefault(ref, []).append(beat)

    def _read_map(self) -> dict[str, dict[str, JSON]]:
        """The players' map, as `didact map` has it: place id → place."""
        _lines, data = maps.lines(self.repo, gm=False)
        listed = data.get("places")
        places = [p for p in listed if isinstance(p, dict)] if isinstance(listed, list) else []
        return {str(p.get("id")): p for p in places}

    # ------------------------------------------------------------------ pages

    def files(self) -> dict[str, str]:
        """Every file of the site: its path in the folder → its text."""
        found = {
            "style.css": STYLE,
            "favicon.svg": FAVICON,
            "index.html": self._index(),
            "journal.html": self._journal(),
            "map.html": self._map(),
        }
        for record_id, name in self.pages.items():
            found[f"{RECORDS}/{name}"] = self._record(record_id)
        return found

    def _page(self, title: str, body: object, *, here: str = "", depth: int = 0) -> str:
        up = "../" * depth
        nav = [
            h(t'<a href="{up}{href}"{_current(key == here)}>{label}</a>')
            for key, href, label in _nav()
        ]
        heading = title if title == self.brand else f"{title} · {self.brand}"
        return str(
            h(
                t'<!doctype html>\n<html lang="{i18n.current().tag}"><head><meta charset="utf-8">'
                t'<meta name="viewport" content="width=device-width, initial-scale=1">'
                t'<meta name="color-scheme" content="light dark">'
                t'<meta http-equiv="Content-Security-Policy" content="{CSP}">'
                t'<meta name="referrer" content="no-referrer"><title>{heading}</title>'
                t'<link rel="icon" href="{up}favicon.svg">'
                t'<link rel="stylesheet" href="{up}style.css"></head>\n<body>'
                t'<header class="bar"><a class="brand" href="{up}index.html">{self.brand}</a>'
                t"<nav>{nav}</nav></header>\n<main>{body}</main>\n"
                t"<footer>{_('What the players know, from Didact.')}</footer>\n</body></html>\n"
            )
        )

    def _link(self, record_id: str, base: str) -> Markup:
        return h(t'<a href="{base}{self.pages[record_id]}">{self.names[record_id]}</a>')

    def _beat(self, beat: dict[str, JSON], *, base: str, up: str, own: str | None = None) -> Markup:
        """One beat: where it happened (a link into the journal), its kind, its text, and
        the other pages it's about."""
        beat_id = str(beat.get("id") or "")
        anchor = _beat_anchor(beat_id) if beat_id else None
        where = (
            h(t'<a class="beat-where" href="{up}journal.html#{anchor}">{beat_id}</a>')
            if anchor
            else h(t'<span class="beat-where"></span>')
        )
        kind = str(beat.get("kind") or "")
        text = str(beat.get("text") or "")
        if kind == "dialogue":
            text = f"“{text}”"
        about = [r for r in dict.fromkeys(_about(beat)) if r in self.pages and r != own]
        others = [self._link(record_id, base) for record_id in about]
        with_ = h(t'<span class="dim small"> · {_join(others, ", ")}</span>') if others else None
        label = h(t'<span class="beat-kind">{_beat_kind(kind)}</span> ') if kind else None
        id_attr = h(t' id="{anchor}"') if anchor and own is None else None  # the journal's copy
        return h(
            t'<li class="beat"{id_attr}>{where}<div class="beat-text">{label}{_inline(text)}'
            t"{with_}</div></li>"
        )

    # ------------------------------------------------------------------ the index

    def _index(self) -> str:
        parts = [self._intro(), self._party(), self._latest(), self._directory()]
        return self._page(self.brand, parts, here="index")

    def _intro(self) -> Markup:
        world, campaign = self.world, self.campaign
        eyebrow = h(t'<p class="eyebrow">{world.name}</p>') if campaign is not None else None
        texts = [world.description, campaign.description if campaign is not None else ""]
        about = [_markdown(knowledge.player_body(text)[0]) for text in texts]
        counts = [
            ngettext("{n} record", "{n} records", len(self.rows)),
            ngettext("{n} session", "{n} sessions", len(self.sessions)),
            ngettext("{n} place", "{n} places", len(self.places)),
        ]
        return h(
            t'<section class="card hero">{eyebrow}<h1>{self.brand}</h1>{about}'
            t'<p class="dim small">{" · ".join(counts)}</p></section>'
        )

    def _party(self) -> Markup | None:
        cards: list[Markup] = []
        for member in party.members(self.repo, gm=False):
            record_id = str(member.entity.id)
            if record_id not in self.shown:
                continue  # a secret member, or one from outside the world and campaign
            entity = self.shown[record_id]
            role = _chip(member.role) if member.role != "pc" else None
            looks = [h(t'<p class="looks">{text}</p>') for text in entity.details.values()]
            cards.append(
                h(
                    t'<article class="card member"><div class="member-head">'
                    t'<a class="member-name" href="{RECORDS}/{self.pages[record_id]}">'
                    t"{entity.name}</a>{role}</div>{looks}{self._tiles(entity)}</article>"
                )
            )
        if not cards:
            return None
        return _section(_("The party"), h(t'<div class="cards">{cards}</div>'))

    def _latest(self) -> Markup | None:
        """The newest session with a summary."""
        for number, _beats in reversed(self.sessions):
            record = self._play_record("session", number)
            summary = _summary(record)
            if summary:
                name = record.name if record is not None else ""
                title = _numbered(_("Session {n}", n=number), f"Session {number}", name)
                link = h(t'<a href="journal.html#session-{number}">{title}</a>')
                text = _markdown(summary)
                return _section(
                    _("Last time"),
                    h(t'<div class="card"><p class="eyebrow">{link}</p>{text}</div>'),
                )
        return None

    def _directory(self) -> Markup:
        """Every page, by type."""
        by_type: dict[str, list[str]] = {}
        for record_id, row in self.rows.items():
            by_type.setdefault(row.type, []).append(record_id)
        if not by_type:
            return _section(_("Records"), h(t'<p class="dim">{_("Nothing yet.")}</p>'))
        groups: list[Markup] = []
        for type_ in sorted(by_type, key=_type_order):
            ids = sorted(by_type[type_], key=lambda i: (self.names[i].casefold(), i))
            rows = [self._row(record_id) for record_id in ids]
            count = h(t'<span class="count">{len(ids)}</span>')
            groups.append(
                h(
                    t'<section class="group" id="type-{type_}"><h2>{_label(type_)} {count}</h2>'
                    t'<ul class="list">{rows}</ul></section>'
                )
            )
        return _join(groups, "\n")

    def _row(self, record_id: str) -> Markup:
        entity = self.shown[record_id]
        marks = [
            _chip(pgettext("knowledge", "rumor"), "rumor") if entity.knowledge == "rumor" else None,
            _chip(entity.status) if entity.status != "active" else None,
        ]
        tags = h(t'<span class="row-sub">{", ".join(entity.tags)}</span>') if entity.tags else None
        return h(
            t'<li><a class="row" href="{RECORDS}/{self.pages[record_id]}">'
            t'<span class="row-title">{entity.name}{tags}</span>{marks}</a></li>'
        )

    # ------------------------------------------------------------------ a record

    def _record(self, record_id: str) -> str:
        entity = self.shown[record_id]
        parts = [
            self._head(record_id, entity),
            self._numbers(entity),
            self._body(entity),
            self._fields(entity),
            self._exits(record_id, base="", up="../"),
            self._contents(record_id, entity),
            self._links(record_id, entity),
            self._chronicle(record_id),
        ]
        return self._page(entity.name, parts, depth=1)

    def _head(self, record_id: str, entity: Entity) -> Markup:
        sh = self.sheet(entity.type)
        kind = sh.core.label if sh.core is not None and sh.core.label else _label(entity.type)
        place = self.places.get(record_id)
        state = str(place.get("state")) if place is not None else None
        marks = [
            _chip(pgettext("knowledge", "rumor"), "rumor") if entity.knowledge == "rumor" else None,
            _chip(entity.status) if entity.status != "active" else None,
            _chip(_place_state(state), "here" if state == "here" else "") if state else None,
            *(_chip(tag) for tag in entity.tags),
        ]
        chips = h(t'<div class="chips">{marks}</div>') if any(marks) else None
        lead = entity.fields.get("description")
        about = h(t'<p class="lead">{lead}</p>') if isinstance(lead, str) and lead else None
        also = ", ".join(entity.aliases)
        aliases = (
            h(t'<p class="dim small">{_("Also known as {names}", names=also)}</p>')
            if also
            else None
        )
        looks = [
            h(t'<p class="looks"><span class="dim">{_detail(name)}:</span> {text}</p>')
            for name, text in entity.details.items()  # a player copy keeps only `looks`
        ]
        return h(
            t'<section class="card head"><p class="eyebrow">{kind}</p><h1>{entity.name}</h1>'
            t"{chips}{about}{aliases}{self._where(record_id, entity)}{looks}</section>"
        )

    def _body(self, entity: Entity) -> Markup | None:
        """Its text, without the GM's sections (`player_copy` took those out)."""
        text = _markdown(entity.body)
        return h(t'<section class="card">{text}</section>') if text is not None else None

    def _where(self, record_id: str, entity: Entity) -> list[Markup]:
        """Where it is: its region if it's a place, else who or what holds it."""
        if entity.type in details.PLACE_TYPES:
            region = entity.fields.get("region")
            page = self._page_of(region) if isinstance(region, str) else None
            if page is None or page == record_id:
                return []
            where = _fill(_("In {place}"), place=self._link(page, ""))
            return [h(t'<p class="where">{where}</p>')]
        if entity.type in details.PEOPLE_TYPES:
            return []
        lines: list[Markup] = []
        for chain in self._chains(record_id):
            steps = [
                _fill(_preposition(self.shown[holder], first=i == 0), holder=self._link(holder, ""))
                for i, holder in enumerate(chain)
            ]
            lines.append(h(t'<p class="where">{_join(steps, " › ")}</p>'))
        return lines

    def _chains(self, record_id: str) -> list[list[str]]:
        """Who or what holds it, and what holds that, outward (a sword → chest → house)."""
        chains: list[list[str]] = []
        for holder in self.holders.get(record_id, []):
            chain, seen = [holder], {record_id, holder}
            while len(chain) < 12:
                outer = next((o for o in self.holders.get(chain[-1], []) if o not in seen), None)
                if outer is None:
                    break
                chain.append(outer)
                seen.add(outer)
            chains.append(chain)
        return chains

    def _numbers(self, entity: Entity) -> Markup | None:
        tiles = self._tiles(entity)
        return _section(_("Numbers"), tiles) if tiles is not None else None

    def _tiles(self, entity: Entity) -> Markup | None:
        tiles = [
            h(
                t'<div class="tile"><span class="tile-label">{item.get("label")}</span>'
                t'<span class="tile-value">{item.get("text")}</span></div>'
            )
            for item in self._numbers_of(entity)
        ]
        return h(t'<div class="tiles">{tiles}</div>') if tiles else None

    def _numbers_of(self, entity: Entity) -> list[dict[str, JSON]]:
        """The system's numbers (`sheets.stat_items` on the player copy), without a secret
        field's worked-out value, and without record ids (those show as links, in Details)."""
        sh = self.sheet(entity.type)
        if sh.mechanics is None or not entity.mechanics.get(sh.mechanics.pack):
            return []
        hidden = {spec.name for spec in sh.mechanics.fields.values() if spec.opt("secret")}
        items = [
            item
            for item in sheets.stat_items(entity, sh)
            if item.get("key") not in hidden and item.get("kind") not in LINK_KINDS
        ]
        stored = any(item.get("kind") != "derived" for item in items)
        return items if stored else []  # only worked-out values: nothing of its own to show

    def _fields(self, entity: Entity) -> Markup | None:
        """The other public values: prose fields, long lists, anything a sheet doesn't show
        as a number. What it holds, and a place's region and map state, show elsewhere."""
        sh = self.sheet(entity.type)
        bag = inventory.find_bag(entity, sh)
        skip = {"description"}  # the lead line, under its name
        if bag.block == "fields":
            skip.add(bag.spec.name)
        if entity.type in details.PLACE_TYPES:
            skip |= {"region", "discovered"}
        pairs: list[tuple[str, Markup]] = []
        for key, value in flatten(entity.fields):
            if key.partition(".")[0] in skip or value in (None, "", [], {}):
                continue
            spec = sh.core.field(key) if sh.core is not None else None
            pairs.append((spec.label if spec else key.replace("_", " "), self._value(value)))
        mechanics = sh.mechanics
        block = entity.mechanics.get(mechanics.pack) if mechanics is not None else None
        if mechanics is not None and isinstance(block, dict):
            numbers = {str(item.get("key")) for item in self._numbers_of(entity)}
            for key, value in block.items():
                spec = mechanics.field(key)
                if key in numbers or value in (None, "", [], {}):
                    continue
                if spec is None or spec.kind in LINK_KINDS:
                    pairs.append((key.replace("_", " "), self._value(value)))
                elif spec.kind != "slots":  # the inventory shows as what it holds
                    pairs.append((spec.label, h(t"{kinds.display(spec, value)}")))
        if not pairs:
            return None
        rows = [h(t"<dt>{label}</dt><dd>{text}</dd>") for label, text in pairs]
        return _section(_("Details"), h(t'<dl class="card pairs">{rows}</dl>'))

    def _value(self, value: JSON) -> Markup:
        """A field's value as text; a record's id becomes a link to its page."""
        if isinstance(value, str):
            page = self._page_of(value)
            return self._link(page, "") if page is not None else h(t"{value}")
        if isinstance(value, bool):
            return h(t"{_('yes') if value else _('no')}")
        if isinstance(value, list):
            return _join((self._value(item) for item in value), ", ")
        if isinstance(value, dict):
            return _join((h(t"{k}: {self._value(v)}") for k, v in value.items()), ", ")
        return h(t"{value}")

    def _exits(self, record_id: str, *, base: str, up: str) -> Markup | None:
        place = self.places.get(record_id)
        line = self._exit_line(place, base) if place is not None else None
        if line is None:
            return None
        more = h(t'<p class="dim small"><a href="{up}map.html">{_("The map")}</a></p>')
        return _section(_("Exits"), h(t'<div class="card">{line}{more}</div>'))

    def _exit_line(self, place: dict[str, JSON], base: str) -> Markup | None:
        """`road → The Wood · path → ?`: an exit to a place the party hasn't found is `?`."""
        raw = place.get("exits")
        exits = [e for e in raw if isinstance(e, dict)] if isinstance(raw, list) else []
        parts: list[Markup] = []
        for item in exits:
            to = item.get("to")
            target = str(to) if isinstance(to, str) and str(to) in self.places else None
            if target is None:
                name: Markup = Markup("?")
            elif target in self.pages:
                name = self._link(target, base)
            else:
                name = h(t"{self.places[target].get('name')}")
            how = str(item.get("how") or pgettext("exit", "way"))
            parts.append(h(t"{how} → {name}"))
        return h(t'<p class="exits">{_join(parts, " · ")}</p>') if parts else None

    def _contents(self, record_id: str, entity: Entity) -> Markup | None:
        held = self._held(record_id, entity, depth=4)
        if not held:
            return None
        title = _("Carrying") if entity.type in details.PEOPLE_TYPES else _("Holds")
        return _section(title, h(t'<div class="card">{self._tree(held)}</div>'))

    def _tree(self, items: list[_Held]) -> Markup:
        entries: list[Markup] = []
        for item in items:
            name = self._link(item.page, "") if item.page is not None else h(t"{item.name}")
            count = h(t' <span class="dim">×{item.count}</span>') if item.count != 1 else None
            inner = self._tree(item.inner) if item.inner else None
            entries.append(h(t"<li>{name}{count}{inner}</li>"))
        return h(t'<ul class="tree">{entries}</ul>')

    def _held(self, record_id: str, entity: Entity, *, depth: int) -> list[_Held]:
        """What it holds (`details.contents` on the player copy), nested through the pages
        of what's inside. An entry that is a secret record isn't listed at all."""
        if self._bag(entity) is None:
            return []
        found: list[_Held] = []
        for item in details.contents(self.repo, entity, depth=2):
            ref = item.get("ref")
            name = str(item.get("name") or "")
            if (isinstance(ref, str) and self._names_secret(ref)) or self._names_secret(name):
                continue
            page = self._page_of(ref) if isinstance(ref, str) else None
            count = item.get("count")
            inner = (
                self._held(page, self.shown[page], depth=depth - 1)
                if page is not None and page != record_id and depth > 1
                else []
            )
            found.append(
                _Held(
                    self.names[page] if page is not None else name,
                    count if isinstance(count, int) else 1,
                    page,
                    inner,
                )
            )
        return found

    def _links(self, record_id: str, entity: Entity) -> list[Markup]:
        """Its links to other pages, and the pages that link to it."""
        out = [
            (link.rel, page)
            for link in entity.links
            if (page := self._page_of(link.to)) and self._shows_link(link.rel, record_id, page)
        ]
        back = [
            (rel, source)
            for rel, source in self.backlinks.get(record_id, [])
            if self._shows_link(rel, source, record_id)
        ]
        found: list[Markup] = []
        for title, pairs in ((_("Links"), out), (_("Linked from"), back)):
            rows = [
                h(t"<li>{_chip(rel)} {self._link(page, '')}</li>")
                for rel, page in dict.fromkeys(pairs)
            ]
            if rows:
                found.append(_section(title, h(t'<ul class="card links">{rows}</ul>')))
        return found

    def _shows_link(self, rel: str, source: str, target: str) -> bool:
        """A hidden path stays hidden, and a way from one place to another is an exit: it
        shows as the map shows it (only from where the party has been)."""
        places = maps.PLACE_TYPES
        exit_ = self.rows[source].type in places and self.rows[target].type in places
        return not knowledge.secret_path(rel) and not exit_

    def _chronicle(self, record_id: str) -> Markup | None:
        beats = self.chronicles.get(record_id, [])
        if not beats:
            return None
        items = [self._beat(beat, base="", up="../", own=record_id) for beat in beats]
        return _section(_("Chronicle"), h(t'<ol class="timeline card">{items}</ol>'))

    # ------------------------------------------------------------------ the journal

    def _play_record(self, type_: str, number: int) -> Entity | None:
        """A session or scene record, if the players may see it."""
        found = (
            play.session_record(self.repo, number)
            if type_ == "session"
            else play.scene_record(self.repo, number)
        )
        return found if found is not None and knowledge.visible(found.knowledge, False) else None

    def _journal(self) -> str:
        parts: list[Markup | None] = [h(t"<h1>{_('Journal')}</h1>"), self._story()]
        if not self.sessions:
            none = (
                _("No sessions yet.")
                if self.campaign is not None
                else _("No sessions yet: sessions belong to a campaign.")
            )
            parts.append(h(t'<p class="dim">{none}</p>'))
        if len(self.sessions) > 1:
            links = [
                h(t'<li><a href="#session-{n}">{_("Session {n}", n=n)}</a></li>')
                for n, _beats in self.sessions
            ]
            label = _("Sessions")
            parts.append(h(t'<nav class="toc" aria-label="{label}"><ul>{links}</ul></nav>'))
        parts += [self._session(number, beats) for number, beats in self.sessions]
        return self._page(_("Journal"), parts, here="journal")

    def _story(self) -> Markup | None:
        """The campaign's own summaries: the story so far, then the arcs."""
        rows = [
            (record_id, row)
            for record_id, row in self.nearest.items()
            if row.type == "summary"
            and row.scope.kind == "campaign"
            and not row.archived
            and record_id not in self.secret
        ]
        rows.sort(key=lambda item: (item[0] != "summary:campaign", item[1].name.casefold()))
        cards: list[Markup] = []
        for _id, row in rows:
            text = knowledge.player_body(row.body)[0]
            text = play.get_summary(text) or text.strip()
            if text:
                cards.append(_story_card(row.name, text))
        return _join(cards, "\n") if cards else None

    def _session(self, number: int, beats: list[dict[str, JSON]]) -> Markup:
        record = self._play_record("session", number)
        title = record.name if record is not None else ""
        status = record.fields.get("status") if record is not None else None
        badge = h(t" {_chip(pgettext('session', 'open'), 'here')}") if status == "open" else None
        listed = record.fields.get("scenes") if record is not None else None
        scenes = [s for s in listed if isinstance(s, int)] if isinstance(listed, list) else []
        for beat in beats:
            scene = beat.get("scene")
            if isinstance(scene, int) and scene not in scenes:
                scenes.append(scene)
        loose = [b for b in beats if not isinstance(b.get("scene"), int)]
        parts: list[Markup | None] = [_markdown(_summary(record)), self._timeline(loose)]
        for scene in scenes:
            own = [b for b in beats if b.get("scene") == scene]
            parts.append(self._scene(scene, own))
        if not beats and not _summary(record):
            parts.append(h(t'<p class="dim">{_("Nothing was written down.")}</p>'))
        heading = _numbered(_("Session {n}", n=number), f"Session {number}", title)
        return h(
            t'<section class="card session" id="session-{number}">'
            t"<h2>{heading}{badge}</h2>{parts}</section>"
        )

    def _scene(self, number: int, beats: list[dict[str, JSON]]) -> Markup | None:
        record = self._play_record("scene", number)
        if record is None and not beats:
            return None  # a scene out of the players' sight
        title = record.name if record is not None else ""
        summary = _markdown(_summary(record))
        about = h(t'<div class="dim">{summary}</div>') if summary is not None else None
        heading = _numbered(_("Scene {n}", n=number), f"Scene {number}", title)
        return h(t'<h3 id="scene-{number}">{heading}</h3>{about}{self._timeline(beats)}')

    def _timeline(self, beats: list[dict[str, JSON]]) -> Markup | None:
        if not beats:
            return None
        items = [self._beat(beat, base=f"{RECORDS}/", up="") for beat in beats]
        return h(t'<ol class="timeline">{items}</ol>')

    # ------------------------------------------------------------------ the map

    def _map(self) -> str:
        children: dict[str | None, list[str]] = {}
        for place_id, place in self.places.items():
            region = place.get("region")
            parent = region if isinstance(region, str) and region in self.places else None
            children.setdefault(None if parent == place_id else parent, []).append(place_id)
        seen: set[str] = set()
        tree = self._places(children, None, seen)
        for place_id in sorted(set(self.places) - seen):  # regions in a loop: shown on their own
            tree += self._places({**children, None: [place_id]}, None, seen)
        here = next((p for p, place in self.places.items() if place.get("state") == "here"), None)
        where = None
        if here is not None:
            at = _fill(_("The party is at {place}."), place=self._place_name(here, f"{RECORDS}/"))
            where = h(t'<p class="card">{at}</p>')
        body = (
            h(t'<ul class="tree card">{tree}</ul>')
            if tree
            else h(t'<p class="dim">{_("No places known yet.")}</p>')
        )
        legend = _(
            "Exits show for the places the party has been; "
            "one that leads somewhere not found yet is ?."
        )
        note = h(t'<p class="dim small">{legend}</p>')
        title = _("Map")
        return self._page(title, [h(t"<h1>{title}</h1>"), where, body, note], here="map")

    def _places(
        self, children: dict[str | None, list[str]], parent: str | None, seen: set[str]
    ) -> list[Markup]:
        items: list[Markup] = []
        for place_id in sorted(children.get(parent, []), key=self._sort_place):
            if place_id in seen:
                continue
            seen.add(place_id)
            place = self.places[place_id]
            state = str(place.get("state") or "")
            chip = _chip(_place_state(state), "here" if state == "here" else "") if state else None
            exits = self._exit_line(place, f"{RECORDS}/")
            inner = self._places(children, place_id, seen)
            nested = h(t'<ul class="tree">{inner}</ul>') if inner else None
            name = self._place_name(place_id, f"{RECORDS}/")
            anchor = _anchor(place_id)
            items.append(h(t'<li id="place-{anchor}">{name} {chip}{exits}{nested}</li>'))
        return items

    def _sort_place(self, place_id: str) -> tuple[str, str]:
        return (str(self.places[place_id].get("name")).casefold(), place_id)

    def _place_name(self, place_id: str, base: str) -> Markup:
        if place_id in self.pages:
            return self._link(place_id, base)
        return h(t"{self.places[place_id].get('name')}")


def _story_card(name: str, text: str) -> Markup:
    return h(
        t'<section class="card story"><p class="eyebrow">{name}</p>{_markdown(text)}</section>'
    )


def _summary(record: Entity | None) -> str:
    """A session's or scene's summary, without what its text keeps for the GM."""
    return play.get_summary(knowledge.player_body(record.body)[0]) if record is not None else ""


def _about(beat: dict[str, JSON]) -> list[str]:
    raw = beat.get("about")
    return [str(ref).partition("@")[0] for ref in raw] if isinstance(raw, list) else []


def _names(row: Row) -> list[str]:
    raw = row.data.get("aliases")
    aliases = [a for a in raw if isinstance(a, str)] if isinstance(raw, list) else []
    return [row.name, *aliases]


def _nav() -> tuple[tuple[str, str, str], ...]:
    """The header's links: (key, page, label)."""
    return (
        ("index", "index.html", _("Home")),
        ("journal", "journal.html", _("Journal")),
        ("map", "map.html", _("Map")),
    )


def _labels() -> dict[str, str]:
    """The index's headings for the usual record types."""
    return labels.types_plural()


def _label(type_: str) -> str:
    return _labels().get(type_, type_.replace("-", " ").capitalize())


def _beat_kind(kind: str) -> str:
    """A journal beat's kind, as its label shows it (an unknown kind as it is)."""
    kinds = {
        "action": pgettext("beat kind", "action"),
        "oracle": pgettext("beat kind", "oracle"),
        "roll": pgettext("beat kind", "roll"),
        "result": pgettext("beat kind", "result"),
        "consequence": pgettext("beat kind", "consequence"),
        "narration": pgettext("beat kind", "narration"),
        "dialogue": pgettext("beat kind", "dialogue"),
        "note": pgettext("beat kind", "note"),
        "ooc": pgettext("beat kind", "ooc"),
    }
    return kinds.get(kind, kind)


def _place_state(state: str) -> str:
    """A place's state on the map (`maps.Place.state`), as its chip shows it."""
    states = {
        "here": pgettext("place", "here"),
        "visited": pgettext("place", "visited"),
        "rumored": pgettext("place", "rumored"),
        "not visited": pgettext("place", "not visited"),
    }
    return states.get(state, state)


def _detail(name: str) -> str:
    """A detail's name as a label (players only ever see `looks`)."""
    return _("Looks") if name == "looks" else name.capitalize()


def _type_order(type_: str) -> tuple[int, str]:
    return (FIRST.index(type_) if type_ in FIRST else len(FIRST), _label(type_))


def _preposition(entity: Entity, *, first: bool) -> str:
    """How a holder holds it: `carried by` a person, `at` a place, `in` anything else. A
    message with `{holder}` in it, for `_fill`; the first of a chain starts a sentence."""
    if entity.type in details.PEOPLE_TYPES:
        return _("Carried by {holder}") if first else _("carried by {holder}")
    if entity.type in details.PLACE_TYPES:
        return _("At {holder}") if first else _("at {holder}")
    return _("In {holder}") if first else _("in {holder}")


def _numbered(plain: str, english: str, title: str) -> str:
    """`Session 3 · The Wood`, or just `Session 3` when that's all its name says (in the
    language in use, or in English, as a record's own name may be)."""
    return plain if title in ("", plain, english) else f"{plain} · {title}"


def _anchor(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-") or "x"


def _beat_anchor(beat_id: str) -> str:
    return f"beat-{_anchor(beat_id)}"


# ---------------------------------------------------------------------------- the folder


def _previous(root: Path) -> set[str]:
    """The files an earlier export wrote into the folder (none if it's new or empty).
    Refuses a folder that holds anything else."""
    if not root.exists():
        return set()
    if not root.is_dir():
        raise InvalidError(
            _("{path} is a file, not a folder", path=root),
            hint=_("--to names a folder: a new one, or one an earlier `export --as site` wrote"),
        )
    marker = root / MARKER
    if marker.is_file() and not marker.is_symlink():
        return _listed(marker)
    if any(entry.name not in OS_FILES for entry in root.iterdir()):
        raise ConflictError(
            _("{path} isn't empty, and no site was exported there", path=root),
            hint=_("export to a new or empty folder (later exports there replace only the site)"),
        )
    return set()


def _listed(marker: Path) -> set[str]:
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConflictError(
            _("can't read {path}, so what the last export wrote is unclear", path=marker),
            hint=_("export to a new folder, or delete the old site first"),
        ) from exc
    site = isinstance(data, dict) and data.get("didact") == "site"
    files = data.get("files") if site else None
    if not isinstance(files, list):
        raise ConflictError(
            _("{path} doesn't list the files of a site", path=marker),
            hint=_("export to a new folder, or delete the old site first"),
        )
    return {f for f in files if isinstance(f, str) and _safe(f)}


def _safe(rel: str) -> bool:
    """A path an export could have written: relative, plain names, no way out of the folder."""
    return bool(LISTED.fullmatch(rel)) and rel != MARKER


def _write(root: Path, files: dict[str, str], previous: set[str]) -> int:
    """Write the site; remove what the last export wrote and this one doesn't. Returns how
    many old files went. The list is written first with both, so a failure half way never
    leaves a file of the site unlisted."""
    for rel in files:
        blocker = _in_the_way(root, rel, previous)
        if blocker is not None:
            raise ConflictError(
                _("{path} is in the way: it isn't from an earlier export", path=root / blocker),
                hint=_("move it out of the folder, or export to a new one"),
            )
    root.mkdir(parents=True, exist_ok=True)
    _put(root / MARKER, _marker(previous | set(files)))
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(exist_ok=True)
        _put(path, text)
    removed = sum(1 for rel in sorted(previous - set(files)) if _remove(root, rel))
    _put(root / MARKER, _marker(set(files)))
    return removed


def _in_the_way(root: Path, rel: str, previous: set[str]) -> str | None:
    """What stops the export writing `rel`: a file it didn't write, or a folder that isn't
    a plain folder (a link could lead out of `--to`)."""
    current = root
    parts = rel.split("/")
    for part in parts[:-1]:
        current = current / part
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            return str(current.relative_to(root))
    path = root / rel
    taken = path.exists() or path.is_symlink()
    if taken and (rel not in previous or (path.is_dir() and not path.is_symlink())):
        return rel
    return None


def _put(path: Path, text: str) -> None:
    """Write a file whole: a reader sees the old one or the new one. The new file takes the
    place of whatever was there, and never writes through a link."""
    temp = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    try:
        with temp.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        temp.replace(path)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def _remove(root: Path, rel: str) -> bool:
    """Delete one file an earlier export wrote, and the folders it leaves empty. Anything
    that isn't a plain file in plain folders under `root` stays."""
    current = root
    for part in rel.split("/")[:-1]:
        current = current / part
        if current.is_symlink() or not current.is_dir():
            return False
    path = root / rel
    gone = path.is_symlink() or path.is_file()
    if gone:
        path.unlink()
    parent = path.parent
    while parent != root:
        try:
            parent.rmdir()  # only when empty
        except OSError:
            break
        parent = parent.parent
    return gone


def _marker(files: Iterable[str]) -> str:
    data: dict[str, JSON] = {
        "didact": "site",
        "about": _(
            "Written by `didact export --as site`. The next export into this folder "
            "replaces these files (and removes the ones it no longer writes); nothing else."
        ),
        "files": list[JSON](sorted(files)),
    }
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


# ---------------------------------------------------------------------------- the look

FAVICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path d="M12 2l8.66 5v10L12 22l-8.66-5V7z" fill="#3584e4"/></svg>\n'
)

STYLE = """\
/* A Didact site: what the players know. Plain CSS after GNOME's libadwaita, light and dark. */
:root {
  color-scheme: light dark;
  --window: #fafafa; --view: #ffffff; --fg: rgb(0 0 6 / 80%); --dim: rgb(0 0 6 / 55%);
  --border: rgb(0 0 6 / 12%); --button: rgb(0 0 6 / 7%); --hover: rgb(0 0 6 / 4%);
  --shadow: 0 0 0 1px rgb(0 0 6 / 7%), 0 1px 3px 1px rgb(0 0 6 / 6%);
  --accent: #3584e4; --accent-text: #1c71d8; --rumor: #9141ac;
  --font: system-ui, -apple-system, "Segoe UI", Cantarell, Ubuntu, Roboto, sans-serif;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --window: #242424; --view: #303030; --fg: #ffffff; --dim: rgb(255 255 255 / 55%);
    --border: rgb(255 255 255 / 10%); --button: rgb(255 255 255 / 10%);
    --hover: rgb(255 255 255 / 5%);
    --shadow: 0 0 0 1px rgb(0 0 6 / 30%), 0 1px 3px 1px rgb(0 0 6 / 30%);
    --accent-text: #78aeed; --rumor: #dc8add;
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }
body {
  margin: 0; font: 400 16px/1.55 var(--font); color: var(--fg); background: var(--window);
  overflow-wrap: anywhere; -webkit-font-smoothing: antialiased;
}
a { color: var(--accent-text); text-decoration: none; }
a:hover { text-decoration: underline; }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 4px; }
h1, h2, h3 { margin: 0; line-height: 1.25; }
h1 { font-size: 26px; }
h2 { font-size: 17px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
h3 { font-size: 15px; margin-top: 12px; }
p { margin: 0; }
code, pre { font-family: var(--mono); font-size: 0.92em; }

/* the header bar, the page, the footer */
.bar {
  position: sticky; top: 0; z-index: 1; display: flex; flex-wrap: wrap; align-items: center;
  gap: 2px 12px; padding: 6px 12px; background: var(--view);
  border-bottom: 1px solid var(--border);
}
.brand { margin-right: auto; padding: 4px; font-weight: 700; color: var(--fg); }
.bar nav { display: flex; gap: 2px; }
.bar nav a { padding: 5px 12px; border-radius: 6px; color: var(--fg); font-weight: 500; }
.bar nav a:hover { background: var(--hover); text-decoration: none; }
.bar nav a[aria-current] { background: var(--button); }
main {
  max-width: 760px; margin: 0 auto; padding: 20px 16px 40px; display: flex;
  flex-direction: column; gap: 24px;
}
footer {
  max-width: 760px; margin: 0 auto; padding: 0 16px 32px; color: var(--dim); font-size: 13px;
}

/* cards, groups, lists, chips */
.card {
  background: var(--view); border-radius: 12px; box-shadow: var(--shadow); padding: 14px 16px;
  display: flex; flex-direction: column; gap: 10px;
}
.group { display: flex; flex-direction: column; gap: 10px; }
.eyebrow {
  font-size: 12px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;
  color: var(--accent-text);
}
.dim { color: var(--dim); }
.small { font-size: 14px; }
.count {
  min-width: 24px; padding: 0 8px; border-radius: 999px; background: var(--button);
  color: var(--dim); font-size: 12px; font-weight: 700; text-align: center;
}
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chips:empty { display: none; }
.chip {
  display: inline-block; padding: 1px 10px; border-radius: 999px; background: var(--button);
  font-size: 13px; font-weight: 400; white-space: nowrap;
}
.chip.is-rumor { background: color-mix(in srgb, var(--rumor) 22%, transparent); }
.chip.is-here { background: var(--accent); color: #ffffff; }
.list {
  list-style: none; margin: 0; padding: 0; background: var(--view); border-radius: 12px;
  box-shadow: var(--shadow); overflow: hidden;
}
.list > li + li { border-top: 1px solid var(--border); }
.row {
  display: flex; align-items: center; gap: 8px; min-height: 48px; padding: 8px 14px;
  color: var(--fg);
}
a.row:hover { background: var(--hover); text-decoration: none; }
.row-title { flex: 1; min-width: 0; }
.row-sub { display: block; font-size: 13px; color: var(--dim); }
.lead { font-size: 17px; }
.links { list-style: none; margin: 0; gap: 6px; }
.toc ul { display: flex; flex-wrap: wrap; gap: 6px; list-style: none; margin: 0; padding: 0; }
.toc a {
  display: inline-block; padding: 2px 12px; border-radius: 999px; background: var(--button);
}

/* records: the party, numbers, details, whereabouts */
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
.member-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.member-name { font-size: 17px; font-weight: 700; }
.tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(92px, 1fr)); gap: 8px; }
.tile {
  display: flex; flex-direction: column; padding: 8px 12px; border-radius: 10px;
  background: var(--button);
}
.tile-label {
  font-size: 11.5px; color: var(--dim); text-transform: uppercase; letter-spacing: 0.04em;
}
.tile-value { font-size: 19px; font-weight: 500; }
.pairs {
  display: grid; grid-template-columns: minmax(80px, max-content) 1fr; gap: 6px 16px; margin: 0;
}
.pairs dt { color: var(--dim); }
.pairs dd { margin: 0; }
.where, .exits { color: var(--dim); }
.tree { list-style: none; margin: 0; padding-left: 18px; }
.card > .tree, ul.tree.card { padding-left: 16px; }
.tree li { padding: 3px 0; }

/* the journal and chronicles */
.timeline { list-style: none; margin: 0; padding: 0; }
.beat { display: flex; align-items: baseline; gap: 10px; padding: 6px 0; }
.beat + .beat { border-top: 1px solid var(--border); }
.beat-where {
  flex: none; min-width: 44px; font-family: var(--mono); font-size: 13px; color: var(--dim);
}
.beat-text { flex: 1; min-width: 0; }
.beat-kind {
  font-size: 11.5px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase;
  color: var(--accent-text);
}
:target { scroll-margin-top: 64px; }
li:target, h3:target {
  background: color-mix(in srgb, var(--accent) 12%, transparent); border-radius: 6px;
}

/* Markdown */
.prose > :first-child { margin-top: 0; }
.prose > :last-child { margin-bottom: 0; }
.prose p, .prose ul, .prose ol { margin: 0.5em 0; }
.prose ul, .prose ol { padding-left: 1.4em; }
.prose h1, .prose h2, .prose h3, .prose h4 { font-size: 1.05em; margin: 1em 0 0.4em; }
.prose code { background: var(--button); padding: 1px 5px; border-radius: 5px; }
.prose pre {
  background: var(--button); padding: 10px 12px; border-radius: 8px; overflow-x: auto;
}
.prose pre code { background: none; padding: 0; }
.prose blockquote {
  margin: 0.5em 0; padding-left: 12px; border-left: 3px solid var(--border); color: var(--dim);
}
.prose table { display: block; overflow-x: auto; border-collapse: collapse; }
.prose th, .prose td {
  padding: 4px 10px; border-bottom: 1px solid var(--border); text-align: left;
}
.prose hr { border: 0; border-top: 1px solid var(--border); }

@media (max-width: 520px) {
  h1 { font-size: 22px; }
  main { padding: 16px 12px 32px; gap: 20px; }
  .pairs { grid-template-columns: 1fr; gap: 0; }
  .pairs dd { margin-bottom: 8px; }
}
"""
