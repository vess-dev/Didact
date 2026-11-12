"""Sheets: templates for describing records, and JSON Schema for them."""

import json
from typing import Annotated

from didact.commands._common import open_repo
from didact.commands.registry import Metavar, command
from didact.core.context import Context
from didact.core.i18n import N_, _
from didact.core.output import JSON, Out, code

CONTENT: dict[str, dict[str, JSON]] = {
    "table": {
        "table": "id",
        "title": "…",
        "dice": "d6",
        "entries": {"1-3": "…", "4-6": {"text": "…"}},
    },
    "check": {
        "check": "id",
        "params": {"who": "ref"},
        "roll": "d20",
        "success": "@roll <= @who.STR",
    },
    "action": {"action": "id", "params": {"target": "ref"}, "steps": [{"roll": "d6", "as": "dmg"}]},
    "procedure": {"procedure": "id", "steps": [{"prompt": "Describe …"}, {"table": "events"}]},
    "deck": {"deck": "id", "cards": ["…", "…"]},
    "bag": {"bag": "id", "tokens": {"pc": 2, "end-of-round": 1}},
    "entry": {"id": "id", "type": "npc", "name": "…", "tags": [], "hp": 4},
}


def _content_help(kind: str) -> str:
    """How to use a pack content skeleton (in the request's language, so not at import time)."""
    helps = {
        "table": _(
            "Add it: `didact pack add <pack> table --data '{…}'`; options: `didact guide packs`."
        ),
        "check": _(
            "Add it: `didact pack add <pack> check --data '{…}'`; "
            "run it with `didact do <id> who=…`."
        ),
        "action": _(
            "Steps: roll, let, set, check, table, if, message, prompt (`didact guide packs`)."
        ),
        "procedure": _("A procedure is steps with prompts: exploration, travel, downtime."),
        "deck": _('Or `"standard": true` for 52 cards.'),
        "bag": _("Draw with `didact bag draw <id>`."),
        "entry": _(
            "A compendium entry: `didact compendium add --data '{…}'`, then `didact spawn <id>`."
        ),
    }
    return helps[kind]


@command(
    "template",
    summary="A fill-in template for a record type (describe it, get it)",
    examples=("didact template pc", "didact template npc --format json"),
    description=(
        "Show the fields a record type has here (the core pack's plus the system's), with a\n"
        'JSON skeleton to fill in. Write "roll" for fields the rules roll, then create it\n'
        "with `didact new <type> --data '{…}'` (add --fill to roll or default the rest)."
    ),
)
def template(
    ctx: Context, type_: Annotated[str, "the record type, e.g. pc, npc, loc", Metavar("type")]
) -> Out:
    from didact.schema.template import describe, skeleton
    from didact.services import sheets

    if type_ in CONTENT:
        shell = CONTENT[type_]
        text = "\n".join(
            [
                _("template: {type} (pack content)", type=type_),
                _content_help(type_),
                "",
                "```json",
                json.dumps(shell, indent=2),
                "```",
            ]
        )
        return Out(data={"type": type_, "skeleton": shell}, md=text)
    repo = open_repo(ctx)
    sh = sheets.sheet(repo, type_)
    if sh.empty:
        text = _(
            "no enabled pack defines `{type}`, so its fields are free-form: {command}",
            type=type_,
            command=code(f"didact new {type_} <name> --set key=value"),
        )
        return Out(data={"type": type_, "fields": [], "skeleton": {"name": "…"}}, md=text)
    shell = skeleton(sh)
    sources = " + ".join(f"{s.pack}.{s.type}" for s in sh.schemas)
    create = code(f"didact new {type_} --data '{{…}}'")
    lines = [
        _("template: {type} ({sources})", type=type_, sources=sources),
        _(
            'Fill in what the description gives; write "roll" where it says 🎲. '
            "Then: {command} (--fill rolls or defaults the rest).",
            command=create,
        ),
        "",
        "```json",
        json.dumps(shell, indent=2, ensure_ascii=False),
        "```",
        "",
        _("fields:"),
    ]
    fields: list[JSON] = []
    for schema in sh.schemas:
        where = "fields" if schema.pack == "core" else f"mechanics.{schema.pack}"
        for spec in schema.fields.values():
            lines.append(f"- `{spec.name}` ({where}): {describe(spec)}")
            fields.append(
                {"name": spec.name, "kind": spec.kind, "block": where, "about": describe(spec)}
            )
    guidance = [s.guidance.strip() for s in sh.schemas if s.guidance.strip()]
    if guidance:
        lines += ["", _("guidance:"), *(f"- {g}" for g in guidance)]
    data: dict[str, JSON] = {
        "type": type_,
        "system": sh.system,
        "fields": fields,
        "skeleton": shell,
        "guidance": list[JSON](guidance),
    }
    return Out(data=data, md="\n".join(lines))


@command(
    "pack schema",
    summary="JSON Schema for a record type here (for editors and for writing --data)",
    examples=("didact pack schema pc", "didact pack schema npc --format json"),
)
def pack_schema(
    ctx: Context, type_: Annotated[str, "the record type, e.g. pc", Metavar("type")]
) -> Out:
    from didact.core.errors import NotFoundError
    from didact.schema.template import json_schema
    from didact.services import sheets

    repo = open_repo(ctx)
    sh = sheets.sheet(repo, type_)
    if sh.empty:
        raise NotFoundError(
            _("no enabled pack defines `{type}`", type=type_),
            hint=_("see `didact pack info <system>`"),
        )
    schema = json_schema(sh)
    text = "```json\n" + json.dumps(schema, indent=2, ensure_ascii=False) + "\n```"
    return Out(data=schema, md=text)


@command(
    "convert",
    summary="Give a record another system's stats (one world, any system)",
    writes=True,
    examples=(
        "didact convert npc:troll --to other-system",
        "didact convert freya --to my-system --fill",
    ),
)
def convert(
    ctx: Context,
    ref: Annotated[str, "the record", Metavar("record")],
    *,
    to: Annotated[str, "the target system pack", Metavar("system")],
    fill: Annotated[bool, "roll or default what doesn't carry over"] = False,
) -> Out:
    from didact.commands._common import changeset, finish, roller
    from didact.services import convert as conversion
    from didact.services import records

    repo = open_repo(ctx)
    located = repo.resolve(ref)
    sheet = conversion.target_sheet(repo, to, located.entity.type)
    cs = changeset(ctx, repo, N_("convert {id} to {to}"), id=str(located.entity.id), to=to)
    report = conversion.Converted()

    def change(entity: object) -> None:
        nonlocal report
        from didact.store.entity import Entity

        assert isinstance(entity, Entity)
        report = conversion.convert(
            entity, sheet, roll=roller(ctx, repo, entity.name) if fill else None
        )

    records.edit(cs, located.path, change)
    notes = []
    if report.copied:
        notes.append(_("carried over: {fields}", fields=", ".join(report.copied)))
    if report.filled:
        notes.append(_("filled: {fields}", fields=", ".join(report.filled)))
    if report.missing:
        notes.append(
            _(
                "still to decide: {fields} (see `didact template {type}`)",
                fields=", ".join(report.missing),
                type=located.entity.type,
            )
        )
    data: dict[str, JSON] = {
        "copied": list[JSON](report.copied),
        "filled": list[JSON](report.filled),
        "missing": list[JSON](report.missing),
    }
    done = _("{record} now has {system} stats", record=located.entity.id, system=to)
    return finish(ctx, cs, done=done, extra=data, notes=notes)
