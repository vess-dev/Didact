"""Helpers for the dice tests: roll with exact faces or a fixed stream."""

from collections.abc import Mapping

from didact.expr import (
    HashStream,
    PhysicalFaces,
    Registry,
    RollContext,
    Rolled,
    default_registry,
    run,
)
from didact.expr.model import Value
from didact.expr.render import line


def roll(
    text: str,
    faces: str | None = None,
    *,
    variables: Mapping[str, Value] | None = None,
    registry: Registry | None = None,
    key: str = "test",
) -> Rolled:
    """Roll `text`; with `faces` ("6,5,3") the dice show exactly those, in the order drawn."""
    source = PhysicalFaces.parse(faces) if faces is not None else HashStream(key)
    ctx = RollContext(registry or default_registry(), source, dict(variables or {}))
    return run(text, ctx)


def shown(
    text: str,
    faces: str | None = None,
    *,
    variables: Mapping[str, Value] | None = None,
    registry: Registry | None = None,
) -> str:
    """The one-line rendering without a roll label, e.g. `4d6kh3 → [6 5 3 (2)] = 14`."""
    rolled = roll(text, faces, variables=variables, registry=registry)
    return line("", rolled.canonical, rolled.result)
