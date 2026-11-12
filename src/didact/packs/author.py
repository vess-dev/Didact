"""Authoring packs: scaffold a new pack, add items from JSON, lint, and import Markdown tables."""

import re
from pathlib import Path

from didact.core.errors import ConflictError, InvalidError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.packs.kinds import DEFAULT_FOLDERS, KINDS, Kind, validator_for
from didact.packs.source import Doc, Problem
from didact.store import frontmatter
from didact.store.fsutil import atomic_write

PACK_KINDS = ("system", "oracle", "supplement", "setting", "adventure")

GUIDE_TEMPLATE = """# {name}

How to run this pack with Didact. Keep it short and practical: an LLM reads this first.

## What it is
One paragraph: the game, its tone, and what this pack covers.

## Core loop
- How a turn or scene goes, and the Didact commands it uses (`didact do …`, `didact table roll …`).

## Rules to remember
- The few rules that matter most, each pointing at its check or action (`didact rules show <id>`).

## Creating characters
- `didact template pc` then `didact new pc --data '{{…}}' --fill`.
"""

EXAMPLES: dict[str, str] = {
    "tables/example.yaml": """# A table: `didact table roll {id}.example`
table: example
title: Example table
dice: d6
entries:
  1-2: Something calm
  3-5: Something tense
  6: {{text: Something dangerous, then: [{{table: example}}]}}
source: "Your book, p. 1"
""",
    "rules/example.yaml": """# A check: `didact do {id}.example-save who=<pc> attr=STR`
check: example-save
title: Save
params: {{who: ref, attr: {{enum: [STR, DEX, WIL]}}}}
roll: d20
success: "@roll <= @who.$attr"
""",
    "schemas/character.yaml": """# Character fields in this system (see `didact guide packs`)
type: character
fields:
  STR: {{kind: stat, range: [0, 18], roll: 3d6}}
  hp: {{kind: resource, min: 0, roll: d6}}
---
type: pc
extends: character
---
type: npc
extends: character
""",
}


def scaffold(root: Path, pack_id: str, name: str, kind: str) -> list[str]:
    """Write a new pack's skeleton. Returns the files written (relative to `root`)."""
    if kind not in PACK_KINDS:
        raise InvalidError(
            _("unknown pack kind {kind}", kind=repr(kind)),
            hint=_("use one of: {kinds}", kinds=", ".join(PACK_KINDS)),
        )
    if (root / "pack.yaml").exists():
        raise ConflictError(
            _("{folder} already holds a pack", folder=root), hint=_("choose another id or folder")
        )
    manifest: dict[str, JSON] = {
        "id": pack_id,
        "name": name,
        "kind": kind,
        "version": "0.1.0",
        "description": "",
        "requires": {"didact": ">=0.1", "packs": ["core"]},
        "license": {"spdx": "", "redistributable": True, "attribution": ""},
    }
    files = {
        "pack.yaml": frontmatter.dump(frontmatter.from_plain(manifest)),
        "GUIDE.md": GUIDE_TEMPLATE.format(name=name),
    }
    for rel, text in EXAMPLES.items():
        files[rel] = text.format(id=pack_id)
    for folder in ("compendium", "reference", "tests"):
        files[f"{folder}/.keep"] = ""
    for rel, text in files.items():
        atomic_write(root / rel, text)
    return sorted(files)


def kind_named(name: str) -> Kind:
    for kind in KINDS:
        if kind.name == name:
            return kind
    known = ", ".join(k.name for k in KINDS)
    raise InvalidError(
        _("unknown content kind {kind}", kind=repr(name)),
        hint=_("use one of: {kinds}", kinds=known),
    )


