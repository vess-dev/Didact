"""Details, the chronicle and whereabouts: what keeps a game consistent from scene to scene.

- **Details** are short named notes on any record, for whoever runs the game: what it looks
  like, its personality, what it wants and fears, what it's doing and plans next, where it is,
  its history and secrets, and the author's own thoughts about it.
  `didact about sweeney plan='sell the route' doing='sharpening a knife'` writes them, and
  `didact about sweeney` reads them back. Players see only `looks`; `didact reveal sweeney plan`
  moves one into the record's text once the players learn it.
- **The chronicle** is the journal beats about a record (`didact log consequence '…' --about
  sweeney --about freya`): what it did and what happened to it, one beat shared by everyone
  involved.
- **Whereabouts** follow the inventories: a sword in a chest in a house is where the chest's
  inventory holds it (`didact where sword` → Chest › My House), and `show` on the house lists
  what's in it, all the way down.
"""

from dataclasses import dataclass

from didact.core.errors import DidactError, InvalidError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.services import inventory, sheets
from didact.store.entity import Entity
from didact.store.repo import Repo

PEOPLE = (
    "looks", "personality", "wants", "fears", "attitude", "doing", "plan", "where", "history",
    "secret", "thoughts",
)  # fmt: skip
THINGS = ("looks", "history", "where", "powers", "secret", "thoughts")
PLACES = ("looks", "state", "history", "secret", "thoughts")
GROUPS = ("wants", "plan", "state", "history", "secret", "thoughts")
OTHER = ("looks", "state", "history", "secret", "thoughts")

FAMILIES: dict[str, tuple[str, ...]] = {
    **dict.fromkeys(
        ("pc", "npc", "character", "monster", "creature", "beast", "animal", "companion",
         "hireling", "follower", "person", "spirit", "deity"),
        PEOPLE,
    ),
    **dict.fromkeys((*inventory.ITEM_TYPES, "container", "vehicle"), THINGS),
    **dict.fromkeys(
        ("loc", "location", "place", "site", "region", "settlement", "dungeon", "room", "area",
         "building", "landmark", "poi", "hex"),
        PLACES,
    ),
    **dict.fromkeys(
        ("faction", "group", "organization", "guild", "cult", "clan", "order"), GROUPS
    ),
}  # fmt: skip

MEANING: dict[str, str] = {
    "looks": "what anyone can see (players see this one)",
    "personality": "manner, traits, voice",
    "wants": "motives and goals",
    "fears": "what it avoids or dreads",
    "attitude": "how it feels about the PCs, and why",
    "doing": "what it's doing right now",
    "plan": "what it will do next",
    "where": "where it is now",
    "history": "backstory: where it came from, who made or owned it",
    "powers": "what it can do",
    "state": "its condition: guarded, flooded, burning, …",
    "secret": "what the players don't know yet",
    "thoughts": "your own notes: why it exists, where it could lead",
}

PEOPLE_TYPES = frozenset(k for k, v in FAMILIES.items() if v is PEOPLE)
PLACE_TYPES = frozenset(k for k, v in FAMILIES.items() if v is PLACES)
IN_SCENE = ("where", "doing", "plan")  # what a scene or a fight needs at hand


# ---------------------------------------------------------------------------- details


def suggested(repo: Repo, entity: Entity) -> list[str]:
    """Detail names worth filling for this record: its schema's list, or its kind's."""
    names: tuple[str, ...] = ()
    try:
        sh = sheets.sheet(repo, entity.type)
    except DidactError:
        sh = None
    if sh is not None:
        for schema in (sh.mechanics, sh.core):
            if schema is not None and schema.details:
                names = schema.details
                break
    return list(names or FAMILIES.get(entity.type, OTHER))


def missing(repo: Repo, entity: Entity) -> list[str]:
    """Suggested details not filled yet."""
    have = {k.casefold() for k in entity.details}
    return [n for n in suggested(repo, entity) if n.casefold() not in have]


