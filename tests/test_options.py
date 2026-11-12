"""Options: a system's variant and optional rules, chosen at session zero, read by its rules."""

import html
import json
import re
from pathlib import Path
from typing import Any

from tests.conftest import Cli
from tests.test_web import Browser, web  # noqa: F401  (the fixture)


def setup(cli: Cli, world: str = "vale") -> None:
    assert cli("world", "new", world, "--system", "options-lite", "--seed", "options").code == 0
    assert cli("campaign", "new", "tale", "--seed", "options").code == 0
    cli("new", "pc", "Wren")


def _json(cli: Cli, *args: str) -> Any:  # parsed JSON, read freely in tests
    out = cli(*args, "--format", "json")
    assert out.code == 0, out.err
    return json.loads(out.out)


def test_session_zero_asks_the_options_and_the_profile_keeps_them(cli: Cli) -> None:
    setup(cli)
    asked = cli("session", "zero").out
    assert "- lethality: How deadly should it be? (gentle / standard / deadly)" in asked
    assert "- torches: Do torches burn out? (on / off)" in asked
    assert asked.count("- lethality:") == 1  # the system's replaces Didact's own question
    questions = {q["key"]: q for q in _json(cli, "session", "zero")["questions"]}
    lethality = questions["lethality"]
    assert lethality["option"] is True and lethality["value"] == "standard"
    assert lethality["meanings"]["deadly"] == "Deadly: a fall is a 1d roll."

    saved = cli("campaign", "profile", "lethality=deadly", "torches=on")
    assert saved.code == 0, saved.err
    assert "lethality deadly" in saved.out and "torches on" in saved.out
    profile = _json(cli, "campaign", "profile")["profile"]
    assert profile["lethality"] == "deadly" and profile["torches"] is True  # a flag's a flag
    wrong = cli("campaign", "profile", "lethality=brutal")
    assert wrong.code != 0 and "lethality is one of: gentle, standard, deadly" in wrong.err
    assert "torches is on or off" in cli("campaign", "profile", "torches=maybe").err
    cleared = cli("campaign", "profile", "lethality=")
    assert cleared.code == 0 and "lethality" not in _json(cli, "campaign", "profile")["profile"]


def test_rules_character_creation_and_generators_read_them(cli: Cli) -> None:
    setup(cli)
    assert "(2d)." in cli("do", "fall", "who=wren").out  # safe or hurt: the dice it took
    assert "Wren's torch burns." in cli("do", "light", "who=wren").out
    assert cli("gen", "run", "options-lite.lantern", "--auto").code == 0
    assert cli("gen", "commit", "g1").code == 0

    cli("campaign", "profile", "lethality=deadly", "torches=on")
    assert "(1d)." in cli("do", "fall", "who=wren").out
    assert "burns for an hour, then it's gone" in cli("do", "light", "who=wren").out
    made = _json(cli, "char", "new", "--mode", "random")["draft"]
    assert made["entities"][0]["fields"]["hp"] == 4  # a deadly game starts with less
    refused = cli("gen", "run", "options-lite.lantern", "--auto")
    assert refused.code != 0 and "nothing burns forever here" in refused.err
    assert "`didact session zero`" in refused.err  # the hint: where the options are
    assert "lantern" not in cli("gen", "drafts").out  # no draft was left behind


def test_adding_to_a_field_nobody_set_starts_from_its_default(cli: Cli) -> None:
    setup(cli)
    assert cli("set", "wren", "level+=1").code == 0  # the sheet's default is 1
    assert _json(cli, "show", "wren")["mechanics"]["options-lite"]["level"] == 2


