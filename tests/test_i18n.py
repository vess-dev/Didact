"""Translations: the catalogs follow the code, every language has every guide, the browser app
speaks the chosen language (Settings, else the browser's), and commands stay English."""

import gettext
import html
import json
from pathlib import Path
from typing import Any

import pytest
from babel.messages.catalog import Message
from babel.messages.pofile import read_po
from tools import i18n as tool

from didact import guides
from didact.core import i18n
from didact.core.i18n import _, ngettext
from didact.web.pages.overview import brief_rows
from tests.conftest import Cli
from tests.test_web import Browser, web  # noqa: F401  (the fixture)

CODES = [code for code in i18n.LANGUAGES if code != i18n.DEFAULT]


def test_the_catalogs_follow_the_code() -> None:
    assert tool.check() == []  # else: `make i18n`


def _key(message: Message) -> tuple[str, str]:
    """A message as the catalogs sort it: its id (a plural's first form), then its context."""
    ids = message.id
    return (str(ids[0]) if isinstance(ids, tuple) else str(ids), message.context or "")


def _translated(message: Message, forms: int) -> bool:
    """Whether a message has its translation: every plural form, none of them blank."""
    strings = message.string if isinstance(message.string, tuple) else (message.string,)
    if isinstance(message.id, tuple) and len(strings) != forms:
        return False
    return all(isinstance(text, str) and text.strip() for text in strings)


def test_every_catalog_is_complete_sorted_and_alike() -> None:
    """Read straight from the files, without the code: the template's messages are sorted, and
    every language's catalog has exactly those messages in the same order, each translated
    (every plural form, nothing fuzzy) and nothing more (no obsolete ones). So every catalog
    holds as many translations as the template has messages, and every language has the same
    guides as the English."""
    with tool.TEMPLATE.open("rb") as handle:
        template = read_po(handle)
    wanted = [_key(m) for m in template if m.id]
    assert wanted == sorted(wanted), "didact.pot isn't sorted: run `make i18n`"
    assert len(set(wanted)) == len(wanted), "didact.pot has a message twice: run `make i18n`"
    counts: dict[str, int] = {}
    for code in CODES:
        catalog = tool._read(tool.po_path(code), code)
        messages = [m for m in catalog if m.id]
        found = [_key(m) for m in messages]
        assert found == sorted(found), f"{code}: didact.po isn't sorted: run `make i18n`"
        missing = sorted(set(wanted) - set(found))[:3]
        extra = sorted(set(found) - set(wanted))[:3]
        assert found == wanted, f"{code}: not the template's messages: {missing=} {extra=}"
        assert not catalog.obsolete, f"{code}: obsolete messages: run `make i18n`"
        fuzzy = [key for key, m in zip(found, messages, strict=True) if m.fuzzy]
        assert not fuzzy, f"{code}: fuzzy translations: {fuzzy[:3]}"
        left = [
            k
            for k, m in zip(found, messages, strict=True)
            if not _translated(m, catalog.num_plurals)
        ]
        assert not left, f"{code}: {len(left)} untranslated, e.g. {left[:3]}"
        counts[code] = len(messages)
    assert set(counts.values()) == {len(wanted)}, counts
    topics = set(guides.topics())
    for code in CODES:
        shipped = {path.stem for path in (tool.GUIDES / code).glob("*.md")}
        assert shipped == topics, f"{code}: guides {sorted(shipped ^ topics)} don't match English"


def test_every_language_has_every_guide_and_its_messages() -> None:
    template = [m for m in tool.extract() if m.id]
    for code in CODES:
        for topic in guides.topics():
            shown = guides.translated(topic, code)
            assert shown.language == code, f"{code} has no {topic} guide"
            assert not shown.text.startswith("<!--")  # the mark isn't shown
        catalog = tool._read(tool.po_path(code), code)
        done = [
            m
            for m in catalog
            if m.id and m.string and all(m.string if isinstance(m.string, tuple) else (m.string,))
        ]
        assert len(done) == len(template), f"{code}: {len(done)}/{len(template)} translated"


