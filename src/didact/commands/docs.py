"""The code's API documentation: its state, and building it."""

from typing import Annotated

from didact.commands.registry import command
from didact.core.context import Context
from didact.core.i18n import _, ngettext
from didact.core.output import JSON, Out, code


@command(
    "docs status",
    summary="Say whether the code's API documentation is built and up to date",
    examples=("didact docs status",),
)
def docs_status(ctx: Context) -> Out:
    from didact.services import docs

    where = docs.folder(ctx.config)
    found = docs.state(ctx.config)
    said = {
        "current": _("API documentation: up to date ({path})", path=str(where)),
        "stale": _("API documentation: older than the code ({path})", path=str(where)),
        "missing": _("API documentation: not built yet ({path})", path=str(where)),
    }[found]
    lines = [said]
    if found != "current":
        lines.append(_("build it: {command}", command=code("didact docs build")))
    lines.append(
        _(
            "read it: {path}, or the browser app's code button",
            path=str(where / "index.html"),
        )
    )
    return Out(data={"state": found, "path": str(where)}, md="\n".join(lines))


@command(
    "docs build",
    summary="Build the code's API documentation from its docstrings and types (like cargo doc)",
    examples=("didact docs build", "didact docs build --force"),
    description=(
        "Renders every module with pdoc into Didact's cache folder. It's skipped when the\n"
        "documentation is already up to date with the code, unless --force. The browser app\n"
        "serves it at /docs/, rebuilding it first when the code changed."
    ),
)
def docs_build(
    ctx: Context, *, force: Annotated[bool, "build it even if it's up to date"] = False
) -> Out:
    from didact.services import docs

    done = docs.build(ctx.config, force=force)
    data: dict[str, JSON] = {"path": str(done.path), "pages": done.pages, "rebuilt": done.rebuilt}
    if not done.rebuilt:
        return Out(
            data=data, md=_("✔ already up to date: {path}", path=str(done.path / "index.html"))
        )
    return Out(
        data={**data, "seconds": round(done.seconds, 1)},
        md=ngettext(
            "✔ built {n} page in {seconds}s: {path}",
            "✔ built {n} pages in {seconds}s: {path}",
            done.pages,
            seconds=f"{done.seconds:.1f}",
            path=str(done.path / "index.html"),
        ),
    )
