"""Turn a result tree into one readable line and into JSON-safe data.

    #r12 4d6kh3 → [6 5 3 (2)] = 14
    #r13 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
    #r14 d20 <= @STR → [7] <= @STR(12) = true
    #r15 2d6 → [3 4] = 7                   (asked as `(@wits + @spark)d6`: counts show as rolled)

Dice: `(2)` dropped · `6!` exploded · `1→4` rerolled or clamped · `6+6+2` compounded ·
`6-1` penetrating · `✓`/`✗` success/failure · `purr:3` added by a pack effect.
"""

from collections import Counter

from didact.core.i18n import ngettext
from didact.core.output import JSON
from didact.core.phrases import english, translated
from didact.expr.engine import (
    CallResult,
    CompareResult,
    ConstResult,
    Die,
    GroupResult,
    LogicResult,
    NegResult,
    NotResult,
    OpResult,
    Pool,
    PoolResult,
    RepeatResult,
    Result,
    VarResult,
    show,
)
from didact.expr.model import Value, to_json

_PRECEDENCE = {"or": 1, "and": 2, "not": 3, "cmp": 4, "+": 5, "-": 5, "*": 6, "/": 6, "//": 6}
_PRECEDENCE |= {"%": 6, "neg": 7}


def number(value: Value) -> str:
    """A value for display: numbers and true/false as is, text quoted, lists in brackets."""
    return show(value)


# ---------------------------------------------------------------------------- one line


def die_text(die: Die) -> str:
    if die.symbols:
        text = "+".join(die.symbols)
    elif die.spec.symbolic and die.value == 0:
        text = "·"  # a blank face
    elif die.parts:
        text = "+".join(str(p) for p in die.parts)
    elif die.penalty:
        text = f"{die.face}-{die.penalty}"
    else:
        text = str(die.value)
    if die.history:
        text = "→".join([*(str(h) for h in die.history), text])
    if die.exploded and not die.parts:
        text += "!"
    if die.success:
        text += "✓"
    elif die.failure:
        text += "✗"
    if die.added_by and die.added_by != "explode":
        text = f"{die.added_by.rpartition('.')[2]}:{text}"
    return text if die.kept else f"({text})"


def detail(result: Result, parent: int = 0) -> str:
    """The rolled expression with every die shown, e.g. `[6 5 3 (2)] + 2`."""
    text = _detail(result, parent)
    if result.tag:
        text = f"{result.tag}:{text}"
    if result.label:
        text = f"{text} {result.label}"
    return text


def _detail(result: Result, parent: int) -> str:
    match result:
        case PoolResult(pool=pool, count=count):
            dice = "[" + " ".join(die_text(d) for d in pool.dice) + "]"
            if count is None or not _rolled(count):  # a count from values: `2d6` says it
                return dice
            return f"({detail(count)}){dice}"  # a rolled count: `([1 2])[8 8 8]`
        case GroupResult(pool=pool):
            items = [detail(i.result) + _mark(i) for i in pool.items]
            shown = [
                text if i.kept else f"({text})" for text, i in zip(items, pool.items, strict=True)
            ]
            return "{" + ", ".join(shown) + "}"
        case OpResult(op=op, left=left, right=right):
            mine = _PRECEDENCE[op]
            text = f"{detail(left, mine)} {op} {detail(right, mine + 1)}"
            return f"({text})" if mine < parent else text
        case NegResult(operand=operand):
            return "-" + detail(operand, _PRECEDENCE["neg"])
        case CompareResult(op=op, left=left, right=right):
            inner = _PRECEDENCE["cmp"] + 1
            text = f"{detail(left, inner)} {op} {detail(right, inner)}"
            return f"({text})" if parent > _PRECEDENCE["cmp"] else text
        case LogicResult(op=op, left=left, right=right):
            mine = _PRECEDENCE[op]
            rest = detail(right, mine + 1) if right is not None else "…"
            text = f"{detail(left, mine)} {op} {rest}"
            return f"({text})" if mine < parent else text
        case NotResult(operand=operand):
            text = "not " + detail(operand, _PRECEDENCE["not"])
            return f"({text})" if _PRECEDENCE["not"] < parent else text
        case CallResult(name=name, args=args, expansion=expansion):
            inside = (
                detail(expansion) if expansion is not None else ", ".join(detail(a) for a in args)
            )
            return f"{name}({inside})"
        case VarResult(name=name, value=value):
            return f"@{name}({number(value)})"
        case ConstResult(value=value):
            return number(value)
        case RepeatResult(items=items):
            return "; ".join(f"{detail(i)} = {total_text(i)}{flag_suffix(i)}" for i in items)
    return number(result.value)


