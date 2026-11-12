"""Dice property tests: bounds, keep/drop counts, explosion caps, canonical round trips."""

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from didact.core.errors import InvalidError
from didact.expr import HashStream, canonical, default_registry, parse
from didact.expr.engine import MAX_EXTRA, PoolResult
from didact.expr.model import ComparePoint, Dice, ModifierCall, Number, Span, numeric
from tests.dice_helpers import roll

REGISTRY = default_registry()
counts = st.integers(min_value=1, max_value=12)
sides = st.integers(min_value=1, max_value=100)
keys = st.text(min_size=1, max_size=12)


def pool(text: str, key: str) -> PoolResult:
    result = roll(text, key=key).result
    assert isinstance(result, PoolResult)
    return result


@given(n=counts, x=sides, key=keys)
def test_sums_stay_in_bounds(n: int, x: int, key: str) -> None:
    value = roll(f"{n}d{x}", key=key).result.value
    assert isinstance(value, int) and n <= value <= n * x


@given(n=counts, x=sides, k=st.integers(min_value=0, max_value=15), key=keys)
def test_keep_and_drop_counts(n: int, x: int, k: int, key: str) -> None:
    kept = pool(f"{n}d{x}kh{k}", key).pool.kept()
    assert len(kept) == min(n, k)
    dropped = pool(f"{n}d{x}dl{k}", key).pool.kept()
    assert len(dropped) == max(n - k, 0)
    highest = sorted((d.value for d in pool(f"{n}d{x}", key).pool.dice), reverse=True)
    assert sorted((d.value for d in kept), reverse=True) == highest[: min(n, k)]


@given(n=counts, x=st.integers(min_value=2, max_value=20), key=keys)
def test_explosions_add_dice_but_stay_capped(n: int, x: int, key: str) -> None:
    result = pool(f"{n}d{x}!", key)
    assert n <= len(result.pool.dice) <= n + MAX_EXTRA
    triggered = sum(1 for d in result.pool.dice if d.exploded)
    assert len(result.pool.dice) == n + triggered


@given(key=keys)
def test_an_always_exploding_run_hits_the_cap(key: str) -> None:
    result = pool("50d2!>=2", key)
    assert len(result.pool.dice) <= 50 + MAX_EXTRA
    if len(result.pool.dice) == 50 + MAX_EXTRA:
        assert "capped" in result.pool.flags


@given(n=counts, x=st.integers(min_value=2, max_value=12), t=st.integers(1, 12), key=keys)
def test_successes_never_exceed_the_dice(n: int, x: int, t: int, key: str) -> None:
    result = pool(f"{n}d{x}>={t}f1", key)
    assert 0 <= result.pool.successes <= n
    assert result.value == result.pool.successes - result.pool.failures


@given(x=st.integers(min_value=2, max_value=50), key=keys)
def test_rerolls_remove_the_face(x: int, key: str) -> None:
    result = pool(f"10d{x}r1", key)
    assert all(d.value != 1 for d in result.pool.dice) or "capped" in result.pool.flags


MODIFIERS = ["", "kh2", "kl1", "dl1", "dh1", "!", "!!", "!p", "r1", "ro<3", ">=4", ">=4f1", "cs",
             "cf", "min2", "max5", "mt", "ms10", "sa", "sd", "even", "u"]  # fmt: skip


@settings(max_examples=200)
@given(
    n=st.integers(min_value=1, max_value=6),
    x=st.sampled_from([4, 6, 8, 10, 12, 20]),
    mods=st.lists(st.sampled_from(MODIFIERS), max_size=3, unique=True),
    add=st.integers(min_value=-5, max_value=5),
)
def test_canonical_form_reads_back_as_itself(n: int, x: int, mods: list[str], add: int) -> None:
    if "u" in mods and n > x:
        mods.remove("u")
    text = f"{n}d{x}{''.join(mods)} + {add}"
    try:
        node = parse(text, REGISTRY)
    except InvalidError:
        assume(False)  # joined spellings can run together (`!` + `!p` reads `!!p`)
    once = canonical(node, REGISTRY)
    assert canonical(parse(once, REGISTRY), REGISTRY) == once
    roll(once)  # and it rolls


@given(n=st.integers(min_value=1, max_value=10_000), key=keys)
def test_streams_draw_in_range(n: int, key: str) -> None:
    stream = HashStream(key)
    draws = [stream.below(n) for _ in range(5)]
    assert all(0 <= d < n for d in draws)
    again = HashStream(key)
    assert [again.below(n) for _ in range(5)] == draws


@given(
    n=st.integers(min_value=1, max_value=4),
    mods=st.lists(st.sampled_from(MODIFIERS[1:]), min_size=2, max_size=3, unique=True),
)
def test_canonical_keeps_modifiers_apart(n: int, mods: list[str]) -> None:
    """Built from separate parts, the canonical form must still read back part by part."""
    calls: list[ModifierCall] = []
    for text in mods:
        parsed = parse(f"1d6{text}", REGISTRY)
        assert isinstance(parsed, Dice)
        calls.extend(parsed.modifiers)
    node = Dice(Span(0, 0), Number(Span(0, 0), n), numeric(6), tuple(calls))
    reread = parse(canonical(node, REGISTRY), REGISTRY)
    assert isinstance(reread, Dice)
    in_order = sorted(calls, key=lambda c: REGISTRY.modifiers[c.name].order)
    assert list(map(_shape, reread.modifiers)) == list(map(_shape, in_order))


def _shape(call: ModifierCall) -> tuple[str, object]:
    """A modifier without source positions: its name and argument."""
    if isinstance(call.arg, ComparePoint):
        return call.name, (call.arg.op, canonical(call.arg.value, REGISTRY))
    return call.name, call.arg
