"""Sheets: field kinds, schema-aware new/set/edit/show, strictness, templates."""

import json
from pathlib import Path

import pytest

from didact.schema.fields import FieldError, FieldSpec, change, coerce
from tests.conftest import Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")


def mechanics(home: Path, cli: Cli, ref: str) -> dict[str, object]:
    data = json.loads(cli("show", ref, "--format", "json").out)
    block = data["mechanics"]["mini-system"]
    assert isinstance(block, dict)
    return block


@pytest.mark.parametrize(
    ("kind", "options", "raw", "stored"),
    [
        ("stat", {"range": [0, 18]}, 12, {"value": 12, "max": 12}),
        ("stat", {"range": [0, 18]}, "10/12", {"value": 10, "max": 12}),
        ("resource", {"min": 0}, {"value": 4, "max": 6}, {"value": 4, "max": 6}),
        ("uses", {"max": 3}, 2, {"value": 2, "max": 3}),
        ("uses", {}, "d8", {"die": "d8"}),
        ("clock", {"size": 6}, 2, {"value": 2, "size": 6}),
        ("track", {}, "3/10", {"value": 3, "size": 10}),
        ("enum", {"values": ["Aurifex", "Cutpurse"]}, "cutpurse", "Cutpurse"),
        ("flag", {}, "yes", True),
        ("int", {"min": 0}, "7", 7),
        (
            "slots",
            {},
            ["Rope", {"name": "Tent", "size": "bulky"}],
            ["Rope", {"name": "Tent", "size": "bulky"}],
        ),
        ("dice", {}, " d8 ", "d8"),
        ("ref", {"to": "npc"}, "npc:tom", "npc:tom"),
    ],
)
def test_coerce(kind: str, options: dict[str, object], raw: object, stored: object) -> None:
    spec = FieldSpec("x", kind, options)  # type: ignore[arg-type]
    assert coerce(spec, raw) == stored  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("kind", "options", "raw", "message"),
    [
        ("stat", {"range": [0, 18]}, 20, "can't go above 18"),
        ("enum", {"values": ["a", "b"]}, "c", "must be one of: a, b"),
        ("clock", {"size": 4}, 5, "must be 0–4"),
        ("ref", {"to": "npc"}, "loc:inn", "must point at a npc"),
        ("dice", {}, "d6 +", "ends too early"),
        ("derived", {"expr": "1"}, 1, "computed from other fields"),
        ("conditions", {"allowed": ["deprived"]}, ["sleepy"], "isn't allowed"),
    ],
)
def test_coerce_refuses(kind: str, options: dict[str, object], raw: object, message: str) -> None:
    spec = FieldSpec("x", kind, options)  # type: ignore[arg-type]
    with pytest.raises(FieldError, match=message):
        coerce(spec, raw)  # type: ignore[arg-type]


def test_change_clamps_and_explains() -> None:
    hp = FieldSpec("hp", "resource", {"min": 0})
    assert change(hp, {"value": 3, "max": 6}, "-=", 5) == (
        {"value": 0, "max": 6},
        "hp stopped at 0 (2 past zero)",
    )
    assert change(hp, {"value": 3, "max": 6}, "+=", 5) == (
        {"value": 6, "max": 6},
        "hp stopped at its max 6 (2 over)",
    )
    assert change(hp, {"value": 3, "max": 6}, "=", 5) == ({"value": 5, "max": 6}, None)
    fatigue = FieldSpec("fatigue", "counter", {"min": 0})
    assert change(fatigue, 1, "-=", 3) == (0, "fatigue stopped at 0 (2 past its limit)")
    clock = FieldSpec("doom", "clock", {"size": 4})
    assert change(clock, {"value": 3, "size": 4}, "+=", 2) == (
        {"value": 4, "size": 4},
        "doom is full (4/4)",
    )
    bag = FieldSpec("inventory", "slots", {})
    assert change(bag, ["Rope"], "+=", "Torch")[0] == ["Rope", "Torch"]
    assert change(bag, ["Rope", "Torch"], "-=", "rope")[0] == ["Torch"]


def test_new_with_fill_rolls_and_logs(cli: Cli) -> None:
    setup(cli)
    created = cli("new", "pc", "Freya", "--fill", "--set", "background=Cutpurse")
    assert created.code == 0
    assert "note: rolled STR: 3d6 → " in created.out and "note: rolled hp: 1d6 → " in created.out
    rolls = cli("rolls").out
    assert "— Freya: STR" in rolls and "— Freya: hp" in rolls
    shown = cli("show", "freya").out
    assert "mini-system: STR " in shown and "background cutpurse" in shown and "armor 0" in shown


