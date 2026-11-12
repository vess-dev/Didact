"""Generators: drafts, choices, edits, commit (records, links, map), describe-it worlds."""

import json
from pathlib import Path
from typing import Any

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")


def draft(cli: Cli, *args: str) -> Any:  # parsed JSON, read freely in tests
    out = cli(*args, "--format", "json")
    assert out.code == 0, out.err
    return json.loads(out.out)["draft"]


def test_a_pointcrawl_draft_is_answered_edited_and_committed(cli: Cli, home: Path) -> None:
    setup(cli)
    started = draft(cli, "gen", "run", "pointcrawl", "size=4")
    assert started["id"] == "g1" and started["waiting"] == "terrain"
    assert not (home / "worlds/vale/loc").exists()  # a draft writes no records
    answered = draft(cli, "gen", "choose", "g1", "swamp")  # any case
    entities = answered["entities"]
    assert isinstance(entities, list) and len(entities) == 5
    assert entities[0]["name"] == "The Swamp Reach"
    places = answered["map"]["places"]
    assert places == ["poi-1", "poi-2", "poi-3", "poi-4"]
    routes = answered["map"]["routes"]
    assert len(routes) >= 3 and all(r["distance"] in ("short", "medium", "long") for r in routes)
    rolls_after_choice = len(answered["rolls"])
    shown = cli("gen", "show", "g1").out
    assert "```mermaid" in shown and "graph LR" in shown and "ask: What would draw people" in shown
    edited = draft(cli, "gen", "edit", "g1", "poi-1.name=Amber Grave", "--drop", "poi-4")
    assert len(edited["rolls"]) == rolls_after_choice  # editing rolls nothing
    assert "poi-4" not in json.dumps(edited["entities"])
    committed = cli("gen", "commit", "g1")
    assert committed.code == 0 and "4 records" in committed.out
    grave = json.loads(cli("show", "amber-grave", "--gm", "--format", "json").out)
    assert grave["fields"]["region"] == "loc:the-swamp-reach"  # a draft key became a record id
    assert "x" in grave["fields"]["map"] and grave["fields"]["routes"]
    assert any(link["rel"].endswith("path") for link in grave["links"])
    assert "The Swamp Reach" in cli("map", "--gm").out
    assert cli("gen", "show", "g1").code == 1  # the draft is gone once committed
    assert cli("undo").code == 0 and cli("show", "amber-grave").code == 1


def test_prefill_auto_discard_and_drafts(cli: Cli) -> None:
    setup(cli)
    auto = draft(cli, "gen", "run", "pointcrawl", "--prefill", '{"terrain": "Coast"}', "--auto")
    assert auto["waiting"] is None and auto["entities"][0]["name"] == "The Coast Reach"
    waiting = draft(cli, "gen", "run", "pointcrawl")
    assert waiting["waiting"] == "terrain"
    listed = cli("gen", "drafts").out
    assert "#g1 from mini-system.pointcrawl (ready to commit)" in listed
    assert "#g2 from mini-system.pointcrawl (waiting for terrain)" in listed
    assert cli("gen", "commit", "g2").code == 1  # still waiting
    rolled = draft(cli, "gen", "roll", "g2")
    assert rolled["waiting"] is None
    assert cli("gen", "discard", "g2").code == 0 and "g2" not in cli("gen", "drafts").out
    assert cli("gen", "choose", "g1", "Swamp").code == 1  # g1 isn't waiting
    assert cli("gen", "run", "nope").code == 1


def test_a_described_world_is_generated_and_committed(cli: Cli) -> None:
    made = cli(
        "world", "new", "fenmoor", "--system", "mini-system", "--gen", "pointcrawl",
        "--prefill", '{"terrain": "Swamp", "size": 3}',
    )  # fmt: skip
    assert made.code == 0 and "world fenmoor · Fenmoor created" in made.out
    assert "4 records from mini-system.pointcrawl" in made.out
    places = cli("find", "--type", "loc").out
    assert "The Swamp Reach" in places and places.startswith("4 records")  # as described
    assert cli("world", "new", "x", "--prefill", "{}").code == 1  # --prefill needs --gen


