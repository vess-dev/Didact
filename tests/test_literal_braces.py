"""`{…}` in the text a rule, a generator or a table fills in is an expression (or a table, or a
column, or an entry's data); `{{` and `}}` write a brace itself, so a prompt can show a command
with a JSON prefill (the `braces-lite` fixture)."""

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "braces-lite", "--seed", "braces").code == 0
    assert cli("campaign", "new", "c", "--seed", "braces").code == 0
    assert cli("new", "pc", "Freya").code == 0


def test_a_rule_and_a_generator_write_braces_beside_what_they_fill_in(cli: Cli) -> None:
    setup(cli)
    bragged = cli("do", "brag", "who=freya")
    assert bragged.code == 0, bragged.err
    assert '--prefill \'{"quest": "The Lost Key"}\'`.' in bragged.out
    assert "In braces: {Freya}; a lone } stays." in bragged.out  # `let` text too
    hunted = cli("gen", "run", "braces-lite.hunt", "--auto")  # its table's text has one too
    assert hunted.code == 0, hunted.err
    assert '\'{"quarry": "A stag {the white one}, 1 of them"}\' --auto`.' in hunted.out


def test_a_tables_text_its_reading_and_what_an_entry_means(cli: Cli) -> None:
    setup(cli)
    rolled = cli("table", "roll", "braces-lite.stags").out
    assert "A stag {the white one}, 1 of them" in rolled  # `{1d1}` still rolls
    assert "Ash {and} Oak" in cli("table", "roll", "braces-lite.pairs").out  # `read:`
    asked = cli("gen", "run", "braces-lite.pick").out  # the choice says what each one costs
    assert "Costs 2 {coins}." in asked and "Costs 3 {coins}." in asked  # `about:`
