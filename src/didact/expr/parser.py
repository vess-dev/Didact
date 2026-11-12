"""Parse dice expressions (hand-written, registry-driven) and print their canonical form.

Grammar (lowest precedence first):

    expr        := and ("or" and)*
    and         := not ("and" not)*
    not         := "not" not | compare
    compare     := sum (CMP sum)?                     CMP: == = <> < <= > >= in (spaced)
    sum         := product (("+" | "-") product)*
    product     := unary (("*" | "/" | "//" | "%") unary)*
    unary       := "-" unary | postfix
    postfix     := primary modifier* ("[" label "]")?
    primary     := NUMBER | NUMBER "#" postfix | dice | "(" expr ")" ["d" faces] | 'text'
                 | true | false | "{" expr ("," expr)* "}" | NAME "(" args ")"
                 | NAME ":" postfix | "@" var
    dice        := [count] "d" faces       faces: N | % | F | 66 | {1,2,…} | [name]

Modifiers attach directly to dice or groups (no space): `4d6kh3`, `6d10>=8f1`, `{d8,d6}kh1`.
A comparison written right after a pool counts successes; with spaces it compares totals.
"""

import re

from didact.core.errors import InvalidError, UnknownName
from didact.core.i18n import _
from didact.expr.model import (
    COMPARE_OPS,
    FUDGE,
    BinOp,
    Bool,
    Call,
    CompareOp,
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
    Span,
    Tagged,
    Text,
    Var,
    numeric,
)

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_-]*)*")
_TAG = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
_VAR = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*")
_DIGIT_DIE = re.compile(r"([2-9])\1{1,2}$")
KEYWORDS = frozenset({"and", "or", "not", "in", "true", "false"})
MAX_SIDES = 1_000_000


