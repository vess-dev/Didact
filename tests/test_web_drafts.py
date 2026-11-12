"""The drafts pages: character creation and generators in the browser, one step at a time.

Every step runs the real command (`char new`, `gen choose`, `char roll --one`, `gen edit`,
`gen commit`, …), and the player view never shows what a generator's draft holds.
"""

import html
import json
import os
import re
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import FIXTURE_PACKS, Cli
from tests.test_web import Browser, web  # noqa: F401  (the fixture)

ODD_PACK = {
    "pack.yaml": (
        "id: odd-options\nname: Odd options (test pack)\nkind: supplement\nversion: 0.1.0\n"
        "requires: {packs: [core]}\nlicense: {spdx: CC0-1.0}\n"
    ),
    "GUIDE.md": "# Odd options\n\nA generator whose options need escaping.\n",
    "generators/odd.yaml": (
        "generator: odd\ntitle: Odd <options>\nsteps:\n"
        "  - choose: {from: ['<b>bold</b>', '\"Quoted\" & ''single''', '-1'], as: pick}\n"
        '  - entity: {key: thing, type: note, name: "{@pick}"}\n'
        "  - choose: {from: [" + ", ".join(f"'<i>{n}</i>'" for n in range(30)) + "], as: many}\n"
    ),
}


