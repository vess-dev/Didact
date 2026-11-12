"""The library: init, status, worlds, campaigns, and upkeep (validate, reindex, export, migrate)."""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

from didact.commands._common import (
    changeset,
    finish,
    headline,
    open_repo,
    render_record,
    scope_list,
)
from didact.commands.registry import Metavar, command
from didact.core import labels
from didact.core.context import Context
from didact.core.errors import InvalidError, NotFoundError
from didact.core.i18n import N_, _, ngettext, pgettext
from didact.core.ids import Scope
from didact.core.output import JSON, Out, code
from didact.services.worlds import create_campaign, create_world
from didact.store.layout import SCHEMA_VERSION
from didact.store.repo import Repo, State, parse_entity

if TYPE_CHECKING:
    from didact.services.worlds import Removal
    from didact.store.changeset import Changeset


@command(
    "init",
    summary="Create the data home (safe to run again)",
    examples=("didact init", "didact init --home ~/Games/Didact"),
)
def init(ctx: Context) -> Out:
    repo = open_repo(ctx)
    created = repo.init()
    said = (
        _("data home created: {path}", path=str(repo.home))
        if created
        else _("data home already set up: {path}", path=str(repo.home))
    )
    after = _("next: {command}", command=code("didact world new <id> --system <pack>"))
    return Out(data={"home": str(repo.home), "created": created}, md=f"{said}\n{after}")


@command(
    "status",
    summary="Show the active world and campaign, the visible scopes and the last change",
    examples=("didact status",),
)
def status(ctx: Context) -> Out:
    repo = open_repo(ctx)
    if not repo.initialized():
        return Out(
            data={"home": str(repo.home), "initialized": False},
            md=_(
                "no data home at {path} yet → {command}",
                path=str(repo.home),
                command=code("didact init"),
            ),
        )
    world = repo.active_world()
    campaign = repo.active_campaign()
    chain = repo.chain()
    counts = {str(s): len(repo.index().rows([s])) for s in chain}
    last = repo.log.last_seq()
    lines = [
        _("home: {path}", path=str(repo.home)),
        _(
            "world: {world}",
            world=headline("world:" + world.id, world.name, world.system or _("no system")),
        )
        if world
        else _("world: (none)"),
        _("campaign: {campaign} · {name}", campaign=campaign.id, name=campaign.name)
        if campaign
        else _("campaign: (none)"),
        _("visible: {scopes}", scopes=", ".join(f"{s} ({n})" for s, n in counts.items())),
        _("last change: #e{event}", event=last) if last else _("last change: (none yet)"),
    ]
    data: dict[str, JSON] = {
        "home": str(repo.home),
        "world": world.id if world else None,
        "campaign": campaign.id if campaign else None,
        "scopes": [str(s) for s in chain],
        "counts": dict(counts),
        "last_event": last,
    }
    return Out(data=data, md="\n".join(lines))


# ---------------------------------------------------------------------------- worlds


@command(
    "world new",
    summary="Create a world (and make it active)",
    writes=True,
    examples=(
        "didact world new vale --name Vale --system my-system",
        'didact world new drowned-coast --description "Fog, frog knights and a haunted lighthouse"',
        "didact world new fenmoor --system my-system --gen pointcrawl "
        '--prefill \'{"terrain": "Swamp", "size": 5}\'',
    ),
)
def world_new(
    ctx: Context,
    world_id: Annotated[str, "short id, e.g. `vale` (lowercase, digits, dashes)"],
    *,
    name: Annotated[str | None, "display name (default: from the id)"] = None,
    system: Annotated[
        str | None, "the game system it plays, for good (its campaigns too), e.g. `my-system`"
    ] = None,
    description: Annotated[str, "a line or paragraph about the setting"] = "",
    seed: Annotated[str | None, "fix the dice streams (same seed, same rolls)"] = None,
    gen: Annotated[str | None, "fill it with a generator (describe it, get it)"] = None,
    prefill: Annotated[str | None, "what the description decided, as JSON (with --gen)"] = None,
    no_use: Annotated[bool, "don't switch to the new world"] = False,
) -> Out:
    repo = open_repo(ctx)
    repo.require_init()
    if gen and (no_use or ctx.dry_run):
        raise InvalidError(
            _("--gen fills the new world: it can't go with --no-use or --dry-run"),
            hint=_("drop them, or make the world first and then `didact gen run … --auto` in it"),
        )
    if prefill and not gen:
        raise InvalidError(
            _("--prefill goes with --gen"), hint=_("e.g. --gen my-system.pointcrawl")
        )
    cs = changeset(ctx, repo, N_("create world {world}"), world=world_id)
    world = create_world(cs, world_id, name=name, system=system, description=description, seed=seed)
    out = finish(
        ctx,
        cs,
        done=_("world {world} · {name} created", world=world.id, name=world.name),
        extra={"world": world.id},
        notes=_missing_pack_note(repo, system),
    )
    if not ctx.dry_run and not no_use:
        repo.save_state(State(world=world.id, campaign=None))
        out = Out(data=out.data, md=out.md + "\n" + _("active world: {world}", world=world.id))
    if gen:
        return _generate_world(ctx, out, gen, prefill)
    return out


