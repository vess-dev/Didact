"""The `grimfall` pack, a hack that extends `grimwild-ce` and hides what it drops of it: its own
tests, the book converted, a survivor with a class and its Core Perk, an action roll with thorns,
a threat of its bestiary as linked pools, and the parent's text and content gone from play."""

import json

import pytest

from tests.conftest import PACKS, Cli

PACK = PACKS / "grimfall"
pytestmark = pytest.mark.usefixtures("system_packs")
STATS = ("brawn", "agility", "wits", "presence")

type Sheet = dict[str, object]


def _world(cli: Cli) -> None:
    assert cli("world", "new", "waste", "--system", "grimfall", "--seed", "waste").code == 0
    assert cli("campaign", "new", "c", "--seed", "waste").code == 0


def _sheet(cli: Cli, ref: str) -> Sheet:
    record = json.loads(cli("show", ref, "--format", "json").out)
    block = record["mechanics"]["grimfall"]
    assert isinstance(block, dict)
    return block


@pytest.mark.slow
def test_the_pack_tests_pass_including_the_smoke_plays(cli: Cli) -> None:
    result = cli("pack", "test", str(PACK))
    assert result.code == 0, result.out + result.err
    assert "grimfall: 20/20 tests passed" in result.out


def test_the_whole_book_is_converted(cli: Cli) -> None:
    result = cli("pack", "coverage", str(PACK))
    assert "cites 96 sections of 96 (100%)" in result.out


def test_a_survivor_has_a_class_its_core_perk_and_eight_points_of_stats(cli: Cli) -> None:
    _world(cli)
    made = cli("char", "new", "--mode", "random", "--prefill", json.dumps({"name": "Dutch"}))
    assert made.code == 0, made.err
    assert cli("char", "commit", "c1").code == 0
    dutch = _sheet(cli, "dutch")
    assert str(dutch["class"]).startswith("The ")
    perks = dutch["perks"]
    assert isinstance(perks, list) and len(perks) == 2  # the class's Core Perk and one more
    stats = [value for stat in STATS if isinstance(value := dutch[stat], int)]
    assert len(stats) == 4 and sum(stats) == 8 and min(stats) >= 1  # 1 in each, plus 4 points


def test_an_action_roll_keeps_the_highest_die_and_rolls_its_thorns(cli: Cli) -> None:
    _world(cli)
    sets = [f"{stat}={value}" for stat, value in zip(STATS, (3, 1, 2, 2), strict=True)]
    args = [arg for pair in sets for arg in ("--set", pair)]
    assert cli("new", "pc", "Dutch", *args).code == 0
    done = cli("do", "action", "who=dutch", "stat=brawn", "thorns=1", "--format", "json")
    assert done.code == 0, done.err
    run = json.loads(done.out)
    values = run["values"]
    dice, thorns = values["roll.dice"], values["thorn.dice"]
    assert len(dice) == 3 and len(thorns) == 1  # the stat's d6s, and a d8 for the thorn
    assert values["highest"] == max(dice) and values["cuts"] == sum(1 for t in thorns if t >= 7)
    assert run["outcome"] in ("critical", "perfect", "messy", "grim", "disaster")


def test_a_threat_of_the_bestiary_is_its_linked_pools(cli: Cli) -> None:
    _world(cli)
    shown = json.loads(cli("compendium", "show", "deathclaw", "--format", "json").out)
    assert shown["id"] == "grimfall.deathclaw" and shown["data"]["tier"] == "boss"
    assert [pool["dice"] for pool in shown["data"]["pools"]] == [8, 6, 6]


def test_what_the_hack_hides_of_its_parent_is_gone_from_play(cli: Cli) -> None:
    _world(cli)
    assert "nothing in the compendium matches" in cli("compendium", "find", "basilisk").out
    assert "no rules text about 'spellcasting'" in cli("rules", "lookup", "spellcasting").out
    tables = cli("table", "list").out
    assert tables.count("grimwild-ce.") == 1 and "grimwild-ce.bonds" in tables  # the one kept
    assert "(grimfall)" in cli("define", "thorn").out
