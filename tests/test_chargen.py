"""Character creation: every creation style, guided and random, prefill, advancement."""

import json

import pytest

from tests.conftest import Cli

SYSTEMS = [
    "mini-system", "ironsworn-lite", "pbta-lite", "blades-lite", "genesys-lite", "yze-lite",
    "daggerheart-lite", "grimwild-lite", "d20-lite", "traveller-lite",
]  # fmt: skip

# One sentence each (the comment), as the LLM would turn it into prefill: what the player
# said is kept exactly as said, and the dice fill in the rest.
DESCRIBED: dict[str, dict[str, object]] = {
    # "Wren, a greedy cutpurse"
    "mini-system": {"name": "Wren", "background": "Cutpurse", "vice": "Greedy"},
    # "Cora, all iron and heart"
    "ironsworn-lite": {"name": "Cora", "stats": "iron=3 heart=2 edge=2 shadow=1 wits=1"},
    # "Snow, a Brainer"
    "pbta-lite": {"name": "Snow", "playbook": "Brainer"},
    # "Rye, a Lurk from Skovlan"
    "blades-lite": {"name": "Rye", "playbook": "Lurk", "heritage": "Skovlan"},
    # "Dessa, a charming aristocrat"
    "genesys-lite": {"name": "Dessa", "archetype": "Aristocrat", "skills": ["Charm", "Knowledge"]},
    # "Hask, strong but slow"
    "yze-lite": {"name": "Hask", "attributes": "5 2"},
    # "Marrow, a nimble ranger"
    "daggerheart-lite": {
        "name": "Marrow",
        "class": "Ranger",
        "traits": "agility=2 strength=0 finesse=1",
    },
    # "Duskin, a druid and a ranger"
    "grimwild-lite": {"name": "Duskin", "paths": ["Druid", "Ranger"]},
    # "Corin, a wizard"
    "d20-lite": {"name": "Corin", "class": "wizard"},
    # "Varra, a merchant"
    "traveller-lite": {"name": "Varra", "career": "Merchant"},
}


def world(cli: Cli, system: str, name: str = "w") -> None:
    assert cli("world", "new", name, "--system", system).code == 0
    cli("campaign", "new", f"{name}-run")


@pytest.mark.parametrize("system", SYSTEMS)
def test_every_style_makes_a_valid_character_at_random(cli: Cli, system: str) -> None:
    world(cli, system)
    made = json.loads(cli("char", "new", "--mode", "random", "--format", "json").out)["draft"]
    assert made["waiting"] is None
    main = made["entities"][0]
    committed = cli("char", "commit", made["id"])
    assert committed.code == 0, committed.err
    ref = committed.out.split("(")[1].split(")")[0]  # "1 record (pc:x)"
    assert cli("char", "check", ref).code == 0
    assert main["name"] in cli("sheet", ref).out


@pytest.mark.parametrize("system", SYSTEMS)
def test_a_character_described_in_one_sentence_keeps_what_was_said(cli: Cli, system: str) -> None:
    world(cli, system)
    prefill = DESCRIBED[system]
    made = json.loads(
        cli(
            "char", "new", "--mode", "random", "--prefill", json.dumps(prefill), "--format", "json"
        ).out
    )["draft"]
    main = made["entities"][0]
    assert main["name"] == prefill["name"]
    for key, value in prefill.items():
        if key in main.get("fields", {}):
            given = main["fields"][key]
            assert given == value or (
                isinstance(value, str) and str(given).casefold() == value.casefold()
            )
    assert cli("char", "commit", made["id"]).code == 0
    assert cli("char", "check", prefill["name"]).code == 0


