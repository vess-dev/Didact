"""Housekeeping: removing save points (undoable) and pruning backups (for good, and only
`snapshot-*.zip` files in the backups folder)."""

import json
from pathlib import Path

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "pc", "Wren", "--set", "hp=4")


def test_remove_a_save_point_and_undo_it(cli: Cli) -> None:
    setup(cli)
    cli("save", "before the dragon")
    cli("save", "after the dragon")
    removed = cli("save", "--remove", "Before  the Dragon")  # case and spaces don't matter
    assert removed.code == 0 and "removed save point 'before the dragon' (#e" in removed.out
    saves = cli("saves").out
    assert "before the dragon" not in saves and "after the dragon" in saves
    assert "remove save point: before the dragon" in cli("history").out
    assert cli("undo").code == 0
    assert "before the dragon" in cli("saves").out
    assert cli("rewind", "before the dragon", "--dry-run").code == 0
    dry = cli("save", "--remove", "after the dragon", "--dry-run")
    assert dry.code == 0 and dry.out.startswith("dry run:")
    assert "after the dragon" in cli("saves").out


def test_removing_a_save_point_that_isnt_there_lists_them(cli: Cli) -> None:
    setup(cli)
    missing = cli("save", "--remove", "nope")
    assert missing.code == 1 and "no save point 'nope'" in missing.err
    assert "none here" in missing.err
    cli("save", "camp")
    cli("save", "cave")
    missing = cli("save", "--remove", "nope")
    assert missing.code == 1 and "save points: 'camp', 'cave'" in missing.err
    both = cli("save", "camp", "--remove", "cave")
    assert both.code == 2 and "not both" in both.err


def backups(home: Path, *names: str) -> Path:
    folder = home / "backups"
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        (folder / name).write_bytes(b"PK")
    return folder


def test_keep_the_newest_backups(cli: Cli, home: Path) -> None:
    setup(cli)
    made = Path(json.loads(cli("snapshot", "--format", "json").out)["snapshot"])
    folder = backups(
        home,
        "snapshot-20200101-000000.zip",
        "snapshot-20200102-000000.zip",
        "snapshot-20200102-000000-2.zip",  # the same second, made after the one above
        "snapshot-20200103-000000.zip",
        "notes.txt",
        "other.zip",
    )
    (folder / "snapshot-folder.zip").mkdir()
    listed = cli("snapshot", "--list").out.splitlines()
    assert listed[0].startswith("- snapshot-20200101-000000.zip")
    assert listed[-1].startswith(f"- {made.name}")  # oldest first
    kept = cli("snapshot", "--keep", "3")
    assert kept.code == 0 and "✔ deleted 2 backups" in kept.out and "can't be undone" in kept.out
    left = {p.name for p in folder.iterdir()}
    assert left == {
        "snapshot-20200102-000000-2.zip",
        "snapshot-20200103-000000.zip",
        made.name,
        "notes.txt",
        "other.zip",
        "snapshot-folder.zip",
    }
    assert "nothing to delete: 3 backups" in cli("snapshot", "--keep", "3").out
    assert cli("snapshot", "--keep", "-1").code == 1
    everything = cli("snapshot", "--keep", "0")
    assert everything.code == 0 and "no backups left" in everything.out
    assert {p.name for p in folder.iterdir()} == {"notes.txt", "other.zip", "snapshot-folder.zip"}


def test_remove_one_backup(cli: Cli, home: Path) -> None:
    setup(cli)
    folder = backups(home, "snapshot-20200101-000000.zip", "snapshot-20200102-000000.zip")
    removed = cli("snapshot", "--remove", "snapshot-20200101-000000")  # `.zip` is optional
    assert removed.code == 0 and "✔ deleted backup snapshot-20200101-000000.zip" in removed.out
    assert "can't be undone" in removed.out
    assert not (folder / "snapshot-20200101-000000.zip").exists()
    by_path = cli("snapshot", "--remove", str(folder / "snapshot-20200102-000000.zip"))
    assert by_path.code == 0 and not any(folder.iterdir())
    backups(home, "snapshot-20200103-000000.zip", "notes.txt")
    missing = cli("snapshot", "--remove", "notes.txt")  # only backups are ever deleted
    assert missing.code == 1 and "newest first: snapshot-20200103-000000.zip" in missing.err
    outside = cli("snapshot", "--remove", str(home / "log" / "events.jsonl"))
    assert outside.code == 1 and (home / "log" / "events.jsonl").is_file()
    assert (folder / "notes.txt").is_file()
    both = cli("snapshot", "--list", "--keep", "1")
    assert both.code == 2 and "pick one of" in both.err
