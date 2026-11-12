"""The dice notation: every documented example parses and rolls; canonical form; errors."""

import pytest

from didact.core.errors import InvalidError
from didact.expr import DieSpec, Face, Macro, Registry, canonical, default_registry, parse
from tests.dice_helpers import roll

# The notation's documented examples, then examples written in other dice rollers' dialects.
# Pack dice and macros are registered in `pack_registry`.
DOCUMENTED = [
    "3d6", "d%", "4dF", "d66", "d{0,0,1,1,2,3}", "2d[boost] + 1d[setback]",
    "hope:1d12 + fear:1d12", "4d6mt", "d20ms15", "4d6kh3", "2d20kl1", "d6!", "5d10!>=9",
    "2d6r1", "d20ro<3", "6d10>=8f1", "d20cs>=19", "4d6min2", "{d8, d6}kh1", "3#3d6",
    "3d6*10", "d20 <= @DEX", "(@level)d6", "(2d4)d8", "d20 <= @STR", "d8[cryo]",
    "step(d6, +1)", "hack.attack(d8, d8)",
]  # fmt: skip
DIALECTS = [
    "2d20kh1+@str", "6#(4d6dl1)", "{1d8!,1d6!}kh1", "8d10!>=10>=8", "12d6>=5", "4dF+3",
    "3d6kh1", "2d6kl1", "1d20!p", "hope:1d12+fear:1d12+2", "2d[ability]+1d[difficulty]",
]  # fmt: skip
VARIABLES = {"DEX": 12, "STR": 9, "level": 3, "str": 2}


PACK_DICE = {
    "boost": ("", "", "success", "success+advantage", "advantage+advantage", "advantage"),
    "setback": ("", "", "failure", "failure", "threat", "threat"),
    "ability": ("", "success", "success", "success+success", "advantage", "advantage",
                "success+advantage", "advantage+advantage"),
    "difficulty": ("", "failure", "failure+failure", "threat", "threat", "threat",
                   "threat+threat", "failure+threat"),
}  # fmt: skip


def pack_registry() -> Registry:
    """The built-ins plus what two packs would add: symbol dice and an attack macro."""
    registry = default_registry()
    for name, faces in PACK_DICE.items():
        parsed = tuple(Face(0, tuple(f.split("+"))) if f else Face() for f in faces)
        registry.add_die(name, DieSpec("custom", len(parsed), faces=parsed))
    registry.add_macro(Macro("hack.attack", ("a", "b"), "{$a, $b}kh1", "attack with two weapons"))
    return registry


@pytest.mark.parametrize("text", DOCUMENTED + DIALECTS)
def test_every_documented_example_parses_and_rolls(text: str) -> None:
    registry = pack_registry()
    rolled = roll(text, variables=VARIABLES, registry=registry)
    again = canonical(parse(rolled.canonical, registry), registry)
    assert again == rolled.canonical  # the canonical form reads back as itself


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("d20", "1d20"),
        ("d%", "1d100"),
        ("4d6k3", "4d6kh3"),
        ("4d6d1", "4d6dl1"),
        ("2d20k", "2d20kh1"),
        ("2d6rr1", "2d6r1"),
        ("3d6s", "3d6sa"),
        ("6d10>=8f=1", "6d10>=8f1"),
        ("d20=5", "1d20=5"),
        ("d20 = 5", "1d20 == 5"),
        ("d6!>=5", "1d6!>=5"),
        ("4d6mt", "4d6mt"),
        ("4d6mt3", "4d6mt3"),
        ("2*(3+d4)", "2 * (3 + 1d4)"),
        ("{d8,d6}kh1", "{1d8, 1d6}kh1"),
        ("@{mechanics.cairn-2e.str}", "@{mechanics.cairn-2e.str}"),
        ("4d6sdkh3dl1", "4d6kh3dl1sd"),  # printed in application order
        ("(1d6!)>=8", "(1d6!)>=8"),  # `1d6!>=8` would explode on 8+
        ("(4d6u)odd", "(4d6u)odd"),  # `4d6uodd` would read as `uo` + `d` + `d`
        ("(1d4!)!p", "(1d4!)!p"),  # `1d4!!p` would read as `!!` + `p`
    ],
)
def test_canonical_form(text: str, expected: str) -> None:
    registry = default_registry()
    assert canonical(parse(text, registry), registry) == expected


@pytest.mark.parametrize(
    ("text", "message", "hint"),
    [
        ("2d6+", "ends too early", "finish it"),
        ("4d6 kh3", "unexpected 'kh3'", "attach directly"),
        ("d6!=6", "ambiguous", "`!6`"),
        ("d20 != 5", "isn't supported", "`<>`"),
        ("2d[nope]", "unknown die [nope]", "named dice come from packs"),
        ("d0", "1–1000000 sides", None),
        ("goblin", "unknown name 'goblin'", "variables start with @"),
        ("{d8, d6", "unclosed group", "close it"),
        ("3#3#d6", "can't be nested", None),
        ("", "empty expression", None),
        ("4d6kx3", "unexpected 'x3'", None),
        ("101#d6", "repeat counts must be 1–100", None),
        ("2.5d6", "whole numbers", None),
    ],
)
def test_errors_point_at_the_problem(text: str, message: str, hint: str | None) -> None:
    with pytest.raises(InvalidError) as caught:
        parse(text, pack_registry())
    assert message in caught.value.message
    if hint:
        assert caught.value.hint and hint in caught.value.hint


def test_error_caret_sits_under_the_bad_character() -> None:
    with pytest.raises(InvalidError) as caught:
        parse("4d6kx3", default_registry())
    assert caught.value.where == "4d6kx3\n    ^"
