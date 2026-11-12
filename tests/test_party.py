"""Party play: PCs, companions and hirelings in one campaign."""

import json

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "pc", "Freya", "--set", "STR=12", "--set", "hp=4")
    cli("new", "pc", "Ansel", "--set", "STR=10", "--set", "hp=3")
    cli("new", "npc", "Old Gannet", "--set", "hp=3")
    cli("spawn", "troll")


def test_the_party_roster(cli: Cli) -> None:
    setup(cli)
    assert (
        "Old Gannet joins the party (hireling)"
        in cli("party", "add", "old-gannet", "--as", "hireling").out
    )
    shown = cli("party", "show").out
    assert shown.startswith("Party (3):")
    assert "- Old Gannet [npc:old-gannet] (hireling) · hp 3/3 · armor 0" in shown
    brief = cli("brief").out
    assert "PC Ansel [pc:ansel]" in brief and "Hireling Old Gannet [npc:old-gannet]" in brief
    assert cli("party", "add", "old-gannet").code == 1  # already in
    assert cli("party", "add", "troll", "--as", "pc").code == 1  # not a PC
    left = cli("party", "remove", "freya", "--why", "died")
    assert left.code == 0 and "Freya leaves the party (pc: died)" in left.out
    after = cli("party", "show").out
    assert "Freya [pc:freya]" not in after and "left: pc:freya (died)" in after
    assert "PC Freya" not in cli("brief").out
    assert "Freya joins the party (pc)" in cli("party", "add", "freya").out
    data = json.loads(cli("party", "show", "--format", "json").out)
    assert [m["id"] for m in data["members"]] == ["pc:ansel", "pc:freya", "npc:old-gannet"]


def test_combat_can_bring_the_whole_party(cli: Cli) -> None:
    setup(cli)
    cli("party", "add", "old-gannet", "--as", "companion")
    fight = json.loads(cli("combat", "start", "--party", "troll", "--format", "json").out)
    sides = {f["ref"]: f["side"] for f in fight["combat"]["order"]}
    assert sides == {
        "pc:ansel": "party", "pc:freya": "party", "npc:old-gannet": "party", "npc:troll": "foes",
    }  # fmt: skip
    cli("combat", "end")
    alone = json.loads(cli("combat", "start", "old-gannet", "troll", "--format", "json").out)
    assert {f["ref"]: f["side"] for f in alone["combat"]["order"]}["npc:old-gannet"] == "party"
