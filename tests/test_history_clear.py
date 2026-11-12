"""Clearing the history: a preview first, numbering that carries on, the dice record kept unless
asked, save points the log can no longer rebuild removed, and later undo still working."""

import json
import re
from pathlib import Path

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "pc", "Wren", "--set", "hp=4")
    cli("session", "start")
    cli("scene", "new", "The Mill")


def log_file(home: Path) -> Path:
    return home / "log" / "events.jsonl"


def last_event(cli: Cli) -> int:
    return int(json.loads(cli("status", "--format", "json").out)["last_event"])


def event_of(out: str) -> int:
    """The event number a `✔ … (#e12)` line reports."""
    found = re.search(r"\(#e(\d+)\)", out)
    assert found, out
    return int(found.group(1))


def hp(cli: Cli) -> int:
    wren = json.loads(cli("show", "wren", "--format", "json").out)
    return int(wren["mechanics"]["mini-system"]["hp"]["value"])


def test_the_preview_says_what_would_go_and_changes_nothing(cli: Cli, home: Path) -> None:
    setup(cli)
    cli("save", "start")
    cli("set", "wren", "hp-=1")
    cli("roll", "2d6", "--reason", "climb")
    before = log_file(home).read_bytes()
    preview = cli("history", "--clear")
    assert preview.code == 0
    out = preview.out
    assert out.startswith("Clearing would drop ") and "KB of the log's" in out
    assert "changes and undos with their file snapshots" in out
    assert "- stays: 1 roll or note, the dice record" in out
    assert "undo, redo, `diff`" in out and "`rewind` and `campaign fork --at`" in out
    assert "save points removed: 'start' (campaign run, #e" in out
    assert "can't be undone" in out and "`didact snapshot`" in out
    assert "`didact history --clear --yes`" in out
    assert log_file(home).read_bytes() == before  # a preview writes nothing
    assert "- start" in cli("saves").out
    data = json.loads(cli("history", "--clear", "--rolls", "--format", "json").out)
    assert data["preview"] is True and data["next"] == "didact history --clear --rolls --yes"
    assert data["dice"] == 1 and data["kept"] == 0 and data["saves"][0]["label"] == "start"
    rolls_preview = cli("history", "--clear", "--rolls").out
    assert "`rolls`, `replay` and the roll lines in `session show`" in rolls_preview
    assert "beats stay" in rolls_preview


def test_clearing_shrinks_the_log_and_numbering_carries_on(cli: Cli, home: Path) -> None:
    setup(cli)
    cli("new", "npc", "Tom")
    cli("set", "wren", "hp-=1")
    last = last_event(cli)
    size = log_file(home).stat().st_size
    done = json.loads(cli("history", "--clear", "--yes", "--format", "json").out)
    assert done["event"] == last + 1 and done["events"] == last
    assert log_file(home).stat().st_size == done["log_bytes"] < size
    history = cli("history").out
    assert f"#e{last + 1}" in history and "history cleared:" in history
    assert f"#e{last} " not in history  # the old changes are gone
    assert cli("undo").out == "nothing to undo\n"
    assert cli("redo").out == "nothing to redo\n"
    marker = cli("undo", "--event", f"e{last + 1}")
    assert marker.code == 1 and "a cleared history can't come back" in marker.err
    assert "history cleared:" in cli("audit").out
    gone = cli("diff", "e2")
    assert gone.code == 1 and f"the history before #e{last + 1} was cleared" in gone.err
    assert event_of(cli("new", "npc", "Ann").out) == last + 2  # never a number used before
    assert cli("show", "tom").code == 0 and hp(cli) == 3  # files are untouched
    assert cli("undo").code == 0 and cli("show", "ann").code == 1  # new changes undo as usual


def test_the_dice_record_stays_by_default(cli: Cli) -> None:
    setup(cli)
    cli("roll", "2d6", "--reason", "climb the wall")
    cli("roll", "d6")
    cli("undo", "--event", "r2")
    cli("log", "action", "Wren climbs")
    cli("history", "--clear", "--yes")
    rolls = cli("rolls").out
    assert "#r1" in rolls and "climb the wall" in rolls and "#r2" in rolls and "(undone)" in rolls
    view = cli("session", "show").out
    assert "#r1 2d6" in view and "Wren climbs" in view and "(undone)" in view
    assert "2 rolls reproduced exactly" in cli("replay").out
    assert cli("diff", "r1").code == 0
    again = cli("history", "--clear", "--yes")  # only rolls and notes are left before now
    assert "nothing to clear: no changes" in again.out and "`--rolls`" in again.out


def test_rolls_go_with_rolls_and_roll_numbers_never_repeat(cli: Cli, home: Path) -> None:
    setup(cli)
    cli("roll", "2d6")
    cli("roll", "d20")
    cli("log", "action", "Wren climbs")
    done = cli("history", "--clear", "--rolls", "--yes")
    assert done.code == 0 and "✔ cleared" in done.out
    assert "no rolls yet" in cli("rolls").out
    assert "no rolls to replay" in cli("replay").out
    view = cli("session", "show").out
    assert "#r1" not in view and "Wren climbs" in view  # the journal's beats stay
    gone = cli("diff", "r1")
    assert gone.code == 1 and "rolls went when the history was cleared" in gone.err
    (home / "log" / "counters.json").unlink()  # lost: rebuilt from the log and its marker
    assert cli("roll", "d6").out.startswith("#r3 ")


