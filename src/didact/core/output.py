"""Command results, plus small helpers for writing Markdown that LLMs read well."""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from string.templatelib import Interpolation, Template
from typing import Literal

from didact.core.i18n import ngettext

type JSON = bool | int | float | str | list[JSON] | dict[str, JSON] | None
type Format = Literal["md", "yaml", "json"]
type Detail = Literal["brief", "full"]


@dataclass(frozen=True, slots=True)
class Out:
    """What every command returns: structured data for machines, Markdown for LLM eyes."""

    data: dict[str, JSON]
    md: str
    md_full: str | None = None
    ok: bool = True  # False → exit code 1, e.g. `doctor` found a blocking problem.
    whole: bool = False  # documentation asked for by name: never cut (see `budget`)

    def markdown(self, detail: Detail) -> str:
        if detail == "full":
            return self.md_full if self.md_full is not None else self.md
        return self.md if self.whole else budget(self.md)


BUDGET = 12_000  # characters of brief Markdown: an LLM's context is precious


def budget(text: str, limit: int = BUDGET) -> str:
    """Cut long brief output at a line, and say how to see the rest."""
    if len(text) <= limit:
        return text
    kept = text[:limit].rpartition("\n")[0] or text[:limit]
    rest = text[len(kept) :].count("\n")
    more = ngettext(
        "… {n} more lines (`--detail full` shows everything, `--format json` too)",
        "… {n} more lines (`--detail full` shows everything, `--format json` too)",
        rest,
    )
    return f"{kept}\n{more}"


def flatten(data: Mapping[str, JSON], prefix: str = "") -> list[tuple[str, JSON]]:
    """Nested mappings as dotted keys: {"a": {"b": 1}} → [("a.b", 1)]."""
    items: list[tuple[str, JSON]] = []
    for key, value in data.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict) and value:
            items.extend(flatten(value, f"{name}."))
        else:
            items.append((name, value))
    return items


def plain(value: JSON) -> str:
    """A value in words, to read or search: a list by its parts, a mapping by its values
    (`[{"name": "dagger", "damage": "d6"}]` → `dagger d6`)."""
    if isinstance(value, list):
        return ", ".join(plain(v) for v in value)
    if isinstance(value, dict):
        return " ".join(plain(v) for v in value.values())
    if isinstance(value, bool) or value is None:
        return {True: "true", False: "false", None: "null"}[value]
    return str(value)


def escape_cell(value: object) -> str:
    """Make a value safe inside a Markdown table cell."""
    return str(value).replace("|", "\\|").replace("\n", " ")


def code(value: object) -> str:
    """Wrap a value as inline code, choosing a fence that its own backticks can't break."""
    text = str(value)
    fence = "``" if "`" in text else "`"
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{pad}{text}{pad}{fence}"


def md(template: Template) -> str:
    """Render a t-string as Markdown. Format specs: `code` (inline code), `cell` (table-safe).

    Example: md(t"unknown command {name:code}")  →  "unknown command `rol`"
    """
    parts: list[str] = []
    for part in template:
        if isinstance(part, str):
            parts.append(part)
            continue
        parts.append(_render_interpolation(part))
    return "".join(parts)


def _render_interpolation(part: Interpolation[object]) -> str:
    value = part.value
    match part.conversion:
        case "r":
            value = repr(value)
        case "s":
            value = str(value)
        case "a":
            value = ascii(value)
        case None:
            pass
    match part.format_spec:
        case "code":
            return code(value)
        case "cell":
            return escape_cell(value)
        case "":
            return str(value)
        case spec:
            return format(value, spec)


def table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    """A GitHub-flavoured Markdown table with escaped cells."""
    lines = [
        "| " + " | ".join(escape_cell(h) for h in headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    lines.extend("| " + " | ".join(escape_cell(c) for c in row) + " |" for row in rows)
    return "\n".join(lines)


def plural(count: int, noun: str, plural_form: str | None = None) -> str:
    """`1 record`, `3 records`."""
    return f"{count} {noun if count == 1 else plural_form or noun + 's'}"


def bullets(items: Iterable[object]) -> str:
    return "\n".join(f"- {item}" for item in items)


def kv(pairs: Iterable[tuple[str, object]]) -> str:
    """`key: value` lines, the most LLM-legible way to show a record."""
    return "\n".join(f"{key}: {value}" for key, value in pairs)
