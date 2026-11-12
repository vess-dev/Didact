"""The `elder-scrolls-2e` pack, a hack that extends `cairn-2e`: its own tests, the book
converted, a character with a race and Septims on the parent's sheet, a disease and its save, a
creature of its bestiary on the parent's attack chain, and a Spell Tome cast as a spellbook is."""

import json

import pytest

from tests.conftest import PACKS, Cli

PACK = PACKS / "elder-scrolls-2e"
pytestmark = pytest.mark.usefixtures("system_packs")

type Sheet = dict[str, object]


def _world(cli: Cli) -> None:
    made = cli("world", "new", "skyrim", "--system", "elder-scrolls-2e", "--seed", "skyrim")
    assert made.code == 0, made.err
    assert cli("campaign", "new", "c", "--seed", "skyrim").code == 0
    freya = cli("new", "pc", "Freya", "--set", "STR=12", "--set", "DEX=12", "--set", "WIL=12")
    assert freya.code == 0, freya.err


def _sheet(cli: Cli, ref: str) -> Sheet:
    record = json.loads(cli("show", ref, "--format", "json").out)
    block = record["mechanics"]["elder-scrolls-2e"]
    assert isinstance(block, dict)
    return block


@pytest.mark.slow
def test_the_pack_tests_pass_including_the_smoke_plays(cli: Cli) -> None:
    result = cli("pack", "test", str(PACK))
    assert result.code == 0, result.out + result.err
    assert "elder-scrolls-2e: 39/39 tests passed" in result.out


def test_the_whole_book_is_converted(cli: Cli) -> None:
    result = cli("pack", "coverage", str(PACK))
    assert "cites 103 sections of 103 (100%)" in result.out


def test_a_background_makes_a_character_with_a_race_and_septims(cli: Cli) -> None:
    _world(cli)
    prefill = {"background": "Miner", "name": "Bolverk"}
    made = cli("char", "new", "--mode", "random", "--prefill", json.dumps(prefill))
    assert made.code == 0, made.err
    assert cli("char", "commit", "c1").code == 0
    bolverk = _sheet(cli, "bolverk")
    assert bolverk["background"] == "Miner"
    assert bolverk["race"] and bolverk["trait"]  # every PC has a race and its one trait
    assert isinstance(bolverk["gold"], int)  # the parent's field, so its rules still spend it
    assert "Septims " in cli("sheet", "bolverk").out and "gold" not in cli("sheet", "bolverk").out


def test_a_disease_takes_hold_on_a_failed_save(cli: Cli) -> None:
    _world(cli)
    exposed = cli("do", "disease", "who=freya", "disease=rockjoint")
    assert exposed.code == 0, exposed.err
    assert "1d20" in exposed.out
    caught = _sheet(cli, "freya").get("diseases", [])
    assert (caught == ["rockjoint"]) == ("→ failure" in exposed.out)
    cured = cli("do", "cure-disease", "who=freya", "how=shrine")
    assert cured.code == 0, cured.err
    assert not _sheet(cli, "freya").get("diseases")


def test_a_creature_of_the_bestiary_fights_on_the_parents_chain(cli: Cli) -> None:
    _world(cli)
    assert cli("spawn", "draugr").code == 0
    draugr = _sheet(cli, "draugr")
    assert draugr["armor"] == 1 and draugr["hp"] == {"value": 6, "max": 6}
    assert draugr["STR"] == {"value": 12, "max": 12}
    cli("set", "freya", "hp=1")
    struck = cli("do", "attack", "attacker=draugr", "target=freya", "weapon=d8+12")
    assert struck.code == 0, struck.err
    assert "STR -= " in struck.out  # damage past 0 HP comes off STR, as in Cairn


def test_a_spell_tome_is_cast_for_a_fatigue(cli: Cli) -> None:
    _world(cli)
    cast = cli("do", "cast", "who=freya", "spell=Flames")
    assert cast.code == 0, cast.err
    assert "fatigue += 1" in cast.out
    assert _sheet(cli, "freya")["fatigue"] == 1
