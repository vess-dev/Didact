"""Oracles: ask, meaning, interpret; the core yes/no oracle; state; pack lore."""

import json

from tests.conftest import Cli

ANSWERS = {"Yes, and…", "Yes", "Yes, but…", "No, but…", "No", "No, and…"}


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")


def test_the_core_oracle_answers_and_logs(cli: Cli) -> None:
    setup(cli)
    cli("session", "start")
    asked = cli("ask", "Is", "the", "door", "locked?", "--odds", "likely", "--format", "json")
    data = json.loads(asked.out)
    assert data["oracle"] == "core.yes-no" and data["number"] == 1
    assert data["answer"] in ANSWERS and data["odds"] == "likely" and len(data["rolls"]) >= 2
    shown = cli("ask", "Is anyone home?").out
    assert shown.startswith("#o2 ? Is anyone home? (even) → ")
    assert "interpret it: `didact interpret o2 '…'`" in shown
    assert cli("ask", "Is it?", "--odds", "maybe").code == 1
    words = cli("meaning").out
    assert words.startswith("#o3 meaning: ") and " · " in words.splitlines()[0]
    kept = cli("interpret", "o1", "The", "lock", "is", "rusted.")
    assert kept.code == 0 and "#o1" in kept.out
    history = cli("oracle", "history").out
    assert "- #o1 ? Is the door locked? (likely) → " in history
    assert "  → The lock is rusted." in history and "- #o3 meaning: " in history
    journal = cli("session", "show").out
    assert (
        "? Is the door locked? (likely) → " in journal and "-> The lock is rusted. (#o1)" in journal
    )
    assert cli("interpret", "o9", "nope").code == 1
    assert "— meaning: core.yes-no" in cli("rolls").out  # meaning rolls are logged rolls


def test_every_answer_is_reachable_and_twists_bring_meaning(cli: Cli) -> None:
    setup(cli)
    seen: set[str] = set()
    twisted = False
    for _ in range(80):
        data = json.loads(cli("ask", "Does it happen?", "--format", "json").out)
        seen.add(data["answer"])
        if "twist" in data["flags"]:
            twisted = True
    assert seen == ANSWERS and twisted


def test_undo_keeps_numbers_moving(cli: Cli) -> None:
    setup(cli)
    cli("ask", "One?")
    cli("undo")
    assert cli("ask", "Two?").out.startswith("#o2 ")  # numbers never repeat


def test_oracles_with_state_keep_it_per_campaign(cli: Cli, home: object) -> None:
    from pathlib import Path

    assert isinstance(home, Path)
    setup(cli)
    pack = home / "systems" / "mini-system" / "homebrew"
    (pack / "oracles").mkdir(parents=True)
    (pack / "rules").mkdir(parents=True)
    (pack / "oracles" / "fate.yaml").write_text(
        "oracle: fate\ntitle: Fate\nask: fate\nstate: {chaos: {start: 5, min: 1, max: 9}}\n"
    )
    (pack / "rules" / "fate.yaml").write_text(
        "check: fate\nparams: {question: {kind: text, optional: true}, oracle: ref}\n"
        "roll: d10\nsuccess: '@roll <= @oracle.chaos'\n"
        "on: {success: [{set: oracle.chaos, op: '+=', value: 1}]}\n"
    )
    assert "- mini-system.fate: Fate" in cli("oracle", "list").out
    before = cli("oracle", "show").out
    assert "state: not started yet" in before  # a pack oracle is preferred over core's
    for _ in range(6):
        cli("ask", "Does chaos grow?")
    after = cli("oracle", "show").out
    chaos = int(after.split("state: chaos ")[1].split()[0])
    assert chaos >= 5
    assert cli("ask", "x", "--oracle", "core.yes-no").code == 0


def test_pack_lore_comes_up(cli: Cli) -> None:
    setup(cli)
    found = cli("lore", "scan", "I light a torch").out
    assert '[lore:torch-uses] (rule-reminder; key "torch") Torches burn for 3 uses' in found
    cli("lore", "add", "Our torches are longer.", "--keys", "torch", "--name", "torch-uses")
    shadowed = json.loads(cli("lore", "scan", "a torch", "--format", "json").out)["hits"]
    assert [h["text"] for h in shadowed] == ["Our torches are longer."]
