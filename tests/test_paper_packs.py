"""Paper tests: seven tiny packs, each resolving rolls its own way, prove that the pack
format isn't shaped by one system. Each validates, and its tests (including a smoke-play
script) pass."""

from pathlib import Path

import pytest

from tests.conftest import Cli

PAPER = [
    "ironsworn-lite",  # action vs challenge dice, momentum burn as a pending roll, progress by rank
    "pbta-lite",  # 2d6 + stat bands
    "blades-lite",  # take the highest; 0 dice → 2d6 take the lowest; crit on two 6s; clocks
    "genesys-lite",  # symbol dice that cancel
    "yze-lite",  # success pools, push with banes into stress
    "daggerheart-lite",  # Hope/Fear role-tagged dice, a capped resource
    "grimwild-lite",  # thorns cut the result, diminishing pools, a story-roll oracle
]


@pytest.mark.parametrize("pack", PAPER)
def test_paper_pack(cli: Cli, pack: str) -> None:
    assert cli("pack", "validate", pack).out.startswith(f"✔ ok: {pack} 0.1.0")
    result = cli("pack", "test", pack)
    assert result.code == 0, result.out
    assert "tests passed" in result.out and "✘" not in result.out


def test_a_plugin_pack_validates(cli: Cli, lucky: Path) -> None:
    assert cli("pack", "validate", "lucky").out.startswith("✔ ok: lucky 0.1.0")
