"""Generators (`gen …`) and character creation (`char …`): drafts first, commit when ready."""

import json
from typing import TYPE_CHECKING, Annotated, Literal

from didact.commands._common import changeset, finish, open_repo, parse_data
from didact.commands.registry import Metavar, command
from didact.core.context import Context
from didact.core.errors import InvalidError, NotFoundError
from didact.core.i18n import N_, _, ngettext
from didact.core.output import JSON, Out
from didact.core.phrases import english, translated
from didact.store.changeset import Changeset

if TYPE_CHECKING:
    from didact.services.drafts import Stored

type Kind = Literal["generator", "chargen"]


def _params(args: tuple[str, ...]) -> dict[str, str]:
    found: dict[str, str] = {}
    for text in args:
        name, sep, value = text.partition("=")
        if not sep or not name.strip():
            raise InvalidError(
                _("can't read {text}", text=repr(text)), hint=_("parameters look like name=value")
            )
        found[name.strip()] = value.strip()
    return found


def _shown(ctx: Context, cs: Changeset, stored: Stored, done: str) -> Out:
    from didact.services import drafts

    shown = drafts.lines(cs.repo, stored, full=ctx.detail == "full")
    body = [*stored.lines, "", *shown] if stored.lines else shown
    data: dict[str, JSON] = {"draft": stored.to_data()}
    if cs.is_empty():
        return Out(data=data, md="\n".join(body))
    out = finish(ctx, cs, done=done, extra=data)
    return Out(data=out.data, md="\n".join([*body, out.md]), ok=out.ok)


def _start(
    ctx: Context,
    kind: Kind,
    ref: str,
    args: tuple[str, ...],
    prefill: str | None,
    auto: bool,
    *,
    target: str | None = None,
) -> Out:
    from didact.services import drafts

    repo = open_repo(ctx)
    said = N_("gen {ref}") if kind == "generator" else N_("char {ref}")
    cs = changeset(ctx, repo, said, ref=ref)
    given = parse_data(prefill, "--prefill") or {}
    stored = drafts.start(
        cs, kind, ref, _params(args), given, auto=auto, dry=ctx.dry_run,
        command=ctx.command_line, target=target,
    )  # fmt: skip
    if target is not None:
        cs.say(N_("draft #{draft}: {record} by {source}"), draft=stored.id, record=target,
               source=stored.source)  # fmt: skip
    else:
        cs.say(N_("draft #{draft} from {source}"), draft=stored.id, source=stored.source)
    return _shown(ctx, cs, stored, _("draft #{draft}", draft=stored.id))


def _choose(ctx: Context, draft_id: str, value: str) -> Out:
    from didact.services import drafts

    repo = open_repo(ctx)
    stored = drafts.load(repo, draft_id)
    cs = changeset(ctx, repo, N_("#{draft}: {value}"), draft=stored.id, value=value)
    drafts.choose(cs, stored, value, dry=ctx.dry_run, command=ctx.command_line)
    return _shown(ctx, cs, stored, _("#{draft}: {value}", draft=stored.id, value=value))


def _roll(ctx: Context, draft_id: str, one: bool) -> Out:
    from didact.services import drafts

    repo = open_repo(ctx)
    stored = drafts.load(repo, draft_id)
    choice = stored.draft.open
    cs = (
        changeset(ctx, repo, N_("#{draft}: roll {choice}"), draft=stored.id, choice=choice.name)
        if one and choice is not None
        else changeset(ctx, repo, N_("#{draft}: roll the rest"), draft=stored.id)
    )
    drafts.roll_open(cs, stored, dry=ctx.dry_run, command=ctx.command_line, one=one)
    done = (
        _("#{draft}: rolled {choice}", draft=stored.id, choice=choice.name)
        if one and choice is not None
        else _("#{draft}: rolled the rest", draft=stored.id)
    )
    return _shown(ctx, cs, stored, done)


def _edit(
    ctx: Context,
    draft_id: str,
    changes: tuple[str, ...],
    drop: list[str] | None,
    add: list[str] | None,
) -> Out:
    from didact.services import drafts

    repo = open_repo(ctx)
    stored = drafts.load(repo, draft_id)
    added = [parse_data(a, "--add") or {} for a in add or []]
    done = drafts.edit(stored, list(changes), drop or [], added)
    if not done:
        raise InvalidError(
            _("nothing to change"),
            hint=_("key.field=value, --drop <key> or --add '{json}'", json="{…}"),
        )
    edited = "; ".join(english(d) for d in done)
    cs = changeset(ctx, repo, N_("#{draft}: {changes}"), draft=stored.id, changes=edited)
    drafts.save(cs, stored)
    return _shown(ctx, cs, stored, "; ".join(translated(d) for d in done))


