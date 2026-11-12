"""Administration: rename, replace, bulk set, merge, copy/move/promote, staging, history, undo."""

from typing import Annotated

from didact.commands._common import changeset, finish, open_repo
from didact.commands.registry import Metavar, command
from didact.core import labels
from didact.core.clock import local_display
from didact.core.context import Context
from didact.core.errors import InvalidError, NotFoundError, UsageError
from didact.core.i18n import N_, _, ngettext
from didact.core.ids import EntityId, Scope
from didact.core.output import JSON, Out, code
from didact.core.phrases import shown as shown_phrase
from didact.services import admin, assign
from didact.store import changeset as changesets
from didact.store.changeset import Changeset, describe_change
from didact.store.events import SAY, Cleared, Event, shown, undone_seqs
from didact.store.repo import Located, Repo


def _target_scopes(ctx: Context, scope: list[str] | None) -> list[Scope]:
    repo = open_repo(ctx)
    if scope:
        if scope == ["all"]:
            return repo.all_scopes()
        return [repo.check_scope(Scope.parse(s)) for s in scope]
    return repo.world_family(repo.require_world().id)


# ---------------------------------------------------------------------------- rename


@command(
    "rename",
    summary="Rename a record, world or campaign (old name kept as an alias); optionally everywhere",
    writes=True,
    examples=(
        "didact rename npc:tom 'Tomas the Grey'",
        "didact rename npc:tom 'Tomas the Grey' --reslug",
        "didact rename world:vale Valemark --rewrite-text",
    ),
)
def rename(
    ctx: Context,
    ref: Annotated[str, "the record (or world:<id> / campaign:<id>)"],
    new_name: Annotated[str, "the new name"],
    *,
    reslug: Annotated[bool, "also change the id to match, rewriting every reference"] = False,
    rewrite_text: Annotated[bool, "also replace the old name in text across the world"] = False,
    yes: Annotated[bool, "apply without the preview step"] = False,
) -> Out:
    repo = open_repo(ctx)
    kind, sep, rest = ref.partition(":")
    if sep and rest and kind in ("world", "campaign"):  # these prefixes are never record types
        container_id = rest
        cs = changeset(
            ctx,
            repo,
            N_("rename {kind} {id} → {name}"),
            kind=kind,
            id=container_id,
            name=new_name,
        )
        old_name = admin.rename_container(cs, kind, container_id, new_name)
        scopes: list[Scope] = []
        if rewrite_text and old_name != new_name:
            world_id = container_id if kind == "world" else repo.load_campaign(container_id).world
            scopes = (
                repo.world_family(world_id)
                if kind == "world"
                else [Scope("campaign", container_id)]
            )
            admin.replace_text(cs, old_name, new_name, scopes=scopes, whole_word=True)
        return finish(
            ctx,
            cs,
            done=_(
                "{kind} {id}: {old} → {new}",
                kind=labels.inline(kind, labels.scope_name(kind)),
                id=container_id,
                old=old_name,
                new=new_name,
            ),
            review=rewrite_text,
            yes=yes,
        )
    located = repo.resolve(ref)
    world = repo.active_world()
    text_scopes = repo.world_family(world.id) if world else [located.scope]
    cs = changeset(ctx, repo, N_("rename {id} → {name}"), id=str(located.entity.id), name=new_name)
    new_id = admin.rename(
        cs, located, new_name, reslug=reslug, rewrite_text=rewrite_text, text_scopes=text_scopes
    )
    touches_others = any(f.path != repo.layout.rel(located.path) for f in cs.files) and (
        reslug or rewrite_text
    )
    return finish(
        ctx,
        cs,
        done=(
            _(
                "renamed {id} → {name} ({new_id})",
                id=located.entity.id,
                name=new_name,
                new_id=new_id,
            )
            if new_id != located.entity.id
            else _("renamed {id} → {name}", id=located.entity.id, name=new_name)
        ),
        review=touches_others,
        yes=yes,
        extra={"id": str(new_id)},
    )


# ---------------------------------------------------------------------------- replace / bulk


