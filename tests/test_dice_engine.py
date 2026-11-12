"""Dice evaluation. Exact faces (as with `--got`) pin down every modifier's behavior."""

import pytest

from didact.core.errors import InvalidError
from didact.expr import Macro, default_registry
from didact.expr.engine import MAX_EXTRA, PoolResult, RepeatResult
from didact.expr.render import collect_flags, collect_notes, parts, to_data
from tests.dice_helpers import roll, shown


@pytest.mark.parametrize(
    ("text", "faces", "expected"),
    [
        # keep / drop (ties: the earlier die wins)
        ("4d6kh3", "6,5,3,2", "4d6kh3 → [6 5 3 (2)] = 14"),
        ("4d6dl1", "6,5,3,2", "4d6dl1 → [6 5 3 (2)] = 14"),
        ("4d6dh1", "6,5,3,2", "4d6dh1 → [(6) 5 3 2] = 10"),
        ("2d20kl1", "5,17", "2d20kl1 → [5 (17)] = 5"),
        ("3d6kh2", "5,5,5", "3d6kh2 → [5 5 (5)] = 10 (all-same, doubles)"),
        # explode, compound, penetrate, once
        ("d6!", "6,6,2", "1d6! → [6! 6! 2] = 14 (exploded, max)"),
        ("3d6!", "6,1,6,2,3", "3d6! → [6! 2 1 6! 3] = 18 (doubles, exploded)"),
        ("d6!!", "6,6,2", "1d6!! → [6+6+2] = 14 (exploded, max)"),
        ("d6!p", "6,6,2", "1d6!p → [6! 6-1! 2-1] = 12 (exploded, max)"),
        ("d6!o", "6,6", "1d6!o → [6! 6] = 12 (exploded, max)"),
        ("5d10!>=9", "9,1,1,1,1,4", "5d10!>=9 → [9! 4 1 1 1 1] = 17 (doubles, exploded)"),
        # reroll, unique, clamp
        ("2d6r1", "1,4,1,5", "2d6r1 → [1→1→5 4] = 9 (rerolled)"),
        ("2d6ro1", "1,1,3,1", "2d6ro1 → [1→3 1→1] = 4 (rerolled)"),
        ("d20ro<3", "2,1", "1d20ro<3 → [2→1] = 1 (min, rerolled)"),
        ("3d6u", "2,2,5,2,3", "3d6u → [2 2→2→3 5] = 10 (rerolled)"),
        ("4d6min3", "1,2,3,6", "4d6min3 → [1→3 2→3 3 6] = 15 (doubles)"),
        ("2d6max4", "6,2", "2d6max4 → [6→4 2] = 6"),
        # counting
        ("6d10>=8f1", "9,8,3,1,10,4", "6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes"),
        ("4d6even", "2,3,4,6", "4d6even → [2✓ 3 4✓ 6✓] = 3 successes"),
        ("4d6odd", "2,3,4,6", "4d6odd → [2 3✓ 4 6] = 1 success"),
        ("6d6mt", "3,3,5,5,5,1", "6d6mt → [3 3 5 5 5 1] = 2 sets (doubles)"),
        ("6d6mt3", "3,3,5,5,5,1", "6d6mt3 → [3 3 5 5 5 1] = 1 set (doubles)"),
        ("d20ms15", "18", "1d20ms15 → [18] = 3"),
        ("d20ms<=12", "7", "1d20ms<=12 → [7] = 5"),
        ("3d6sd", "2,6,4", "3d6sd → [6 4 2] = 12"),
        ("3d6sa", "2,6,4", "3d6sa → [2 4 6] = 12"),
        # crits are markers: the total never changes
        ("d20cs>=19", "19", "1d20cs>=19 → [19] = 19 (crit)"),
        ("d20cf", "1", "1d20cf → [1] = 1 (fumble, min)"),
        ("d20", "20", "1d20 → [20] = 20 (max)"),
        # groups
        ("{d8, d6}kh1", "3,5", "{1d8, 1d6}kh1 → {([3]), [5]} = 5"),
        ("{d8, d6}kl1", "3,5", "{1d8, 1d6}kl1 → {[3], ([5])} = 3"),
        (
            "{3d6, 2d8}>=10",
            "6,6,6,2,3",
            "{3d6, 2d8}>=10 → {[6 6 6]✓, [2 3]} = 1 success (3d6: all-same, doubles, max)",
        ),
        # arithmetic, comparisons, variables
        ("2d6+3", "4,2", "2d6 + 3 → [4 2] + 3 = 9"),
        ("(1d6+2)*2", "5", "(1d6 + 2) * 2 → ([5] + 2) * 2 = 14"),
        ("3d6*10", "1,2,3", "3d6 * 10 → [1 2 3] * 10 = 60"),
        ("d6/2", "5", "1d6 / 2 → [5] / 2 = 2.5"),
        ("d6//2", "5", "1d6 // 2 → [5] // 2 = 2"),
        ("d6%4", "5", "1d6 % 4 → [5] % 4 = 1"),
        ("-d4", "2", "-1d4 → -[2] = -2"),
        ("2d6 >= 8", "6,2", "2d6 >= 8 → [6 2] >= 8 = true"),
        ("d20 = 5", "5", "1d20 == 5 → [5] == 5 = true"),
        ("d20 <> 5", "5", "1d20 <> 5 → [5] <> 5 = false"),
        ("(2d4)d8", "1,2,8,8,8", "(2d4)d8 → ([1 2])[8 8 8] = 24 (all-same, doubles, max)"),
        # dice kinds
        ("d66", "35", "1d66 → [35] = 35"),
        ("4dF", "+,-,0,+", "4dF → [1 -1 0 1] = 1 (doubles)"),
        ("d{0,0,1,1,2,3}", "2", "1d{0,0,1,1,2,3} → [2] = 2"),
        # functions and dice steps
        ("max(d6, d6)", "2,5", "max(1d6, 1d6) → max([2], [5]) = 5"),
        (
            "floor(7/2) + ceil(7/2)",
            None,
            "floor(7 / 2) + ceil(7 / 2) → floor(7 / 2) + ceil(7 / 2) = 7",
        ),
        (
            "round(2.5) + round(-2.5)",
            None,
            "round(2.5) + round(-2.5) → round(2.5) + round(-2.5) = 0",
        ),
        ("step(d6, 1)", "8", "step(1d6, 1) → [8] = 8 (max)"),
        ("step(d6, -1)", "3", "step(1d6, -1) → [3] = 3"),
        ("step(2d6, 1)", "8,1", "step(2d6, 1) → [8 1] = 9"),
        ("step.extended(d7, 1)", "5", "step.extended(1d7, 1) → [5] = 5"),
    ],
)
def test_modifiers_with_exact_faces(text: str, faces: str | None, expected: str) -> None:
    assert shown(text, faces) == expected


