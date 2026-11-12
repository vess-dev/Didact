"""Lore: keyword-triggered memory: add entries, scan text, explain why something came up."""

from typing import Annotated, Literal

from didact.commands._common import changeset, finish, open_repo
from didact.commands.registry import Metavar, command
from didact.core.context import Context
from didact.core.errors import InvalidError
from didact.core.i18n import N_, _, ngettext
from didact.core.output import JSON, Out


@command(
    "lore add",
    summary="Add a lore entry: what comes back whenever its keys are mentioned",
    writes=True,
    examples=(
        "didact lore add 'Sweeney owes the ferryman a debt.' --keys 'sweeney, ferryman'",
        "didact lore add 'Torches burn 3 uses; an oil can relights a lantern 6 times.' "
        "--keys 'torch, lantern' --kind rule-reminder --scope system",
        "didact lore add 'The player dislikes spiders: keep them off screen.' --constant "
        "--kind preference --scope global",
        "didact lore add 'The river spirit is awake.' --keys river --secondary night --sticky 2",
    ),
    description=(
        "The content should name its subject: keys and titles are never injected. Entries\n"
        "go to the campaign unless --scope says otherwise (world canon, system reminders,\n"
        "global preferences). Edit them like any record (`set`, `edit`); widen with `promote`."
    ),
)
def lore_add(
    ctx: Context,
    content: Annotated[str, "what comes back (name the subject in it)", Metavar("content")],
    *,
    keys: Annotated[list[str] | None, "words or phrases, comma-separated; /regex/ too"] = None,
    secondary: Annotated[list[str] | None, "extra keys, checked with --logic"] = None,
    logic: Annotated[
        Literal["and_any", "and_all", "not_any", "not_all"] | None, "how secondary keys count"
    ] = None,
    priority: Annotated[int | None, "higher comes first (default 50)", Metavar("n")] = None,
    kind: Annotated[
        Literal["lore", "memory", "rule-reminder", "preference", "secret"] | None, "what it is"
    ] = None,
    scope: Annotated[str | None, "campaign (default), world, system or global"] = None,
    constant: Annotated[bool, "always included (brief, every scan)"] = False,
    probability: Annotated[int | None, "percent chance it fires", Metavar("n")] = None,
    group: Annotated[str | None, "only the best entry of a group comes up"] = None,
    sticky: Annotated[str | None, "stays on after firing: turns, or '2 scenes'"] = None,
    cooldown: Annotated[str | None, "rests after firing: turns, or '2 scenes'"] = None,
    delay: Annotated[str | None, "not before turn (or scene) n", Metavar("n")] = None,
    no_recurse: Annotated[bool, "its content doesn't trigger other entries"] = False,
    name: Annotated[str | None, "a title (never injected)", Metavar("title")] = None,
) -> Out:
    from didact.services import lore, records, rulings

    repo = open_repo(ctx)
    fields = lore.entry_fields(
        lore.split_keys(keys),
        secondary=lore.split_keys(secondary),
        logic=logic,
        priority=priority,
        kind=kind,
        constant=constant,
        probability=probability,
        group=group,
        sticky=sticky,
        cooldown=cooldown,
        delay=delay,
        recursive=not no_recurse,
    )
    if not content.strip():
        raise InvalidError(
            _("a lore entry needs content"),
            hint=_("e.g. `didact lore add 'Tom owes the witch.' --keys tom`"),
        )
    where = rulings.scope_for(repo, scope) if scope else repo.default_scope("lore")
    title = name or lore.title_for(content)
    entity = records.build_entity(
        records.new_id("lore", title), title, {"fields": fields}, body=content.strip() + "\n"
    )
    cs = changeset(ctx, repo, N_("lore: {title}"), title=title)
    records.create(cs, where, entity)
    listed = fields.get("keys")
    shown = (
        ", ".join(str(k) for k in listed) if isinstance(listed, list) and listed else _("always")
    )
    extra: dict[str, JSON] = {"id": str(entity.id), "scope": str(where)}
    done = _("{record} in {scope} (keys: {keys})", record=entity.id, scope=where, keys=shown)
    return finish(ctx, cs, done=done, extra=extra)