def test_a_language_is_per_request_and_falls_back_to_english() -> None:
    assert _("Settings") == "Settings"
    with i18n.use("fr"):
        assert _("Settings") != "Settings"
        assert i18n.current().tag == "fr"
    with i18n.use("xx"):
        assert i18n.current().code == "en" and _("Settings") == "Settings"
    with i18n.use("pl"):  # four plural forms, chosen by the catalog's rule
        assert ngettext("{n} update", "{n} updates", 1) != ngettext("{n} update", "{n} updates", 5)


def test_the_browsers_languages_choose_one() -> None:
    assert i18n.negotiate("fr-CA,fr;q=0.9,en;q=0.8") == "fr"
    assert i18n.negotiate("pt-BR") == "pt_BR" and i18n.negotiate("pt-PT") == "pt"
    assert i18n.negotiate("es-MX") == "es_419" and i18n.negotiate("es-ES") == "es"
    assert i18n.negotiate("no;q=0.8, ja") == "nb"
    assert i18n.negotiate("ja, zh") == "en" and i18n.negotiate("") == "en"


def test_the_app_speaks_the_chosen_language(web: Browser, cli: Cli) -> None:  # noqa: F811
    assert '<html lang="en"' in web.get("/").body
    page = web.get("/settings").body
    assert "Français · French" in page and 'action="/language"' in page
    web.post("/language", {"lang": "fr", "next": "/settings"})
    french = html.unescape(web.get("/").body)
    with i18n.use("fr"):
        assert '<html lang="fr"' in french and _("Settings") in french
    before = cli("status").out
    web.post("/language", {"lang": "", "next": "/"})  # back to the browser's
    assert '<html lang="en"' in web.get("/").body
    assert cli("status").out == before  # commands stay English


def test_a_guide_in_another_language(cli: Cli, tmp_path: Path) -> None:
    shown = json.loads(cli("guide", "dice", "--lang", "pt-BR", "--format", "json").out)
    assert shown["language"] == "pt_BR" and shown["text"] != guides.read("dice")
    refused = cli("guide", "dice", "--lang", "tlh")
    assert refused.code != 0 and "no language 'tlh'" in refused.err


def test_the_api_docs_build_and_are_served(web: Browser, cli: Cli) -> None:  # noqa: F811
    assert "not built yet" in cli("docs", "status").out
    assert 'href="/docs/"' in web.get("/").body  # the header's button
    index = web.get("/docs/")  # built on the way
    assert index.status == 200 and "didact" in index.body
    assert "up to date" in cli("docs", "status").out
    assert "already up to date" in cli("docs", "build").out
    assert web.get("/docs/../../etc/passwd").status == 404


def test_command_help_is_translated_in_the_app_only(web: Browser, cli: Cli) -> None:  # noqa: F811
    with i18n.use("fr"):
        label = i18n.translate("what was accomplished")
        summary = i18n.translate(
            "Record an accomplishment (growth, XP, a milestone for advancement)"
        )
    assert label != "what was accomplished"
    web.post("/language", {"lang": "fr", "next": "/"})
    shown = label[:1].upper() + label[1:]  # the form's label starts with a capital
    assert shown in html.unescape(web.get("/commands/accomplish").body)
    assert summary in html.unescape(web.get("/commands").body)
    assert "Record an accomplishment" in cli("help", "accomplish").out  # the command line: English


def test_the_command_lines_help_follows_didact_lang(cli: Cli, monkeypatch: Any) -> None:
    summary = "Record an accomplishment (growth, XP, a milestone for advancement)"
    assert summary in cli("help", "accomplish").out  # English by default: the LLM reads it
    monkeypatch.setenv("DIDACT_LANG", "pt-BR")
    with i18n.use("pt_BR"):
        translated, examples = i18n.translate(summary), _("examples:")
    shown = cli("help", "accomplish").out
    assert translated in shown and examples in shown
    data = json.loads(cli("help", "accomplish", "--format", "json").out)
    assert data["summary"] == summary  # the data stays as it is
    monkeypatch.setenv("DIDACT_LANG", "tlh")  # unknown: English
    assert summary in cli("help", "accomplish").out


def test_another_language_is_only_for_the_call_that_asks(cli: Cli, monkeypatch: Any) -> None:
    summary = "Record an accomplishment (growth, XP, a milestone for advancement)"
    monkeypatch.setenv("DIDACT_LANG", "fr")  # this call, in French
    with i18n.use("fr"):
        french = i18n.translate(summary)
    assert french in cli("help", "accomplish").out
    monkeypatch.delenv("DIDACT_LANG")
    assert summary in cli("help", "accomplish").out  # nothing stuck: English, as LLMs read it
    assert cli("setup", "language", "fr").code != 0  # and no setting to make it stick