@command(
    "replace",
    summary="Replace text in names, bodies and fields across records (previewed first)",
    writes=True,
    examples=(
        "didact replace 'the Wood' 'the Thornveil'",
        "didact replace Vale Valemark --word --yes",
        "didact replace 'Order of (Nine|9)' 'Order of Nine' --regex --scope world:vale",
    ),
)
def replace(
    ctx: Context,
    old: Annotated[str, "text (or --regex pattern) to find"],
    new: Annotated[str, "replacement text"],
    *,
    scope: Annotated[
        list[str] | None, "limit to this scope, or `all` (default: active world + its campaigns)"
    ] = None,
    type_: Annotated[list[str] | None, "only records of this type"] = None,
    regex: Annotated[bool, "treat OLD as a regular expression"] = False,
    ignore_case: Annotated[bool, "match regardless of case"] = False,
    word: Annotated[bool, "match whole words only"] = False,
    yes: Annotated[bool, "apply without the preview step"] = False,
) -> Out:
    repo = open_repo(ctx)
    scopes = _target_scopes(ctx, scope)
    cs = changeset(ctx, repo, N_("replace {old} → {new}"), old=repr(old), new=repr(new))
    stats = admin.replace_text(
        cs,
        old,
        new,
        scopes=scopes,
        types=type_ or [],
        regex=regex,
        ignore_case=ignore_case,
        whole_word=word,
    )
    return finish(
        ctx,
        cs,
        done=_(
            "replaced {count} occurrence(s) in {files} file(s)",
            count=stats.replacements,
            files=len(stats.per_file),
        ),
        review=True,
        yes=yes,
        extra={"replacements": stats.replacements, "per_file": dict(stats.per_file)},
    )


@command(
    "bulk set",
    summary="Apply assignments to every record matching --where conditions (previewed first)",
    writes=True,
    examples=(
        "didact bulk set status=hostile --where type=npc --where tag=goblin",
        "didact bulk set disposition=wary --where fields.faction~=crimson --yes",
    ),
)
def bulk_set(
    ctx: Context,
    *assignments: Annotated[str, "key=value, key+=value or key-=value"],
    where: Annotated[
        list[str] | None, "condition: key=value, key!=value or key~=text (repeatable, AND)"
    ] = None,
    unset: Annotated[list[str] | None, "remove this key"] = None,
    scope: Annotated[
        list[str] | None, "limit to this scope, or `all` (default: active world + campaigns)"
    ] = None,
    yes: Annotated[bool, "apply without the preview step"] = False,
) -> Out:
    if not where:
        raise InvalidError(
            _("bulk set needs at least one --where"), hint=_("e.g. `--where type=npc`")
        )
    if not assignments and not unset:
        raise InvalidError(_("nothing to set"), hint=_("e.g. `status=hostile`"))
    conditions = [admin.parse_condition(w) for w in where]
    parsed = [assign.parse_assignment(a) for a in assignments]
    repo = open_repo(ctx)
    scopes = _target_scopes(ctx, scope)
    cs = changeset(
        ctx,
        repo,
        N_("bulk set {changes} where {conditions}"),
        changes=" ".join(assignments),
        conditions=" and ".join(where),
    )
    matched = admin.bulk_set(
        cs, scopes=scopes, conditions=conditions, assignments=parsed, unsets=unset or []
    )
    if not matched:
        return Out(data={"matched": []}, md=_("no records match those conditions"))
    return finish(
        ctx,
        cs,
        done=_(
            "updated {changed} of {matched} matching record(s)",
            changed=len(cs.files),
            matched=len(matched),
        ),
        review=True,
        yes=yes,
        extra={"matched": list(matched)},
    )


# ---------------------------------------------------------------------------- merge / copy / move


@command(
    "merge",
    summary="Fold a duplicate record into another and point every reference at the survivor",
    writes=True,
    examples=("didact merge npc:sweeny npc:sweeney", "didact merge 'Old Tom' npc:tom --yes"),
)
def merge(
    ctx: Context,
    duplicate: Annotated[str, "the record that goes away"],
    keep: Annotated[str, "the record that stays"],
    *,
    yes: Annotated[bool, "apply without the preview step"] = False,
) -> Out:
    repo = open_repo(ctx)
    dup = repo.resolve(duplicate)
    kept = repo.resolve(keep)
    cs = changeset(
        ctx, repo, N_("merge {id} into {into}"), id=str(dup.entity.id), into=str(kept.entity.id)
    )
    conflicts, left = admin.merge(cs, dup, kept)
    notes = (
        [_("kept {id}'s value for: {keys}", id=kept.entity.id, keys=", ".join(conflicts))]
        if conflicts
        else []
    )
    if left:  # a merge across types: what the survivor's sheet has no field for stays out
        notes.append(
            _(
                "left out what a {type} has no field for: {values}",
                type=kept.entity.type,
                values=", ".join(left),
            )
        )
    return finish(
        ctx,
        cs,
        done=_("merged {duplicate} into {kept}", duplicate=dup.entity.id, kept=kept.entity.id),
        review=True,
        yes=yes,
        notes=notes,
        extra={"conflicts": list(conflicts), "left_out": list[JSON](left)},
    )


