"""Assignments like `hp=5`, `hp-=2`, `tags+=wood`, `fields.mood="wary"`, applied to entities.

- `=` sets; `+=` adds to a number, appends to a list, or extends text; `-=` subtracts or removes.
- Values are JSON when they parse as JSON (5, true, null, [1,2], "text"), otherwise plain text.
- Keys: core keys (name, aliases, tags, status, knowledge, archived), `body`, dotted paths into
  `fields.` / `mechanics.` / `extra.`, and any other key as shorthand for `fields.<key>`. Past
  the first dot a key holds what an item's name holds (`inventory.Leather jacket.armor=2`).
"""

import json
import re
from dataclasses import dataclass
from typing import Literal, cast

from didact.core.errors import InvalidError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.store.entity import KNOWLEDGE, SETTABLE_CORE, Entity

type Op = Literal["=", "+=", "-="]

# The key's first part is a plain name (`hp`, `fields`, `inventory`: so `long text = x` is no
# assignment); after a dot it may hold what an item's name holds, spaces and all
# (`inventory.Leather jacket.armor`), up to the first `=`, `+=` or `-=`. It is matched lazily,
# so `hp-=2` reads as key `hp`, op `-=` (keys may still contain dashes).
_ASSIGNMENT = re.compile(
    r"^(?P<key>[A-Za-z0-9_][A-Za-z0-9_\-]*?(?:\.[^=\n]*?)?)\s*(?P<op>\+=|-=|=)(?P<value>.*)$",
    re.S,
)
_CONTAINERS = ("fields", "mechanics", "extra")
_MANAGED = {"id", "type", "created", "updated", "links"}


@dataclass(frozen=True, slots=True)
class Assignment:
    path: tuple[
        str, ...
    ]  # ("name",), ("body",), ("fields", "hp"), ("mechanics", "my-system", "hp")
    op: Op
    value: JSON
    bare: bool = False  # written without a container (`hp`), so a sheet may route it

    @property
    def key(self) -> str:
        return ".".join(self.path)


def parse_value(raw: str) -> JSON:
    text = raw.strip()
    if not text:
        return ""
    try:
        return cast(JSON, json.loads(text))
    except ValueError:
        return raw.strip()


def invalid_key(key: str) -> InvalidError:
    return InvalidError(
        _("invalid key {key}", key=repr(key)),
        hint=_("use keys like `hp`, `fields.hp` or `mechanics.my-system.hp`"),
    )


def parse_key(key: str) -> tuple[str, ...]:
    """A dotted key as its parts. An empty part inside is let through, because a carried item's
    name may hold a dot of its own (`inventory..45 pistol.damage`): `apply_nested` refuses one
    anywhere else."""
    parts = tuple(key.split("."))
    if not parts[0] or not parts[-1]:
        raise invalid_key(key)
    head = parts[0]
    if head in _MANAGED:
        hint = {
            "id": _("change ids with `didact rename <ref> <name> --reslug`"),
            "type": _("change a record's type with `didact rename … --reslug` and a new id"),
            "links": _("use `didact link <ref> <rel> <target>`"),
        }.get(head) or _("Didact maintains it")
        raise InvalidError(_("`{key}` can't be set directly", key=head), hint=hint)
    if head in SETTABLE_CORE or head == "body":
        if len(parts) > 1:
            raise InvalidError(
                _("`{key}` has no sub-keys", key=head), hint=_("use `{key}=…`", key=head)
            )
        return parts
    if head in _CONTAINERS:
        if len(parts) == 1:
            raise InvalidError(
                _("`{key}` needs a sub-key", key=head), hint=_("e.g. `{key}.hp=6`", key=head)
            )
        return parts
    return ("fields", *parts)


def parse_assignment(text: str) -> Assignment:
    match = _ASSIGNMENT.match(text)
    if match is None:
        raise InvalidError(
            _("can't read assignment {text}", text=repr(text)),
            hint=_("use `key=value`, `key+=value` or `key-=value`, e.g. `hp-=2`"),
        )
    op = cast(Op, match["op"])
    head = match["key"].split(".")[0]
    bare = head not in SETTABLE_CORE and head != "body" and head not in _CONTAINERS
    return Assignment(parse_key(match["key"]), op, parse_value(match["value"]), bare)


