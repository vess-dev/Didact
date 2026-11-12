"""A record made without `key:` has no key to swap: a field that reads like one stays as written,
in a rule and in a draft alike; a key the pack wrote (`key:`, or a name it refers to it by,
`as:`) becomes the record's id (the `keyless-lite` fixture)."""

import json
from typing import Any

from tests.conftest import Cli


def _fields(cli: Cli, ref: str) -> Any:  # parsed JSON, read freely in tests
    return json.loads(cli("show", ref, "--format", "json").out)["fields"]


def test_a_field_like_a_key_stays_as_written(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "keyless-lite").code == 0
    assert cli("campaign", "new", "c").code == 0
    assert "+ track Demo [track:demo]" in cli("do", "make-tracker").out
    assert _fields(cli, "track:demo")["kind"] == "track"  # not track:demo
    assert cli("gen", "run", "keyless-lite.camp", "--auto").code == 0
    assert cli("gen", "commit", "g1").code == 0
    assert _fields(cli, "loc:the-camp")["kind"] == "loc-1"  # its draft key, but none it named
    keeper = _fields(cli, "npc:the-keeper")
    assert keeper["home"] == "loc:the-ford"  # `as: ford`: a name the pack refers to it by
    assert keeper["role"] == "npc:the-keeper"  # its own `key:`: swapped (pick keys no field holds)
