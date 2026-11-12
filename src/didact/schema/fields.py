"""Field kinds: what a sheet field holds, how input is read, checked, changed and shown.

| kind       | stored as                  | options                                              |
|------------|----------------------------|------------------------------------------------------|
| int        | 7                          | min, max                                             |
| number     | 2.5                        | min, max                                             |
| text       | "…"                        |                                                      |
| enum       | "kind"                     | values (required)                                    |
| flag       | true                       |                                                      |
| tags       | [a, b]                     | allowed                                              |
| stat       | {value: 10, max: 12}       | range [lo, hi]                                       |
| resource   | {value: 4, max: 6}         | min (floor, 0), max (fixed) or max_field, reset      |
| uses       | {value: 2, max: 3}         | max, die (usage die), recharge                       |
| pool       | {value: 4, max: 4}         | die (sides, 6), max                                  |
| counter    | 3                          | min, max, thresholds {n: note}, occupies (slots)     |
| track      | {value: 2, size: 10}       | size                                                 |
| clock      | {value: 1, size: 6}        | size                                                 |
| slots      | [{name, size, …}, …]       | capacity, groups, sizes, default_size, when_full     |
| dice       | "d8"                       |                                                      |
| conditions | [deprived, {name, rounds}] | allowed                                              |
| ref / refs | "npc:tom" / [..]           | to (entity type)                                     |
| list       | [..]                       |                                                      |
| map        | {..}                       |                                                      |
| derived    | (computed, never stored)   | expr (required)                                      |

Every field also takes: label, help, required, default, roll (a dice expression rolled when
the value is given as "roll"), and free-form rule hooks (on_zero, …) that rules read.
"""

import re
from dataclasses import dataclass, field
from typing import Literal, cast

from didact.core.i18n import _
from didact.core.output import JSON

type FieldKind = Literal[
    "int", "number", "text", "enum", "flag", "tags", "stat", "resource", "uses", "pool",
    "counter", "track", "clock", "slots", "dice", "conditions", "ref", "refs", "list", "map",
    "derived",
]  # fmt: skip

KIND_OPTIONS: dict[str, frozenset[str]] = {
    "int": frozenset({"min", "max"}),
    "number": frozenset({"min", "max"}),
    "text": frozenset(),
    "enum": frozenset({"values"}),
    "flag": frozenset(),
    "tags": frozenset({"allowed"}),
    "stat": frozenset({"range"}),
    "resource": frozenset({"min", "max", "max_field", "reset"}),
    "uses": frozenset({"max", "die", "recharge"}),
    "pool": frozenset({"die", "max"}),
    "counter": frozenset({"min", "max", "thresholds", "occupies"}),
    "track": frozenset({"size"}),
    "clock": frozenset({"size"}),
    "slots": frozenset({"capacity", "groups", "sizes", "default_size", "when_full"}),
    "dice": frozenset(),
    "conditions": frozenset({"allowed"}),
    "ref": frozenset({"to"}),
    "refs": frozenset({"to"}),
    "list": frozenset(),
    "map": frozenset(),
    "derived": frozenset({"expr"}),
}
COMMON_OPTIONS = frozenset({"kind", "label", "help", "required", "default", "roll", "secret"})
HOOK_OPTIONS = re.compile(r"^on_[a-z_]+$")  # on_zero, on_full, on_threshold: read by rules
VALUED = frozenset({"stat", "resource", "uses", "pool"})  # {value, max}
SIZED = frozenset({"track", "clock"})  # {value, size}
LIST_KINDS = frozenset({"tags", "conditions", "refs", "list", "slots"})
REPEATS = frozenset({"list", "slots"})  # the list kinds `+=` adds a value to again (two torches)
REF_RE = re.compile(r"^[a-z][a-z0-9-]*:[a-z0-9]+(?:-[a-z0-9]+)*(?:@[a-z]+:[a-z0-9-]+)?$")
DEFAULT_SIZES = {"petty": 0, "normal": 1, "bulky": 2}


class FieldError(ValueError):
    """A value doesn't fit its field; the message says why and how to fix it."""


