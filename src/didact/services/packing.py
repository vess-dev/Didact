"""Packs made from a library: a system's homebrew as a supplement (`pack new --from-overlay`),
and a world as a setting (`world export --as setting`).

Records become compendium entries (`compendium import <pack>` brings them back as records) and
lore records become pack lore, which comes up in play by itself. What the players don't know
stays out unless asked for: secret records, secret sections and fields, and the GM's notes.
A made pack isn't marked as shareable: `pack export` refuses it until its licence says so.
"""

import shutil
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from didact.core.errors import ConflictError, InvalidError
from didact.core.i18n import _, ngettext
from didact.core.ids import Scope
from didact.core.output import JSON
from didact.packs.build import build
from didact.services import knowledge, sheets
from didact.store import frontmatter
from didact.store.entity import Entity
from didact.store.fsutil import atomic_write
from didact.store.repo import BOOKKEEPING, Repo

LORE_KEEPS = ("keys", "secondary", "logic", "priority", "kind", "constant", "group", "probability")
LORE_DROPS = ("sticky", "cooldown", "delay")  # play-time timing a pack's lore doesn't take
LEFT_OUT = frozenset({*BOOKKEEPING, "pc", "task", "track", "thread"}) - {"lore"}


@dataclass(slots=True)
class Made:
    """A pack written: where, its files, and what was left out or needs looking at."""

    root: Path
    files: list[str] = field(default_factory=list)
    entries: int = 0
    lore: int = 0
    notes: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def entry_of(repo: Repo, entity: Entity, *, secrets: bool) -> dict[str, JSON]:
    """A record as a compendium entry: `compendium import` turns it back into the record. A
    player copy unless `secrets`, which keeps the GM's notes and marks a secret record so."""
    sh = sheets.sheet(repo, entity.id.type)
    shown = entity if secrets else knowledge.player_copy(entity, sh, knowledge.unknown(repo))[0]
    data: dict[str, JSON] = {"id": entity.id.slug, "type": entity.id.type, "name": shown.name}
    if shown.aliases:
        data["aliases"] = list[JSON](shown.aliases)
    if shown.tags:
        data["tags"] = list[JSON](shown.tags)
    for key in ("fields", "mechanics"):
        value = getattr(shown, key)
        if value:
            data[key] = value
    if shown.details:
        data["details"] = dict[str, JSON](shown.details)
    if shown.links:
        data["links"] = [link.to_data() for link in shown.links]
    if shown.body.strip():
        data["body"] = shown.body.strip()
    if secrets and not knowledge.visible(entity.knowledge, gm=False):
        data["secret"] = True
    return data


def lore_of(entity: Entity) -> tuple[dict[str, JSON], bool]:
    """A lore record as pack lore, and whether play-time timing (sticky, …) had to go."""
    data: dict[str, JSON] = {"lore": entity.id.slug, "title": entity.name}
    data.update({k: entity.fields[k] for k in LORE_KEEPS if k in entity.fields})
    if entity.fields.get("recursive") is False:
        data["recursive"] = False
    if entity.tags:
        data["tags"] = list[JSON](entity.tags)
    data["content"] = entity.body.strip()
    return data, any(k in entity.fields for k in LORE_DROPS)


def records(repo: Repo, scopes: Sequence[Scope], *, secrets: bool) -> list[Entity]:
    """The records in these scopes a pack can carry: no play bookkeeping, no PCs, and no
    secret ones unless `secrets`."""
    found: list[Entity] = []
    for _scope, rel in repo.entity_files(scopes):
        entity = repo.load_entity(repo.layout.abs(rel))
        if entity.id.type in LEFT_OUT or entity.archived:
            continue
        if not secrets and not knowledge.visible(entity.knowledge, gm=False):
            continue
        found.append(entity)
    return found


def write(
    root: Path,
    manifest: dict[str, JSON],
    guide: str,
    repo: Repo,
    entities: Iterable[Entity],
    *,
    secrets: bool,
    copies: Path | None = None,
) -> Made:
    """Write a pack: its manifest and guide, the records as entries and lore, and the files
    under `copies` (homebrew, already in a pack's folders) as they are. Then build it, to say
    what's wrong."""
    if (root / "pack.yaml").exists():
        raise ConflictError(
            _("{folder} already holds a pack", folder=root), hint=_("choose another id or folder")
        )
    made = Made(root)
    files: dict[str, str] = {
        "pack.yaml": frontmatter.dump(frontmatter.from_plain(manifest)),
        "GUIDE.md": guide,
    }
    entries: list[dict[str, JSON]] = []
    lore: list[dict[str, JSON]] = []
    timed = 0
    for entity in entities:
        if entity.id.type == "lore":
            item, dropped = lore_of(entity)
            if not item["content"] or not (item.get("keys") or item.get("constant")):
                continue
            lore.append(item)
            timed += dropped
        else:
            entries.append(entry_of(repo, entity, secrets=secrets))
    if entries:
        files["compendium/records.yaml"] = _docs(entries)
    if lore:
        files["lore/lore.yaml"] = _docs(lore)
    if copies is not None and copies.is_dir():
        for path in sorted(copies.rglob("*")):
            rel = path.relative_to(copies).as_posix()
            if path.is_file() and path.suffix in (".yaml", ".yml", ".md") and rel not in files:
                files[rel] = path.read_text(encoding="utf-8")
    try:
        for rel, text in files.items():
            atomic_write(root / rel, text)
    except OSError:
        shutil.rmtree(root, ignore_errors=True)
        raise
    made.files = sorted(files)
    if timed:
        made.notes.append(
            ngettext(
                "{n} lore entry lost its sticky, cooldown or delay: pack lore has no timing",
                "{n} lore entries lost their sticky, cooldown or delay: pack lore has no timing",
                timed,
            )
        )
    result = build(root)
    made.problems = [p.text() for p in result.problems if p.severity == "error"]
    built = result.bundle.get("items") if result.bundle is not None else None
    if isinstance(built, dict):  # what the pack holds, copied homebrew included
        made.entries, made.lore = _count(built.get("entry")), _count(built.get("lore"))
    return made


def check_folder(root: Path) -> None:
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ConflictError(
            _("{folder} isn't empty", folder=root),
            hint=_("choose a new folder with --dir, or another id"),
        )


def guide(name: str, about: str, use: list[str]) -> str:
    """A short GUIDE.md for a made pack: what it is, and how to use it."""
    lines = [f"# {name}", "", about, "", "## Using it", *(f"- {u}" for u in use), ""]
    return "\n".join(lines)


def need_content(entities: list[Entity], copies: Path | None, what: str) -> None:
    if not entities and not (
        copies is not None and copies.is_dir() and any(copies.rglob("*.y*ml"))
    ):
        raise InvalidError(
            _("there's nothing to put in a pack: {what} has no records or homebrew", what=what),
            hint=_("add some first: `didact compendium add`, `didact new`, `didact lore add`"),
        )


def _count(items: JSON) -> int:
    return len(items) if isinstance(items, dict) else 0


def _docs(items: list[dict[str, JSON]]) -> str:
    return "---\n".join(frontmatter.dump(frontmatter.from_plain(item)) for item in items)