def test_a_choice_implies_others_and_an_answer_wins(cli: Cli) -> None:
    setup(cli)
    cli("campaign", "profile", "flavor=grim")
    assert "(1d)." in cli("do", "fall", "who=wren").out  # implied: deadly
    brief = cli("brief").out
    assert "Option flavor=grim: Grim: deadly, and the torches run out." in brief
    assert "Option lethality=deadly: Deadly: a fall is a 1d roll." in brief
    assert "Option torches=on: Each torch burns for an hour, then it's gone." in brief
    cli("campaign", "profile", "lethality=gentle")  # said outright, it wins
    assert "(3d)." in cli("do", "fall", "who=wren").out
    zero = {q["key"]: q for q in _json(cli, "session", "zero")["questions"]}
    assert zero["lethality"]["value"] == "gentle" and zero["lethality"]["unset"] == "deadly"


def test_broken_options_are_reported(cli: Cli, tmp_path: Path) -> None:
    pack = tmp_path / "bad-options"
    (pack / "rules").mkdir(parents=True)
    (pack / "pack.yaml").write_text("id: bad-options\nname: B\nkind: system\nversion: 0.1.0\n")
    (pack / "rules" / "options.yaml").write_text(
        "option: one\nchoices: {only: The only one.}\n---\n"
        "option: two\nkind: flag\nchoices: {a: A, b: B}\n---\n"
        "option: three\nchoices: {a: A, b: B}\ndefault: c\nimplies: {z: {one: only}}\n---\n"
        "option: four\nkind: toggle\ncolor: red\n"
    )
    result = cli("pack", "validate", str(pack))
    assert result.code == 1
    assert "rules/options.yaml:2: an option needs two choices or more" in result.out
    assert "a flag has no choices" in result.out
    assert "the default 'c' isn't a choice" in result.out
    assert "'z' isn't a choice" in result.out
    assert "an option's kind is flag, or left out for choices" in result.out
    assert "unknown key `color`" in result.out


def test_the_settings_page_saves_what_changed(web: Browser, cli: Cli) -> None:  # noqa: F811
    setup(cli, "tides")  # the web fixture's own world plays another system
    page = web.get("/settings").body
    assert 'id="options"' in page and 'name="opt.lethality"' in page
    assert "(default: standard)" in page and 'name="was.torches" value=""' in page
    saved = web.post(
        "/run",
        {
            "action": "options",
            "opt.lethality": "deadly",
            "was.lethality": "",
            "opt.torches": "",
            "was.torches": "",
            "next": "/settings",
        },
    )
    assert "$ didact campaign profile lethality=deadly" in saved.body  # torches left alone
    profile = _json(cli, "campaign", "profile")["profile"]
    assert profile == {"lethality": "deadly"}
    again = web.get("/settings").body
    assert re.search(r'<option value="deadly" selected>', again)
    same = web.post(
        "/run",
        {"action": "options", "opt.lethality": "deadly", "was.lethality": "deadly"},
    )
    assert "nothing changed" in same.body


def test_each_option_says_what_it_does(web: Browser, cli: Cli) -> None:  # noqa: F811
    """A flag says what turning it on does even while it's off, a choice what each value
    means, and a default another option sets says which."""
    setup(cli, "tides")
    page = html.unescape(web.get("/settings").body)
    assert "When on: Each torch burns for an hour, then it's gone. (p. 8)" in page
    assert "As the book has it: a 2d roll. (p. 7)" in page  # the value in play
    assert "What each choice means" in page
    for meaning in ("Gentle: a fall is a 3d roll.", "Deadly: a fall is a 1d roll."):
        assert meaning in page
    zero = {q["key"]: q for q in _json(cli, "session", "zero")["questions"]}
    assert zero["lethality"]["default"] == "standard" and zero["lethality"]["implied_by"] is None
    cli("campaign", "profile", "flavor=grim")
    zero = {q["key"]: q for q in _json(cli, "session", "zero")["questions"]}
    assert zero["lethality"]["implied_by"] == {
        "option": "flavor",
        "title": "Flavor",
        "value": "grim",
    }
    grim = html.unescape(web.get("/settings").body)
    assert "(default: deadly, as Flavor is grim)" in grim
    assert "(default: on, as Flavor is grim)" in grim
