"""A rule changes what a character carries as the inventory commands do: `set` reaches a carried
item's own keys (`who.inventory.$item.damage`; uses and charges count within their max), and
`didact set` the same way; `give` and `take` add and drop items as `inv add` and `inv drop` do.
The item is named as they name it, and the room and the field's hooks are checked as they check
them (the `carry-lite` fixture)."""

import json
from pathlib import Path
from typing import Any

from tests.conftest import Cli

SWORD = {
    "name": "Steel sword",
    "damage": "d10",
    "size": "normal",
    "entry": "carry-lite.steel-sword",
}


def setup(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "carry-lite", "--seed", "carry").code == 0
    assert cli("campaign", "new", "c", "--seed", "carry").code == 0
    assert cli("new", "pc", "Freya", "--set", "hp=4").code == 0


def _items(cli: Cli) -> Any:  # parsed JSON, read freely in tests
    return json.loads(cli("inv", "show", "freya", "--format", "json").out)["items"]


def test_a_rule_changes_a_carried_items_own_keys(cli: Cli) -> None:
    setup(cli)
    cli("inv", "add", "freya", "Steel sword")
    cli("inv", "add", "freya", "Amulet", "--data", '{"charges": {"value": 1, "max": 3}}')
    tempered = cli("do", "temper", "who=freya", "item=Steel sword").out
    assert "pc:freya: inventory.Steel sword.damage = d10" in tempered
    assert _items(cli)[0] == {**SWORD, "tempered": True}
    assert cli("do", "charge", "who=freya", "item=amulet").code == 0  # a part of its name will do
    charged = cli("do", "charge", "who=freya", "item=amu").out
    assert "charges stopped at its max 3 (2 over)" in charged
    assert _items(cli)[1]["charges"] == {"value": 3, "max": 3}
    assert cli("set", "freya", "inventory.steel.damage=d12").code == 0  # the command line too
    assert _items(cli)[0]["damage"] == "d12"

    unknown = cli("do", "temper", "who=freya", "item=axe")
    assert unknown.code == 1 and "no 'axe' here" in unknown.err
    assert "carrying: Steel sword, Amulet" in unknown.err
    whole = cli("set", "freya", "inventory.amulet=3")
    assert whole.code == 1 and "'amulet' is an item: set one of its keys" in whole.err
    too_big = cli("set", "freya", "inventory.steel.size=9")  # 9 slots and the amulet's 1
    assert too_big.code == 1 and "Freya can't carry that: 10/4 slots" in too_big.err


def test_a_rule_gives_and_takes_items_as_inv_does(cli: Cli) -> None:
    setup(cli)
    assert "dry run: carry-lite.forge" in cli("do", "forge", "who=freya", "--dry-run").out
    assert _items(cli) == []
    forged = cli("do", "forge", "who=freya").out
    assert "pc:freya: + Steel sword (Steel sword: details from carry-lite.steel-sword)" in forged
    assert _items(cli) == [{**SWORD, "tempered": True}]  # its details, and the rule's on top
    brewed = cli("do", "brew", "who=freya").out
    count = _items(cli)[1].get("count", 1)  # a roll of 1d4 doses
    assert f"pc:freya: + Potion of Healing{f' ×{count}' if count > 1 else ''} (" in brewed

    cli("inv", "add", "freya", "Soul gem", "--count", "2")
    assert "pc:freya: - Soul gem" in cli("do", "spend", "who=freya").out
    assert _items(cli)[-1] == {"name": "Soul gem", "size": "petty", "entry": "carry-lite.soul-gem"}
    assert cli("do", "spend", "who=freya").code == 0
    missing = cli("do", "spend", "who=freya")
    assert missing.code == 1 and "no 'soul gem' here" in missing.err
    assert cli("undo").code == 0 and _items(cli)[-1]["name"] == "Soul gem"  # undone whole


def test_the_room_and_the_fields_hooks_are_checked(cli: Cli) -> None:
    setup(cli)
    cli("inv", "add", "freya", "Steel sword", "Amulet")
    refused = cli("do", "haul", "who=freya")  # an anvil: 3 slots more than the 4
    assert refused.code == 1 and "Freya can't carry that: 5/4 slots" in refused.err
    cli("inv", "drop", "freya", "amulet")
    hauled = cli("do", "haul", "who=freya").out  # 4/4: full, so its hook runs its trigger
    assert "inventory is full (4/4): runs overburdened" in hauled
    assert "Freya staggers under the load." in hauled


def test_a_step_says_whose_items_and_how_many(cli: Cli, tmp_path: Path) -> None:
    setup(cli)
    miscounted = cli("do", "miscount", "who=freya")
    assert miscounted.code == 1 and "`count` needs a whole number, not 0" in miscounted.err
    pack = tmp_path / "bad-carry"
    (pack / "rules").mkdir(parents=True)
    (pack / "pack.yaml").write_text("id: bad-carry\nname: B\nkind: system\nversion: 0.1.0\n")
    (pack / "rules" / "r.yaml").write_text(
        "action: loot\nsteps:\n  - {give: Rope}\n  - {take: Rope, to: '@who'}\n"
    )
    out = cli("pack", "validate", str(pack)).out
    assert "a `give` step needs `to:`" in out and "a `take` step needs `from:`" in out
