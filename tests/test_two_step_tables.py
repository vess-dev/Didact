"""A table entry that rolls another table (one `table:` instead, or `then:` follow-ups) carries
what it rolled next: a rule's `table` step, and a draft's `table`, `choose`, `choose_or_roll` and
`roll_tables`, bind the data of the tables rolled next beside the entry's own (a key the entry
sets keeps its value, and of two follow-ups the first one's), and a draft binds it again when it
replays: the `follow-lite` fixture."""

import json
from typing import Any

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "follow-lite", "--seed", "follow").code == 0
    assert cli("campaign", "new", "c", "--seed", "follow").code == 0


def _draft(cli: Cli, *args: str) -> Any:  # parsed JSON, read freely in tests
    out = cli(*args, "--format", "json")
    assert out.code == 0, out.err
    return json.loads(out.out)["draft"]


def test_a_rule_reads_what_the_tables_rolled_next_carry(cli: Cli) -> None:
    setup(cli)
    done = cli("do", "scavenge").out
    assert "A blade: ashen-sword, blade, bulky" in done  # the entry's own size stays
    assert "A ring and a blade: ring-of-ash, ring, normal" in done  # the first follow-up's first
    assert "Ring of Ash: ring-of-ash, relic, deep" in done  # the table it rolls instead


def test_a_draft_binds_it_and_binds_it_again_when_it_replays(cli: Cli) -> None:
    setup(cli)
    made = _draft(cli, "gen", "run", "follow-lite.cache", "--auto")  # choose_or_roll and choose
    assert made["waiting"] == "owner"
    found = made["entities"][0]
    assert found["name"] == "Ashen Sword"  # the follow-up's compendium entry
    assert (found["fields"]["size"], found["fields"]["pair"]) == ("bulky", "ring-of-ash")
    path = [["follow-lite.blade-cache", "1"], ["follow-lite.blades", "1"]]
    assert ["find>", path] in made["trail"]  # beside the value: what the roll took
    answered = _draft(cli, "gen", "choose", "g1", "the smith")  # the draft replays
    assert answered["entities"] == made["entities"]
    assert answered["trail"][: len(made["trail"])] == made["trail"]

    hoard = _draft(cli, "gen", "run", "follow-lite.hoard", "--auto")  # a `table` step
    again = _draft(cli, "gen", "choose", hoard["id"], "the abbot")
    relic = again["entities"][0]
    assert (relic["name"], relic["fields"]["found"]) == ("Ring of Ash", "deep")

    started = _draft(cli, "char", "new", "--mode", "random")  # roll_tables: its gear too
    hero = _draft(cli, "char", "choose", started["id"], "to wander")["entities"][0]
    assert hero["fields"]["inventory"] == ["Ashen Sword"]
    assert hero["fields"]["traits"] == {"blade_cache": "A blade"}


def test_a_logged_table_roll_keeps_each_tables_data_where_it_was(cli: Cli) -> None:
    setup(cli)
    rolled = json.loads(cli("table", "roll", "blade-cache", "--format", "json").out)
    result = rolled["results"][0]
    assert result["data"] == {"size": "bulky"}  # the entry's own
    assert result["follow"][0]["data"]["id"] == "ashen-sword"  # the follow-up's, beside it
