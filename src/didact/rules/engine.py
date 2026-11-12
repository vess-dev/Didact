"""Running rules: checks, actions, procedures and triggers.

    check: save                          action: attack
    params: {who: ref, attr: {enum: [STR, DEX, WIL]}}   params: {target: ref, weapon: dice}
    roll: d20                            steps:
    success: "@roll <= @who.$attr"         - roll: $weapon
    auto: {1: success, 20: failure}          as: damage
                                           - set: target.hp
                                             op: "-="
                                             value: "@damage - @target.armor"

`$name` pastes a parameter's text into an expression (`@who.$attr` → `@who.STR`); `@name`
reads a value. The engine talks to the library only through a `Host`, so it's easy to test.
"""

import difflib
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Protocol, cast

from didact.core import labels
from didact.core.errors import DidactError, InvalidError, UnknownName
from didact.core.i18n import _, ngettext, pgettext
from didact.core.output import JSON
from didact.expr import Registry, RollContext, parse
from didact.expr.engine import evaluate, show, truthy
from didact.expr.model import Bool, Text, Value, from_json, to_json

MAX_DEPTH = 12
NOW = frozenset({"system", "session", "scene", "time", "combat"})  # where play stands, for any rule
ACCEPT = "accept the result"  # the option every pending roll has, as kept (`option_label`)


def option_label(name: str, label: str) -> str:
    """A pending roll's option as shown: the book's words, or Didact's own in the reader's
    language."""
    return _("accept the result") if name == "accept" and label == ACCEPT else label


_DOLLAR = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
_BRACED = r"@\{[^{}]*\}"  # a variable whose path `@a.b` can't hold: `@{who.inventory.$item.damage}`
_BRACES = re.compile(  # `{{` and `}}` write a brace itself; `@{…}` is a variable, not a template
    rf"\{{\{{|\}}\}}|{_BRACED}|\{{((?:[^{{}}]|{_BRACED})+)\}}"
)
_LONE = re.compile(rf"\{{((?:[^{{}}]|{_BRACED})+)\}}")  # a value that is one `{expression}`
_VARIABLE = re.compile(_BRACED)
# In a roll, `{…}` is filled in as in any text (`{@d} + 1`), but for what is dice already: a
# variable (`@{…}`), a die's faces (`d{0,1,2}`), or a set of rolls (`{d8, d6}kh1`: `_dice_set`).
_ROLL_FILL = re.compile(rf"{_BRACED}|(?<![dD])\{{((?:[^{{}}]|{_BRACED})+)\}}")
_ATOM = re.compile(r"[\w%\[\]]+")  # a die or a number as it is (`d8`, `2d6kh1`, `4`): no brackets
_SET = re.compile(r"^\s*([A-Za-z_][\w.-]*)\s*(\+=|-=|=)\s*(.+)$")
_BARE_WORD = re.compile(r"(?!(?:true|false)$)[A-Za-z][A-Za-z_ -]*")  # text, not an expression
_PARAM = re.compile(r"\$([A-Za-z_]\w*)")
_OPTION = re.compile(r"@\{?\s*option\.")  # a condition that reads a campaign option


def is_text(value: JSON) -> bool:
    """Is a `set`/`let` value text rather than an expression (so validation leaves it be)?
    `$param` is the parameter's text, text with `{…}` is a template to fill in, and a bare
    word is itself (`value: dead`)."""
    if not isinstance(value, str):
        return False
    text = value.strip()
    params_only = "$" in text and "@" not in text  # text with parameters (or a sum of them)
    return "{" in text or params_only or bool(_BARE_WORD.fullmatch(text))


def _named(item: JSON) -> bool:
    """An item as a list of them holds it: its name, or a mapping with a `name`."""
    return isinstance(item, str) or (isinstance(item, dict) and isinstance(item.get("name"), str))


def substitute(text: str, params: Mapping[str, str], *, placeholder: str | None = None) -> str:
    """Paste parameter text into an expression: `@who.$attr` → `@who.STR`."""

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in params:
            return params[name]
        if placeholder is not None:
            return placeholder
        raise InvalidError(
            _("`${name}` isn't a parameter here", name=name),
            hint=_("parameters are listed under `params:`"),
        )

    return _DOLLAR.sub(replace, text)


# ---------------------------------------------------------------------------- the model


@dataclass(frozen=True, slots=True)
class Param:
    name: str
    kind: str
    values: tuple[str, ...] = ()
    default: JSON = None
    to: str | None = None
    optional: bool = False
    help: str = ""


@dataclass(frozen=True, slots=True)
class Rule:
    kind: str  # check | action | procedure | trigger
    id: str  # qualified
    pack: str
    data: dict[str, JSON]
    source: str

    @property
    def title(self) -> str:
        return str(
            self.data.get("title") or self.id.rpartition(".")[2].replace("-", " ").capitalize()
        )

    @property
    def params(self) -> dict[str, Param]:
        raw = self.data.get("params")
        found: dict[str, Param] = {}
        for name, spec in raw.items() if isinstance(raw, dict) else []:
            spec_map: dict[str, JSON] = spec if isinstance(spec, dict) else {"kind": spec}
            if "enum" in spec_map:
                spec_map = {"kind": "enum", "values": spec_map["enum"], **spec_map}
            values = spec_map.get("values")
            found[name] = Param(
                name,
                str(spec_map.get("kind", "text")),
                tuple(str(v) for v in values) if isinstance(values, list) else (),
                spec_map.get("default"),
                str(spec_map["to"]) if isinstance(spec_map.get("to"), str) else None,
                bool(spec_map.get("optional", False)),
                str(spec_map.get("help", "")),
            )
        return found

    def usage(self) -> str:
        parts = [f"didact do {self.id}"]
        for param in self.params.values():
            example = param.values[0] if param.values else f"<{param.kind}>"
            item = f"{param.name}={example}"
            parts.append(f"[{item}]" if param.optional or param.default is not None else item)
        return " ".join(parts)


# ---------------------------------------------------------------------------- the host


@dataclass(frozen=True, slots=True)
class RollDone:
    label: str  # "#r12"
    line: str
    total: Value
    dice: list[int]  # kept dice, in order
    faces: list[int]  # every die as rolled (for rerolls)
    flags: list[str]
    parts: dict[str, Value] = field(default_factory=dict)  # tagged/labelled parts: hope, fear
    symbols: dict[str, int] = field(default_factory=dict)  # symbol dice: success, advantage


type Resolver = Callable[[str], Value | None]


@dataclass(frozen=True, slots=True)
class FieldSet:
    """What setting a field did: a note (clamping, hooks) and the hook triggers to run."""

    note: str | None = None
    triggers: tuple[str, ...] = ()  # rule refs, run with who=<the record>


@dataclass(frozen=True, slots=True)
class PoolDone:
    """What rolling (or dropping dice from) a tracker's pool did: its lines, the rolls' labels,
    and `highest`, `dropped`, `left`, `empty` and `faces` for the rule to read."""

    lines: list[str]
    rolls: list[str]
    values: dict[str, Value]


@dataclass(frozen=True, slots=True)
class TableDone:
    """A table roll: its label, the entry's text, and its data with what the tables it went on
    to roll add. `path` is each entry it took, as [table, entry], when it went on to any: a
    draft keeps it on its trail (`PATH`), to replay that data."""

    label: str
    text: str
    data: dict[str, JSON]
    path: list[Value] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class EntityDone:
    """A record a rule's `entity:` step made: its id and name, and whether it's new (one of that
    type and name already here is taken as it is)."""

    record: str
    name: str
    new: bool = True


