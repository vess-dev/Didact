"""A value prefilled for a choice among known options is checked where it is used: it is the
option it names as written, in another letter case, by its entry's `id`, or (a table's) by a
roll that lands on it, and brings that entry's data as a roll would; a near miss is refused,
naming the nearest, and anything else is an answer of one's own, kept as given (the
`follow-lite` and `mini-system` fixtures)."""

import json
from typing import Any

from tests.conftest import Cli


def setup(cli: Cli, system: str = "follow-lite") -> None:
    assert cli("world", "new", system, "--system", system, "--seed", "prefill").code == 0
    assert cli("campaign", "new", f"{system}-run", "--seed", "prefill").code == 0


def _draft(cli: Cli, *args: str) -> Any:  # parsed JSON, read freely in tests
    out = cli(*args, "--format", "json")
    assert out.code == 0, out.err
    return json.loads(out.out)["draft"]


def test_a_prefilled_table_step_is_the_entry_it_names(cli: Cli) -> None:
    setup(cli)
    for given, entry, dwellers in (
        (3, "Spirits", "wisp, shade"),  # a roll that lands on it
        ("2", "Beasts", "wolf, bear"),
        ("beasts", "Beasts", "wolf, bear"),  # its text, in another case
        ("restless-dead", "Spirits", "wisp, shade"),  # its data's `id`
    ):
        ran = cli("gen", "run", "follow-lite.lair", "--prefill", json.dumps({"group": given}))
        assert ran.code == 0, ran.err
        assert (
            f"group: {entry} (given)" in ran.out and f"waiting for dweller: {dwellers}" in ran.out
        )
    # an entry of the table it rolls instead, with that entry's data and the one it went by
    relic = _draft(cli, "gen", "run", "follow-lite.hoard", "--prefill", '{"relic": "ring of ash"}')
    found = relic["entities"][0]
    assert (found["name"], found["fields"]["found"]) == ("Ring of Ash", "deep")


def test_a_prefilled_choice_and_traits_are_the_options_they_name(cli: Cli) -> None:
    setup(cli, "mini-system")
    prefill = {"background": "bonekeeper", "vice": 2, "physique": "wiry", "name": "Crane"}
    hero = _draft(cli, "char", "new", "--mode", "random", "--prefill", json.dumps(prefill))
    fields = hero["entities"][0]["fields"]
    assert fields["background"] == "Bonekeeper" and fields["inventory"] == ["Shovel", "Lantern"]
    assert fields["traits"] == {"physique": "Wiry", "vice": "Lazy"}
    site = _draft(cli, "gen", "run", "delve", "--prefill", '{"site": "crypt"}', "--auto")
    assert site["entities"][0]["name"] == "The Crypt Below"


def test_a_prefill_that_names_no_option_fails_where_it_is_used(cli: Cli) -> None:
    setup(cli)
    near = cli("gen", "run", "follow-lite.lair", "--prefill", '{"group": "Beastz"}')
    assert near.code == 1 and "prefilled group 'Beastz' isn't one of its options" in near.err
    assert "did you mean Beasts?" in near.err
    past = cli("gen", "run", "follow-lite.lair", "--prefill", '{"group": 7}')
    assert past.code == 1 and "a roll from 1 to 4" in past.err
    rolls_on = cli("gen", "run", "follow-lite.hoard", "--prefill", '{"relic": 1}')
    assert rolls_on.code == 1 and "prefilled relic '1' rolls on rings" in rolls_on.err
    assert cli("gen", "drafts").out.strip() == "no drafts"  # nothing was drafted
    setup(cli, "mini-system")
    typo = cli("gen", "run", "delve", "--prefill", '{"site": "Crpyt"}')
    assert typo.code == 1 and "did you mean Crypt?" in typo.err


def test_free_values_and_answers_of_ones_own_stay_as_given(cli: Cli) -> None:
    setup(cli, "mini-system")
    prefill = {"site": "Barrow", "site_name": "beasts", "rooms": 4, "offering": "hide"}
    done = _draft(cli, "gen", "run", "delve", "--prefill", json.dumps(prefill), "--auto")
    assert done["entities"][0]["name"] == "beasts"  # a `let`: any text
    assert ["site", "Barrow"] in done["trail"]  # far from every option: one of its own
    named = _draft(cli, "char", "new", "--mode", "random", "--prefill", '{"name": "Bonekeeper"}')
    assert named["entities"][0]["name"] == "Bonekeeper"  # a name is any name
