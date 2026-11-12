"""Compile a pack folder into one validated bundle (plain JSON), or explain what's wrong.

The bundle is what Didact loads at run time (cached by content fingerprint), so YAML parsing
and validation happen once per change, not on every command.
"""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from didact.core.i18n import _
from didact.core.output import JSON
from didact.packs.kinds import DEFAULT_FOLDERS, KIND_NAMES, default_alias, detect, validator_for
from didact.packs.source import Doc, PackFileError, Problem, read_markdown, read_yaml_items
from didact.packs.versions import parse_requirement

if TYPE_CHECKING:
    from didact.packs.manifest import Manifest

BUNDLE_FORMAT = 1
MANIFEST = "pack.yaml"


@dataclass(slots=True)
class BuildResult:
    bundle: dict[str, JSON] | None
    problems: list[Problem] = field(default_factory=list)

    @property
    def errors(self) -> list[Problem]:
        return [p for p in self.problems if p.severity == "error"]

    @property
    def ok(self) -> bool:
        return self.bundle is not None and not self.errors


def fingerprint(root: Path) -> str:
    """Changes whenever any file in the pack changes (paths, sizes, modification times)."""
    digest = hashlib.sha256()
    for path in _files(root):
        stat = path.stat()
        digest.update(
            f"{path.relative_to(root).as_posix()}|{stat.st_size}|{stat.st_mtime_ns}\n".encode()
        )
    return digest.hexdigest()[:24]


def file_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in _files(root)
    }


def _files(root: Path) -> list[Path]:
    return sorted(
        p
        for p in root.rglob("*")
        if p.is_file()
        and not any(
            part.startswith(".") or part == "__pycache__" for part in p.relative_to(root).parts
        )
    )


def build(root: Path) -> BuildResult:
    problems: list[Problem] = []
    if not (root / MANIFEST).is_file():
        return BuildResult(
            None, [Problem(MANIFEST, None, _("no pack.yaml here"), _("run `didact pack new <id>`"))]
        )
    manifest = _manifest(root, problems)
    # Check the content even when the manifest is wrong, so one run reports everything.
    folders = DEFAULT_FOLDERS | (manifest.content if manifest else {})
    items = scan_items(root, folders, problems)
    reference = _reference(root / folders["reference"], root, problems)
    glossary = _glossary(root, problems)
    dice = _dice(root, problems)
    if manifest is None:
        return BuildResult(None, problems)
    guide_path = root / manifest.guide
    guide = guide_path.read_text(encoding="utf-8") if guide_path.is_file() else ""
    if not guide:
        problems.append(
            Problem(
                manifest.guide,
                None,
                _("no guide"),
                _("add a GUIDE.md: how to run this pack"),
                "warning",
            )
        )
    for plugin in manifest.plugins:
        if not (root / plugin).is_file():
            problems.append(
                Problem(
                    MANIFEST, None, _("plugin {plugin} not found", plugin=plugin), _("fix the path")
                )
            )
    for requirement in manifest.requires.packs:
        try:
            parse_requirement(requirement)
        except ValueError as exc:
            problems.append(Problem(MANIFEST, None, str(exc), _("e.g. `core` or `core >=0.1`")))
    bundle: dict[str, JSON] = {
        "format": BUNDLE_FORMAT,
        "manifest": manifest.model_dump(mode="json"),
        "alias": manifest.alias or default_alias(manifest.id),
        "items": {kind: entries for kind, entries in items.items() if entries},
        "reference": reference,
        "glossary": glossary,
        "dice": dice,
        "guide": guide,
        "files": dict(file_hashes(root)),
    }
    return BuildResult(
        bundle if not [p for p in problems if p.severity == "error"] else None, problems
    )


def scan_items(
    root: Path, folders: dict[str, str], problems: list[Problem]
) -> dict[str, dict[str, JSON]]:
    """Every content item under `root`, by kind, each validated (problems collected)."""
    items: dict[str, dict[str, JSON]] = {kind: {} for kind in KIND_NAMES}
    seen: dict[tuple[str, str], str] = {}
    for folder_key, folder_name in folders.items():
        directory = root / folder_name
        if not directory.is_dir() or folder_key == "reference":
            continue
        for path in sorted(directory.rglob("*.y*ml")):
            rel = path.relative_to(root).as_posix()
            try:
                docs = list(read_yaml_items(path, rel))
            except PackFileError as exc:
                problems.append(exc.problem)
                continue
            for doc in docs:
                _add_item(doc, folder_key, items, seen, problems)
    return items


def build_overlay(root: Path) -> BuildResult:
    """Homebrew for a pack (`systems/<pack>/homebrew/`): the same folders, no manifest."""
    problems: list[Problem] = []
    items = scan_items(root, dict(DEFAULT_FOLDERS), problems)
    bundle: dict[str, JSON] = {"items": {k: v for k, v in items.items() if v}}
    errors = [p for p in problems if p.severity == "error"]
    return BuildResult(None if errors else bundle, problems)


