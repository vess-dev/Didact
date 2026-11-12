"""Records as expression values: what `@hp`, `@who.STR` or `@tom.conditions` read."""

from collections.abc import Callable

from didact.core.errors import DidactError
from didact.core.output import JSON, flatten
from didact.expr.model import Value, from_json
from didact.store.entity import Entity
from didact.store.repo import Repo

to_value = from_json


def record_values(entity: Entity) -> dict[str, Value]:
    """A record's values: `hp`, `stats.str`, `tags`, and mechanics both long and short.

    `mechanics.my-system.STR` is also plain `STR`; a system-agnostic field of the same name wins.
    """
    found: dict[str, Value] = {}

    def add(key: str, raw: JSON) -> None:
        converted = to_value(raw)
        if converted is not None:
            found.setdefault(key, converted)

    for key, raw in flatten(entity.fields):
        add(key, raw)
        if key.endswith(".value"):
            add(key.removesuffix(".value"), raw)  # `hp` reads `hp.value` (stats, resources)
    for key, raw in flatten(entity.mechanics, "mechanics."):
        add(key, raw)
        pieces = key.split(".", 2)
        if len(pieces) == 3:
            add(pieces[2], raw)
        for name in (key, pieces[-1] if len(pieces) == 3 else key):
            if name.endswith(".value"):
                add(name.removesuffix(".value"), raw)
    core: dict[str, JSON] = {
        "id": str(entity.id),
        "type": entity.type,
        "name": entity.name,
        "tags": list[JSON](entity.tags),
        "status": entity.status,
    }
    for key, raw in core.items():
        add(key, raw)
    return found


def lookup(found: dict[str, Value], key: str) -> Value | None:
    """A key, matched exactly or ignoring case (`@str` finds `STR`)."""
    if key in found:
        return found[key]
    return {k.casefold(): v for k, v in found.items()}.get(key.casefold())


def record_resolver(repo: Repo) -> Callable[[str], Value | None]:
    """`@tom.hp` or `@{npc:tom.hp}`: a field of any record in scope."""

    def resolve(path: str) -> Value | None:
        ref, dot, key = path.partition(".")
        if not dot:
            return None
        try:
            located = repo.resolve(ref)
        except DidactError:
            return None
        return lookup(record_values(located.entity), key)

    return resolve
