"""A two-step table whose first step says what it is (`{text: "A ring: roll on Rings", then:
[{table: rings}]}`, the `onward-lite` fixture): a prefill names what the step can come out as,
the next table's entries too, and a near miss is refused; a chosen first step rolls the next
table, as a roll landing on it does, and a draft replays it. Three levels down (school, element,
spell, and a ring of tables): a prefill finds an entry at any depth, the nearest of a name, and
one further down that goes on rolls on."""

import json
from typing import Any

from tests.conftest import Cli

GEN = "onward-lite.trinket"
SPELL = "onward-lite.spell"


def setup(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "onward-lite", "--seed", "onward").code == 0
    assert cli("campaign", "new", "c", "--seed", "onward").code == 0


def _run(cli: Cli, prefill: str) -> str:
    done = cli("gen", "run", GEN, "--prefill", json.dumps({"trinket": prefill}), "--auto")
    assert done.code == 0, done.err
    return done.out


def test_a_prefill_names_an_entry_of_the_next_table(cli: Cli) -> None:
    setup(cli)
    ring = _run(cli, "ring of the moon")  # any letter case
    assert "trinket: Ring of the Moon (given)" in ring
    assert "trinket: Ring of the Moon; id: ring-of-the-moon; kind: rings" in ring  # both data
    amulet = _run(cli, "amulet-of-kings")  # by its data's id
    assert "trinket: Amulet of Kings; id: amulet-of-kings; kind: amulets" in amulet
    missed = cli("gen", "run", GEN, "--prefill", '{"trinket": "Ring of the Mon"}', "--auto")
    assert (
        missed.code == 1
        and "prefilled trinket 'Ring of the Mon' isn't one of its options" in missed.err
    )
    assert "did you mean Ring of the Moon" in missed.err


def test_a_chosen_first_step_rolls_the_next(cli: Cli) -> None:
    setup(cli)
    first = _run(cli, "A ring: roll on Rings")
    assert "onward-lite.trinket-kinds (chosen): A ring: roll on Rings" in first
    assert "then onward-lite.rings (d2 → [" in first  # the next table, rolled
    assert "id: none" not in first and "kind: rings" in first
    assert cli("gen", "run", GEN).code == 0  # guided: it waits for the kind
    guided = cli("gen", "choose", "g2", "An amulet: roll on Amulets")
    assert guided.code == 0, guided.err
    assert "onward-lite.trinket-kinds (chosen): An amulet: roll on Amulets" in guided.out
    draft: Any = json.loads(cli("gen", "show", "g2", "--format", "json").out)["draft"]
    path = [["onward-lite.trinket-kinds", "3-4"], ["onward-lite.amulets"]]
    assert draft["trail"][0] == ["trinket", "An amulet: roll on Amulets"]
    assert draft["trail"][1][0] == "trinket>"  # its path kept: a replay rolls nothing new
    assert [
        step[: len(want)] for step, want in zip(draft["trail"][1][1], path, strict=True)
    ] == path


def _spell(cli: Cli, prefill: str) -> str:
    done = cli("gen", "run", SPELL, "--prefill", json.dumps({"spell": prefill, "owner": "Wren"}))
    assert done.code == 0, done.err
    return done.out


def test_a_prefill_names_an_entry_at_any_depth(cli: Cli) -> None:
    setup(cli)
    ball = _spell(cli, "Fireball")  # two steps down: every entry's data on the way comes too
    assert "spell: Fireball; id: fireball; school: destruction; element: fire; scroll: none" in ball
    draft: Any = json.loads(cli("gen", "show", "g1", "--format", "json").out)["draft"]
    way = [
        ["onward-lite.spell-schools", "1-2"],
        ["onward-lite.destruction", "1"],
        ["onward-lite.fire-spells", "2"],
    ]
    assert draft["trail"][1] == ["spell>", way]  # the path a roll would have taken
    flames = _spell(cli, "flames")  # the nearer of two: the spell, not the Scroll's
    assert "id: flames; school: destruction; element: fire; scroll: none" in flames
    assert "id: fire-rune; school: destruction; element: fire" in _spell(cli, "Rune")  # the first
    spike = _spell(cli, "ice-spike")  # by its data's id
    assert "spell: Ice Spike; id: ice-spike; school: destruction; element: frost" in spike
    missed = cli("gen", "run", SPELL, "--prefill", '{"spell": "Firebal"}')
    assert missed.code == 1 and "did you mean Fireball" in missed.err  # the nearest, at any depth
    own = _spell(cli, "Nothing like it")  # through a ring of tables, and out: one's own answer
    assert "spell: Nothing like it; id: none; school: none" in own


def test_a_prefilled_row_further_down_rolls_on(cli: Cli) -> None:
    setup(cli)
    made = cli("gen", "run", SPELL, "--prefill", '{"spell": "Frost"}')  # it waits for the owner
    assert made.code == 0, made.err
    assert "onward-lite.destruction (chosen): Frost" in made.out
    assert "then onward-lite.frost-spells (d2 → [" in made.out  # rolled on from there, logged
    before: Any = json.loads(cli("gen", "show", "g1", "--format", "json").out)["draft"]
    name, way = before["trail"][1]
    tables = ["onward-lite.spell-schools", "onward-lite.destruction", "onward-lite.frost-spells"]
    assert name == "spell>" and [step[0] for step in way] == tables and len(before["rolls"]) == 1
    answered = cli("gen", "choose", "g1", "Wren")  # a replay: nothing rolled again
    assert answered.code == 0, answered.err
    after: Any = json.loads(cli("gen", "show", "g1", "--format", "json").out)["draft"]
    assert after["rolls"] == before["rolls"] and after["trail"][:2] == before["trail"][:2]
    spell = "ice-spike" if way[2][1] == "2" else "frost-rune"
    assert f"id: {spell}; school: destruction; element: frost; scroll: none" in answered.out
