# Playing a session

How a game runs through Didact: the LLM narrates, and Didact keeps every fact, roll and change.

## Before the first session

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

A world keeps the system it was made with, and its campaigns play it: another system plays in a world of its own. `didact campaign close` puts a campaign away (its world stays open) and `didact campaign open <id>` picks it up where it was left, session and all.

`didact world delete <id>` and `didact campaign delete <id>` remove one, previewed first; `--yes` deletes, and `didact undo` brings it all back.

`session zero` lists the questions to settle with the player. The pack's own come first, with the system's options (its variant and optional rules): its rules follow those answers, and the brief says what each one changed means. Every brief carries the answers.

## A session

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Turns:** each player message opens a turn (the Claude Code hook calls `didact capture`, and other clients use `turn begin`). `didact undo --turn` takes back everything done for that message: changes, beats and rolls. The transcript keeps it.
- **Jumping back:** `didact undo --to e40` takes back everything after #e40, newest first (`--dry-run` lists it): each change is undone and each roll marked undone. Nothing is deleted: `redo`, or jumping back to a later change, brings it back.
- **Time:** `didact time advance 1 watch` runs out timers, brings up reminders and runs time triggers. `didact remind --list` shows the reminders to come, and `didact remind --cancel 2` drops one. A campaign opens on the calendar's start, or on the date `campaign new --date '4 July 1902'` gives, and `didact time set '<date>'` changes it until the first session.
- **Places:** `didact visit <place>` moves the party and marks the place visited. `didact map` shows what the party knows, and an unexplored exit is `?`.
- **Fights:** `didact combat start --party troll`, then `combat next`, `combat hit freya troll weapon=d8` and `combat end`. Fighters come and go mid-fight: `didact combat join wolf-2` (in individual mode they roll initiative) and `didact combat leave troll --why fled`. Nobody's turn is skipped.
- **Things:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (or into a chest, or onto a place); `didact where rope` finds it. `inv add` finds a compendium item by its id, its name or an alias.
- **Your notes:** `didact about sweeney plan='…' doing='…' where='…'` keeps what you've decided about anyone or anything. Players see only `looks`. `didact log … --about sweeney` puts a beat on their record (`--secret` if the players don't see it). `didact guide details` has more.
- **The world moving on:** `didact faction turn`, plus clocks: `didact track new 'The flood' --size 6`. A command for one kind of record takes a name others share as that kind: `didact track roll draugr` rolls the pool a foe is named for (`track tick` a tracker, `quest done` a quest and `visit` a place, likewise).

## Oracles, generators and characters

```
didact ask 'Is the ferryman home?' --odds likely        # #o3 ? … → Yes, but…
didact interpret o3 'Home, but drunk and grieving.'     # what it meant, kept with it
didact meaning                                          # two words to interpret: betray · oath
didact gen run pointcrawl --prefill '{"terrain": "Swamp"}' --auto   # a draft: #g4
didact gen edit g4 poi-1.name='Amber Grave'
didact gen commit g4
didact char new                                         # guided: answer with `char choose c5 …`
didact char back c5                                     # take the last answer back: ask it again
didact char new --mode random --prefill '{"name": "Wren", "background": "Cutpurse"}'
didact char advance wren                                # the system's level-up, step by step (#c6)
didact world new fenmoor --system my-system --gen <generator> --prefill '{…}'
```

Nothing a generator or creation makes is written until `commit`. Describe what the player wants in `--prefill`, and the procedure fills the gaps. A question lists what each option means when the pack says (`- Cutpurse: …`): tell the player, so they choose knowing what they get.

## Secrets

Views are player-safe by default: `show`, `find`, `sheet`, `map`, `brief`. They leave out:
- secret records (`knowledge: secret`);
- `## Secrets` and `## GM notes` sections;
- `secret: true` fields.

`--gm` shows everything. When the players learn something:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` writes what the players know as a small website to share or read on a phone: the party, a page per record, the journal and the map. It's always player-safe, and exporting again to that folder updates it. `didact export --as lonelog` writes the journal in Lonelog notation (`@ ? d: -> =>`, scenes as `S1`, tags like `[N:Sweeney]`), player-safe too.

## Lore: what comes back when something is mentioned

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **What counts:** every NPC, place, item and faction is a card keyed by its name and aliases. Lore entries have `keys`, and rulings come up through their rule. Matching is on whole words, and plurals count ("wolves" matches `wolf`).
- **When lore comes up:** the Claude Code hook scans each player message. `log`, `scene new` and `show` also carry newly triggered lore, and an entry isn't repeated for a few turns.
- **Tuning an entry:** `--secondary` with `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (in turns or scenes), `--constant` (always in the brief) and `--no-recurse`.
- **Scopes:** entries go to the campaign unless `--scope` says world, system or global. A scan only sees this campaign, its world, its system and global, never another world. A narrower entry with the same id shadows a wider one.
- **Other tools' lorebooks:** `didact lore import <file>` reads SillyTavern World Info (KoboldAI's too), a character card's lorebook and NovelAI's `.lorebook`; `didact lore export --to <file>` writes World Info. Keys, logic, priority, probability, groups and timing carry over.

## Changing the story

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` changes the fact but keeps the old value. It also marks summaries that mention Sweeney as stale, and `audit` lists it.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` records a ruling. It then shows up in `rules lookup` and when that rule runs.
- `didact name npc` rolls a fresh name, never one the world already uses. Before you invent one, check it with `didact names check <name>`. `didact names forget <name>` frees one again.

## Housekeeping

- `didact history --clear` shows what clearing old history would drop; `--yes` drops it for good, deleted records included, and undo, `diff`, `rewind` and older save points can't reach it any more (`--before e120` keeps that event and later ones, `--rolls` drops the dice record too). Run `didact snapshot` first.
- `didact save --remove 'before the dragon'` removes a save point; `didact undo` brings it back.
- `didact transcript 3 --clear` deletes session 3's transcript (`--clear --all`: every session's). `didact undo` brings it back, and the text stays in the history until `history --clear`.
- `didact compendium remove <entry>` deletes an entry you added; records spawned from it stay.
- `didact snapshot --keep 3` deletes all but the newest three backups, and `didact snapshot --remove <name>` deletes one. Neither can be undone.
- `didact session end` backs the library up by itself (`snapshot-<time>-auto.zip`), keeping the newest five of those; `didact snapshot --list` marks them.
- `didact reset` shows what emptying the library would take; `--yes` makes it as newly installed: every world, campaign and record, the history and the search index go, and the next change is #e1 again. It backs the library up first (`…-before-reset.zip`), and the backups stay, as do installed packs unless `--packs`. To try Didact on a ready-made campaign instead, `didact sample` builds the sample one into an empty library (`--home` gives it a folder of its own), and `didact serve --demo` serves it afresh.
- `didact snapshot --restore <name>` shows what a backup holds next to the library now; `--yes` backs the library up as it is (`…-before-restore.zip`), then puts the backup in its place. Event and roll numbers carry on. Undo can't take a restore back: restoring that safety backup can.