@pytest.fixture
def odd(home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A pack whose generator offers options with HTML, quotes and a leading dash."""
    pack = tmp_path / "extra" / "odd-options"
    for name, text in ODD_PACK.items():
        (pack / name).parent.mkdir(parents=True, exist_ok=True)
        (pack / name).write_text(text, encoding="utf-8")
    monkeypatch.setenv("DIDACT_PACK_PATH", os.pathsep.join([str(FIXTURE_PACKS), str(pack.parent)]))
    return pack


FOLLOWERS_PACK = {
    "pack.yaml": (
        "id: followers\nname: Followers (test pack)\nkind: supplement\nversion: 0.1.0\n"
        "requires: {packs: [core]}\nlicense: {spdx: CC0-1.0}\n"
    ),
    "GUIDE.md": "# Followers\n\nA second way to make a character.\n",
    "chargen/follower.yaml": (
        "chargen: follower\ntitle: A follower\ncreates: npc\nmodes: [random, guided]\n"
        "steps:\n  - name: {from: [Pell, Wren]}\n"
    ),
}


@pytest.fixture
def followers(home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A pack with a second character creation beside the system's own."""
    pack = tmp_path / "extra" / "followers"
    for name, text in FOLLOWERS_PACK.items():
        (pack / name).parent.mkdir(parents=True, exist_ok=True)
        (pack / name).write_text(text, encoding="utf-8")
    monkeypatch.setenv("DIDACT_PACK_PATH", os.pathsep.join([str(FIXTURE_PACKS), str(pack.parent)]))
    return pack


def _text(body: str) -> str:
    """A page as a reader sees it: no tags, no entities."""
    return html.unescape(re.sub(r"<[^>]+>", " ", body))


def _draft(cli: Cli, draft_id: str) -> Any:  # parsed JSON, read freely in tests
    shown = cli("gen", "show", draft_id, "--format", "json")
    assert shown.code == 0, shown.err
    return json.loads(shown.out)["draft"]


def _record(cli: Cli, ref: str) -> Any:
    shown = cli("show", ref, "--gm", "--format", "json")
    assert shown.code == 0, shown.err
    return json.loads(shown.out)


# ---------------------------------------------------------------------------- characters


def test_a_guided_character_from_start_to_commit(web: Browser, cli: Cli) -> None:  # noqa: F811
    records = web.get("/records").body
    assert 'href="/drafts/new#character"' in records and 'href="/drafts/new#generate"' in records
    assert 'href="/drafts"' in records  # the drafts list
    assert "Or let the system make it" in web.get("/records/new").body
    start = web.get("/drafts/new").body
    assert "Create a character" in start and 'value="guided"' in start and 'value="random"' in start

    begun = web.post("/drafts/start", {"what": "character", "mode": "guided"})
    assert begun.url.startswith(web.base + "/drafts/c1?flash=")
    assert "$ didact char new" in begun.body
    for option in ("Aurifex", "Bonekeeper", "Cutpurse"):  # each option is a button
        assert f'name="w" value="{option}"><button type="submit" class="button">' in begun.body
    assert "Let the dice decide" in begun.body and "Roll the rest" in begun.body
    assert "/drafts/c1/commit" not in begun.body  # still waiting: nothing to commit yet

    chose = web.run("char", "choose", "c1", "Bonekeeper", next_="/drafts/c1")
    assert "$ didact char choose c1 Bonekeeper" in chose.body
    assert "Swap" in chose.body and 'value="STR WIL"' in chose.body
    assert "Shovel, Lantern" in chose.body  # what the draft holds so far
    assert "mini-system.pc: STR" in chose.body  # the rolls it made, as the log has them

    rolled = web.run("char", "roll", "c1", "--one", next_="/drafts/c1")  # Let the dice decide
    assert "$ didact char roll c1 --one" in rolled.body
    draft = _draft(cli, "c1")
    assert draft["waiting"] == "name" and [n for n, _ in draft["trail"]].count("swap") == 1
    assert draft["open"]["free"] is True and "dice" not in draft["open"]
    assert 'name="a.value"' in rolled.body and "or one of your own" in rolled.body
    assert 'value="Crane"' in rolled.body  # the background's names are buttons too

    named = web.post(
        "/run",
        {
            "action": "command",
            "cmd": "char choose",
            "a.draft": "c1",
            "a.value": "Freya",  # not one of the options: a name of her own
            "next": "/drafts/c1",
        },
    )
    assert "$ didact char choose c1 Freya" in named.body
    assert "Nothing left to decide" in named.body and "/drafts/c1/commit" in named.body
    assert "Describe the character in two sentences" in named.body  # the book's prompt

    edited = web.post(
        "/drafts/c1/edit",
        {
            "verb": "char",
            "key": "character",
            "v:name": "Freya",
            "was:name": "Freya",
            "v:fields.hp": str(draft["entities"][0]["fields"]["hp"]),
            "was:fields.hp": str(draft["entities"][0]["fields"]["hp"]),
            "new.key": "pronouns",
            "new.value": "she/her",
        },
    )
    assert edited.url.startswith(web.base + "/drafts/c1?flash=")
    assert "$ didact char edit c1 character.fields.pronouns=she/her" in edited.body  # only that
    nothing = web.post(
        "/drafts/c1/edit", {"verb": "char", "key": "character", "v:name": "a", "was:name": "a"}
    )
    assert "nothing changed" in nothing.body

    committed = web.post("/drafts/c1/commit", {"verb": "char"})
    assert committed.url.startswith(web.base + "/record/pc:freya?flash=")  # the new record
    assert "$ didact char commit c1" in committed.body and "Freya" in committed.body
    freya = _record(cli, "pc:freya")
    assert freya["name"] == "Freya" and freya["fields"]["pronouns"] == "she/her"
    assert web.get("/drafts/c1").status == 404  # the draft went with the commit
    assert "No drafts" in web.get("/drafts").body


def test_a_random_character(web: Browser, cli: Cli) -> None:  # noqa: F811
    made = web.post(
        "/drafts/start",
        {"what": "character", "mode": "random", "prefill": "background=Cutpurse\r\nhp=4"},
    )
    assert made.url.startswith(web.base + "/drafts/c1?flash=")
    assert "didact char new --mode random --prefill" in made.body
    assert _draft(cli, "c1")["prefill"] == {"background": "Cutpurse", "hp": 4}
    assert "Nothing left to decide" in made.body  # the dice decided the rest, name and all
    assert "background=Cutpurse" in made.body and "the dice decide" in made.body
    name = _draft(cli, "c1")["entities"][0]["name"]
    listed = web.get("/drafts").body
    assert name in listed and "#c1 · character" in listed and "ready" in listed
    committed = web.post("/drafts/c1/commit", {"verb": "char"})
    assert "/record/pc:" in committed.url and name in committed.body
    assert cli("char", "check", name).code == 0

    wrong = web.post("/drafts/start", {"what": "character", "prefill": "no equals sign"})
    assert wrong.url.startswith(web.base + "/drafts/new")  # back, with what went wrong
    assert "can&#x27;t read" in wrong.body and "no equals sign" in wrong.body


# ---------------------------------------------------------------------------- generators


def test_a_generator_run_step_by_step_and_committed(web: Browser, cli: Cli) -> None:  # noqa: F811
    web.gm(True)
    start = web.get("/drafts/new?generator=mini-system.pointcrawl").body
    assert "A small pointcrawl" in start and 'name="r.size"' in start
    assert "Step by step" in start and "All at once" in start

    begun = web.post(
        "/drafts/start",
        {
            "what": "generator",
            "generator": "mini-system.pointcrawl",
            "r.size": "3",
            "mode": "guided",
        },
    )
    assert begun.url.startswith(web.base + "/drafts/g1?flash=")
    assert "$ didact gen run mini-system.pointcrawl size=3" in begun.body
    assert "Terrain" in begun.body and 'name="w" value="Swamp"' in begun.body

    chose = web.run("gen", "choose", "g1", "Swamp", next_="/drafts/g1")
    assert "$ didact gen choose g1 Swamp" in chose.body
    page = chose.body
    assert '<svg viewBox="0 0 1000 600"' in page and 'class="route' in page  # the map
    assert "The Swamp Reach" in page and "Places" in page and "Paths" in page
    assert "What would draw people to this region?" in page  # the prompt
    assert "Nothing left to decide" in page and "size=3" in page
    draft = _draft(cli, "g1")
    first = next(e for e in draft["entities"] if e["key"] == "poi-1")

    renamed = web.post(
        "/drafts/g1/edit",
        {"verb": "gen", "key": "poi-1", "v:name": "Sunken Bell", "was:name": first["name"]},
    )
    assert "$ didact gen edit g1 &#x27;poi-1.name=Sunken Bell&#x27;" in renamed.body
    added = web.post("/drafts/g1/edit", {"verb": "gen", "add.type": "npc", "add.name": "Gannet"})
    assert "didact gen edit g1 --add" in added.body and "Gannet" in added.body
    dropped = web.run("gen", "edit", "g1", "--drop", "poi-3", next_="/drafts/g1")
    assert "$ didact gen edit g1 --drop poi-3" in dropped.body
    keys = [e["key"] for e in _draft(cli, "g1")["entities"]]
    assert keys == ["region-1", "poi-1", "poi-2", "npc-1"]

    committed = web.post("/drafts/g1/commit", {"verb": "gen"})
    assert committed.url.startswith(web.base + "/drafts/made?id=loc%3Athe-swamp-reach")
    assert "$ didact gen commit g1" in committed.body
    for name in ("The Swamp Reach", "Sunken Bell", "Gannet"):
        assert name in committed.body
    assert _record(cli, "sunken-bell")["fields"]["region"] == "loc:the-swamp-reach"
    assert web.get("/drafts/g1").status == 404
    assert "Undo" in committed.body  # the whole commit is one change


def test_discard_asks_first(web: Browser, cli: Cli) -> None:  # noqa: F811
    assert cli("char", "new").code == 0
    page = web.get("/drafts/c1").body
    assert 'href="/drafts/c1/discard" data-confirm-form' in page  # without JS: a page that asks
    assert 'data-confirm="Discard draft #c1?"' in page  # with JS: a dialog
    asked = web.get("/drafts/c1/discard")
    assert asked.status == 200 and "Discard draft #c1?" in asked.body
    assert "$ didact char discard c1" in asked.body and 'href="/drafts/c1">' in asked.body
    assert cli("gen", "drafts").out.startswith("- #c1")  # asking changed nothing

    gone = web.run("char", "discard", "c1", next_="/drafts/c1", next_ok="/drafts")
    assert gone.url.startswith(web.base + "/drafts?flash=")
    assert "$ didact char discard c1" in gone.body and "No drafts" in gone.body
    assert cli("gen", "drafts").out.strip() == "no drafts"
    undo = re.search(r'name="w" value="(e\d+)"', gone.body)
    assert undo is not None, "the discard offers an Undo"
    web.run("undo", "--event", undo.group(1), next_="/drafts")
    assert "#c1" in web.get("/drafts").body  # it came back


def test_a_question_takes_any_answer_and_no_dice(web: Browser, cli: Cli) -> None:  # noqa: F811
    web.gm(True)
    assert cli("gen", "run", "mini-system.patron", "--auto").code == 0
    page = web.get("/drafts/g1").body
    assert "Wants" in page and "what they want for " in page  # the question, filled in
    assert 'name="a.value"' in page and "Let the dice decide" not in page  # typed, not rolled
    answered = web.run("gen", "choose", "g1", "a debt repaid", next_="/drafts/g1")
    assert "$ didact gen choose g1 &#x27;a debt repaid&#x27;" in answered.body
    assert _draft(cli, "g1")["waiting"] == "name"


# ---------------------------------------------------------------------------- player safety


def test_the_player_view_never_shows_a_generators_gm_material(
    web: Browser,  # noqa: F811
    cli: Cli,
) -> None:
    ran = cli("gen", "run", "pointcrawl", "--prefill", '{"terrain": "Swamp"}', "--auto")
    assert ran.code == 0, ran.err
    secret = '{"type": "npc", "name": "Mother Hollow", "body": "## Secrets\\nShe drowned it."}'
    assert cli("gen", "edit", "g1", "--add", secret).code == 0
    assert cli("char", "new").code == 0  # a character's draft: the player's own
    draft = _draft(cli, "g1")
    spoilers = [e["name"] for e in draft["entities"]]  # the region, its places, the NPC
    spoilers += ["She drowned it", "What would draw people", "— mini-system.pointcrawl"]
    drafts = ["/drafts", "/drafts/new", "/drafts/g1", "/drafts/g1?edit=1", "/drafts/g1/discard"]
    for path in [*drafts, "/drafts/c2", "/", "/records"]:
        page = web.get(path)
        assert page.status == 200, path
        seen = _text(page.body)
        for text in spoilers:
            assert text not in seen, f"{path} shows {text!r}"
    notice = web.get("/drafts/g1").body
    assert "This draft is for the GM" in notice and 'action="/gm"' in notice
    assert "/drafts/g1/commit" not in notice and 'value="choose"' not in notice
    assert "GM view only" in web.get("/drafts").body
    new = web.get("/drafts/new").body
    assert 'name="r.size"' not in new and "Turn on the GM view to run one" in new
    assert "A small pointcrawl" in new  # what there is to run, by name, but none of its steps
    character = web.get("/drafts/c2").body  # shown in full, as it's the player's
    assert "Background" in character and 'value="Aurifex"' in character

    web.gm(True)
    seen = _text(web.get("/drafts/g1").body)
    for text in [e["name"] for e in draft["entities"]] + ["She drowned it"]:
        assert text in seen, f"the GM view lacks {text!r}"
    assert "The Swamp Reach" in web.get("/drafts").body


def test_options_with_quotes_or_html_are_escaped(
    odd: Path,
    web: Browser,  # noqa: F811
    cli: Cli,
) -> None:
    assert cli("pack", "enable", "odd-options").code == 0
    web.gm(True)
    start = web.get("/drafts/new").body
    assert "Odd &lt;options&gt;" in start and "Odd <options>" not in start
    begun = web.post(
        "/drafts/start", {"what": "generator", "generator": "odd-options.odd", "mode": "guided"}
    )
    page = begun.body
    assert "<b>bold</b>" not in page and '"Quoted"' not in page
    assert 'value="&lt;b&gt;bold&lt;/b&gt;"' in page
    assert "<span>&lt;b&gt;bold&lt;/b&gt;</span>" in page
    assert 'value="&quot;Quoted&quot; &amp; &#x27;single&#x27;"' in page
    assert 'name="w" value="--"><input type="hidden" name="w" value="-1">' in page  # not a flag

    chose = web.run("gen", "choose", "g1", "\"Quoted\" & 'single'", next_="/drafts/g1")
    assert _draft(cli, "g1")["entities"][0]["name"] == "\"Quoted\" & 'single'"
    assert "&quot;Quoted&quot; &amp; &#x27;single&#x27;" in chose.body
    assert '"Quoted" & ' not in chose.body
    assert '<select class="entry" name="a.value"' in chose.body  # 30 options: a list to pick
    assert '<option value="&lt;i&gt;29&lt;/i&gt;">&lt;i&gt;29&lt;/i&gt;</option>' in chose.body
    assert "<i>29</i>" not in chose.body

    web.post("/drafts/start", {"what": "generator", "generator": "odd-options.odd"})
    dashed = web.run("gen", "choose", "g2", "--", "-1", next_="/drafts/g2")
    assert "$ didact gen choose g2 -- -1" in dashed.body
    assert _draft(cli, "g2")["entities"][0]["name"] == "-1"


def test_a_wrong_answer_says_why_and_keeps_what_was_typed(
    web: Browser,  # noqa: F811
    cli: Cli,
) -> None:
    cli("world", "new", "iron", "--system", "ironsworn-lite")  # stats spread as an array
    cli("campaign", "new", "iron-run")
    assert cli("char", "new").code == 0
    page = web.get("/drafts/c1").body
    assert "Stats" in page and "give 3, 2, 2, 1, 1 to edge" in page
    assert 'placeholder="your answer"' not in page  # the array is spread a field at a time
    assert '<select class="entry" name="as.edge"' in page and "Use each of 3, 2, 2, 1, 1" in page
    answer = {"verb": "char", "kind": "assign", "fields": "edge heart iron shadow wits"}
    wrong = {"as.edge": "3", "as.heart": "3", "as.iron": "2", "as.shadow": "1", "as.wits": "1"}
    refused = web.post("/drafts/c1/answer", {**answer, **wrong})
    assert "use each of [3, 2, 2, 1, 1] once" in refused.body
    heart = refused.body.split('name="as.heart"')[1].split("</select>")[0]
    assert '<option value="3" selected>' in heart  # what was chosen, to fix
    right = web.post("/drafts/c1/answer", {**answer, **wrong, "as.heart": "2"})
    typed = "&#x27;edge=3 heart=2 iron=2 shadow=1 wits=1&#x27;"
    assert f"$ didact char choose c1 {typed}" in right.body
    assert _draft(cli, "c1")["entities"][0]["fields"]["edge"] == 3


def test_an_answer_in_parts_picks_several_and_buys_scores(
    web: Browser,  # noqa: F811
    cli: Cli,
) -> None:
    """Picking several (a box to tick for each, no more than asked), and scores bought with a
    budget (a number for each field), each sent as the one answer it makes."""
    assert cli("world", "new", "picks", "--system", "picks-lite").code == 0
    assert cli("campaign", "new", "picks-run").code == 0
    assert cli("char", "new").code == 0
    page = web.get("/drafts/c1").body
    assert 'data-pick="2"' in page and page.count('name="pick"') == 4
    assert "0 of 2 chosen" in page
    one = web.post("/drafts/c1/answer", {"verb": "char", "kind": "pick", "pick": ["brave"]})
    assert "pick 2 different ones" in one.body and 'value="brave" checked' in one.body
    none = web.post("/drafts/c1/answer", {"verb": "char", "kind": "pick"})
    assert "tick the ones you want first" in none.body
    two = web.post(
        "/drafts/c1/answer", {"verb": "char", "kind": "pick", "pick": ["brave", "quiet"]}
    )
    assert "$ didact char choose c1 &#x27;brave, quiet&#x27;" in two.body
    bought = web.get("/drafts/c1").body
    assert 'name="pb.might"' in bought and 'min="0"' in bought and 'max="3"' in bought
    assert (
        "data-budget=" in bought and "What each score costs: 0 → 0, 1 → 1, 2 → 2, 3 → 4" in bought
    )
    scores = {"verb": "char", "kind": "point_buy", "fields": "might wit"}
    over = web.post("/drafts/c1/answer", {**scores, "pb.might": "3", "pb.wit": "3"})
    assert "the budget is 5" in over.body
    done = web.post("/drafts/c1/answer", {**scores, "pb.might": "3", "pb.wit": "1"})
    assert "$ didact char choose c1 &#x27;3 1&#x27;" in done.body
    fields = _draft(cli, "c1")["entities"][0]["fields"]
    assert fields["traits"] == ["brave", "quiet"] and (fields["might"], fields["wit"]) == (3, 1)


def test_back_takes_the_last_step_back(web: Browser, cli: Cli) -> None:  # noqa: F811
    button = "Go back a step: take back the last answer, roll or edit"
    assert cli("char", "new").code == 0  # the web fixture's world plays mini-system
    first = web.get("/drafts/c1").body
    assert button not in first  # at its first question: nothing to go back to
    cli("char", "choose", "c1", "Cutpurse")
    asked = web.get("/drafts/c1").body
    assert '<span class="draft-kicker">Next</span><h2>Swap</h2>' in asked and button in asked
    back = web.run("char", "back", "c1", next_="/drafts/c1")
    assert "went back a step" in back.body and "<h2>Background</h2>" in back.body
    assert button not in back.body  # the first question again
    assert _draft(cli, "c1")["waiting"] == "background"
    again = web.run("char", "back", "c1", next_="/drafts/c1")
    assert "is at its first step" in again.body and "char discard c1" in again.body


def test_bad_draft_ids_give_a_helpful_404(web: Browser) -> None:  # noqa: F811
    missing = web.get("/drafts/g99")
    assert missing.status == 404
    assert "no draft #g99" in missing.body and "didact gen drafts" in missing.body
    assert 'href="/drafts"' in missing.body  # the way to the drafts that are there
    for path in ("/drafts/nonsense", "/drafts/..%2F..%2Fstate", "/drafts/%3Cscript%3E"):
        page = web.get(path)
        assert page.status == 404, path
        assert "isn&#x27;t a draft" in page.body and "c3" in page.body, path
        assert "<script>" not in page.body
    assert web.get("/drafts/g99/discard").status == 404
    refused = web.post("/drafts/g99/commit", {"verb": "gen"})
    assert refused.status == 404 and "no draft #g99" in refused.body


# ---------------------------------------------------------------------------- the commands' data


def test_the_draft_json_says_what_the_wizard_needs(cli: Cli) -> None:
    """Whether an answer can be typed in (`free`), whether the dice can make it (`dice`),
    rolling just the open choice (`--one`), and the generators' help and parameters."""
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    begun = json.loads(cli("char", "new", "--format", "json").out)["draft"]
    assert begun["open"]["name"] == "background" and "free" not in begun["open"]
    once = json.loads(cli("char", "roll", "c1", "--one", "--format", "json").out)["draft"]
    assert once["waiting"] == "swap" and not once["auto"]  # only the background was rolled
    assert cli("char", "roll", "c1", "--one").code == 0
    name = json.loads(cli("char", "show", "c1", "--format", "json").out)["draft"]["open"]
    assert name["name"] == "name" and name["free"] is True and "dice" not in name
    empty = cli("char", "choose", "c1", " ")
    assert empty.code == 1 and "name needs an answer" in empty.err
    assert cli("char", "choose", "c1", "Zed").code == 0  # a name of the player's own
    assert _draft(cli, "c1")["entities"][0]["name"] == "Zed"

    generators = json.loads(cli("gen", "list", "--format", "json").out)["generators"]
    crawl = next(g for g in generators if g["id"] == "mini-system.pointcrawl")
    assert crawl["params"] == {"size": {"kind": "int", "default": 4}}
    assert crawl["help"] == "A region with a few places, joined by paths."
    cli("gen", "run", "pointcrawl")
    listed = json.loads(cli("gen", "drafts", "--format", "json").out)
    character, generated = listed["items"]
    assert listed["drafts"] == ["c1", "g2"]  # as before: the ids
    assert character == {
        "id": "c1",
        "kind": "chargen",
        "source": "mini-system.pc",
        "waiting": None,
        "name": "Zed",
    }
    assert (generated["kind"], generated["waiting"], generated["name"]) == (
        "generator",
        "terrain",
        "",
    )

    cli("world", "new", "iron", "--system", "ironsworn-lite")
    cli("campaign", "new", "iron-run")
    array = json.loads(cli("char", "new", "--format", "json").out)["draft"]["open"]
    assert array["name"] == "stats" and array["options"] == [] and array["free"] is True


def test_the_page_offers_each_character_creation(
    followers: Path,
    web: Browser,  # noqa: F811
    cli: Cli,
) -> None:
    assert '<select class="entry" name="chargen"' not in web.get("/drafts/new").body  # just one
    assert cli("pack", "enable", "followers").code == 0
    start = web.get("/drafts/new").body
    assert '<option value="mini-system.pc" selected>' in start  # the system's own comes first
    assert '<option value="followers.follower">A follower</option>' in start
    made = web.post(
        "/drafts/start", {"what": "character", "chargen": "followers.follower", "mode": "random"}
    )
    assert "didact char new followers.follower --mode random" in made.body
    drafted = _draft(cli, "c1")
    assert drafted["source"] == "followers.follower" and drafted["entities"][0]["type"] == "npc"
