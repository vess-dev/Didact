"""The static files shipped in `didact/web/static`: loaded once, served by exact name only.

Only files found in that folder at start-up can be served, so there is no path to traverse.
Their URLs carry a content hash (`?v=…`), so browsers may cache them for a long time.
"""

import hashlib
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from importlib.resources.abc import Traversable

TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
}


@dataclass(frozen=True, slots=True)
class Asset:
    body: bytes
    content_type: str


@cache
def assets() -> dict[str, Asset]:
    """Every servable file, by its path under `static/` (e.g. `fonts/ubuntu-….woff2`)."""
    found: dict[str, Asset] = {}

    def walk(folder: Traversable, prefix: str) -> None:
        for entry in folder.iterdir():
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                walk(entry, f"{prefix}{entry.name}/")
                continue
            suffix = entry.name[entry.name.rfind(".") :] if "." in entry.name else ""
            if suffix in TYPES:
                found[prefix + entry.name] = Asset(entry.read_bytes(), TYPES[suffix])

    walk(files("didact.web") / "static", "")
    return found


@cache
def version() -> str:
    """A short hash of every static file: it changes whenever one of them does."""
    digest = hashlib.sha256()
    for name, asset in sorted(assets().items()):
        digest.update(name.encode())
        digest.update(asset.body)
    return digest.hexdigest()[:10]


def asset_url(name: str) -> str:
    return f"/static/{name}?v={version()}"