@command(
    "copy",
    summary="Copy a record into another scope (e.g. an NPC into another world)",
    writes=True,
    examples=(
        "didact copy npc:tom --to world:drowned-coast",
        "didact copy npc:tom --to world:vale --id tom-twin",
    ),
)
def copy_(
    ctx: Context,
    ref: Annotated[str, "the record"],
    *,
    to: Annotated[str, "target scope"],
    id_: Annotated[str | None, "new slug for the copy"] = None,
) -> Out:
    repo = open_repo(ctx)
    located = repo.resolve(ref)
    target = Scope.parse(to)
    cs = changeset(
        ctx, repo, N_("copy {id} to {scope}"), id=str(located.entity.id), scope=str(target)
    )
    new_id = admin.copy_to(cs, located, target, id_)
    return finish(
        ctx,
        cs,
        done=_(
            "copied {id} to {target} as {new_id}",
            id=located.entity.id,
            target=target,
            new_id=new_id,
        ),
    )


@command(
    "move",
    summary="Move a record to another scope (same id)",
    writes=True,
    examples=("didact move npc:tom --to world:vale", "didact move lore:prophecy --to global"),
)
def move(
    ctx: Context, ref: Annotated[str, "the record"], *, to: Annotated[str, "target scope"]
) -> Out:
    repo = open_repo(ctx)
    located = repo.resolve(ref)
    target = Scope.parse(to)
    cs = changeset(
        ctx,
        repo,
        N_("move {id} from {scope} to {target}"),
        id=str(located.entity.id),
        scope=str(located.scope),
        target=str(target),
    )
    admin.move_to(cs, located, target)
    return finish(ctx, cs, done=_("moved {id} to {target}", id=located.entity.id, target=target))


@command(
    "promote",
    summary="Move a record one scope wider: campaign → world → global",
    writes=True,
    examples=("didact promote npc:tom", "didact promote npc:tom --to global"),
)
def promote(
    ctx: Context,
    ref: Annotated[str, "the record"],
    *,
    to: Annotated[str | None, "target scope (default: the next wider one)"] = None,
) -> Out:
    repo = open_repo(ctx)
    located = repo.resolve(ref)
    target = Scope.parse(to) if to else admin.promotion_target(repo, located.scope)
    cs = changeset(
        ctx,
        repo,
        N_("promote {id} from {scope} to {target}"),
        id=str(located.entity.id),
        scope=str(located.scope),
        target=str(target),
    )
    admin.move_to(cs, located, target)
    return finish(ctx, cs, done=_("promoted {id} to {target}", id=located.entity.id, target=target))


# ---------------------------------------------------------------------------- staging


@command(
    "apply",
    summary="Apply a staged changeset (from a preview)",
    writes=True,
    examples=("didact apply x3f9a2c1",),
)
def apply(ctx: Context, change_id: Annotated[str, "the staged changeset id"]) -> Out:
    repo = open_repo(ctx)
    cs = Changeset.load_staged(repo, change_id)
    if ctx.reason:
        cs.reason = ctx.reason
    out = finish(ctx, cs, done=shown_phrase(cs.phrase, cs.summary))
    if not ctx.dry_run:
        (repo.layout.staging_dir / f"{change_id.lstrip('#')}.json").unlink(missing_ok=True)
    return out


@command("discard", summary="Throw away a staged changeset", examples=("didact discard x3f9a2c1",))
def discard(ctx: Context, change_id: Annotated[str, "the staged changeset id"]) -> Out:
    repo = open_repo(ctx)
    path = repo.layout.staging_dir / f"{change_id.lstrip('#')}.json"
    if not path.exists():
        raise NotFoundError(
            _("no staged changeset {change}", change=repr(change_id)),
            hint=_("see `didact staged`"),
        )
    path.unlink()
    return Out(data={"discarded": change_id}, md=_("✔ discarded {change}", change=change_id))


@command(
    "staged",
    summary="List staged changesets waiting for `didact apply`",
    examples=("didact staged",),
)
def staged(ctx: Context) -> Out:
    repo = open_repo(ctx)
    directory = repo.layout.staging_dir
    items = sorted(directory.glob("*.json")) if directory.exists() else []
    lines = [ngettext("{n} staged changeset", "{n} staged changesets", len(items))]
    data: list[JSON] = []
    for path in items:
        cs = Changeset.load_staged(repo, path.stem)
        lines.append(
            _(
                "- {id}: {summary} ({files} file(s))",
                id=code(path.stem),
                summary=shown_phrase(cs.phrase, cs.summary),
                files=len(cs.files),
            )
        )
        data.append({"id": path.stem, "summary": cs.summary, "files": len(cs.files)})
    return Out(data={"staged": data}, md="\n".join(lines))


# ---------------------------------------------------------------------------- history / undo


