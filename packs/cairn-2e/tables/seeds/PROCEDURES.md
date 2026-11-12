# Seed procedures: brief for the generators

This file describes how the three seed chapters of the Warden's Guide roll the tables in `setting.yaml`, `forest.yaml` and `dungeon.yaml`. The steps follow the book's order. Source: Cairn Second Edition, CC-BY-SA 4.0.

**Conventions**
- `a` + `b` means two tables made from the book's two columns. Roll each once and combine the results ("Roll 1d20 for each column and combine the results").
- **Row data for `if:` steps** (e.g. `@drop.poi == 'lair'`):

  | Table | Data key | Values |
  |---|---|---|
  | `setting-terrain-die-drop` | `difficulty` | easy, tough, perilous |
  | `setting-poi-die-drop` | `poi` | waypoint-or-settlement, curiosity, lair, dungeon |
  | `forest-die-drop` | `poi` | monster, ruins, shelter, hazard |
  | `dungeon-die-drop` | `room` | monster, lore, special, trap |
  | `setting-faction-advantage-count` | `count` | 1–4 |
  | `setting-faction-action` | `goals` | 0/1 (change) |
  |  | `advantages` | −1/0/+1 (change) |
  |  | `obstacles` | 0/1 (change) |

- **`what` and `detail`** on the die-drop entries (and the terrain die drop) name the two tables to roll next, so a generator can say `table: "{@drop.what}"`. Waypoint-or-Settlement has none: choose first.
- **Die drops.** A die drop is a d6 rolled onto the map. Its face is one roll on the die-drop table, and where it lands places the region, POI or room. The `map:` generator step emulates positions, paths and distances.
- **Counts.** A count given as a range ("3-8 d6") is the Warden's choice. The dice in brackets are defaults for `--auto`; they are not in the book.
- **Rerolls.** Every chapter says: "if you don't like a table result, roll again or tweak as desired!" Every rolled value should be prefillable.

## Setting seed (`setting-*`, wardens-guide/setting-seeds)

A setting seed builds one region: its people, factions, terrain, water, weather, POIs and paths.

1. **Culture.** `setting-culture-character` + `setting-culture-ambition`: the people's character and ambition.
2. **Resources.** `setting-resources-abundance` + `setting-resources-scarcity`: what is plentiful and what is rare. Both columns hold the same 20 resources, and the book doesn't rule out a match.
3. **Factions.** A smaller region with fewer POIs has 1–2 factions; a larger one has up to 5–6. So decide the POI count (step 7) first. The book says "Roll one or more times" on these tables. For each faction:
   - `setting-faction-type` + `setting-faction-agent`. The agent is a representative in charge of one or more of the agenda's goals. Particularly large factions have more agents, one per goal. An agent may have personal motives that differ from the agenda. Agents need a WIL score for opposed saves. The book gives no roll for it; its example agent has WIL 15.
   - `setting-faction-trait-1` + `setting-faction-trait-2`.
   - `setting-faction-advantage-count`, which gives `count`. Then roll `setting-faction-advantage` `count` times and **reroll repeated results**. Advantages are the faction's influence, materials, wealth and other unique features.
   - `setting-faction-agenda` + `setting-faction-obstacle`: the objective and its primary obstacle. The Warden then writes **3–5 progressive goals** toward the objective. Each goal acquires a distinct advantage needed for the next one. At least one goal deals with the obstacle, either the first goal or the last.
4. **Terrain.** Roll 1d6: that is the number of terrain dice.
   - For each terrain die, roll `setting-terrain-die-drop` for its `difficulty`, then that difficulty's pair:
     - easy: `setting-easy-terrain` + `setting-easy-landmark`
     - tough: `setting-tough-terrain` + `setting-tough-landmark`
     - perilous: `setting-perilous-terrain` + `setting-perilous-landmark`
   - The terrain is the region carved out around the die.
   - The landmark replaces the die and is drawn as a triangle. It is a unique, visible POI and a reference point, seen best from high ground.
   - Dice that roll off the page are rolled again until none remain, so the count is exactly the 1d6.
   - Any empty space still needing terrain gets one more die, used the same way.
