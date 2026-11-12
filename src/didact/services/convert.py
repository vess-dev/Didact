"""One world, any system: give a record another system's mechanics block.

Values carry over by name (STR stays STR, whatever block it was in); `--fill` rolls or
defaults the rest the target sheet knows how to; anything left is listed for the LLM to decide
from the target pack's guidance (`didact template <type>`).
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from didact.core.errors import InvalidError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.schema import fields as kinds
from didact.schema.sheet import Sheet, sheet_for
from didact.services import packs as pack_service
from didact.store.entity import Entity
from didact.store.repo import Repo


@dataclass(slots=True)
class Converted:
    copied: list[str] = field(default_factory=list)
    filled: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


def target_sheet(repo: Repo, system: str, type_: str) -> Sheet:
    lib = pack_service.library(repo)
    wanted = [w for w in (pack_service.CORE, system) if w in lib.available()]
    if system not in wanted:
        raise InvalidError(_("no pack {pack}", pack=repr(system)), hint=_("see `didact pack list`"))
    packs = lib.resolve(wanted)
    sheet = sheet_for(packs, system, type_)
    if sheet.mechanics is None:
        raise InvalidError(
            _("{system} has no {type} sheet", system=system, type=type_),
            hint=_("see `didact pack info {system}`", system=system),
        )
    return sheet


def convert(entity: Entity, sheet: Sheet, *, roll: Callable[[str, str], int] | None) -> Converted:
    """Fill `entity.mechanics[<target>]` in place."""
    assert sheet.mechanics is not None
    target = sheet.mechanics.pack
    known = _known_values(entity, target)
    block: dict[str, JSON] = dict(entity.mechanics.get(target) or {})  # type: ignore[arg-type]
    result = Converted()
    for spec in sheet.mechanics.fields.values():
        if not spec.stored or spec.name in block:
            continue
        found = known.get(spec.name.casefold())
        if found is not None:
            try:
                block[spec.name] = kinds.coerce(spec, found)
                result.copied.append(spec.name)
                continue
            except kinds.FieldError:
                pass
        expr = spec.opt("roll")
        if roll is not None and isinstance(expr, str):
            block[spec.name] = kinds.coerce(spec, roll(expr, spec.name))
            result.filled.append(f"{spec.name} ({expr})")
        elif roll is not None and spec.opt("default") is not None:
            block[spec.name] = kinds.coerce(spec, spec.opt("default"))
            result.filled.append(f"{spec.name} (default)")
        else:
            result.missing.append(spec.name)
    entity.mechanics[target] = block
    return result


def _known_values(entity: Entity, skip: str) -> dict[str, JSON]:
    """Values by lower-case name from every other mechanics block, then the prose fields."""
    found: dict[str, JSON] = {}
    for system, block in entity.mechanics.items():
        if system == skip or not isinstance(block, dict):
            continue
        for key, value in block.items():
            found.setdefault(key.casefold(), value)
    for key, value in entity.fields.items():
        found.setdefault(key.casefold(), value)
    return found
