"""Administration: rename, replace, bulk set, merge, copy/move/promote, undo, history."""

import json
from pathlib import Path

import pytest

from tests.conftest import Cli


@pytest.fixture
def world(cli: Cli) -> Cli:
    cli("world", "new", "vale", "--name", "Vale")  # freeform: no system schema
    cli("campaign", "new", "withering")
    cli("new", "npc", "Sweeney", "--set", "hp=6", "--body", "Champion of the Wood of Vale.")
    cli("new", "loc", "Cabin", "--body", "A cabin in Vale.")
    cli("link", "sweeney", "lives-at", "cabin")
    cli("new", "npc", "Rival", "--body", "Hates npc:sweeney.")
    cli("link", "rival", "rival", "sweeney")
    return cli


def _snapshot(home: Path) -> dict[str, bytes]:
    return {
        p.relative_to(home).as_posix(): p.read_bytes()
        for p in sorted(home.rglob("*"))
        if p.is_file() and "log" not in p.parts and ".staging" not in p.parts and p.name != ".lock"
    }


def test_plain_rename_keeps_old_name_as_alias(world: Cli) -> None:
    assert world("rename", "sweeney", "Sweeney the Warden").code == 0
    data = json.loads(world("show", "npc:sweeney", "--format", "json").out)
    assert data["name"] == "Sweeney the Warden" and "Sweeney" in data["aliases"]
    assert world("show", "Sweeney").code == 0  # the old name still resolves


def test_reslug_rewrites_every_reference(world: Cli, home: Path) -> None:
    staged = world("rename", "sweeney", "Sweeney the Warden", "--reslug")
    assert "staged as" in staged.out and "npc:sweeney-the-warden" in staged.out
    assert world("rename", "sweeney", "Sweeney the Warden", "--reslug", "--yes").code == 0
    assert not (home / "worlds/vale/npc/sweeney.md").exists()
    rival = json.loads(world("show", "rival", "--format", "json").out)
    assert rival["links"] == [{"rel": "rival", "to": "npc:sweeney-the-warden"}]
    assert "Hates npc:sweeney-the-warden." in rival["body"]
    assert world("show", "npc:sweeney").out.startswith("npc:sweeney-the-warden")  # old id resolves


def test_rename_world_everywhere(world: Cli) -> None:
    result = world("rename", "world:vale", "Valemark", "--rewrite-text", "--yes")
    assert result.code == 0, result.err
    assert "Valemark" in world("world", "show").out
    assert "Champion of the Wood of Valemark." in world("show", "sweeney").out


def test_replace_previews_then_applies(world: Cli) -> None:
    preview = world("replace", "Vale", "Valemark", "--word")
    assert "staged as" in preview.out
    change_id = json.loads(world("staged", "--format", "json").out)["staged"][0]["id"]
    assert "Vale." in world("show", "cabin").out  # nothing changed yet
    assert world("apply", change_id).code == 0
    assert "A cabin in Valemark." in world("show", "cabin").out
    assert json.loads(world("staged", "--format", "json").out)["staged"] == []


def test_bulk_set_with_conditions(world: Cli) -> None:
    world("new", "npc", "Goblin A", "--tag", "goblin")
    world("new", "npc", "Goblin B", "--tag", "goblin")
    result = world(
        "bulk",
        "set",
        "disposition=hostile",
        "--where",
        "type=npc",
        "--where",
        "tag=goblin",
        "--yes",
    )
    assert result.code == 0 and "updated 2 of 2" in result.out
    assert json.loads(world("show", "Goblin A", "--format", "json").out)["fields"] == {
        "disposition": "hostile"
    }
    assert (
        "disposition" not in json.loads(world("show", "sweeney", "--format", "json").out)["fields"]
    )


def test_merge_folds_and_repoints(world: Cli, home: Path) -> None:
    world("new", "npc", "Sweeny", "--set", "mood=grumpy", "--body", "Seen near the cabin.")
    world("link", "cabin", "haunted-by", "sweeny")
    result = world("merge", "sweeny", "npc:sweeney", "--yes")
    assert result.code == 0, result.err
    merged = json.loads(world("show", "npc:sweeney", "--format", "json").out)
    assert {"Sweeny", "npc:sweeny"} <= set(merged["aliases"])
    assert merged["fields"] == {"hp": 6, "mood": "grumpy"}
    assert "## Merged from npc:sweeny" in merged["body"]
    cabin = json.loads(world("show", "cabin", "--format", "json").out)
    assert {"rel": "haunted-by", "to": "npc:sweeney"} in cabin["links"]
    assert not (home / "worlds/vale/npc/sweeny.md").exists()


def test_copy_move_promote(world: Cli, home: Path) -> None:
    world("world", "new", "coast", "--no-use")
    assert world("copy", "sweeney", "--to", "world:coast").code == 0
    assert (home / "worlds/coast/npc/sweeney.md").is_file()
    world("new", "npc", "Hermit", "--scope", "campaign:withering")
    assert world("promote", "hermit").code == 0
    assert (home / "worlds/vale/npc/hermit.md").is_file()
    assert world("move", "hermit", "--to", "global").code == 0
    assert (home / "global/npc/hermit.md").is_file()


def test_undo_restores_bytes_and_redo_reapplies(world: Cli, home: Path) -> None:
    before = _snapshot(home)
    world("rename", "sweeney", "Sweeney the Warden", "--reslug", "--yes")
    world("set", "rival", "hp=3")
    after = _snapshot(home)
    assert world("undo", "--steps", "2").code == 0
    assert _snapshot(home) == before
    assert world("redo").code == 0
    assert world("redo").code == 0
    assert _snapshot(home) == after


def test_undo_refuses_when_later_changes_touch_the_file(world: Cli) -> None:
    world("set", "sweeney", "hp=5")
    world("set", "sweeney", "hp=4")
    history = json.loads(world("history", "--format", "json").out)["events"]
    older = history[1]["seq"]
    result = world("undo", "--event", str(older))
    assert result.code == 1 and "--force" in result.err


def test_history_diff_and_audit(world: Cli) -> None:
    world("set", "sweeney", "hp=5", "--reason", "took a hit from the troll")
    history = world("history", "sweeney").out
    assert "set npc:sweeney: hp=5" in history and "took a hit from the troll" in history
    seq = json.loads(world("history", "--format", "json").out)["events"][0]["seq"]
    diff = world("diff", f"e{seq}").out
    assert "fields.hp: 6 → 5" in diff and "command: didact set sweeney hp=5" in diff
    assert "took a hit" in world("audit").out