@dataclass(frozen=True, slots=True)
class ItemDone:
    """What giving or taking an item did (`give`, `take`): the item as it came or went (`Rope
    ×2`), a note (where its details came from, the room, hooks) and the hook triggers to run."""

    item: str
    note: str | None = None
    triggers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class UseDone:
    """What using an item did (`use`), as `inv use` does it: the item, a note (its uses left, the
    usage die's roll), the rolls' labels, the hook triggers to run, and for the rule to read
    `out` (its last use went), `gone` (none of it is left), `left`, `die` and `rolled`."""

    item: str
    note: str | None = None
    rolls: tuple[str, ...] = ()
    triggers: tuple[str, ...] = ()
    values: dict[str, Value] = field(default_factory=dict)


class Host(Protocol):
    """What rules need from the library (implemented by `didact.services.rules`)."""

    registry: Registry

    def roll(
        self, expression: str, reason: str, resolve: Resolver, faces: list[int] | None = None
    ) -> RollDone: ...
    def record(self, ref: str, of: str | None = None) -> str: ...  # its id (`of`: a type)
    def values(self, record_id: str) -> dict[str, Value]: ...
    def set_field(self, record_id: str, key: str, op: str, value: Value) -> FieldSet: ...
    def unset_field(self, record_id: str, key: str) -> FieldSet: ...  # set --unset
    def make(self, spec: dict[str, JSON], rule: Rule) -> EntityDone: ...  # a record, at once
    def give(self, record_id: str, item: str, data: dict[str, JSON]) -> ItemDone: ...  # inv add
    def take(self, record_id: str, item: str, count: int | None) -> ItemDone: ...  # inv drop
    def use(self, record_id: str, item: str, spend: int) -> UseDone: ...  # inv use
    def item(  # one item carried, and the keys asked of it (`Iron Sword.damage`)
        self, record_id: str, field: str, path: str
    ) -> tuple[dict[str, JSON], tuple[str, ...]] | None: ...
    def table(self, ref: str, inputs: dict[str, Value], reason: str) -> TableDone: ...
    def rule(self, ref: str, from_pack: str) -> Rule: ...
    def settings(self, pack: str) -> dict[str, JSON]: ...
    def option(self, name: str) -> JSON: ...  # a campaign's option (`@option.lethality`)
    def now(self) -> dict[str, Value]: ...  # where play stands: `@session`, `@time.day`, …
    def party(self, pcs: bool) -> list[str]: ...  # its members' ids (`pcs`: its PCs only)
    def pool(
        self, record_id: str, *, roll: bool, drop: int, extra: int, reason: str
    ) -> PoolDone: ...  # a tracker's diminishing pool
    def remind(self, text: str, after: str | None, every: str | None) -> str: ...  # a reminder
    def oracle_state(self, rule: Rule) -> str | None: ...  # the state record its `oracle` reads


# ---------------------------------------------------------------------------- a run


PATH = ">"  # on a draft's trail, `<name>>` after a table roll's value: the entries it took


@dataclass(slots=True)
class Given:
    """Decisions made in advance, used instead of rolling or choosing (drafts).

    - `trail`: what an earlier run of the same draft rolled or chose. Each value is used once,
      in order, so a resumed draft replays exactly. A table roll that went on to other tables
      left its path beside its value (`paths`); `path` is the one of the value taken last.
    - `prefill`: decisions given up front, used once the trail runs out. A single value answers
      every occurrence; a list answers one occurrence each, then the dice take over.
    """

    trail: dict[str, list[Value]] = field(default_factory=dict)
    prefill: dict[str, Value] = field(default_factory=dict)
    spent: dict[str, int] = field(default_factory=dict)  # list items used, per name
    paths: dict[str, list[Value | None]] = field(default_factory=dict)  # one per trail value
    path: Value | None = None

    @classmethod
    def build(cls, trail: list[tuple[str, Value]], prefill: Mapping[str, Value]) -> Given:
        queues: dict[str, list[Value]] = {}
        paths: dict[str, list[Value | None]] = {}
        for name, value in trail:
            base = name.removesuffix(PATH)
            if base != name and paths.get(base):  # the path of the value before it
                paths[base][-1] = value
                continue
            queues.setdefault(name, []).append(value)
            paths.setdefault(name, []).append(None)
        spent = {  # the trail starts with the list items an earlier run already used
            name: min(len(value), len(queues.get(name, [])))
            for name, value in prefill.items()
            if isinstance(value, list)
        }
        return cls(queues, dict(prefill), spent, paths)

    def __contains__(self, name: str) -> bool:
        return bool(self.trail.get(name)) or self._prefilled(name) is not None

    def prefilled(self, name: str) -> bool:
        """Whether the next value of `name` is the prefill's: the trail has none left."""
        return not self.trail.get(name) and self._prefilled(name) is not None

    def take(self, name: str) -> Value | None:
        queue = self.trail.get(name)
        if queue:
            return self._next(name, queue)
        self.path = None
        value = self._prefilled(name)
        if value is not None and isinstance(self.prefill.get(name), list):
            self.spent[name] = self.spent.get(name, 0) + 1
        return value

    def take_whole(self, name: str) -> Value | None:
        """A pick of several at once: the trail's answer, or a whole prefilled list."""
        queue = self.trail.get(name)
        if queue:
            return self._next(name, queue)
        self.path = None
        value = self.prefill.get(name)
        if isinstance(value, list):
            if self.spent.get(name, 0):
                return None
            self.spent[name] = len(value)
            return ", ".join(str(v) for v in value)
        return value

    def _next(self, name: str, queue: list[Value]) -> Value:
        """The trail's next value of `name`, its path kept as `path`."""
        paths = self.paths.get(name)
        self.path = paths.pop(0) if paths else None
        return queue.pop(0)

    def _prefilled(self, name: str) -> Value | None:
        value = self.prefill.get(name)
        if not isinstance(value, list):
            return value
        used = self.spent.get(name, 0)
        return value[used] if used < len(value) else None


def answered(name: str, value: Value, options: list[str]) -> Value:
    """A prefilled choice as the option it names, as written or in another letter case; else
    an answer of one's own, which brings no entry data. One close to an option but none of them
    is taken for a slip: refused, naming the nearest."""
    text = str(value)
    if not options or text in options:
        return value
    folded = {option.casefold(): option for option in options}
    if text.casefold() in folded:
        return folded[text.casefold()]
    close = difflib.get_close_matches(text.casefold(), list(folded), n=3)
    if close:
        raise InvalidError(
            _("prefilled {name} {value} isn't one of its options", name=name, value=repr(text)),
            hint=_("did you mean {names}?", names=", ".join(folded[c] for c in close)),
        )
    return value


@dataclass(slots=True)
class Run:
    """What a rule did: lines to show, the outcome, prompts, and bound values."""

    rule: str
    params: dict[str, Value] = field(default_factory=dict)
    lines: list[str] = field(default_factory=list)
    outcome: str | None = None
    flags: list[str] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)
    rolls: list[str] = field(default_factory=list)
    bound: dict[str, Value] = field(default_factory=dict)
    faces: dict[str, list[int]] = field(default_factory=dict)  # per named roll, for rerolls
    exprs: dict[str, str] = field(default_factory=dict)
    options: dict[str, str] = field(default_factory=dict)  # pending: name → label
    stopped: str | None = None
    stopped_by_option: bool = False  # the `stop:` sat under an `if:` reading `@option.…`
    guards: int = 0  # how many `if:` branches reading an option it is in, now
    changed: bool = False
    skipped: bool = False  # a trigger whose `when` was false
    given: Given = field(default_factory=Given)  # decided in advance (drafts)
    trail: list[tuple[str, Value]] = field(default_factory=list)  # every rolled or chosen value
    paths: dict[str, Value] = field(default_factory=dict)  # a table roll's path, by its name
    records: dict[str, str] = field(default_factory=dict)  # names a step bound to a record
    unread: set[str] = field(default_factory=set)  # data keys holding what values can't hold
    extra: dict[str, object] = field(default_factory=dict)  # state for extra step kinds

    def to_data(self) -> dict[str, JSON]:
        data: dict[str, JSON] = {
            "rule": self.rule,
            "params": {k: to_json(v) for k, v in self.params.items()},
            "outcome": self.outcome,
            "flags": list[JSON](self.flags),
            "rolls": list[JSON](self.rolls),
            "values": {k: to_json(v) for k, v in self.bound.items()},
            "prompts": list[JSON](self.prompts),
            "lines": list[JSON](self.lines),
        }
        if self.options:
            data["pending"] = dict[str, JSON](self.options)
        return data