def _generate_world(ctx: Context, created: Out, gen: str, prefill: str | None) -> Out:
    """The second half of `world new --gen`: run the generator and commit what it made."""
    from didact.commands._common import parse_data
    from didact.services import drafts

    repo = open_repo(ctx)  # opened again: the new world is active now
    given = parse_data(prefill, "--prefill") or {}
    cs = changeset(ctx, repo, N_("generate the world with {generator}"), generator=gen)
    stored, ids = drafts.generate(cs, gen, given, dry=False, command=ctx.command_line)
    done = ngettext(
        "{n} record from {source}", "{n} records from {source}", len(ids), source=stored.source
    )
    out = finish(ctx, cs, done=done, extra={"records": list[JSON](ids)})
    lines = [created.md, out.md, *drafts.lines(repo, stored)[1:-1]]
    return Out(data={**created.data, **out.data}, md="\n".join(lines), ok=out.ok)


def _pins_for(repo: Repo, system: str | None, world_packs: JSON) -> dict[str, JSON] | None:
    """Pack versions to pin a new campaign to (None when the packs can't load yet)."""
    from didact.core.errors import DidactError
    from didact.services.packs import CORE, library, pin_set

    extra = [str(p) for p in world_packs] if isinstance(world_packs, list) else []
    try:
        return pin_set(library(repo), [CORE, *([system] if system else []), *extra], {})
    except DidactError:
        return None


def _missing_pack_note(repo: Repo, system: str | None) -> list[str]:
    from didact.packs.share import shipped
    from didact.services.packs import library

    if system and system not in library(repo).available():
        how = (
            f"`didact pack install {system}`"
            if any(s.id == system for s in shipped())
            else "`didact pack list`"
        )
        return [
            _("no pack {pack} is installed yet: rules need it ({how})", pack=repr(system), how=how)
        ]
    return []


@command("world list", summary="List worlds", examples=("didact world list",))
def world_list(ctx: Context) -> Out:
    repo = open_repo(ctx)
    active = repo.state().world
    worlds = [repo.load_world(w) for w in repo.world_ids()]
    if not worlds:
        return Out(
            data={"worlds": []},
            md=_("no worlds yet → {command}", command=code("didact world new <id>")),
        )
    lines = [
        f"- {w.id} · {w.name}"
        + (f" ({w.system})" if w.system else "")
        + ("  " + _("← active") if w.id == active else "")
        for w in worlds
    ]
    data: dict[str, JSON] = {"worlds": [w.meta() for w in worlds], "active": active}
    return Out(data=data, md="\n".join([ngettext("{n} world", "{n} worlds", len(worlds)), *lines]))


@command("world use", summary="Make a world active", examples=("didact world use vale",))
def world_use(ctx: Context, world_id: Annotated[str, "the world's id"]) -> Out:
    repo = open_repo(ctx)
    world = repo.load_world(world_id)
    state = repo.state()
    keep_campaign = (
        state.campaign
        if state.campaign and repo.campaign_index().get(state.campaign) == world.id
        else None
    )
    repo.save_state(State(schema=state.schema, world=world.id, campaign=keep_campaign))
    return Out(
        data={"world": world.id, "campaign": keep_campaign},
        md=_("active world: {world} · {name}", world=world.id, name=world.name),
    )


