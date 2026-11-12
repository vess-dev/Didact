"""The packs that ship with Didact: core is part of it, the others are `.didactpack` files in
`packs/`, installed on request (by id, from the Library page) and uninstalled like any other."""

import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any

import pytest

from didact.packs.build import file_hashes
from didact.packs.share import CATALOG, INDEX, shipped
from tests.conftest import PACKS, Cli
from tests.test_web import Browser, web  # noqa: F401  (the fixture)


def _json(cli: Cli, *argv: str) -> Any:
    return json.loads(cli(*argv, "--format", "json").out)


def _published() -> set[str]:
    """The pack folders .gitignore publishes."""
    text = (PACKS.parent / ".gitignore").read_text(encoding="utf-8")
    return set(re.findall(r"^!/packs/([^/*]+)/$", text, re.MULTILINE))


def test_every_published_pack_ships_as_a_current_didactpack() -> None:
    ready = {s.id: s for s in shipped()}
    assert set(ready) == _published() - {"core"}, "run `make packs`"
    for pack_id, pack in ready.items():
        with zipfile.ZipFile(pack.path) as archive:
            files = json.loads(archive.read(INDEX))["files"]
        files.pop("ATTRIBUTION.md", None)  # added by the export
        assert files == file_hashes(PACKS / pack_id), f"{pack_id} changed: run `make packs`"
        assert pack.path.name == f"{pack_id}-{pack.version}.didactpack"
    catalog = json.loads((PACKS / CATALOG).read_text(encoding="utf-8"))["packs"]
    assert {(c["id"], c["version"], c["file"]) for c in catalog} == {
        (s.id, s.version, s.path.name) for s in ready.values()
    }, "run `make packs`"
    for entry in catalog:
        digest = hashlib.sha256((PACKS / entry["file"]).read_bytes()).hexdigest()
        assert entry["sha256"] == digest, "run `make packs`"


def test_a_fresh_library_has_core_and_offers_the_rest(cli: Cli) -> None:
    packs = {p["id"]: p for p in _json(cli, "pack", "list")["packs"]}
    assert packs["core"]["origin"] == "bundled"
    for pack_id in _published() - {"core"}:
        assert packs[pack_id]["origin"] == "shipped" and packs[pack_id]["installed"] == []
    listing = cli("pack", "list").out
    assert "[ships with Didact, install: `didact pack install grimwild-ce`]" in listing
    refused = cli("pack", "uninstall", "core", "--yes")
    assert refused.code != 0


def test_installing_by_id_brings_what_it_needs(cli: Cli, home: Path) -> None:
    done = cli("pack", "install", "cairn-2e-vald")
    assert done.code == 0, done.err
    assert "also installed cairn-2e 1.0.0, which it needs" in done.out
    packs = {p["id"]: p for p in _json(cli, "pack", "list")["packs"]}
    assert (
        packs["cairn-2e"]["installed"] == ["1.0.0"] and packs["cairn-2e"]["origin"] == "installed"
    )
    assert cli("world", "new", "vale", "--system", "cairn-2e").code == 0
    assert cli("pack", "enable", "cairn-2e-vald").code == 0
    assert cli("pack", "disable", "cairn-2e-vald").code == 0
    assert cli("pack", "uninstall", "cairn-2e-vald", "--yes").code == 0
    again = {p["id"]: p for p in _json(cli, "pack", "list")["packs"]}
    assert again["cairn-2e-vald"]["origin"] == "shipped"  # ready to install again


def test_a_world_on_a_system_not_installed_says_how_to_install_it(cli: Cli) -> None:
    made = cli("world", "new", "wild", "--system", "grimwild-ce")
    assert "`didact pack install grimwild-ce`" in made.out + made.err


def test_the_library_page_installs_a_shipped_pack(web: Browser, cli: Cli) -> None:  # noqa: F811
    page = web.get("/library").body
    assert "ships with Didact" in page
    assert "grimwild-ce" in page and 'value="install"' in page
    web.run("pack", "install", "grimwild-ce", next_="/library")
    packs = {p["id"]: p for p in _json(cli, "pack", "list")["packs"]}
    assert packs["grimwild-ce"]["installed"] == ["1.0.0"]


def test_the_sample_installs_a_system_that_ships_when_none_is_installed(cli: Cli) -> None:
    built = _json(cli, "sample")
    assert built["system"] == "cairn-2e" and not built["skipped"]
    packs = {p["id"]: p for p in _json(cli, "pack", "list")["packs"]}
    assert packs["cairn-2e"]["installed"] == ["1.0.0"]


def test_an_older_installed_copy_is_offered_the_shipped_version(cli: Cli, tmp_path: Path) -> None:
    older = tmp_path / "grimwild-ce"
    shutil.copytree(PACKS / "grimwild-ce", older)
    manifest = older / "pack.yaml"
    manifest.write_text(manifest.read_text().replace("version: 1.0.0", "version: 0.9.0"))
    assert cli("pack", "install", str(older)).code == 0
    listed = next(p for p in _json(cli, "pack", "list")["packs"] if p["id"] == "grimwild-ce")
    assert listed["update"] == "1.0.0"
    assert "- grimwild-ce: 0.9.0 → 1.0.0 (from Didact's packs folder)" in cli("pack", "update").out
    assert "✔ installed grimwild-ce 1.0.0" in cli("pack", "update", "--yes").out


def test_an_installed_copy_finds_what_ships_inside_the_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from didact.packs import library

    package = tmp_path / "site-packages" / "didact"
    (package / "shipped" / "core").mkdir(parents=True)
    monkeypatch.setattr(library, "__file__", str(package / "packs" / "library.py"))
    assert library.bundled_dir() == (package / "shipped").resolve()
    (package / "shipped" / "core").rmdir()
    (package / "shipped").rmdir()
    assert library.bundled_dir() is None


def test_doctor_fails_without_the_core_pack(cli: Cli, monkeypatch: pytest.MonkeyPatch) -> None:
    from didact.packs import library

    monkeypatch.setattr(library, "bundled_dir", lambda: None)
    result = cli("doctor")
    assert result.code == 1 and "core pack: not found" in result.out
