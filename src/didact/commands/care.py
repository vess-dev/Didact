"""Keeping the library healthy: save points and forks, snapshots, sizes, continuity, the
timeline and relationship graphs."""

from typing import Annotated

from didact.commands._common import changeset, finish, open_repo
from didact.commands.registry import Metavar, command
from didact.core import labels
from didact.core.context import Context
from didact.core.errors import UsageError
from didact.core.i18n import N_, _, ngettext, pgettext, translate
from didact.core.output import JSON, Out, code
from didact.store.repo import Repo


@command(
    "save",
    summary="Make a save point in the campaign, to rewind to later (or remove one)",
    writes=True,
    examples=("didact save 'before the dragon'", "didact save --remove 'before the dragon'"),
)
def save(
    ctx: Context,
    *label: Annotated[str, "its name", Metavar("name")],
    remove: Annotated[
        str | None, "remove this save point instead (`undo` brings it back)", Metavar("save")
    ] = None,
) -> Out:
    from didact.services import savepoints

    repo = open_repo(ctx)
    if remove is not None:
        if label:
            raise UsageError(
                _("make a save point or remove one, not both"),
                hint=_("e.g. `didact save --remove 'before the dragon'`"),
            )
        cs = changeset(ctx, repo, N_("remove save point: {label}"), label=remove)
        point = savepoints.remove(cs, remove)
        cs.say(N_("remove save point: {label}"), label=point.label)
        done = _(
            "removed save point {label} (#e{event})", label=repr(point.label), event=point.event
        )
        return finish(ctx, cs, done=done, extra={"removed": point.to_data()})
    cs = changeset(ctx, repo, N_("save point: {label}"), label=" ".join(label))
    point = savepoints.save(cs, " ".join(label))
    done = _("saved {label} at #e{event}", label=repr(point.label), event=point.event)
    return finish(ctx, cs, done=done, extra={"save": point.to_data()})


@command("saves", summary="The campaign's save points", examples=("didact saves",))
def saves(ctx: Context) -> Out:
    from didact.services import savepoints

    repo = open_repo(ctx)
    found = savepoints.listing(repo)
    lines = [f"- {p.label} (#e{p.event}, {p.ts})" for p in found] or [
        _("no save points yet: `didact save '…'`")
    ]
    return Out(data={"saves": [p.to_data() for p in found]}, md="\n".join(lines))


@command(
    "rewind",
    summary="Take the campaign back to a save point (one change: undo reverses it)",
    writes=True,
    examples=("didact rewind 'before the dragon'", "didact rewind e120 --dry-run"),
    description=(
        "Puts the campaign's records and state (sheets, lists, the play state) back as they\n"
        "were at the save point, as one change you can undo. Logs stay as they are (the\n"
        "transcript, the oracle log, journals), and so does the world's canon."
    ),
)
def rewind(
    ctx: Context, *label: Annotated[str, "a save point, or an event", Metavar("save")]
) -> Out:
    from didact.services import savepoints

    repo = open_repo(ctx)
    cs = changeset(ctx, repo, N_("rewind to {label}"), label=" ".join(label))
    point, changed = savepoints.rewind(cs, " ".join(label))
    if not changed:
        return Out(
            data={"changed": []},
            md=_(
                "nothing to rewind: the campaign is as it was at {label}", label=repr(point.label)
            ),
        )
    done = ngettext(
        "rewound to {label} (#e{event}): {n} file",
        "rewound to {label} (#e{event}): {n} files",
        len(changed),
        label=repr(point.label),
        event=point.event,
    )
    return finish(ctx, cs, done=done, extra={"changed": list[JSON](changed)})