def _manifest(root: Path, problems: list[Problem]) -> Manifest | None:
    from pydantic import ValidationError

    from didact.packs.manifest import Manifest

    path = root / MANIFEST
    try:
        docs = list(read_yaml_items(path, MANIFEST))
    except PackFileError as exc:
        problems.append(exc.problem)
        return None
    if len(docs) != 1:
        problems.append(Problem(MANIFEST, 1, _("pack.yaml must hold exactly one mapping")))
        return None
    doc = docs[0]
    try:
        return Manifest.model_validate(doc.data)
    except ValidationError as exc:
        problems.extend(pydantic_problems(doc, exc))
        return None


def pydantic_problems(doc: Doc, exc: object) -> list[Problem]:
    """Turn a pydantic ValidationError into file:line problems."""
    found: list[Problem] = []
    for error in getattr(exc, "errors")():  # noqa: B009 (typed as object to keep pydantic lazy)
        loc = tuple(error.get("loc", ()))
        key = ".".join(str(p) for p in loc) or "(item)"
        message = str(error.get("msg", "invalid")).removeprefix("Value error, ")
        kind = error.get("type", "")
        hint = None
        if kind == "extra_forbidden":
            message = _("unknown key `{key}`", key=key)
            hint = _("remove it or check the spelling")
        elif kind == "missing":
            message, hint = _("missing `{key}`", key=key), _("add `{key}:`", key=key)
        elif kind == "literal_error":
            expected = str(error.get("ctx", {}).get("expected", "")).replace("'", "")
            message = _("`{key}` must be one of: {expected}", key=key, expected=expected)
        else:
            message = f"`{key}`: {message}"
        found.append(doc.problem(loc, message, hint))
    return found


def _add_item(
    doc: Doc,
    folder: str,
    items: dict[str, dict[str, JSON]],
    seen: dict[tuple[str, str], str],
    problems: list[Problem],
) -> None:
    detected = detect(doc, folder)
    if isinstance(detected, Problem):
        problems.append(detected)
        return
    kind, item_id = detected
    where = f"{doc.file}:{doc.line}"
    if (kind.name, item_id) in seen:
        problems.append(
            doc.problem(
                (kind.key,),
                _(
                    "duplicate {kind} `{id}` (also at {other})",
                    kind=kind.name,
                    id=item_id,
                    other=seen[kind.name, item_id],
                ),
                _("give one of them another id"),
            )
        )
        return
    seen[kind.name, item_id] = where
    validate = validator_for(kind.name)
    if validate is not None:
        found = validate(doc)
        problems.extend(found)
        if any(p.severity == "error" for p in found):
            return
    items[kind.name][item_id] = {"data": doc.data, "source": where}


def _reference(directory: Path, root: Path, problems: list[Problem]) -> dict[str, JSON]:
    """`reference/*.md`: rule text in short, citeable sections (front matter: id, title, …)."""
    sections: dict[str, JSON] = {}
    if not directory.is_dir():
        return sections
    for path in sorted(directory.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        try:
            meta, body = read_markdown(path, rel)
        except PackFileError as exc:
            problems.append(exc.problem)
            continue
        section_id = str(meta.get("id") or path.stem)
        if section_id in sections:
            problems.append(Problem(rel, 1, _("duplicate reference section `{id}`", id=section_id)))
            continue
        title = str(meta.get("title") or section_id.replace("-", " ").capitalize())
        sections[section_id] = {"meta": meta, "title": title, "body": body.strip(), "source": rel}
    return sections


def _glossary(root: Path, problems: list[Problem]) -> dict[str, JSON]:
    """`glossary.yaml`: `term: definition`, or a list of {term, definition, aliases, see}."""
    path = root / "glossary.yaml"
    terms: dict[str, JSON] = {}
    if not path.is_file():
        return terms
    try:
        docs = list(read_yaml_items(path, "glossary.yaml"))
    except PackFileError as exc:
        problems.append(exc.problem)
        return terms
    for doc in docs:
        if "term" in doc.data:
            entries: list[dict[str, JSON]] = [doc.data]
        else:
            entries = [{"term": k, "definition": v} for k, v in doc.data.items()]
        for entry in entries:
            term = entry.get("term")
            definition = entry.get("definition")
            if not isinstance(term, str) or not isinstance(definition, str):
                problems.append(
                    doc.problem((), _("glossary entries need `term` and `definition` text"))
                )
                continue
            terms[term.casefold()] = {**entry, "source": f"glossary.yaml:{doc.line}"}
    return terms


def _dice(root: Path, problems: list[Problem]) -> dict[str, JSON]:
    """`dice.yaml`: named dice (faces), macros and dice chains."""
    path = root / "dice.yaml"
    if not path.is_file():
        return {}
    try:
        docs = list(read_yaml_items(path, "dice.yaml"))
    except PackFileError as exc:
        problems.append(exc.problem)
        return {}
    if len(docs) != 1:
        problems.append(Problem("dice.yaml", 1, _("dice.yaml must hold one mapping")))
        return {}
    doc = docs[0]
    from didact.packs.dice import check_dice

    problems.extend(check_dice(doc))
    return doc.data
