# The browser app

`didact serve` opens your library in a web browser: explore and edit records, see how they link in a graph, read the journal, run rules and tables, and use every command from a form.

```
didact serve                     # http://127.0.0.1:8765/ until Ctrl-C
didact serve --open              # and open it in a browser tab
didact serve --gm                # start with the GM view on
didact serve --port 9000
didact serve --campaign withering --home ~/OtherLibrary
didact serve --demo              # a fresh sample campaign to try things on
```

It works offline: the fonts and icons ship with Didact.

**Demo mode.** `--demo` serves the sample campaign (`didact sample`: a river valley, a PC, people with the GM's notes, places and paths, a quest, a clock, and a session under way with a fight) from a library of its own, beside Didact's cache folder, with every pack that ships with Didact installed. It's built afresh each time `--demo` starts, so try anything: your own library isn't touched.

## Options

| Option | Default | What it does |
|---|---|---|
| `--port <n>` | 8765 | the port to listen on |
| `--host <address>` | 127.0.0.1 | the address to listen on: this machine only |
| `--open` | off | open the app in a browser tab |
| `--gm` | off | start with the GM view on |
| `--demo` | off | serve a fresh sample campaign instead of your library |

The global `--home`, `--world` and `--campaign` apply to everything the app does. Opening another world or campaign in the app's Library page switches to it, as `didact world use` and `didact campaign open` do, and Close puts the open campaign away (`didact campaign close`).

## What's in it

- **Overview:** the brief (world, campaign, session, scene, party, what's due), quick actions (roll dice, ask the oracle with the odds it knows, log a beat, start or end a session, a new record) and the latest changes.
- **Status:** where things stand, at a glance: the session and scene, the time and the reminders coming up, each party member's numbers and what they carry, the fight (whose turn, conditions), open quests and trackers, and where the party is with its ways out. The numbers can be nudged right there: − and + on a stat, tick a tracker, use or drop an item, add one, finish a quest, advance the time (a number, and a unit the calendar knows: hours, watches, days, …), set a reminder (once, or every so often) and cancel one.
- **Records:** every record, grouped by type, with a filter box and all, world or campaign chips. A record's page shows its sheet, description, details, fields, contents, links both ways, its chronicle and its history, with forms to change each of them, and to archive or delete it. A character whose system has a level-up has a Level up button (`char advance`): a draft that shows what changes, before and after, until it's committed.
- **Drafts:** character creation and generators, one step at a time. Create a character (step by step or at random, choosing which kind when the system has several: a player character, a hireling, …) and Generate… are on the Records pages; the drafts waiting are listed there and on the Overview. A draft's page shows what it holds so far (its entities and their fields, the map a generator drew, the rolls, the book's prompts) and the question it waits for. Each option is a button that says what it means when the pack does (what a background gives, what a talent does); picking several is a box to tick for each; scores bought with a budget are numbers that count the points as you go; a name or other open answer can be typed in; and Let the dice decide rolls that one alone (`char roll c3 --one`). Back takes the last step back, so its question comes again (`char back c3`: the rolls it made are marked undone, and Undo brings the step back). Then Roll the rest, Edit, Discard… (it asks first) and Commit, which opens the new character's record, or lists what the generator made. A generator's draft is the GM's: the player view shows only that it's there.
- **Graph:** records as nodes and links as edges. Drag nodes, drag the background to pan, zoom with the wheel; hover to light up a record's neighbours; click to open one. The Graph button on a record's page shows just its neighbourhood.
  - **Map** (the switch above the graph, or Open the map on Status): the places the party knows, the paths between them (labelled road, trail, …), the region each lies in (dashed), and where the party is. A path to a place not found yet leads to a "?"; the GM view shows every place.
- **Journal:** the sessions, each opening to its scenes, beats and rolls. Each beat has Edit and Remove (hover over it), which open the `beat edit` and `beat rm` forms.
- **Reference:** search everything (results appear as you type), run the enabled packs' rules from forms, roll their tables, and read their rules text, glossary and guides.
- **Library:** worlds and campaigns (open, close, create, delete), packs (each with what it is; enable, disable, install, uninstall; the packs that ship with Didact have an Install button), the history (Undo, Redo, Jump back, Clear), save points (rewind, remove) and backups (back up now, restore, delete, keep the newest few; those made when a session ends are marked auto). With no campaign open, the Overview lists the world's campaigns to open one.
  - Deleting a world or campaign asks first, and Undo brings it all back.
  - Jump back (beside each change) takes back everything after that change (`didact undo --to e40`): its page lists what goes first. Each change is undone and each roll marked undone, not deleted: Redo, or jumping back to a later change, brings them back. Show older changes lists more of the history.
  - The core pack is always on. One game system is in use at a time: the open world's, which it keeps for good (chosen when it's made). Another system plays in a world of its own: its row opens a world that plays it, or makes a new one. Uninstalling a pack can't be undone: install its .didactpack again.
  - Clearing the history first shows exactly what goes and what stops working, with a button to back up first. It can't be undone, and neither can deleting a backup.
  - Start over: **Reset…** empties the library, as if Didact were newly installed, and numbering starts again at #e1. Its page shows what goes first. The library is backed up first, and backups stay (installed packs too, unless you tick the box).
  - Restoring a backup first shows what it holds next to the library now. The library as it was is backed up first: Undo can't take a restore back, but restoring that backup can.