def test_set_routes_clamps_and_validates(cli: Cli, home: Path) -> None:
    setup(cli)
    cli("new", "pc", "Freya", "--set", "STR=12", "--set", "hp=5")
    hurt = cli("set", "freya", "hp-=8")
    assert hurt.code == 0 and "note: hp stopped at 0 (3 past zero)" in hurt.out
    assert mechanics(home, cli, "freya")["hp"] == {"value": 0, "max": 5}
    too_strong = cli("set", "freya", "STR=20")
    assert too_strong.code == 1 and "STR can't go above 18" in too_strong.err
    assert "STR's max rose to 14" in cli("set", "freya", "STR=14").out
    gear = cli(
        "set", "freya", 'inventory+={"name":"Shield","armor":1}', "inventory+=Rope", "fatigue+=2"
    )
    assert gear.code == 0
    shown = cli("show", "freya").out
    assert "armor 1" in shown and "inventory (4/10 slots): Shield, Rope" in shown
    assert cli("set", "freya", "conditions+=sleepy").code == 1
    assert cli("set", "freya", "mood=grim").code == 0  # not on the sheet: a free-form field
    assert json.loads(cli("show", "freya", "--format", "json").out)["fields"]["mood"] == "grim"


def test_rolls_read_sheet_values(cli: Cli) -> None:
    setup(cli)
    cli("new", "pc", "Freya", "--set", "STR=12")
    assert "<= @STR(12) = " in cli("roll", "d20 <= @STR", "--as", "freya").out
    assert "@freya.STR(12)" in cli("roll", "d20 <= @freya.STR").out


def test_force_needs_a_reason_and_is_audited(cli: Cli) -> None:
    setup(cli)
    cli("new", "pc", "Freya", "--set", "STR=12")
    assert cli("set", "freya", "STR=25", "--force").code == 2
    forced = cli("set", "freya", "STR=25", "--force", "--reason", "blessed by the Wood")
    assert forced.code == 0
    assert "[forced] — reason: blessed by the Wood" in cli("audit").out


def test_lenient_mode_warns(cli: Cli, home: Path) -> None:
    setup(cli)
    path = home / "worlds/vale/campaigns/run/campaign.yaml"
    path.write_text(path.read_text() + "strictness: lenient\n", encoding="utf-8")
    cli("new", "pc", "Freya", "--set", "STR=12")
    result = cli("set", "freya", "conditions+=sleepy")
    assert (
        result.code == 0 and "warning: mini-system.conditions: 'sleepy' isn't allowed" in result.out
    )


def test_data_keys_are_routed(cli: Cli, home: Path) -> None:
    setup(cli)
    cli("new", "npc", "--data", '{"name": "Troll", "STR": 16, "hp": 12, "role": "bridge guard"}')
    block = mechanics(home, cli, "troll")
    assert block["STR"] == {"value": 16, "max": 16} and block["hp"] == {"value": 12, "max": 12}
    assert (
        json.loads(cli("show", "troll", "--format", "json").out)["fields"]["role"] == "bridge guard"
    )
    cli("edit", "troll", "--data", '{"hp": 7}')
    assert mechanics(home, cli, "troll")["hp"] == {"value": 7, "max": 12}  # the max stays


def test_template_and_json_schema(cli: Cli) -> None:
    setup(cli)
    text = cli("template", "pc").out
    assert text.startswith("template: pc (core.pc + mini-system.pc)")
    assert '"STR": "roll"' in text and "- `STR` (mechanics.mini-system): stat 0–18 · 🎲 3d6" in text
    assert "A starting character has three 3d6 attributes" in text
    schema = json.loads(cli("pack", "schema", "pc", "--format", "json").out)
    assert schema["properties"]["background"] == {"enum": ["aurifex", "bonekeeper", "cutpurse"]}
    assert {"const": "roll", "description": "Didact rolls 3d6"} in schema["properties"]["STR"][
        "anyOf"
    ]
    assert "free-form" in cli("template", "dragon").out


def test_broken_schemas_are_reported(tmp_path: Path, cli: Cli) -> None:
    pack = tmp_path / "bad-sheet"
    (pack / "schemas").mkdir(parents=True)
    (pack / "pack.yaml").write_text("id: bad-sheet\nname: B\nkind: system\nversion: 0.1.0\n")
    (pack / "schemas" / "pc.yaml").write_text(
        "type: pc\nfields:\n  STR: {kind: stats}\n  hp: {kind: resource, range: [0, 5]}\n"
        "  mood: {kind: enum}\n  armor: {kind: derived, expr: 'min(3,'}\n"
        "  DEX: {kind: stat, on_zero: {trigr: death}}\n"
        "  doom: {kind: counter, thresholds: {3: [ok, {set: 0}]}}\n"
        "  details: {kind: list}\n"  # a record keeps `details` for the GM's notes
    )
    result = cli("pack", "validate", str(pack))
    assert result.code == 1
    assert "schemas/pc.yaml:3: field `STR`: unknown kind 'stats'" in result.out
    assert "schemas/pc.yaml:4: field `hp`: `range` doesn't apply to resource" in result.out
    assert "schemas/pc.yaml:5: field `mood`: an enum needs `values`" in result.out
    assert "schemas/pc.yaml:6: `min(3,`" in result.out
    assert "schemas/pc.yaml:7: unknown hook action `trigr`" in result.out
    assert "schemas/pc.yaml:8: `set` takes field: value pairs" in result.out
    assert "schemas/pc.yaml:9: field `details` is named like a record's own key" in result.out
