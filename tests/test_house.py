"""House rules: overrides by scope, schema extensions, settings, content templates."""

import json

from tests.conftest import Cli

PATCH = '{"entries": {"1-2": "Ash fall", "3-4": null, "5": null, "6": null, "3-6": "Smoke"}}'


def test_a_world_override_changes_that_world_only(cli: Cli) -> None:
    cli("world", "new", "ash", "--system", "mini-system")
    cli("world", "new", "green", "--system", "mini-system", "--no-use")
    done = cli("override", "add", "table", "weather", "--data", PATCH, "--reason", "volcano world")
    assert done.code == 0 and "overridden for this world" in done.out
    assert "- 3-6: Smoke" in cli("table", "show", "weather").out
    assert "- 5: Storm" in cli("table", "show", "weather", "--world", "green").out
    rolled = json.loads(cli("table", "roll", "weather", "--format", "json").out)
    assert rolled["text"] in ("Ash fall", "Smoke")
    assert "- world: table mini-system.weather — volcano world" in cli("override", "list").out
    diff = cli("override", "diff", "table", "weather").out
    assert '- entries.1-2: "Clear" → "Ash fall"' in diff
    assert "override table mini-system.weather (world) — reason: volcano world" in cli("audit").out
    assert cli("override", "remove", "table", "weather").code == 0
    assert "- 5: Storm" in cli("table", "show", "weather").out


def test_house_rules_are_validated(cli: Cli) -> None:
    cli("world", "new", "ash", "--system", "mini-system")
    broken = cli("override", "add", "table", "weather", "--data", '{"entries": {"6": null}}')
    assert broken.code == 1 and "d6 can roll 6, which no entry covers" in broken.err
    assert cli("override", "add", "table", "nope", "--data", "{}").code == 1


def test_campaign_overrides_beat_world_ones(cli: Cli) -> None:
    cli("world", "new", "ash", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("override", "add", "check", "save", "--data", '{"auto": {"1": "failure"}}')
    cli(
        "override",
        "add",
        "check",
        "save",
        "--data",
        '{"auto": {"1": "success", "2": "success"}}',
        "--scope",
        "campaign",
    )
    shown = json.loads(cli("rules", "show", "save", "--format", "json").out)
    assert shown["data"]["auto"] == {"1": "success", "20": "failure", "2": "success"}


def test_schema_extend_and_settings(cli: Cli) -> None:
    cli("world", "new", "ash", "--system", "mini-system")
    cli("campaign", "new", "run")
    extended = cli(
        "schema",
        "extend",
        "pc",
        "--field",
        "reputation=counter",
        "--field",
        'sanity={"kind": "resource"}',
    )
    assert extended.code == 0 and "pc gains reputation, sanity" in extended.out
    assert "- `reputation` (mechanics.mini-system): counter" in cli("template", "pc").out
    cli("new", "pc", "Ash", "--set", "reputation=2", "--set", "sanity=5")
    assert "reputation 2" in cli("show", "ash").out
    assert cli("set", "ash", "conditions+=sleepy").code == 1  # strict by default
    assert cli("campaign", "set", "strictness=lenient").code == 0
    lenient = cli("set", "ash", "conditions+=sleepy")
    assert lenient.code == 0 and lenient.out.count("warning:") == 1
    assert cli("campaign", "set", "strictness=chaotic").code == 1
    assert cli("world", "set", "description=Ash and smoke").code == 0


def test_content_templates(cli: Cli) -> None:
    table = cli("template", "table").out
    assert table.startswith("template: table (pack content)") and '"entries"' in table
    assert '"steps"' in cli("template", "action").out
