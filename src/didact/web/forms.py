"""Forms made from command and rule definitions, and the argument lists they turn back into.

A command's arguments are fields named after their command-line spelling (`a.ref`, `a.tag`
for `--tag`); a rule's parameters are `r.<name>`.
Fields that hold several values (`*args`, repeated options) take one value per line.
Every writing command also gets a dry-run switch and a reason; any command can ask for
full detail. The argument list is built as a list, never as a shell string.
"""

from collections.abc import Mapping, Sequence

from didact.commands.registry import CommandSpec, Param
from didact.core import labels
from didact.core.i18n import _, translate
from didact.core.output import JSON
from didact.rules.engine import Param as RuleParam
from didact.rules.engine import Rule
from didact.web.html import Html, entry, field, h, select, switch, switch_row, textarea
from didact.web.markdown import inline

type Form = Mapping[str, list[str]]


def first(form: Form, name: str) -> str:
    values = form.get(name)
    return values[0] if values else ""


def lines(text: str) -> list[str]:
    """One value per non-blank line."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def split_tags(text: str) -> list[str]:
    return [tag.strip() for chunk in text.splitlines() for tag in chunk.split(",") if tag.strip()]


def text_block(raw: str) -> str:
    """A textarea's text with plain newlines (browsers send CRLF)."""
    return raw.replace("\r\n", "\n").replace("\r", "\n")


def option(flag: str, value: str) -> list[str]:
    """`--flag value`, or `--flag=value` when the value starts with a dash (a list item…)."""
    return [f"{flag}={value}"] if value.startswith("-") else [flag, value]


# ---------------------------------------------------------------------------- typed inputs

# What a box of each kind takes, as the command behind it checks it: a pattern the browser
# holds the box to, and its longest length. `data-input` lets app.js drop or change what
# doesn't fit as it's typed (spaces in an id become dashes, capitals go lower case).
PATTERNS = {
    "id": (r"[a-z0-9][a-z0-9\-]{0,63}", 64),  # world and campaign ids (`core/ids.py`)
    "type": (r"[a-z][a-z0-9\-]{0,31}", 32),  # record types
    "key": (r"[A-Za-z0-9_][A-Za-z0-9_.\-]*", 0),  # field keys (`services/assign.py`)
    "word": (r"[\p{L}\p{N}_\-]+", 64),  # a detail's name: one word
    "event": (r"#?[eErRtT]?[0-9]+", 12),  # e12, r7, t5
}


def accepts(kind: str) -> str:
    """What a box of a kind takes, said for people (under the box, and when it's refused)."""
    return {
        "id": _("lowercase letters, digits and dashes; spaces become dashes"),
        "type": _("lowercase letters, digits and dashes, starting with a letter"),
        "key": _("letters, digits, dashes, dots and underscores; spaces become underscores"),
        "word": _("one word: letters, digits, dashes or underscores"),
        "event": _("an event: e12 (a change), r7 (a roll) or t5 (a turn)"),
    }.get(kind, "")


def bound(kind: str, attrs: Mapping[str, str] | None = None) -> dict[str, str]:
    """The attributes that hold a box to a kind of value (and `attrs` on top)."""
    pattern, longest = PATTERNS[kind]
    found = {
        "pattern": pattern,
        "title": accepts(kind),
        "data-input": kind,
        "autocapitalize": "off",
        "autocomplete": "off",
        "spellcheck": "false",
    }
    if longest:
        found["maxlength"] = str(longest)
    return {**found, **(attrs or {})}


def typed_entry(
    kind: str,
    name: str,
    value: str = "",
    *,
    placeholder: str = "",
    required: bool = False,
    label: str | None = None,
    list_: str | None = None,
) -> Html:
    """A box that takes only one kind of value (`PATTERNS`): an id, a record type, a key."""
    return entry(
        name, value, placeholder=placeholder, required=required, label=label, list_=list_,
        attrs=bound(kind),
    )  # fmt: skip


def time_amount(
    name: str,
    units: Sequence[str],
    *,
    unit_name: str | None = None,
    amount: str = "",
    unit: str = "",
    required: bool = False,
) -> Html:
    """How long, as a number and one of the calendar's units (`3` `watches`): a box that takes
    only a number, and a list of the units this game knows. Both are named `name` unless the
    unit has a name of its own, so a form's words read `3 watch` in order."""
    box = entry(
        name, amount, type_="number", required=required, label=_("How many"), placeholder="1",
        attrs={"min": "0", "step": "any", "inputmode": "decimal"}, cls="is-amount",
    )  # fmt: skip
    chosen = unit if unit in units else "hour" if "hour" in units else (units[0] if units else "")
    pick = select(
        unit_name or name, [(u, labels.time_unit(u)) for u in units], chosen,
        label=_("Unit of time"),
    )  # fmt: skip
    return h(t"{box}{pick}")


