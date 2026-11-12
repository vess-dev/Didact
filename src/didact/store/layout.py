"""Where things live inside the data home."""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from didact.core.ids import GLOBAL, NAME_RE, RESERVED_TYPES, SLUG_RE, TYPE_RE, EntityId, Scope

SCHEMA_VERSION = 1  # data-home layout version; `didact migrate` upgrades older homes


@dataclass(frozen=True, slots=True)
class Layout:
    home: Path

    @property
    def state_file(self) -> Path:
        return self.home / "state.yaml"

    @property
    def log_file(self) -> Path:
        return self.home / "log" / "events.jsonl"

    @property
    def counters_file(self) -> Path:
        """Roll numbers and other counters that undo never rewinds."""
        return self.home / "log" / "counters.json"

    @property
    def applying_file(self) -> Path:
        """Names the change being written, while it is (`store/recovery.py`)."""
        return self.home / "log" / "applying.json"

    @property
    def lock_file(self) -> Path:
        return self.home / ".lock"

    @property
    def staging_dir(self) -> Path:
        return self.home / ".staging"

    @property
    def global_root(self) -> Path:
        return self.home / "global"

    @property
    def systems_dir(self) -> Path:
        return self.home / "systems"

    @property
    def worlds_dir(self) -> Path:
        return self.home / "worlds"

    @property
    def packs_dir(self) -> Path:
        return self.home / "packs"

    def world_dir(self, world: str) -> Path:
        return self.worlds_dir / world

    def world_file(self, world: str) -> Path:
        return self.world_dir(world) / "world.yaml"

    def campaign_dir(self, world: str, campaign: str) -> Path:
        return self.world_dir(world) / "campaigns" / campaign

    def campaign_file(self, world: str, campaign: str) -> Path:
        return self.campaign_dir(world, campaign) / "campaign.yaml"

    def rel(self, path: Path) -> str:
        """A path relative to the home, POSIX style (as stored in the event log)."""
        return path.relative_to(self.home).as_posix()

    def abs(self, rel: str) -> Path:
        return self.home / PurePosixPath(rel)


def entity_location(rel: str) -> tuple[Scope, EntityId] | None:
    """If a home-relative path is an entity file, return its scope and id."""
    parts = PurePosixPath(rel).parts
    if not parts or not parts[-1].endswith(".md"):
        return None
    slug = parts[-1][:-3]
    match parts:
        case ("global", type_, _):
            scope = GLOBAL
        case ("systems", pack, type_, _) if NAME_RE.match(pack):
            scope = Scope("system", pack)
        case ("worlds", world, type_, _) if NAME_RE.match(world):
            scope = Scope("world", world)
        case ("worlds", world, "campaigns", campaign, type_, _) if NAME_RE.match(
            world
        ) and NAME_RE.match(campaign):
            scope = Scope("campaign", campaign)
        case _:
            return None
    if not TYPE_RE.match(type_) or type_ in RESERVED_TYPES or not SLUG_RE.match(slug):
        return None
    return scope, EntityId(type_, slug)
