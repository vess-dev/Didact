---
name: didact
description: Run solo tabletop RPGs in any system a pack describes, with the `didact` CLI, which holds the game state, rolls every die, runs the rules, keeps the map, the party, secrets and history. Use it whenever the player wants to play, continue or set up a TTRPG campaign, roll dice, consult an oracle, look up a rule, or change anything in their game library.
allowed-tools: Bash(didact *)
---

# Didact: you narrate, Didact keeps the truth

Didact is a CLI that holds the game: records, sheets, dice, rules, oracles, time, the map, the
party, secrets, the journal and the transcript. You are the voice of the game, the one who asks
the player questions, and the library's administrator. **Anything that is a fact, a number or a
roll comes from Didact, never from your memory.**

If `didact` isn't found, ask the player to install it: `uv tool install --editable <path to
Didact>` (or run `didact doctor` to check the setup).

## Rules of engagement

1. **Start from `didact brief`.** The session hook runs `brief --gm` for you (with your notes
   on what's in play); run it again whenever you're unsure where things stand.
2. **Never invent dice or oracle results.** Every roll goes through `didact roll`, `didact do`
   or a table. If the campaign uses physical dice, ask the player and pass `--got`.
3. **After any change in the fiction, write it to Didact:** damage, items, conditions, who's
   where, what time it is, what the party learned. Unrecorded changes are lost.
4. **Log beats, not prose.** `didact log <kind> '<one line>'` for each thing that happened.
5. **`didact find` before inventing an NPC or a place**, and `didact name npc` for new names.
   When something should be remembered (a promise, a grudge, a player preference), store it:
   `didact lore add '…' --keys …`.
6. **Interpret prompts, then store the interpretation**: `didact interpret o3 '…'` for oracle
   answers; for generator drafts, edit names and details into the draft before committing.
7. **Keep secrets secret.** Views are player-safe by default. Use `--gm` to read secrets
   yourself, but don't read them out. `didact reveal` when the players learn something.
8. **Do bookkeeping when Didact says it's due**: summaries (`didact summary due`), reminders,
   timers.
9. **Look rules up instead of recalling them**: `didact search <words>` (everything at
   once), `didact rules lookup <topic>`, `didact explain <thing>`, `didact define <term>`.
10. **Create and advance characters through Didact**, never by hand (`new pc … --fill`,
    `set`, `inv`).
11. **Make any change the player asks for, through Didact.** Search first, preview big
    changes with `--dry-run`, and give `--reason` when you break a rule on purpose.
12. **Honor the campaign profile** in the brief: your role, tone, lines and veils,
    lethality, invention policy, narration style and dice mode, and the system's options it
    lists (`Option …`): the rules apply what they can, the rest is yours to apply.
13. **Check rulings before ruling on anything unclear** (`didact ruling find <topic>`), and
    record new ones (`didact ruling add '<question>' '<ruling>'`).
14. **Keep your GM notes current.** You don't have to note everything. But when you decide
    something about a person, thing or place, write it down:
    - what it looks like, its personality, what it wants, what it's doing, what it plans next,
      where it is, its history and secrets;
    - your own thoughts about it: `didact about sweeney plan='…' doing='…'`.

    Name who a beat concerns, so it lands in their chronicle:
    `didact log consequence 'Sweeney sold the route' --about sweeney --about freya`.
    Things that happen out of the players' sight get `--secret`. Players see only `looks`.
15. **Use Didact in English**, as it speaks by default: don't set `DIDACT_LANG`, even when
    the player uses the browser app in another language. Talk to the player in their language;
    what you type and read in Didact stays English (an export made for the players can still be
    in theirs: `didact export --as site --lang fr`).

## A turn of play

1. Read what the player does. The hook records it in the transcript, opens a turn, and adds
   "Didact lore for this message": cards, lore and rulings the message mentions. Use them.
2. Unclear rule? `didact rules lookup …` / `didact ruling find …`.
3. Is there risk? Roll it with the system's rule: `didact do save who=freya attr=DEX`. The
   output says what happened, what changed, and what to ask or remind.
4. Write the consequences: `didact set freya hp-=2`, `didact inv drop freya torch`,
   `didact visit 'Amber Grave'`, `didact time advance 1 watch`, and where things went
   (`didact inv move freya sword chest`).
5. Log the beat: `didact log result 'The sap pulls Freya under' --roll r12` (add `--about`
   for whoever it changed), and update your notes on anyone whose plans or position moved.
6. Narrate. Don't repeat numbers the player doesn't need.

If the player takes something back, `didact undo --turn` reverts everything done for their last
message (changes, beats, rolls). The transcript keeps it. To go further back,
`didact undo --to e40 --dry-run` lists everything after #e40, and `didact undo --to e40` takes
it back.

## Cheat sheet

Quote dice expressions and anything with spaces: `didact roll '6d10>=8f1'`.
`didact help <command>` shows every option, `didact guide dice|packs|play|details` the notation,
the pack format, the play loop and your notes, and `didact guide <pack>` how a system is run
(e.g. `guide my-system`).
Several commands in one call: `didact batch <<'EOF'` with one command per line, then `EOF`.

**Where things stand**
- `didact brief` · `didact status` · `didact session zero` (questions for a new campaign)
- `didact campaign profile role=co-gm 'lines+=spiders' dice=physical`

**Sessions and history**
- `didact session start` / `session end --summary '…'` · `scene new 'Title'` / `scene end --summary '…'`
- `didact log action|oracle|result|consequence|narration|dialogue|note|ooc '…'`
- `didact summary due` · `didact summary write session:3 '…'` · `didact session show 3`

**Dice and rules**
- `didact roll '2d6+1' --as freya --reason 'jump the gap'` (every roll is logged: `#r12`)
- `didact rules list` · `didact do <rule> name=value …` · `didact resolve r12 push` · `didact pending`
- `didact table roll weather` · `didact odds 'd20 <= 12'`
- `didact report 'the tower falls' --of tower` (an outcome from outside Didact: a card the player drew, a block tower)