# ---------------------------------------------------------------------------- commands


def spelling(param: Param) -> str:
    """How the command line spells an argument: `<ref>`, `<text> ...`, `--as <record>`."""
    match param.kind:
        case "positional":
            return param.metavar
        case "variadic":
            return f"{param.metavar} ..."
        case "flag":
            return param.flag
        case _:
            return f"{param.flag} {param.metavar}" + (" ..." if param.multiple else "")


# What an argument takes, by the name of its value (`Metavar`): a kind of box (`PATTERNS`), an
# amount of game time, or one of a list the page offers (records, drafts, packs, …).
TYPED = {"id": "id", "world-id": "id", "campaign-id": "id", "type": "type", "event": "event"}
TIMES = frozenset({"time", "amount"})
OFFERED = {
    "record": "records", "ref": "records", "who": "records", "target": "records",
    "item": "records", "place": "records", "pc": "records", "thing": "records",
    "fighter": "records", "attacker": "records", "quest": "records", "track": "records",
    "draft": "drafts", "pack": "packs", "save": "saves", "oracle": "oracles",
    "table": "tables", "rule": "rules", "generator": "generators", "chargen": "chargens",
}  # fmt: skip


def value_name(param: Param) -> str:
    """What an argument's value is called (`record`, `time`, …)."""
    return param.value_name or param.cli_name


def offered(spec: CommandSpec) -> set[str]:
    """The lists a command's form can offer (`OFFERED`'s values)."""
    return {OFFERED[value_name(p)] for p in spec.params if value_name(p) in OFFERED}


def command_fields(
    spec: CommandSpec,
    values: Form,
    *,
    gm: bool = False,
    lists: Mapping[str, str] | None = None,
    units: Sequence[str] = (),
) -> Html:
    """The fields for a command's arguments, filled from `values` (a form sent before).

    Each box takes what its argument takes: a number, one of its choices, an id, a record type
    or an event as their patterns have them, an amount of game time as a number and one of
    `units`, and the values of a list the page offers (`lists`: a list's name → its datalist)."""
    controls: list[Html] = []
    switches: list[Html] = []
    for param in spec.params:
        name = f"a.{param.cli_name}"
        given = first(values, name)
        label = _label(param)
        if param.kind == "flag":
            checked = bool(given) if values else (gm and param.name == "gm")
            switches.append(switch_row(label, switch(name, checked=checked, label=param.flag)))
            continue
        wanted = value_name(param)
        if wanted in TIMES and units and not param.multiple:
            unit = first(values, f"{name}.unit")
            amount = time_amount(name, units, unit_name=f"{name}.unit", amount=given, unit=unit,
                                 required=param.required)  # fmt: skip
            controls.append(field(label, h(t'<span class="action-row">{amount}</span>')))
            continue
        listed = (lists or {}).get(OFFERED.get(wanted, ""))
        kind = TYPED.get(wanted)
        about = accepts(kind) if kind and not param.choices else None
        controls.append(field(label, _control(param, name, given, listed), help_=about))
    if spec.writes:
        switches.append(
            switch_row(
                _("Dry run: show what would change, change nothing"),
                switch("dry_run", checked=bool(first(values, "dry_run")), label="--dry-run"),
            )
        )
        controls.append(
            field(
                _label_text(_("why; recorded in the log"), "--reason <text>"),
                entry("reason", first(values, "reason")),
            )
        )
    switches.append(
        switch_row(
            _("Full detail"),
            switch("detail", checked=bool(first(values, "detail")), label="--detail full"),
        )
    )
    return h(t'<div class="fields">{controls}</div><div class="switches">{switches}</div>')


def _label(param: Param) -> Html:
    return _label_text(translate(param.help) or param.cli_name.replace("-", " "), spelling(param))


def _label_text(text: str, spelled: str) -> Html:
    said = text[:1].upper() + text[1:]
    return h(t'<span>{inline(said)}</span> <code class="spelling">{spelled}</code>')


