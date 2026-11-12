"""Changing and removing what could only be made: fighters mid-fight, reminders, names, homebrew."""

import json
from pathlib import Path
from typing import Any, cast

from didact.services import combat
from tests.conftest import Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "pc", "Freya", "--set", "STR=12", "--set", "hp=4")
    cli("spawn", "troll")
    cli("spawn", "wolf", "--count", "3")


def run_json(cli: Cli, *args: str) -> dict[str, Any]:
    result = cli(*args, "--format", "json")
    assert result.code == 0, result.err
    return cast(dict[str, Any], json.loads(result.out))


def fight(cli: Cli) -> dict[str, Any]:
    return cast(dict[str, Any], run_json(cli, "combat", "status")["combat"])


def up(state: dict[str, Any]) -> str:
    """Whose turn it is (individual and popcorn modes)."""
    return str(state["order"][state["turn"]]["ref"])


def refs(state: dict[str, Any]) -> list[str]:
    return [str(f["ref"]) for f in state["order"]]


# ---------------------------------------------------------------------------- combat join


def test_joiners_roll_initiative_and_take_their_place(cli: Cli) -> None:
    setup(cli)
    cli("combat", "start", "freya", "troll", "--mode", "individual")
    cli("combat", "next")
    before = fight(cli)
    joined = cli("combat", "join", "wolf-1", "wolf-2:bandits")
    assert joined.code == 0 and "Wolf 1 (foes), Wolf 2 (bandits) join the fight" in joined.out
    assert "— initiative: Wolf 1" in joined.out and "— initiative: Wolf 2" in joined.out
    after = fight(cli)
    inits = [f["init"] for f in after["order"]]
    assert inits == sorted(inits, reverse=True)  # slotted in by initiative
    assert up(after) == up(before) and after["round"] == 1  # the turn stays where it was
    assert after["sides"] == ["party", "foes", "bandits"]
    logged = run_json(cli, "rolls", "--limit", "100")["rolls"]
    for fighter in after["order"]:
        if fighter["ref"] in ("npc:wolf-1", "npc:wolf-2"):
            wanted = f"initiative: {fighter['name']}"
            roll = next(r for r in logged if r["line"].endswith(wanted))
            assert roll["value"] == fighter["init"]


def test_join_appends_in_sides_and_popcorn_modes(cli: Cli) -> None:
    setup(cli)
    cli("combat", "start", "freya", "troll")
    assert "Wolf 1 (foes) joins the fight" in cli("combat", "join", "wolf-1").out
    cli("combat", "join", "wolf-2:bandits")
    assert refs(fight(cli)) == ["pc:freya", "npc:troll", "npc:wolf-1", "npc:wolf-2"]
    assert "initiative" not in cli("rolls").out  # sides mode rolls nothing
    assert "now: foes: Troll, Wolf 1 (round 1)" in cli("combat", "next").out
    assert "now: bandits: Wolf 2 (round 1)" in cli("combat", "next").out  # a new side goes last
    assert "now: party: Freya (round 2)" in cli("combat", "next").out
    cli("combat", "end")
    cli("combat", "start", "freya", "troll", "--mode", "popcorn")
    cli("combat", "join", "wolf-3")
    assert refs(fight(cli))[-1] == "npc:wolf-3" and up(fight(cli)) == "pc:freya"
    assert "now: Wolf 3 (round 1)" in cli("combat", "next", "--to", "wolf-3").out


def test_nobody_joins_twice(cli: Cli) -> None:
    setup(cli)
    cli("combat", "start", "freya", "troll", "--mode", "individual")
    rolled = len(run_json(cli, "rolls", "--limit", "100")["rolls"])
    again = cli("combat", "join", "wolf-1", "troll")
    assert again.code == 1 and "already in the fight: Troll" in again.err
    assert len(run_json(cli, "rolls", "--limit", "100")["rolls"]) == rolled  # before any roll
    assert len(fight(cli)["order"]) == 2
    assert cli("combat", "join").code == 2
    cli("combat", "end")
    alone = cli("combat", "join", "wolf-1")
    assert alone.code == 1 and "no fight is on" in alone.err


def test_individual_joiners_slot_in_by_roll_without_moving_the_turn() -> None:
    def fighter(ref: str, init: float = 0) -> combat.Fighter:
        return combat.Fighter(ref, ref.upper(), "foes", init)

    state = combat.Fight(
        mode="individual", turn=1, order=[fighter("a", 18), fighter("b", 12)], sides=["foes"]
    )
    combat.join(state, [fighter("d")], {"d": 15})  # higher than b, who is acting: next round
    assert [f.ref for f in state.order] == ["a", "d", "b"] and state.order[state.turn].ref == "b"
    combat.join(state, [fighter("e"), fighter("f")], {"e": 12, "f": 3})  # a tie goes after
    assert [f.ref for f in state.order] == ["a", "d", "b", "e", "f"]
    assert state.order[state.turn].ref == "b"