5. **Water.** No table. Every region needs a water source: a river from the highest point (e.g. Mountains) to the lowest. It ends in a lake or the sea, or runs off the map.
6. **Weather.** Roll once per season for the region's average weather: `setting-seasonal-weather-spring`, `setting-seasonal-weather-summer`, `setting-seasonal-weather-fall` and `setting-seasonal-weather-winter`. Optionally, roll `setting-unusual-weather` around particular landmarks or terrain.
7. **POIs.** A region has 4–9 POIs: the Heart plus 3–8 dropped dice.
   - **The Heart (H).** It is POI 1, placed close to a water source (step 5). It is the region's primary settlement, significant to its history and people, and "usually a Waypoint or Settlement". Roll that type's pair (below).
   - **The dice.** Drop 3–8 d6 [d6+2]. Dice that roll off the page are rolled again until none remain. For each die, roll `setting-poi-die-drop` for its `poi`. On a 1, choose Waypoint or Settlement.
   - Number the POIs starting from the Heart. Then roll each POI's type + feature pair:
     - waypoint: `setting-waypoint` + `setting-waypoint-feature`
     - settlement: `setting-settlement` + `setting-settlement-feature`
     - curiosity: `setting-curiosity` + `setting-curiosity-feature`
     - lair: `setting-lair` + `setting-lair-feature`
     - dungeon: `setting-dungeon-type` + `setting-dungeon-feature`. Flesh it out with the dungeon seed below.
   - A POI's terrain is the region it lands in: each POI takes the terrain of the nearest terrain die.
   - What each type means:
     - Settlement: a permanent, largely self-sufficient population center, usually governed by a political body or faction.
     - Waypoint: a safe place to resupply, sleep or get directions.
     - Curiosity: a remarkable or strange wilderness locale, hazardous only if the PCs interact with it.
     - Lair: an enemy encampment, a hive, or a source of heightened monster activity.
     - Dungeon: an explicitly dangerous locale or adventure site.
   - "Some POIs may allow the PCs to see more of the world than what appears on their map."
8. **Paths.**
   - Starting with the Heart, draw **1–4 paths per POI**: loops, branches, dead-ends and shortcuts. Some paths chain along terrain (mountain passes, rivers).
   - Path types:
     - Standard (thick line): obvious or well-trod.
     - Hidden (dashed line): on no known map; discovering one always costs something.
     - Conditional (crossed line): blocked, or needs tools such as boats or climbing gear, or a map or guide.
   - The book only says "some" paths are Hidden or Conditional and gives no odds.
   - Label each path by its ends, e.g. `1 ↔ 3`. The Warden decides whether it is a road, a trail or a wilderness route.
   - For each path, roll `setting-path-feature` + `setting-path-condition`.
   - **Watches:** a short path takes 1 watch, a medium one 2 and a long one 3. Add 1 for a trail and 2 for a wilderness route. A watch is 8 hours, and a day of travel is typically two watches and one rest. In a generator: `map:` with `paths: {max: 4}` and `watches: {short: 1, medium: 2, long: 3}`, then add the route's extra watches.
9. **Questions** ("Put It All Together"):
   - "What would draw people to this region? What keeps them here?"
   - "How do the people here think of outsiders? How do outsiders think of them?"
   - "What power do the Factions have over the people who live here?"
   - "Who or what threatens their agendas?"
   - "How would a faction interact with any newcomers (e.g. an adventuring party)?"
   - "How does the region's terrain and weather affect the people that live here?"

   In the book's example, a faction agent "should likely appear in an important place such as the region's **Heart**." "To expand your realm, repeat the process as many times as you wish."

**Faction actions (during play, not generation).**
- Factions act even if the PCs do nothing.
- Whenever the fiction positions a faction to advance a goal, roll `setting-faction-action` (d6). Apply its data: a goal achieved, advantages lost or found, a new obstacle.
- If two factions are opposed, the faction most at risk makes a WIL save with its highest-ranking agent's WIL. On a fail, it doesn't roll this time.
- The PCs' actions can overrule the roll or shift it either way.
- Completing an agenda is a significant event that can change the region, and the map should keep reflecting the factions' progress.
- A `settings.factions.turn` rule for `didact faction turn` could roll this table.

## Forest seed (`forest-*`, wardens-guide/forest-seeds)

Use it for any forested terrain in a region, e.g. a setting seed's Forests, Woodlands, Rainforests or Jungles. "If a conflict or interesting pattern emerges, be open to restating or modifying any earlier results!"

1. **Description.** `forest-description-1` + `forest-description-2`, e.g. "Diseased, Frozen". Both of the book's columns are headed "Description". The result is how outsiders perceive the forest, plus its unique natural features. If the forest came from a setting seed, consider how that terrain's Landmark affects it. Forest landmarks are mostly seen only by climbing a tree; a few stand out, and some are heard rather than seen.
2. **Spirit of the forest.**
   - `forest-traits-virtue` + `forest-traits-vice`: the general attitude of the forest's creatures.
   - `forest-agenda-goal` + `forest-agenda-obstacle`: what the forest wants as a whole, and what stands in its way.
