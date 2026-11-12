"""The expression language for rules: logic, text, lists, `in`, `if()` and list functions."""

import pytest

from didact.core.errors import InvalidError
from didact.expr import HashStream, RollContext, canonical, default_registry, parse, run
from didact.expr.engine import PoolResult
from didact.expr.model import Value
from tests.dice_helpers import roll, shown

REGISTRY = default_registry()
PC: dict[str, Value] = {
    "STR": 12,
    "roll": 9,
    "conditions": ["deprived"],
    "armor": [1, 2],
    "action": "travel",
    "tags": [],
    "order": 3,
}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("@roll <= @STR and not 'deprived' in @conditions", False),
        ("@roll <= @STR and not 'panicked' in @conditions", True),
        ("@roll > @STR or @action == 'travel'", True),
        ("not @roll > @STR", True),
        ("sum(@armor) == 3 and count(@armor) == 2", True),
        ("min(@armor) + max(@armor, 5)", 6),
        ("if(@STR >= 10, 'strong', 'weak')", "strong"),
        ("count(@tags) == 0 and not any(@tags) and all(@armor)", True),
        ("'wood' in 'Champion of the Wood'", True),
        ("@order + 1", 4),  # `@order` is a variable, not the start of `or`
        ("true and not false", True),
        ("sum(@tags)", 0),
    ],
)
def test_rule_expressions(text: str, expected: object) -> None:
    assert roll(text, variables=PC).result.value == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("not @a or @b and @c", "not @a or @b and @c"),
        ("(@a or @b) and @c", "(@a or @b) and @c"),
        ("not (@a and @b)", "not (@a and @b)"),
        ("@x in @list", "@x in @list"),
        ('"it\'s"', '"it\'s"'),
        ("'plain'", "'plain'"),
        ("(@a == 1) + 1", "(@a == 1) + 1"),
        ("if(@a, 1d6, 1d4)", "if(@a, 1d6, 1d4)"),
    ],
)
def test_canonical_logic(text: str, expected: str) -> None:
    assert canonical(parse(text, REGISTRY), REGISTRY) == expected


def test_only_the_needed_dice_roll() -> None:
    """`and`/`or` stop early and `if()` evaluates one branch: unrolled dice draw nothing."""
    ctx = RollContext(REGISTRY, HashStream("t"))
    assert run("false and d6 > 3", ctx).result.value is False and ctx.draws == 0
    assert shown("false and d6 > 3") == "false and 1d6 > 3 → false and … = false"
    assert shown("if(true, d6, d20)", "4") == "if(true, 1d6, 1d20) → if(true, [4]) = 4"
    ctx = RollContext(REGISTRY, HashStream("t"))
    run("1d20 > 0 or 1d6 > 3", ctx)
    assert ctx.draws == 1


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("'a' < 3", "can't compare 'a' < 3"),
        ("@action + 1", "expected a number, got 'travel'"),
        ("3 in 4", "`in` needs a list or text"),
        ("if(true, 1)", "if() takes a condition and two values"),
        ("floor(1, 2)", "floor() takes one number"),
        ("max(@tags)", "max() got nothing"),
        ("'unclosed", "unclosed text"),
        ("@a and", "ends too early"),
        ("and @a", "unexpected `and`"),
    ],
)
def test_expression_errors(text: str, message: str) -> None:
    with pytest.raises(InvalidError, match=message.replace("(", r"\(").replace(")", r"\)")):
        roll(text, variables={**PC, "a": 1})


def test_dice_still_work_inside_logic() -> None:
    rolled = roll("2d6 >= 7 and d20 <= @STR", "3,4,10", variables=PC)
    assert rolled.result.value is True
    assert isinstance(roll("4d6kh3", "6,5,3,2").result, PoolResult)
