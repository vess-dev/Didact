"""The `cairn-2e` rules as the book has them: growth that writes the sheet, scars applied,
critical damage, deprivation counted per day, Fatigue that needs room, and the character
creation results of each background. (The pack's own scripted tests cover the rest.)"""

import json
import re

import pytest

from tests.conftest import Cli
from tests.test_web import Browser, web  # noqa: F401  (the fixture)

pytestmark = pytest.mark.usefixtures("system_packs")

type Sheet = dict[str, object]


def _world(cli: Cli, seed: str = "rules", world: str = "vale") -> None:
    assert cli("world", "new", world, "--system", "cairn-2e", "--seed", seed).code == 0
    assert cli("campaign", "new", "c", "--seed", seed).code == 0


def _sheet(cli: Cli, ref: str) -> Sheet:
    record = json.loads(cli("show", ref, "--format", "json").out)
    block = record["mechanics"]["cairn-2e"]
    assert isinstance(block, dict)
    return block


def _pc(cli: Cli, name: str, *sets: str) -> None:
    """A PC with 12 in each attribute and 4 HP, but for the fields given (each set once: a
    stat set lower later keeps its max, as damage does)."""
    fields = {"STR": "12", "DEX": "12", "WIL": "12", "hp": "4"}
    fields |= dict(item.split("=", 1) for item in sets)
    args = ["new", "pc", name]
    for key, value in fields.items():
        args += ["--set", f"{key}={value}"]
    assert cli(*args).code == 0


# ---------------------------------------------------------------------------- growth


def test_growth_raises_the_max_then_the_value_and_records_the_trigger(cli: Cli) -> None:
    _world(cli)
    _pc(cli, "Rui", "STR=7/10")
    started = cli(
        "char", "advance", "rui", "source=downtime", "how=raise", "attr=STR", "amount=1",
        "cost=none", "trigger=Trained with a Protector",
    )  # fmt: skip
    assert started.code == 0, started.out + started.err
    assert "STR raised 1: max 10 → 11" in started.out
    assert cli("char", "commit", "c1").code == 0
    sheet = _sheet(cli, "rui")
    assert sheet["STR"] == {"value": 8, "max": 11}  # max first, then the value by as much
    assert sheet["growth"] == [
        "Trained with a Protector (Downtime work): STR raised 1: max 10 → 11"
    ]


def test_growth_reroll_keeps_only_a_higher_result_and_hp_rerolls_on_the_chosen_dice(
    cli: Cli,
) -> None:
    _world(cli, "reroll")
    _pc(cli, "Ox", "WIL=3", "hp=1")
    made = cli(
        "char", "advance", "ox", "source=fiction", "pattern=yes", "risk=yes", "unique=no",
        "how=reroll", "attr=WIL", "cost=a WIL save when a foe is at his mercy",
        "trigger=Drank the murderer's spirit",
    )  # fmt: skip
    assert made.code == 0, made.out + made.err
    assert cli("char", "commit", "c1").code == 0
    sheet = _sheet(cli, "ox")
    wil = sheet["WIL"]
    assert isinstance(wil, dict) and wil["max"] >= 3 and wil["value"] == wil["max"]
    assert sheet["abilities"] == ["Flaw: a WIL save when a foe is at his mercy"]
    hp = cli(
        "char", "advance", "ox", "source=bond", "how=reroll", "attr=HP", "amount=3d6",
        "cost=none", "trigger=The curse lifted", "new_bond=no",
    )  # fmt: skip
    assert hp.code == 0 and "3d6" in hp.out
    assert cli("char", "commit", "c2").code == 0
    after = _sheet(cli, "ox")["hp"]
    assert isinstance(after, dict) and after["max"] >= 3


def test_the_app_grows_a_character_from_its_page(web: Browser, cli: Cli) -> None:  # noqa: F811
    _world(cli, "web", "wood")  # the web fixture's own world plays another system
    _pc(cli, "Rui", "STR=7/10")
    page = web.get("/record/pc:rui").body
    assert 'name="what" value="advance"' in page and "Growth" in page
    started = web.post("/drafts/start", {"what": "advance", "record": "pc:rui"})
    found = re.search(r"/drafts/(c\d+)", started.url)
    assert found is not None, started.body
    draft = found.group(1)
    for answer in ("downtime", "Trained with a Protector", "raise", "STR", "1", "none"):
        web.run("char", "choose", draft, answer, next_=f"/drafts/{draft}")
    committed = web.post(f"/drafts/{draft}/commit", {"verb": "char"})
    assert "/record/pc:rui?" in committed.url, committed.body
    assert _sheet(cli, "rui")["STR"] == {"value": 8, "max": 11}


def test_growth_stops_without_two_of_the_three(cli: Cli) -> None:
    _world(cli, "weak")
    _pc(cli, "Julius")
    started = cli("char", "advance", "julius", "source=fiction", "pattern=no")
    assert started.code == 0 and "waiting for risk" in started.out
    refused = cli("char", "choose", "c1", "no")
    assert refused.code != 0
    assert "Not a growth trigger" in refused.err
    assert _sheet(cli, "julius").get("growth") is None  # nothing was written


