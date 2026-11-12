"""A fight starting and ending runs the packs' `combat_start` and `combat_end` triggers (`for:
pcs` too) inside the command's own change, once per fight: they read the fight
(`@combat.round`, `@combat.fighters`), so do the rules they run, and any rule reads the fight
under way. Leaving the fight doesn't end it, and nothing runs when no fight starts or ends (the
`fight-lite` fixture)."""

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "fight-lite", "--seed", "fight").code == 0
    assert cli("campaign", "new", "c", "--seed", "fight").code == 0
    for record in (("pc", "Freya"), ("pc", "Ansel"), ("npc", "Troll"), ("npc", "Wolf")):
        assert cli("new", *record).code == 0


def test_a_fights_start_and_end_run_their_triggers_once(cli: Cli) -> None:
    setup(cli)
    started = cli("combat", "start", "freya", "troll", "wolf").out
    assert "trigger fight-lite.opening (Freya): Freya draws steel (round 1, 3 fighters)." in started
    assert "(Ansel)" not in started  # a PC out of the fight: its `when:` doesn't hold
    assert "Freya strikes in round 1." in cli("do", "strike", "who=freya").out
    assert "has struck this fight already" in cli("do", "strike", "who=freya").out
    refused = cli("combat", "start", "ansel", "wolf")  # one fight at a time: nothing runs
    assert refused.code == 1 and "trigger" not in refused.out + refused.err
    cli("combat", "next")
    assert "round 2" in cli("combat", "next").out
    for fighter in ("troll", "wolf"):  # leaving doesn't end the fight
        assert "trigger" not in cli("combat", "leave", fighter).out

    preview = cli("combat", "end", "--dry-run").out
    assert "dry run" in preview and "The fight ends in round 2." in preview
    assert cli("combat", "status").out.startswith("round 2")  # nothing ended
    ended = cli("combat", "end").out
    closing = "trigger fight-lite.closing: The fight ends in round 2. · Still standing: pc:freya."
    assert closing in ended  # `tally`, which the trigger runs, reads the fight too
    assert "trigger fight-lite.refresh (Freya): pc:freya: used = []" in ended
    again = cli("combat", "end").out
    assert "no fight was on" in again and "trigger" not in again
    assert "Freya strikes in round 0." in cli("do", "strike", "who=freya").out  # fresh again

    assert cli("undo").code == 0 and cli("undo").code == 0  # the strike, then the fight's end
    assert cli("combat", "status").out.startswith("round 2")
    assert "has struck this fight already" in cli("do", "strike", "who=freya").out
