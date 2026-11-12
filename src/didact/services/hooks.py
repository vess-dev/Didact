"""Field hooks: what a sheet says happens when a value crosses a line.

    STR: {kind: stat, range: [0, 18], on_zero: {trigger: death}}
    hp: {kind: resource, on_zero: "At exactly 0 HP, roll on the Scars table."}
    inventory: {kind: slots, capacity: 10, when_full: {set: {hp: 0}}}
    corruption: {kind: counter, thresholds: {10: "Gain a mutation.", 20: {trigger: taken}}}
    doom: {kind: clock, size: 6, on_full: {trigger: doom-falls}}

A hook fires when a change crosses its line: hp 3 → 0 fires `on_zero`, 0 → 0 doesn't. `on_full`
(`when_full` for slots) fires when a value reaches its max, size or capacity. An action is a note
for the LLM (text), `set: {field: value}` or `condition: name` on the same record, `trigger: rule`
(run with `who` = the record), or a list of these. Hooks are consequences, not checks, so they
fire in every strictness mode; `--force` edits skip them.
"""

from dataclasses import dataclass, field
from typing import cast

from didact.core.i18n import _
from didact.core.output import JSON
from didact.expr.model import Value
from didact.schema import fields as kinds
from didact.schema.model import TypeSchema
from didact.schema.sheet import Sheet
from didact.services import assign, sheets
from didact.store.entity import Entity

MAX_PASSES = 4  # a hook's `set` may cross another line (full pack → hp 0 → on_zero)
FULL_HOOKS = ("on_full", "when_full")


@dataclass(frozen=True, slots=True)
class Fired:
    field: str
    why: str  # "hp reached 0", "inventory is full (10/10)", "corruption reached 10"
    action: JSON


@dataclass(slots=True)
class Outcome:
    notes: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)  # rule refs, run with who=<record>

    def extend(self, other: Outcome) -> None:
        self.notes.extend(other.notes)
        self.triggers.extend(other.triggers)


def hooked(sh: Sheet) -> bool:
    return any(_hooks(spec) for schema in sh.schemas for spec in schema.fields.values())


def _hooks(spec: kinds.FieldSpec) -> dict[str, JSON]:
    return {
        k: v
        for k, v in spec.options.items()
        if k in ("on_zero", *FULL_HOOKS) or (k == "thresholds" and spec.kind == "counter")
    }


def _number(raw: Value | None) -> float | None:
    return float(raw) if isinstance(raw, int | float) and not isinstance(raw, bool) else None


def _read(found: dict[str, Value], schema: TypeSchema, name: str) -> float | None:
    """A field's number: `hp` (its value), `hp.max`, `doom.size`, … in this schema's block."""
    if schema.pack != "core":
        long = _number(found.get(f"mechanics.{schema.pack}.{name}"))
        if long is not None:
            return long
    return _number(found.get(name))


def _levels(
    schema: TypeSchema, spec: kinds.FieldSpec, found: dict[str, Value]
) -> tuple[float | None, float | None]:
    """(current, full) for a field: value and max/size/capacity."""
    if spec.kind == "slots":
        return _number(found.get(f"{spec.name}.used")), _number(found.get(f"{spec.name}.capacity"))
    current = _read(found, schema, spec.name)
    top = "size" if spec.kind in kinds.SIZED else "max"
    full = _read(found, schema, f"{spec.name}.{top}")
    if full is None and spec.kind in ("counter", "int", "number"):
        full = _number(cast(Value, spec.opt("max")))
    return current, full


def _show(number: float) -> str:
    return str(int(number)) if number.is_integer() else str(number)


