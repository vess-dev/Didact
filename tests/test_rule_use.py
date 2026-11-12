"""What a character carries, named and used (the `use-lite` fixture): `inv add` finds an entry
as the compendium does (an alias too, and two that share one say so), takes a name with `: ` in
it as a name, and knows a pack's own type that `extends` an item; a rule's `use:` step uses an
item as `inv use` does, and `@{who.inventory.$item.damage}` reads one carried item's key. Of
several items of a name, using one takes the first with a use left."""

import json
from typing import Any

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "use-lite", "--seed", "use").code == 0
    assert cli("campaign", "new", "c", "--seed", "use").code == 0
    assert cli("new", "pc", "Ada", "--set", "hp=4").code == 0


def _items(cli: Cli) -> Any:  # parsed JSON, read freely in tests
    return json.loads(cli("inv", "show", "ada", "--format", "json").out)["items"]


def test_an_item_is_named_as_the_compendium_names_it(cli: Cli) -> None:
    setup(cli)
    lantern = cli("inv", "add", "ada", "Lantern")  # an alias of `Lantern / Torch`
    assert "Lantern / Torch: details from use-lite.lantern-torch" in lantern.out
    assert "Ada gets Lantern / Torch (" in lantern.out  # named as it's kept, not as typed
    shared = cli("inv", "add", "ada", "Pelt")  # the alias of two entries
    assert shared.code == 1
    assert "several entries are called 'Pelt': use-lite.bear-pelt, use-lite.wolf-pelt" in shared.err
    assert cli("inv", "add", "ada", "use-lite.wolf-pelt").code == 0  # pack.id says which
    colon = cli("inv", "add", "ada", "Series 1: Grit")  # a `:` in a name: still a name
    assert "Series 1: Grit: details from use-lite.grit-1" in colon.out
    by_id = cli("inv", "add", "ada", "grit-1")  # a type of the pack's own that extends an item
    assert "Series 1: Grit: details from use-lite.grit-1" in by_id.out
    assert cli("inv", "add", "ada", "Odd: Thing").code == 0  # in no compendium: as written
    names = [i if isinstance(i, str) else i["name"] for i in _items(cli)]
    assert names == ["Lantern / Torch", "Wolf pelt", "Series 1: Grit", "Odd: Thing"]
    assert _items(cli)[2] == {
        "name": "Series 1: Grit",
        "skill": "grit",
        "entry": "use-lite.grit-1",
        "count": 2,
    }
    record = cli("inv", "add", "ada", "item:nothing-here")  # a record's id must be one
    assert record.code == 1 and "nothing called 'item:nothing-here'" in record.err


def test_a_rule_uses_an_item_as_inv_use_does(cli: Cli) -> None:
    setup(cli)
    assert cli("inv", "add", "ada", "Rations", "Oil lamp").code == 0
    eaten = cli("do", "eat", "who=ada").out
    assert "pc:ada uses Rations (Rations: 2 uses left)" in eaten
    assert "Ada eats: 2 left." in eaten
    cli("do", "eat", "who=ada")
    last = cli("do", "eat", "who=ada").out
    assert "Rations is used up and gone" in last and "Ada eats the last of them." in last
    assert cli("do", "eat", "who=ada").code == 1  # none left: as `inv use` says
    lit = cli("do", "light", "who=ada").out  # a d4 usage die: it holds on 3-4
    assert "pc:ada uses Oil lamp (Oil lamp: usage die holds at d4 (rolled 4))" in lit
    assert "The lamp burns on: d4 (4)." in lit
    out = [cli("do", "light", "who=ada").out for _try in range(12)]  # 1-2 and it's out
    assert any("The lamp gutters out (" in said for said in out)
    assert all("Oil lamp" not in str(i) for i in _items(cli))  # used up and gone
    spent = cli("do", "overspend", "who=ada")
    assert spent.code == 1 and "`spend` needs a whole number, not 0" in spent.err


def test_using_a_name_takes_one_with_a_use_left(cli: Cli) -> None:
    setup(cli)
    cli("inv", "add", "ada", "Rations")
    assert cli("set", "ada", "inventory.Rations.uses-=3").code == 0  # empty, and still carried
    cli("inv", "add", "ada", "Rations")  # a full one beside it
    used = cli("inv", "use", "ada", "Rations")
    assert used.code == 0 and "Rations: 2 uses left" in used.out
    assert cli("set", "ada", "inventory.Rations.uses-=1").code == 0  # `set` takes it too
    assert cli("do", "eat", "who=ada").code == 0  # and a rule's `use:`
    uses = [i["uses"] for i in _items(cli)]
    assert uses == [{"value": 0, "max": 3}]  # the full one is used up and gone
    assert cli("inv", "use", "ada", "rat").code == 1  # a part of the name: the same answer


