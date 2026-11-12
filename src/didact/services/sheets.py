"""Sheets in the library: which schemas apply to a record here, and schema-aware edits.

`set freya hp-=2` finds `hp` in the system's character type, changes `mechanics.my-system.hp`,
clamps it to its range and says what overflowed. Strictness (campaign setting `strictness`):
`strict` (default) refuses values that don't fit, `lenient` warns, `freeform` doesn't check.
"""

import dataclasses
from collections.abc import Callable
from typing import Literal, cast

from didact.core import labels
from didact.core.errors import DidactError, InvalidError, UsageError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.expr.model import Value
from didact.schema import fields as kinds
from didact.schema.sheet import Sheet, check, sheet_for, values
from didact.services import assign
from didact.services.values import record_values
from didact.store.entity import Entity
from didact.store.repo import Repo

type Strictness = Literal["strict", "lenient", "freeform"]
STRICTNESS: tuple[Strictness, ...] = ("strict", "lenient", "freeform")


def active_system(repo: Repo) -> str | None:
    campaign = repo.active_campaign()
    if campaign is not None and campaign.system:
        return campaign.system
    world = repo.active_world()
    return world.system if world is not None else None


def sheet(repo: Repo, type_: str) -> Sheet:
    """The sheet for a type here; empty (no checks) when no pack defines the type."""
    from didact.services import packs

    system = active_system(repo)
    if not repo.initialized():
        return Sheet(type_, system)
    try:
        return sheet_for(packs.active(repo), system, type_)
    except DidactError:
        return Sheet(type_, system)


def strictness(repo: Repo) -> Strictness:
    campaign = repo.active_campaign()
    raw = campaign.other.get("strictness") if campaign is not None else None
    if raw is None:
        world = repo.active_world()
        raw = world.other.get("strictness") if world is not None else None
    for mode in STRICTNESS:
        if raw == mode:
            return mode
    return "strict"


def check_force(force: bool, reason: str | None) -> None:
    if force and not (reason or "").strip():
        raise UsageError(
            _("--force needs --reason"),
            hint=_("say why the rules bend here, e.g. --reason 'the Warden allows it'"),
        )


# ---------------------------------------------------------------------------- edits


def unset(entity: Entity, key: str, sh: Sheet) -> str | None:
    """Remove a field as `set --unset` does (a rule's `unset:` too), found through the sheet
    (`curse_timer` → `mechanics.<system>.curse_timer`). A field the sheet has that the record
    hasn't set changes nothing, and the note says so; a key that is neither is a mistake still.
    Returns the note."""
    explicit = key.split(".")[0] in ("fields", "mechanics", "extra")
    routed = None if explicit else sh.route(key)
    path = ".".join(routed) if routed else key
    try:
        assign.unset(entity, path)
    except InvalidError:
        if routed is None and sh.spec_at(assign.parse_key(path)) is None:  # no such field
            raise
        return _("no key {key} to remove", key=repr(key))
    return None


def apply(entity: Entity, assignment: assign.Assignment, sh: Sheet, mode: Strictness) -> str | None:
    """Apply one assignment, schema-aware. Returns a note (e.g. about clamping) or None."""
    path = assignment.path
    if assignment.bare and not sh.empty:
        routed = sh.route(assignment.key.removeprefix("fields."))
        if routed is not None:
            path = routed
    spec = sh.spec_at(path)
    routed_assignment = dataclasses.replace(assignment, path=path)
    depth = 2 if path[0] == "fields" else 3  # the keys that name the field
    if spec is not None and spec.kind == "slots" and len(path) > depth:  # an item it holds
        from didact.services import inventory

        return inventory.set_key(entity, sh, spec, routed_assignment, mode)
    if spec is None or mode == "freeform":
        assign.apply(entity, routed_assignment)
        return None
    block = _block(entity, path)
    whole = len(path) == depth
    try:
        if whole:
            current = block.get(spec.name)
            if current is None and assignment.op in ("+=", "-="):
                current = spec.opt("default")  # nobody set it: it starts where the sheet says
            new, note = kinds.change(spec, current, assignment.op, assignment.value)
            if new is not current:  # (`current` itself: nothing changed, not even an empty list)
                block[spec.name] = new
            return note
        assign.apply(entity, routed_assignment)  # a sub-key such as `hp.max`: check the whole
        block[spec.name] = kinds.coerce(spec, block.get(spec.name))
        return None
    except kinds.FieldError as exc:
        if mode == "strict":
            raise InvalidError(str(exc), hint=_field_hint(spec)) from exc
        assign.apply(entity, routed_assignment)  # lenient: keep it; `validate` warns once
        return None


