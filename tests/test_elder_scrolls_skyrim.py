"""The `elder-scrolls-skyrim` setting, The Elder Scrolls 2e's campaigns and Holds for either Elder
Scrolls system: its own tests, the book's campaigns and Holds converted, the Tamrielic calendar from
the book's own moment (its year written 4E 201, a date read back so), a frame started under each
system with that system's numbers and trackers (and under any other system, with clocks), a Hold
visited with its Jarl, and a Daedric Prince's bargain."""

import json

import pytest

from tests.conftest import PACKS, Cli

PACK = PACKS / "elder-scrolls-skyrim"
pytestmark = pytest.mark.usefixtures("system_packs")

type Record = dict[str, dict[str, dict[str, object]]]


def _world(cli: Cli, system: str) -> None:
    assert cli("world", "new", "skyrim", "--system", system, "--seed", "skyrim").code == 0
    assert cli("pack", "enable", "elder-scrolls-skyrim").code == 0
    assert cli("campaign", "new", "c", "--seed", "skyrim").code == 0


def _draft(cli: Cli, generator: str, prefill: dict[str, str]) -> str:
    """Run one of the setting's generators and commit its draft; what it said."""
    args = ["gen", "run", f"elder-scrolls-skyrim.{generator}"]
    drafted = cli(*args, "--prefill", json.dumps(prefill), "--auto")
    assert drafted.code == 0, drafted.out + drafted.err
    draft = drafted.out.rsplit("`didact gen commit ", 1)[1].split("`", 1)[0]
    assert cli("gen", "commit", draft).code == 0
    return drafted.out


def _record(cli: Cli, ref: str) -> Record:
    shown: Record = json.loads(cli("show", ref, "--gm", "--format", "json").out)
    return shown


@pytest.mark.slow
def test_the_pack_tests_pass_including_a_play_under_each_system(cli: Cli) -> None:
    result = cli("pack", "test", str(PACK))
    assert result.code == 0, result.out + result.err
    assert "elder-scrolls-skyrim: 4/4 tests passed" in result.out


def test_the_campaigns_and_the_holds_are_converted(cli: Cli) -> None:
    result = cli("pack", "coverage", str(PACK))
    assert "cites 13 sections of 13 (100%)" in result.out


@pytest.mark.parametrize("system", ["elder-scrolls-2e", "grimscrolls"])
def test_the_calendar_opens_the_day_helgen_burns(cli: Cli, system: str) -> None:
    _world(cli, system)
    assert "Sundas, 17 Last Seed 4E 201 (summer)" in cli("time", "show").out
    later = cli("time", "set", "3 Hearthfire 4E 201")  # a date as the calendar writes one
    assert later.code == 0, later.out + later.err
    assert "Middas, 3 Hearthfire 4E 201 (summer) · Tales and Tallows" in later.out


def test_under_elder_scrolls_2e_a_frame_brings_stat_blocks_and_a_hold_its_jarl(cli: Cli) -> None:
    _world(cli, "elder-scrolls-2e")
    said = _draft(cli, "frame", {"frame": "The Main Quest"})
    assert "The Main Quest opens Sundas, 17 Last Seed 4E 201: the campaign's today." in said
    alduin = _record(cli, "Alduin")  # the cast member and the threat are one record
    block = alduin["mechanics"]["elder-scrolls-2e"]
    scores = [block[score] for score in ("hp", "STR", "DEX", "WIL")]
    assert scores == [{"value": v, "max": v} for v in (18, 18, 14, 18)] and block["armor"] == 3
    assert alduin["mechanics"]["grimscrolls"]["tier"] == "boss"  # kept for a Grimscrolls world
    trackers = cli("track", "list", "--gm").out
    assert "The World-Eater's Hunger 0/6" in trackers and "The Blades' Patience 1/4" in trackers
    assert "Blades' Patience" not in cli("track", "list").out  # the clocks are the GM's
    assert "npc Maven Black-Briar [rival-1]" in _draft(cli, "hold", {"hold": "The Rift"})
    jarl = cli("show", "Laila Law-Giver").out  # the Jarls of 4E 201 are no secret
    assert "role: Jarl of the Rift" in jarl and "rules → loc:the-rift" in jarl


def test_under_grimscrolls_a_frame_brings_cards_and_pools_a_prince_his_bargain(cli: Cli) -> None:
    _world(cli, "grimscrolls")
    said = _draft(cli, "frame", {"frame": "Dawnguard"})
    assert "kind: pool, pool: pressure" in said
    card = _record(cli, "Lord Harkon")["mechanics"]["grimscrolls"]
    # The card's own role, not the cast line's (a record's role is in `fields`).
    assert (card["tier"], card["role"]) == ("boss", "skirmisher")
    trackers = cli("track", "list", "--gm").out
    assert "The Tyranny Clock 6d" in trackers and "Serana's Trust 3" in trackers
    rolled = cli("track", "roll", "the-tyranny-clock")
    assert rolled.code == 0 and "The Tyranny Clock" in rolled.out
    bargain = _draft(cli, "daedric-quest", {"quest": "The House of Horrors"})
    assert "Molag Bal's quest" in bargain and "Molag Bal's 8d Patience pool" in bargain
    notes = cli("show", "quest:the-house-of-horrors", "--gm", "--detail", "full").out
    assert "`grimscrolls.molag-bal`" in notes


def test_under_another_system_the_clocks_are_clocks_and_the_numbers_are_kept(cli: Cli) -> None:
    _world(cli, "cairn-2e")
    said = _draft(cli, "frame", {"frame": "The Dark Brotherhood"})
    assert "This world plays cairn-2e, neither Elder Scrolls system" in said
    assert "Suspicion 0/4" in cli("track", "list", "--gm").out
    cicero = _record(cli, "Cicero")  # both systems' blocks kept, neither read
    assert set(cicero["mechanics"]) == {"elder-scrolls-2e", "grimscrolls"}
