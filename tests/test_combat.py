"""Light combat: initiative modes, rounds, conditions, the system's attack rule."""

import json

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "pc", "Freya", "--set", "STR=12", "--set", "hp=4")
    cli("spawn", "troll")
    cli("spawn", "wolf")


def test_sides_rounds_and_conditions(cli: Cli) -> None:
    setup(cli)
    started = cli("combat", "start", "freya", "troll", "wolf")
    assert "round one: Each PC makes a DEX save" in started.out
    assert "round 1 · sides · now: party: Freya" in started.out
    assert cli("combat", "start", "freya", "troll").code == 1  # one fight at a time
    assert (
        "stunned on for 1 round:"
        in cli("combat", "condition", "troll", "stunned", "--rounds", "1").out
    )
    assert "now: foes: Troll, Wolf (round 1)" in cli("combat", "next").out
    second = cli("combat", "next").out
    assert "note: round 2" in second and "note: stunned ends for npc:troll" in second
    hit = cli("combat", "hit", "freya", "troll", "weapon=d8")
    assert hit.code == 0 and "action mini-system.attack" in hit.out
    status = cli("combat", "status").out
    assert status.startswith("round 2 · sides") and "Troll (foes)" in status
    assert "the fight ends after 2 rounds" in cli("combat", "end").out
    assert cli("combat", "status").out.strip() == "no fight is on"


def test_individual_initiative_is_rolled_and_logged(cli: Cli) -> None:
    setup(cli)
    started = cli(
        "combat", "start", "freya", "troll:bandits", "--mode", "individual", "--format", "json"
    )
    fight = json.loads(started.out)["combat"]
    assert fight["mode"] == "individual" and len(fight["order"]) == 2
    assert fight["order"][0]["init"] >= fight["order"][1]["init"]
    assert {f["side"] for f in fight["order"]} == {"party", "bandits"}
    assert "— initiative: Freya" in cli("rolls").out


def test_popcorn(cli: Cli) -> None:
    setup(cli)
    cli("combat", "start", "freya", "troll", "wolf", "--mode", "popcorn")
    assert "now: Wolf" in cli("combat", "next", "--to", "wolf").out
    assert cli("combat", "next", "--to", "wolf").code == 1  # the wolf already went
    assert "now: Troll" in cli("combat", "next").out
    assert "round 2" in cli("combat", "next").out


def test_a_fight_can_be_undone(cli: Cli) -> None:
    setup(cli)
    cli("combat", "start", "freya", "troll")
    cli("combat", "next")
    cli("undo")
    assert "round 1 · sides · now: party: Freya" in cli("combat", "status").out