def test_repeat_rolls_each_on_its_own() -> None:
    rolled = roll("3#d6", "1,2,3")
    assert isinstance(rolled.result, RepeatResult)
    assert [i.value for i in rolled.result.items] == [1, 2, 3]
    assert shown("3#d6", "1,2,3") == "3#1d6 → [1] = 1 (min); [2] = 2; [3] = 3"
    with pytest.raises(InvalidError, match="can't be used inside"):
        roll("(3#d6) + 1", "1,2,3")


def test_variables_labels_and_tags() -> None:
    assert (
        shown("d20 <= @STR", "8", variables={"STR": 12}) == "1d20 <= @STR → [8] <= @STR(12) = true"
    )
    assert shown("d20 <= @str", "8", variables={"STR": 12}).endswith("= true")  # any case
    assert shown("(@level)d6", "3,4", variables={"level": 2}) == "2d6 → [3 4] = 7"  # as rolled
    rolled = roll("hope:1d12 + fear:1d12", "7,3")
    assert parts(rolled.result) == {"hope": 7, "fear": 3}
    rolled = roll("d8[cryo] + d6[fire]", "5,3")
    assert parts(rolled.result) == {"cryo": 5, "fire": 3}
    assert shown("d8[cryo] + d6[fire]", "5,3") == "1d8[cryo] + 1d6[fire] → [5] cryo + [3] fire = 8"
    with pytest.raises(InvalidError, match="unknown variable @DEX") as caught:
        roll("d20 <= @DEX", "8", variables={"STR": 12})
    assert caught.value.hint == "known variables: STR"


