"""Evaluate a dice-expression AST into a typed result tree.

Pools are rolled, then their modifiers run in registry order (`didact.expr.modifiers`), then
values combine through arithmetic, comparisons, functions, macros, tags, labels and repeats.
"""

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol

from didact.core.errors import InvalidError, UnknownName
from didact.core.i18n import N_, _
from didact.core.phrases import Phrase, phrase
from didact.expr.model import (
    BinOp,
    Bool,
    Call,
    CompareOp,
    ComparePoint,
    Comparison,
    Dice,
    DieSpec,
    Group,
    Labeled,
    Logic,
    ModifierCall,
    Negate,
    Node,
    Not,
    Number,
    Registry,
    Repeat,
    Scalar,
    Tagged,
    Target,
    Text,
    Value,
    Var,
    numeric,
)
from didact.expr.parser import Parser, canonical
from didact.expr.rng import Source

MAX_DICE = 1000  # dice in one pool
MAX_EXTRA = 100  # explosions or rerolls in one pool
MAX_DRAWS = 20_000  # dice drawn for one whole expression
MAX_MACRO_DEPTH = 16

type CountKind = Literal["sum", "successes", "sets"]

_CMP: dict[str, CompareOp] = {"==": "=", "<>": "<>", "<": "<", "<=": "<=", ">": ">", ">=": ">="}


class Member(Protocol):
    """What modifiers need from a pool member: a die, or one item of a {group}."""

    @property
    def value(self) -> Scalar: ...

    kept: bool
    success: bool
    failure: bool
    crit: bool
    fumble: bool


# ---------------------------------------------------------------------------- pool members


@dataclass(slots=True)
class Die:
    spec: DieSpec
    value: int
    symbols: tuple[str, ...] = ()
    kept: bool = True
    history: list[int] = field(default_factory=list)  # earlier values: rerolls and clamps
    parts: list[int] = field(default_factory=list)  # every face of a compounding die
    exploded: bool = False  # this die triggered an extra die
    explodable: bool = True
    added_by: str | None = None  # the modifier that added this die ("explode", "lucky.charm", …)
    penalty: int = 0  # penetrating dice count one less
    success: bool = False
    failure: bool = False
    crit: bool = False
    fumble: bool = False

    @property
    def sides(self) -> int:
        """The highest face (6 on a d6); handy in plugins: `die.value == die.sides`."""
        return self.spec.max_value

    @property
    def face(self) -> int:
        """The face shown, before any penetration penalty."""
        return self.value + self.penalty


@dataclass(slots=True)
class Item:
    """One member of a {group}: a sub-result and its value."""

    result: Result
    value: Scalar
    kept: bool = True
    success: bool = False
    failure: bool = False
    crit: bool = False
    fumble: bool = False


@dataclass(slots=True)
class Pool:
    """What dice pools and groups share: members, how they count, flags and notes."""

    count: CountKind = "sum"
    margin: Target | None = None  # `ms`: report the total's distance from a target
    min_set: int = 2  # `mt`: the smallest set that counts
    extra: int = 0  # explosions and rerolls so far (capped at MAX_EXTRA)
    flags: set[str] = field(default_factory=set)
    notes: list[str | Phrase] = field(default_factory=list)  # a phrase: shown in any language

    def members(self) -> Sequence[Member]:
        raise NotImplementedError

    def kept_members(self) -> list[Member]:
        return [m for m in self.members() if m.kept]

    @property
    def successes(self) -> int:
        return sum(1 for m in self.kept_members() if m.success)

    @property
    def failures(self) -> int:
        return sum(1 for m in self.kept_members() if m.failure)

    def sets(self) -> dict[Scalar, int]:
        """Values shown by at least `min_set` kept members, with how many show each."""
        counts = Counter(m.value for m in self.kept_members())
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], -kv[0]))
        return {value: n for value, n in ranked if n >= self.min_set}

    @property
    def total(self) -> Scalar:
        """The pool's value before any margin: sum, successes − failures, or number of sets."""
        match self.count:
            case "successes":
                return self.successes - self.failures
            case "sets":
                return len(self.sets())
            case "sum":
                return sum(m.value for m in self.kept_members())

    @property
    def value(self) -> Scalar:
        base = self.total
        if self.margin is None:
            return base
        if self.margin.op in ("<", "<="):  # roll-under: how far below the target
            return self.margin.number - base
        return base - self.margin.number

    def take_extra(self, what: str) -> bool:
        """Count one explosion or reroll; False (and a note) once the cap is reached."""
        if self.extra >= MAX_EXTRA:
            if "capped" not in self.flags:
                self.flags.add("capped")
                capped = (
                    N_("stopped after {count} explosions (the safety cap)")
                    if what == "explosion"
                    else N_("stopped after {count} rerolls (the safety cap)")
                )
                self.notes.append(phrase(capped, count=MAX_EXTRA))
            return False
        self.extra += 1
        return True


