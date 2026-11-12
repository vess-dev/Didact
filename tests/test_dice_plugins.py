"""A pack adds a dice effect (the `lucky` test pack) with no change to Didact's core."""

from pathlib import Path

import pytest

from didact.core.errors import InvalidError
from didact.expr import default_registry, load_plugin
from didact.expr.engine import PoolResult
from tests.dice_helpers import roll, shown
from tests.plugin_pack import write


@pytest.fixture
def plugin(tmp_path: Path) -> Path:
    return write(tmp_path) / "plugins" / "lucky.py"


def test_a_plugin_adds_a_dice_effect(plugin: Path) -> None:
    registry = default_registry()
    assert load_plugin(plugin, registry, namespace="lucky") == ["lucky.charm"]
    # two sixes are lucky: each adds a d4 (here 3 and 4) that can't explode
    assert shown("3d6~", "6,2,6,3,4", registry=registry) == (
        "3d6~ → [6 2 6 charm:3 charm:4] = 21 (doubles)"
    )
    result = roll("3d6~", "6,2,6,3,4", registry=registry).result
    assert isinstance(result, PoolResult)
    added = [d for d in result.pool.dice if d.added_by == "charm"]
    assert [d.value for d in added] == [3, 4] and not any(d.explodable for d in added)


def test_plugins_stay_in_their_own_registry(plugin: Path) -> None:
    with pytest.raises(InvalidError, match="unexpected '~'"):
        roll("3d6~")  # the default registry has no such effect
    registry = default_registry()
    load_plugin(plugin, registry, namespace="lucky")
    with pytest.raises(InvalidError, match=r"already registered|already in use"):
        load_plugin(plugin, registry, namespace="lucky")


def test_a_broken_plugin_is_reported(tmp_path: Path) -> None:
    broken = tmp_path / "broken.py"
    broken.write_text("raise RuntimeError('boom')\n", encoding="utf-8")
    with pytest.raises(InvalidError, match="failed to load: boom"):
        load_plugin(broken, default_registry(), namespace="broken")
