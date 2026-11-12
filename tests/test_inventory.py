"""Inventory on slots sheets: add, drop, move, use, recharge; capacity and when_full."""

import json
import os
from pathlib import Path

import pytest

from tests.conftest import FIXTURE_PACKS, Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "pc", "Freya", "--set", "STR=12", "--set", "hp=4")
    cli("new", "pc", "Ansel", "--set", "STR=10", "--set", "hp=3")


def items(cli: Cli, who: str) -> list[object]:
    data = json.loads(cli("inv", "show", who, "--format", "json").out)
    listed = data["items"]
    assert isinstance(listed, list)
    return listed


def test_add_brings_compendium_details_and_stacks(cli: Cli) -> None:
    setup(cli)
    added = cli("inv", "add", "freya", "Longsword", "Rope")
    assert added.code == 0 and "(3/10 slots)" in added.out
    assert "Longsword: details from mini-system.longsword" in added.out
    assert cli("inv", "add", "freya", "Rope").code == 0  # stacks with the first rope
    listed = items(cli, "freya")
    assert listed[0] == {
        "name": "Longsword",
        "damage": "d8",
        "size": "bulky",
        "entry": "mini-system.longsword",
    }
    assert listed[1] == {"name": "Rope", "count": 2}
    shown = cli("inv", "show", "freya").out
    assert "Freya · inventory: 4/10 slots" in shown
    assert "- Longsword (bulky, 2 slots): damage d8" in shown
    assert "- Rope ×2 (2 slots)" in shown
    assert cli("inv", "add", "freya", "chainmail").code == 0
    assert "armor 2" in cli("show", "freya").out  # the derived armor reads the item


def test_capacity_when_full_and_force(cli: Cli) -> None:
    setup(cli)
    cli("inv", "add", "freya", "Longsword", "Chainmail", "Rope", "Spikes", "Chalk", "Pole")
    full = cli("inv", "add", "freya", "Rations", "Lamp")
    assert full.code == 0 and "(10/10 slots)" in full.out
    assert "note: inventory is full (10/10): hp = 0" in full.out
    assert "hp 0/4" in cli("show", "freya").out
    over = cli("inv", "add", "freya", "Sack")
    assert over.code == 1 and "Freya can't carry that: 11/10 slots" in over.err
    assert cli("inv", "add", "freya", "Sack", "--force").code == 2  # --force needs --reason
    forced = cli("inv", "add", "freya", "Sack", "--force", "--reason", "the Warden allows it")
    assert forced.code == 0 and "(11/10 slots)" in forced.out
    assert cli("campaign", "set", "strictness=lenient").code == 0
    lenient = cli("inv", "add", "freya", "Twine")
    assert lenient.code == 0 and "warning: Freya can't carry that: 12/10 slots" in lenient.out


def test_fatigue_occupies_slots_and_fills_them(cli: Cli) -> None:
    setup(cli)
    cli("inv", "add", "freya", "Longsword", "Chainmail", "Rope", "Spikes", "Chalk", "Pole")
    cli("inv", "add", "freya", "Rations")
    filled = cli("set", "freya", "fatigue+=1")
    assert "note: inventory is full (10/10): hp = 0" in filled.out
    shown = cli("inv", "show", "freya").out
    assert "10/10 slots" in shown and "- also taken: 1 slot (fatigue)" in shown


def test_uses_stacks_and_recharge(cli: Cli) -> None:
    setup(cli)
    cli("inv", "add", "freya", "Torch", "--count", "2")  # the compendium torch: 3 uses
    assert items(cli, "freya") == [
        {"name": "Torch", "uses": {"value": 3, "max": 3}, "entry": "mini-system.torch", "count": 2}
    ]
    assert "note: Torch: 2 uses left" in cli("inv", "use", "freya", "torch").out
    assert (
        "note: one Torch is used up; 1 left"
        in cli("inv", "use", "freya", "torch", "--spend", "2").out
    )
    assert "- Torch (1 slot): uses 3/3" in cli("inv", "show", "freya").out
    too_many = cli("inv", "use", "freya", "torch", "--spend", "4")
    assert too_many.code == 1 and "Torch has 3 uses left" in too_many.err
    cli("inv", "use", "freya", "torch", "--spend", "3")
    assert items(cli, "freya") == []  # used up and gone
    cli("inv", "add", "freya", "Wand", "--uses", "2", "--data", '{"recharge": "at dawn"}')
    spent = cli("inv", "use", "freya", "wand", "--spend", "2")
    assert "note: Wand is spent until it recharges" in spent.out
    assert "- Wand (1 slot): recharge at dawn, uses 0/2" in cli("inv", "show", "freya").out
    assert "Wand: 0 → 2 uses" in cli("inv", "recharge", "freya", "wand").out
    rope = cli("inv", "add", "freya", "Rope")
    assert rope.code == 0
    no_uses = cli("inv", "use", "freya", "rope")
    assert no_uses.code == 1 and "inv recharge pc:freya 'Rope' --to 3" in no_uses.err