def _event_line(event: Event, undone: set[int]) -> str:
    mark = " " + _("(undone)") if event.seq in undone else ""
    reason = " " + _("— reason: {reason}", reason=event.reason) if event.reason else ""
    forced = " " + _("[forced]") if event.forced else ""
    return f"- {event.label} {local_display(event.ts)} {shown(event)}{forced}{reason}{mark}"


def _event_data(event: Event, undone: set[int]) -> dict[str, JSON]:
    return {
        "seq": event.seq,
        "ts": event.ts,
        "kind": event.kind,
        "summary": event.summary,
        "say": event.data.get(SAY),  # the summary as a phrase, to show in any language
        "command": event.command,
        "reason": event.reason,
        "forced": event.forced,
        "undone": event.seq in undone,
        "entities": list(event.entities),
        "files": [{"path": f.path, "action": f.action} for f in event.files],
    }


@command(
    "history",
    summary="List changes, newest first (optionally for one record), or clear old history",
    examples=(
        "didact history",
        "didact history npc:tom",
        "didact history --limit 50",
        "didact history --clear                # shows what would go; changes nothing",
        "didact history --clear --before e120 --yes",
    ),
    description=(
        "Lists changes, newest first; rolls are in `didact rolls`.\n"
        "\n"
        "`--clear` drops old history from the log, to shrink it and to be rid of deleted\n"
        "records for good: every change and undo with its file snapshots, or with --before\n"
        "only those before that event. Rolls and notes stay unless --rolls. Undo, redo, diff,\n"
        "rewind and fork stop working for what went, and save points older than it are\n"
        "removed. Event and roll numbers carry on. Without --yes it only shows what would go.\n"
        "It can't be undone: `didact snapshot` first."
    ),
)
def history(
    ctx: Context,
    ref: Annotated[str | None, "only changes touching this record"] = None,
    *,
    limit: Annotated[int, "how many"] = 20,
    clear: Annotated[bool, "drop old history from the log (a preview; --yes clears)"] = False,
    before: Annotated[
        str | None, "with --clear: only events before this one", Metavar("event")
    ] = None,
    rolls: Annotated[bool, "with --clear: rolls and notes too (the dice record)"] = False,
    yes: Annotated[bool, "with --clear: clear it now; this can't be undone"] = False,
) -> Out:
    if clear or before is not None or rolls or yes:
        return _clear_history(ctx, ref, clear=clear, before=before, rolls=rolls, yes=yes)
    repo = open_repo(ctx)
    events = repo.log.all()
    undone = undone_seqs(events)
    events = [e for e in events if e.kind != "roll"]  # rolls: `didact rolls`
    if ref:
        wanted = ref if EntityId.looks_like(ref) else str(repo.resolve(ref).entity.id)
        events = [e for e in events if wanted in e.entities]
    chosen = list(reversed(events))[:limit]
    if not chosen:
        return Out(data={"events": []}, md=_("no changes yet"))
    lines = [ngettext("{n} change, newest first:", "{n} changes, newest first:", len(chosen))]
    lines += [_event_line(e, undone) for e in chosen]
    return Out(data={"events": [_event_data(e, undone) for e in chosen]}, md="\n".join(lines))


