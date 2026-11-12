"""A seeded scenario plays a 3-scene session through the CLI.

The journal, the summaries-due list and the brief come out right, the transcript holds every
turn, and every roll replays exactly. Two runs with the same seed roll the same dice.
"""

import json
import re
from pathlib import Path

import pytest

from tests.conftest import Cli


def hook(cli: Cli, **payload: str) -> None:
    result = cli("capture", "--hook", "--text", json.dumps({**payload, "session_id": "s1"}))
    assert result.code == 0 and result.out == ""


def play(cli: Cli) -> list[str]:
    """The scripted session. Returns the roll lines, to compare runs."""
    assert cli("world", "new", "vale", "--system", "mini-system", "--seed", "vald-1").code == 0
    assert cli("campaign", "new", "withering", "--seed", "withering-1").code == 0
    cli("campaign", "profile", "role=gm", "tone=grim", "lines+=spiders", "invention=book-first")
    cli("new", "pc", "Freya", "--set", "STR=12", "--set", "DEX=14", "--set", "WIL=9",
        "--set", "hp=4")  # fmt: skip
    cli(
        "new", "npc", "Sweeney", "--body", "Guards the wood.\n## Secrets\n- He is Anglwyst's son.\n"
    )
    cli("new", "loc", "The Wood")
    cli("new", "loc", "Amber Grave", "--set", "region=loc:the-wood")
    cli("new", "loc", "The Hut", "--set", "region=loc:the-wood")
    cli("link", "amber-grave", "path", "loc:the-hut")
    cli("spawn", "wolf")
    assert "session 1 started" in cli("session", "start", "Into the Wood").out

    # Scene 1: the grave. A save against the sap.
    cli("scene", "new", "Amber Grave", "--expected", "a quiet pool of sap")
    hook(cli, prompt="I wade into the sap pool to reach the crystal.")
    cli("visit", "amber-grave")
    cli("inv", "add", "freya", "Rope", "Torch")
    save = cli("do", "save", "who=freya", "attr=DEX")
    assert save.code == 0
    cli("log", "action", "Freya wades into the sap for the crystal")
    cli("log", "result", "The sap holds her fast", "--importance", "6")
    hook(cli, last_assistant_message="The sap closes around your knees.")
    cli("scene", "end", "--summary", "Freya reached the crystal in the sap pool.")

    # Scene 2: the wolf. A short fight.
    cli("scene", "new", "Wolf")
    hook(cli, prompt="I draw my knife and face the wolf.")
    assert cli("combat", "start", "--party", "wolf").code == 0
    assert cli("combat", "hit", "freya", "wolf", "weapon=d6").code == 0
    cli("combat", "next")
    cli("combat", "end")
    cli("log", "consequence", "The wolf flees into the dark")
    hook(cli, last_assistant_message="The wolf yelps and bolts.")
    cli("scene", "end")  # no summary yet: it will be due

    # Scene 3: the hut. Night falls; Sweeney talks.
    cli("scene", "new", "The Hut")
    hook(cli, prompt="I knock on the hut's door.")
    cli("visit", "the-hut")
    cli("time", "advance", "1", "watch")
    cli("inv", "use", "freya", "torch")
    cli("log", "dialogue", "Sweeney: Come in out of the cold.")
    hook(cli, last_assistant_message="Sweeney opens the door.")
    cli("session", "end")
    rolls = cli("rolls", "--format", "json").out
    return [str(r["line"]) for r in json.loads(rolls)["rolls"]]


def test_a_seeded_three_scene_session(
    cli: Cli, home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = play(cli)
    assert len(first) >= 2  # the save and the damage, at least

    view = cli("session", "show", "1").out
    assert view.startswith("# Session 1 · Into the Wood (closed)")
    scenes = re.findall(r"^## Scene (\d) · (.+)$", view, re.MULTILINE)
    assert scenes == [("1", "Amber Grave"), ("2", "Wolf"), ("3", "The Hut")]
    lines = view.splitlines()
    wading = next(i for i, line in enumerate(lines) if "@ Freya wades into the sap" in line)
    held = next(i for i, line in enumerate(lines) if "-> The sap holds her fast" in line)
    fled = next(i for i, line in enumerate(lines) if "=> The wolf flees into the dark" in line)
    said = next(i for i, line in enumerate(lines) if '"Sweeney: Come in out of the cold."' in line)
    assert wading < held < fled < said
    assert "Summary: Freya reached the crystal in the sap pool." in view

    due = cli("summary", "due").out.splitlines()
    assert due[1:4] == ["- scene:2", "- scene:3", "- session:1"]

    brief = cli("brief").out.splitlines()
    assert brief[0] == 'Vale / "Withering" (mini-system) · session 1 (closed) · scene 3'
    assert brief[1].startswith("Profile: role gm · tone grim · lines: spiders")
    assert "Time: day 1, 08:00 (afternoon watch)" in brief  # 3 watches a day: one passed
    assert "Where: The Hut [loc:the-hut]" in brief
    assert any(line.startswith("PC Freya [pc:freya] · STR 12") for line in brief)
    assert "Due: summary for scene:2, scene:3, session:1" in brief
    assert not any("Anglwyst" in line for line in brief)  # secrets stay out

    transcript = cli("transcript", "1").out
    for said_text in (
        "I wade into the sap pool", "The sap closes around", "I draw my knife",
        "The wolf yelps", "I knock on the hut", "Sweeney opens the door",
    ):  # fmt: skip
        assert said_text in transcript
    assert transcript.count("· player") == 3 and transcript.count("· gm") == 3

    assert re.match(r"✔ \d+ rolls reproduced exactly", cli("replay").out)
    torch = cli("inv", "show", "freya").out
    assert "Torch (1 slot): uses 2/3" in torch

    # The same seeds roll the same dice in a fresh library.
    monkeypatch.setenv("DIDACT_HOME", str(home.parent / "second-home"))
    cli("init")
    second = play(cli)
    strip = [re.sub(r"^#r\d+ ", "", line) for line in first]
    assert [re.sub(r"^#r\d+ ", "", line) for line in second] == strip