def _commit(ctx: Context, draft_id: str, force: bool) -> Out:
    from didact.services import drafts, sheets

    sheets.check_force(force, ctx.reason)
    repo = open_repo(ctx)
    stored = drafts.load(repo, draft_id)
    cs = changeset(
        ctx, repo, N_("commit #{draft} from {source}"), draft=stored.id, source=stored.source
    )
    cs.forced = force
    ids = drafts.commit(cs, stored, force=force)
    if stored.target is not None:
        main = stored.draft.main()
        changed = ", ".join(
            f"{k} {drafts.short(stored.base.get(k))} → {drafts.short(v)}"
            for k, v in main.fields.items()
            if stored.base.get(k) != v
        )
        done = _("{record} advanced: {changes}", record=stored.target, changes=changed)
        if len(ids) > 1:  # and made records beside it (a new bond's thread)
            done += " " + _("(made {records})", records=", ".join(ids[1:]))
        return finish(ctx, cs, done=done, extra={"records": list[JSON](ids)})
    listed = ", ".join(ids[:8]) + (", …" if len(ids) > 8 else "")
    done = ngettext(
        "#{draft} committed: {n} record ({records})",
        "#{draft} committed: {n} records ({records})",
        len(ids),
        draft=stored.id,
        records=listed,
    )
    return finish(ctx, cs, done=done, extra={"records": list[JSON](ids)})


def _discard(ctx: Context, draft_id: str) -> Out:
    from didact.services import drafts

    repo = open_repo(ctx)
    stored = drafts.load(repo, draft_id)
    cs = changeset(ctx, repo, N_("discard #{draft}"), draft=stored.id)
    drafts.discard(cs, stored)
    return finish(ctx, cs, done=_("#{draft} discarded", draft=stored.id))


def _show(ctx: Context, draft_id: str) -> Out:
    from didact.core.errors import DidactError
    from didact.services import drafts, packs

    repo = open_repo(ctx)
    stored = drafts.load(repo, draft_id)
    try:
        title = packs.active(repo).find(stored.kind, stored.source).data.get("title")
    except DidactError:
        title = None  # its pack is gone: the draft still shows
    try:
        back: JSON = drafts.last_step(repo, stored).event.seq  # what `back` would take back
    except DidactError:
        back = None  # at its first step
    return Out(
        data={"draft": stored.to_data(), "title": title, "back": back},
        md="\n".join(drafts.lines(repo, stored, full=ctx.detail == "full")),
    )


def _back(ctx: Context, draft_id: str) -> Out:
    from didact.services import drafts
    from didact.store.events import shown

    repo = open_repo(ctx)
    stored = drafts.load(repo, draft_id)
    step = drafts.last_step(repo, stored)
    rolls = [f"#r{r.data.get('roll')}" for r in step.rolls]
    said = shown(step.event)
    if ctx.dry_run:
        text = _(
            "dry run: would go back a step, taking back {event} ({summary})",
            event=step.event.label,
            summary=said,
        )
        if rolls:
            text += " " + _("and marking {rolls} undone", rolls=", ".join(rolls))
        data: dict[str, JSON] = {
            "dry_run": True,
            "event": step.event.seq,
            "rolls": list[JSON](rolls),
        }
        return Out(data=data, md=text)
    reason = ctx.reason or f"back a step in #{stored.id}"
    done = drafts.back(repo, step, reason=reason, command=ctx.command_line)
    now = drafts.load(repo, stored.id)
    text = _(
        "#{draft}: went back a step (took back {event}: {summary})",
        draft=now.id,
        event=step.event.label,
        summary=said,
    )
    if rolls:
        text += " " + _("and marked {rolls} undone", rolls=", ".join(rolls))
    data = {
        "draft": now.to_data(),
        "event": done[0].seq,  # undoing it takes the step again
        "undone": [step.event.seq, *(r.seq for r in step.rolls)],
        "events": [d.seq for d in done],
    }
    lines = drafts.lines(repo, now, full=ctx.detail == "full")
    lines.append(_("✔ {done} ({event})", done=text, event=done[0].label))
    return Out(data=data, md="\n".join(lines))


# ---------------------------------------------------------------------------- gen