@command(
    "world export",
    summary="Make a world into a setting pack, to use again in other worlds or share",
    writes=True,
    examples=(
        "didact world export --as setting",
        "didact world export vale --id vale-setting --name 'The Vale'",
        "didact world export --secrets --campaigns --dir ./vale-setting",
    ),
    description=(
        "Writes a setting pack for the world's system: its people, places, things, factions\n"
        "and quests as compendium entries (`compendium import <pack>` brings them into another\n"
        "world), its lore entries as pack lore, and its calendar. It's what the players know:\n"
        "secret records, secret sections and fields, and the GM's notes stay out unless\n"
        "--secrets (which marks a secret record secret again on import). The campaigns' own\n"
        "records stay out unless --campaigns; characters and play bookkeeping (sessions,\n"
        "scenes, journals) always do. It goes into the library's packs, or --dir. The pack\n"
        "isn't marked as shareable: set its licence in pack.yaml before `pack export`."
    ),
)
def world_export(
    ctx: Context,
    world_id: Annotated[str | None, "the world (default: the active one)"] = None,
    *,
    as_: Annotated[Literal["setting"], "what to make: a setting pack"] = "setting",
    id_: Annotated[str | None, "the pack's id (default: <world>-setting)"] = None,
    name: Annotated[str | None, "the pack's name (default: the world's)"] = None,
    dir_: Annotated[str | None, "where (default: the library's packs folder)"] = None,
    secrets: Annotated[bool, "secret records, sections and fields, and the GM's notes too"] = False,
    campaigns: Annotated[bool, "the records the world's campaigns hold too"] = False,
) -> Out:
    from didact.commands._common import made_pack
    from didact.core.ids import check_name_id
    from didact.services import knowledge, packing, packs

    repo = open_repo(ctx)
    world = repo.load_world(world_id) if world_id else repo.require_world()
    if not world.system:
        raise InvalidError(
            _("world {world} has no system yet: a setting belongs to one", world=world.id),
            hint=_("give it one: `didact world set system=<pack>`"),
        )
    pack_id = check_name_id(id_ or f"{world.id}-setting", "pack")
    scopes = repo.world_family(world.id) if campaigns else [Scope("world", world.id)]
    entities = packing.records(repo, scopes, secrets=secrets)
    packing.need_content(entities, None, f"world:{world.id}")
    root = (
        Path(dir_).expanduser() if dir_ else packs.library(repo).installed_dir / pack_id / "0.1.0"
    )
    packing.check_folder(root)
    if ctx.dry_run:
        return Out(
            data={"dry_run": True, "path": str(root), "records": len(entities)},
            md=_("dry run: would create {pack} in {path}", pack=pack_id, path=root),
        )
    about = world.description if secrets else knowledge.player_body(world.description)[0]
    manifest: dict[str, JSON] = {
        "id": pack_id,
        "name": name or world.name,
        "kind": "setting",
        "version": "0.1.0",
        "description": " ".join(about.split()),
        "requires": {"didact": ">=0.1", "packs": ["core", world.system]},
        "license": {"spdx": "", "redistributable": False, "attribution": ""},
    }
    calendar = world.other.get("calendar")
    if isinstance(calendar, dict):
        manifest["settings"] = {"calendar": calendar}
    guide = packing.guide(
        name or world.name,
        " ".join(about.split()) or f"The world {world.name}, as a setting for {world.system}.",
        [
            f"`didact world new <id> --system {world.system}`, "
            f"then `didact pack enable {pack_id}`.",
            f"`didact compendium import {pack_id}` brings its records into the world.",
            "Its lore comes up in play by itself; its calendar is the world's.",
        ],
    )
    made = packing.write(root, manifest, guide, repo, entities, secrets=secrets)
    return made_pack(pack_id, made)


@command(
    "world show",
    summary="Show a world (default: the active one)",
    examples=("didact world show", "didact world show --gm"),
)
def world_show(
    ctx: Context,
    world_id: Annotated[str | None, "the world's id"] = None,
    *,
    gm: Annotated[bool, "the description's secret sections too"] = False,
) -> Out:
    from didact.services import knowledge

    repo = open_repo(ctx)
    world = repo.load_world(world_id) if world_id else repo.require_world()
    described = world.description if gm else knowledge.player_body(world.description)[0].strip()
    campaigns = sorted(c for c, w in repo.campaign_index().items() if w == world.id)
    counts: dict[str, int] = {}
    for row in repo.index().rows([Scope("world", world.id)]):
        counts[row.type] = counts.get(row.type, 0) + 1
    lines = [f"world:{world.id} · {world.name}"]
    if world.system:
        lines.append(_("system: {system}", system=world.system))
    if described:
        lines.append(_("description: {text}", text=described))
    lines.append(
        _("campaigns: {campaigns}", campaigns=", ".join(campaigns))
        if campaigns
        else _("campaigns: (none)")
    )
    lines.append(
        _(
            "records: {counts}",
            counts=", ".join(
                f"{labels.inline(t, labels.type_plural(t))} {n}" for t, n in sorted(counts.items())
            ),
        )
        if counts
        else _("records: (none)")
    )
    data: dict[str, JSON] = {**world.meta(), "campaigns": list(campaigns), "counts": dict(counts)}
    data["description"] = described
    return Out(data=data, md="\n".join(lines))


# ---------------------------------------------------------------------------- campaigns