@dataclass(frozen=True, slots=True)
class FieldSpec:
    name: str
    kind: FieldKind
    options: dict[str, JSON] = field(default_factory=dict)

    def opt(self, key: str, default: JSON = None) -> JSON:
        return self.options.get(key, default)

    @property
    def label(self) -> str:
        return str(self.opt("label") or self.name)

    @property
    def stored(self) -> bool:
        return self.kind != "derived"

    def bounds(self) -> tuple[float | None, float | None]:
        """(floor, ceiling) for the field's number or current value, if any."""
        match self.kind:
            case "stat":
                rng = self.opt("range")
                if isinstance(rng, list) and len(rng) == 2:
                    return _num(rng[0]), _num(rng[1])
                return 0, None
            case "resource" | "uses" | "pool":
                return _num(self.opt("min", 0)), None  # the ceiling is each value's own max
            case "counter":
                return _num(self.opt("min", 0)), _num(self.opt("max"))
            case "int" | "number":
                return _num(self.opt("min")), _num(self.opt("max"))
            case _:
                return None, None


def _num(raw: JSON) -> float | None:
    return float(raw) if isinstance(raw, int | float) and not isinstance(raw, bool) else None


def _int(raw: JSON, what: str) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int | float) or not float(raw).is_integer():
        raise FieldError(_("{what} must be a whole number, not {raw}", what=what, raw=repr(raw)))
    return int(raw)


# ---------------------------------------------------------------------------- reading input


def coerce(spec: FieldSpec, raw: JSON) -> JSON:
    """Turn input into the stored form (`12` → `{value: 12, max: 12}` for a stat) and check it."""
    match spec.kind:
        case "int" | "counter":
            value = _int(_parse_number(raw), spec.name)
            _check_range(spec, value)
            return value
        case "number":
            number = _parse_number(raw)
            if isinstance(number, bool) or not isinstance(number, int | float):
                raise FieldError(
                    _("{field} must be a number, not {raw}", field=spec.name, raw=repr(raw))
                )
            _check_range(spec, number)
            return number
        case "text":
            if not isinstance(raw, str | int | float) or isinstance(raw, bool):
                raise FieldError(_("{field} must be text", field=spec.name))
            return str(raw)
        case "enum":
            values = [str(v) for v in cast(list[JSON], spec.opt("values") or [])]
            text = str(raw)
            match = next((v for v in values if v.casefold() == text.casefold()), None)
            if match is None:
                raise FieldError(
                    _(
                        "{field} must be one of: {values} (not {text})",
                        field=spec.name,
                        values=", ".join(values),
                        text=repr(text),
                    )
                )
            return match
        case "flag":
            if isinstance(raw, bool):
                return raw
            if isinstance(raw, str) and raw.lower() in ("true", "yes", "false", "no"):
                return raw.lower() in ("true", "yes")
            raise FieldError(_("{field} must be true or false", field=spec.name))
        case "tags" | "conditions":
            return _coerce_names(spec, raw)
        case "stat" | "resource" | "uses" | "pool":
            return _coerce_valued(spec, raw)
        case "track" | "clock":
            return _coerce_sized(spec, raw)
        case "slots":
            return _coerce_slots(spec, raw)
        case "dice":
            text = str(raw).strip()
            _check_dice(spec, text)
            return text
        case "ref":
            return _check_ref(spec, raw)
        case "refs":
            items = raw if isinstance(raw, list) else [raw]
            return [_check_ref(spec, item) for item in items]
        case "list":
            return raw if isinstance(raw, list) else [raw]
        case "map":
            if not isinstance(raw, dict):
                raise FieldError(_("{field} must be a mapping", field=spec.name))
            return raw
        case "derived":
            raise FieldError(
                _("{field} is computed from other fields and can't be set", field=spec.name)
            )
    raise FieldError(_("unknown kind {kind}", kind=repr(spec.kind)))


def _parse_number(raw: JSON) -> JSON:
    if isinstance(raw, str) and re.fullmatch(r"\s*-?\d+(\.\d+)?\s*", raw):
        text = raw.strip()
        return float(text) if "." in text else int(text)
    return raw


def _check_range(spec: FieldSpec, value: float) -> None:
    floor, ceiling = spec.bounds()
    if floor is not None and value < floor:
        raise FieldError(
            _(
                "{field} can't go below {limit} (got {value})",
                field=spec.name,
                limit=_show(floor),
                value=_show(value),
            )
        )
    if ceiling is not None and value > ceiling:
        raise FieldError(
            _(
                "{field} can't go above {limit} (got {value})",
                field=spec.name,
                limit=_show(ceiling),
                value=_show(value),
            )
        )