- **Commands:** every command as a form, and a box that takes a whole command line. Each box takes what its argument takes: a number, an id or an event (`e12`) by its pattern, an amount of game time as a number and a unit, and a list to pick from of the records, drafts, packs, save points, oracles, tables and rules here.
- **Settings:** the campaign's options (its system's variant and optional rules, which its rules, character creation and generators follow; each says what it does: an optional rule what turning it on changes, a choice what each of its values means, and a default that another option sets says which), the app's language, the thesaurus (the language searches use for synonyms: download one, with a progress bar, switch between those downloaded, remove one) and the code's documentation.
  - The app, its guides and what commands show in it come in 24 languages. Without a choice, the app follows the browser's language. The command line and the LLMs that use it stay in English: the language chosen here is only the app's.
  - The code button in the header bar opens the code's API documentation. It's built from the code the first time, and again whenever the code changes (`didact docs build`).

Every change runs a real `didact` command, so it is checked, logged and undoable exactly as on the command line. The app shows the command it ran each time (`didact set sweeney hp-=2`), with an Undo button when there is something to take back.

A box takes only what its command takes. An id (a world's or a campaign's) and a record type take lowercase letters, digits and dashes: spaces become dashes and capitals go lower case as you type. A field's name takes no spaces (they become underscores), a detail's name is one word, and numbers take numbers. What a box takes is written under it, and the command checks again anyway.

Saving never overwrites a change you haven't seen. If the record changed after the page showed it (an LLM changed it from the command line, say, or another tab did), the save is refused and says what's there now. A description you were editing stays in the editor, next to the new version, to merge and save again. − and + always go through: they add up.

## Player view and GM view

The app shows what the players know, as `didact show` does: secret records, `## Secrets` sections, secret fields and GM-only details stay out. The **GM** button in the header bar turns the GM view on, and a banner says so ("GM view: spoilers shown"). The browser remembers the choice.

In the player view:
- a description with GM-only lines can't be edited (saving it would lose them): turn the GM view on first;
- a GM detail or secret field the page doesn't show can't be written over, though a new note for the GM can be added;
- the history names the command and the records the players know (`set · Freya`), never the values, and Undo says which change it took back, not what it was.

## Safety

The app can change your library, so it only listens to this machine by default.

- `--host` with another address lets other machines reach it, and Didact warns about that. Use it only on a network you trust.
- It answers only requests addressed to itself (its own address, `localhost`, `127.0.0.1` or `[::1]`, with its port). That stops other websites from reaching it through DNS tricks.
- Every change needs a form from the app itself: a secret token in each form must match a cookie that other sites can't read or send.
- There is no login. Anyone who can use this computer's browser can use the app.
