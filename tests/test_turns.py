"""Turn groups: everything done for one player message is taken back together."""

import json

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "pc", "Freya", "--set", "STR=12", "--set", "hp=4")
    cli("session", "start")


def hook(cli: Cli, payload: dict[str, str]) -> str:
    result = cli("capture", "--text", json.dumps({**payload, "session_id": "abc"}))
    assert result.code == 0
    return result.out


def test_undo_turn_takes_back_changes_beats_and_rolls(cli: Cli) -> None:
    setup(cli)
    assert "captured a player turn" in hook(cli, {"prompt": "I attack the troll"})
    cli("spawn", "troll")
    cli("do", "attack", "attacker=freya", "target=troll", "weapon=d8")
    cli("log", "action", "Freya swings at the troll")
    cli("inv", "add", "freya", "Rope")
    hook(cli, {"last_assistant_message": "The troll staggers."})
    hook(cli, {"prompt": "wait, take that back"})
    preview = cli("undo", "--turn", "--dry-run").out
    assert preview.startswith("dry run: would take back turn t1:")
    taken = cli("undo", "--turn")
    assert taken.code == 0 and "✔ took back turn t1: 4 changes, 1 roll" in taken.out
    assert cli("show", "troll").code == 1  # the spawn is gone
    assert "- nothing" in cli("inv", "show", "freya").out
    view = cli("session", "show").out
    assert "Freya swings" not in view and "(undone)" in view
    transcript = cli("transcript").out
    assert "I attack the troll" in transcript and "take that back" in transcript  # kept
    assert cli("undo", "--turn").code == 1  # t2 has done nothing yet, and t1 is gone


def test_turns_are_numbered_and_can_be_named(cli: Cli) -> None:
    setup(cli)
    hook(cli, {"prompt": "I hail the ferryman"})
    cli("new", "npc", "Old Tom")
    hook(cli, {"prompt": "I head north"})
    cli("time", "advance", "1", "watch")
    cli("inv", "add", "freya", "Rope")
    assert "turn t1" in cli("undo", "--event", "t1", "--dry-run").out
    assert "took back turn t1: 1 change, 0 rolls" in cli("undo", "--event", "t1").out
    assert cli("show", "old-tom").code == 1 and "Rope" in cli("inv", "show", "freya").out
    assert "took back turn t2: 2 changes" in cli("undo", "--turn").out
    cli("inv", "add", "freya", "Torch")  # still turn t2: a turn lasts until the next begins
    started = cli("turn", "begin", "I", "search", "the", "room")
    assert "turn t3 begins" in started.out
    cli("inv", "add", "freya", "Chalk")
    assert "turn t3 ends" in cli("turn", "end").out
    cli("inv", "add", "freya", "Lamp")  # no turn is open: not part of t3
    assert cli("undo", "--turn").code == 1  # t3's chalk is under the lamp: a conflict
    cli("undo")  # the lamp (no turn)
    assert "took back turn t3: 1 change" in cli("undo", "--turn").out
    shown = cli("inv", "show", "freya").out
    assert "Chalk" not in shown and "Torch" in shown