@command(
    "gen list",
    summary="The generators the enabled packs bring (regions, dungeons, settlements, …)",
    examples=("didact gen list",),
)
def gen_list(ctx: Context) -> Out:
    from didact.services import drafts

    found = drafts.items(open_repo(ctx), "generator")
    lines = [f"- {g.qualified}: {g.data.get('title', g.id)}" for g in found] or [
        _("no generators here")
    ]
    items: list[JSON] = [
        {
            "id": g.qualified,
            "title": g.data.get("title"),
            "help": g.data.get("help"),
            "params": g.data.get("params") or {},  # name=value arguments: kind, default, help
        }
        for g in found
    ]
    return Out(data={"generators": items}, md="\n".join(lines))


@command(
    "gen run",
    summary="Run a generator into a draft (#g7): nothing is written until `gen commit`",
    writes=True,
    examples=(
        "didact gen run my-system.pointcrawl",
        "didact gen run my-system.pointcrawl size=6 --auto",
        'didact gen run my-system.region --prefill \'{"terrain": "Swamps"}\' --auto',
    ),
    description=(
        "Every roll is logged. `--prefill` gives decisions in advance (a choice takes the\n"
        "option it names; a list gives one value per occurrence); `--auto` lets the dice make\n"
        "the choices the procedure would otherwise ask about. Then `gen show`, `gen edit`,\n"
        "`gen commit`."
    ),
)
def gen_run(
    ctx: Context,
    generator: Annotated[str, "the generator", Metavar("generator")],
    *args: Annotated[str, "parameters: name=value", Metavar("name=value")],
    prefill: Annotated[str | None, "decisions already made, as JSON", Metavar("json")] = None,
    auto: Annotated[bool, "roll every choice instead of asking"] = False,
) -> Out:
    return _start(ctx, "generator", generator, args, prefill, auto)


@command(
    "gen show",
    summary="Show a draft: its entities, map and open questions",
    examples=("didact gen show g7",),
)
def gen_show(ctx: Context, draft: Annotated[str, "the draft, e.g. g7", Metavar("draft")]) -> Out:
    return _show(ctx, draft)


@command(
    "gen choose",
    summary="Answer the choice a draft is waiting for, and carry on",
    writes=True,
    examples=("didact gen choose g7 Swamps",),
)
def gen_choose(
    ctx: Context,
    draft: Annotated[str, "the draft", Metavar("draft")],
    *value: Annotated[str, "the answer", Metavar("value")],
) -> Out:
    return _choose(ctx, draft, " ".join(value))


@command(
    "gen roll",
    summary="Let the dice make a draft's open choice (and any after it)",
    writes=True,
    examples=("didact gen roll g7", "didact gen roll g7 --one"),
)
def gen_roll(
    ctx: Context,
    draft: Annotated[str, "the draft", Metavar("draft")],
    *,
    one: Annotated[bool, "roll the open choice only, then stop at the next one"] = False,
) -> Out:
    return _roll(ctx, draft, one)


@command(
    "gen back",
    summary="Go back a step in a draft: take back its last answer, roll or edit",
    writes=True,
    examples=("didact gen back g7", "didact gen back g7 --dry-run"),
    description=(
        "The step is undone (the history keeps it: `redo` brings it back), and the rolls it\n"
        "made are marked undone, so the draft asks that question again. A draft's first step\n"
        "can't be taken back: discard the draft to start again."
    ),
)
def gen_back(ctx: Context, draft: Annotated[str, "the draft", Metavar("draft")]) -> Out:
    return _back(ctx, draft)


@command(
    "gen edit",
    summary="Change a draft before committing: names, fields, drop or add entities",
    writes=True,
    examples=(
        "didact gen edit g7 poi-1.name='Amber Grave' poi-2.fields.feature='a sunken bell'",
        "didact gen edit g7 --drop poi-4",
        'didact gen edit g7 --add \'{"type": "npc", "name": "Old Gannet"}\'',
    ),
)
def gen_edit(
    ctx: Context,
    draft: Annotated[str, "the draft", Metavar("draft")],
    *changes: Annotated[str, "key.field=value", Metavar("key.field=value")],
    drop: Annotated[list[str] | None, "remove an entity (and its links)", Metavar("key")] = None,
    add: Annotated[
        list[str] | None, "add an entity: JSON with type and name", Metavar("json")
    ] = None,
) -> Out:
    return _edit(ctx, draft, changes, drop, add)


