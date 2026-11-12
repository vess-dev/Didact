"""A quoted phrase that finds nothing in the rules text is tried as its words (`rules lookup "act
3 clocks"`), saying so; and a near spelling counts only for a word nothing has as typed,
so `scroll` finds the scrolls, not every `roll` (the `lookup-lite` fixture)."""

import json

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "lookup-lite").code == 0


def test_a_quoted_phrase_is_tried_as_its_words(cli: Cli) -> None:
    setup(cli)
    quoted = cli("rules", "lookup", "act 3 clocks").out
    assert "no rules text about 'act 3 clocks' as written; these have its words:" in quoted
    assert "## Act 3: Clocks (lookup-lite.act-3-clocks" in quoted
    plain = cli("rules", "lookup", "act", "3", "clocks").out
    assert "as written" not in plain and "## Act 3: Clocks" in plain
    phrase = cli("rules", "lookup", "siege clock").out  # found as a phrase: no note
    assert "as written" not in phrase and "## Act 3: Clocks" in phrase
    data = json.loads(cli("rules", "lookup", "act 3 clocks", "--format", "json").out)
    assert data["words"] == ["act", "3", "clocks"]
    found = cli("compendium", "find", "plate x-01").out  # its own search: a phrase is a phrase
    assert "nothing in the compendium matches" in found
    none = cli("rules", "lookup", "dragon hoard").out  # nor as words: as before
    assert "no rules text about 'dragon hoard'" in none


def test_a_near_spelling_is_for_a_word_nothing_has(cli: Cli) -> None:
    setup(cli)
    typed = cli("search", "--in", "terms", "scroll").out
    assert "potion" in typed and "reaction" not in typed and "armor" not in typed
    both = cli("search", "--in", "terms", "--in", "compendium", "scroll").out
    assert "Scroll case (item)" in both and "save" not in both
    typo = cli("search", "--in", "terms", "potoin").out  # a typo: its near spelling counts
    assert "potion" in typo
    rules = cli("rules", "lookup", "clocsk").out  # the same in the rules text
    assert "## Act 3: Clocks" in rules
