"""Time and calendars, trackers and timers, reminders, quests, accomplishments."""

import json
import os
from pathlib import Path

import pytest

from didact.core.errors import InvalidError
from didact.core.output import JSON
from didact.services.clock import calendar_from
from tests.conftest import FIXTURE_PACKS, Cli

VALD: dict[str, JSON] = {
    "hours": 24,
    "week": ["Moon", "Tide", "Root", "Ash", "Hearth", "Crown"],
    "months": [{"name": "Frost", "days": 24}, {"name": "Bright", "days": 24}],
    "start": {"year": 7728, "month": 2, "day": 10},
}


def test_calendars() -> None:
    plain = calendar_from({}, {})
    assert (
        plain.parse("2 watches") == 8 * 3600
        and plain.parse("turn") == 600
        and plain.parse("3 rounds") == 18
    )
    assert plain.describe(26 * 3600) == "day 2, 02:00"
    vale = calendar_from({"watches": ["morning", "afternoon", "night"]}, {"calendar": VALD})
    assert vale.parse("1 watch") == 8 * 3600
    assert vale.describe(14 * 3600) == "day 1, 14:00 (afternoon watch) · Moon, 10 Bright 7728"
    assert vale.describe(20 * 86400).endswith("Root, 6 Frost 7729")  # rolls past the year's end
    known = vale.values(20 * 86400)
    assert (known["time.month_name"], known["time.day_of_month"], known["time.year"]) == (
        "Frost",
        6,
        7729,
    )
    assert "time.month" not in plain.values(0)  # no months, nothing to read
    with pytest.raises(InvalidError, match="unknown unit 'fortnight'"):
        vale.parse("1 fortnight")


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("session", "start")


def test_time_advance_fires_timers_reminders_and_triggers(cli: Cli) -> None:
    setup(cli)
    assert cli("time", "show").out.strip() == "it's day 1, 00:00 (morning watch)"
    cli(
        "track",
        "new",
        "Torch",
        "--kind",
        "timer",
        "--lasts",
        "6 turns",
        "--note",
        "the torch gutters out",
    )
    cli("remind", "Eat a ration", "--every", "1 day")
    hour = cli("time", "advance", "1", "hour")
    assert "note: timer: Torch ran out: the torch gutters out" in hour.out
    assert "trigger" not in hour.out  # less than a day: the trigger's `when` is false
    day = cli("time", "advance", "1", "day")
    assert "note: reminder: Eat a ration" in day.out
    assert "note: trigger mini-system.new-day: A new day dawns: check rations." in day.out
    assert "day 2, 01:00" in cli("time", "show").out


def test_trackers_and_quests(cli: Cli) -> None:
    setup(cli)
    made = cli("track", "new", "Spider infestation", "--kind", "clock", "--size", "6")
    assert "tracking Spider infestation 0/6" in made.out
    assert cli("track", "tick", "spider-infestation", "--by", "5").out.startswith(
        "✔ Spider infestation 5/6"
    )
    full = cli("track", "tick", "spider-infestation", "--by", "3")
    assert "note: value is full (6/6)" in full.out
    cli("track", "new", "Doom", "--kind", "counter")
    assert "Doom 0" in cli("track", "list").out
    cli(
        "quest",
        "new",
        "Purify the forest",
        "--goal",
        "Free the spirit",
        "--milestone",
        "Find the grave",
        "--milestone",
        "Burn the rot",
    )
    step = cli("quest", "done", "purify-the-forest", "--milestone", "1")
    assert "(1/2 milestones)" in step.out
    cli("quest", "new", "Find the hut", "--type", "thread")
    listing = cli("quest", "list").out
    assert (
        "- quest Purify the forest (1/2 milestones)" in listing
        and "- thread Find the hut" in listing
    )
    cli("quest", "done", "find-the-hut")
    assert "Find the hut" not in cli("quest", "list").out
    brief = cli("brief").out
    assert (
        "Open: quest Purify the forest" in brief
        and "Trackers: Doom 0 · Spider infestation 6/6" in brief
    )


def test_accomplishments(cli: Cli) -> None:
    setup(cli)
    cli("new", "pc", "Freya")
    done = cli("accomplish", "Freed the spirit of the Wood", "--pc", "freya", "--xp", "1")
    assert done.code == 0 and "accomplished: Freed the spirit" in done.out
    assert (
        "accomplishment:freed-the-spirit-of-the-wood" in cli("find", "--type", "accomplishment").out
    )