def test_growth_caps_attributes_at_twenty(cli: Cli) -> None:
    _world(cli, "cap")
    _pc(cli, "Titan", "STR=19")
    assert cli(
        "char", "advance", "titan", "source=downtime", "how=raise", "attr=STR", "amount=d8",
        "cost=none", "trigger=Years at the forge",
    ).code == 0  # fmt: skip
    assert cli("char", "commit", "c1").code == 0
    assert _sheet(cli, "titan")["STR"] == {"value": 20, "max": 20}


def test_a_resolved_bond_leaves_the_sheet_and_its_thread_is_done(cli: Cli) -> None:
    _world(cli, "bond")
    stone = (
        "You crossed a creature of the Wood, and it cursed you with a Stone Heart. With each "
        "passing month, the stone grows heavier by one slot. Until your debt is lifted, you "
        "cannot truly die."
    )
    prefill = {"background": "Cutpurse", "name": "Cobb", "youngest": "no", "bond": stone}
    assert cli("char", "new", "--mode", "random", "--prefill", json.dumps(prefill)).code == 0
    assert cli("char", "commit", "c1").code == 0
    sheet = _sheet(cli, "cobb")
    assert sheet["bond"] == [stone] and sheet["burden"] == 1
    resolved = cli("do", "resolve-bond", "who=cobb", "bond=bond-stone-heart")
    assert resolved.code == 0, resolved.out + resolved.err
    assert "char advance pc:cobb source=bond" in resolved.out
    after = _sheet(cli, "cobb")
    assert after["bond"] == [] and after["burden"] == 0
    thread = json.loads(cli("show", "thread:bond-stone-heart", "--format", "json").out)
    assert thread["status"] == "done"
    silver = (
        "You once freed a Naiad from a choked stream. In return, it gave you some Silver Moss "
        "(petty). Swallow it near water, and the creature will come, once, to repay its debt."
    )
    grew = cli(
        "char", "advance", "cobb", "source=bond", "how=ability", "cost=none", "new_bond=yes",
        "ability=A Boon of the Woodwose", "trigger=The Woodwose lifted the curse",
        "--prefill", json.dumps({"next_bond": silver}),
    )  # fmt: skip
    assert grew.code == 0, grew.out + grew.err
    committed = cli("char", "commit", "c2")
    assert committed.code == 0, committed.out + committed.err
    assert _sheet(cli, "cobb")["bond"] == [silver]
    naiad = json.loads(cli("show", "thread:bond-silver-moss", "--format", "json").out)
    assert naiad["fields"]["goal"] == silver
    assert {"rel": "of", "to": "pc:cobb"} in naiad["links"]  # the new bond's thread, beside it


# ---------------------------------------------------------------------------- combat and scars


def test_a_dying_pc_gets_an_hours_reminder(cli: Cli) -> None:
    _world(cli, "dying")
    _pc(cli, "Wren", "STR=3", "hp=1")
    assert cli("spawn", "blood-elk").code == 0
    hit = cli("do", "attack", "attacker=blood-elk", "target=wren", "weapon=3")
    assert "Wren takes critical damage" in hit.out, hit.out
    listed = cli("remind", "--list").out
    assert "Wren dies of critical damage unless stabilized" in listed
    due = cli("time", "advance", "1", "hour")
    assert "Wren dies of critical damage unless stabilized" in due.out


def test_critical_damage_skips_the_save_when_str_reaches_zero(cli: Cli) -> None:
    _world(cli, "dead")
    _pc(cli, "Wren", "STR=2", "hp=1")
    assert cli("spawn", "wolf").code == 0
    hit = cli("do", "attack", "attacker=wolf", "target=wren", "weapon=5")
    assert hit.code == 0, hit.out + hit.err
    assert "Wren is dead." in hit.out and "1d20" not in hit.out  # no save once STR is 0
    record = json.loads(cli("show", "wren", "--format", "json").out)
    assert record["status"] == "dead"


def test_a_detachment_at_zero_str_is_destroyed_and_a_monster_dies(cli: Cli) -> None:
    _world(cli, "units")
    _pc(cli, "Ivy")
    assert cli("new", "detachment", "Rats", "--set", "hp=1", "--set", "STR=1").code == 0
    hit = cli("do", "attack", "attacker=ivy", "target=rats", "weapon=4", "mode=normal")
    assert "Rats is destroyed." in hit.out
    assert json.loads(cli("show", "rats", "--format", "json").out)["status"] == "destroyed"


def test_two_dice_attacks_keep_the_highest(cli: Cli) -> None:
    _world(cli, "twin")
    owlbear = json.loads(cli("compendium", "show", "owlbear", "--format", "json").out)
    assert "{d8, d8}kh1" in json.dumps(owlbear)
    _pc(cli, "Ivy")
    assert cli("spawn", "wolf").code == 0
    hit = cli("do", "attack", "attacker=ivy", "target=wolf", "weapon={d6, d6}kh1")
    assert "{1d6, 1d6}kh1" in hit.out


