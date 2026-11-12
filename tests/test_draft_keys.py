"""A field naming a key of the draft holds the id of the record that key becomes on commit:
when a character is made, and when a level-up makes a record beside the one it changes (the
`keys-lite` fixture)."""

import json
from typing import Any

from tests.conftest import Cli


def _mechanics(cli: Cli, ref: str) -> dict[str, Any]:
    shown = cli("show", ref, "--format", "json")
    assert shown.code == 0, shown.err
    return dict(json.loads(shown.out)["mechanics"]["keys-lite"])


def test_a_level_up_points_the_sheet_at_the_record_it_makes(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "keys-lite", "--seed", "keys").code == 0
    assert cli("campaign", "new", "c", "--seed", "keys").code == 0
    assert cli("char", "new", "--mode", "random").code == 0
    assert cli("char", "commit", "c1").code == 0
    assert _mechanics(cli, "wren")["oath"] == "note:an-old-oath"  # made with the character

    drafted = cli("char", "advance", "wren")
    assert "blood: None → pool-1" in drafted.out  # a key, while it's a draft
    done = cli("char", "commit", "c2")
    assert done.code == 0, done.err
    assert "blood None → track:wren-s-blood (made track:wren-s-blood)" in done.out
    assert _mechanics(cli, "wren")["blood"] == "track:wren-s-blood"
    pool = json.loads(cli("show", "track:wren-s-blood", "--format", "json").out)
    assert {"rel": "of", "to": "pc:wren"} in pool["links"]
