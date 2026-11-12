"""The code's API documentation, like `cargo doc`: pdoc renders every module's docstrings and
types into HTML in the cache folder (`docs/`). A fingerprint of the code says when it's out of
date; `didact docs build` (or opening the docs in the browser app) rebuilds it then.
"""

import hashlib
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from didact.core.config import Config

STAMP = ".fingerprint"
type State = Literal["current", "stale", "missing"]


def folder(config: Config) -> Path:
    return config.cache / "docs"


def package_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def fingerprint() -> str:
    """Every module's path, size and time: any change to the code changes it."""
    digest = hashlib.sha256()
    root = package_dir()
    for path in sorted(root.rglob("*.py")):
        info = path.stat()
        digest.update(f"{path.relative_to(root)}:{info.st_size}:{info.st_mtime_ns}\n".encode())
    return digest.hexdigest()[:16]


def state(config: Config) -> State:
    stamp = folder(config) / STAMP
    if not (folder(config) / "index.html").is_file() or not stamp.is_file():
        return "missing"
    return "current" if stamp.read_text(encoding="utf-8").strip() == fingerprint() else "stale"


@dataclass(frozen=True, slots=True)
class Built:
    path: Path
    pages: int
    seconds: float
    rebuilt: bool


def build(config: Config, *, force: bool = False) -> Built:
    """Render the docs unless they're current (or `force`). Written beside, then swapped in."""
    target = folder(config)
    if not force and state(config) == "current":
        return Built(target, _pages(target), 0.0, rebuilt=False)
    import pdoc
    import pdoc.render

    started = time.monotonic()
    stamp = fingerprint()
    fresh = target.with_name(f"docs-{stamp}-{time.time_ns()}")
    pdoc.render.configure(docformat="markdown", footer_text="Didact")
    pdoc.pdoc("didact", output_directory=fresh)
    (fresh / STAMP).write_text(stamp + "\n", encoding="utf-8")
    old = target.with_name(f"{target.name}-old-{time.time_ns()}")
    if target.exists():
        target.rename(old)
    fresh.rename(target)
    shutil.rmtree(old, ignore_errors=True)
    return Built(target, _pages(target), time.monotonic() - started, rebuilt=True)


def _pages(target: Path) -> int:
    return sum(1 for _ in target.rglob("*.html")) if target.is_dir() else 0