def crossed(sh: Sheet, before: dict[str, Value], after: dict[str, Value]) -> list[Fired]:
    """The hooks a change fires: lines crossed going from `before` to `after`."""
    fired: list[Fired] = []
    for schema in sh.schemas:
        for spec in schema.fields.values():
            hooks = _hooks(spec)
            if not hooks:
                continue
            was, was_full = _levels(schema, spec, before)
            now, full = _levels(schema, spec, after)
            if now is None:
                continue
            if "on_zero" in hooks and now <= 0 and (was is None or was > 0):
                fired.append(
                    Fired(
                        spec.name,
                        _("{field} reached {value}", field=spec.label, value=_show(now)),
                        hooks["on_zero"],
                    )
                )
            for key in FULL_HOOKS:
                if key not in hooks or full is None or now < full:
                    continue
                if was is not None and was_full is not None and was >= was_full:
                    continue
                shown = {"field": spec.label, "now": _show(now), "full": _show(full)}
                why = (
                    _("{field} is full ({now}/{full})", **shown)
                    if spec.kind in ("slots", "track", "clock")
                    else _("{field} is at its max ({now}/{full})", **shown)
                )
                fired.append(Fired(spec.name, why, hooks[key]))
            marks = hooks.get("thresholds")
            if isinstance(marks, dict):
                for mark, action in marks.items():
                    line = _number(_parse_mark(mark))
                    if line is not None and now >= line and (was is None or was < line):
                        why = _("{field} reached {value}", field=spec.label, value=_show(line))
                        fired.append(Fired(spec.name, why, action))
    return fired


def _parse_mark(raw: object) -> Value | None:
    if isinstance(raw, int | float) and not isinstance(raw, bool):
        return raw
    try:
        return float(str(raw))
    except ValueError:
        return None


def settle(entity: Entity, sh: Sheet, before: dict[str, Value], mode: sheets.Strictness) -> Outcome:
    """Fire the hooks a change crossed, applying `set` and `condition` actions to `entity`.

    `before` is `sheets.entity_values` from before the change. Triggers are returned, not run:
    the caller runs them (`services.rules.run_hooks`) so their rolls and changes are logged.
    """
    out = Outcome()
    if sh.empty or not hooked(sh):
        return out
    previous = before
    for _unused in range(MAX_PASSES):
        current = sheets.entity_values(entity, sh)
        fired = crossed(sh, previous, current)
        if not fired:
            break
        for hook in fired:
            _act(entity, sh, hook, hook.action, mode, out)
        previous = current
    return out


def skipped(entity: Entity, sh: Sheet, before: dict[str, Value]) -> list[str]:
    """What hooks a `--force` edit would have fired (it skips them): for the notes."""
    if sh.empty or not hooked(sh):
        return []
    fired = crossed(sh, before, sheets.entity_values(entity, sh))
    return [_("--force: skipped the hook for {why}", why=hook.why) for hook in fired]


def _act(
    entity: Entity, sh: Sheet, hook: Fired, action: JSON, mode: sheets.Strictness, out: Outcome
) -> None:
    if isinstance(action, list):
        for item in action:
            _act(entity, sh, hook, item, mode, out)
        return
    if isinstance(action, str):
        out.notes.append(f"{hook.why}: {action}")
        return
    if not isinstance(action, dict):
        return
    changes = action.get("set")
    if isinstance(changes, dict):
        for key, value in changes.items():
            assignment = assign.Assignment(assign.parse_key(key), "=", value, True)
            note = sheets.apply(entity, assignment, sh, mode)
            out.notes.append(f"{hook.why}: {key} = {value}" + (f" ({note})" if note else ""))
    condition = action.get("condition")
    if isinstance(condition, str):
        if _add_condition(entity, sh, condition, mode):
            out.notes.append(_("{why}: now {condition}", why=hook.why, condition=condition))
        else:
            out.notes.append(_("{why}: already {condition}", why=hook.why, condition=condition))
    for key in ("message", "note"):
        text = action.get(key)
        if isinstance(text, str):
            out.notes.append(f"{hook.why}: {text}")
    rule = action.get("trigger", action.get("do"))
    if isinstance(rule, str):
        out.notes.append(_("{why}: runs {rule}", why=hook.why, rule=rule))
        out.triggers.append(rule)


def _add_condition(entity: Entity, sh: Sheet, name: str, mode: sheets.Strictness) -> bool:
    """Give the record a condition; False when it already had it."""
    spec = next(
        (s for schema in sh.schemas for s in schema.fields.values() if s.kind == "conditions"),
        None,
    )
    key = spec.name if spec is not None else "conditions"
    current = sheets.entity_values(entity, sh).get(key)
    if isinstance(current, list) and name in current:
        return False
    sheets.apply(entity, assign.Assignment(assign.parse_key(key), "+=", name, True), sh, mode)
    return True
