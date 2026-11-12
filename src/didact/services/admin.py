"""Administration: rename everywhere, replace text, bulk edits, merges, copies, moves, promotions.

Everything plans into a Changeset, so it can be previewed, staged, applied as one event and undone.
The event log and transcripts are never rewritten. When an id changes (a merge, a new slug),
references follow everywhere else: links, text, details, the records journal beats are about,
and campaign state (the party, the fight, where the party is).
"""

import copy
import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from didact.core.errors import ConflictError, InvalidError
from didact.core.i18n import _
from didact.core.ids import GLOBAL, EntityId, Scope, slugify
from didact.core.output import JSON
from didact.schema.model import TypeSchema
from didact.schema.sheet import Sheet
from didact.services import assign
from didact.services.records import edit, planned
from didact.store.changeset import Changeset
from didact.store.entity import Entity
from didact.store.repo import (
    Located,
    Repo,
    campaign_file_text,
    parse_entity,
    render_entity,
    world_file_text,
)


@dataclass(slots=True)
class ReplaceStats:
    replacements: int = 0
    per_file: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------- id references


def id_pattern(entity_id: str) -> re.Pattern[str]:
    """Matches an id as a whole token (so `npc:tom` doesn't match inside `npc:tomas`)."""
    return re.compile(rf"(?<![A-Za-z0-9_:\-]){re.escape(entity_id)}(?![A-Za-z0-9_\-])")


def rewrite_references(
    changeset: Changeset, old_id: str, new_id: str, *, skip: Sequence[Path] = ()
) -> list[str]:
    """Point every link and textual mention of `old_id` at `new_id`, across the whole home."""
    repo = changeset.repo
    pattern = id_pattern(old_id)
    touched: list[str] = []
    skipped = {repo.layout.rel(p) for p in skip}
    for _scope, rel in repo.entity_files():
        if rel in skipped:
            continue
        path = repo.layout.abs(rel)
        text = changeset.planned_text(path)
        if text is None or not pattern.search(text):
            continue

        def retarget(entity: Entity) -> None:
            for link in entity.links:
                base, sep, scope = link.to.partition("@")
                if base == old_id:
                    link.to = new_id + (sep + scope if sep else "")
            _map_strings(entity, lambda s: pattern.sub(new_id, s))

        entity = edit(changeset, path, retarget)
        touched.append(str(entity.id))
    _rewrite_play_files(changeset, pattern, new_id)
    return touched


def _rewrite_play_files(changeset: Changeset, pattern: re.Pattern[str], new_id: str) -> None:
    """Journals' `about` lists and campaign state files (party, fight, location) follow an id."""
    repo = changeset.repo
    for world_id in repo.world_ids():
        folder = repo.layout.world_dir(world_id)
        paths = [
            *folder.glob("campaigns/*/journal/*.jsonl"),
            *folder.glob("campaigns/*/state/*.yaml"),
            *folder.glob("state/*.yaml"),
        ]
        for path in sorted(paths):
            text = changeset.planned_text(path)
            if text is None or not pattern.search(text):
                continue
            new = _rewrite_about(text, pattern, new_id) if path.suffix == ".jsonl" else (
                pattern.sub(new_id, text)
            )  # fmt: skip
            if new != text:
                changeset.write(path, new)


def _rewrite_about(journal: str, pattern: re.Pattern[str], new_id: str) -> str:
    """A journal with each beat's `about` ids pointed at `new_id` (the beats' text stays)."""
    lines: list[str] = []
    for line in journal.splitlines(keepends=True):
        if not line.strip():
            lines.append(line)
            continue
        beat = json.loads(line)
        about = beat.get("about") if isinstance(beat, dict) else None
        if not isinstance(about, list) or not any(pattern.fullmatch(str(a)) for a in about):
            lines.append(line)
            continue
        beat["about"] = list(
            dict.fromkeys(new_id if pattern.fullmatch(str(a)) else a for a in about)
        )
        lines.append(json.dumps(beat, ensure_ascii=False) + "\n")
    return "".join(lines)


def _map_strings(entity: Entity, fn: Callable[[str], str]) -> None:
    """Apply fn to the body, the details, and every string value in fields, mechanics and
    extra."""
    entity.body = fn(entity.body)
    entity.details = {name: fn(text) for name, text in entity.details.items()}

    def walk(value: JSON) -> JSON:
        if isinstance(value, str):
            return fn(value)
        if isinstance(value, list):
            return [walk(v) for v in value]
        if isinstance(value, dict):
            return {k: walk(v) for k, v in value.items()}
        return value

    entity.fields = cast(dict[str, JSON], walk(entity.fields))
    entity.mechanics = cast(dict[str, JSON], walk(entity.mechanics))
    entity.extra = cast(dict[str, JSON], walk(entity.extra))