@command(
    "campaign new",
    summary="Start a campaign in a world, playing its game system (and open it)",
    writes=True,
    examples=(
        "didact campaign new withering --name 'The Withering'",
        "didact campaign new run-2 --world vale",
        "didact campaign new long-ago --date '14 March 1890'",
    ),
)
def campaign_new(
    ctx: Context,
    campaign_id: Annotated[str, "short id, unique across the library"],
    *,
    name: Annotated[str | None, "display name"] = None,
    description: Annotated[str, "premise or pitch"] = "",
    seed: Annotated[str | None, "fix the dice streams (same seed, same rolls)"] = None,
    date: Annotated[
        str | None,
        "the date it opens on, as the calendar writes one (default: the calendar's start)",
        Metavar("date"),
    ] = None,
    no_use: Annotated[bool, "don't open the new campaign"] = False,
) -> Out:
    repo = open_repo(ctx)
    world = repo.require_world()
    start: dict[str, JSON] | None = None
    opens: list[str] = []
    if date:
        from didact.services import timeline

        alone = Repo(ctx.config, world=world.id, no_campaign=True)  # the packs it will have
        try:  # (not those of a campaign open now)
            cal = timeline.calendar(alone)
        finally:
            alone.close()
        cal.start_at(*cal.read_date(date))
        start = cal.first_day()
        weekday = cal.weekday_note(date, 0)  # the date decides; a day of the week that isn't its
        opens = [_("it's {time}", time=cal.describe(0)), *([weekday] if weekday else [])]
    cs = changeset(
        ctx, repo, N_("create campaign {campaign} in {world}"), campaign=campaign_id, world=world.id
    )
    campaign = create_campaign(
        cs,
        campaign_id,
        world_id=world.id,
        name=name,
        description=description,
        pins=_pins_for(repo, world.system, world.other.get("packs")),
        seed=seed,
        start=start,
    )
    out = finish(
        ctx,
        cs,
        done=_(
            "campaign {campaign} · {name} created in world {world}",
            campaign=campaign.id,
            name=campaign.name,
            world=world.id,
        ),
        notes=[
            *_missing_pack_note(repo, world.system),
            *opens,
            _("next: `didact session zero` (the questions to settle with the player)"),
        ],
    )
    if not ctx.dry_run and not no_use:
        repo.save_state(State(world=world.id, campaign=campaign.id))
        out = Out(
            data=out.data, md=out.md + "\n" + _("open campaign: {campaign}", campaign=campaign.id)
        )
    return out


@command("campaign list", summary="List campaigns (all worlds)", examples=("didact campaign list",))
def campaign_list(ctx: Context) -> Out:
    repo = open_repo(ctx)
    active = repo.state().campaign
    campaigns = [repo.load_campaign(c) for c in sorted(repo.campaign_index())]
    if not campaigns:
        return Out(
            data={"campaigns": []},
            md=_("no campaigns yet → {command}", command=code("didact campaign new <id>")),
        )
    lines = [
        _("- {campaign} · {name} (world {world})", campaign=c.id, name=c.name, world=c.world)
        + ("  " + _("← active") if c.id == active else "")
        for c in campaigns
    ]
    data: dict[str, JSON] = {"campaigns": [c.meta() for c in campaigns], "active": active}
    return Out(
        data=data,
        md="\n".join([ngettext("{n} campaign", "{n} campaigns", len(campaigns)), *lines]),
    )


@command(
    "campaign open",
    summary="Open a campaign to play it: its world opens too, and its game system is in use",
    examples=("didact campaign open withering",),
)
def campaign_open(ctx: Context, campaign_id: Annotated[str, "the campaign's id"]) -> Out:
    repo = open_repo(ctx)
    campaign = repo.load_campaign(campaign_id)
    world = repo.load_world(campaign.world)
    system = campaign.system or world.system  # a campaign of old may have its own
    repo.save_state(State(schema=repo.state().schema, world=campaign.world, campaign=campaign.id))
    return Out(
        data={"world": campaign.world, "campaign": campaign.id, "system": system},
        md=_(
            "open campaign: {campaign} · {name} (world {world}, {system})",
            campaign=campaign.id,
            name=campaign.name,
            world=campaign.world,
            system=system or pgettext("system", "no system"),
        ),
    )


