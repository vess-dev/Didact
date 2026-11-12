"""From a rulebook to a pack: extract page-marked text, spot candidate tables, measure coverage."""

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from didact.core.errors import InvalidError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.store.fsutil import atomic_write

_ROW = re.compile(r"^\s*(\d{1,3}(?:\s*[-–]\s*\d{1,3})?)[.:)]?\s+(\S.*)$")
_RANGE = r"\d+(?:\s*[-–]\s*\d+)?"
_PAGE = re.compile(  # "p. 12", "pp. 10-17", "p. 14, 15, 17"
    rf"\bp(?:p|age|ages)?\.?\s*({_RANGE}(?:\s*,\s*{_RANGE})*)", re.IGNORECASE
)
MIN_ROWS = 3


@dataclass(frozen=True, slots=True)
class Candidate:
    page: int
    first: int  # line number on the page
    rows: list[tuple[str, str]]

    def yaml(self, table_id: str) -> str:
        entries = "\n".join(f"  {key.replace(' ', '')}: {_quote(text)}" for key, text in self.rows)
        head = f"# draft from page {self.page}: check it, then `didact pack add`\n"
        return f'{head}table: {table_id}\nsource: "p. {self.page}"\nentries:\n{entries}\n'


def _quote(text: str) -> str:
    return '"' + text.replace('"', "'") + '"'


def pages(source: Path) -> list[str]:
    """The source's text, one string per page (PDF via pdftotext; text files are one page)."""
    if source.suffix.lower() == ".pdf":
        tool = shutil.which("pdftotext")
        if tool is None:
            raise InvalidError(
                _("pdftotext isn't installed"), hint=_("brew install poppler (or give Markdown)")
            )
        done = subprocess.run(
            [tool, "-layout", str(source), "-"], capture_output=True, text=True, check=False
        )
        if done.returncode != 0:
            raise InvalidError(
                _("pdftotext failed: {error}", error=done.stderr.strip()[:200]),
                hint=_("check the PDF opens; or save its text as a .txt file and ingest that"),
            )
        return done.stdout.split("\f")
    return [source.read_text(encoding="utf-8")]


def candidates(text_pages: list[str]) -> list[Candidate]:
    """Runs of 3+ lines that start with rising roll numbers: likely random tables."""
    found: list[Candidate] = []
    for number, page in enumerate(text_pages, 1):
        found.extend(_page_candidates(number, page))
    return found


def _page_candidates(number: int, page: str) -> list[Candidate]:
    found: list[Candidate] = []
    run: list[tuple[str, str]] = []
    start = last = blanks = 0
    for index, line in enumerate([*page.splitlines(), ""]):
        match = _ROW.match(line)
        if match is None:
            blanks = blanks + 1 if not line.strip() else 99
            if blanks > 1:  # one blank line may sit inside a table; more ends it
                if len(run) >= MIN_ROWS:
                    found.append(Candidate(number, start + 1, run))
                run, last = [], 0
            continue
        blanks = 0
        low, high = _bounds(match.group(1))
        if run and low <= last:  # numbering restarted: a new table
            if len(run) >= MIN_ROWS:
                found.append(Candidate(number, start + 1, run))
            run = []
        if not run:
            start = index
        run.append((match.group(1), match.group(2).strip()))
        last = high
    if len(run) >= MIN_ROWS:
        found.append(Candidate(number, start + 1, run))
    return found


def _bounds(key: str) -> tuple[int, int]:
    numbers = [int(n) for n in re.split(r"\s*[-–]\s*", key.strip())]
    return numbers[0], numbers[-1]


def ingest(source: Path, workspace: Path) -> tuple[int, list[Candidate]]:
    """Write `text.md` (page-marked) and `candidates/*.yaml` into the workspace."""
    text_pages = pages(source)
    marked = "\n\n".join(
        f"<!-- page {i} -->\n{page.rstrip()}" for i, page in enumerate(text_pages, 1)
    )
    atomic_write(workspace / "text.md", marked + "\n")
    found = candidates(text_pages)
    for index, candidate in enumerate(found, 1):
        name = f"p{candidate.page:03d}-{index}"
        atomic_write(workspace / "candidates" / f"{name}.yaml", candidate.yaml(f"table-{name}"))
    return len(text_pages), found


def cited_pages(bundle: dict[str, JSON]) -> set[int]:
    """Every page the pack cites: `source:` on items, `page:` on reference sections."""
    found: set[int] = set()

    def add(text: str) -> None:
        for match in _PAGE.finditer(text):
            for part in match.group(1).split(","):
                first, _sep, last = part.replace("–", "-").partition("-")
                low = int(first)
                high = int(last) if last.strip() else low
                found.update(range(low, min(high, low + 50) + 1))

    items = bundle.get("items")
    for entries in items.values() if isinstance(items, dict) else []:
        for entry in entries.values() if isinstance(entries, dict) else []:
            data = entry.get("data") if isinstance(entry, dict) else None
            if isinstance(data, dict):
                for key in ("source", "page"):
                    value = data.get(key)
                    if isinstance(value, str):
                        add(value)
                    elif isinstance(value, int):
                        found.add(value)
    reference = bundle.get("reference")
    for section in reference.values() if isinstance(reference, dict) else []:
        meta = section.get("meta") if isinstance(section, dict) else None
        page = meta.get("page") if isinstance(meta, dict) else None
        if isinstance(page, int):
            found.add(page)
        elif isinstance(page, str):
            add(f"p. {page}")
    return found


def cited_sections(bundle: dict[str, JSON]) -> set[str]:
    """Every section of an unpaginated book the pack cites: `source: players-guide/saves#…`."""
    found: set[str] = set()

    def add(text: str) -> None:
        for part in re.split(r"[;,]", text):
            section = part.strip().partition("#")[0].strip().removesuffix(".md")
            if section and "/" in section:
                found.add(section)

    items = bundle.get("items")
    for entries in items.values() if isinstance(items, dict) else []:
        for entry in entries.values() if isinstance(entries, dict) else []:
            data = entry.get("data") if isinstance(entry, dict) else None
            if isinstance(data, dict) and isinstance(data.get("source"), str):
                add(str(data["source"]))
    reference = bundle.get("reference")
    for section in reference.values() if isinstance(reference, dict) else []:
        meta = section.get("meta") if isinstance(section, dict) else None
        for key in ("source", "page"):
            value = meta.get(key) if isinstance(meta, dict) else None
            if isinstance(value, str):
                add(value)
    return found


def ranges(numbers: list[int]) -> str:
    """`1, 2, 3, 7, 9, 10` → `1–3, 7, 9–10`."""
    if not numbers:
        return _("none")
    parts: list[str] = []
    start = prev = numbers[0]
    for n in [*numbers[1:], 0]:
        if n == prev + 1:
            prev = n
            continue
        parts.append(f"{start}–{prev}" if prev != start else str(start))
        start = prev = n
    return ", ".join(parts)
