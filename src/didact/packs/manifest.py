"""The pack manifest (`pack.yaml`): identity, dependencies, license, content folders."""

import re
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from didact.core.i18n import _
from didact.core.ids import NAME_RE
from didact.packs.kinds import ALL_KINDS, DEFAULT_FOLDERS
from didact.packs.versions import Version

type PackKind = Literal["base", "system", "oracle", "supplement", "setting", "adventure"]

ALIAS_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class License(Strict):
    spdx: str = ""
    redistributable: bool = True  # False: `pack export` refuses (a personal transcription)
    attribution: str = ""


class Requires(Strict):
    didact: str = ""  # a version range, e.g. ">=0.1"
    packs: list[str] = Field(default_factory=list)  # "core" or "core >=0.1"


class Manifest(Strict):
    id: str
    name: str
    kind: PackKind
    version: str
    description: str = ""
    alias: str | None = None  # the name used in expressions: `mysys.attack(d8, d8)`
    requires: Requires = Field(default_factory=Requires)
    extends: list[str] = Field(default_factory=list)
    # A hack: the items of the packs it extends that it drops, as patterns by kind
    # (`{table: ["spell-*"], entry: ["*", "!rope"]}`); what it replaces is never dropped.
    hides: dict[str, list[str]] = Field(default_factory=dict)
    license: License = Field(default_factory=License)
    content: dict[str, str] = Field(default_factory=dict)
    plugins: list[str] = Field(default_factory=list)
    guide: str = "GUIDE.md"
    settings: dict[str, object] = Field(default_factory=dict)
    source: dict[str, object] = Field(default_factory=dict)  # book title, url, pages (coverage)

    @field_validator("id")
    @classmethod
    def _id(cls, value: str) -> str:
        if not NAME_RE.match(value):
            raise ValueError(_("use lowercase letters, digits and dashes, e.g. `my-system`"))
        return value

    @field_validator("version")
    @classmethod
    def _version(cls, value: str) -> str:
        Version.parse(value)
        return value

    @field_validator("alias")
    @classmethod
    def _alias(cls, value: str | None) -> str | None:
        if value is not None and not ALIAS_RE.match(value):
            raise ValueError(_("use lowercase letters, digits and underscores, e.g. `mysys`"))
        return value

    @field_validator("hides")
    @classmethod
    def _hides(cls, value: dict[str, list[str]]) -> dict[str, list[str]]:
        unknown = sorted(set(value) - set(ALL_KINDS))
        if unknown:
            raise ValueError(_("unknown kind(s) in `hides`: {kinds}", kinds=", ".join(unknown)))
        return value

    @model_validator(mode="after")
    def _hides_needs_a_base(self) -> Self:
        if self.hides and not self.extends:
            raise ValueError(
                _("`hides` drops items of the pack this one extends: name it in `extends`")
            )
        return self

    @field_validator("content")
    @classmethod
    def _content(cls, value: dict[str, str]) -> dict[str, str]:
        unknown = sorted(set(value) - set(DEFAULT_FOLDERS))
        if unknown:
            raise ValueError(_("unknown content kind(s): {kinds}", kinds=", ".join(unknown)))
        return value
