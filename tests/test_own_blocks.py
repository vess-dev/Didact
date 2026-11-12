"""`pack validate` checks a block naming the pack under validation against that pack as it is
in its folder, not against the library's copy of it (the `self-lite` fixture)."""

import shutil
from pathlib import Path

from tests.conftest import FIXTURE_PACKS, Cli


def _copy(tmp_path: Path, pack_id: str) -> Path:
    folder = tmp_path / pack_id
    shutil.copytree(FIXTURE_PACKS / "self-lite", folder)
    schema = folder / "schemas" / "creatures.yaml"
    schema.write_text(schema.read_text() + "  grit: {kind: int, min: 0}\n")  # a field it adds
    entries = folder / "compendium" / "bestiary.yaml"
    added = "- {id: boar, type: monster, name: Boar, mechanics: {self-lite: {hp: 4, grit: 2}}}\n"
    entries.write_text(entries.read_text() + added)
    if pack_id != "self-lite":
        for path in (folder / "pack.yaml", entries):
            path.write_text(path.read_text().replace("self-lite", pack_id))
    return folder


def test_a_packs_own_blocks_are_checked_against_its_folder(cli: Cli, tmp_path: Path) -> None:
    assert "✔ ok: self-lite 0.1.0" in cli("pack", "validate", "self-lite").out
    newer = cli("pack", "validate", str(_copy(tmp_path, "self-lite")))  # the library's lacks grit
    assert newer.code == 0 and "✔ ok: self-lite 0.1.0" in newer.out
    assert "grit" not in newer.out
    unknown = cli("pack", "validate", str(_copy(tmp_path, "self-new")))  # none in the library
    assert unknown.code == 0 and "isn't checked" not in unknown.out
    wrong = _copy(tmp_path / "wrong", "self-lite")
    entries = wrong / "compendium" / "bestiary.yaml"
    entries.write_text(entries.read_text().replace("grit: 2", "grit: lots"))
    checked = cli("pack", "validate", str(wrong))  # still checked, against its own sheet
    assert checked.code == 1 and "boar: self-lite.grit must be a whole number" in checked.out
