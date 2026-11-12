"""Correcting the journal: beats edited or removed, and transcripts cleared."""

import json
from pathlib import Path
from typing import Any

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "pc", "Freya")
    cli("new", "npc", "Tom")
    cli("session", "start")


def data(cli: Cli, *args: str) -> Any:  # parsed JSON, read freely in tests
    done = cli(*args, "--format", "json")
    assert done.code == 0, done.err
    return json.loads(done.out)


def test_a_beat_is_corrected_and_its_chronicles_follow(cli: Cli) -> None:
    setup(cli)
    cli("log", "consequence", "Tom betrays Freya")
    edited = cli("beat", "edit", "S1.1", "--about", "tom", "--about", "freya", "--importance", "8")
    assert edited.code == 0
    assert [b["id"] for b in data(cli, "show", "freya")["chronicle"]] == ["S1.1"]
    cli("beat", "edit", "s1.1", "--not-about", "freya", "--secret", "--kind", "result")
    assert "chronicle" not in data(cli, "show", "freya")
    assert "chronicle" not in data(cli, "show", "tom")  # secret now: the player view hides it
    beat = data(cli, "show", "tom", "--gm")["chronicle"][0]
    assert beat["kind"] == "result" and beat["secret"] and beat["importance"] == 8
    assert "(a secret beat)" in cli("history").out  # the change log doesn't spill it
    cli("beat", "edit", "S1.1", "--public", "--text", "Tom sells the route")
    assert data(cli, "show", "tom")["chronicle"][0]["text"] == "Tom sells the route"
    assert cli("beat", "edit", "S1.9").code == 1
    assert cli("beat", "edit", "nonsense").code == 1
    assert cli("beat", "edit", "S1.1", "--secret", "--public").code == 1
    assert cli("undo").code == 0
    assert data(cli, "show", "tom", "--gm")["chronicle"][0]["text"] == "Tom betrays Freya"


def test_removed_beats_keep_their_numbers_taken(cli: Cli) -> None:
    setup(cli)
    cli("log", "action", "one")
    cli("log", "action", "two")
    assert cli("beat", "rm", "S1.1").code == 0
    assert data(cli, "log", "action", "three")["beat"]["id"] == "S1.3"  # never S1.2 again
    shown = cli("session", "show").out
    assert "one" not in shown and "S1.2" in shown and "S1.3" in shown
    assert cli("undo").code == 0 and cli("undo").code == 0  # the new beat, then the removal
    assert "one" in cli("session", "show").out


def test_transcripts_are_cleared_and_come_back(cli: Cli, home: Path) -> None:
    setup(cli)
    cli("capture", "--role", "player", "--text", "I open the door.")
    cli("capture", "--role", "gm", "--text", "It creaks.")
    assert "I open the door." in cli("transcript").out
    cleared = cli("transcript", "--clear")
    assert cleared.code == 0 and "cleared 1 transcript" in cleared.out
    assert "no transcript" in cli("transcript").out
    assert "no transcript to clear" in cli("transcript", "--clear", "--all").out
    assert cli("undo").code == 0 and "It creaks." in cli("transcript").out