@command(
    "campaign close",
    summary="Close the open campaign (its world stays open); open it again to play on",
    examples=("didact campaign close",),
    description=(
        "Nothing of the campaign changes: a session under way is still under way when it's\n"
        "opened again. With no campaign open, commands work on the world alone."
    ),
)
def campaign_close(ctx: Context) -> Out:
    from didact.services import play

    repo = open_repo(ctx)
    campaign = repo.active_campaign()
    if campaign is None:
        return Out(data={"campaign": None, "changed": False}, md=_("no campaign is open"))
    under_way = play.load(repo).session_open
    state = repo.state()
    repo.save_state(State(schema=state.schema, world=campaign.world, campaign=None))
    lines = [
        _(
            "closed campaign {campaign} · {name} (world {world} stays open)",
            campaign=campaign.id,
            name=campaign.name,
            world=campaign.world,
        )
    ]
    if under_way:
        lines.append(_("its session is still under way: it goes on when the campaign opens"))
    lines.append(_("open it again: {command}", command=code(f"didact campaign open {campaign.id}")))
    data: dict[str, JSON] = {"world": campaign.world, "campaign": None, "closed": campaign.id}
    return Out(data=data, md="\n".join(lines))


@command(
    "campaign show",
    summary="Show a campaign (default: the active one)",
    examples=("didact campaign show",),
)
def campaign_show(
    ctx: Context,
    campaign_id: Annotated[str | None, "the campaign's id"] = None,
    *,
    gm: Annotated[bool, "the description's secret sections too"] = False,
) -> Out:
    from didact.services import knowledge

    repo = open_repo(ctx)
    campaign = repo.load_campaign(campaign_id) if campaign_id else repo.active_campaign()
    if campaign is None:
        raise InvalidError(
            _("no campaign is open"),
            hint=_("open one: `didact campaign open <id>` (or start one: `campaign new <id>`)"),
        )
    lines = [
        f"campaign:{campaign.id} · {campaign.name}",
        _("world: {world}", world=campaign.world),
    ]
    system = campaign.system or repo.load_world(campaign.world).system
    if system:
        lines.append(_("system: {system}", system=system))
    described = (
        campaign.description if gm else knowledge.player_body(campaign.description)[0].strip()
    )
    if described:
        lines.append(_("description: {text}", text=described))
    return Out(data={**campaign.meta(), "description": described}, md="\n".join(lines))


@command(
    "world delete",
    summary="Delete a world with its records and campaigns (previewed first; undoable)",
    writes=True,
    examples=("didact world delete old-vale", "didact world delete old-vale --yes"),
    description=(
        "Everything in the world goes: its records, maps, lore and every campaign in it\n"
        "(sessions, journals, transcripts, oracle state). Without --yes it shows what would\n"
        "go and stages the change for `didact apply <id>`. `didact undo` brings it all back,\n"
        "byte for byte. The event log keeps its history either way."
    ),
)
def world_delete(
    ctx: Context,
    world_id: Annotated[str, "the world's id"],
    *,
    yes: Annotated[bool, "delete now, without the preview step"] = False,
) -> Out:
    from didact.services import worlds

    repo = open_repo(ctx)
    repo.require_init()
    world = repo.load_world(world_id)
    removal = worlds.plan_removal(repo, repo.layout.world_dir(world.id))
    cs = changeset(ctx, repo, N_("delete world {world}"), world=world.id)
    for path in removal.files:
        cs.delete(path)
    done = _("deleted world {world}", world=world.id)
    holds = _("world {world} holds", world=world.id)
    return _deleted(ctx, repo, cs, removal, done, holds, yes=yes)


@command(
    "campaign delete",
    summary="Delete a campaign: its PCs, sessions, journal and state (previewed first; undoable)",
    writes=True,
    examples=("didact campaign delete test-run", "didact campaign delete test-run --yes"),
    description=(
        "The world and its records stay; the campaign's own records, sessions, journal,\n"
        "transcripts, oracle state and save points go. Without --yes it shows what would go\n"
        "and stages the change for `didact apply <id>`. `didact undo` brings it all back."
    ),
)
def campaign_delete(
    ctx: Context,
    campaign_id: Annotated[str, "the campaign's id"],
    *,
    yes: Annotated[bool, "delete now, without the preview step"] = False,
) -> Out:
    from didact.services import worlds

    repo = open_repo(ctx)
    repo.require_init()
    campaign = repo.load_campaign(campaign_id)
    folder = repo.layout.campaign_dir(campaign.world, campaign.id)
    removal = worlds.plan_removal(repo, folder)
    cs = changeset(
        ctx,
        repo,
        N_("delete campaign {campaign} (world {world})"),
        campaign=campaign.id,
        world=campaign.world,
    )
    for path in removal.files:
        cs.delete(path)
    done = _("deleted campaign {campaign}", campaign=campaign.id)
    holds = _("campaign {campaign} holds", campaign=campaign.id)
    return _deleted(ctx, repo, cs, removal, done, holds, yes=yes)