def test_usage_die_is_rolled_logged_and_steps_down(cli: Cli) -> None:
    setup(cli)
    cli("inv", "add", "freya", "Lantern", "--uses", "d6")
    held = cli("inv", "use", "freya", "lantern", "--got", "5")
    assert held.code == 0 and "note: Lantern: usage die holds at d6 (rolled 5)" in held.out
    assert "usage die: Lantern" in held.out  # the roll line, logged
    down = cli("inv", "use", "freya", "lantern", "--got", "2")
    assert "note: Lantern: usage die steps down to d4 (rolled 2)" in down.out
    gone = cli("inv", "use", "freya", "lantern", "--got", "1")
    assert "note: Lantern is used up and gone" in gone.out
    assert "— usage die: Lantern" in cli("rolls").out


def test_drop_move_and_groups(cli: Cli) -> None:
    setup(cli)
    cli("inv", "add", "freya", "Rope", "Torch", "--count", "2")
    dropped = cli("inv", "drop", "freya", "rope", "--count", "1")
    assert dropped.code == 0 and "Freya drops Rope ×1" in dropped.out
    assert cli("inv", "drop", "freya", "rope", "--count", "5").code == 1
    moved = cli("inv", "move", "freya", "torch", "ansel", "--count", "1")
    assert moved.code == 0 and "Freya gives Torch to Ansel (1/10 slots)" in moved.out
    assert "- Torch (1 slot): uses 3/3" in cli("inv", "show", "ansel").out
    assert "- Torch (1 slot)" in cli("inv", "show", "freya").out  # one left
    nowhere = cli("inv", "move", "freya", "torch", "backpack")
    assert nowhere.code == 1 and "neither a record nor a slot group" in nowhere.err
    cli("new", "mule", "Bessie", "--set", "hp=5")
    cli("inv", "add", "bessie", "Tent", "--size", "bulky", "--count", "2")
    shown = cli("inv", "show", "bessie").out
    assert "Bessie · packs: 4/8 slots · left 4/4 · right 0/4" in shown and "right: empty" in shown
    cli("inv", "add", "bessie", "Feed")  # the left side is full: it goes right
    assert "right 1/4" in cli("inv", "show", "bessie").out
    full_side = cli("inv", "move", "bessie", "feed", "left")
    assert full_side.code == 1 and "left 5/4" in full_side.err
    assert "Bessie: Feed → right" in cli("inv", "move", "bessie", "feed", "right").out
    values = json.loads(cli("show", "bessie", "--format", "json").out)["values"]
    assert values["packs.left.used"] == 4 and values["packs.right.free"] == 3  # each side's room


def test_records_without_slots_keep_a_plain_list(cli: Cli) -> None:
    setup(cli)
    cli("new", "loc", "Bridge")
    assert cli("inv", "move", "freya", "rope", "bridge").code == 1  # she has no rope
    cli("inv", "add", "freya", "Rope")
    left = cli("inv", "move", "freya", "rope", "bridge")
    assert left.code == 0 and "Freya leaves Rope at Bridge" in left.out
    assert "- Rope (1 slot)" in cli("inv", "show", "bridge").out
    assert "inventory" in cli("show", "loc:bridge", "--format", "json").out


def test_inventory_changes_undo(cli: Cli) -> None:
    setup(cli)
    cli("inv", "add", "freya", "Longsword", "Chainmail", "Rope", "Spikes", "Chalk", "Pole")
    cli("inv", "add", "freya", "Rations", "Lamp")  # full: hp → 0
    assert "hp 0/4" in cli("show", "freya").out
    assert cli("undo").code == 0
    shown = cli("show", "freya").out
    assert "hp 4/4" in shown and "Lamp" not in shown


def test_rules_read_a_groups_columns(
    cli: Cli, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack = tmp_path / "extra" / "weigh"
    (pack / "rules").mkdir(parents=True)
    (pack / "pack.yaml").write_text("id: weigh\nname: W\nkind: supplement\nversion: 0.1.0\n")
    (pack / "rules" / "w.yaml").write_text(
        "action: weigh\nparams: {who: ref}\nsteps: ['left {sum(@who.packs.left.count)}, "
        "right {sum(@who.packs.right.count)}, all {sum(@who.packs.count)}']\n"
    )
    monkeypatch.setenv("DIDACT_PACK_PATH", os.pathsep.join([str(FIXTURE_PACKS), str(pack.parent)]))
    setup(cli)
    cli("pack", "enable", "weigh")
    cli("new", "mule", "Bessie", "--set", "hp=5")
    cli("inv", "add", "bessie", "Tent", "--size", "bulky", "--count", "2")
    weighed = cli("do", "weigh", "who=bessie")
    assert "left 2, right 0, all 2" in weighed.out  # a column no item has in a group: none
