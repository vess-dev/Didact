"""Record operations shared by commands.

Each one plans into a Changeset; nothing writes directly.
"""

import copy
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import cast

from didact.core.clock import now_iso
from didact.core.errors import ConflictError, InvalidError
from didact.core.i18n import _
from didact.core.ids import EntityId, Scope, check_type, slugify
from didact.core.output import JSON
from didact.store import frontmatter
from didact.store.changeset import Changeset
from didact.store.entity import CORE_ORDER, Entity, Link
from didact.store.repo import Located, parse_entity, render_entity

# Keys accepted in `--data` besides the core front matter keys; anything else goes into fields.
DATA_KEYS = frozenset({*CORE_ORDER, "body"})


def build_entity(
    entity_id: EntityId,
    name: str | None,
    data: Mapping[str, JSON] | None = None,
    *,
    aliases: Sequence[str] = (),
    tags: Sequence[str] = (),
    body: str | None = None,
    where: str = "--data",
) -> Entity:
    """Build and validate an entity from `--data` JSON plus flags (flags win)."""
    meta: dict[str, JSON] = {}
    fields: dict[str, JSON] = {}
    for key, value in (data or {}).items():
        if key in ("id", "type", "created", "updated"):
            continue  # Didact decides these
        if key in DATA_KEYS:
            meta[key] = value
        else:
            fields[key] = value  # "describe it" payloads often put stats at the top level
    if fields:
        existing = meta.get("fields")
        merged: dict[str, JSON] = dict(existing) if isinstance(existing, dict) else {}
        merged.update(fields)
        meta["fields"] = merged
    if name is not None:
        meta["name"] = name
    if aliases:
        meta["aliases"] = [*cast(list[str], meta.get("aliases") or []), *aliases]
    if tags:
        meta["tags"] = [*cast(list[str], meta.get("tags") or []), *tags]
    text = body if body is not None else meta.pop("body", "")
    meta.pop("body", None)
    meta["id"] = str(entity_id)
    meta["type"] = entity_id.type
    return Entity.from_meta(meta, text if isinstance(text, str) else "", where=where)


def new_id(type_: str, name: str, slug: str | None = None) -> EntityId:
    check_type(type_)
    if slug is not None and ":" in slug:
        parsed = EntityId.parse(slug)
        if parsed.type != type_:
            raise InvalidError(
                _("--id {slug} doesn't match type {type}", slug=repr(slug), type=repr(type_)),
                hint=_("an id for this type starts with `{type}:`", type=type_),
            )
        return parsed
    return EntityId(type_, slugify(slug if slug else name))


def create(changeset: Changeset, scope: Scope, entity: Entity) -> Path:
    repo = changeset.repo
    repo.ensure_new(scope, entity.id)
    repo.touch(entity, created=True)
    path = repo.entity_path(scope, entity.id)
    changeset.write(path, render_entity(entity))
    changeset.mention(str(entity.id))
    return path


def planned(changeset: Changeset, path: Path) -> Entity:
    """The entity as it will be after the changes planned so far."""
    text = changeset.planned_text(path)
    if text is None:
        raise ConflictError(
            _("{path} is already being removed", path=changeset.repo.layout.rel(path)),
            hint=_("remove each record once"),
        )
    return parse_entity(text, changeset.repo.layout.rel(path))


def edit(changeset: Changeset, path: Path, mutate: Callable[[Entity], None]) -> Entity:
    """Load (as planned), mutate, stamp and re-render an entity, keeping hand-written comments."""
    previous = changeset.planned_text(path)
    entity = planned(changeset, path)
    before = copy.deepcopy(entity)
    mutate(entity)
    if entity.meta() == before.meta() and entity.body == before.body:
        return entity
    changeset.repo.touch(entity)
    changeset.write(path, render_entity(entity, previous))
    changeset.mention(str(entity.id))
    return entity


def add_note(entity: Entity, text: str) -> None:
    """Append a dated bullet under a `## Notes` heading."""
    bullet = f"- {now_iso()[:10]}: {text.strip()}"
    body = entity.body.rstrip("\n")
    if "## Notes" not in body.splitlines():
        body = f"{body}\n\n## Notes" if body else "## Notes"
    entity.body = f"{body}\n{bullet}\n"