@command(
    "gen commit",
    summary="Write a draft: its records, links and map, in one undoable change",
    writes=True,
    examples=("didact gen commit g7",),
)
def gen_commit(
    ctx: Context,
    draft: Annotated[str, "the draft", Metavar("draft")],
    *,
    force: Annotated[bool, "allow values the sheets don't (needs --reason)"] = False,
) -> Out:
    return _commit(ctx, draft, force)


@command(
    "gen discard", summary="Throw a draft away", writes=True, examples=("didact gen discard g7",)
)
def gen_discard(ctx: Context, draft: Annotated[str, "the draft", Metavar("draft")]) -> Out:
    return _discard(ctx, draft)


@command(
    "gen drafts",
    summary="Drafts waiting to be committed (generators and characters)",
    examples=("didact gen drafts",),
)
def gen_drafts(ctx: Context) -> Out:
    from didact.services import drafts

    found = drafts.listing(open_repo(ctx))
    items: list[JSON] = [
        {
            "id": s.id,
            "kind": s.kind,
            "source": s.source,
            "waiting": s.waiting,
            "name": s.draft.entities[0].name if s.draft.entities else "",  # a character's name
        }
        for s in found
    ]
    if not found:
        return Out(data={"drafts": [], "items": items}, md=_("no drafts"))
    lines = [
        _(
            "- #{draft} from {source} (waiting for {waiting})",
            draft=s.id,
            source=s.source,
            waiting=s.waiting,
        )
        if s.waiting
        else _("- #{draft} from {source} (ready to commit)", draft=s.id, source=s.source)
        for s in found
    ]
    return Out(data={"drafts": [s.id for s in found], "items": items}, md="\n".join(lines))


# ---------------------------------------------------------------------------- char


def _chargen_for(ctx: Context, ref: str | None) -> str:
    from didact.services import drafts, sheets

    if ref:
        return ref
    repo = open_repo(ctx)
    found = drafts.creations(repo)
    system = sheets.active_system(repo)
    pcs = [c for c in found if c.pack == system and c.data.get("creates", "pc") == "pc"]
    if pcs:
        return pcs[0].qualified
    if len(found) == 1:
        return found[0].qualified
    names = ", ".join(c.qualified for c in found) or _("none")
    raise NotFoundError(_("which character creation?"), hint=_("name one: {names}", names=names))


@command(
    "char list",
    summary="The character creations the enabled packs bring (player characters, hirelings, …)",
    examples=("didact char list", "didact char new my-system.hireling --mode random"),
)
def char_list(ctx: Context) -> Out:
    from didact.services import drafts, sheets

    repo = open_repo(ctx)
    found = drafts.creations(repo)
    try:
        default = _chargen_for(ctx, None) if found else None
    except NotFoundError:  # several, and none is the system's PC creation
        default = None
    lines = [
        f"- {c.qualified}: {c.data.get('title', c.id)}"
        + (" " + _("(the default)") if c.qualified == default else "")
        for c in found
    ] or [_("no character creation here")]
    items: list[JSON] = [
        {
            "id": c.qualified,
            "title": c.data.get("title"),
            "help": c.data.get("help"),
            "creates": c.data.get("creates", "pc"),
            "modes": c.data.get("modes") or ["random", "guided"],
            "system": c.pack == sheets.active_system(repo),
        }
        for c in found
    ]
    advancements: list[JSON] = [
        {"id": c.qualified, "title": c.data.get("title"), "advances": c.data.get("advances")}
        for c in drafts.items(repo, "chargen")
        if "advances" in c.data
    ]
    data: dict[str, JSON] = {"chargens": items, "default": default, "advancements": advancements}
    return Out(data=data, md="\n".join(lines))


@command(
    "char new",
    summary="Create a character the system's way: random, or guided step by step (draft #c3)",
    writes=True,
    examples=(
        "didact char new                         # the system's PC creation, guided",
        "didact char new --mode random           # roll everything",
        'didact char new --prefill \'{"name": "Freya", "background": "Cutpurse"}\' --mode random',
    ),
    description=(
        "Guided mode stops at each choice (background, swap, name, …): answer with `char\n"
        "choose c3 <value>` or let the dice decide with `char roll c3`. `--prefill` keeps what\n"
        "the player already decided. Nothing is written until `char commit c3`."
    ),
)
def char_new(
    ctx: Context,
    chargen: Annotated[
        str | None, "which creation (default: the system's PC)", Metavar("chargen")
    ] = None,
    *args: Annotated[str, "parameters: name=value", Metavar("name=value")],
    mode: Annotated[
        Literal["random", "guided"], "roll everything, or ask at each choice"
    ] = "guided",
    prefill: Annotated[str | None, "decisions already made, as JSON", Metavar("json")] = None,
    template: Annotated[
        str | None, "start from a pregen: a compendium entry or a record", Metavar("entry")
    ] = None,
) -> Out:
    if template:
        prefill = _from_template(ctx, template, prefill)
    return _start(ctx, "chargen", _chargen_for(ctx, chargen), args, prefill, mode == "random")