@dataclass(slots=True)
class DiePool(Pool):
    spec: DieSpec = field(default_factory=lambda: numeric(6))
    dice: list[Die] = field(default_factory=list)

    def members(self) -> list[Die]:
        return self.dice

    def kept(self) -> list[Die]:
        return [d for d in self.dice if d.kept]

    def add(self, die: Die, *, reason: str, explode: bool = True, after: Die | None = None) -> Die:
        """Add a die to the pool (plugin API), e.g. a bonus d4 from a pack effect."""
        die.added_by = reason
        die.explodable = explode
        index = next((i for i, d in enumerate(self.dice) if d is after), None)
        if index is None:
            self.dice.append(die)
        else:
            self.dice.insert(index + 1, die)
        return die

    def symbol_counts(self) -> dict[str, int]:
        counts: Counter[str] = Counter()
        for die in self.kept():
            counts.update(die.symbols)
        return dict(sorted(counts.items()))


@dataclass(slots=True)
class GroupPool(Pool):
    items: list[Item] = field(default_factory=list)

    def members(self) -> list[Item]:
        return self.items


# ---------------------------------------------------------------------------- results


@dataclass(slots=True)
class Result:
    value: Value
    tag: str | None = field(default=None, kw_only=True)
    label: str | None = field(default=None, kw_only=True)


@dataclass(slots=True)
class ConstResult(Result):
    pass


@dataclass(slots=True)
class VarResult(Result):
    name: str = ""


@dataclass(slots=True)
class PoolResult(Result):
    canonical: str = ""
    pool: DiePool = field(default_factory=DiePool)
    count: Result | None = None  # set when the number of dice was rolled or looked up


@dataclass(slots=True)
class GroupResult(Result):
    canonical: str = ""
    pool: GroupPool = field(default_factory=GroupPool)


@dataclass(slots=True)
class OpResult(Result):
    op: str = "+"
    left: Result = field(default_factory=lambda: ConstResult(0))
    right: Result = field(default_factory=lambda: ConstResult(0))


@dataclass(slots=True)
class NegResult(Result):
    operand: Result = field(default_factory=lambda: ConstResult(0))


@dataclass(slots=True)
class CompareResult(Result):
    op: str = "=="
    left: Result = field(default_factory=lambda: ConstResult(0))
    right: Result = field(default_factory=lambda: ConstResult(0))


@dataclass(slots=True)
class LogicResult(Result):
    op: str = "and"
    left: Result = field(default_factory=lambda: ConstResult(0))
    right: Result | None = None  # None: not evaluated (`false and …`)


@dataclass(slots=True)
class NotResult(Result):
    operand: Result = field(default_factory=lambda: ConstResult(0))


@dataclass(slots=True)
class CallResult(Result):
    name: str = ""
    args: list[Result] = field(default_factory=list)
    expansion: Result | None = None  # set for macros: the expanded expression's result


@dataclass(slots=True)
class RepeatResult(Result):
    items: list[Result] = field(default_factory=list)


# ---------------------------------------------------------------------------- context


