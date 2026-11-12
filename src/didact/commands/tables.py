"""Table commands: roll, list, show."""

from typing import Annotated

from didact.commands._common import open_repo
from didact.commands.registry import Metavar, command
from didact.core.context import Context
from didact.core.errors import InvalidError
from didact.core.i18n import _, ngettext
from didact.core.output import JSON, Out
from didact.expr.model import Value


def _inputs(texts: list[str] | None) -> dict[str, Value]:
    found: dict[str, Value] = {}
    for text in texts or []:
        key, sep, raw = text.partition("=")
        if not sep or not key.strip():
            raise InvalidError(
                _("invalid --with {value}", value=repr(text)), hint=_("write `--with name=value`")
            )
        found[key.strip()] = _number(raw.strip())
    return found


def _number(text: str) -> Value:
    for kind in (int, float):
        try:
            return kind(text)
        except ValueError:
            continue
    return text


@command(
    "table roll",
    summary="Roll on a table from the enabled packs (logged, replayable)",
    writes=True,
    examples=(
        "didact table roll weather",
        "didact table roll my-system.poi-name --with poi=Tower",
        "didact table roll scars --with hp_lost=3      # a lookup table",
        "didact table roll wilderness-events --times 2",
    ),
)
def table_roll(
    ctx: Context,
    ref: Annotated[str, "the table: id or pack.id", Metavar("table")],
    *,
    with_: Annotated[
        list[str] | None, "a value for the table: name=value", Metavar("name=value")
    ] = None,
    times: Annotated[int, "roll this many times"] = 1,
    seed: Annotated[str | None, "a fixed stream: same seed, same result", Metavar("text")] = None,
) -> Out:
    from didact.services import tables

    if not 1 <= times <= 100:
        raise InvalidError(_("--times must be 1–100"), hint=_("e.g. --times 3"))
    repo = open_repo(ctx)
    if ctx.dry_run:
        from didact.services import packs

        found = tables.finder(packs.active(repo))(ref, "")
        text = _("dry run: would roll {table} ({title})", table=found.id, title=found.title)
        return Out(data={"dry_run": True, "table": found.id}, md=text)
    outcome = tables.roll_table(
        repo,
        ref,
        inputs=_inputs(with_),
        times=times,
        seed=seed,
        reason=ctx.reason,
        command=ctx.command_line,
    )
    return Out(data=outcome.to_data(), md="\n".join(outcome.lines()))


@command(
    "table list",
    summary="List the tables in the enabled packs",
    examples=("didact table list", "didact table list --pack my-system"),
)
def table_list(
    ctx: Context, *, pack: Annotated[str | None, "only this pack's tables", Metavar("pack")] = None
) -> Out:
    from didact.services import packs

    repo = open_repo(ctx)
    items = [i for i in packs.active(repo).all("table") if pack is None or i.pack == pack]
    if not items:
        return Out(data={"tables": []}, md=_("no tables in the enabled packs"))
    rows: list[JSON] = []
    lines = [ngettext("{n} table:", "{n} tables:", len(items))]
    for item in items:
        title = item.data.get("title") or item.id
        dice = item.data.get("dice") or ("lookup" if item.data.get("lookup") else "weights")
        shown = item.data.get("dice") or (_("lookup") if item.data.get("lookup") else _("weights"))
        lines.append(f"- {item.qualified} · {title} ({shown})")
        rows.append(
            {
                "id": item.qualified,
                "title": title,
                "dice": dice,
                "description": item.data.get("description"),
                "source": item.source,
            }
        )
    return Out(data={"tables": rows}, md="\n".join(lines))


@command(
    "table show",
    summary="Show a table's entries",
    examples=("didact table show weather",),
)
def table_show(ctx: Context, ref: Annotated[str, "the table", Metavar("table")]) -> Out:
    from didact.services import packs, tables

    repo = open_repo(ctx)
    table = tables.finder(packs.active(repo))(ref, "")
    how = table.dice or (
        _("lookup by {columns}", columns=", ".join(table.lookup)) if table.lookup else _("weights")
    )
    lines = [f"{table.id} · {table.title} ({how})"]
    if table.source:
        lines.append(_("source: {source}", source=table.source))
    if table.columns:
        lines.append(_("columns: {columns}", columns=", ".join(table.columns)))
    for entry in table.entries:
        key = entry.band.label if entry.band else _("weight {weight}", weight=entry.weight)
        if entry.table:
            line = _("- {key}: {text} → table {table}", key=key, text=entry.text, table=entry.table)
        elif entry.times:
            line = _(
                "- {key}: {text} (roll {times} more)", key=key, text=entry.text, times=entry.times
            )
        else:
            line = f"- {key}: {entry.text}"
        lines.append(line)
    if table.lookup:
        lines.append(
            _(
                "(a lookup table: `didact table roll {table} --with {column}=…`)",
                table=table.id,
                column=table.lookup[0],
            )
        )
    data: dict[str, JSON] = {
        "id": table.id,
        "title": table.title,
        "dice": table.dice,
        "data": table.data,
    }
    return Out(data=data, md="\n".join(lines))