def _mark(item: object) -> str:
    success = getattr(item, "success", False)
    failure = getattr(item, "failure", False)
    return "✓" if success else "✗" if failure else ""


def total_text(result: Result) -> str:
    """The result's value in words where that helps: `3 successes`, `2 sets`."""
    pool = _pool_of(result)
    symbols = symbol_counts(result)
    if symbols and result.value == 0:
        return ", ".join(f"{name} {count}" for name, count in symbols.items())
    text = number(result.value)
    if pool is not None and pool.margin is None:
        match pool.count:
            case "successes":
                text = ngettext("{n} success", "{n} successes", int(pool.total))
            case "sets":
                text = ngettext("{n} set", "{n} sets", int(pool.total))
            case "sum":
                pass
    if symbols:
        text += " · " + ", ".join(f"{name} {count}" for name, count in symbols.items())
    return text


def line(label: str, canonical: str, result: Result, reason: str | None = None) -> str:
    """`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — Sweeney's attack`"""
    text = f"{label} {as_rolled(canonical, result)} → {detail(result)}".strip()
    if not isinstance(result, RepeatResult):  # each repeated roll shows its own total and flags
        text += f" = {total_text(result)}{flag_suffix(result)}"
    if reason:
        text += f" — {reason}"
    return text


def as_rolled(canonical: str, result: Result) -> str:
    """The expression as rolled: a pool counted from values alone (`(@wits + @spark)d6`) shows
    the number of dice it came to (`3d6`); a rolled count stays as written (`(2d4)d8`)."""
    for node in walk(result):
        if not isinstance(node, PoolResult) or node.count is None or _rolled(node.count):
            continue
        end = _count_end(node.canonical)
        count = node.count.value
        if end and isinstance(count, int | float) and not isinstance(count, bool):
            rolled = f"{int(count)}{node.canonical[end:]}"
            canonical = canonical.replace(node.canonical, rolled, 1)
    return canonical


def _rolled(result: Result) -> bool:
    """Whether dice went into a result (a pool's count, say)."""
    return any(isinstance(node, PoolResult | GroupResult) for node in walk(result))


def _count_end(canonical: str) -> int:
    """Where a pool's parenthesized count ends: `(@a + @b)d6` → 9; 0 without one."""
    depth = 0
    for index, char in enumerate(canonical):
        depth += {"(": 1, ")": -1}.get(char, 0)
        if depth == 0:
            return index + 1 if index else 0
    return 0


def flag_suffix(result: Result) -> str:
    """` (doubles, max)`, or ` (hope: max; fear: max)` when several pools have flags."""
    grouped: dict[str, list[str]] = {}
    for flag in collect_flags(result):
        owner, sep, name = flag.rpartition(": ")
        grouped.setdefault(owner if sep else "", []).append(name)
    if not grouped:
        return ""
    shown = [
        f"{owner}: {', '.join(names)}" if owner else ", ".join(names)
        for owner, names in grouped.items()
    ]
    return f" ({'; '.join(shown)})"


# ---------------------------------------------------------------------------- walking the tree


def children(result: Result) -> list[Result]:
    match result:
        case GroupResult(pool=pool):
            return [i.result for i in pool.items]
        case OpResult(left=left, right=right) | CompareResult(left=left, right=right):
            return [left, right]
        case NegResult(operand=operand):
            return [operand]
        case CallResult(args=args, expansion=expansion):
            return [*args, *([expansion] if expansion is not None else [])]
        case RepeatResult(items=items):
            return list(items)
    return []


def walk(result: Result) -> list[Result]:
    found = [result]
    for child in children(result):
        found.extend(walk(child))
    return found


def _pool_of(result: Result) -> Pool | None:
    match result:
        case PoolResult(pool=pool) | GroupResult(pool=pool):
            return pool
        case CallResult(expansion=expansion) if expansion is not None:
            return _pool_of(expansion)
    return None