# ---------------------------------------------------------------------------- combat leave


def test_leave_in_sides_mode(cli: Cli) -> None:
    setup(cli)
    cli("combat", "start", "freya", "troll", "wolf-1")
    cli("combat", "condition", "troll", "stunned")
    cli("combat", "next")  # the foes' turn
    fled = cli("combat", "leave", "troll", "--why", "fled")
    assert "✔ Troll leaves the fight (fled); now: foes: Wolf 1 (round 1)" in fled.out
    assert fight(cli)["conditions"] == []  # their conditions went with them
    cli("undo")
    logged = run_json(cli, "combat", "leave", "troll", "--why", "fled")
    assert logged["summary"] == "combat: Troll leaves (fled)" and logged["left"] == "npc:troll"
    last = cli("combat", "leave", "wolf-1", "--why", "died")
    assert "now: party: Freya (round 2)" in last.out and "note: round 2" in last.out
    assert "note: only one side is left (party): `didact combat end`" in last.out
    assert fight(cli)["sides"] == ["party"]
    everyone = cli("combat", "leave", "freya")
    assert "note: nobody is left in the fight" in everyone.out
    assert cli("combat", "next").code == 1  # nobody to act
    assert cli("combat", "end").code == 0


def test_leave_in_individual_mode_skips_nobody(cli: Cli) -> None:
    setup(cli)
    cli("combat", "start", "freya", "troll", "wolf-1", "wolf-2", "--mode", "individual")
    order = refs(fight(cli))
    cli("combat", "next")  # the second fighter's turn
    cli("combat", "leave", order[0])  # someone before the turn leaves
    assert up(fight(cli)) == order[1]
    cli("combat", "leave", order[1], "--why", "surrendered")  # the one acting leaves
    state = fight(cli)
    assert up(state) == order[2] and state["round"] == 1  # the next one is up
    cli("combat", "next")
    assert up(fight(cli)) == order[3]
    wrapped = cli("combat", "leave", order[3])  # the last of the round leaves on their turn
    state = fight(cli)
    assert refs(state) == [order[2]] and state["round"] == 2 and "note: round 2" in wrapped.out
    missing = cli("combat", "leave", order[3])
    assert missing.code == 1 and "isn't in the fight" in missing.err and order[2] in missing.err


def test_leave_in_popcorn_mode(cli: Cli) -> None:
    setup(cli)
    cli("combat", "start", "freya", "troll", "wolf-1", "wolf-2", "--mode", "popcorn")
    cli("combat", "next", "--to", "wolf-2")
    gone = cli("combat", "leave", "Wolf 2")  # the one acting: the first who hasn't acted is up
    assert "now: Troll (round 1)" in gone.out
    cli("combat", "next")  # the troll acted: Wolf 1 is left this round
    assert up(fight(cli)) == "npc:wolf-1"
    cli("combat", "leave", "troll")  # before the turn: Wolf 1 keeps it
    state = fight(cli)
    assert up(state) == "npc:wolf-1" and state["acted"] == ["pc:freya"]
    assert "now: Freya (round 2)" in cli("combat", "next").out


def test_join_and_leave_can_be_undone(cli: Cli) -> None:
    setup(cli)
    cli("combat", "start", "freya", "troll")
    cli("combat", "join", "wolf-1")
    cli("undo")
    assert refs(fight(cli)) == ["pc:freya", "npc:troll"]
    cli("combat", "condition", "troll", "prone")
    cli("combat", "leave", "troll", "--why", "fled")
    cli("undo")
    state = fight(cli)
    assert refs(state) == ["pc:freya", "npc:troll"] and state["sides"] == ["party", "foes"]
    assert state["conditions"] == [{"ref": "npc:troll", "name": "prone", "rounds": None}]


# ---------------------------------------------------------------------------- reminders


def test_reminders_can_be_listed_and_cancelled(cli: Cli) -> None:
    setup(cli)
    assert cli("remind", "--list").out.strip() == "no reminders are pending"
    added = cli("remind", "Eat a ration", "--every", "1 day")
    assert "reminder set for day 2, 00:00 (morning watch): Eat a ration" in added.out
    cli("remind", "The ferry leaves", "--in", "2 watches")
    cli("remind", "Check the torches", "--every", "6 turns")
    listed = cli("remind", "--list").out
    assert listed.startswith("3 reminders (it's day 1, 00:00 (morning watch)):")
    assert "1. Check the torches · day 1, 01:00 (morning watch) · every 1 hour" in listed
    assert "2. The ferry leaves · day 1, 16:00 (night watch)\n" in listed
    assert "3. Eat a ration · day 2, 00:00 (morning watch) · every 1 day" in listed
    rows = run_json(cli, "remind", "--list")["reminders"]
    assert [r["n"] for r in rows] == [1, 2, 3] and rows[2]["every"] == 86400
    by_number = cli("remind", "--cancel", "2")
    assert "cancelled the reminder for day 1, 16:00 (night watch): The ferry leaves" in (
        by_number.out
    )
    by_words = cli("remind", "--cancel", "RATION eat")
    assert "Eat a ration" in by_words.out
    assert "1. Check the torches" in cli("remind", "--list").out
    assert "Eat a ration" not in cli("remind", "--list").out
    unknown = cli("remind", "--cancel", "dragon")
    assert unknown.code == 1 and "no reminder mentions 'dragon'" in unknown.err
    assert "pending: 1. Check the torches" in unknown.err
    assert cli("remind", "--cancel", "4").code == 1
    assert cli("remind", "--cancel", "ferry", "leaves").code == 2  # quote the words
    cli("undo")
    assert "Eat a ration" in cli("remind", "--list").out
    day = cli("time", "advance", "1", "day")
    assert "note: reminder: Eat a ration" in day.out  # still fires as before


