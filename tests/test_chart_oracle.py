"""A chart oracle (fixture `oracle-lite`): a chart looked up before the roll, a state that
rules change, weighted lists rolled by sections, meaning pairs."""

import json

import pytest

from didact.tables import lists
from tests.conftest import Cli

CHART = "oracle:oracle-lite-chart"


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system", "--seed", "chart")
    cli("pack", "enable", "oracle-lite")
    cli("campaign", "new", "run", "--seed", "chart")


def test_the_chart_is_read_before_the_roll(cli: Cli) -> None:
    setup(cli)
    answers = set()
    for _ in range(12):
        asked = json.loads(cli("ask", "Is it?", "--odds", "likely", "--format", "json").out)
        assert asked["oracle"] == "oracle-lite.chart"
        answers.add(asked["answer"])
    assert answers <= {"Exceptional Yes", "Yes", "No", "Exceptional No"} and "Yes" in answers
    shown = cli("ask", "Again?", "--odds", "unlikely").out
    assert "odds-chart: 10 / 50 / 91" in shown  # chaos 2 falls in the 2-3 column
    assert cli("set", CHART, "method=check").code == 0
    checked = cli("ask", "By the check?", "--odds", "likely").out
    assert "check-odds: 2" in checked and "+ @odds_mod.value(2) =" in checked
    as_rule = cli("ask", "As a rule?", "--with", "as_rule=true", "--with", "odds=likely").out
    assert "→" in as_rule
    assert cli("ask", "Bad?", "--with", "nope=1").code == 1


def test_rules_change_the_state_and_get_it_by_themselves(cli: Cli) -> None:
    setup(cli)
    cli("ask", "Start it?")
    calmed = cli("do", "calm")  # no oracle= needed: the pack's oracle state comes in
    assert calmed.code == 0 and "Chaos 1." in calmed.out
    assert "Chaos 1." in cli("do", "calm").out  # it stays within its floor
    npc = cli("do", "answer-for", "who=Sweeney", "deed=flee")
    assert npc.code == 0 and "Sweeney: " in npc.out  # "$who $deed" text, a loose lookup
    assert any(
        line in npc.out
        for line in ("It happens.", "It happens, more so.", "Something else", "The opposite")
    )


def test_lists_weight_roll_and_drop(cli: Cli) -> None:
    setup(cli)
    assert cli("lists", "add", "threads", "Find", "the", "well").code == 0
    assert "(2 lines)" in cli("lists", "add", "characters", "Sweeney", "--times", "2").out
    assert cli("lists", "add", "characters", "Sweeney", "--times", "2").code == 1  # at most 3
    cli("lists", "add", "characters", "The Hollow King")
    shown = cli("lists", "show").out
    assert (
        "characters: 3 lines\n  1. Sweeney (×2)\n  2. Sweeney (×2)\n  3. The Hollow King" in shown
    )
    rolled = json.loads(cli("lists", "roll", "characters", "--format", "json").out)
    assert rolled["entry"] in ("Sweeney", "The Hollow King", None)
    assert rolled["choose"] == (rolled["entry"] is None)  # a blank line past line 3
    assert "took 2 lines" in cli("lists", "drop", "characters", "Sweeney", "--all").out
    assert cli("lists", "drop", "characters", "Nobody").code == 1
    empty = json.loads(cli("lists", "roll", "threads-wood", "--format", "json").out)
    assert empty["entry"] is None and empty["choose"] is False  # nothing listed there


def test_meaning_pairs_and_roll_twice_tables(cli: Cli) -> None:
    setup(cli)
    words = cli("meaning").out.splitlines()[0]
    verb, noun = words.split("meaning: ")[1].split(" · ")
    assert verb in ("Seek", "Break", "Hide", "Wake") and noun in ("Gate", "Oath", "Crown", "Storm")
    twice = cli("table", "roll", "twice").out
    assert "first: " in twice and "second: " in twice  # one list, rolled once per column


@pytest.mark.parametrize(
    ("count", "dice"),
    [
        (0, []),
        (3, ["d10"]),
        (5, ["d10"]),
        (6, ["d4", "d10"]),
        (12, ["d6", "d10"]),
        (25, ["d10", "d10"]),
    ],
)
def test_list_dice_by_sections(count: int, dice: list[str]) -> None:
    assert lists.dice_for(count, "sections") == dice


def test_list_picks_read_sections_and_lines() -> None:
    names = [f"n{i}" for i in range(1, 8)]  # two sections: lines 1-5 and 6-7
    assert lists.pick(names, "sections", [1, 1]).entry == "n1"  # section 1, line 1
    assert lists.pick(names, "sections", [4, 3]).entry == "n7"  # section 2, line 2
    blank = lists.pick(names, "sections", [3, 9])  # section 2, line 5: past the end
    assert blank.entry is None and blank.choose and blank.line == 10
    assert lists.pick(["a", "b"], "uniform", [2]).entry == "b"
    assert lists.pick([], "sections", []).entry is None
    added = lists.add(["a"], "b", 2, 3, 25)
    assert added == ["a", "b", "b"] and lists.drop(added, "B", every=False) == (["a", "b"], 1)
    with pytest.raises(ValueError, match="the most is 3"):
        lists.add(added, "b", 2, 3, 25)


def test_a_dry_run_logs_no_table_rolls(cli: Cli) -> None:
    setup(cli)
    cli("ask", "Start it?")
    before = cli("rolls", "--format", "json").out
    dry = cli("do", "event", "--dry-run")
    assert dry.code == 0 and "Event: " in dry.out
    assert cli("rolls", "--format", "json").out == before
