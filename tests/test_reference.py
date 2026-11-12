"""The reference desk: rules lookup, define, explain."""

import json

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")


def test_rules_lookup_links_the_mechanics(cli: Cli) -> None:
    setup(cli)
    found = cli("rules", "lookup", "saves").out
    assert found.startswith("## Saves (mini-system.saves · p. 4 · reference/saves.md)")
    assert "run it: `didact do mini-system.save who=<ref> attr=STR`" in found
    critical = cli("rules", "lookup", "critical", "damage").out
    assert (
        critical.startswith("## Damage and critical damage")
        and "didact do mini-system.attack" in critical
    )
    assert "no rules text about 'dragons'" in cli("rules", "lookup", "dragons").out


def test_define(cli: Cli) -> None:
    setup(cli)
    assert cli("define", "fatigue").out.startswith("**fatigue** (mini-system): Each point takes up")
    alias = cli("define", "HP").out
    assert "**Hit Protection**" in alias and "see: damage" in alias
    typo = cli("define", "fatiuge")
    assert typo.code == 1 and "did you mean fatigue?" in typo.err


def test_explain_anything(cli: Cli) -> None:
    setup(cli)
    assert "- check mini-system.save:" in cli("explain", "save").out
    assert "use: `didact table roll mini-system.weather`" in cli("explain", "weather").out
    assert "template: `didact template pc`" in cli("explain", "pc").out
    assert "use: `didact spawn mini-system.troll`" in cli("explain", "troll").out
    assert "- command `didact roll`:" in cli("explain", "roll").out
    assert "- guide dice:" in cli("explain", "dice").out
    assert "- term fatigue" in cli("explain", "fatigue").out
    missing = cli("explain", "zeppelin")
    assert missing.code == 1 and "nothing called 'zeppelin'" in missing.err


def test_search_ranks_every_source(cli: Cli) -> None:
    setup(cli)
    cli("campaign", "new", "c")
    cli("new", "npc", "Sweeney", "--body", "A champion of the fatigue-less wood.")
    cli("new", "npc", "Mag", "--set", "knowledge=secret", "--body", "Knows the fatigue cure.")
    found = json.loads(cli("search", "fatigue", "--format", "json").out)
    sources = [h["source"] for h in found["hits"]]
    assert sources[0] == "terms" and {"records", "terms"} <= set(sources)
    assert found["hidden"] == 1  # Mag is secret
    assert any(
        h["id"] == "npc:mag"
        for h in json.loads(cli("search", "fatigue", "--gm", "--format", "json").out)["hits"]
    )
    only = cli("search", "sweeney", "--in", "records").out
    assert "[records] Sweeney (npc) · `didact show npc:sweeney`" in only
    docs = cli("search", "undo", "turn", "--in", "docs").out
    assert "[docs] didact undo:" in docs
    assert cli("search", "fatigue", "--in", "nowhere").code == 1
    assert "nothing matches" in cli("search", "xyzzy").out


def test_guide_shows_a_packs_guide(cli: Cli) -> None:
    setup(cli)
    listing = cli("guide").out
    assert "`mini-system`: how to run the mini-system pack" in listing
    assert cli("guide", "mini-system").code == 0