def test_generators_validate(cli: Cli, tmp_path: Path) -> None:
    pack = tmp_path / "bad-gen"
    (pack / "generators").mkdir(parents=True)
    (pack / "pack.yaml").write_text("id: bad-gen\nname: B\nkind: system\nversion: 0.1.0\n")
    (pack / "generators" / "g.yaml").write_text(
        "generator: g\nsteps:\n  - entity: {type: loc, name: X}\n  - teleport: somewhere\n"
        "  - repeat: 2\n    steps: [{choose: {from: [a]}, color: red}]\n"
    )
    result = cli("pack", "validate", str(pack))
    assert result.code == 1
    assert "generators/g.yaml:4: a step needs exactly one of:" in result.out
    assert "unknown step key `color`" in result.out


LAIRS = {"Den", "Nest", "Burrow", "Warren"}
LAIR_DETAILS = {"Bones", "Musk", "Eggs", "Silence"}
BOONS = {"Gold", "Silver", "A map", "A key", "A song", "A secret"}


def test_a_delve_replays_exactly_and_numbers_its_rooms(cli: Cli) -> None:
    setup(cli)
    assert draft(cli, "gen", "run", "delve")["waiting"] == "site"
    current = draft(cli, "gen", "choose", "g1", "Crypt")
    while current["waiting"]:  # a shrine asks for an offering; each answer replays the rest
        trail = current["trail"]
        current = draft(cli, "gen", "choose", "g1", "ask")
        assert current["trail"][: len(trail)] == trail  # nothing decided before changes
    site = current["entities"][0]
    assert site["name"] == "The Crypt Below"  # a `let` template
    assert "note" not in site["fields"]  # an empty value leaves the field out
    boons = site["fields"]["boons"]
    assert len(boons) == 3 and len(set(boons)) == 3 and set(boons) <= BOONS  # distinct draws
    rooms = [e for e in current["entities"] if e["key"].startswith("room-")]
    count = len(rooms)
    assert 4 <= count <= 7
    assert [r["key"] for r in rooms] == [f"room-{n}" for n in range(1, count + 1)]
    assert [r["name"] for r in rooms] == [f"The Crypt Below, room {n}" for n in range(1, count + 1)]
    assert rooms[0]["fields"]["map"]["entrance"] and rooms[-1]["fields"]["map"]["exit"]
    for room in rooms:  # the table each room rolled came from its die-drop entry
        what, detail = room["fields"]["feature"].split(", ")
        assert (what in LAIRS) == (detail in LAIR_DETAILS)
        assert room["fields"]["region"] == "site-1"
    number = {r["key"]: r["fields"]["map"]["n"] for r in rooms}
    routes = current["map"]["routes"]
    assert all(number[r["from"]] < number[r["to"]] for r in routes)  # away from the entrance
    assert all(r["details"][0] in BOONS for r in routes)  # `describe` rolls for each path
    assert {r.get("type", "standard") for r in routes} <= {"standard", "conditional", "hidden"}
    assert cli("gen", "commit", "g1").code == 0
    assert cli("show", "the-crypt-below-room-1").code == 0


def test_prefill_decides_lets_and_every_occurrence(cli: Cli) -> None:
    setup(cli)
    prefill = {"site": "Cave", "site_name": "Batholith", "rooms": 5, "offering": "hide"}
    done = draft(cli, "gen", "run", "delve", "--prefill", json.dumps(prefill), "--auto")
    assert done["waiting"] is None
    assert done["entities"][0]["name"] == "Batholith"  # a prefilled `let`
    assert len([e for e in done["entities"] if e["key"].startswith("room-")]) == 5
    offerings = [value for name, value in done["trail"] if name == "offering"]
    assert all(o == "hide" for o in offerings)  # a single value answers every occurrence


def test_exclude_rules_out_an_earlier_pick(cli: Cli) -> None:
    setup(cli)
    rerolled = 0
    for _ in range(12):
        done = draft(cli, "gen", "run", "rivals", "--auto")
        picks = dict(done["trail"])
        assert picks["first"] != picks["second"]
        assert [name for name, _ in done["trail"]].count("second") == 1  # a replay takes it
        rerolled += any("is ruled out; rolling again" in line for line in done["lines"])
    assert rerolled  # the d3 came up with the first pick at least once
    waiting = draft(cli, "gen", "run", "rivals", "--prefill", '{"first": "Cutpurse"}')
    shown = cli("gen", "show", waiting["id"]).out
    assert "waiting for second (or roll on backgrounds): Aurifex, Bonekeeper\n" in shown
    assert cli("gen", "choose", waiting["id"], "cutpurse").code == 1
    both = cli("gen", "run", "rivals", "--prefill", '{"first": "Cutpurse", "second": "Cutpurse"}')
    assert both.code == 1 and "second: Cutpurse is ruled out here" in both.err


