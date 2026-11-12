"""Probabilities for an expression: exact through icepool (optional extra), else simulated.

`pip install didact[odds]` enables exact answers. Without it, or for modifiers the adapter does
not translate (unique, matches, plugins, keep/drop mixed with explosions or successes, …),
Didact rolls the expression many times with a fixed seed and reports the estimate.
"""

import importlib
import math
import random
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Literal

from didact.core.errors import InvalidError
from didact.core.i18n import _
from didact.expr.engine import BUILTINS, RollContext, evaluate, scalar
from didact.expr.model import (
    BinOp,
    Bool,
    Call,
    ComparePoint,
    Comparison,
    Dice,
    DieSpec,
    Face,
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
    Value,
    Var,
)
from didact.expr.parser import Parser, canonical

DEFAULT_SAMPLES = 20_000
EXPLODE_DEPTH = 9  # icepool's explosion depth; deeper chains are vanishingly rare

type Outcome = Scalar | bool


@dataclass(frozen=True, slots=True)
class Odds:
    canonical: str
    method: Literal["exact", "simulated"]
    distribution: dict[Outcome, float]  # outcome → probability, sorted by outcome
    samples: int | None = None
    why_simulated: str | None = None

    @property
    def is_check(self) -> bool:
        return all(isinstance(o, bool) for o in self.distribution)

    @property
    def chance(self) -> float:
        """P(true) for a comparison."""
        return self.distribution.get(True, 0.0)

    @property
    def mean(self) -> float:
        return sum(float(o) * p for o, p in self.distribution.items())

    @property
    def sd(self) -> float:
        mean = self.mean
        return math.sqrt(sum((float(o) - mean) ** 2 * p for o, p in self.distribution.items()))

    def at_least(self, outcome: Outcome) -> float:
        return sum(p for o, p in self.distribution.items() if float(o) >= float(outcome))

    def margin(self, p: float) -> float:
        """The 95% margin of error of a simulated probability."""
        if self.samples is None:
            return 0.0
        return 1.96 * math.sqrt(max(p * (1 - p), 1e-12) / self.samples)


def odds(
    text: str,
    registry: Registry,
    variables: Mapping[str, Value] | None = None,
    *,
    samples: int = DEFAULT_SAMPLES,
    exact: bool = True,
) -> Odds:
    node = Parser(text, registry).parse()
    if isinstance(node, Repeat):
        raise InvalidError(_("odds works on one roll, not a repeat"), hint=_("drop the `N#`"))
    variables = dict(variables or {})
    shown = canonical(node, registry)
    reason = _("exact odds were turned off")
    if exact:
        try:
            ice = importlib.import_module("icepool")
        except ImportError:
            reason = _("icepool isn't installed (`uv sync --extra odds` for exact odds)")
        else:
            try:
                die = _Translate(ice, registry, variables).node(node)
                return Odds(shown, "exact", _distribution(die))
            except _Unsupported as exc:
                reason = str(exc)
    return _simulate(node, shown, registry, variables, samples, reason)


# ---------------------------------------------------------------------------- simulation


@dataclass(slots=True)
class _Random:
    rng: random.Random

    def draw(self, die: DieSpec) -> Face:
        match die.kind:
            case "numeric":
                return Face(self.rng.randint(1, die.sides))
            case "fudge":
                return Face(self.rng.randint(-1, 1))
            case "digit":
                digits = "".join(
                    str(self.rng.randint(1, die.sides)) for _unused in range(die.digits)
                )
                return Face(int(digits))
            case "custom":
                return self.rng.choice(die.faces)


def _simulate(
    node: Node,
    shown: str,
    registry: Registry,
    variables: dict[str, Value],
    samples: int,
    reason: str,
) -> Odds:
    source = _Random(random.Random(0x0DD5))  # fixed: the same question gets the same answer
    counts: Counter[Outcome] = Counter()
    for _unused in range(samples):
        result = evaluate(node, RollContext(registry, source, variables))
        outcome = result.value
        counts[outcome if isinstance(outcome, bool) else scalar(result)] += 1
    distribution = {o: n / samples for o, n in sorted(counts.items(), key=lambda kv: kv[0])}
    return Odds(shown, "simulated", distribution, samples=samples, why_simulated=reason)


# ---------------------------------------------------------------------------- icepool adapter


class _Unsupported(Exception):
    pass


def _distribution(die: Any) -> dict[Outcome, float]:
    total = die.denominator()
    found: dict[Outcome, float] = {}
    for outcome, quantity in die.items():
        key: Outcome = outcome
        if isinstance(outcome, Fraction):
            key = int(outcome) if outcome.denominator == 1 else float(outcome)
        found[key] = found.get(key, 0.0) + quantity / total
    return dict(sorted(found.items(), key=lambda kv: kv[0]))