def _show(number: float) -> str:
    return str(int(number)) if float(number).is_integer() else str(number)


def _coerce_names(spec: FieldSpec, raw: JSON) -> list[JSON]:
    items = raw if isinstance(raw, list) else [raw]
    allowed = [str(a) for a in cast(list[JSON], spec.opt("allowed") or [])]
    found: list[JSON] = []
    for item in items:
        name = item.get("name") if isinstance(item, dict) else item
        if not isinstance(name, str) or not name.strip():
            raise FieldError(_("{field} entries need a name", field=spec.name))
        if allowed and name not in allowed:
            raise FieldError(
                _(
                    "{field}: {name} isn't allowed (allowed: {allowed})",
                    field=spec.name,
                    name=repr(name),
                    allowed=", ".join(allowed),
                )
            )
        found.append(item if isinstance(item, dict) else name.strip())
    return found


def _coerce_valued(spec: FieldSpec, raw: JSON) -> dict[str, JSON]:
    """stat/resource/uses/pool: `12`, `"4/6"` or `{value: 4, max: 6}`."""
    if spec.kind == "uses" and isinstance(raw, str) and re.fullmatch(r"d\d+", raw.strip()):
        return {"die": raw.strip()}  # a usage die: `d8`
    if isinstance(raw, dict):
        if spec.kind == "uses" and "die" in raw:
            _check_dice(spec, str(raw["die"]))
            return {"die": str(raw["die"])}
        value = _int(raw.get("value", raw.get("max")), f"{spec.name} value")
        cap_raw = raw.get("max", value)
        cap = _int(cap_raw, f"{spec.name} max") if cap_raw is not None else value
    elif isinstance(raw, str) and "/" in raw:
        left, _sep, right = raw.partition("/")
        value, cap = (
            _int(_parse_number(left), spec.name),
            _int(_parse_number(right), f"{spec.name} max"),
        )
    else:
        value = _int(_parse_number(raw), spec.name)
        fixed = spec.opt("max")
        cap = _int(fixed, f"{spec.name} max") if isinstance(fixed, int) else value
    floor, ceiling = spec.bounds()
    if floor is not None and value < floor:
        raise FieldError(
            _(
                "{field} can't go below {limit} (got {value})",
                field=spec.name,
                limit=_show(floor),
                value=value,
            )
        )
    if ceiling is not None and cap > ceiling:
        raise FieldError(
            _(
                "{field} can't go above {limit} (got {value})",
                field=spec.name,
                limit=_show(ceiling),
                value=cap,
            )
        )
    if value > cap:
        raise FieldError(
            _(
                "{field} {value} is above its max {cap}; set the max too (`{value}/{value}`)",
                field=spec.name,
                value=value,
                cap=cap,
            )
        )
    return {"value": value, "max": cap}


def _coerce_sized(spec: FieldSpec, raw: JSON) -> dict[str, JSON]:
    size_default = spec.opt("size", 4 if spec.kind == "clock" else 10)
    if isinstance(raw, dict):
        value = _int(raw.get("value", 0), f"{spec.name} value")
        size = _int(raw.get("size", size_default), f"{spec.name} size")
    elif isinstance(raw, str) and "/" in raw:
        left, _sep, right = raw.partition("/")
        value, size = (
            _int(_parse_number(left), spec.name),
            _int(_parse_number(right), f"{spec.name} size"),
        )
    else:
        value, size = _int(_parse_number(raw), spec.name), _int(size_default, f"{spec.name} size")
    if not 0 <= value <= size:
        raise FieldError(
            _("{field} must be 0–{size} (got {value})", field=spec.name, size=size, value=value)
        )
    return {"value": value, "size": size}


def _coerce_slots(spec: FieldSpec, raw: JSON) -> list[JSON]:
    items = raw if isinstance(raw, list) else [raw]
    sizes = slot_sizes(spec)
    found: list[JSON] = []
    for item in items:
        entry: dict[str, JSON] = (
            {"name": item}
            if isinstance(item, str)
            else dict(item)
            if isinstance(item, dict)
            else {}
        )
        name = entry.get("name") or entry.get("ref")
        if not isinstance(name, str) or not name.strip():
            raise FieldError(
                _(
                    "{field} items need a name, e.g. `{{name: Rope, size: normal}}`",
                    field=spec.name,
                )
            )
        size = entry.get("size")
        if size is not None and not (isinstance(size, int) or size in sizes):
            raise FieldError(
                _(
                    "{field}: size {size} must be a number or one of {sizes}",
                    field=spec.name,
                    size=repr(size),
                    sizes=", ".join(sizes),
                )
            )
        found.append(entry["name"] if list(entry) == ["name"] else entry)
    return found


