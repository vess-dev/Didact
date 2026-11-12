"""Drafts a step at a time: going back a step (`char back`, `gen back`), choices that say what
each option means, picks of several, and scores bought with a budget."""

import json
from pathlib import Path
from typing import Any

from didact.packs.share import head_of
from didact.tables.model import about, table_from
from tests.conftest import Cli


def _json(cli: Cli, *argv: str) -> Any:
    result = cli(*argv, "--format", "json")
    assert result.code == 0, result.err
    return json.loads(result.out)


def _draft(cli: Cli, draft: str) -> dict[str, Any]:
    reader = "char" if draft.startswith("c") else "gen"
    found: dict[str, Any] = _json(cli, reader, "show", draft)["draft"]
    return found


def _mini(cli: Cli) -> None:
    assert cli("world", "new", "vale", "--system", "mini-system").code == 0
    assert cli("campaign", "new", "run").code == 0


def test_back_takes_a_step_back_and_its_rolls_with_it(cli: Cli) -> None:
    _mini(cli)
    assert cli("char", "new").code == 0
    assert _json(cli, "char", "show", "c1")["back"] is None  # the first question: no step yet
    first = cli("char", "back", "c1")
    assert first.code != 0 and "#c1 is at its first step" in first.err
    assert "didact char discard c1" in first.err
    rolled = cli("char", "roll", "c1", "--one")  # the dice choose the background
    assert rolled.code == 0
    made = _draft(cli, "c1")
    assert made["waiting"] == "swap" and made["rolls"]
    preview = cli("char", "back", "c1", "--dry-run")
    assert "would go back a step" in preview.out and "and marking #r" in preview.out
    assert _draft(cli, "c1")["waiting"] == "swap"  # a preview changes nothing
    back = _json(cli, "char", "back", "c1")
    assert back["draft"]["waiting"] == "background" and back["draft"]["rolls"] == []
    assert all("(undone)" in line for line in cli("rolls").out.splitlines()[1:])
    assert cli("redo").code == 0  # the step again, as it was
    assert _draft(cli, "c1")["waiting"] == "swap"


def test_back_goes_over_edits_and_answers_alike(cli: Cli) -> None:
    _mini(cli)
    assert cli("char", "new").code == 0
    assert cli("char", "choose", "c1", "Cutpurse").code == 0
    assert cli("char", "edit", "c1", "character.fields.pronouns=they/them").code == 0
    back = cli("char", "back", "c1")
    assert back.code == 0 and "character.fields.pronouns = they/them" in back.out
    assert "pronouns" not in _draft(cli, "c1")["entities"][0]["fields"]
    assert cli("char", "back", "c1").code == 0
    assert _draft(cli, "c1")["waiting"] == "background"


def test_back_leaves_another_change_to_the_draft_to_the_history(cli: Cli) -> None:
    _mini(cli)
    assert cli("char", "new").code == 0
    assert cli("save", "start").code == 0
    assert cli("char", "choose", "c1", "Cutpurse").code == 0
    assert cli("rewind", "start").code == 0  # the draft goes back with the campaign's files
    assert _draft(cli, "c1")["waiting"] == "background"
    refused = cli("char", "back", "c1")
    assert refused.code != 0 and "(rewind to start), not one of its own steps" in refused.err
    assert "didact undo --event e" in refused.err
    assert _json(cli, "char", "show", "c1")["back"] is None  # so the page offers no Back


def test_back_works_for_a_generators_draft(cli: Cli) -> None:
    _mini(cli)
    assert cli("gen", "run", "pointcrawl").code == 0
    assert _draft(cli, "g1")["waiting"] == "terrain"
    assert cli("gen", "choose", "g1", "Swamp").code == 0
    assert _draft(cli, "g1")["open"] is None  # ready to commit
    assert cli("gen", "back", "g1").code == 0
    assert _draft(cli, "g1")["waiting"] == "terrain"


