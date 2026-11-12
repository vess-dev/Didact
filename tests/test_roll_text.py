"""A rule rolls dice it holds as text with `{…}`, filled in before the roll is read, as in any
text (`roll: "{@d} + 1"`, `roll: "{@{who.inventory.$item.damage}}"`): the log shows the dice
rolled, and a value that isn't dice is refused, naming it. `roll: "@d"` of such text, which
rolls nothing, is refused with the way to roll it, and a set of rolls stays one (the `roll-lite`
and `use-lite` fixtures)."""

from tests.conftest import Cli


def test_a_roll_fills_in_dice_held_as_text(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "roll-lite", "--seed", "roll").code == 0
    assert cli("campaign", "new", "c", "--seed", "roll").code == 0
    hit = cli("do", "hit").out
    assert "1d8 + 2 → [" in hit and "The hit deals " in hit  # the log shows the dice
    assert "2d6 + 1 + 2 → [" in cli("do", "hit", "die=2d6+1").out
    word = cli("do", "hit", "die=eight")
    assert word.code == 1 and "roll-lite.hit: `{@d}` is 'eight', not dice" in word.err
    assert "give it a die or a number to roll" in word.err
    sets = cli("do", "best").out  # a set of rolls, one of them filled in, and a set of one
    assert "{1d8, 1d6}kh1 → {" in sets and "{2d6} → {" in sets
    bare = cli("do", "bare")
    assert bare.code == 1 and "`@die` is the text 'd8', which rolls nothing" in bare.err
    assert "put it in braces: `{@die}`" in bare.err


def test_a_rule_rolls_a_carried_weapons_own_die(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "use-lite", "--seed", "use").code == 0
    assert cli("campaign", "new", "c", "--seed", "use").code == 0
    assert cli("new", "pc", "Ada", "--set", "hp=4").code == 0
    assert cli("inv", "add", "ada", "Iron Sword", "Oil lamp").code == 0
    struck = cli("do", "strike", "who=ada", "item=Iron Sword").out
    assert "1d6 + 1 → [" in struck and "Iron Sword deals " in struck
    assert cli("set", "ada", "inventory.Iron Sword.damage=d10").code == 0  # the die it has now
    assert "1d10 + 1 → [" in cli("do", "strike", "who=ada", "item=Iron Sword").out
    lamp = cli("do", "strike", "who=ada", "item=Oil lamp")  # no damage die: absent, and said
    assert lamp.code == 1 and "unknown variable @who.inventory.Oil lamp.damage" in lamp.err
    assert "give it a fallback, e.g. `{default(@{who.inventory.$item.damage}, 'd4')}`" in lamp.err
