"""Checking rules (checks, actions, procedures, triggers, options) when a pack is built."""

import re

from didact.core.i18n import _
from didact.core.output import JSON
from didact.packs.kinds import register_validator
from didact.packs.source import Doc, Loc, Problem

PARAM_KINDS = frozenset({"ref", "enum", "int", "number", "text", "dice", "flag", "list"})
PARAM_KEYS = frozenset({"kind", "values", "default", "help", "to", "optional"})
CHECK_KEYS = frozenset({
    "check", "title", "help", "params", "before", "roll", "success", "bands", "auto", "natural",
    "flags", "on", "prompt", "options", "source", "tags",
})  # fmt: skip
STEPS_KEYS = frozenset(
    {"action", "procedure", "title", "help", "params", "steps", "prompt", "source", "tags"}
)
TRIGGER_KEYS = frozenset(
    {"trigger", "title", "help", "on", "for", "when", "params", "steps", "source", "tags"}
)
TRIGGER_FOR = frozenset({"party", "pcs"})  # run once per member, as `who`
OPTION_KEYS = frozenset(
    {"option", "title", "ask", "help", "kind", "choices", "default", "implies", "source", "tags"}
)
STEP_KINDS = frozenset({
    "roll", "let", "set", "unset", "entity", "give", "take", "use", "check", "table", "if",
    "repeat", "for", "message", "prompt", "reminder", "do", "stop", "reroll", "pick", "pool",
    "remind",
})  # fmt: skip
STEP_EXTRAS = frozenset({
    "as", "with", "then", "else", "steps", "record", "field", "op", "value", "to", "from",
    "count", "spend", "data", "keep_if", "times", "distinct", "method", "mode", "drop", "extra",
    "in", "every", "go_on",
})  # fmt: skip
CARRIED = {"give": "to", "take": "from", "use": "from"}  # whose inventory the step changes
DRAFT_STEPS = frozenset({
    "choose", "choose_or_roll", "swap", "point_buy", "assign", "apply", "roll_tables", "name",
    "ask", "add", "remove", "map",
})  # fmt: skip
GENERATOR_KEYS = frozenset(
    {"generator", "title", "help", "params", "steps", "creates", "prompt", "source", "tags"}
)
CHARGEN_KEYS = frozenset({
    "chargen", "title", "help", "params", "steps", "creates", "advances", "modes", "prompt",
    "advance", "source", "tags",
})  # fmt: skip
MODES = frozenset({"random", "guided", "template"})
TRIGGER_EVENTS = frozenset({
    "scene_start", "scene_end", "session_start", "session_end", "combat_start", "combat_end",
    "time", "manual",
})  # fmt: skip


def check_rule(doc: Doc) -> list[Problem]:
    data = doc.data
    if "check" in data:
        allowed, kind = CHECK_KEYS, "check"
    elif "trigger" in data:
        allowed, kind = TRIGGER_KEYS, "trigger"
    else:
        allowed, kind = STEPS_KEYS, "action" if "action" in data else "procedure"
    problems = [
        doc.problem(
            (key,),
            _("unknown key `{key}`", key=key),
            _("a {kind} takes: {keys}", kind=kind, keys=", ".join(sorted(allowed))),
        )
        for key in sorted(set(data) - allowed)
    ]
    problems += _check_params(doc, data.get("params"))
    problems += quoted_params(doc)
    if kind == "check":
        problems += _check_check(doc, data)
    else:
        steps = data.get("steps")
        if kind != "trigger" and not isinstance(steps, list):
            problems.append(doc.problem((), _("a {kind} needs `steps: [...]`", kind=kind)))
        problems += _check_steps(doc, ("steps",), steps)
    if kind == "trigger":
        event = data.get("on", "manual")
        if event not in TRIGGER_EVENTS:
            events = ", ".join(sorted(TRIGGER_EVENTS))
            problems.append(
                doc.problem(
                    ("on",),
                    _("unknown trigger event {event}", event=repr(event)),
                    _("use one of: {events}", events=events),
                )
            )
        problems += _expr(doc, ("when",), data.get("when"))
        each = data.get("for")
        if each is not None and each not in TRIGGER_FOR:
            problems.append(
                doc.problem(
                    ("for",),
                    _("a trigger runs `for:` party or pcs, not {value}", value=repr(each)),
                    _("e.g. `for: pcs` runs it once per player character, as `who`"),
                )
            )
    return problems


