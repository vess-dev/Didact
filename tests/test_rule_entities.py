"""A rule makes a record at once with `entity:`, described as a draft's is (a pool tracker above
all, but any type, from a compendium entry too): checked against its sheet, logged and undone
with the rest of the rule, previewed by a dry run, and bound so later steps point at it
(`set: who.bleeding`, `pool: "@bleeding"`). One of that type and name already here is taken as
it is, so a rule run again makes nothing new (the `made-lite` fixture)."""

import json
from typing import Any

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "made-lite", "--seed", "made").code == 0
    assert cli("campaign", "new", "c", "--seed", "made").code == 0
    assert cli("new", "pc", "Freya", "--set", "hp=4").code == 0
    assert cli("new", "pc", "Ansel", "--set", "hp=3").code == 0


def _record(cli: Cli, ref: str) -> Any:  # parsed JSON, read freely in tests
    shown = cli("show", ref, "--format", "json")
    assert shown.code == 0, shown.err
    return json.loads(shown.out)


def test_a_rule_makes_a_pool_points_at_it_and_rolls_it(cli: Cli) -> None:
    setup(cli)
    made = "+ track Freya: Bleeding Out [track:freya-bleeding-out]"
    preview = cli("do", "bleed", "who=freya", "--dry-run").out
    assert made in preview and "+ create worlds/w/campaigns/c/track/freya-bleeding-out" in preview
    assert cli("show", "track:freya-bleeding-out").code == 1  # a dry run keeps nothing
    bled = cli("do", "bleed", "who=freya").out
    assert made in bled and "pool Freya: Bleeding Out" in bled  # rolled in the same run
    pool = _record(cli, "track:freya-bleeding-out")
    assert (pool["fields"]["kind"], pool["fields"]["note"]) == ("pool", "dropped")
    assert pool["links"] == [{"rel": "of", "to": "pc:freya"}]
    assert _record(cli, "freya")["mechanics"]["made-lite"]["bleeding"] == pool["id"]
    left = pool["fields"]["value"]["value"]

    again = cli("do", "bleed", "who=freya").out  # run again: the same pool, rolled again
    assert "track Freya: Bleeding Out [track:freya-bleeding-out] is here already" in again
    assert _record(cli, "track:freya-bleeding-out")["fields"]["value"]["value"] <= left
    assert cli("undo").code == 0 and cli("undo").code == 0  # each run undone whole
    assert cli("show", "track:freya-bleeding-out").code == 1
    assert "bleeding" not in _record(cli, "freya")["mechanics"]["made-lite"]


def test_a_shared_pool_is_made_once_for_every_pc(cli: Cli) -> None:
    setup(cli)
    assert "+ track Party Stimpaks [track:party-stimpaks]" in cli("do", "stock").out
    assert "is here already" in cli("do", "stock").out
    assert cli("show", "track:party-stimpaks-2").code == 1  # nothing new the second time
    for pc in ("freya", "ansel"):
        assert _record(cli, pc)["mechanics"]["made-lite"]["stimpaks"] == "track:party-stimpaks"


def test_any_type_from_a_compendium_entry_checked_against_its_sheet(cli: Cli) -> None:
    setup(cli)
    summoned = cli("do", "summon").out  # a procedure
    assert "+ npc Wolf [npc:wolf]" in summoned and "Wolf answers the call with 3 HP." in summoned
    assert _record(cli, "npc:wolf")["tags"] == ["summoned"]
    refused = cli("do", "mistake")
    assert refused.code == 1 and "made-lite.hp must be a whole number, not 'lots'" in refused.err
    assert cli("show", "npc:shade").code == 1  # refused whole: nothing written
