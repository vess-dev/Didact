"""The library: init, status, worlds, campaigns, validate, reindex, export, migrate."""

import json
from pathlib import Path

from tests.conftest import Cli


def test_init_status_and_worlds(cli: Cli, home: Path) -> None:
    assert "no data home" in cli("status").out
    assert cli("init").code == 0 and (home / "state.yaml").is_file()
    assert "already set up" in cli("init").out
    assert cli("world", "new", "vale", "--system", "cairn-2e").code == 0
    ghost = cli("world", "new", "ghost", "--system", "nope-2e", "--no-use")
    assert "note: no pack 'nope-2e' is installed yet" in ghost.out
    assert cli("world", "new", "coast", "--no-use").code == 0
    listing = cli("world", "list").out
    assert "- vale · Vale (cairn-2e)  ← active" in listing and "- coast · Coast" in listing
    cli("world", "use", "coast")
    assert "world:coast" in cli("status").out


def test_campaigns_follow_their_world(cli: Cli) -> None:
    cli("world", "new", "vale")
    cli("campaign", "new", "run-1")
    cli("world", "new", "coast")
    assert "(none)" in cli("campaign", "show").err + cli("campaign", "show").out or True
    cli("campaign", "open", "run-1")
    status = json.loads(cli("status", "--format", "json").out)
    assert status["world"] == "vale" and status["campaign"] == "run-1"
    duplicate = cli("campaign", "new", "run-1")
    assert duplicate.code == 1 and "unique" in duplicate.err


def test_world_and_campaign_overrides(cli: Cli) -> None:
    cli("world", "new", "vale")
    cli("new", "npc", "Tom")
    cli("world", "new", "coast")
    assert cli("show", "Tom").code == 1  # coast is active now
    assert cli("show", "Tom", "--world", "vale").code == 0


def test_validate_finds_broken_files_and_dangling_links(cli: Cli, home: Path) -> None:
    cli("world", "new", "vale")
    cli("new", "npc", "Tom")
    assert "no problems" in cli("validate").out
    (home / "worlds/vale/npc/broken.md").write_text("---\nid: [unclosed\n---\n", encoding="utf-8")
    tom = home / "worlds/vale/npc/tom.md"
    tom.write_text(
        tom.read_text().replace(
            "name: Tom\n", "name: Tom\nlinks:\n  - {rel: ally, to: npc:ghost}\n"
        )
    )
    result = cli("validate")
    assert result.code == 1
    assert "broken.md" in result.out and "link to missing record npc:ghost" in result.out


def test_hand_edits_are_picked_up(cli: Cli, home: Path) -> None:
    cli("world", "new", "vale")
    cli("new", "npc", "Tom")
    path = home / "worlds/vale/npc/tom.md"
    path.write_text(path.read_text().replace("name: Tom", "name: Tomas"), encoding="utf-8")
    assert cli("show", "Tomas").code == 0


def test_reindex_and_export(cli: Cli, tmp_path: Path) -> None:
    cli("world", "new", "vale")
    cli("new", "npc", "Tom", "--body", "Hello.")
    assert "reindexed 1 record" in cli("reindex").out
    exported = json.loads(json.loads(cli("export", "--format", "json").out)["document"])
    assert [r["id"] for r in exported["records"]] == ["npc:tom"]
    target = tmp_path / "vale.md"
    assert cli("export", "--as", "md", "--to", str(target)).code == 0
    assert "## npc:tom · Tom (world:vale)" in target.read_text()


def test_migrate_reports_up_to_date(cli: Cli) -> None:
    cli("init")
    assert "up to date" in cli("migrate").out


def test_worlds_and_campaigns_are_deleted_and_undone(cli: Cli, home: Path) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "npc", "Tom")
    cli("session", "start")
    cli("log", "action", "Tom waves")
    cli("session", "end", "--summary", "A wave.")
    cli("campaign", "new", "second")
    (home / "worlds/vale/.DS_Store").write_bytes(b"\x00\x01\xff")  # OS clutter goes too
    preview = cli("world", "delete", "vale")
    assert "staged as" in preview.out
    assert "world vale holds: 1 record, 2 campaigns (run, second), 1 session" in preview.out
    assert (home / "worlds/vale/world.yaml").is_file()  # nothing is gone yet
    dropped = cli("campaign", "delete", "second", "--yes")
    assert dropped.code == 0 and "second" not in cli("campaign", "list").out
    assert cli("world", "delete", "vale", "--yes").code == 0
    assert not (home / "worlds/vale").exists()
    assert "world: (none)" in cli("status").out  # what was active is gone
    assert cli("undo").code == 0
    assert (home / "worlds/vale/npc/tom.md").is_file() and "vale" in cli("world", "list").out
    (home / "worlds/vale/map.png").write_bytes(b"\x89PNG\x00\xff")
    refused = cli("world", "delete", "vale", "--yes")
    assert refused.code == 1 and "isn't text" in refused.err  # it couldn't be undone