@command(
    "lore list",
    summary="Lore entries here (campaign, world, system, global), with their keys",
    examples=("didact lore list", "didact lore list --kind rule-reminder"),
)
def lore_list(
    ctx: Context,
    *,
    kind: Annotated[str | None, "only this kind", Metavar("kind")] = None,
    gm: Annotated[bool, "include secret entries"] = False,
) -> Out:
    repo = open_repo(ctx)
    rows = repo.index().rows(repo.chain(), types=["lore"])
    items: list[JSON] = []
    lines: list[str] = []
    hidden = 0
    for row in rows:
        fields = row.data.get("fields")
        values = fields if isinstance(fields, dict) else {}
        entry_kind = str(values.get("kind", "lore"))
        if kind and entry_kind != kind:
            continue
        if (row.knowledge == "secret" or entry_kind == "secret") and not gm:
            hidden += 1
            continue
        keys = values.get("keys")
        shown = ", ".join(str(k) for k in keys) if isinstance(keys, list) and keys else _("always")
        if values.get("constant") is True:
            line = _(
                "- {record} ({kind}, {scope}) · constant: {keys}",
                record=row.id,
                kind=entry_kind,
                scope=row.scope,
                keys=shown,
            )
        else:
            line = f"- {row.id} ({entry_kind}, {row.scope}): {shown}"
        lines.append(line)
        items.append({"id": row.id, "scope": str(row.scope), "kind": entry_kind, "keys": keys})
    head = [ngettext("{n} lore entry:", "{n} lore entries:", len(items))]
    if hidden:
        lines.append(
            ngettext("({n} secret entry hidden; --gm)", "({n} secret entries hidden; --gm)", hidden)
        )
    return Out(data={"entries": items, "hidden": hidden}, md="\n".join(head + lines))


@command(
    "lore scan",
    summary="What a text brings up: lore entries, cards and rulings, best first",
    examples=(
        "didact lore scan 'Freya asks Sweeney about the ferryman'",
        "didact lore scan --recent 5          # the last 5 journal beats",
        "didact lore scan 'the torch gutters' --gm --budget 1200",
    ),
    description=(
        "Matches whole words (plurals too) against the keys of everything in scope. Each\n"
        "result says why it came up. Player-safe unless --gm; the Claude Code hook scans\n"
        "every player message for you (`capture --hook`)."
    ),
)
def lore_scan(
    ctx: Context,
    *text: Annotated[str, "the text to scan", Metavar("text")],
    recent: Annotated[int | None, "scan the last n journal beats instead", Metavar("n")] = None,
    budget: Annotated[int, "about how many tokens of lore to return", Metavar("n")] = 600,
    gm: Annotated[bool, "include secret entries"] = False,
) -> Out:
    from didact.services import lore, play

    repo = open_repo(ctx)
    words = " ".join(text)
    if recent:
        current = play.load(repo)
        beats = play.beats(repo, current.session) if current.session else []
        beats = [b for b in beats if play.visible(b, gm)]
        words = " ".join([words, *(str(b.get("text", "")) for b in beats[-recent:])])
    if not words.strip():
        raise InvalidError(_("nothing to scan"), hint=_("give text, or --recent 5 for the journal"))
    found = lore.scan(repo, words, gm=gm, budget=budget)
    head = (
        ngettext("{n} match:", "{n} matches:", len(found.hits))
        if found.hits
        else _("nothing comes up")
    )
    data: dict[str, JSON] = {
        "hits": [
            {"id": str(h.entity.id), "source": h.source, "reason": h.reason, "text": h.text}
            for h in found.hits
        ],
        "omitted": len(found.omitted),
        "hidden": found.hidden,
    }
    return Out(data=data, md="\n".join([head, *found.lines()]))


@command(
    "lore explain",
    summary="Why an entry (or card, or ruling) does or doesn't come up for a text",
    examples=("didact lore explain lore:ferryman-debt 'we meet the ferryman'",),
)
def lore_explain(
    ctx: Context,
    entry: Annotated[str, "the lore entry or record", Metavar("entry")],
    *text: Annotated[str, "the text to test (default: the last 5 beats)", Metavar("text")],
    gm: Annotated[bool, "as the GM sees it"] = False,
) -> Out:
    from didact.services import lore, play

    repo = open_repo(ctx)
    entity = repo.resolve(entry).entity
    words = " ".join(text)
    if not words.strip():
        current = play.load(repo)
        beats = play.beats(repo, current.session) if current.session else []
        words = " ".join(str(b.get("text", "")) for b in beats[-5:] if play.visible(b, gm))
    lines = lore.explain(repo, entity, words, gm=gm)
    return Out(data={"id": str(entity.id), "lines": list[JSON](lines)}, md="\n".join(lines))


