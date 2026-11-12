"""A command whose record can only be of one type takes a name that records of other types share
as the one of its type: `track roll` and `track tick` a tracker (a foe's pool is named as its
card), `quest done` a quest, `visit` and `map --within` a place, `party add --as pc` a PC. An id
still works, a name no record of that type has gets the error it always got, and elsewhere the
name is still both of them (the `call-lite` fixture)."""

from tests.conftest import Cli


def test_a_command_for_one_type_takes_the_record_of_that_type(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "call-lite", "--seed", "typed").code == 0
    assert cli("campaign", "new", "c", "--seed", "typed").code == 0
    assert cli("new", "monster", "Draugr", "--set", "hp=6").code == 0
    assert cli("track", "new", "Draugr", "--kind", "pool", "--size", "3").code == 0  # its pool
    rolled = cli("track", "roll", "draugr")
    assert rolled.code == 0 and "Draugr: " in rolled.out and "pool Draugr" in rolled.out
    assert cli("track", "roll", "track:draugr").code == 0  # an id, as ever
    assert cli("new", "monster", "Warg").code == 0
    assert cli("track", "new", "Warg", "--kind", "clock", "--size", "4").code == 0
    ticked = cli("track", "tick", "warg")
    assert ticked.code == 0 and "Warg" in ticked.out
    shared = cli("show", "draugr")  # elsewhere the name is still both of them
    assert shared.code == 1 and "matches several records" in shared.err
    missing = cli("track", "roll", "barrow-wight")  # no tracker of that name: as before
    assert missing.code == 1 and "nothing called 'barrow-wight'" in missing.err
    assert cli("quest", "new", "The Barrow").code == 0
    assert cli("new", "loc", "The Barrow").code == 0
    assert "quest:the-barrow done" in cli("quest", "done", "the barrow").out
    visited = cli("visit", "the barrow")  # the place, not the quest
    assert visited.code == 0 and "the party is at The Barrow" in visited.out
    assert cli("map", "--within", "the barrow").code == 0
    assert cli("new", "pc", "Wren", "--set", "hp=4").code == 0  # she joins the party
    assert cli("party", "remove", "pc:wren", "--why", "retired").code == 0
    assert cli("new", "npc", "Wren").code == 0
    joined = cli("party", "add", "wren", "--as", "pc")  # back: the PC, not the NPC
    assert joined.code == 0 and "Wren joins the party (pc)" in joined.out
