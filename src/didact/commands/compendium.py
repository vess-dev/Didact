"""The compendium: find, show and add entries; spawn them into the world."""

import json
from typing import Annotated, cast

from didact.commands._common import changeset, finish, open_repo, roller
from didact.commands.registry import Metavar, command
from didact.core.context import Context
from didact.core.errors import InvalidError
from didact.core.i18n import N_, _, ngettext
from didact.core.ids import Scope
from didact.core.output import JSON, Out, code


def _summary(data: dict[str, JSON]) -> str:
    skip = {"id", "type", "name", "tags", "aliases", "body", "source", "page", "summary", "extra"}
    parts = []
    for key, value in data.items():
        if key in skip or isinstance(value, dict | list):
            continue
        parts.append(f"{key} {value}")
    return " · ".join(parts[:8])


@command(
    "compendium find",
    summary="Search the compendium: monsters, items, spells, … from the enabled packs",
    examples=(
        "didact compendium find troll",
        "didact compendium find --type monster",
        "didact compendium find fire relic",
    ),
)
def compendium_find(
    ctx: Context,
    *words: Annotated[str, "words to look for", Metavar("word")],
    type_: Annotated[str | None, "only this type, e.g. monster", Metavar("type")] = None,
    limit: Annotated[int, "how many"] = 20,
) -> Out:
    from didact.services import compendium, packs

    repo = open_repo(ctx)
    hits = compendium.find(packs.active(repo), list(words), type_, limit)
    if not hits:
        return Out(data={"entries": []}, md=_("nothing in the compendium matches"))
    lines = [ngettext("{n} entry:", "{n} entries:", len(hits))]
    rows: list[JSON] = []
    for hit in hits:
        data = hit.item.data
        about = _summary(data)
        lines.append(
            f"- {hit.item.qualified} · {data.get('name')} ({data.get('type')})"
            + (f": {about}" if about else "")
        )
        rows.append(
            {
                "id": hit.item.qualified,
                "name": data.get("name"),
                "type": data.get("type"),
                "source": hit.item.source,
            }
        )
    return Out(data={"entries": rows}, md="\n".join(lines))


@command(
    "compendium show",
    summary="Show a compendium entry",
    examples=("didact compendium show troll",),
)
def compendium_show(ctx: Context, ref: Annotated[str, "the entry", Metavar("entry")]) -> Out:
    from didact.services import packs

    repo = open_repo(ctx)
    item = packs.active(repo).find("entry", ref)
    data = item.data
    lines = [f"{item.qualified} · {data.get('name')} ({data.get('type')})"]
    for key, value in data.items():
        if key in ("id", "type", "name", "body"):
            continue
        if isinstance(value, list) and all(isinstance(v, str | int | float) for v in value):
            shown = ", ".join(str(v) for v in value)
        else:
            shown = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        lines.append(f"{key}: {shown}")
    if isinstance(data.get("body"), str):
        lines += ["", str(data["body"]).strip()]
    lines.append(
        _(
            "source: {source} · spawn it: {command}",
            source=item.source,
            command=code(f"didact spawn {item.qualified}"),
        )
    )
    return Out(
        data={"id": item.qualified, "source": item.source, "data": data}, md="\n".join(lines)
    )


@command(
    "compendium add",
    summary="Add a homebrew entry to a pack's compendium (stored in your library)",
    writes=True,
    examples=(
        'didact compendium add --data \'{"name": "Bog Hag", "type": "npc", "hp": 8, "STR": 12}\'',
        "didact compendium add --pack my-system --data '{…}'",
    ),
)
def compendium_add(
    ctx: Context,
    *,
    data: Annotated[str, "the entry as JSON: name, type and its fields"],
    pack: Annotated[str | None, "whose compendium (default: the system)", Metavar("pack")] = None,
) -> Out:
    from didact.services import compendium, sheets

    try:
        payload = json.loads(data)
    except ValueError as exc:
        raise InvalidError(
            _("--data is not valid JSON: {error}", error=exc), hint=_("e.g. --data '{\"hp\": 6}'")
        ) from exc
    if not isinstance(payload, dict):
        raise InvalidError(_("--data must be a JSON object"), hint=_("e.g. --data '{\"hp\": 6}'"))
    repo = open_repo(ctx)
    target = pack or sheets.active_system(repo)
    if not target:
        raise InvalidError(_("which pack? this world has no system"), hint=_("pass --pack <id>"))
    cs = changeset(
        ctx,
        repo,
        N_("homebrew {pack} compendium entry {name}"),
        pack=target,
        name=str(payload.get("name")),
    )
    entry_id, rel = compendium.add(cs, target, cast(dict[str, JSON], payload))
    return finish(
        ctx,
        cs,
        done=_("added {entry} ({path})", entry=f"{target}.{entry_id}", path=rel),
        extra={"id": f"{target}.{entry_id}", "path": rel},
    )


@command(
    "compendium remove",
    summary="Remove a homebrew entry from the compendium (the packs' own entries stay)",
    writes=True,
    examples=(
        "didact compendium remove my-system.frost-wolf",
        "didact compendium remove 'Frost Wolf'",
    ),
    description=(
        "Deletes an entry added with `compendium add` (or written into\n"
        "`systems/<pack>/homebrew/compendium/` by hand); `didact undo` brings it back.\n"
        "Records spawned from it stay. A pack's own entries can't be deleted, but a house\n"
        "rule can change them: `didact override add entry <entry> --data '{…}'`."
    ),
)
def compendium_remove(
    ctx: Context, ref: Annotated[str, "the entry: pack.id, id or name", Metavar("entry")]
) -> Out:
    from didact.services import compendium, packs

    repo = open_repo(ctx)
    item = compendium.locate(packs.active(repo, house_rules=False), ref)
    cs = changeset(ctx, repo, N_("homebrew compendium entry {entry} removed"), entry=item.qualified)
    rel, left = compendium.remove(cs, item)
    notes = (
        [ngettext("{path} still holds {n} entry", "{path} still holds {n} entries", left, path=rel)]
        if left
        else []
    )
    name = item.data.get("name", item.id)
    return finish(
        ctx,
        cs,
        done=_("removed {entry} · {name} ({path})", entry=item.qualified, name=name, path=rel),
        extra={"id": item.qualified, "path": rel},
        notes=notes,
    )


