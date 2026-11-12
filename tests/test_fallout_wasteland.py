"""The `fallout-wasteland` setting, Fallout 2e's campaigns and vaults for either Fallout system:
its own tests, the book's two folders converted, the calendar from the book's default moment, a
frame started under each system with that system's numbers and trackers (and under any other
system, with clocks), the campaign moved to a frame's date, and a vault found with its secret."""

import json

import pytest

from tests.conftest import PACKS, Cli

PACK = PACKS / "fallout-wasteland"
pytestmark = pytest.mark.usefixtures("system_packs")

type Record = dict[str, dict[str, dict[str, object]]]


def _world(cli: Cli, system: str) -> None:
    assert cli("world", "new", "waste", "--system", system, "--seed", "waste").code == 0
    assert cli("pack", "enable", "fallout-wasteland").code == 0
    assert cli("campaign", "new", "c", "--seed", "waste").code == 0


def _draft(cli: Cli, generator: str, prefill: dict[str, str]) -> str:
    """Run one of the setting's generators and commit its draft; what it said."""
    args = ["gen", "run", f"fallout-wasteland.{generator}"]
    drafted = cli(*args, "--prefill", json.dumps(prefill), "--auto")
    assert drafted.code == 0, drafted.out + drafted.err
    draft = drafted.out.rsplit("`didact gen commit ", 1)[1].split("`", 1)[0]
    assert cli("gen", "commit", draft).code == 0
    return drafted.out


def _record(cli: Cli, ref: str) -> Record:
    shown: Record = json.loads(cli("show", ref, "--gm", "--format", "json").out)
    return shown


def _field(cli: Cli, ref: str, key: str) -> object:
    """A field of core's on a record (the GM's view: the cast come in secret)."""
    return _record(cli, ref)["fields"][key]


@pytest.mark.slow
def test_the_pack_tests_pass_including_a_play_under_each_system(cli: Cli) -> None:
    result = cli("pack", "test", str(PACK))
    assert result.code == 0, result.out + result.err
    assert "fallout-wasteland: 4/4 tests passed" in result.out


def test_both_folders_of_the_book_are_converted(cli: Cli) -> None:
    result = cli("pack", "coverage", str(PACK))
    assert "cites 43 sections of 43 (100%)" in result.out


@pytest.mark.parametrize("system", ["fallout-2e", "grimfall"])
def test_the_calendar_opens_two_centuries_after_the_war(cli: Cli, system: str) -> None:
    _world(cli, system)
    assert "Tuesday, 23 October 2277 (fall)" in cli("time", "show").out


def test_under_fallout_2e_a_frame_brings_its_stat_blocks_and_its_clocks(cli: Cli) -> None:
    _world(cli, "fallout-2e")
    said = _draft(cli, "frame", {"frame": "Fallout 3"})
    assert "Fallout 3 opens Tuesday, 23 October 2277: the campaign's today." in said
    autumn = _record(cli, "Colonel Autumn")  # the cast member and the threat are one record
    block = autumn["mechanics"]["fallout-2e"]
    scores = [block[score] for score in ("hp", "STR", "DEX", "WIL")]
    assert scores == [{"value": v, "max": v} for v in (10, 14, 15, 14)] and block["armor"] == 2
    assert autumn["mechanics"]["grimfall"]["tier"] == "elite"  # kept for a Grimfall world
    assert _field(cli, "Three Dog", "role") == "Galaxy News Radio host"  # core's, not a system's
    trackers = cli("track", "list", "--gm").out
    assert "Purity Clock 0/6" in trackers and "Eden Clock 0/4" in trackers
    assert "no trackers" in cli("track", "list").out  # the clocks are the GM's


def test_under_grimfall_a_frame_brings_cards_and_pools_on_its_date_and_a_vault(cli: Cli) -> None:
    _world(cli, "grimfall")
    said = _draft(cli, "frame", {"frame": "Fallout 76"})
    assert "`didact time set 'Monday, 23 October 2102'`" in said
    assert cli("time", "set", "Monday, 23 October 2102").code == 0
    assert "Monday, 23 October 2102 (fall)" in cli("time", "show").out
    wendigo = _record(cli, "Morris Stevens, Progenitor Wendigo")
    assert wendigo["mechanics"]["grimfall"]["tier"] == "tough"
    assert "Chorus Clock 8d" in cli("track", "list", "--gm").out
    rolled = cli("track", "roll", "chorus-clock")
    assert rolled.code == 0 and "Chorus Clock" in rolled.out
    assert "monster The Panther" in _draft(cli, "vault", {"vault": "Vault 43"})
    assert "panther was the control" not in cli("show", "loc:vault-43").out  # Hidden: the GM's
    assert cli("reveal", "loc:vault-43", "panther was the control").code == 0
    assert "panther was the control" in cli("show", "loc:vault-43").out


def test_under_another_system_the_clocks_are_clocks_and_the_numbers_are_kept(cli: Cli) -> None:
    _world(cli, "cairn-2e")
    said = _draft(cli, "frame", {"frame": "Lonesome Road"})
    assert "This world plays cairn-2e, neither Fallout system" in said
    assert "Launch Clock 0/4" in cli("track", "list", "--gm").out
    ulysses = _record(cli, "Ulysses")
    assert set(ulysses["mechanics"]) == {"fallout-2e", "grimfall"}  # both kept, neither read
