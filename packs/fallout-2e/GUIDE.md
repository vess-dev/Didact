# Fallout 2e in Didact

Fallout 2e (CC BY-SA 4.0) is a wasteland hack of Cairn Second Edition by Yochai Gal: scavengers,
raiders, vault dwellers and ghouls in the ruins of the old world. This pack extends `cairn-2e`:
Cairn's chassis is unchanged (d20-under saves on STR, DEX and WIL, ten slots, auto-hit damage,
Scars, detachments) and everything Fallout adds is bolted on. It holds the fifty backgrounds,
the bestiary, the Marketplace, relics, unique weapons and armors, perk magazines, companions and
vehicles, the seed procedures and every random table. An unofficial, non-commercial fan work;
"Fallout" is a trademark of Bethesda Softworks / ZeniMax.

## What changes from Cairn

| Cairn | Fallout 2e | In Didact |
|---|---|---|
| Warden | Overseer | the same job |
| gold | caps | the `caps` field; `didact do coins` |
| Fatigue | Rads + Fatigue, distinct | `rads` and `fatigue` both fill slots |
| spellbooks, `cast` | Perk Magazines | `didact do read-magazine` (`cast` says so) |
| scrolls | chems | `didact do chem` |
| relics | pre-war relics | compendium `relic` |
| dungeon, forest | vault and ruin, the wastes | `vault-seed`, `wasteland-seed` |
| — | Scrap, crafting, mods | `scrap`, `craft`, `repair` |
| — | addiction, Rad Scars, ghoulification | `chem`, `rad-scar-save`, `ghoulify` |
| — | power armor, heavy weapons, vehicles, settlements | `save`, `attack`, `drive`, `build` |
| — | faction reputation (±2), party karma (±3) | `reputation`, `karma` |

Rules that read the same as Cairn's are the parent's, untouched: `save-together`, `morale`,
`fate`, `steady`, `fatigue`, `deprive`, `attribute-damage`, `blast-targets`, `trap`, `death`,
and the scar helpers `attribute-reroll` and `attribute-raise`. Everything else below is this
pack's.

## Running it

- **The Overseer's principles are always in the brief.** Information is free, telegraph every
  danger, roll only when risky and uncertain (fail-forward is always valid), and when a rule and
  the fiction disagree, the fiction usually wins.
- **Saves:** `didact do save who=freya attr=DEX`. Saves are pass/fail: no "a step easier". What
  the book allows instead: "save counts as attribute +N" (`bonus=2`), a re-roll (roll again), an
  automatic pass or fail, or no save. Opposed: the side more at risk rolls; together:
  `didact do save-together`. **Power armor without training fails every DEX save** (the save
  checks the suit worn and `power_armor_trained`).
- **Step ladders** (Reactions, terrain, weather, the die steps, reputation, karma, Loyalty,
  settlement attributes) clamp at their ends; "one step" means one rung of the matching ladder.

### Fights

`didact combat start --party raider` (the first-round DEX saves are in the setting), then
`didact combat hit freya raider weapon=d8` or `didact do attack attacker=freya target=raider
weapon=d8`. The parent's chain runs, with Fallout's dice:

- **Impaired is 1d4 whatever the weapon** (no d4 per die): bad cover, long range
  (`mode=impaired`), a Panicked attacker, an individual hitting a detachment, a **called shot**
  (`called=true`: the narrative effect applies on a hit), a **heavy weapon fired unbraced or on
  the move** (`heavy=true`; `braced=true` when braced; the Heavy Gunner perk, the Gunner's Heavy
  Weapons Cert, a super mutant and a trained wearer in a powered suit need no brace).
- **Enhanced is 1d12, never worse than the weapon's own dice** (a d20 or two dice of d10 and up
  are kept), never stacking: a helpless target (`mode=enhanced`), a detachment hitting an
  individual, a Psycho dose. **Impaired and Enhanced together cancel**: the normal die.
- Armor comes off (never past 3); `pierce=N` ignores N of it (the alien blaster ignores it all:
  `pierce=3`); `cover=N` adds half a vehicle's Armor for a passenger inside.
