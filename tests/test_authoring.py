"""Authoring packs: new, add, lint, build, test, import; and the packs guide."""

import json
from pathlib import Path

from didact.packs.author import md_table
from tests.conftest import Cli

MARKDOWN = """| d6 | Name | Mood |
|---|---|---|
| 1-2 | Ann | glum |
| 3–4 | Bo | merry |
| 5-6 | Cy | sly |
"""


def test_new_pack_is_valid_and_usable(cli: Cli, home: Path) -> None:
    made = cli("pack", "new", "my-hack", "--name", "My Hack")
    assert made.code == 0 and "✔ created pack my-hack" in made.out
    assert (home / "packs/my-hack/0.1.0/pack.yaml").is_file()
    assert "- my-hack 0.1.0 · system · My Hack [installed]" in cli("pack", "list").out
    assert cli("pack", "validate", "my-hack").out.startswith("✔ ok: my-hack 0.1.0")
    cli("world", "new", "vale", "--system", "my-hack")
    assert "didact do my-hack.example-save" in cli("rules", "show", "example-save").out
    assert cli("pack", "new", "my-hack").code == 1  # already there


def test_add_items_from_json(cli: Cli, home: Path) -> None:
    cli("pack", "new", "my-hack")
    good = cli(
        "pack",
        "add",
        "my-hack",
        "table",
        "--data",
        '{"table": "fog", "dice": "d6", "entries": {"1-6": "Fog"}}',
    )
    assert good.code == 0 and (home / "packs/my-hack/0.1.0/tables/fog.yaml").is_file()
    again = cli(
        "pack", "add", "my-hack", "table", "--data", '{"table": "fog", "entries": {"1-6": "Mist"}}'
    )
    assert again.code == 1 and "already exists" in again.err
    gap = cli(
        "pack",
        "add",
        "my-hack",
        "table",
        "--data",
        '{"table": "bad", "dice": "d6", "entries": {"1-3": "x"}}',
    )
    assert gap.code == 1 and "d6 can roll 4, 5, 6, which no entry covers" in gap.err
    missing = cli("pack", "add", "my-hack", "check", "--data", '{"roll": "d20"}')
    assert missing.code == 1 and "a check needs `check`" in missing.err
    assert cli("pack", "add", "my-hack", "spell", "--data", "{}").code == 1


def test_markdown_tables() -> None:
    plain = md_table(MARKDOWN, "names", None)
    entries = plain["entries"]
    assert plain["dice"] == "d6" and isinstance(entries, dict)
    assert entries["3-4"] == {"text": "Bo", "data": {"mood": "merry"}}
    split = md_table(MARKDOWN, "names", None, columns=True)
    columns = split["entries"]
    assert split["columns"] == ["name", "mood"] and isinstance(columns, dict)
    assert columns["1-2"] == ["Ann", "glum"]


def test_import_lint_build(cli: Cli, home: Path, tmp_path: Path) -> None:
    cli("pack", "new", "my-hack")
    source = tmp_path / "names.md"
    source.write_text(MARKDOWN, encoding="utf-8")
    shown = cli("pack", "import", str(source), "--id", "names")
    assert shown.out.startswith("```yaml\ntable: names\ndice: d6")
    assert cli("pack", "import", str(source), "--id", "names", "--into", "my-hack").code == 0
    lint = cli("pack", "lint", "my-hack").out
    assert lint.startswith("✔ ok: my-hack") and "table names has no `source`" in lint
    built = cli("pack", "build", "my-hack")
    path = Path(built.out.split("→ ")[1].strip())
    bundle = json.loads(path.read_text())
    assert "names" in bundle["items"]["table"] and bundle["manifest"]["id"] == "my-hack"


def test_pack_tests_run_and_fail_loudly(cli: Cli, home: Path) -> None:
    ok = cli("pack", "test", "mini-system")
    assert (
        ok.code == 0
        and ok.out.startswith("mini-system: 4/4 tests passed")
        and "✔ play: 7 commands ran" in ok.out
    )
    cli("pack", "new", "my-hack")
    tests = home / "packs/my-hack/0.1.0/tests/t.yaml"
    tests.write_text(
        "test: wrong\nexpr: '1 + 1'\nexpect: 3\n---\n"
        "test: broken-script\nscript: ['do nothing-here']\n"
    )
    bad = cli("pack", "test", "my-hack")
    assert bad.code == 1 and "✘ wrong: expected 3, got 2" in bad.out
    assert "✘ broken-script: step 1 `do nothing-here` failed" in bad.out


def test_the_packs_guide(cli: Cli) -> None:
    guide = cli("guide", "packs").out
    assert guide.startswith("# Packs") and "## From rulebook to pack: the checklist" in guide
