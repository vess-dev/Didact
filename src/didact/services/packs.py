"""Which packs are in play, and enabling or disabling them for a world or campaign.

One game system is in use at a time: the open world's. A world keeps the system it was made
with (one without a system takes the first it's given), a campaign plays its world's, and the
packs added to a world or campaign go with that system: an added pack that is a system, or
that needs another one (a setting written for it), stays out of play.
"""

import contextlib
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from didact.core import labels
from didact.core.errors import DidactError, InvalidError, NotFoundError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.packs.build import build_overlay
from didact.packs.library import CORE as CORE
from didact.packs.library import Pack, PackLibrary, PackSet
from didact.store.changeset import Changeset
from didact.store.repo import Repo, WorldInfo, campaign_file_text, world_file_text


def library(repo: Repo) -> PackLibrary:
    return PackLibrary(repo.config)


def _listed(value: JSON) -> list[str]:
    return [str(v) for v in value] if isinstance(value, list) else []


def enabled(repo: Repo, lib: PackLibrary | None = None) -> list[str]:
    """The packs in play here: core, the system, and the packs added to the world and the
    campaign that go with it (`conflicts`: the others stay out of play)."""
    wanted = [CORE]
    world = repo.active_world()
    campaign = repo.active_campaign()
    system = (campaign.system if campaign and campaign.system else None) or (
        world.system if world else None
    )  # a campaign of old may have its own
    if system:
        wanted.append(system)
    added: list[str] = []
    if world is not None:
        added += _listed(world.other.get("packs"))
    if campaign is not None:
        added += _listed(campaign.other.get("packs"))
    added = [p for p in dict.fromkeys(added) if p not in wanted]
    if added:
        misfits = conflicts(lib or library(repo), system, added)
        wanted += [p for p in added if p not in misfits]
    return wanted


def conflicts(lib: PackLibrary, system: str | None, added: Sequence[str]) -> dict[str, str]:
    """The added packs that can't be used with `system`, each with the system it is or needs
    instead: one system is in use at a time. A pack that isn't here isn't judged (using it
    says what's wrong)."""
    ours = _brings(lib, system)
    found: dict[str, str] = {}
    for pack_id in added:
        try:
            needed = lib.resolve([pack_id]).packs
        except DidactError:
            continue
        other = next((p.id for p in needed if p.kind == "system" and p.id not in ours), None)
        if other is not None:
            found[pack_id] = other
    return found


def _brings(lib: PackLibrary, system: str | None) -> set[str]:
    """The packs a system loads: itself, the system it extends and what it requires."""
    if not system:
        return set()
    try:
        return {p.id for p in lib.resolve([system]).packs}
    except DidactError:
        return {system}


def kind_of(lib: PackLibrary, pack_id: str) -> str | None:
    """What a pack is (system, setting, …), or None when it isn't here."""
    try:
        return lib.load(lib.find(pack_id)).kind
    except NotFoundError:
        return None


def tie_system(cs: Changeset, world: WorldInfo, pack_id: str) -> dict[str, str]:
    """Give a world with no game system yet its system, for good. The packs added to the
    world that can't go with it are disabled: returned, each with the system it is or needs.
    A system that isn't installed yet can be named (using it says so)."""
    lib = library(cs.repo)
    kind = kind_of(lib, pack_id)
    if kind not in (None, "system"):
        raise InvalidError(
            _(
                "{pack} is a {kind} pack, not a game system",
                pack=pack_id,
                kind=labels.pack_kind(kind),
            ),
            hint=_("the game systems here: `didact pack list`"),
        )
    listed = _listed(world.other.get("packs"))
    dropped = conflicts(lib, pack_id, listed)
    if listed:
        world.other["packs"] = list[JSON](p for p in listed if p not in dropped and p != pack_id)
    world.system = pack_id
    path = cs.repo.layout.world_file(world.id)
    cs.write(path, world_file_text(world, cs.planned_text(path)))
    cs.mention(f"world:{world.id}")
    return dropped


def dropped_lines(dropped: dict[str, str]) -> list[str]:
    """What giving a world its system disabled, and why, a line each."""
    return [
        _("disabled {pack}: another game system", pack=p)
        if p == other
        else _("disabled {pack}: it needs {system}", pack=p, system=other)
        for p, other in dropped.items()
    ]


def played_in(repo: Repo, pack_id: str) -> list[str]:
    """The worlds that play a system."""
    return [w for w in repo.world_ids() if repo.load_world(w).system == pack_id]


