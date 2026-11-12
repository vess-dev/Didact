"""Packs: discovery, validation with file:line errors, enabling, dice, extends."""

import json
from pathlib import Path

import pytest

from didact.core.config import resolve_config
from didact.core.errors import ConflictError, InvalidError, NotFoundError
from didact.packs.build import build
from didact.packs.library import PackLibrary
from didact.packs.versions import Version, satisfies
from tests.conftest import FIXTURE_PACKS, Cli


def library(home: Path) -> PackLibrary:
    return PackLibrary(resolve_config(home=str(home)))


def test_versions() -> None:
    assert Version.parse("1.2") == Version(1, 2, 0)
    assert Version.parse("1.0.0-beta") < Version.parse("1.0.0") < Version.parse("1.0.1")
    assert satisfies("0.3.0", ">=0.1, <1") and not satisfies("1.0.0", ">=0.1, <1")
    assert satisfies("1.4.0", "~=1.2") and not satisfies("2.0.0", "~=1.2")
    assert satisfies("0.1.0", "")


def test_list_and_info(cli: Cli, lucky: Path) -> None:
    listing = cli("pack", "list").out
    assert "- core 1.0.0 · base · Didact core [bundled]  ← enabled" in listing
    assert "- lucky 0.1.0 · supplement · Lucky (test pack) [path]" in listing
    info = cli("pack", "info", "lucky").out
    assert "contains: 1 named dice, 1 dice macros" in info
    assert "plugins: plugins/lucky.py (trusted)" in info
    assert "# Lucky" in cli("pack", "info", "lucky", "--detail", "full").out
    missing = cli("pack", "info", "luckky")
    assert missing.code == 1 and "did you mean lucky?" in missing.err


def test_broken_packs_get_precise_errors(cli: Cli, lucky: Path) -> None:
    result = cli("pack", "validate", "broken")
    assert result.code == 1
    assert "pack.yaml:3: `kind` must be one of: base, system, oracle" in result.out
    assert "pack.yaml:5: unknown key `colour`" in result.out
    assert "tables/bad.yaml:5: invalid table id 'Not An Id'" in result.out
    assert "rules/x.yaml:1: can't tell what kind of rules item this is" in result.out
    assert cli("pack", "validate", "lucky").out.startswith("✔ ok: lucky 0.1.0")


def test_bad_yaml_points_at_the_line(tmp_path: Path) -> None:
    pack = tmp_path / "p"
    (pack / "tables").mkdir(parents=True)
    (pack / "pack.yaml").write_text("id: p\nname: P\nkind: system\nversion: 0.1.0\n")
    (pack / "tables" / "t.yaml").write_text("table: t\ndice: d6\nentries: {1-6: [unclosed\n")
    result = build(pack)
    assert not result.ok
    assert result.errors[0].text().startswith("tables/t.yaml:3: invalid YAML: expected ',' or ']'")
    assert any(p.severity == "warning" and "no guide" in p.message for p in result.problems)


def test_enabling_packs_brings_their_dice(cli: Cli, home: Path, lucky: Path) -> None:
    cli("world", "new", "vale")
    cli("campaign", "new", "run")
    assert cli("roll", "3d6~").code == 1  # the pack isn't enabled yet
    enabled = cli("pack", "enable", "lucky")
    assert enabled.code == 0 and "enabled lucky in campaign:run (packs: lucky)" in enabled.out
    charmed = json.loads(cli("roll", "3d6~", "--got", "6,2,6,3,4", "--format", "json").out)
    assert charmed["value"] == 21
    assert cli("roll", "d[clover]", "--got", "hit+hit").out.startswith("#r2 1d[clover] → [hit+hit]")
    assert "lucky.best(" in cli("roll", "lucky.best(d6)").out
    assert cli("pack", "enable", "nope").code == 1
    cli("pack", "disable", "lucky")
    assert cli("roll", "3d6~").code == 1


def test_world_scope_packs(cli: Cli, home: Path, lucky: Path) -> None:
    cli("world", "new", "vale")
    cli("campaign", "new", "run")
    assert "in world:vale" in cli("pack", "enable", "lucky", "--scope", "world").out
    assert "lucky" in (home / "worlds/vale/world.yaml").read_text()
    assert cli("roll", "3d6~").code == 0


def test_extends_resolution(home: Path) -> None:
    lib = library(home)
    packs = lib.resolve(["hack-b"])
    assert packs.ids == ["base-a", "hack-b"]  # the base loads first
    weather = packs.find("table", "weather")
    assert weather.pack == "hack-b" and "3-5" in json.dumps(weather.data)
    assert packs.find("table", "base-a.weather").pack == "hack-b"  # the hack replaces it
    assert packs.find("table", "omens").pack == "base-a"  # inherited unchanged
    assert [i.qualified for i in packs.all("table")] == ["base-a.omens", "hack-b.weather"]
    with pytest.raises(NotFoundError, match="no table 'wether'") as caught:
        packs.find("table", "wether")
    assert caught.value.hint == "did you mean weather, hack-b.weather?"


def test_requirements_are_checked(home: Path, tmp_path: Path) -> None:
    needy = tmp_path / "needy"
    needy.mkdir()
    (needy / "pack.yaml").write_text(
        "id: needy\nname: Needy\nkind: supplement\nversion: 0.1.0\n"
        "requires: {packs: [base-a >=2]}\n"
    )
    lib = PackLibrary(resolve_config(home=str(home)), extra=[tmp_path])
    with pytest.raises(NotFoundError, match="no version of pack 'base-a' matches '>=2'"):
        lib.resolve(["needy"])
    loop = tmp_path / "loop"
    loop.mkdir()
    (loop / "pack.yaml").write_text(
        "id: loop\nname: L\nkind: supplement\nversion: 0.1.0\nextends: [loop]\n"
    )
    lib = PackLibrary(resolve_config(home=str(home)), extra=[tmp_path])
    with pytest.raises(InvalidError, match="circle"):
        lib.resolve(["loop"])
    _ = ConflictError  # (version conflicts are covered once packs pin versions)