@command(
    "campaign fork",
    summary="Branch the campaign into a new one: as it is now, or as it was at a save point",
    writes=True,
    examples=(
        "didact campaign fork what-if --at 'before the dragon'",
        "didact campaign fork second-try --name 'The Withering, again'",
    ),
)
def campaign_fork(
    ctx: Context,
    new_id: Annotated[str, "the new campaign's id", Metavar("id")],
    *,
    at: Annotated[str | None, "a save point or event to branch from", Metavar("save")] = None,
    name: Annotated[str | None, "the new campaign's name", Metavar("name")] = None,
) -> Out:
    from didact.services import savepoints

    repo = open_repo(ctx)
    cs = changeset(ctx, repo, N_("fork into {campaign}"), campaign=new_id)
    fork_id, copied = savepoints.fork(cs, new_id, name, at)
    use = code(f"didact campaign open {fork_id}")
    done = ngettext(
        "forked into campaign {campaign} ({n} file); play it: {command}",
        "forked into campaign {campaign} ({n} files); play it: {command}",
        copied,
        campaign=fork_id,
        command=use,
    )
    return finish(ctx, cs, done=done, extra={"campaign": fork_id, "files": copied})


@command(
    "reset",
    summary="Empty the library, as if Didact were newly installed (shown first; backed up first)",
    examples=(
        "didact reset                 # shows what would go; changes nothing",
        "didact reset --yes",
        "didact reset --packs --yes   # the installed packs too",
    ),
    description=(
        "Every world, campaign and record goes, with the history, drafts, save points and the\n"
        "search index, and numbering starts again: the next change is #e1, the next roll #r1.\n"
        "The backups stay, and so do installed packs unless --packs. The library as it is is\n"
        "backed up first (snapshot-<time>-before-reset.zip): undo can't take a reset back, but\n"
        "restoring that backup can. Without --yes it only shows what would go."
    ),
)
def reset(
    ctx: Context,
    *,
    packs: Annotated[bool, "remove the installed packs too"] = False,
    yes: Annotated[bool, "reset it now; undo can't take it back"] = False,
) -> Out:
    from didact.services import care

    repo = open_repo(ctx)
    if not yes:
        now = care.holdings(repo)
        installed = care.installed_packs(repo)
        backups = len(care.snapshots(repo))
        again = "didact reset" + (" --packs" if packs else "") + " --yes"
        kept_backups = ngettext("{n} backup", "{n} backups", backups)
        kept_packs = ngettext(
            "{n} installed pack (`--packs` removes them too)",
            "{n} installed packs (`--packs` removes them too)",
            len(installed),
        )
        if backups and installed and not packs:
            stays = _("- stays: {backups} and {packs}", backups=kept_backups, packs=kept_packs)
        elif backups:
            stays = _("- stays: {what}", what=kept_backups)
        elif installed and not packs:
            stays = _("- stays: {what}", what=kept_packs)
        else:
            stays = _("- nothing else is kept")
        lines = [
            _("Resetting would empty the library, as if Didact were newly installed:"),
            _(
                "- goes: {holdings}, and with them every record, the journal, drafts, save "
                "points and the search index",
                holdings=now.describe(),
            ),
            *(
                [_("- the installed packs go too: {packs}", packs=", ".join(installed))]
                if installed and packs
                else []
            ),
            _("- numbering starts again: the next change is #e1, the next roll #r1"),
            stays,
            "",
            _(
                "It can't be undone, but the library as it is is backed up first "
                "(snapshot-<time>-before-reset.zip): restoring that backup brings it back. To "
                "reset: {command}.",
                command=code(again),
            ),
        ]
        data: dict[str, JSON] = {
            "preview": True,
            "now": now.to_data(),
            "packs": list[JSON](installed),
            "removes_packs": packs,
            "backups": backups,
            "next": again,
        }
        return Out(data=data, md="\n".join(lines))
    done = care.reset(repo, packs=packs)
    back = f"didact snapshot --restore {done.safety.name} --yes"
    lines = [
        _("✔ reset the library: it's as newly installed, and the next change is #e1"),
        _(
            "the library as it was is in {name}: {command} brings it back",
            name=done.safety.name,
            command=code(back),
        ),
        *(
            [_("removed the installed packs: {packs}", packs=", ".join(done.packs))]
            if done.packs
            else []
        ),
    ]
    data = {
        "reset": True,
        "before": done.before.to_data(),
        "safety": {"name": done.safety.name, "path": str(done.safety)},
        "packs_removed": list[JSON](done.packs),
    }
    return Out(data=data, md="\n".join(lines))


