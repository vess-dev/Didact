"""A merge across types folds in what the survivor's sheet has a field for, and says what it
leaves out (the `mini-system` fixture: an npc folded into a pack animal)."""

import json

from tests.conftest import Cli


def test_a_merge_leaves_out_what_the_survivors_sheet_lacks(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "mini-system").code == 0
    assert cli("new", "npc", "Old Bess", "--set", "hp=3", "--set", "STR=11").code == 0
    assert cli("new", "mule", "Bess", "--set", "hp=5").code == 0
    merged = cli("merge", "npc:old-bess", "mule:bess", "--yes")
    assert merged.code == 0, merged.err
    assert "left out what a mule has no field for: mini-system.STR" in merged.out
    assert "kept mule:bess's value for: mechanics.mini-system.hp" in merged.out
    shown = cli("show", "mule:bess")
    assert "problems" not in shown.out  # no stray data: nothing to report
    record = json.loads(cli("show", "mule:bess", "--format", "json").out)
    assert set(record["mechanics"]["mini-system"]) <= {"hp", "packs"}
    assert "Old Bess" in record["aliases"]