def add_link(entity: Entity, rel: str, target: str) -> None:
    if not rel.strip():
        raise InvalidError(
            _("a link needs a relation"), hint=_("e.g. `didact link npc:tom ally npc:ann`")
        )
    if any(link.rel == rel and link.to == target for link in entity.links):
        return
    entity.links.append(Link(rel.strip(), target))


def remove_link(entity: Entity, rel: str | None, target: str) -> None:
    before = len(entity.links)
    entity.links = [
        link
        for link in entity.links
        if not (_same_target(link.to, target) and (rel is None or link.rel == rel))
    ]
    if len(entity.links) == before:
        raise InvalidError(
            _("{id} has no link to {target}", id=entity.id, target=target),
            hint=_("`didact show {id}` lists its links", id=entity.id),
        )


def _same_target(link_to: str, target: str) -> bool:
    return link_to == target or link_to.partition("@")[0] == target.partition("@")[0]


def delete(changeset: Changeset, located: Located, *, unlink: bool, force: bool) -> list[str]:
    """Delete a record. References from other records block it unless unlinked or forced.

    Returns the ids of records whose links were removed.
    """
    repo = changeset.repo
    target = str(located.entity.id)
    backlinks = [
        b
        for b in repo.index().backlinks([target])
        if b.source.path != repo.layout.rel(located.path)
    ]
    if backlinks and not (unlink or force):
        sources = ", ".join(sorted({f"{b.source.id} ({b.rel})" for b in backlinks}))
        raise ConflictError(
            _("{target} is still referenced by {sources}", target=target, sources=sources),
            hint=_("pass --unlink to remove those links too, or --force to leave them dangling"),
        )
    touched: list[str] = []
    if unlink:
        for backlink in backlinks:
            path = repo.layout.abs(backlink.source.path)
            edit(changeset, path, lambda e: remove_link(e, None, target))
            touched.append(backlink.source.id)
    changeset.delete(located.path)
    changeset.mention(target)
    return touched


def forget_in_play(changeset: Changeset, target: str) -> list[str]:
    """A deleted record leaves play too: every campaign's party, its fight (the turn order
    stays sensible) and the party's location. Returns notes saying what changed."""
    repo = changeset.repo
    notes: list[str] = []
    for campaign_id, world_id in sorted(repo.campaign_index().items()):
        folder = repo.layout.campaign_dir(world_id, campaign_id) / "state"
        if _edit_state(changeset, folder / "party.yaml", lambda d: _drop_member(d, target)):
            notes.append(_("left the party (campaign {campaign})", campaign=campaign_id))
        if _edit_state(changeset, folder / "combat.yaml", lambda d: _drop_fighter(d, target)):
            notes.append(_("left the fight (campaign {campaign})", campaign=campaign_id))
        if _edit_state(changeset, folder / "play.yaml", lambda d: _drop_location(d, target)):
            notes.append(
                _(
                    "the party is nowhere in particular now (campaign {campaign})",
                    campaign=campaign_id,
                )
            )
    return notes


def _edit_state(
    changeset: Changeset, path: Path, change: Callable[[dict[str, JSON]], bool]
) -> bool:
    text = changeset.planned_text(path)
    if not text:
        return False
    data = frontmatter.to_plain(frontmatter.load(text, where=changeset.repo.layout.rel(path)))
    if not isinstance(data, dict) or not change(data):
        return False
    changeset.write(path, frontmatter.dump(frontmatter.from_plain(data)))
    return True


def _drop_member(data: dict[str, JSON], target: str) -> bool:
    members = data.get("members")
    if not isinstance(members, list):
        return False
    kept = [m for m in members if not (isinstance(m, dict) and m.get("id") == target)]
    data["members"] = list[JSON](kept)
    return len(kept) != len(members)


def _drop_fighter(data: dict[str, JSON], target: str) -> bool:
    """The fighter leaves the fight the way `combat leave` does: nobody's turn is skipped."""
    from didact.services import combat

    fight = combat.Fight.from_data(data)
    if not any(f.ref == target for f in fight.order):
        return False
    combat.leave(fight, target)
    data.clear()
    data.update(fight.to_data())
    return True


def _drop_location(data: dict[str, JSON], target: str) -> bool:
    if data.get("location") != target:
        return False
    data["location"] = None
    return True


def describe(entity: Entity, scope: Scope) -> str:
    return f"{entity.id} · {entity.name} ({scope})"
