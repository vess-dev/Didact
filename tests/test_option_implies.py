"""What an option implies is followed all the way (a flavor sets the lethality, which sets the
potions), an answer wins over what another option implies and that over the default, of two
implications the nearer one wins, and options that imply each other are harmless: the
`implies-lite` fixture."""

import json
from typing import Any

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    assert cli("world", "new", "tides", "--system", "implies-lite", "--seed", "tides").code == 0
    assert cli("campaign", "new", "c", "--seed", "tides").code == 0


def _looked(cli: Cli) -> str:
    return cli("do", "look").out


def _zero(cli: Cli) -> dict[str, Any]:  # parsed JSON, read freely in tests
    out = cli("session", "zero", "--format", "json")
    assert out.code == 0, out.err
    return {q["key"]: q for q in json.loads(out.out)["questions"]}


def test_what_an_option_implies_is_followed_all_the_way(cli: Cli) -> None:
    setup(cli)
    assert "lethality standard; potions common; torches false; dark false" in _looked(cli)
    cli("campaign", "profile", "flavor=grim")
    assert "lethality deadly; potions scarce; torches true; dark true" in _looked(cli)  # 3 steps
    brief = cli("brief").out
    assert "Option potions=scarce: Scarce." in brief
    assert "Option dark=on: Unlit places are deadly." in brief


def test_an_answer_and_the_nearer_implication_win(cli: Cli) -> None:
    setup(cli)
    cli("campaign", "profile", "flavor=wild")  # wild sets the potions itself: nearer than deadly
    assert "lethality deadly; potions plenty; torches true" in _looked(cli)
    cli("campaign", "profile", "flavor=grim", "potions=common")  # said outright, it wins
    assert "lethality deadly; potions common; torches true; dark true" in _looked(cli)
    cli("campaign", "profile", "lethality=gentle")  # and what it would have implied goes too
    assert "lethality gentle; potions common; torches false; dark false" in _looked(cli)


def test_session_zero_names_the_option_that_implies_a_value(cli: Cli) -> None:
    setup(cli)
    cli("campaign", "profile", "flavor=grim")
    zero = _zero(cli)
    assert zero["potions"]["value"] == "scarce" and zero["potions"]["implied_by"] == {
        "option": "lethality",
        "title": "Lethality",
        "value": "deadly",
    }
    assert zero["dark"]["implied_by"] == {"option": "torches", "title": "Torches", "value": "on"}
    assert zero["lethality"]["implied_by"]["option"] == "flavor"


def test_a_default_implies_too_and_options_implying_each_other_are_harmless(cli: Cli) -> None:
    setup(cli)
    # the weather's default sets the sky, and the sky's grey (not its default blue) the mood
    assert "sky grey; mood low; tides false; moons one" in _looked(cli)
    assert _zero(cli)["mood"]["implied_by"] == {"option": "sky", "title": "Sky", "value": "grey"}
    cli("campaign", "profile", "tides=on")
    assert "tides true; moons two" in _looked(cli)
    cli("campaign", "profile", "tides=", "moons=two")
    assert "tides true; moons two" in _looked(cli)
    cli("campaign", "profile", "tides=off")  # both answered: each answer stands
    assert "tides false; moons two" in _looked(cli)