def add_item(
    root: Path, kind_name: str, data: dict[str, JSON], *, replace: bool
) -> tuple[str, list[Problem]]:
    """Validate a JSON item and write it as YAML into the pack. Returns (file, warnings)."""
    kind = kind_named(kind_name)
    item_id = data.get(kind.key)
    if not isinstance(item_id, str):
        raise InvalidError(
            _("a {kind} needs `{key}`: its id", kind=kind.name, key=kind.key),
            hint=_('e.g. {{"{key}": "weather", …}}', key=kind.key),
        )
    folder = DEFAULT_FOLDERS[kind.folder]
    rel = f"{folder}/{item_id}.yaml"
    path = root / rel
    if path.exists() and not replace:
        raise ConflictError(
            _("{file} already exists", file=rel), hint=_("pass --replace to overwrite it")
        )
    ordered = {kind.key: item_id, **{k: v for k, v in data.items() if k != kind.key}}
    text = frontmatter.dump(frontmatter.from_plain(ordered))
    node = frontmatter.load(text, where=rel)
    doc = Doc(ordered, node, rel, 1)
    validate = validator_for(kind.name)
    problems = validate(doc) if validate else []
    errors = [p for p in problems if p.severity == "error"]
    if errors:
        raise InvalidError(
            f"{kind.name} {item_id}: " + "; ".join(p.message for p in errors),
            hint=errors[0].hint or _("fix the JSON and try again"),
        )
    atomic_write(path, text)
    return rel, problems


def lint(bundle: dict[str, JSON]) -> list[str]:
    """Style warnings a valid pack can still have: missing titles, help, sources, guide."""
    warnings: list[str] = []
    items = bundle.get("items")
    for kind, entries in items.items() if isinstance(items, dict) else []:
        for item_id, entry in entries.items() if isinstance(entries, dict) else []:
            if not isinstance(entry, dict):
                continue
            data, source = entry.get("data"), entry.get("source")
            if not isinstance(data, dict):
                continue
            where = {"source": source, "kind": kind, "id": item_id}
            if kind in ("check", "action", "procedure") and not data.get("help"):
                warnings.append(
                    _("{source}: {kind} {id} has no `help` (one line on what it's for)", **where)
                )
            if kind in ("table", "check", "action", "procedure", "entry") and not data.get(
                "source"
            ):
                warnings.append(
                    _(
                        "{source}: {kind} {id} has no `source` (a book page makes it checkable)",
                        **where,
                    )
                )
            if kind == "table" and not data.get("title"):
                warnings.append(_("{source}: {kind} {id} has no `title`", **where))
    guide = bundle.get("guide")
    if not isinstance(guide, str) or len(guide.strip()) < 80:
        warnings.append(_("GUIDE.md is missing or very short: say how to run the pack"))
    return warnings


# ---------------------------------------------------------------------------- Markdown tables

_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
_RULE = re.compile(r"^\s*\|?\s*:?-{2,}")


def md_table(
    text: str, table_id: str, dice: str | None, *, columns: bool = False
) -> dict[str, JSON]:
    """A Markdown pipe table → a Didact table: the first column holds the rolls.

    With several result columns, each row becomes `{text: first, <header>: …}`; with
    `columns`, each column is rolled separately instead (books that say "roll each column").
    """
    rows = [
        [cell.strip() for cell in match.group(1).split("|")]
        for line in text.splitlines()
        if (match := _ROW.match(line)) and not _RULE.match(line)
    ]
    if len(rows) < 2:
        raise InvalidError(
            _("no Markdown table found"), hint=_("give a pipe table: | d6 | Result |")
        )
    header, body = rows[0], rows[1:]
    guessed = dice or (header[0] if re.fullmatch(r"\d*d\d+|d%|d66", header[0].strip()) else None)
    names = [
        re.sub(r"[^a-z0-9]+", "_", h.lower()).strip("_") or f"col{i}" for i, h in enumerate(header)
    ]
    entries: dict[str, JSON] = {}
    for cells in body:
        key = cells[0].replace("–", "-").replace("—", "-")
        values = cells[1:]
        if len(values) == 1:
            entries[key] = values[0]
        elif columns:
            entries[key] = list[JSON](values)
        else:
            entry: dict[str, JSON] = {"text": values[0]}
            entry["data"] = {
                names[i + 2]: v for i, v in enumerate(values[1:]) if i + 2 < len(names)
            }
            entries[key] = entry
    table: dict[str, JSON] = {"table": table_id}
    if guessed:
        table["dice"] = guessed
    if columns and len(header) > 2:
        table["columns"] = list[JSON](names[1:])
    table["entries"] = entries
    return table
