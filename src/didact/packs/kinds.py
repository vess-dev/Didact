"""The kinds of pack content: where each lives and which key names its id.

    rules/save.yaml        check: save            → my-system.save
    rules/options.yaml     option: lethality      → my-system.lethality
    tables/weather.yaml    table: weather         → my-system.weather
    schemas/character.yaml type: character
    compendium/troll.yaml  id: troll, type: monster

Engines register a validator for their kinds (`register_validator`); until then an item is
only checked for a valid id.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

from didact.core.i18n import _
from didact.packs.source import Doc, Problem

ITEM_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
DEFAULT_FOLDERS: dict[str, str] = {
    "schemas": "schemas",
    "tables": "tables",
    "rules": "rules",
    "compendium": "compendium",
    "reference": "reference",
    "tests": "tests",
    "generators": "generators",
    "chargen": "chargen",
    "oracles": "oracles",
    "lore": "lore",
}


def default_alias(pack_id: str) -> str:
    """`my-system` → `my_system`: pack ids with dashes can't be names in expressions."""
    return re.sub(r"[^a-z0-9_]", "_", pack_id)


@dataclass(frozen=True, slots=True)
class Kind:
    name: str
    folder: str  # key in DEFAULT_FOLDERS
    key: str  # the key whose value is the item's id


KINDS: tuple[Kind, ...] = (
    Kind("type", "schemas", "type"),
    Kind("table", "tables", "table"),
    Kind("deck", "tables", "deck"),
    Kind("bag", "tables", "bag"),
    Kind("check", "rules", "check"),
    Kind("action", "rules", "action"),
    Kind("procedure", "rules", "procedure"),
    Kind("trigger", "rules", "trigger"),
    Kind("option", "rules", "option"),
    Kind("entry", "compendium", "id"),
    Kind("test", "tests", "test"),
    Kind("generator", "generators", "generator"),
    Kind("chargen", "chargen", "chargen"),
    Kind("oracle", "oracles", "oracle"),
    Kind("lore", "lore", "lore"),
)
KIND_NAMES = tuple(k.name for k in KINDS)
# Markdown reference sections and glossary terms are kinds too, loaded from their own files.
ALL_KINDS = (*KIND_NAMES, "reference", "term")

type Validator = Callable[[Doc], list[Problem]]
_VALIDATORS: dict[str, Validator] = {}


def register_validator(kind: str, validator: Validator) -> None:
    _VALIDATORS[kind] = validator


def validator_for(kind: str) -> Validator | None:
    _load_engine_validators()
    return _VALIDATORS.get(kind)


def kinds_in(folder: str) -> list[Kind]:
    return [k for k in KINDS if k.folder == folder]


def detect(doc: Doc, folder: str) -> tuple[Kind, str] | Problem:
    """Which kind an item is (by its key) and its id."""
    candidates = kinds_in(folder)
    for kind in candidates:
        value = doc.data.get(kind.key)
        if value is None:
            continue
        if not isinstance(value, str) or not ITEM_ID.match(value):
            return doc.problem(
                (kind.key,),
                _("invalid {kind} id {value}", kind=kind.name, value=repr(value)),
                _("use lowercase letters, digits and dashes, e.g. `wilderness-events`"),
            )
        return kind, value
    keys = ", ".join(f"`{k.key}: <id>`" for k in candidates)
    return doc.problem(
        (),
        _("can't tell what kind of {folder} item this is", folder=folder),
        _("start it with one of {keys}", keys=keys),
    )


_LOADED = False


def _load_engine_validators() -> None:
    """Engines register validators when imported; import the ones that exist."""
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    import importlib

    for module in (
        "didact.schema.validate",
        "didact.tables.validate",
        "didact.rules.validate",
        "didact.packs.entries",
        "didact.packs.testing",
        "didact.packs.lore",
        "didact.oracles.validate",
    ):
        try:
            importlib.import_module(module)
        except ModuleNotFoundError as exc:
            if not (exc.name and module.startswith(exc.name)):
                raise  # a real import error inside an existing engine
