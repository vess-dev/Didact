"""Records: create, show, find, change, link, remove."""

from typing import TYPE_CHECKING, Annotated, cast

from didact.commands._common import (
    changeset,
    finish,
    headline,
    open_repo,
    parse_data,
    render_record,
    roller,
    scope_list,
)
from didact.commands.registry import command
from didact.core import labels
from didact.core.context import Context
from didact.core.errors import InvalidError
from didact.core.i18n import N_, _, ngettext
from didact.core.ids import Scope, normalize_name
from didact.core.output import JSON, Out
from didact.expr.model import Value
from didact.schema.sheet import Sheet
from didact.services import assign, hooks, names, records, sheets
from didact.services.records import DATA_KEYS as _DATA_KEYS
from didact.store.changeset import Changeset
from didact.store.entity import Entity
from didact.store.repo import Repo

if TYPE_CHECKING:
    from didact.services.knowledge import Unknown
    from didact.services.lore import Hit

NAMED_TYPES = frozenset({"npc", "pc", "loc", "faction"})  # checked for overused names


@command(
    "new",
    summary="Create a record from a name, flags, and/or a JSON description",
    writes=True,
    examples=(
        "didact new npc Sweeney --tag wood --set disposition=wary",
        "didact new loc 'Amber Grave' --body 'A pool of bubbling sap.'",
        'didact new npc --data \'{"name": "Old Gannet", "hp": 4, "traits": ["one-eyed"]}\'',
        "didact new pc Freya --scope campaign:withering",
        "didact new pc Freya --fill            # roll every field the system rolls",
        'didact new npc Troll --set STR=roll --set hp=12 --force --reason "boss"',
    ),
)
def new(
    ctx: Context,
    type_: Annotated[str, "record type: npc, pc, loc, item, faction, quest, note, …"],
    name: Annotated[str | None, "display name (or give it in --data)"] = None,
    *,
    id_: Annotated[str | None, "slug or full id (default: from the name)"] = None,
    scope: Annotated[str | None, "where it lives (default: pc/note → campaign, else world)"] = None,
    alias: Annotated[list[str] | None, "another name it's known by"] = None,
    tag: Annotated[list[str] | None, "a tag"] = None,
    set_: Annotated[list[str] | None, "a field assignment, e.g. hp=6"] = None,
    body: Annotated[str | None, "prose description"] = None,
    data: Annotated[str | None, "a JSON object describing the record (describe it, get it)"] = None,
    fill: Annotated[bool, "roll (or default) every field the sheet knows how to fill"] = False,
    force: Annotated[bool, "allow values the rules don't (needs --reason)"] = False,
) -> Out:
    sheets.check_force(force, ctx.reason)
    repo = open_repo(ctx)
    payload = parse_data(data) or {}
    display = name or (payload.get("name") if isinstance(payload.get("name"), str) else None)
    if not display:
        raise InvalidError(
            _("a new record needs a name"), hint=_("pass it as an argument or in --data")
        )
    entity_id = records.new_id(type_, str(display), id_)
    entity = records.build_entity(
        entity_id, str(display), payload, aliases=alias or (), tags=tag or (), body=body
    )
    sh = sheets.sheet(repo, entity_id.type)
    mode = "freeform" if force else sheets.strictness(repo)
    notes: list[str] = []
    sheets.route_bare(entity, sh, [k for k in payload if k not in _DATA_KEYS])
    for text in set_ or []:
        note = sheets.apply(entity, assign.parse_assignment(text), sh, mode)
        if note:
            notes.append(note)
    rolled = sheets.fill(entity, sh, roller(ctx, repo, entity.name), missing=fill)
    notes.extend(rolled)
    notes.extend(sheets.validate(entity, sh, mode))
    target = repo.check_scope(Scope.parse(scope)) if scope else repo.default_scope(entity_id.type)
    same_name = [
        r for r in repo.index().by_name(entity.name, repo.chain()) if r.id != str(entity_id)
    ]
    if same_name:
        notes.append(
            _(
                "the name also belongs to {records}",
                records=", ".join(f"{r.id} ({r.scope})" for r in same_name),
            )
        )
    elif entity_id.type in NAMED_TYPES and names.cliche(entity.name):
        notes.append(
            _(
                "{name} is a name LLMs overuse; `didact name {type}` rolls a fresh one",
                name=entity.name,
                type=entity_id.type,
            )
        )
    cs = changeset(
        ctx,
        repo,
        N_("create {id} ({name}) in {scope}"),
        id=str(entity_id),
        name=entity.name,
        scope=str(target),
    )
    cs.forced = force
    records.create(cs, target, entity)
    return finish(
        ctx,
        cs,
        done=_("created {record}", record=headline(str(entity_id), entity.name, target)),
        extra={"id": str(entity_id), "scope": str(target)},
        notes=notes,
    )