def _check_params(doc: Doc, params: JSON) -> list[Problem]:
    if params is None:
        return []
    if not isinstance(params, dict):
        return [
            doc.problem(
                ("params",),
                _("`params` must map names to kinds"),
                _("e.g. {example}", example="{who: ref, attr: {enum: [STR]}}"),
            )
        ]
    problems: list[Problem] = []
    for name, spec in params.items():
        loc: Loc = ("params", name)
        if isinstance(spec, str):
            spec = {"kind": spec}
        if not isinstance(spec, dict):
            problems.append(
                doc.problem(loc, _("param `{name}` must be a kind or a mapping", name=name))
            )
            continue
        if "enum" in spec:
            spec = {
                "kind": "enum",
                "values": spec["enum"],
                **{k: v for k, v in spec.items() if k != "enum"},
            }
        kind = spec.get("kind", "text")
        if kind not in PARAM_KINDS:
            kinds = ", ".join(sorted(PARAM_KINDS))
            problems.append(
                doc.problem(
                    loc,
                    _("param `{name}`: unknown kind {kind}", name=name, kind=repr(kind)),
                    _("use one of: {kinds}", kinds=kinds),
                )
            )
        for key in sorted(set(spec) - PARAM_KEYS):
            problems.append(
                doc.problem(
                    (*loc, key), _("param `{name}`: unknown option `{key}`", name=name, key=key)
                )
            )
        if kind == "enum" and not isinstance(spec.get("values"), list):
            problems.append(
                doc.problem(loc, _("param `{name}`: an enum needs `values`", name=name))
            )
    return problems


def _check_check(doc: Doc, data: dict[str, JSON]) -> list[Problem]:
    problems = _check_steps(doc, ("before",), data.get("before"))
    roll = data.get("roll")
    if roll is None and "before" not in data:
        problems.append(
            doc.problem(
                (),
                _("a check needs `roll:`"),
                _("e.g. roll: d20 (or a `before:` step rolls it)"),
            )
        )
    elif isinstance(roll, dict):
        for name, expr in roll.items():
            problems += _expr(doc, ("roll", name), expr, dice=True)
    else:
        problems += _expr(doc, ("roll",), roll, dice=True)
    problems += _expr(doc, ("success",), data.get("success"))
    bands = data.get("bands")
    if bands is not None:
        if not isinstance(bands, dict) or not bands:
            problems.append(
                doc.problem(("bands",), _("`bands` must map outcome names to conditions"))
            )
        else:
            for name, expr in bands.items():
                if expr != "else":
                    problems += _expr(doc, ("bands", name), expr)
    flags = data.get("flags")
    for name, expr in flags.items() if isinstance(flags, dict) else []:
        problems += _expr(doc, ("flags", name), expr)
    on = data.get("on")
    for outcome, steps in on.items() if isinstance(on, dict) else []:
        problems += _check_steps(doc, ("on", outcome), steps)
    options = data.get("options")
    for name, option in options.items() if isinstance(options, dict) else []:
        if isinstance(option, dict):
            problems += _expr(doc, ("options", name, "when"), option.get("when"))
            problems += _check_steps(doc, ("options", name, "steps"), option.get("steps"))
    return problems


