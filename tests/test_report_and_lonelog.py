"""Outcomes that weren't rolled here (`report`), and the journal in Lonelog notation."""

import json
from pathlib import Path

from tests.conftest import Cli


def _campaign(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "pc", "Freya", "--fill")
    cli("new", "npc", "Old Tom")
    cli("new", "loc", "The Mill")


def test_a_report_is_a_numbered_roll_that_replay_passes_over(cli: Cli) -> None:
    _campaign(cli)
    done = cli("report", "the tower stands", "--of", "the tower", "--format", "json")
    assert done.code == 0, done.err
    number = json.loads(done.out)["roll"]
    assert f"#r{number} reported the tower: the tower stands" in cli("rolls").out
    assert "beat" not in json.loads(done.out)  # no session open: no journal line
    assert cli("roll", "2d6").code == 0
    replayed = cli("replay")
    assert replayed.code == 0 and "reproduced exactly" in replayed.out


def test_a_report_in_a_session_is_a_result_beat_on_the_chronicle(cli: Cli) -> None:
    _campaign(cli)
    cli("session", "start")
    done = cli("report", "the Queen of Spades", "--of", "the deck", "--about", "Old Tom")
    assert done.code == 0, done.err
    assert "-> the deck: the Queen of Spades" in done.out
    assert "the Queen of Spades" in cli("show", "Old Tom").out
    assert cli("report", "--of", "x").code == 2  # nothing said


def test_the_journal_exports_as_lonelog_and_keeps_secrets(cli: Cli, tmp_path: Path) -> None:
    _campaign(cli)
    cli("session", "start")
    cli("scene", "new", "The drowned mill")
    cli("log", "action", "Freya pushes the door", "--about", "freya", "--about", "The Mill")
    cli("roll", "2d6", "--reason", "force the door")
    cli("report", "the Queen of Spades", "--of", "the deck", "--about", "Old Tom")
    cli("ask", "Is the miller home?", "--odds", "likely")
    cli("log", "consequence", "Tom flees upstream", "--about", "Old Tom")
    cli("log", "note", "Raiders gather", "--secret")
    cli("scene", "end")
    cli("scene", "new", "Upstream")
    cli("log", "result", "Tracks in the mud")
    target = tmp_path / "run.log.md"
    assert cli("export", "--as", "lonelog", "--to", str(target)).code == 0
    text = target.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert "S1 *The drowned mill*" in lines and "S2 *Upstream*" in lines
    assert "@ Freya pushes the door [PC:Freya] [L:The Mill]" in lines
    assert any(line.startswith("d: 2d6 → ") and "force the door" in line for line in lines)
    assert "-> the deck: the Queen of Spades (#r" in text and "[N:Old Tom]" in text
    assert any(line.startswith("? Is the miller home?") for line in lines)
    assert "=> Tom flees upstream [N:Old Tom]" in lines
    assert "Raiders" not in text  # the secret beat
    assert "reported" not in text  # a report is its result beat, not a roll line too
    assert lines.index("@ Freya pushes the door [PC:Freya] [L:The Mill]") < lines.index(
        "=> Tom flees upstream [N:Old Tom]"
    )


def test_lonelog_needs_a_campaign(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    result = cli("export", "--as", "lonelog")
    assert result.code == 1 and "a journal belongs to a campaign" in result.err
