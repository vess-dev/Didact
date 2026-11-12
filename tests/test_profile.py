"""Session zero and the campaign profile."""

import json

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    assert "next: `didact session zero`" in cli("campaign", "new", "run").out


def test_session_zero_saves_a_profile_the_brief_carries(cli: Cli) -> None:
    setup(cli)
    assert "Profile: not set yet (`didact session zero`)" in cli("brief").out
    zero = cli("session", "zero").out
    assert "- role: Should I be the full GM" in zero and "(gm / co-gm / oracle / scribe)" in zero
    saved = cli(
        "campaign", "profile", "role=co-gm", "lines+=harm to children", "veils+=torture",
        "tone=grim, hopeful", "dice=physical", "narration.person=second",
    )  # fmt: skip
    assert saved.code == 0
    line = cli("brief").out.splitlines()[1]
    assert line == (
        "Profile: role co-gm · tone grim, hopeful · lines: harm to children · veils: torture"
        " · invention balanced · narration second · dice physical (ask, then --got)"
    )
    assert "- role: Should I be" in cli("session", "zero").out
    assert "→ co-gm" in cli("session", "zero").out
    cli("campaign", "profile", "lines+=spiders, drowning", "lines-=harm to children")
    data = json.loads(cli("campaign", "profile", "--format", "json").out)["profile"]
    assert data["lines"] == ["spiders", "drowning"] and data["narration"] == {"person": "second"}
    bad = cli("campaign", "profile", "role=boss")
    assert bad.code == 1 and "role is one of: gm, co-gm, oracle, scribe" in bad.err
    assert cli("campaign", "profile", "mood=sad").code == 1  # not a question here
    assert "physical dice: ask the player, then pass --got" in cli("roll", "d20").out
    assert "physical dice" not in cli("roll", "d20", "--got", "7").out