def apply(entity: Entity, values: dict[str, str], clear: list[str]) -> list[str]:
    """Set and clear details. Returns lines saying what changed."""
    changed: list[str] = []
    for name in clear:
        found = _key(entity, name)
        if found is None:
            raise InvalidError(
                _("{name} has no detail {detail}", name=entity.name, detail=repr(name)),
                hint=_("its details: {details}", details=", ".join(entity.details))
                if entity.details
                else _("its details: none yet"),
            )
        del entity.details[found]
        changed.append(_("{detail}: cleared", detail=found))
    for name, text in values.items():
        clean = name.strip().lower()
        if not clean or not all(c.isalnum() or c in "_-" for c in clean):
            raise InvalidError(
                _("a detail's name is one word, not {name}", name=repr(name)),
                hint=_("e.g. plan='…', looks='…'"),
            )
        found = _key(entity, clean) or clean
        if not text.strip():
            entity.details.pop(found, None)
            changed.append(_("{detail}: cleared", detail=found))
            continue
        entity.details[found] = text.strip()
        changed.append(f"{found}: {text.strip()}")
    return changed


def _key(entity: Entity, name: str) -> str | None:
    wanted = name.strip().casefold()
    return next((k for k in entity.details if k.casefold() == wanted), None)


def lines(entity: Entity, *, gm: bool) -> list[str]:
    """`key: text` lines for the details a viewer may see."""
    from didact.services.knowledge import KNOWN_DETAILS

    return [
        f"{name}: {text}"
        if name in KNOWN_DETAILS
        else _("{name}: {text} (GM)", name=name, text=text)
        for name, text in entity.details.items()
        if gm or name in KNOWN_DETAILS
    ]


# ---------------------------------------------------------------------------- chronicle


def chronicle(repo: Repo, entity_id: str, *, gm: bool) -> list[dict[str, JSON]]:
    """The journal beats about a record in this campaign, oldest first. Secret beats (things
    happening out of the players' sight) only for the GM, and for players, only the records
    each beat is about that they know."""
    from didact.services import knowledge, play

    if repo.active_campaign() is None:
        return []
    current = play.load(repo)
    hid = knowledge.NOTHING if gm else knowledge.unknown(repo)
    found: list[dict[str, JSON]] = []
    for session in range(1, current.session + 1):
        for beat in play.beats(repo, session):
            about = beat.get("about")
            if not isinstance(about, list) or entity_id not in about:
                continue
            if beat.get("secret") and not gm:
                continue
            if not gm:
                beat = {**beat, "about": [a for a in about if not hid.names_one(str(a))]}
            found.append(beat)
    return found


def chronicle_line(beat: dict[str, JSON]) -> str:
    from didact.services import play

    if beat.get("secret"):
        return _("{id}: {beat} (GM)", id=beat.get("id"), beat=play.beat_line(beat))
    return f"{beat.get('id')}: {play.beat_line(beat)}"


# ---------------------------------------------------------------------------- whereabouts


@dataclass(slots=True)
class Holding:
    """A record whose inventory holds something: who, and the entry there."""

    holder: Entity
    entry: JSON


def _entries(repo: Repo, entity: Entity) -> list[JSON]:
    try:
        return list(inventory.find_bag(entity, sheets.sheet(repo, entity.type)).items)
    except DidactError:
        return []


def _entry_ref(entry: JSON) -> str | None:
    ref = entry.get("ref") if isinstance(entry, dict) else None
    return str(ref) if isinstance(ref, str) and ref else None


def _holdings(repo: Repo, name: str, *, gm: bool) -> list[Holding]:
    """Inventory entries of the records whose text mentions `name` (the index narrows it)."""
    found: list[Holding] = []
    seen: set[str] = set()
    for hit in repo.index().search(name, repo.chain(), limit=500):
        row = hit.row
        if row.path in seen or (not gm and row.knowledge == "secret"):
            continue
        seen.add(row.path)
        entity = row.entity()
        found += [Holding(entity, entry) for entry in _entries(repo, entity)]
    return found


def _matches(held: Holding, target: Entity | None, name: str) -> bool:
    ref = _entry_ref(held.entry)
    if target is not None and ref == str(target.id):
        return True
    wanted = (target.name if target is not None else name).casefold()
    return ref is None and inventory.name_of(held.entry).casefold() == wanted


