"""The built-in dice modifiers and the default registry.

Order of application (lower first; plugins default to 80):

    10 min, max → 20 explode (!, !!, !p, !o) → 30 reroll (r, ro) → 40 unique (u, uo)
    → 50 keep (kh, kl) → 51 drop (dl, dh) → 60 successes (>=N), failures (f), even, odd
    → 70 crits (cs, cf) → 75 matches (mt) → 90 margin (ms) → 95 sort (sa, sd)
"""

from collections.abc import Callable, Iterable
from functools import partial

from didact.core.errors import InvalidError
from didact.core.i18n import N_, _, ngettext
from didact.core.phrases import phrase
from didact.expr.engine import MAX_DICE, DiePool, GroupPool, Pool, RollContext
from didact.expr.model import ArgKind, DieSpec, ModifierSpec, Registry, Target

type Arg = int | Target | None


def _dice(pool: Pool, token: str) -> DiePool:
    if not isinstance(pool, DiePool):
        raise InvalidError(
            _("`{token}` works on dice, not on {{groups}}", token=token),
            hint=_("put it right after the dice, e.g. `4d6kh3`"),
        )
    return pool


def _number(arg: Arg, token: str, example: str) -> int:
    if not isinstance(arg, int):
        raise InvalidError(
            _("`{token}` needs a number", token=token), hint=_("e.g. `{example}`", example=example)
        )
    return arg


def faces(spec: DieSpec) -> Iterable[int]:
    """Every value a die can show (large numeric dice are not enumerated)."""
    match spec.kind:
        case "numeric":
            return range(1, spec.sides + 1)
        case "fudge":
            return (-1, 0, 1)
        case "digit":
            values = [0]
            for _unused in range(spec.digits):
                values = [v * 10 + d for v in values for d in range(1, spec.sides + 1)]
            return values
        case "custom":
            return sorted({f.value for f in spec.faces})


def _every_face(spec: DieSpec, target: Target) -> bool:
    if spec.kind == "numeric" and spec.sides > 10_000:
        return target.test(1) and target.test(spec.sides) and target.op not in ("=", "<>")
    return all(target.test(v) for v in faces(spec))


def _no_face(spec: DieSpec, target: Target) -> bool:
    if spec.kind == "numeric" and spec.sides > 10_000:
        return not (target.test(1) or target.test(spec.sides))
    return not any(target.test(v) for v in faces(spec))


# ---------------------------------------------------------------------------- clamp


def clamp(pool: Pool, ctx: RollContext, arg: Arg, *, low: bool) -> None:
    token = "min" if low else "max"
    dice = _dice(pool, token)
    bound = _number(arg, token, f"4d6{token}{2 if low else 5}")
    for die in dice.dice:
        if (die.value < bound) if low else (die.value > bound):
            die.history.append(die.value)
            die.value = bound


# ---------------------------------------------------------------------------- explode


def explode(pool: Pool, ctx: RollContext, arg: Arg, *, how: str) -> None:
    """`!` adds a die, `!!` adds into the same die, `!p` adds a die worth one less, `!o` once."""
    token = {"explode": "!", "compound": "!!", "penetrate": "!p", "once": "!o"}[how]
    dice = _dice(pool, token)
    target = arg if isinstance(arg, Target) else Target("=", dice.spec.max_value)
    if _every_face(dice.spec, target):
        raise InvalidError(
            _(
                "`{modifier}` would explode forever: every face of d{die} matches",
                modifier=f"{token}{target.text()}",
                die=dice.spec.text,
            ),
            hint=_(
                "use a condition only some faces meet, e.g. `{example}`",
                example=f"{token}>={dice.spec.max_value}",
            ),
        )
    if how == "compound":
        for die in dice.dice:
            if not (die.explodable and die.kept):
                continue
            last = die.value
            while target.test(last) and dice.take_extra("explosion"):
                last = ctx.roll_die(dice.spec).value
                die.parts = die.parts or [die.value]
                die.parts.append(last)
                die.exploded = True
            if die.parts:
                die.value = sum(die.parts)
        return
    index = 0
    while index < len(dice.dice):
        die = dice.dice[index]
        if die.explodable and die.kept and target.test(die.face):
            if not dice.take_extra("explosion"):
                break
            die.exploded = True
            extra = ctx.roll_die(dice.spec)
            if how == "penetrate":
                extra.penalty = 1
                extra.value -= 1
            dice.add(extra, reason="explode", explode=how != "once", after=die)
        index += 1


# ---------------------------------------------------------------------------- reroll


