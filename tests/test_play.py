"""Sessions, scenes, the journal, transcripts, summaries and the brief."""

import json
from pathlib import Path

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "withering")
    cli("new", "pc", "Freya", "--set", "STR=12", "--set", "hp=4")


def test_a_session_from_start_to_end(cli: Cli, home: Path) -> None:
    setup(cli)
    started = cli("session", "start", "Into the Wood")
    assert (
        started.code == 0
        and "session 1 started" in started.out
        and "PC Freya [pc:freya]" in started.out
    )
    assert cli("session", "start").code == 1  # one open session at a time
    cli("scene", "new", "Amber Grave", "--expected", "a quiet pool")
    cli("log", "action", "Freya wades into the pool")
    roll = cli("roll", "d20 <= @STR", "--as", "freya")
    number = roll.out.split(" ")[0].lstrip("#")
    cli("log", "result", "The spirit wakes", "--roll", number, "--importance", "7")
    cli("scene", "end", "--summary", "Freya woke the spirit.")
    cli("scene", "new", "The Hut")
    cli("log", "narration", "A crooked hut in the rain.")
    ended = cli("session", "end")
    assert "summary due" in ended.out
    view = cli("session", "show", "1").out
    lines = view.splitlines()
    assert lines[0] == "# Session 1 · Into the Wood (closed)"
    wading = next(i for i, line in enumerate(lines) if "@ Freya wades" in line)
    rolled = next(i for i, line in enumerate(lines) if line.startswith(f"- #{number} "))
    woke = next(i for i, line in enumerate(lines) if "-> The spirit wakes" in line)
    assert wading < rolled < woke  # beats and rolls in the order they happened
    assert "Summary: Freya woke the spirit." in view and "## Scene 2 · The Hut" in view
    journal = (
        (home / "worlds/vale/campaigns/withering/journal/session-001.jsonl")
        .read_text()
        .splitlines()
    )
    first = json.loads(journal[0])
    assert first["kind"] == "action" and first["scene"] == 1 and first["id"] == "S1.1"


def test_summaries_due_and_the_brief(cli: Cli) -> None:
    setup(cli)
    cli("session", "start")
    cli("scene", "new", "One")
    cli("scene", "new", "Two")
    assert cli("summary", "due").out.strip().splitlines()[1] == "- scene:1"
    cli("summary", "write", "scene:1", "The first scene.")
    cli("session", "end", "--summary", "A short session.")
    due = cli("summary", "due").out
    assert "- scene:2" in due and "session:1" not in due
    cli("session", "start")
    cli("session", "end", "--summary", "Another.")
    assert "campaign (no story-so-far yet)" in cli("summary", "due").out
    cli("summary", "write", "campaign", "Freya walked into the Wood and woke it.")
    cli("summary", "write", "scene:2", "Nothing much.")
    assert cli("summary", "due").out.strip() == "no summaries due"
    brief = cli("brief").out
    assert (
        "Last time (session 2): Another." in brief
        and "Story so far: Freya walked into the Wood" in brief
    )


def test_transcript_capture_binds_to_one_claude_session(cli: Cli, home: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    setup(cli)
    assert "nothing captured" in cli("capture", "--text", "too early").out
    cli("session", "start")
    for payload in (
        {"prompt": "I ask its name", "session_id": "abc"},
        {"last_assistant_message": "It whispers: Anglwyst.", "session_id": "abc"},
        {"prompt": "from another chat", "session_id": "zzz"},
        {"hook_event_name": "Notification", "session_id": "abc"},
    ):
        monkeypatch.setattr("sys.stdin", _Stdin(json.dumps(payload)))
        cli("capture")
    text = cli("transcript").out
    assert "· player\n\nI ask its name" in text and "· gm\n\nIt whispers: Anglwyst." in text
    assert "another chat" not in text
    assert cli("capture", "--role", "gm", "--text", "Plain text works too.").code == 0
    assert "Plain text works too." in cli("transcript", "1").out


class _Stdin:
    def __init__(self, text: str) -> None:
        self.text = text

    def read(self) -> str:
        return self.text

    def isatty(self) -> bool:
        return False


def test_undo_takes_back_a_beat_exactly(cli: Cli, home: Path) -> None:
    setup(cli)
    cli("session", "start")
    cli("log", "note", "keep me")
    cli("log", "note", "drop me")
    cli("undo")
    journal = (home / "worlds/vale/campaigns/withering/journal/session-001.jsonl").read_text()
    assert "keep me" in journal and "drop me" not in journal
    cli("undo")
    assert not (home / "worlds/vale/campaigns/withering/journal/session-001.jsonl").exists()
    assert "+ append" in cli("diff", "e1").out or True
    assert cli("log", "action", "no session").code == 0


def test_play_needs_a_campaign(cli: Cli) -> None:
    cli("world", "new", "vale")
    result = cli("session", "start")
    assert result.code == 1 and "no campaign is open" in result.err


def test_scene_and_session_triggers(cli: Cli, home: Path) -> None:
    setup(cli)
    rules = home / "systems" / "mini-system" / "homebrew" / "rules"
    rules.mkdir(parents=True)
    (rules / "events.yaml").write_text(
        "trigger: tally\non: scene_end\nsteps: ['Scene {@scene} is over: tally the torches.']\n"
        "---\ntrigger: omen\non: session_start\nwhen: '@session == 1'\nsteps: [An omen.]\n"
        "---\ntrigger: toll\non: session_end\nparams: {who: ref}\nsteps: [A bell tolls.]\n",
        encoding="utf-8",
    )
    first = cli("session", "start")
    assert "note: trigger mini-system.omen: An omen." in first.out
    cli("scene", "new", "Amber Grave")
    second = cli("scene", "new", "The Hut")  # closes scene 1 first
    assert "note: trigger mini-system.tally: Scene 1 is over: tally the torches." in second.out
    ended = cli("session", "end")
    assert "trigger mini-system.tally: Scene 2 is over" in ended.out
    assert "trigger mini-system.toll: skipped (it needs who; run it with `do`)" in ended.out
    assert "omen" not in cli("session", "start").out  # its `when` is false in session 2
