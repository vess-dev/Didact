"""Dice and expressions: parse, evaluate, render; plus the plugin API for pack dice effects.

from didact.expr import HashStream, RollContext, default_registry, run
rolled = run("4d6kh3", RollContext(default_registry(), HashStream("seed:1")))
"""

from didact.expr.engine import (
    Die,
    DiePool,
    GroupPool,
    Item,
    Pool,
    Result,
    RollContext,
    Rolled,
    evaluate,
    run,
)
from didact.expr.model import DieSpec, Face, Macro, Registry, Target
from didact.expr.modifiers import default_registry
from didact.expr.parser import canonical, parse
from didact.expr.plugins import load_plugin, modifier
from didact.expr.rng import HashStream, PhysicalFaces, Source

__all__ = [
    "Die",
    "DiePool",
    "DieSpec",
    "Face",
    "GroupPool",
    "HashStream",
    "Item",
    "Macro",
    "PhysicalFaces",
    "Pool",
    "Registry",
    "Result",
    "RollContext",
    "Rolled",
    "Source",
    "Target",
    "canonical",
    "default_registry",
    "evaluate",
    "load_plugin",
    "modifier",
    "parse",
    "run",
]
