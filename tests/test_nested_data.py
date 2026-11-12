"""A table entry's data can hold mappings, read by their path (`@row.pool.dice`): in a rule, a
generator and character creation, for rolled, chosen, prefilled and replayed entries alike, and
in what a two-step roll carries from the table it rolled next (the `nested-lite` fixture)."""

import json
import re
from typing import Any

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "nested-lite", "--seed", "nest").code == 0
    assert cli("campaign", "new", "c", "--seed", "nest").code == 0


def _draft(cli: Cli, *args: str) -> Any:  # parsed JSON, read freely in tests
    out = cli(*args, "--format", "json")
    assert out.code == 0, out.err
    return json.loads(out.out)["draft"]


def test_a_rule_reads_an_entrys_mapping_by_its_path(cli: Cli) -> None:
    setup(cli)
    done = cli("do", "loot")
    assert done.code == 0, done.err
    found = re.search(r"(Cache|Vault): (\d) dice, a (\w+) pool of (\d)d", done.out)
    assert found is not None
    assert found.groups()[1:] in (("4", "task", "6"), ("2", "timer", "8"))
    assert re.search(r"The Wolf's den hides a [68]d pool\.", done.out)  # carried by `then:`


def test_drafts_read_it_rolled_chosen_prefilled_and_replayed(cli: Cli) -> None:
    setup(cli)
    rolled = _draft(cli, "gen", "run", "nested-lite.cache", "--auto")["entities"][0]
    pool = 6 if rolled["name"].startswith("Cache") else 8
    assert rolled["fields"]["pool"] == pool and rolled["name"].endswith(f", {pool}d")

    waiting = _draft(cli, "gen", "run", "nested-lite.cache", "--prefill", '{"row": 2}')
    assert waiting["waiting"] == "where"  # a roll of 2: the vault
    replayed = _draft(cli, "gen", "choose", waiting["id"], "hidden")["entities"][0]
    assert replayed["name"] == "Vault (hidden), 8d"
    assert replayed["fields"] == {"pool": 8, "kind": "timer"}

    started = _draft(cli, "char", "new", "--mode", "guided")
    chosen = _draft(cli, "char", "choose", started["id"], "Vault")["entities"][0]
    assert (chosen["fields"]["pool_dice"], chosen["fields"]["pool_kind"]) == (8, "timer")
    given = _draft(cli, "char", "new", "--prefill", '{"row": "cache"}', "--mode", "random")
    assert given["entities"][0]["fields"]["pool_dice"] == 6
