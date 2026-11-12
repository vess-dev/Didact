"""Command modules. Importing a module registers its commands.

Rule: command modules stay light at import time. Heavy libraries (pydantic, ruamel.yaml)
are imported inside command bodies, so `didact --version` and `didact roll` start fast.
"""

import importlib

MODULES: tuple[str, ...] = (
    "didact.commands.meta",
    "didact.commands.library",
    "didact.commands.records",
    "didact.commands.admin",
    "didact.commands.dice",
    "didact.commands.packs",
    "didact.commands.sheets",
    "didact.commands.tables",
    "didact.commands.decks",
    "didact.commands.rules",
    "didact.commands.compendium",
    "didact.commands.reference",
    "didact.commands.house",
    "didact.commands.play",
    "didact.commands.tracking",
    "didact.commands.combat",
    "didact.commands.inventory",
    "didact.commands.knowledge",
    "didact.commands.names",
    "didact.commands.profile",
    "didact.commands.rulings",
    "didact.commands.party",
    "didact.commands.lore",
    "didact.commands.oracles",
    "didact.commands.lists",
    "didact.commands.care",
    "didact.commands.drafts",
    "didact.commands.web",
    "didact.commands.docs",
)


def load_all() -> None:
    """Import every command module so the registry is complete."""
    for name in MODULES:
        importlib.import_module(name)