class Parser:
    def __init__(self, text: str, registry: Registry) -> None:
        self.text = text
        self.pos = 0
        self.registry = registry

    # ------------------------------------------------------------------ helpers

    def fail(
        self, message: str, hint: str | None = None, at: int | None = None, unknown: str = ""
    ) -> InvalidError:
        """The error for this spot; `unknown` (`die`, `name`) when a name isn't known."""
        where = self.pos if at is None else at
        pointer = f"{self.text}\n{' ' * where}^"
        said = _("{message} at position {position}", message=message, position=where + 1)
        if unknown:
            return UnknownName(said, what=unknown, where=pointer, hint=hint)
        return InvalidError(said, where=pointer, hint=hint)

    def skip_ws(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            self.pos += 1

    def peek(self, ahead: int = 0) -> str:
        index = self.pos + ahead
        return self.text[index] if index < len(self.text) else ""

    def take(self, literal: str) -> bool:
        if self.text.startswith(literal, self.pos):
            self.pos += len(literal)
            return True
        return False

    def expect(self, literal: str, hint: str | None = None) -> None:
        if not self.take(literal):
            found = self.peek() or _("the end")
            raise self.fail(
                _("expected {literal} but found {found}", literal=repr(literal), found=repr(found)),
                hint,
            )

    # ------------------------------------------------------------------ grammar

    def parse(self) -> Node:
        self.skip_ws()
        if not self.text.strip():
            raise InvalidError(_("empty expression"), hint=_("e.g. `2d6+1` or `4d6kh3`"))
        node = self.expression()
        self.skip_ws()
        if self.pos < len(self.text):
            hint = None
            if self.text[self.pos - 1 : self.pos].isspace() and self.registry.match_modifier(
                self.text, self.pos
            ):
                hint = _("modifiers attach directly to the dice, e.g. `4d6kh3` (no space)")
            raise self.fail(_("unexpected {text}", text=repr(self.text[self.pos :])), hint)
        return node

    def keyword(self, word: str) -> bool:
        """Take `word` if it comes next as a whole word (`or`, but not the start of `order`)."""
        self.skip_ws()
        end = self.pos + len(word)
        if self.text.startswith(word, self.pos) and not (
            end < len(self.text) and (self.text[end].isalnum() or self.text[end] == "_")
        ):
            self.pos = end
            return True
        return False

    def expression(self) -> Node:
        self.skip_ws()
        start = self.pos
        node = self.conjunction()
        while self.keyword("or"):
            node = Logic(Span(start, self.pos), "or", node, self.conjunction())
        return node

    def conjunction(self) -> Node:
        self.skip_ws()
        start = self.pos
        node = self.negation()
        while self.keyword("and"):
            node = Logic(Span(start, self.pos), "and", node, self.negation())
        return node

    def negation(self) -> Node:
        self.skip_ws()
        start = self.pos
        if self.keyword("not"):
            return Not(Span(start, self.pos), self.negation())
        return self.comparison()

    def comparison(self) -> Node:
        start = self.pos
        left = self.sum()
        self.skip_ws()
        if self.keyword("in"):
            return Comparison(Span(start, self.pos), "in", left, self.sum())
        for op in ("==", "<>", "<=", ">=", "!=", "<", ">", "="):
            if self.text.startswith(op, self.pos):
                if op == "!=":
                    raise self.fail(_("`!=` isn't supported"), hint=_("use `<>` for not-equal"))
                self.pos += len(op)
                right = self.sum()
                normalized = "==" if op == "=" else op
                return Comparison(Span(start, self.pos), normalized, left, right)  # type: ignore[arg-type]
        return left

    def sum(self) -> Node:
        start = self.pos
        node = self.product()
        while True:
            self.skip_ws()
            op = self.peek()
            if op not in ("+", "-"):
                return node
            self.pos += 1
            right = self.product()
            node = BinOp(Span(start, self.pos), op, node, right)  # type: ignore[arg-type]

    def product(self) -> Node:
        start = self.pos
        node = self.unary()
        while True:
            self.skip_ws()
            if self.take("//"):
                op = "//"
            elif self.peek() in ("*", "/", "%"):
                op = self.peek()
                self.pos += 1
            else:
                return node
            right = self.unary()
            node = BinOp(Span(start, self.pos), op, node, right)  # type: ignore[arg-type]

    def unary(self) -> Node:
        self.skip_ws()
        start = self.pos
        if self.take("-"):
            operand = self.unary()
            return Negate(Span(start, self.pos), operand)
        if self.take("+"):
            return self.unary()
        return self.postfix()

    def postfix(self) -> Node:
        start = self.pos
        node = self.primary()
        if isinstance(node, Dice | Group):
            modifiers = node.modifiers + self.modifiers(node)  # `(4d6dl1)kh2` keeps both
            if isinstance(node, Dice):
                node = Dice(node.span, node.count, node.die, modifiers)
            else:
                node = Group(node.span, node.items, modifiers)
        if self.peek() == "[":
            self.pos += 1
            end = self.text.find("]", self.pos)
            if end < 0:
                raise self.fail(_("unclosed label"), hint=_("labels look like `d8[fire]`"))
            label = self.text[self.pos : end].strip()
            self.pos = end + 1
            node = Labeled(Span(start, self.pos), node, label)
        return node

    def primary(self) -> Node:
        self.skip_ws()
        start = self.pos
        char = self.peek()
        if not char:
            raise self.fail(_("the expression ends too early"), hint=_("finish it, e.g. `2d6+1`"))
        if char == "(":
            self.pos += 1
            inner = self.expression()
            self.skip_ws()
            self.expect(")", hint=_("close the parenthesis"))
            if self._at_dice():
                return self.dice(start, inner)
            return inner
        if char == "{":
            return self.group()
        if char == "@":
            return self.variable()
        if char in ("'", '"'):
            end = self.text.find(char, self.pos + 1)
            if end < 0:
                raise self.fail(
                    _("unclosed text"), hint=_("close it with {quote}", quote=char), at=start
                )
            self.pos = end + 1
            return Text(Span(start, self.pos), self.text[start + 1 : end])
        if char.isdigit():
            match = _NUMBER.match(self.text, self.pos)
            assert match
            text = match.group()
            self.pos = match.end()
            number: int | float = float(text) if "." in text else int(text)
            if self.take("#"):
                if not isinstance(number, int) or not 1 <= number <= 100:
                    raise self.fail(_("repeat counts must be 1–100"), at=start)
                inner = self.postfix()
                if isinstance(inner, Repeat):
                    raise self.fail(
                        _("repeats can't be nested"), hint=_("e.g. `6#4d6dl1`"), at=start
                    )
                return Repeat(Span(start, self.pos), number, inner)
            if self._at_dice():
                if not isinstance(number, int):
                    raise self.fail(_("dice counts must be whole numbers"), at=start)
                return self.dice(start, Number(Span(start, self.pos), number))
            return Number(Span(start, self.pos), number)
        if self._at_dice():
            return self.dice(start, Number(Span(start, start), 1))
        name_match = _NAME.match(self.text, self.pos)
        if name_match:
            name = name_match.group()
            after = name_match.end()
            if name in ("true", "false"):
                self.pos = after
                return Bool(Span(start, self.pos), name == "true")
            if name in KEYWORDS:
                raise self.fail(
                    _("unexpected `{name}`", name=name), hint=_("it needs a value on each side")
                )
            if self.text.startswith("(", after):
                self.pos = after + 1
                args = self.arguments()
                return Call(Span(start, self.pos), name, args)
            tag_match = _TAG.match(self.text, self.pos)
            if tag_match and self.text.startswith(":", tag_match.end()):
                self.pos = tag_match.end() + 1
                inner = self.postfix()
                return Tagged(Span(start, self.pos), tag_match.group(), inner)
            raise self.fail(
                _("unknown name {name}", name=repr(name)),
                hint=_("variables start with @ (`@STR`), functions need parentheses (`max(1, 2)`)"),
                unknown="name",
            )
        raise self.fail(
            _("unexpected {char}", char=repr(char)),
            hint=_("expressions look like `2d6+1`, `d20 <= @DEX`, `{d8,d6}kh1`"),
        )

    def arguments(self) -> tuple[Node, ...]:
        args: list[Node] = []
        self.skip_ws()
        if self.take(")"):
            return ()
        while True:
            args.append(self.expression())
            self.skip_ws()
            if self.take(")"):
                return tuple(args)
            self.expect(",", hint=_("separate arguments with commas"))

    def group(self) -> Group:
        start = self.pos
        self.expect("{")
        items: list[Node] = []
        while True:
            items.append(self.expression())
            self.skip_ws()
            if self.take("}"):
                break
            if not self.peek():
                raise self.fail(
                    _("unclosed group"), hint=_("close it with `}`, e.g. `{d8, d6}kh1`")
                )
            self.expect(",", hint=_("separate group items with commas, e.g. `{d8, d6}kh1`"))
        return Group(Span(start, self.pos), tuple(items))

    def variable(self) -> Var:
        start = self.pos
        self.expect("@")
        if self.take("{"):
            end = self.text.find("}", self.pos)
            if end < 0:
                raise self.fail(_("unclosed variable"), hint=_("write `@{mechanics.my-system.hp}`"))
            path = self.text[self.pos : end].strip()
            self.pos = end + 1
        else:
            match = _VAR.match(self.text, self.pos)
            if not match:
                raise self.fail(
                    _("expected a variable name after @"), hint=_("e.g. `@STR` or `@hp`")
                )
            path = match.group()
            self.pos = match.end()
        return Var(Span(start, self.pos), path)

    # ------------------------------------------------------------------ dice

    def _at_dice(self) -> bool:
        if self.peek() not in ("d", "D"):
            return False
        nxt = self.peek(1)
        if nxt.isdigit() or nxt in ("%", "{", "["):
            return True
        if nxt in ("F", "f"):
            after = self.peek(2)
            return not (after.isalnum() or after == "_")
        return False

    def dice(self, start: int, count: Node) -> Dice:
        self.pos += 1  # the "d"
        die = self.die_spec()
        return Dice(Span(start, self.pos), count, die)

    def die_spec(self) -> DieSpec:
        char = self.peek()
        if char == "%":
            self.pos += 1
            return numeric(100)
        if char in ("F", "f"):
            self.pos += 1
            return FUDGE
        if char == "{":
            return self.custom_faces()
        if char == "[":
            self.pos += 1
            end = self.text.find("]", self.pos)
            if end < 0:
                raise self.fail(_("unclosed die name"), hint=_("pack dice look like `2d[boost]`"))
            name = self.text[self.pos : end].strip()
            self.pos = end + 1
            spec = self.registry.dice.get(name)
            if spec is None:
                known = ", ".join(sorted(self.registry.dice)) or _("none are loaded")
                raise self.fail(
                    _("unknown die [{name}]", name=name),
                    hint=_("named dice come from packs ({known})", known=known),
                    unknown="die",
                )
            return spec
        match = re.compile(r"\d+").match(self.text, self.pos)
        if not match:
            raise self.fail(
                _("expected the number of sides after `d`"), hint=_("e.g. `d6`, `d%`, `dF`, `d66`")
            )
        text = match.group()
        self.pos = match.end()
        if _DIGIT_DIE.match(text):
            return DieSpec("digit", int(text[0]), digits=len(text))
        sides = int(text)
        if not 1 <= sides <= MAX_SIDES:
            raise self.fail(_("a die needs 1–{most} sides", most=MAX_SIDES), at=match.start())
        return numeric(sides)

    def custom_faces(self) -> DieSpec:
        start = self.pos
        self.expect("{")
        end = self.text.find("}", self.pos)
        if end < 0:
            raise self.fail(
                _("unclosed face list"), hint=_("custom dice look like `d{0,0,1,1,2,3}`")
            )
        raw = self.text[self.pos : end]
        self.pos = end + 1
        faces: list[Face] = []
        for part in raw.split(","):
            item = part.strip()
            if not item or item == "-":
                faces.append(Face(0, ()))
            elif re.fullmatch(r"-?\d+", item):
                faces.append(Face(int(item), ()))
            elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\+[A-Za-z_][A-Za-z0-9_]*)*", item):
                faces.append(Face(0, tuple(item.split("+"))))
            else:
                raise self.fail(
                    _("invalid face {face}", face=repr(item)),
                    hint=_("faces are numbers or symbol names"),
                    at=start,
                )
        if len(faces) < 2:
            raise self.fail(_("a custom die needs at least two faces"), at=start)
        return DieSpec("custom", len(faces), faces=tuple(faces))

    # ------------------------------------------------------------------ modifiers

    def modifiers(self, pool: Dice | Group) -> tuple[ModifierCall, ...]:
        calls: list[ModifierCall] = []
        is_group = isinstance(pool, Group)
        while self.pos < len(self.text):
            start = self.pos
            op = next((o for o in COMPARE_OPS if self.text.startswith(o, self.pos)), None)
            if op is not None:
                if "success" not in self.registry.modifiers:
                    raise self.fail(_("success counting isn't available in this registry"))
                self.pos += len(op)
                point = ComparePoint(op, self.compare_value())
                calls.append(ModifierCall("success", point, Span(start, self.pos)))
                continue
            if self.text.startswith("!=", self.pos):
                raise self.fail(
                    _("`!=` is ambiguous"),
                    hint=_("write `!6` to explode on 6, or `<>` for not-equal"),
                )
            found = self.registry.match_modifier(self.text, self.pos)
            if found is None:
                break
            token, spec = found
            self.pos += len(token)
            if is_group and not spec.groups:
                raise self.fail(_("`{token}` can't be used on a {{group}}", token=token), at=start)
            arg = self.modifier_arg(spec.arg, spec.bare_number_compare, spec.default_arg)
            calls.append(ModifierCall(spec.name, arg, Span(start, self.pos)))
        return tuple(calls)

    def modifier_arg(
        self, kind: str, bare_compare: bool, default: int | None
    ) -> int | ComparePoint | None:
        match kind:
            case "none":
                return None
            case "number":
                match = re.compile(r"\d+").match(self.text, self.pos)
                if match:
                    self.pos = match.end()
                    return int(match.group())
                return default
            case _:
                op: CompareOp | None = next(
                    (o for o in COMPARE_OPS if self.text.startswith(o, self.pos)), None
                )
                if op is not None:
                    self.pos += len(op)
                    return ComparePoint(op, self.compare_value())
                if bare_compare and (self.peek().isdigit() or self.peek() == "@"):
                    return ComparePoint("=", self.compare_value())
                return None

    def compare_value(self) -> Node:
        start = self.pos
        if self.peek() == "@":
            return self.variable()
        negative = self.take("-")
        match = _NUMBER.match(self.text, self.pos)
        if not match:
            raise self.fail(
                _("expected a number to compare with"), hint=_("e.g. `>=8` or `<=@DEX`")
            )
        self.pos = match.end()
        text = match.group()
        value: int | float = float(text) if "." in text else int(text)
        return Number(Span(start, self.pos), -value if negative else value)