def _check_steps(doc: Doc, loc: Loc, steps: JSON, *, draft: bool = False) -> list[Problem]:
    from didact.rules.engine import is_text

    if steps is None:
        return []
    if not isinstance(steps, list):
        return [doc.problem(loc, _("steps must be a list"))]
    allowed = STEP_KINDS | DRAFT_STEPS if draft else STEP_KINDS
    problems: list[Problem] = []
    for index, step in enumerate(steps):
        where: Loc = (*loc, index)
        if isinstance(step, str):
            continue  # a bare string is a message
        if not isinstance(step, dict):
            problems.append(
                doc.problem(
                    where,
                    _(
                        "each step must be a mapping, e.g. {example}",
                        example="{roll: d6, as: dmg}",
                    ),
                )
            )
            continue
        kinds = [k for k in step if k in allowed]
        unknown = sorted(set(step) - allowed - STEP_EXTRAS)
        if len(kinds) != 1:
            problems.append(
                doc.problem(
                    where,
                    _("a step needs exactly one of: {kinds}", kinds=", ".join(sorted(allowed))),
                )
            )
        elif unknown:
            problems.append(
                doc.problem((*where, unknown[0]), _("unknown step key `{key}`", key=unknown[0]))
            )
        if "if" in step:
            problems += _expr(doc, (*where, "if"), step["if"])
            problems += _check_steps(doc, (*where, "then"), step.get("then"), draft=draft)
            problems += _check_steps(doc, (*where, "else"), step.get("else"), draft=draft)
        if "repeat" in step or "for" in step:
            problems += _check_steps(doc, (*where, "steps"), step.get("steps"), draft=draft)
        if "for" in step:
            problems += _check_for(doc, where, step)
        if "entity" in step and not draft:
            problems += _check_entity(doc, where, step)
        for kind, key in CARRIED.items():
            if kind in step and key not in step:
                problems.append(
                    doc.problem(
                        (*where, kind),
                        _("a `{step}` step needs `{key}:`", step=kind, key=key),
                        _("e.g. {example}", example=f'{{{kind}: Rope, {key}: "@who"}}'),
                    )
                )
        if "roll" in step and isinstance(step["roll"], str):
            problems += _expr(doc, (*where, "roll"), step["roll"], dice=True)
        lets = step.get("let")
        if isinstance(lets, dict):
            for name, expr in lets.items():
                if not is_text(expr):
                    problems += _expr(doc, (*where, "let", name), expr)
    return problems


def _check_for(doc: Doc, where: Loc, step: dict[str, JSON]) -> list[Problem]:
    """A loop over the party (`for: party`) or its player characters (`for: pcs`), each member
    named by `as:`: never a parameter's name, so a rule's own `who` can't be taken for it."""
    problems: list[Problem] = []
    if str(step["for"]) not in TRIGGER_FOR:
        problems.append(
            doc.problem(
                (*where, "for"),
                _("a `for:` step runs over party or pcs, not {value}", value=repr(step["for"])),
                _("e.g. {example}", example="for: pcs"),
            )
        )
    name = str(step.get("as", "member"))
    params = doc.data.get("params")
    if isinstance(params, dict) and name in params:
        problems.append(
            doc.problem(
                (*where, "as"),
                _(
                    "a `for:` step can't call each member {name}: a parameter has that name",
                    name=name,
                ),
                _("e.g. {example}", example="as: member"),
            )
        )
    return problems


def _check_entity(doc: Doc, where: Loc, step: dict[str, JSON]) -> list[Problem]:
    """A record a rule's `entity:` step makes, named by `as:` (else its `key`, else its type):
    never a parameter's name either, so a rule's own `faction` can't be taken for the new one."""
    spec = step["entity"]
    described = spec if isinstance(spec, dict) else {}
    name = step.get("as", described.get("key") or described.get("type"))
    params = doc.data.get("params")
    if not isinstance(params, dict) or name not in params:
        return []
    message = _(
        "an `entity:` step can't call its record {name}: a parameter has that name", name=name
    )
    loc: Loc = (*where, "as" if "as" in step else "entity")
    return [doc.problem(loc, message, _("e.g. {example}", example=f"as: new_{name}"))]


_META = frozenset({
    "check", "action", "procedure", "trigger", "generator", "chargen", "title", "help", "params",
    "source", "tags", "creates", "advances", "modes", "for",
})  # fmt: skip
_EXPRESSIONS = frozenset({"if", "when", "roll", "repeat", "success", "value", "keep_if"})
_EXPRESSION_MAPS = frozenset({"let", "bands", "flags", "with", "roll"})  # each value one
_PLACEHOLDER = re.compile(r"(?<![@{])\{((?:[^{}]|@\{[^{}]*\})+)\}")  # `{…}` in a text
_QUOTED = re.compile(r"'([^']*)'|\"([^\"]*)\"")
_DOLLAR = re.compile(r"\$([A-Za-z_]\w*)")


