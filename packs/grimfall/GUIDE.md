# Grimfall in Didact

Grimfall is a Fallout hack of Grimwild, by way of Grimwild: Community Edition: survivors in the
irradiated bones of the old world. Say what you do, roll a handful of d6, keep the highest, and
let d8 thorns complicate things. This pack extends `grimwild-ce` and hides what of it Grimfall
drops: the Core Engine (action, defense and story rolls, thorns, diminishing pools, the harm
ladder, suspense) is re-stated in Grimfall's words and dice, and everything Grimfall adds is here:
seven S.P.E.C.I.A.L. classes with Core Perk engines, 275 perks, rads, stimpaks, chems, caps and
hauls, the Bestiary's 122 threats, the Armory's 331 arcana, standing, communities, vaults and the
options. An unofficial, non-commercial fan work (pass it on, just don't sell it).

## What changes from Grimwild

| Grimwild | Grimfall | In Didact |
|---|---|---|
| paths, talents | classes, perks (a Core Perk + one, a perk a level) | `class`, `perks`; compendium `class`, `perk` |
| talent dice, setup dice | perk dice don't stack: +1d for perks, one each for a setup, a chem, a relic | `perk`, `setup`, `chem`, `relic` flags |
| marks | marks, and rad marks that linger | `marks`, `rad_marks`; `do rad` |
| — | stimpaks (3d each), a 4d Caps pool, hauls | `do stimpak`, `do spend`, `do sell` |
| magic, spells, twists | science: devices, potent devices, rituals; a misfire under dangerous tech | `do device`, `misfire` |
| arcana | relics, unique weapons, unique armors (the Armory) | compendium `arcana`; `gen run grimfall.treasure` |
| carousing, expanded downtime (option) | downtime actions, always: rest, venture, blow off steam, pursue a goal, plan ahead | `do downtime` |
| monsters with tiers | Bestiary threats, put in play as pools | `gen run grimfall.foe` |
| flavors of fantasy | flavors of the wasteland, Wild Wasteland, dangerous tech | options |

## What is hidden, what is inherited

`pack.yaml`'s `hides` drops what Grimfall's book replaces wholesale (`didact pack info grimfall`
lists the patterns). Hidden: every Grimwild compendium entry (its paths and talents, its 48 arcana,
its monsters, its backgrounds), every Grimwild table but `bonds`, all of its rules text (`rules
lookup` answers with Grimfall's sections only: `overview-*`, `engine-*`, `survivors-*`, `classes-*`,
`perks-*`, `surviving-*`, `bestiary-*`, `armory-*`, `running-*`, `options-*`) and all of its glossary
(`define` answers with Grimfall's 122 terms), the `path` and `talent` types, the magical twist, the
narrative-break reset, the talent switch, carousing, vigor and per-session talents, the sword &
sorcery and noblebright triggers, the potion and talent generators, and the options Grimfall lacks
(magic, lasting marks, random vex, random bonds, vigor pool, wealth, expanded downtime: Grimfall's
downtime actions are always on).

Inherited, because they read the same in Grimfall: the faction pools (`faction-turn`,
`faction-pool`, `faction-pool-roll`, `faction-goal`: `didact faction turn`), `tick` (tick pools),
`tokens` (exploration tokens), `reset-suspense` and the triggers that run `pre-session` and end a
party's reset, the story oracle (`didact ask`, and the GM's suspense on its state), the `npc` type,
and the `bonds` table (an intensity and a nature: the book's examples are its words). Their help
still cites Grimwild's page numbers. The parent's `settings` are inherited key by key: its
`factions` (the faction turn is `faction-turn`) as it is, while Grimfall states its own `combat`
(no turns: the spotlight moves like a camera) and `names` (the survivor crucible). Everything else
with a Grimwild id (the rolls, damage, the options Grimfall shares, the chargen, the generators, the
lore) is replaced by Grimfall's own. The parent's `site` generator is replaced by a stop that names
`grimfall.vault` (the book builds any delve as a 5-point site).

## The sheet points at its pools

A survivor's sheet holds a ref to each pool it carries: `stimpaks` (a machine's Repair Kit; with
the grimmer dial's shared pool, the party's), `caps`, `supplies`, `chem_stash`, `armor_pool`, and
the perks' `plating`, `pack`, `chems_pool`, `winging_it`, `serendipity` and `standing_pool`.
Character creation sets them, and so does leveling up, swapping a perk (`do switch-perk`) and the
party's shared Stimpaks (`do party-stimpaks`, run by itself when a session starts with that dial).
So the rules find the pool without being told: `do stimpak`, `do spend`, `do sell`, `do armor`,
`do plating`, `do breach`, `do rest … safe` and `do downtime` take the sheet's own unless `pool=`
(or `stimpaks=`) names another, and a community's `stockpile` does the same for `do stockpile`. The
session's reset refreshes the perks' pools and an Armor pool by itself (a breached frame stays
breached until it's repaired); an arcana's pools are still refreshed by hand. A swapped-out perk's
pool comes off the sheet (its record is yours to `didact rm`). A survivor made before a ref existed
gets it with `didact set <pc> stimpaks=<track>`. Every pool parameter takes a track (`to: track`),
so a pool named as its foe (the foe generator names the pool after the card) is named plainly:
`didact do push who=… pool=feral-ghoul stat=brawn`, and so do `track roll` and `track tick`, which
take the tracker (`didact track roll feral-ghoul`). `show` still needs the id (`track:feral-ghoul`)
when a card shares the name, and so do the parent's untyped pool parameters Grimfall inherits
(`tick pool=`, `faction-goal pool=`).

## Rolls

- **Action roll:** `didact do action who=dutch stat=brawn thorns=1`. The highest d6 is the
  result: 6 perfect, 4-5 messy (with an impact move), 1-3 grim (with one); each thorn on 7-8 cuts a
  step, to disaster (spark as consolation); more than one 6 is a critical, uncuttable. Dice:
  `spark=1` (+1d each, spent), `perk` (+1d in total, however many perks apply, Core Perks
  included), `setup`, `chem`, `relic` (one die of each kind), `assist=1` (1d per helper, rolled
  apart, sharing the risk), `outside` (the GM's 1d), `weak_point` (a Pathfinder's quarry: the Weak
  Point die joins the roll, and its 6 adds a critical bonus besides), `bonus=<pool>` (a bonus-dice
  pool rolled alongside: only its best die counts with yours, then its 1-3s drop), `instead=3`
  (dice in place of the stat: a companion's tricks, Almost Perfect). Thorns come by themselves for
  a mark on the stat (it clears), a rad mark (it stays), bloodied or rattled on a related stat,
  desperate, and a Flesh Wound. `all_in` (Rooted, Better Criticals): 5s count as 6s and 4s as 1s on
  your own dice only (your stat's, spark, a perk, setup, chem or relic die), and those 1s count
  toward a misfire; `finesse` (Finesse, Isodoped): a 5 alongside a 6, anywhere in the roll, is a
  second 6. `stakes=low|regular|high|dire` weighs the impact move (said out loud when it changes);
  `interrupt` is a perk's roll to stop one (perfect stops it, messy banks the GM 1 suspense, grim
  lands; you share the risk); `device` is a roll that misfires on two 1s under dangerous tech.
- **Defense roll:** `didact do defense who=… stat=agility` when trouble comes at you that your own
  roll didn't invite (perfect clear, messy lessened, grim taken, disaster worse and spark).
  `protect` is the 1d roll for an ally; `all_in`, `finesse` and `bonus=` read as above. Quick Draw
  drops the thorns on Agility defense rolls, except those from damage; Stonewall's +1d when
  assisting is one more assist die.
- **Story roll:** `didact do story-roll odds=bad|even|good question='…'` (1d, 2d, 3d; `perk` for
  Charmed life or Educated); it's the story oracle too: `didact ask 'Does the caravan have Rad-X?'
  --odds good`. With Wild Wasteland on, two 6s go strange (the crucible is rolled).
- **Montage:** `didact do montage who=…` for each survivor (2d; `perk` for Idiot Savant, Swift
  Learner, Lone Wanderer); the table keeps the highest.
- **Power pools:** `didact do pool-action who=… pool=<pool>` rolls a power pool in place of a stat
  (Winging It, a relic's Cells); `drop=1` first for a potent use. A riskless use: `track roll`.

## Damage, healing, pools

- `didact do mark who=… stat=wits` (a second mark, or a mark on a rad-marked stat, is harm; a side
  character takes harm instead), `didact do harm who=… kind=bloodied|rattled` (a second of the
  same is desperate; once desperate, one you carry drops you), `didact do dropped who=…` (2d, or as
  lethality says; `spark=`, `perk` for Charmed life or Medic, `surgeon` for a Field Surgeon who
  reached them, `relic`, `stimpak` with softer stimpaks, `all_in` for Rooted), `didact do end-story
  who=… end=sacrifice|retirement|another`. A dropped survivor is back when the scene ends (a prompt).
- **Grit and friends:** `grit` on `do mark` and `do push` is Dig deep (1 Grit), on `do harm` Walk it
  off (2 Grit); `flesh_wound` on `do harm` is Life Giver (it clears at the scene's end);
  `serendipity=<pool>` rolls Serendipity. Pain is fuel (a blow that leaves a Sledge bloodied or
  worse) and Adrenaline come by themselves.
- **Healing:** `didact do stimpak who=<giver> on=<ally>` (a breather: one harm, then the giver's
  pool rolls; Medic and Fast Metabolism: `mark=`), `didact do treat who=… heal=…` or
  `condition='…'` (it nearly always works; the drama is the cost), `didact do rest who=… safe` (any
  real rest clears marks, harm and rad marks; a night somewhere safe refills the sheet's Stimpaks).
  Both take `heal=` for the harm cleared; left out, desperate goes first.
- **Timers to worse, made at once:** a lethal dose makes the survivor's Lethal Dose timer (4d, a
  warhead's 2d, Rad Tolerance 2d larger), and deadlier lethality's desperate makes 4d Bleeding Out
  (`didact do bleeding-out who=…`, also what a dropped roll's messy can cost): on the sheet as a
  condition and as a timer pool to roll as time passes (the sheet points at it: `lethal_dose`,
  `bleeding_out`), at 0d dropped. A second one while the first runs keeps the first. Treatment
  (`didact do treat who=… condition='4d Lethal Dose'`) takes the condition off and the sheet's
  pointer with it, and names the timer's record for `didact rm` (no rule deletes a record). The
  book gives the timers no rate, so they're rolled by hand as time passes.
- **Pools:** `didact track new 'Raider Pack' --kind pool --size 4 --pool task`, `didact track roll
  <pool>`; a task pool that drops nothing: `didact do push who=… pool=… stat=…` (or pivot). The GM
  drops 1d from a stubborn pool with `didact do suspense spend=1 pool=…`. `didact do refresh
  pool=…`, `didact do grow-pool pool=… by=2 most=8`, `didact do tick pool=…` (tick pools).

## The Core Perks' engines

- **Sledge:** `didact do might who=… use=heave|hurl|follow-through|bull-through` (4 each scene, set
  when a scene starts; hurl costs 2). Power Armor Training: `didact set <pc> suited=true`, `didact
  do plating who=…`; a disaster while suited breaches the sheet's Plating by itself (`didact do
  breach who=… fix=patch` back to 1d, still breached; `fix=repair` whole again). A named suit's
  Plating stands in for the battered frame's: `didact set <pc> plating=<its pool>`.
- **Pathfinder:** `didact do study who=… foe='…' weak_point='…'` (once a session, +1 at 3 and 6),
  then `weak_point` on any roll against the quarry. Keen eye's hint is read by `do vigilance`.
- **Everlast:** Grit, above; the scene's end handles Flesh Wounds, and prompts Better Healing,
  Rad Absorption and Ghoulish.
- **Charmer:** `didact do sway who=… use=raise|vex|mark|potent|interrupt|rattled ally=… stat=…`.
- **Inventor:** `didact do device who=… schematic='shock baton'` (`potent`, `riskless`, `mends`,
  `reach` for +1t past the touchstone's edge); schematics on the sheet (`schematics`).
- **Ace:** `didact do cool who=… skill=stealth` (a potent feat within a tagged skill; +1d with
  `perk` when rolling it).
- **Longshot:** Luck is kept on the sheet by face (`luck: {sixes: 1, …}`); `didact do luck who=…
  use=6` crosses one off (then read the roll again). A disaster rolls a fresh die if short.
- **Thread:** `didact do thread who=… detail='…'` (`plan` spends a plan-ahead thread; `flashback`
  is Explorer's or Covert Ops' 3d montage; `find` is Fortune Finder's 2d story roll).

## Surviving the wasteland

- **Rads:** `didact do rad who=… dose=zone stat=brawn` (a hot zone's rad mark; without `stat`, +1t
  while working in it), `dose=bad condition=rad-sick|rad-poisoned` (rad-sick if left out),
  `dose=lethal` / `warhead` (a 4d or 2d Lethal Dose, its timer made at once). Rad-X, Lead
  Belly, Cyborg, Ghoulish, Rad Tolerance and Rad Resistance are read from the sheet; `grit` lets
  Grit eat the rad mark.
- **Chems:** `didact do chem who=… chem=buffout` (Buffout, Psycho, Jet, Mentats, Med-X, Cateye,
  Hydra, Fixer, Rad-X; RadAway with `treat=marks|rad-sick|rad-poisoned|lethal`). The buff lasts the
  scene (`chem` on the roll it helps); when the scene ends the kick comes due by itself (marks,
  Psycho's vex, the comedowns; Chem Resistant steps a mark or vex down to +1t for a beat and the
  rest to set dressing). A grim or disaster while riding a chem prompts Hooked.
- **Caps:** `didact do spend who=…` (the Caps power pool, rolled by `caps-roll`; `huge` drops 1d
  first; Hard Bargain keeps a die; `workshop` with Scribe Counter); `didact do sell who=…
  haul=minor|major` (+2d or +4d, max 8d; Cap Collector 1d more; a second downtime action).
- **A dose out of a pool:** `didact do chem who=… chem=jet from=stash` (the Chem Stash option) or
  `from=chems` (a Chemist's batch) rolls that pool first; an empty one has no dose.
- **Supplies:** `didact do supplies` rolls every survivor's Supplies pool at once (as time passes
  away from settlements: the time trigger says when), `who=` one survivor's after heavy use.
- **Scavenging:** `didact do scavenge place=picked|ordinary|sealed`.
- **The long road:** montage rolls; `didact do tokens who=… take=3` when the map expands (`spend=`,
  `thread`, `clear`); wonder in the wastes is `didact do take-spark who=… why=wonder`; `didact do
  time-passes` when the game jumps ahead.
- **Downtime:** `didact do downtime who=… act=rest|venture|steam|pursue|plan` (`also=` a second,
  different one after a sold haul; `plan='…'`; `project='Mod the rifle'` makes that project's task
  pool the first time, `dice=` sized, 4d unless said, and rolls the same pool by name each time
  after; `goal=<task pool>` names one by hand). Marks, harm and rad marks clear; the sheet's
  Stimpaks refill; per-session perks and the Core Perks' wells refresh (Luck is rolled anew); the
  GM is reminded of the faction turn.

## Running the wasteland

- **Suspense** lives on the story oracle's state, 1 at a time: `didact do suspense take=1 why=…`,
  `spend=1` (`pool=`, `challenge=`); the suspense moves: `didact do suspense-move
  move=build-up|clue-in|foreshadow|resolve` (a Build Up gives every PC spark by itself). Before each
  session after the first the GM takes 1 (a trigger).
- **Fights:** enemies never roll. `didact gen run grimfall.foe` puts a Bestiary threat in play: its
  card and its pool (a pack of mooks 4d, a knot of toughs 6d, an elite 6d with 2 bonus suspense, a
  boss 8d, or a linked challenge's parts, each with 2 bonus suspense, and a fail state's timer).
  Hurt it: `didact track roll <name>` (the tracker, though its card shares the name); at 0d it's
  beaten. Impact moves are its moves. A fight run
  with the tracker (`didact combat start <pc> … <foe>`, `combat end`) says what the book counts per
  fight: the per-fight edges coming back (the first shot or swing of a fight on the named weapons,
  a foe's once-per-fight moves), Kamikaze's first impact move, United We Stand, and Adrenaline
  ending with the fight; a table that plays its fights without it loses only those reminders.
- **Challenges and places:** `gen run grimfall.challenge` (2 bonus suspense), `linked-challenge`,
  `battleground`, `quest` (the book's ladder: moderate 4d + 4d, daunting 4d + 4d + 6d, epic and
  legendary; linked peril pools, one fewer, sized like its first links), `ritual`.
- **Factions:** `gen run grimfall.faction` or `gang` (the gang crucible); `didact faction turn` rolls
  their listed pools; `didact do standing who=<faction> shift=-1 why='…'` moves its standing a step
  (Vilified makes a 6d They Find You campaign pool at once and lists it on the faction, so its turn
  rolls it). `gen run grimfall.powderkeg` is Canyon Junction and its
  six factions, pools listed; `gen run grimfall.door-under-junction` its first session.
- **Communities:** `gen run grimfall.community` (a Stockpile, started by the first haul traded in),
  `didact do stockpile community=… act=trade haul=major|roll|plan asset='…' tier=…|repair dice=1`
  (`leader` for Local Leader; the community's own Stockpile unless `pool=` names one), `gen run
  grimfall.community-asset` (a face).
- **Vaults:** `gen run grimfall.vault` (the vault crucible and the five points, the Reward first).
- **Weather & drift:** `didact do drift at=<place>` each downtime or dawn.
- **Vigilance:** the GM picks reveal, hint or strike (`didact table show vigilance`); with active
  vigilance, `didact do vigilance who=… dice=2` (`floor=hint|reveal` for a perk that guarantees one;
  Keen eye's hint is automatic).
- **Solo:** the `solo` option's guardrails ride the impact move; side characters (stats as usual):
  `didact char new grimfall.side-character`; a companion: `gen run grimfall.companion`.

## Sessions and growth

- **Sessions start warm:** from the second session on, each survivor's `pre-session` runs by
  itself: spark for their best moment, thread reset (2, +1 each for Explorer, Covert Ops, Fortune
  Finder, Educated), and the per-session wells: Grit, Sway, devices and potent devices, Cool,
  studies (and a new quarry), the Longshot's Luck rolled; the perks' pools and an Armor pool the
  sheet points at come back (a breached frame stays breached); Frayed Genes rolls; a prompt lists the
  arcana pools to refresh. With rest resets, a real rest does it instead.
- **Experience:** each survivor takes 1 XP when a session ends; `didact do experience who=… bonus`
  for a standout session, `why=theme` with focused growth. `didact char advance <pc>` levels up:
  a new perk (any class's seven, the compendium, a heritage perk, or a repeatable one again), the
  Core Perk's Growth (the Inventor's new schematic, the Ace's new tagged skill), stat progression's
  one lifetime bump, level 0's Core Perk at level 1; a perk with a pool of its own makes it, and the
  sheet points at it. Cap 7 (3 at the smaller scale; then `didact do switch-perk`, which makes the
  new perk's pool too).

## Making things

- **Survivors:** `didact char new` (guided) or `--mode random`: two backgrounds and their wises, two
  traits and one not, two desires and one not, a class with its Core Perk and one more perk (and
  what that perk brings: Light Step's rigs, Inspirational's companion, Chemist's recipes and 4d
  Chems, Educated's wises, Power Armor Training's Plating, …), the class page's crucibles, stats (1
  each + 4 points), a name from the survivor crucible, the Core Perk's choices (4 schematics, 3
  tagged skills) and wells, a 3d Stimpaks pool (a Repair Kit for a machine background) and a 4d
  Caps pool, the options' pools and quirk, every pool on the sheet; then features, arcs, bonds and
  the montage as prompts.
  Prefill what the player chose: `--prefill '{"name": "Dutch", "class": "The Everlast"}'`.
- **Generators** (on the Records page, or `didact gen run grimfall.<id>`, `--auto` for the dice):
  people and threats (`npc`, `companion`, `monster`, `foe`, `faction`, `gang`, `party`), challenges
  (`challenge`, `linked-challenge`, `battleground`, `quest`, `ritual`), places (`region`,
  `settlement`, `vault`, `community`, `community-asset`), things (`arcana`, `chem-recipe`,
  `treasure`, `weapon`, `vehicle`, `perk`), and the book's sandbox (`powderkeg`,
  `door-under-junction`). A haul with an arcana puts its first pool, or a suit's Plating, in play.
  Names: `didact name npc` (the survivor crucible), `didact name vault-file`.

## Options

Session zero asks them (`didact session zero`, then `didact campaign profile …`): lethality
(softer, standard, deadlier), scale, the flavors of the wasteland (grim survival, pulp heroics,
frontier western, weird science: each implies its dials, and what an option implies is followed all
the way, so grim survival's deadlier lethality brings its 2d stimpaks and pulp heroics' softer
lethality the Softer stimpak dial), dangerous tech, Wild Wasteland, caps and stimpaks (on by
default; grimmer is pick one: `grimmer-2d`, `grimmer-self`, or `grimmer-shared`, a single 3d pool
the party shares, made when a session starts and every sheet pointed at it; or `softer`), a chem
stash, weapon styles, armor, supplies,
encumbrance, rest resets, milestone levels, focused growth, a slower road, level 0, stat
progression, token initiative, tick pools, the writers' room, active vigilance, quirks, solo.

## Where the book was silent

The author's standing answer is to settle it in the book and in the pack together. Thirteen
small edits to the rulebook's Markdown did (logged in `Didact Work/Temp/grimfall/book-edits.md`),
and this pack follows the book as it now reads:

- A Weak Point die's 6, and a per-scene well's maneuver, add a **critical bonus** (the book had
  also said "critical effect").
- Going all in (Rooted, Better Criticals) changes **your own dice**: your stat's, plus any spark,
  perk, setup, chem or relic die; never an assist, outside help, a pool's dice, or the Weak Point
  die.
- Downtime refreshes the Core Perks' wells along with the per-session perks.
- Chem Resistant's "one step lighter": a mark or vex becomes +1t for a beat; anything lighter is
  set dressing.
- Selling off a major haul adds +4d to the Caps pool (a minor one +2d; max 8d).
- Suspense is earned and spent 1 at a time (a skipped move, a suspense move, a strike).
- Side characters have the usual stats (1 in each, plus 4 points).
- Quests run moderate 4d + 4d, daunting 4d + 4d + 6d, epic 4d + 4d + 6d + 6d, legendary 4d + 4d +
  6d + 6d + 8d, with peril pools sized like the quest's first links.
- The grimmer stimpak dial is a menu (pick one), and its shared pool is 3d; softer lethality's
  "stimpaks flow" is the Softer stimpak dial.

What the book says plainly, and the pack does: the Weak Point die is part of the roll (it counts
toward the highest and a critical); a rad mark is a mark (a second mark on that stat is harm), and
any real rest, downtime included, clears it; a blow that leaves a Sledge bloodied or worse feeds
Pain is fuel; perk dice don't stack, so Field Surgeon, Medic and Charmed life share one die on a
dropped roll; a lone tough falls to one roll, a knot of them is a pool; a community's Stockpile
starts empty and every die that drops pays toward the next asset.

## How Didact reads the rest

These are the pack's own choices, not rules: they shape how the book is kept on a sheet.

- The Longshot's Luck is kept by face, so crossing off one of two equal results takes only one.
- A stimpak or treatment clears desperate first unless told which harm; a bad dose is rad-sick
  unless told it's rad-poisoned; Lead Belly's stepped-down condition is a rad mark on a stat the GM
  names.
- The Core Perks' wells grow at the first reset after a level (levels come between sessions).
- A Bestiary threat's pool is its card's own when its Note opens by giving one, else its tier's
  usual; the linked-challenge generator offers 2 to 4 parts, as the Bestiary's bosses have.
- Map points and buildings take their two-word labels from the GM crucible, a word from each
  column's row; the arcana generator seeds two touchstones the same way, with the function third.
  Rename them freely.
- A ritual's invocation is offered at the book's pool sizes: 2d, 4d, 6d or 8d.
- Standing is kept on the faction, as the party's; a survivor who has earned a name of their own
  keeps theirs as a note.
- Finesse is offered on action and defense rolls; on a story roll, the GM reads it.

## What stays with the GM

Didact can't know the fiction, so these are prompts or the GM's call: vantage and thorns; stakes;
choosing and narrating impact moves, and whether to skip one for suspense; whether a use is risky,
potent, or past a touchstone's edge; Counter; most perks' effects beyond the engines (their +1d is
`perk`; their menus, once-per-session and once-per-scene uses, quick actions and "always" are
read from the sheet's perks); conditions and their timers (the urgent ones the rules make are
rolled as time passes; the rest the rules prompt); what
treatment and a doctor cost; addiction (the GM "may"); vehicles' chases and fuel; hauls' contents
and prices; karma out of every faction's earshot; fiction pillars and story kits beyond the
Junction; token initiative, the writers' room, encumbrance slots and weapon styles' thorns;
Watching the Stacks' caps (one fate intervention per roll; one free mark-clear per survivor per
scene) and building an eighth class.

## Credits

Grimfall is an unofficial, non-commercial fan work, adapted from Grimwild by J. D. Maxwell (Oddity
Press), used under CC BY 4.0, by way of Grimwild: Community Edition (lead developer Chancey Scott,
Groov Games). Fallout and its settings, creatures, and trademarks belong to Bethesda Softworks;
Grimfall is not endorsed by or affiliated with Bethesda Softworks, Oddity Press, or the Community
Edition team. Play it at your table, change it, pass it on: just don't sell it.
