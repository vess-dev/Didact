"""A record's sheet: the core type (system-agnostic `fields`) plus the system's type
(`mechanics.<system>`). Checking values, routing `set` keys, and computing derived values."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import cast

from didact.core.errors import DidactError, InvalidError, UnknownName
from didact.core.i18n import _
from didact.core.output import JSON
from didact.expr import DieSpec, Face, RollContext, default_registry, parse
from didact.expr.engine import evaluate
from didact.expr.model import Value, to_json
from didact.packs.library import PackSet
from didact.schema.fields import FieldError, FieldSpec, item_size
from didact.schema.model import TypeSchema, fields_from

MAX_DERIVED_PASSES = 8
LISTS = frozenset({"conditions", "list", "refs", "tags"})  # unset, these read as empty lists


def load_type(
    packs: PackSet, pack_id: str, type_: str, _seen: tuple[str, ...] = ()
) -> TypeSchema | None:
    """The effective type `pack.type`, with the fields of any type it `extends`."""
    ref = f"{pack_id}.{type_}"
    if ref in _seen:
        raise InvalidError(
            _("type {ref} extends itself", ref=ref), hint=_("break the `extends` cycle")
        )
    try:
        item = packs.find("type", ref)
    except DidactError:
        return None
    data = item.data
    fields: dict[str, FieldSpec] = {}
    sources: list[str] = []
    inherited = ""
    suggested: tuple[str, ...] = ()
    parent_ref = data.get("extends")
    if isinstance(parent_ref, str) and parent_ref:
        parent_pack, dot, parent_type = parent_ref.replace("/", ".").rpartition(".")
        parent = load_type(packs, parent_pack if dot else pack_id, parent_type, (*_seen, ref))
        if parent is None:
            raise InvalidError(
                _("type {ref} extends {parent}, which isn't there", ref=ref, parent=parent_ref),
                where=item.source,
                hint=_("enable the pack that defines it, or fix the `extends`"),
            )
        fields |= parent.fields
        sources += parent.sources
        inherited = parent.guidance
        suggested = parent.details
    fields |= fields_from(data)
    own = data.get("details")
    if isinstance(own, list):
        suggested = tuple(dict.fromkeys([*suggested, *(str(d) for d in own)]))
    return TypeSchema(
        type=type_,
        pack=pack_id,
        fields=fields,
        label=str(data.get("label") or type_),
        description=str(data.get("description") or ""),
        guidance=str(data.get("guidance") or inherited),
        open=bool(data.get("open", pack_id == "core")),
        sources=(*sources, item.source),
        details=suggested,
    )


@dataclass(frozen=True, slots=True)
class Sheet:
    """The schemas that apply to one entity type in one system."""

    type: str
    system: str | None
    core: TypeSchema | None = None
    mechanics: TypeSchema | None = None

    @property
    def schemas(self) -> list[TypeSchema]:
        return [s for s in (self.core, self.mechanics) if s is not None]

    @property
    def empty(self) -> bool:
        return not self.schemas

    def route(self, key: str) -> tuple[str, ...] | None:
        """Where a bare key lives: `hp` → ("mechanics", "my-system", "hp")."""
        head, _sep, rest = key.partition(".")
        tail = tuple(rest.split(".")) if rest else ()
        for schema in (self.mechanics, self.core):
            if schema is None:
                continue
            spec = schema.field(head)
            if spec is not None:
                if schema.pack == "core":
                    return ("fields", spec.name, *tail)
                return ("mechanics", schema.pack, spec.name, *tail)
        return None

    def spec_at(self, path: tuple[str, ...]) -> FieldSpec | None:
        """The field a full path points at (`mechanics.my-system.hp` → hp's spec)."""
        if path[:1] == ("fields",) and self.core is not None and len(path) >= 2:
            return self.core.field(path[1])
        mechanics = self.mechanics
        if path[:1] == ("mechanics",) and mechanics is not None and path[1:2] == (mechanics.pack,):
            return mechanics.field(path[2]) if len(path) >= 3 else None
        return None


def sheet_for(packs: PackSet, system: str | None, type_: str) -> Sheet:
    core = load_type(packs, "core", type_) if "core" in packs.ids else None
    mechanics = load_type(packs, system, type_) if system and system in packs.ids else None
    return Sheet(type_, system, core, mechanics)


# ---------------------------------------------------------------------------- checking


@dataclass(slots=True)
class Check:
    """What checking a record found: normalized blocks plus problems (field: message)."""

    fields: dict[str, JSON]
    mechanics: dict[str, JSON]
    problems: list[str] = field(default_factory=list)


def check(sheet: Sheet, fields: dict[str, JSON], mechanics: dict[str, JSON]) -> Check:
    """Normalize known fields (`12` → `{value: 12, max: 12}`) and list what doesn't fit."""
    result = Check(dict(fields), dict(mechanics))
    if sheet.core is not None:
        result.fields = _check_block(sheet.core, fields, result.problems, "")
    if sheet.mechanics is not None:
        pack = sheet.mechanics.pack
        block = mechanics.get(pack)
        checked = _check_block(
            sheet.mechanics, block if isinstance(block, dict) else {}, result.problems, f"{pack}."
        )
        if checked or pack in mechanics:
            result.mechanics[pack] = cast(JSON, checked)
    return result


def _check_block(
    schema: TypeSchema, block: dict[str, JSON], problems: list[str], prefix: str
) -> dict[str, JSON]:
    out: dict[str, JSON] = {}
    for key, raw in block.items():
        spec = schema.field(key)
        if spec is None:
            out[key] = raw
            if not schema.open:
                known = ", ".join(schema.fields)
                problems.append(
                    _(
                        "{field}: not a {type} field (fields: {known})",
                        field=f"{prefix}{key}",
                        type=schema.label,
                        known=known,
                    )
                )
            continue
        if not spec.stored:
            problems.append(
                _("{field}: computed from other fields; don't store it", field=f"{prefix}{key}")
            )
            continue
        try:
            out[spec.name] = coerce_field(spec, raw)
        except FieldError as exc:
            out[spec.name] = raw
            problems.append(f"{prefix}{exc}")
    for spec in schema.fields.values():
        if spec.opt("required") and spec.stored and spec.name not in out:
            problems.append(_("{field}: required", field=f"{prefix}{spec.name}"))
    return out


def coerce_field(spec: FieldSpec, raw: JSON) -> JSON:
    from didact.schema.fields import coerce

    return coerce(spec, raw)


# ---------------------------------------------------------------------------- values


class NoDice:
    """Derived fields are pure: they may not roll."""

    def draw(self, die: DieSpec) -> Face:
        raise InvalidError(
            _("derived fields can't roll dice"), hint=_("use a `roll:` spec instead")
        )


def values(
    sheet: Sheet, base: dict[str, Value], fields: dict[str, JSON], mechanics: dict[str, JSON]
) -> dict[str, Value]:
    """Everything expressions can read about a record: stored values, slot totals, derived."""
    found = dict(base)
    for schema in sheet.schemas:
        block = fields if schema.pack == "core" else mechanics.get(schema.pack)
        stored = block if isinstance(block, dict) else {}
        for spec in schema.fields.values():
            if spec.name not in stored and spec.stored and spec.opt("default") is not None:
                found.update(_default_values(spec))  # readable before anyone sets it
            elif spec.name not in stored and spec.kind in LISTS:
                found.setdefault(spec.name, [])  # `'deprived' in @who.conditions` with none yet
            if spec.kind == "slots":
                occupying = sum(
                    value
                    for other in schema.fields.values()
                    if other.kind == "counter" and other.opt("occupies") == spec.name
                    and isinstance(value := stored.get(other.name, 0), int)
                )  # fmt: skip
                found.update(_slot_values(spec, stored.get(spec.name), occupying, found))
    derived = [s for schema in sheet.schemas for s in schema.fields.values() if s.kind == "derived"]
    lists = {
        s.name for schema in sheet.schemas for s in schema.fields.values() if s.kind == "slots"
    }
    pending = list(derived)
    for _pass in range(MAX_DERIVED_PASSES):
        if not pending:
            break
        waiting: list[FieldSpec] = []
        for spec in pending:
            try:
                found[spec.name] = _evaluate(str(spec.opt("expr")), found, lists)
            except InvalidError as exc:
                if isinstance(exc, UnknownName) and exc.what == "variable":
                    waiting.append(spec)  # may depend on another derived field
                else:
                    found[spec.name] = _("error: {problem}", problem=exc.message)
        if len(waiting) == len(pending):
            for spec in waiting:
                found[spec.name] = _("error: depends on a missing value")
            break
        pending = waiting
    return found


def _default_values(spec: FieldSpec) -> dict[str, Value]:
    """A field's default as expression values: `steps` → 0; a resource → `hp` and `hp.max`."""
    from didact.schema.fields import coerce

    try:
        stored = coerce(spec, spec.opt("default"))
    except FieldError:
        return {}
    if isinstance(stored, dict):
        return {
            (spec.name if key == "value" else f"{spec.name}.{key}"): cast(Value, value)
            for key, value in stored.items()
            if isinstance(value, int | float | str | bool)
        }
    if isinstance(stored, int | float | str | bool):
        return {spec.name: stored}
    return {}


def _evaluate(text: str, known: dict[str, Value], lists: set[str]) -> Value:
    """Evaluate a derived field. A column no item has (`@inventory.armor`) is an empty list."""

    def empty_column(path: str) -> Value | None:
        return [] if path.partition(".")[0] in lists else None

    ctx = RollContext(default_registry(), NoDice(), known, empty_column)
    return evaluate(parse(text, ctx.registry), ctx).value


def summary(sheet: Sheet, found: dict[str, Value]) -> dict[str, Value]:
    """The sheet's own values by field name (plus slot totals, a group's too): what
    `show --format json` gives."""
    specs = [s for schema in sheet.schemas for s in schema.fields.values()]
    names = {s.name for s in specs}
    parts = ("used", "free", "capacity")
    totals = {f"{n}.{part}" for n in names for part in parts}
    for spec in specs:
        groups = spec.opt("groups") if spec.kind == "slots" else None
        for group in groups if isinstance(groups, dict) else {}:
            totals |= {f"{spec.name}.{group}.{part}" for part in parts}
    return {k: v for k, v in found.items() if k in names or k in totals}


def _slot_values(
    spec: FieldSpec, raw: JSON, occupying: int, known: dict[str, Value]
) -> dict[str, Value]:
    """`inventory.used`, `.free`, `.capacity`, and a column per item key (`inventory.armor`).
    With groups, each group's too: `inventory.body.armor` (only what's worn or held),
    `inventory.body.used`, `inventory.body.free`."""
    items = raw if isinstance(raw, list) else []
    used = sum(item_size(spec, i) for i in items) + occupying
    capacity = _capacity(spec, known)
    found: dict[str, Value] = {f"{spec.name}.used": used}
    if capacity is not None:
        found[f"{spec.name}.capacity"] = capacity
        found[f"{spec.name}.free"] = capacity - used
    found |= _columns(spec.name, items, skip={"name"})
    groups = spec.opt("groups")
    for group, room in groups.items() if isinstance(groups, dict) else []:
        held = [i for i in items if isinstance(i, dict) and i.get("group") == group]
        taken = sum(item_size(spec, i) for i in held)
        found[f"{spec.name}.{group}.used"] = taken
        if isinstance(room, int):
            found[f"{spec.name}.{group}.free"] = room - taken
        found |= _columns(f"{spec.name}.{group}", held, skip={"name", "group"})
    found[spec.name] = [str(i.get("name")) if isinstance(i, dict) else str(i) for i in items]
    return found


def _columns(prefix: str, items: Sequence[JSON], *, skip: set[str]) -> dict[str, Value]:
    """A column per item key: `inventory.armor` is every item's armor, in order."""
    found: dict[str, Value] = {}
    keys = {k for i in items if isinstance(i, dict) for k in i}
    for key in keys - skip:
        column = [i.get(key) for i in items if isinstance(i, dict) and i.get(key) is not None]
        converted = [c for c in column if isinstance(c, int | float | str | bool)]
        found[f"{prefix}.{key}"] = cast(Value, converted)
    return found


def _capacity(spec: FieldSpec, known: dict[str, Value]) -> int | None:
    raw = spec.opt("capacity")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        found = known.get(raw)
        return found if isinstance(found, int) else None
    return None


def fill_value(spec: FieldSpec, roll: Callable[[str], int]) -> JSON | None:
    """A starting value for a missing field: rolled (`roll:`) or its `default`."""
    text = spec.opt("roll")
    if isinstance(text, str):
        return roll(text)
    default = spec.opt("default")
    return default if default is not None else None


def json_values(found: dict[str, Value]) -> dict[str, JSON]:
    return {k: to_json(v) for k, v in found.items()}