@command(
    "show",
    summary="Show a record by id, name or alias (what the players know; --gm for everything)",
    examples=(
        "didact show sweeney",
        "didact show npc:sweeney --gm --detail full",
        "didact show npc:tom@world:vale",
    ),
    description=(
        "The default view is player-safe: secret records, `## Secrets` sections and\n"
        "`secret: true` fields are left out, and it says when something was. `--gm` shows\n"
        "everything; read it to run the game, but don't read it out."
    ),
)
def show(
    ctx: Context,
    ref: Annotated[str, "id (npc:sweeney), name or alias"],
    *,
    gm: Annotated[bool, "show secrets too (GM eyes only)"] = False,
) -> Out:
    from didact.services import knowledge

    repo = open_repo(ctx)
    located = repo.resolve(ref)
    entity = located.entity
    if not knowledge.visible(entity.knowledge, gm):
        return Out(
            data={"id": str(entity.id), "knowledge": "secret", "hidden": True},
            md=_(
                "{id} is secret: the players don't know about it yet.\n"
                "GM view: `didact show {id} --gm` · "
                "to let them know: `didact reveal {id}`",
                id=str(entity.id),
            ),
        )
    sh = sheets.sheet(repo, entity.type)
    hid = knowledge.NOTHING if gm else knowledge.unknown(repo)
    shown, hidden = (entity, knowledge.Hidden()) if gm else knowledge.player_copy(entity, sh, hid)
    backlinks = [
        (b.source.id, b.rel)
        for b in repo.index().backlinks([str(entity.id)])
        if b.source.id not in hid.ids and (gm or not knowledge.secret_path(b.rel))
    ]
    data = shown.to_data()
    data["scope"] = str(located.scope)
    data["backlinks"] = [{"id": src, "rel": rel} for src, rel in backlinks]
    lines: list[str] = []
    if not sh.empty:
        from didact.schema.sheet import json_values, summary

        lines = sheets.sheet_lines(shown, sh)
        data["values"] = json_values(summary(sh, sheets.entity_values(shown, sh)))
        found = sheets.problems(entity, sh)
        if found:
            data["problems"] = list[JSON](found)
            lines.append(_("problems: {problems}", problems="; ".join(found)))
    handled = _handled_keys(sh)
    tail = hidden.note(str(entity.id))
    if tail:
        data["hidden"] = {
            "lines": hidden.lines,
            "fields": list[JSON](hidden.fields),
            "details": list[JSON](hidden.details),
        }
    extras = _whereabouts(repo, shown, gm, data, handled, hid)
    tail = "\n".join([*extras, tail]) if tail else "\n".join(extras)
    related = _related_lore(repo, entity, gm)
    if related:
        data["lore"] = [str(h.entity.id) for h in related]
        lore_lines = "\n".join(_("lore: {line}", line=h.line()) for h in related)
        tail = f"{tail}\n{lore_lines}" if tail else lore_lines

    def render(full: bool) -> str:
        text = render_record(
            shown, located.scope, full=full, backlinks=backlinks, sheet=lines, handled=handled
        )
        return f"{text}\n{tail}" if tail else text

    return Out(data=data, md=render(False), md_full=render(True))


