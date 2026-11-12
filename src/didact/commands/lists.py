"""Oracle lists: Threads, Characters, Features (and any other), with weights and a roll."""

from typing import Annotated

from didact.commands._common import changeset, finish, open_repo
from didact.commands.registry import Metavar, command
from didact.core.context import Context
from didact.core.i18n import N_, _
from didact.core.output import JSON, Out


@command(
    "lists show",
    summary="The oracle's lists (Threads, Characters, …): numbered lines, weights marked",
    examples=("didact lists show", "didact lists show threads"),
)
def lists_show(
    ctx: Context,
    name: Annotated[str | None, "just this list", Metavar("list")] = None,
    *,
    oracle: Annotated[str | None, "which oracle", Metavar("oracle")] = None,
) -> Out:
    from didact.services import lists, oracles
    from didact.tables import lists as engine

    repo = open_repo(ctx)
    chosen = oracles.pick(repo, oracle)
    cfg = lists.config(chosen)
    entity = lists.state(repo, chosen, dry=ctx.dry_run, command=ctx.command_line)
    wanted = [lists.check_name(name)] if name else lists.names(entity, cfg)
    lines: list[str] = []
    data: dict[str, JSON] = {}
    for item in wanted:
        current = lists.entries(entity, item)
        lines += engine.lines(item, current, cfg.method)
        data[item] = list[JSON](current)
    if not lines:
        lines = [_("no lists yet: `didact lists add threads '…'`")]
    return Out(data={"oracle": chosen.qualified, "lists": data}, md="\n".join(lines))


@command(
    "lists add",
    summary="Put an entry on an oracle list (add it again to weight it, up to 3 lines)",
    writes=True,
    examples=(
        "didact lists add threads 'Find who poisoned the well'",
        "didact lists add characters Sweeney --times 2",
        "didact lists add characters-wood 'The Hollow King'",
    ),
    description=(
        "An oracle keeps lists such as threads (goals, open questions) and characters (NPCs,\n"
        "and places or things that act). Any other name starts a list of its own. At the end of a\n"
        "scene, add what mattered; an important element gets more lines (up to 3)."
    ),
)
def lists_add(
    ctx: Context,
    name: Annotated[str, "the list", Metavar("list")],
    *entry: Annotated[str, "the entry", Metavar("entry")],
    times: Annotated[int, "how many lines", Metavar("n")] = 1,
    oracle: Annotated[str | None, "which oracle", Metavar("oracle")] = None,
) -> Out:
    from didact.services import lists, oracles

    repo = open_repo(ctx)
    chosen = oracles.pick(repo, oracle)
    list_name = lists.check_name(name)
    cs = changeset(ctx, repo, N_("list {list}: add {entry}"), list=list_name, entry=" ".join(entry))
    current, note = lists.change(
        cs, chosen, list_name, " ".join(entry), times=max(1, times), remove=False, every=False
    )
    return finish(ctx, cs, done=note, extra={"list": list_name, "entries": list[JSON](current)})


@command(
    "lists drop",
    summary="Take an entry off an oracle list (one line, or every line with --all)",
    writes=True,
    examples=(
        "didact lists drop threads 'Find who poisoned the well' --all",
        "didact lists drop characters Sweeney",
    ),
    description=(
        "Drop a thread once it's resolved, and anything you can't make sense of when it comes\nup."
    ),
)
def lists_drop(
    ctx: Context,
    name: Annotated[str, "the list", Metavar("list")],
    *entry: Annotated[str, "the entry", Metavar("entry")],
    all_: Annotated[bool, "every line of it"] = False,
    oracle: Annotated[str | None, "which oracle", Metavar("oracle")] = None,
) -> Out:
    from didact.services import lists, oracles

    repo = open_repo(ctx)
    chosen = oracles.pick(repo, oracle)
    list_name = lists.check_name(name)
    cs = changeset(
        ctx, repo, N_("list {list}: drop {entry}"), list=list_name, entry=" ".join(entry)
    )
    current, note = lists.change(
        cs, chosen, list_name, " ".join(entry), times=1, remove=True, every=all_
    )
    return finish(ctx, cs, done=note, extra={"list": list_name, "entries": list[JSON](current)})


@command(
    "lists roll",
    summary="Roll on an oracle list: an entry, or a blank line (choose one yourself)",
    writes=True,
    examples=("didact lists roll characters", "didact lists roll threads"),
)
def lists_roll(
    ctx: Context,
    name: Annotated[str, "the list", Metavar("list")],
    *,
    oracle: Annotated[str | None, "which oracle", Metavar("oracle")] = None,
) -> Out:
    from didact.services import lists, oracles

    repo = open_repo(ctx)
    chosen = oracles.pick(repo, oracle)
    list_name = lists.check_name(name)
    cs = changeset(ctx, repo, N_("list {list}: roll"), list=list_name)
    rolled = lists.roll(cs, chosen, list_name, dry=ctx.dry_run, command=ctx.command_line)
    picked = rolled.pick
    if picked.entry is not None:
        result = f"{list_name}: {picked.entry}"
    elif picked.choose:
        result = _("{list}: a blank line: choose an entry (or roll again)", list=list_name)
    else:
        result = _("{list} is empty: use the current context", list=list_name)
    data: dict[str, JSON] = {
        "list": list_name,
        "entry": picked.entry,
        "line": picked.line,
        "choose": picked.choose,
        "rolls": list[JSON](rolled.rolls),
    }
    return Out(data=data, md="\n".join([*rolled.lines, f"{picked.how} → {result}"]))
