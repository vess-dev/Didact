# CLAUDE.md

The guide to Didact's code: what it is, how it's built, and how to change it. It's written for coding agents, and it works for people too. [README.md](README.md) is the short overview for users, and [AGENTS.md](AGENTS.md) tells an LLM how to *play* with Didact.

Didact is a typed Python 3.14 toolkit that lets LLMs run solo tabletop RPGs for any game system. **The LLM narrates, adjudicates and administers. Didact holds the truth and does the hard parts:** records, sheets, dice, rules, oracles, time, the map, secrets, the GM's notes and the journal.

## Principles

1. **Truth lives in Didact.** State, rolls and rules come from Didact, never from the LLM's memory. The LLM reads state before narrating it and writes it after changing it, and it looks rules up rather than recalling them.
2. **Didact rolls, the LLM interprets.** Every roll gets an id (`#r12`) in the event log and can be replayed.
3. **Data first, code second.** Packs describe systems in YAML: sheets, tables, rules, oracles, generators, character creation. Python plugins cover what data can't, behind the same registries.
4. **Everything is an event.** Every write and roll is appended to the event log: that gives undo, history, audit, journals and save points.
5. **Scoped.** Records belong to one scope (global → system → world → campaign), and reads only see the active chain.
6. **Prompts, not prose.** Didact never calls an LLM. It returns results, keywords, structure and the book's own questions; the LLM writes the prose.
7. **Output for LLM eyes.** Compact Markdown by default (`key: value` lines, ids inline), `--format json|yaml` for machines, and a 12,000-character budget on long output.
8. **Helpful failure.** Every error names the problem and how to fix it (`hint`).
9. **Player-safe by default.** Secrets, hidden fields and the GM's notes stay out of views unless `--gm` is passed.
10. **The LLM administers, Didact guards.** Anything can be changed on request; every change is validated, previewable (`--dry-run`), logged and undoable.
11. **Describe it, get it.** Anything can be created from a description. Didact rolls what the system's procedures decide, derives the rest and checks it against the pack's guidance.
12. **System-agnostic core.** No game system's name or rule appears in the code. What a system needs becomes a general feature any pack can use.
13. **Fast and current.** CLI start under ~250 ms (lazy imports), Python 3.14+, every dependency on its latest stable release.

## The gate

```
unset VIRTUAL_ENV          # the shell's global venv is not the project's .venv (the Makefile does this too)
make fmt                   # ruff format + autofix
make skill                 # regenerate the plugin's command reference and guide copies
make check                 # ruff format check, ruff lint, mypy --strict, pytest: must be green
```

- `make skill` must be run after changing any command's help or any guide; a test fails until you do.
- Dependencies: `uv lock --upgrade`, `uv sync --all-extras`, then `make check`.
- Scratch work goes in `Temp/` (git-ignored). Nothing in Didact imports from it.
- `make docs` (`didact docs build`) builds the API documentation from the docstrings and types (pdoc) into the cache folder's `docs/`; `didact docs status` says whether it's current. The web app serves it at `/docs/`, rebuilding it when the code changed.
- `make i18n` updates the translation catalogs after the web app's words change (`tools/i18n.py`; `test_i18n.py` fails until you do, and until every language is translated).
- `make packs` rebuilds the `.didactpack` files of the packs that ship with Didact, and `packs/index.json`.
- `make clean` removes the developer caches in the checkout (and `pack build` output); `didact cache clear` removes Didact's runtime caches (search indexes, compiled packs), which rebuild as needed.

## Repository map

```
src/didact/
  core/        ids, scopes, config, context, errors, output (Out, budgets), clock, YAML IO, words (loose matching, thesaurus)
  store/       records (front matter), event log, changesets (undo), SQLite index, repo, layout
  expr/        the dice and expression language: parser, evaluator, modifiers, streams, odds, plugins
  packs/       pack format: manifest, kinds, building bundles, validation, authoring, sharing, trust
  schema/      sheets: field kinds, record types, templates, JSON Schema
  tables/      random and lookup tables, decks and bags, oracle lists
  rules/       the rule language (checks, actions, procedures, triggers) and draft steps
  services/    operations the commands share: records, play, lore, oracles, details, search, …
  commands/    the typed command registry and every `didact` command
  cli/         argparse generated from the registry; `execute()`; `batch`
  mcp/         the MCP server (`didact-mcp`, extra `[mcp]`)
  web/         the browser app (`didact serve`)
  guides/      `didact guide <topic>`: Markdown docs shipped with the package; translations in guides/<code>/
  locale/      the web app's gettext catalogs, one folder per language (didact.po, compiled didact.mo)
packs/         `core` (part of Didact); the packs that ship with it, as folders and `.didactpack` files; private packs
tests/         pytest; fixture packs in tests/fixtures/packs
tools/         developer tools: tools/i18n.py (extract, merge, compile, check the translations)
docs/          images for the README
claude/        the Claude Code plugin: skills, hooks, references (generated by `make skill`)
AGENTS.md      how any LLM plays with Didact
```

