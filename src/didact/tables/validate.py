"""Checking tables, decks and bags when a pack is built: keys, coverage, overlaps, shapes."""

from didact.core.i18n import _
from didact.core.output import JSON
from didact.packs.kinds import register_validator
from didact.packs.source import Doc, Problem
from didact.tables.model import Band, parse_key

TABLE_KEYS = frozenset({
    "table", "title", "description", "dice", "entries", "columns", "lookup", "refs", "clamp",
    "duplicates", "source", "tags", "data", "remember", "labels", "both_ways", "read", "about",
})  # fmt: skip
ENTRY_KEYS = frozenset(
    {"text", "name", "data", "then", "table", "roll", "weight", "source", "note", "repeat"}
)
DUPLICATES = ("reroll", "keep", "make_it_worse")
MAX_VALUES = 10_000


def check_table(doc: Doc) -> list[Problem]:
    data = doc.data
    problems = [
        doc.problem(
            (key,),
            _("unknown key `{key}`", key=key),
            _("tables take: {keys}", keys=", ".join(sorted(TABLE_KEYS))),
        )
        for key in sorted(set(data) - TABLE_KEYS)
    ]
    entries = data.get("entries")
    if entries is None:
        return [
            *problems,
            doc.problem(
                (),
                _("a table needs `entries`"),
                _("e.g. entries: {1-3: calm, 4-6: storm}"),
            ),
        ]
    if data.get("duplicates", "reroll") not in DUPLICATES:
        problems.append(
            doc.problem(
                ("duplicates",),
                _("`duplicates` must be one of: {values}", values=", ".join(DUPLICATES)),
            )
        )
    dice = data.get("dice")
    if dice is not None and not isinstance(dice, str | int):
        problems.append(doc.problem(("dice",), _("`dice` must be an expression like d6 or 2d6")))
    lookup = data.get("lookup")
    if lookup:
        depth = len(lookup) if isinstance(lookup, list) else 1
        problems.extend(_check_lookup(doc, entries, depth))
        return problems
    if isinstance(entries, list):
        for index, entry in enumerate(entries):
            problems.extend(_check_entry(doc, ("entries", index), entry, data))
        return problems
    if not isinstance(entries, dict):
        return [*problems, doc.problem(("entries",), _("`entries` must be a mapping or a list"))]
    percentile = isinstance(dice, str) and dice.replace(" ", "") in ("d100", "1d100", "d%", "1d%")
    bands: list[Band] = []
    for key, entry in entries.items():
        try:
            band = parse_key(key, percentile=percentile)
        except ValueError as exc:
            problems.append(doc.problem(("entries", key), str(exc)))
            continue
        for other in bands:
            if band.low <= other.high and other.low <= band.high:
                problems.append(
                    doc.problem(
                        ("entries", key),
                        _(
                            "entries {first} and {second} overlap",
                            first=other.label,
                            second=band.label,
                        ),
                    )
                )
        bands.append(band)
        problems.extend(_check_entry(doc, ("entries", key), entry, data))
    if bands and isinstance(dice, str) and not problems:
        problems.extend(_check_coverage(doc, dice, bands, bool(data.get("clamp"))))
    return problems


def _check_entry(
    doc: Doc, loc: tuple[str | int, ...], entry: JSON, table: dict[str, JSON]
) -> list[Problem]:
    columns = table.get("columns")
    if isinstance(columns, list) and columns:
        if not isinstance(entry, list):
            return []  # one value fills every column (roll the same list once per column)
        if len(entry) != len(columns):
            return [
                doc.problem(
                    loc,
                    _(
                        "each row needs {n} values ({columns})",
                        n=len(columns),
                        columns=", ".join(map(str, columns)),
                    ),
                )
            ]
        return []
    if isinstance(entry, dict):
        unknown = sorted(set(entry) - ENTRY_KEYS)
        if unknown:
            takes = ", ".join(sorted(ENTRY_KEYS))
            message = _("unknown entry key `{key}`", key=unknown[0])
            hint = _("entries take: {keys}", keys=takes)
            return [doc.problem((*loc, unknown[0]), message, hint)]
    return []


