"""Tables (dice, weights, columns, lookups, templates, follow-ups), decks and bags."""

import json
import re
from pathlib import Path

import pytest

from didact.core.config import resolve_config
from didact.core.errors import InvalidError
from didact.expr import PhysicalFaces, RollContext, default_registry
from didact.expr.model import Value
from didact.packs.build import build
from didact.packs.library import PackLibrary
from didact.services.tables import finder
from didact.tables.engine import FindTable, TableRoller
from didact.tables.model import parse_key
from tests.conftest import Cli


def roller(home: Path, faces: str) -> tuple[TableRoller, FindTable]:
    packs = PackLibrary(resolve_config(home=str(home))).resolve(["mini-system"])
    find = finder(packs)
    ctx = RollContext(default_registry(), PhysicalFaces(faces.split(",") if faces else []))
    return TableRoller(find, ctx), find


def roll(home: Path, table: str, faces: str, **inputs: Value) -> str:
    engine, find = roller(home, faces)
    return engine.roll(find(table, ""), inputs).text


@pytest.mark.parametrize(
    ("key", "low", "high"),
    [
        (3, 3, 3),
        ("2-3", 2, 3),
        ("2–3", 2, 3),
        ("96-00", 96, 100),
        ("-4..-2", -4, -2),
        ("12+", 12, 10**9),
    ],
)
def test_entry_keys(key: str | int, low: int, high: int) -> None:
    band = parse_key(key, percentile=True)
    assert (band.low, band.high) == (low, high)


def test_rolling_every_shape(home: Path) -> None:
    assert roll(home, "weather", "1") == "Clear"
    engine, find = roller(home, "5,4")
    storm = engine.roll(find("weather", ""))
    assert storm.text == "Storm" and storm.follow[0].text == "A tree splits"
    assert roll(home, "weather", "6,1,3") == "Clear + Rain"  # "roll twice"
    assert roll(home, "poi-name", "1,3", poi="Tower") == "(The) Crow Tower"
    assert roll(home, "poi-name", "4,2,3,6", poi="Keep") == "Broken Keep of 3 Frosts"
    assert roll(home, "culture", "2,4") == "character: Bureaucratic · ambition: Faith"
    assert roll(home, "tavern", "3,4") == "A crowded tavern that pours bilge."  # `read:`
    assert (
        roll(home, "encounters", "3") == "Wolves"
        and roll(home, "encounters", "4") == "A lost merchant"
    )
    assert roll(home, "scars", "", hp_lost=3) == "Walloped"
    assert roll(home, "scars", "", hp_lost=9) == "Broken limb"
    assert roll(home, "fate", "", odds="Likely", chaos=6) == "15 / 75 / 96"
    assert roll(home, "taint", "20", corruption=15) == "Possession"  # clamped past 20


def test_duplicates_make_it_worse(home: Path) -> None:
    engine, find = roller(home, "3,2,2")
    result = engine.roll(find("omens", ""))
    assert result.text == "Blood moon + Blood moon"
    assert result.note_lines == ["Blood moon came up again: make it worse"]


def test_table_errors(home: Path) -> None:
    with pytest.raises(InvalidError, match="scars is read by hp_lost; hp_lost is missing"):
        roll(home, "scars", "")
    with pytest.raises(InvalidError, match="no entry for 'certain'"):
        roll(home, "fate", "", odds="certain", chaos=1)
    with pytest.raises(InvalidError, match="nothing fills \\{poi\\}"):
        roll(home, "poi-name", "3,1")


def _pack(tmp_path: Path, tables: str) -> list[str]:
    pack = tmp_path / "t"
    (pack / "tables").mkdir(parents=True)
    (pack / "pack.yaml").write_text("id: t\nname: T\nkind: system\nversion: 0.1.0\n")
    (pack / "GUIDE.md").write_text("# T\n")
    (pack / "tables" / "t.yaml").write_text(tables)
    return [p.text() for p in build(pack).problems]


def test_validation_catches_gaps_and_overlaps(tmp_path: Path) -> None:
    problems = _pack(
        tmp_path,
        "table: gaps\ndice: 2d6\nentries: {2-6: a, 8-12: b}\n---\n"
        "table: overlap\ndice: d6\nentries: {1-4: a, 4-6: b}\n---\n"
        "table: rows\ndice: d4\ncolumns: [a, b]\nentries: {1-4: [x]}\n---\n"
        "table: odd\ndice: d6\nentries: {1-6: {text: x, colour: red}}\n",
    )
    gap = "tables/t.yaml:3: 2d6 can roll 7, which no entry covers (fix: add entries for them"
    assert any(p.startswith(gap) for p in problems)
    assert any("entries 1-4 and 4-6 overlap" in p for p in problems)
    assert any("each row needs 2 values (a, b)" in p for p in problems)
    assert any("unknown entry key `colour`" in p for p in problems)


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")


