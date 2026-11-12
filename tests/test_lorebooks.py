"""Lorebooks to and from other tools: SillyTavern World Info out and in, a character card's
book, and NovelAI's `.lorebook`."""

import json
from pathlib import Path

from tests.conftest import Cli


def _campaign(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")


def _fields(cli: Cli, ref: str) -> dict[str, object]:
    return dict(json.loads(cli("show", ref, "--format", "json").out)["fields"])


def test_world_info_goes_out_and_comes_back_the_same(cli: Cli, tmp_path: Path) -> None:
    _campaign(cli)
    cli(
        "lore", "add", "The river spirit is awake.", "--keys", "river", "--secondary", "night",
        "--logic", "not_any", "--sticky", "2", "--priority", "70", "--probability", "40",
        "--group", "spirits", "--no-recurse",
    )  # fmt: skip
    cli("lore", "add", "The witch is Tom's mother.", "--keys", "witch", "--kind", "secret")
    cli("lore", "add", "Fog every dawn.", "--keys", "fog", "--cooldown", "2 scenes")
    book = tmp_path / "wi.json"
    out = cli("lore", "export", "--to", str(book))
    assert "1 secret entry left out" in out.out and "timing in scenes left out" in out.out
    entries = list(json.loads(book.read_text(encoding="utf-8"))["entries"].values())
    river = next(e for e in entries if e["comment"] == "The river spirit is awake")
    assert river["key"] == ["river"] and river["keysecondary"] == ["night"]
    assert river["selectiveLogic"] == 2 and river["order"] == 70 and river["sticky"] == 2
    assert river["useProbability"] and river["probability"] == 40 and river["preventRecursion"]
    assert all("Tom's mother" not in e["content"] for e in entries)
    cli("world", "new", "dale", "--system", "mini-system")
    cli("campaign", "new", "two")
    assert cli("lore", "import", str(book)).code == 0
    assert _fields(cli, "lore:the-river-spirit-is-awake") == {
        "keys": ["river"], "secondary": ["night"], "logic": "not_any", "priority": 70,
        "probability": 40, "group": "spirits", "sticky": 2, "recursive": False,
    }  # fmt: skip
    again = cli("lore", "import", str(book))
    assert "entries already here" in again.out  # a book imported twice doesn't double up


def test_a_character_cards_book_and_a_novelai_lorebook_come_in(cli: Cli, tmp_path: Path) -> None:
    _campaign(cli)
    card = {
        "spec": "chara_card_v2",
        "data": {
            "name": "Mira",
            "character_book": {
                "entries": [
                    {"keys": ["mira"], "content": "Mira heals for coin.", "enabled": True,
                     "insertion_order": 60, "comment": "Mira"},
                    {"keys": ["old war"], "secondary_keys": ["mira"], "enabled": True,
                     "content": "Mira fought in the old war.", "extensions": {"selectiveLogic": 3}},
                    {"keys": ["x"], "content": "off", "enabled": False},
                ]
            },
        },
    }  # fmt: skip
    (tmp_path / "card.json").write_text(json.dumps(card), encoding="utf-8")
    novelai = {
        "lorebookVersion": 5,
        "entries": [
            {"text": "The Sunken Bell rings at low tide.", "displayName": "Sunken Bell",
             "keys": ["bell", "tide"], "enabled": True},
            {"text": "", "keys": ["nothing"]},
        ],
    }  # fmt: skip
    (tmp_path / "bell.lorebook").write_text(json.dumps(novelai), encoding="utf-8")
    first = cli("lore", "import", str(tmp_path / "card.json"), "--scope", "world")
    assert first.code == 0 and "1 disabled entry left out" in first.out
    assert _fields(cli, "lore:mira")["priority"] == 60
    assert _fields(cli, "lore:mira-fought-in-the-old-war")["logic"] == "and_all"
    second = cli("lore", "import", str(tmp_path / "bell.lorebook"))
    assert second.code == 0 and "1 entry left out" in second.out
    assert "The Sunken Bell rings at low tide." in cli("lore", "scan", "the bell tolls").out


def test_what_isnt_a_lorebook_is_refused(cli: Cli, tmp_path: Path) -> None:
    _campaign(cli)
    (tmp_path / "x.json").write_text('{"name": "nothing here"}', encoding="utf-8")
    (tmp_path / "y.json").write_text("not json", encoding="utf-8")
    assert "isn't a lorebook" in cli("lore", "import", str(tmp_path / "x.json")).err
    assert "isn't JSON" in cli("lore", "import", str(tmp_path / "y.json")).err
