"""Records through the CLI: create, show, find, set, edit, note, link, rm, archive."""

import json
from pathlib import Path

import pytest

from tests.conftest import Cli


@pytest.fixture
def world(cli: Cli) -> Cli:
    assert cli("world", "new", "vale", "--name", "Vale").code == 0  # freeform: no system
    assert cli("campaign", "new", "withering", "--name", "The Withering").code == 0
    return cli


def test_create_show_and_default_scopes(world: Cli, home: Path) -> None:
    result = world(
        "new", "npc", "Sweeney", "--tag", "wood", "--set", "hp=6", "--body", "Forest champion."
    )
    assert result.code == 0 and "created npc:sweeney · Sweeney (world:vale)" in result.out
    assert (home / "worlds/vale/npc/sweeney.md").is_file()
    assert "pc:freya · Freya (campaign:withering)" in world("new", "pc", "Freya").out
    assert (home / "worlds/vale/campaigns/withering/pc/freya.md").is_file()
    shown = world("show", "sweeney").out
    assert shown.splitlines()[0] == "npc:sweeney · Sweeney (world:vale)"
    assert "hp: 6" in shown and "tags: wood" in shown and "Forest champion." in shown


def test_describe_it_json(world: Cli) -> None:
    payload = {
        "name": "Old Gannet",
        "hp": 4,
        "traits": ["one-eyed", "loyal"],
        "body": "Smuggles relics.",
    }
    result = world("new", "npc", "--data", json.dumps(payload))
    assert result.code == 0
    data = json.loads(world("show", "Old Gannet", "--format", "json").out)
    assert data["id"] == "npc:old-gannet"
    assert data["fields"] == {"hp": 4, "traits": ["one-eyed", "loyal"]}
    assert data["body"].strip() == "Smuggles relics."


def test_duplicate_ids_are_refused_with_a_hint(world: Cli) -> None:
    world("new", "npc", "Tom")
    result = world("new", "npc", "Tom")
    assert result.code == 1
    assert "already exists" in result.err and "--id" in result.err
    assert world("new", "npc", "Tom", "--id", "tom-the-guard").code == 0


def test_set_arithmetic_lists_and_unset(world: Cli) -> None:
    world("new", "pc", "Freya", "--set", "hp=4", "--set", "gold=5")
    assert world("set", "freya", "hp-=2", "gold+=10", "tags+=wounded", "mood=grim").code == 0
    data = json.loads(world("show", "pc:freya", "--format", "json").out)
    assert data["fields"] == {"hp": 2, "gold": 15, "mood": "grim"}
    assert data["tags"] == ["wounded"]
    world("set", "freya", "tags-=wounded", "--unset", "mood")
    data = json.loads(world("show", "pc:freya", "--format", "json").out)
    assert "tags" not in data and "mood" not in data["fields"]


def test_set_rejects_managed_keys(world: Cli) -> None:
    world("new", "npc", "Tom")
    result = world("set", "tom", "id=npc:x")
    assert result.code == 1 and "rename" in result.err


def test_find_search_and_list(world: Cli) -> None:
    world("new", "npc", "Sweeney", "--body", "The forest champion.")
    world("new", "loc", "Amber Grave", "--body", "A pool of bubbling sap.")
    hits = world("find", "sap").out
    assert "loc:amber-grave" in hits and "npc:sweeney" not in hits
    listing = world("find", "--type", "npc").out
    assert listing.startswith("1 record in") and "npc:sweeney" in listing


def test_unknown_names_suggest_matches(world: Cli) -> None:
    world("new", "npc", "Sweeney")
    result = world("show", "sweeny")
    assert result.code == 1
    assert "did you mean `npc:sweeney` (Sweeney)?" in result.err


def test_ambiguous_names_list_the_options(world: Cli) -> None:
    world("new", "npc", "Tom")
    world("new", "npc", "Tom", "--id", "tom-2")
    result = world("show", "Tom")
    assert result.code == 1 and "npc:tom" in result.err and "npc:tom-2" in result.err


def test_links_backlinks_and_protected_deletes(world: Cli) -> None:
    world("new", "npc", "Sweeney")
    world("new", "loc", "Cabin")
    assert world("link", "sweeney", "lives-at", "cabin").code == 0
    assert "referenced by: npc:sweeney (lives-at)" in world("show", "cabin").out
    blocked = world("rm", "cabin")
    assert blocked.code == 1 and "--unlink" in blocked.err
    staged = world("rm", "cabin", "--unlink")
    assert "staged as" in staged.out
    assert world("rm", "cabin", "--unlink", "--yes").code == 0
    assert "links" not in json.loads(world("show", "sweeney", "--format", "json").out)


def test_note_edit_archive_restore(world: Cli) -> None:
    world("new", "npc", "Tom", "--body", "A tall man.")
    world("note", "tom", "Owes the party a favor.")
    assert "## Notes\n- " in world("show", "tom", "--detail", "full").out
    world("edit", "tom", "--data", json.dumps({"hp": 3, "tags": ["smuggler"]}))
    data = json.loads(world("show", "tom", "--format", "json").out)
    assert data["fields"] == {"hp": 3} and data["tags"] == ["smuggler"]
    world("archive", "tom")
    assert "npc:tom" not in world("find", "--type", "npc").out
    assert "npc:tom" in world("find", "--type", "npc", "--archived").out
    world("restore", "tom")
    assert "npc:tom" in world("find", "--type", "npc").out


def test_dry_run_changes_nothing(world: Cli, home: Path) -> None:
    result = world("new", "npc", "Ghost", "--dry-run")
    assert result.out.startswith("dry run:") and "+ create worlds/vale/npc/ghost.md" in result.out
    assert not (home / "worlds/vale/npc/ghost.md").exists()


def test_scope_override_and_global_records(world: Cli, home: Path) -> None:
    assert world("new", "lore", "The Pale Folk", "--scope", "global").code == 0
    assert (home / "global/lore/the-pale-folk.md").is_file()
    assert "lore:the-pale-folk" in world("show", "The Pale Folk").out