def test_bundles_are_cached_and_rebuilt_on_change(home: Path, tmp_path: Path) -> None:
    pack = tmp_path / "live"
    (pack / "tables").mkdir(parents=True)
    (pack / "pack.yaml").write_text("id: live\nname: Live\nkind: system\nversion: 0.1.0\n")
    table = pack / "tables" / "t.yaml"
    table.write_text("table: t\ndice: d4\nentries: {1-4: old}\n")
    first = PackLibrary(resolve_config(home=str(home)), extra=[tmp_path]).resolve(["live"])
    assert "old" in json.dumps(first.find("table", "t").data)
    table.write_text("table: t\ndice: d4\nentries: {1-4: new, }\n")
    second = PackLibrary(resolve_config(home=str(home)), extra=[tmp_path]).resolve(["live"])
    assert "new" in json.dumps(second.find("table", "t").data)
    assert FIXTURE_PACKS.is_dir()


def test_core_and_the_system_stay_and_uninstall_says_what_uses_a_pack(
    cli: Cli, home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lucky: Path
) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    assert "core is always in use" in cli("pack", "disable", "core").err
    assert "is this world's game system, for good" in cli("pack", "disable", "mini-system").err
    assert "can't be removed" in cli("pack", "uninstall", "core").err
    assert "isn't installed in this library" in cli("pack", "uninstall", "lucky").err
    assert cli("pack", "export", "lucky", "--to", str(tmp_path)).code == 0
    assert cli("pack", "install", str(tmp_path / "lucky-0.1.0.didactpack")).code == 0
    monkeypatch.setenv("DIDACT_PACK_PATH", str(FIXTURE_PACKS))  # now the only copy is installed
    cli("pack", "trust", "lucky", "--yes")
    cli("pack", "enable", "lucky")
    preview = cli("pack", "uninstall", "lucky")
    assert "in use by: campaign run (enabled, pinned)" in preview.out
    assert "can't be undone" in preview.out
    refused = cli("pack", "uninstall", "lucky", "--yes")
    assert refused.code == 1 and "pack disable lucky" in refused.err
    assert cli("pack", "uninstall", "lucky", "--yes", "--force").code == 0
    assert not (home / "packs/lucky").exists() or not any((home / "packs/lucky").iterdir())


def test_a_pack_test_with_broken_quoting_is_reported(cli: Cli, tmp_path: Path) -> None:
    pack = tmp_path / "quotes"
    (pack / "tests").mkdir(parents=True)
    (pack / "pack.yaml").write_text("id: quotes\nname: Q\nkind: supplement\nversion: 0.1.0\n")
    (pack / "tests" / "t.yaml").write_text('test: quoted\nscript:\n  - run: "roll \'d6"\n')
    tested = cli("pack", "test", str(pack))
    assert (
        tested.code == 1 and "step 1 `roll 'd6` can't be read: No closing quotation" in tested.out
    )


def test_a_script_step_can_expect_text_not_printed_and_a_command_to_fail(
    cli: Cli, tmp_path: Path
) -> None:
    pack = tmp_path / "steps"
    (pack / "tests").mkdir(parents=True)
    (pack / "pack.yaml").write_text("id: steps\nname: S\nkind: supplement\nversion: 0.1.0\n")
    (pack / "tests" / "t.yaml").write_text(
        "test: holds\nscript:\n"
        "  - run: guide\n    expect: packs\n    expect_not: [no-such-guide, '`spells`']\n"
        "  - run: guide no-such-guide\n    fails: true\n    expect: \"no guide 'no-such-guide'\"\n"
        "---\ntest: printed\nscript:\n  - run: guide\n    expect_not: packs\n"
        "---\ntest: ran\nscript:\n  - run: guide packs\n    fails: true\n"
        "---\ntest: refused\nscript:\n  - run: guide no-such-guide\n    expect: guides\n"
    )
    tested = cli("pack", "test", str(pack))
    assert tested.code == 1 and "steps: 1/4 tests passed" in tested.out
    assert "✔ holds: 2 commands ran" in tested.out
    assert "✘ printed: step 1 `guide` printed 'packs'" in tested.out
    assert "✘ ran: step 1 `guide packs` didn't fail" in tested.out
    assert "✘ refused: step 1 `guide no-such-guide` failed: error (not_found)" in tested.out


def test_script_steps_are_validated(cli: Cli, tmp_path: Path) -> None:
    pack = tmp_path / "steps"
    (pack / "tests").mkdir(parents=True)
    (pack / "pack.yaml").write_text("id: steps\nname: S\nkind: supplement\nversion: 0.1.0\n")
    (pack / "tests" / "t.yaml").write_text(
        "test: wrong\nscript:\n  - run: guide\n    fails: 'yes'\n"
        "  - run: guide\n    expect_not: [1, 2]\n  - run: guide\n    expect_nothing: packs\n"
        "  - run: guide\n    expect: packs\n    expect_not: dice\n    fails: false\n"
    )
    checked = cli("pack", "validate", str(pack)).out
    step = "a step is a command, or {run: …, expect: …, expect_not: …, fails: true}"
    assert checked.count(step) == 3  # the last step is right
    assert all(f"tests/t.yaml:{line}: {step}" in checked for line in (3, 5, 7))
