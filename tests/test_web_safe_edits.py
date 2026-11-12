"""Safe edits in the browser: saving never overwrites a change made since the page was opened
(by an LLM on the command line, or in another tab), and the player view never writes over
what it can't see."""

import html
import json
import re
from typing import Any

from tests.conftest import Cli
from tests.test_web import Browser, web  # noqa: F401  (the fixture)

TOM = "/record/npc:tom"


def _record(cli: Cli, ref: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(cli("show", ref, "--gm", "--format", "json").out)
    return data


def _snapshot(page: str, name: str) -> str:
    """What a form on the page carries of what it showed (`was.details`, …)."""
    found = re.search(rf'name="{re.escape(name)}" value="([^"]*)"', page)
    assert found, f"no {name} on the page"
    return html.unescape(found[1])


def _save(web: Browser, fields: dict[str, str]) -> str:  # noqa: F811
    """Submit a form from Tom's page; the page it lands on, as text."""
    return html.unescape(web.post("/run", {**fields, "next": TOM}).body)


def test_a_description_changed_meanwhile_is_never_overwritten(web: Browser, cli: Cli) -> None:  # noqa: F811
    cli("new", "npc", "Tom", "--body", "Runs the mill.")
    page = web.get(TOM).body
    was = _snapshot(page, "was.body")
    newer = "Runs the mill.\nOwes the witch a debt.\n"
    cli("edit", "tom", "--data", json.dumps({"body": newer}))  # from the command line, meanwhile
    mine = "Runs the mill.\nHates geese."
    refused = _save(web, {"action": "edit", "ref": "npc:tom", "body": mine, "was.body": was})
    assert "description changed since you opened this page" in refused
    assert _record(cli, "tom")["body"] == newer
    assert "Your version, not saved" in refused and "Hates geese." in refused  # to merge
    assert _snapshot(refused, "was.body").strip() == newer.strip()  # the editor knows the new one
    merged = newer + "Hates geese.\n"
    _save(web, {"action": "edit", "ref": "npc:tom", "body": merged, "was.body": newer})
    assert _record(cli, "tom")["body"] == merged


def test_changes_to_other_parts_dont_block_a_save(web: Browser, cli: Cli) -> None:  # noqa: F811
    cli("new", "npc", "Tom", "--body", "Runs the mill.")
    was = _snapshot(web.get(TOM).body, "was.body")
    cli("set", "tom", "mood=grim")
    cli("about", "tom", "plan=flee")
    _save(web, {"action": "edit", "ref": "npc:tom", "body": "Runs the mill well.", "was.body": was})
    assert _record(cli, "tom")["body"].strip() == "Runs the mill well."


def test_the_name_and_tags_keep_what_was_typed(web: Browser, cli: Cli) -> None:  # noqa: F811
    cli("new", "npc", "Tom", "--tag", "miller")
    cli("edit", "tom", "--data", json.dumps({"tags": ["miller", "liar"]}))  # after the page
    refused = _save(
        web,
        {
            "action": "edit",
            "ref": "npc:tom",
            "name": "Tom",
            "was.name": "Tom",
            "tags": "miller, grumpy",
            "was.tags": "miller",
        },
    )
    assert "tags changed since you opened this page: now “miller, liar”" in refused
    assert 'value="miller, grumpy"' in refused  # the form still holds what was typed
    assert _record(cli, "tom")["tags"] == ["miller", "liar"]


def test_details_fields_and_values_refuse_stale_saves(web: Browser, cli: Cli) -> None:  # noqa: F811
    web.gm(True)
    cli("new", "npc", "Tom")
    cli("about", "tom", "plan=buy the mill")
    cli("set", "tom", "mood=calm", "coins=3", "weapon=d6")
    page = web.get(TOM).body
    details, fields = _snapshot(page, "was.details"), _snapshot(page, "was.fields")
    values = _snapshot(page, "was.values")
    assert json.loads(details)["plan"] == "buy the mill" and json.loads(fields)["mood"] == "calm"

    cli("about", "tom", "plan=flee to the city")  # from the command line, meanwhile
    cli("set", "tom", "mood=furious", "coins=5", "weapon=d8")

    base = {"ref": "npc:tom", "was.details": details, "was.fields": fields}
    plan = _save(web, {**base, "action": "about", "name": "plan", "text": "stay and fight"})
    assert "plan changed since you opened this page: now “flee to the city”" in plan
    assert "you typed “stay and fight”" in plan
    mood = _save(web, {**base, "action": "set", "key": "mood", "value": "happy"})
    assert "mood changed since you opened this page: now “furious”" in mood
    gone = _save(web, {**base, "action": "set", "key": "mood", "unset": "1"})
    assert "mood changed since you opened this page" in gone
    sheet = _save(
        web, {"action": "set", "ref": "npc:tom", "assignment": "weapon=d10", "was.values": values}
    )
    assert "weapon changed since you opened this page: now “d8”" in sheet
    record = _record(cli, "tom")
    assert record["details"]["plan"] == "flee to the city"
    assert record["fields"]["mood"] == "furious" and record["values"]["weapon"] == "d8"

    _save(web, {**base, "action": "set", "key": "coins", "op": "+=", "value": "1"})  # adds up
    assert _record(cli, "tom")["fields"]["coins"] == 6
    fresh = _snapshot(web.get(TOM).body, "was.details")
    _save(web, {**base, "was.details": fresh, "action": "about", "name": "plan", "text": "stay"})
    assert _record(cli, "tom")["details"]["plan"] == "stay"  # seen, so it's replaced


def test_the_player_view_cant_write_over_what_it_cant_see(web: Browser, cli: Cli) -> None:  # noqa: F811
    cli("new", "npc", "Tom")
    cli("about", "tom", "plan=buy the mill")
    cli("set", "tom", "true_name=Bran", 'extra.secret_keys=["fields.true_name"]')
    page = web.get(TOM).body
    assert "buy the mill" not in page and "Bran" not in page
    details, fields = _snapshot(page, "was.details"), _snapshot(page, "was.fields")

    plan = _save(
        web,
        {"action": "about", "ref": "npc:tom", "name": "plan", "text": "x", "was.details": details},
    )
    assert "plan is one of the GM's notes" in plan and "buy the mill" not in plan
    for form in (
        {
            "action": "set",
            "ref": "npc:tom",
            "key": "true_name",
            "value": "Bob",
            "was.fields": fields,
        },
        {"action": "set", "ref": "npc:tom", "assignment": "true_name=Bob", "was.fields": fields},
    ):
        refused = _save(web, form)
        assert "true_name is hidden in the player view" in refused and "Bran" not in refused
    record = _record(cli, "tom")
    assert record["details"]["plan"] == "buy the mill" and record["fields"]["true_name"] == "Bran"

    _save(
        web,
        {
            "action": "about",
            "ref": "npc:tom",
            "name": "looks",
            "text": "tall",
            "was.details": details,
        },
    )
    assert _record(cli, "tom")["details"]["looks"] == "tall"  # what the players see, they can set


def test_a_secret_record_cant_be_changed_from_the_player_view(web: Browser, cli: Cli) -> None:  # noqa: F811
    refused = web.post(
        "/run",
        {"action": "set", "ref": "npc:hidden-heir", "key": "mood", "value": "x", "next": "/"},
    ).body
    assert "secret in the player view" in refused
    assert "mood" not in _record(cli, "hidden-heir").get("fields", {})


def test_the_player_views_history_names_no_secrets(web: Browser, cli: Cli) -> None:  # noqa: F811
    """A change's summary can hold a secret field's value, a secret record's name or a reason
    that gives something away: the player view names the command and known records only."""
    cli("new", "npc", "Tom")
    secret = ["true_name=Bran", 'extra.secret_keys=["fields.true_name"]']
    cli("set", "tom", *secret, "--reason", "Bran is the heir")
    for path in ("/", "/library", TOM):
        page = html.unescape(web.get(path).body)
        assert "Bran" not in page and "Hidden Heir" not in page, path
    assert "set · Tom" in html.unescape(web.get(TOM).body)
    assert "new · a hidden record" in html.unescape(web.get("/library").body)
    web.gm(True)
    assert "true_name=Bran" in html.unescape(web.get(TOM).body)  # the GM sees it all
    assert "why: Bran is the heir" in html.unescape(web.get("/library").body)


def test_undo_in_the_player_view_names_the_change_not_its_secrets(web: Browser, cli: Cli) -> None:  # noqa: F811
    cli("new", "npc", "Tom")
    cli("set", "tom", "true_name=Bran", 'extra.secret_keys=["fields.true_name"]')
    page = html.unescape(web.run("undo", next_=TOM).body)
    assert "undid #e" in page and "Bran" not in page
    web.run("redo", next_=TOM)
    web.gm(True)
    assert "true_name=Bran" in html.unescape(web.run("undo", next_=TOM).body)  # the GM sees it
