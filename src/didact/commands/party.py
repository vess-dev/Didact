"""The party: PCs, companions and hirelings."""

from typing import Annotated, Literal

from didact.commands._common import changeset, finish, open_repo
from didact.commands.registry import Metavar, command
from didact.core import labels
from didact.core.context import Context
from didact.core.i18n import N_, _
from didact.core.output import JSON, Out


@command(
    "party show",
    summary="Who's in the party: PCs, companions and hirelings, with their numbers",
    examples=("didact party show", "didact party show --gm"),
)
def party_show(ctx: Context, *, gm: Annotated[bool, "include secret members"] = False) -> Out:
    from didact.services import knowledge, party, sheets

    repo = open_repo(ctx)
    found = party.members(repo, gm=gm)
    hid = knowledge.NOTHING if gm else knowledge.unknown(repo)
    lines = (
        [_("Party ({count}):", count=len(found))]
        if found
        else [_("the party is empty: `didact new pc <name>`")]
    )
    items: list[JSON] = []
    for member in found:
        sheet = sheets.sheet(repo, member.entity.type)
        shown = member.entity if gm else knowledge.player_copy(member.entity, sheet, hid)[0]
        stats = sheets.stat_line(shown, sheet)
        lines.append(
            f"- {member.entity.name} [{member.entity.id}] "
            f"({labels.inline(member.role, labels.party_role(member.role))})"
            + (f" · {stats}" if stats else "")
        )
        items.append(
            {
                "id": str(member.entity.id),
                "name": member.entity.name,
                "role": member.role,
                "stats": list[JSON](sheets.stat_items(shown, sheet)),
            }
        )
    gone = party.departed(repo)
    if gone:
        who_left = ", ".join(f"{e.get('id')} ({e.get('why')})" for e in gone)
        lines.append(_("left: {members}", members=who_left))
    return Out(data={"members": items, "left": list[JSON](gone)}, md="\n".join(lines))


@command(
    "party add",
    summary="Someone joins the party: a companion, a hireling, or a PC coming back",
    writes=True,
    examples=(
        "didact party add old-gannet --as hireling",
        "didact party add npc:wren --as companion",
        "didact party add freya                # a PC who had left",
    ),
)
def party_add(
    ctx: Context,
    who: Annotated[str, "the record", Metavar("record")],
    *,
    as_: Annotated[Literal["companion", "hireling", "pc"] | None, "their role"] = None,
) -> Out:
    from didact.services import party

    repo = open_repo(ctx)
    entity = repo.resolve(who, of="pc" if as_ == "pc" else None).entity  # `--as pc`: only a PC
    role = as_ or ("pc" if entity.type == "pc" else "companion")
    cs = changeset(ctx, repo, N_("{name} joins the party"), name=entity.name)
    party.add(cs, entity, role)
    extra: dict[str, JSON] = {"id": str(entity.id), "role": role}
    done = _("{name} joins the party ({role})", name=entity.name, role=_role(role))
    return finish(ctx, cs, done=done, extra=extra)


@command(
    "party remove",
    summary="Someone leaves the party (died, retired, dismissed, …); the record stays",
    writes=True,
    examples=(
        "didact party remove old-gannet --why dismissed",
        "didact party remove freya --why died",
    ),
)
def party_remove(
    ctx: Context,
    who: Annotated[str, "the record", Metavar("record")],
    *,
    why: Annotated[str | None, "why they left", Metavar("text")] = None,
) -> Out:
    from didact.services import party

    repo = open_repo(ctx)
    entity = repo.resolve(who).entity
    cs = changeset(ctx, repo, N_("{name} leaves the party"), name=entity.name)
    role = party.remove(cs, entity, why)
    if why:
        done = _(
            "{name} leaves the party ({role}: {why})", name=entity.name, role=_role(role), why=why
        )
    else:
        done = _("{name} leaves the party ({role})", name=entity.name, role=_role(role))
    return finish(ctx, cs, done=done, extra={"id": str(entity.id), "role": role})


def _role(role: str) -> str:
    """A role as `--as` takes it, in English; else in the reader's language."""
    return labels.inline(role, labels.party_role(role))