def _block(entity: Entity, path: tuple[str, ...]) -> dict[str, JSON]:
    if path[0] == "fields":
        return entity.fields
    block = entity.mechanics.get(path[1])
    if not isinstance(block, dict):
        block = {}
        entity.mechanics[path[1]] = block
    return block


def _field_hint(spec: kinds.FieldSpec) -> str:
    name = spec.name
    match spec.kind:
        case "stat":
            return _("e.g. `{name}=12` or `{name}=10/12`", name=name)
        case "resource":
            return _("e.g. `{name}-=2` or `{name}=4/6`", name=name)
        case "uses":
            return _("e.g. `{name}-=1`", name=name)
        case "slots":
            sword = '{"name":"Sword","size":"normal"}'
            return _("e.g. `{name}+=Rope` or `{name}+={sword}`", name=name, sword=sword)
        case "enum":
            allowed = ", ".join(str(v) for v in cast(list[JSON], spec.opt("values") or []))
            return _("one of: {values}", values=allowed)
        case "conditions":
            return _("e.g. `{name}+=deprived`", name=name)
    return _("see `didact template` for {name}'s format", name=name)


def validate(
    entity: Entity, sh: Sheet, mode: Strictness, *, before: list[str] | None = None
) -> list[str]:
    """Normalize the record's known fields and enforce strictness for problems that are new.

    Returns warnings to show (lenient mode); raises in strict mode.
    """
    if sh.empty or mode == "freeform":
        return []
    result = check(sh, entity.fields, entity.mechanics)
    entity.fields = result.fields
    entity.mechanics = result.mechanics
    fresh = [p for p in result.problems if p not in (before or [])]
    if not fresh:
        return []
    if mode == "strict":
        raise InvalidError(
            f"{entity.id}: " + "; ".join(fresh),
            hint=_("fix the values, or pass --force --reason '…' to allow it this once"),
        )
    return [_("warning: {problem}", problem=p) for p in fresh]


def route_bare(entity: Entity, sh: Sheet, keys: list[str]) -> None:
    """Move top-level `--data` keys that belong to the system's sheet into its mechanics block,
    as `set` routes them, but for those the description gave that block itself (`stated`)."""
    for key in keys:
        if key not in entity.fields or stated(sh, key, entity.mechanics):
            continue
        path = sh.route(key)
        if path is not None and path[0] == "mechanics":
            _block(entity, path)[path[2]] = entity.fields.pop(key)


def stated(sh: Sheet, key: str, mechanics: dict[str, JSON]) -> bool:
    """Whether a description's own block for the system holds the field a top-level key names
    (`role: innkeeper` beside `mechanics: {my-system: {role: tactician}}`): what the block says
    stands, and the top-level key keeps its core meaning, in `fields`."""
    path = sh.route(key)
    if path is None or path[0] != "mechanics":
        return False
    block = mechanics.get(path[1])
    return isinstance(block, dict) and path[2] in block


def problems(entity: Entity, sh: Sheet) -> list[str]:
    if sh.empty:
        return []
    return check(sh, entity.fields, entity.mechanics).problems


def fill(entity: Entity, sh: Sheet, roll: Callable[[str, str], int], *, missing: bool) -> list[str]:
    """Resolve values given as "roll", and with `missing`, roll or default every absent field
    that says how (`roll:` / `default:`). Returns notes about what was filled."""
    notes: list[str] = []
    for schema in sh.schemas:
        found = entity.fields if schema.pack == "core" else entity.mechanics.get(schema.pack)
        block: dict[str, JSON] = found if isinstance(found, dict) else {}
        for spec in schema.fields.values():
            if not spec.stored:
                continue
            current = block.get(spec.name)
            asked = isinstance(current, str) and current.strip().lower().split(" ")[0] == "roll"
            if not asked and (current is not None or not missing):
                continue
            given = str(current).strip()[4:].strip() if asked else ""
            expr = given or spec.opt("roll")  # "roll" uses the field's dice; "roll 2d8" these
            if isinstance(expr, str):
                value = roll(expr, spec.name)
                block[spec.name] = kinds.coerce(spec, value)
                notes.append(
                    _("rolled {field}: {expr} → {value}", field=spec.name, expr=expr, value=value)
                )
            elif asked:
                raise InvalidError(
                    _("{field} has no dice to roll", field=spec.name), hint=_("give it a value")
                )
            elif spec.opt("default") is not None:
                block[spec.name] = kinds.coerce(spec, spec.opt("default"))
        if block and schema.pack != "core":
            entity.mechanics[schema.pack] = block  # only once something is in it
    return notes