def _check_dice(spec: FieldSpec, text: str) -> None:
    from didact.core.errors import InvalidError
    from didact.expr import default_registry, parse

    try:
        parse(text, default_registry())
    except InvalidError as exc:
        raise FieldError(_("{field}: {problem}", field=spec.name, problem=exc.message)) from exc


def _check_ref(spec: FieldSpec, raw: JSON) -> str:
    if not isinstance(raw, str) or not REF_RE.match(raw):
        raise FieldError(
            _(
                "{field} must be a record id like `npc:tom`, not {raw}",
                field=spec.name,
                raw=repr(raw),
            )
        )
    wanted = spec.opt("to")
    if isinstance(wanted, str) and raw.partition(":")[0] != wanted:
        raise FieldError(
            _("{field} must point at a {type} (got {raw})", field=spec.name, type=wanted, raw=raw)
        )
    return raw


# ---------------------------------------------------------------------------- slots


def slot_sizes(spec: FieldSpec) -> dict[str, int]:
    sizes = spec.opt("sizes")
    if isinstance(sizes, dict):
        return {str(k): int(v) for k, v in sizes.items() if isinstance(v, int)}
    return dict(DEFAULT_SIZES)


def item_size(spec: FieldSpec, item: JSON) -> int:
    sizes = slot_sizes(spec)
    default = str(spec.opt("default_size", "normal"))
    raw: JSON = item.get("size", default) if isinstance(item, dict) else default
    count = item.get("count", 1) if isinstance(item, dict) else 1
    per = raw if isinstance(raw, int) else sizes.get(str(raw), 1)
    stack = item.get("stack") if isinstance(item, dict) else None
    if isinstance(stack, int) and stack > 0 and isinstance(count, int):
        return per * -(-count // stack)  # e.g. 3 rations per slot
    return per * (count if isinstance(count, int) and not isinstance(count, bool) else 1)


def item_name(item: JSON) -> str:
    if isinstance(item, dict):
        name = str(item.get("name") or item.get("ref") or "?")
        count = item.get("count")
        return f"{name} ×{count}" if isinstance(count, int) and count > 1 else name
    return str(item)


# ---------------------------------------------------------------------------- changing values


def change(spec: FieldSpec, current: JSON, op: str, raw: JSON) -> tuple[JSON, str | None]:
    """Apply `=`, `+=` or `-=`; returns (new stored value, note). Numbers clamp to their range;
    taking from a list what it doesn't hold returns `current` itself, unchanged, with a note."""
    if op == "=":
        if spec.kind in VALUED and isinstance(current, dict) and "value" in current:
            parsed = _parse_number(raw)
            if isinstance(parsed, int) and not isinstance(parsed, bool):
                cap = current.get("max")
                if spec.kind == "stat" and isinstance(cap, int) and parsed > cap:
                    rose = _("{field}'s max rose to {value}", field=spec.name, value=parsed)
                    return coerce(spec, parsed), rose
                _check_range(spec, parsed) if spec.kind == "stat" else None
                return _clamp_valued(spec, current, parsed)
        if spec.kind in SIZED and isinstance(current, dict):
            parsed = _parse_number(raw)
            if isinstance(parsed, int) and not isinstance(parsed, bool):
                return coerce(spec, {**current, "value": parsed}), None
        return coerce(spec, raw), None
    sign = 1 if op == "+=" else -1
    if spec.kind in VALUED | SIZED:
        base = (
            current
            if isinstance(current, dict)
            else coerce(spec, 0 if spec.kind in SIZED else current or 0)
        )
        amount = _int(_parse_number(raw), spec.name)
        target = _int(cast(dict[str, JSON], base).get("value", 0), spec.name) + sign * amount
        if spec.kind in SIZED:
            size = _int(cast(dict[str, JSON], base)["size"], f"{spec.name} size")
            clamped = min(max(target, 0), size)
            note = (
                f"{spec.name} is full ({size}/{size})"
                if clamped == size and target >= size
                else None
            )
            return {"value": clamped, "size": size}, note
        return _clamp_valued(spec, cast(dict[str, JSON], base), target)
    if spec.kind in ("int", "number", "counter"):
        delta = _parse_number(raw)
        if isinstance(delta, bool) or not isinstance(delta, int | float):
            raise FieldError(_("{field}: `{op}` needs a number", field=spec.name, op=op))
        start = current if isinstance(current, int | float) and not isinstance(current, bool) else 0
        number = float(start) + sign * float(delta)
        floor, ceiling = spec.bounds()
        limited = number
        if floor is not None:
            limited = max(limited, floor)
        if ceiling is not None:
            limited = min(limited, ceiling)
        stored: JSON = int(limited) if limited.is_integer() else limited
        note = None
        if limited != number:
            past = _show(abs(number - limited))
            note = _(
                "{field} stopped at {value} ({past} past its limit)",
                field=spec.name,
                value=_show(limited),
                past=past,
            )
        return stored, note
    if spec.kind in LIST_KINDS:
        items = cast(list[JSON], current if isinstance(current, list) else [])
        incoming = raw if isinstance(raw, list) else [raw]
        if sign > 0:
            merged = [*items, *(i for i in incoming if spec.kind in REPEATS or i not in items)]
            return coerce(spec, merged), None
        names = {item_name(i).casefold() for i in incoming} | {str(i).casefold() for i in incoming}
        kept = [
            i
            for i in items
            if item_name(i).casefold() not in names and str(i).casefold() not in names
        ]
        held = {item_name(i).casefold() for i in items} | {str(i).casefold() for i in items}
        absent = [i for i in incoming if not {item_name(i).casefold(), str(i).casefold()} & held]
        if not absent:
            return kept, None
        if spec.kind in ("tags", "conditions"):  # one it could never hold is still a mistake
            _coerce_names(spec, absent)
        elif spec.kind == "refs":
            for value in absent:
                _check_ref(spec, value)
        note = _(  # taking what isn't there changes nothing, and says so
            "{field} has no {items}", field=spec.name, items=", ".join(str(i) for i in absent)
        )
        return (kept if len(kept) != len(items) else current), note
    raise FieldError(
        _(
            "{field}: `{op}` doesn't apply to a {kind}; use `=`",
            field=spec.name,
            op=op,
            kind=spec.kind,
        )
    )


def _clamp_valued(
    spec: FieldSpec, current: dict[str, JSON], target: int
) -> tuple[JSON, str | None]:
    cap = _int(current.get("max", target), f"{spec.name} max")
    floor, _ceiling = spec.bounds()
    low = int(floor) if floor is not None else None
    clamped = min(target, cap)
    if low is not None:
        clamped = max(clamped, low)
    note = None
    if target < clamped:
        note = _(
            "{field} stopped at {value} ({past} past zero)",
            field=spec.name,
            value=clamped,
            past=clamped - target,
        )
    elif target > clamped:
        note = _(
            "{field} stopped at its max {value} ({past} over)",
            field=spec.name,
            value=cap,
            past=target - cap,
        )
    return {**current, "value": clamped}, note


# ---------------------------------------------------------------------------- reading and showing


def display(spec: FieldSpec, stored: JSON) -> str:
    """`10/12`, `4/6`, `2/10`, `[deprived]`, `d8`, …"""
    match spec.kind:
        case "stat" | "resource" | "uses" | "pool" if isinstance(stored, dict):
            if "die" in stored:
                return _("usage die {die}", die=stored["die"])
            value, cap = stored.get("value"), stored.get("max")
            text = f"{value}" if value == cap and spec.kind == "stat" else f"{value}/{cap}"
            if spec.kind == "pool":
                return (
                    f"{value}d" if value == cap else _("{value}d (of {cap})", value=value, cap=cap)
                )
            return text
        case "track" | "clock" if isinstance(stored, dict):
            return f"{stored.get('value')}/{stored.get('size')}"
        case "slots" if isinstance(stored, list):
            return ", ".join(item_name(i) for i in stored) or _("empty")
        case "conditions" | "tags" | "refs" | "list" if isinstance(stored, list):
            return ", ".join(item_name(i) for i in stored) or _("none")
        case "flag":
            return _("yes") if stored else _("no")
    if isinstance(stored, dict):
        return ", ".join(f"{k}: {v}" for k, v in stored.items())
    return str(stored)