@command(
    "lore import",
    summary="Bring in a lorebook from SillyTavern, KoboldAI, a character card or NovelAI",
    writes=True,
    examples=(
        "didact lore import ~/Downloads/vale-world-info.json",
        "didact lore import tom.card.json --scope world",
        "didact lore import vale.lorebook --dry-run",
    ),
    description=(
        "Reads SillyTavern World Info (KoboldAI writes the same), the lorebook inside a\n"
        "character card (`character_book`), and NovelAI's .lorebook. Each enabled entry becomes\n"
        "a lore entry: its keys, secondary keys and logic, constant, order (priority),\n"
        "probability, group, sticky, cooldown, delay and recursion carry over. Placement and\n"
        "scan settings don't: Didact decides those. Entries go to the campaign unless --scope\n"
        "says otherwise; a name already taken gets a number. Undoable like any change."
    ),
)
def lore_import(
    ctx: Context,
    file: Annotated[str, "the lorebook (JSON)", Metavar("file")],
    *,
    scope: Annotated[str | None, "campaign (default), world, system or global"] = None,
) -> Out:
    import json
    from pathlib import Path

    from didact.services import lorebook, rulings

    path = Path(file).expanduser()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise InvalidError(
            _("{file} isn't JSON: {error}", file=path.name, error=exc),
            hint=_("export the lorebook as JSON from the tool it's in"),
        ) from exc
    repo = open_repo(ctx)
    where = rulings.scope_for(repo, scope) if scope else repo.default_scope("lore")
    cs = changeset(ctx, repo, N_("import the lorebook {file}"), file=path.name)
    done = lorebook.import_book(cs, where, data)
    notes: list[str] = []
    if done.disabled:
        notes.append(
            ngettext("{n} disabled entry left out", "{n} disabled entries left out", done.disabled)
        )
    if done.empty:
        notes.append(
            ngettext(
                "{n} entry left out: no content, or no keys and not constant",
                "{n} entries left out: no content, or no keys and not constant",
                done.empty,
            )
        )
    if done.there:
        notes.append(ngettext("{n} entry already here", "{n} entries already here", done.there))
    if not done.created:
        return Out(
            data={"created": [], "disabled": done.disabled, "empty": done.empty},
            md="\n".join([_("nothing to import from {file}", file=path.name), *notes]),
        )
    told = ngettext(
        "imported {n} lore entry into {scope}",
        "imported {n} lore entries into {scope}",
        len(done.created),
        scope=str(where),
    )
    extra: dict[str, JSON] = {"created": list[JSON](done.created), "scope": str(where)}
    return finish(ctx, cs, done=told, extra=extra, notes=notes)


@command(
    "lore export",
    summary="Write the lore entries here as a SillyTavern World Info lorebook",
    examples=(
        "didact lore export --to vale-world-info.json",
        "didact lore export --secrets --to vale-gm.json",
    ),
    description=(
        "The lore entries in play here (campaign, world, system and global) as World Info JSON,\n"
        "which SillyTavern and KoboldAI read. Secret entries stay out unless --secrets. Timing\n"
        "counted in scenes doesn't travel: World Info counts messages."
    ),
)
def lore_export(
    ctx: Context,
    *,
    to: Annotated[str | None, "write to this file instead of printing", Metavar("file")] = None,
    secrets: Annotated[bool, "the secret entries too"] = False,
) -> Out:
    import json
    from pathlib import Path

    from didact.services import lorebook

    repo = open_repo(ctx)
    found = lorebook.export(repo, secrets=secrets)
    document = json.dumps(found.book, ensure_ascii=False, indent=2) + "\n"
    notes: list[str] = []
    if found.secret:
        notes.append(
            ngettext(
                "{n} secret entry left out (--secrets adds it)",
                "{n} secret entries left out (--secrets adds them)",
                found.secret,
            )
        )
    if found.scenes:
        notes.append(
            ngettext(
                "{n} entry's timing in scenes left out: World Info counts messages",
                "{n} entries' timing in scenes left out: World Info counts messages",
                found.scenes,
            )
        )
    data: dict[str, JSON] = {
        "entries": found.entries,
        "secret": found.secret,
        "notes": list[JSON](notes),
    }
    if not to:
        return Out(data={**data, "book": found.book}, md=document.rstrip())
    target = Path(to).expanduser()
    target.write_text(document, encoding="utf-8")
    lines = [
        ngettext(
            "✔ exported {n} lore entry to {path}",
            "✔ exported {n} lore entries to {path}",
            found.entries,
            path=str(target),
        ),
        *(_("note: {note}", note=n) for n in notes),
    ]
    return Out(data={**data, "file": str(target)}, md="\n".join(lines))
