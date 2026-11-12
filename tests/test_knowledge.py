"""What the players know: player-safe views, reveal, the map and visiting, names."""

import json

from tests.conftest import Cli

SWEENEY = "Guards the wood.\n\n## Secrets\n- He is Anglwyst's son.\n- He fears fire.\n"


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "npc", "Sweeney", "--body", SWEENEY)
    cli("new", "npc", "Anglwyst", "--set", "knowledge=secret")
    cli("link", "sweeney", "parent", "npc:anglwyst")


def test_show_is_player_safe_unless_gm(cli: Cli) -> None:
    setup(cli)
    shown = cli("show", "sweeney").out
    assert "Guards the wood." in shown and "Anglwyst" not in shown and "fears" not in shown
    assert "(2 secret lines hidden: `didact show npc:sweeney --gm` shows them)" in shown
    gm = cli("show", "sweeney", "--gm").out
    assert "- He is Anglwyst's son." in gm and "parent → npc:anglwyst" in gm
    secret = cli("show", "anglwyst")
    assert secret.code == 0 and "npc:anglwyst is secret" in secret.out
    assert json.loads(cli("show", "anglwyst", "--format", "json").out)["hidden"] is True
    assert "mechanics.mini-system" not in shown  # no empty blocks
    cli("link", "anglwyst", "watches", "npc:sweeney")  # a secret record's link stays secret
    assert "referenced by" not in cli("show", "sweeney").out
    assert "referenced by: npc:anglwyst (watches)" in cli("show", "sweeney", "--gm").out


def test_find_hides_secret_records_and_secret_text(cli: Cli) -> None:
    setup(cli)
    son = cli("find", "son").out
    assert son.startswith("0 results") and "(1 secret match hidden; `--gm` shows them)" in son
    assert "npc:sweeney" in cli("find", "son", "--gm").out
    listing = cli("find", "--type", "npc").out
    assert "npc:sweeney" in listing and "anglwyst" not in listing
    assert (
        "npc:anglwyst · Anglwyst (world:vale) [secret]" in cli("find", "--type", "npc", "--gm").out
    )
    guards = cli("find", "guards").out
    assert "npc:sweeney · Sweeney (world:vale): Guards the wood." in guards


def test_reveal_a_record_or_one_secret_line(cli: Cli) -> None:
    setup(cli)
    cli("session", "start")
    line = cli("reveal", "sweeney", "anglwyst")
    assert line.code == 0 and "revealed Sweeney: He is Anglwyst's son." in line.out
    shown = cli("show", "sweeney").out
    assert "## Revealed\n- He is Anglwyst's son." in shown and "fears" not in shown
    assert "(1 secret line hidden" in shown
    missing = cli("reveal", "sweeney", "dragons")
    assert missing.code == 1 and "its secret lines: - He fears fire." in missing.err
    assert "revealed Anglwyst (rumor)" in cli("reveal", "anglwyst", "--rumor").out
    assert "npc:anglwyst · Anglwyst (world:vale) [rumor]" in cli("find", "--type", "npc").out
    assert "revealed Anglwyst (known)" in cli("reveal", "anglwyst").out
    assert "is already known" in cli("reveal", "anglwyst").out
    journal = cli("session", "show", "1").out
    assert "revealed: Sweeney: He is Anglwyst's son." in journal


def test_sheet_is_the_players_view(cli: Cli) -> None:
    setup(cli)
    cli(
        "new",
        "pc",
        "Freya",
        "--set",
        "STR=12",
        "--set",
        "hp=4",
        "--body",
        "Scarred.\n## GM\n- Doomed.\n",
    )
    cli("inv", "add", "freya", "Longsword", "Rope")
    cli("link", "freya", "rival", "npc:sweeney")
    cli("link", "freya", "hunted-by", "npc:anglwyst")
    sheet = cli("sheet", "freya").out
    assert sheet.startswith("# Freya (Player character)")
    assert "mini-system: STR 12 · hp 4/4 · armor 0" in sheet
    assert "Freya · inventory: 3/10 slots\n- Longsword (bulky, 2 slots): damage d8\n- Rope" in sheet
    assert "Links: rival → Sweeney" in sheet and "Anglwyst" not in sheet
    assert "Scarred." in sheet and "Doomed" not in sheet
    assert "Doomed" in cli("sheet", "freya", "--gm").out


def test_the_map_reveals_as_the_party_explores(cli: Cli) -> None:
    setup(cli)
    cli("new", "loc", "The Wood")
    cli("new", "loc", "Amber Grave", "--set", "region=loc:the-wood")
    cli("new", "loc", "The Hut")
    cli("new", "loc", "Old Mill", "--set", "knowledge=rumor")
    cli("new", "loc", "Hidden Vault", "--set", "knowledge=secret")
    cli("link", "amber-grave", "path", "loc:the-hut")
    cli("link", "amber-grave", "river", "loc:hidden-vault")
    cli("link", "the-hut", "road", "loc:old-mill")
    cli("link", "amber-grave", "hidden path", "loc:the-wood")
    before = cli("map").out
    assert "Old Mill [loc:old-mill] (rumored)" in before and "Vault" not in before
    assert "Amber Grave [loc:amber-grave] (not visited)\n" in before + "\n"  # no exits shown yet
    assert "(1 secret place hidden; `--gm` shows them)" in before
    visited = cli("visit", "amber-grave")
    assert "the party is at Amber Grave" in visited.out
    assert "note: exits: path → The Hut · river → ?" in visited.out
    after = cli("map").out
    assert after.startswith("Map · what the party knows · here: Amber Grave")
    assert "- The Wood [loc:the-wood] (visited)\n  - Amber Grave [loc:amber-grave] (here)" in after
    assert "Where: Amber Grave [loc:amber-grave]" in cli("brief").out
    assert "river → Hidden Vault" in cli("map", "--gm").out
    assert "hidden path" not in after and "hidden path → The Wood" in cli("map", "--gm").out
    assert cli("visit", "sweeney").code == 1  # not a place
    cli("visit", "old-mill")
    assert "Old Mill [loc:old-mill] (here) · exits: road → The Hut" in cli("map").out
    only = cli("map", "--within", "the-wood").out
    assert "- The Hut" not in only and "- Amber Grave" in only


def test_names_are_fresh_and_remembered(cli: Cli) -> None:
    setup(cli)
    rolled = cli("name", "npc", "--count", "3", "--format", "json")
    fresh = json.loads(rolled.out)["names"]
    assert len(fresh) == 3 and len(set(fresh)) == 3
    assert all(" " in n and not n.startswith("Kael") for n in fresh)  # first + surname, no cliché
    assert "offered earlier" in cli("names", "check", fresh[0]).out
    assert "taken: npc:sweeney" in cli("names", "check", "sweeney").out
    assert "overuse" in cli("names", "check", "Elara").out
    assert "fresh (nobody here has it)" in cli("names", "check", "Wenna", "Moss").out
    used = cli("names", "use", "Old", "Tom", "--for", "the ferryman")
    assert used.code == 0 and "registered Old Tom" in used.out
    assert "registered: the ferryman" in cli("names", "check", "old tom").out
    assert "- Old Tom — the ferryman" in cli("names", "list").out
    again = json.loads(cli("name", "npc", "--count", "3", "--format", "json").out)["names"]
    assert not set(again) & set(fresh)
    assert "overuse" in cli("new", "npc", "Kael").out
    missing = cli("name", "dragon")
    assert missing.code == 1 and "no name tables for 'dragon'" in missing.err
