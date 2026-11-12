"""Rules as function calls: checks, actions, procedures, triggers, pending rolls."""

import json
import os
import re
from pathlib import Path
from typing import cast

import pytest

from didact.core.errors import InvalidError
from didact.core.output import JSON
from didact.rules.engine import Engine
from tests.conftest import FIXTURE_PACKS, Cli
from tests.rules_helpers import FakeHost, Records, make_engine, pack_rules

RULES = pack_rules("mini-system")


def engine(faces: str, records: Records | None = None) -> tuple[Engine, FakeHost]:
    return make_engine(faces, records, RULES)


def test_check_outcomes() -> None:
    eng, _ = engine("9", {"pc:freya": {"STR": 12, "name": "Freya"}})
    result = eng.run(RULES["save"], {"who": "freya", "attr": "STR"})
    assert result.outcome == "success" and result.prompts == ["State the risk before rolling."]
    eng, _ = engine("14", {"pc:freya": {"STR": 12, "name": "Freya"}})
    failed = eng.run(RULES["save"], {"who": "freya", "attr": "STR"})
    assert failed.outcome == "failure" and "The risk comes true for Freya." in failed.lines
    eng, _ = engine("20", {"pc:freya": {"STR": 18, "name": "Freya"}})
    assert eng.run(RULES["save"], {"who": "freya", "attr": "STR"}).outcome == "failure"  # a 20
    eng, _ = engine("1", {"pc:freya": {"STR": 0, "name": "Freya"}})
    assert eng.run(RULES["save"], {"who": "freya", "attr": "STR"}).outcome == "success"  # a 1


def test_a_set_target_can_name_a_parameter() -> None:
    from didact.rules.engine import Rule

    lose: dict[str, JSON] = {
        "action": "lose",
        "params": {"who": "ref", "attr": {"enum": ["STR", "DEX"]}},
        "steps": [{"set": "who.$attr", "op": "-=", "value": 2}],
    }
    rule = Rule("action", "mini-system.lose", "mini-system", lose, "rules/x.yaml:1")
    eng, host = engine("", {"pc:freya": {"STR": 12, "DEX": 9, "name": "Freya"}})
    eng.run(rule, {"who": "freya", "attr": "DEX"})
    assert host.changes == ["pc:freya.DEX -= 2"]  # the field named, not one called `$attr`


def test_a_refusal_inside_stops_the_rule_that_asked() -> None:
    from didact.rules.engine import Rule

    def rule(rule_id: str, data: dict[str, JSON]) -> Rule:
        return Rule("action", f"mini-system.{rule_id}", "mini-system", data, "rules/x.yaml:1")

    inner = rule("tire", {"action": "tire", "steps": [{"stop": "No room for Fatigue."}]})
    outer = rule("cast", {"action": "cast", "steps": [{"do": "tire"}, "The spell goes off."]})
    eng, host = engine("", {"pc:freya": {"name": "Freya"}})
    host.rules = {**host.rules, "tire": inner}
    stopped = eng.run(outer, {})
    assert stopped.stopped == "No room for Fatigue." and "The spell goes off." not in stopped.lines
    going = rule("try", {"action": "try", "steps": [{"do": "tire", "go_on": True}, "Anyway."]})
    assert "Anyway." in eng.run(going, {}).lines  # `go_on: true` carries on


def test_a_check_whose_before_stops_rolls_nothing() -> None:
    from didact.rules.engine import Rule

    data: dict[str, JSON] = {
        "check": "hold",
        "before": [{"stop": "Nobody's left to hold the line."}],
        "roll": "d20",
        "success": "@roll <= 10",
    }
    check = Rule("check", "mini-system.hold", "mini-system", data, "rules/x.yaml:1")
    eng, host = engine("7", {})
    result = eng.run(check, {})
    assert result.rolls == [] and host.faces == ["7"]  # no die was used