def _clear_history(
    ctx: Context, ref: str | None, *, clear: bool, before: str | None, rolls: bool, yes: bool
) -> Out:
    """`history --clear`: show what would go, or (--yes) rewrite the log without it."""
    import shlex

    from didact.services import history as histories
    from didact.services.care import human

    if not clear:
        raise UsageError(
            _("--before, --rolls and --yes go with --clear"),
            hint=_("e.g. `didact history --clear --before e120`"),
        )
    if ref:
        raise UsageError(
            _("--clear clears the whole library's history, not one record's"),
            hint=_("leave out the record: `didact history --clear`"),
        )
    repo = open_repo(ctx)
    cut = histories.parse_cut(before) if before is not None else None
    found = histories.plan(repo, before=cut, rolls=rolls)
    span = (
        _("before #e{event}", event=found.cut)
        if cut is not None
        else _("up to #e{event}", event=found.last)
    )
    if found.nothing:
        if rolls or not found.kept:
            md = _("nothing to clear {span}", span=span) if found.last else _("nothing to clear")
        else:
            md = _(
                "nothing to clear: no changes {span}, only rolls and notes (`--rolls`)", span=span
            )
        return Out(
            data={"events": 0, "before": found.cut, "rolls": rolls, "kept": found.kept}, md=md
        )
    data: dict[str, JSON] = {
        "events": found.events,
        "bytes": found.bytes,
        "log_bytes": found.size,
        "before": found.cut,
        "rolls": rolls,
        "changes": found.changes,
        "dice": found.dice,
        "kept": found.kept,
        "saves": [p.to_data() for p in found.saves],
    }
    if not yes:
        argv = ["didact", "history", "--clear"]
        argv += ["--before", f"e{found.cut}"] if cut is not None else []
        argv += ["--rolls", "--yes"] if rolls else ["--yes"]
        goes: list[str] = []
        if found.changes:
            goes.append(
                ngettext(
                    "{n} change or undo with their file snapshots (deleted records too)",
                    "{n} changes and undos with their file snapshots (deleted records too)",
                    found.changes,
                )
            )
        if found.dice:
            goes.append(ngettext("{n} roll or note", "{n} rolls and notes", found.dice))
        lines = [
            ngettext(
                "Clearing would drop {n} event {span}: {part} of the log's {whole}.",
                "Clearing would drop {n} events {span}: {part} of the log's {whole}.",
                found.events,
                span=span,
                part=human(found.bytes),
                whole=human(found.size),
            ),
            _("- goes: {items}", items="; ".join(goes)),
        ]
        if found.kept:
            lines.append(
                ngettext(
                    "- stays: {n} roll or note, the dice record (`--rolls` clears them too)",
                    "- stays: {n} rolls and notes, the dice record (`--rolls` clears them too)",
                    found.kept,
                )
            )
        if found.changes:
            back = (
                _("- `rewind` and `campaign fork --at` can't go back to any earlier point")
                if found.horizon > found.last
                else _(
                    "- `rewind` and `campaign fork --at` can't go back further than #e{event}",
                    event=found.horizon - 1,
                )
            )
            lines += [
                _("- stops working for those changes: undo, redo, `diff`, and `undo --turn`"),
                back,
            ]
        if found.dice:
            lines.append(
                _(
                    "- `rolls`, `replay` and the roll lines in `session show` lose those rolls "
                    "(the journal's beats stay)"
                )
            )
        saves = [f"{p.point.label!r} ({p.where}, #e{p.point.event})" for p in found.saves]
        lines.append(
            _("- save points removed: {saves}", saves=", ".join(saves))
            if saves
            else _("- no save point is lost")
        )
        lines += [
            "",
            _(
                "It can't be undone: back up first with {snapshot}, then clear it with {command}.",
                snapshot=code("didact snapshot"),
                command=code(shlex.join(argv)),
            ),
        ]
        data |= {"preview": True, "next": shlex.join(argv)}
        return Out(data=data, md="\n".join(lines))
    done = histories.clear(repo, before=cut, rolls=rolls, command=ctx.command_line)
    if done is None:  # cleared by someone else in the meantime
        return Out(
            data={"events": 0, "before": found.cut, "rolls": rolls}, md=_("nothing to clear")
        )
    found = done.plan
    data |= {
        "events": found.events,
        "bytes": found.bytes,
        "log_bytes": done.size,
        "event": done.marker.seq,
        "saves": [p.to_data() for p in done.saves],
        "saves_event": done.saves_event.seq if done.saves_event else None,
    }
    lines = [
        ngettext(
            "✔ cleared {n} event {span} ({size}); the log is now {left} ({event})",
            "✔ cleared {n} events {span} ({size}); the log is now {left} ({event})",
            found.events,
            span=span,
            size=human(found.bytes),
            left=human(done.size),
            event=done.marker.label,
        )
    ]
    if found.kept:
        lines.append(
            ngettext(
                "kept: {n} roll or note {span}, the dice record",
                "kept: {n} rolls and notes {span}, the dice record",
                found.kept,
                span=span,
            )
        )
    if done.saves:
        removed = ", ".join(f"{p.point.label!r} ({p.where})" for p in done.saves)
        lines.append(
            _(
                "save points removed ({event}): {removed}",
                event=done.saves_event.label,
                removed=removed,
            )
            if done.saves_event
            else _("save points removed: {removed}", removed=removed)
        )
    lines.append(_("This can't be undone."))
    return Out(data=data, md="\n".join(lines))


HOUSE_RULES = ("override ", "schema extend ")


def _find_event(repo: Repo, text: str) -> Event:
    """`e12`, `#e12` or `12` is event 12; `r7` or `#r7` is the event that logged roll 7."""
    cleaned = text.strip().lstrip("#").lower()
    kind, digits = (cleaned[0], cleaned[1:]) if cleaned[:1] in ("e", "r") else ("e", cleaned)
    if not digits.isdigit():
        raise InvalidError(
            _("invalid event {event}", event=repr(text)),
            hint=_("events look like `e12` (a change) or `r7` (a roll)"),
        )
    if kind == "r":
        from didact.services.dice import find_roll

        return find_roll(repo, int(digits))
    return repo.log.get(int(digits))


