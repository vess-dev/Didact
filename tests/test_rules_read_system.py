"""Every rule (a generator and character creation too) reads the id of the system its world plays
as `@system`, so a setting enabled under either of two systems tells them apart without being
told; a parameter of that name still wins (the `either-setting` fixture, played under
`clock-lite` and under `nested-lite`)."""

import json

from tests.conftest import Cli


def _world(cli: Cli, world: str, system: str) -> None:
    assert cli("world", "new", world, "--system", system, "--seed", "either").code == 0
    assert cli("campaign", "new", f"{world}-run", "--seed", "either").code == 0
    assert cli("pack", "enable", "either-setting").code == 0


def _frame(cli: Cli) -> object:
    made = cli("gen", "run", "either-setting.frame", "--auto", "--format", "json")
    assert made.code == 0, made.err
    return json.loads(made.out)["draft"]["entities"][0]["fields"]


def test_a_setting_reads_the_system_its_world_plays(cli: Cli) -> None:
    _world(cli, "west", "clock-lite")
    assert "Playing clock-lite." in cli("do", "played").out
    assert "Chosen: clock-lite." in cli("do", "chosen").out  # the parameter left out
    assert "Chosen: by hand." in cli("do", "chosen", "system=by hand").out  # given, it wins
    assert "The session opens under clock-lite." in cli("session", "start").out  # a trigger
    assert _frame(cli) == {"kind": "clock", "size": 6}

    _world(cli, "east", "nested-lite")
    assert "Playing nested-lite." in cli("do", "played").out
    assert _frame(cli) == {"kind": "pool", "value": {"value": 6, "max": 6}}
