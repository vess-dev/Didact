"""A hack drops what it has no use for in the pack it extends (`hides` in its manifest), and its
items, reference sections, glossary terms and name tables stand in for the base's: the
`hide-base`, `hide-hack` and `hide-heir` fixtures."""

import shutil
from pathlib import Path

import pytest

from didact.core.config import resolve_config
from didact.core.errors import NotFoundError
from didact.packs.build import build
from didact.packs.library import PackLibrary, PackSet
from didact.services import reference
from tests.conftest import FIXTURE_PACKS, Cli


def _packs(home: Path, pack_id: str) -> PackSet:
    return PackLibrary(resolve_config(home=str(home))).resolve([pack_id])


def _ids(packs: PackSet, kind: str) -> list[str]:
    return [item.qualified for item in packs.all(kind) if item.pack != "core"]


def _world(cli: Cli) -> None:
    assert cli("world", "new", "dust", "--system", "hide-hack", "--seed", "dust").code == 0
    assert cli("campaign", "new", "c", "--seed", "dust").code == 0


def test_a_hack_hides_its_bases_items_by_pattern(home: Path) -> None:
    packs = _packs(home, "hide-hack")
    # `spell-*` goes but for `!spell-ice`, and `places` goes; the hack's own replace or add
    assert _ids(packs, "table") == ["hide-base.spell-ice", "hide-hack.names", "hide-hack.weather"]
    # `*` hides every entry of the base but the one kept (`!rope`) and the one replaced (wolf)
    assert _ids(packs, "entry") == ["hide-base.rope", "hide-hack.mole", "hide-hack.wolf"]
    assert packs.find("entry", "hide-base.wolf").pack == "hide-hack"
    with pytest.raises(NotFoundError, match=r"no table 'hide-base\.spell-fire'"):
        packs.find("table", "hide-base.spell-fire")
    alone = _packs(home, "hide-base")  # the base by itself is whole
    assert "hide-base.spell-fire" in _ids(alone, "table")
    assert "hide-base.ghost" in _ids(alone, "entry")


def test_a_hacks_sections_and_terms_stand_in_for_its_bases(home: Path) -> None:
    packs = _packs(home, "hide-hack")
    sections = reference.sections(packs)
    assert [(s.pack, s.id) for s in sections] == [("hide-hack", "combat")]  # `magic` is hidden
    assert "armor counts twice" in sections[0].body
    assert [(t.pack, t.term) for t in reference.terms(packs)] == [("hide-hack", "wound")]
    alone = _packs(home, "hide-base")
    assert sorted(s.id for s in reference.sections(alone)) == ["combat", "magic"]
    assert sorted(t.term for t in reference.terms(alone)) == ["spell", "wound"]


def test_a_hack_of_a_hack_replaces_and_hides_down_the_line(home: Path) -> None:
    packs = _packs(home, "hide-heir")
    assert _ids(packs, "table") == ["hide-hack.names", "hide-heir.weather"]  # one weather: the last
    assert packs.find("table", "hide-base.weather").pack == "hide-heir"
    assert _ids(packs, "entry") == ["hide-base.rope", "hide-hack.wolf"]  # the heir hides the mole


def test_what_a_hack_hides_is_gone_from_play(cli: Cli) -> None:
    _world(cli)
    assert cli("table", "roll", "spell-ice").code == 0
    gone = cli("table", "roll", "hide-base.spell-fire")
    assert gone.code != 0 and "no table 'hide-base.spell-fire'" in gone.err
    assert "hide-base.spell-fire" not in cli("table", "list").out
    assert "nothing in the compendium matches" in cli("compendium", "find", "ghost").out
    assert "A hairless wolf." in cli("compendium", "show", "wolf").out
    combat = cli("rules", "lookup", "combat").out
    assert "armor counts twice" in combat and "hide-base" not in combat
    assert "no rules text about 'magic'" in cli("rules", "lookup", "magic").out
    assert (
        cli("define", "wound").out.strip() == "**wound** (hide-hack): Harm that lasts, and glows."
    )
    assert "no glossary term 'spell'" in cli("define", "spell").err


def test_a_hacks_name_tables_stand_in_for_its_bases(cli: Cli) -> None:
    _world(cli)
    named = cli("name", "npc")
    assert named.code == 0 and ("Rust" in named.out or "Slag" in named.out)
    place = cli("name", "place")  # the base's kinds don't come along: its tables may be hidden
    assert place.code != 0
    assert "no name tables for 'place' in the enabled packs (kinds: npc)" in place.err


def test_validate_warns_about_a_pattern_that_hides_nothing(cli: Cli, tmp_path: Path) -> None:
    hack = tmp_path / "hide-hack"
    shutil.copytree(FIXTURE_PACKS / "hide-hack", hack)
    manifest = hack / "pack.yaml"
    manifest.write_text(manifest.read_text().replace('"spell-*"', '"spel-*"'))
    checked = cli("pack", "validate", str(hack))
    assert checked.code == 0 and "✔ ok, 1 warning: hide-hack 0.1.0" in checked.out
    assert (
        "pack.yaml: `hides` table pattern 'spel-*' matches nothing in hide-base "
        "(fix: remove it or check the spelling)"
    ) in checked.out
    assert "warning" not in cli("pack", "validate", "hide-hack").out


def test_hides_is_for_a_hack_and_names_kinds(tmp_path: Path) -> None:
    pack = tmp_path / "lone"
    pack.mkdir()
    (pack / "GUIDE.md").write_text("# Lone\n")
    head = "id: lone\nname: Lone\nkind: system\nversion: 0.1.0\n"
    (pack / "pack.yaml").write_text(head + "hides: {table: [x]}\n")
    assert "name it in `extends`" in " ".join(p.message for p in build(pack).problems)
    (pack / "pack.yaml").write_text(head + "extends: [hide-base]\nhides: {tables: [x]}\n")
    assert "unknown kind(s) in `hides`: tables" in " ".join(p.message for p in build(pack).problems)


def test_pack_info_says_what_a_hack_hides(cli: Cli) -> None:
    shown = cli("pack", "info", "hide-hack").out
    hides = (
        "hides: table: spell-*, !spell-ice, places; entry: *, !rope; reference: magic; term: spell"
    )
    assert hides in shown
