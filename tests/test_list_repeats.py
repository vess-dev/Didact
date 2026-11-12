"""`+=` adds a value to a `list` field again, as to `slots` (a once-a-day power used twice is on
the list twice), from `set` and from a rule's `set` step; `tags`, `conditions` and `refs` hold a
value once, and `-=` takes every copy off (the `repeats-lite` fixture)."""

import json
from typing import Any

from didact.schema.fields import FieldSpec, change
from tests.conftest import Cli


def _mechanics(cli: Cli, ref: str) -> dict[str, Any]:
    shown = cli("show", ref, "--format", "json")
    assert shown.code == 0, shown.err
    return dict(json.loads(shown.out)["mechanics"]["repeats-lite"])


def test_a_list_keeps_a_value_added_again(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "repeats-lite", "--seed", "repeats").code == 0
    assert cli("campaign", "new", "c", "--seed", "repeats").code == 0
    cli("new", "pc", "Hero")
    cli("new", "npc", "Ally")
    twice = cli(
        "set", "hero", "used_today+=dragonskin", "used_today+=dragonskin", "marks+=brave",
        "marks+=brave", "conditions+=deprived", "conditions+=deprived", "allies+=npc:ally",
        "allies+=npc:ally",
    )  # fmt: skip
    assert twice.code == 0, twice.err
    used = cli("do", "use", "who=hero", "power=dragonskin")  # a rule's `set` step
    assert "Hero has used: dragonskin, dragonskin, dragonskin." in used.out
    sheet = _mechanics(cli, "hero")
    assert sheet["used_today"] == ["dragonskin"] * 3
    assert [sheet[key] for key in ("marks", "conditions", "allies")] == [
        ["brave"], ["deprived"], ["npc:ally"]
    ]  # fmt: skip
    assert cli("set", "hero", "used_today-=dragonskin").code == 0
    assert _mechanics(cli, "hero")["used_today"] == []  # every copy


def test_change_adds_again_to_lists_and_slots_only() -> None:
    for kind, twice in (("list", ["a", "a"]), ("slots", ["a", "a"]), ("tags", ["a"])):
        assert change(FieldSpec("x", kind, {}), ["a"], "+=", "a")[0] == twice  # type: ignore[arg-type]