- HP to exactly 0 gives a PC a **Scar**; damage past 0 comes off STR and forces a Critical
  Damage save: a PC (or a companion) who fails is dying, stabilized with Bandages or a Stimpak
  (`didact do stabilize who=freya aid=Stimpak by=<who gives it>`: the aid comes out of the giver's
  inventory, else the patient's; no Stimpak, nor a kit, for a deathclaw or a robot), dead within
  the hour otherwise (a reminder is set). NPCs who
  fail die; a detachment is routed. Buffout makes the target immune for a scene, Overdrive makes
  the attacker's targets fail.
- Two weapons or several attackers keep the highest die: `weapon='{d8, d8}kh1'` (the bestiary
  stores them that way). Blast: `blast=true`, once per target (`didact do blast-targets`).
- Morale (`didact do morale`), retreat (`didact do retreat`: a DEX save, a direction to run),
  panic (`didact do panic`, `alone=true`; bond 13's yao guai stops it when alone) and `steady`
  are Cairn's.
- A vehicle hit to 0 Frame HP says whether it crashed (`didact do crash vehicle=… driver=…`) or
  broke.

### Scars

The attack runs `didact do scar who=<pc> lost=<n>` by itself, with Fallout's names: Close Shave,
Concussed, Flung Clear, Broken (leg, arm, rib, jaw), Rad-Necrotic Wound, Scrambled, Crippled,
Burst Eardrums, Shell-Shocked, Severed, Bleeding Out, Doomed. Wounds that heal later are
conditions (`flung-clear`, `broken-jaw`, `rad-necrotic-wound`, `crippled`, `burst-eardrums`,
`bleeding-out`): `didact do scar-heal who=freya scar=broken-leg` when the fiction heals one. A
**deathclaw** never gets Severed or Bleeding Out (a super mutant with Pressure Blood never gets
Bleeding Out): as the book says for any row a rule keeps from you, 1d12 picks the row instead,
rolled again on a row it can't have (the `deathclaw-scar` and `no-bleeding-out-scar` tables
roll the rows that are left). **Thinned Blood** worsens the first Scar of a session by a row;
**Glowing Marrow** offers a Rad for a Close Shave (the procedure says how).

### Rads, Rad Scars and ghoulification

- **Taking Rads:** `didact do rad who=freya source=hot-zone` (`amount=n`; `gear=halves` for a
  radiation suit, sealed power armor or a Lead Lining: every second Rad of that kind ignored,
  counted per source in `rad_halved`; `gear=negates` for a sealed hazmat suit or X-01). Rad-X
  negates the next one. A Rad needs a free slot. Robots
  and super mutants take none; a Radiant ghoul takes none from the environment. **NPCs and
  creatures don't track Rads:** the same command costs a rad-susceptible one 1 STR (no Critical
  Damage save), and rad-immune ones (`rad_immune` in the bestiary) ignore it.
- **Rad zones:** `didact do rad-zone who=freya watches=2` (ambient: a Rad a watch of travel),
  `zone=hot scenes=1` (+1 a scene). Dirty water is a Rad (`didact do consume food='Dirty water'`).