def apply(entity: Entity, assignment: Assignment) -> None:
    """Apply one assignment to an entity in place (with validation)."""
    head = assignment.path[0]
    if head in _CONTAINERS:
        container = cast(dict[str, JSON], getattr(entity, head))
        apply_nested(container, assignment.path[1:], assignment)
        return
    current: JSON
    match head:
        case "name":
            current = entity.name
        case "aliases":
            current = cast(JSON, list(entity.aliases))
        case "tags":
            current = cast(JSON, list(entity.tags))
        case "status":
            current = entity.status
        case "knowledge":
            current = entity.knowledge
        case "archived":
            current = entity.archived
        case "body":
            current = entity.body
        case _:
            raise InvalidError(
                _("unknown key {key}", key=repr(head)),
                hint=_("e.g. name=…, tags+=…, or a field such as hp=4"),
            )
    value = _combine(current, assignment)
    match head:
        case "name":
            text = _as_text(value, "name")
            if not text.strip():
                raise InvalidError(_("`name` can't be empty"), hint=_("e.g. name='Tom Miller'"))
            entity.name = text.strip()
        case "aliases":
            entity.aliases = _dedupe(_as_text_list(value, "aliases"))
        case "tags":
            entity.tags = _dedupe(_as_text_list(value, "tags"))
        case "status":
            entity.status = _as_text(value, "status") or "active"
        case "knowledge":
            if value not in KNOWLEDGE:
                raise InvalidError(
                    _("invalid knowledge {value}", value=repr(value)),
                    hint=_("use known, secret or rumor"),
                )
            entity.knowledge = value
        case "archived":
            if not isinstance(value, bool):
                raise InvalidError(
                    _("`archived` must be true or false"),
                    hint=_("or use `didact archive` and `didact restore`"),
                )
            entity.archived = value
        case "body":
            entity.body = _as_text(value, "body")


def unset(entity: Entity, key: str) -> None:
    """Remove a key (containers) or reset a core key to its default."""
    path = parse_key(key)
    head = path[0]
    match head:
        case "name":
            raise InvalidError(_("`name` can't be removed"), hint=_("rename it instead"))
        case "aliases":
            entity.aliases = []
        case "tags":
            entity.tags = []
        case "status":
            entity.status = "active"
        case "knowledge":
            entity.knowledge = "known"
        case "archived":
            entity.archived = False
        case "body":
            entity.body = ""
        case _:
            container = cast(dict[str, JSON], getattr(entity, head))
            _delete_nested(container, path[1:], key)


def apply_nested(container: dict[str, JSON], path: tuple[str, ...], assignment: Assignment) -> None:
    """Apply an assignment to the key at `path` in a mapping (a container, an item carried),
    making the mappings on the way."""
    if any(not part for part in path):
        raise invalid_key(assignment.key)
    node = container
    for part in path[:-1]:
        child = node.get(part)
        if child is None:
            child = {}
            node[part] = child
        if not isinstance(child, dict):
            raise InvalidError(
                _("`{key}`: `{part}` is not a mapping", key=assignment.key, part=part),
                hint=_("set `{part}` as a whole instead", part=part),
            )
        node = child
    last = path[-1]
    node[last] = _combine(node.get(last), assignment)


def _delete_nested(container: dict[str, JSON], path: tuple[str, ...], key: str) -> None:
    node = container
    for part in path[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            raise InvalidError(
                _("no key {key} to remove", key=repr(key)),
                hint=_("`didact show <record> --gm` lists its keys"),
            )
        node = child
    if path[-1] not in node:
        raise InvalidError(
            _("no key {key} to remove", key=repr(key)),
            hint=_("`didact show <record> --gm` lists its keys"),
        )
    del node[path[-1]]


def _combine(current: JSON, assignment: Assignment) -> JSON:
    value = assignment.value
    if assignment.op == "=":
        return value
    sign = 1 if assignment.op == "+=" else -1
    if current is None:
        current = (
            []
            if isinstance(value, list) or assignment.path[0] in ("aliases", "tags")
            else 0
            if _is_number(value)
            else ""
        )
    if _is_number(current) and _is_number(value):
        result = cast(float, current) + sign * cast(float, value)
        return int(result) if isinstance(current, int) and isinstance(value, int) else result
    if isinstance(current, list):
        items = value if isinstance(value, list) else [value]
        if sign > 0:
            return [*current, *(i for i in items if i not in current)]
        return [c for c in current if c not in items]
    if isinstance(current, str) and isinstance(value, str) and sign > 0:
        return current + value
    raise InvalidError(
        _(
            "can't apply `{op}` to `{key}` ({current} with {value})",
            op=assignment.op,
            key=assignment.key,
            current=_kind(current),
            value=_kind(value),
        ),
        hint=_("use `=` to replace the value"),
    )


def _is_number(value: JSON) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _kind(value: JSON) -> str:
    return type(value).__name__ if value is not None else _("nothing")


def _as_text(value: JSON, key: str) -> str:
    if isinstance(value, str):
        return value
    if _is_number(value):
        return str(value)
    raise InvalidError(
        _("`{key}` must be text", key=key), hint=_("e.g. {key}='some words'", key=key)
    )


def _as_text_list(value: JSON, key: str) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(v, str | int | float) for v in value):
        return [str(v) for v in value]
    raise InvalidError(
        _("`{key}` must be a list of text", key=key),
        hint=_('e.g. `{key}+=wood` or `{key}=["a","b"]`', key=key),
    )


def _dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        cleaned = item.strip()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return seen
