"""Any rule loops: `for: pcs` (or `party`) runs steps once per player character (or party
member), each a record the steps read and set as `@member` while the rule's own `who` stays its
own, and `repeat` counts in a check, an action, a procedure and a trigger as it does in a draft
(the `party-lite` fixture)."""

import json
from pathlib import Path

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "party-lite", "--seed", "party").code == 0
    assert cli("campaign", "new", "c", "--seed", "party").code == 0
    for name in ("Freya", "Ansel"):
        assert cli("new", "pc", name).code == 0
    assert cli("new", "npc", "Old Gannet").code == 0
    assert cli("party", "add", "old-gannet", "--as", "hireling").code == 0


def _fatigue(cli: Cli, who: str) -> object:
    shown = json.loads(cli("show", who, "--format", "json").out)
    return shown.get("mechanics", {}).get("party-lite", {}).get("fatigue")


def test_a_rule_runs_steps_for_each_pc_and_keeps_its_own_who(cli: Cli) -> None:
    setup(cli)
    assert "dry run: party-lite.rest" in cli("do", "rest", "who=freya", "--dry-run").out
    assert _fatigue(cli, "freya") is None  # a dry run keeps nothing
    rested = cli("do", "rest", "who=freya").out
    assert "Freya keeps the first watch." in rested and "Freya still keeps watch." in rested
    assert "Ansel marks the rest (1 fatigue)." in rested
    assert "Freya marks the rest (1 fatigue)." in rested
    assert "Old Gannet" not in rested  # a hireling isn't a PC
    assert (_fatigue(cli, "freya"), _fatigue(cli, "ansel")) == (1, 1)
    assert cli("undo").code == 0  # one change, undone whole
    assert (_fatigue(cli, "freya"), _fatigue(cli, "ansel")) == (None, None)


def test_loops_nest_in_every_kind_of_rule(cli: Cli) -> None:
    setup(cli)
    drilled = cli("do", "drill").out  # a procedure: `repeat` around `for: party`
    for name in ("Freya", "Ansel", "Old Gannet"):
        assert f"Round 1: {name} rolls" in drilled and f"Round 2: {name} rolls" in drilled
    assert "party-lite.drill (hand=npc:old-gannet): drill" in cli("rolls").out  # whose roll
    mustered = cli("do", "muster").out  # a check's outcome steps
    assert "Muster 1." in mustered and "Muster 2." in mustered
    woken = cli("do", "dawn").out  # a trigger
    assert "Freya wakes." in woken and "Ansel wakes." in woken and "Gannet" not in woken


def test_a_loops_member_cant_take_a_parameters_name(cli: Cli, tmp_path: Path) -> None:
    pack = tmp_path / "bad-loops"
    (pack / "rules").mkdir(parents=True)
    (pack / "pack.yaml").write_text("id: bad-loops\nname: B\nkind: system\nversion: 0.1.0\n")
    (pack / "rules" / "r.yaml").write_text(
        "action: rest\nparams: {who: ref, member: text}\nsteps:\n"
        "  - {for: pcs, as: who, steps: []}\n  - {for: pcs, steps: []}\n"
        "  - {for: everyone, as: one, steps: [{roll: d6, bogus: 1}]}\n"
    )
    out = cli("pack", "validate", str(pack)).out
    assert "a `for:` step can't call each member who: a parameter has that name" in out
    assert "a `for:` step can't call each member member: a parameter has that name" in out
    assert "a `for:` step runs over party or pcs, not 'everyone'" in out
    assert "rules/r.yaml:6" in out and "unknown step key `bogus`" in out  # its steps too
