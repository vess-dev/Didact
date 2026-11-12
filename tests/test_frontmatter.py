"""Front matter: round trips keep hand edits; YAML 1.1 traps are avoided."""

import pytest

from didact.core.errors import InvalidError
from didact.store import frontmatter as fm
from didact.store.entity import CORE_ORDER


def test_new_document_layout() -> None:
    text = fm.render(
        {
            "id": "npc:tom",
            "type": "npc",
            "name": "Tom",
            "tags": ["a", "b"],
            "links": [{"rel": "ally", "to": "npc:ann"}],
        },
        "Prose.",
        order=CORE_ORDER,
    )
    assert text == (
        "---\nid: npc:tom\ntype: npc\nname: Tom\ntags: [a, b]\n"
        "links:\n  - {rel: ally, to: npc:ann}\n---\n\nProse.\n"
    )


def test_comments_and_order_survive_edits() -> None:
    original = (
        "---\nid: npc:tom  # keep me\ntype: npc\nname: Tom\n"
        "created: '2026-01-01T00:00:00Z'\n---\n\nBody.\n"
    )
    yaml_text, body = fm.split(original, where="t")
    data = fm.to_plain(fm.load(yaml_text, where="t"))
    assert isinstance(data, dict)
    data["aliases"] = ["Tommy"]
    updated = fm.render(data, body, previous=original, order=CORE_ORDER)
    assert "id: npc:tom  # keep me" in updated
    assert updated.index("aliases:") < updated.index("created:")  # canonical position, not appended


@pytest.mark.parametrize("word", ["no", "yes", "on", "off", "null", "True"])
def test_yaml11_words_stay_strings(word: str) -> None:
    text = fm.render({"id": "npc:x", "type": "npc", "name": "X", "fields": {"motto": word}}, "")
    yaml_text, _ = fm.split(text, where="t")
    assert f"motto: '{word}'" in text
    data = fm.to_plain(fm.load(yaml_text, where="t"))
    assert isinstance(data, dict) and data["fields"] == {"motto": word}


def test_multiline_strings_become_blocks() -> None:
    text = fm.render({"id": "npc:x", "type": "npc", "name": "X", "fields": {"note": "a\nb"}}, "")
    assert "note: |-\n" in text


def test_split_errors_are_helpful() -> None:
    with pytest.raises(InvalidError, match="missing front matter"):
        fm.split("no fence", where="f.md")
    with pytest.raises(InvalidError, match="not closed"):
        fm.split("---\nid: x\n", where="f.md")
