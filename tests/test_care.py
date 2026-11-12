"""Keeping the library healthy: save points and forks, snapshots, sizes, continuity, the
timeline, graphs and the story."""

import json
import zipfile
from pathlib import Path

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "pc", "Wren", "--set", "hp=4")
    cli("session", "start")
    cli("scene", "new", "The Mill")
    cli("log", "action", "Wren sneaks into the mill")


def test_rewind_to_a_save_point_and_undo_it(cli: Cli) -> None:
    setup(cli)
    assert "saved 'before the fight'" in cli("save", "before the fight").out
    assert cli("save", "before the fight").code == 1  # names are unique
    cli("set", "wren", "hp-=3")
    cli("log", "result", "The miller strikes")
    rewound = cli("rewind", "before the fight")
    assert rewound.code == 0 and "rewound to 'before the fight'" in rewound.out
    assert (
        json.loads(cli("show", "wren", "--format", "json").out)["mechanics"]["mini-system"]["hp"][
            "value"
        ]
        == 4
    )
    assert "The miller strikes" in cli("session", "show").out  # the journal is history: kept
    assert "- before the fight" in cli("saves").out  # save points survive a rewind
    assert cli("undo").code == 0  # a rewind is one change
    assert (
        json.loads(cli("show", "wren", "--format", "json").out)["mechanics"]["mini-system"]["hp"][
            "value"
        ]
        == 1
    )
    assert "nothing to rewind" not in cli("rewind", "before the fight", "--dry-run").out
    assert cli("rewind", "no such point").code == 1


def test_fork_a_campaign_at_a_save_point(cli: Cli) -> None:
    setup(cli)
    cli("save", "start")
    cli("set", "wren", "hp-=2")
    forked = cli("campaign", "fork", "what-if", "--at", "start", "--name", "What if")
    assert forked.code == 0 and "forked into campaign what-if" in forked.out
    assert cli("campaign", "open", "what-if").code == 0
    wren = json.loads(cli("show", "wren", "--format", "json").out)
    assert wren["mechanics"]["mini-system"]["hp"]["value"] == 4  # as it was at the save point
    assert "What if" in cli("campaign", "show").out
    assert cli("campaign", "fork", "what-if").code == 1  # taken


def test_story_timeline_graph_and_continuity(cli: Cli, home: Path) -> None:
    setup(cli)
    cli("new", "npc", "Miller", "--body", "Grinds bones.")
    cli("new", "npc", "The Miler")
    cli("link", "wren", "knows", "miller")
    cli("time", "advance", "1", "day")
    cli("log", "note", "A day later")
    story = cli("export", "--as", "story").out
    assert story.startswith("# ") and "## Session 1" in story and "@ Wren sneaks" in story
    timeline = cli("timeline").out
    assert "## day 1" in timeline and "## day 2" in timeline and "A day later" in timeline
    graph = cli("graph", "wren").out
    assert "pc_wren -- knows --> npc_miller" in graph
    cli("set", "miller", "status=dead")
    cli("party", "add", "miller", "--as", "companion")
    issues = json.loads(cli("continuity", "--format", "json").out)["issues"]
    kinds = {i["kind"] for i in issues}
    assert {"near duplicate", "gone but in play"} <= kinds
    assert any("didact merge" in i["fix"] for i in issues)


def test_library_sizes_and_snapshots(cli: Cli, home: Path) -> None:
    setup(cli)
    listing = cli("library").out
    assert "- world vale:" in listing and "  - campaign run:" in listing
    made = json.loads(cli("snapshot", "--format", "json").out)
    archive = Path(made["snapshot"])
    assert archive.is_file() and archive.parent == home / "backups"
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
    assert any(n.startswith("worlds/vale/") for n in names)
    assert not any(n.startswith("backups/") for n in names)
    assert archive.name in cli("snapshot", "--list").out
