"""The web app: `didact serve` opens the library in a browser.

This module only registers and documents the command. The command line runs it itself, as it
does `batch`, and the work is in `didact.web`: nothing heavy is imported here.
"""

from typing import Annotated

from didact.commands.registry import Metavar, command
from didact.core.context import Context
from didact.core.errors import UsageError
from didact.core.i18n import _
from didact.core.output import Out


@command(
    "serve",
    summary="Open the library in a web browser: browse, edit, roll and run any command",
    examples=(
        "didact serve",
        "didact serve --open",
        "didact serve --port 9000 --gm",
        "didact serve --campaign withering",
        "didact serve --demo            # a fresh sample campaign; your library isn't touched",
    ),
    description=(
        "Runs a small web app on this machine until Ctrl-C: records, a graph of their links,\n"
        "the journal, rules and tables, the library, and every command as a form. Changes run\n"
        "the same commands as the command line, so they are checked, logged and undoable, and\n"
        "each one shows its command line. Secrets stay hidden unless the GM view is on (--gm\n"
        "starts with it on). It listens on 127.0.0.1 only unless --host says otherwise.\n"
        "\n"
        "--demo serves the sample campaign (`didact sample`) from a library of its own, with\n"
        "every pack that ships with Didact installed, built afresh each time it starts: a place\n"
        "to try things without touching your own.\n"
        "More: `didact guide web`."
    ),
)
def serve(
    ctx: Context,
    *,
    port: Annotated[int, "the port to listen on", Metavar("n")] = 8765,
    host: Annotated[
        str, "the address to listen on (default: this machine only)", Metavar("address")
    ] = "127.0.0.1",
    open_: Annotated[bool, "open it in a browser tab"] = False,
    gm: Annotated[bool, "start with the GM view on (spoilers shown)"] = False,
    demo: Annotated[bool, "serve a fresh sample campaign instead of your library"] = False,
) -> Out:
    raise UsageError(
        _("serve runs from the command line"), hint=_("run `didact serve` in a terminal")
    )
