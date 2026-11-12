"""Packs made from a library: homebrew as a supplement (`pack new --from-overlay`) and a world
as a setting (`world export --as setting`), each brought back into another world."""

import json
from pathlib import Path

from tests.conftest import Cli


def _made(cli: Cli, *argv: str) -> Path:
    result = cli(*argv, "--format", "json")
    assert result.code == 0, result.out + result.err
    data = json.loads(result.out)
    assert not data["problems"], data["problems"]
    return Path(data["path"])


def _world(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("new", "npc", "Old Tom", "--body", "Runs the mill.\n\n## Secrets\nHe is the heir.\n")
    cli("about", "Old Tom", "plan=flee", "looks=tall")
    cli("new", "npc", "Hidden Witch", "--data", '{"knowledge": "secret"}')
    cli("new", "loc", "The Mill")
    cli("link", "Old Tom", "lives-at", "The Mill")
    cli("lore", "add", "Tom owes the witch.", "--keys", "tom, witch", "--scope", "world")
    cli("lore", "add", "The spirit wakes.", "--keys", "spirit", "--sticky", "2", "--scope", "world")
    cli("campaign", "new", "run")
    cli("new", "pc", "Freya", "--fill")
    cli("quest", "new", "Free the spirit")


def test_a_world_becomes_a_setting_another_world_imports(cli: Cli) -> None:
    _world(cli)
    root = _made(cli, "world", "export", "--as", "setting")
    manifest = (root / "pack.yaml").read_text(encoding="utf-8")
    assert "kind: setting" in manifest and "mini-system" in manifest
    assert "redistributable: false" in manifest
    entries = (root / "compendium" / "records.yaml").read_text(encoding="utf-8")
    assert "Old Tom" in entries and "The Mill" in entries and "lives-at" in entries
    for hidden in ("heir", "Hidden Witch", "flee", "Freya", "Free the spirit"):
        assert hidden not in entries, hidden
    assert "looks: tall" in entries  # what players see of the GM's notes
    lore = (root / "lore" / "lore.yaml").read_text(encoding="utf-8")
    assert "Tom owes the witch." in lore and "sticky" not in lore
    cli("world", "new", "dale", "--system", "mini-system")
    assert cli("pack", "enable", "vale-setting").code == 0
    assert cli("compendium", "import", "vale-setting").code == 0
    shown = cli("show", "Old Tom").out
    assert "npc:old-tom · Old Tom (world:dale)" in shown and "lives-at → loc:the-mill" in shown
    assert "Tom owes the witch." in cli("lore", "scan", "we met tom").out


def test_secrets_and_campaigns_come_along_when_asked(cli: Cli, tmp_path: Path) -> None:
    _world(cli)
    root = _made(
        cli, "world", "export", "vale", "--secrets", "--campaigns", "--id", "vale-gm",
        "--dir", str(tmp_path / "gm"),
    )  # fmt: skip
    entries = (root / "compendium" / "records.yaml").read_text(encoding="utf-8")
    assert "heir" in entries and "plan: flee" in entries and "Free the spirit" in entries
    assert "Hidden Witch" in entries and "secret: true" in entries
    assert "Freya" not in entries  # characters never go
    assert cli("world", "export", "--dir", str(root)).code == 1  # not over another pack


def test_homebrew_becomes_a_supplement(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("compendium", "add", "--data", '{"name": "Bog Hag", "type": "monster", "hp": 9}')
    cli("new", "npc", "Wandering Tinker", "--scope", "system:mini-system")
    cli("lore", "add", "Tinkers never lie.", "--keys", "tinker", "--scope", "system")
    shown = cli("pack", "new", "vale-brew", "--from-overlay", "mini-system", "--dry-run")
    assert shown.code == 0 and "dry run: would create vale-brew" in shown.out
    root = _made(cli, "pack", "new", "vale-brew", "--from-overlay", "mini-system")
    assert "Bog Hag" in (root / "compendium" / "bog-hag.yaml").read_text(encoding="utf-8")
    manifest = (root / "pack.yaml").read_text(encoding="utf-8")
    assert "kind: supplement" in manifest and "[core, mini-system]" in manifest
    cli("world", "new", "dale", "--system", "mini-system")
    assert cli("pack", "enable", "vale-brew").code == 0
    assert "Wandering Tinker" in cli("compendium", "show", "vale-brew.wandering-tinker").out


def test_nothing_to_make_a_pack_of_says_so(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    result = cli("pack", "new", "empty", "--from-overlay", "mini-system")
    assert result.code == 1 and "nothing to put in a pack" in result.err
    bare = cli("world", "export")
    assert bare.code == 1 and "nothing to put in a pack" in bare.err