def _whereabouts(
    repo: Repo,
    entity: Entity,
    gm: bool,
    data: dict[str, JSON],
    handled: set[str],
    hid: Unknown,
) -> list[str]:
    """What it holds, where it is, what happened to it (and, for the GM, what's left to note).
    Fills `data` and returns lines for the Markdown view. `hid`: what a player view mustn't
    name."""
    from didact.services import details, inventory, knowledge, sheets

    lines: list[str] = []
    held = details.contents(repo, entity)
    if hid != knowledge.NOTHING:  # a public chest can hold a secret thing
        kept = knowledge.without_secrets(list[JSON](held), hid)[0]
        held = cast(list[dict[str, JSON]], kept)
    if held:
        data["contents"] = list[JSON](held)
        bag = inventory.find_bag(entity, sheets.sheet(repo, entity.type))
        if bag.block == "fields":  # a plain list (a place, a chest): show it as a tree
            handled.add("inventory")
            lines += [_("contents:"), *details.contents_lines(held)]
    if entity.type not in details.PEOPLE_TYPES | details.PLACE_TYPES:
        chains = details.where(repo, str(entity.id), gm=gm)
        if chains:
            data["where"] = [[{"id": str(e.id), "name": e.name} for e in c] for c in chains]
            lines += [_("whereabouts: {chain}", chain=details.chain_text(c)) for c in chains]
    beats = details.chronicle(repo, str(entity.id), gm=gm)
    if beats:
        data["chronicle"] = list[JSON](beats)
        lines.append(_("chronicle:"))
        lines += [f"- {details.chronicle_line(b)}" for b in beats[-5:]]
        if len(beats) > 5:
            lines.append(
                ngettext(
                    "({n} earlier: `didact about {id}`)",
                    "({n} earlier: `didact about {id}`)",
                    len(beats) - 5,
                    id=str(entity.id),
                )
            )
    if gm:
        open_ = details.missing(repo, entity)
        data["suggested"] = list[JSON](open_)
        if open_:
            lines.append(
                _(
                    "open details: {details} (`didact about {id} …`)",
                    details=", ".join(labels.inline(n, labels.detail_name(n)) for n in open_),
                    id=str(entity.id),
                )
            )
    return lines


def _related_lore(repo: Repo, entity: Entity, gm: bool) -> list[Hit]:
    """Lore entries and rulings its name brings up (not its own card, not constants)."""
    from didact.services import lore

    if repo.active_world() is None or entity.type == "lore":
        return []
    names = " ".join([entity.name, *entity.aliases])
    found = lore.scan(repo, names, gm=gm, budget=300)
    return [h for h in found.hits if h.source != "card" and h.reason != "constant"]


def _handled_keys(sh: Sheet) -> set[str]:
    """Flattened key prefixes the sheet lines already show (`mechanics.my-system.STR`)."""
    keys: set[str] = set()
    for schema in sh.schemas:
        prefix = "" if schema.pack == "core" else f"mechanics.{schema.pack}."
        keys |= {prefix + name for name in schema.fields}
    return keys


@command(
    "find",
    summary="Search records (full text), or list them by type, tag or scope",
    examples=(
        "didact find champion",
        "didact find --type npc",
        "didact find sap pool --type loc --limit 5",
        "didact find --tag wood --scope world:vale",
        "didact find heir --gm                # secrets too",
    ),
)
def find(
    ctx: Context,
    *words: Annotated[str, "words to search for (none = list)"],
    type_: Annotated[list[str] | None, "only this type"] = None,
    tag: Annotated[list[str] | None, "only records with this tag"] = None,
    scope: Annotated[list[str] | None, "only this scope (default: everything visible)"] = None,
    limit: Annotated[int, "maximum results"] = 20,
    archived: Annotated[bool, "include archived records"] = False,
    gm: Annotated[bool, "search secrets too (GM eyes only)"] = False,
) -> Out:

    repo = open_repo(ctx)
    scopes = [repo.check_scope(Scope.parse(s)) for s in scope] if scope else repo.chain()
    types = type_ or []
    query = " ".join(words).strip()
    index = repo.index()
    if query:
        hits = index.search(
            query, scopes, types=types, include_archived=archived, limit=limit * 3, loose=True
        )
        found = [(h.row, h.snippet) for h in hits]
    else:
        found = [(r, "") for r in index.rows(scopes, types=types, include_archived=archived)]
    if tag:
        wanted = {normalize_name(t) for t in tag}
        found = [(r, s) for r, s in found if wanted <= {normalize_name(t) for t in r.tags}]
    hidden = 0
    if not gm:
        from didact.services import knowledge

        found, hidden = knowledge.player_hits(repo, found, list(words))
    total = len(found)
    found = found[:limit]
    where = scope_list(scopes)
    if query and total > limit:
        head = ngettext(
            '{n} result for "{query}" in {scopes} (showing {limit})',
            '{n} results for "{query}" in {scopes} (showing {limit})',
            total,
            query=query,
            scopes=where,
            limit=limit,
        )
    elif query:
        head = ngettext(
            '{n} result for "{query}" in {scopes}',
            '{n} results for "{query}" in {scopes}',
            total,
            query=query,
            scopes=where,
        )
    elif total > limit:
        head = ngettext(
            "{n} record in {scopes} (showing {limit})",
            "{n} records in {scopes} (showing {limit})",
            total,
            scopes=where,
            limit=limit,
        )
    else:
        head = ngettext("{n} record in {scopes}", "{n} records in {scopes}", total, scopes=where)
    lines = [head]
    for row, snippet in found:
        line = f"- {headline(row.id, row.name, row.scope)}"
        if row.knowledge != "known":
            line += f" [{row.knowledge}]"
        if snippet:
            line += f": {snippet.replace(chr(10), ' ')}"
        lines.append(line)
    if hidden:
        lines.append(
            ngettext(
                "({n} secret match hidden; `--gm` shows them)",
                "({n} secret matches hidden; `--gm` shows them)",
                hidden,
            )
        )
    data: dict[str, JSON] = {
        "total": total,
        "results": [
            {
                "id": r.id,
                "name": r.name,
                "type": r.type,
                "scope": str(r.scope),
                "knowledge": r.knowledge,
                "snippet": s,
            }
            for r, s in found
        ],
    }
    if hidden:
        data["hidden"] = hidden
    return Out(data=data, md="\n".join(lines))