# ---------------------------------------------------------------------- rename


def rename(
    changeset: Changeset,
    located: Located,
    new_name: str,
    *,
    reslug: bool,
    rewrite_text: bool,
    text_scopes: Sequence[Scope],
) -> EntityId:
    repo = changeset.repo
    old = located.entity
    old_name, old_id = old.name, old.id
    new_name = new_name.strip()
    if not new_name:
        raise InvalidError(
            _("the new name can't be empty"), hint=_("e.g. `didact rename tom 'Tom Miller'`")
        )
    target_id = EntityId(old_id.type, slugify(new_name)) if reslug else old_id
    if target_id != old_id:
        repo.ensure_new(located.scope, target_id)

    def change(entity: Entity) -> None:
        entity.name = new_name
        if old_name != new_name and old_name not in entity.aliases:
            entity.aliases.append(old_name)
        if target_id != old_id and str(old_id) not in entity.aliases:
            entity.aliases.append(str(old_id))

    edit(changeset, located.path, change)
    if target_id != old_id:
        text = changeset.planned_text(located.path)
        assert text is not None
        moved = parse_entity(text, repo.layout.rel(located.path))
        moved.id = target_id
        new_path = repo.entity_path(located.scope, target_id)
        changeset.write(new_path, render_entity(moved, text))
        changeset.delete(located.path)
        changeset.mention(str(target_id))
        rewrite_references(changeset, str(old_id), str(target_id), skip=[located.path, new_path])
    if rewrite_text and old_name != new_name:
        replace_text(
            changeset, old_name, new_name, scopes=text_scopes, whole_word=True, keep_alias=True
        )
    return target_id


def rename_container(changeset: Changeset, kind: str, container_id: str, new_name: str) -> str:
    """Rename a world or campaign (its display name; ids of worlds and campaigns stay)."""
    repo = changeset.repo
    if kind == "world":
        world = repo.load_world(container_id)
        old = world.name
        world.name = new_name
        path = repo.layout.world_file(container_id)
        changeset.write(path, world_file_text(world, repo.read_text(path)))
    else:
        campaign = repo.load_campaign(container_id)
        old = campaign.name
        campaign.name = new_name
        path = repo.layout.campaign_file(campaign.world, container_id)
        changeset.write(path, campaign_file_text(campaign, repo.read_text(path)))
    return old


# ---------------------------------------------------------------------- replace text


def replace_text(
    changeset: Changeset,
    old: str,
    new: str,
    *,
    scopes: Sequence[Scope],
    types: Sequence[str] = (),
    regex: bool = False,
    ignore_case: bool = False,
    whole_word: bool = False,
    keep_alias: bool = True,
) -> ReplaceStats:
    """Replace text in names, bodies and string values of records (and world/campaign names).

    Old names are kept as aliases so references by name still resolve. Ids are never touched.
    """
    if not old:
        raise InvalidError(_("nothing to replace"), hint=_("give the text to find"))
    flags = re.IGNORECASE if ignore_case else 0
    source = old if regex else re.escape(old)
    if whole_word:
        source = rf"(?<!\w){source}(?!\w)"
    try:
        pattern = re.compile(source, flags)
    except re.error as exc:
        raise InvalidError(
            _("invalid pattern: {error}", error=exc), hint=_("check the regex, or drop --regex")
        ) from exc
    repo = changeset.repo
    stats = ReplaceStats()

    def sub(text: str) -> str:
        result, count = pattern.subn(new, text)
        stats.replacements += count
        return result

    for _scope, rel in repo.entity_files(scopes):
        path = repo.layout.abs(rel)
        text = changeset.planned_text(path)
        if text is None or not pattern.search(text):
            continue
        entity = planned(changeset, path)
        if types and entity.type not in types:
            continue
        before_count = stats.replacements

        def change(entity: Entity) -> None:
            renamed = sub(entity.name)
            if renamed != entity.name:
                if keep_alias and entity.name not in entity.aliases:
                    entity.aliases.append(entity.name)
                entity.name = renamed
            _map_strings(entity, sub)

        edit(changeset, path, change)
        if stats.replacements > before_count:
            stats.per_file[rel] = stats.replacements - before_count

    for scope in scopes:
        if scope.kind not in ("world", "campaign"):
            continue
        before_count = stats.replacements
        if scope.kind == "world":
            world = repo.load_world(str(scope.name))
            world.name, world.description = sub(world.name), sub(world.description)
            path = repo.layout.world_file(world.id)
            if stats.replacements > before_count:
                changeset.write(path, world_file_text(world, changeset.planned_text(path)))
        else:
            campaign = repo.load_campaign(str(scope.name))
            campaign.name, campaign.description = sub(campaign.name), sub(campaign.description)
            path = repo.layout.campaign_file(campaign.world, campaign.id)
            if stats.replacements > before_count:
                changeset.write(path, campaign_file_text(campaign, changeset.planned_text(path)))
        if stats.replacements > before_count:
            stats.per_file[repo.layout.rel(path)] = stats.replacements - before_count
    return stats