def _from_template(ctx: Context, ref: str, prefill: str | None) -> str:
    """A pregen, archetype or gear pack as prefill: its name and fields; `--prefill` wins."""
    from didact.core.errors import DidactError
    from didact.services import packs

    repo = open_repo(ctx)
    found: dict[str, JSON]
    try:
        entry = packs.active(repo).find("entry", ref)
        skip = ("id", "type", "tags", "body", "source")
        found = {k: v for k, v in entry.data.items() if k not in skip}
    except DidactError:
        entity = repo.resolve(ref).entity
        found = {"name": entity.name, **entity.fields}
        for block in entity.mechanics.values():
            if isinstance(block, dict):
                found |= block
    return json.dumps(found | (parse_data(prefill, "--prefill") or {}))


@command("char show", summary="Show a character draft", examples=("didact char show c3",))
def char_show(ctx: Context, draft: Annotated[str, "the draft, e.g. c3", Metavar("draft")]) -> Out:
    return _show(ctx, draft)


@command(
    "char choose",
    summary="Answer the choice a character draft is waiting for",
    writes=True,
    examples=(
        "didact char choose c3 Cutpurse",
        "didact char choose c3 'STR DEX'",
        "didact char choose c3 Freya",
    ),
)
def char_choose(
    ctx: Context,
    draft: Annotated[str, "the draft", Metavar("draft")],
    *value: Annotated[str, "the answer", Metavar("value")],
) -> Out:
    return _choose(ctx, draft, " ".join(value))


@command(
    "char roll",
    summary="Let the dice make a character draft's open choices",
    writes=True,
    examples=("didact char roll c3", "didact char roll c3 --one"),
)
def char_roll(
    ctx: Context,
    draft: Annotated[str, "the draft", Metavar("draft")],
    *,
    one: Annotated[bool, "roll the open choice only, then stop at the next one"] = False,
) -> Out:
    return _roll(ctx, draft, one)


@command(
    "char back",
    summary="Go back a step in a character draft: take back its last answer, roll or edit",
    writes=True,
    examples=("didact char back c3", "didact char back c3 --dry-run"),
    description=(
        "The step is undone (the history keeps it: `redo` brings it back), and the rolls it\n"
        "made are marked undone, so the draft asks that question again. A draft's first step\n"
        "can't be taken back: discard the draft to start again."
    ),
)
def char_back(ctx: Context, draft: Annotated[str, "the draft", Metavar("draft")]) -> Out:
    return _back(ctx, draft)


@command(
    "char edit",
    summary="Change a character draft before committing",
    writes=True,
    examples=("didact char edit c3 character.name=Freya character.fields.pronouns=she/her",),
)
def char_edit(
    ctx: Context,
    draft: Annotated[str, "the draft", Metavar("draft")],
    *changes: Annotated[str, "key.field=value", Metavar("key.field=value")],
) -> Out:
    return _edit(ctx, draft, changes, None, None)


@command(
    "char commit",
    summary="Write a character draft as a record (checked against its sheet)",
    writes=True,
    examples=("didact char commit c3",),
)
def char_commit(
    ctx: Context,
    draft: Annotated[str, "the draft", Metavar("draft")],
    *,
    force: Annotated[bool, "allow values the sheet doesn't (needs --reason)"] = False,
) -> Out:
    return _commit(ctx, draft, force)


@command(
    "char discard",
    summary="Throw a character draft away",
    writes=True,
    examples=("didact char discard c3",),
)
def char_discard(ctx: Context, draft: Annotated[str, "the draft", Metavar("draft")]) -> Out:
    return _discard(ctx, draft)