@command(
    "set",
    summary="Change fields: key=value, key+=value (add/append), key-=value (subtract/remove)",
    writes=True,
    examples=(
        "didact set sweeney disposition=hostile",
        "didact set pc:freya hp-=2 fatigue+=1",
        "didact set npc:tom tags+=smuggler status=missing",
        "didact set npc:tom mechanics.my-system.hp=4",
        "didact set npc:tom --unset mood",
    ),
)
def set_(
    ctx: Context,
    ref: Annotated[str, "the record (id, name or alias)"],
    *assignments: Annotated[str, "key=value, key+=value or key-=value"],
    unset: Annotated[list[str] | None, "remove this key"] = None,
    force: Annotated[bool, "allow values the rules don't (needs --reason)"] = False,
) -> Out:
    if not assignments and not unset:
        raise InvalidError(_("nothing to set"), hint=_("e.g. `didact set sweeney hp=5`"))
    sheets.check_force(force, ctx.reason)
    parsed = [assign.parse_assignment(a) for a in assignments]
    repo = open_repo(ctx)
    located = repo.resolve(ref)
    sh = sheets.sheet(repo, located.entity.type)
    mode = "freeform" if force else sheets.strictness(repo)
    what = ", ".join([*assignments, *(f"unset {k}" for k in unset or [])])
    cs = changeset(ctx, repo, N_("set {id}: {what}"), id=str(located.entity.id), what=what)
    shown = ", ".join([*assignments, *(_("unset {key}", key=k) for k in unset or [])])
    cs.forced = force
    notes: list[str] = []
    fired = hooks.Outcome()

    def change(entity: Entity) -> None:
        before = sheets.problems(entity, sh)
        values = sheets.entity_values(entity, sh)
        for assignment in parsed:
            note = sheets.apply(entity, assignment, sh, mode)
            if note:
                notes.append(note)
        for key in unset or []:
            note = sheets.unset(entity, key, sh)  # a field not set: no change, and a note
            if note:
                notes.append(note)
        _settle(entity, sh, values, mode, force, notes, fired)
        notes.extend(sheets.validate(entity, sh, mode, before=before))

    records.edit(cs, located.path, change)
    notes.extend(_run_hooks(ctx, cs, str(located.entity.id), fired))
    return finish(
        ctx,
        cs,
        done=f"{located.entity.id}: {shown}",
        extra={"id": str(located.entity.id)},
        notes=notes,
    )


