"""Didact's own words in the reader's language: a record's keys and details, types, journal
kinds, what a pack is and holds, the library's parts, and expired timers. English output keeps
the keys as they're typed (the command line's own language, for the LLMs that read it)."""

import html
import json

import pytest

from didact.core import i18n, labels
from tests.conftest import Cli
from tests.test_web import Browser, web  # noqa: F401  (the fixture)


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "npc", "Sweeney", "--set", "knowledge=secret", "--set", "role=ferryman")
    cli("about", "sweeney", "plan=sell the route", "looks=tall")


def test_a_record_reads_in_the_readers_language(cli: Cli, monkeypatch: pytest.MonkeyPatch) -> None:
    setup(cli)
    english = cli("show", "sweeney", "--gm").out
    assert "knowledge: secret" in english and "plan: sell the route (GM)" in english
    assert "role: ferryman" in english  # English keeps the keys as they're typed
    monkeypatch.setenv("DIDACT_LANG", "de")
    german = cli("show", "sweeney", "--gm").out
    with i18n.use("de"):
        knowledge = f"{labels.record_key('knowledge')}: {labels.knowledge_name('secret')}"
        plan = i18n._("{name}: {text} (GM)", name=labels.detail_name("plan"), text="sell the route")
        role = f"{labels.field_name('role')}: ferryman"
    assert knowledge in german and plan in german and role in german
    assert "knowledge: secret" not in german


def test_types_kinds_and_parts_read_in_the_readers_language(
    cli: Cli, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup(cli)
    cli("track", "new", "Torch", "--kind", "timer", "--lasts", "1 hour")
    tables = json.loads(cli("pack", "info", "mini-system", "--format", "json").out)["contents"]
    monkeypatch.setenv("DIDACT_LANG", "de")
    with i18n.use("de"):
        npcs = f"{labels.type_plural('npc')} 1"
        held = labels.item_count("table", tables["table"])
        world = labels.library_part("world vale")
        ran_out = i18n._("timer: {timer} ran out", timer="Torch")
    assert npcs in cli("world", "show").out
    assert held in cli("pack", "info", "mini-system").out
    assert world in cli("library").out
    assert ran_out in cli("time", "advance", "2 hours").out
    monkeypatch.delenv("DIDACT_LANG")
    assert "npc 1" in cli("world", "show").out  # English: the keys
    assert f"{tables['table']} table" in cli("pack", "info", "mini-system").out


def test_play_reads_in_the_readers_language(cli: Cli, monkeypatch: pytest.MonkeyPatch) -> None:
    setup(cli)
    cli("new", "pc", "Freya")
    cli("about", "sweeney", "doing=whittling")
    cli("session", "start")
    cli("log", "action", "Freya waits")
    cli("combat", "start", "freya", "sweeney:foes")
    english = cli("timeline").out
    assert "## day 1" in english and "(S1)" in english
    monkeypatch.setenv("DIDACT_LANG", "de")
    with i18n.use("de"):
        member = f"[pc:freya] ({labels.party_role('pc')})"
        doing = f"{labels.detail_name('doing')}: whittling"
        day = i18n._("day {n}", n=1)
        status = f"({labels.session_status('open')})"
        mode = labels.initiative_mode("sides")
    assert member in cli("party", "show").out
    assert doing in cli("brief", "--gm").out
    assert doing in cli("combat", "status", "--gm").out
    assert mode in cli("combat", "status").out
    assert status in cli("session", "show").out
    timeline = cli("timeline", "--format", "json")
    assert json.loads(timeline.out)["days"][0]["day"] == "day 1"  # the data stays English
    assert f"## {day}" in cli("timeline").out


def test_a_rules_prompts_are_shown_once(cli: Cli) -> None:
    setup(cli)
    cli("new", "faction", "Raiders")
    turned = cli("faction", "turn")
    assert turned.code == 0, turned.err
    said = [line for line in turned.out.splitlines() if line.startswith(("prompt:", "reminder:"))]
    assert len(said) == len({line.partition(":")[2] for line in said})  # none said twice


def test_the_app_names_journal_kinds_and_oracles_in_the_readers_language(
    web: Browser,  # noqa: F811
    cli: Cli,
) -> None:
    cli("pack", "enable", "oracle-lite")
    cli("session", "start")
    cli("log", "consequence", "The ford floods")
    assert cli("ask", "Is it raining?").code == 0  # this oracle keeps its state in a record
    web.post("/language", {"lang": "de", "next": "/journal"})
    with i18n.use("de"):
        consequence = labels.beat_name("consequence")
        oracles = labels.type_plural("oracle")
    journal = html.unescape(web.get("/journal").body)
    assert f'class="beat-kind">{consequence}<' in journal
    assert oracles in html.unescape(web.get("/records").body)
