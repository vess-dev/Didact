"""The MCP server (an optional extra): coarse tools, `didact_cli`, docs as resources."""

from pathlib import Path

import pytest

pytest.importorskip("mcp")

from mcp.client.client import Client

from didact.mcp.server import build
from tests.conftest import Cli


def _text(result: object) -> str:
    content = getattr(result, "content", [])
    return "\n".join(getattr(c, "text", "") for c in content)


@pytest.mark.anyio
async def test_the_tools_play_and_errors_say_how_to_fix(cli: Cli, home: Path) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "c")
    async with Client(build()) as client:
        names = {t.name for t in (await client.list_tools()).tools}
        assert {"didact_brief", "didact_roll", "didact_ask", "didact_do", "didact_cli"} <= names
        assert len(names) <= 14  # coarse tools keep the definitions small
        rolled = await client.call_tool("didact_roll", {"expression": "2d6", "reason": "test"})
        assert not rolled.is_error and "#r1 2d6" in _text(rolled)
        made = await client.call_tool(
            "didact_new", {"type": "npc", "name": "Tom", "data": {"hp": 4, "STR": 12}}
        )
        assert not made.is_error and "npc:tom" in _text(made)
        changed = await client.call_tool("didact_set", {"ref": "tom", "changes": ["hp-=1"]})
        assert not changed.is_error
        shown = await client.call_tool("didact_show", {"ref": "tom"})
        assert "Tom" in _text(shown)
        missing = await client.call_tool("didact_show", {"ref": "nobody"})
        assert missing.is_error and "fix:" in _text(missing)  # the model can retry
        anything = await client.call_tool("didact_cli", {"command": "didact rolls"})
        assert "#r1" in _text(anything)
        asked = await client.call_tool("didact_ask", {"question": "Is it raining?"})
        assert "#o1" in _text(asked)
        found = await client.call_tool("didact_search", {"query": "fatigue"})
        assert "[terms]" in _text(found)
        brief = await client.call_tool("didact_brief", {})
        assert not brief.is_error
        noted = await client.call_tool(
            "didact_about", {"ref": "tom", "details": {"plan": "steal the ledger"}}
        )
        assert not noted.is_error and "plan: steal the ledger" in _text(noted)
        assert "steal the ledger" in _text(await client.call_tool("didact_about", {"ref": "tom"}))
        cli("session", "start")
        logged = await client.call_tool(
            "didact_log",
            {"kind": "note", "text": "Tom slips out", "about": ["tom"], "secret": True},
        )
        assert not logged.is_error
        gm_brief = _text(await client.call_tool("didact_brief", {"gm": True}))
        assert "Tom slips out" in gm_brief and "plan: steal the ledger" in gm_brief
        where = await client.call_tool("didact_where", {"thing": "ledger"})
        assert not where.is_error and "nothing called 'ledger'" in _text(where)
        for blocking in ("serve", "didact batch"):  # a server, or stdin: both would hang
            refused = await client.call_tool("didact_cli", {"command": blocking})
            assert refused.is_error


@pytest.mark.anyio
async def test_the_docs_are_resources(home: Path) -> None:
    async with Client(build()) as client:
        listed = await client.read_resource("didact://commands")
        text = "\n".join(getattr(c, "text", "") for c in listed.contents)
        assert "didact roll" in text or "roll" in text
        guide = await client.read_resource("didact://guide/dice")
        assert "dice" in "\n".join(getattr(c, "text", "") for c in guide.contents).casefold()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.slow
@pytest.mark.anyio
async def test_the_stdio_server_answers(cli: Cli, home: Path) -> None:
    import os
    import sys

    from mcp.client.stdio import StdioServerParameters

    cli("world", "new", "vale")
    server = StdioServerParameters(
        command=str(Path(sys.executable).with_name("didact-mcp")),
        env={**os.environ, "DIDACT_HOME": str(home)},
    )
    async with Client(server) as client:
        rolled = await client.call_tool("didact_roll", {"expression": "3d6"})
        assert not rolled.is_error and "3d6" in _text(rolled)
