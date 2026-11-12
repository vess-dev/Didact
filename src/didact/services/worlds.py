"""Creating and deleting worlds and campaigns."""

import secrets
from dataclasses import dataclass, field
from pathlib import Path

from didact.core.clock import now_iso
from didact.core.errors import ConflictError, InvalidError
from didact.core.i18n import _, ngettext
from didact.core.ids import check_name_id
from didact.core.output import JSON
from didact.store.changeset import Changeset
from didact.store.repo import (
    CampaignInfo,
    Repo,
    WorldInfo,
    campaign_file_text,
    world_file_text,
)


def create_world(
    changeset: Changeset,
    world_id: str,
    *,
    name: str | None,
    system: str | None,
    description: str,
    seed: str | None = None,
) -> WorldInfo:
    repo = changeset.repo
    check_name_id(world_id, "world")
    if system:
        check_name_id(system, "system")
    if world_id in repo.world_ids():
        raise ConflictError(
            _("world {world} already exists", world=repr(world_id)),
            hint=_("switch to it with `didact world use {world}`", world=world_id),
        )
    world = WorldInfo(
        id=world_id,
        name=name or world_id.replace("-", " ").title(),
        system=system,
        description=description,
        created=now_iso(),
        other={"seed": seed or secrets.token_hex(8)},  # dice streams; see didact.services.dice
    )
    changeset.write(repo.layout.world_file(world_id), world_file_text(world))
    changeset.mention(f"world:{world_id}")
    return world


def create_campaign(
    changeset: Changeset,
    campaign_id: str,
    *,
    world_id: str,
    name: str | None,
    description: str,
    pins: dict[str, JSON] | None = None,
    seed: str | None = None,
    start: dict[str, JSON] | None = None,
) -> CampaignInfo:
    """A new campaign in a world: it plays the world's game system, from the calendar's start
    or from a date of its own (`start`: `{year, month, day}`)."""
    repo = changeset.repo
    check_name_id(campaign_id, "campaign")
    repo.load_world(world_id)
    existing = repo.campaign_index()
    if campaign_id in existing:
        raise ConflictError(
            _(
                "campaign {campaign} already exists (in world {world})",
                campaign=repr(campaign_id),
                world=repr(existing[campaign_id]),
            ),
            hint=_("campaign ids are unique across the library; choose another id"),
        )
    campaign = CampaignInfo(
        id=campaign_id,
        world=world_id,
        name=name or campaign_id.replace("-", " ").title(),
        description=description,
        created=now_iso(),
        other={"seed": seed or secrets.token_hex(8)},  # dice streams; see didact.services.dice
    )
    if pins:
        campaign.other["pins"] = pins  # the exact pack versions this campaign plays with
    if start:
        campaign.other["start"] = start  # its first day (see didact.services.clock)
    changeset.write(repo.layout.campaign_file(world_id, campaign_id), campaign_file_text(campaign))
    changeset.mention(f"campaign:{campaign_id}")
    return campaign


# ---------------------------------------------------------------------------- deleting

JUNK = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})  # OS clutter, not game data
NOT_RECORDS = frozenset({"session", "scene", "journal", "state", "transcripts", "views"})


@dataclass(slots=True)
class Removal:
    """What deleting a world or a campaign takes with it."""

    folder: Path
    files: list[Path] = field(default_factory=list)  # text: deleted through the changeset
    junk: list[Path] = field(default_factory=list)  # OS clutter: swept afterwards
    records: int = 0
    campaigns: list[str] = field(default_factory=list)
    sessions: int = 0

    def line(self, what: str) -> str:
        parts = [ngettext("{n} record", "{n} records", self.records)]
        if self.campaigns:
            parts.append(
                ngettext(
                    "{n} campaign ({names})",
                    "{n} campaigns ({names})",
                    len(self.campaigns),
                    names=", ".join(self.campaigns),
                )
            )
        if self.sessions:
            parts.append(ngettext("{n} session", "{n} sessions", self.sessions))
        files = ngettext("{n} file", "{n} files", len(self.files))
        return _("{what}: {parts}; {files}", what=what, parts=", ".join(parts), files=files)


def plan_removal(repo: Repo, folder: Path) -> Removal:
    """Every file under a world's or campaign's folder. Anything that isn't text (besides OS
    clutter) stops it: the delete couldn't be undone."""
    removal = Removal(folder)
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        if path.name in JUNK:
            removal.junk.append(path)
            continue
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise InvalidError(
                _(
                    "{path} isn't text, so deleting it couldn't be undone",
                    path=repo.layout.rel(path),
                ),
                hint=_("move it out of the folder first"),
            ) from None
        removal.files.append(path)
        if path.suffix == ".md" and path.parent.name == "session":
            removal.sessions += 1
        elif path.suffix == ".md" and path.parent.name not in NOT_RECORDS:
            removal.records += 1
        if path.name == "campaign.yaml" and path.parent != folder:  # a world's campaigns
            removal.campaigns.append(path.parent.name)
    return removal


def sweep(removal: Removal) -> None:
    """After the delete: OS clutter and the folders left empty."""
    for path in removal.junk:
        path.unlink(missing_ok=True)
    folders = sorted(
        (p for p in removal.folder.rglob("*") if p.is_dir()), key=lambda p: -len(p.parts)
    )
    for folder in [*folders, removal.folder]:
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
