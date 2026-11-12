"""The `cairn-2e` pack, its `cairn-2e-vald` setting, and a hack that extends it
(the `monolith-lite` fixture)."""

import json

import pytest

from tests.conftest import PACKS, Cli

pytestmark = pytest.mark.usefixtures("system_packs")


def test_the_pack_tests_pass_including_the_smoke_play(cli: Cli) -> None:
    result = cli("pack", "test", str(PACKS / "cairn-2e"))
    assert result.code == 0, result.out + result.err
    assert "cairn-2e: 26/26 tests passed" in result.out
    assert "smoke-play: 28 commands ran" in result.out
    for script in ("attacks", "scars", "armor-worn-or-held", "deprivation", "growth"):
        assert f"✔ {script}: " in result.out


def test_the_setting_pack_tests_pass(cli: Cli) -> None:
    result = cli("pack", "test", str(PACKS / "cairn-2e-vald"))
    assert result.code == 0, result.out + result.err
    assert "cairn-2e-vald: 2/2 tests passed" in result.out


def test_the_whole_book_is_converted(cli: Cli) -> None:
    result = cli("pack", "coverage", str(PACKS / "cairn-2e"))
    assert "cites 45 sections of 45 (100%)" in result.out


def test_a_region_a_forest_and_a_dungeon_nest_on_the_map(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "cairn-2e", "--seed", "vale")
    cli("campaign", "new", "c")
    assert cli("gen", "run", "cairn-2e.setting-seed", "--auto").code == 0
    region = json.loads(cli("gen", "show", "g1", "--format", "json").out)["draft"]
    kinds = [e["fields"].get("kind") for e in region["entities"] if e["type"] == "loc"]
    assert kinds[0] == "region" and "terrain" in kinds and kinds.count("poi") >= 4
    pois = [e for e in region["entities"] if e["key"].startswith("poi-")]
    assert pois[0]["fields"]["heart"] is True  # POI 1 is the Heart
    assert all(p["fields"]["region"].startswith("terrain-") for p in pois)  # in the nearest terrain
    assert all(len(r["details"]) == 2 for r in region["map"]["routes"])  # feature and condition
    factions = [e for e in region["entities"] if e["type"] == "faction"]
    assert factions and all(1 <= len(f["fields"]["advantages"]) <= 4 for f in factions)
    assert cli("gen", "commit", "g1").code == 0
    forest = cli("gen", "run", "cairn-2e.forest-seed", "region=loc:" + _slug(pois[0]["name"]))
    assert forest.code == 0 and "(entrance)" in forest.out and "(exit)" in forest.out
    assert cli("gen", "commit", "g2").code == 0
    dungeon = json.loads(
        cli("gen", "run", "cairn-2e.dungeon-seed", "--auto", "--format", "json").out
    )["draft"]
    rooms = [e for e in dungeon["entities"] if e["key"].startswith("room-")]
    assert 6 <= len(rooms) <= 20 and rooms[0]["name"].endswith(", room 1")
    assert all(r["fields"]["poi"] in ("monster", "lore", "special", "trap") for r in rooms)


def test_a_bond_or_background_result_adds_gold(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "cairn-2e", "--seed", "vale")
    cli("campaign", "new", "c")
    summer_home = (
        "A noble's summer home. The place was full of fancy wine (+20gp) but not much else. "
        "Take Fence Cutters."
    )
    prefill = {"background": "Cutpurse", "cutpurse_1": summer_home, "gold": 5, "name": "Ivy"}
    made = cli("char", "new", "--mode", "random", "--prefill", json.dumps(prefill))
    assert made.code == 0 and "gold +20" in made.out
    assert cli("char", "commit", "c1").code == 0
    ivy = json.loads(cli("show", "ivy", "--format", "json").out)
    assert ivy["mechanics"]["cairn-2e"]["gold"] >= 25  # 5, +20, and maybe a bond's gold


