"""Lorebooks to and from other tools: SillyTavern World Info (also KoboldAI's), the lorebook a
character card carries (`character_book`), and NovelAI's `.lorebook`.

Didact's lore entries were modelled on World Info, so its fields map one to one: keys and
secondary keys with their logic (AND ANY, NOT ALL, NOT ANY, AND ALL), constant, order
(priority), probability, inclusion group, sticky, cooldown, delay and recursion. What doesn't
travel: timing counted in scenes (World Info counts messages), and the other tools' placement
and scan settings, which Didact decides for itself.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import cast

from didact.core.errors import InvalidError
from didact.core.i18n import _
from didact.core.ids import EntityId, Scope
from didact.core.output import JSON
from didact.services import knowledge, lore, records
from didact.store.changeset import Changeset
from didact.store.entity import Entity
from didact.store.repo import Repo

LOGIC = ("and_any", "not_all", "not_any", "and_all")  # World Info's selectiveLogic 0–3


@dataclass(slots=True)
class Exported:
    book: dict[str, JSON]
    entries: int = 0
    secret: int = 0  # left out
    scenes: int = 0  # timing in scenes, left out


@dataclass(slots=True)
class Imported:
    created: list[str] = field(default_factory=list)
    disabled: int = 0
    empty: int = 0  # no content, or neither keys nor constant
    there: int = 0  # already here: the same title and text (a book imported again)


def export(repo: Repo, *, secrets: bool) -> Exported:
    """The lore entries here (campaign, world, system, global) as World Info JSON."""
    rows = [r for r in repo.index().rows(repo.chain()) if r.type == "lore"]
    found = Exported({})
    entries: dict[str, JSON] = {}
    for row in rows:
        entity = repo.located(row).entity
        if not secrets and (
            not knowledge.visible(entity.knowledge, gm=False)
            or entity.fields.get("kind") == "secret"
        ):
            found.secret += 1
            continue
        entry, scenes = _world_info(entity, len(entries))
        found.scenes += scenes
        entries[str(len(entries))] = entry
    found.book = {"entries": entries}
    found.entries = len(entries)
    return found


def _world_info(entity: Entity, uid: int) -> tuple[dict[str, JSON], bool]:
    fields = entity.fields
    timing: dict[str, int] = {}
    scenes = False
    for name in ("sticky", "cooldown", "delay"):
        value = fields.get(name)
        if isinstance(value, int) and not isinstance(value, bool):
            timing[name] = value
        elif value is not None:
            scenes = True  # `2 scenes`: World Info counts messages only
    secondary = _strings(fields.get("secondary"))
    logic = str(fields.get("logic") or "and_any")
    probability = fields.get("probability")
    priority = fields.get("priority")
    entry: dict[str, JSON] = {
        "uid": uid,
        "key": list[JSON](_strings(fields.get("keys"))),
        "keysecondary": list[JSON](secondary),
        "comment": entity.name,
        "content": entity.body.strip(),
        "constant": fields.get("constant") is True,
        "selective": bool(secondary),
        "selectiveLogic": LOGIC.index(logic) if logic in LOGIC else 0,
        "order": priority if isinstance(priority, int) else 50,
        "position": 0,
        "disable": False,
        "probability": probability if isinstance(probability, int) else 100,
        "useProbability": isinstance(probability, int),
        "group": str(fields.get("group") or ""),
        "sticky": timing.get("sticky", 0),
        "cooldown": timing.get("cooldown", 0),
        "delay": timing.get("delay", 0),
        "preventRecursion": fields.get("recursive") is False,
        "excludeRecursion": False,
    }
    return entry, scenes


def entries_of(data: JSON) -> list[dict[str, JSON]]:
    """The entries of a lorebook in any of the shapes read here, each as World Info fields."""
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        data = cast(dict[str, JSON], data["data"])  # a character card (V2, V3)
    if isinstance(data, dict) and isinstance(data.get("character_book"), dict):
        data = cast(dict[str, JSON], data["character_book"])
    raw = data.get("entries") if isinstance(data, dict) else None
    listed = list(raw.values()) if isinstance(raw, dict) else raw
    if not isinstance(listed, list):
        raise InvalidError(
            _("that isn't a lorebook: there's no list of entries"),
            hint=_("export a World Info file from SillyTavern, or a .lorebook from NovelAI"),
        )
    return [_normal(e) for e in listed if isinstance(e, dict)]


def _normal(entry: dict[str, JSON]) -> dict[str, JSON]:
    """An entry as World Info has it, whichever tool wrote it."""
    if "text" in entry and "content" not in entry:  # NovelAI
        return {
            "key": entry.get("keys") or [],
            "comment": entry.get("displayName") or "",
            "content": entry.get("text"),
            "constant": entry.get("forceActivation") is True,
            "disable": entry.get("enabled") is False,
        }
    if "keys" in entry and "key" not in entry:  # a character card's book
        extensions = entry.get("extensions")
        extra = extensions if isinstance(extensions, dict) else {}
        return {
            **{k: v for k, v in extra.items() if k in ("probability", "useProbability", "group")},
            "key": entry.get("keys") or [],
            "keysecondary": entry.get("secondary_keys") or [],
            "comment": entry.get("comment") or entry.get("name") or "",
            "content": entry.get("content"),
            "constant": entry.get("constant") is True,
            "selectiveLogic": extra.get("selectiveLogic", 0),
            "order": entry.get("insertion_order", entry.get("priority")),
            "disable": entry.get("enabled") is False,
        }
    return entry


def import_book(cs: Changeset, scope: Scope, data: JSON) -> Imported:
    """Add a lorebook's entries as lore records in `scope`."""
    repo = cs.repo
    done = Imported()
    taken: set[str] = set()
    for entry in entries_of(data):
        if entry.get("disable") is True:
            done.disabled += 1
            continue
        content = str(entry.get("content") or "").strip()
        keys = [k for k in _strings(entry.get("key")) if k.strip()]
        constant = entry.get("constant") is True
        if not content or not (keys or constant):
            done.empty += 1
            continue
        fields = lore.entry_fields(
            keys,
            secondary=[k for k in _strings(entry.get("keysecondary")) if k.strip()],
            logic=_logic(entry),
            priority=_int(entry.get("order")),
            kind=None,
            constant=constant,
            probability=_int(entry.get("probability")) if entry.get("useProbability") else None,
            group=str(entry.get("group") or "") or None,
            sticky=_turns(entry.get("sticky")),
            cooldown=_turns(entry.get("cooldown")),
            delay=_turns(entry.get("delay")),
            recursive=entry.get("preventRecursion") is not True,
        )
        title = str(entry.get("comment") or "").strip() or lore.title_for(content)
        wanted = records.new_id("lore", title)
        if _same(repo, scope, wanted, content):
            done.there += 1
            continue
        entity_id = _free(repo, scope, wanted, taken)
        entity = records.build_entity(entity_id, title, {"fields": fields}, body=content + "\n")
        records.create(cs, scope, entity)
        done.created.append(str(entity_id))
    return done