def test_action_with_nested_check() -> None:
    eng, host = engine(
        "6,17", {"pc:freya": {"name": "Freya"}, "npc:troll": {"name": "Troll", "hp": 3, "STR": 14}}
    )
    result = eng.run(RULES["attack"], {"attacker": "freya", "target": "troll", "weapon": "d6"})
    assert host.changes == ["npc:troll.hp -= 6", "npc:troll.STR -= 3"]
    assert result.bound["dealt"] == 6 and result.bound["critical"] == "failure"
    assert "Troll takes critical damage." in result.lines
    assert result.lines[-1] == "Freya deals 6 to Troll."


def test_pending_and_resolve() -> None:
    eng, host = engine("5,5,2", {"pc:freya": {"name": "Freya", "fatigue": 0}})
    first = eng.run(RULES["scramble"], {"who": "freya"})
    assert first.outcome == "failure" and set(first.options) == {"push", "accept"}
    saved = cast(
        dict[str, JSON],
        {k: getattr(first, k) for k in ("params", "bound", "faces", "exprs", "rolls")},
    )
    saved["texts"] = {"who": "pc:freya"}
    host.faces = ["6", "4", "1"]
    pushed = eng.resolve(RULES["scramble"], saved, "push")
    assert pushed.outcome == "success" and host.changes == ["pc:freya.fatigue += 1"]
    with pytest.raises(InvalidError, match="has no option 'burn'"):
        eng.resolve(RULES["scramble"], saved, "burn")


def test_parameters_are_checked() -> None:
    eng, _ = engine("", {"pc:freya": {"STR": 12}})
    with pytest.raises(InvalidError, match="needs attr"):
        eng.run(RULES["save"], {"who": "freya"})
    with pytest.raises(InvalidError, match="attr must be one of: STR, DEX, WIL"):
        eng.run(RULES["save"], {"who": "freya", "attr": "CHA"})
    with pytest.raises(InvalidError, match="has no parameter 'luck'"):
        eng.run(RULES["save"], {"who": "freya", "attr": "STR", "luck": "1"})


def test_procedures_and_triggers() -> None:
    eng, _ = engine("1")
    watch = eng.run(RULES["watch"], {"action": "travel"})
    assert watch.prompts == ["Describe the terrain and the weather.", "Record torches and rations."]
    assert "The party is lost." in watch.lines and "Weather: a roll on weather" in watch.lines
    assert eng.run(RULES["nightfall"], {}).lines == ["Night falls."]


def setup(cli: Cli, home: Path) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    path = home / "worlds/vale/campaigns/run/campaign.yaml"  # a fixed seed: the same dice every run
    text = path.read_text()
    path.write_text(
        "\n".join("seed: fixed" if x.startswith("seed:") else x for x in text.splitlines()) + "\n"
    )
    cli("new", "pc", "Freya", "--set", "STR=12", "--set", "hp=4")
    cli("new", "npc", "Troll", "--set", "STR=14", "--set", "hp=3")


def test_do_logs_rolls_and_changes(cli: Cli, home: Path) -> None:
    setup(cli, home)
    listing = cli("rules", "list").out
    assert re.match(r"\d+ rules:", listing) and "- check mini-system.save · Save" in listing
    assert (
        "run: `didact do mini-system.save who=<ref> attr=STR`" in cli("rules", "show", "save").out
    )
    save = cli("do", "save", "who=freya", "attr=STR")
    assert (
        save.code == 0
        and "#r1 1d20 → [" in save.out
        and ("→ success" in save.out or "→ failure" in save.out)
    )
    attack = cli("do", "attack", "attacker=freya", "target=troll", "weapon=d8")
    assert attack.code == 0 and "npc:troll: hp -= " in attack.out
    assert "do mini-system.attack (attacker=freya, target=troll, weapon=d8)" in cli("history").out
    before = json.loads(cli("show", "troll", "--format", "json").out)["mechanics"]
    cli("undo")
    after = json.loads(cli("show", "troll", "--format", "json").out)["mechanics"]
    assert after["mini-system"]["hp"] == {"value": 3, "max": 3} and before != after
    assert cli("replay").code == 0