def test_flags_name_their_pool_when_there_are_several() -> None:
    rolled = roll("hope:1d12 + fear:1d12", "12,12")
    assert collect_flags(rolled.result) == ["hope: max", "fear: max"]
    assert shown("hope:1d12 + fear:1d12", "12,12").endswith("= 24 (hope: max; fear: max)")
    assert shown("d20 + d4", "20,2").endswith("= 22 (1d20: max)")


def test_macros_expand_like_the_pack_wrote_them() -> None:
    registry = default_registry()
    registry.add_macro(Macro("hack.attack", ("a", "b"), "{$a, $b}kh1"))
    assert shown("hack.attack(d8, d6)", "3,5", registry=registry) == (
        "hack.attack(1d8, 1d6) → hack.attack({([3]), [5]}) = 5"
    )
    with pytest.raises(InvalidError, match="takes 2 argument"):
        roll("hack.attack(d8)", "3", registry=registry)


def test_step_stops_at_the_end_of_the_chain() -> None:
    rolled = roll("step(d12, 2)", "12")
    assert rolled.result.value == 12
    assert collect_notes(rolled.result) == ["the standard dice chain stops at d12"]
    with pytest.raises(InvalidError, match="isn't on the standard dice chain"):
        roll("step(d7, 1)", "1")
    with pytest.raises(InvalidError, match="unknown dice chain"):
        roll("step.nope(d6, 1)", "1")


def test_success_counting_warns_when_no_die_can_succeed() -> None:
    rolled = roll("2d6>=8", "6,2")
    assert rolled.result.value == 0
    assert "put spaces around it (`2d6 >= 8`)" in collect_notes(rolled.result)[0]


def test_explosions_are_capped() -> None:
    rolled = roll("d2!", ",".join(["2"] * (MAX_EXTRA + 1)))
    assert isinstance(rolled.result, PoolResult)
    assert len(rolled.result.pool.dice) == MAX_EXTRA + 1
    assert "capped" in collect_flags(rolled.result)
    assert collect_notes(rolled.result) == [
        f"stopped after {MAX_EXTRA} explosions (the safety cap)"
    ]


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("d6!>=1", "would explode forever"),
        ("d1!", "would explode forever"),
        ("d6r<=6", "would reroll forever"),
        ("8d6u", "can't all differ"),
        ("1001d6", "a pool needs 0–1000 dice"),
        ("d6/0", "division by zero"),
        ("nope(1)", "unknown function nope()"),
        ("4d6f", "`f` needs a condition"),
        ("d6mt1", "at least 2"),
        ("{d8, d6}!", "can't be used on a {group}"),
    ],
)
def test_impossible_rolls_are_refused(text: str, message: str) -> None:
    with pytest.raises(InvalidError, match=message.replace("(", r"\(").replace(")", r"\)")):
        roll(text)


def test_got_faces_must_fit_the_dice() -> None:
    with pytest.raises(InvalidError, match="'7' isn't a face of d6"):
        roll("2d6", "7,1")
    with pytest.raises(InvalidError, match="ran out of faces"):
        roll("d6!", "6")


def test_result_data_is_json_ready() -> None:
    data = to_data(roll("6d10>=8f1", "9,8,3,1,10,4").result)
    assert data["type"] == "dice" and data["successes"] == 3 and data["failures"] == 1
    assert data["dice"] == [
        {"value": 9, "success": True},
        {"value": 8, "success": True},
        {"value": 3},
        {"value": 1, "failure": True},
        {"value": 10, "success": True},
        {"value": 4},
    ]


def test_seeded_streams_are_reproducible_and_independent() -> None:
    first = roll("10d10", key="seed:1").result
    assert to_data(roll("10d10", key="seed:1").result) == to_data(first)
    assert to_data(roll("10d10", key="seed:2").result) != to_data(first)