@command(
    "diff",
    summary="Show exactly what one change did",
    examples=("didact diff e12", "didact diff 12 --detail full"),
)
def diff(ctx: Context, event: Annotated[str, "the event, e.g. e12"]) -> Out:
    repo = open_repo(ctx)
    found = _find_event(repo, event)
    lines = [f"{found.label} {found.ts} {shown(found)}"]
    if found.command:
        lines.append(_("command: {command}", command=found.command))
    if found.reason:
        lines.append(_("reason: {reason}", reason=found.reason))
    for change in found.files:
        lines.extend(describe_change(change, full=ctx.detail == "full"))
    undone = undone_seqs(repo.log.all())
    return Out(data=_event_data(found, undone), md="\n".join(lines))


@command(
    "audit",
    summary="List changes that bent the rules or carried a reason (forced, fiat, undo)",
    examples=("didact audit",),
)
def audit(ctx: Context, *, limit: Annotated[int, "how many"] = 50) -> Out:
    repo = open_repo(ctx)
    events = repo.log.all()
    undone = undone_seqs(events)
    flagged = [
        e
        for e in reversed(events)
        if e.kind != "roll"
        and (
            e.forced
            or e.reason
            or e.kind == "undo"
            or e.summary.startswith(HOUSE_RULES)
            or Cleared.of(e) is not None  # the history was cleared here
        )
    ][:limit]
    if not flagged:
        return Out(
            data={"events": []}, md=_("nothing to audit: no forced, explained or undone changes")
        )
    lines = [ngettext("{n} flagged change:", "{n} flagged changes:", len(flagged))]
    lines += [_event_line(e, undone) for e in flagged]
    return Out(data={"events": [_event_data(e, undone) for e in flagged]}, md="\n".join(lines))


@command(
    "undo",
    summary="Undo the last change(s), restoring files exactly; a roll; a whole turn; or "
    "everything after a point",
    writes=True,
    examples=(
        "didact undo",
        "didact undo --steps 3",
        "didact undo --event e12",
        "didact undo --event r7 --reason 'rolled the wrong die'",
        "didact undo --turn                   # everything done for the last player message",
        "didact undo --event t5               # that turn",
        "didact undo --to e40 --dry-run       # jump back: what everything after #e40 is",
        "didact undo --to e40                 # and take it all back",
    ),
    description=(
        "`--to` jumps back to a point in the history: every change after it that is still in\n"
        "effect is undone, newest first, and the rolls after it are marked undone. Each is\n"
        "logged as an undo, so nothing is lost: `redo`, or jumping back to a later point,\n"
        "brings them back. It's checked against the files first: it goes through whole or\n"
        "not at all."
    ),
)
def undo(
    ctx: Context,
    *,
    steps: Annotated[int, "how many changes to undo"] = 1,
    event: Annotated[
        str | None, "undo this change (e12), roll (r7) or turn (t5)", Metavar("event")
    ] = None,
    turn: Annotated[bool, "take back the latest turn: its changes and rolls"] = False,
    to: Annotated[
        str | None, "jump back to this event (e40): take back everything after it", Metavar("event")
    ] = None,
    force: Annotated[bool, "undo even if later changes touched the same files"] = False,
) -> Out:
    repo = open_repo(ctx)
    if to is not None:
        if event is not None or turn:
            raise UsageError(
                _("--to goes alone: it takes back everything after an event"),
                hint=_("`didact undo --to e40`, or `didact undo --event e40` for that change"),
            )
        return _undo_to(ctx, repo, to, force)
    if turn or (event is not None and event.strip().lstrip("#").lower().startswith("t")):
        return _undo_turn(ctx, repo, event if not turn else None, force)
    targets = [_find_event(repo, event)] if event else changesets.undoable(repo)[:steps]
    if targets and targets[0].kind == "roll":
        return _undo_roll(ctx, repo, targets[0])
    if not targets:
        return Out(data={"undone": []}, md=_("nothing to undo"))
    if ctx.dry_run:
        lines = [_("dry run: would undo {events}", events=", ".join(t.label for t in targets))]
        for target in targets:
            lines.append(f"- {target.label} {shown(target)}")
        return Out(data={"dry_run": True, "events": [t.seq for t in targets]}, md="\n".join(lines))
    done: list[Event] = []
    for target in targets:
        done.append(
            changesets.undo(repo, target, force=force, reason=ctx.reason, command=ctx.command_line)
        )
    lines = [
        _("✔ undid {event} ({summary}) as {undo}", event=t.label, summary=shown(t), undo=d.label)
        for t, d in zip(targets, done, strict=True)
    ]
    return Out(
        data={"undone": [t.seq for t in targets], "events": [d.seq for d in done]},
        md="\n".join(lines),
    )


