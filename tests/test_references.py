"""When an id changes (a merge, a new slug), every reference follows: links and text, the GM's
details, the records journal beats are about, the party, the fight and the party's place."""

import json
from pathlib import Path

from tests.conftest import Cli


def test_a_merge_takes_every_reference_with_it(cli: Cli, home: Path) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "pc", "Freya")
    cli("new", "npc", "Tom")
    cli("new", "npc", "Tom Two", "--id", "tom-2")
    cli("new", "loc", "Mill")
    cli("new", "loc", "Old Mill", "--id", "mill-2")
    cli("party", "add", "tom-2", "--as", "hireling")
    cli("session", "start")
    cli("visit", "mill-2")
    cli("combat", "start", "freya", "tom-2")
    cli("log", "consequence", "Tom Two lied", "--about", "tom-2", "--about", "freya")
    cli("about", "freya", "attitude=wary of npc:tom-2")
    assert cli("merge", "npc:tom-2", "npc:tom", "--yes").code == 0
    assert cli("merge", "loc:mill-2", "loc:mill", "--yes").code == 0
    state = home / "worlds/vale/campaigns/run/state"
    assert "npc:tom-2" not in (state / "party.yaml").read_text()
    assert "npc:tom" in (state / "party.yaml").read_text()
    assert "npc:tom-2" not in (state / "combat.yaml").read_text()
    assert "location: loc:mill" in (state / "play.yaml").read_text()
    shown = json.loads(cli("about", "tom", "--format", "json").out)
    assert [b["text"] for b in shown["chronicle"]] == ["Tom Two lied"]
    freya = json.loads(cli("about", "freya", "--format", "json").out)
    assert freya["details"]["attitude"] == "wary of npc:tom"
    journal = (home / "worlds/vale/campaigns/run/journal/session-001.jsonl").read_text()
    assert "Tom Two lied" in journal  # the beat's own words stay as they were written


def test_a_deleted_record_leaves_play_and_undo_brings_it_back(cli: Cli, home: Path) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "pc", "Freya")
    cli("new", "npc", "Tom")
    cli("new", "npc", "Goblin")
    cli("new", "loc", "Mill")
    cli("party", "add", "tom", "--as", "hireling")
    cli("session", "start")
    cli("visit", "mill")
    cli("combat", "start", "freya", "tom", "goblin")
    cli("combat", "next")
    cli("combat", "next")  # the goblin's turn (sides: party, then foes)
    before = json.loads(cli("combat", "status", "--format", "json").out)["combat"]
    turn_of = before["order"][before["turn"]]["ref"] if "order" in before else None
    gone = cli("rm", "tom")
    assert gone.code == 0 and "left the party (campaign run)" in gone.out
    assert "left the fight (campaign run)" in gone.out
    assert "npc:tom" not in cli("party", "show").out
    after = json.loads(cli("combat", "status", "--format", "json").out)["combat"]
    assert [f["ref"] for f in after["order"]] == ["pc:freya", "npc:goblin"]
    if turn_of and turn_of != "npc:tom":
        assert after["order"][after["turn"]]["ref"] == turn_of  # the same fighter's turn
    removed = cli("rm", "mill")
    assert "the party is nowhere in particular now" in removed.out
    assert "loc:mill" not in (home / "worlds/vale/campaigns/run/state/play.yaml").read_text()
    assert cli("undo").code == 0 and cli("undo").code == 0
    assert "npc:tom" in cli("party", "show").out
    assert "Tom" in cli("combat", "status").out
