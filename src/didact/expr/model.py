"""The dice-expression AST, die specifications and the plugin registry.

Everything here is plain data; parsing lives in `parser.py`, evaluation in `engine.py`.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from didact.core.i18n import _, ngettext
from didact.core.output import JSON

if TYPE_CHECKING:
    from didact.expr.engine import Pool, RollContext

type Scalar = int | float
type Value = int | float | bool | str | list[Value]  # what variables and results can hold
type CompareOp = Literal["=", "<>", "<", "<=", ">", ">="]
type ArgKind = Literal["none", "number", "compare"]
type ModifierFunc = Callable[["Pool", "RollContext", "int | Target | None"], object]

COMPARE_OPS: tuple[CompareOp, ...] = (">=", "<=", "<>", ">", "<", "=")


def to_json(value: Value) -> JSON:
    """An expression value as plain JSON data."""
    if isinstance(value, list):
        return [to_json(v) for v in value]
    return value


def from_json(raw: JSON) -> Value | None:
    """JSON → an expression value (None for maps and nulls, which expressions can't hold)."""
    match raw:
        case bool() | int() | float() | str():
            return raw
        case list():
            items = [from_json(item) for item in raw]
            return None if any(i is None for i in items) else [i for i in items if i is not None]
        case _:
            return None


def values_from(raw: JSON) -> dict[str, Value]:
    """A JSON mapping as expression variables (entries that can't be values are dropped)."""
    found: dict[str, Value] = {}
    for key, item in raw.items() if isinstance(raw, dict) else []:
        value = from_json(item)
        if value is not None:
            found[key] = value
    return found


CHAINS: dict[str, tuple[int, ...]] = {
    "standard": (4, 6, 8, 10, 12),
    "extended": (3, 4, 5, 6, 7, 8, 10, 12, 14, 16, 20, 24, 30),
}


@dataclass(frozen=True, slots=True)
class Target:
    """A resolved compare point, e.g. `>=8`: what modifiers receive as their argument."""

    op: CompareOp
    number: Scalar

    def test(self, value: Scalar) -> bool:
        match self.op:
            case "=":
                return value == self.number
            case "<>":
                return value != self.number
            case "<":
                return value < self.number
            case "<=":
                return value <= self.number
            case ">":
                return value > self.number
            case ">=":
                return value >= self.number

    def text(self) -> str:
        number = self.number
        shown = str(int(number)) if float(number).is_integer() else str(number)
        return f"{self.op}{shown}"


@dataclass(frozen=True, slots=True)
class Span:
    start: int
    end: int


# ------------------------------------------------------------------------- die specs


@dataclass(frozen=True, slots=True)
class Face:
    """One face of a custom die: a number, symbols, or both (blank faces have neither)."""

    value: int = 0
    symbols: tuple[str, ...] = ()

    def text(self) -> str:
        if self.symbols:
            return "+".join(self.symbols)
        return str(self.value)


@dataclass(frozen=True, slots=True)
class DieSpec:
    """What one die looks like: d6, dF, d66, d{…} or a named pack die d[boost]."""

    kind: Literal["numeric", "fudge", "digit", "custom"]
    sides: int  # numeric: faces; digit: sides of each digit die; custom: number of faces
    digits: int = 1
    faces: tuple[Face, ...] = ()
    name: str | None = None  # set for named pack dice

    @property
    def text(self) -> str:
        if self.name is not None:
            return f"[{self.name}]"
        match self.kind:
            case "numeric":
                return str(self.sides)
            case "fudge":
                return "F"
            case "digit":
                return str(self.sides) * self.digits
            case "custom":
                return "{" + ",".join(f.text() for f in self.faces) + "}"

    @property
    def min_value(self) -> int:
        match self.kind:
            case "numeric":
                return 1
            case "fudge":
                return -1
            case "digit":
                return int("1" * self.digits)
            case "custom":
                return min(f.value for f in self.faces)

    @property
    def max_value(self) -> int:
        match self.kind:
            case "numeric":
                return self.sides
            case "fudge":
                return 1
            case "digit":
                return int(str(self.sides) * self.digits)
            case "custom":
                return max(f.value for f in self.faces)

    @property
    def symbolic(self) -> bool:
        return any(f.symbols for f in self.faces)


def numeric(sides: int) -> DieSpec:
    return DieSpec("numeric", sides)


FUDGE = DieSpec("fudge", 3)


# ------------------------------------------------------------------------- AST


@dataclass(frozen=True, slots=True)
class ComparePoint:
    op: CompareOp
    value: Node


@dataclass(frozen=True, slots=True)
class ModifierCall:
    name: str  # registry name, e.g. "keep-highest"
    arg: int | ComparePoint | None
    span: Span


@dataclass(frozen=True, slots=True)
class Node:
    span: Span


@dataclass(frozen=True, slots=True)
class Number(Node):
    value: int | float


@dataclass(frozen=True, slots=True)
class Dice(Node):
    count: Node
    die: DieSpec
    modifiers: tuple[ModifierCall, ...] = ()


@dataclass(frozen=True, slots=True)
class Group(Node):
    items: tuple[Node, ...]
    modifiers: tuple[ModifierCall, ...] = ()


@dataclass(frozen=True, slots=True)
class BinOp(Node):
    op: Literal["+", "-", "*", "/", "//", "%"]
    left: Node
    right: Node


@dataclass(frozen=True, slots=True)
class Negate(Node):
    operand: Node


@dataclass(frozen=True, slots=True)
class Comparison(Node):
    op: Literal["==", "<>", "<", "<=", ">", ">=", "in"]
    left: Node
    right: Node


@dataclass(frozen=True, slots=True)
class Logic(Node):
    op: Literal["and", "or"]
    left: Node
    right: Node


@dataclass(frozen=True, slots=True)
class Not(Node):
    operand: Node


@dataclass(frozen=True, slots=True)
class Text(Node):
    value: str


@dataclass(frozen=True, slots=True)
class Bool(Node):
    value: bool


@dataclass(frozen=True, slots=True)
class Call(Node):
    name: str
    args: tuple[Node, ...]


@dataclass(frozen=True, slots=True)
class Var(Node):
    path: str


@dataclass(frozen=True, slots=True)
class Tagged(Node):
    tag: str
    inner: Node


@dataclass(frozen=True, slots=True)
class Labeled(Node):
    inner: Node
    label: str


@dataclass(frozen=True, slots=True)
class Repeat(Node):
    times: int
    inner: Node


# ------------------------------------------------------------------------- registry


@dataclass(frozen=True, slots=True)
class ModifierSpec:
    """A dice modifier: built-in or added by a pack plugin."""

    name: str  # unique, e.g. "keep-highest" or "lucky.charm"
    tokens: tuple[str, ...]  # spellings; the first is canonical
    order: int  # application order (lower first)
    arg: ArgKind
    apply: ModifierFunc
    summary: str
    default_arg: int | None = None
    groups: bool = False  # also valid on {group} pools
    bare_number_compare: bool = True  # `r1` means `r=1`
    quiet_default: bool = False  # canonical form omits the default number (`mt`, not `mt2`)

    @property
    def token(self) -> str:
        """The canonical spelling ("" for success counting, which is written as `>=8`)."""
        return self.tokens[0] if self.tokens else ""


@dataclass(frozen=True, slots=True)
class Macro:
    """A named expression template, e.g. `mysys.attack(a, b)` = `{$a, $b}kh1`."""

    name: str
    params: tuple[str, ...]
    template: str
    summary: str = ""

    def expand(self, args: list[str]) -> str:
        """The template with each `$param` (or `$1`, `$2`, …) replaced by `(arg)`."""
        if len(args) != len(self.params):
            wanted = ", ".join(self.params)
            raise ValueError(
                ngettext(
                    "{name}() takes {n} argument(s): {wanted}",
                    "{name}() takes {n} argument(s): {wanted}",
                    len(self.params),
                    name=self.name,
                    wanted=wanted,
                )
            )
        text = self.template
        # longest names first, so `$ab` is not clobbered by `$a`
        order = sorted(range(len(args)), key=lambda i: -len(self.params[i]))
        for i in order:
            text = text.replace(f"${self.params[i]}", f"({args[i]})")
        for i in reversed(range(len(args))):
            text = text.replace(f"${i + 1}", f"({args[i]})")
        return text


@dataclass(slots=True)
class Registry:
    """Modifiers, named dice, functions, macros and dice chains. Packs add to the same registry."""

    modifiers: dict[str, ModifierSpec] = field(default_factory=dict)
    dice: dict[str, DieSpec] = field(default_factory=dict)
    functions: dict[str, Callable[..., Value]] = field(default_factory=dict)
    macros: dict[str, Macro] = field(default_factory=dict)
    chains: dict[str, tuple[int, ...]] = field(default_factory=lambda: dict(CHAINS))
    canonical_cache: dict[Node, str] = field(default_factory=dict)  # see parser.canonical
    _tokens: list[tuple[str, ModifierSpec]] = field(default_factory=list)

    def add_modifier(self, spec: ModifierSpec) -> None:
        if spec.name in self.modifiers:
            raise ValueError(_("modifier {name} is already registered", name=repr(spec.name)))
        taken = {token for token, _spec in self._tokens}
        clash = [t for t in spec.tokens if t in taken]
        if clash:
            raise ValueError(
                ngettext(
                    "modifier token(s) {tokens} already in use",
                    "modifier token(s) {tokens} already in use",
                    len(clash),
                    tokens=clash,
                )
            )
        self.modifiers[spec.name] = spec
        self._tokens.extend((t, spec) for t in spec.tokens)
        self._tokens.sort(key=lambda item: -len(item[0]))  # longest match first
        self.canonical_cache.clear()  # a new spelling can change how text reads back

    def match_modifier(self, text: str, pos: int) -> tuple[str, ModifierSpec] | None:
        for token, spec in self._tokens:
            if text.startswith(token, pos):
                return token, spec
        return None

    def add_die(self, name: str, spec: DieSpec) -> None:
        if name in self.dice:
            raise ValueError(_("die {name} is already registered", name=repr(name)))
        self.dice[name] = DieSpec(spec.kind, spec.sides, spec.digits, spec.faces, name)

    def add_function(self, name: str, func: Callable[..., Value]) -> None:
        if name in self.functions or name in self.macros:
            raise ValueError(_("function {name} is already registered", name=repr(name)))
        self.functions[name] = func

    def add_macro(self, macro: Macro) -> None:
        if macro.name in self.functions or macro.name in self.macros:
            raise ValueError(_("function {name} is already registered", name=repr(macro.name)))
        self.macros[macro.name] = macro

    def add_chain(self, name: str, sides: tuple[int, ...]) -> None:
        if name in self.chains:
            raise ValueError(_("dice chain {name} is already registered", name=repr(name)))
        if list(sides) != sorted(set(sides)) or not sides:
            raise ValueError(_("a dice chain lists die sizes from smallest to largest"))
        self.chains[name] = sides

    def copy(self) -> Registry:
        """An independent copy, so packs can extend it without touching the original."""
        clone = Registry(
            dict(self.modifiers), dict(self.dice), dict(self.functions), dict(self.macros)
        )
        clone.chains = dict(self.chains)
        clone._tokens = list(self._tokens)
        return clone