def test_clearing_rolls_leaves_one_marker_that_carries_the_numbers(cli: Cli, home: Path) -> None:
    setup(cli)
    cli("roll", "d6")
    cli("new", "npc", "Ann")
    cli("history", "--clear", "--yes")  # a first marker; the roll stays
    cli("roll", "d6")
    cli("history", "--clear", "--rolls", "--yes")
    assert cli("history").out.count("history cleared:") == 1  # the new marker stands in
    assert len(log_file(home).read_text().splitlines()) == 1
    assert "nothing to clear" in cli("history", "--clear", "--rolls", "--yes").out
    (home / "log" / "counters.json").unlink()
    assert cli("roll", "d4").out.startswith("#r3 ")


def test_save_points_older_than_the_cut_go_and_later_ones_still_rewind(cli: Cli) -> None:
    setup(cli)
    cli("save", "early")
    cli("set", "wren", "hp-=1")
    cut = event_of(cli("save", "later").out)  # the save itself; `later` is just before it
    cli("set", "wren", "hp-=2")
    preview = cli("history", "--clear", "--before", f"e{cut}").out
    assert "'early' (campaign run" in preview and "'later'" not in preview
    done = cli("history", "--clear", "--before", f"e{cut}", "--yes")
    assert done.code == 0 and "save points removed (#e" in done.out and "'early'" in done.out
    saves = cli("saves").out
    assert "- later" in saves and "early" not in saves
    assert hp(cli) == 1
    assert cli("rewind", "later").code == 0 and hp(cli) == 3  # still rebuilds
    assert cli("undo").code == 0 and hp(cli) == 1
    old = cli("rewind", "e2")
    assert old.code == 1 and "was cleared" in old.err and "pick an event from" in old.err
    assert cli("rewind", "early").code == 1
    forked = cli("campaign", "fork", "what-if", "--at", "later")
    assert forked.code == 0
    cli("campaign", "open", "what-if")
    assert hp(cli) == 3


def test_a_save_point_brought_back_by_undo_is_refused(cli: Cli) -> None:
    setup(cli)
    cli("save", "early")
    cli("set", "wren", "hp-=1")
    cli("history", "--clear", "--yes")
    assert "remove 1 save point" in cli("undo").out  # the removal was a change like any other
    refused = cli("rewind", "early")
    assert refused.code == 1 and "can't go back to 'early'" in refused.err
    assert "didact save --remove early" in refused.err
    assert cli("campaign", "fork", "what-if", "--at", "early").code == 1


def test_before_keeps_later_undo_and_redo_working(cli: Cli) -> None:
    setup(cli)
    cli("set", "wren", "hp-=1")
    found = re.search(r" as #e(\d+)", cli("undo").out)  # an undo of a change that goes
    assert found
    undone = int(found.group(1))
    cli("set", "wren", "hp-=2")
    assert hp(cli) == 2
    assert cli("history", "--clear", "--before", f"e{undone}", "--yes").code == 0
    history = cli("history").out
    assert f"#e{undone} " in history and "(undone)" not in history  # its target is gone: fine
    assert cli("undo").code == 0 and hp(cli) == 4
    assert cli("redo").code == 0 and hp(cli) == 2
    assert cli("undo").code == 0 and hp(cli) == 4
    assert cli("undo").out == "nothing to undo\n"  # the change it undid went with the history
    assert cli("redo").code == 0 and hp(cli) == 2
    assert cli("redo").out == "nothing to redo\n"
    assert cli("audit").code == 0


def test_deleted_records_leave_the_log(cli: Cli, home: Path) -> None:
    setup(cli)
    cli("new", "npc", "Mirelle", "--body", "Keeper of the quincunx cipher.")
    cli("rm", "mirelle")
    cli("world", "new", "coast", "--no-use")
    cli("new", "npc", "Bell", "--body", "Rings for the zephyrine dead.", "--world", "coast")
    assert cli("world", "delete", "coast", "--yes").code == 0
    text = log_file(home).read_text()
    assert "quincunx" in text and "zephyrine" in text
    cli("history", "--clear", "--yes")
    text = log_file(home).read_text()
    assert "quincunx" not in text and "zephyrine" not in text


def test_turns_from_before_the_cut_are_over(cli: Cli) -> None:
    setup(cli)
    cli("turn", "begin", "I", "search", "the", "mill")
    cli("inv", "add", "wren", "Rope")
    cli("roll", "d6")
    cli("history", "--clear", "--yes")
    over = cli("undo", "--turn")
    assert over.code == 1 and "no turn to take back" in over.err
    named = cli("undo", "--event", "t1")
    assert named.code == 1 and "was cleared" in named.err
    cli("turn", "begin", "I", "climb")
    cli("inv", "add", "wren", "Torch")
    assert "took back turn t2: 1 change" in cli("undo", "--turn").out


def test_clearing_needs_clear_and_a_real_cut(cli: Cli) -> None:
    assert "nothing to clear" in cli("history", "--clear").out  # no library yet
    setup(cli)
    misplaced = cli("history", "--before", "e2")
    assert misplaced.code == 2 and "go with --clear" in misplaced.err
    assert cli("history", "--yes").code == 2
    one = cli("history", "wren", "--clear")
    assert one.code == 2 and "not one record's" in one.err
    roll = cli("history", "--clear", "--before", "r1")
    assert roll.code == 1 and "--before takes an event" in roll.err
    ahead = cli("history", "--clear", "--before", "e999")
    assert ahead.code == 1 and "there's no #e999 yet" in ahead.err
    assert "nothing to clear" in cli("history", "--clear", "--before", "e1").out