def test_detachments_and_recovery(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "cairn-2e", "--seed", "vale")
    cli("campaign", "new", "c", "--seed", "vale")
    cli("new", "pc", "Freya", "--set", "STR=12", "--set", "DEX=12", "--set", "WIL=12")
    cli("set", "freya", "hp=4", "gold=60")
    cli("new", "detachment", "Bandits", "--set", "hp=6", "--set", "STR=12", "--set", "count=6")
    on_unit = cli("do", "attack", "attacker=freya", "target=bandits", "weapon=d8")
    assert "The attack is impaired" in on_unit.out and "d4" in on_unit.out
    blast = cli("do", "attack", "attacker=freya", "target=bandits", "weapon=d8", "blast=true")
    assert "impaired" not in blast.out
    by_unit = cli("do", "attack", "attacker=bandits", "target=freya", "weapon=d6")
    assert "The attack is enhanced" in by_unit.out and "d12" in by_unit.out
    # Whatever the enhanced hit did, she's down to 8 STR with critical damage (STR 0 is death,
    # which no week of rest undoes).
    cli("set", "freya", "STR=8", "conditions+=critical")
    healed = cli("do", "recover", "who=freya")
    assert "attributes are restored (50gp)" in healed.out
    sheet = json.loads(cli("show", "freya", "--format", "json").out)["mechanics"]["cairn-2e"]
    assert (
        sheet["STR"]["value"] == 12
        and sheet["gold"] == 10
        and "critical" not in sheet.get("conditions", [])
    )


def test_the_setting_calendar_has_seasons_and_holidays(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "cairn-2e")
    assert cli("pack", "enable", "cairn-2e-vald").code == 0
    cli("campaign", "new", "c")
    advanced = cli("time", "advance", "23", "days")
    assert "Resting Day, 24 Mourning 7728 (Dead) · First Light" in advanced.out
    assert "holiday: First Light (24 Mourning)" in advanced.out


def test_a_hack_pack_extends_its_parent_system(cli: Cli) -> None:
    cli("world", "new", "void", "--system", "monolith-lite", "--seed", "vale")
    cli("campaign", "new", "c")
    assert "STR" in cli("template", "pc").out  # the base pack's character, inherited
    assert cli("new", "starship", "Rocinante", "--set", "hull=8").code == 0
    cli("new", "pc", "Nova", "--set", "STR=10", "--set", "hp=6")
    cli("new", "npc", "Drone", "--set", "STR=8", "--set", "hp=20")
    cli("new", "weapon", "Railgun")
    for _ in range(30):  # the die steps up on its highest face, for good
        cli("do", "overclock", "wielder=nova", "weapon=railgun", "target=drone")
        cli("set", "drone", "hp=20", "STR=8", "status=active")
    railgun = json.loads(cli("show", "railgun", "--format", "json").out)
    assert railgun["mechanics"]["monolith-lite"]["steps"] >= 1


def _slug(name: str) -> str:
    return "-".join("".join(c if c.isalnum() else " " for c in name.lower()).split())


def test_a_new_character_reads_as_words_not_data(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "cairn-2e", "--seed", "vale")
    cli("campaign", "new", "c")
    made = cli("char", "new", "--mode", "random")
    assert made.code == 0, made.err
    for python in ("{'", "['"):
        assert python not in made.out, made.out
    assert "inventory: [Rations, " in made.out, made.out  # items by their names, not as data
    assert "Physique: " in made.out and "physique " not in made.out  # traits by their titles
    assert cli("char", "commit", "c1").code == 0
    pc = json.loads(cli("find", "--type", "pc", "--format", "json").out)["results"][0]["id"]
    sheet = cli("sheet", pc).out
    assert "{'" not in sheet and "_1 " not in sheet and "Physique: " in sheet
    assert "in no group yet (they count as carried):" in sheet and "elsewhere" not in sheet
    found = cli("search", "torch").out
    assert "{'" not in found and "price 5 · uses 3" in found
