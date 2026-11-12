# Names: how the tables combine

```
didact table roll poi-name --with poi=Keep     # "Sunken Keep of (the) Blue"
didact table roll place-names                  # "Tarn of the Crimson Moon"
didact name npc                                # first-names + surnames: "Luna Crow"
```

Sources: `wardens-guide/naming-procedures` (`names.yaml`) and `wardens-guide/npc-tables` (`npcs.yaml`).
A `{word}` in an entry rolls the table named in the table's `refs`. A value passed in by the
caller (`--with word=…`, or `with:` on a rule's `table:` step) wins over the ref. The formulas
carry their own spaces and "of", so their results are finished names.

## People (`npcs.yaml`)

- **`first-names`** picks one of `npc-name-1`, `npc-name-2` or `npc-name-3` (d20 each, 60 names).
- **`surnames`** rolls `first-names` again. The book has no family names: NPCs and backgrounds
  have one name each, so a second book name stands in as a family name or byname.
- **`settings.names.npc: [first-names, surnames]`**: `didact name npc` rolls both and joins them
  with a space. About 1 roll in 60 repeats the first name ("Luna Luna"): take the next candidate.
- **A quick NPC:** roll `npc-quirk`, `npc-background`, `npc-goal`, `npc-virtue` and `npc-vice`
  once each, in any order. The book gives no procedure for combining them.

## POIs

1. Roll `poi-name` (the d6 Names Formula) for each POI.
2. `{noun}` rolls `nouns` (d100) and `{adjective}` rolls `adjectives` (d100).
3. `{poi}` is the kind of place. Pass it in, e.g. `poi=Keep`: the setting seeds' POI tables
   (Settlements, Waypoints, …) give the kind. Without it, `terrain-synonyms` fills the slot.
4. "(The)" and "(the)" are optional, as in the book: keep the article or drop the brackets.

## Regions

- **The formula:** use `poi-name` with the terrain as the POI: `poi=<terrain type or a synonym>`.
- **A synonym for a known terrain:** roll `terrain-synonyms-<terrain>`, e.g.
  `terrain-synonyms-hills`. Jungle uses forest, Sea uses beaches, and Wasteland uses desert:
  these are the book's "See …" rows.
- **`terrain-synonyms`** (d24; the book gives no die) rolls a row, then one of that row's
  synonyms. `data.terrain` names the row.

## `place-names` (`settings.names.place`)

- **One roll** runs the whole procedure. The entries are the six formula rows, each with and
  without "the", so 12 even entries and each row keeps its 1-in-6 chance.
- **The parts:** `{poi}` is a random terrain synonym (the book's advice for naming regions), and
  `{noun}` and `{adjective}` are as above.
- **The formula** is repeated in `place-names`. If you change one formula table, change the other.

## Factions

- **`faction-name`** is the d6 Faction Names Formula: `{noun}` → `nouns`, `{adjective}` →
  `adjectives`, `{group}` → `group-types` (d20).

## Realms

- **`realm-name`** is the d6 Ruler Names Formula: `{noun}`, `{adjective}` and `{rulers}` →
  `ruler-types` (d20). The book says to add "of" or "the" where appropriate.
- **Optionally**, replace any part with the dominant terrain synonym ("The Misty Bluffs"). Roll
  `terrain-synonyms-<terrain>` first, then pass the result in, e.g. `noun=Bluffs`.

## Forests

- **`forest-names`** is `{adjective} {noun}`: `forest-adjectives` (d100), then `forest-nouns`
  (d100), for example "Whispering Woods". It covers forest seeds step 6, "Name the forest".
- **The book's advice:** reroll or tweak for sound (alliteration) or contrast ("Twisted Canopy").

## Wiring notes

- **`didact name <kind>`:** `settings.names` could add `faction: faction-name`,
  `realm: realm-name` and `forest: forest-names`. `faction-name` and `realm-name` keep the
  book's "(The)". Expand them into 12 entries, as in `place-names`, if clean names are needed.
- **d100:** the book rolls 2d10 for tens and ones. The tables use `d100` with keys 1–100.
- **Kept as written:** Bogs "Quad" is probably "quag", and River "Runnel Creek" is probably
  "runnel, creek". Terrain synonyms are capitalized because they are name parts.
- **The Quirks table's header reads "Quirk 1",** but the book has only one quirk column.