def _deleted(
    ctx: Context, repo: Repo, cs: Changeset, removal: Removal, done: str, holds: str, *, yes: bool
) -> Out:
    """Finish a delete: preview or stage it, or apply it and tidy up after."""
    from didact.services import worlds

    extra: dict[str, JSON] = {
        "records": removal.records,
        "campaigns": list[JSON](removal.campaigns),
        "sessions": removal.sessions,
        "file_count": len(removal.files),
    }
    out = finish(
        ctx, cs, done=done, review=True, yes=yes, extra=extra,
        notes=[removal.line(holds)],
    )  # fmt: skip
    if isinstance(out.data, dict) and "event" in out.data:
        worlds.sweep(removal)
        _forget_active(repo)
        out = Out(data=out.data, md=out.md + "\n" + _("`didact undo` brings it back"))
    return out


def _forget_active(repo: Repo) -> None:
    """After a delete, the active world or campaign may be gone: then nothing is active."""
    state = repo.state()
    campaign = state.campaign if state.campaign in repo.campaign_index() else None
    world = state.world if state.world in repo.world_ids() else None
    if (world, campaign) != (state.world, state.campaign):
        repo.save_state(State(schema=state.schema, world=world, campaign=campaign))


# ---------------------------------------------------------------------------- upkeep


@command(
    "validate",
    summary="Check every record for problems (bad YAML, id/file mismatches, dangling links)",
    examples=("didact validate", "didact validate --format json"),
)
def validate(ctx: Context) -> Out:
    repo = open_repo(ctx)
    index = repo.index()
    problems: list[dict[str, JSON]] = [
        {"path": path, "problem": message} for path, message in index.broken()
    ]
    rows = index.rows(include_archived=True)
    known = {r.id for r in rows}
    aliases: set[str] = set()
    for row in rows:
        row_aliases = row.data.get("aliases")
        if isinstance(row_aliases, list):
            aliases.update(a for a in row_aliases if isinstance(a, str))
    seen: dict[tuple[str, str], str] = {}
    for row in rows:
        key = (str(row.scope), row.id)
        if key in seen:
            problems.append(
                {
                    "path": row.path,
                    "problem": _("duplicate id {id} in {scope}", id=row.id, scope=str(row.scope)),
                }
            )
        seen[key] = row.path
        row_links = row.data.get("links")
        for link in row_links if isinstance(row_links, list) else []:
            if isinstance(link, dict):
                target = str(link.get("to", "")).partition("@")[0]
                if target not in known and target not in aliases:
                    problems.append(
                        {"path": row.path, "problem": _("link to missing record {id}", id=target)}
                    )
    if not problems:
        return Out(
            data={"ok": True, "problems": []},
            md=ngettext("✔ {n} record(s), no problems", "✔ {n} record(s), no problems", len(rows)),
        )
    lines = [
        ngettext(
            "{n} problem(s) in {records}:",
            "{n} problem(s) in {records}:",
            len(problems),
            records=ngettext("{n} record(s)", "{n} record(s)", len(rows)),
        )
    ]
    lines += [f"- {p['path']}: {p['problem']}" for p in problems]
    return Out(data={"ok": False, "problems": list(problems)}, md="\n".join(lines), ok=False)


@command(
    "reindex",
    summary="Rebuild the search index from the files (safe any time)",
    examples=("didact reindex",),
)
def reindex(ctx: Context) -> Out:
    repo = open_repo(ctx)
    index = repo.index()
    index.clear()
    report = index.sync(repo.entity_files(), parse_entity)
    said = ngettext("✔ reindexed {n} record(s)", "✔ reindexed {n} record(s)", report.updated)
    if report.broken:
        said = ngettext(
            "✔ reindexed {records}; {n} broken file(s): see `didact validate`",
            "✔ reindexed {records}; {n} broken file(s): see `didact validate`",
            len(report.broken),
            records=ngettext("{n} record(s)", "{n} record(s)", report.updated),
        )
    return Out(data={"indexed": report.updated, "broken": len(report.broken)}, md=said)


@command(
    "cache show",
    summary="Didact's disposable caches: where they are and how much they hold",
    examples=("didact cache show",),
    description=(
        "Search indexes (one per library) and compiled packs. None of it is the truth, and\n"
        "`didact cache clear` deletes it all; it's rebuilt as needed."
    ),
)
def cache_show(ctx: Context) -> Out:
    from didact.services import cache

    found = cache.parts(ctx.config)
    lines = [_("cache folder: {path}", path=str(ctx.config.cache))]
    lines += [
        f"- {labels.cache_part(part.kind)}: {part.count}, {cache.size_text(part.size)}"
        for part in found
    ]
    total = sum(part.size for part in found)
    lines.append(
        _("total: {size} (`didact cache clear` deletes it all)", size=cache.size_text(total))
    )
    data: dict[str, JSON] = {
        "folder": str(ctx.config.cache),
        "parts": [{"kind": part.kind, "count": part.count, "bytes": part.size} for part in found],
        "bytes": total,
    }
    return Out(data=data, md="\n".join(lines))