@command(
    "spawn",
    summary="Create a record from a compendium entry (a troll, a sword, a relic, …)",
    writes=True,
    examples=(
        "didact spawn troll",
        "didact spawn my-system.troll --name 'Bridge Troll'",
        "didact spawn wolf --count 3",
    ),
)
def spawn(
    ctx: Context,
    ref: Annotated[str, "the entry", Metavar("entry")],
    *,
    name: Annotated[str | None, "a name for it (default: the entry's)", Metavar("name")] = None,
    count: Annotated[int, "how many (numbered: Wolf 1, Wolf 2, …)"] = 1,
    scope: Annotated[str | None, "where it lives (default: by type)", Metavar("scope")] = None,
) -> Out:
    from didact.services import compendium, packs, records, sheets

    if not 1 <= count <= 50:
        raise InvalidError(_("--count must be 1–50"), hint=_("e.g. --count 3"))
    repo = open_repo(ctx)
    item = packs.active(repo).find("entry", ref)
    data = compendium.record_data(item)
    type_ = str(item.data["type"])
    base = name or str(item.data.get("name", item.id))
    cs = changeset(ctx, repo, N_("spawn {entry}"), entry=item.qualified)
    sh = sheets.sheet(repo, type_)
    mode = sheets.strictness(repo)
    created: list[str] = []
    notes: list[str] = []
    for number in range(1, count + 1):
        display = f"{base} {number}" if count > 1 else base
        entity_id = records.new_id(type_, display)
        suffix = 2
        while repo.exists(repo.default_scope(type_), entity_id) or any(
            c == str(entity_id) for c in created
        ):
            entity_id = records.new_id(type_, f"{display} {suffix}")
            suffix += 1
        entity = records.build_entity(
            entity_id, display, {k: v for k, v in data.items() if k != "name"}
        )
        if item.data.get("secret") is True:  # adventure content stays hidden until discovered
            entity.knowledge = "secret"
            entity.fields.pop("secret", None)
        sheets.route_bare(entity, sh, [k for k in data if k not in records.DATA_KEYS])
        notes.extend(sheets.fill(entity, sh, roller(ctx, repo, display), missing=False))
        notes.extend(sheets.validate(entity, sh, mode))
        target = repo.check_scope(Scope.parse(scope)) if scope else repo.default_scope(type_)
        records.create(cs, target, entity)
        created.append(str(entity_id))
    shown = ", ".join(created)
    return finish(
        ctx,
        cs,
        done=_("spawned {ids} from {entry}", ids=shown, entry=item.qualified),
        extra={"ids": list[JSON](created)},
        notes=notes,
    )


@command(
    "compendium import",
    summary="Bring a pack's entries into the world (adventure or setting content)",
    writes=True,
    examples=(
        "didact compendium import drowned-lighthouse",
        "didact compendium import vale --type loc",
        "didact compendium import vale --type loc --tag coast --tag ruin --dry-run",
    ),
)
def compendium_import(
    ctx: Context,
    pack: Annotated[str, "the pack whose entries to bring in", Metavar("pack")],
    *,
    type_: Annotated[str | None, "only entries of this type", Metavar("type")] = None,
    tag: Annotated[
        list[str] | None, "only entries with this tag (repeatable: all of them)", Metavar("tag")
    ] = None,
) -> Out:
    from didact.services import compendium, packs, records, sheets

    repo = open_repo(ctx)
    active = packs.active(repo)
    active.get(pack)  # it must be enabled
    entries = [i for i in compendium.entries(active, type_, tag or []) if i.pack == pack]
    if not entries:
        return Out(data={"created": []}, md=_("{pack} has no entries to import", pack=pack))
    cs = changeset(ctx, repo, N_("import {pack} entries"), pack=pack)
    created: list[str] = []
    skipped: list[str] = []
    secret = 0
    for item in entries:
        type_name = str(item.data["type"])
        name = str(item.data.get("name", item.id))
        entity_id = records.new_id(type_name, name, item.id)
        scope = repo.default_scope(type_name)
        if repo.exists(scope, entity_id):
            skipped.append(str(entity_id))
            continue
        data = compendium.record_data(item)
        entity = records.build_entity(
            entity_id, name, {k: v for k, v in data.items() if k != "name"}
        )
        sh = sheets.sheet(repo, type_name)
        sheets.route_bare(entity, sh, [k for k in data if k not in records.DATA_KEYS])
        if item.data.get("secret") is True:
            entity.knowledge = "secret"
            entity.fields.pop("secret", None)
            secret += 1
        records.create(cs, scope, entity)
        created.append(str(entity_id))
    notes = [_("already there: {ids}", ids=", ".join(skipped))] if skipped else []
    if secret:
        notes.append(
            ngettext(
                "{n} secret: undiscovered until `didact set <id> knowledge=known`",
                "{n} secret: undiscovered until `didact set <id> knowledge=known`",
                secret,
            )
        )
    done = ngettext(
        "imported {n} record from {pack}",
        "imported {n} records from {pack}",
        len(created),
        pack=pack,
    )
    return finish(ctx, cs, done=done, extra={"created": list[JSON](created)}, notes=notes)
