"""The paper-test packs' mechanics with exact dice (a scripted host, no library)."""

from didact.core.output import JSON
from tests.rules_helpers import Records, make_engine, pack_rules

MOMENTUM = pack_rules("ironsworn-lite")  # an action die against two challenge dice
POOLS = pack_rules("blades-lite")  # d6 pools read by the highest die
SYMBOLS = pack_rules("genesys-lite")  # dice with symbol faces that cancel
PUSH = pack_rules("yze-lite")  # d6 pools you can push
DUALITY = pack_rules("daggerheart-lite")  # hope and fear dice
THORNS = pack_rules("grimwild-lite")  # difficulty dice that cut the result


def test_an_action_die_against_challenge_dice_and_a_momentum_burn() -> None:
    kyn: Records = {"pc:kyn": {"name": "Kyn", "iron": 3, "momentum": 9}}
    eng, _ = make_engine("6,8,5", kyn, MOMENTUM)  # 6 + 3 = 9 beats 8 and 5
    hit = eng.run(MOMENTUM["action-roll"], {"who": "kyn", "stat": "iron"})
    assert hit.outcome == "strong-hit" and hit.flags == []
    eng, host = make_engine("1,7,7", kyn, MOMENTUM)  # 1 + 3 = 4: a miss, and a match
    miss = eng.run(MOMENTUM["action-roll"], {"who": "kyn", "stat": "iron"})
    assert miss.outcome == "miss" and miss.flags == ["match"] and "burn" in miss.options
    saved: dict[str, JSON] = {
        k: getattr(miss, k) for k in ("params", "bound", "faces", "exprs", "rolls")
    }
    saved["texts"] = {"who": "pc:kyn", "stat": "iron", "adds": "0"}
    burned = eng.resolve(MOMENTUM["action-roll"], saved, "burn")
    assert burned.outcome == "strong-hit" and host.changes == ["pc:kyn.momentum = 2"]


def test_progress_is_marked_by_rank() -> None:
    eng, host = make_engine("", {"vow:avenge": {"name": "Avenge", "progress": 0}}, MOMENTUM)
    eng.run(MOMENTUM["mark-progress"], {"vow": "avenge", "rank": "dangerous"})
    assert host.records["vow:avenge"]["progress"] == 8


def test_zero_dice_take_the_lowest_of_two() -> None:
    eng, _ = make_engine("6,2", {}, POOLS)
    assert eng.run(POOLS["action"], {"dice": "0"}).outcome == "failure"  # lowest of 2d6 is 2
    eng, _ = make_engine("6,3,6", {}, POOLS)
    assert eng.run(POOLS["action"], {"dice": "3"}).outcome == "critical"  # two sixes


def test_symbol_dice_cancel() -> None:
    # ability faces: 2 = success, 4 = success+success; difficulty: 2 = failure
    eng, _ = make_engine("success,success+success,failure", {}, SYMBOLS)
    result = eng.run(SYMBOLS["skill"], {"ability": "2", "difficulty": "1"})
    assert result.outcome == "success"  # 3 successes − 1 failure
    eng, _ = make_engine("success,failure+failure", {}, SYMBOLS)
    assert eng.run(SYMBOLS["skill"], {"ability": "1", "difficulty": "1"}).outcome == "failure"


def test_a_push_turns_banes_into_stress() -> None:
    ingrid: Records = {"pc:ingrid": {"name": "Ingrid", "agility": 3, "stress": 0}}
    eng, host = make_engine("1,3,4", ingrid, PUSH)
    first = eng.run(PUSH["skill"], {"who": "ingrid", "attr": "agility"})
    assert first.outcome == "failure" and "push" in first.options
    saved: dict[str, JSON] = {
        k: getattr(first, k) for k in ("params", "bound", "faces", "exprs", "rolls")
    }
    saved["texts"] = {"who": "pc:ingrid", "attr": "agility", "skill": "0"}
    host.faces = ["6", "1"]  # the 1 is kept; the 3 and 4 reroll as 6 and 1
    pushed = eng.resolve(PUSH["skill"], saved, "push")
    assert pushed.outcome == "success" and host.changes == ["pc:ingrid.stress += 2"]


def test_duality_dice_hope_and_fear() -> None:
    wren: Records = {"pc:wren": {"name": "Wren", "agility": 1, "hope": 2}}
    eng, host = make_engine("9,4", wren, DUALITY)
    result = eng.run(DUALITY["duality"], {"who": "wren", "trait": "agility"})
    assert result.outcome == "success-with-hope" and host.changes == ["pc:wren.hope += 1"]
    eng, _ = make_engine("5,5", wren, DUALITY)
    assert eng.run(DUALITY["duality"], {"who": "wren", "trait": "agility"}).outcome == "critical"


def test_thorn_dice_cut_the_result() -> None:
    eng, _ = make_engine("6,2,8", {}, THORNS)  # a 6, cut once by a thorn (8)
    assert eng.run(THORNS["action"], {"pool": "2", "thorns": "1"}).outcome == "messy"
    eng, _ = make_engine("6,6", {}, THORNS)
    assert eng.run(THORNS["action"], {"pool": "2"}).outcome == "critical"
