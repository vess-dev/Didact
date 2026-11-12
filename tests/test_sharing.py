"""Sharing packs: export, install, trust, tamper checks, licenses, campaign pins."""

import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from tests.conftest import FIXTURE_PACKS, Cli


@pytest.fixture
def exported(cli: Cli, tmp_path: Path, lucky: Path) -> Path:
    """The `lucky` pack (with its dice plugin) exported to an archive."""
    out = cli("pack", "export", "lucky", "--to", str(tmp_path))
    assert out.code == 0 and "✔ exported lucky" in out.out
    return tmp_path / "lucky-0.1.0.didactpack"


def test_export_writes_a_hashed_archive(exported: Path) -> None:
    archive = exported
    with zipfile.ZipFile(archive) as opened:
        index = json.loads(opened.read("didactpack.json"))
        assert index["id"] == "lucky" and "plugins/lucky.py" in index["files"]
        assert set(opened.namelist()) >= {"pack.yaml", "GUIDE.md", "dice.yaml", "plugins/lucky.py"}


def test_install_into_a_fresh_library_keeps_plugins_off_until_trusted(
    cli: Cli, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exported: Path
) -> None:
    archive = exported
    monkeypatch.delenv("DIDACT_PACK_PATH")  # a library that has never seen the fixtures
    fresh = str(tmp_path / "friend")
    installed = cli("pack", "install", str(archive), "--home", fresh)
    assert installed.code == 0 and "off until you trust them" in installed.out
    for args in (("world", "new", "vale"), ("campaign", "new", "run"), ("pack", "enable", "lucky")):
        assert cli(*args, "--home", fresh).code == 0
    assert cli("roll", "3d6~", "--home", fresh).code == 1  # the plugin is off
    shown = cli("pack", "trust", "lucky", "--home", fresh)
    assert '@modifier("charm", token="~")' in shown.out and "--yes" in shown.out
    assert cli("pack", "trust", "lucky", "--yes", "--home", fresh).code == 0
    assert cli("roll", "3d6~", "--home", fresh).code == 0
    plugin = Path(fresh) / "packs/lucky/0.1.0/plugins/lucky.py"
    plugin.write_text(plugin.read_text() + "\n# changed\n", encoding="utf-8")
    assert cli("roll", "3d6~", "--home", fresh).code == 1  # changed code revokes trust
    again = cli("pack", "install", str(archive), "--home", fresh)
    assert again.code == 1 and "already installed" in again.err


def test_tampered_archives_are_refused(cli: Cli, tmp_path: Path, exported: Path) -> None:
    archive = exported
    tampered = tmp_path / "tampered.didactpack"
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(tampered, "w") as target:
        for name in source.namelist():
            data = source.read(name)
            target.writestr(name, data + b"\nevil()\n" if name == "plugins/lucky.py" else data)
    result = cli("pack", "install", str(tampered), "--home", str(tmp_path / "other"))
    assert result.code == 1 and "plugins/lucky.py doesn't match its hash" in result.err
    junk = tmp_path / "junk.didactpack"
    junk.write_text("not a zip")
    assert "isn't a .didactpack" in cli("pack", "install", str(junk)).err


def test_personal_use_packs_are_not_exported(cli: Cli, tmp_path: Path) -> None:
    pack = tmp_path / "private"
    pack.mkdir()
    (pack / "pack.yaml").write_text(
        "id: private\nname: P\nkind: oracle\nversion: 0.1.0\nlicense: {redistributable: false}\n"
    )
    result = cli("pack", "export", str(pack), "--to", str(tmp_path))
    assert result.code == 1 and "personal use only" in result.err


def test_campaigns_pin_pack_versions(cli: Cli, home: Path) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    campaign = home / "worlds/vale/campaigns/run/campaign.yaml"
    text = campaign.read_text()
    assert "pins:" in text and "mini-system:" in text and "version: 0.1.0" in text
    campaign.write_text(text.replace("version: 0.1.0", "version: 0.0.9", 1), encoding="utf-8")
    broken = cli("table", "roll", "weather")
    assert broken.code == 1 and "campaign upgrade" in broken.err
    upgraded = cli("campaign", "upgrade")
    assert upgraded.code == 0 and "0.0.9 → 0.1.0" in upgraded.out
    assert cli("table", "roll", "weather").code == 0


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_install_from_git(cli: Cli, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    shutil.copytree(FIXTURE_PACKS / "pbta-lite", repo)

    def run(*args: str) -> None:
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

    run("init", "-q")
    run("-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    run("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "pack")
    run("tag", "v0.1.0")
    monkeypatch.delenv("DIDACT_PACK_PATH")
    result = cli("pack", "install", f"git+file://{repo}@v0.1.0", "--home", str(tmp_path / "lib"))
    assert result.code == 0 and "installed pbta-lite 0.1.0" in result.out
    assert not (tmp_path / "lib/packs/pbta-lite/0.1.0/.git").exists()


def test_a_round_trip_between_two_libraries_over_https(
    cli: Cli, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import functools
    import http.server
    import threading

    author = str(tmp_path / "author")
    folder = tmp_path / "fens"  # the pack's own folder
    assert (
        cli(
            "pack", "new", "fens", "--kind", "supplement", "--dir", str(folder), "--home", author
        ).code
        == 0
    )
    table = {"table": "fog", "dice": "d4", "entries": {"1-2": "Thin", "3": "Thick", "4": "Choking"}}
    assert (
        cli(
            "pack",
            "add",
            str(folder),
            "table",
            "--data",
            json.dumps(table),
            "--home",
            author,
        ).code
        == 0
    )
    served = tmp_path / "served"
    served.mkdir()
    assert cli("pack", "export", str(folder), "--to", str(served), "--home", author).code == 0
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(served))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        monkeypatch.delenv("DIDACT_PACK_PATH")
        friend = str(tmp_path / "friend")
        url = f"http://127.0.0.1:{server.server_port}/fens-0.1.0.didactpack"
        installed = cli("pack", "install", url, "--home", friend)
        assert installed.code == 0, installed.err
    finally:
        server.shutdown()
    for args in (("world", "new", "moor"), ("pack", "enable", "fens")):
        assert cli(*args, "--home", friend).code == 0
    rolled = cli("table", "roll", "fog", "--home", friend)
    assert rolled.code == 0 and any(w in rolled.out for w in ("Thin", "Thick", "Choking"))
