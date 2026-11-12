"""Every rule reads where play stands as a trigger does: `@session`, `@scene` and the game time
(`@time.day`, `@time.hour`, …), in a check, an action, a procedure or a generator, and a rule a
trigger runs reads what that trigger reads; only an event has `@time.passed` (the `clock-lite`
fixture)."""

import json

from tests.conftest import Cli


def test_every_rule_reads_the_session_the_scene_and_the_time(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "clock-lite", "--seed", "clock").code == 0
    assert cli("campaign", "new", "c", "--seed", "clock").code == 0
    assert "session 0; scene 0; day 1; hour 0; passed none" in cli("do", "tell").out
    assert "No session is open." in cli("do", "renown").out  # a procedure
    cli("session", "start")
    cli("scene", "new", "At the ford")
    assert "session 1; scene 1; day 1; hour 0; passed none" in cli("do", "tell").out
    assert "Renown moves in session 1." in cli("do", "renown").out

    dusk = cli("time", "advance", "20", "hours").out  # the trigger, and the rule it runs
    assert "72000 seconds passed. · session 1; scene 1; day 1; hour 20; passed 72000" in dusk
    assert "session 1; scene 1; day 1; hour 20; passed none" in cli("do", "tell").out
    assert "→ success" in cli("do", "late").out  # a check: 20 >= 18
    made = json.loads(cli("gen", "run", "clock-lite.chronicle", "--auto", "--format", "json").out)
    assert made["draft"]["entities"][0]["name"] == "Session 1, day 1"