def test_a_mortal_wound_heals_upon_recovery(cli: Cli) -> None:
    _world(cli, "mortal")
    _pc(cli, "Lucius", "gold=50")
    wounded = cli("do", "scar", "who=lucius", "lost=11")
    assert wounded.code == 0
    sheet = _sheet(cli, "lucius")
    assert sheet["conditions"] == ["deprived", "mortal-wound"]
    assert cli("do", "stabilize", "who=lucius").code == 0
    healed = cli("do", "recover", "who=lucius")
    assert healed.code == 0, healed.out + healed.err
    after = _sheet(cli, "lucius")
    assert after.get("conditions") == [] and after["gold"] == 0
    hp = after["hp"]
    assert isinstance(hp, dict) and 2 <= hp["max"] <= 12  # 2d6 is max HP now
    scars = after["scars"]
    assert isinstance(scars, list) and any("Mortal Wound, recovered" in s for s in scars)


def test_recover_works_without_critical_damage(cli: Cli) -> None:
    _world(cli, "recover")
    _pc(cli, "Freya", "gold=60")
    cli("set", "freya", "DEX-=3")
    healed = cli("do", "recover", "who=freya", "cost=0")
    assert healed.code == 0, healed.out + healed.err
    assert _sheet(cli, "freya")["DEX"] == {"value": 12, "max": 12}


# ---------------------------------------------------------------------------- needs


def test_deprivation_counts_a_fatigue_for_each_day_past_the_first(cli: Cli) -> None:
    _world(cli, "hunger")
    _pc(cli, "Lyra")
    totals = []
    for _day in range(3):
        assert cli("do", "deprive", "who=lyra", "need=food").code == 0
        totals.append(_sheet(cli, "lyra").get("fatigue", 0))
    assert totals == [0, 1, 2]


def test_fatigue_needs_a_free_slot(cli: Cli) -> None:
    _world(cli, "full")
    _pc(cli, "Hazel")
    assert cli("inv", "add", "hazel", *["Rope"] * 10).code == 0
    refused = cli("do", "fatigue", "who=hazel")
    assert refused.code == 0 and "drop an item first" in refused.out
    assert _sheet(cli, "hazel").get("fatigue") is None


def test_armor_counts_only_while_worn_or_held(cli: Cli) -> None:
    _world(cli, "armor")
    _pc(cli, "Rook")
    assert cli("inv", "add", "rook", "Shield", "Helmet").code == 0
    assert "armor 2" in cli("show", "rook").out
    assert cli("inv", "move", "rook", "Shield", "backpack").code == 0
    assert "armor 1" in cli("show", "rook").out  # a stowed shield protects no one


def test_skipping_camp_deprives_even_without_room_for_the_fatigue(cli: Cli) -> None:
    _world(cli, "sleepless")
    _pc(cli, "Hazel")
    assert cli("inv", "add", "hazel", *["Rope"] * 10).code == 0
    skipped = cli("do", "skip-camp", "who=hazel")
    assert skipped.code == 0 and "drop an item first" in skipped.out
    sheet = _sheet(cli, "hazel")
    assert sheet["conditions"] == ["deprived"] and sheet.get("fatigue") is None


def test_dungeon_turn_without_a_trigger_rolls_nothing(cli: Cli) -> None:
    _world(cli, "quiet")
    turn = cli("do", "dungeon-turn")
    assert turn.code == 0, turn.out + turn.err
    assert "No event this turn." in turn.out and "#r" not in turn.out


# ---------------------------------------------------------------------------- creation


def test_an_outrider_rides_a_horse_that_carries_its_own_load(cli: Cli) -> None:
    _world(cli, "horse")
    destrier = (
        "Heavy Destrier: A beast built for war, an imposing creature. 8 HP, 1 Armor, hooves "
        "(d10+d10), +2 slots."
    )
    prefill = {"background": "Outrider", "name": "Keir", "youngest": "no", "outrider_2": destrier}
    assert cli("char", "new", "--mode", "random", "--prefill", json.dumps(prefill)).code == 0
    assert cli("char", "commit", "c1").code == 0
    horse = _sheet(cli, "heavy-destrier")
    assert horse["owner"] == "pc:keir" and horse["slots"] == 2
    assert cli("inv", "add", "heavy-destrier", "Rope", "Rope").code == 0
    assert cli("inv", "add", "heavy-destrier", "Rope").code != 0  # two slots, no more


def test_a_hireling_gets_its_roles_wage_and_every_trait(cli: Cli) -> None:
    _world(cli, "hire")
    prefill = {"role": "Veteran Bodyguard", "name": "Brom"}
    made = cli("char", "new", "hireling", "--mode", "random", "--prefill", json.dumps(prefill))
    assert made.code == 0, made.out + made.err
    assert cli("char", "commit", "c1").code == 0
    record = json.loads(cli("show", "brom", "--format", "json").out)
    assert record["mechanics"]["cairn-2e"]["wage"] == 20
    assert len(record["fields"]["traits"]) == 8  # all the Character Traits tables
