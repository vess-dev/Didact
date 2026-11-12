"""Translation upkeep (a developer tool, not part of Didact): `make i18n` runs `update`.

- `update`: extract the marked messages (`_`, `N_`, `ngettext`, `pgettext`, and the plural
  phrases of `core/phrases.counted`) from the browser app, and
  every command's help (summary, description, arguments) from the registry, into
  `didact.pot`, merge them into every language's `didact.po`, and compile each `didact.mo`.
- `check`: what `test_i18n.py` asserts: the catalogs match the code, every `.mo` matches its
  `.po`, and no translation drops or invents a `{placeholder}`.
- `status`: how much of each language is translated, and which guide translations are
  missing or older than the English.

Messages are found by reading the code's syntax tree, so `_()` inside t-strings counts too.
"""

import ast
import io
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from babel.messages.catalog import Catalog
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po, write_po

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "didact"
SOURCES = (PACKAGE,)  # every `_()`: the browser app, the command line's help, the site export
LOCALE = PACKAGE / "locale"
TEMPLATE = LOCALE / "didact.pot"
GUIDES = PACKAGE / "guides"
STAMP = datetime(2026, 1, 1, tzinfo=UTC)  # fixed dates: the files only change with the messages
PLACEHOLDER = re.compile(r"\{(\w*)[^{}]*\}")
PERCENT = re.compile(r"%(?:\(\w+\))?[sdr]")  # argparse's own messages fill these in
PLURALS = ("ngettext", "counted", "N_plural")  # (singular, plural, …): one plural message

sys.path.insert(0, str(ROOT / "src"))
from didact import guides  # noqa: E402
from didact.commands.registry import CommandSpec  # noqa: E402
from didact.core.i18n import DEFAULT, LANGUAGES  # noqa: E402

CODES = [code for code in LANGUAGES if code != DEFAULT]


# ---------------------------------------------------------------------------- extracting


def extract() -> Catalog:
    template = Catalog(
        domain="didact", project="Didact", creation_date=STAMP, revision_date=STAMP, fuzzy=False
    )
    for folder in SOURCES:
        for path in sorted(folder.rglob("*.py")):
            rel = path.relative_to(ROOT / "src").as_posix()
            for call in _calls(ast.parse(path.read_text(encoding="utf-8"))):
                name, args = call
                if name in ("_", "N_") and len(args) >= 1:
                    template.add(args[0], locations=[(rel, 0)])
                elif name in PLURALS and len(args) >= 2:
                    template.add((args[0], args[1]), locations=[(rel, 0)])
                elif name == "pgettext" and len(args) >= 2:
                    template.add(args[1], context=args[0], locations=[(rel, 0)])
    for spec in _commands():  # command help: English on the command line, translated in the app
        rel = f"didact/commands/{spec.func.__module__.rpartition('.')[2]}.py"
        note = [f"command help: didact {spec.name}"]
        for text in (spec.summary, spec.description, *(p.help for p in spec.params)):
            if text and text.strip():
                template.add(text, locations=[(rel, 0)], auto_comments=note)
    return template


def _commands() -> list[CommandSpec]:
    from didact.commands import load_all
    from didact.commands.registry import REGISTRY

    load_all()
    return sorted(REGISTRY.values(), key=lambda spec: spec.name)


def _calls(tree: ast.AST) -> list[tuple[str, list[str]]]:
    found: list[tuple[str, list[str]]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id not in ("_", "N_", "pgettext", *PLURALS):
            continue
        texts = [
            a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)
        ]
        if len(texts) == len(node.args) or node.func.id in PLURALS:
            found.append((node.func.id, texts))
    return found


# ---------------------------------------------------------------------------- the catalogs


def po_path(code: str) -> Path:
    return LOCALE / code / "LC_MESSAGES" / "didact.po"


def _dump_po(catalog: Catalog) -> bytes:
    out = io.BytesIO()
    write_po(out, catalog, width=100, sort_output=True, include_previous=False)
    return out.getvalue()


def _dump_mo(catalog: Catalog) -> bytes:
    out = io.BytesIO()
    write_mo(out, catalog, use_fuzzy=False)
    return out.getvalue()


def _read(path: Path, code: str) -> Catalog:
    with path.open("rb") as handle:
        return read_po(handle, locale=code, domain="didact")


def merged(code: str, template: Catalog) -> Catalog:
    path = po_path(code)
    if path.is_file():
        catalog = _read(path, code)
    else:
        catalog = Catalog(locale=code, domain="didact", project="Didact", fuzzy=False)
    catalog.creation_date = STAMP
    catalog.revision_date = STAMP
    catalog.update(template, no_fuzzy_matching=True, update_creation_date=False)
    catalog.obsolete.clear()
    return catalog


def update() -> None:
    template = extract()
    TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATE.write_bytes(_dump_po(template))
    for code in CODES:
        catalog = merged(code, template)
        path = po_path(code)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_dump_po(catalog))
        path.with_suffix(".mo").write_bytes(_dump_mo(_read(path, code)))  # as saved


