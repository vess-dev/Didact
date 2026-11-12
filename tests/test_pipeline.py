"""Rulebook to pack (ingest, coverage), adventure content, and convert."""

import json
from pathlib import Path

from didact.packs.ingest import candidates, ranges
from tests.conftest import Cli

BOOK = """# Weather (p. 3)
Roll a d6:
1. Clear skies
2. Rain

3. Storm
4 Fog
Some rules text that isn't a table.
1-2 Amber
3-4 Broken
5-6 Cold
"""


def test_candidate_tables() -> None:
    found = candidates([BOOK])
    assert [len(c.rows) for c in found] == [4, 3]
    assert found[0].rows[0] == ("1", "Clear skies") and found[1].rows[0] == ("1-2", "Amber")
    assert ranges([1, 2, 3, 7, 9, 10]) == "1–3, 7, 9–10"


def test_ingest_writes_a_workspace(cli: Cli, tmp_path: Path) -> None:
    book = tmp_path / "book.md"
    book.write_text(BOOK, encoding="utf-8")
    out = tmp_path / "work"
    result = cli("pack", "ingest", str(book), "--out", str(out))
    assert result.code == 0 and "2 candidate tables" in result.out
    assert (out / "text.md").read_text().startswith("<!-- page 1 -->")
    draft = (out / "candidates" / "p001-1.yaml").read_text()
    assert "table: table-p001-1" in draft and '"Clear skies"' in draft


def test_coverage(cli: Cli, tmp_path: Path) -> None:
    covered = cli("pack", "coverage", "mini-system").out
    assert covered.startswith("mini-system cites 3 pages: 3–4, 6")
    pack = tmp_path / "sized"
    (pack / "tables").mkdir(parents=True)
    (pack / "pack.yaml").write_text(
        "id: sized\nname: S\nkind: system\nversion: 0.1.0\nsource: {pages: 10}\n"
    )
    (pack / "tables" / "t.yaml").write_text(
        "table: t\ndice: d4\nentries: {1-4: x}\nsource: 'p. 2-4'\n"
    )
    report = cli("pack", "coverage", str(pack)).out
    assert "30% of 10 pages; not yet: 1, 5–10" in report
    (pack / "tables" / "u.yaml").write_text(  # every page of a list counts
        "table: u\ndice: d4\nentries: {1-4: x}\nsource: 'p. 6, 8-9'\n"
    )
    assert "60% of 10 pages; not yet: 1, 5, 7, 10" in cli("pack", "coverage", str(pack)).out


def test_adventure_content_keeps_its_secrets(cli: Cli, home: Path) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    added = cli(
        "compendium", "add", "--data", '{"name": "Hidden Vault", "type": "loc", "secret": true}'
    )
    assert added.code == 0
    imported = cli("compendium", "import", "mini-system", "--type", "loc")
    assert "imported 1 record" in imported.out and "1 secret" in imported.out
    vault = json.loads(cli("show", "hidden-vault", "--format", "json").out)
    assert vault["knowledge"] == "secret" and "secret" not in vault.get("fields", {})
    again = cli("compendium", "import", "mini-system", "--type", "loc")
    assert "already there: loc:hidden-vault" in again.out


def test_convert_between_systems(cli: Cli, home: Path) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("spawn", "troll")
    cli("set", "troll", "fields.agility=2")
    plain = cli("convert", "troll", "--to", "yze-lite")
    assert "carried over: agility" in plain.out and "still to decide: strength, stress" in plain.out
    filled = cli("convert", "troll", "--to", "daggerheart-lite", "--fill")
    assert "hope (default), stress (default)" in filled.out
    shown = cli("show", "troll", "--gm", "--format", "json").out  # every system's block
    block = json.loads(shown)["mechanics"]
    assert block["daggerheart-lite"]["hope"] == {"value": 2, "max": 6} and "mini-system" in block
    assert cli("convert", "troll", "--to", "pbta-lite").code == 1  # no npc sheet there
