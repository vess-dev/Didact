"""Pack updates: `pack update` finds newer versions of the installed packs in an index of
`.didactpack` files (GitHub's, or `$DIDACT_PACK_UPDATES`) and installs them beside the old
ones; the Library page does the same."""

import functools
import http.server
import json
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from didact.packs.share import CATALOG, write_catalog
from tests.conftest import Cli
from tests.test_web import Browser, web  # noqa: F401  (the fixture)


def _json(cli: Cli, *argv: str) -> Any:
    return json.loads(cli(*argv, "--format", "json").out)


@pytest.fixture
def served(cli: Cli, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """`fens` 0.1.0 installed, and 0.2.0 on a web server that updates are looked for on."""
    folder = tmp_path / "fens"
    assert cli("pack", "new", "fens", "--kind", "supplement", "--dir", str(folder)).code == 0
    assert cli("pack", "install", str(folder)).code == 0
    manifest = folder / "pack.yaml"
    manifest.write_text(manifest.read_text().replace("version: 0.1.0", "version: 0.2.0"))
    shelf = tmp_path / "site" / "packs"  # served as /packs/, as on GitHub
    shelf.mkdir(parents=True)
    assert cli("pack", "export", str(folder), "--to", str(shelf)).code == 0
    write_catalog(shelf)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(shelf.parent))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("DIDACT_PACK_UPDATES", f"http://127.0.0.1:{server.server_port}/packs")
    try:
        yield shelf
    finally:
        server.shutdown()


def test_an_update_is_shown_then_installed_beside_the_old_version(cli: Cli, served: Path) -> None:
    shown = cli("pack", "update")
    assert "1 update:" in shown.out and "- fens: 0.1.0 → 0.2.0 (from http://127.0.0.1" in shown.out
    fens = next(p for p in _json(cli, "pack", "list")["packs"] if p["id"] == "fens")
    assert fens["installed"] == ["0.1.0"]  # nothing yet
    done = cli("pack", "update", "--yes")
    assert "✔ installed fens 0.2.0" in done.out and "didact campaign upgrade" in done.out
    fens = next(p for p in _json(cli, "pack", "list")["packs"] if p["id"] == "fens")
    assert sorted(fens["installed"]) == ["0.1.0", "0.2.0"]  # campaigns keep their pins
    assert "the installed packs are up to date" in cli("pack", "update").out


def test_a_download_that_doesnt_match_its_index_is_refused(cli: Cli, served: Path) -> None:
    catalog = json.loads((served / CATALOG).read_text())
    catalog["packs"][0]["sha256"] = "0" * 64
    (served / CATALOG).write_text(json.dumps(catalog))
    refused = cli("pack", "update", "--yes")
    assert refused.code != 0 and "doesn't match the hash its index gives" in refused.err


def test_an_unreachable_index_is_a_note(cli: Cli, tmp_path: Path, monkeypatch: Any) -> None:
    folder = tmp_path / "fens"
    cli("pack", "new", "fens", "--kind", "supplement", "--dir", str(folder))
    cli("pack", "install", str(folder))
    monkeypatch.setenv("DIDACT_PACK_UPDATES", "http://127.0.0.1:9/")  # nothing listens there
    shown = cli("pack", "update")
    assert shown.code == 0 and "up to date" in shown.out and "note: couldn't check" in shown.out


def test_the_library_page_checks_and_installs_updates(web: Browser, cli: Cli, served: Path) -> None:  # noqa: F811
    assert 'href="/library/updates"' in web.get("/library").body
    asked = web.get("/library/updates").body
    assert "fens: 0.1.0 → 0.2.0" in asked and "Install the updates" in asked
    web.run("pack", "update", "--yes", next_="/library#packs")
    fens = next(p for p in _json(cli, "pack", "list")["packs"] if p["id"] == "fens")
    assert sorted(fens["installed"]) == ["0.1.0", "0.2.0"]
