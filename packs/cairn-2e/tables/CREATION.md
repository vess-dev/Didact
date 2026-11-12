# Creation procedures: monsters, backgrounds, bonds and omens, growth

Notes on four Warden's Guide chapters (Cairn 2e, CC-BY-SA 4.0), for building generators and the guidance on templates. The tables are in `creation.yaml`.

| Chapter | Tables in `creation.yaml` |
|---|---|
| `wardens-guide/creating-monsters` | 8 d20 tables (the book's four two-column tables, one table per column) and 2 conversion lookups |
| `wardens-guide/creating-backgrounds` | none: the chapter has no tables |
| `wardens-guide/bonds-and-omens` | none: the chapter has no tables (the player's d20 Bonds and Omens tables are in `players-guide/character-creation`) |
| `wardens-guide/growth` | none: the chapter has no tables (its checklists are example Downtime milestones) |

## Creating monsters

### Procedure (`#overview`)

| Step | Roll | Book table |
|---|---|---|
| 1. Appearance | `monster-physique` + `monster-feature` | Monster Appearance |
| 2. Traits | `monster-quirk` + `monster-weakness` | Monster Traits |
| 3. Attacks | `monster-attack-type` + `monster-critical-damage` | Monster Attacks |
| 4. Abilities | `monster-ability` + `monster-ability-target` | Monster Abilities |
| 5. Describe | none | Describe the creature's appearance, abilities and attacks in plain English (the LLM's job). |
| 6. Stat it | none | Write the stats from the guidance numbers and the stat block format below. |

- Each step rolls 1d20 per column and combines the two results (Hunched + Carapace). The words are prompts to interpret, not stats.
- Book quirk: Monster Abilities row 20 is printed as "Zaps / Weakens", a copy of Monster Attacks row 20 ("Weakens" is not a target). Both entries keep the printed text, with a `note`.
- Principles: use Critical Damage to lean into the threat or strangeness of any aggressive NPC. Use flavor and style so creatures stand out (a pig-faced humanoid looking for his missing sheep beats a generic goblin archer). Always adjust stats for what is fun and interesting.

### Guidance numbers (the `monster` fields)

| Field | Guidance |
|---|---|
| `hp` | Hit Protection is the ability to avoid danger through toughness, speed or skill. 3 average, 6 hardier, 10+ a serious threat. |
| `armor` | Natural toughness, or something worn or carried. Raise it if the creature can withstand an attack without moving. 1–3 at most. |
| `STR`, `DEX`, `WIL` | 3 deficient, 6 weak, 10 average, 14 noteworthy, 18 legendary. |
| `STR` | Overall health, physical power and resistance to poisons: surviving a direct hit, not avoiding danger (that is HP). |
| `DEX` | Start at 10. Raise it if quick, agile or nimble; lower it if slow to respond, bulky or clumsy. |
| `WIL` | Withstanding another's influence, power over others, and defense in magical or spiritual matters. |
| `attacks` | Usually an object (sword, bow) or a natural weapon (claws, teeth). |
| `abilities` | A unique action or power usable both in and out of combat. |

Attack or ability:
- It can be meaningfully avoided or defended against by traditional means: an Attack, which goes through HP.
- It can't: an Ability.
- It affects a single PC: generally an immediate effect, with no Save that round (possibly none at all).
- It can affect a group of PCs: generally an immediate Save.

### Stat block (`#monster-stat-block-format`)

```
X HP, X Armor, X STR, X DEX, X WIL, Attack (dX, special items, qualities)
- An engaging descriptor of appearance, demeanor, or living habits.
- A quirk, tactic, or peculiarity that distinguish this creature.
- Special effect or consequence of critical damage.
```

The bestiary leaves out Armor when it is 0, and some creatures have no attack. The last line is the `critical` field; the other lines suit `abilities` or the body.

### Writing the critical damage line

- When it fires (players-guide/core-rules): damage past 0 HP comes off STR, and the target makes a STR save with its new STR. A failure is Critical Damage: a PC can only crawl and dies within the hour untreated, and an NPC or monster is dead (Warden's discretion). A monster's line is the extra effect when *its target* fails that save.
- Start from the `monster-critical-damage` verb (Asphyxiates, Ensnares, Severs…) and lean into the threat or strangeness.
- Write `Critical Damage: <what happens to the target>`: a concrete consequence, often ongoing or needing a save or help to end. The chapter's examples:
  - Thunder Snail: "Target is pulled into its rolling momentum, losing an additional 1 STR per round until freed (STR save to escape)."
  - Foxwoman: "Victim is choked unconscious."
- An ability can be made into an attack with a damage die, leaving Critical Damage to reveal its real impact.

### Worked example (`#monster-example`)

Rolls: Hunched + Carapace; Moves in a Straight Line + Weak Spot; Smashes + Grapples; Disables + Hearing. Description: a snail-like creature with a hard shell and a soft underbelly that moves only in straight lines, rolls into opponents and pulls them into its orbit, and roars loud enough to drown out other sounds. Reasoning: physically tough (higher STR, strong Armor), fast but not maneuverable (low DEX), a wild beast (low WIL), and it rolls in a line through several targets (blast). Result: **Thunder Snail**, 6 HP, 2 Armor, 14 STR, 6 DEX, 4 WIL, smash & roll (d10, blast), with the critical damage above.

### Converting from other systems (`#converting-monsters`)

Do HP first, then STR.
- **HP:** 3 (an average person) + 1 per HD. Think of HD as a d6 (mean 3.5).
- **Armor:** look for "as leather" or "as plate". B/X descending AC (ignore THAC0): 7 Leather, 5 Chainmail, 3 Plate mail. Ascending AC: 12 Leather, 14 Chainmail, 16 Plate mail. Armor runs 1–3 only. The chapter doesn't give the Armor for each; Leather 1, Chainmail 2, Plate 3 is the natural reading, and the Marketplace has Chainmail 2 and Plate 3. The fiction wins: the Foxwoman (AC 14) gets no Armor, since she has no protective hide.
- **STR:** start at 10. A creature that is hard to kill, but not because it is nimble or skilled, gets more STR, not more HP.
- **DEX:** start at 10. Quick (often "speed" or SP), agile or nimble-fingered: up. Slow to respond, bulky or clumsy: down.
- **WIL:** morale (ML, typically 2–12) is the guidepost; more personality, spirit or presence means more WIL. Lookup `monster-morale-to-wil` (`--with ml=8`) gives 4→6, 8→12, 10→15, 12→18 (each is 1.5 × ML). It has only those four keys, and the Foxwoman's ML 11 became 15 WIL, so treat it as a guide.
- **Saving throws** (`#saving-throws`): shorthand like (E1) or (F1) means a level 1 Elf or Fighter. A strong save suggests raising an ability: lookup `monster-saving-throw` (`--with 'saving_throw=Breath Attacks'`; `data.abilities` lists the candidates). It can also suggest a tag like "immune to toxic gas" or "good at dodging".
- **Combat:** damage dice usually copy as is (check them against the Marketplace weapons). Multiple attacks become blast or several dice (d6+d6: roll both and keep the highest, which Didact writes `{d6, d6}kh1`). Devastating attacks become enhanced, get blast, or get several dice.
- **Abilities:** if the mechanics don't translate, write a Cairn "version" of what's most interesting. An ability that asks PCs to dodge or save becomes an out-of-combat "trap" the PCs can trigger; otherwise it succeeds automatically. The Warden telegraphs danger before a fight begins.
- **Magic:** magical creatures can "know" spells without Spellbooks; then make their corpses magical (and dangerous). Magic-users can carry Spellbooks, but might drop them when defeated, and some dropped Spellbooks implode (the Die of Fate decides which).
- **Use the fiction:** read the original stat block and text, write a few plain-English sentences about the creature, then convert those. The Foxwoman (HD 5, Speed 120', Armor 14, Morale 11, +4 d8 claw, bite or choke; can't be harmed by metal; turns into a fox at will) becomes 8 HP, 12 STR, 14 DEX, 15 WIL, claws (d6+d6), bite (d8): takes the form of a fox or of a woman with a hidden fox leg; immune to attacks from metal weapons; critical damage: victim is choked unconscious.

## Creating backgrounds: no tables

Guidance for writing a new background. The published ones (`backgrounds/*.md`) follow it and also carry a Names list. In play, a background is a filter for interpreting a roll, or a reason not to roll at all (a Greenwise needn't save DEX to cut leaves from a poisonous plant).
- **Principles:** players should be excited to roll on its tables. It can be archetypal and familiar, but leaves room for other readings. It tells the player something about the implied setting. Every table result is unique, so two characters with the same background still differ.
- **Theme:** a list of adjectives. For a profession, ask what leads someone to it; for something stranger (the Half-Witch), how that strangeness alienates them from others or brings them closer. Draw on the setting, inspirations and tropes.
- **Starting gear:** gold, food and a light source, each still distinctive (unusual Rations, a candle helmet). Up to four unique items that reinforce the theme, at least one of them a weapon. No more than seven slots in all.
- **Two tables**, each a defining question with six answers (d6):
  1. The distant or recent past, and what led to the present. It offers a unique item, an ability, or both.
  2. Who the character is today. Answers are typically a specific item or skill that broadly defines them.

## Bonds and omens: no tables

The chapter is guidance for writing new bonds and omens, for PCs, a setting, or a whole adventure. Its d20 tables are in the player's guide, handled elsewhere.
- **Bond:** ties a PC to another PC, the setting and its characters. It is resolved by discovering the truth behind its mysteries or solving its root cause; the PC should then grow, and the Warden may give a new Bond. Resolving it is optional.
- **A bond should:** give an item (often petty) or a unique ability; encourage engagement with the implied setting; flesh out the character's history without relying on events tied to specific backgrounds; provide a quest, opportunity or plan of action.
- **Omen:** the seed of an adventure to come, a premonition of a future disaster, or the cause of a problem the characters face now. It is resolved by revealing the truth behind its origin or resolving its dangers, which yields growth for the party or an entangled individual. Ignored, it comes to pass and wreaks havoc.
- **An omen should:** never rely on a specific PC; always tell the characters something about the setting they didn't know; reveal a pattern or other obvious sign that something terrible is going on.

## Growth: no tables

- **Where it comes from:** a character's own experiences in the fiction (Scars are the notable exception), and Downtime: training or specialization, research, faction relationships.
- **Principles:** never arbitrary, always tied to a specific experience in the fiction. Becoming more interesting matters more than becoming more capable. It comes from an experience that affected the character significantly, not just a new one. Place opportunities everywhere; it happens in play as often as in Downtime. It should lead to more interaction with the world. It is the logical result of actions, not a reward. It happens most when a character interacts with something they don't (or weren't *meant* to) understand. Changes can be unwelcome, or new abilities can come at a cost. Relics, treasure, factions, monsters and important NPCs make good triggers. It can be slow, or cumulative around one kind of experience.
- **Trigger test:** a trigger needs at least two of: (1) a focused, consistent pattern of behavior around a single objective or course of action; (2) an obvious risk with potentially serious consequences, especially when the outcome is unknown; (3) interacting with a unique item, creature or entity. Meet it with a permanent, related change.
- **Kinds** (the chapter's examples): interacting with something (or someone) not understood; long-term exposure to or manipulation of a Spellbook or Relic; forging a relationship with a being of great power; overcoming a long-time woe, misdeed or foe; injury or contamination; learning through trial and error; success or failure despite a natural talent or ability; faction advancement; resolving a bond or omen.
- **Changes the examples award:**
  - A new ability with a price. Esme feeds only on sunlight and water and hears the Wood, but is bound to the forest.
  - A save no longer needed in a situation: Hazel's Spellbook under duress, Julius's net, Harrow's sneaking.
  - Rerolling an attribute and keeping it if higher, with a lingering WIL-save flaw (Ox).
  - A new body feature: Aster's gills.
  - New needs and a weakness. Madrigal eats no Rations, only decomposed matter, and takes a Fatigue if drenched.
  - A faction rank with gear, a stipend and an oath (Rui).
  - A curse lifted by a Boon (Cobb).
- **Milestones:** a Downtime checklist of steps (Rui's come from *Strengthening Ties* and *Training*, Cobb's from a research action). Faction example: complete one, two, then three missions; train with a Protector; take the Oath. Bond-cure example: find a Master (a witch, scholar, healer or powerful spirit); seek them out and ask their requirements; complete them.