@command(
    "snapshot",
    summary="Back up the whole data home into one zip (backups/); list, restore or prune backups",
    examples=(
        "didact snapshot",
        "didact snapshot --list",
        "didact snapshot --restore <name>     # shows what restoring it would do",
        "didact snapshot --restore <name> --yes",
        "didact snapshot --keep 3             # deletes all but the newest three",
        "didact snapshot --remove <name>      # a name from --list",
    ),
    description=(
        "Zips the whole data home (all but its backups) into backups/. Ending a session\n"
        "makes one too (snapshot-<time>-auto.zip), and only the newest five of those stay.\n"
        "\n"
        "--restore shows what a backup holds next to the library now. With --yes it backs\n"
        "the library up as it is (snapshot-<time>-before-restore.zip), then puts the\n"
        "backup's files in place of everything but the backups. Undo can't take a restore\n"
        "back: restoring that backup can. Event and roll numbers carry on.\n"
        "\n"
        "--remove and --keep delete backups for good: they aren't part of the library's\n"
        "history, so undo can't bring them back."
    ),
)
def snapshot(
    ctx: Context,
    *,
    list_: Annotated[bool, "list the snapshots"] = False,
    restore: Annotated[
        str | None, "restore this backup (shows what it would do; --yes restores)", Metavar("name")
    ] = None,
    yes: Annotated[bool, "with --restore: restore it now (undo can't take it back)"] = False,
    remove: Annotated[str | None, "delete this backup (can't be undone)", Metavar("name")] = None,
    keep: Annotated[
        int | None, "keep the newest n backups, delete the rest (can't be undone)", Metavar("n")
    ] = None,
) -> Out:
    from didact.services import care

    if sum((list_, restore is not None, remove is not None, keep is not None)) > 1:
        raise UsageError(
            _("pick one of --list, --restore, --remove and --keep"),
            hint=_("e.g. `didact snapshot --keep 3`"),
        )
    if yes and restore is None:
        raise UsageError(
            _("--yes goes with --restore"),
            hint=_("e.g. `didact snapshot --restore <name> --yes`"),
        )
    repo = open_repo(ctx)
    if restore is not None:
        return _restore(ctx, repo, restore, yes=yes)
    if remove is not None:
        path, freed = care.remove_snapshot(repo, remove)
        return Out(
            data={"removed": [str(path)], "bytes": freed},
            md=_(
                "✔ deleted backup {name} ({size}); this can't be undone",
                name=path.name,
                size=care.human(freed),
            ),
        )
    if keep is not None:
        gone = care.keep_snapshots(repo, keep)
        left = len(care.snapshots(repo))
        if not gone:
            return Out(
                data={"removed": [], "bytes": 0, "kept": left},
                md=ngettext(
                    "nothing to delete: {n} backup, keeping up to {keep}",
                    "nothing to delete: {n} backups, keeping up to {keep}",
                    left,
                    keep=keep,
                ),
            )
        freed = sum(size for _unused, size in gone)
        names = ", ".join(path.name for path, _unused in gone)
        deleted = ngettext(
            "✔ deleted {n} backup ({size}): {names}",
            "✔ deleted {n} backups ({size}): {names}",
            len(gone),
            size=care.human(freed),
            names=names,
        )
        kept = (
            _("kept the newest {n}; this can't be undone", n=left)
            if left
            else _("no backups left; this can't be undone")
        )
        return Out(
            data={"removed": [str(p) for p, _unused in gone], "bytes": freed, "kept": left},
            md=f"{deleted}\n{kept}",
        )
    if list_:
        found = [(p, p.stat().st_size, care.kind_of(p)) for p in care.snapshots(repo)]
        lines: list[str] = []
        for path, nbytes, kind in found:
            marked = f", {translate(care.KINDS[kind])}" if kind in care.KINDS else ""
            lines.append(f"- {path.name} ({care.human(nbytes)}{marked})")
        listed: list[JSON] = [
            {"name": p.name, "path": str(p), "bytes": n, "kind": kind} for p, n, kind in found
        ]
        return Out(
            data={"snapshots": listed},
            md="\n".join(lines) or _("no snapshots yet: `didact snapshot`"),
        )
    target = care.snapshot(repo)
    size = care.human(target.stat().st_size)
    return Out(
        data={"snapshot": str(target), "bytes": target.stat().st_size},
        md=(
            _(
                "✔ snapshot {name} ({size}) in {folder}",
                name=target.name,
                size=size,
                folder=str(target.parent),
            )
            + "\n"
            + _(
                "to restore it: {command}",
                command=code(f"didact snapshot --restore {target.name}"),
            )
        ),
    )