- **Every Rad a PC takes calls for a Rad Scar save,** and the sheet rolls it by itself (the
  `rads` field's hook runs `rad-scar-save` once for each Rad gained, however it was added: `do
  rad`, `set rads+=1`): 1d20 at or under 20 − current Rads. Several at once are added first, then
  saved one by one against the new total, as the book says. A failure rolls the Rad Scars table
  and applies it (max HP, WIL or DEX changes included) to `rad_scars`, counting toward
  ghoulification (`rad_scar_count`; Ghoul-Kissed counts two).
- **Clearing Rads:** RadAway (`didact do chem chem=RadAway`), a clinic (`didact do clinic`, 80
  caps: STR restored, every Rad flushed, a Scar treated), a purifier, a meal, a relic, a bond or
  an ability: `didact do clear-rads who=freya amount=1 by='Industrial Water Purifier'`. Never
  sleep or rest; never while Deprived, the clinic included. Bond 10's nanite culture clears one
  a day by itself.
- **Ghoulification:** at three Rad Scars the next long rest (`didact do recover`) rolls it
  (`didact do ghoulify who=freya`; `choose=true` from two Rad Scars). A ghoul's sheet gets
  `kind: ghoul`, background Ghoul and the `rad-scars` immunity. A ghoul at six or more Rads for a
  full day: `didact do feral-check who=…` at the next watch (a new day reminds you).

### Chems, food, addiction, perks

- `didact do chem who=freya chem=Stimpak` (`by=<pc>` when someone else gives it): the dose is
  spent from that inventory (one that isn't carried spends nothing, and the rule says so), and
  the `chems` table says what each does. Healing goes on STR (a Stimpak 1d6, a super mutant's 1d4, a Purist's
  Hand 2d6; none for a deathclaw); Super Stimpaks add a Fatigue; Rad-X and RadAway work on Rads;
  Addictol / Fixer breaks one addiction (`addiction=Jet`). Psycho, Overdrive, Buffout and Med-X
  put a condition on the PC that the attack and scar rules read: Psycho and Overdrive come off by
  themselves when the fight ends (`didact combat end`), Buffout and Med-X when the scene ends
  (`didact scene end`); a table that keeps neither takes them off by hand (the rule says how).
  Robots get nothing from chems. **While Deprived a chem heals nothing** (no STR, no Rad, no
  addiction's Fatigue cleared: the book's Chems); a Stimpak still stabilizes someone dying
  (`didact do stabilize`). A background's medkit (the Medi-Kit, the Followers Medical Kit, the
  Combat Medkit: one slot, 3 uses) is used the same way, `chem=Medi-Kit`, one use at a time, and
  heals as a Stimpak: a super mutant's 1d4, nothing for a deathclaw or a robot, nothing while
  Deprived.
- **Addiction:** every dose of an addictive chem forces a STR save (Ultrajet's at STR −2); a
  failure adds it to `addictions`. Each morning a time trigger adds a Fatigue per addiction (and
  one per drink of the night before: `hangover`); a dose of that chem clears its Fatigue for the
  day. A second dose of the same chem in one session is counted while a session is open
  (`didact session start`; `again=true` says so at a table without sessions): a warning, or with
  the second-dose option, addiction without a save. Cure: `didact do cure-addiction who=freya
  addiction=Jet method=clinic` (50 caps) or `method=week`, then a WIL save.
- **Food and drink:** `didact do consume who=freya food='Mirelurk Cakes'` (soft drinks heal HP,
  cooked meals full HP and more, alcohol 1 HP and a Fatigue next morning; Dry Mouth gets nothing
  from cooked meals; a deathclaw's fresh meat restores 1d6 STR once a day). Nothing heals while
  Deprived, unless the meal or the water is the lack itself: `meets_need=true` ends the
  Deprivation first. A carried meal is spent (`food=Ration` is a use of Rations; a deathclaw's
  meal costs two); one found, hunted or bought on the spot spends nothing.
- **Perk Magazines:** `didact do read-magazine who=freya magazine='Guns and Bullets 3: Pistol Grip'`
  (a turn somewhere safe, not Deprived and not in a fight: one run with `combat start` counts by
  itself, `fighting=true` says so for one played without; five Perk Slots, `swap=<perk>` when
  full). The perk (Gunslinger) and its effect come from `didact table show magazine-perks`;
  `perk=` names one for a magazine the book doesn't list. The copy is spent: taken out of the
  reader's inventory, or of the lender's (`by=<pc>`). `didact inv add freya 'Guns and Bullets 3:
  Pistol Grip'` (or its id, `guns-and-bullets-3`) carries one with its perk and effect. Applying a
  perk's effect is the LLM's job; `Heavy Gunner` in `perks` is read by the attack.

### Out of combat

- **Hazards hit attributes, not HP:** `didact do fall who=freya feet=30 landing=hard` (a Shock
  Absorber noted on worn armor passes the save by itself; `absorber=true` otherwise), `drown
  who=… round=4`, `fire who=…` (`sustained=true`: a DEX save or catch fire), `electrocution`,
  `exposure who=… weather=Cold watch=2` (Deprived after a watch, a Fatigue each further one;
  Extreme at once), `explosion` (a near miss), `venom`, `gas`. Armor applies only when it would.
- **Luck and people:** `didact do fate` (4+ favors the party), `didact do reaction who=<npc>
  party=<party record>` (karma added for strangers; `shift=±1` for Day Tripper, a Zetan's first
  meeting, a perk).
- **Short rest:** `didact do rest who=…` (all HP; never while Deprived, Panicked or full; `turn=true`
  in a ruin). **Long rest:** `didact do recover who=… cost=<caps>` (a week: attributes back, the
  "after recovery" Scars healed, the ghoulification roll; a robot needs `workshop=true`).
- **Deprivation:** `didact do deprive who=… need=water` once a day (a Fatigue past the first),
  `didact do relieve who=…` when met; a new day reminds you.

### Vaults, ruins and the wastes

- **Ruins:** `didact do dungeon-turn trigger=hurried` (Ruin Events when lingering, hurrying,
  entering a new zone, or loud; `hot=true` in a hot ruin). A turn is five minutes here
  (`time_units`).
- **Watches:** `didact do watch action=travel path=trail` (`path=highway|trail|wastes`; `known=true`
  on ground a Pip-Boy has mapped; `shift=±1`), `action=supply helpers=1 bonus=1 who=<pc>` (the
  Rations gathered go to that PC), `action=make-camp` (every PC makes camp), then `didact time
  advance 1 watch`. The clock's night watch rolls Wasteland Events twice (`night=true` for a table
  that keeps no clock).