@command(
    "cache clear",
    summary="Delete Didact's caches (search indexes, compiled packs); they're rebuilt as needed",
    writes=True,
    examples=("didact cache clear", "didact cache clear --dry-run"),
    description=(
        "Safe any time: your library's files are the truth. The next command rebuilds the\n"
        "search index of the library it opens, and packs recompile as they load. It touches\n"
        "nothing else: not the library, not other files in the cache folder, and not what\n"
        "`pack build` wrote into a pack's `.build/` folder. For the developer caches in a\n"
        "checkout of Didact (mypy, ruff, pytest, pack builds), use `make clean`."
    ),
)
def cache_clear(ctx: Context) -> Out:
    from didact.services import cache

    found = cache.parts(ctx.config) if ctx.dry_run else cache.clear(ctx.config)
    files = sum(len(part.files) for part in found)
    head = (
        ngettext(
            "dry run: would delete {n} cached file", "dry run: would delete {n} cached files", files
        )
        if ctx.dry_run
        else ngettext("✔ deleted {n} cached file", "✔ deleted {n} cached files", files)
    )
    lines = [
        head,
        *(f"- {labels.cache_part(part.kind)}: {part.count}" for part in found if part.files),
    ]
    data: dict[str, JSON] = {
        "deleted": 0 if ctx.dry_run else files,
        "parts": {part.kind: part.count for part in found},
    }
    return Out(data=data, md="\n".join(lines))


@command(
    "export",
    summary="Export records as JSON or Markdown, the campaign as a story, or a player-safe website",
    examples=(
        "didact export",
        "didact export --scope world:vale --as md --to vale.md",
        "didact export --scope all --to backup.json",
        "didact export --as story --to withering.md",
        "didact export --as lonelog --to withering.log.md",
        "didact export --as site --to ~/Desktop/withering-site",
        "didact export --as site --lang fr --to ~/Desktop/withering-site",
    ),
    description=(
        "json and md hold every record, secrets too: for backups and tools. story is the\n"
        "campaign as a readable book; lonelog is its journal in Lonelog notation (@ ? d: -> =>,\n"
        "scenes as S1, tags like [N:Tom]), player-safe like the story. site writes a folder of\n"
        "web pages about what the players know, to share with them or read on a phone: open\n"
        "its index.html (no server, network or JavaScript needed). It holds the party, a page\n"
        "per record they know, the journal and the map, and it's always player-safe: no secret\n"
        "records, sections, fields or beats, no GM notes and no transcript. --to is required\n"
        "and must be a new or empty folder, or one an earlier site export wrote: exporting\n"
        "again replaces the files it wrote there, and nothing else."
    ),
)
def export(
    ctx: Context,
    *,
    scope: Annotated[
        str | None, "a scope, or `all` (default: the active world and its campaigns)"
    ] = None,
    as_: Annotated[
        Literal["json", "md", "story", "lonelog", "site"],
        "json, md, story (the campaign as a readable book), lonelog (its journal in Lonelog "
        "notation) or site (a player-safe website)",
    ] = "json",
    to: Annotated[str | None, "write to this file instead of printing (site: a folder)"] = None,
    lang: Annotated[
        str | None,
        "the language of a site, story or lonelog export's own words (fr, pt-BR, …); "
        "English by default",
    ] = None,
) -> Out:
    from didact.core import i18n

    code = _export_language(lang)
    repo = open_repo(ctx)
    if as_ == "site":
        return _site(repo, scope, to, code)
    if as_ == "story":
        from didact.services import story

        with i18n.use(code):
            book = story.book(repo)
        return _deliver(book, to)
    if as_ == "lonelog":
        from didact.services import lonelog

        with i18n.use(code):
            journal = lonelog.document(repo)
        return _deliver(journal, to, journal=True)
    if scope == "all":
        scopes = repo.all_scopes()
    elif scope:
        scopes = [repo.check_scope(Scope.parse(scope))]
    else:
        scopes = repo.world_family(repo.require_world().id)
    rows = repo.index().rows(scopes, include_archived=True)
    if as_ == "json":
        document = json.dumps(
            {
                "scopes": [str(s) for s in scopes],
                "records": [{"scope": str(r.scope), **r.data} for r in rows],
            },
            ensure_ascii=False,
            indent=2,
        )
    else:
        parts = [f"# Didact export ({scope_list(scopes)})"]
        for row in rows:
            entity = parse_entity((repo.home / row.path).read_text(encoding="utf-8"), row.path)
            parts.append("## " + render_record(entity, row.scope, full=True))
        document = "\n\n".join(parts) + "\n"
    if to:
        target = Path(to).expanduser()
        target.write_text(document, encoding="utf-8")
        return Out(
            data={"file": str(target), "records": len(rows)},
            md=ngettext(
                "✔ exported {n} record(s) to {path}",
                "✔ exported {n} record(s) to {path}",
                len(rows),
                path=str(target),
            ),
        )
    return Out(data={"document": document, "records": len(rows)}, md=document)