# ---------------------------------------------------------------------- bulk set


@dataclass(frozen=True, slots=True)
class Condition:
    key: str
    op: str  # "=", "!=", "~="
    value: str

    def matches(self, entity: Entity, scope: Scope) -> bool:
        actual = _lookup(entity, scope, self.key)
        values = [
            str(v).casefold()
            for v in (actual if isinstance(actual, list) else [actual])
            if v is not None
        ]
        wanted = self.value.casefold()
        match self.op:
            case "=":
                return wanted in values
            case "!=":
                return wanted not in values
            case _:
                return any(wanted in v for v in values)


_CONDITION = re.compile(r"^(?P<key>[A-Za-z0-9_.\-]+)\s*(?P<op>!=|~=|=)(?P<value>.*)$")


def parse_condition(text: str) -> Condition:
    match = _CONDITION.match(text)
    if match is None:
        raise InvalidError(
            _("can't read condition {text}", text=repr(text)),
            hint=_("use key=value, key!=value or key~=text, e.g. `type=npc`"),
        )
    return Condition(match["key"], match["op"], match["value"].strip())


def _lookup(entity: Entity, scope: Scope, key: str) -> JSON:
    match key:
        case "type":
            return entity.type
        case "id":
            return str(entity.id)
        case "scope":
            return str(scope)
        case "name":
            return [entity.name, *entity.aliases]
        case "tag" | "tags":
            return list(entity.tags)
        case "status":
            return entity.status
        case "knowledge":
            return entity.knowledge
        case "archived":
            return str(entity.archived).lower()
    path = assign.parse_key(key)
    node: JSON = cast(JSON, getattr(entity, path[0]))
    for part in path[1:]:
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def bulk_set(
    changeset: Changeset,
    *,
    scopes: Sequence[Scope],
    conditions: Sequence[Condition],
    assignments: Sequence[assign.Assignment],
    unsets: Sequence[str],
) -> list[str]:
    repo = changeset.repo
    matched: list[str] = []
    for scope, rel in repo.entity_files(scopes):
        path = repo.layout.abs(rel)
        entity = planned(changeset, path)
        if not all(c.matches(entity, scope) for c in conditions):
            continue

        def change(entity: Entity) -> None:
            for a in assignments:
                assign.apply(entity, a)
            for key in unsets:
                assign.unset(entity, key)

        edit(changeset, path, change)
        matched.append(str(entity.id))
    return matched


# ---------------------------------------------------------------------- merge