def test_guided_creation_step_by_step(cli: Cli) -> None:
    world(cli, "mini-system")
    first = json.loads(cli("char", "new", "--format", "json").out)["draft"]
    assert first["id"] == "c1" and first["waiting"] == "background"
    assert "waiting for background (or roll on backgrounds): Aurifex, Bonekeeper, Cutpurse" in (
        cli("char", "show", "c1").out
    )
    assert cli("char", "choose", "c1", "Knight").code == 1  # not an option
    cli("char", "choose", "c1", "Bonekeeper")
    swap = json.loads(cli("char", "show", "c1", "--format", "json").out)["draft"]
    assert swap["waiting"] == "swap" and swap["entities"][0]["fields"]["inventory"] == [
        "Shovel",
        "Lantern",
    ]
    stats = swap["entities"][0]["fields"]
    swapped = json.loads(cli("char", "choose", "c1", "STR WIL", "--format", "json").out)["draft"]
    after = swapped["entities"][0]["fields"]
    assert (after["STR"], after["WIL"]) == (stats["WIL"], stats["STR"])  # no reroll on replay
    named = json.loads(cli("char", "choose", "c1", "Crane", "--format", "json").out)["draft"]
    assert named["waiting"] is None and named["entities"][0]["name"] == "Crane"
    cli("char", "edit", "c1", "character.fields.pronouns=he/him")
    assert cli("char", "commit", "c1").code == 0
    sheet = cli("sheet", "crane").out
    assert "traits: physique" in sheet and "Shovel" in sheet and "pronouns: he/him" in sheet


def test_multi_picks_and_arrays_are_checked(cli: Cli) -> None:
    world(cli, "pbta-lite")
    cli("char", "new")
    cli("char", "choose", "c1", "Skinner")
    wrong = cli("char", "choose", "c1", "Breathtaking")
    assert wrong.code == 1 and "pick 2 different ones" in wrong.err
    assert cli("char", "choose", "c1", "breathtaking, lost").code == 0
    world(cli, "ironsworn-lite", "w2")
    cli("char", "new")
    bad = cli("char", "choose", "c2", "edge=3 heart=3 iron=2 shadow=1 wits=1")
    assert bad.code == 1 and "use each of [3, 2, 2, 1, 1] once" in bad.err


def test_level_ups_run_and_are_logged(cli: Cli) -> None:
    world(cli, "d20-lite")
    made = json.loads(
        cli("char", "new", "--mode", "random", "--prefill", '{"name": "Corin", "class": "fighter"}',
            "--format", "json").out
    )["draft"]  # fmt: skip
    cli("char", "commit", made["id"])

    def level_and_max() -> tuple[int, int]:
        block = json.loads(cli("show", "corin", "--format", "json").out)["mechanics"]["d20-lite"]
        return int(block["level"]), int(block["hp"]["max"])

    level, top = level_and_max()
    up = cli("char", "advance", "corin")
    assert up.code == 0 and "Corin reaches level 2" in up.out
    new_level, new_top = level_and_max()
    assert (level, new_level) == (1, 2) and new_top > top
    assert "d20-lite.level-up" in cli("rolls").out
    assert cli("undo").code == 0
    assert json.loads(cli("show", "corin", "--format", "json").out)["values"]["level"] == 1


def test_char_check_and_import(cli: Cli) -> None:
    world(cli, "mini-system")
    imported = cli(
        "char",
        "import",
        "--data",
        '{"name": "Ansel", "STR": "roll", "DEX": 12, "WIL": 9, "hp": "roll"}',
    )
    assert imported.code == 0 and "rolled STR" in imported.out
    assert cli("char", "check", "ansel").code == 0
    cli("new", "pc", "Blank")
    missing = cli("char", "check", "blank")
    assert missing.code == 1 and "STR: missing (the system rolls it" in missing.out


def test_a_template_starts_from_a_pregen(cli: Cli) -> None:
    world(cli, "mini-system")
    made = json.loads(
        cli("char", "new", "--template", "veteran-ferryman", "--mode", "random",
            "--prefill", '{"WIL": 13}', "--format", "json").out
    )["draft"]  # fmt: skip
    fields = made["entities"][0]["fields"]
    assert made["entities"][0]["name"] == "Gannet"
    assert (fields["STR"], fields["DEX"], fields["WIL"], fields["hp"]) == (12, 9, 13, 4)
    assert fields["inventory"] == ["Shovel", "Lantern"]  # the background's gear still comes
    assert cli("char", "commit", made["id"]).code == 0