def _export_language(lang: str | None) -> str:
    """The language code `--lang` names (English when it's not given)."""
    from didact.core import i18n
    from didact.core.errors import UsageError

    if lang is None:
        return i18n.DEFAULT
    code = i18n.chosen(lang)
    if code == i18n.DEFAULT and lang.strip().casefold().replace("_", "-").split("-")[0] != "en":
        tags = ", ".join(known.tag for known in i18n.LANGUAGES.values())
        raise UsageError(
            _("unknown language {name}", name=repr(lang)), hint=_("use one of: {tags}", tags=tags)
        )
    return code


def _deliver(document: str, to: str | None, *, journal: bool = False) -> Out:
    """The story (or the Lonelog journal): written to `to`, or printed."""
    if to:
        target = Path(to).expanduser()
        target.write_text(document, encoding="utf-8")
        done = (
            _("✔ exported the journal to {path}", path=str(target))
            if journal
            else _("✔ exported the story to {path}", path=str(target))
        )
        return Out(data={"file": str(target)}, md=done)
    return Out(data={"document": document}, md=document)


def _site(repo: Repo, scope: str | None, to: str | None, language: str) -> Out:
    """`export --as site`: what the players know, as web pages in a folder (in `language`;
    what the command says stays in the command line's language)."""
    from didact.core import i18n
    from didact.core.errors import UsageError
    from didact.services import site

    if not to:
        raise UsageError(
            _("a site is a folder of pages: say where with --to"),
            hint=_("e.g. `didact export --as site --to ~/Desktop/vale-site`"),
        )
    if scope:
        raise UsageError(
            _("--scope doesn't go with --as site"),
            hint=_(
                "the site shows the active world and campaign (`--campaign <id>` picks another)"
            ),
        )
    with i18n.use(language):
        done = site.export(repo, Path(to))
    index = done.folder / "index.html"
    lines = [
        ngettext(
            "✔ exported the site to {folder}: {n} page",
            "✔ exported the site to {folder}: {n} pages",
            done.pages,
            folder=str(done.folder),
        ),
        _("open {path}", path=str(index)),
    ]
    if done.removed:
        lines.append(
            ngettext(
                "note: removed {n} file the last export wrote",
                "note: removed {n} files the last export wrote",
                done.removed,
            )
        )
    data: dict[str, JSON] = {
        "folder": str(done.folder),
        "index": str(index),
        "pages": done.pages,
        "files": done.files,
        "records": done.records,
        "removed": done.removed,
    }
    return Out(data=data, md="\n".join(lines))


@command(
    "migrate",
    summary="Upgrade an older data home to the current layout",
    examples=("didact migrate",),
)
def migrate(ctx: Context) -> Out:
    repo = open_repo(ctx)
    if not repo.initialized():
        raise NotFoundError(
            _("no data home at {path}", path=str(repo.home)), hint=_("run `didact init`")
        )
    state = repo.state()
    if state.schema > SCHEMA_VERSION:
        raise InvalidError(
            _(
                "this data home uses layout v{found}, newer than this Didact (v{known})",
                found=state.schema,
                known=SCHEMA_VERSION,
            ),
            hint=_("upgrade Didact"),
        )
    if state.schema == SCHEMA_VERSION:
        return Out(
            data={"schema": state.schema, "migrated": False},
            md=_("✔ up to date (layout v{version})", version=state.schema),
        )
    # Future layouts add step functions here, applied in order, each through a changeset.
    repo.save_state(State(schema=SCHEMA_VERSION, world=state.world, campaign=state.campaign))
    return Out(
        data={"schema": SCHEMA_VERSION, "migrated": True},
        md=_("✔ migrated to layout v{version}", version=SCHEMA_VERSION),
    )
