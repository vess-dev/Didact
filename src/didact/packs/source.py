"""Reading pack files with positions, so every problem names its file and line."""

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from didact.core.errors import InvalidError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.store import frontmatter

type Loc = tuple[str | int, ...]
type Severity = Literal["error", "warning", "note"]  # a note: nothing wrong, worth knowing


@dataclass(frozen=True, slots=True)
class Problem:
    """One thing wrong with a pack, e.g. `tables/weather.yaml:12: entries must cover 1–6`."""

    file: str
    line: int | None
    message: str
    hint: str | None = None
    severity: Severity = "error"

    @property
    def where(self) -> str:
        return f"{self.file}:{self.line}" if self.line else self.file

    def text(self) -> str:
        if self.hint:
            return _(
                "{where}: {message} (fix: {hint})",
                where=self.where,
                message=self.message,
                hint=self.hint,
            )
        return f"{self.where}: {self.message}"

    def to_data(self) -> dict[str, JSON]:
        return {
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "hint": self.hint,
            "severity": self.severity,
        }


@dataclass(frozen=True, slots=True)
class Doc:
    """One YAML item from a pack file: plain data plus the node that knows its lines."""

    data: dict[str, JSON]
    node: Any
    file: str  # pack-relative, POSIX
    line: int  # 1-based line where the item starts

    def line_of(self, loc: Loc) -> int:
        """The line of the deepest key or index in `loc` that exists (else the item's line)."""
        node: Any = self.node  # ruamel nodes: `.lc` holds each key's and item's position
        line = self.line
        for part in loc:
            try:
                if isinstance(part, int) and isinstance(node, Sequence):
                    line = int(node.lc.item(part)[0]) + 1  # type: ignore[attr-defined]
                    node = node[part]
                elif isinstance(node, Mapping) and part in node:
                    line = int(node.lc.key(part)[0]) + 1  # type: ignore[attr-defined]
                    node = node[part]
                else:
                    break
            except AttributeError, IndexError, KeyError, TypeError:
                break
        return line

    def problem(self, loc: Loc, message: str, hint: str | None = None) -> Problem:
        return Problem(self.file, self.line_of(loc), message, hint)


def read_yaml_items(path: Path, rel: str) -> Iterator[Doc]:
    """Every item in a YAML file: one mapping, a list of mappings, or `---`-separated documents."""
    from ruamel.yaml import YAML
    from ruamel.yaml.error import YAMLError

    yaml = YAML()
    try:
        documents = list(yaml.load_all(path.read_text(encoding="utf-8")))
    except YAMLError as exc:
        raise PackFileError(_yaml_problem(rel, exc)) from exc
    for document in documents:
        if document is None:
            continue
        items = (
            document
            if isinstance(document, Sequence) and not isinstance(document, str)
            else [document]
        )
        for index, item in enumerate(items):
            if not isinstance(item, Mapping):
                line = _line(document, index) if items is document else 1
                raise PackFileError(
                    Problem(
                        rel,
                        line,
                        _("expected a mapping (`key: value` lines)"),
                        _("see the pack guide"),
                    )
                )
            data = frontmatter.to_plain(item, where=rel)
            assert isinstance(data, dict)
            yield Doc(data, item, rel, _start(item))


def read_markdown(path: Path, rel: str) -> tuple[dict[str, JSON], str]:
    """A Markdown file with optional front matter: (metadata, body)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    try:
        yaml_text, body = frontmatter.split(text, where=rel)
        meta = frontmatter.to_plain(frontmatter.load(yaml_text, where=rel), where=rel)
    except InvalidError as exc:
        raise PackFileError(Problem(rel, 1, exc.message, exc.hint)) from exc
    return (meta if isinstance(meta, dict) else {}), body


class PackFileError(Exception):
    def __init__(self, problem: Problem) -> None:
        super().__init__(problem.text())
        self.problem = problem


def _start(node: Any) -> int:
    try:
        return int(node.lc.line) + 1
    except AttributeError:
        return 1


def _line(seq: Any, index: int) -> int:
    try:
        return int(seq.lc.item(index)[0]) + 1
    except AttributeError, IndexError, KeyError:
        return 1


def _yaml_problem(rel: str, exc: Exception) -> Problem:
    """Point at where the broken construct starts (an unclosed `[` is reported at its `[`)."""
    context, problem = getattr(exc, "context", None), getattr(exc, "problem", None)
    start, found = getattr(exc, "context_mark", None), getattr(exc, "problem_mark", None)
    mark = start or found
    line = mark.line + 1 if mark is not None else None
    message = str(problem or exc).strip().splitlines()[0]
    if context and start is not None:
        text = _(
            "invalid YAML: {message} ({context} from line {line})",
            message=message,
            context=context,
            line=start.line + 1,
        )
    else:
        text = _("invalid YAML: {message}", message=message)
    return Problem(rel, line, text, _("fix the syntax"))