def _undo_turn(ctx: Context, repo: Repo, turn: str | None, force: bool) -> Out:
    from didact.services import turns
    from didact.services.dice import void_roll

    found = turns.group(repo, turn.strip().lstrip("#") if turn else None)
    labels = [e.label for e in found.changes] + [f"#r{e.data.get('roll')}" for e in found.rolls]
    if ctx.dry_run:
        lines = [
            _(
                "dry run: would take back turn {turn}: {events}",
                turn=found.turn,
                events=", ".join(labels),
            )
        ]
        lines += [f"- {e.label} {shown(e)}" for e in [*found.changes, *found.rolls]]
        return Out(data={"dry_run": True, "turn": found.turn}, md="\n".join(lines))
    reason = ctx.reason or f"take back turn {found.turn}"
    done: list[Event] = []
    for target in found.changes:  # newest first, so each undo finds its own `after`
        done.append(
            changesets.undo(repo, target, force=force, reason=reason, command=ctx.command_line)
        )
    for target in found.rolls:
        done.append(void_roll(repo, target, reason=reason, command=ctx.command_line))
    lines = [
        _(
            "✔ took back turn {turn}: {changes}, {rolls}",
            turn=found.turn,
            changes=ngettext("{n} change", "{n} changes", len(found.changes)),
            rolls=ngettext("{n} roll", "{n} rolls", len(found.rolls)),
        )
    ]
    lines += [
        _("- undid {event} {summary}", event=e.label, summary=shown(e)) for e in found.changes
    ]
    lines += [_("- marked #r{roll} undone", roll=e.data.get("roll")) for e in found.rolls]
    data: dict[str, JSON] = {
        "turn": found.turn,
        "undone": [e.seq for e in [*found.changes, *found.rolls]],
        "events": [d.seq for d in done],
    }
    return Out(data=data, md="\n".join(lines))


def _undo_to(ctx: Context, repo: Repo, to: str, force: bool) -> Out:
    """Jump back: take back every step after an event (`services/jumpback.py`)."""
    from didact.services import jumpback

    point = _find_event(repo, to)
    found = jumpback.plan(repo, point)
    steps: list[JSON] = [_event_data(e, set()) for e in found.steps]
    at = _event_data(point, set())
    if not found.steps:
        return Out(
            data={"to": point.seq, "point": at, "undone": [], "events": [], "steps": steps},
            md=_(
                "nothing to take back: nothing after {event} is still in effect", event=point.label
            ),
        )
    jumpback.check(repo, found, force=force)
    counts = [
        ngettext("{n} change", "{n} changes", len(found.changes)) if found.changes else "",
        ngettext("{n} roll", "{n} rolls", len(found.rolls) + len(found.marks))
        if found.rolls or found.marks
        else "",
    ]
    what = (
        _("{first} and {second}", first=counts[0], second=counts[1])
        if all(counts)
        else (counts[0] or counts[1])
    )
    lines = [
        _("dry run: would jump back to {event}, taking back {what}:", event=point.label, what=what)
        if ctx.dry_run
        else _("✔ jumped back to {event}: took back {what}", event=point.label, what=what)
    ]
    if ctx.dry_run:
        lines += [f"- {step.label} {shown(step)}" for step in found.steps]
        data: dict[str, JSON] = {"dry_run": True, "to": point.seq, "point": at, "steps": steps}
        return Out(data=data, md="\n".join(lines))
    for step in found.steps:
        if step.kind == "roll":
            lines.append(_("- marked #r{roll} undone", roll=step.data.get("roll")))
        elif not step.files:
            roll, stands = found.marked.get(step.seq, (0, True))
            lines.append(
                _("- #r{roll} stands again", roll=roll)
                if stands
                else _("- marked #r{roll} undone", roll=roll)
            )
        else:
            lines.append(_("- undid {event} {summary}", event=step.label, summary=shown(step)))
    reason = ctx.reason or f"jump back to {point.label}"
    done = jumpback.apply(repo, found, force=force, reason=reason, command=ctx.command_line)
    data = {
        "to": point.seq,
        "point": at,
        "undone": [e.seq for e in found.steps],
        "events": [d.seq for d in done],
        "steps": steps,
    }
    return Out(data=data, md="\n".join(lines))


def _undo_roll(ctx: Context, repo: Repo, target: Event) -> Out:
    from didact.services.dice import void_roll

    number = target.data.get("roll")
    if ctx.dry_run:
        return Out(
            data={"dry_run": True, "event": target.seq, "roll": number},
            md=_(
                "dry run: would mark #r{roll} undone ({summary})",
                roll=number,
                summary=shown(target),
            ),
        )
    done = void_roll(repo, target, reason=ctx.reason, command=ctx.command_line)
    return Out(
        data={"undone": [target.seq], "roll": number, "events": [done.seq]},
        md=_(
            "✔ marked #r{roll} undone ({event}); it stays in the log, marked (undone)",
            roll=number,
            event=done.label,
        ),
    )