def _control(param: Param, name: str, given: str, listed: str | None = None) -> Html:
    many = param.kind == "variadic" or param.multiple
    if many:
        return textarea(name, given, rows=2, placeholder=_("one per line"))
    required = param.kind == "positional" and param.required
    if param.choices:
        blank = _("(choose)") if required else _default_label(param)
        options = [("", blank), *((c, c) for c in param.choices)]
        return select(name, options, given, required=required)
    if param.base is bool:
        return select(
            name, [("", _default_label(param)), ("true", _("yes")), ("false", _("no"))], given
        )
    kind = "number" if param.base in (int, float) else "text"
    attrs = {"step": "any"} if param.base is float else {}
    if param.base is int:
        attrs = {"step": "1", "inputmode": "numeric"}
    typed = TYPED.get(value_name(param))
    if typed and kind == "text":
        attrs = bound(typed)
    placeholder = (
        "" if param.default in (None, [], ()) else _("default: {value}", value=param.default)
    )
    return entry(
        name, given, type_=kind, placeholder=placeholder, required=required, attrs=attrs,
        list_=listed,
    )  # fmt: skip


def _default_label(param: Param) -> str:
    if param.default in (None, [], ()):
        return _("(default)")
    return _("(default: {value})", value=param.default)


def command_argv(spec: CommandSpec, form: Form) -> list[str]:
    """The argument list a filled-in command form stands for."""
    positionals: list[str] = []
    options: list[str] = []
    for param in spec.params:
        raw = first(form, f"a.{param.cli_name}")
        unit = first(form, f"a.{param.cli_name}.unit").strip()
        if unit and raw.strip():  # an amount of game time: the number, then its unit
            raw = f"{raw.strip()} {unit}"
        match param.kind:
            case "positional":
                if raw.strip():
                    positionals.append(raw.strip())
            case "variadic":
                positionals.extend(lines(raw))
            case "flag":
                if raw:
                    options.append(param.flag)
            case _:
                for value in lines(raw) if param.multiple else [raw.strip()]:
                    if value:
                        options += option(param.flag, value)
    if spec.writes:
        if first(form, "dry_run"):
            options.append("--dry-run")
        reason = first(form, "reason").strip()
        if reason:
            options += option("--reason", reason)
    if first(form, "detail"):
        options += ["--detail", "full"]
    if any(value.startswith("-") for value in positionals):
        return [*spec.words, *options, "--", *positionals]  # so `-1` isn't read as an option
    return [*spec.words, *positionals, *options]


# ---------------------------------------------------------------------------- rules


def rule_params(rule_id: str, data: Mapping[str, JSON]) -> list[RuleParam]:
    """A rule's parameters, read the way the rules engine reads them."""
    rule = Rule("rule", rule_id, rule_id.partition(".")[0], dict(data), "")
    return list(rule.params.values())


def rule_fields(params: Sequence[RuleParam], values: Form, *, records: str | None = None) -> Html:
    """Fields for `didact do <rule> name=value …` (`records` names a datalist of refs)."""
    controls: list[Html] = []
    for param in params:
        name = f"r.{param.name}"
        given = first(values, name)
        spelled = f"{param.name}=<{param.kind}>"
        about = param.help or param.name.replace("_", " ").replace("-", " ")
        required = not param.optional and param.default is None
        label = _label_text(about, spelled)
        match param.kind:
            case "enum":
                blank = (
                    _("(choose)")
                    if required
                    else _("(default: {value})", value=param.default)
                    if param.default
                    else _("(default: none)")
                )
                options = [("", blank), *((v, v) for v in param.values)]
                control = select(name, options, given, required=required)
            case "flag":
                controls.append(switch_row(label, switch(name, checked=bool(given))))
                continue
            case "int" | "number":
                control = entry(
                    name, given, type_="number", required=required, attrs={"step": "any"}
                )
            case "ref":
                control = entry(
                    name, given, required=required, list_=records, placeholder=_("a record")
                )
            case _:
                hint = _("e.g. d6") if param.kind == "dice" else ""
                control = entry(name, given, required=required, placeholder=hint)
        if param.default is not None and param.kind != "enum":
            default = _("(default: {value})", value=param.default)
            label = h(t'{label} <span class="dim small">{default}</span>')
        controls.append(field(label, control))
    return h(t'<div class="fields">{controls}</div>')


def rule_argv(rule_id: str, params: Sequence[RuleParam], form: Form) -> list[str]:
    args: list[str] = []
    for param in params:
        raw = first(form, f"r.{param.name}").strip()
        if param.kind == "flag":
            raw = "true" if raw else ""
        if raw:
            args.append(f"{param.name}={raw}")
    options = ["--dry-run"] if first(form, "dry_run") else []
    return ["do", rule_id, *args, *options]