def _check_lookup(doc: Doc, entries: JSON, depth: int) -> list[Problem]:
    level: list[tuple[tuple[str | int, ...], JSON]] = [(("entries",), entries)]
    for _level in range(depth):
        nested: list[tuple[tuple[str | int, ...], JSON]] = []
        for loc, node in level:
            if not isinstance(node, dict) or not node:
                return [
                    doc.problem(
                        loc,
                        _(
                            "a lookup by {depth} key(s) needs {depth} level(s) of entries",
                            depth=depth,
                        ),
                    )
                ]
            nested.extend(((*loc, k), v) for k, v in node.items())
        level = nested
    return []


def _check_coverage(doc: Doc, dice: str, bands: list[Band], clamp: bool) -> list[Problem]:
    """Every result the dice can roll must land on an entry (past the ends is fine with clamp)."""
    values = possible(dice)
    if values is None:
        return []
    covered = [v for v in values if any(b.covers(v) for b in bands)]
    missing = sorted(set(values) - set(covered))
    low, high = min(b.low for b in bands), max(b.high for b in bands)
    if clamp:
        missing = [v for v in missing if low <= v <= high]
    if not missing:
        return []
    shown = ", ".join(str(v) for v in missing[:8]) + (" …" if len(missing) > 8 else "")
    hint = (
        _("add entries for them")
        if clamp
        else _("add entries for them, or `clamp: true` for rolls past the ends")
    )
    message = _("{dice} can roll {shown}, which no entry covers", dice=dice, shown=shown)
    return [doc.problem(("entries",), message, hint)]


def possible(dice: str) -> list[int] | None:
    """Every total a simple dice expression can roll (None when it's not simple)."""
    from didact.core.errors import InvalidError
    from didact.expr import default_registry, parse
    from didact.expr.model import BinOp, Dice, Negate, Node, Number

    def values(node: Node) -> set[int] | None:
        match node:
            case Number(value=int() as number):
                return {number}
            case Dice(count=Number(value=int() as count), die=die, modifiers=()):
                if die.kind == "custom" and die.symbolic:
                    return None
                faces = _faces(die)
                totals = {0}
                for _die in range(count):
                    totals = {t + f for t in totals for f in faces}
                    if len(totals) > MAX_VALUES:
                        return None
                return totals
            case BinOp(op="+" | "-" as op, left=left, right=right):
                a, b = values(left), values(right)
                if a is None or b is None or len(a) * len(b) > MAX_VALUES * 10:
                    return None
                return {x + y if op == "+" else x - y for x in a for y in b}
            case Negate(operand=operand):
                inner = values(operand)
                return None if inner is None else {-v for v in inner}
        return None

    try:
        found = values(parse(str(dice), default_registry()))
    except InvalidError:
        return None
    return sorted(found) if found is not None else None


def _faces(die: object) -> list[int]:
    from didact.expr.modifiers import faces

    return list(faces(die))  # type: ignore[arg-type]


def check_deck(doc: Doc) -> list[Problem]:
    data = doc.data
    cards, standard = data.get("cards"), data.get("standard")
    if not (isinstance(cards, list) and cards) and not standard:
        return [doc.problem((), _("a deck needs `cards: [...]` or `standard: true` (52 cards)"))]
    jokers = data.get("jokers", 0)
    if not isinstance(jokers, int) or jokers < 0:
        return [doc.problem(("jokers",), _("`jokers` must be a number"))]
    return []


def check_bag(doc: Doc) -> list[Problem]:
    tokens = doc.data.get("tokens")
    if not isinstance(tokens, dict) or not tokens:
        return [
            doc.problem(
                (),
                _("a bag needs `tokens: {name: count, …}`"),
                _("e.g. tokens: {pc: 2, end-of-round: 1}"),
            )
        ]
    problems: list[Problem] = []
    for name, count in tokens.items():
        if not isinstance(count, int | str) or isinstance(count, bool):
            problems.append(
                doc.problem(
                    ("tokens", name),
                    _("`{name}` needs a count (a number or an expression)", name=name),
                )
            )
    return problems


register_validator("table", check_table)
register_validator("deck", check_deck)
register_validator("bag", check_bag)
