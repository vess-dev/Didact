"""House rules: patches over pack items at system, world or campaign scope.

    systems/<pack>/overrides/<kind>/<id>.yaml                    every world using the pack
    worlds/<w>/overrides/<pack>/<kind>/<id>.yaml                 one world
    worlds/<w>/campaigns/<c>/overrides/<pack>/<kind>/<id>.yaml   one campaign

A patch deep-merges into the item (`null` removes a key; lists are replaced), or replaces it
whole with `mode: replace`. Narrower scopes apply last, so the campaign has the final word.
"""

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from didact.core.errors import InvalidError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.packs.library import Pack
from didact.store import frontmatter
from didact.store.changeset import Changeset
from didact.store.repo import Repo

type OverrideScope = Literal["system", "world", "campaign"]
SCOPES: tuple[OverrideScope, ...] = ("system", "world", "campaign")


@dataclass(frozen=True, slots=True)
class Override:
    scope: OverrideScope
    pack: str
    kind: str
    id: str
    patch: dict[str, JSON]
    replace: bool
    reason: str
    path: Path


def root(repo: Repo, scope: OverrideScope, pack: str) -> Path | None:
    match scope:
        case "system":
            return repo.layout.systems_dir / pack / "overrides"
        case "world":
            world = repo.active_world()
            return repo.layout.world_dir(world.id) / "overrides" / pack if world else None
        case "campaign":
            campaign = repo.active_campaign()
            if campaign is None:
                return None
            return repo.layout.campaign_dir(campaign.world, campaign.id) / "overrides" / pack


def active(repo: Repo, pack: str) -> list[Override]:
    """The overrides in effect here for one pack, broadest scope first."""
    found: list[Override] = []
    for scope in SCOPES:
        base = root(repo, scope, pack)
        if base is None or not base.is_dir():
            continue
        for path in sorted(base.glob("*/*.yaml")):
            data = frontmatter.to_plain(
                frontmatter.load(path.read_text(encoding="utf-8"), where=str(path))
            )
            if not isinstance(data, dict):
                continue
            patch = data.get("patch")
            found.append(
                Override(
                    scope,
                    pack,
                    path.parent.name,
                    path.stem,
                    patch if isinstance(patch, dict) else {},
                    data.get("mode") == "replace",
                    str(data.get("reason") or ""),
                    path,
                )
            )
    return found


def merge(base: JSON, patch: JSON) -> JSON:
    """Deep-merge `patch` into `base`: maps merge, `null` removes, anything else replaces."""
    if not isinstance(base, dict) or not isinstance(patch, dict):
        return copy.deepcopy(patch)
    merged: dict[str, JSON] = dict(base)
    for key, value in patch.items():
        if value is None:
            merged.pop(key, None)
        else:
            merged[key] = merge(merged.get(key), value)
    return merged


def apply(pack: Pack, overrides: list[Override]) -> Pack:
    """The pack with its overrides applied to its items."""
    if not overrides:
        return pack
    items = {
        k: dict(cast(dict[str, JSON], v))
        for k, v in cast(dict[str, JSON], pack.bundle.get("items") or {}).items()
    }
    for override in overrides:
        entries = items.setdefault(override.kind, {})
        current = cast(dict[str, JSON], entries.get(override.id) or {"data": {}, "source": ""})
        data = (
            override.patch if override.replace else merge(current.get("data") or {}, override.patch)
        )
        label = f"override ({override.scope}): {override.path.name}"
        entries[override.id] = {
            "data": data,
            "source": f"{current.get('source') or 'new'} + {label}",
        }
    return Pack(pack.ref, {**pack.bundle, "items": cast(dict[str, JSON], items)}, pack.trusted)


def write(
    cs: Changeset,
    scope: OverrideScope,
    pack: str,
    kind: str,
    item_id: str,
    patch: dict[str, JSON],
    *,
    replace: bool,
) -> Path:
    base = root(cs.repo, scope, pack)
    if base is None:
        raise InvalidError(
            _("no active {scope} to hold this override", scope=scope),
            hint=_("`didact {scope} use <id>` first", scope=scope),
        )
    path = base / kind / f"{item_id}.yaml"
    record: dict[str, JSON] = {"override": f"{kind}:{pack}.{item_id}", "scope": scope}
    if replace:
        record["mode"] = "replace"
    if cs.reason:
        record["reason"] = cs.reason
    record["patch"] = patch
    cs.write(path, frontmatter.dump(frontmatter.from_plain(record)))
    return path