def parse(text: str, registry: Registry) -> Node:
    return Parser(text, registry).parse()


# ---------------------------------------------------------------------------- canonical form

_PRECEDENCE = {"or": 1, "and": 2, "not": 3, "cmp": 4, "+": 5, "-": 5, "*": 6, "/": 6, "//": 6}
_PRECEDENCE |= {"%": 6, "neg": 7}
ATOM = 8  # tighter than anything: never parenthesized


def canonical(node: Node, registry: Registry) -> str:
    """The normalized spelling of an expression, echoed back so dialect differences show."""
    cache = registry.canonical_cache
    text = cache.get(node)
    if text is None:
        text = cache[node] = _print(node, registry, 0)
    return text


def _print(node: Node, registry: Registry, parent: int) -> str:
    match node:
        case Number(value=value):
            return _number(value)
        case Dice(count=count, die=die, modifiers=mods):
            count_text = _print(count, registry, ATOM)
            if not isinstance(count, Number):
                count_text = f"({_print(count, registry, 0)})"
            return _with_mods(f"{count_text}d{die.text}", mods, registry)
        case Group(items=items, modifiers=mods):
            base = "{" + ", ".join(_print(i, registry, 0) for i in items) + "}"
            return _with_mods(base, mods, registry)
        case BinOp(op=op, left=left, right=right):
            mine = _PRECEDENCE[op]
            text = f"{_print(left, registry, mine)} {op} {_print(right, registry, mine + 1)}"
            return f"({text})" if mine < parent else text
        case Negate(operand=operand):
            return "-" + _print(operand, registry, _PRECEDENCE["neg"])
        case Comparison(op=op, left=left, right=right):
            inner = _PRECEDENCE["cmp"] + 1
            text = f"{_print(left, registry, inner)} {op} {_print(right, registry, inner)}"
            return f"({text})" if parent > _PRECEDENCE["cmp"] else text
        case Logic(op=op, left=left, right=right):
            mine = _PRECEDENCE[op]
            text = f"{_print(left, registry, mine)} {op} {_print(right, registry, mine + 1)}"
            return f"({text})" if mine < parent else text
        case Not(operand=operand):
            text = "not " + _print(operand, registry, _PRECEDENCE["not"])
            return f"({text})" if _PRECEDENCE["not"] < parent else text
        case Text(value=value):
            return f'"{value}"' if "'" in value else f"'{value}'"
        case Bool(value=value):
            return "true" if value else "false"
        case Call(name=name, args=args):
            return f"{name}(" + ", ".join(_print(a, registry, 0) for a in args) + ")"
        case Var(path=path):
            return f"@{path}" if re.fullmatch(_VAR.pattern, path) else f"@{{{path}}}"
        case Tagged(tag=tag, inner=inner):
            return f"{tag}:{_print(inner, registry, ATOM)}"
        case Labeled(inner=inner, label=label):
            return f"{_print(inner, registry, ATOM)}[{label}]"
        case Repeat(times=times, inner=inner):
            return f"{times}#{_print(inner, registry, ATOM)}"
    raise TypeError(f"cannot print {node!r}")


