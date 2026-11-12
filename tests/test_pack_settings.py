"""A hack's settings are its base's with its own on top, key by key, down a chain of hacks, for
whoever reads them: the engine (combat, session zero), the hack's rules, and the base's rules
(the hack is the game being played). A pack that only requires another keeps its own: the
`inherit-base`, `inherit-hack`, `inherit-heir` and `inherit-setting` fixtures."""

from pathlib import Path

from didact.core.config import resolve_config
from didact.packs.library import PackLibrary, PackSet
from tests.conftest import Cli

AMBUSH = "The ambushers act first."


def _packs(home: Path, pack_id: str) -> PackSet:
    return PackLibrary(resolve_config(home=str(home))).resolve([pack_id])


def _world(cli: Cli, system: str) -> None:
    assert cli("world", "new", "keep", "--system", system, "--seed", "keep").code == 0
    assert cli("campaign", "new", "c", "--seed", "keep").code == 0


def test_a_hacks_settings_are_its_bases_with_its_own_on_top(home: Path) -> None:
    packs = _packs(home, "inherit-hack")
    settings = packs.settings("inherit-hack")
    assert settings["torch_uses"] == 5
    assert settings["odds"] == {"likely": 5}  # a key the hack sets replaces the base's whole
    assert settings["combat"] == {"mode": "popcorn", "round_one": AMBUSH}  # kept from the base
    assert packs.settings("inherit-base") == settings  # the base's rules read the hack's
    assert packs.setting("inherit-base", "torch_uses") == 5
    alone = _packs(home, "inherit-base").settings("inherit-base")  # by itself, the base is whole
    assert alone["torch_uses"] == 3 and alone["odds"] == {"likely": 4, "even": 3}


def test_a_hack_of_a_hack_inherits_down_the_line(home: Path) -> None:
    packs = _packs(home, "inherit-heir")
    settings = packs.settings("inherit-heir")
    assert (settings["flares"], settings["torch_uses"], settings["odds"]) == (2, 5, {"likely": 5})
    assert settings["session_zero"] == [{"key": "oath", "ask": "What oath binds you?"}]
    assert packs.settings("inherit-base") == packs.settings("inherit-hack") == settings
    assert "flares" not in _packs(home, "inherit-hack").settings("inherit-base")


def test_rules_and_the_engine_read_the_settings_of_the_game_played(cli: Cli) -> None:
    _world(cli, "inherit-hack")
    assert "torches: 5; likely: 5; even: unset" in cli("do", "torch").out  # the base's rule
    assert f"torches: 5; ambush: {AMBUSH}" in cli("do", "lamp").out  # the hack's own
    assert "- oath: What oath binds you?" in cli("session", "zero").out  # the base's question
    cli("new", "npc", "Ash")
    cli("new", "npc", "Birch")
    fight = cli("combat", "start", "ash", "birch")
    assert fight.code == 0 and f"round one: {AMBUSH}" in fight.out
    assert cli("combat", "status", "--format", "json").out.count('"mode": "popcorn"') == 1


def test_a_hack_of_a_hack_plays_with_what_it_inherits(cli: Cli) -> None:
    _world(cli, "inherit-heir")
    assert "torches: 5; likely: 5; even: unset" in cli("do", "torch").out
    assert f"torches: 5; ambush: {AMBUSH}" in cli("do", "lamp").out


def test_a_pack_that_only_requires_the_system_keeps_its_own_settings(cli: Cli) -> None:
    _world(cli, "inherit-hack")
    assert cli("pack", "enable", "inherit-setting").code == 0
    assert "beacons: 9; likely: unset" in cli("do", "beacon").out  # its own, and only its own
    assert "torches: 5; likely: 5" in cli("do", "torch").out  # the system's are the hack's still
