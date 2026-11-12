"""The `fallout-2e` pack, a hack that extends `cairn-2e`: its own tests, the book converted, a
character from one of its backgrounds, a Rad and its save, a creature of its bestiary on the
parent's attack chain, and what it answers when asked for the parent's spells."""

import json

import pytest

from tests.conftest import PACKS, Cli

PACK = PACKS / "fallout-2e"
pytestmark = pytest.mark.usefixtures("system_packs")

type Sheet = dict[str, object]


def _world(cli: Cli) -> None:
    assert cli("world", "new", "waste", "--system", "fallout-2e", "--seed", "waste").code == 0
    assert cli("campaign", "new", "c", "--seed", "waste").code == 0
    made = cli("new", "pc", "Freya", "--set", "STR=12", "--set", "DEX=12", "--set", "WIL=12")
    assert made.code == 0, made.err


def _sheet(cli: Cli, ref: str) -> Sheet:
    record = json.loads(cli("show", ref, "--format", "json").out)
    block = record["mechanics"]["fallout-2e"]
    assert isinstance(block, dict)
    return block


@pytest.mark.slow
def test_the_pack_tests_pass_including_the_smoke_plays(cli: Cli) -> None:
    result = cli("pack", "test", str(PACK))
    assert result.code == 0, result.out + result.err
    assert "fallout-2e: 26/26 tests passed" in result.out


def test_the_whole_book_is_converted(cli: Cli) -> None:
    result = cli("pack", "coverage", str(PACK))
    assert "cites 101 sections of 101 (100%)" in result.out


def test_a_background_makes_a_character_with_caps_and_its_kind(cli: Cli) -> None:
    _world(cli)
    prefill = {"background": "Ghoul", "name": "Hap", "youngest": "no"}
    made = cli("char", "new", "--mode", "random", "--prefill", json.dumps(prefill))
    assert made.code == 0, made.err
    assert cli("char", "commit", "c1").code == 0
    hap = _sheet(cli, "hap")
    assert hap["background"] == "Ghoul" and hap["kind"] == "ghoul"
    immunities = hap["immunities"]  # a Radiant ghoul's result adds one more
    assert isinstance(immunities, list) and "rad-scars" in immunities
    assert isinstance(hap["caps"], int) and "gold" not in hap  # caps, where Cairn has gold


def test_a_rad_fills_a_slot_and_calls_for_a_rad_scar_save(cli: Cli) -> None:
    _world(cli)
    took = cli("do", "rad", "who=freya", "source=hot-zone")
    assert took.code == 0, took.err
    assert "rads reached 1: runs rad-scar-save" in took.out and "1d20" in took.out
    assert _sheet(cli, "freya")["rads"] == 1


def test_a_creature_of_the_bestiary_fights_on_the_parents_chain(cli: Cli) -> None:
    _world(cli)
    assert cli("spawn", "deathclaw").code == 0
    deathclaw = _sheet(cli, "deathclaw")
    assert deathclaw["armor"] == 2 and deathclaw["hp"] == {"value": 14, "max": 14}
    assert deathclaw["attacks"] == [
        {"name": "claws", "damage": "{d12, d12}kh1"},
        {"name": "bite", "damage": "d10"},
    ]
    cli("set", "freya", "hp=1")
    mauled = cli("do", "attack", "attacker=deathclaw", "target=freya", "weapon=d12+12")
    assert mauled.code == 0, mauled.err
    assert "STR -= " in mauled.out  # damage past 0 HP comes off STR, as in Cairn


def test_the_parents_spells_are_refused_with_what_replaces_them(cli: Cli) -> None:
    _world(cli)
    cast = cli("do", "cast", "who=freya")
    assert "Fallout 2e has no spells" in cast.out + cast.err
    assert "`didact do read-magazine`" in cast.out + cast.err
