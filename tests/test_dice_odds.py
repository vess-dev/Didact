"""Dice odds. Exact answers through icepool agree with the engine's own dice."""

import importlib
from fractions import Fraction
from types import ModuleType

import pytest

from didact.expr import default_registry
from didact.expr.odds import odds

REGISTRY = default_registry()


def test_exact_odds() -> None:
    check = odds("2d6 >= 8", REGISTRY)
    assert check.method == "exact" and check.is_check
    assert check.chance == pytest.approx(float(Fraction(15, 36)))
    stats = odds("4d6kh3", REGISTRY)
    assert stats.method == "exact"
    assert stats.mean == pytest.approx(12.2446, abs=1e-4)
    assert odds("d20 <= @STR", REGISTRY, {"STR": 12}).chance == pytest.approx(0.6)


@pytest.mark.parametrize(
    "text",
    [
        "4d6kh3", "2d6r1", "d6!", "d6!>=5", "2d6ro<3", "{d8, d6}kh1", "6d10>=8f1", "d20ms<=12",
        "3d6min2", "2dF + d66 // 10", "d{0,0,1,1,2,3} * 2", "max(d6, d8) - abs(-2)",
    ],
)  # fmt: skip
def test_exact_odds_match_the_engine(text: str) -> None:
    """The icepool adapter must mean what the engine means: compare with simulation."""
    exact = odds(text, REGISTRY)
    simulated = odds(text, REGISTRY, exact=False, samples=4000)
    assert exact.method == "exact" and simulated.method == "simulated"
    tolerance = 5 * exact.sd / 4000**0.5 + 1e-9
    assert simulated.mean == pytest.approx(exact.mean, abs=tolerance)


def test_unsupported_modifiers_are_simulated() -> None:
    result = odds("4d6u", REGISTRY, samples=500)
    assert result.method == "simulated" and result.samples == 500
    assert result.why_simulated == "unique is simulated"


def test_without_icepool_everything_is_simulated(monkeypatch: pytest.MonkeyPatch) -> None:
    real = importlib.import_module

    def fake(name: str, package: str | None = None) -> ModuleType:
        if name == "icepool":
            raise ImportError(name)
        return real(name, package)

    monkeypatch.setattr("didact.expr.odds.importlib.import_module", fake)
    result = odds("2d6 >= 8", REGISTRY, samples=500)
    assert result.method == "simulated" and "icepool isn't installed" in str(result.why_simulated)
