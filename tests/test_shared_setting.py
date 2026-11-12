"""A setting written for two systems (the `shared-setting` fixture, for `role-lite` or
`mini-system`): `compendium import` narrowed by tags, each entry's `mechanics.<system>` block
checked by `pack validate` against that system's sheet, and a top-level key beside an entry's own
block: what the block says stands, and the top-level key keeps its core meaning."""

import json
from pathlib import Path
from typing import Any

from didact.core import i18n
from didact.core.i18n import _
from tests.conftest import Cli


def setup(cli: Cli, world: str = "w") -> None:
    assert cli("world", "new", world, "--system", "role-lite", "--seed", "shared").code == 0
    assert cli("pack", "enable", "shared-setting").code == 0
    assert cli("campaign", "new", f"{world}-c", "--seed", "shared").code == 0


def _record(cli: Cli, ref: str, *where: str) -> Any:  # parsed JSON, read freely in tests
    shown = cli("show", ref, *where, "--gm", "--format", "json")
    assert shown.code == 0, shown.err
    return json.loads(shown.out)


def _created(cli: Cli, *argv: str) -> list[str]:
    done = cli("compendium", "import", "shared-setting", *argv, "--format", "json")
    assert done.code == 0, done.err
    return sorted(json.loads(done.out).get("created", []))


def test_an_import_takes_the_entries_with_every_tag_given(cli: Cli) -> None:
    setup(cli)
    preview = cli("compendium", "import", "shared-setting", "--tag", "park", "--dry-run").out
    assert "dry run: imported 4 records from shared-setting" in preview
    assert "+ create worlds/w/loc/the-gate.md" in preview and "the-dam" not in preview
    assert cli("show", "loc:the-gate").code == 1  # a dry run keeps nothing
    assert _created(cli, "--tag", "park", "--tag", "PLACE") == ["loc:the-gate"]  # both of them
    assert _created(cli, "--type", "npc", "--tag", "park") == ["npc:bram", "npc:nell"]
    nothing = cli("compendium", "import", "shared-setting", "--tag", "x").out
    assert "shared-setting has no entries to import" in nothing
    assert _created(cli) == ["loc:the-dam", "loc:the-park", "npc:gil"]  # the rest


def test_validate_checks_each_systems_block_against_its_sheet(cli: Cli, tmp_path: Path) -> None:
    checked = cli("pack", "validate", "shared-setting")
    assert checked.code == 0 and "✔ ok: shared-setting 0.1.0" in checked.out
    assert (
        "note: compendium/people.yaml:16: 1 entry's `mechanics.absent-lite` block isn't checked: "
        "there's no absent-lite pack here" in checked.out
    )
    assert (
        "note: compendium/people.yaml:11: 1 entry's bare `role` goes to role-lite's npc field "
        "(as `set` puts it), not core's: write it under `fields:` or `mechanics:`" in checked.out
    )  # Nell's; Bram's own block says its role, and Gil's is under `fields:`
    pack = tmp_path / "bad-setting"
    (pack / "compendium").mkdir(parents=True)
    (pack / "pack.yaml").write_text(
        "id: bad-setting\nname: B\nkind: setting\nversion: 0.1.0\nrequires: {packs: [core]}\n"
    )
    (pack / "compendium" / "x.yaml").write_text(
        "id: brute\ntype: npc\nname: Brute\n"
        "mechanics:\n  role-lite: {role: wizard, hp: lots, mana: 3}\n  mini-system: {hp: roll}\n"
    )
    out = cli("pack", "validate", str(pack)).out
    assert "✘ 3 errors" in out and "compendium/x.yaml:1: brute: role-lite.hp" in out
    assert "role-lite.role" in out and "role-lite.mana: not a" in out  # its sheet's own words
    assert "what role-lite's npc takes: `didact template npc` in a world that plays it" in out
    assert "mini-system" not in out  # a value to roll is rolled at spawn


def test_validate_says_what_each_problem_is_in_the_language_in_use(
    cli: Cli, monkeypatch: Any
) -> None:
    monkeypatch.setenv("DIDACT_LANG", "de")
    with i18n.use("de"):
        note = _("note: {note}", note="compendium/people.yaml:16")
    assert note != "note: compendium/people.yaml:16"  # the catalog has it
    assert f"  - {note}" in cli("pack", "validate", "shared-setting").out
    shown = json.loads(cli("pack", "validate", "shared-setting", "--format", "json").out)
    severities = {p["severity"] for p in shown["packs"][0]["problems"]}
    assert severities == {"note"}  # the data keeps it as it is


def test_an_entrys_own_block_stands_beside_its_top_level_key(cli: Cli) -> None:
    setup(cli)
    assert cli("spawn", "shared-setting.bram").code == 0
    bram = _record(cli, "npc:bram")
    assert bram["fields"]["role"] == "head of the dockers"  # core's: its place in the world
    assert bram["mechanics"]["role-lite"] == {"role": "brute", "hp": {"value": 4, "max": 4}}
    _created(cli, "--type", "npc")
    assert _record(cli, "npc:nell")["mechanics"]["role-lite"]["role"] == "tactician"  # as `set`
    assert _record(cli, "npc:gil")["fields"]["role"] == "the mayor's right hand"  # `fields:`
    described = '{"role": "innkeeper", "mechanics": {"role-lite": {"role": "tactician"}}}'
    assert cli("new", "npc", "Old Tom", "--data", described).code == 0
    tom = _record(cli, "old-tom")
    assert tom["fields"]["role"] == "innkeeper"  # `new --data` reads a description the same way
    assert tom["mechanics"]["role-lite"]["role"] == "tactician"
    edited = '{"role": "ferryman", "mechanics": {"role-lite": {"role": "brute"}}}'
    assert cli("edit", "old-tom", "--data", edited).code == 0
    tom = _record(cli, "old-tom")
    assert (tom["fields"]["role"], tom["mechanics"]["role-lite"]["role"]) == ("ferryman", "brute")
    assert cli("set", "old-tom", "role=tactician").code == 0  # a key alone: the system's, as ever
    assert _record(cli, "old-tom")["mechanics"]["role-lite"]["role"] == "tactician"


def test_a_draft_and_a_rule_start_a_record_from_an_entry_the_same_way(cli: Cli) -> None:
    setup(cli)
    drafted = cli("gen", "run", "shared-setting.meet", "--auto").out
    draft = drafted.rsplit("`didact gen commit ", 1)[1].split("`", 1)[0]
    assert cli("gen", "commit", draft).code == 0
    setup(cli, "w2")  # a world of its own, for the rule to make Bram anew
    assert "Bram joins." in cli("do", "recruit").out  # a rule's `entity:` step
    for world in ("w", "w2"):
        bram = _record(cli, "npc:bram", "--world", world)
        assert bram["fields"]["role"] == "head of the dockers"
        assert bram["mechanics"]["role-lite"]["role"] == "brute"