@dataclass(slots=True)
class RollContext:
    """Everything evaluation needs: the registry, where faces come from, and variables."""

    registry: Registry
    source: Source
    vars: Mapping[str, Value] = field(default_factory=dict)
    resolve: Callable[[str], Value | None] | None = None  # e.g. `@tom.hp` → a record field
    used: dict[str, Value] = field(default_factory=dict)  # variables read, for replay
    draws: int = 0
    depth: int = 0

    def roll_die(self, spec: DieSpec) -> Die:
        self.draws += 1
        if self.draws > MAX_DRAWS:
            raise InvalidError(
                _("this roll needs more than {count} dice", count=f"{MAX_DRAWS:,}"),
                hint=_("roll fewer or smaller pools"),
            )
        face = self.source.draw(spec)
        return Die(spec, face.value, face.symbols)

    def reroll(self, die: Die) -> None:
        """Replace a die's face with a fresh draw, remembering the old value."""
        fresh = self.roll_die(die.spec)
        die.history.append(die.value)
        die.value, die.symbols, die.penalty = fresh.value, fresh.symbols, 0

    def roll(self, text: str) -> Die:
        """Roll one die written in dice notation, e.g. `ctx.roll("d4")` (plugin API)."""
        node = Parser(text.strip(), self.registry).parse()
        if not isinstance(node, Dice) or node.modifiers or not isinstance(node.count, Number):
            raise InvalidError(
                _("{text} is not a single die", text=repr(text)), hint=_("e.g. `d4`")
            )
        return self.roll_die(node.die)

    def lookup(self, path: str) -> Value:
        value = self.vars.get(path)
        if value is None:
            folded = {k.casefold(): v for k, v in self.vars.items()}
            value = folded.get(path.casefold())
        if value is None and self.resolve is not None:
            value = self.resolve(path)
        if value is None:
            known = ", ".join(sorted(self.vars)[:12])
            hint = (
                _("known variables: {known}", known=known)
                if known
                else _("pass `--as <record>` or `--var name=value`")
            )
            raise UnknownName(_("unknown variable @{path}", path=path), what="variable", hint=hint)
        self.used[path] = value
        return value


# ---------------------------------------------------------------------------- evaluation


@dataclass(frozen=True, slots=True)
class Rolled:
    """One evaluated expression: what was asked, how Didact read it, and what came out."""

    text: str
    node: Node
    canonical: str
    result: Result


def run(text: str, ctx: RollContext) -> Rolled:
    """Parse and evaluate an expression."""
    node = Parser(text, ctx.registry).parse()
    return Rolled(text, node, canonical(node, ctx.registry), evaluate(node, ctx))


def evaluate(node: Node, ctx: RollContext) -> Result:
    match node:
        case Number(value=number):
            return ConstResult(number)
        case Text(value=text):
            return ConstResult(text)
        case Bool(value=flag):
            return ConstResult(flag)
        case Var(path=path):
            return VarResult(ctx.lookup(path), name=path)
        case Dice():
            return _dice(node, ctx)
        case Group():
            return _group(node, ctx)
        case BinOp(op=op, left=left, right=right):
            lhs, rhs = evaluate(left, ctx), evaluate(right, ctx)
            return OpResult(_arith(op, scalar(lhs), scalar(rhs)), op=op, left=lhs, right=rhs)
        case Negate(operand=operand):
            inner = evaluate(operand, ctx)
            return NegResult(-scalar(inner), operand=inner)
        case Comparison(op=op, left=left, right=right):
            lhs, rhs = evaluate(left, ctx), evaluate(right, ctx)
            return CompareResult(compare(op, value(lhs), value(rhs)), op=op, left=lhs, right=rhs)
        case Logic(op=op, left=left, right=right):
            lhs = evaluate(left, ctx)
            if truthy(value(lhs)) == (op == "or"):  # `true or …`, `false and …`: settled
                return LogicResult(op == "or", op=op, left=lhs)
            rhs = evaluate(right, ctx)
            return LogicResult(truthy(value(rhs)), op=op, left=lhs, right=rhs)
        case Not(operand=operand):
            inner = evaluate(operand, ctx)
            return NotResult(not truthy(value(inner)), operand=inner)
        case Call():
            return _call(node, ctx)
        case Tagged(tag=tag, inner=inner):
            result = evaluate(inner, ctx)
            result.tag = tag
            return result
        case Labeled(inner=inner, label=label):
            result = evaluate(inner, ctx)
            result.label = label
            return result
        case Repeat(times=times, inner=inner):
            return RepeatResult(0, items=[evaluate(inner, ctx) for _unused in range(times)])
    raise TypeError(f"cannot evaluate {node!r}")


