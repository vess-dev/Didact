"""The compendium: find, show, spawn, and homebrew entries in an overlay."""

import json
import re
from pathlib import Path

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")


def test_find_and_show(cli: Cli) -> None:
    setup(cli)
    everything = cli("compendium", "find").out
    assert re.match(r"\d+ entries:", everything) and "mini-system.troll · Troll" in everything
    assert cli("compendium", "find", "giant").out.startswith(
        "1 entry:\n- mini-system.troll · Troll (npc)"
    )
    assert "mini-system.longsword" in cli("compendium", "find", "--type", "item").out
    shown = cli("compendium", "show", "troll").out
    assert "tags: giant, bridge" in shown and "Regrows unless burned." in shown
    assert "nothing in the compendium matches" in cli("compendium", "find", "dragon").out


def test_spawn_routes_rolls_and_numbers(cli: Cli) -> None:
    setup(cli)
    assert cli("spawn", "troll").code == 0
    troll = json.loads(cli("show", "troll", "--gm", "--format", "json").out)  # bookkeeping
    assert troll["mechanics"]["mini-system"]["STR"] == {"value": 16, "max": 16}
    assert troll["extra"]["compendium"] == "mini-system.troll" and troll["tags"] == [
        "giant",
        "bridge",
    ]
    wolves = cli("spawn", "wolf", "--count", "2")
    assert (
        "spawned npc:wolf-1, npc:wolf-2" in wolves.out
        and wolves.out.count("note: rolled hp: 1d6+2") == 2
    )
    again = cli("spawn", "troll")
    assert "spawned npc:troll-2" in again.out
    assert cli("spawn", "troll", "--name", "Bridge Troll").out.startswith(
        "✔ spawned npc:bridge-troll"
    )


def test_homebrew_entries_live_in_the_library(cli: Cli, home: Path) -> None:
    setup(cli)
    added = cli(
        "compendium",
        "add",
        "--data",
        '{"name": "Bog Hag", "type": "npc", "hp": 8, "tags": ["swamp"]}',
    )
    assert added.code == 0 and "added mini-system.bog-hag" in added.out
    assert (home / "systems/mini-system/homebrew/compendium/bog-hag.yaml").is_file()
    found = cli("compendium", "find", "hag").out
    assert "mini-system.bog-hag · Bog Hag (npc)" in found
    assert (
        "homebrew:mini-system/compendium/bog-hag.yaml" in cli("compendium", "show", "bog-hag").out
    )
    cli("undo")
    assert "nothing in the compendium matches" in cli("compendium", "find", "hag").out
    bad = cli("compendium", "add", "--data", '{"type": "npc"}')
    assert bad.code == 1 and "an entry needs a name" in bad.err
