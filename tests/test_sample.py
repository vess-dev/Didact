"""The sample campaign (`didact sample`) and the web app's demo mode (`didact serve --demo`),
which serves it from a library of its own, rebuilt each time it starts."""

import json
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import Cli


def _json(cli: Cli, *argv: str) -> Any:
    return json.loads(cli(*argv, "--format", "json").out)


def test_the_sample_is_a_campaign_under_way(cli: Cli, home: Path) -> None:
    built = _json(cli, "sample", "--system", "mini-system")
    assert built["world"] == "vale" and built["campaign"] == "withering" and not built["skipped"]
    for ref in ("pc:freya", "npc:sweeney", "loc:my-house", "item:chest", "faction:raiders"):
        assert cli("show", ref).code == 0, ref
    assert "in Chest" in cli("where", "sword").out
    brief = cli("brief", "--gm").out
    assert "Stop the raid" in brief and "The raid 1/6" in brief and "Raider scouts" in brief
    assert "round 1" in cli("combat", "status").out
    assert "plan" not in _json(cli, "show", "sweeney")["details"]  # the GM's notes stay hidden
    assert "path → ?" in cli("map").out  # a secret place
    assert cli("undo").code == 0  # built with real commands: its history is real


def test_the_sample_needs_an_empty_library(cli: Cli) -> None:
    cli("world", "new", "isles", "--system", "mini-system")
    refused = cli("sample", "--system", "mini-system")
    assert refused.code != 0 and "already has worlds" in refused.err
    cli("world", "delete", "isles", "--yes")
    unknown = cli("sample", "--system", "no-such-system")
    assert unknown.code != 0 and "no game system" in unknown.err and "mini-system" in unknown.err


def test_serve_demo_serves_a_fresh_sample(
    cli: Cli, home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import didact.web
    from didact.cli import sample

    seen: dict[str, Any] = {}
    monkeypatch.setattr(didact.web, "serve", lambda **kwargs: seen.update(kwargs))
    monkeypatch.setattr(sample, "_system", lambda runner, wanted: "mini-system")
    assert cli("serve", "--demo").code == 0
    demo = Path(seen["home"])
    assert demo == tmp_path / "didact-demo" and demo != home  # beside the cache, not yours
    assert "vale" in cli("--home", str(demo), "world", "list").out
    listed = cli("--home", str(demo), "pack", "list").out
    assert "ships with Didact, install" not in listed  # every pack that ships is installed
    cli("--home", str(demo), "new", "npc", "Visitor")
    assert cli("serve", "--demo").code == 0  # rebuilt: what was done in it is gone
    assert cli("--home", str(demo), "show", "visitor").code != 0
    assert "no worlds yet" in cli("world", "list").out  # your own library is untouched
    assert cli("serve", "--demo", "--home", str(tmp_path / "x")).code != 0


def test_serve_demo_never_replaces_a_stranger(cli: Cli, tmp_path: Path) -> None:
    stranger = tmp_path / "didact-demo"
    stranger.mkdir()
    (stranger / "notes.txt").write_text("mine", encoding="utf-8")
    refused = cli("serve", "--demo")
    assert refused.code != 0 and "isn't Didact's demo library" in refused.err
    assert (stranger / "notes.txt").read_text(encoding="utf-8") == "mine"
