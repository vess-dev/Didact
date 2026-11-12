"""`didact reset`: the library emptied, as if newly installed, with numbering starting again;
backed up first, backups and installed packs kept (unless asked), and the way back is the
safety backup. And the Library page's button for it."""

import json
from pathlib import Path
from typing import Any

from tests.conftest import Cli
from tests.test_web import Browser, web  # noqa: F401  (the fixture)


def _json(cli: Cli, *argv: str) -> Any:
    return json.loads(cli(*argv, "--format", "json").out)


def _play(cli: Cli) -> None:
    for argv in (
        ("world", "new", "vale", "--system", "mini-system"),
        ("campaign", "new", "run"),
        ("new", "npc", "Tom"),
        ("roll", "d6"),
        ("roll", "d6"),
        ("session", "start"),
        ("log", "note", "Tom lied"),
        ("save", "before the ford"),
        ("history", "--clear", "--yes"),  # a history clear's marker and numbers go too
    ):
        assert cli(*argv).code == 0, argv


def test_the_preview_changes_nothing(cli: Cli, home: Path) -> None:
    _play(cli)
    before = (home / "log" / "events.jsonl").read_bytes()
    shown = cli("reset")
    assert "Resetting would empty the library" in shown.out and "#e1" in shown.out
    assert "didact reset --yes" in shown.out
    assert (home / "log" / "events.jsonl").read_bytes() == before
    assert "vale" in cli("world", "list").out


def test_a_reset_empties_the_library_and_numbering_starts_again(cli: Cli, home: Path) -> None:
    _play(cli)
    cli("snapshot")
    done = _json(cli, "reset", "--yes")
    assert done["reset"] is True and done["before"]["worlds"] == ["vale"]
    assert "no worlds yet" in cli("world", "list").out
    assert cli("history").out.startswith("no changes yet")
    assert _json(cli, "find", "tom")["results"] == []  # the search index went too
    assert not (home / ".staging").exists() and not (home / ".restore").exists()
    made = _json(cli, "world", "new", "isles", "--system", "mini-system")
    assert made["event"] == 1  # the next change is #e1
    assert cli("roll", "d6").out.startswith("#r1 ")  # and the next roll #r1
    kinds = [s["kind"] for s in _json(cli, "snapshot", "--list")["snapshots"]]
    assert kinds == ["manual", "before-reset"]  # the backups stay, the safety one with them


def test_the_safety_backup_brings_it_all_back(cli: Cli, home: Path) -> None:
    _play(cli)
    safety = _json(cli, "reset", "--yes")["safety"]["name"]
    assert cli("snapshot", "--restore", safety, "--yes").code == 0
    assert "vale" in cli("world", "list").out and cli("show", "tom").code == 0
    assert "history cleared" in cli("history").out  # the history as it was, marker and all


def test_installed_packs_stay_unless_asked(cli: Cli, lucky: Path, tmp_path: Path) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    assert cli("pack", "export", "lucky", "--to", str(tmp_path)).code == 0
    assert cli("pack", "install", str(tmp_path / "lucky-0.1.0.didactpack")).code == 0
    assert "1 installed pack" in cli("reset").out
    cli("reset", "--yes")
    installed = {p["id"]: p["installed"] for p in _json(cli, "pack", "list")["packs"]}
    assert installed["lucky"] == ["0.1.0"]
    assert "the installed packs go too: lucky" in cli("reset", "--packs").out
    assert _json(cli, "reset", "--packs", "--yes")["packs_removed"] == ["lucky"]
    installed = {p["id"]: p["installed"] for p in _json(cli, "pack", "list")["packs"]}
    assert installed["lucky"] == []


def test_the_library_page_resets_it(web: Browser, cli: Cli) -> None:  # noqa: F811
    assert 'href="/library/reset"' in web.get("/library").body
    asked = web.get("/library/reset").body
    assert "Reset the library?" in asked and "numbering starts again" in asked
    done = web.run("reset", "--yes", next_="/")
    assert "reset the library" in done.body
    assert "no worlds yet" in cli("world", "list").out


def test_a_reset_keeps_the_demo_librarys_mark(cli: Cli, home: Path) -> None:
    """`serve --demo` rebuilds only a folder carrying its mark: resetting the demo from its own
    Reset page mustn't make it refuse to start next time."""
    cli("world", "new", "vale", "--system", "mini-system")
    (home / ".didact-demo").write_text("demo\n", encoding="utf-8")
    assert cli("reset", "--yes").code == 0
    assert (home / ".didact-demo").is_file()