- **Weather:** `didact do weather season=fall hot_zone=true` (a new day rolls it by itself with a
  seasons calendar, and with one the season can be left out). Rad weather turns its Fatigue into
  a Rad.
- **Travel time:** `didact do travel-time path=wastes distance=long terrain=tough weather=Stormy`,
  plus `vast=1|2`, `sleepless=true`, `bonus=n`, a vehicle's `speed=Standard|Fast fuel=n`,
  `airborne=true`, `rad=true`.
- **Camp:** `didact do make-camp who=…` (a Ration's use spent from their pack, two for a
  deathclaw; `ration=` a meal that stands in for one; `truck=true` in the back of a pre-war truck,
  none; no Ration, no meal: a day without food Deprives; Fatigue cleared, never Rads; robots run
  diagnostics), `didact do skip-camp who=…`. A mount's Ration is the GM's to spend.

### Inventory, caps and Scrap

- Ten slots (`slots_max`; an Eyebot six, two background results eleven, as the book allows):
  `body` (4) and the Backpack (6). Rads, Fatigue, a growing Lead Battery Cell (`burden`), caps
  past 100 (`purse`) and Scrap (`scrap_load`) fill slots. A full inventory sets HP to 0. A
  robot's built-in parts take slots like any item (an Eyebot's none) and can't be dropped.
- **Caps:** after they change, `didact do coins who=…` (the coin-weight option). Rules that spend
  caps run it.
- **What a rule uses up** (a dose, a bandage, a Ration's use, a medkit's use, a magazine read) it
  spends itself through `didact do spend-item who=… item=…`: one use as `inv use` spends it, or
  the whole thing when it has no uses; one that isn't carried spends nothing, and the line says
  so.
