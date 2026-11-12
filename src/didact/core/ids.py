"""Identifiers: entity ids (`type:slug`), scopes, and qualified references (`id@scope`)."""

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from didact.core.errors import InvalidError
from didact.core.i18n import _

type ScopeKind = Literal["global", "system", "world", "campaign"]

TYPE_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")  # world, campaign and pack ids
MAX_SLUG = 64

# Directory names that live inside scope roots and therefore can't be entity types.
RESERVED_TYPES = frozenset(
    {
        # directories inside scope roots
        "campaigns",
        "maps",
        "views",
        "transcripts",
        "log",
        "packs",
        "lore-index",
        "homebrew",  # systems/<pack>/homebrew: additions to a pack
        "state",  # decks, bags and other campaign state
        "journal",  # beats, one file per session
        "workspace",  # rulebook ingest workspaces
        "overrides",  # house rules at world or campaign scope
        # scope prefixes, so `world:vale` can never be mistaken for a record id
        "world",
        "campaign",
        "system",
        "global",
    }
)


def slugify(text: str) -> str:
    """Turn a name into a stable ASCII slug: "Old Tom's Inn" → "old-tom-s-inn"."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:MAX_SLUG].rstrip("-") or "unnamed"


def normalize_name(text: str) -> str:
    """How names and aliases are compared: case-folded, single-spaced."""
    return " ".join(text.casefold().split())


def check_type(value: str) -> str:
    if not TYPE_RE.match(value) or value in RESERVED_TYPES:
        raise InvalidError(
            _("invalid entity type {type}", type=repr(value)),
            hint=_(
                "use lowercase letters, digits and dashes (e.g. npc, loc, item, faction, quest)"
            ),
        )
    return value


def check_name_id(value: str, what: str) -> str:
    if not NAME_RE.match(value):
        raise InvalidError(
            _("invalid {what} id {value}", what=what, value=repr(value)),
            hint=_(
                "use lowercase letters, digits and dashes, e.g. {example}",
                example=repr(slugify(value)),
            ),
        )
    return value


@dataclass(frozen=True, slots=True, order=True)
class EntityId:
    """`type:slug`, e.g. `npc:sweeney`."""

    type: str
    slug: str

    def __str__(self) -> str:
        return f"{self.type}:{self.slug}"

    @classmethod
    def parse(cls, text: str) -> EntityId:
        type_, sep, slug = text.strip().partition(":")
        if (
            not sep
            or not TYPE_RE.match(type_)
            or type_ in RESERVED_TYPES
            or not SLUG_RE.match(slug)
            or len(slug) > MAX_SLUG
        ):
            raise InvalidError(
                _("invalid entity id {id}", id=repr(text)),
                hint=_("ids look like `type:slug`, e.g. `npc:sweeney`"),
            )
        return cls(type_, slug)

    @staticmethod
    def looks_like(text: str) -> bool:
        type_, sep, slug = text.strip().partition(":")
        return bool(
            sep and TYPE_RE.match(type_) and type_ not in RESERVED_TYPES and SLUG_RE.match(slug)
        )


@dataclass(frozen=True, slots=True, order=True)
class Scope:
    """Where a record lives: `global`, `system:<pack>`, `world:<id>` or `campaign:<id>`."""

    kind: ScopeKind
    name: str | None = None

    def __str__(self) -> str:
        return self.kind if self.name is None else f"{self.kind}:{self.name}"

    @classmethod
    def parse(cls, text: str) -> Scope:
        kind, _sep, name = text.strip().partition(":")
        match kind:
            case "global" if not name:
                return GLOBAL
            case "system" | "world" | "campaign" if name:
                return cls(kind, check_name_id(name, kind))
        raise InvalidError(
            _("invalid scope {scope}", scope=repr(text)),
            hint=_("scopes are `global`, `system:<pack>`, `world:<id>` or `campaign:<id>`"),
        )


GLOBAL = Scope("global")


@dataclass(frozen=True, slots=True)
class Ref:
    """A reference typed by a user: an id, optionally pinned to a scope (`npc:tom@world:vale`)."""

    id: EntityId
    scope: Scope | None = None

    def __str__(self) -> str:
        return str(self.id) if self.scope is None else f"{self.id}@{self.scope}"

    @classmethod
    def parse(cls, text: str) -> Ref:
        id_text, sep, scope_text = text.strip().partition("@")
        return cls(EntityId.parse(id_text), Scope.parse(scope_text) if sep else None)
