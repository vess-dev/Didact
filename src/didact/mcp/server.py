"""The MCP server: coarse tools for the hot paths, `didact_cli` for everything else,
and Didact's guides as resources.

Every tool runs a real `didact` command line in-process, so tools and the CLI never drift.
A failed command comes back as an error result (`is_error`) whose text says how to fix it,
so the model can retry.
"""

import json
import shlex
from collections.abc import Sequence

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from didact import __version__
from didact.cli.main import execute

INSTRUCTIONS = """\
Didact holds the game: records, sheets, dice, rules, oracles, time, the map, secrets and the
journal. You are the voice of the game; Didact is its memory and its dice.
- Start from `didact_brief`. Never invent dice or oracle results: roll with `didact_roll`,
  run rules with `didact_do`, ask the oracle with `didact_ask`.
- After any change in the fiction, write it (`didact_set`, `didact_new`, `didact_log`).
- Keep your own notes current with `didact_about`: what people want, are doing and plan
  next, where things are, what you intend. Name who a beat concerns (`about`) so it stays on
  their record. Players see only `looks`.
- Look rules up (`didact_search`, `didact_explain`) instead of recalling them.
- Anything else: `didact_cli` runs any didact command (`didact_cli("help")` lists them).
"""


TOOLS = {  # what each tool is for: the model reads these to choose
    "didact_brief": (
        "The current game at a glance: context, PCs, scene, lists, what's due; gm=true adds "
        "your notes on what's in play."
    ),
    "didact_roll": (
        "Roll dice (logged, replayable). Any notation: '2d6+1', '4d6kh3', 'd20 <= @STR'."
    ),
    "didact_ask": "Ask the oracle a yes/no question with odds (e.g. likely); the answer is kept.",
    "didact_do": (
        "Run a system rule: a check, action or procedure, e.g. rule='save', args={'who': "
        "'freya', 'attr': 'DEX'}."
    ),
    "didact_show": "Show a record (NPC, place, item, …): player-safe unless gm=true.",
    "didact_search": (
        "Search everything: rules text, terms, mechanics, tables, compendium, records, "
        "transcript, docs."
    ),
    "didact_explain": (
        "What is this? A rule, table, record type, compendium entry, term, command or guide."
    ),
    "didact_set": (
        "Change fields: changes like ['hp-=2', 'disposition=hostile', 'tags+=wounded']."
    ),
    "didact_new": (
        "Create a record from a description turned into data, e.g. type='npc', name='Tom', "
        "data={'hp': 4}."
    ),
    "didact_log": (
        "Log a beat to the journal: kind is action, oracle, result, consequence, narration, "
        "dialogue, note or ooc. about=[records] puts it on their chronicles; secret=true: out "
        "of the players' sight."
    ),
    "didact_about": (
        "Your notes on a record (hidden from players, except looks): set details like "
        "{'plan': '…', 'doing': '…', 'where': '…', 'wants': '…', 'thoughts': '…'}, or read "
        "them (with its chronicle and whereabouts) by giving none."
    ),
    "didact_where": "Where a thing is: who carries it, or what it's in and where that is.",
    "didact_lore_scan": "Lore that play text brings up (keyword-triggered memory), to weave in.",
    "didact_cli": (
        "Run any didact command line, e.g. 'gen run my-system.setting --auto' or 'help'."
    ),
}


def run(args: Sequence[str]) -> str:
    """Run a command line (without `didact`); its text, or a ToolError with the fix."""
    result = execute(list(args))
    text = result.text().strip()
    if result.code != 0:
        raise ToolError(text or f"didact {shlex.join(args)} failed")
    return text


def build() -> MCPServer:
    server = MCPServer(
        name="didact",
        title="Didact",
        description="Rules engine, dice, oracles and memory for LLM-run solo tabletop RPGs.",
        instructions=INSTRUCTIONS,
        version=__version__,
    )

    @server.tool(description=TOOLS["didact_brief"])
    def didact_brief(gm: bool = False) -> str:
        return run(["brief", *(["--gm"] if gm else [])])

    @server.tool(description=TOOLS["didact_roll"])
    def didact_roll(expression: str, reason: str = "", as_record: str = "") -> str:
        args = ["roll", expression]
        if as_record:
            args += ["--as", as_record]
        if reason:
            args += ["--reason", reason]
        return run(args)

    @server.tool(description=TOOLS["didact_ask"])
    def didact_ask(question: str, odds: str = "") -> str:
        return run(["ask", question, *(["--odds", odds] if odds else [])])

    @server.tool(description=TOOLS["didact_do"])
    def didact_do(rule: str, args: dict[str, str] | None = None) -> str:
        return run(["do", rule, *(f"{k}={v}" for k, v in (args or {}).items())])

    @server.tool(description=TOOLS["didact_show"])
    def didact_show(ref: str, gm: bool = False) -> str:
        return run(["show", ref, *(["--gm"] if gm else [])])

    @server.tool(description=TOOLS["didact_search"])
    def didact_search(query: str, sources: list[str] | None = None) -> str:
        return run(["search", *query.split(), *(a for s in sources or [] for a in ("--in", s))])

    @server.tool(description=TOOLS["didact_explain"])
    def didact_explain(name: str) -> str:
        return run(["explain", *name.split()])

    @server.tool(description=TOOLS["didact_set"])
    def didact_set(ref: str, changes: list[str], reason: str = "") -> str:
        return run(["set", ref, *changes, *(["--reason", reason] if reason else [])])

    @server.tool(description=TOOLS["didact_new"])
    def didact_new(type: str, name: str, data: dict[str, object] | None = None) -> str:
        return run(["new", type, name, *(["--data", json.dumps(data)] if data else [])])

    @server.tool(description=TOOLS["didact_log"])
    def didact_log(
        kind: str, text: str, about: list[str] | None = None, secret: bool = False
    ) -> str:
        refs = [a for ref in about or [] for a in ("--about", ref)]
        return run(["log", kind, text, *refs, *(["--secret"] if secret else [])])

    @server.tool(description=TOOLS["didact_about"])
    def didact_about(ref: str, details: dict[str, str] | None = None) -> str:
        return run(["about", ref, *(f"{k}={v}" for k, v in (details or {}).items())])

    @server.tool(description=TOOLS["didact_where"])
    def didact_where(thing: str, gm: bool = False) -> str:
        return run(["where", thing, *(["--gm"] if gm else [])])

    @server.tool(description=TOOLS["didact_lore_scan"])
    def didact_lore_scan(text: str) -> str:
        return run(["lore", "scan", text])

    @server.tool(description=TOOLS["didact_cli"])
    def didact_cli(command: str) -> str:
        words = shlex.split(command)
        if words[:1] == ["didact"]:
            words = words[1:]
        if words[:1] == ["serve"]:
            raise ToolError("`didact serve` runs a web server: start it in a terminal instead")
        if words[:1] == ["batch"] and "--file" not in words:
            raise ToolError(
                "`batch` reads commands from stdin, which is this server's channel: call the "
                "commands one by one, or give `batch --file <path>`"
            )
        return run(words or ["commands"])

    @server.resource("didact://commands", name="commands", mime_type="text/markdown")
    def commands() -> str:
        return run(["commands"])

    @server.resource("didact://guide/{topic}", name="guide", mime_type="text/markdown")
    def guide(topic: str) -> str:
        return run(["guide", topic])

    return server


def main() -> None:
    """`didact-mcp`: serve over stdio (Claude Desktop, Claude Code and other MCP clients)."""
    build().run("stdio")
