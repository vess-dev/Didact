"""`didact roll`, `rolls`, `replay`, `odds`; the roll log, ids, seeds and undo."""

import json
from pathlib import Path

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale")
    cli("campaign", "new", "withering")
    cli("new", "npc", "Sweeney", "--set", "STR=12", "--set", "hp=6")


def roll_events(home: Path) -> list[dict[str, object]]:
    lines = (home / "log/events.jsonl").read_text(encoding="utf-8").splitlines()
    return [e for e in map(json.loads, lines) if e["kind"] == "roll"]


def test_rolls_without_a_library_are_not_logged(cli: Cli, home: Path) -> None:
    result = cli("roll", "4d6k3")
    assert result.code == 0 and result.out.startswith("#r? 4d6kh3 → [")
    assert "note: read `4d6k3` as `4d6kh3`" in result.out
    assert "not logged" in result.out and not home.exists()


def test_rolls_are_numbered_logged_and_listed(cli: Cli, home: Path) -> None:
    setup(cli)
    first = cli("roll", "2d6", "--reason", "sneak past")
    assert first.out.startswith("#r1 2d6 → [") and first.out.rstrip().endswith("— sneak past")
    assert cli("roll", "d20").out.startswith("#r2 1d20 → [")
    events = roll_events(home)
    assert [e["data"]["roll"] for e in events] == [1, 2]  # type: ignore[index]
    assert events[0]["data"]["scope"] == "campaign:withering"  # type: ignore[index]
    listing = cli("rolls").out
    assert listing.startswith("2 rolls (campaign:withering), newest first:")
    assert "- #r2 1d20" in listing and "- #r1 2d6" in listing
    assert "no changes" not in cli("history").out and "#r" not in cli("history").out


def test_dry_run_only_shows_the_canonical_form(cli: Cli, home: Path) -> None:
    setup(cli)
    assert cli("roll", "4d6d1", "--dry-run").out.strip() == "dry run: would roll `4d6dl1`"
    assert roll_events(home) == []


def test_variables_from_records_and_the_command_line(cli: Cli) -> None:
    setup(cli)
    save = cli("roll", "d20 <= @STR", "--as", "sweeney")
    assert "<= @STR(12) = " in save.out
    assert "@sweeney.STR(12)" in cli("roll", "d20 <= @sweeney.STR").out
    assert "@DEX(9)" in cli("roll", "d20 <= @DEX", "--var", "DEX=9").out
    missing = cli("roll", "d20 <= @DEX")
    assert missing.code == 1 and "unknown variable @DEX" in missing.err
    assert cli("roll", "d20", "--var", "DEX=high").code == 1


def test_physical_dice(cli: Cli, home: Path) -> None:
    setup(cli)
    result = cli("roll", "4d6kh3", "--got", "6,5,3,2")
    assert result.out.strip() == "#r1 4d6kh3 → [6 5 3 (2)] = 14"
    assert roll_events(home)[0]["data"]["got"] == ["6", "5", "3", "2"]  # type: ignore[index]
    extra = cli("roll", "2d6", "--got", "6,3,4")
    assert extra.code == 1 and "didn't use: 4" in extra.err
    short = cli("roll", "d6!", "--got", "6")
    assert short.code == 1 and "ran out of faces" in short.err


def test_a_missing_system_pack_falls_back_to_built_in_dice(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "nope-2e")
    result = cli("roll", "2d6")
    assert result.code == 0
    assert "note: pack dice unavailable (no pack 'nope-2e'); built-in dice only" in result.out


def test_seeds(cli: Cli, home: Path) -> None:
    setup(cli)
    campaign = (home / "worlds/vale/campaigns/withering/campaign.yaml").read_text()
    assert "\nseed: " in campaign
    a = json.loads(cli("roll", "10d10", "--seed", "42", "--format", "json").out)
    b = json.loads(cli("roll", "10d10", "--seed", "42", "--format", "json").out)
    assert a["result"] == b["result"] and a["roll"] != b["roll"]