def value(result: Result) -> Value:
    if isinstance(result, RepeatResult):
        raise InvalidError(
            _("a repeated roll (`N#…`) can't be used inside a bigger expression"),
            hint=_("roll the repeat on its own"),
        )
    return result.value


def scalar(result: Result) -> Scalar:
    """A result's value as a number (true/false count as 1/0)."""
    return as_number(value(result))


def as_number(raw: Value, what: str | None = None) -> Scalar:
    if isinstance(raw, bool):
        return int(raw)
    if isinstance(raw, int | float):
        return raw
    raise InvalidError(
        _("expected {what}, got {value}", what=what or _("a number"), value=show(raw)),
        hint=_("only numbers work here"),
    )


def truthy(raw: Value) -> bool:
    return bool(raw)


def show(raw: Value) -> str:
    """A value the way expressions write it: 3, 2.5, true, 'text', [1, 2]."""
    match raw:
        case bool():
            return "true" if raw else "false"
        case float() if raw.is_integer():
            return str(int(raw))
        case float():
            return f"{raw:.4f}".rstrip("0").rstrip(".")
        case int():
            return str(raw)
        case str():
            return f'"{raw}"' if "'" in raw else f"'{raw}'"
        case list():
            return "[" + ", ".join(show(v) for v in raw) + "]"


def compare(op: str, left: Value, right: Value) -> bool:
    if op == "in":
        if isinstance(right, list):
            return left in right
        if isinstance(right, str) and isinstance(left, str):
            return left.casefold() in right.casefold()
        raise InvalidError(
            _("`in` needs a list or text on its right, not {value}", value=show(right)),
            hint=_("e.g. `'fire' in @tags`"),
        )
    if op in ("==", "<>"):
        same = left == right
        return same if op == "==" else not same
    if isinstance(left, str | list) or isinstance(right, str | list):
        raise InvalidError(
            _(
                "can't compare {left} {op} {right}",
                left=show(left),
                op=op,
                right=show(right),
            ),
            hint=_("`<`, `>` and friends need numbers"),
        )
    return Target(_CMP[op], as_number(right)).test(as_number(left))


def _arith(op: str, left: Scalar, right: Scalar) -> Scalar:
    match op:
        case "+":
            return left + right
        case "-":
            return left - right
        case "*":
            return left * right
        case "/" | "//" | "%":
            if right == 0:
                raise InvalidError(_("division by zero"), hint=_("check the divisor"))
            if op == "/":
                quotient = left / right
                return int(quotient) if quotient.is_integer() else quotient
            return left // right if op == "//" else left % right
    raise InvalidError(
        _("unknown operator {op}", op=repr(op)), hint=_("`didact guide dice` lists the operators")
    )


def _dice(node: Dice, ctx: RollContext) -> PoolResult:
    counted = evaluate(node.count, ctx)
    count = scalar(counted)
    if not float(count).is_integer() or not 0 <= count <= MAX_DICE:
        raise InvalidError(
            _("a pool needs 0–{most} dice, not {count}", most=MAX_DICE, count=count),
            hint=_("check the number of dice"),
        )
    pool = DiePool(spec=node.die, dice=[ctx.roll_die(node.die) for _unused in range(int(count))])
    apply_modifiers(pool, node.modifiers, ctx)
    flag_pool(pool)
    shown = canonical(node, ctx.registry)
    dynamic = None if isinstance(counted, ConstResult) else counted
    return PoolResult(pool.value, canonical=shown, pool=pool, count=dynamic)


def _group(node: Group, ctx: RollContext) -> GroupResult:
    items = []
    for item_node in node.items:
        result = evaluate(item_node, ctx)
        items.append(Item(result, scalar(result)))
    pool = GroupPool(items=items)
    apply_modifiers(pool, node.modifiers, ctx)
    return GroupResult(pool.value, canonical=canonical(node, ctx.registry), pool=pool)