type StepHandler = Callable[[Scope, dict[str, JSON]], bool]  # True: it handled the step


class Engine:
    def __init__(self, host: Host, handlers: Mapping[str, StepHandler] | None = None) -> None:
        self.host = host
        self.handlers = dict(handlers or {})  # extra step kinds (drafts: entity, choose, …)

    # ------------------------------------------------------------------ entry points

    def run(
        self,
        rule: Rule,
        args: Mapping[str, str],
        *,
        depth: int = 0,
        preset: Mapping[str, Value] | None = None,
        given: Given | None = None,
        extra: Mapping[str, object] | None = None,
    ) -> Run:
        """Run a rule. `preset` values are readable from the start (e.g. `@time.day`); `given`
        values are used instead of rolling or choosing (drafts); `extra` is for step handlers."""
        if depth > MAX_DEPTH:
            raise InvalidError(
                _(
                    "rules call each other more than {depth} deep at {rule}",
                    depth=MAX_DEPTH,
                    rule=rule.id,
                ),
                hint=_("a rule that ends up calling itself: check its `do` steps"),
            )
        run = Run(rule.id)
        run.bound.update(preset or {})
        run.given = given or Given()
        run.extra = dict(extra or {})
        if "oracle" in rule.params and "oracle" not in args:  # its oracle's state, wherever run
            state = self.host.oracle_state(rule)
            if state is not None:
                args = {**args, "oracle": state}
        texts = self._bind(rule, args, run)
        scope = Scope(self, rule, run, texts, depth)
        match rule.kind:
            case "check":
                self._check(scope)
            case "generator" | "chargen":
                scope.steps(rule.data.get("steps"))
            case "trigger":
                when = rule.data.get("when")
                if isinstance(when, str) and not truthy(scope.eval(when)):
                    run.lines.append(
                        _("{rule}: not now ({when} is false)", rule=rule.id, when=when)
                    )
                    run.skipped = True
                    return run
                scope.steps(rule.data.get("steps"))
            case _:
                prompt = rule.data.get("prompt")
                if isinstance(prompt, str):
                    scope.prompt(prompt)
                scope.steps(rule.data.get("steps"))
        return run

    def resolve(self, rule: Rule, saved: dict[str, JSON], option: str) -> Run:
        """Finish a pending check with one of its options (or `accept`)."""
        run = Run(rule.id)
        texts = {k: str(v) for k, v in cast(dict[str, JSON], saved.get("texts") or {}).items()}
        run.params = {
            k: cast(Value, v) for k, v in cast(dict[str, JSON], saved.get("params") or {}).items()
        }
        run.bound = {
            k: cast(Value, v) for k, v in cast(dict[str, JSON], saved.get("bound") or {}).items()
        }
        run.records = {
            k: str(v) for k, v in cast(dict[str, JSON], saved.get("records") or {}).items()
        }
        run.faces = {
            k: [int(x) for x in cast(list[int], v)]
            for k, v in cast(dict[str, JSON], saved.get("faces") or {}).items()
        }
        run.exprs = {k: str(v) for k, v in cast(dict[str, JSON], saved.get("exprs") or {}).items()}
        run.rolls = [str(r) for r in cast(list[JSON], saved.get("rolls") or [])]
        scope = Scope(self, rule, run, texts, 0)
        options = cast(dict[str, JSON], rule.data.get("options") or {})
        if option != "accept":
            chosen = options.get(option)
            if not isinstance(chosen, dict):
                known = ", ".join([*options, "accept"])
                raise InvalidError(
                    _("{rule} has no option {option}", rule=rule.id, option=repr(option)),
                    hint=_("options: {options}", options=known),
                )
            when = chosen.get("when")
            if isinstance(when, str) and not truthy(scope.eval(when)):
                raise InvalidError(
                    _("{option} isn't possible now ({when} is false)", option=option, when=when),
                    hint=_("pick another option"),
                )
            run.lines.append(f"{option}: {option_label(option, str(chosen.get('label', option)))}")
            scope.steps(chosen.get("steps"))
        self._outcome(scope)
        self._effects(scope)
        return run

    # ------------------------------------------------------------------ binding parameters

    def _bind(self, rule: Rule, args: Mapping[str, str], run: Run) -> dict[str, str]:
        params = rule.params
        unknown = sorted(set(args) - set(params))
        if unknown:
            raise InvalidError(
                _("{rule} has no parameter {name}", rule=rule.id, name=repr(unknown[0])),
                hint=_("usage: {usage}", usage=rule.usage()),
            )
        texts: dict[str, str] = {}
        for name, param in params.items():
            raw = args.get(name)
            if raw is None and param.default is not None:
                raw = str(param.default)
            if raw is None:
                if param.optional:  # not given: `$name` reads as empty text, `@name` is unset
                    texts[name] = ""
                    continue
                raise InvalidError(
                    _("{rule} needs {name}", rule=rule.id, name=name),
                    hint=_("usage: {usage}", usage=rule.usage()),
                )
            value, text = self._convert(rule, param, raw)
            run.params[name] = value
            texts[name] = text
        return texts

    def _convert(self, rule: Rule, param: Param, raw: str) -> tuple[Value, str]:
        match param.kind:
            case "ref":
                record = self.host.record(raw, param.to)  # by name: only records of its type
                if param.to and record.partition(":")[0] != param.to:
                    raise InvalidError(
                        _(
                            "{name} must be a {type}, not {record}",
                            name=param.name,
                            type=param.to,
                            record=record,
                        ),
                        hint=_("name a {type} record", type=param.to),
                    )
                return record, record
            case "enum":
                found = next((v for v in param.values if v.casefold() == raw.casefold()), None)
                if found is None:
                    raise InvalidError(
                        _(
                            "{name} must be one of: {values}",
                            name=param.name,
                            values=", ".join(param.values),
                        ),
                        hint=_("e.g. {example}", example=f"{param.name}={param.values[0]}")
                        if param.values
                        else None,
                    )
                return found, found
            case "int" | "number":
                try:
                    number: Value = int(raw) if param.kind == "int" else float(raw)
                except ValueError:
                    raise InvalidError(
                        _("{name} must be a number, not {raw}", name=param.name, raw=repr(raw)),
                        hint=_("e.g. {example}", example=f"{param.name}=2"),
                    ) from None
                return number, str(number)
            case "flag":
                flag = raw.strip().lower() in ("1", "true", "yes", "on")
                return flag, "true" if flag else "false"
            case "dice":
                try:
                    parse(raw, self.host.registry)
                except DidactError as exc:
                    raise InvalidError(f"{param.name}: {exc.message}", hint=exc.hint) from exc
                return raw, raw
            case _:
                return raw, raw

    # ------------------------------------------------------------------ checks

    def _check(self, scope: Scope) -> None:
        data = scope.rule.data
        prompt = data.get("prompt")
        if isinstance(prompt, str):
            scope.prompt(prompt)
        scope.steps(data.get("before"))  # look a chart up, or roll by a method, first
        roll = data.get("roll")
        if roll is not None and scope.run.stopped is None:  # a `before:` that stops rolls nothing
            rolls = roll if isinstance(roll, dict) else {"roll": roll}
            for name, expression in rolls.items():
                scope.roll(str(expression), name)
        if scope.run.stopped is not None:
            return
        self._outcome(scope)
        options = data.get("options")
        if isinstance(options, dict) and options:
            for name, option in options.items():
                when = option.get("when") if isinstance(option, dict) else None
                if isinstance(when, str) and not truthy(scope.eval(when)):
                    continue
                label = option.get("label", name) if isinstance(option, dict) else name
                scope.run.options[name] = scope.text(str(label))
            if scope.run.options:
                scope.run.options["accept"] = ACCEPT
                return  # pending: `didact resolve` finishes it
        self._effects(scope)

    def _outcome(self, scope: Scope) -> None:
        data, run = scope.rule.data, scope.run
        outcome: str | None = None
        auto = data.get("auto")
        natural = run.bound.get("roll.natural")
        if isinstance(auto, dict) and natural is not None:
            found = auto.get(str(natural))
            if isinstance(found, str):
                outcome = found
                run.lines.append(_("natural {roll}: {outcome}", roll=show(natural), outcome=found))
        if outcome is None:
            bands = data.get("bands")
            if isinstance(bands, dict):
                for name, condition in bands.items():
                    if condition == "else" or truthy(scope.eval(str(condition))):
                        outcome = name
                        break
            elif isinstance(data.get("success"), str):
                outcome = "success" if truthy(scope.eval(str(data["success"]))) else "failure"
        run.outcome = outcome
        flags = data.get("flags")
        run.flags = [
            name
            for name, cond in (flags.items() if isinstance(flags, dict) else [])
            if truthy(scope.eval(str(cond)))
        ]
        run.bound["outcome"] = outcome or ""
        run.bound["flags"] = list[Value](run.flags)  # a caller reads `@answer.flags`
        if outcome is not None:
            flagged = f" ({', '.join(run.flags)})" if run.flags else ""
            run.lines.append(f"→ {outcome}{flagged}")

    def _effects(self, scope: Scope) -> None:
        on = scope.rule.data.get("on")
        if isinstance(on, dict) and scope.run.outcome is not None:
            scope.steps(on.get(scope.run.outcome))
            for flag in scope.run.flags:
                scope.steps(on.get(flag))