def test_the_overviews_brief_keeps_its_rows_in_another_language(
    web: Browser,  # noqa: F811
    cli: Cli,
    monkeypatch: Any,
) -> None:
    cli("new", "pc", "Freya")
    cli("session", "start")
    cli("scene", "new", "At the grave")
    cli("visit", "amber-grave")
    french = {  # the brief's lines, as a translator might write them
        "Time: {when}": "Heure : {when}",
        "Where: {place}": "Lieu : {place}",
        "Scene {n}: {name}": "Scène {n} : {name}",
        "PC {who}": "PJ {who}",
    }

    class Catalog(gettext.NullTranslations):
        def gettext(self, message: str) -> str:
            return french.get(message) or super().gettext(message)

    real = i18n.catalog

    def catalog(code: str) -> gettext.NullTranslations:
        if code != "fr":
            return real(code)
        fake = Catalog()
        fake.add_fallback(real(code))
        return fake

    monkeypatch.setattr(i18n, "catalog", catalog)
    web.post("/language", {"lang": "fr", "next": "/"})
    page = html.unescape(web.get("/").body)
    for label in ("Heure", "Lieu", "Scène 1", "PJ"):
        assert f'<span class="brief-label">{label}</span>' in page
    brief = page.partition('<div class="brief">')[2]
    assert 'href="/record/loc:amber-grave">Amber Grave</a>' in brief  # records as links
    assert 'href="/record/pc:freya">Freya</a>' in brief
    assert '<a class="chip" href="/record/pc:freya">' in page  # the party's chips
    assert '<div class="brief-row"><span></span>' not in page  # every line has its label
    assert "Time: day 1" in cli("brief").out  # the command line: English
    with i18n.use("fr"):  # a character's numbers as chips
        rows = str(brief_rows("head\nPJ Freya [pc:freya] · hp 3/4", {"pc:freya": "Freya"}))
    assert '<span class="brief-label">PJ</span>' in rows
    assert '<span class="chip"><span>hp 3/4</span></span>' in rows


def test_history_is_read_in_the_readers_language_and_kept_in_english(
    cli: Cli, home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "loc", "The Ford")
    cli("visit", "the-ford")
    assert "the party goes to The Ford" in cli("history").out
    visit = json.loads(cli("history", "--format", "json").out)["events"][0]["seq"]
    monkeypatch.setenv("DIDACT_LANG", "fr")
    with i18n.use("fr"):
        said = _("the party goes to {place}", place="The Ford")
        undo = _("undo {event}: {what}", event=f"#e{visit}", what=said)
    assert said != "the party goes to The Ford" and said in cli("history").out
    undone = cli("undo").out
    assert said in undone and undo in cli("history").out  # the undo names it in French too
    log = (home / "log" / "events.jsonl").read_text(encoding="utf-8")
    assert "the party goes to The Ford" in log and said not in log  # the log keeps English


def test_the_command_line_speaks_its_language_everywhere(
    cli: Cli, monkeypatch: pytest.MonkeyPatch
) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    monkeypatch.setenv("DIDACT_LANG", "de")
    guide = json.loads(cli("guide", "dice", "--format", "json").out)
    assert guide["language"] == "de"  # without --lang: the command line's own language
    wrong = cli("roll", "2d6", "--bogus")
    with i18n.use("de"):
        unrecognized = i18n.translate("unrecognized arguments: %s") % "--bogus"
        counted = ngettext("{n} success", "{n} successes", 0)
        summary = i18n.translate("Roll any dice expression; every roll is logged with an id (#r12)")
    assert unrecognized in wrong.err and "unrecognized" not in wrong.err  # argparse's words
    assert counted in cli("roll", "3d6>=7").out  # the dice's words
    assert summary in cli("explain", "roll").out  # a command's help, wherever it's shown
    monkeypatch.delenv("DIDACT_LANG")
    rolled = cli("rolls").out
    assert "0 successes" in rolled and counted not in rolled  # the log keeps English