def reroll(pool: Pool, ctx: RollContext, arg: Arg, *, once: bool) -> None:
    token = "ro" if once else "r"
    dice = _dice(pool, token)
    target = arg if isinstance(arg, Target) else Target("=", dice.spec.min_value)
    if not once and _every_face(dice.spec, target):
        raise InvalidError(
            _(
                "`{modifier}` would reroll forever: every face of d{die} matches",
                modifier=f"r{target.text()}",
                die=dice.spec.text,
            ),
            hint=_(
                "reroll only some faces, e.g. `{example}`, or use `ro` (once)",
                example=f"r{dice.spec.min_value}",
            ),
        )
    for die in dice.dice:
        if not die.kept:
            continue
        while target.test(die.value) and dice.take_extra("reroll"):
            ctx.reroll(die)
            dice.flags.add("rerolled")
            if once:
                break


def unique(pool: Pool, ctx: RollContext, arg: Arg, *, once: bool) -> None:
    token = "uo" if once else "u"
    dice = _dice(pool, token)
    kept = dice.kept()
    distinct = dice.spec.sides if dice.spec.sides > 10_000 else len(set(faces(dice.spec)))
    rolled = [d for d in kept if d.added_by is None]  # not the dice explosions added
    if not once and len(rolled) > distinct:
        raise InvalidError(
            ngettext(
                "{n} dice can't all differ on a d{die}",
                "{n} dice can't all differ on a d{die}",
                len(rolled),
                die=dice.spec.text,
            ),
            hint=_("roll fewer dice or use `uo` (reroll duplicates once)"),
        )
    seen: set[int] = set()
    for die in kept:
        if len(seen) >= distinct:  # explosions added more dice than there are faces
            dice.notes.append(
                phrase(
                    N_("every face of d{die} is taken: the extra dice repeat"), die=dice.spec.text
                )
            )
            break
        while die.value in seen and dice.take_extra("reroll"):
            ctx.reroll(die)
            dice.flags.add("rerolled")
            if once:
                break
        seen.add(die.value)


# ---------------------------------------------------------------------------- keep / drop


def select(pool: Pool, ctx: RollContext, arg: Arg, *, keep: bool, highest: bool) -> None:
    """kh/kl keep the N highest/lowest members; dh/dl drop them."""
    n = _number(arg, "k", "4d6kh3")
    if not 0 <= n <= MAX_DICE:
        raise InvalidError(
            ngettext("can't keep or drop {n} die", "can't keep or drop {n} dice", n),
            hint=_("use a number from 0 up"),
        )
    kept = pool.kept_members()
    ranked = sorted(kept, key=lambda m: m.value, reverse=highest)  # stable: earlier wins ties
    chosen = {id(m) for m in ranked[:n]}
    for member in kept:
        if (id(member) in chosen) != keep:
            member.kept = False


# ---------------------------------------------------------------------------- counting


def success(pool: Pool, ctx: RollContext, arg: Arg) -> None:
    if not isinstance(arg, Target):
        raise InvalidError(_("success counting needs a condition"), hint=_("e.g. `6d10>=8`"))
    pool.count = "successes"
    for member in pool.kept_members():
        if arg.test(member.value):
            member.success = True
    if isinstance(pool, DiePool) and not pool.spec.symbolic and _no_face(pool.spec, arg):
        sides = pool.spec.text
        pool.notes.append(
            phrase(
                N_(
                    "no d{die} can roll {target}, so this counts 0 successes; "
                    "to compare the total, put spaces around it (`{example}`)"
                ),
                die=sides,
                target=arg.text(),
                example=f"{len(pool.dice)}d{sides} {arg.op} {arg.text().lstrip('<>=')}",
            )
        )


def failure(pool: Pool, ctx: RollContext, arg: Arg) -> None:
    if not isinstance(arg, Target):
        raise InvalidError(_("`f` needs a condition"), hint=_("e.g. `6d10>=8f1` or `f<=2`"))
    pool.count = "successes"
    for member in pool.kept_members():
        if arg.test(member.value) and not member.success:
            member.failure = True


def parity(pool: Pool, ctx: RollContext, arg: Arg, *, even: bool) -> None:
    pool.count = "successes"
    for member in pool.kept_members():
        if int(member.value) % 2 == (0 if even else 1):
            member.success = True


def crit(pool: Pool, ctx: RollContext, arg: Arg, *, fumble: bool) -> None:
    token = "cf" if fumble else "cs"
    dice = _dice(pool, token)
    default = dice.spec.min_value if fumble else dice.spec.max_value
    target = arg if isinstance(arg, Target) else Target("=", default)
    for die in dice.kept():
        if target.test(die.face):
            if fumble:
                die.fumble = True
            else:
                die.crit = True


def matches(pool: Pool, ctx: RollContext, arg: Arg) -> None:
    size = _number(arg, "mt", "10d10mt")
    if size < 2:
        raise InvalidError(_("a set needs at least 2 matching dice"), hint=_("e.g. `mt` or `mt3`"))
    pool.count = "sets"
    pool.min_set = size