def test_given_uses_the_trail_once_then_the_prefill() -> None:
    from didact.rules.engine import Given

    given = Given.build([("a", 1), ("a", 2), ("b", "x")], {"c": 7, "d": [1, 2]})
    assert [given.take("a"), given.take("a"), given.take("a")] == [1, 2, None]
    assert [given.take("c"), given.take("c")] == [7, 7]  # a single prefill value sticks
    assert [given.take("d"), given.take("d"), given.take("d")] == [1, 2, None]
    replay = Given.build([("d", 1)], {"d": [1, 2]})  # an earlier run used the first item
    assert [replay.take("d"), replay.take("d"), replay.take("d")] == [1, 2, None]
    whole = Given.build([], {"skills": ["Stealth", "Climb"]})
    assert whole.take_whole("skills") == "Stealth, Climb" and "skills" not in whole


def test_a_choice_from_a_computed_table_and_a_record_from_the_compendium(cli: Cli) -> None:
    setup(cli)
    assert "waiting for kind" in cli("gen", "run", "mini-system.armory").out
    kind = cli("gen", "choose", "g1", "Armor").out
    assert "waiting for item (or roll on armory-armor): Chainmail\n" in kind  # the kind's table
    made = cli("gen", "choose", "g1", "Chainmail").out
    assert "item Chainmail: armor: 2, size: bulky" in made  # the entry's type, name and fields
    assert cli("gen", "commit", "g1").code == 0
    record = json.loads(cli("show", "chainmail", "--format", "json").out)
    assert record["type"] == "item" and record["fields"]["note"] == "from the armory"
    rolled = draft(cli, "gen", "run", "mini-system.armory", "--auto")
    assert rolled["entities"][0]["name"] in ("Longsword", "Chainmail")


def test_a_question_any_answer_will_do_waits_even_for_the_dice(cli: Cli) -> None:
    setup(cli)
    made = draft(cli, "gen", "run", "mini-system.patron", "--auto")
    assert made["waiting"] == "wants"  # nothing to roll it from: even a random draft asks
    favor = made["entities"][0]["fields"]["favor"]
    assert favor in (4, 6, 8)  # picked by the dice from a list of numbers, and kept a number
    asked = made["open"]
    assert asked["note"] == f"what they want for {favor} favors"  # the prompt is filled in
    assert asked["free"] is True and asked["dice"] is False
    assert draft(cli, "gen", "choose", "g1", "a debt repaid")["waiting"] == "name"
    named = cli("gen", "choose", "g1", "Old Marrow").out
    assert "They carry " in named  # the pick, a list, read into the prompt
    assert cli("gen", "commit", "g1").code == 0
    fields = json.loads(cli("show", "old-marrow", "--format", "json").out)["fields"]
    assert fields["goal"] == "a debt repaid" and fields["favor"] == favor
    assert fields["deals_in"] == {"Weapons": "weapons", "Armor": "armor"}[fields["deals"]]
    assert len(fields["gear"]) == 2 and set(fields["gear"]) <= {"rope", "lamp, hooded", "chalk"}


def test_an_answer_of_ones_own_brings_no_entry_data(cli: Cli) -> None:
    setup(cli)
    prefill = {"favor": 6, "wants": "a map", "deals": "Spices", "gear": ["lamp, hooded", "chalk"]}
    prefill["name"] = "Pell"
    made = draft(cli, "gen", "run", "mini-system.patron", "--prefill", json.dumps(prefill))
    fields = made["entities"][0]["fields"]
    assert made["waiting"] is None and fields["deals"] == "Spices"
    assert "deals_in" not in fields  # not one of the table's entries: nothing to apply
    assert fields["gear"] == ["lamp, hooded", "chalk"]  # a pick may hold a comma of its own
    assert made["prompts"] == ["They carry lamp, hooded, chalk."]