# ---------------------------------------------------------------------------- names


def test_names_can_be_forgotten(cli: Cli) -> None:
    setup(cli)
    cli("names", "use", "Old", "Tom", "--for", "the ferryman")
    cli("names", "use", "Brannoc")
    forgot = cli("names", "forget", "old", "tom")
    assert forgot.code == 0 and "forgot Old Tom (the ferryman)" in forgot.out
    assert "Old Tom" not in cli("names", "list").out
    assert "fresh (nobody here has it)" in cli("names", "check", "Old", "Tom").out
    cli("undo")
    assert "- Old Tom — the ferryman" in cli("names", "list").out
    offered = run_json(cli, "name", "npc")["names"][0]
    assert "offered earlier" in cli("names", "check", offered).out
    cli("names", "forget", offered)
    assert "fresh" in cli("names", "check", offered).out
    assert offered not in cli("names", "list").out
    unknown = cli("names", "forget", "Nobody")
    assert unknown.code == 1 and "Nobody isn't a registered name" in unknown.err
    assert "registered names: Old Tom, Brannoc" in unknown.err
    record = cli("names", "forget", "freya")
    assert record.code == 1 and "it's the name of pc:freya" in record.err


# ---------------------------------------------------------------------------- compendium


def test_homebrew_entries_can_be_removed_but_pack_entries_cannot(cli: Cli, home: Path) -> None:
    setup(cli)
    cli("compendium", "add", "--data", '{"name": "Frost Wolf", "type": "npc", "hp": 6}')
    path = home / "systems/mini-system/homebrew/compendium/frost-wolf.yaml"
    removed = cli("compendium", "remove", "Frost Wolf")
    assert removed.code == 0 and "removed mini-system.frost-wolf · Frost Wolf" in removed.out
    assert not path.exists()
    assert "frost-wolf" not in cli("compendium", "find", "wolf").out
    cli("undo")
    assert path.is_file() and "mini-system.frost-wolf" in cli("compendium", "find", "wolf").out
    assert cli("compendium", "remove", "mini-system.frost-wolf").code == 0
    pack = cli("compendium", "remove", "troll")
    assert pack.code == 1 and "mini-system.troll is the mini-system pack's own entry" in pack.err
    assert "didact override add entry mini-system.troll" in pack.err
    assert "mini-system.troll" in cli("compendium", "find", "troll").out
    assert cli("compendium", "remove", "dragon").code == 1


def test_a_house_rule_on_a_homebrew_entry_is_taken_back_first(cli: Cli) -> None:
    setup(cli)
    cli("compendium", "add", "--data", '{"name": "Frost Wolf", "type": "npc", "hp": 6}')
    cli("override", "add", "entry", "frost-wolf", "--data", '{"hp": 9}')
    ruled = cli("compendium", "remove", "frost-wolf")
    assert (
        ruled.code == 1 and "a house rule still changes mini-system.frost-wolf (world)" in ruled.err
    )
    assert "didact override remove entry mini-system.frost-wolf --scope world" in ruled.err
    cli("override", "remove", "entry", "frost-wolf")
    assert cli("compendium", "remove", "frost-wolf").code == 0
    assert "frost-wolf" not in cli("compendium", "find", "wolf").out


def test_removing_one_of_several_homebrew_entries_in_a_file(cli: Cli, home: Path) -> None:
    setup(cli)
    beasts = home / "systems/mini-system/homebrew/compendium/beasts.yaml"
    beasts.parent.mkdir(parents=True)
    text = (
        "id: ice-bear\ntype: npc\nname: Ice Bear\n---\nid: snow-hare\ntype: npc\nname: Snow Hare\n"
    )
    beasts.write_text(text)
    removed = cli("compendium", "remove", "ice-bear")
    assert "note: systems/mini-system/homebrew/compendium/beasts.yaml still holds 1 entry" in (
        removed.out
    )
    found = cli("compendium", "find", "--type", "npc").out
    assert "Snow Hare" in found and "Ice Bear" not in found
    cli("undo")
    assert beasts.read_text() == text