def test_dry_run_keeps_nothing(cli: Cli, home: Path) -> None:
    setup(cli, home)
    result = cli("do", "attack", "attacker=freya", "target=troll", "--dry-run")
    assert result.code == 0 and "#r?" in result.out
    assert (
        json.loads(cli("show", "troll", "--format", "json").out)["mechanics"]["mini-system"]["hp"][
            "value"
        ]
        == 3
    )
    assert cli("rolls").out.strip() == "no rolls yet (campaign:run)"


def test_pending_rolls_through_the_cli(cli: Cli, home: Path) -> None:
    setup(cli, home)
    for _ in range(10):  # scramble until one comes back pending (0 successes)
        result = cli("do", "scramble", "who=freya")
        if "pending:" in result.out:
            break
    else:
        pytest.skip("no pending scramble in 10 tries")
    key = result.out.split("didact resolve ")[1].split(" ")[0]
    assert "- " + key in cli("pending").out
    assert cli("resolve", key, "burn").code == 1
    done = cli("resolve", key, "accept")
    assert done.code == 0 and "no pending rolls" in cli("pending").out


def test_broken_rules_are_reported(tmp_path: Path, cli: Cli) -> None:
    pack = tmp_path / "bad-rules"
    (pack / "rules").mkdir(parents=True)
    (pack / "pack.yaml").write_text("id: bad-rules\nname: B\nkind: system\nversion: 0.1.0\n")
    (pack / "rules" / "r.yaml").write_text(
        "check: oops\nroll: d20 +\nsuccess: '@roll <='\nbands: 3\n---\n"
        "action: hit\nparams: {who: {kind: person}}\nsteps: [{roll: d6, bogus: 1}]\n---\n"
        "trigger: t\non: whenever\nsteps: []\n"
    )
    out = cli("pack", "validate", str(pack)).out
    assert "rules/r.yaml:2: `d20 +`" in out
    assert "rules/r.yaml:3: `@roll <=`" in out
    assert "`bands` must map outcome names to conditions" in out
    assert "param `who`: unknown kind 'person'" in out
    assert "unknown step key `bogus`" in out
    assert "unknown trigger event 'whenever'" in out


def test_triggers_read_their_oracles_state(
    cli: Cli, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack = tmp_path / "extra" / "tally"
    (pack / "rules").mkdir(parents=True)
    (pack / "oracles").mkdir()
    (pack / "pack.yaml").write_text("id: tally\nname: T\nkind: oracle\nversion: 0.1.0\n")
    (pack / "oracles" / "o.yaml").write_text(
        "oracle: tally\ntitle: Tally\nask: question\nodds: [even]\n"
        "state:\n  suspense: {start: 0, min: 0}\n"
    )
    (pack / "rules" / "r.yaml").write_text(
        "check: question\nparams: {oracle: ref}\nroll: d6\nsuccess: '@roll >= 4'\n---\n"
        "trigger: build-up\non: session_start\nparams: {oracle: ref}\n"
        "steps:\n  - set: oracle.suspense\n    op: '+='\n    value: 1\n"
    )
    monkeypatch.setenv("DIDACT_PACK_PATH", os.pathsep.join([str(FIXTURE_PACKS), str(pack.parent)]))
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("pack", "enable", "tally")
    skipped = cli("session", "start", "--dry-run")
    assert (
        skipped.code == 0 and "tally.build-up: skipped (its oracle has no state yet)" in skipped.out
    )
    started = cli("session", "start")
    assert started.code == 0 and "tally.build-up" in started.out  # no `oracle=` given: supplied
    state = json.loads(cli("show", "oracle:tally-tally", "--format", "json").out)
    assert state["fields"]["suspense"] == 1