def apply_modifiers(pool: Pool, calls: Sequence[ModifierCall], ctx: RollContext) -> None:
    """Run a pool's modifiers in registry order (stable for equal orders)."""
    registry = ctx.registry
    for call in sorted(calls, key=lambda c: registry.modifiers[c.name].order):
        spec = registry.modifiers[call.name]
        arg: int | Target | None
        match call.arg:
            case ComparePoint(op=op, value=value_node):
                arg = Target(op, scalar(evaluate(value_node, ctx)))
            case int() as number:
                arg = number
            case None:
                arg = spec.default_arg
        spec.apply(pool, ctx, arg)


def flag_pool(pool: DiePool) -> None:
    """Flags for the rules layer. Doubles, max and min look only at the dice rolled for the
    pool itself (kept ones), not at dice added by explosions or pack effects."""
    kept = pool.kept()
    rolled = [d for d in kept if d.added_by is None]
    values = [d.value for d in rolled] if not pool.spec.symbolic else []
    if len(values) >= 2 and len(set(values)) < len(values):
        pool.flags.add("doubles")
    if len(values) >= 2 and len(set(values)) == 1:
        pool.flags.add("all-same")
    if rolled and not pool.spec.symbolic:
        if all(d.face >= pool.spec.max_value for d in rolled):
            pool.flags.add("max")
        if all(d.face <= pool.spec.min_value for d in rolled):
            pool.flags.add("min")
    if any(d.exploded for d in pool.dice):
        pool.flags.add("exploded")
    if any(d.crit for d in kept):
        pool.flags.add("crit")
    if any(d.fumble for d in kept):
        pool.flags.add("fumble")


# ---------------------------------------------------------------------------- functions


def _flat(values: list[Value]) -> list[Value]:
    found: list[Value] = []
    for item in values:
        if isinstance(item, list):
            found.extend(item)
        else:
            found.append(item)
    return found


def _numbers(values: list[Value], name: str) -> list[Scalar]:
    found = [as_number(v, _("numbers in {name}()", name=name)) for v in _flat(values)]
    if not found:
        raise InvalidError(
            _("{name}() got nothing", name=name),
            hint=_("give {name}() at least one number", name=name),
        )
    return found


def _one(values: list[Value], name: str) -> Scalar:
    if len(values) != 1:
        raise InvalidError(
            _("{name}() takes one number, got {count}", name=name, count=len(values)),
            hint=_("e.g. `{name}(2d6)`", name=name),
        )
    return as_number(values[0], _("a number in {name}()", name=name))


def _count(values: list[Value]) -> int:
    """`count(@list)` is its length; `count(@roll.dice, 6)` counts the sixes."""
    if len(values) == 2 and isinstance(values[0], list):
        return sum(1 for v in values[0] if v == values[1])
    return len(_flat(values))


def _round(x: Scalar) -> int:
    """Round half away from zero (2.5 → 3), as tabletop rules expect."""
    return int(x + 0.5) if x >= 0 else -int(-x + 0.5)