def test_a_rule_reads_one_carried_items_key(cli: Cli) -> None:
    setup(cli)
    cli("inv", "add", "ada", "Iron Sword", "Oil lamp")
    first = cli("do", "temper", "who=ada", "item=Iron Sword").out
    assert "Iron Sword is tempered: d6 → d8." in first  # read before and after the `set`
    assert "iron is tempered: d8 → d10." in cli("do", "temper", "who=ada", "item=iron").out
    assert _items(cli)[0]["damage"] == "d10"
    lamp = cli("do", "temper", "who=ada", "item=Oil lamp").out  # no key: absent, for `default`
    assert "stop: Oil lamp has no damage die to temper." in lamp
    axe = cli("do", "temper", "who=ada", "item=axe").out  # no such item: absent too
    assert "stop: axe has no damage die to temper." in axe


def test_an_items_name_may_hold_a_dot(cli: Cli) -> None:
    setup(cli)
    cli("inv", "add", "ada", ".45 Auto pistol", "12.7mm pistol")
    auto = cli("do", "temper", "who=ada", "item=.45 Auto pistol").out  # read, set and read
    assert ".45 Auto pistol is tempered: d6 → d8." in auto
    heavy = cli("do", "temper", "who=ada", "item=12.7mm pistol").out
    assert "12.7mm pistol is tempered: d8 → d10." in heavy
    by_hand = cli("set", "ada", "inventory.12.7mm.damage=d12")  # a part of its name, dot and all
    assert by_hand.code == 0, by_hand.err
    assert cli("set", "ada", "inventory..45.damage=d10").code == 0
    carried = [(i["name"], i["damage"], sorted(i)) for i in _items(cli)]
    assert carried == [  # each die on its own item, and no stray key beside it
        (".45 Auto pistol", "d10", ["damage", "entry", "name"]),
        ("12.7mm pistol", "d12", ["damage", "entry", "name"]),
    ]
    cli("inv", "add", "ada", "12.7mm SMG")
    either = cli("set", "ada", "inventory.12.7mm.damage=d6")  # two of that calibre: say which
    assert either.code == 1 and "'12.7mm' could be: 12.7mm pistol, 12.7mm SMG" in either.err
    whole = cli("set", "ada", "inventory.12.7mm pistol=d6")  # an item, not one of its keys
    assert whole.code == 1
    for key in ("hp..max=3", "inventory.SMG..damage=d6", "inventory..damage=d6"):
        empty = cli("set", "ada", key)  # an empty part anywhere else is a mistake still
        assert empty.code == 1 and "invalid key" in empty.err, key


def test_set_names_an_item_whole_spaces_and_all(cli: Cli) -> None:
    setup(cli)
    cli("inv", "add", "ada", "Leather jacket", "12.7mm pistol", "Volunteer's Manual: Vol. 2")
    assert cli("set", "ada", "inventory.Leather jacket.armor=2").code == 0
    assert cli("set", "ada", "inventory.12.7mm pistol.damage=d10").code == 0  # a dot in it too
    assert cli("set", "ada", "inventory.Volunteer's Manual: Vol. 2.read=true").code == 0
    items = {i["name"]: i for i in _items(cli)}
    assert items["Leather jacket"]["armor"] == 2 and items["12.7mm pistol"]["damage"] == "d10"
    assert items["Volunteer's Manual: Vol. 2"]["read"] is True
    whole = cli("set", "ada", "inventory.Leather jacket=2")  # the item, not a key of it
    assert whole.code == 1 and "'Leather jacket' is an item: set one of its keys" in whole.err
    loose = cli("set", "ada", "long text = x")  # the first part as strict as ever
    assert loose.code == 1 and "can't read assignment 'long text = x'" in loose.err
    assert "pc:ada: hp-=2" in cli("set", "ada", "hp-=2").out  # `hp`, `-=`, `2`


def test_an_item_list_reads_as_its_names_and_goes_to_a_step_whole(cli: Cli) -> None:
    setup(cli)
    made = cli("char", "new", "--mode", "random")
    assert made.code == 0, made.err
    assert "Laser is off the inventory (1; Laser in it: true)." in made.out  # names, as read
    assert "parts: unread" in made.out  # mappings without names: absent, for `default`
    drafted = json.loads(cli("char", "show", "c1", "--format", "json").out)["draft"]
    assert drafted["entities"][0]["fields"]["inventory"] == ["Rope"]  # the Laser, damage and all
    names = cli("do", "kit-names").out  # a rule reads them the same way
    assert "gear: Rope, Laser; 1 to drop" in names
    parts = cli("do", "kit-parts")
    assert (
        parts.code == 1 and "@kit.parts holds mappings, which an expression can't read" in parts.err
    )
    assert 'hand it to a step as it is: `apply: "@kit.parts"`' in parts.err
