"""Markdown documents with YAML front matter, round-tripped so hand edits and comments survive.

Documents look like:

    ---
    id: npc:sweeney
    name: Sweeney
    ---

    Free prose (the body).

YAML is YAML 1.2 via ruamel.yaml (imported lazily): `no`/`on` stay strings.
"""

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from io import StringIO
from typing import Any

from didact.core.errors import InvalidError
from didact.core.i18n import _
from didact.core.output import JSON

_FENCES = ("---", "...")
# Plain words that YAML 1.1 readers (e.g. some editors) would turn into booleans or null.
_YAML11_SPECIAL = frozenset({"y", "n", "yes", "no", "on", "off", "true", "false", "null", "~", ""})


def split(text: str, *, where: str) -> tuple[str, str]:
    """Split a document into (front matter YAML, body)."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise InvalidError(
            _("missing front matter"),
            where=where,
            hint=_("the file must start with a `---` line"),
        )
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") in _FENCES:
            return "".join(lines[1:i]), "".join(lines[i + 1 :]).lstrip("\r\n")
    raise InvalidError(
        _("front matter is not closed"), where=where, hint=_("add a `---` line after the YAML")
    )


def join(yaml_text: str, body: str) -> str:
    """Assemble a document; the body is separated by one blank line and ends with a newline."""
    head = f"---\n{yaml_text}---\n"
    text = body.strip("\n")
    return f"{head}\n{text}\n" if text else head


def _yaml() -> Any:
    from ruamel.yaml import YAML

    yaml = YAML()  # round-trip mode keeps comments, key order and quoting
    yaml.preserve_quotes = True
    yaml.width = 4096
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml


def load(yaml_text: str, *, where: str) -> Any:
    """Parse YAML into ruamel's round-trip nodes (CommentedMap for a mapping)."""
    from ruamel.yaml.error import YAMLError

    try:
        node = _yaml().load(yaml_text) if yaml_text.strip() else None
    except YAMLError as exc:
        raise InvalidError(
            _("invalid YAML: {error}", error=exc), where=where, hint=_("fix the YAML syntax")
        ) from exc
    if node is None:
        from ruamel.yaml.comments import CommentedMap

        return CommentedMap()
    if not isinstance(node, Mapping):
        raise InvalidError(
            _("front matter must be a mapping"), where=where, hint=_("use `key: value` lines")
        )
    return node


def dump(node: Any) -> str:
    buffer = StringIO()
    _yaml().dump(node, buffer)
    return buffer.getvalue()


def to_plain(node: Any, *, where: str = "") -> JSON:
    """Convert round-trip nodes to plain JSON-safe data."""
    if node is None or isinstance(node, bool):
        return node
    if isinstance(node, int):
        return int(node)
    if isinstance(node, float):
        return float(node)
    if isinstance(node, str):
        return str(node)
    if isinstance(node, datetime):
        text = node.isoformat()
        return text.replace("+00:00", "Z")
    if isinstance(node, date):
        return node.isoformat()
    if isinstance(node, Mapping):
        return {str(k): to_plain(v, where=where) for k, v in node.items()}
    if isinstance(node, Sequence):
        return [to_plain(v, where=where) for v in node]
    raise InvalidError(
        _("unsupported YAML value {value}", value=repr(node)),
        where=where,
        hint=_("use plain scalars, lists and maps"),
    )


def from_plain(data: JSON) -> Any:
    """Build round-trip nodes from plain data: short scalar lists and small flat maps go inline."""
    from ruamel.yaml.comments import CommentedMap, CommentedSeq
    from ruamel.yaml.scalarstring import LiteralScalarString, SingleQuotedScalarString

    if isinstance(data, str):
        if "\n" in data:
            return LiteralScalarString(data)
        if data.lower() in _YAML11_SPECIAL:
            return SingleQuotedScalarString(data)  # stays a string in YAML 1.1 tools too
        return data
    if isinstance(data, dict):
        mapping = CommentedMap()
        for key, value in data.items():
            mapping[key] = from_plain(value)
        return mapping
    if isinstance(data, list):
        seq = CommentedSeq(from_plain(v) for v in data)
        if all(_is_inline_scalar(v) for v in data):
            seq.fa.set_flow_style()  # tags: [wood, champion]
        elif all(_is_flat_map(v) for v in data):
            for item in seq:
                item.fa.set_flow_style()  # - {rel: lives-at, to: loc:cabin}
        return seq
    return data


def _is_inline_scalar(value: JSON) -> bool:
    return (
        value is None
        or isinstance(value, bool | int | float)
        or (isinstance(value, str) and "\n" not in value and len(value) <= 60)
    )


def _is_flat_map(value: JSON) -> bool:
    return (
        isinstance(value, dict)
        and len(value) <= 4
        and all(_is_inline_scalar(v) for v in value.values())
    )


def sync(node: Any, data: Mapping[str, JSON], order: Sequence[str] = ()) -> None:
    """Update a round-trip mapping in place to equal `data`, keeping comments on unchanged parts.

    New keys are inserted at their canonical position (per `order`) when possible.
    """
    for key in [k for k in node if k not in data]:
        del node[key]
    for key, value in data.items():
        if key in node:
            current = node[key]
            if isinstance(value, dict) and isinstance(current, Mapping):
                sync(current, value)
            elif to_plain(current) != value:
                node[key] = from_plain(value)
            continue
        node.insert(_insert_position(node, key, order), key, from_plain(value))


def _insert_position(node: Any, key: str, order: Sequence[str]) -> int:
    if key not in order:
        return len(node)
    rank = order.index(key)
    position = 0
    for i, existing in enumerate(node):
        if existing in order and order.index(existing) < rank:
            position = i + 1
    return position


def render(
    data: Mapping[str, JSON], body: str, *, previous: str | None = None, order: Sequence[str] = ()
) -> str:
    """Render a document. With `previous` text, keep its comments and layout where unchanged."""
    if previous is not None:
        try:
            yaml_text, _body = split(previous, where="(previous)")
            node = load(yaml_text, where="(previous)")
        except InvalidError:
            node = None
        if node is not None:
            sync(node, data, order)
            return join(dump(node), body)
    return join(dump(from_plain(dict(data))), body)