def test_each_roll_has_its_own_stream(cli: Cli, home: Path, tmp_path: Path) -> None:
    """Roll #r2 comes out the same whatever #r1 was: one roll never shifts another."""
    setup(cli)
    path = home / "worlds/vale/campaigns/withering/campaign.yaml"
    path.write_text(path.read_text().replace("seed: ", "seed: fixed #"), encoding="utf-8")
    cli("roll", "d6")
    second = json.loads(cli("roll", "4d6", "--format", "json").out)
    # the same campaign seed in a fresh library, with a very different first roll
    other = tmp_path / "other"
    for args in (
        ("world", "new", "vale"),
        ("campaign", "new", "withering"),
    ):
        cli(*args, "--home", str(other))
    other_file = other / "worlds/vale/campaigns/withering/campaign.yaml"
    text = other_file.read_text()
    seed_line = next(line for line in text.splitlines() if line.startswith("seed: "))
    other_file.write_text(text.replace(seed_line, "seed: fixed"), encoding="utf-8")
    cli("roll", "100d100!", "--home", str(other))
    again = json.loads(cli("roll", "4d6", "--format", "json", "--home", str(other)).out)
    assert again["roll"] == second["roll"] == 2
    assert again["result"] == second["result"]


def test_undoing_a_roll_marks_it_and_never_rewinds_the_counter(cli: Cli) -> None:
    setup(cli)
    cli("roll", "d20")
    undone = cli("undo", "--event", "r1", "--reason", "wrong die")
    assert undone.code == 0 and "marked #r1 undone" in undone.out
    assert "(undone)" in cli("rolls").out
    assert cli("roll", "d8").out.startswith("#r2 ")
    again = cli("undo", "--event", "r1")
    assert again.code == 1 and "already undone" in again.err
    assert "undo roll #r1" in cli("history").out
    assert cli("undo").out.strip().startswith("✔ undid #e3")  # plain undo: the last *change*


def test_replay_reproduces_every_roll_and_catches_tampering(cli: Cli, home: Path) -> None:
    setup(cli)
    for expression in ("4d6kh3", "6d10>=8f1", "{d8, d6}kh1", "d20 <= @STR", "3#d6", "d6!"):
        cli("roll", expression, "--as", "sweeney")
    cli("roll", "2d6", "--got", "6,3")
    ok = cli("replay")
    assert ok.code == 0 and ok.out.strip() == "✔ 7 rolls reproduced exactly (campaign:withering)"
    log = home / "log/events.jsonl"
    lines = log.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        event = json.loads(line)
        if event["kind"] == "roll" and event["data"]["roll"] == 1:
            event["data"]["result"]["value"] = 99
            lines[i] = json.dumps(event)
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    bad = cli("replay")
    assert bad.code == 1 and "#r1: came out differently" in bad.out


def test_lost_counters_are_rebuilt_from_the_log(cli: Cli, home: Path) -> None:
    setup(cli)
    cli("roll", "d6")
    cli("roll", "d6")
    (home / "log/counters.json").unlink()
    assert cli("roll", "d6").out.startswith("#r3 ")


def test_odds(cli: Cli) -> None:
    setup(cli)
    assert cli("odds", "2d6 >= 8").out.strip() == "`2d6 >= 8`: 41.67% chance of true (exact)"
    table = cli("odds", "4d6kh3").out
    assert table.startswith("`4d6kh3` (exact): mean 12.24, sd 2.85, from 3 to 18")
    assert "| 18 | 1.62% | 1.62% |" in table
    assert "60.00% chance of true" in cli("odds", "d20 <= @STR", "--as", "sweeney").out
    simulated = cli("odds", "4d6u", "--samples", "1000").out
    assert "simulated, 1,000 rolls" in simulated and "note: simulated because" in simulated
    assert cli("odds", "3#d6").code == 1


def test_help_and_the_dice_guide(cli: Cli) -> None:
    text = cli("help", "roll").out
    assert "--as <record>" in text and "--got <faces>" in text and "didact guide dice" in text
    assert "- `dice`: Roll every die through Didact" in cli("guide").out
    guide = cli("guide", "dice").out
    assert guide.startswith("# Dice") and "**Quote the expression**" in guide
    assert cli("help", "dice").out == guide  # topics work through `help` too
    missing = cli("guide", "dcie")
    assert missing.code == 1 and "did you mean `dice`?" in missing.err