def test_choices_say_what_each_option_means(cli: Cli) -> None:
    assert cli("world", "new", "picks", "--system", "picks-lite").code == 0
    assert cli("campaign", "new", "run").code == 0
    begun = _json(cli, "char", "new")["draft"]["open"]
    assert begun["pick"] == 2 and begun["options"] == ["brave", "quiet", "rash", "stubborn"]
    assert "free" not in begun  # the picks are the options' own
    one = cli("char", "choose", "c1", "brave")
    assert one.code != 0 and "pick 2 different ones" in one.err
    scores = _json(cli, "char", "choose", "c1", "brave, quiet")["draft"]["open"]
    assert scores["form"] == {
        "kind": "point_buy",
        "fields": ["might", "wit"],
        "budget": 5,
        "costs": {"0": 0, "1": 1, "2": 2, "3": 4},
    }
    assert "what each score costs: 0 → 0, 1 → 1, 2 → 2, 3 → 4" in cli("char", "show", "c1").out
    gift = _json(cli, "char", "choose", "c1", "3 1")["draft"]["open"]
    assert gift["about"] == {
        "Ember": "Grants: warmth, light.",
        "Feather": "Grants: a soft fall.",
        "Lantern": "A light that never goes out.",  # the entry's own note
    }
    knack = _json(cli, "char", "choose", "c1", "Ember")["draft"]["open"]
    assert knack["labels"] == {"quick-hands": "Quick Hands", "keen-eye": "Keen Eye"}
    assert knack["about"] == {
        "quick-hands": "Take +1 on anything done with nimble fingers.",
        "keen-eye": "You notice what others miss: ask the GM one question about a room.",
    }
    shown = cli("char", "show", "c1").out
    assert "  - quick-hands (Quick Hands): Take +1 on anything done with nimble fingers." in shown
    assert cli("char", "choose", "c1", "keen-eye").code == 0
    fields = _draft(cli, "c1")["entities"][0]["fields"]
    assert (fields["traits"], fields["might"], fields["gift"], fields["knack"]) == (
        ["brave", "quiet"],
        3,
        "Ember",
        "keen-eye",
    )


def test_a_table_says_what_an_entry_means() -> None:
    table = table_from(
        "p.gifts",
        "p",
        {
            "table": "gifts",
            "about": "Grants: {grants}; {text} ({missing}).",
            "entries": [
                {"text": "Ember", "data": {"grants": ["warmth", "light"]}},
                {"text": "Lantern", "note": "Never goes out.", "data": {"grants": ["light"]}},
            ],
        },
    )
    ember, lantern = table.entries
    assert about(table, ember) == "Grants: warmth, light; Ember ()."
    assert about(table, lantern) == "Never goes out."
    plain = table_from("p.t", "p", {"table": "t", "entries": ["a"]})
    assert about(plain, plain.entries[0]) == ""


def test_a_manifest_says_what_its_pack_is(tmp_path: Path) -> None:
    assert head_of('id: x\nkind: system\nname: "X Game"\ndescription: A short one.\n') == {
        "kind": "system",
        "name": "X Game",
        "description": "A short one.",
    }
    folded = "kind: system\ndescription: >-\n  Two lines\n  that fold.\nname: Y\n"
    assert head_of(folded) == {"kind": "system", "description": "Two lines that fold.", "name": "Y"}


def test_the_data_a_form_needs_to_offer_choices(cli: Cli) -> None:
    _mini(cli)
    units = _json(cli, "time", "show")["units"]
    assert list(units)[:4] == ["second", "round", "minute", "turn"] and units["turn"] == 600
    assert cli("time", "advance", "2", "watch").code == 0  # a number and a unit, as a form sends
    odds = _json(cli, "oracle", "show")
    assert odds["odds"] == ["very-unlikely", "unlikely", "even", "likely", "very-likely"]
    packs = {p["id"]: p for p in _json(cli, "pack", "list")["packs"]}
    assert packs["mini-system"]["description"] == "A tiny system to test sheets."
    tables = {t["id"]: t for t in _json(cli, "table", "list")["tables"]}
    assert "description" in tables["mini-system.terrain"]