3. **POIs.** Drop 8–12 d6 [d5+7]. Dice that fall off the page are ignored, so fewer POIs is fine.
   - For each die, roll `forest-die-drop` for its `poi`.
   - Pick two opposite points near the page border as the entrance and the exit. Number the POIs from the entrance (1) to the exit (last).
   - Roll each POI's pair:
     - monster: `forest-monster` + `forest-monster-activity`
     - ruins: `forest-ruin` + `forest-ruin-feature`
     - shelter: `forest-shelter` + `forest-shelter-feature`
     - hazard: `forest-hazard` + `forest-hazard-feature`
   - Filter every result through steps 1–2.
   - What each type means:
     - Monster: a dangerous creature with its own wants, not one waiting to attack ("People can be monsters, too").
     - Ruins: the remnants of attempts to tame the Wood.
     - Shelter: somewhere people have built a life, a respite for travelers.
     - Hazard: a trap or danger laid by the forest itself.
4. **Trails.**
   - From the entrance, draw **1–4 paths between each point**: loops, branches, dead-ends and shortcuts. Some are Conditional and some Hidden (see setting step 8). Where possible, add crossings with no point between them.
   - Trails are runs of paths linking 3–4 points "in an obvious, consistent, or interesting manner". Hidden paths and short isolated routes usually aren't part of one.
   - For each trail, roll `forest-trail-type` + `forest-trail-marker`.
   - "If some of the results seem incongruous, that's OK! Turn these juxtapositions into questions like "Why is there an old logging road leading to the bandit's hideout?""
5. **Encounters.** The book has no table for this step. `forest-example-encounters` is the book's example forest's own table. The book heads it d20 but prints only 6 rows, so it rolls a d6. It shows the style: write one encounter table per forest, drawing on its POIs and agenda.
6. **Name.** There is no table in this chapter; the naming-procedures chapter has the formula.

**Exploring a forestcrawl.**
- Use the dungeon exploration procedure, but roll Wilderness Events instead of Dungeon Events.
- Going off-trail costs time, effort or tools. Make the cost clear; it always triggers a Wilderness Events roll.
- On marked trails, a small forest (10–15 POIs) can be explored in a single watch.

## Dungeon seed (`dungeon-*`, wardens-guide/dungeon-seeds)

Run it for each Dungeon POI of a setting. Start from the POI's `setting-dungeon-type` + `setting-dungeon-feature` and its terrain. Ask: "What image springs immediately to mind? Where is the dungeon located? What does its entrance look like?" These may only be answerable at the end.

1. **History.**
   - `dungeon-purpose-original-use` + `dungeon-purpose-built-by`
   - `dungeon-construction-entrance` + `dungeon-construction-composition` (what it's built of)
   - `dungeon-ruination-condition` + `dungeon-ruination-cause`
   - Questions: "What kind of dungeon is this, and what makes it unusual?" and "Why was this dungeon built, how was it built, and what caused its downfall?"
2. **Denizens and factions.**
   - `dungeon-traits-virtue` + `dungeon-traits-vice`, **once**: the general attitude of the dungeon's intelligent creatures.
   - The same pair **again** for at least one standout NPC. This NPC prefers dungeon life, acts differently from the rest, and is someone the party can talk to, trade with, hire or aid.
   - **One or more factions** (the example has two). Each gets `dungeon-agenda-goal` + `dungeon-agenda-obstacle`, plus leaders and a hierarchy (no table).
   - Questions: "What do we know about the creatures and factions that occupy the dungeon?" and "What is each faction trying to achieve, and what stands in their way?"
3. **Theme.** No table. Combine steps 1–2 into a paragraph. The example adds hooks and "features throughout" (light, smell, noise, build).
4. **Map.**
   - Drop 6–20 d6 [d15+5]. Dice that fall off the page are ignored.
   - For each die, roll `dungeon-die-drop` for its `room`.
   - If a room feels "too far" from the rest, drop one more die and add a room.
   - The room closest to the page border is the entrance. Number the rooms from it.
   - Paths: from the entrance, draw **1–4 between each room**: loops, branching hallways, dead-ends and shortcuts. Some are Conditional (hidden levers, climbing gear) and some Hidden. Add crossings with no room between them.
5. **Stock the rooms.** Roll each room's pair:
   - monster: `dungeon-monster-group` + `dungeon-monster-activity`
   - lore: `dungeon-lore-room-type` + `dungeon-lore-clue`
   - special: `dungeon-special` + `dungeon-special-feature`
   - trap: `dungeon-trap` + `dungeon-trap-trigger`

   Filter each result through the theme, and "Name each room!". What each type means:
   - Monster: a creature with its own wants; it may talk, reason or beg.
   - Lore: builds the theme, teaches a lesson, or links to an NPC or faction. It holds no danger, but the players mustn't know that.
   - Special: a hidden or interactive element (challenge, obstacle, puzzle) offering hard choices with lasting costs.
   - Trap: a hidden danger triggered by interaction, with hints of its presence.

The chapter's Dungeon Principles (purpose, levels, layout, verticality, secret areas, rooms, treasure, challenges, NPCs, factions, puzzles, the dungeon map, room keying, encounter tables) are Warden guidance with no rolls. They make good closing prompts for the generator.
