"""One game system at a time: the open world's, which it keeps for good. A campaign plays its
world's system, and the packs added to either go with it. Campaigns open and close."""

import html
import json
import os
import re
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import FIXTURE_PACKS, Cli
from tests.test_web import Browser, web  # noqa: F401  (the fixture)


def _json(cli: Cli, *args: str) -> Any:  # parsed JSON, read freely in tests
    out = cli(*args, "--format", "json")
    assert out.code == 0, out.err
    return json.loads(out.out)


def _enabled(cli: Cli) -> set[str]:
    return {p["id"] for p in _json(cli, "pack", "list")["packs"] if p["enabled"]}


@pytest.fixture
def d20_setting(home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A setting written for d20-lite, on the pack path."""
    pack = tmp_path / "extra" / "d20-coast"
    (pack / "tables").mkdir(parents=True)
    (pack / "pack.yaml").write_text(
        "id: d20-coast\nname: The Coast\nkind: setting\nversion: 0.1.0\n"
        "requires: {packs: [core, d20-lite]}\n"
    )
    (pack / "tables" / "tides.yaml").write_text(
        "table: tides\ndice: d2\nentries: {1: Low, 2: High}\n"
    )
    monkeypatch.setenv("DIDACT_PACK_PATH", os.pathsep.join([str(FIXTURE_PACKS), str(pack.parent)]))
    return pack


def test_a_world_keeps_its_system(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    switched = cli("world", "set", "system=d20-lite")
    assert switched.code == 1 and "a world keeps the system it was made with" in switched.err
    assert (
        "a campaign plays its world's game system" in cli("campaign", "set", "system=d20-lite").err
    )
    refused = cli("pack", "enable", "d20-lite")
    assert refused.code == 1 and "world vale plays mini-system" in refused.err
    assert "`didact world new <id> --system d20-lite`" in refused.err  # where it can play
    assert (
        "--system" not in cli("help", "campaign", "new").out
    )  # a campaign has no system of its own
    assert cli("pack", "enable", "mini-system").out.startswith("mini-system is already")
    assert _enabled(cli) == {"core", "mini-system"}

    cli("world", "new", "moor", "--system", "d20-lite", "--no-use")
    hinted = cli("pack", "enable", "d20-lite").err
    assert "d20-lite plays in world moor: `didact world use moor`" in hinted
    assert cli("world", "use", "moor").code == 0
    assert _enabled(cli) == {"core", "d20-lite"}  # only the open world's


def test_a_world_without_a_system_takes_one_once(cli: Cli) -> None:
    cli("world", "new", "bare")
    cli("campaign", "new", "run")
    assert _enabled(cli) == {"core"}
    tied = cli("pack", "enable", "mini-system")
    assert tied.code == 0 and "world bare plays mini-system now, for good" in tied.out
    assert _json(cli, "world", "show")["system"] == "mini-system"
    assert _enabled(cli) == {"core", "mini-system"}
    assert cli("pack", "enable", "d20-lite").code == 1  # and never another
    assert "keeps the system it was made with" in cli("world", "set", "system=d20-lite").err
    assert cli("undo").code == 0 and _enabled(cli) == {"core"}  # undoable like any change
    assert cli("world", "set", "system=mini-system").code == 0  # the same choice, this way
    oracle = cli("world", "set", "system=oracle-lite", "--world", "bare")
    assert "keeps the system" in oracle.err  # it has one now


def test_a_pack_for_another_system_stays_out(cli: Cli, home: Path, d20_setting: Path) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    refused = cli("pack", "enable", "d20-coast")
    assert refused.code == 1
    assert "d20-coast needs d20-lite, but world vale plays mini-system" in refused.err
    world = home / "worlds" / "vale" / "world.yaml"  # written by hand, or before this rule
    world.write_text(world.read_text() + "packs: [d20-lite, d20-coast]\n")
    assert _enabled(cli) == {"core", "mini-system"}
    assert cli("table", "roll", "tides").code == 1  # the setting's tables aren't in play

    cli("world", "new", "coast", "--system", "d20-lite")
    cli("campaign", "new", "tale")
    assert cli("pack", "enable", "d20-coast").code == 0  # at home in its own system
    assert cli("table", "roll", "tides").code == 0


def test_a_world_taking_its_system_drops_what_cant_go_with_it(
    cli: Cli, home: Path, d20_setting: Path
) -> None:
    cli("world", "new", "bare")
    world = home / "worlds" / "bare" / "world.yaml"
    world.write_text(world.read_text() + "packs: [oracle-lite, d20-lite, d20-coast]\n")
    tied = cli("pack", "enable", "mini-system")
    assert "disabled d20-coast: it needs d20-lite" in tied.out
    assert "disabled d20-lite: another game system" in tied.out
    assert _json(cli, "world", "show")["system"] == "mini-system"
    assert "packs: [oracle-lite]" in world.read_text()  # the oracle stays


def test_campaigns_open_and_close(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("session", "start")
    closed = cli("campaign", "close")
    assert closed.code == 0 and "closed campaign run" in closed.out
    assert "its session is still under way" in closed.out
    assert "`didact campaign open run`" in closed.out
    status = _json(cli, "status")
    assert status["world"] == "vale" and status["campaign"] is None  # the world stays open
    assert cli("campaign", "close").out.startswith("no campaign is open")
    needs = cli("log", "note", "The ford floods")
    assert needs.code == 1 and "campaign open" in needs.err
    opened = cli("campaign", "open", "run")
    assert opened.code == 0 and "open campaign: run" in opened.out and "mini-system" in opened.out
    assert _json(cli, "brief")["session"] == 1  # where it was left


def test_the_app_opens_and_closes_campaigns_and_shows_the_system_in_use(
    web: Browser,  # noqa: F811
    cli: Cli,
) -> None:
    library = web.get("/library").body
    buttons = _buttons(library)
    assert ("campaign", "close") in buttons  # the open one can be closed
    assert "in use" in library
    assert ("pack", "enable", "d20-lite") not in buttons  # another system: a world of its own
    assert "/library?system=d20-lite#new-world" in library
    picked = web.get("/library?system=d20-lite").body
    assert '<option value="d20-lite" selected>' in picked
    assert "For good: a world keeps its system" in picked
    web.run("campaign", "close", next_="/")
    overview = web.get("/").body
    assert "Open a campaign" in html.unescape(overview)
    assert ("campaign", "open", "run") in _buttons(overview)
    web.run("campaign", "open", "run", next_="/")
    assert _json(cli, "status")["campaign"] == "run"


def _buttons(page: str) -> set[tuple[str, ...]]:
    """The command lines a page's one-button forms run."""
    forms = re.findall(r"<form\b.*?</form>", page, re.DOTALL)
    return {tuple(re.findall(r'name="w" value="([^"]*)"', form)) for form in forms}


def test_installing_a_pack_says_where_it_plays(cli: Cli, system_packs: Path) -> None:
    cli("world", "new", "wild", "--system", "grimwild-ce")
    assert (
        "grimwild-ce is already this world's game system"
        in cli("pack", "install", "grimwild-ce").out
    )
    other = cli("pack", "install", "cairn-2e").out
    assert "make a world for it: `didact world new <id> --system cairn-2e`" in other
    cli("world", "new", "bare")
    assert (
        "use it: `didact pack enable cairn-2e`" in cli("pack", "install", "cairn-2e", "--force").out
    )
