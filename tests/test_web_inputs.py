"""Boxes that take what their command takes (ids, record types, keys, events, numbers, game
time as a number and a unit, a choice from a list), and jumping back in the history."""

import html
import re

from didact.commands import load_all
from didact.commands.registry import REGISTRY
from didact.web.forms import PATTERNS, command_argv
from tests.conftest import Cli
from tests.test_web import Browser, web  # noqa: F401  (the fixture)
from tests.test_web_status import _json, _page, _play


def _box(page: str, name: str) -> str:
    """The first `<input>` (not a hidden one) or `<select>` named `name` on a page."""
    for found in re.finditer(rf'<(?:input|select)[^>]*name="{re.escape(name)}"[^>]*>', page):
        if 'type="hidden"' not in found.group(0):
            return found.group(0)
    raise AssertionError(name)


def test_ids_types_keys_and_names_take_only_what_fits(web: Browser, cli: Cli) -> None:  # noqa: F811
    library = web.get("/library").body
    world = _box(library, "w")  # the first: a new campaign's id in the open world
    assert 'data-input="id"' in world and 'maxlength="64"' in world
    assert f'pattern="{html.escape(PATTERNS["id"][0])}"' in world
    assert "lowercase letters, digits and dashes; spaces become dashes" in library
    new = web.get("/records/new").body
    assert 'data-input="type"' in _box(new, "type")
    record = web.get("/record/npc:sweeney").body
    assert 'data-input="key"' in _box(record, "key") and "maxlength" not in _box(record, "key")
    names = re.findall(r'<input[^>]*name="name"[^>]*>', record)
    assert any('data-input="word"' in box for box in names)  # a detail's name: one word
    assert "app.js" in record  # where the boxes are held to it as they're typed
    cli("campaign", "close")
    overview = web.get("/").body
    assert 'data-input="id"' in _box(overview, "w")  # a new campaign's id


def test_time_goes_forward_by_a_number_and_a_unit(web: Browser, cli: Cli) -> None:  # noqa: F811
    _play(cli)
    before = _json(cli, "time", "show")
    page = web.get("/status").body
    amount = _box(page, "w")
    assert 'type="number"' in amount and 'min="0"' in amount and 'inputmode="decimal"' in amount
    units = page.split('<select class="entry" name="w"')[1].split("</select>")[0]
    assert '<option value="hour" selected>hours</option>' in units
    assert '<option value="watch">watches</option>' in units  # the system's units too
    moved = web.post(
        "/run", {"action": "words", "w": ["time", "advance", "2", "watch"], "next": "/status"}
    )
    assert "$ didact time advance 2 watch" in html.unescape(moved.body)
    after = _json(cli, "time", "show")
    assert after["seconds"] == before["seconds"] + 2 * before["units"]["watch"]
    assert after["text"] in _page(web, "/status")
    reminder = {"action": "remind", "text": "Feed the mule", "amount": "1", "unit": "day"}
    every = web.post("/run", {**reminder, "when": "every", "next": "/status"})
    assert "$ didact remind --every '1 day' 'Feed the mule'" in html.unescape(every.body)
    once = web.post("/run", {**reminder, "text": "-dash first", "when": "in", "next": "/status"})
    assert "$ didact remind --in '1 day' -- '-dash first'" in html.unescape(once.body)
    listed = [r["text"] for r in _json(cli, "remind", "--list")["reminders"]]
    assert "Feed the mule" in listed and "-dash first" in listed
    empty = web.post("/run", {**reminder, "text": " ", "next": "/status"})
    assert "say what the reminder is" in html.unescape(empty.body)