- **Scrap:** `didact do scrap who=freya source=scavenge` (1d6), `heap`, `wreck` (2d6),
  `breakdown item='Pipe rifle'` (the carried thing is gone, and whether it's bulky is read from it;
  `item_scrap=4` for a crafted one's cost), `buy amount=2`, `sell`, `spend`; 5 Scrap a slot.
- **Power armor** is an inventory item with `power_armor: true` (3 Armor, bulky): worn means in
  the `body` group or in no group; stowed in the backpack it isn't worn.

### Downtime and crafting

`didact do downtime who=freya action=training goal='Field Surgery' caps=40 size=3` (research,
training, ties; `size=` is the Milestones the Overseer sets: the first time, the goal's tracker is
made, and each action completes one; `milestones=<tracker>` for one made by hand; `abate=true` for
a WIL save past a cost). Its own actions: `didact do scavenge who=freya ruin=<place> find=cache` (a
loot roll and a Ruin Events roll; twice and the ruin is empty), `didact do craft who=freya
recipe='Long Scope' item='Hunting rifle'` (any recipe in `didact table show recipes`: the station,
Scrap, caps and Downtime Actions; chems roll reagent cost and 1d4 doses; `batches=3` for ammo;
`half=true` for a chem cook at a settlement Chemistry Station; what's made goes to the crafter's
inventory, and a mod is noted on the item it goes on), `didact do repair who=freya item='Laser
rifle'` (half the carried item's price; `value=380` for one with none), `didact do
cure-addiction`.
When the session ends, each PC is reminded of Downtime, Training, their Bonds and the Omen.

### Factions, karma and settlements

- **Reputation:** factions carry `reputation` (−2 to +2) and `opposed`: `didact do reputation
  who=<faction> shift=1 why='delivered the intel'` moves it a step (and its opposite down a step).
- **Karma:** one record for the party (`didact new party "The Party"`): `didact do karma
  party=<it> shift=-1 why='looted a body while the family watched'`. One step a session, public
  acts only: with a session open (`didact session start`) the rule refuses a second step in it.
- **Faction turns:** Fallout has no faction roll: `didact faction turn` asks what each faction did.
- **Settlements:** `didact gen run fallout-2e.settlement` (1/1/1, eight slots), `didact do build
  settlement=<it> building='Walls & Gate' who=<pc> caps=300` (unconditional "+1 Defense" and the
  like apply; conditional ones are the Overseer's), `didact do raid settlement=<it> rating=2`
  (`won=true`, `destroyed=<building>`), `didact do upkeep settlement=<it>` each season.

### Companions and vehicles

- Companions are records (`type: companion`, with `owner`, `loyalty`, `trick`, a robot's
  `directive`): `didact spawn dog`, or `didact gen run fallout-2e.companion`. `didact do command
  who=freya companion=dog target=raider weapon=d6` (once per combat: Enhanced; in a fight run with
  `combat start`, a second one is refused until `combat end`). `didact do loyalty companion=dog
  shift=1`. `didact party add dog --as companion`.
- Vehicles are records (`type: vehicle`: Frame HP, armor, passengers, slots, fuel, fuel_uses,
  speed): `didact spawn motorbike`. `didact do drive who=freya` (DEX under pressure, `attr=STR` in a
  rad storm or broken terrain; Deprived drivers fail), `vehicle-damage vehicle=… amount=1d12`,
  `crash vehicle=… driver=…` (`crash-passenger who=…` for each passenger), `ram`, `field-patch`,
  `vehicle-repair points=2`, `frame-rebuild`. Fuel: `didact set motorbike fuel_uses-=1`.

### Growth

No XP, no levels. Scars apply themselves. **Training** and **Acquisition**: `didact char advance
freya how=training technique='One-Handed Brace: with one hand free, once per combat one attack
with a one-handed weapon is Enhanced' master='a Ranger sniper' cost='beat her in a footrace'`,
then `didact char commit c4`. Bonds and Omens are threads: `didact do resolve-bond who=freya
bond=<thread>` (a removed Lead Battery Cell weighs nothing again), `didact do resolve-omen
omen=<thread>`. Bond 15's Lead Battery Cell is the `burden` counter, a slot heavier each month.

## Making things

- **Characters:** `didact char new` (guided) or `--mode random`. Every background result
  applies: its gear and 3d6 caps, `kind` and the `immunities` an unusual body brings (robot,
  super mutant, ghoul, deathclaw), attribute caps (an Eyebot's STR 8 and DEX 16, a Protectron's
  DEX 13, a Zetan's STR 12 and DEX 16, a deathclaw's DEX 16), a super mutant's highest roll on STR,
  an Eyebot's six slots, power armor training, a Stimpak's strength, a second Bond (a Desert
  Ranger's ledger), the Overseer's picks (the Brotherhood Outcast's stolen weapon, the Chem
  Cook's three chems), and the companions, the hired gun and the vehicles some bring (Gristle,
  Barker, the Destrier, Pip; Ruan, a hireling; a pack brahmin, a motorbike, an old wagon) as
  records beside the character; starting gear a result replaces comes off (the Fire Brigade
  Protectron's laser). The
  youngest rolls an Omen (in random mode, prefill it: `--prefill '{"youngest": "no"}'`).
  Prefill what the player chose: `--prefill '{"background": "Ghoul", "name": "Hap"}'`.
- **Hirelings:** `didact char new hireling` (a role and its daily rate) or
  `hireling-background`.
- **People and creatures:** `didact gen run fallout-2e.npc`, `fallout-2e.faction`,
  `fallout-2e.monster` (the Creating Monsters prompts), `fallout-2e.companion`,
  `fallout-2e.encounter` (a threat level, a region's table, or `where=category`: the Bestiary's
  d20 groups, a 20 off the main map reaching the DLC Creatures; the creature written as a record).
  `didact compendium find deathclaw`, `didact spawn deathclaw`.
- **Loot:** `didact gen run fallout-2e.weapon`, `armor`, `gear` (the Random Weapon, Armor and Gear
  tables), `relic` (by rarity), `perk-magazine`, `unique-weapon`, `unique-armor` (by catalog
  section; a full section's last row rolls its continued table, so every unique can come up, and a
  prefill can name any of them: `--prefill '{"kind": "unarmed", "unique": "Ogua Gauntlet"}'`); a
  cache: `didact table roll fallout-2e.loot-cache`.
- **Places** (drafts first; `gen show`, `gen edit`, then `gen commit` writes them with the map):
  `fallout-2e.setting-seed` (a region: character, threat, opportunity, the book's points, three
  factions, paths with their watches), `fallout-2e.wasteland-seed region=loc:<place>`,
  `fallout-2e.vault-seed region=loc:<place>` (history, denizens, factions, 6–20 rooms numbered from
  the entrance). Ruin and faction names are the book's patterns ("The X Site"): fill in the X.
- **Jobs:** `didact gen run fallout-2e.adventure-hook` (mission, hook, complication, reward and
  2d6 × 25 caps base pay, as a quest).
- **Names:** `didact name npc`, `didact name place` (a settlement), `didact name poi` (a ruin
  pattern), `didact name faction` (a faction pattern).
- **Session zero** asks the Tone Dial (`tone`: bleak, pulpy, weird, horror), the stakes
  (`lethality`), the reach, whether to track ammo (`track-ammo`), and the second-dose rule.

## Readings where the book is silent

- **A turn is five minutes** ("a few minutes of focused action"); the parent's is ten.
- **Hidden and conditional paths** are a d6 per path (6 hidden; 5 conditional in a vault), as
  the parent reads Cairn's "some paths are".
- **Attributes stop at 20,** as in the parent (neither book sets a ceiling); unusual caps apply
  at creation.
- **HP lost past 12** reads as 12 (Doomed).

## What is hidden and what is inherited

A Fallout 2e world shows Fallout's things only. `pack.yaml` hides what cairn-2e has that Fallout
has no place for (`didact pack info fallout-2e` lists the patterns):

- **Hidden:** Cairn's whole compendium (its spellbooks, relics, monsters, gear and services),
  its reference text and its glossary (this pack's own sections and terms stand in, the chassis
  in the book's words), every Cairn table but `die-of-fate` and `head-wound` (its forty background
  d6 tables, the forest, setting and naming tables, `spellbooks`), the `spellbook` type, the
  `spellbook`, `realm`, `pointcrawl` and `point-of-interest` generators, the `faction-action` rule
  and the `unusual-weather` option. `didact name realm` and `name forest` find nothing: Fallout's
  name tables stand in for Cairn's (`npc`, `place`, `poi`, `faction`).
- **Replaced by a pointer:** `cast` (perk magazines and chems), `dungeon-seed` (the vault seed)
  and `forest-seed` (the wasteland seed) stop with the Fallout command to run instead.
- **Inherited and kept:** the rules that read the same (`save-together`, `morale`, `fate`,
  `steady`, `trap`, `fatigue`, `deprive`, `attribute-damage`, `blast-targets`, `death`,
  `new-day`, `attribute-reroll`, `attribute-raise`), the tables `die-of-fate` and `head-wound`
  (the scar rule rolls it), and the types `npc` and `detachment` (on this pack's `character` and
  `monster`). None of them reads anything hidden. Settings come key by key: cairn-2e's watches
  (morning, afternoon, night) are Fallout's too; this pack sets its own turn length, combat,
  faction turn and name tables.

## Credits

Fallout 2e: rules chassis by Yochai Gal, Cairn Second Edition (CC BY-SA 4.0); conversion, tables
and setting text, fan work, CC BY-SA 4.0. This pack is shared under the same license.
