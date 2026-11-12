"""The rulings log: settled once, answered the same way again."""

from tests.conftest import Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("new", "pc", "Freya", "--set", "STR=12", "--set", "hp=4")


def test_rulings_are_recorded_and_come_back(cli: Cli) -> None:
    setup(cli)
    added = cli(
        "ruling", "add", "Can you push a scramble twice?", "No: one push per roll.",
        "--rule", "scramble",
    )  # fmt: skip
    assert added.code == 0 and "(campaign:run)" in added.out
    assert "ruling [ruling:can-you-push-a-scramble-twice]" in added.out
    shared = cli(
        "ruling", "add", "Does armor stop critical damage?", "Yes, armor applies first.",
        "--scope", "system", "--tag", "damage",
    )  # fmt: skip
    assert shared.code == 0 and "(system:mini-system)" in shared.out
    found = cli("ruling", "find", "push").out
    assert found.startswith("1 ruling:") and "→ No: one push per roll." in found
    assert cli("ruling", "find").out.startswith("2 rulings:")
    lookup = cli("rules", "lookup", "armor").out
    assert lookup.startswith("Rulings here (they come first):")
    assert "Does armor stop critical damage? → Yes, armor applies first." in lookup
    run = cli("do", "scramble", "who=freya").out
    assert "ruling [ruling:can-you-push-a-scramble-twice]" in run
    assert cli("ruling", "add", "Q?", "A", "--rule", "nope").code == 1  # no such rule
    cli("campaign", "new", "other")  # the system ruling follows; the campaign one doesn't
    assert cli("ruling", "find").out.startswith("1 ruling:")