def collect_flags(result: Result) -> list[str]:
    """Every pool's flags. With several dice pools, each flag names its pool: its tag or label
    if it has one, else its expression (`hope: max`, `3d6: doubles`)."""
    nodes = walk(result)
    several = sum(isinstance(n, PoolResult) for n in nodes) > 1
    flags: list[str] = []
    for node in nodes:
        if not isinstance(node, PoolResult | GroupResult):
            continue
        owner = node.tag or node.label or (node.canonical if several else "")
        for flag in sorted(node.pool.flags):
            text = f"{owner}: {flag}" if owner else flag
            if text not in flags:
                flags.append(text)
    return flags


def collect_notes(result: Result) -> list[str]:
    notes: list[str] = []
    for node in walk(result):
        pool = _pool_of(node) if isinstance(node, PoolResult | GroupResult) else None
        for note in pool.notes if pool else ():
            text = translated(note) if isinstance(note, dict) else note
            if text not in notes:
                notes.append(text)
    return notes


def symbol_counts(result: Result) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for node in walk(result):
        if isinstance(node, PoolResult):
            counts.update(node.pool.symbol_counts())
    return dict(sorted(counts.items()))


def parts(result: Result) -> dict[str, JSON]:
    """Tagged and labelled values, e.g. {"hope": 7, "fear": 3} for `hope:1d12 + fear:1d12`."""
    found: dict[str, JSON] = {}
    for node in walk(result):
        for name in (node.tag, node.label):
            if name and not isinstance(node, RepeatResult):
                found[name] = to_json(node.value)
    return found


# ---------------------------------------------------------------------------- data


def die_data(die: Die) -> dict[str, JSON]:
    data: dict[str, JSON] = {"value": die.value}
    if die.symbols:
        data["symbols"] = list(die.symbols)
    if not die.kept:
        data["kept"] = False
    for name in ("exploded", "success", "failure", "crit", "fumble"):
        if getattr(die, name):
            data[name] = True
    if die.history:
        data["was"] = list(die.history)
    if die.parts:
        data["parts"] = list(die.parts)
    if die.penalty:
        data["penalty"] = die.penalty
    if die.added_by:
        data["added_by"] = die.added_by
    return data


def to_data(result: Result) -> dict[str, JSON]:
    data: dict[str, JSON] = {"value": to_json(result.value)}
    if result.tag:
        data["tag"] = result.tag
    if result.label:
        data["label"] = result.label
    match result:
        case PoolResult(canonical=text, pool=pool, count=count):
            data |= {"type": "dice", "expr": text, "dice": [die_data(d) for d in pool.dice]}
            if count is not None:
                data["count"] = to_data(count)
            data |= _pool_data(pool)
            symbols = pool.symbol_counts()
            if symbols:
                data["symbols"] = dict(symbols)
        case GroupResult(canonical=text, pool=pool):
            items: list[JSON] = []
            for item in pool.items:
                entry = to_data(item.result)
                if not item.kept:
                    entry["kept"] = False
                if item.success:
                    entry["success"] = True
                if item.failure:
                    entry["failure"] = True
                items.append(entry)
            data |= {"type": "group", "expr": text, "items": items}
            data |= _pool_data(pool)
        case OpResult(op=op, left=left, right=right):
            data |= {"type": "op", "op": op, "left": to_data(left), "right": to_data(right)}
        case NegResult(operand=operand):
            data |= {"type": "negate", "operand": to_data(operand)}
        case CompareResult(op=op, left=left, right=right):
            data |= {"type": "compare", "op": op, "left": to_data(left), "right": to_data(right)}
        case CallResult(name=name, args=args, expansion=expansion):
            data |= {"type": "call", "name": name, "args": [to_data(a) for a in args]}
            if expansion is not None:
                data["expansion"] = to_data(expansion)
        case VarResult(name=name):
            data |= {"type": "var", "name": name}
        case RepeatResult(items=repeated):
            data |= {"type": "repeat", "items": [to_data(i) for i in repeated]}
            data.pop("value")
        case _:
            data["type"] = "number"
    return data


def _pool_data(pool: Pool) -> dict[str, JSON]:
    data: dict[str, JSON] = {}
    match pool.count:
        case "successes":
            data |= {"successes": pool.successes, "failures": pool.failures}
        case "sets":
            data["sets"] = {number(v): n for v, n in pool.sets().items()}
        case "sum":
            pass
    if pool.margin is not None:
        data["margin"] = {"target": pool.margin.text(), "value": pool.value}
    if pool.flags:
        data["flags"] = list[JSON](sorted(pool.flags))
    if pool.notes:  # English, as the log keeps it
        data["notes"] = [english(n) if isinstance(n, dict) else n for n in pool.notes]
    return data