def quoted_params(doc: Doc) -> list[Problem]:
    """A warning where an expression quotes a parameter of free text (`'$book' in
    @who.inventory`, or inside a text's `{…}`): an apostrophe in its text (`Ana's`) ends the
    quotes, and the rule breaks on it. `@book` reads the same text whole. An enum's, a number's
    or a record's text can't hold one, so quoting those is left be."""
    params = doc.data.get("params")
    free = {
        str(name)
        for name, spec in params.items()
        if (spec if isinstance(spec, str) else _param_kind(spec)) == "text"
    } if isinstance(params, dict) else set()  # fmt: skip
    if not free:
        return []
    found: list[Problem] = []
    for key, node in doc.data.items():
        if key in _META:
            continue
        for loc, text, whole in _strings(node, (str(key),), str(key) in _EXPRESSIONS):
            parts = [text] if whole and "{" not in text else []
            parts += [m.group(1) for m in _PLACEHOLDER.finditer(text)]
            quoted: dict[str, str] = {}  # each parameter quoted, and the first text quoting it
            for literal in (q for part in parts for q in _QUOTED.finditer(part)):
                for name in _DOLLAR.findall(literal.group(1) or literal.group(2) or ""):
                    if name in free:
                        quoted.setdefault(name, literal.group(0))
            found += [
                Problem(
                    doc.file,
                    doc.line_of(loc),
                    _("`{quoted}` quotes `${name}`, free text: an apostrophe in it ends the quotes",
                      quoted=literal, name=name),
                    _("read it as `@{name}`, which takes any text whole", name=name),
                    "warning",
                )
                for name, literal in sorted(quoted.items())
            ]  # fmt: skip
    return found


def _param_kind(spec: JSON) -> str:
    """A parameter's kind as the engine reads it (`Rule.params`): an enum, else `kind:`, else
    text."""
    if not isinstance(spec, dict):
        return "text"
    return "enum" if "enum" in spec else str(spec.get("kind", "text"))


