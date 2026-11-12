"""The names a rule's steps bind to records (a record an `entity:` step made, a loop's member):
a check that comes back pending keeps them, so its options and its outcome's steps read and
change the record after `didact resolve` as they would at once (the `doom-lite` fixture); and
an `entity:` step never takes a parameter's name, as a loop's member doesn't."""

import json
from pathlib import Path
from typing import Any

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "doom-lite", "--seed", "doom").code == 0
    assert cli("campaign", "new", "c", "--seed", "doom").code == 0
    assert cli("new", "pc", "Freya", "--set", "hp=4").code == 0


def _record(cli: Cli, ref: str) -> Any:  # parsed JSON, read freely in tests
    shown = cli("show", ref, "--format", "json")
    assert shown.code == 0, shown.err
    return json.loads(shown.out)


def _pending(cli: Cli) -> str:
    """Defy the doom: it comes back pending; the roll to resolve."""
    defied = cli("do", "defy", "who=freya")
    assert defied.code == 0, defied.err
    assert "+ track Doom of Freya [track:doom-of-freya]" in defied.out
    return defied.out.split("didact resolve ")[1].split(" ")[0]


def test_a_pending_check_keeps_the_record_it_made(cli: Cli) -> None:
    setup(cli)
    pushed = cli("resolve", _pending(cli), "push")
    assert pushed.code == 0, pushed.err
    assert "track:doom-of-freya: note = pushed" in pushed.out
    assert "Doom of Freya: pushed." in pushed.out  # the outcome's steps read it too
    doom = _record(cli, "track:doom-of-freya")["fields"]
    assert doom["note"] == "pushed" and doom["value"]["value"] == 3  # a push drops a die
    assert cli("undo").code == 0
    assert _record(cli, "track:doom-of-freya")["fields"]["note"] == "waiting"
    accepted = cli("resolve", cli("pending").out.split("#")[1].split(" ")[0], "accept")
    assert accepted.code == 0 and "Doom of Freya: waiting." in accepted.out


def test_an_entity_step_cant_take_a_parameters_name(cli: Cli, tmp_path: Path) -> None:
    pack = tmp_path / "bad-entities"
    (pack / "rules").mkdir(parents=True)
    (pack / "pack.yaml").write_text("id: bad-entities\nname: B\nkind: system\nversion: 0.1.0\n")
    (pack / "rules" / "r.yaml").write_text(
        "action: rise\nparams: {faction: ref, rival: text, who: ref}\nsteps:\n"
        "  - entity: {type: faction, name: The Upstarts}\n"
        "  - {entity: {type: npc, name: Their Leader}, as: rival}\n"
        "  - {if: 'true', then: [{entity: {key: who, type: npc, name: A Spy}}]}\n"
        "  - {entity: {type: faction, name: The Others}, as: others}\n"
    )
    out = cli("pack", "validate", str(pack)).out
    for name, line in (("faction", 4), ("rival", 5), ("who", 6)):
        said = f"an `entity:` step can't call its record {name}: a parameter has that name"
        assert f"rules/r.yaml:{line}: {said}" in out
    assert "call its record others" not in out and "e.g. as: new_faction" in out