def merge(changeset: Changeset, duplicate: Located, keep: Located) -> tuple[list[str], list[str]]:
    """Fold `duplicate` into `keep`; returns the conflicting keys where `keep`'s value won, and
    the values left out because `keep`'s sheet has no field for them (`key (value)`): a merge
    across types keeps no stray data."""
    from didact.services import sheets

    if duplicate.path == keep.path:
        raise InvalidError(
            _("can't merge a record into itself"), hint=_("name two different records")
        )
    dup = duplicate.entity
    conflicts: list[str] = []
    incoming, left = _fitting(dup, sheets.sheet(changeset.repo, keep.entity.type))

    def fold(entity: Entity) -> None:
        for alias in (dup.name, *dup.aliases, str(dup.id)):
            if alias != entity.name and alias not in entity.aliases:
                entity.aliases.append(alias)
        entity.tags += [t for t in dup.tags if t not in entity.tags]
        for container in ("fields", "mechanics", "extra"):
            conflicts.extend(
                _merge_maps(getattr(entity, container), incoming[container], container)
            )
        # Links from the survivor to the duplicate would point at itself after the merge.
        entity.links = [lk for lk in entity.links if lk.to.partition("@")[0] != str(dup.id)]
        for link in dup.links:
            if link.to != str(entity.id) and not any(
                other.rel == link.rel and other.to == link.to for other in entity.links
            ):
                entity.links.append(copy.copy(link))
        if dup.body.strip():
            entity.body = (
                entity.body.rstrip("\n") + f"\n\n## Merged from {dup.id}\n\n{dup.body.strip()}\n"
            )

    edit(changeset, keep.path, fold)
    changeset.delete(duplicate.path)
    changeset.mention(str(dup.id))
    # The survivor is skipped: its aliases and merge note must keep naming the duplicate.
    rewrite_references(
        changeset, str(dup.id), str(keep.entity.id), skip=[duplicate.path, keep.path]
    )
    return conflicts, left


def _fitting(dup: Entity, sh: Sheet) -> tuple[dict[str, dict[str, JSON]], list[str]]:
    """The duplicate's values that the survivor's sheet has room for (a closed schema's own
    fields: another system's block, or an open one, takes anything), and those it hasn't."""
    incoming: dict[str, dict[str, JSON]] = {
        "fields": copy.deepcopy(dup.fields),
        "mechanics": copy.deepcopy(dup.mechanics),
        "extra": copy.deepcopy(dup.extra),
    }
    left: list[str] = []
    places: list[tuple[TypeSchema, dict[str, JSON], str]] = []
    if sh.core is not None:
        places.append((sh.core, incoming["fields"], ""))
    if sh.mechanics is not None:
        block = incoming["mechanics"].get(sh.mechanics.pack)
        if isinstance(block, dict):
            places.append((sh.mechanics, block, f"{sh.mechanics.pack}."))
    for schema, values, prefix in places:
        if schema.open:
            continue
        for key in [k for k in values if schema.field(k) is None]:
            value = values.pop(key)
            shown = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            left.append(f"{prefix}{key} ({shown})")
    return incoming, left


def _merge_maps(target: dict[str, JSON], source: dict[str, JSON], prefix: str) -> list[str]:
    conflicts: list[str] = []
    for key, value in source.items():
        if key not in target:
            target[key] = copy.deepcopy(value)
        elif isinstance(target[key], dict) and isinstance(value, dict):
            conflicts += _merge_maps(cast(dict[str, JSON], target[key]), value, f"{prefix}.{key}")
        elif target[key] != value:
            conflicts.append(f"{prefix}.{key}")
    return conflicts


# ---------------------------------------------------------------------- copy / move / promote


def copy_to(
    changeset: Changeset, located: Located, target: Scope, new_slug: str | None = None
) -> EntityId:
    repo = changeset.repo
    repo.check_scope(target)
    entity = copy.deepcopy(located.entity)
    if new_slug:
        entity.id = EntityId(entity.id.type, slugify(new_slug))
    if target == located.scope and entity.id == located.entity.id:
        raise ConflictError(
            _("a copy into the same scope needs a new id"), hint=_("pass --id <slug>")
        )
    repo.ensure_new(target, entity.id)
    entity.created = ""
    repo.touch(entity, created=True)
    changeset.write(repo.entity_path(target, entity.id), render_entity(entity))
    changeset.mention(str(entity.id))
    return entity.id


def move_to(changeset: Changeset, located: Located, target: Scope) -> None:
    repo = changeset.repo
    repo.check_scope(target)
    if target == located.scope:
        raise InvalidError(
            _("{id} is already in {scope}", id=located.entity.id, scope=target),
            hint=_("promote it to a wider scope"),
        )
    repo.ensure_new(target, located.entity.id)
    text = changeset.planned_text(located.path)
    assert text is not None
    changeset.write(repo.entity_path(target, located.entity.id), text)
    changeset.delete(located.path)
    changeset.mention(str(located.entity.id))


def promotion_target(repo: Repo, scope: Scope) -> Scope:
    """The next wider scope: campaign → its world → global."""
    match scope.kind:
        case "campaign":
            return Scope("world", repo.load_campaign(str(scope.name)).world)
        case "world" | "system":
            return GLOBAL
        case _:
            raise InvalidError(
                _("global records can't be promoted further"),
                hint=_("global is the widest scope"),
            )
