"""Advancing a character the system's way: a level-up is a draft that changes the record (fixture
`advance-lite`), answered step by step like character creation; triggers `for: pcs` give each
player character their experience."""

import json
import re
from pathlib import Path
from typing import Any

from tests.conftest import Cli
from tests.test_web import Browser, web  # noqa: F401  (the fixture)

HERO = '{"calling": "Warden", "gift": "ward", "name": "Wren"}'


def setup(cli: Cli, world: str = "vale") -> None:
    assert cli("world", "new", world, "--system", "advance-lite", "--seed", "advance").code == 0
    assert cli("campaign", "new", "tale", "--seed", "advance").code == 0
    made = cli("char", "new", "--mode", "random", "--prefill", HERO)
    assert made.code == 0, made.err
    assert cli("char", "commit", "c1").code == 0


def _json(cli: Cli, *args: str) -> Any:  # parsed JSON, read freely in tests
    out = cli(*args, "--format", "json")
    assert out.code == 0, out.err
    return json.loads(out.out)


def _mechanics(cli: Cli, ref: str) -> dict[str, Any]:
    return dict(_json(cli, "show", ref)["mechanics"]["advance-lite"])


def _draft(text: str) -> str:
    found = re.search(r"#(c\d+) [a-z]+:", text)
    assert found is not None, text
    return found.group(1)


def test_a_level_up_is_a_draft_that_changes_the_record(cli: Cli) -> None:
    setup(cli)
    early = cli("char", "advance", "wren")
    assert early.code == 1 and "Wren has 0 of 2 XP" in early.err
    assert "advance it again when it can" in early.err
    cli("set", "wren", "xp=2")

    started = cli("char", "advance", "wren")
    assert started.code == 0, started.err
    assert "pc:wren advancing by advance-lite.level-up" in started.out
    assert "level: 1 → 2, xp: 2 → 0" in started.out  # what changes so far
    assert "a new gift: a Warden's, or one of your own" in started.out  # its calling: no question
    draft = _draft(started.out)
    waiting = _json(cli, "char", "show", draft)["draft"]["open"]
    assert waiting["name"] == "gift" and waiting["options"] == ["watch", "hold"]  # not ward again
    assert _mechanics(cli, "wren")["level"] == 1  # nothing written yet

    cli("char", "choose", draft, "hold")
    done = cli("char", "commit", draft)
    assert done.code == 0, done.err
    assert "pc:wren advanced: level 1 → 2, xp 2 → 0, gifts [ward] → [ward, hold]" in done.out
    after = _mechanics(cli, "wren")
    assert (after["level"], after["xp"], after["gifts"]) == (2, 0, ["ward", "hold"])
    assert cli("undo").code == 0 and _mechanics(cli, "wren")["level"] == 1  # undoable


def test_the_level_up_isnt_a_character_creation(cli: Cli) -> None:
    setup(cli)
    listed = _json(cli, "char", "list")
    assert [c["id"] for c in listed["chargens"]] == ["advance-lite.pc"]
    assert {"id": "advance-lite.level-up", "title": "Level up", "advances": "pc"} in listed[
        "advancements"
    ]
    assert "advance-lite.pc" in cli("char", "new").out  # still the one `char new` picks


def test_a_records_own_kind_joins_the_choice(cli: Cli) -> None:
    setup(cli)
    cli("new", "gift", "Storm Voice", "--set", "note=learned at sea")
    cli("set", "wren", "xp=2")
    options = _json(cli, "char", "advance", "wren")["draft"]["open"]["options"]
    assert options == ["watch", "hold", "gift:storm-voice"]


def test_triggers_run_for_each_player_character(cli: Cli) -> None:
    setup(cli)
    cli("new", "pc", "Ash")
    cli("new", "npc", "Old Gannet")
    cli("party", "add", "old-gannet", "--as", "hireling")
    cli("session", "start")
    ended = cli("session", "end", "--summary", "The ford held.")
    assert "advance-lite.session-xp (Wren)" in ended.out
    assert "advance-lite.session-xp (Ash)" in ended.out
    assert "Old Gannet" not in ended.out  # a hireling isn't a PC
    assert _mechanics(cli, "wren")["xp"] == 1 and _mechanics(cli, "ash")["xp"] == 1


def test_broken_advancements_are_reported(cli: Cli, tmp_path: Path) -> None:
    pack = tmp_path / "bad-advance"
    (pack / "chargen").mkdir(parents=True)
    (pack / "rules").mkdir()
    (pack / "pack.yaml").write_text("id: bad-advance\nname: B\nkind: system\nversion: 0.1.0\n")
    (pack / "chargen" / "up.yaml").write_text("chargen: up\nadvances: pc\ncreates: pc\nsteps: []\n")
    (pack / "rules" / "xp.yaml").write_text(
        "trigger: xp\non: session_end\nfor: everyone\nsteps: ['XP!']\n"
    )
    result = cli("pack", "validate", str(pack))
    assert result.code == 1
    assert "advances names the type of record it changes, and goes without creates" in result.out
    assert "a trigger runs `for:` party or pcs, not 'everyone'" in result.out


def test_the_app_levels_up_from_the_record(web: Browser, cli: Cli) -> None:  # noqa: F811
    setup(cli, "tides")  # the web fixture's own world plays another system
    cli("set", "wren", "xp=2")
    page = web.get("/record/pc:wren").body
    assert 'name="what" value="advance"' in page and "Level up" in page
    started = web.post("/drafts/start", {"what": "advance", "record": "pc:wren"})
    found = re.search(r"/drafts/(c\d+)", started.url)
    assert found is not None, started.body
    draft = found.group(1)
    assert "Level up: Wren" in started.body and "What changes" in started.body
    assert "1 → 2" in started.body  # the level
    web.run("char", "choose", draft, "watch", next_=f"/drafts/{draft}")
    committed = web.post(f"/drafts/{draft}/commit", {"verb": "char"})
    assert "/record/pc:wren?" in committed.url  # the character, with what was done
    assert _mechanics(cli, "wren")["gifts"] == ["ward", "watch"]


def test_an_advancement_can_take_off_and_make_records(cli: Cli) -> None:
    setup(cli)
    cli("new", "familiar", "Rex", "--set", "tricks+=sit", "--set", "tricks+=fetch")
    rolled = cli("char", "advance", "rex", "--mode", "random")
    assert rolled.code == 1 and "goes step by step" in rolled.err  # `modes: [guided]`
    started = cli("char", "advance", "rex", "--prefill", '{"old": "sit", "new": "roll over"}')
    assert started.code == 0, started.err
    draft = _draft(started.out)
    done = cli("char", "commit", draft)
    assert done.code == 0, done.err
    assert "familiar:rex advanced: tricks [sit, fetch] → [fetch, roll over]" in done.out
    assert "(made note:rex-learns-roll-over)" in done.out
    note = _json(cli, "show", "note:rex-learns-roll-over")
    assert {"rel": "about", "to": "familiar:rex"} in note["links"]