def _strings(node: JSON, loc: Loc, whole: bool) -> list[tuple[Loc, str, bool]]:
    """Every text under a rule's key, where it is (`loc`), and whether it is an expression whole
    (`if:`, `let:` values …) or only in its `{…}`."""
    if isinstance(node, str):
        return [(loc, node, whole)]
    found: list[tuple[Loc, str, bool]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            expression = str(key) in _EXPRESSIONS or loc[-1] in _EXPRESSION_MAPS
            found += _strings(value, (*loc, str(key)), expression)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found += _strings(value, (*loc, index), False)
    return found


def _expr(doc: Doc, loc: Loc, text: JSON, *, dice: bool = False) -> list[Problem]:
    """Parse an expression (after `$param` text is filled with a placeholder)."""
    if text is None or isinstance(text, bool | int | float):
        return []
    if not isinstance(text, str):
        return [doc.problem(loc, _("expected an expression (text)"))]
    from didact.core.errors import InvalidError, UnknownName
    from didact.expr import default_registry, parse
    from didact.rules.engine import substitute

    probe = substitute(text, {}, placeholder="d6" if dice else "1")
    try:
        parse(probe, default_registry())
    except InvalidError as exc:
        if isinstance(exc, UnknownName) and exc.what in ("die", "name"):
            return []  # pack dice and macros are checked when the rule runs
        return [doc.problem(loc, f"`{text}`: {exc.message}", exc.hint)]
    return []


def check_draft_procedure(doc: Doc) -> list[Problem]:
    """Generators and chargen: procedures that build a draft (see `didact.rules.drafts`)."""
    data = doc.data
    kind = "chargen" if "chargen" in data else "generator"
    allowed = CHARGEN_KEYS if kind == "chargen" else GENERATOR_KEYS
    problems = [
        doc.problem(
            (key,),
            _("unknown key `{key}`", key=key),
            _("a {kind} takes: {keys}", kind=kind, keys=", ".join(sorted(allowed))),
        )
        for key in sorted(set(data) - allowed)
    ]
    problems += _check_params(doc, data.get("params"))
    problems += quoted_params(doc)
    if not isinstance(data.get("steps"), list):
        problems.append(doc.problem((), _("a {kind} needs `steps: [...]`", kind=kind)))
    problems += _check_steps(doc, ("steps",), data.get("steps"), draft=True)
    modes = data.get("modes")
    if modes is not None and not (isinstance(modes, list) and set(map(str, modes)) <= MODES):
        problems.append(
            doc.problem(("modes",), _("modes are some of: {modes}", modes=", ".join(sorted(MODES))))
        )
    advances = data.get("advances")
    if advances is not None and (not isinstance(advances, str) or "creates" in data):
        problems.append(
            doc.problem(
                ("advances",),
                _("advances names the type of record it changes, and goes without creates"),
                _("e.g. {example}", example="advances: pc"),
            )
        )
    advance = data.get("advance")
    if advance is not None and not (
        isinstance(advance, dict) and isinstance(advance.get("rule"), str)
    ):
        problems.append(
            doc.problem(
                ("advance",),
                _("advance names a rule"),
                _("e.g. {example}", example="advance: {rule: level-up}"),
            )
        )
    return problems


def check_option(doc: Doc) -> list[Problem]:
    """An option: a flag (`kind: flag`), or `choices` (value → what it means) with a default
    among them; `implies` maps a choice to the other options it sets."""
    data = doc.data
    problems = [
        doc.problem(
            (key,),
            _("unknown key `{key}`", key=key),
            _("an option takes: {keys}", keys=", ".join(sorted(OPTION_KEYS))),
        )
        for key in sorted(set(data) - OPTION_KEYS)
    ]
    kind = data.get("kind")
    choices = data.get("choices")
    if kind is not None and kind != "flag":
        problems.append(
            doc.problem(("kind",), _("an option's kind is flag, or left out for choices"))
        )
    if kind == "flag":
        if choices is not None:
            problems.append(
                doc.problem(("choices",), _("a flag has no choices"), _("drop `kind: flag`"))
            )
        if data.get("default") not in (None, True, False):
            problems.append(doc.problem(("default",), _("a flag's default is true or false")))
        values = ["on", "off"]
    else:
        if not isinstance(choices, dict) or len(choices) < 2:
            problems.append(
                doc.problem(
                    ("choices",),
                    _("an option needs two choices or more, each with what it means"),
                    _("e.g. {example}", example="choices: {standard: …, deadly: …}"),
                )
            )
            return problems
        values = [str(k) for k in choices]
        default = data.get("default")
        if default is not None and str(default) not in values:
            problems.append(
                doc.problem(
                    ("default",),
                    _("the default {value} isn't a choice", value=repr(default)),
                    _("choices: {choices}", choices=", ".join(values)),
                )
            )
    implies = data.get("implies")
    if implies is not None:
        if not isinstance(implies, dict):
            problems.append(
                doc.problem(("implies",), _("`implies` maps a choice to the options it sets"))
            )
        else:
            for key, sets in implies.items():
                shown = str(key)
                if shown not in values:
                    problems.append(
                        doc.problem(
                            ("implies", str(key)),
                            _("{value} isn't a choice", value=repr(shown)),
                            _("choices: {choices}", choices=", ".join(values)),
                        )
                    )
                if not isinstance(sets, dict):
                    problems.append(
                        doc.problem(
                            ("implies", str(key)),
                            _("a choice implies option: value pairs"),
                            _("e.g. {example}", example="{lethality: deadly}"),
                        )
                    )
    return problems


for _kind in ("check", "action", "procedure", "trigger"):
    register_validator(_kind, check_rule)
register_validator("option", check_option)
for _kind in ("generator", "chargen"):
    register_validator(_kind, check_draft_procedure)