@command(
    "redo",
    summary="Redo the last undone change",
    writes=True,
    examples=("didact redo",),
)
def redo(
    ctx: Context, *, force: Annotated[bool, "redo even if files changed since"] = False
) -> Out:
    repo = open_repo(ctx)
    candidates = changesets.redoable(repo)
    if not candidates:
        return Out(data={"redone": None}, md=_("nothing to redo"))
    target = candidates[0]
    if ctx.dry_run:
        return Out(
            data={"dry_run": True, "event": target.seq},
            md=_("dry run: would redo by undoing {event}", event=target.label),
        )
    done = changesets.undo(repo, target, force=force, reason=ctx.reason, command=ctx.command_line)
    return Out(
        data={"redone": target.undoes, "event": done.seq},
        md=_("✔ redid #e{event} ({undo})", event=target.undoes, undo=done.label),
    )


@command(
    "retcon",
    summary="Change a fact after the fact: apply it, keep the old value, flag stale summaries",
    writes=True,
    examples=(
        'didact retcon "Sweeney is Anglwyst\'s son" --set sweeney.parent=npc:anglwyst --secret',
        "didact retcon 'The mill burned down last winter' --set loc:mill.status=ruined",
        "didact retcon 'Tom was never a smuggler' --set 'npc:tom.tags-=smuggler' --about npc:ann",
    ),
    description=(
        "`--set record.key=value` changes a record (checked like `set`); the old value is\n"
        "kept in its `extra.superseded` with the in-game time it stopped being true. The\n"
        "fact is added to each record's `## Facts` (or `## Secrets`). Summaries that mention\n"
        "those records are marked stale for `summary due`, and `audit` lists the retcon."
    ),
)
def retcon(
    ctx: Context,
    fact: Annotated[str, "the new truth, in a sentence", Metavar("fact")],
    *,
    set_: Annotated[
        list[str] | None, "a change: record.key=value (+= and -= too)", Metavar("record.key=value")
    ] = None,
    about: Annotated[list[str] | None, "a record the fact is about (no change)"] = None,
    secret: Annotated[bool, "the players don't know it: add it under ## Secrets"] = False,
    force: Annotated[bool, "allow values the rules don't (needs --reason)"] = False,
) -> Out:
    from didact.services import play, sheets
    from didact.services import retcon as retcons

    sheets.check_force(force, ctx.reason)
    if not set_ and not about:
        raise InvalidError(
            _("say what the retcon changes"), hint=_("--set record.key=value, or --about <record>")
        )
    repo = open_repo(ctx)
    mode = "freeform" if force else sheets.strictness(repo)
    targets: dict[str, tuple[Located, list[assign.Assignment]]] = {}
    for text in set_ or []:
        left, _sep, _value = text.partition("=")
        ref, dot, _key = left.rstrip("+-").partition(".")
        if not dot:
            raise InvalidError(
                _("can't read {text}", text=repr(text)),
                hint=_("use record.key=value, e.g. tom.hp=3"),
            )
        located = repo.resolve(ref)
        entry = targets.setdefault(str(located.entity.id), (located, []))
        entry[1].append(assign.parse_assignment(text[len(ref) + 1 :]))
    for ref in about or []:
        located = repo.resolve(ref)
        targets.setdefault(str(located.entity.id), (located, []))
    cs = changeset(ctx, repo, N_("retcon: {fact}"), fact=fact)
    cs.reason = ctx.reason or f"retcon: {fact}"
    cs.forced = force
    notes: list[str] = []
    names: list[str] = []
    for located, assignments in targets.values():
        done = retcons.apply(cs, located, assignments, fact, secret=secret, mode=mode)
        notes += [f"{done.record}: {c}" for c in done.changes]
        names += [located.entity.name, *located.entity.aliases, str(located.entity.id)]
    stale = retcons.mark_stale(cs, names, f"retcon: {fact}")
    if stale:
        notes.append(
            _("summaries marked stale: {records} (`didact summary due`)", records=", ".join(stale))
        )
    current = play.load(repo)
    if current.session_open:
        play.add_beat(cs, current, "note", f"retcon: {fact}")
    extra: dict[str, JSON] = {"records": list[JSON](list(targets)), "stale": list[JSON](stale)}
    return finish(ctx, cs, done=_("retcon: {fact}", fact=fact), extra=extra, notes=notes)