def margin(pool: Pool, ctx: RollContext, arg: Arg) -> None:
    if not isinstance(arg, Target):
        raise InvalidError(_("`ms` needs a target"), hint=_("e.g. `d20ms15` or `d20ms<=@DEX`"))
    pool.margin = arg


def sort(pool: Pool, ctx: RollContext, arg: Arg, *, descending: bool) -> None:
    match pool:
        case DiePool():
            pool.dice.sort(key=lambda d: d.value, reverse=descending)
        case GroupPool():
            pool.items.sort(key=lambda i: i.value, reverse=descending)
        case _:
            pass


# ---------------------------------------------------------------------------- registry


def _spec(
    name: str,
    tokens: tuple[str, ...],
    order: int,
    arg: ArgKind,
    apply: Callable[[Pool, RollContext, Arg], None],
    summary: str,
    **options: int | bool | None,
) -> ModifierSpec:
    return ModifierSpec(name, tokens, order, arg, apply, summary, **options)  # type: ignore[arg-type]


BUILTIN_MODIFIERS: tuple[ModifierSpec, ...] = (
    _spec("min", ("min",), 10, "number", partial(clamp, low=True), "raise dice below N to N"),
    _spec("max", ("max",), 11, "number", partial(clamp, low=False), "lower dice above N to N"),
    _spec("explode", ("!",), 20, "compare", partial(explode, how="explode"),
          "roll an extra die on the highest face (or on the condition), again and again"),
    _spec("compound", ("!!",), 21, "compare", partial(explode, how="compound"),
          "like ! but adds the extra rolls into the same die"),
    _spec("penetrate", ("!p",), 22, "compare", partial(explode, how="penetrate"),
          "like ! but each extra die counts one less (HackMaster)"),
    _spec("explode-once", ("!o",), 23, "compare", partial(explode, how="once"),
          "like ! but each die explodes at most once"),
    _spec("reroll", ("r", "rr"), 30, "compare", partial(reroll, once=False),
          "reroll dice showing the lowest face (or the condition) until they don't"),
    _spec("reroll-once", ("ro",), 31, "compare", partial(reroll, once=True),
          "reroll matching dice once and keep the new result"),
    _spec("unique", ("u",), 40, "none", partial(unique, once=False),
          "reroll duplicates until every die differs"),
    _spec("unique-once", ("uo",), 41, "none", partial(unique, once=True),
          "reroll duplicates once"),
    _spec("keep-highest", ("kh", "k"), 50, "number", partial(select, keep=True, highest=True),
          "keep the N highest (default 1)", default_arg=1, groups=True),
    _spec("keep-lowest", ("kl",), 50, "number", partial(select, keep=True, highest=False),
          "keep the N lowest (default 1)", default_arg=1, groups=True),
    _spec("drop-lowest", ("dl", "d"), 51, "number", partial(select, keep=False, highest=False),
          "drop the N lowest (default 1)", default_arg=1, groups=True),
    _spec("drop-highest", ("dh",), 51, "number", partial(select, keep=False, highest=True),
          "drop the N highest (default 1)", default_arg=1, groups=True),
    _spec("success", (), 60, "compare", success,
          "count dice meeting the condition as successes (`6d10>=8`)",
          groups=True, bare_number_compare=False),
    _spec("failure", ("f",), 61, "compare", failure,
          "count dice meeting the condition as failures, subtracted from successes",
          groups=True),
    _spec("even", ("even",), 62, "none", partial(parity, even=True),
          "count even dice as successes", groups=True),
    _spec("odd", ("odd",), 62, "none", partial(parity, even=False),
          "count odd dice as successes", groups=True),
    _spec("crit-success", ("cs",), 70, "compare", partial(crit, fumble=False),
          "mark crits on the highest face (or the condition); the total is unchanged"),
    _spec("crit-fail", ("cf",), 71, "compare", partial(crit, fumble=True),
          "mark fumbles on the lowest face (or the condition); the total is unchanged"),
    _spec("matches", ("mt",), 75, "number", matches,
          "count sets of matching dice (at least N alike, default 2) instead of the total",
          default_arg=2, groups=True, quiet_default=True),
    _spec("margin", ("ms",), 90, "compare", margin,
          "report the margin: total − N (or N − total for `<=`/`<`)", groups=True),
    _spec("sort", ("sa", "s"), 95, "none", partial(sort, descending=False),
          "show dice sorted low to high", groups=True),
    _spec("sort-desc", ("sd",), 95, "none", partial(sort, descending=True),
          "show dice sorted high to low", groups=True),
)  # fmt: skip


def default_registry() -> Registry:
    """A fresh registry with every built-in modifier. Packs add to their own copy."""
    registry = Registry()
    for spec in BUILTIN_MODIFIERS:
        registry.add_modifier(spec)
    return registry
