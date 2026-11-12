"""Templates and JSON Schema for a record type: "describe it, get it".

The LLM reads `didact template pc`, fills in what the description gives, writes `"roll"` for
anything the rules roll, and passes the result to `didact new pc --data '{…}'`.
"""

from typing import cast

from didact.core.i18n import _
from didact.core.output import JSON
from didact.schema.fields import VALUED, FieldSpec, slot_sizes
from didact.schema.sheet import Sheet


def describe(spec: FieldSpec) -> str:
    """One line about a field: kind, limits, dice, choices, help."""
    parts: list[str] = [spec.kind]
    match spec.kind:
        case "stat":
            rng = spec.opt("range")
            if isinstance(rng, list) and len(rng) == 2:
                parts[0] = f"stat {rng[0]}–{rng[1]}"
        case "resource" | "uses" | "pool" | "counter" | "int" | "number":
            limits = [
                f"{k} {spec.opt(k)}" for k in ("min", "max", "max_field") if spec.opt(k) is not None
            ]
            if limits:
                parts[0] += f" ({', '.join(limits)})"
        case "enum":
            values = cast(list[JSON], spec.opt("values") or [])
            parts[0] = _("one of: {values}", values=", ".join(str(v) for v in values))
        case "slots":
            sizes = ", ".join(f"{k} {v}" for k, v in slot_sizes(spec).items())
            capacity = spec.opt("capacity", "?")
            parts[0] = _(
                "slots (capacity {capacity}; sizes {sizes}): names or {{name, size, …}}",
                capacity=capacity,
                sizes=sizes,
            )
        case "conditions" | "tags":
            allowed = cast(list[JSON], spec.opt("allowed") or [])
            if allowed:
                listed = ", ".join(str(a) for a in allowed)
                parts[0] = _("{kind} from: {allowed}", kind=parts[0], allowed=listed)
        case "derived":
            parts[0] = _("computed: {expr} (don't give it)", expr=spec.opt("expr"))
        case "ref" | "refs":
            if spec.opt("to"):
                parts[0] = _("{kind} to a {type}", kind=parts[0], type=spec.opt("to"))
        case _:
            pass
    if isinstance(spec.opt("roll"), str):
        parts.append(_('🎲 {roll} (give "roll")', roll=spec.opt("roll")))
    if spec.opt("default") is not None:
        parts.append(_("default {value}", value=spec.opt("default")))
    if spec.opt("required"):
        parts.append(_("required"))
    if spec.opt("help"):
        parts.append(str(spec.opt("help")))
    return " · ".join(parts)


def placeholder(spec: FieldSpec) -> JSON:
    """What the skeleton shows for a field."""
    if isinstance(spec.opt("roll"), str):
        return "roll"
    match spec.kind:
        case "int" | "number" | "counter":
            return spec.opt("default", 0)
        case "flag":
            return spec.opt("default", False)
        case "stat" | "resource" | "uses" | "pool":
            return spec.opt("default", spec.opt("max", 0))
        case "track" | "clock":
            return f"0/{spec.opt('size', 4 if spec.kind == 'clock' else 10)}"
        case "enum":
            values = cast(list[JSON], spec.opt("values") or [])
            return spec.opt("default", values[0] if values else "")
        case "tags" | "conditions" | "refs" | "list" | "slots":
            return []
        case "map":
            return {}
        case "dice":
            return spec.opt("default", "d6")
        case _:
            return spec.opt("default", "")


def skeleton(sheet: Sheet) -> dict[str, JSON]:
    found: dict[str, JSON] = {"name": "…"}
    for schema in sheet.schemas:
        for spec in schema.fields.values():
            if spec.stored:
                found[spec.name] = placeholder(spec)
    return found


# ---------------------------------------------------------------------------- JSON Schema


def json_schema(sheet: Sheet) -> dict[str, JSON]:
    """JSON Schema for `new <type> --data` (top-level keys; Didact routes them to their block)."""
    properties: dict[str, JSON] = {"name": {"type": "string", "minLength": 1}}
    for schema in sheet.schemas:
        for spec in schema.fields.values():
            if spec.stored:
                properties[spec.name] = _property(spec)
    title = " + ".join(f"{s.pack}.{s.type}" for s in sheet.schemas)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"{sheet.type} ({title})",
        "type": "object",
        "properties": properties,
        "required": [
            "name",
            *(n for s in sheet.schemas for n, f in s.fields.items() if f.opt("required")),
        ],
    }


def _property(spec: FieldSpec) -> JSON:
    number: dict[str, JSON] = {"type": "integer"}
    shapes: list[JSON]
    match spec.kind:
        case "int" | "counter":
            shapes = [_limits(number, spec)]
        case "number":
            shapes = [_limits({"type": "number"}, spec)]
        case "text":
            shapes = [{"type": "string"}]
        case "enum":
            shapes = [{"enum": cast(list[JSON], spec.opt("values") or [])}]
        case "flag":
            shapes = [{"type": "boolean"}]
        case "tags" | "conditions":
            item: dict[str, JSON] = {"type": "string"}
            if spec.opt("allowed"):
                item = {"enum": cast(list[JSON], spec.opt("allowed"))}
            shapes = [{"type": "array", "items": item}]
        case kind if kind in VALUED:
            shapes = [
                _limits(dict(number), spec),
                {"type": "string", "pattern": r"^\d+/\d+$"},
                {
                    "type": "object",
                    "properties": {"value": number, "max": number},
                    "required": ["value"],
                },
            ]
        case "track" | "clock":
            shapes = [
                number,
                {"type": "string", "pattern": r"^\d+/\d+$"},
                {"type": "object", "properties": {"value": number, "size": number}},
            ]
        case "slots":
            entry: JSON = {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            }
            shapes = [{"type": "array", "items": {"anyOf": [{"type": "string"}, entry]}}]
        case "dice":
            shapes = [{"type": "string", "description": "a dice expression, e.g. d8"}]
        case "ref":
            shapes = [{"type": "string", "pattern": "^[a-z][a-z0-9-]*:[a-z0-9-]+$"}]
        case "refs" | "list":
            shapes = [{"type": "array"}]
        case _:
            shapes = [{"type": "object"}]
    if isinstance(spec.opt("roll"), str):
        shapes.append({"const": "roll", "description": f"Didact rolls {spec.opt('roll')}"})
    described: dict[str, JSON] = (
        {"anyOf": shapes} if len(shapes) > 1 else dict(cast(dict[str, JSON], shapes[0]))
    )
    if spec.opt("help"):
        described["description"] = str(spec.opt("help"))
    return described


def _limits(base: dict[str, JSON], spec: FieldSpec) -> dict[str, JSON]:
    floor, ceiling = spec.bounds()
    for key, bound in (("minimum", floor), ("maximum", ceiling)):
        if bound is not None:
            base[key] = int(bound) if float(bound).is_integer() else bound
    return base