def _restore(ctx: Context, repo: Repo, name: str, *, yes: bool) -> Out:
    """`snapshot --restore`: what restoring a backup would do, or (--yes) restore it."""
    from didact.core.clock import local_display
    from didact.services import care

    if not yes:
        backup = care.look(repo, name)
        now = care.holdings(repo)
        again = f"didact snapshot --restore {backup.path.name} --yes"
        kind = f" ({translate(care.KINDS[backup.kind])})" if backup.kind in care.KINDS else ""
        after = max(now.log.last, backup.holds.log.last)
        lines = [
            _(
                "Restoring {name} would replace everything in the library but its backups.",
                name=backup.path.name,
            ),
            _(
                "- the backup: {size}, made {made}{kind}",
                size=care.human(backup.bytes),
                made=local_display(backup.made),
                kind=kind,
            ),
            _("- it holds: {holdings}", holdings=backup.holds.describe()),
            _("- the library now: {holdings}", holdings=now.describe()),
            _(
                "- first, the library as it is now is backed up into backups/ "
                "(snapshot-<time>-before-restore.zip)"
            ),
            _(
                "- then the backup's files take the place of the library's (records, journals, "
                "the log, packs and state), and the search index is rebuilt"
            ),
            _(
                "- event and roll numbers carry on after #e{event}: a note in the restored log "
                "marks the restore",
                event=after,
            ),
            _("- undo can't take a restore back: restoring that safety backup can"),
            "",
            _("Restore it with {command}.", command=code(again)),
        ]
        data: dict[str, JSON] = {
            "preview": True,
            "backup": backup.to_data(),
            "now": now.to_data(),
            "next": again,
        }
        return Out(data=data, md="\n".join(lines))
    done = care.restore(repo, name, command=ctx.command_line)
    safety, size = done.safety, done.safety.stat().st_size
    back = f"didact snapshot --restore {safety.name} --yes"
    lines = [
        _(
            "✔ restored {name}, made {made} ({event})",
            name=done.backup.path.name,
            made=local_display(done.backup.made),
            event=done.marker.label,
        ),
        _("it holds: {holdings}", holdings=done.backup.holds.describe()),
        _(
            "the library as it was is in {name} ({size}): undo can't take a restore back, "
            "{command} can",
            name=safety.name,
            size=care.human(size),
            command=code(back),
        ),
    ]
    data = {
        "restored": done.backup.to_data(),
        "before": done.before.to_data(),
        "safety": {"name": safety.name, "path": str(safety), "bytes": size},
        "event": done.marker.seq,
    }
    return Out(data=data, md="\n".join(lines))