## Architecture

### Layers

```
core → store → engines (expr, tables, rules, schema, packs) → services → commands → cli / mcp / web
```

- Each layer imports only from the layers before it. Nothing imports `cli`, except `mcp` and `web`, which reuse `cli.main.execute()`.
- Library code never prints.
- One typed command registry generates the CLI, the MCP tools' command line and the web app's command forms, so they can't drift apart.

### The library (data home)

`$DIDACT_HOME`, by default `~/Documents/DidactLibrary`:

```
state.yaml                      active world and campaign
log/events.jsonl                append-only event log (rolls, oracle answers, every change)
packs/<id>/<version>/           installed packs, versions side by side
systems/<pack>/                 system-scope overlays (homebrew monsters, tables, lore)
global/                         global scope
worlds/<world>/world.yaml       default system, calendar, settings
worlds/<world>/<type>/<slug>.md one record per file (npc, loc, item, faction, quest, lore, …)
worlds/<world>/campaigns/<c>/   campaign.yaml; pc/; session/ and scene/ records; journal/ (beats,
                                JSONL); state/ (oracle, play, fight, drafts); transcripts
```

The search index lives in the OS cache directory, and can be thrown away and rebuilt.

### Records

- **Files are the truth.** A record is Markdown with YAML front matter. The front-matter keys, in canonical order:
  - `id`, `type`, `name`, `aliases`, `tags`, `status`, `knowledge`, `archived`, `links`;
  - `fields` (system-agnostic), `details` (the GM's notes), `mechanics` (one block per system);
  - `extra` (bookkeeping), `created`, `updated`.

  The body is prose, with `## Secrets` and `## GM notes` sections hidden from players.
- **Ids** are `type:slug` (`npc:sweeney`), stable through renames (the old names stay as aliases). Commands accept ids, names and aliases, and suggest near matches.
- **Scopes:** global ⊃ `system:<pack>` ⊃ `world:<id>` ⊃ `campaign:<id>`. Reads resolve through the active chain; `--world` and `--campaign` override it per call.

### Changes, undo, turns

- **Every write goes through a `Changeset`:** validate, append events (with before and after), write files atomically, update the index.
  - Anything that writes the log or a counter holds `repo.writing()`: the data-home lock, after clearing up what a crash left.
  - **Cut short:** a marker (`log/applying.json`) names the change while its files are written (`store/recovery.py`). A crash leaves it behind, and the next command (or `doctor --repair`) puts the files back from the event and drops the event, leaving a `note`; a full disk or another refusal takes it back at once and says nothing changed. A half-written last log line is ignored by readers and cut off by the next write.
  - `undo` reverts a changeset exactly.
  - `undo --turn` reverts everything done for one player message: a turn group, opened by the Claude Code hook (`capture`) or by `turn begin`.
  - `undo --to e40` jumps back (`services/jumpback.py`): every step after the event still in effect is undone newest first (an undo of an earlier change is undone too, which redoes it), and rolls are marked undone (or stand again). It's checked against the files before anything is written, and nothing leaves the log: a jump to a later event brings it all back.
  - `--dry-run` previews a change; `--reason` records why a rule was broken on purpose.
- **Save points and forks** are rebuilt from the log (`save`, `rewind`, `campaign fork --at`).
- **The log is only ever appended to,** except by `history --clear` (`services/history.py`), `snapshot --restore` (`services/care.py`) and a change cut short, whose event is cut off its end. Each rewrites the log and leaves a `note` marker, so event and roll numbers never repeat. Anything that reads the log (dice counters, save points, turns) must respect the marker. The one deliberate restart is `reset` (`care.reset`), which empties the library as if newly installed, after a safety backup.
- **Ids stored anywhere must follow the record.** `merge` and a new slug rewrite references through `admin.rewrite_references`: records, journal beats and `state/*.yaml`. `rm` takes a record out of play (party, fight, location) through `records.forget_in_play`. A new place that stores ids needs a line in both. A merge across types leaves out what the survivor's closed schema has no field for, and says so (`admin._fitting`).

### The index and search

- SQLite with FTS5 (porter, bm25, snippets), a trigram table for names, links and backlinks, and the lore trigger table.
- It syncs one way (files → index) and is rebuilt when files change.
- Player searches re-check every hit against player-safe text, so hidden text never leaks through a match.
- `search` ranks rules text, terms, mechanics, tables, compendium, records, transcript and docs in one list. `rules lookup` tries a quoted phrase that finds nothing as its words, each as a whole word, and says so (`words.phrase_words`); `compendium find` keeps a phrase a phrase.
- **Loose matching** (`core/words.py`): `search`, `find` and `rules lookup` match a word as typed, as a near spelling above `NEAR_CUTOFF` (only for a word no text searched has as typed: a first pass notes the words that are, `Matcher.typed` and `seen`), or as a synonym one step away in WordNet (the `wn` library; never a synonym's synonym). Exact beats near beats synonym. The WordNet data is downloaded by `didact setup thesaurus` into the cache folder's `wordnet/`, one language in use at a time (`active`), with `progress.json` reporting a download (the Settings page starts it as a process of its own and polls that file); without it there are no synonyms, and tests use `tests/fixtures/wordnet-mini.xml` (the `thesaurus` fixture). The player-safety re-check uses the same `Matcher`.
- **The web app's search box** searches as you type (`data-live` in `app.js`: it fetches `/search` and shows its `#search-results`).

### Packs

- **A pack is a folder:** `pack.yaml` (id, kind (system, oracle, setting or supplement), licence, requires, settings), `GUIDE.md`, and items by kind:
  - `schemas/` (record types and their sheets, with `details` suggestions);
  - `tables/`, `rules/`, `oracles/`, `generators/`, `chargen/`;
  - `compendium/` (monsters, items, …), `lore/`, `reference/` (rules text sections), `glossary.yaml`;
  - `tests/` (pack tests: scripted plays, every table rolled, odds).
- **Content ids are qualified** by the pack (`my-system.save`).
- **Building:** packs build into cached JSON bundles. Overlays, `extends` (a hack on top of its parent: its same-id items, reference sections and glossary terms replace the parent's, its settings go over the parent's key by key (`PackSet.settings`, which the parent's rules read too), and `hides` in its manifest drops the parent's items it names), overrides, version pins and plugin trust (by hash) are all supported.
- **Licensing:** each pack declares its licence. `redistributable: false` makes `pack export` refuse.
- **Where packs come from:** `$DIDACT_PACK_PATH`, the library's installed packs, and core, which is part of Didact. The other packs that ship with Didact are `.didactpack` files in `packs/`, beside their folders. A wheel carries core and those files as `didact/shipped/` (`[tool.hatch.build.targets.wheel]` in `pyproject.toml`), never the other pack folders, and `packs.library.bundled_dir` finds either place. `pack list` offers them, and `pack install <id>` (or the Library page) installs one with the shipped packs it needs. `pack update` finds newer versions of installed packs there and in `packs/index.json` on GitHub (`share.UPDATES`; tests set `DIDACT_PACK_UPDATES` empty, so none goes online).
- **Publishing:** only the pack folders listed in `.gitignore` are published; every other pack stays local. After changing a published pack, `make packs` rebuilds its `.didactpack` (`test_shipped_packs.py` fails until you do).
- **Made from a library** (`services/packing.py`): `pack new --from-overlay <system>` (homebrew as a supplement) and `world export --as setting`. Records become compendium entries that `compendium import` turns back into records, lore records become pack lore; player-safe unless `--secrets`, and never marked shareable.
- **Authoring commands:** `pack new`, `pack validate` (beside the build's checks, each compendium entry's `mechanics.<system>` block against that system's sheet, the pack's own against itself as it is in its folder: `compendium.sheet_problems`; the calendar's `leap`, `weekday` and `year`: `clock.problems`; a warning where an expression quotes a parameter of free text, `'$book'`, which an apostrophe breaks: `validate.quoted_params`), `pack test`, `pack coverage` (which pages of the source a pack cites), `pack ingest` (a rulebook to draft tables), and `guide packs` for the format.
- **One system at a time:** a system decides what can be made, so a world keeps the system it was made with (one made without takes the first it's given: `pack enable`, `world set system=`), and its campaigns play it (`campaign set system=` is refused; an older campaign's own `system` is still honoured). The packs added to a world or campaign go with it: an added system, or a pack that needs another system, stays out of play (`services/packs.py`: `enabled`, `conflicts`, `tie_system`). Campaigns open and close (`campaign open`, `campaign close`: the world stays open).

### Sheets

- A record's sheet is its core type (`fields`) plus the active system's type (`mechanics.<system>`).
- Field kinds (stat, resource, pool, slots, conditions, list, ref, enum, …) validate, clamp and derive values, and fire hooks (e.g. `when_full`, `on_zero`).
- `set freya hp-=2` finds `hp` in the right block; `-=` of what a list doesn't hold, like `--unset` of a field not set, changes nothing and says so (what the field could never hold is refused). A description's top-level key (`new --data`, `edit --data`, a compendium entry spawned, imported or drafted) goes there too, unless its own block for that system holds the key: then the block stands and the key is core's (`sheets.stated`).
- `inventory` lives in a `slots` field; any record without one keeps a plain `fields.inventory` list. That's how places and containers hold items. `set freya inventory.sword.damage=d10` changes a carried item's own key (`inventory.set_key`), checked as `inv add` checks it; a rule reads one as `@{who.inventory.$item.damage}` (`Host.item`). An item is named as `inv` names it (`find_item`: of several of a name, the first; to spend a use, the first with one left); in a dotted path the name is the longest run of parts that names an item carried (`inventory.item_keys`), so `12.7mm pistol` and `.45 pistol` are names like any other, and after its first part a `set` key holds what a name holds, spaces and all (`assign._ASSIGNMENT`; `assign.parse_key` lets an empty part inside through, and `apply_nested` refuses one that isn't in an item's name). `inv add` (and `give`) find an entry as `compendium.locate` does, among the types one carries (`inventory.carried_types`: the usual ones and any that `extends` one); a text that doesn't look like a record id is a name.

### Dice and expressions

- A hand-written parser for a rich notation: keep and drop, explode, reroll, successes, symbol dice, `d66`, tags, macros, steps, repeats, and variables (`@STR`, `@who.hp`).
- Registries let packs add dice, modifiers and macros.
- **Randomness:** one SHA-256 stream per roll, seeded per campaign, so every roll replays. `--got` records physical dice; `report` logs an outcome made outside Didact (a card, a block tower) as a roll with nothing to replay (`kind: report`).
- **Display:** a count worked out from values shows as rolled (`2d6 → [3 4]`).
- Exact odds come through `icepool` (the `odds` extra).

### Tables

Tables can be random or lookup, weighted, `d66` (optionally read both ways), with columns (`read:` makes them a sentence), nested references and computed ids. There are also decks and bags. An oracle's weighted lists (threads, characters) live on the oracle's state (`lists`).

### Rules

Rules are data: checks (roll, bands, outcomes), actions, procedures and triggers.
- **Steps:** roll, let, set (`who.$attr` names a field through a parameter; `who.inventory.$item.damage` a carried item's key), entity (a record made at once, or the one of that name already here), give, take and use (an item, as `inv add`, `inv drop` and `inv use`), unset (as `set --unset`: `sheets.unset`), check, do (`as:` reads what it bound), table, if, repeat, for (once per PC or party member, as a record of its own), message, prompt, reminder, stop, reroll, pick, pool (roll or drop dice from a tracker's diminishing pool), remind (a reminder due in game time).
- **Where play stands:** any rule reads `@system`, `@session`, `@scene`, `@time.*` and, during a fight, `@combat.round` and `@combat.fighters` (`Host.now()`, `events.now`); an event's own values are passed on to the rules its triggers run.
- **Pending rolls:** a check can come back pending (push, burn, reroll) and is finished with `resolve`, which gets back what its steps bound (values, rolls, records).
- **Text:** `{…}` in what a rule or a table fills in is an expression (or a table, a column, an entry's data), and `{{` and `}}` are a brace: `_BRACES` (rules), `_PLACEHOLDER`, `_COLUMN` and `_FIELD` (tables) alike; in rules `@{…}` is a variable, not a template (`_VARIABLE`). A roll fills its `{…}` in too, so it rolls dice a value holds as text (`roll: "{@d} + 1"`: `Scope._filled`, `_ROLL_FILL`), leaving a set of rolls (`{d8, d6}kh1`) and a die's faces be; a roll that is only such text, rolling nothing, is refused (`Scope._not_text`).
- **Triggers** run on time, scene, session and fight events; `for: pcs` (or `party`) runs one once per player character, as `who`. One that fails names itself, with how to go on without it (`events.failed`).
- **Values:** a table entry's list of items reads as their names (`bind_data`; handed to a step as it is, the items themselves); other mapping lists can't be read (`Run.unread`). A `ref` parameter's `to:` narrows a name to records of that type (`Repo.resolve(of=)`, a type or several), and so does a command whose record can only be of one kind: `track roll` and `track tick` (a tracker), `quest done` (a quest, thread or task), `visit` and `map --within` (a place), `party add --as pc` (a PC).
- **Options:** a system's variant and optional rules (`option:` documents in `rules/`, `services/options.py`), asked at session zero and kept in the campaign profile; rules, character creation and generators read `@option.x`, and the brief lists the changed ones.
- `do <rule> name=value …` runs one; a flag parameter can stand alone.

### Drafts: generators and character creation

- **Procedures build a draft:** steps entity (here, a record drafted), choose (`exclude`), choose_or_roll, point_buy, assign, swap, apply, roll_tables, add, remove, name, ask (a typed answer) and map (a die-drop pointcrawl). A generator with `creates:` builds one record the way character creation does. Only keys the pack wrote (`key:`, or an `as:` name: `DraftEntity.keyed`) are swapped for record ids at commit; a rule's `entity:` swaps its own `key:` only. A `stop:` under an `if:` reading an option (`Run.stopped_by_option`) hints at the options.
- **Nothing is written until `commit`.**
- **Advancing:** a chargen with `advances: pc` is the system's level-up (`char advance`): the draft starts from a copy of the record (`Stored.target`, `base`), steps read it as `@who`, and `commit` writes what changed, checked against the sheet like `set` (field hooks don't fire; a field naming a draft key gets that record's id, as in creation). Choices take `answer:` (decided by the record, not asked) and `records:` (the records of a type here join the options).
- **Replay:** guided choices replay from the draft's trail (each value used once; a table roll that went on to other tables keeps the entries it took beside its value, `PATH`, so their data replays too), and `--prefill` decides things up front (a choice as the option it names: `Scope.settle`; an entry further down, behind rows that go on, counts too, at any depth and the nearest first: the drafts' `_further`, as deep as `MAX_DEPTH`; near misses refused). An entry chosen or prefilled rather than rolled that goes on (`then:`) rolls on then (`Scope.onward`, `Scope._rolled_on`, `TableRoller.take`), its path kept.
- **Going back:** `char back`/`gen back` undo the newest change in effect to the draft's state file when it was one of the draft's own steps (its logged phrase names the draft), and mark the rolls it made undone (`drafts.last_step`).
- **Describing:** an open choice carries what each option means and the names of options that are ids (`Choice.about`, `labels`, from the `option_notes` hook: a table entry's `note:` or its table's `about:`, else a compendium entry's summary), how many to pick (`pick`), and how a structured answer is made (`form`: `point_buy`, `assign`), so the web app can ask for it field by field.
- A random draft still waits for a name when there's nothing to roll one from.

### Oracles

An oracle pack defines checks (a yes/no question with odds, which may look things up in a chart first), its per-campaign state (e.g. a chaos factor), and its lists. `ask` rolls and keeps each answer. `interpret` stores what it meant.

### Play

- **Sessions and scenes:** records with summaries.
- **The journal:** typed beats (action, oracle, roll, result, consequence, narration, dialogue, note, ooc). A beat can be `--about` records and `--secret`.
- **The transcript,** captured by hooks.
- **Time:** a calendar (leap years, the start's weekday, how a date writes its year: `services/clock.py`; a weekday written before a date is checked, `weekday_note`), a campaign's own first day (`start` in `campaign.yaml`: `campaign new --date`, read with the world's calendar through `Repo(..., no_campaign=True)` since a campaign open now may have packs of its own, or `time set` until the first session, since the journal is dated by the clock), timers, reminders and time triggers.
- **Trackers:** clocks, counters, diminishing dice pools, quests and factions.
- **Combat:** order, rounds and conditions; the system's attack rule; `status --gm` shows positions and plans.
- **The map:** places, paths and discovery.
- **The rest:** the party; rulings; the campaign profile (session zero); due summaries; the brief.

### What the GM knows

- **Secrets:** `knowledge: secret` records, `## Secrets` body sections, secret fields and `extra.secret_keys`. `reveal` moves knowledge to the players.
- **Player views** use `knowledge.player_copy(entity, sheet, knowledge.unknown(repo))`. It drops:
  - the secrets above;
  - anything that names a secret record, by id or by name (a link, an item carried, a field pointing at one);
  - bookkeeping (`extra`), links that are hidden paths, and values of a system whose sheet isn't loaded.

  Numbers shown to players (`stat_line`) are worked out from that copy. Summaries go through `play.summary_of(body, gm=…)`, and a secret session's or scene's title through `play.title_of`.
- **Details** (`about`): the GM's short named notes on any record:
  - looks, personality, wants, fears, attitude;
  - doing, plan, where;
  - history, powers, state, secret, thoughts.

  Players see only `looks`. Suggestions depend on the kind of record, or on the schema's `details`. `reveal <record> <name>` moves one into the body.
- **The chronicle:** the journal beats `--about` a record, shown on it. Secret beats are the GM's only.
- **Whereabouts:** `where <thing>` follows the inventories outward (a sword in a chest in a house), and `show` on a holder lists its contents nested. During a session, moving an item logs a beat about both holders.
- **The GM brief** (`brief --gm`, run by the session-start hook) lists what's in play and the latest secret beats.

### Lore

Lore is keyword-triggered memory. Lore entries, record "cards" and rulings are indexed by their keys. `lore scan` (run by the hooks and after `log`) pushes what the text brings up; `constant` entries are always in the brief. Secret entries only show in GM scans.

### Interfaces

- **CLI:** `didact <command>`. `batch` runs one command per line in one call. `batch`, `serve` and `sample` are run by `cli/main.py` itself, since only that layer may run other commands. `cli/sample.py` builds the sample campaign with ordinary commands, and `serve --demo` serves it from a library of its own.
- **MCP:** `didact-mcp` offers coarse tools (brief, roll, ask, do, show, search, explain, set, new, log, about, where, lore scan) plus `didact_cli` for anything else, and the guides as resources. Every tool runs a real command line through `execute()`.
- **Translations** (`core/i18n.py`): the web app's words and the guides come in 24 languages (Steam's fully supported languages that the Ubuntu font covers). Mark every shown message with `_()` (a literal: extraction reads the syntax tree): the web's words, and commands' output and errors (their `md`, `done`, notes, messages and hints), but never anything persisted (files, the log, changeset summaries) or data (`Out.data`). Name its values (`_("Uninstall {pack}?", pack=…)`), use `ngettext` for counts, keep markup out of messages, and never translate at import time. The language is per request: the Settings cookie, else Accept-Language. The command line speaks English, for the LLMs that use it, unless a call asks for another language with `DIDACT_LANG` (`cli.main.main` only: MCP, the Claude Code plugin and `make skill` are always English). Nothing makes a language stick: the browser app's choice is only the browser app's. Commands' help (summaries, descriptions, argument help) is looked up with `i18n.translate`; `tools/i18n.py` extracts it from the registry. A guide translation is `guides/<code>/<topic>.md`, starting with `<!-- translated from <hash> -->` (`guides.source_hash`); an older one says so on its page.
- **Web:** `didact serve` is a local browser app, a client of the command layer. Its pages are Overview, Status (where things stand), Records (with the drafts wizard for characters and generators), Graph (with a map mode), Journal, Reference, Library, Commands and Settings (language, thesaurus, the API docs at `/docs/`):
  - every write goes through `execute()`;
  - it's player-safe unless GM view is on;
  - forms that save typed values carry what the page showed, and saving refuses when the record changed since (`web/safe.py`), so nothing changed meanwhile (from the command line, say) is overwritten;
  - it binds to localhost, checks the Host header, and requires a CSRF token on every POST;
  - a box takes what its command takes: `web/forms.py` binds ids, record types, keys, one-word names and events (`PATTERNS`, `data-input`, which `app.js` holds them to as they're typed), game time as a number and a unit, and offers lists to pick from on command forms (`OFFERED`).
  `didact guide web`.
- **Exports:** `export --as json|md` (the records), `--as story` (the campaign as a readable book), `--as lonelog` (the journal in Lonelog notation, `services/lonelog.py`) and `--as site` (a player-safe static website, `services/site.py`, which doesn't import `didact.web`). `lore export`/`lore import` trade lorebooks with SillyTavern, KoboldAI, character cards and NovelAI (`services/lorebook.py`).
- **Claude Code plugin** (`claude/`): the skill, hooks (the GM brief at start and after compaction, transcript capture, lore, auto-approval of plain `didact` commands) and slash commands.

## Conventions

**Adding a command**
1. Write a function in a `src/didact/commands/` module and decorate it with `@command("name words", summary=…, examples=…, writes=…, description=…)`.
2. Its first parameter is `ctx: Context`, and the others become arguments (see the `registry.py` docstring). Document each with `Annotated[T, "help"]`, plus `Metavar("record")` for the placeholder.
   - `bool` options are flags, `list[...]` ones repeat, and `Literal[...]` gives choices.
   - These names are global options, so never reuse them: `--format`, `--detail`, `--home`, `--world`, `--campaign`, `--dry-run`, `--reason`.
3. Return `Out(data=…, md=…)`: JSON-safe data plus compact Markdown. Writes go through `changeset(ctx, repo, …)` and `finish(...)`.
4. New modules go in `didact.commands.MODULES`. Keep command modules light: import heavy libraries inside functions.
5. Add a CLI test (the `cli` fixture), run `make skill`, and add it to the plugin skill's cheat sheet if it matters in play.

**Errors.** Raise `DidactError` subclasses (`UsageError`, `NotFoundError`, `InvalidError`, `ConflictError`), always with a `hint` that says how to fix it.

**Typing.** `mypy --strict` clean. Use `JSON` (`didact.core.output`) for plain data. No `Any` across module boundaries.

**Docs.**
- A command's summary and examples come from its decorator.
- How-tos are guides in `src/didact/guides/`.
- A pack's `GUIDE.md` says how to run that system.
- Keep docs short, plain and current: examples first, no dates, and no game system named outside its own pack. Quote dice in examples (`didact roll '6d10>=8f1'`).

**Tests.**
- **Where they live:** `tests/`. The `home` fixture gives each test a temporary library, with `tests/fixtures/packs` on `DIDACT_PACK_PATH`. `cli(...)` runs a command in-process.
- **Fixture packs:**
  - `mini-system` is the everyday system;
  - the `*-lite` packs are small test systems for different mechanics;
  - the `lucky` fixture writes a pack with a Python dice plugin into a test's own folder (`tests/plugin_pack.py`);
  - `oracle-lite` is a chart oracle;
  - `broken` fails validation.
  Add a fixture pack rather than stretching one to cover everything.
- **The packs that ship** are tested through their own `tests/` folder (`didact pack test`) and a test file each, with the `system_packs` fixture putting their folders on the pack path.
- **Sweeps** catch whole classes of bugs at once; extend them as you add things:
  - `test_undo_sweep.py` plays a whole session, undoes it byte for byte and redoes it. Add each new writing command to its session.
  - `test_secrecy_sweep.py` plants a marker in every hiding place (the planting is shared with `test_site_export.py`, which sweeps the exported site) and checks no player view shows one. Add each new player-facing command, page or tool to its lists, and each new kind of secret to the planting.
  - `test_two_writers.py` checks that concurrent writers lose nothing.
  - `test_interrupted_writes.py` cuts every file write of the undo sweep's session short in turn, as a kill and as a full disk, and checks the library is as it was before that change.
  - `test_error_hints.py` fails on any error raised without a `hint`.
- No test calls an LLM.

## Things that are easy to get wrong

- Adding or changing words in the web app without `_()` and `make i18n`, or a guide without re-translating it.
- Changing a command's help or a guide without `make skill`.
- Printing from library code: return `Out` instead.
- Reading secrets into a player view: use `knowledge.player_copy` with `knowledge.unknown(repo)`, pass `gm` through, and add the view to the secrecy sweep.
- Writing a file directly instead of through a changeset: it can't be undone, and the index won't know.
- Naming a game system in core code, comments or docs: describe the mechanic instead.
- Publishing a pack that isn't licensed for it: packs are private unless listed in `.gitignore`.
