"""Guides: how-to docs for LLMs and people, shipped with Didact (`didact guide <topic>`).

The English guides are the source. A translation lives in `<code>/<topic>.md` (a language code
from `didact.core.i18n`) and starts with `<!-- translated from <hash> -->`: the first 12 hex
digits of the English file's SHA-256 when it was translated, so an older one can say so.
"""

import hashlib
import re
from dataclasses import dataclass
from importlib.resources import files

MARK = re.compile(r"^<!-- translated from ([0-9a-f]{12}) -->\n")


def topics() -> dict[str, str]:
    """topic → one-line summary (the first paragraph line after the title)."""
    found: dict[str, str] = {}
    for entry in sorted(files(__name__).iterdir(), key=lambda e: e.name):
        if entry.name.endswith(".md"):
            found[entry.name.removesuffix(".md")] = _summary(entry.read_text(encoding="utf-8"))
    return found


def _summary(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    return next((line for line in lines[1:] if line and not line.startswith("#")), "")


def read(topic: str) -> str:
    return (files(__name__) / f"{topic}.md").read_text(encoding="utf-8")


def source_hash(topic: str) -> str:
    """What a translation records of the English it came from."""
    raw = (files(__name__) / f"{topic}.md").read_bytes()
    return hashlib.sha256(raw).hexdigest()[:12]


@dataclass(frozen=True, slots=True)
class Translated:
    text: str
    language: str  # the language shown: the one asked for, or "en"
    current: bool  # False: translated from an older English (or not translated: English)


def translated(topic: str, code: str) -> Translated:
    """The guide in language `code` when there's a translation, else in English."""
    entry = files(__name__) / code / f"{topic}.md"
    if code == "en" or not entry.is_file():
        return Translated(read(topic), "en", code == "en")
    text = entry.read_text(encoding="utf-8")
    mark = MARK.match(text)
    body = text[mark.end() :] if mark else text
    current = mark is not None and mark.group(1) == source_hash(topic)
    return Translated(body, code, current)


def summary(topic: str, code: str) -> str:
    return _summary(translated(topic, code).text)
