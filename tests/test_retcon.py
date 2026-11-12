"""Retcons: the new fact applies, the old one is kept, summaries go stale, audit sees it."""

import json

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "npc", "Sweeney", "--set", "hp=3")
    cli("new", "npc", "Anglwyst")
    cli("session", "start")
    cli("scene", "new", "Grave")
    cli("scene", "end", "--summary", "Freya met Sweeney at the grave.")
    cli("scene", "new", "Hut")
    cli("scene", "end", "--summary", "A quiet night in the hut.")
    cli("session", "end", "--summary", "Sweeney helped Freya.")


def test_a_retcon_supersedes_and_marks_summaries_stale(cli: Cli) -> None:
    setup(cli)
    done = cli(
        "retcon", "Sweeney is Anglwyst's son", "--set", "sweeney.parent=npc:anglwyst",
        "--set", "sweeney.hp=5/5", "--set", "sweeney.hp=9",
    )  # fmt: skip
    assert done.code == 0 and "✔ retcon: Sweeney is Anglwyst's son" in done.out
    assert "note: npc:sweeney: parent: (none) → npc:anglwyst" in done.out
    assert "note: npc:sweeney: hp: 3 → 5" in done.out
    assert "note: npc:sweeney: hp: unchanged (hp stopped at its max 5 (4 over))" in done.out
    assert "summaries marked stale: scene:1, session:1" in done.out  # not the hut
    record = json.loads(cli("show", "sweeney", "--gm", "--format", "json").out)
    old = record["extra"]["superseded"]
    assert old[0] == {
        "key": "parent", "was": None, "now": "npc:anglwyst",
        "why": "Sweeney is Anglwyst's son", "until": 0,
    }  # fmt: skip
    assert "## Facts\n- Sweeney is Anglwyst's son" in record["body"]
    due = cli("summary", "due").out
    assert "- scene:1 (stale: retcon: Sweeney is Anglwyst's son)" in due and "scene:2" not in due
    cli("summary", "write", "scene:1", "Freya met Sweeney, Anglwyst's son.")
    assert "scene:1" not in cli("summary", "due").out
    assert "retcon: Sweeney is Anglwyst's son" in cli("audit").out


def test_a_secret_retcon_stays_secret(cli: Cli) -> None:
    setup(cli)
    cli("retcon", "Sweeney is Anglwyst's son", "--set", "sweeney.parent=npc:anglwyst", "--secret")
    shown = cli("show", "sweeney").out
    assert "anglwyst" not in shown.lower() and "superseded" not in shown
    assert "secret field hidden" in shown
    assert "## Secrets\n- Sweeney is Anglwyst's son" in cli("show", "sweeney", "--gm").out
    assert cli("reveal", "sweeney", "--field", "hp").code == 1  # hp isn't secret
    assert "revealed Sweeney's parent" in cli("reveal", "sweeney", "--field", "parent").out
    assert "parent: npc:anglwyst" in cli("show", "sweeney").out


def test_a_retcon_needs_something_to_change(cli: Cli) -> None:
    setup(cli)
    assert cli("retcon", "Nothing happened").code == 1
    about = cli("retcon", "The mill burned last winter", "--about", "sweeney")
    assert about.code == 0 and "stale" in about.out
    assert cli("retcon", "x", "--set", "sweeney").code == 1  # no key
