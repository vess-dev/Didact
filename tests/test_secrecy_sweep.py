"""The secrecy sweep: a marker planted in every kind of hiding place never reaches a player's
view, from any command, page or tool.

The markers and where they hide come from the site export's sweep (`tests/test_site_export.py`),
so both check the same places: `QX<n>`, each in one hiding place, so a leak names its source.
That sweep also checks that the GM's views show every marker. The transcript is left out here:
it's the conversation the player took part in, and the app shows it to them. The site, which
may be shared, leaves it out too.
"""

import html
import json
import re
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from didact.web.app import App
from didact.web.server import WebServer
from tests.conftest import Cli
from tests.test_site_export import HIDING_PLACES, MARKER, plant
from tests.test_web import Browser

PLAYERS_SEE = {"QX8"}  # the transcript
PUBLIC = ("npc:tom", "pc:freya", "loc:the-mill", "loc:the-wood", "item:ring")


def _plant(cli: Cli, home: Path) -> None:
    plant(cli, home)
    done = cli("combat", "start", "--party", "tom")  # a fight, with Tom's numbers in it
    assert done.code == 0, done.err


CLI_READS: tuple[tuple[str, ...], ...] = (
    *(("show", ref) for ref in PUBLIC),
    ("find", "tom"),  # the words of each secret, not its marker: a query is echoed back
    ("find", "heir"),
    ("find", "poisoned"),
    ("find", "relic"),
    ("find", "spy"),
    ("find", "coffer"),
    ("find", "ring"),
    ("search", "well"),
    ("search", "heir"),
    ("search", "raiders"),
    ("search", "shrine"),
    ("search", "flood"),
    ("search", "ambush"),
    ("search", "drowned"),
    ("brief",),
    ("map",),
    ("timeline",),
    ("session", "show", "1"),
    ("session", "list"),
    ("export", "--as", "story"),
    ("export", "--as", "lonelog"),
    ("lore", "export"),
    ("party", "show"),
    ("combat", "status"),
    ("quest", "list"),
    ("track", "list"),
    ("sheet", "freya"),
    ("where", "ring"),
    ("graph", "tom"),
    ("inv", "show", "tom"),
    ("inv", "show", "the mill"),
    ("world", "show"),
    ("lore", "scan", "Tom went to the mill with the heir and the spy"),
)
PAGES = (
    "/",
    "/status",
    "/records",
    *(f"/record/{ref}" for ref in PUBLIC),
    "/record/npc:qx1-heir",
    "/graph",
    "/api/graph",
    "/api/graph?mode=map",
    "/api/graph?focus=npc:tom&depth=2",
    "/journal",
    "/journal/1",
    "/search?q=well",
    "/search?q=heir",
    "/search?q=raiders",
    "/search?q=poisoned",
    "/library",
    "/library?history=2000",
    "/library/jump?to=e1",  # every change after the first, as the player view names them
    "/drafts",
    "/drafts/new",
    "/settings",
    "/commands/show",  # the records offered to pick from
    "/commands/gen/show",  # and the drafts
    "/commands/campaign/fork",  # and the save points
)


def _leaks(where: str, text: str) -> Iterator[str]:
    for marker in sorted({m.upper() for m in MARKER.findall(text)} - PLAYERS_SEE):
        yield f"{where}: {marker} ({HIDING_PLACES.get(marker, '?')})"


def test_no_secret_reaches_a_players_command(cli: Cli, home: Path) -> None:
    _plant(cli, home)
    leaks: list[str] = []
    for argv in CLI_READS:
        for form in ("md", "json"):
            result = cli(*argv, "--format", form)
            leaks += _leaks(f"didact {' '.join(argv)} ({form})", result.out + result.err)
    assert not leaks, "\n".join(leaks)


def test_no_secret_reaches_a_setting_pack_made_of_the_world(cli: Cli, home: Path) -> None:
    _plant(cli, home)
    made = cli("world", "export", "--as", "setting", "--format", "json")
    assert made.code == 0, made.err
    root = Path(json.loads(made.out)["path"])
    leaks = [
        leak
        for path in sorted(root.rglob("*"))
        if path.is_file()
        for leak in _leaks(str(path.relative_to(root)), path.read_text(encoding="utf-8"))
    ]
    assert not leaks, "\n".join(leaks)


@pytest.fixture
def planted(cli: Cli, home: Path) -> Iterator[Browser]:
    """The planted library, served in the player view."""
    _plant(cli, home)
    server = WebServer(App(), "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield Browser(server)
    finally:
        server.shutdown()
        server.server_close()


def test_no_secret_reaches_a_players_page(planted: Browser) -> None:
    leaks: list[str] = []
    for path in PAGES:
        text = html.unescape(planted.get(path).body)
        if path.endswith("qx1-heir"):  # the id that was asked for is in the page's links
            text = re.sub("qx1-heir", "", text, flags=re.IGNORECASE)
        leaks += _leaks(path, text)
    assert not leaks, "\n".join(leaks)


@pytest.mark.anyio
async def test_no_secret_reaches_a_players_tool(cli: Cli, home: Path) -> None:
    pytest.importorskip("mcp")
    from mcp.client.client import Client

    from didact.mcp.server import build

    _plant(cli, home)
    calls: tuple[tuple[str, dict[str, object]], ...] = (
        ("didact_show", {"ref": "tom"}),
        ("didact_search", {"query": "well"}),
        ("didact_brief", {}),
        ("didact_cli", {"command": "didact map"}),
        ("didact_cli", {"command": "didact session show 1"}),
        ("didact_where", {"thing": "ring"}),
    )
    leaks: list[str] = []
    async with Client(build()) as client:
        for name, arguments in calls:
            result = await client.call_tool(name, arguments)
            text = "\n".join(getattr(c, "text", "") for c in getattr(result, "content", []))
            leaks += _leaks(f"{name} {json.dumps(arguments)}", text)
    assert not leaks, "\n".join(leaks)
