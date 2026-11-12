"""Details, the chronicle and whereabouts: the GM's notes that keep a game consistent."""

import json
from pathlib import Path
from typing import Any

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "pc", "Freya")
    cli("new", "npc", "Sweeney")


def data(cli: Cli, *args: str) -> Any:  # parsed JSON, read freely in tests
    done = cli(*args, "--format", "json")
    assert done.code == 0, done.err
    return json.loads(done.out)


def test_details_are_the_gms_notes_and_players_see_only_looks(cli: Cli, home: Path) -> None:
    setup(cli)
    written = cli(
        "about", "sweeney", "looks=tall, one eye clouded", "plan=sell the route",
        "doing=whittling", "Personality=jovial, greedy",
    )  # fmt: skip
    assert written.code == 0 and "plan: sell the route" in written.out
    record = (home / "worlds/vale/npc/sweeney.md").read_text(encoding="utf-8")
    assert "details:" in record and "plan: sell the route" in record  # plain front matter
    player = cli("show", "sweeney").out
    assert "looks: tall, one eye clouded" in player
    assert "sell the route" not in player and "GM details hidden" in player
    gm = cli("show", "sweeney", "--gm").out
    assert "plan: sell the route (GM)" in gm and "personality: jovial, greedy (GM)" in gm
    shown = data(cli, "show", "sweeney")
    assert shown["details"] == {"looks": "tall, one eye clouded"}
    assert shown["hidden"]["details"] == ["plan", "doing", "personality"]
    assert "suggested" not in shown  # the open suggestions are for the GM
    assert "wants" in data(cli, "show", "sweeney", "--gm")["suggested"]
    cli("about", "sweeney", "PLAN=wait for the ford")  # names match in any case
    cli("about", "sweeney", "--clear", "doing", "looks=")  # clear, or set to nothing
    details = data(cli, "about", "sweeney")["details"]
    assert details == {"plan": "wait for the ford", "personality": "jovial, greedy"}
    assert cli("about", "sweeney", "two words=x").code == 1
    assert cli("about", "sweeney", "--clear", "fears").code == 1
    assert cli("undo").code == 0 and "doing" in data(cli, "about", "sweeney")["details"]


def test_suggestions_follow_the_kind_of_record(cli: Cli, tmp_path: Path) -> None:
    setup(cli)
    cli("new", "item", "Old Sword")
    cli("new", "loc", "The Ford")
    assert data(cli, "about", "sweeney")["suggested"][:4] == [
        "looks", "personality", "wants", "fears",
    ]  # fmt: skip
    assert "powers" in data(cli, "about", "old sword")["suggested"]
    assert "state" in data(cli, "about", "the ford")["suggested"]
    pack = tmp_path / "noted"
    (pack / "schemas").mkdir(parents=True)
    (pack / "pack.yaml").write_text("id: noted\nname: Noted\nkind: system\nversion: 0.1.0\n")
    (pack / "schemas" / "npc.yaml").write_text(
        "type: npc\nfields: {mood: text}\ndetails: [mood, grudge, plan]\n"
    )
    assert cli("pack", "validate", str(pack)).code == 0
    (pack / "schemas" / "npc.yaml").write_text("type: npc\nfields: {}\ndetails: nope\n")
    assert "`details` lists detail names" in cli("pack", "validate", str(pack)).out


def test_revealing_a_detail_moves_it_into_the_record(cli: Cli) -> None:
    setup(cli)
    cli("about", "sweeney", "plan=sell the route", "secret=the Bone Queen's nephew")
    cli("session", "start")
    assert cli("reveal", "sweeney", "plan").code == 0
    player = cli("show", "sweeney").out
    assert "## Revealed" in player and "plan: sell the route" in player
    assert "nephew" not in player
    assert "plan" not in data(cli, "about", "sweeney")["details"]
    journal = cli("session", "show").out
    assert "revealed: Sweeney's plan: sell the route" in journal
    assert "revealed" in cli("show", "sweeney").out.split("chronicle:")[1]  # it's his


def test_hidden_details_stay_out_of_player_searches(cli: Cli) -> None:
    setup(cli)
    cli("about", "sweeney", "secret=he hoards moonsilver", "looks=wears a copper torc")
    assert "sweeney" not in cli("find", "moonsilver").out
    assert "npc:sweeney" in cli("find", "moonsilver", "--gm").out
    assert "npc:sweeney" in cli("find", "copper", "torc").out  # looks are for everyone