_SIMPLE = {"min", "max", "reroll", "reroll-once", "crit-success", "crit-fail", "sort", "sort-desc"}
_SELECT = {"keep-highest", "keep-lowest", "drop-lowest", "drop-highest"}
_COUNT = {"success", "failure", "even", "odd"}
_EXPLODE = {"explode", "compound"}


class _Translate:
    """AST → icepool Die. Raises _Unsupported for anything it can't express exactly."""

    def __init__(self, ice: Any, registry: Registry, variables: dict[str, Value]) -> None:
        self.ice = ice
        self.registry = registry
        self.variables = variables

    def node(self, node: Node) -> Any:
        ice = self.ice
        match node:
            case Number(value=value):
                return ice.Die([value])
            case Var(path=path):
                return ice.Die([self.var(path)])
            case Dice():
                return self.dice(node)
            case Group():
                return self.group(node)
            case BinOp(op=op, left=left, right=right):
                return self.binary(op, self.node(left), self.node(right))
            case Negate(operand=operand):
                return -self.node(operand)
            case Comparison(op=op, left=left, right=right) if op != "in":
                test = _compare(op)
                return ice.map(test, self.node(left), self.node(right))
            case Logic(op=op, left=left, right=right):
                both = (self.node(left), self.node(right))
                if op == "and":
                    return ice.map(lambda a, b: bool(a) and bool(b), *both)
                return ice.map(lambda a, b: bool(a) or bool(b), *both)
            case Not(operand=operand):
                return ice.map(lambda a: not a, self.node(operand))
            case Bool(value=flag):
                return ice.Die([flag])
            case Call(name=name, args=args):
                if name in self.registry.macros:
                    macro = self.registry.macros[name]
                    text = macro.expand([canonical(a, self.registry) for a in args])
                    return self.node(Parser(text, self.registry).parse())
                func = BUILTINS.get(name)
                if func is None or name in ("count", "any", "all"):
                    raise _Unsupported(_("{name}() is simulated", name=name))
                return ice.map(lambda *xs: func(list(xs)), *(self.node(a) for a in args))
            case Tagged(inner=inner) | Labeled(inner=inner):
                return self.node(inner)
        raise _Unsupported(_("{name} is simulated", name=type(node).__name__.lower()))

    def var(self, path: str) -> Scalar:
        raw = self._var(path)
        if isinstance(raw, bool) or not isinstance(raw, int | float):
            raise _Unsupported(_("@{path} isn't a number, so it's simulated", path=path))
        return raw

    def _var(self, path: str) -> Value:
        if path in self.variables:
            return self.variables[path]
        folded = {k.casefold(): v for k, v in self.variables.items()}
        if path.casefold() in folded:
            return folded[path.casefold()]
        raise InvalidError(
            _("unknown variable @{path}", path=path), hint=_("pass `--var name=value`")
        )

    def binary(self, op: str, left: Any, right: Any) -> Any:
        match op:
            case "+":
                return left + right
            case "-":
                return left - right
            case "*":
                return left * right
            case "//":
                return left // right
            case "%":
                return left % right
        return self.ice.map(_true_divide, left, right)

    def base_die(self, spec: DieSpec) -> Any:
        ice = self.ice
        match spec.kind:
            case "numeric":
                return ice.d(spec.sides)
            case "fudge":
                return ice.Die([-1, 0, 1])
            case "digit":
                values = [0]
                for _unused in range(spec.digits):
                    values = [v * 10 + d for v in values for d in range(1, spec.sides + 1)]
                return ice.Die(values)
            case "custom":
                if spec.symbolic:
                    raise _Unsupported(_("symbol dice are simulated"))
                return ice.Die([f.value for f in spec.faces])

    def count(self, node: Node) -> int:
        match node:
            case Number(value=value) if float(value).is_integer():
                return int(value)
            case Var(path=path):
                return int(self.var(path))
        raise _Unsupported(_("a rolled number of dice is simulated"))

    def target(self, call: ModifierCall, default: Scalar) -> Target:
        match call.arg:
            case None:
                return Target("=", default)
            case ComparePoint(op=op, value=Number(value=number)):
                return Target(op, number)
            case ComparePoint(op=op, value=Var(path=path)):
                return Target(op, self.var(path))
        raise _Unsupported(_("{name} is simulated", name=call.name))

    def dice(self, node: Dice) -> Any:
        spec = node.die
        die = self.base_die(spec)
        n = self.count(node.count)
        names = [c.name for c in node.modifiers]
        unknown = set(names) - _SIMPLE - _SELECT - _COUNT - _EXPLODE - {"margin"}
        if unknown:
            raise _Unsupported(_("{name} is simulated", name=", ".join(sorted(unknown))))
        selects = [c for c in node.modifiers if c.name in _SELECT]
        counts = [c for c in node.modifiers if c.name in _COUNT]
        explodes = [c for c in node.modifiers if c.name in _EXPLODE]
        others = [c for c in node.modifiers if c.name in ("min", "max", "reroll", "reroll-once")]
        mixed = (selects and (counts or explodes)) or (counts and explodes) or (explodes and others)
        if len(selects) > 1 or len(explodes) > 1 or mixed:
            raise _Unsupported(_("this mix of modifiers is simulated"))
        for call in sorted(node.modifiers, key=lambda c: self.registry.modifiers[c.name].order):
            match call.name:
                case "min":
                    die = die.clip(call.arg, None)
                case "max":
                    die = die.clip(None, call.arg)
                case "reroll" | "reroll-once":
                    target = self.target(call, spec.min_value)
                    depth: int | str = 1 if call.name == "reroll-once" else "inf"
                    die = die.reroll(target.test, depth=depth)
                case "explode" | "compound":
                    target = self.target(call, spec.max_value)
                    die = die.explode(target.test, depth=EXPLODE_DEPTH)
                case _:
                    pass
        if selects:
            call = selects[0]
            k = int(call.arg) if isinstance(call.arg, int) else 1
            k = min(k, n)
            pool = die.pool(n)
            match call.name:
                case "keep-highest":
                    return self.margin(node, pool.highest(k).sum() if k else self.ice.Die([0]))
                case "keep-lowest":
                    return self.margin(node, pool.lowest(k).sum() if k else self.ice.Die([0]))
                case "drop-lowest":
                    return self.margin(
                        node, pool.highest(n - k).sum() if n > k else self.ice.Die([0])
                    )
                case _:
                    return self.margin(
                        node, pool.lowest(n - k).sum() if n > k else self.ice.Die([0])
                    )
        if counts:
            score = self.scorer(counts, spec)
            die = die.map(score)
        return self.margin(node, n @ die if n else self.ice.Die([0]))

    def scorer(self, calls: list[ModifierCall], spec: DieSpec) -> Callable[[Scalar], int]:
        success: list[Callable[[Scalar], bool]] = []
        failure: list[Callable[[Scalar], bool]] = []
        for call in calls:
            match call.name:
                case "success":
                    success.append(self.target(call, spec.max_value).test)
                case "failure":
                    failure.append(self.target(call, spec.min_value).test)
                case "even":
                    success.append(lambda v: int(v) % 2 == 0)
                case _:
                    success.append(lambda v: int(v) % 2 == 1)

        def score(value: Scalar) -> int:
            if any(test(value) for test in success):
                return 1
            return -1 if any(test(value) for test in failure) else 0

        return score

    def margin(self, node: Dice | Group, die: Any) -> Any:
        call = next((c for c in node.modifiers if c.name == "margin"), None)
        if call is None:
            return die
        target = self.target(call, 0)
        if target.op in ("<", "<="):
            return target.number - die
        return die - target.number

    def group(self, node: Group) -> Any:
        items = [self.node(i) for i in node.items]
        names = {c.name for c in node.modifiers} - {"sort", "sort-desc"}
        if not names:
            total = items[0]
            for item in items[1:]:
                total = total + item
            return total
        if len(node.modifiers) != 1 or not names <= _SELECT:
            raise _Unsupported(_("this group is simulated"))
        call = node.modifiers[0]
        n = len(items)
        k = min(int(call.arg) if isinstance(call.arg, int) else 1, n)
        pool = self.ice.Pool(items)
        match call.name:
            case "keep-highest":
                return pool.highest(k).sum()
            case "keep-lowest":
                return pool.lowest(k).sum()
            case "drop-lowest":
                return pool.highest(n - k).sum()
            case _:
                return pool.lowest(n - k).sum()


def _compare(op: str) -> Callable[[Scalar, Scalar], bool]:
    return {
        "==": lambda a, b: a == b,
        "<>": lambda a, b: a != b,
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
    }[op]


def _true_divide(a: Scalar, b: Scalar) -> Scalar:
    if b == 0:
        raise InvalidError(_("division by zero"), hint=_("check the divisor"))
    quotient = Fraction(a) / Fraction(b)
    return int(quotient) if quotient.denominator == 1 else float(quotient)
