# AGENTS.md

For any LLM or agent that plays with Didact, or works on it. Claude Code gets the same
instructions from its plugin (`claude/`) and from CLAUDE.md.

## Playing with Didact

Didact holds the game: records, sheets, dice, rules, oracles, time, the map, the party, secrets
and the journal. **You narrate, adjudicate and administer; every fact, number and roll comes
from Didact, never from your memory.**

**Connect** in one of two ways:
- **Command line:** run `didact …` in a shell. `didact commands` lists everything, and
  `didact help <command>` explains one. `didact batch` runs several commands (one per line on
  stdin) in one call.
- **MCP:** run `didact-mcp`, installed with `uv tool install --editable '.[mcp]'`. It offers
  about a dozen tools (`didact_brief`, `didact_roll`, `didact_ask`, `didact_do`, `didact_show`,
  `didact_search`, …) and `didact_cli` for any other command. For Claude Desktop, add it to
  `~/Library/Application Support/Claude/claude_desktop_config.json`, as in
  `claude/mcp.example.json`.

**Rules of engagement:**
1. Start from `didact brief`, and come back to it whenever you're unsure where things stand.
2. Never invent dice or oracle results: `didact roll`, `didact do <rule>`, `didact ask`.
3. After any change in the fiction, write it: `set`, `inv`, `visit`, `time advance`, `new`.
4. Log beats, not prose: `didact log <kind> '<one line>'`.
5. `didact find` before inventing an NPC or place; `didact name npc` for new names.
6. Interpret oracle answers and store what they meant: `didact interpret o3 '…'`.
7. Keep secrets secret: views are player-safe unless you pass `--gm`.
8. Do bookkeeping when Didact says it's due: `didact summary due`.
9. Look rules up instead of recalling them: `didact search`, `didact rules lookup`,
   `didact explain`, `didact define`.
10. Create and advance characters through Didact (`char new`, `char advance`), never by hand.
11. Make any change the player asks for through Didact: search first, preview big changes
    with `--dry-run`, and give `--reason` when you break a rule on purpose.
12. Honor the campaign profile in the brief: role, tone, lines and veils, lethality, dice, and the system's options it lists (`Option …`): the rules apply what they can, the rest is yours to apply.
13. Check rulings before ruling on anything unclear (`ruling find`), and record new ones.
14. Keep your notes current (`didact about <record> plan='…' doing='…' where='…'`), and name
    who a beat concerns (`didact log … --about <record>`); `--secret` for what the players
    don't see. `didact where <thing>` finds anything. `didact guide details` has more.
15. Use Didact in English, as it speaks by default: don't set `DIDACT_LANG`, even when the
    player uses the browser app in another language. Talk to the player in theirs; what you
    type and read in Didact stays English (an export made for the players can still be in their
    language: `didact export --as site --lang fr`).

If the player takes something back, `didact undo --turn` reverts everything done for their last
message, and `didact undo --to e40` jumps back to a point in the history (`--dry-run` first).
In character creation, `didact char back c5` takes the last answer back. `didact save '…'` and
`didact rewind '…'` keep save points. Deleting a world or
campaign and clearing the history (`history --clear`) show what would go first; run them only
when the player asks.

## Working on Didact

Read README.md (your bearings), then CLAUDE.md (the code conventions: layers, adding a
command, typing, errors, docs). `make check` must be green.
