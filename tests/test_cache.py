"""The disposable caches: what's in them, clearing them, and never touching the library."""

import json
import os
from pathlib import Path

import pytest

from tests.conftest import Cli


def data(cli: Cli, *args: str) -> dict[str, object]:
    done = cli(*args, "--format", "json")
    assert done.code == 0, done.err
    found: dict[str, object] = json.loads(done.out)
    return found


def test_clearing_the_caches_keeps_the_library(
    cli: Cli, home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack = tmp_path / "extra" / "tiny"
    (pack / "tables").mkdir(parents=True)
    (pack / "pack.yaml").write_text("id: tiny\nname: Tiny\nkind: supplement\nversion: 0.1.0\n")
    (pack / "tables" / "t.yaml").write_text("table: t\ndice: d2\nentries: {1: a, 2: b}\n")
    paths = os.pathsep.join([os.environ["DIDACT_PACK_PATH"], str(tmp_path / "extra")])
    monkeypatch.setenv("DIDACT_PACK_PATH", paths)
    cli("world", "new", "vale", "--system", "mini-system")
    cli("new", "npc", "Sweeney", "--body", "Keeper of the old trail.")
    assert cli("pack", "build", str(pack)).code == 0
    shown = data(cli, "cache", "show")
    counts = {str(p["kind"]): p["count"] for p in shown["parts"]}  # type: ignore[attr-defined]
    assert counts["search indexes"] == 1 and counts["compiled packs"] >= 1 and shown["bytes"]
    preview = cli("cache", "clear", "--dry-run")
    assert "dry run: would delete" in preview.out
    cleared = data(cli, "cache", "clear")
    assert cleared["parts"] == counts and cleared["deleted"]
    assert list((pack / ".build").glob("*.json"))  # `pack build` output isn't a cache: it stays
    assert data(cli, "cache", "show")["bytes"] == 0
    assert (home / "worlds/vale/npc/sweeney.md").is_file()  # the library is untouched
    assert "npc:sweeney" in cli("find", "trail").out  # the index rebuilds by itself


def test_a_cache_folder_inside_the_library_is_refused(
    cli: Cli, home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cli("world", "new", "vale")
    monkeypatch.setenv("DIDACT_CACHE", str(home / "cache"))
    refused = cli("cache", "clear")
    assert refused.code == 1 and "overlaps the library" in refused.err
    assert (home / "worlds/vale/world.yaml").is_file()