def entity_values(entity: Entity, sh: Sheet) -> dict[str, Value]:
    return values(sh, record_values(entity), entity.fields, entity.mechanics)


def sheet_lines(entity: Entity, sh: Sheet) -> list[str]:
    """`my-system: STR 10/12 · DEX 14 · hp 4/6 · armor 1` plus a line per list field."""
    lines: list[str] = []
    known = entity_values(entity, sh) if not sh.empty else {}
    for schema in sh.schemas:
        core = schema.pack == "core"  # Didact's own fields, named in the reader's language
        block = entity.fields if core else entity.mechanics.get(schema.pack)
        stored = block if isinstance(block, dict) else {}
        between = ": " if core else " "  # prose fields: one `label: value` line each
        inline: list[str] = []
        listed: list[str] = []
        for spec in schema.fields.values():
            label = labels.inline(spec.name, labels.field_name(spec.name)) if core else spec.label
            if spec.kind == "derived":
                if spec.name in known:
                    inline.append(f"{label}{between}{_show(known[spec.name])}")
                continue
            if spec.name not in stored:
                continue
            shown = kinds.display(spec, stored[spec.name])
            if spec.kind == "slots":
                used, cap = known.get(f"{spec.name}.used"), known.get(f"{spec.name}.capacity")
                room = " " + (
                    _("({used}/{cap} slots)", used=used, cap=cap)
                    if cap is not None
                    else _("({used} slots)", used=used)
                )
                listed.append(f"{label}{room}: {shown}")
            elif spec.kind in ("list", "conditions", "refs", "map", "text") and len(shown) > 40:
                listed.append(f"{label}: {shown}")
            else:
                inline.append(f"{label}{between}{shown}")
        if core:
            lines.extend(inline)
            lines.extend(listed)
        elif inline or listed:
            head = f"{schema.pack}: "
            if inline:
                lines.append(head + " · ".join(inline))
            lines.extend(("  " if inline else head) + item for item in listed)
    return lines


def stat_items(entity: Entity, sh: Sheet) -> list[dict[str, JSON]]:
    """The system's numbers, one item each in the sheet's order: the key `set` takes, the
    label, the text shown (`4/6`), the field's kind and, when the sheet has it, its help.
    Long lists and slots are left out, as in the stat line."""
    schema = sh.mechanics
    if schema is None:
        return []
    known = entity_values(entity, sh)
    block = entity.mechanics.get(schema.pack)
    stored = block if isinstance(block, dict) else {}
    items: list[dict[str, JSON]] = []
    for spec in schema.fields.values():
        about = spec.opt("help")
        said: dict[str, JSON] = {"help": about} if isinstance(about, str) and about else {}
        if spec.kind == "derived":
            if spec.name in known:
                text = _show(known[spec.name])
                derived: dict[str, JSON] = {"key": spec.name, "label": spec.label, "text": text}
                items.append(derived | {"kind": "derived"} | said)
            continue
        if spec.name not in stored or spec.kind == "slots":
            continue
        shown = kinds.display(spec, stored[spec.name])
        if spec.kind in ("list", "conditions", "refs", "map", "text") and len(shown) > 40:
            continue
        stat: dict[str, JSON] = {"key": spec.name, "label": spec.label, "text": shown}
        items.append(stat | {"kind": spec.kind} | said)
    return items


def stat_line(entity: Entity, sh: Sheet) -> str:
    """The system's numbers in one line: `STR 10/12 · DEX 14 · hp 4/6 · armor 1`."""
    for line in sheet_lines(entity, sh):
        if sh.mechanics is not None and line.startswith(f"{sh.mechanics.pack}: "):
            return line.split(": ", 1)[1]
    return ""


def _show(value: Value) -> str:
    from didact.expr.engine import show

    return value if isinstance(value, str) else show(value)