def _record_named(repo: Repo, name: str) -> Entity | None:
    """The one record with this name (an inventory entry that is a record by name)."""
    rows = repo.index().by_name(name, repo.chain())
    return rows[0].entity() if len(rows) == 1 else None


def where(repo: Repo, thing: str, *, gm: bool = True) -> list[list[Entity]]:
    """Where something is: for each place it's held, the chain of holders from the nearest
    outward (a sword → [Chest, My House]). A thing can be in several places (two swords)."""
    try:
        target: Entity | None = repo.resolve(thing).entity
    except DidactError:
        target = None
    name = target.name if target is not None else thing
    held = [
        h
        for h in _holdings(repo, name, gm=gm)
        if not (target is not None and h.holder.id == target.id)
    ]
    found = [h for h in held if _matches(h, target, thing)]
    if not found:  # "sword" finds a Long Sword: every word of the question in the item's name
        wanted = _words(thing)
        found = [h for h in held if wanted and wanted <= _words(inventory.name_of(h.entry))]
    chains: list[list[Entity]] = []
    for holding in found:
        chain = [holding.holder]
        seen = {str(holding.holder.id)}
        while len(chain) < 12:
            outer = _holder_of(repo, chain[-1], gm=gm)
            if outer is None or str(outer.id) in seen:
                break
            chain.append(outer)
            seen.add(str(outer.id))
        chains.append(chain)
    return chains


def _words(text: str) -> set[str]:
    return {w for w in "".join(c if c.isalnum() else " " for c in text.casefold()).split() if w}


def _holder_of(repo: Repo, entity: Entity, *, gm: bool) -> Entity | None:
    for holding in _holdings(repo, entity.name, gm=gm):
        if holding.holder.id != entity.id and _matches(holding, entity, entity.name):
            return holding.holder
    return None


def chain_text(chain: list[Entity]) -> str:
    """`in Chest (item:chest) › at My House (loc:house)`."""
    return " › ".join(_held_by(e) for e in chain)


def _held_by(entity: Entity) -> str:
    if entity.type in PEOPLE_TYPES:
        return _("carried by {name} ({id})", name=entity.name, id=entity.id)
    if entity.type in PLACE_TYPES:
        return _("at {name} ({id})", name=entity.name, id=entity.id)
    return _("in {name} ({id})", name=entity.name, id=entity.id)


def held_ids(repo: Repo, entity: Entity) -> list[str]:
    """The records this one holds directly (by `ref`, or by a record's unique name)."""
    found: list[str] = []
    for entry in _entries(repo, entity):
        ref = _entry_ref(entry)
        if ref is None:
            named = _record_named(repo, inventory.name_of(entry))
            ref = str(named.id) if named is not None and named.id != entity.id else None
        if ref is not None:
            found.append(ref)
    return found


def contents(repo: Repo, entity: Entity, *, depth: int = 4) -> list[dict[str, JSON]]:
    """What a record holds, nested: a chest's contents appear under the chest."""
    out: list[dict[str, JSON]] = []
    for entry in _entries(repo, entity):
        item: dict[str, JSON] = {"name": inventory.name_of(entry)}
        count = inventory.count_of(entry)
        if count != 1:
            item["count"] = count
        ref = _entry_ref(entry)
        inner: Entity | None = None
        if ref is not None:
            item["ref"] = ref
            try:
                inner = repo.resolve(ref).entity
            except DidactError:
                inner = None
        else:
            inner = _record_named(repo, str(item["name"]))
            if inner is not None and inner.id == entity.id:
                inner = None
        if inner is not None and depth > 1:
            item.setdefault("ref", str(inner.id))
            nested = contents(repo, inner, depth=depth - 1)
            if nested:
                item["contents"] = list[JSON](nested)
        out.append(item)
    return out


def contents_lines(items: list[dict[str, JSON]], indent: str = "") -> list[str]:
    lines_: list[str] = []
    for item in items:
        count = f" ×{item['count']}" if "count" in item else ""
        ref = f" ({item['ref']})" if "ref" in item else ""
        lines_.append(f"{indent}- {item['name']}{count}{ref}")
        inner = item.get("contents")
        if isinstance(inner, list):
            lines_ += contents_lines([i for i in inner if isinstance(i, dict)], indent + "  ")
    return lines_