def test_faction_turns_roll_and_tick_their_clocks(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "faction", "The Order", "--set", "agenda=Hold the ford")
    cli("new", "faction", "Bog Cult", "--set", "knowledge=secret")
    cli("new", "faction", "Old Guild", "--set", "status=gone")
    cli("track", "new", "The Order seizes the ford", "--size", "2", "--for", "faction:the-order")
    turns = [cli("faction", "turn").out for _ in range(6)]
    assert all("## The Order [faction:the-order]" in t for t in turns)
    assert all("Bog Cult" not in t and "1 secret faction acted" in t for t in turns)
    assert all("Old Guild" not in t for t in turns)
    assert all("narrate what The Order did (agenda: Hold the ford)" in t for t in turns)
    moved = [t for t in turns if "advances: The Order seizes the ford" in t]
    held = [t for t in turns if "holds: no progress" in t]
    assert len(moved) + len(held) == 6
    if len(moved) >= 2:
        assert any("filled: The Order seizes the ford" in t for t in moved)
    assert "## Bog Cult" in cli("faction", "turn", "--gm").out
    assert "— faction turn: The Order" in cli("rolls").out


def test_diminishing_pools_drop_and_link_phases(cli: Cli) -> None:
    cli("world", "new", "wild", "--seed", "pools")
    cli("campaign", "new", "c", "--seed", "pools")
    made = cli("track", "new", "Poisoned", "--kind", "pool", "--size", "4", "--note", "harm")
    assert made.code == 0 and "Poisoned 4d" in made.out
    left, rolls = 4, 0
    while left and rolls < 30:
        rolled = json.loads(cli("track", "roll", "poisoned", "--format", "json").out)
        assert rolled["left"] == left - sum(1 for f in rolled["faces"] if f <= 3)
        left, rolls = rolled["left"], rolls + 1
    assert left == 0 and rolled["empty"] is True
    assert cli("track", "roll", "poisoned").code == 1  # already empty
    cli("track", "new", "Troll", "--kind", "pool", "--linked", "1+2")
    phase_two = None
    for _ in range(30):
        out = cli("track", "roll", "troll")
        if "phase 2 of 2 begins at 2d" in out.out:
            phase_two = out
            break
    assert phase_two is not None
    first = json.loads(cli("track", "roll", "troll", "--drop", "1", "--format", "json").out)
    assert len(first["faces"]) == 1  # one of the 2d dropped before rolling


def test_rules_roll_and_push_pools(
    cli: Cli, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack = tmp_path / "extra" / "pools"
    (pack / "rules").mkdir(parents=True)
    (pack / "pack.yaml").write_text("id: pools\nname: P\nkind: supplement\nversion: 0.1.0\n")
    (pack / "rules" / "pools.yaml").write_text(
        "action: press\nparams: {target: ref}\n"
        "steps:\n  - pool: '@target'\n    as: press\n"
        "  - message: '{@press.left}d left, highest {@press.highest}'\n---\n"
        "action: push\nparams: {target: ref}\n"
        "steps:\n  - pool: '@target'\n    mode: drop\n    as: pushed\n"
        "  - if: '@pushed.empty'\n    then: ['It all comes down.']\n"
        "    else: ['{@pushed.left}d left']\n"
    )
    monkeypatch.setenv("DIDACT_PACK_PATH", os.pathsep.join([str(FIXTURE_PACKS), str(pack.parent)]))
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    assert cli("pack", "enable", "pools").code == 0
    cli("track", "new", "Troll", "--kind", "pool", "--linked", "1+2")
    pushed = cli("do", "push", "target=troll")
    assert pushed.code == 0, pushed.err
    assert "phase 2 of 2 begins at 2d" in pushed.out and "2d left" in pushed.out  # linked
    pressed = json.loads(cli("do", "press", "target=troll", "--format", "json").out)
    assert "d left, highest " in "\n".join(pressed["lines"]) and pressed["rolls"]
    if pressed["values"]["press.empty"]:  # both dice dropped: nothing left to push
        assert cli("do", "push", "target=troll").code == 1
        return
    done = ""
    for _ in range(4):  # a push drops 1d: the 2d phase empties within two, whatever was rolled
        done = cli("do", "push", "target=troll").out
        if "It all comes down." in done:
            break
    assert "It all comes down." in done and "Troll is empty" in done


def test_rules_set_reminders(cli: Cli, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pack = tmp_path / "extra" / "wounds"
    (pack / "rules").mkdir(parents=True)
    (pack / "pack.yaml").write_text("id: wounds\nname: W\nkind: supplement\nversion: 0.1.0\n")
    (pack / "rules" / "wounds.yaml").write_text(
        "action: wound\nparams: {who: ref}\n"
        "steps:\n  - remind: '{@who.name} dies unless stabilized'\n    in: 1 hour\n"
        "  - remind: 'Check on {@who.name}'\n    every: 1 day\n"
    )
    monkeypatch.setenv("DIDACT_PACK_PATH", os.pathsep.join([str(FIXTURE_PACKS), str(pack.parent)]))
    setup(cli)
    cli("pack", "enable", "wounds")
    cli("new", "pc", "Freya")
    done = cli("do", "wound", "who=freya")
    assert done.code == 0, done.err
    assert (
        "reminder set for day 1, 01:00" in done.out and "Freya dies unless stabilized" in done.out
    )
    pending = cli("remind", "--list").out
    assert "Freya dies unless stabilized" in pending and "Check on Freya" in pending  # both kept
    assert "Freya dies unless stabilized" in cli("time", "advance", "2 hours").out