@command(
    "char check",
    summary="Check a character against its sheet: values, ranges, required fields, slots",
    examples=("didact char check freya",),
)
def char_check(ctx: Context, who: Annotated[str, "the character", Metavar("record")]) -> Out:
    from didact.schema import fields as kinds
    from didact.services import inventory, sheets

    repo = open_repo(ctx)
    entity = repo.resolve(who).entity
    sh = sheets.sheet(repo, entity.type)
    problems = list(sheets.problems(entity, sh))  # English, for the data
    shown = list(problems)  # the same, for people to read
    bag = inventory.find_bag(entity, sh)
    room = inventory.room(entity, sh, bag)
    if room.capacity is not None and room.used > room.capacity:
        problems.append(f"{bag.spec.label}: {room.used}/{room.capacity} slots (over)")
        shown.append(
            _(
                "{bag}: {used}/{capacity} slots (over)",
                bag=bag.spec.label,
                used=room.used,
                capacity=room.capacity,
            )
        )
    for schema in sh.schemas:
        block = entity.fields if schema.pack == "core" else entity.mechanics.get(schema.pack)
        stored = block if isinstance(block, dict) else {}
        for spec in schema.fields.values():
            if (
                spec.stored
                and spec.opt("roll") is not None
                and spec.name not in stored
                and spec.kind != "slots"
            ):
                fix = f"`didact set {entity.id} {spec.name}=roll`"
                problems.append(f"{spec.name}: missing (the system rolls it: {fix})")
                shown.append(
                    _("{field}: missing (the system rolls it: {fix})", field=spec.name, fix=fix)
                )
            elif spec.kind in kinds.VALUED and spec.name not in stored and spec.opt("required"):
                problems.append(f"{spec.name}: missing")
                shown.append(_("{field}: missing", field=spec.name))
    if not problems:
        return Out(
            data={"id": str(entity.id), "problems": []},
            md=_("✔ {name}'s sheet checks out", name=entity.name),
        )
    return Out(
        data={"id": str(entity.id), "problems": list[JSON](problems)},
        md="\n".join(
            [
                ngettext(
                    "{name}: {n} problem", "{name}: {n} problems", len(shown), name=entity.name
                ),
                *(f"- {p}" for p in shown),
            ]
        ),
        ok=False,
    )


@command(
    "char advance",
    summary="Advance a character the system's way (level up, new move, …); logged and undoable",
    writes=True,
    examples=(
        "didact char advance freya                  # a level-up, step by step (draft #c4)",
        "didact char advance freya --mode random    # the dice decide what can be rolled",
        "didact char advance freya how=reroll attr=WIL trigger='drank the murderer's spirit'",
    ),
    description=(
        "A system with a level-up procedure (`advances:` in its chargen/) starts a draft\n"
        "that changes the character: answer its choices with `char choose c4 <value>`, then\n"
        "`char commit c4` writes what changed. Other systems run their advance rule at once."
    ),
)
def char_advance(
    ctx: Context,
    who: Annotated[str, "the character", Metavar("record")],
    *args: Annotated[str, "more for the rule: name=value", Metavar("name=value")],
    mode: Annotated[
        Literal["random", "guided"], "a level-up draft: roll what can be rolled, or ask each"
    ] = "guided",
    prefill: Annotated[str | None, "decisions already made, as JSON", Metavar("json")] = None,
) -> Out:
    from didact.commands.rules import do
    from didact.services import drafts

    repo = open_repo(ctx)
    entity = repo.resolve(who).entity
    procedure = drafts.advancement(repo, entity.type)
    if procedure is not None:
        return _start(
            ctx, "chargen", procedure.qualified, args, prefill, mode == "random",
            target=str(entity.id),
        )  # fmt: skip
    rules_found = [
        c.data["advance"]
        for c in drafts.items(repo, "chargen")
        if c.data.get("creates", "pc") == entity.type and isinstance(c.data.get("advance"), dict)
    ]
    if not rules_found:
        raise NotFoundError(
            _("this system has no advancement for a {type}", type=entity.type),
            hint=_("packs set it in chargen: advance: {spec}", spec="{rule: …}"),
        )
    rule = rules_found[0]
    assert isinstance(rule, dict)
    return do(ctx, f"{rule['rule']}", f"who={entity.id}", *args)


@command(
    "char import",
    summary='A character from a full JSON description ("roll" values are rolled, then checked)',
    writes=True,
    examples=(
        'didact char import --data \'{"name": "Freya", "STR": "roll", "DEX": 14, "hp": "roll"}\'',
    ),
)
def char_import(
    ctx: Context,
    *,
    data: Annotated[str, "the character as JSON", Metavar("json")],
    type_: Annotated[str, "record type", Metavar("type")] = "pc",
    force: Annotated[bool, "allow values the sheet doesn't (needs --reason)"] = False,
) -> Out:
    from didact.commands.records import new

    return new(ctx, type_, None, data=data, fill=True, force=force)
