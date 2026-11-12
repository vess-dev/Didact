"""The Claude Code plugin stays in step with the commands it teaches."""

import importlib.util
import json
import re
from pathlib import Path

from didact.commands import load_all
from didact.commands.registry import REGISTRY
from tests.conftest import Cli

PLUGIN = Path(__file__).parent.parent / "claude"
SKILL = PLUGIN / "skills" / "didact" / "SKILL.md"


def test_the_command_reference_is_generated_from_the_registry(cli: Cli) -> None:
    listed = (PLUGIN / "skills" / "didact" / "references" / "commands.md").read_text()
    assert listed == cli("commands").out, "run `make skill` to regenerate it"


def mentioned(text: str) -> list[str]:
    """`didact …` in inline code, and lines of code blocks that start with `didact`."""
    inline = re.findall(r"`didact ([^`]+)`", text)
    blocks = re.findall(r"^(?:uv run )?didact (.+?)(?:\s+#.*)?$", text, re.MULTILINE)
    return inline + blocks


def test_every_command_the_skill_and_play_guide_mention_exists() -> None:
    load_all()
    names = sorted(REGISTRY, key=len, reverse=True)
    guide = Path(__file__).parent.parent / "src" / "didact" / "guides" / "play.md"
    for doc in (SKILL, guide):
        snippets = mentioned(doc.read_text())
        assert len(snippets) > 20
        for snippet in snippets:
            joined = " ".join(w for w in snippet.split() if not w.startswith(("-", "'", '"')))
            assert any(joined == name or joined.startswith(name + " ") for name in names), (
                f"{doc.name} mentions `didact {snippet}`, which isn't a command"
            )


def test_the_skill_is_short_and_introduces_itself() -> None:
    text = SKILL.read_text()
    assert text.startswith("---\nname: didact\ndescription: ")
    assert len(text.splitlines()) < 500


def test_the_hooks_capture_brief_and_approve() -> None:
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"]
    assert set(hooks) == {"SessionStart", "UserPromptSubmit", "Stop", "PreToolUse"}
    assert "capture --hook" in hooks["UserPromptSubmit"][0]["hooks"][0]["command"]
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    assert manifest["name"] == "didact"


def test_only_plain_didact_commands_are_approved() -> None:
    spec = importlib.util.spec_from_file_location("approve", PLUGIN / "hooks" / "approve.py")
    assert spec is not None and spec.loader is not None
    approve = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(approve)
    allowed = ["didact roll '6d10>=8'", "didact show freya --gm", "didact log note 'a; b'"]
    refused = [
        "didact roll d20; rm -rf ~",
        "didact find x | head",
        'didact log note "$(whoami)"',
        "didact log note `id`",
        "didact roll d20 > out.txt",
        "didact set a hp=1 && didact brief",
        "/tmp/evil/didact brief",
        "echo didact",
        "didact log note 'unbalanced",
    ]
    assert all(approve.plain_didact(c) for c in allowed)
    assert not any(approve.plain_didact(c) for c in refused)


def test_capture_in_a_hook_prints_nothing(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("session", "start")
    payload = json.dumps({"prompt": "I open the door", "session_id": "abc"})
    quiet = cli("capture", "--hook", "--text", payload)
    assert quiet.code == 0 and quiet.out == ""
    assert "I open the door" in cli("transcript").out


QUICK = {"sheet", "recap", "roll", "rules", "map", "undo"}  # the player's quick commands
WORKFLOWS = {"start", "end", "new-campaign"}


def test_the_plugins_skills_and_marketplace_entry_are_well_formed() -> None:
    from ruamel.yaml import YAML

    found = {p.parent.name: p for p in (PLUGIN / "skills").glob("*/SKILL.md")}
    assert QUICK | WORKFLOWS | {"didact"} <= set(found)
    for name, path in found.items():
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\n"), name
        meta = YAML(typ="safe").load(text.split("---\n")[1])
        assert meta["name"] == name and meta["description"], name
        assert (meta.get("disable-model-invocation") is True) == (name in QUICK), name
        for command in re.findall(r"!`([^`]+)`", text):  # injected commands exist
            words = command.split('didact"', 1)[-1].split()
            assert any(
                spec.name == " ".join(words[:n]) for n in (1, 2) for spec in REGISTRY.values()
            ), command
    market = json.loads((PLUGIN.parent / ".claude-plugin" / "marketplace.json").read_text())
    entry = next(p for p in market["plugins"] if p["name"] == "didact")
    assert (PLUGIN.parent / entry["source"] / ".claude-plugin" / "plugin.json").is_file()


def test_the_guides_are_copied_into_the_skill() -> None:
    guides = Path(__file__).parent.parent / "src" / "didact" / "guides"
    for guide in guides.glob("*.md"):
        copy = PLUGIN / "skills" / "didact" / "references" / guide.name
        assert copy.is_file() and copy.read_text() == guide.read_text(), "run `make skill`"
