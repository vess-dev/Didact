"""Jumping back (`undo --to`): the library as it was right after an event, byte for byte, and
everything after it brought back by jumping to a later point.

The session is the undo sweep's, so every kind of change is jumped over.
"""

import json
import shlex
from pathlib import Path
from typing import Any

from tests.conftest import Cli
from tests.test_undo_sweep import SESSION, _differences, _files


def _json(cli: Cli, *argv: str) -> Any:
    result = cli(*argv, "--format", "json")
    assert result.code == 0, result.err
    return json.loads(result.out)


def _newest(cli: Cli) -> int:
    """The newest change's number."""
    return int(_json(cli, "history", "--limit", "1")["events"][0]["seq"])


def test_jumping_back_gives_the_library_as_it_was_and_forward_brings_it_back(
    cli: Cli, home: Path
) -> None:
    lines = [line for line in SESSION.strip().splitlines() if line.strip()]
    snapshots: list[tuple[int, dict[str, bytes]]] = []
    for line in lines:
        result = cli(*shlex.split(line))
        assert result.code == 0, (line, result.err)
        snapshots.append((_newest(cli), _files(home)))
    end, last = _files(home), snapshots[-1][0]
    for point, then in (snapshots[len(snapshots) // 2], snapshots[2]):
        preview = _json(cli, "undo", "--to", f"e{point}", "--dry-run")
        assert preview["dry_run"] is True and preview["to"] == point
        assert all(step["seq"] > point for step in preview["steps"])
        assert _files(home) == end  # a preview changes nothing
        done = cli("undo", "--to", f"e{point}")
        assert done.code == 0, done.err
        assert f"✔ jumped back to #e{point}" in done.out
        assert _files(home) == then, _differences(then, _files(home))
        forward = cli("undo", "--to", f"e{last}")  # the newest change before the jump
        assert forward.code == 0, forward.err
        assert _files(home) == end, _differences(end, _files(home))
        last = _newest(cli)
    nothing = cli("undo", "--to", f"e{last}")
    assert nothing.code == 0 and "nothing to take back" in nothing.out


def test_a_jump_takes_rolls_back_and_a_later_one_brings_them_back(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    point = _newest(cli)
    cli("roll", "2d6")
    cli("new", "npc", "Tom")
    cli("roll", "d20")
    jumped = cli("undo", "--to", f"e{point}")
    assert "took back 1 change and 2 rolls" in jumped.out
    assert "- marked #r1 undone" in jumped.out and "- marked #r2 undone" in jumped.out
    assert cli("show", "tom").code != 0
    rolls = cli("rolls").out
    assert rolls.count("(undone)") == 2
    forward = cli("undo", "--to", f"e{_newest(cli) - 3}")  # the last change before the jump
    assert "- #r1 stands again" in forward.out and "- #r2 stands again" in forward.out
    assert cli("show", "tom").code == 0 and "(undone)" not in cli("rolls").out


def test_a_jump_redoes_what_was_undone_after_the_point(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "npc", "Tom")
    point = _newest(cli)
    assert cli("undo").code == 0  # Tom goes, after the point
    assert cli("show", "tom").code != 0
    assert cli("undo", "--to", f"e{point}").code == 0  # as it was then: Tom was there
    assert cli("show", "tom").code == 0


def test_a_jump_goes_through_whole_or_not_at_all(cli: Cli, home: Path) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    point = _newest(cli)
    cli("new", "npc", "Tom")
    cli("new", "npc", "Ann")
    tom = next(home.rglob("npc/tom.md"))
    tom.write_text(tom.read_text(encoding="utf-8") + "\nEdited by hand.\n", encoding="utf-8")
    refused = cli("undo", "--to", f"e{point}")
    assert refused.code != 0 and "was changed after" in refused.err
    assert f"undo --to e{point} --force" in refused.err
    assert cli("show", "ann").code == 0  # nothing was taken back
    forced = cli("undo", "--to", f"e{point}", "--force")
    assert forced.code == 0, forced.err
    assert cli("show", "ann").code != 0 and cli("show", "tom").code != 0


def test_jumping_back_says_what_it_can_and_cant_do(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "npc", "Tom")
    alone = cli("undo", "--to", "e1", "--event", "e2")
    assert alone.code != 0 and "--to goes alone" in alone.err
    bad = cli("undo", "--to", "yesterday")
    assert bad.code != 0 and "invalid event" in bad.err
    missing = cli("undo", "--to", "e999")
    assert missing.code != 0 and "no event #e999" in missing.err
    cli("history", "--clear", "--yes")
    cleared = cli("undo", "--to", "e1")
    assert (
        cleared.code != 0 and "the history before" in cleared.err and "was cleared" in cleared.err
    )
