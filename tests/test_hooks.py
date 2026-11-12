"""Field hooks: on_zero, on_full / when_full and counter thresholds fire when crossed."""

from didact.core.output import JSON
from didact.rules.engine import Rule
from didact.schema.model import TypeSchema, fields_from
from didact.schema.sheet import Sheet
from didact.services import hooks, sheets
from didact.store.entity import Entity
from tests.conftest import Cli
from tests.rules_helpers import make_engine

FIELDS: dict[str, JSON] = {
    "fields": {
        "hp": {"kind": "resource", "min": 0, "on_zero": "Roll on the Scars table."},
        "doom": {"kind": "clock", "size": 4, "on_full": {"trigger": "doom-falls"}},
        "taint": {
            "kind": "counter",
            "thresholds": {"3": "A mark appears.", "5": {"condition": "tainted"}},
        },
        "pack": {"kind": "slots", "capacity": 2, "when_full": {"set": {"hp": 0}}},
        "conditions": {"kind": "conditions"},
    }
}
SHEET = Sheet("pc", "sys", None, TypeSchema("pc", "sys", fields_from(FIELDS), open=True))


def pc(**values: JSON) -> Entity:
    base: dict[str, JSON] = {"hp": {"value": 3, "max": 3}, "doom": {"value": 0, "size": 4}}
    meta: dict[str, JSON] = {"id": "pc:x", "type": "pc", "name": "X"}
    meta["mechanics"] = {"sys": base | values}
    return Entity.from_meta(meta, "", where="test")


def change(entity: Entity, **values: JSON) -> hooks.Outcome:
    before = sheets.entity_values(entity, SHEET)
    block = entity.mechanics["sys"]
    assert isinstance(block, dict)
    block.update(values)
    return hooks.settle(entity, SHEET, before, "strict")


def test_on_zero_fires_when_crossed_only() -> None:
    entity = pc()
    assert change(entity, hp={"value": 0, "max": 3}).notes == [
        "hp reached 0: Roll on the Scars table."
    ]
    assert change(entity, hp={"value": 0, "max": 3}).notes == []  # 0 → 0 crosses nothing


def test_on_full_triggers_and_thresholds() -> None:
    entity = pc(taint=2)
    full = change(entity, doom={"value": 4, "size": 4})
    assert full.triggers == ["doom-falls"] and full.notes == ["doom is full (4/4): runs doom-falls"]
    marks = change(entity, taint=5)  # crosses 3 and 5 at once
    assert marks.notes == ["taint reached 3: A mark appears.", "taint reached 5: now tainted"]
    block = entity.mechanics["sys"]
    assert isinstance(block, dict) and block["conditions"] == ["tainted"]
    assert change(entity, taint=4).notes == []  # going down fires nothing


def test_a_hook_can_cross_another_line() -> None:
    entity = pc(pack=["Rope"])
    fired = change(entity, pack=["Rope", "Lamp"])
    assert fired.notes == ["pack is full (2/2): hp = 0", "hp reached 0: Roll on the Scars table."]


def test_set_runs_the_sheet_hooks(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "pc", "Freya", "--set", "STR=12", "--set", "hp=4")
    cli("new", "pc", "Ansel", "--set", "STR=10", "--set", "hp=3")
    dead = cli("set", "freya", "STR=0")
    assert "note: STR reached 0: runs death" in dead.out and "note: Freya is dead." in dead.out
    cli("undo")
    forced = cli("set", "freya", "STR=0", "--force", "--reason", "retcon")
    assert "note: --force: skipped the hook for STR reached 0" in forced.out
    assert "is dead" not in forced.out
    attack = cli("do", "attack", "attacker=freya", "target=ansel", "weapon=20")
    assert "STR reached 0: runs death" in attack.out and "  Ansel is dead." in attack.out


def test_the_engine_runs_hook_triggers_and_notes_missing_ones() -> None:
    hit: dict[str, JSON] = {"params": {"who": "ref"}, "steps": [{"set": "who.hp", "value": 0}]}
    fall: dict[str, JSON] = {"params": {"who": "ref"}, "steps": ["{@who.name} falls."]}
    rules = {
        "hit": Rule("action", "mini-system.hit", "mini-system", hit, "test"),
        "fall": Rule("trigger", "mini-system.fall", "mini-system", fall, "test"),
    }
    engine, host = make_engine("", {"pc:x": {"name": "X", "hp": 3}}, rules)
    host.fires = {"hp": ("fall", "missing")}
    lines = engine.run(rules["hit"], {"who": "x"}).lines
    assert "  X falls." in lines
    assert "  hook: there's no rule 'missing' to run" in lines