def in_text(value: Value) -> str:
    """A value in a message: text as it is, a list as its items ("fire, orb"), else as an
    expression writes it."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ", ".join(in_text(v) for v in value)
    return show(value)


def _dice_set(text: str) -> bool:
    """Whether a roll's `{…}` holds a set of rolls (`d8, d6`): a comma outside any brackets."""
    depth, quote = 0, ""
    for char in text:
        if quote:
            quote = "" if char == quote else quote
        elif char in "'\"":
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            return True
    return False


def _reads_as_dice(text: str, registry: Registry) -> bool:
    """Whether a value's text is dice or a number to roll (`d8`, `2d6+1`, `3`), not a word."""
    try:
        node = parse(text, registry)
    except DidactError:
        return False
    return not isinstance(node, Bool | Text)


@dataclass(slots=True)
class Scope:
    engine: Engine
    rule: Rule
    run: Run
    texts: dict[str, str]
    depth: int

    @property
    def host(self) -> Host:
        return self.engine.host

    # ------------------------------------------------------------------ values

    def resolve(self, path: str) -> Value | None:
        head, dot, rest = path.partition(".")
        bound = self.run.bound
        if path in bound:
            return bound[path]
        if path in self.run.unread:  # there, but not a value: say how to pass it
            raise UnknownName(
                _("@{path} holds mappings, which an expression can't read", path=path),
                what="variable",  # (as absent: `default(…)` still gives its fallback)
                hint=_("hand it to a step as it is: {example}", example=f'`apply: "@{path}"`'),
            )
        if rest.startswith("symbols.") and head in self.run.exprs:
            return 0  # a symbol the roll didn't show: none of it (after cancelling)
        record = self.run.records.get(head)  # a loop's member or a record made: read like a ref
        if record is None and head in self.run.params:
            value = self.run.params[head]
            param = self.rule.params.get(head)
            if param is None or param.kind != "ref" or not isinstance(value, str):
                return value if not dot else None
            record = value
        if record is not None:
            if not dot:
                return record
            found = self.host.values(record)
            if rest in found:
                return found[rest]
            folded = {k.casefold(): v for k, v in found.items()}.get(rest.casefold())
            slots, _sep, inner = rest.partition(".")
            if folded is None and inner and f"{slots}.used" in found:
                name, _sep, key = inner.partition(".")
                if key and f"{slots}.{name}.used" not in found:  # not a group: one item's key
                    return self._carried(record, slots, inner)
                return []  # a column no item has (`@who.inventory.armor`): an empty list
            return folded
        if head == "option" and dot:
            chosen = self.host.option(rest)
            return None if isinstance(chosen, dict | list) else chosen
        if head == "settings" and dot:
            raw: JSON = self.host.settings(self.rule.pack)
            for part in rest.split("."):  # nested settings: @settings.odds.likely
                raw = raw.get(part) if isinstance(raw, dict) else None
            if raw is None or isinstance(raw, dict | list):
                return None
            return raw
        if head in NOW:  # as a trigger reads them, without what only its event has
            return self.host.now().get(path)
        return None

    def _carried(self, record: str, slots: str, path: str) -> Value | None:
        """A key of one item a record carries (`@{who.inventory.$item.damage}`, the item named
        as `inv` names it, a dot in its name or not): `uses` and `charges` read as their count
        (`.max` too) or their usage die; an item or key that isn't there reads as absent
        (`default(…)` fills in)."""
        held = self.host.item(record, slots, path)
        if held is None or not held[1]:
            return None
        found: JSON = held[0]
        for part in held[1]:
            found = found.get(part) if isinstance(found, dict) else None
        if isinstance(found, dict):
            found = found.get("value", found.get("die"))  # {value, max}, or a usage die
        return from_json(found)

    def context(self) -> RollContext:
        from didact.expr import HashStream

        return RollContext(self.host.registry, HashStream("rules:no-dice"), {}, self.resolve)

    def eval(self, text: str) -> Value:
        """Evaluate a condition or value (no dice here: dice go through `roll` steps)."""
        expression = substitute(text, self.texts)
        ctx = self.context()
        try:
            result = evaluate(parse(expression, self.host.registry), ctx)
        except DidactError as exc:
            raise InvalidError(f"{self.rule.id}: `{text}`: {exc.message}", hint=exc.hint) from exc
        if ctx.draws:
            raise InvalidError(
                _("{rule}: `{text}` rolls dice", rule=self.rule.id, text=text),
                hint=_("roll in a `roll:` step and use its name"),
            )
        return result.value

    def text(self, template: str) -> str:
        """Fill `{expression}` placeholders in a message: `{@who.name} takes {@dealt}`. `{{` and
        `}}` write a brace itself: `--prefill '{{"name": "Wren"}}'`."""

        def replace(match: re.Match[str]) -> str:
            if match.group(1) is None:  # a brace, or an `@{…}` outside any `{…}`: as written
                return match.group() if match.group().startswith("@") else match.group()[0]
            return in_text(self.eval(match.group(1)))

        return _BRACES.sub(replace, substitute(template, self.texts))

    def filled(self, raw: JSON) -> JSON:
        """A step's value as a draft's steps read it (and `entity:` or `give:` in any rule),
        through lists and mappings: `@name` and a lone `{expression}` are worked out (numbers
        stay numbers), other text is filled in, and anything else is taken as written."""
        if isinstance(raw, str):
            stripped = raw.strip()
            plain = "{" not in stripped and " " not in stripped
            whole = plain or _VARIABLE.fullmatch(stripped) is not None
            if stripped.startswith("@") and whole:
                return to_json(self.eval(stripped))
            if lone := _LONE.fullmatch(stripped):
                return to_json(self.eval(lone.group(1)))
            return self.text(raw)
        if isinstance(raw, list):
            return [self.filled(item) for item in raw]
        if isinstance(raw, dict):
            return {str(k): self.filled(v) for k, v in raw.items()}
        return raw

    # ------------------------------------------------------------------ doing things

    def roll(self, expression: str, name: str, faces: list[int] | None = None) -> RollDone:
        text = substitute(self._filled(expression), self.texts)
        self._not_text(text, expression)
        named = {**self.run.params, **self.run.records}  # a loop's member: whose roll it is
        who = ", ".join(f"{k}={show(v) if not isinstance(v, str) else v}" for k, v in named.items())
        reason = f"{self.rule.id} ({who}): {name}" if who else f"{self.rule.id}: {name}"
        done = self.host.roll(text, reason, self.resolve, faces)
        self.run.rolls.append(done.label)
        self.run.lines.append(done.line)
        self.run.exprs[name] = text
        self.run.faces[name] = done.faces
        bound = self.run.bound
        bound[name] = done.total
        bound[f"{name}.dice"] = list[Value](done.dice)
        bound[f"{name}.flags"] = list[Value](done.flags)
        for index, die in enumerate(done.dice):
            bound[f"{name}.{index}"] = die
        for part, value in done.parts.items():
            bound[f"{name}.{part}"] = value
        for symbol, count in done.symbols.items():
            bound[f"{name}.symbols.{symbol}"] = count
        if done.dice:
            bound[f"{name}.natural"] = done.dice[0] if len(done.dice) == 1 else done.total
        return done

    def _filled(self, expression: str) -> str:
        """A roll's `{…}` filled in before it is read, as in any text, so a rule rolls the dice
        it holds as text (`roll: "{@d} + 1"`, `roll: "{@{who.inventory.$item.damage}}"`): the
        log shows the dice. A set of one roll (`{2d6}`) stays dice; a value that is neither
        dice nor a number is refused, naming it (`_ROLL_FILL`)."""

        def fill(match: re.Match[str]) -> str:
            inner = match.group(1)
            if inner is None or _dice_set(inner):
                return match.group(0)
            ctx = self.context()
            try:
                result = evaluate(parse(substitute(inner, self.texts), self.host.registry), ctx)
            except DidactError as exc:
                absent = isinstance(exc, UnknownName) and exc.what == "variable"
                hint = (
                    _("it isn't there: give it a fallback, e.g. {example}",
                      example=f"`{{default({inner.strip()}, 'd4')}}`")
                    if absent else exc.hint
                )  # fmt: skip
                said = f"{self.rule.id}: `{{{inner}}}`: {exc.message}"
                raise InvalidError(said, hint=hint) from exc
            if ctx.draws:  # dice already: a set of one roll
                return match.group(0)
            found = result.value
            text = in_text(found)
            if isinstance(found, bool) or not _reads_as_dice(text, self.host.registry):
                raise InvalidError(
                    _("{rule}: `{part}` is {value}, not dice", rule=self.rule.id,
                      part=match.group(0), value=repr(text)),
                    hint=_("give it a die or a number to roll, e.g. {example}",
                           example="`d8`, `2d6`, `3`"),
                )  # fmt: skip
            return text if _ATOM.fullmatch(text) else f"({text})"

        return _ROLL_FILL.sub(fill, expression)

    def _not_text(self, text: str, expression: str) -> None:
        """A roll that rolls nothing and comes out as dice written as text (`roll: "@d"`, @d
        being 'd8') is refused, with the way to roll them: `{@d}`."""
        if "@" not in text:
            return
        ctx = self.context()
        try:
            found = evaluate(parse(text, self.host.registry), ctx).value
        except DidactError:
            return  # the roll itself says what's wrong
        if ctx.draws or not isinstance(found, str) or not _reads_as_dice(found, self.host.registry):
            return
        raise InvalidError(
            _("{rule}: `{expression}` is the text {value}, which rolls nothing",
              rule=self.rule.id, expression=expression, value=repr(found)),
            hint=_("to roll the dice it holds, put it in braces: {example}",
                   example=f"`{{{expression.strip()}}}`"),
        )  # fmt: skip

    def table(self, step: dict[str, JSON]) -> str:
        """Roll a table step (or take its given value); binds the text and the entry's data.
        The table may be computed (`setting-{@drop.difficulty}-terrain`). `times: n` rolls n
        results (`distinct: true`: rerolling repeats) and binds them as a list."""
        name = str(step.get("as", "table"))
        ref = self.text(str(step["table"]))
        if "times" not in step:
            return self._table_once(step, name, ref)
        raw = step["times"]
        count = self.eval(raw) if isinstance(raw, str) else raw
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise InvalidError(
                _(
                    "{rule}: `times` needs a whole number, not {raw}",
                    rule=self.rule.id,
                    raw=repr(raw),
                ),
                hint=_("check the pack: `didact pack validate {pack}`", pack=self.rule.pack),
            )
        picked: list[str] = []
        for _try in range(count * 10 + 10):  # rerolled repeats count as tries
            if len(picked) >= count:
                break
            text = self._table_once(step, name, ref)
            if step.get("distinct") is True and text in picked:
                continue
            picked.append(text)
        if len(picked) < count:
            self.run.lines.append(
                ngettext(
                    "{table}: only {n} different result",
                    "{table}: only {n} different results",
                    len(picked),
                    table=ref,
                )
            )
        self.run.bound[name] = list[Value](picked)
        return ", ".join(picked)

    def _table_once(self, step: dict[str, JSON], name: str, ref: str) -> str:
        prefilled = self.run.given.prefilled(name)
        if self.given(name):  # a draft replaying, or a prefill: the entry's data comes too
            if prefilled:
                self.settle(name, [], ref)
            self.onward(name, ref)
            text = str(self.run.bound[name])
            lookup = self.run.extra.get("entry_data")
            data = lookup(ref, text, self.run.paths.get(name)) if callable(lookup) else None
            if isinstance(data, dict):
                self.bind_data(name, cast(dict[str, JSON], data))
            return text
        inputs = {
            key: self._input(raw)
            for key, raw in cast(dict[str, JSON], step.get("with") or {}).items()
        }
        done = self.host.table(ref, inputs, self.rule.id)
        self.run.rolls.append(done.label)
        self.run.lines.append(f"{done.label} {ref}: {done.text}")
        self.keep(name, done.text)
        if done.path:
            self.went(name, done.path)
        self.bind_data(name, done.data)
        return done.text

    def settle(self, name: str, options: list[str], table: str = "") -> None:
        """A prefilled choice as the option it names (`answered`), and a table's entry as the
        draft finds it (by its `id` or a roll too, or further down: its `prefilled`), kept as a
        roll keeps it; one further down that goes on rolls on from there (`_rolled_on`)."""
        given = self.run.bound[name]
        named = self.run.extra.get("prefilled")
        path: Value | None = None
        folded = {option.casefold() for option in options}
        if table and callable(named) and str(given).casefold() not in folded:
            value, path = cast(tuple[Value, Value | None], named(table, name, given))
        else:
            value = answered(name, given, options)
        if value != given:
            self.run.bound[name] = value
            self.run.trail[-1] = (name, value)
            self.run.lines[-1] = _("{name}: {value} (given)", name=name, value=in_text(value))
        if isinstance(path, list) and path:
            *way, (inner, entry) = cast(list[list[Value]], path)
            more = self._rolled_on(str(inner), str(value), str(entry))
            self.went(name, list[Value]([*way, *more]) if isinstance(more, list) else path)

    def onward(self, name: str, table: str) -> None:
        """A table's entry given or chosen, not rolled, that goes on (`then:`, or a table
        instead): what it goes on to is rolled now, as when a roll lands on it, and the path
        kept, so that a draft replays it (the drafts' `onward`)."""
        if self.run.paths.get(name) is not None:
            return
        path = self._rolled_on(table, str(self.run.bound[name]))
        if path is not None:
            self.went(name, path)

    def _rolled_on(self, table: str, text: str, entry: str | None = None) -> Value | None:
        """What a table's entry (by its text, or its label) goes on to, rolled now by the
        drafts' `onward`, its lines and rolls kept: the path it took, from that entry on. None:
        it doesn't go on."""
        roll = self.run.extra.get("onward")
        done = roll(table, text, entry) if callable(roll) else None
        if done is None:
            return None
        path, lines, rolls = cast(tuple[Value, list[str], list[str]], done)
        self.run.lines.extend(lines)
        self.run.rolls.extend(rolls)
        return path

    def _input(self, raw: JSON) -> Value:
        """A `with:` value for a table: `@…` is evaluated, `$param` filled in, else as is."""
        if isinstance(raw, str) and "@" in raw:
            return self.eval(raw)
        if isinstance(raw, str) and "$" in raw:
            return substitute(raw, self.texts)
        return cast(Value, raw)

    def pick(self, step: dict[str, JSON]) -> None:
        """Roll on a list value (an oracle's Threads): `pick: "@oracle.threads"`, `method:`
        sections | uniform, `as: thread`. Binds the entry ("" when blank or empty), and
        `@thread.choose` / `@thread.empty` / `@thread.line`."""
        from didact.tables import lists

        name = str(step.get("as", "pick"))
        if self.given(name):
            return
        raw = self.eval(str(step["pick"]))
        entries = [str(e) for e in raw] if isinstance(raw, list) else []
        method = str(step.get("method", "uniform"))
        if method not in lists.METHODS:
            raise InvalidError(
                _(
                    "{rule}: pick method is one of {methods}",
                    rule=self.rule.id,
                    methods=", ".join(lists.METHODS),
                ),
                hint=_("check the pack: `didact pack validate {pack}`", pack=self.rule.pack),
            )
        dice = lists.dice_for(len(entries), method)
        labels = ["section", "line"][-len(dice) :] if dice else []
        faces = [
            int(cast(int, self.roll(die, f"{name}: {what}").total))
            for die, what in zip(dice, labels, strict=True)
        ]
        found = lists.pick(entries, method, faces)
        self.keep(name, found.entry or "")
        self.run.bound[f"{name}.choose"] = found.choose
        self.run.bound[f"{name}.empty"] = not entries
        self.run.bound[f"{name}.line"] = found.line or 0
        shown = found.entry or (pgettext("list", "choose") if found.choose else _("nothing listed"))
        self.run.lines.append(f"{name}: {found.how} → {shown}")

    def bind_data(self, name: str, data: dict[str, JSON]) -> None:
        """A table entry's data as `@name.key` (text, numbers, flags and lists of them; a list
        of items, `[Rope, {name: Laser, damage: d8}]`, as their names, as an inventory reads),
        and a mapping's by their path (`@name.pool.dice`). A step handed `@name.key` as it is
        still gets the data itself (the items, damage and all). What an earlier entry bound under
        the same name goes first, so a loop never reads stale data."""
        for stale in [k for k in self.run.bound if k.startswith(f"{name}.")]:
            del self.run.bound[stale]
        self.run.unread = {k for k in self.run.unread if not k.startswith(f"{name}.")}
        for key, item in data.items():
            if isinstance(item, dict):
                self.bind_data(f"{name}.{key}", item)
            elif isinstance(item, bool | int | float | str):
                self.run.bound[f"{name}.{key}"] = item
            elif isinstance(item, list) and all(
                isinstance(i, bool | int | float | str) for i in item
            ):
                self.run.bound[f"{name}.{key}"] = cast(list[Value], item)
            elif isinstance(item, list) and all(_named(i) for i in item):
                names = [
                    i if isinstance(i, str) else str(cast(dict[str, JSON], i)["name"]) for i in item
                ]
                self.run.bound[f"{name}.{key}"] = list[Value](names)
            elif isinstance(item, list):  # mappings without names: a step's to read, not a sum's
                self.run.unread.add(f"{name}.{key}")

    def prompt(self, text: str, kind: str = "prompt") -> None:
        filled = self.text(text)
        self.run.prompts.append(filled)
        if kind == "reminder":
            self.run.lines.append(_("reminder: {text}", text=filled))
        else:
            self.run.lines.append(_("prompt: {text}", text=filled))

    def steps(self, steps: JSON) -> None:
        for step in steps if isinstance(steps, list) else []:
            if self.run.stopped is not None:
                return
            self.step(step)

    def given(self, name: str, *, whole: bool = False) -> bool:
        """Use a value decided in advance (a draft's trail or prefill) instead of rolling."""
        value = self.run.given.take_whole(name) if whole else self.run.given.take(name)
        if value is None:
            return False
        self.keep(name, value)
        if self.run.given.path is not None:
            self.went(name, self.run.given.path)
        given = value if isinstance(value, str) else show(value)
        self.run.lines.append(_("{name}: {value} (given)", name=name, value=given))
        return True

    def keep(self, name: str, value: Value) -> None:
        """Bind a rolled or chosen value and note it on the trail (drafts replay from it)."""
        self.run.bound[name] = value
        self.run.trail.append((name, value))
        self.run.paths.pop(name, None)

    def went(self, name: str, path: Value) -> None:
        """Note the entries the table roll just kept as `name` took (its `path`): beside its
        value on the trail, so that a draft replays their data too."""
        self.run.paths[name] = path
        self.run.trail.append((name + PATH, path))

    def step(self, step: JSON) -> None:
        if isinstance(step, str):
            self.run.lines.append(self.text(step))
            return
        if not isinstance(step, dict):
            raise InvalidError(
                _("{rule}: can't run step {step}", rule=self.rule.id, step=repr(step)),
                hint=_("check the pack: `didact pack validate {pack}`", pack=self.rule.pack),
            )
        for key, handler in self.engine.handlers.items():
            if key in step and handler(self, step):
                return
        if "roll" in step:
            name = str(step.get("as", "roll"))
            if self.given(name):
                return
            done = self.roll(str(step["roll"]), name)
            self.run.trail.append((name, done.total))
        elif "let" in step:
            for name, expression in cast(dict[str, JSON], step["let"]).items():
                if name in self.run.given and self.given(name):
                    continue  # a draft's prefill decides it (`--prefill '{"hp": 6}'`)
                self.run.bound[name] = self._value(expression)  # as `set` reads its value
        elif "set" in step:
            self._set(step)
        elif "unset" in step:
            self._unset(step)
        elif "entity" in step:
            self._make(step)
        elif "give" in step or "take" in step:
            self._carry(step)
        elif "use" in step:
            self._use(step)
        elif "check" in step:
            self._call(str(step["check"]), step, "check")
        elif "do" in step:
            self._call(str(step["do"]), step, None)
        elif "table" in step:
            self.table(step)
        elif "if" in step:
            condition = str(step["if"])
            branch = "then" if truthy(self.eval(condition)) else "else"
            guarded = _OPTION.search(condition) is not None  # a stop in it: the options say no
            self.run.guards += guarded
            try:
                self.steps(step.get(branch))
            finally:
                self.run.guards -= guarded
        elif "repeat" in step:
            self._repeat(step)
        elif "for" in step:
            self._for(step)
        elif "message" in step:
            self.run.lines.append(self.text(str(step["message"])))
        elif "prompt" in step:
            self.prompt(str(step["prompt"]))
        elif "reminder" in step:
            self.prompt(str(step["reminder"]), "reminder")
        elif "stop" in step:
            self.run.stopped = self.text(str(step["stop"]))
            self.run.stopped_by_option = self.run.guards > 0
            self.run.lines.append(_("stop: {text}", text=self.run.stopped))
        elif "reroll" in step:
            self._reroll(step)
        elif "pick" in step:
            self.pick(step)
        elif "pool" in step:
            self._pool(step)
        elif "remind" in step:
            after, every = step.get("in"), step.get("every")
            line = self.host.remind(
                self.text(str(step["remind"])),
                self.text(str(after)) if after is not None else None,
                self.text(str(every)) if every is not None else None,
            )
            self.run.changed = True
            self.run.lines.append(line)
        else:
            raise InvalidError(
                _("{rule}: unknown step {keys}", rule=self.rule.id, keys=sorted(step)),
                hint=_("`didact guide packs` lists the steps a rule can use"),
            )

    def _set(self, step: dict[str, JSON]) -> None:
        target = substitute(str(step["set"]), self.texts)  # `who.$attr`: the field named
        op, value_text = str(step.get("op", "=")), step.get("value")
        if value_text is None:
            match = _SET.match(target)
            if match is None:
                raise InvalidError(
                    _("{rule}: can't read `set: {target}`", rule=self.rule.id, target=target),
                    hint=_("e.g. `set: target.hp -= @damage`"),
                )
            target, op, value_text = match.group(1), match.group(2), match.group(3)
        holder, _dot, key = target.partition(".")
        record = self.run.records.get(holder, self.run.params.get(holder))
        if not isinstance(record, str) or not key:
            raise InvalidError(
                _(
                    "{rule}: `set: {target}` must name a record parameter and a field",
                    rule=self.rule.id,
                    target=target,
                ),
                hint=_("check the pack: `didact pack validate {pack}`", pack=self.rule.pack),
            )
        value = self._value(value_text)
        done = self.host.set_field(record, key, op, value)
        self.run.changed = True
        shown = value if isinstance(value, str) else show(value)
        note = f" ({done.note})" if done.note else ""
        self.run.lines.append(f"{record}: {key} {op} {shown}{note}")
        for ref in done.triggers:
            self._hook(ref, record)

    def _unset(self, step: dict[str, JSON]) -> None:
        """Remove a field as `didact set --unset` does (`unset: who.curse_timer`): a cured
        curse's timer, a switched-out talent's pool. One the record hasn't set changes nothing."""
        target = substitute(str(step["unset"]), self.texts)
        holder, _dot, key = target.partition(".")
        record = self.run.records.get(holder, self.run.params.get(holder))
        if not isinstance(record, str) or not key:
            raise InvalidError(
                _(
                    "{rule}: `unset: {target}` must name a record parameter and a field",
                    rule=self.rule.id,
                    target=target,
                ),
                hint=_("check the pack: `didact pack validate {pack}`", pack=self.rule.pack),
            )
        done = self.host.unset_field(record, key)
        self.run.changed = True
        note = f" ({done.note})" if done.note else ""
        self.run.lines.append(f"{record}: " + _("unset {key}", key=key) + note)
        for ref in done.triggers:
            self._hook(ref, record)

    def _hook(self, ref: str, record: str) -> None:
        """Run a trigger a field hook fired (`on_zero: {trigger: death}`) for `record`."""
        try:
            rule = self.host.rule(ref, self.rule.pack)
        except DidactError:
            self.run.lines.append("  " + _("hook: there's no rule {rule} to run", rule=repr(ref)))
            return
        args = {"who": record} if "who" in rule.params else {}
        preset = {**self._now(), "hook.record": record}
        inner = self.engine.run(rule, args, depth=self.depth + 1, preset=preset)
        self.run.lines.extend(f"  {line}" for line in inner.lines)
        self.run.prompts.extend(inner.prompts)
        self.run.rolls.extend(inner.rolls)

    def _now(self) -> dict[str, Value]:
        """Where play stands as this rule was given it (by an event), for a rule it runs."""
        return {k: v for k, v in self.run.bound.items() if k.partition(".")[0] in NOW}

    def _value(self, raw: JSON) -> Value:
        """A `set` or `let` value (see `is_text`); anything else is an expression."""
        if not isinstance(raw, str):
            return cast(Value, raw)
        text = raw.strip()
        param = _PARAM.fullmatch(text)
        if param and param.group(1) in self.texts:
            return self.texts[param.group(1)]
        if "{" in _VARIABLE.sub("", text):  # `@{…}` is a variable of the expression
            return self.text(text)
        if _BARE_WORD.fullmatch(text):
            return text
        if "$" in text and "@" not in text:  # "Does $npc $action?" is text; "$n + 1" a sum
            filled = substitute(text, self.texts)
            try:
                return self.eval(filled)
            except InvalidError:
                return filled
        return self.eval(text)

    def _call(self, ref: str, step: dict[str, JSON], kind: str | None) -> None:
        rule = self.host.rule(substitute(ref, self.texts), self.rule.pack)
        if kind and rule.kind != kind:
            raise InvalidError(
                _("{rule} is a {kind}, not a {wanted}", rule=rule.id, kind=rule.kind, wanted=kind),
                hint=_("check the pack: `didact pack validate {pack}`", pack=self.rule.pack),
            )
        args: dict[str, str] = {}
        for name, raw in cast(dict[str, JSON], step.get("with") or {}).items():
            if isinstance(raw, str) and any(c in raw for c in "@${"):
                value = self._value(raw)  # `@who`, `@days - 1`, `$odds`, "Does {@npc} flee?"
                args[name] = value if isinstance(value, str) else show(value)
            else:
                args[name] = str(raw)
        inner = self.engine.run(rule, args, depth=self.depth + 1, preset=self._now())
        self.run.lines.extend(f"  {line}" for line in inner.lines)
        self.run.prompts.extend(inner.prompts)
        self.run.rolls.extend(inner.rolls)
        self.run.changed = self.run.changed or inner.changed
        if inner.stopped is not None and not step.get("go_on"):
            self.run.stopped = inner.stopped  # a refusal inside stops the rule that asked
            self.run.stopped_by_option = inner.stopped_by_option or self.run.guards > 0
        name = str(step.get("as", rule.id.rpartition(".")[2]))
        self.run.bound[name] = inner.outcome or ""
        for key, value in inner.bound.items():
            self.run.bound[f"{name}.{key}"] = value

    def _pool(self, step: dict[str, JSON]) -> None:
        """Roll a tracker's diminishing pool (`pool: "@quarry"`: 1-3s drop; `drop: 1` first,
        `extra: "@spark"` dice roll along), or only drop dice from it (`mode: drop`: a push, a
        tick). Linked phases and a pool's event work as `didact track roll`. Binds
        `@<as>.highest`, `.dropped`, `.left`, `.empty` and `.faces` (`as:` defaults to pool)."""
        text = substitute(str(step["pool"]), self.texts)
        ref = self._value(text) if text.startswith("@") else text
        record = self.host.record(str(ref))
        mode = str(step.get("mode", "roll"))
        if mode not in ("roll", "drop"):
            raise InvalidError(
                _("{rule}: a pool step's mode is roll or drop", rule=self.rule.id),
                hint=_("check the pack: `didact pack validate {pack}`", pack=self.rule.pack),
            )

        def count(key: str, default: int) -> int:
            raw = step.get(key, default)
            value = self._value(raw) if isinstance(raw, str) else raw
            return max(0, int(value)) if isinstance(value, int | float) else default

        done = self.host.pool(
            record,
            roll=mode == "roll",
            drop=count("drop", 1 if mode == "drop" else 0),
            extra=count("extra", 0),
            reason=self.rule.id,
        )
        self.run.changed = True
        self.run.lines.extend(done.lines)
        self.run.rolls.extend(done.rolls)
        name = str(step.get("as", "pool"))
        for key, value in done.values.items():
            self.run.bound[f"{name}.{key}"] = value

    def _reroll(self, step: dict[str, JSON]) -> None:
        """Reroll a named roll's dice, keeping those that match `keep_if` (`@face == 6`)."""
        name = str(step["reroll"])
        if name not in self.run.exprs:
            raise InvalidError(
                _("{rule}: no roll named {name} to reroll", rule=self.rule.id, name=repr(name)),
                hint=_("name a roll the rule made earlier"),
            )
        keep = step.get("keep_if")
        kept: list[int] = []
        for face in self.run.faces.get(name, []):
            self.run.bound["face"] = face
            keep_it = isinstance(keep, str) and truthy(self.eval(keep))
            kept.append(face if keep_it else 0)  # 0: draw a fresh face
        self.run.bound.pop("face", None)
        self.roll(self.run.exprs[name], name, faces=kept)

    def _repeat(self, step: dict[str, JSON]) -> None:
        """Run steps `repeat` times, counting them as `as:` (`i` by default: 1, 2, …)."""
        raw = step.get("repeat")
        count = self.eval(raw) if isinstance(raw, str) else raw
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise InvalidError(
                _(
                    "{rule}: repeat needs a whole number, not {raw}",
                    rule=self.rule.id,
                    raw=repr(raw),
                ),
                hint=_('e.g. `repeat: 3`, or `repeat: "@rooms"` after rolling rooms'),
            )
        name = str(step.get("as", "i"))
        for index in range(1, min(count, 200) + 1):
            self.run.bound[name] = index
            self.steps(step.get("steps"))

    def _for(self, step: dict[str, JSON]) -> None:
        """Run steps once per party member (`for: party`) or player character (`for: pcs`), each
        bound to `as:` (`member` by default) as a record: read and set like a `ref` parameter
        (`@member.name`, `set: member.hp`). It never takes a parameter's name (validation
        refuses one), so a rule's own `who` stays its own."""
        name = str(step.get("as", "member"))
        for member in self.host.party(pcs=step["for"] == "pcs"):
            self.run.records[name] = self.run.bound[name] = member
            self.steps(step.get("steps"))
        self.run.records.pop(name, None)
        self.run.bound.pop(name, None)

    def _make(self, step: dict[str, JSON]) -> None:
        """Make a record at once, described as a draft's `entity` is (`type`, `name`, `fields`,
        `links`, …), unless one of that type and name is here already: then that one, as it is,
        so a rule run again makes nothing new. It's bound to `as:` (its `key`, else its type) as
        a loop's member is: `pool: "@doom"`, `set: doom.note`."""
        spec = self.filled(step["entity"])
        if not isinstance(spec, dict):
            raise InvalidError(
                _("{rule}: can't run step {step}", rule=self.rule.id, step=repr(step)),
                hint=_("check the pack: `didact pack validate {pack}`", pack=self.rule.pack),
            )
        done = self.host.make(spec, self.rule)
        type_ = done.record.partition(":")[0]
        name = str(step.get("as", spec.get("key") or type_))
        self.run.records[name] = self.run.bound[name] = done.record
        shown = f"{labels.type_inline(type_)} {done.name} [{done.record}]"
        if done.new:
            self.run.changed = True
            self.run.lines.append(f"+ {shown}")
        else:
            self.run.lines.append(_("{record} is here already", record=shown))

    def _carry(self, step: dict[str, JSON]) -> None:
        """Give a record an item as `inv add` does (`give: Rope`, `to: "@who"`: its compendium
        details, `count:`, `data: {…}` for more), or take one from it as `inv drop` does
        (`take: Rope`, `from: "@who"`, `count:` of a stack, else all of it). The room and the
        field's hooks are checked as `inv` checks them."""
        giving = "give" in step
        item = self.filled(step["give" if giving else "take"])
        record = self.host.record(str(self.filled(step.get("to" if giving else "from", ""))))
        raw = step.get("count")
        count = self.filled(raw) if raw is not None else None
        if count is not None and (
            not isinstance(count, int) or isinstance(count, bool) or count < 1
        ):
            raise InvalidError(
                _(
                    "{rule}: `count` needs a whole number, not {raw}",
                    rule=self.rule.id,
                    raw=repr(raw),
                ),
                hint=_("check the pack: `didact pack validate {pack}`", pack=self.rule.pack),
            )
        data = self.filled(step.get("data") or {})
        if not isinstance(data, dict):
            raise InvalidError(
                _("{rule}: can't run step {step}", rule=self.rule.id, step=repr(step)),
                hint=_("check the pack: `didact pack validate {pack}`", pack=self.rule.pack),
            )
        if giving:
            if count is not None:
                data["count"] = count
            done = self.host.give(record, str(item), data)
        else:
            done = self.host.take(record, str(item), count)
        self.run.changed = True
        note = f" ({done.note})" if done.note else ""
        self.run.lines.append(f"{record}: {'+' if giving else '-'} {done.item}{note}")
        for ref in done.triggers:
            self._hook(ref, record)

    def _use(self, step: dict[str, JSON]) -> None:
        """Use an item a record carries as `inv use` does (`use: Torch`, `from: "@who"`,
        `spend: 2`): its uses or charges count down, a usage die rolls (and steps down on 1-2),
        and one that runs out is gone unless it recharges or is kept. Of several of that name,
        the first with a use left. Binds `@<as>.out` (its last use went), `.gone` (none of it is
        left), `.left` (uses left), `.die` (the usage die now) and `.rolled` (what it showed);
        `as:` defaults to use."""
        item = self.filled(step["use"])
        record = self.host.record(str(self.filled(step.get("from", ""))))
        raw = step.get("spend", 1)
        spend = self.filled(raw)
        if not isinstance(spend, int) or isinstance(spend, bool) or spend < 1:
            raise InvalidError(
                _(
                    "{rule}: `spend` needs a whole number, not {raw}",
                    rule=self.rule.id,
                    raw=repr(raw),
                ),
                hint=_("check the pack: `didact pack validate {pack}`", pack=self.rule.pack),
            )
        done = self.host.use(record, str(item), spend)
        self.run.changed = True
        self.run.rolls.extend(done.rolls)
        note = f" ({done.note})" if done.note else ""
        self.run.lines.append(_("{who} uses {item}", who=record, item=done.item) + note)
        name = str(step.get("as", "use"))
        for key, value in done.values.items():
            self.run.bound[f"{name}.{key}"] = value
        for ref in done.triggers:
            self._hook(ref, record)
