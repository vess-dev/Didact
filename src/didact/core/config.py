"""Where Didact keeps things: the data home (source of truth) and the disposable cache."""

import hashlib
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

ENV_HOME = "DIDACT_HOME"
ENV_CACHE = "DIDACT_CACHE"
DEFAULT_HOME = Path("~/Documents/DidactLibrary")


@dataclass(frozen=True, slots=True)
class Config:
    """Resolved locations for one invocation."""

    home: Path
    cache: Path

    @property
    def index_path(self) -> Path:
        """The SQLite index for this home. Disposable: `didact reindex` rebuilds it."""
        digest = hashlib.sha256(str(self.home).encode()).hexdigest()[:16]
        return self.cache / "index" / f"{digest}.sqlite"


def default_cache_dir() -> Path:
    """The platform's cache directory for Didact (never synced, safe to delete)."""
    system = sys.platform  # a plain str, so type checkers don't prune other platforms
    if system == "darwin":
        return Path.home() / "Library" / "Caches" / "didact"
    if system == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "didact" / "Cache"
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "didact"


def resolve_config(
    home: str | os.PathLike[str] | None = None,
    cache: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> Config:
    """Resolve locations: explicit argument > environment variable > default."""
    environ = os.environ if env is None else env
    raw_home = home or environ.get(ENV_HOME) or DEFAULT_HOME
    raw_cache = cache or environ.get(ENV_CACHE) or default_cache_dir()
    return Config(
        home=Path(raw_home).expanduser().resolve(),
        cache=Path(raw_cache).expanduser().resolve(),
    )