@command(
    "edit",
    summary="Merge a JSON description into a record (or replace its fields with --replace)",
    writes=True,
    examples=(
        'didact edit npc:tom --data \'{"hp": 6, "tags": ["smuggler"], "body": "A tall man."}\'',
        'didact edit npc:tom --data \'{"fields": {"hp": 3}}\' --replace',
    ),
)
def edit(
    ctx: Context,
    ref: Annotated[str, "the record"],
    *,
    data: Annotated[str, "a JSON object with the changes"],
    replace: Annotated[bool, "replace fields/mechanics/extra instead of merging into them"] = False,
    force: Annotated[bool, "allow values the rules don't (needs --reason)"] = False,
) -> Out:
    sheets.check_force(force, ctx.reason)
    payload = parse_data(data) or {}
    repo = open_repo(ctx)
    located = repo.resolve(ref)
    sh = sheets.sheet(repo, located.entity.type)
    mode = "freeform" if force else sheets.strictness(repo)
    cs = changeset(ctx, repo, N_("edit {id}"), id=str(located.entity.id))
    cs.forced = force
    notes: list[str] = []
    fired = hooks.Outcome()
    given = payload.get("mechanics")
    blocks = given if isinstance(given, dict) else {}  # what it states there stands (`stated`)
    bare = {
        k: v
        for k, v in payload.items()
        if k not in _DATA_KEYS and sh.route(k) is not None and not sheets.stated(sh, k, blocks)
    }

    def change(entity: Entity) -> None:
        before = sheets.problems(entity, sh)
        values = sheets.entity_values(entity, sh)
        rest = {k: v for k, v in payload.items() if k not in bare}
        incoming = records.build_entity(entity.id, None if "name" in rest else entity.name, rest)
        if "name" in payload:
            entity.name = incoming.name
        for key in ("aliases", "tags", "status", "knowledge", "archived", "links"):
            if key in payload:
                setattr(entity, key, getattr(incoming, key))
        if "body" in payload:
            entity.body = incoming.body
        if "details" in payload:  # the GM's notes: merged (an empty text clears one)
            merged = {} if replace else dict(entity.details)
            raw = payload["details"]
            for name, text in raw.items() if isinstance(raw, dict) else []:
                if text in (None, ""):
                    merged.pop(str(name), None)
            merged |= incoming.details
            entity.details = merged
        for container in ("fields", "mechanics", "extra"):
            new_values = getattr(incoming, container)
            if container not in payload and not new_values:
                continue  # not mentioned (top-level unknown keys arrive as fields)
            if replace:
                setattr(entity, container, new_values)
            else:
                _deep_merge(getattr(entity, container), new_values)
        for key, value in bare.items():  # top-level keys the sheet knows: set like `set`
            note = sheets.apply(
                entity, assign.Assignment(("fields", key), "=", value, True), sh, mode
            )
            if note:
                notes.append(note)
        _settle(entity, sh, values, mode, force, notes, fired)
        notes.extend(sheets.validate(entity, sh, mode, before=before))

    records.edit(cs, located.path, change)
    notes.extend(_run_hooks(ctx, cs, str(located.entity.id), fired))
    return finish(
        ctx,
        cs,
        done=_("edited {id}", id=str(located.entity.id)),
        extra={"id": str(located.entity.id)},
        notes=notes,
    )


def _settle(
    entity: Entity,
    sh: Sheet,
    values: dict[str, Value],
    mode: sheets.Strictness,
    force: bool,
    notes: list[str],
    fired: hooks.Outcome,
) -> None:
    """Fire the sheet's hooks the change crossed (`--force` skips them, and says so)."""
    if force:
        notes.extend(hooks.skipped(entity, sh, values))
        return
    outcome = hooks.settle(entity, sh, values, mode)
    notes.extend(outcome.notes)
    fired.triggers.extend(outcome.triggers)


def _run_hooks(ctx: Context, cs: Changeset, record: str, fired: hooks.Outcome) -> list[str]:
    from didact.services import rules

    return rules.run_hooks(cs.repo, cs, record, fired, dry=ctx.dry_run, command=ctx.command_line)


def _deep_merge(target: dict[str, JSON], source: dict[str, JSON]) -> None:
    for key, value in source.items():
        existing = target.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            _deep_merge(existing, value)
        else:
            target[key] = value


@command(
    "note",
    summary="Append a dated note to a record",
    writes=True,
    examples=("didact note sweeney 'Agreed to let the party hunt on the old trail.'",),
)
def note(ctx: Context, ref: Annotated[str, "the record"], text: Annotated[str, "the note"]) -> Out:
    repo = open_repo(ctx)
    located = repo.resolve(ref)
    cs = changeset(ctx, repo, N_("note on {id}"), id=str(located.entity.id))
    records.edit(cs, located.path, lambda e: records.add_note(e, text))
    return finish(
        ctx,
        cs,
        done=_("noted on {id}", id=str(located.entity.id)),
        extra={"id": str(located.entity.id)},
    )


