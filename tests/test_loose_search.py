"""Loose search: a word also finds its near spellings (when it isn't there as typed) and its
synonyms, one step away in the thesaurus (a tiny WordNet here). Exact matches rank first, then
near spellings, then synonyms; player searches still hide what only a secret matched."""

import json
from typing import Any

import pytest

from didact.core import words
from didact.core.words import Matcher
from tests.conftest import Cli
from tests.test_web import Browser, web  # noqa: F401  (the fixture)


def _json(cli: Cli, *argv: str) -> Any:
    return json.loads(cli(*argv, "--format", "json").out)


@pytest.mark.usefixtures("thesaurus")
def test_synonyms_are_one_step_away() -> None:
    assert "blade" in words.synonyms("sword") and "sword" in words.synonyms("blades")
    sentry = words.synonyms("sentry")  # guard has two senses: only the one they share counts
    assert "guard" in sentry and "lookout" in sentry
    assert "protect" not in sentry  # a synonym of guard, two steps from sentry


def test_without_a_thesaurus_there_are_no_synonyms(cli: Cli) -> None:
    assert words.synonyms("sword") == []
    assert "no thesaurus yet" in cli("setup", "thesaurus", "--check").out


def test_near_spellings_have_a_cutoff() -> None:
    assert words.near("fatiuge", ["fatigue", "fortune"]) == ["fatigue"]
    assert words.near("goblni", ["goblin"]) == ["goblin"]
    assert words.near("trol", ["troll"]) == ["troll"]
    assert words.near("dragon", ["wagon"]) == []  # too far
    assert words.near("hp", ["hps"]) == ["hps"]  # short words too


@pytest.mark.usefixtures("thesaurus")
def test_a_matcher_weighs_exact_over_near_over_synonym() -> None:
    match = Matcher(["sword"])
    assert match.weight("sword", "a sword") == (words.EXACT, "sword")
    assert match.weight("sword", "a swords") == (words.EXACT, "sword")
    assert match.weight("sword", "a swrod and a blade") == (words.NEAR, "swrod")
    assert match.weight("sword", "a blade") == (words.SYNONYM, "blade")
    assert match.weight("sword", "a spoon") == (0.0, "")
    assert words.EXACT > words.NEAR > words.SYNONYM
    assert Matcher(["blade", "sentries"]).found("A sword for the lookout")


@pytest.mark.usefixtures("thesaurus")
def test_search_finds_typos_and_synonyms(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "c")
    cli("new", "npc", "Sweeney", "--body", "Carries an old blade.")
    cli("new", "npc", "Tom", "--body", "Sells a sword at the market.")
    found = _json(cli, "search", "sword", "--in", "records")["hits"]
    assert [h["id"] for h in found] == ["npc:tom", "npc:sweeney"]  # the exact word first
    typo = _json(cli, "search", "fatiuge", "--in", "terms")["hits"]
    assert typo and typo[0]["id"] == "mini-system.fatigue"
    assert "npc:sweeney" in cli("find", "swenney").out  # a near spelling of a name
    assert "npc:sweeney" in cli("find", "steel").out  # a synonym in the text
    assert "nothing matches" in cli("search", "xyzzy").out


@pytest.mark.usefixtures("thesaurus")
def test_a_loose_match_in_a_secret_stays_hidden(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "c")
    cli("new", "npc", "Mag", "--body", "A healer.\n\n## Secrets\n\nHides a cursed blade.")
    player = _json(cli, "search", "sword", "--in", "records")
    assert player["hits"] == [] and player["hidden"] == 1
    assert "npc:mag" not in cli("find", "swrod").out
    gm = _json(cli, "search", "sword", "--in", "records", "--gm")["hits"]
    assert [h["id"] for h in gm] == ["npc:mag"]


def test_the_search_boxes_search_as_you_type(web: Browser) -> None:  # noqa: F811
    """The pages carry what app.js needs: a box that names where results go, and that place
    (empty on the Reference page, the results on the search page)."""
    for path in ("/reference", "/search"):
        page = web.get(path).body
        assert 'data-live="search-results"' in page and 'id="search-results"' in page, path
    found = web.get("/search?q=fatiuge").body
    results = found.split('id="search-results"', 1)[1]
    assert "fatigue" in results.casefold()  # a near spelling, found
