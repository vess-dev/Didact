"""A generator's `stop:` hints at the campaign's options only when it sits under a condition that
reads one (the `stop-lite` fixture). Taking from a list what it doesn't hold changes nothing and
says so (one it could never hold is still refused), and a trigger that fails says it's the
trigger, and how to get on without it (the `wear-lite` fixture)."""

from tests.conftest import Cli

OPTIONS = "the campaign's options: `didact session zero`"


def test_a_stops_hint_fits_why_it_stops(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "stop-lite").code == 0
    assert cli("campaign", "new", "c").code == 0
    vault = cli("gen", "run", "stop-lite.dungeon", "--auto")
    assert vault.code == 1 and "This game's dungeons are vaults" in vault.err
    assert "nothing was drafted: it stops here, for the reason it gives" in vault.err
    assert OPTIONS not in vault.err
    assert cli("gen", "run", "stop-lite.spellbook", "--auto").code == 0  # magic: on
    assert cli("campaign", "profile", "magic=off").code == 0
    book = cli("gen", "run", "stop-lite.spellbook", "--auto")
    assert book.code == 1 and "No magic (an option)" in book.err and OPTIONS in book.err


def setup(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "wear-lite").code == 0
    assert cli("campaign", "new", "c").code == 0
    assert cli("new", "pc", "Ana", "--set", "hp=4").code == 0
    assert cli("session", "start").code == 0


def test_taking_away_what_isnt_there_changes_nothing(cli: Cli) -> None:
    setup(cli)
    gone = cli("set", "ana", "conditions-=warded")
    assert gone.code == 0 and "no changes: it already looks like that" in gone.out
    assert "note: conditions has no warded" in gone.out
    assert cli("set", "ana", "conditions+=warded").code == 0
    assert "pc:ana: conditions-=warded" in cli("set", "ana", "conditions-=warded").out
    typo = cli("set", "ana", "marks-=brnd")  # what the field could never hold: a mistake still
    assert typo.code == 1 and "marks: 'brnd' isn't allowed (allowed: brand, scar)" in typo.err
    assert "note: marks has no scar" in cli("set", "ana", "marks-=scar").out
    assert cli("scene", "new", "At the gate").code == 0
    ended = cli("scene", "end", "--summary", "Over.")  # a trigger without a guard is fine
    assert ended.code == 0, ended.err
    assert "pc:ana: conditions -= warded (conditions has no warded)" in ended.out


def test_a_trigger_that_fails_says_how_to_get_on(cli: Cli) -> None:
    setup(cli)
    assert cli("set", "ana", "conditions+=cursed").code == 0
    assert cli("scene", "new", "At the gate").code == 0
    stuck = cli("scene", "end", "--summary", "Over.")
    assert stuck.code == 1 and "trigger wear-lite.curse-bites failed:" in stuck.err
    away = '`didact override add trigger wear-lite.curse-bites --data \'{"on": "manual"}\'`'
    assert away in stuck.err
    manual = ("--data", '{"on": "manual"}')
    assert cli("override", "add", "trigger", "wear-lite.curse-bites", *manual).code == 0
    assert cli("scene", "end", "--summary", "Over.").code == 0  # on without it