def test_command_forms_take_what_their_arguments_take(web: Browser, cli: Cli) -> None:  # noqa: F811
    undo = web.get("/commands/undo").body
    assert 'data-input="event"' in _box(undo, "a.to") and 'data-input="event"' in _box(
        undo, "a.event"
    )
    assert 'type="number"' in _box(undo, "a.steps") and 'step="1"' in _box(undo, "a.steps")
    remind = web.get("/commands/remind").body
    assert 'type="number"' in _box(remind, "a.in") and "<select" in _box(remind, "a.in.unit")
    show = web.get("/commands/show").body
    assert 'list="offer-records"' in _box(show, "a.ref")
    assert '<option value="npc:sweeney">Sweeney (npc)</option>' in show
    assert "npc:hidden-heir" not in show  # the player view offers what the players know
    fork = web.get("/commands/campaign/fork").body
    assert 'data-input="id"' in _box(fork, "a.new-id") and 'list="offer-saves"' in _box(
        fork, "a.at"
    )
    load_all()
    timed = command_argv(
        REGISTRY["remind"], {"a.text": ["Eat"], "a.in": ["2"], "a.in.unit": ["watch"]}
    )
    assert timed == ["remind", "Eat", "--in", "2 watch"]
    advance = command_argv(REGISTRY["time advance"], {"a.amount": ["3"], "a.amount.unit": ["day"]})
    assert advance == ["time", "advance", "3 day"]


def test_the_oracle_offers_its_own_odds(web: Browser, cli: Cli) -> None:  # noqa: F811
    page = web.get("/").body
    odds = page.split('name="o:--odds"')[1].split("</select>")[0]
    assert '<option value="very-likely">very likely</option>' in odds
    asked = web.post(
        "/run",
        {"action": "words", "w": ["ask", "Is it raining?"], "o:--odds": "likely", "next": "/"},
    )
    assert "$ didact ask &#x27;Is it raining?&#x27; --odds likely" in asked.body


def test_packs_and_tables_say_what_they_are(web: Browser) -> None:  # noqa: F811
    library = html.unescape(web.get("/library").body)
    assert "A tiny system to test sheets." in library  # the pack's own description
    assert "What every campaign has, whatever the system" in library


def test_the_history_jumps_back_to_any_change(web: Browser, cli: Cli) -> None:  # noqa: F811
    cli("new", "npc", "Ann")
    point = int(_json(cli, "history", "--limit", "1")["events"][0]["seq"])
    cli("new", "npc", "Bo", "--body", "Smuggler.\n\n## Secrets\nQX-BO is a spy.")
    cli("set", "bo", "mood=QX-MOOD")
    history = web.get("/library").body
    assert f'href="/library/jump?to=e{point}"' in history
    newest = point + 2
    assert f'href="/library/jump?to=e{newest}"' not in history  # nothing after the newest
    preview = html.unescape(web.get(f"/library/jump?to=e{point}").body)
    assert f"Jump back to #e{point}?" in preview and "2 steps are taken back" in preview
    assert "QX" not in preview  # the player view names the changes, not what they were
    assert f"$ didact undo --to e{point}" in preview
    web.gm(True)
    gm = html.unescape(web.get(f"/library/jump?to=e{point}").body)
    assert "mood=QX-MOOD" in gm  # the GM's sees each change in full
    jumped = web.post(
        "/run",
        {"action": "words", "w": ["undo", "--to", f"e{point}"], "next": "/library#history"},
    )
    assert f"jumped back to #e{point}" in html.unescape(jumped.body)
    assert cli("show", "bo").code != 0 and cli("show", "ann").code == 0
    nothing = html.unescape(web.get(f"/library/jump?to=e{newest + 2}").body)
    assert "Nothing after it is still in effect" in nothing
    wrong = html.unescape(web.get("/library/jump?to=nonsense").body)
    assert "Can't jump back there" in wrong and "invalid event" in wrong
    short = web.get("/library?history=2").body
    assert 'href="/library?history=8#history"' in short and "Show older changes" in short


def test_a_sheet_says_what_its_values_mean(web: Browser, cli: Cli) -> None:  # noqa: F811
    assert cli("world", "new", "picks", "--system", "picks-lite").code == 0
    assert cli("campaign", "new", "picks-run").code == 0
    assert cli("new", "pc", "Wren", "--set", "might=2").code == 0
    page = html.unescape(web.get("/record/pc:wren").body)
    assert '<div class="tile" title="Strength of arm and will.">' in page  # on the tile
    assert "What each one means" in page and "Strength of arm and will." in page