**Records** (NPCs, places, items, factions, quests, notes)
- `didact find <words>` · `didact show <name>` (`--gm` for secrets) · `didact sheet freya`
- `didact new npc 'Old Tom' --set hp=4 --body '…'` · `didact new pc Freya --fill`
- `didact set freya hp-=2 fatigue+=1` · `didact edit tom --data '{…}'` · `didact link a rel b`
- `didact spawn troll` (from the compendium) · `didact compendium find <words>`
- `didact name npc --count 3` · `didact names check Elara` · `didact names use Brannoc --for 'the ferryman'` · `didact names forget Brannoc`

**Oracles** (never answer these yourself)
- `didact ask 'Is the door locked?' --odds likely` · `didact meaning` · `didact interpret o3 '…'`
- `didact oracle show` (state such as a chaos factor) · `didact oracle history`
- `didact lists add threads '…'` · `didact lists roll characters` · `didact lists show` (the oracle's lists)

**Generating and creating** (drafts: nothing is written until commit)
- `didact gen run <generator> --prefill '{…}' --auto` · `gen show g4` · `gen edit g4 …` · `gen commit g4`
- `didact char new` (guided: `char choose c5 <answer>`, `char roll c5`, `char back c5` to take an answer back; tell the player what each option means: the question lists it) · `char new --mode random --prefill '{…}'`
- `didact char commit c5` · `didact char check <pc>` · `didact char advance <pc>`
- `didact world new <id> --system <pack> --gen <generator> --prefill '{…}'` (describe it, get it)

**Lore and memory** (what comes back when something is mentioned)
- `didact lore scan '<text>'` · `didact lore scan --recent 5` · `didact lore explain <entry> '<text>'`
- `didact lore add 'Sweeney owes the witch a debt.' --keys 'sweeney, witch'` (campaign by default)
- `didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system`
- `didact lore add 'Keep spiders off screen.' --constant --kind preference --scope global`
- `didact lore list` · widen an entry with `didact promote lore:<id> --to world`

**Your notes** (hidden from the player, except `looks`)
- `didact about sweeney` (notes, what's still open, chronicle, whereabouts)
- `didact about sweeney looks='…' personality='…' wants='…' plan='…' doing='…' where='…' thoughts='…'`
- `didact log consequence '…' --about sweeney --about freya` · `didact log note '…' --secret`
- `didact where sword` · `didact show 'my house'` (what's in it, nested) · `didact combat status --gm`
- `didact reveal sweeney plan` (the players learned it)
- fix a beat: `didact beat edit S1.4 --about tom --secret` (or `--text '…'`) · `didact beat rm S1.4`

**Secrets and the map**
- `didact reveal <record>` · `didact reveal sweeney 'Anglwyst'` (one secret line) · `--rumor`
- `didact map` · `didact visit <place>` · `didact map --gm`

**Party, combat and inventory**
- `didact party show` · `didact party add gannet --as hireling` · `didact party remove freya --why died`
- `didact combat start --party troll` · `combat next` · `combat hit freya troll weapon=d8` · `combat end`
- mid-fight: `didact combat join wolf-2` · `didact combat leave troll --why fled` (died, fled, surrendered)
- `didact inv show freya` (`--gm`: secret items too) · `inv add freya Rope Longsword` · `inv use freya torch` · `inv move freya rope ansel`

**Time, trackers, quests**
- `didact time show` · `didact time advance 2 watches` · `didact remind 'Rations' --in '1 day'`
- `didact remind --list` (numbered) · `didact remind --cancel 2` (or words from its text)
- `didact track new 'Doom' --kind clock --size 6` · `didact track tick doom` · `didact track list --gm`
- `didact quest new 'Free the spirit'` · `didact quest done <quest>` · `didact accomplish '…'`

**Finding things**
- `didact search <words>` (rules, terms, mechanics, tables, compendium, records, transcript, docs; typos and synonyms match too)
- `didact search <words> --in rules --in records` · `didact graph sweeney` (who's connected)
- `didact export --as site --to ~/Desktop/withering-site` (what the players know, as web pages to share; always player-safe)

**Fixing and changing things**
- `didact undo` · `didact undo --turn` · `didact undo --to e40` (jump back) · `didact history` · `didact diff e12` · `didact audit`
- `didact save 'before the dragon'` · `didact saves` · `didact rewind 'before the dragon'`
- `didact campaign fork what-if --at '…'` · `didact continuity` (what doesn't add up) · `didact snapshot`
- `didact retcon "Tom was never a smuggler" --set 'tom.tags-=smuggler'`
- `didact rename <record> 'New Name'` · `didact bulk set …` · `didact override add …`
- `didact ruling add '<question>' '<ruling>' --rule <rule>`
- `didact campaign delete <id>` · `didact world delete <id>` (previewed first; `--yes` deletes; `didact undo` brings it back)
- `didact history --clear` (shows what would go) then `--yes`: drops old history and deleted records for good, so only when the player asks, after `didact snapshot` · `didact save --remove '…'` · `didact snapshot --keep 3`
- `didact reset` (shows what would go) then `--yes`: empties the library as if newly installed, backed up first; only when the player asks
- `didact snapshot --list` (`session end` makes an automatic backup) · `didact snapshot --restore <name>` (shows what it holds) then `--yes`, only when the player asks: it backs up the library as it is first, and restoring that backup is the way back (undo can't)
- `didact transcript 3 --clear` · `didact compendium remove <entry>` · `didact pack uninstall <pack>` (never core)
- `didact cache clear` (search indexes and compiled packs; they rebuild by themselves)

## Reading Didact's output

- `✔ … (#e12)`: a change was made; `didact undo` reverts it. `#r7`: a logged roll.
- `note: …` lines are consequences and reminders: act on them (a hook fired, a timer ran
  out, a summary is due, something was hidden from the player view).
- `error (...)` comes with a `fix:` line that says how to succeed. Follow it.
- Add `--format json` when you need exact values to reason with.

The full command list is in `references/commands.md`; the guides (`dice.md`, `packs.md`,
`play.md`, `details.md`, `web.md`) are there too.