BUILTINS: dict[str, Callable[[list[Value]], Value]] = {
    "min": lambda a: min(_numbers(a, "min")),
    "max": lambda a: max(_numbers(a, "max")),
    "sum": lambda a: sum(_numbers(a, "sum")) if _flat(a) else 0,
    "count": lambda a: _count(a),
    "any": lambda a: any(truthy(v) for v in _flat(a)),
    "all": lambda a: all(truthy(v) for v in _flat(a)),
    "abs": lambda a: abs(_one(a, "abs")),
    "floor": lambda a: int(_one(a, "floor") // 1),
    "ceil": lambda a: int(-(-_one(a, "ceil") // 1)),
    "round": lambda a: _round(_one(a, "round")),
}
SPECIAL = ("if", "step", "default")


def _call(node: Call, ctx: RollContext) -> Result:
    name = node.name
    if name == "step" or name.startswith("step."):
        return _step(node, ctx)
    if name == "if":
        return _if(node, ctx)
    if name == "default":
        return _default(node, ctx)
    if name in ctx.registry.macros:
        return _macro(node, ctx)
    args = [evaluate(a, ctx) for a in node.args]
    values = [value(a) for a in args]
    builtin = BUILTINS.get(name)
    if builtin is not None:
        return CallResult(builtin(values), name=name, args=args)
    func = ctx.registry.functions.get(name)
    if func is None:
        known = sorted({*BUILTINS, *SPECIAL, *ctx.registry.functions, *ctx.registry.macros})
        raise InvalidError(
            _("unknown function {name}()", name=name),
            hint=_("available: {names}", names=", ".join(known)),
        )
    try:
        result = func(*values)
    except (TypeError, ValueError) as exc:
        raise InvalidError(
            _("{name}(): {error}", name=name, error=exc), hint=_("check the arguments")
        ) from exc
    return CallResult(result, name=name, args=args)


def _if(node: Call, ctx: RollContext) -> Result:
    """`if(condition, then, else)`: only the chosen branch is evaluated (and rolled)."""
    if len(node.args) != 3:
        raise InvalidError(
            _("if() takes a condition and two values"), hint=_("e.g. `if(@hp > 0, 1, 0)`")
        )
    condition = evaluate(node.args[0], ctx)
    chosen = evaluate(node.args[1] if truthy(value(condition)) else node.args[2], ctx)
    return CallResult(value(chosen), name="if", args=[condition, chosen])


def _default(node: Call, ctx: RollContext) -> Result:
    """`default(@thread.flashpoint, 0)`: the value, or the fallback when it isn't set."""
    if len(node.args) != 2:
        raise InvalidError(
            _("default() takes a value and a fallback"), hint=_("e.g. `default(@x, 0)`")
        )
    try:
        found = evaluate(node.args[0], ctx)
    except UnknownName as exc:
        if exc.what != "variable":
            raise
        found = evaluate(node.args[1], ctx)
    return CallResult(value(found), name="default", args=[found])


def _macro(node: Call, ctx: RollContext) -> Result:
    macro = ctx.registry.macros[node.name]
    if ctx.depth >= MAX_MACRO_DEPTH:
        raise InvalidError(
            _("{name}() nests too deeply", name=node.name),
            hint=_("a macro may be calling itself"),
        )
    try:
        text = macro.expand([canonical(a, ctx.registry) for a in node.args])
    except ValueError as exc:
        raise InvalidError(str(exc), hint=macro.summary or None) from exc
    ctx.depth += 1
    try:
        inner = evaluate(Parser(text, ctx.registry).parse(), ctx)
    finally:
        ctx.depth -= 1
    return CallResult(scalar(inner), name=node.name, expansion=inner)


def _step(node: Call, ctx: RollContext) -> Result:
    """`step(d6, 1)` rolls a d8; `step.extended(d7, 1)` steps along the d3–d30 chain instead."""
    chain_name = node.name.partition(".")[2] or "standard"
    chain = ctx.registry.chains.get(chain_name)
    if chain is None:
        known = ", ".join(f"step.{c}" for c in sorted(ctx.registry.chains))
        raise InvalidError(
            _("unknown dice chain {chain}", chain=repr(chain_name)),
            hint=_("available: step, {known}", known=known),
        )
    if len(node.args) != 2 or not isinstance(node.args[0], Dice):
        raise InvalidError(
            _("{name}() takes dice and a number of steps", name=node.name),
            hint=_("e.g. `step(d6, 1)`"),
        )
    dice = node.args[0]
    steps = scalar(evaluate(node.args[1], ctx))
    if dice.die.kind != "numeric" or dice.die.sides not in chain:
        sizes = ", ".join(f"d{s}" for s in chain)
        raise InvalidError(
            _("d{die} isn't on the {chain} dice chain", die=dice.die.text, chain=chain_name),
            hint=_("chain: {sizes}", sizes=sizes),
        )
    wanted = chain.index(dice.die.sides) + int(steps)
    index = min(max(wanted, 0), len(chain) - 1)
    result = _dice(Dice(dice.span, dice.count, numeric(chain[index]), dice.modifiers), ctx)
    if index != wanted:
        result.pool.notes.append(
            phrase(N_("the {chain} dice chain stops at d{die}"), chain=chain_name, die=chain[index])
        )
    return result