def test_the_chronicle_ties_beats_to_everyone_involved(cli: Cli) -> None:
    setup(cli)
    cli("session", "start")
    cli("scene", "new", "The ford")
    cli("log", "consequence", "Sweeney sold our route", "--about", "sweeney", "--about", "freya")
    cli("log", "note", "Scouts find the camp", "--about", "sweeney", "--secret")
    beat = data(cli, "log", "result", "The rope holds")["beat"]
    assert "about" not in beat and "secret" not in beat
    assert cli("log", "note", "x", "--about", "nobody-at-all").code == 1
    freya = data(cli, "show", "freya")["chronicle"]
    assert [b["text"] for b in freya] == ["Sweeney sold our route"]
    assert freya[0]["about"] == ["npc:sweeney", "pc:freya"]
    player = [b["text"] for b in data(cli, "show", "sweeney")["chronicle"]]
    gm = [b["text"] for b in data(cli, "show", "sweeney", "--gm")["chronicle"]]
    assert player == ["Sweeney sold our route"]
    assert gm == ["Sweeney sold our route", "Scouts find the camp"]
    assert "Scouts" in cli("about", "sweeney").out  # the dossier is the GM's
    assert "Scouts" not in cli("session", "show").out
    assert "Scouts" in cli("session", "show", "--gm").out
    story = cli("export", "--as", "story").out
    assert "Scouts" not in story
    assert "Off-screen lately (GM):" in cli("brief", "--gm").out
    assert "Scouts" not in cli("brief").out
    assert "Scouts" not in cli("history").out  # the change log says only that a beat was kept


def test_whereabouts_follow_the_inventories_down_and_up(cli: Cli) -> None:
    setup(cli)
    cli("new", "loc", "My House")
    cli("new", "item", "Chest")
    cli("new", "loc", "Vault", "--set", "knowledge=secret")
    cli("inv", "add", "my house", "item:chest")
    cli("inv", "add", "freya", "Sword", "Rope")
    cli("session", "start")
    moved = cli("inv", "move", "freya", "sword", "chest")
    assert moved.code == 0 and "Freya puts Sword in Chest (1 slot used)" in moved.out
    assert "Freya leaves Rope at My House" in cli("inv", "move", "freya", "rope", "my house").out
    taken = cli("inv", "move", "my house", "rope", "freya")
    assert "Freya takes Rope from My House" in taken.out
    where = data(cli, "where", "sword")
    assert [[step["id"] for step in chain] for chain in where["where"]] == [
        ["item:chest", "loc:my-house"]
    ]
    assert "sword: in Chest (item:chest) › at My House (loc:my-house)" in (
        cli("where", "sword").out
    )
    assert "carried by Freya" in cli("where", "rope").out
    house = data(cli, "show", "my house")
    assert house["contents"] == [
        {"name": "Chest", "ref": "item:chest", "contents": [{"name": "Sword"}]}
    ]
    assert "- Chest (item:chest)\n  - Sword" in cli("show", "my house").out
    assert data(cli, "show", "chest")["where"] == [[{"id": "loc:my-house", "name": "My House"}]]
    moves = [b["text"] for b in data(cli, "show", "chest")["chronicle"]]
    assert moves == ["Sword: Freya → Chest"]  # the move is on the chest's record too
    cli("inv", "move", "freya", "rope", "vault")
    assert "Vault" not in cli("where", "rope").out  # a secret place stays hidden
    assert "Vault" in cli("where", "rope", "--gm").out
    assert "nothing called 'lute'" in cli("where", "lute").out
    cli("inv", "add", "freya", "Long Bow")
    cli("inv", "move", "freya", "long bow", "chest")
    assert "in Chest (item:chest)" in cli("where", "bow").out  # "bow" finds the Long Bow


def test_fights_and_scenes_keep_positions_and_plans(cli: Cli) -> None:
    setup(cli)
    cli("new", "npc", "Goblin")
    cli("session", "start")
    cli("scene", "new", "The bridge")
    cli("combat", "start", "freya", "goblin")
    cli("about", "goblin", "where=on the bridge", "plan=cut the rope", "doing=sawing")
    status = cli("combat", "status", "--gm")
    assert "where: on the bridge · doing: sawing · plan: cut the rope" in status.out
    assert "cut the rope" not in cli("combat", "status").out
    notes = data(cli, "combat", "status", "--gm")["details"]
    assert notes["npc:goblin"]["plan"] == "cut the rope"
    brief = cli("brief", "--gm").out
    assert "In play (GM):" in brief and "Goblin [npc:goblin]: where: on the bridge" in brief
    assert "In play" not in cli("brief").out


def test_described_records_bring_their_details(cli: Cli) -> None:
    setup(cli)
    made = cli(
        "new", "npc", "Old Gannet", "--data",
        '{"name": "Old Gannet", "details": {"plan": "fish at dawn", "looks": "white beard"}}',
    )  # fmt: skip
    assert made.code == 0
    assert data(cli, "about", "old gannet")["details"] == {
        "plan": "fish at dawn", "looks": "white beard",
    }  # fmt: skip
    cli("edit", "old gannet", "--data", '{"details": {"wants": "a new boat", "plan": ""}}')
    assert data(cli, "about", "old gannet")["details"] == {
        "looks": "white beard", "wants": "a new boat",
    }  # fmt: skip
