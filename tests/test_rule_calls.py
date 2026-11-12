"""A rule unsets a field as `didact set --unset` does (one not set changes nothing, and says so;
a key no field has is a mistake still); `do: … as: x` reads what the other rule bound; a `ref`
parameter's `to:` picks the record of that type when a name has several (the `call-lite`
fixture)."""

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "call-lite", "--seed", "call").code == 0
    assert cli("campaign", "new", "c", "--seed", "call").code == 0
    assert cli("new", "pc", "Ana", "--set", "hp=4").code == 0


def test_a_rule_unsets_a_field_as_set_does(cli: Cli) -> None:
    setup(cli)
    assert cli("track", "new", "Werewolf curse", "--kind", "clock", "--size", "6").code == 0
    assert cli("set", "ana", "curse_timer=track:werewolf-curse").code == 0
    cured = cli("do", "cure", "who=ana").out
    assert "pc:ana: unset curse_timer" in cured and "Ana is free of the curse." in cured
    assert "curse_timer" not in cli("show", "ana", "--format", "json").out
    again = cli("do", "cure", "who=ana").out  # nothing to take away: no harm
    assert "pc:ana: unset curse_timer (no key 'curse_timer' to remove)" in again
    by_hand = cli("set", "ana", "--unset", "curse_timer")  # the command, alike
    assert by_hand.code == 0 and "note: no key 'curse_timer' to remove" in by_hand.out
    typo = cli("set", "ana", "--unset", "curse_timre")
    assert typo.code == 1 and "no key 'curse_timre' to remove" in typo.err


def test_do_as_reads_what_the_other_rule_bound(cli: Cli) -> None:
    setup(cli)
    said = cli("do", "supplies").out
    assert "Foraged 2 days of food in the birch wood (luck 1)." in said


def test_a_ref_parameter_takes_the_record_of_its_type(cli: Cli) -> None:
    setup(cli)
    assert cli("new", "monster", "Draugr", "--set", "hp=6").code == 0
    assert cli("track", "new", "Draugr", "--kind", "pool", "--size", "3").code == 0  # its pool
    struck = cli("do", "strike", "foe=draugr")
    assert struck.code == 0 and "Draugr (monster:draugr) takes the blow." in struck.out
    shared = cli("show", "draugr")  # elsewhere the name is still both of them
    assert shared.code == 1 and "matches several records" in shared.err
    wrong = cli("do", "strike", "foe=Ana")
    assert wrong.code == 1 and "foe must be a monster, not pc:ana" in wrong.err