def _number(value: int | float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _with_mods(base: str, mods: tuple[ModifierCall, ...], registry: Registry) -> str:
    """The pool followed by its modifiers in application order.

    Adjacent spellings can run together (`!` + `!p` reads back as `!!` + `p`; a bare `!` before
    `>=8` would take `>=8` as its condition). Each modifier is checked by reading the text back;
    where it would read differently, the pool so far goes in parentheses: `(1d6!)>=8`.
    """
    ordered = sorted(mods, key=lambda m: registry.modifiers[m.name].order)
    parts = [_mod_text(m, registry) for m in ordered]
    text = base
    for i, part in enumerate(parts):
        if not _reads_back(text + part, parts[: i + 1], registry):
            text = f"({text})"
        text += part
    return text


def _reads_back(text: str, expected: list[str], registry: Registry) -> bool:
    try:
        node = Parser(text, registry).parse()
    except InvalidError:
        return False
    if not isinstance(node, Dice | Group):
        return False
    return [_mod_text(m, registry) for m in node.modifiers] == expected


def _mod_text(call: ModifierCall, registry: Registry) -> str:
    spec = registry.modifiers[call.name]
    text = spec.token
    match call.arg:
        case ComparePoint(op=op, value=value):
            bare = op == "=" and spec.bare_number_compare  # `r1` rather than `r=1`
            return text + ("" if bare else op) + _print(value, registry, 5)
        case int() as number if not (spec.quiet_default and number == spec.default_arg):
            return text + str(number)
        case _:
            return text