def check() -> list[str]:
    """Problems that `make i18n` (or a translator) must fix."""
    problems: list[str] = []
    template = extract()
    if not TEMPLATE.is_file() or TEMPLATE.read_bytes() != _dump_po(template):
        problems.append("didact.pot doesn't match the code: run `make i18n`")
    for code in CODES:
        path = po_path(code)
        if not path.is_file():
            problems.append(f"{code}: no didact.po: run `make i18n`")
            continue
        catalog = _read(path, code)
        if path.read_bytes() != _dump_po(merged(code, template)):
            problems.append(f"{code}: didact.po doesn't match the code: run `make i18n`")
        mo = path.with_suffix(".mo")
        if not mo.is_file() or mo.read_bytes() != _dump_mo(catalog):
            problems.append(f"{code}: didact.mo is out of date: run `make i18n`")
        for message in catalog:
            if not message.id or not message.string:
                continue
            ids = [str(i) for i in (message.id if isinstance(message.id, tuple) else (message.id,))]
            strings = [
                str(t)
                for t in (
                    message.string if isinstance(message.string, tuple) else (message.string,)
                )
            ]
            wanted = {n for i in ids for n in PLACEHOLDER.findall(i)}
            for text in strings:
                if text and set(PLACEHOLDER.findall(text)) - wanted - {"n"}:
                    problems.append(f"{code}: {ids[0]!r} has a placeholder the English hasn't")
                if text and wanted - {"n"} - set(PLACEHOLDER.findall(text)):
                    problems.append(f"{code}: {ids[0]!r} drops a placeholder")
                if text and sorted(PERCENT.findall(ids[0])) != sorted(PERCENT.findall(text)):
                    problems.append(f"{code}: {ids[0]!r} changes a %-placeholder")
    return problems


# ---------------------------------------------------------------------------- the guides


def guide_state(code: str, topic: str) -> str:
    """`current`, `stale` (translated from an older English) or `missing`."""
    if not (GUIDES / code / f"{topic}.md").is_file():
        return "missing"
    return "current" if guides.translated(topic, code).current else "stale"


def status() -> str:
    template = extract()
    total = len([m for m in template if m.id])
    topics = sorted(p.stem for p in GUIDES.glob("*.md"))
    lines = [f"{total} messages, {len(topics)} guides"]
    for code in CODES:
        path = po_path(code)
        done = 0
        if path.is_file():
            done = sum(
                1
                for m in _read(path, code)
                if m.id
                and m.string
                and all(m.string if isinstance(m.string, tuple) else (m.string,))
            )
        guides = {t: guide_state(code, t) for t in topics}
        behind = [f"{t} ({s})" for t, s in guides.items() if s != "current"]
        lines.append(
            f"- {code}: {done}/{total} messages"
            + (f"; guides to do: {', '.join(behind)}" if behind else "; guides current")
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------- translating


def _key(message: object) -> str:
    """How a message is named in todo/fill files: its id, `context|id` with a context."""
    ids = message.id  # type: ignore[attr-defined]
    first = ids[0] if isinstance(ids, tuple) else ids
    context = message.context  # type: ignore[attr-defined]
    return f"{context}|{first}" if context else str(first)


def todo(code: str) -> list[dict[str, object]]:
    """The untranslated messages of a language, for a translator (JSON-ready)."""
    catalog = _read(po_path(code), code)
    found: list[dict[str, object]] = []
    for message in catalog:
        if not message.id:
            continue
        strings = message.string if isinstance(message.string, tuple) else (message.string,)
        if all(strings):
            continue
        entry: dict[str, object] = {"key": _key(message)}
        if isinstance(message.id, tuple):
            entry["plural"] = message.id[1]
            entry["forms"] = catalog.num_plurals
        found.append(entry)
    return found


def fill(code: str, translations: dict[str, object]) -> list[str]:
    """Put translations (key → text, or a list of plural forms) into a language's catalog."""
    path = po_path(code)
    catalog = _read(path, code)
    by_key = {_key(m): m for m in catalog if m.id}
    unknown: list[str] = []
    for key, text in translations.items():
        message = by_key.get(key)
        if message is None:
            unknown.append(key)
            continue
        if isinstance(message.id, tuple):
            forms = [str(t) for t in text] if isinstance(text, list) else [str(text)]
            forms += [forms[-1]] * (catalog.num_plurals - len(forms))
            message.string = tuple(forms[: catalog.num_plurals])
        else:
            message.string = str(text)
    path.write_bytes(_dump_po(catalog))
    return unknown


def lint(code: str) -> list[str]:
    """One language's placeholder problems and what's left to translate."""
    problems = [p for p in check() if p.startswith(f"{code}: ") and "out of date" not in p]
    problems = [p for p in problems if "doesn't match the code" not in p]
    left = todo(code)
    if left:
        problems.append(f"{code}: {len(left)} messages still to translate")
    return problems


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "update"
    if action == "update":
        update()
        print(status())
    elif action == "check":
        found = check()
        print("\n".join(found) or "ok")
        sys.exit(1 if found else 0)
    elif action == "status":
        print(status())
    elif action == "todo":  # tools/i18n.py todo fr > todo.json
        import json

        print(json.dumps(todo(sys.argv[2]), ensure_ascii=False, indent=1))
    elif action == "fill":  # tools/i18n.py fill fr done.json
        import json

        data = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
        missed = fill(sys.argv[2], data)
        print("\n".join(f"unknown key: {k}" for k in missed) or "filled")
    elif action == "pairs":  # tools/i18n.py pairs fr: each message and its translation
        catalog = _read(po_path(sys.argv[2]), sys.argv[2])
        for message in catalog:
            if message.id:
                forms = message.string if isinstance(message.string, tuple) else (message.string,)
                print(f"{_key(message)}\n  → {' | '.join(str(f) for f in forms)}")
    elif action == "lint":  # tools/i18n.py lint fr
        found = lint(sys.argv[2])
        print("\n".join(found) or "ok")
        sys.exit(1 if found else 0)
    else:
        sys.exit("usage: tools/i18n.py update | check | status | todo|fill|lint <code> …")
