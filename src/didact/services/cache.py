"""Didact's disposable caches, and clearing them.

Nothing in a cache is the truth; the library's files are. Two kinds:

- **search indexes**: one SQLite file per library, in the cache folder (`index/`). The next
  command that opens a library rebuilds its index from the files.
- **compiled packs**: pack bundles compiled from YAML (`packs/` in the cache folder), rebuilt
  when a pack loads.
Only those files are touched: never anything else in the cache folder (it might be pointed
somewhere shared with `DIDACT_CACHE`), never the library, and never what `pack build` wrote
into a pack's `.build/` folder (output you asked for, not a cache Didact reads).
"""

from dataclasses import dataclass, field
from pathlib import Path

from didact.core.config import Config
from didact.core.errors import InvalidError
from didact.core.i18n import _

INDEX_SUFFIXES = (".sqlite", ".sqlite-wal", ".sqlite-shm", ".sqlite-journal")
KINDS = ("search indexes", "compiled packs")


@dataclass(slots=True)
class Part:
    """One kind of cached data: its files and their total size."""

    kind: str
    files: list[Path] = field(default_factory=list)

    @property
    def count(self) -> int:
        """How many there are: databases (not their journal files), bundles."""
        return sum(1 for p in self.files if not p.name.endswith(INDEX_SUFFIXES[1:]))

    @property
    def size(self) -> int:
        return sum(p.stat().st_size for p in self.files if p.is_file())


def parts(config: Config) -> list[Part]:
    """What's cached right now, by kind."""
    _check(config)
    index = Part(KINDS[0], _files(config.cache / "index", INDEX_SUFFIXES))
    bundles = Part(KINDS[1], _files(config.cache / "packs", (".json",)))
    return [index, bundles]


def clear(config: Config) -> list[Part]:
    """Delete every cached file (and the folders that leaves empty). Returns what went."""
    found = parts(config)
    for part in found:
        for path in part.files:
            path.unlink(missing_ok=True)
        for folder in {p.parent for p in part.files}:
            if folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()
    return found


def _files(folder: Path, suffixes: tuple[str, ...]) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.is_file() and p.name.endswith(suffixes))


def _check(config: Config) -> None:
    """Refuse a cache folder that is (or holds, or sits inside) the library."""
    home, cache = config.home.resolve(), config.cache.resolve()
    if cache == home or home.is_relative_to(cache) or cache.is_relative_to(home):
        raise InvalidError(
            _(
                "the cache folder ({cache}) overlaps the library ({home})",
                cache=cache,
                home=home,
            ),
            hint=_("point DIDACT_CACHE somewhere of its own (or unset it)"),
        )


def size_text(size: int) -> str:
    """`12.3 MB`, `4.0 kB`, `512 B`."""
    amount = float(size)
    for unit in ("B", "kB", "MB", "GB"):
        if amount < 1000 or unit == "GB":
            return f"{amount:.0f} {unit}" if unit == "B" else f"{amount:.1f} {unit}"
        amount /= 1000
    return f"{size} B"
