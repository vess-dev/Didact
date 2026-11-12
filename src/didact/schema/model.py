"""Entity type schemas, as packs define them in `schemas/*.yaml`.

type: character
extends: npc                  # optional: inherit another type's fields
label: Character
fields:
  STR: {kind: stat, range: [0, 18], roll: 3d6, on_zero: {trigger: death}}
  hp: {kind: resource, min: 0, roll: d6}
  armor: {kind: derived, expr: "min(3, sum(@inventory.armor))"}
guidance: "Monsters: 3 HP is average, 6 is hardy, 10+ is a serious threat."
"""

from dataclasses import dataclass, field
from typing import cast

from didact.core.output import JSON
from didact.schema.fields import FieldKind, FieldSpec


@dataclass(frozen=True, slots=True)
class TypeSchema:
    type: str
    pack: str
    fields: dict[str, FieldSpec]
    label: str = ""
    description: str = ""
    guidance: str = ""
    open: bool = False  # unknown keys allowed (core types: system-agnostic prose fields)
    sources: tuple[str, ...] = field(default_factory=tuple)
    details: tuple[str, ...] = ()  # suggested detail names (see services.details)

    @property
    def block_key(self) -> str:
        """Where values live: `fields` for the core pack, `mechanics.<pack>` for systems."""
        return "fields" if self.pack == "core" else f"mechanics.{self.pack}"

    def field(self, name: str) -> FieldSpec | None:
        if name in self.fields:
            return self.fields[name]
        folded = {k.casefold(): v for k, v in self.fields.items()}
        return folded.get(name.casefold())


def fields_from(data: dict[str, JSON]) -> dict[str, FieldSpec]:
    raw = data.get("fields")
    found: dict[str, FieldSpec] = {}
    for name, spec in raw.items() if isinstance(raw, dict) else []:
        options: dict[str, JSON] = dict(spec) if isinstance(spec, dict) else {"kind": spec}
        kind = cast(FieldKind, str(options.pop("kind", "text")))
        found[name] = FieldSpec(name, kind, options)
    return found
