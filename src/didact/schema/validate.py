"""Checking `schemas/*.yaml` type definitions when a pack is built."""

import re

from didact.core.i18n import _
from didact.core.output import JSON
from didact.packs.kinds import register_validator
from didact.packs.source import Doc, Problem
from didact.schema.fields import COMMON_OPTIONS, HOOK_OPTIONS, KIND_OPTIONS
from didact.store.entity import CORE_ORDER

FIELD_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TYPE_KEYS = frozenset(
    {"type", "extends", "label", "description", "fields", "guidance", "open", "details"}
)
HOOK_ACTIONS = frozenset({"set", "condition", "trigger", "do", "message", "note"})
# A record's own keys: a field of the same name would be taken for them (`details` for the
# GM's notes, `extra` for bookkeeping) when a record is made from a payload.
RECORD_KEYS = frozenset({*CORE_ORDER, "body"})


def check_type(doc: Doc) -> list[Problem]:
    problems: list[Problem] = []
    data = doc.data
    for key in sorted(set(data) - TYPE_KEYS):
        problems.append(
            doc.problem(
                (key,),
                _("unknown key `{key}`", key=key),
                _("use one of: {keys}", keys=", ".join(sorted(TYPE_KEYS))),
            )
        )
    suggested = data.get("details", [])
    if not isinstance(suggested, list) or not all(isinstance(d, str) for d in suggested):
        problems.append(
            doc.problem(
                ("details",), _("`details` lists detail names"), _("e.g. [looks, wants, plan]")
            )
        )
    fields = data.get("fields", {})
    if not isinstance(fields, dict):
        return [*problems, doc.problem(("fields",), _("`fields` must be a mapping of name → spec"))]
    for name, spec in fields.items():
        problems.extend(_check_field(doc, name, spec))
    return problems


def _check_field(doc: Doc, name: str, spec: JSON) -> list[Problem]:
    loc = ("fields", name)
    if not FIELD_NAME.match(name):
        return [
            doc.problem(
                loc,
                _("invalid field name {name}", name=repr(name)),
                _("use letters, digits and _"),
            )
        ]
    if name in RECORD_KEYS:
        return [
            doc.problem(
                loc,
                _("field `{name}` is named like a record's own key", name=name),
                _("rename it (a record keeps `{name}` for itself), e.g. `{name}_`", name=name),
            )
        ]
    if isinstance(spec, str):
        spec = {"kind": spec}
    if not isinstance(spec, dict):
        return [
            doc.problem(
                loc,
                _("field `{name}` must be a mapping", name=name),
                _("e.g. {kind: stat, range: [0, 18]}"),
            )
        ]
    kind = spec.get("kind")
    if kind not in KIND_OPTIONS:
        kinds = ", ".join(KIND_OPTIONS)
        return [
            doc.problem(
                (*loc, "kind"),
                _("field `{name}`: unknown kind {kind}", name=name, kind=repr(kind)),
                _("use one of: {keys}", keys=kinds),
            )
        ]
    problems: list[Problem] = []
    allowed = KIND_OPTIONS[str(kind)] | COMMON_OPTIONS
    takes = ", ".join(sorted(KIND_OPTIONS[str(kind)])) or _("no options")
    for option in spec:
        if option not in allowed and not HOOK_OPTIONS.match(option):
            message = _(
                "field `{name}`: `{option}` doesn't apply to {kind}",
                name=name,
                option=option,
                kind=kind,
            )
            hint = _("{kind} takes: {options}", kind=kind, options=takes)
            problems.append(doc.problem((*loc, option), message, hint))
    if kind == "enum" and not (isinstance(spec.get("values"), list) and spec["values"]):
        problems.append(
            doc.problem(
                loc,
                _("field `{name}`: an enum needs `values`", name=name),
                _("e.g. values: [a, b]"),
            )
        )
    if kind == "derived" and not isinstance(spec.get("expr"), str):
        problems.append(
            doc.problem(
                loc,
                _("field `{name}`: a derived field needs `expr`", name=name),
                _('e.g. expr: "min(3, @armor)"'),
            )
        )
    if kind == "stat" and "range" in spec:
        rng = spec["range"]
        if not (isinstance(rng, list) and len(rng) == 2 and all(isinstance(v, int) for v in rng)):
            problems.append(
                doc.problem(
                    (*loc, "range"), _("field `{name}`: range must be [low, high]", name=name)
                )
            )
    for expr_key in ("roll", "expr"):
        text = spec.get(expr_key)
        if isinstance(text, str):
            problems.extend(_check_expr(doc, (*loc, expr_key), text))
    for hook in ("on_zero", "on_full", "when_full"):
        if hook in spec:
            problems.extend(_check_hook(doc, (*loc, hook), spec[hook]))
    marks = spec.get("thresholds")
    if kind == "counter" and marks is not None:
        if not isinstance(marks, dict):
            hint = _('e.g. thresholds: {10: "Gain a mutation."}')
            message = _("thresholds map n → action")
            problems.append(doc.problem((*loc, "thresholds"), message, hint))
        else:
            for mark, action in marks.items():
                problems.extend(_check_hook(doc, (*loc, "thresholds", str(mark)), action))
    return problems


def _check_hook(doc: Doc, loc: tuple[str, ...], action: JSON) -> list[Problem]:
    """A hook action: text, {set: {…}}, {condition: x}, {trigger: rule}, or a list of these."""
    if isinstance(action, str):
        return []
    if isinstance(action, list):
        return [p for item in action for p in _check_hook(doc, loc, item)]
    hint = _("use text, {set: {hp: 0}}, {condition: name}, {trigger: rule} or a list of these")
    if not isinstance(action, dict):
        return [doc.problem(loc, _("a hook action can't be {action}", action=repr(action)), hint)]
    problems = [
        doc.problem(loc, _("unknown hook action `{key}`", key=key), hint)
        for key in sorted(set(action) - HOOK_ACTIONS)
    ]
    if "set" in action and not isinstance(action["set"], dict):
        problems.append(
            doc.problem(loc, _("`set` takes field: value pairs"), _("e.g. {set: {hp: 0}}"))
        )
    return problems


def _check_expr(doc: Doc, loc: tuple[str, ...], text: str) -> list[Problem]:
    from didact.core.errors import InvalidError, UnknownName
    from didact.expr import default_registry, parse

    try:
        parse(text, default_registry())
    except InvalidError as exc:
        if isinstance(exc, UnknownName) and exc.what == "die":
            return []  # pack dice aren't known at this point; checked when rolled
        return [
            doc.problem(loc, _("`{text}`: {problem}", text=text, problem=exc.message), exc.hint)
        ]
    return []


register_validator("type", check_type)