def _same(repo: Repo, scope: Scope, entity_id: EntityId, content: str) -> bool:
    """Whether a lore record of that id here already says this."""
    if not repo.exists(scope, entity_id):
        return False
    return repo.load_entity(repo.entity_path(scope, entity_id)).body.strip() == content


def _free(repo: Repo, scope: Scope, wanted: EntityId, taken: set[str]) -> EntityId:
    """`wanted`, or `wanted-2`, `-3`, … when a record here (or this import) has it."""
    candidate, n = wanted, 1
    while str(candidate) in taken or repo.exists(scope, candidate):
        n += 1
        candidate = EntityId(wanted.type, f"{wanted.slug}-{n}")
    taken.add(str(candidate))
    return candidate


def _logic(entry: Mapping[str, JSON]) -> str | None:
    if not _strings(entry.get("keysecondary")):
        return None
    value = entry.get("selectiveLogic")
    return LOGIC[value] if isinstance(value, int) and 0 <= value < len(LOGIC) else "and_any"


def _turns(value: JSON) -> str | None:
    return (
        str(value) if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None
    )


def _int(value: JSON) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _strings(value: JSON) -> list[str]:
    if isinstance(value, str):
        return [k.strip() for k in value.split(",") if k.strip()]
    return [str(v) for v in value] if isinstance(value, list) else []