@command(
    "link",
    summary="Link two records with a relation (or remove a link with --remove)",
    writes=True,
    examples=(
        "didact link sweeney lives-at 'Sweeney's Cabin'",
        "didact link npc:tom ally npc:ann",
        "didact link npc:tom ally npc:ann --remove",
    ),
)
def link(
    ctx: Context,
    ref: Annotated[str, "the record the link starts from"],
    rel: Annotated[str, "the relation, e.g. ally, lives-at, member-of"],
    target: Annotated[str, "the record it points to"],
    *,
    remove: Annotated[bool, "remove the link instead"] = False,
) -> Out:
    repo = open_repo(ctx)
    source = repo.resolve(ref)
    target_id = str(repo.resolve(target).entity.id)
    said = N_("unlinked {id} {rel} {target}") if remove else N_("linked {id} {rel} {target}")
    cs = changeset(ctx, repo, said, id=str(source.entity.id), rel=rel, target=target_id)
    if remove:
        records.edit(cs, source.path, lambda e: records.remove_link(e, rel, target_id))
    else:
        records.edit(cs, source.path, lambda e: records.add_link(e, rel, target_id))
    values = {"source": str(source.entity.id), "rel": rel, "target": target_id}
    if remove:
        done = _("unlinked {source} —{rel}→ {target}", **values)
    else:
        done = _("linked {source} —{rel}→ {target}", **values)
    return finish(ctx, cs, done=done)


@command(
    "rm",
    summary="Delete a record (undoable); refuses while others link to it unless --unlink/--force",
    description=(
        "Links from other records stop it (unless --unlink removes them, previewed first,\n"
        "or --force leaves them dangling). It also leaves play: any party or fight it's in,\n"
        "and the party's location if that's where they are. `didact undo` brings it all back."
    ),
    writes=True,
    examples=(
        "didact rm npc:tom",
        "didact rm npc:tom --unlink",
        "didact rm npc:tom --unlink --yes",
    ),
)
def rm(
    ctx: Context,
    ref: Annotated[str, "the record"],
    *,
    unlink: Annotated[bool, "also remove links pointing at it (previewed first)"] = False,
    force: Annotated[bool, "delete even if others still link to it"] = False,
    yes: Annotated[bool, "apply without the preview step"] = False,
) -> Out:
    repo = open_repo(ctx)
    located = repo.resolve(ref)
    cs = changeset(ctx, repo, N_("delete {id}"), id=str(located.entity.id))
    cs.forced = force
    touched = records.delete(cs, located, unlink=unlink, force=force)
    left = records.forget_in_play(cs, str(located.entity.id))
    return finish(
        ctx,
        cs,
        done=(
            _(
                "deleted {id}; unlinked from {records}",
                id=str(located.entity.id),
                records=", ".join(touched),
            )
            if touched
            else _("deleted {id}", id=str(located.entity.id))
        ),
        review=bool(touched),
        yes=yes,
        notes=left,
    )


def _set_archived(ctx: Context, ref: str, value: bool) -> Out:
    repo = open_repo(ctx)
    located = repo.resolve(ref)
    said = N_("archived {id}") if value else N_("restored {id}")
    cs = changeset(ctx, repo, said, id=str(located.entity.id))

    def change(entity: Entity) -> None:
        entity.archived = value

    records.edit(cs, located.path, change)
    record = str(located.entity.id)
    done = _("archived {id}", id=record) if value else _("restored {id}", id=record)
    return finish(ctx, cs, done=done)


@command(
    "archive",
    summary="Hide a record from lists and searches without deleting it",
    writes=True,
    examples=("didact archive npc:tom",),
)
def archive(ctx: Context, ref: Annotated[str, "the record"]) -> Out:
    return _set_archived(ctx, ref, True)


@command(
    "restore",
    summary="Bring an archived record back",
    writes=True,
    examples=("didact restore npc:tom",),
)
def restore(ctx: Context, ref: Annotated[str, "the record (archived records resolve too)"]) -> Out:
    return _set_archived(ctx, ref, False)