def used_by(repo: Repo, pack_id: str) -> list[str]:
    """Where a pack is in use: worlds and campaigns that play it as their system, enable it,
    or pin a version of it (`world vale (system)`, `campaign run (enabled)`)."""
    found: list[str] = []

    def uses(system: str | None, other: dict[str, JSON]) -> list[str]:
        how = ["system"] if system == pack_id else []
        how += ["enabled"] if pack_id in _listed(other.get("packs")) else []
        pinned = other.get("pins")
        how += ["pinned"] if isinstance(pinned, dict) and pack_id in pinned else []
        return how

    for world_id in repo.world_ids():
        world = repo.load_world(world_id)
        how = uses(world.system, world.other)
        if how:
            found.append(f"world {world.id} ({', '.join(how)})")
    for campaign_id in repo.campaign_index():
        campaign = repo.load_campaign(campaign_id)
        how = uses(campaign.system, campaign.other)
        if how:
            found.append(f"campaign {campaign.id} ({', '.join(how)})")
    return found


def active(repo: Repo, lib: PackLibrary | None = None, *, house_rules: bool = True) -> PackSet:
    """The packs in play here, each with its homebrew overlay (`systems/<pack>/homebrew/`)."""
    lib = lib or library(repo)
    wanted = enabled(repo, lib)
    if CORE not in lib.available():
        wanted.remove(CORE)
    try:
        found = lib.resolve(wanted, pins=pins(repo))
    except NotFoundError as exc:
        if not pins(repo):
            raise
        raise NotFoundError(
            _("{message} (this campaign pins its pack versions)", message=exc.message),
            hint=_("`didact campaign upgrade` moves the campaign to the versions installed now"),
        ) from exc
    from didact.services import overrides

    packs = [_with_homebrew(repo, p) for p in found.packs]
    if house_rules:
        packs = [overrides.apply(p, overrides.active(repo, p.id)) for p in packs]
    return PackSet(packs)


def pins(repo: Repo) -> dict[str, str]:
    """pack id → the version this campaign is pinned to."""
    campaign = repo.active_campaign()
    raw = campaign.other.get("pins") if campaign is not None else None
    found: dict[str, str] = {}
    for pack_id, entry in raw.items() if isinstance(raw, dict) else []:
        version = entry.get("version") if isinstance(entry, dict) else entry
        if isinstance(version, str):
            found[pack_id] = version
    return found


def pin_set(lib: PackLibrary, wanted: list[str], keep: dict[str, str]) -> dict[str, JSON]:
    """Pins for the packs `wanted` resolves to (existing pins kept): {id: {version, hash}}."""
    from didact.packs.share import content_hash

    wanted = [w for w in wanted if w != CORE or CORE in lib.available()]
    resolved = lib.resolve(wanted, pins=keep)
    return {p.id: {"version": p.version, "hash": content_hash(p)} for p in resolved.packs}


def homebrew_dir(repo: Repo, pack_id: str) -> Path:
    return repo.layout.systems_dir / pack_id / "homebrew"


def _with_homebrew(repo: Repo, pack: Pack) -> Pack:
    root = homebrew_dir(repo, pack.id)
    if not root.is_dir():
        return pack
    overlay = build_overlay(root)
    if overlay.bundle is None:
        first = overlay.errors[0]
        raise InvalidError(
            _("homebrew for {pack} has a problem: {problem}", pack=pack.id, problem=first.text()),
            where=str(root),
            hint=_("fix or remove the file (homebrew is plain YAML in the data home)"),
        )
    return pack.with_overlay(overlay.bundle, f"homebrew:{pack.id}")


def set_enabled(
    cs: Changeset, pack_id: str, *, on: bool, where: Literal["world", "campaign"]
) -> tuple[str, list[str]]:
    """Add or remove a pack in the world's or campaign's `packs` list. Returns (scope, list)."""
    repo = cs.repo
    if where == "campaign":
        campaign = repo.active_campaign()
        if campaign is None:
            raise InvalidError(
                _("no campaign is open"), hint=_("use --world, or `didact campaign open <id>`")
            )
        packs = _listed(campaign.other.get("packs"))
        packs = _toggle(packs, pack_id, on)
        campaign.other["packs"] = list[JSON](packs)
        system = campaign.system or repo.load_world(campaign.world).system
        wanted = [CORE, *([system] if system else []), *packs]
        with contextlib.suppress(DidactError):  # a pack that can't load yet keeps the old pins
            campaign.other["pins"] = pin_set(library(repo), wanted, pins(repo))
        path = repo.layout.campaign_file(campaign.world, campaign.id)
        cs.write(path, campaign_file_text(campaign, repo.read_text(path)))
        cs.mention(f"campaign:{campaign.id}")
        return f"campaign:{campaign.id}", packs
    world = repo.require_world()
    packs = _toggle(_listed(world.other.get("packs")), pack_id, on)
    world.other["packs"] = list[JSON](packs)
    path = repo.layout.world_file(world.id)
    cs.write(path, world_file_text(world, repo.read_text(path)))
    cs.mention(f"world:{world.id}")
    return f"world:{world.id}", packs


def _toggle(packs: list[str], pack_id: str, on: bool) -> list[str]:
    if on:
        return packs if pack_id in packs else [*packs, pack_id]
    return [p for p in packs if p != pack_id]