def test_table_rolls_are_logged_and_replay(cli: Cli) -> None:
    setup(cli)
    first = cli("table", "roll", "weather", "--reason", "setting out")
    assert first.code == 0 and first.out.startswith("#r1 mini-system.weather (d6 → [")
    names = cli("table", "roll", "poi-name", "--with", "poi=Tower", "--times", "3")
    assert names.out.startswith("#r2 mini-system.poi-name ×3:") and names.out.count("\n- ") == 3
    data = json.loads(
        cli(
            "table",
            "roll",
            "fate",
            "--with",
            "odds=likely",
            "--with",
            "chaos=2",
            "--format",
            "json",
        ).out
    )
    assert data["results"][0]["data"]["value"] == [10, 50, 91]
    assert "- #r1 mini-system.weather" in cli("rolls").out
    assert cli("replay").out.strip() == "✔ 3 rolls reproduced exactly (campaign:run)"
    listing = cli("table", "list").out
    assert re.match(r"\d+ tables:", listing) and "- mini-system.weather · Summer weather" in listing
    assert "- 5: Storm" in cli("table", "show", "weather").out
    assert cli("table", "roll", "wether").code == 1


def test_decks_and_bags(cli: Cli) -> None:
    setup(cli)
    first = cli("deck", "draw", "omens-deck", "2")
    assert first.code == 0 and "note: shuffled a new deck (#r1)" in first.out
    last = cli("deck", "draw", "omens-deck")
    assert last.code == 0
    empty = cli("deck", "draw", "omens-deck")
    assert empty.code == 1 and "has 0 left" in empty.err
    assert cli("deck", "status", "omens-deck").out.startswith(
        "mini-system.omens-deck: 0 left, 3 drawn"
    )
    cli("deck", "shuffle", "omens-deck")
    assert cli("deck", "status", "omens-deck").out.startswith(
        "mini-system.omens-deck: 3 left, 0 drawn"
    )
    joker_deck = cli("deck", "draw", "action-deck", "54")
    assert "a Joker: reshuffle after this round" in joker_deck.out
    cli("bag", "fill", "initiative", "--with", "enemy=2")
    drawn = cli("bag", "draw", "initiative", "5")
    assert "end-of-round: the round ends" in drawn.out
    cli("undo")
    assert cli("bag", "status", "initiative").out.startswith(
        "mini-system.initiative: 5 left, 0 drawn"
    )
    assert cli("replay").out.startswith("✔ 4 rolls reproduced exactly")


def test_tables_can_remember_the_last_result(home: Path) -> None:
    packs = PackLibrary(resolve_config(home=str(home))).resolve(["mini-system"])
    find = finder(packs)
    winter = find("winter", "")
    first = TableRoller(find, RollContext(default_registry(), PhysicalFaces(["6"])), {})
    assert first.roll(winter).text == "Extreme" and first.picked == {"mini-system.winter": "6"}
    second = TableRoller(find, RollContext(default_registry(), PhysicalFaces(["6"])), first.picked)
    twice = second.roll(winter)
    assert twice.text == "Catastrophic" and twice.data == {"travel": "impossible"}
    assert twice.note_lines == ["Extreme twice in a row: Catastrophic"]


def test_table_memory_is_kept_per_campaign(cli: Cli, home: Path) -> None:
    setup(cli)
    cli("table", "roll", "winter")
    memory = home / "worlds/vale/campaigns/run/state/tables.yaml"
    assert memory.is_file() and "mini-system.winter" in memory.read_text()
    assert "remember mini-system.winter" in cli("history").out


def test_a_crucible_reads_both_ways(cli: Cli) -> None:
    cli("world", "new", "wild", "--system", "grimwild-lite")
    seen_pairs = 0
    for _ in range(12):
        rolled = json.loads(cli("table", "roll", "gm-crucible", "--format", "json").out)
        result = rolled["results"][0]
        text = result["text"]
        first, _, second = text.partition(" · or ")
        if second:  # 31 also reads as 13: the two words, swapped
            a, b = first.split("-")
            assert second == f"{b}-{a}"
            seen_pairs += 1
    assert seen_pairs > 0