@command(
    "library",
    summary="What the data home holds: worlds, campaigns, packs, the log and backups, with sizes",
    examples=("didact library",),
)
def library(ctx: Context) -> Out:
    from didact.services import care

    repo = open_repo(ctx)
    sizes = care.library(repo)
    lines = [_("Data home: {path}", path=str(repo.home))]
    for size in sizes:
        indent = "  " if size.what.startswith("  ") else ""
        lines.append(
            indent
            + ngettext(
                "- {what}: {size} in {n} file",
                "- {what}: {size} in {n} files",
                size.files,
                what=labels.library_part(size.what),
                size=care.human(size.bytes),
            )
        )
    return Out(
        data={"home": str(repo.home), "parts": [s.to_data() for s in sizes]}, md="\n".join(lines)
    )


@command(
    "continuity",
    summary="What doesn't add up here: dangling links, duplicates, the dead still in play, …",
    examples=("didact continuity",),
    description=(
        "Checks dangling links, near-duplicate names, the dead or gone still in the party, a\n"
        "fight or the oracle's lists, quests gone quiet, sheets the rules would reject, and\n"
        "summaries still to write. Each finding comes with the command that fixes it."
    ),
)
def continuity(ctx: Context) -> Out:
    from didact.services import continuity as checks

    repo = open_repo(ctx)
    issues = checks.check(repo)
    if not issues:
        return Out(data={"issues": []}, md=_("✔ nothing to fix: the library adds up"))
    lines = [ngettext("{n} thing to look at:", "{n} things to look at:", len(issues))]
    for issue in issues:
        lines.append(f"- [{_issue_kind(issue.kind)}] {issue.text}")
        lines.append(_("  fix: `{command}`", command=issue.fix))
    return Out(data={"issues": [i.to_data() for i in issues]}, md="\n".join(lines))


def _issue_kind(kind: str) -> str:
    """A continuity finding's kind as shown (the data keeps the English key)."""
    return {
        "dangling link": pgettext("continuity", "dangling link"),
        "near duplicate": pgettext("continuity", "near duplicate"),
        "gone but in play": pgettext("continuity", "gone but in play"),
        "gone quiet": pgettext("continuity", "gone quiet"),
        "sheet": pgettext("continuity", "sheet"),
        "summary": pgettext("continuity", "summary"),
    }.get(kind, kind)


@command(
    "timeline",
    summary="The campaign by in-game date: every journal beat under the day it happened",
    examples=("didact timeline",),
)
def timeline(ctx: Context) -> Out:
    from didact.services import story

    repo = open_repo(ctx)
    days = story.timeline(repo)
    lines: list[str] = []
    rows: list[JSON] = []
    scene = labels.type_inline("scene")
    for number, date, beats in days:
        day = _("day {n} · {date}", n=number, date=date) if date else _("day {n}", n=number)
        lines.append(f"## {day}")
        lines += [f"- {b.text} ({b.where(scene)})" for b in beats]
        english = f"day {number} · {date}" if date else f"day {number}"
        rows.append({"day": english, "beats": [f"{b.text} ({b.where()})" for b in beats]})
    return Out(data={"days": rows}, md="\n".join(lines) or _("nothing in the journal yet"))


@command(
    "graph",
    summary="Who and what a record is connected to, as a Mermaid graph",
    examples=("didact graph sweeney", "didact graph faction:the-order --depth 2"),
)
def graph(
    ctx: Context,
    ref: Annotated[str, "the record", Metavar("record")],
    *,
    depth: Annotated[int, "how many steps out", Metavar("n")] = 1,
    gm: Annotated[bool, "secrets too"] = False,
) -> Out:
    from didact.services import care

    repo = open_repo(ctx)
    lines = care.graph(repo, ref, depth, gm=gm)
    return Out(data={"mermaid": "\n".join(lines)}, md="```mermaid\n" + "\n".join(lines) + "\n```")
