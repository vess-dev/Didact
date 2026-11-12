"""The `grimscrolls` pack, a hack that extends `grimwild-ce` and hides what it drops of it: its
own tests, the book converted, a hero with a race, a birthsign, a class and its talents, an
action roll with thorns, a creature of its bestiary, and the parent's content gone from play."""

import json

import pytest

from tests.conftest import PACKS, Cli

PACK = PACKS / "grimscrolls"
pytestmark = pytest.mark.usefixtures("system_packs")
STATS = ("brawn", "agility", "wits", "presence")

type Sheet = dict[str, object]


def _world(cli: Cli) -> None:
    assert cli("world", "new", "tamriel", "--system", "grimscrolls", "--seed", "tamriel").code == 0
    assert cli("campaign", "new", "c", "--seed", "tamriel").code == 0


def _sheet(cli: Cli, ref: str) -> Sheet:
    record = json.loads(cli("show", ref, "--format", "json").out)
    block = record["mechanics"]["grimscrolls"]
    assert isinstance(block, dict)
    return block


@pytest.mark.slow
def test_the_pack_tests_pass_including_the_smoke_plays(cli: Cli) -> None:
    result = cli("pack", "test", str(PACK))
    assert result.code == 0, result.out + result.err
    assert "grimscrolls: 15/15 tests passed" in result.out


def test_the_whole_book_is_converted(cli: Cli) -> None:
    result = cli("pack", "coverage", str(PACK))
    assert "cites 90 sections of 90 (100%)" in result.out


def test_a_hero_has_a_race_a_birthsign_a_class_and_its_talents(cli: Cli) -> None:
    _world(cli)
    made = cli("char", "new", "--mode", "random", "--prefill", json.dumps({"name": "Lydia"}))
    assert made.code == 0, made.err
    assert cli("char", "commit", "c1").code == 0
    lydia = _sheet(cli, "lydia")
    assert lydia["race"] and lydia["birthsign"] and lydia["class"]
    talents = lydia["talents"]
    assert isinstance(talents, list) and len(talents) >= 2  # the class's Core Talent and more
    stats = [value for stat in STATS if isinstance(value := lydia[stat], int)]
    assert len(stats) == 4 and min(stats) >= 1


def test_an_action_roll_rolls_the_stat_and_its_thorns(cli: Cli) -> None:
    _world(cli)
    sets = [f"{stat}={value}" for stat, value in zip(STATS, (3, 1, 2, 2), strict=True)]
    args = [arg for pair in sets for arg in ("--set", pair)]
    assert cli("new", "pc", "Lydia", *args).code == 0
    done = cli("do", "action", "who=lydia", "stat=brawn", "thorns=1", "--format", "json")
    assert done.code == 0, done.err
    run = json.loads(done.out)
    values = run["values"]
    dice, thorns = values["roll.dice"], values["thorn.dice"]
    assert len(dice) == 3 and len(thorns) == 1  # the stat's d6s, and a d8 for the thorn
    assert values["cuts"] == sum(1 for t in thorns if t >= 7)
    assert run["outcome"] in ("critical", "perfect", "messy", "grim", "disaster")


def test_a_creature_of_the_bestiary_reads_as_its_card(cli: Cli) -> None:
    _world(cli)
    shown = json.loads(cli("compendium", "show", "draugr", "--format", "json").out)
    assert shown["id"] == "grimscrolls.draugr" and shown["data"]["tier"] == "mook"
    assert shown["data"]["moves"] == ["Rise Behind You", "Shield the Sarcophagus"]


def test_what_the_hack_hides_of_its_parent_is_gone_from_play(cli: Cli) -> None:
    _world(cli)
    assert "nothing in the compendium matches" in cli("compendium", "find", "basilisk").out
    assert "grimwild-ce." not in cli("table", "list").out
    assert "(grimscrolls)" in cli("define", "thorn").out
    assert "grimwild-ce" not in cli("rules", "lookup", "spellcasting").out
