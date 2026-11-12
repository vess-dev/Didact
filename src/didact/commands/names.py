"""Names: roll fresh ones from the packs' tables, and keep a registry so none repeats."""

from typing import Annotated

from didact.commands._common import changeset, finish, open_repo
from didact.commands.registry import Metavar, command
from didact.core.context import Context
from didact.core.errors import UsageError
from didact.core.i18n import N_, _
from didact.core.output import JSON, Out


@command(
    "name",
    summary="Roll fresh names (npc, place, …): none the world uses already, none overused",
    writes=True,
    examples=("didact name npc", "didact name place --count 3"),
    description=(
        "Rolls the name tables the system pack names in `settings.names`, skipping names\n"
        "that records here already have, names registered with `names use`, names offered\n"
        "before, and names LLMs overuse (Elara, Kael, …). Offered names are remembered."
    ),
)
def name(
    ctx: Context,
    kind: Annotated[str, "what needs a name: npc, place, …", Metavar("kind")],
    *,
    count: Annotated[int, "how many names", Metavar("n")] = 1,
) -> Out:
    from didact.services import names

    repo = open_repo(ctx)
    cs = changeset(ctx, repo, N_("offer {kind} names"), kind=kind)
    drawn = names.draw(cs, kind, count, command=ctx.command_line)
    notes = [_("rolled {rolls}", rolls=", ".join(drawn.rolls))]
    if drawn.skipped:
        notes.append(_("skipped: {names}", names=", ".join(drawn.skipped[:6])))
    extra: dict[str, JSON] = {"names": list[JSON](drawn.names)}
    return finish(ctx, cs, done=", ".join(drawn.names), extra=extra, notes=notes)


@command(
    "names check",
    summary="Is a name fresh here? (taken by a record, registered, offered, or overused)",
    examples=("didact names check Elara", "didact names check 'Old Tom'"),
)
def names_check(ctx: Context, *text: Annotated[str, "the name", Metavar("name")]) -> Out:
    from didact.services import names

    wanted = " ".join(text).strip()
    problem = names.check(open_repo(ctx), wanted)
    if problem:
        md = _("{name}: {problem}", name=wanted, problem=problem)
    else:
        md = _("{name}: fresh (nobody here has it)", name=wanted)
    return Out(data={"name": wanted, "fresh": problem is None, "problem": problem}, md=md)


@command(
    "names use",
    summary="Register a name said in play (a passer-by, a ship), so it isn't reused",
    writes=True,
    examples=("didact names use Brannoc --for 'the ferryman'",),
)
def names_use(
    ctx: Context,
    *text: Annotated[str, "the name", Metavar("name")],
    for_: Annotated[str | None, "who or what has it", Metavar("text")] = None,
) -> Out:
    from didact.services import names

    wanted = " ".join(text).strip()
    repo = open_repo(ctx)
    cs = changeset(ctx, repo, N_("name used: {name}"), name=wanted)
    problem = names.use(cs, wanted, for_)
    notes = [_("careful: {name} is {problem}", name=wanted, problem=problem)] if problem else []
    done = _("registered {name}", name=wanted)
    return finish(ctx, cs, done=done, extra={"name": wanted}, notes=notes)


@command(
    "names forget",
    summary="Free a name again: take it out of the registry (registered or offered)",
    writes=True,
    examples=("didact names forget Brannoc", "didact names forget 'Old Tom'"),
)
def names_forget(ctx: Context, *text: Annotated[str, "the name", Metavar("name")]) -> Out:
    from didact.services import names

    wanted = " ".join(text).strip()
    if not wanted:
        raise UsageError(_("which name?"), hint=_("e.g. `didact names forget 'Old Tom'`"))
    repo = open_repo(ctx)
    cs = changeset(ctx, repo, N_("name forgotten: {name}"), name=wanted)
    gone = names.forget(cs, wanted)
    had = [f for f in gone.registered if f]
    if had:
        done = _("forgot {name} ({lists})", name=gone.name, lists=", ".join(had))
    else:
        done = _("forgot {name}", name=gone.name)
    extra: dict[str, JSON] = {
        "name": gone.name,
        "registered": list[JSON](gone.registered),
        "offered": gone.offered,
    }
    return finish(ctx, cs, done=done, extra=extra)


@command(
    "names list",
    summary="Names registered with `names use`, and names offered so far",
    examples=("didact names list",),
)
def names_list(ctx: Context) -> Out:
    from didact.services import names

    repo = open_repo(ctx)
    lines = names.listing(repo)
    return Out(
        data=names.load(repo), md="\n".join(lines) if lines else _("no names registered yet")
    )
