# Grimscrolls in Didact

Grimscrolls is an Elder Scrolls hack of Grimwild, by way of Grimwild: Community Edition: heroes in
Tamriel on the same engine (roll a few d6 and read the highest, d8 thorns cut it, pools run down,
enemies never roll). This pack extends `grimwild-ce`: the parent's engine runs it, and everything
Grimscrolls changes or adds is here, from the ten chapters of the rulebook: the twenty-three
classes and their 186 talents (23 Core Talents, 147 class talents, the curses' 16), the races,
birthsigns, standing stones and the Voice, survival (potions, coin, disease, the curses, crime,
shrines, the road, downtime), the Bestiary, the Reliquary, the GM's kit and the dials. What the
parent has that Grimscrolls doesn't play with is hidden (the end of this guide). An unofficial,
non-commercial fan work.

## What changes from Grimwild

| Grimwild | Grimscrolls | In Didact |
|---|---|---|
| path, core talent | class, Core Talent with a well or pool | `class`; the wells are `uses` fields; `didact do spend` |
| heritage, two backgrounds | a race (a background with a racial talent) and a background | `race`, `background`, `backgrounds` |
| — | birthsign, standing stones, the Voice | `birthsign`; `didact do take-stone`; `shouts` |
| talents stack | one die of each kind: talents, setup, a relic, a draught | flags on every roll: `talent setup relic draught` |
| sorcerer's twist | Destruction's backlash; anyone's with wild magic | `didact do backlash` |
| spellcasting talents | the six schools, each its own economy | `didact do cast school=…` |
| vigor pool, wealth (options) | 3d Potions and 4d Coin, every hero, on by default | `didact do potion`, `didact do spend-coin` |
| carousing, expanded downtime | downtime always has its five actions | `didact do downtime act=…` |
| arcana crucibles | the Reliquary's 176 relics, the tier gate, soul-fed pools | compendium `arcana` |
| monster blocks | the Bestiary's stat blocks; Faces of Tamriel | compendium `monster`, `npc` |
| flavors of fantasy | tone dials, flavors of Tamriel, Sheogorath's dial | options |

Rules that read the same as Grimwild's are the parent's, untouched: `story-roll`, `quarrel`,
`take-spark`, `pre-session`, `suspense`, `change-bond`, `resolve-arc`, `end-story`, `refresh`,
`grow-pool`, `tick`, `tokens`, `reset-suspense`, the faction turn (`faction-turn`, `faction-goal`)
and their triggers (the pre-session, the party's reset, a dropped hero's scene end). Everything else
below is this pack's; the story oracle is the parent's.

## Rolls

- **Action rolls:** `didact do action who=kazari stat=agility thorns=1`. `spark=1` spends spark;
  `talent`, `setup`, `relic`, `draught` add +1d each (one die of each kind, however many apply);
  `dice=1` for special dice on top (a sign's own die); `assist=1` per helper (rolled apart).
  Marks, a lingering exposure mark, bloodied or rattled on a related stat, desperate, starving
  and (on spells) strain add their thorns by themselves; a used mark clears. Two or more 6s are a
  critical (thorns can't cut it); a disaster gives spark. `stakes=low|regular|high|dire` weighs
  the impact move; `interrupt` is a talent's roll to stop one.
  - `hunter`: the Hunter's die, against the quarry; on a 6, a critical effect.
  - `momentum=2`: Acrobatics spends Momentum to remove thorns; remove every thorn and they come
    back as Momentum dice (each 7-8 raises the result a step). A cut gives Momentum back, even
    past the scene's amount (a new scene resets it), and Stamina's spark comes by itself.
  - `reckless`: 5s count as 6s, but 4s count as 1s (Critical Charge, Daring, Master
    Destruction): all or nothing, never messy.
  - `spell` (strain applies, and with wild magic two or more 1s go wrong) and `backlash` (a
    Destruction spell of The Elements): two or more 1s, thorns included, run `didact do backlash`
    by themselves.
  - As the wolf (`changed`), Brawn and Agility count as 3, Wits and Presence as 1 (Totem of the
    Moon: 2), and harm adds no thorns.
- **Defense rolls:** `didact do defense who=kazari stat=agility` (`protect`: 1d, 2d with the Lover
  Stone; `brace` spends 1 Guard and ignores every thorn; Agile Defender drops the situation's
  thorns on Agility by itself). A messy reminds Plate and Sidestep when they apply.
- **Story rolls:** `didact do story-roll dice=2` (1 bad, 3 good), or `didact ask '…' --odds even`.
  The GM crucible: `didact table roll gm-crucible`.
- **Montages:** `didact do montage who=kazari` for each hero (2d; `journey` gives Long Road its 3d).
- **Power pools** in place of a stat (a thrall, a rite, Blood, Coin, a relic's charge): `didact do
  pool-action who=kazari pool=<track>` (`drop=1` first for a potent rite or a huge ask).
- **Active vigilance** (an option): `didact do vigilance who=kazari dice=2`; `guarantee=hint` turns
  a grim into a hint, `guarantee=reveal` a messy or a grim into a reveal. Without the option, the GM
  picks by vantage (`didact table show vigilance`).

## Damage and recovery

- `didact do mark who=… stat=wits` (a marked stat, or one with a lingering mark, takes harm instead;
  a side character always does); `didact do harm who=… kind=bloodied|rattled` (deadlier lethality's
  4d Bleeding Out comes with desperate, made at once: `didact do bleeding-out who=…`, also for a
  dropped roll's messy); `didact do dropped who=…` (2d, softer 3d, deadlier 1d; Stamina +1d
  and its perfect; `draught` with softer potions); `didact do avoid-death who=…`;
  `didact do end-story who=… end=sacrifice|retirement|another`; `didact do vex who=…
  response=fight|flight|freeze|freak-out`.
- `didact do potion who=… (giver=…)` clears one harm, then rolls the giver's Potions pool (`free`
  for Mara's blessing or Benefactor's once a session). `didact do treat who=…` is treatment.
  `didact do rest who=… safe`: any real rest clears marks and harm; a night somewhere safe also
  refills potions and clears lingering exposure marks (you're "properly warm, fed, or clear of
  it"); `didact do shelter` does that alone.
- **Pushing yourself:** `didact do push who=… stat=brawn` (a mark), `pay=wind` (Dig deep),
  `pay=free why='Adrenaline Rush'`; `pool=<task pool>` drops 1d from a pool that dropped nothing.

## The classes' engines

- **Wells** are on the sheet (Temper, Wind, Edge, Guard, Might, Focus, Draughts, Momentum,
  Evasion, Quarries, Favors, Sway, Changes; Alteration's Spells and Potent spells; Mysticism's
  potent spells before strain): `didact do spend who=uzgash well=might n=2 pool=<troll>` says what
  the well buys (Might drops the dice itself, up to 2 a blow). Per-session wells refill when a
  session starts (with the pre-session), per-scene ones when a scene starts, by themselves; each
  Growth level adds its use at once.
- **Pools** are tracks the sheet points at: the class's (`plate`, `picks`, `shadow`, `thrall`,
  `blood`, `bloodlust`, `rite_1`..`rite_3`), the kit's (`potions`, `coin`, and with the options
  `supplies`, `armor_pool`), the talents' own (`juggernaut`, `poisons`, `flesh`, `resistance`,
  `unbinding`, `reflection`, `ward`, `leathers`, `disguise`, `credit`, `will`, `hide`) and a
  curse's timer (`curse_timer`). Character creation, leveling up and switching a talent make each
  one and point the sheet at it. Plate, Picks, the rites, the Armor pool and the talents' pools
  refresh with the session's reset (a talent's only while it's held), Shadow each scene, Hide each
  change; a relic's pool is a prompt (`didact do refresh pool=…`).
- **Casting:** `didact do cast who=vel school=alteration spell='Lock & Open'` spends the session's
  spell (or `potent`), unless `riskless` (no roll, no cost, unless potent or it `mends`), then rolls
  Wits. Destruction always rolls Presence and backlashes (`potent` asks for the push); Illusion
  spends the illusion until the next session; Mysticism's first potent spells are free, then each
  takes strain after it: the second puts +1t on all the spellcasting that follows, the third makes
  it +2t and is the last; Restoration rolls the rite's pool (`rite=<track>`, else the major rite).
- **Regain magic:** `didact do regain-magic who=… what=spell|potent|illusion|pool|strain|destruction`
  (`illusion=`, `pool=`, `why=`).
- **The Hunt:** `didact do quarry who=kazari target='the Pale troll'`, then `hunter` on the rolls.
- **The curses:** `didact do feed who=… how=sip|dry` (`foe` for Blood Healing; the GM takes
  suspense but for the session's first sip), `didact do starve`; `didact do change who=…`
  (`bloodied`: the moment you become bloodied doesn't count against the session's changes, as the
  Barbarian's red doesn't; `night` with Totem of the Moon: the session's first night change
  doesn't either), `didact do bloodlust who=…` after a potent feat, `didact do change-back` (the
  scene's end does it too).
- **Switching a talent:** `didact do switch-talent who=… drop=… take=… why=…` (the smaller scale's
  milestones, a curse's talent, retraining in downtime): the new talent's pool is made with it, and
  the sheet lets the old one's go (its record stays for `didact rm`).

## Surviving Tamriel

- **Coin:** `didact do spend-coin who=… (huge, keep)`; `didact do sell-haul who=…` (+2d, max 8d,
  and a second downtime action). **Plunder:** `didact do plunder place=robbed|ordinary|sealed`.
- **Crime:** `didact do crime jurisdiction='Whiterun Hold' (blood)` starts the jurisdiction's 6d (4d)
  pool, and a crime added there later rolls it (the pool counts its `crimes`); `didact do crime
  pool=<it>` rolls it when you show yourself in its towns; at 0d, `didact do arrest who=…
  choice=pay-the-fine|serve-the-time|resist-arrest pool=<it>` (`stolen='<item>'` takes back what
  was stolen; resisting puts the pool back at 4d and moves `faction=`'s standing a step down).
- **Shrines:** `didact do pray who=… divine=mara (tribunal)` cures every ordinary disease (and, at a
  Tribunal shrine, the Blight) and gives the blessing; `didact do use-blessing who=…`. A blessing
  is held until used or until the next session ends: Didact notes the session it was taken in
  (`blessed_in`) and clears it at the end of the next one.
- **Disease:** `didact do disease who=… disease=rockjoint`, `didact do cure who=… condition=…`; the
  curses: `didact do curse who=… curse=sanguinare-vampiris` makes the 4d timer (caught again, it's
  back at 4d) and points `curse_timer` at it; each night that passes (`didact time advance`) rolls
  it, and at 0d the hero turns (`didact do turn who=… curse=vampire` does it by hand). Any cure for
  disease ends a curse's timer, and turning spends it: either way the sheet lets it go, and its
  record stays for `didact rm`.
- **Hard country:** `didact do exposure who=… stat=brawn` (a lingering mark), `didact do shelter`.
- **Stones:** `didact do take-stone who=… stone=the-lady-stone` (the first fades).
- **The road:** a montage; `didact do tokens` when the GM expands the map; `didact gen run
  grimscrolls.region` (paths come out near, farther or far: the GM adds a waypoint for each day of
  hard travel), `grimscrolls.settlement`, `grimscrolls.site` (a barrow's five points).
- **Supplies** (an option): `didact do supplies` rolls every hero's pool at once (`who=` one hero's,
  after heavy use); with a Beast of Burden in the party, one die that would drop stays, unless
  it's that pool's last, and when the whole party rolls at once it is still one die. As days pass
  Didact reminds you.
- **Armor for everyone:** `didact do armor who=…` rolls the sheet's own Armor pool (`pool=` another).
- **Downtime:** `didact do downtime who=… act=rest|venture|carouse|pursue|plan (also=…)`: talents
  refresh, potions refill, marks and harm clear, then the action; `act=pursue project='Build the
  House'` (`dice=` its pool, 4d unless said) makes the project's task pool the first time and rolls
  it each time, `goal=<pool>` an existing one; the GM rolls the factions. `didact do guild who=…
  guild='…'` makes the 6d Rise in the Guild; `pool=<it>` rolls it.

## The GM's kit

- **Suspense** lives on the story oracle (`didact do suspense take=1`, `spend=1 pool=…`,
  `challenge=<track>` for a challenge's own); Didact adds it at pre-session, for rest resets, an
  interrupt's messy, a vampire's feeding, backlash that draws an eye. Suspense moves: `didact do
  suspense-move move=build-up|clue-in|foreshadow|resolve` (Build Up gives every hero their spark).
- **Challenges:** `didact gen run grimscrolls.challenge` (a 2d-8d task pool with its 2 bonus
  suspense), `grimscrolls.linked-challenge` (chained pools; the 2 bonus suspense once, on the first
  pool), `grimscrolls.battleground` (features, and threats with a timer or 2 suspense each).
- **Threats:** `didact gen run grimscrolls.foe --prefill '{"creature": "Draugr"}'` puts a Bestiary
  threat or Face in play: its card and its pools (the card's own pool when its Note gives one, else
  its tier's usual; a boss's linked parts, with the 2 bonus suspense once on the first; a fail
  state's timer). Its pool takes the card's name, and the name picks the pool wherever only a
  tracker will do: `didact track roll draugr`, `track tick draugr`, and this pack's rules' `pool=`
  (`didact do spend who=uzgash well=might n=2 pool=draugr`). `didact show`, and the parent's own
  `pool=` and `challenge=` (`suspense`, `refresh`, `grow-pool`, `tick`), take any record, so they
  still need its id (`track:draugr`). `didact compendium find dragon`; a new threat: `didact gen
  run grimscrolls.monster`.
- **Factions:** `didact gen run grimscrolls.greywatch` (the Powderkeg's seven factions and their
  pools), `grimscrolls.faction`; `didact faction turn`; `didact do standing who=<faction> shift=-1`
  (outlawed starts the 6d They Find You and lists it with the faction's pools).
- **Quests:** `didact gen run grimscrolls.quest`: a daunting quest's 4d + 4d + 6d and its peril's
  4d + 4d, both linked.
- **Princes:** `didact do prince-task who=… prince=Azura` makes the 8d Patience pool.
- **Holdings:** `didact gen run grimscrolls.holding`, `grimscrolls.community-asset`; `didact do
  stores pool=<stores> haul=minor`, `roll`.
- **Weather:** `didact do drift` steps the Weather counter (made at 1 the first time; `name=` another
  drift, `track=` a counter of your own). **Sheogorath's dial:** `didact do madness`.

## Making things

- **Heroes:** `didact char new` walks Chapter 3: race, background, birthsign (choose, or roll a
  month), class and its Core Talent, the racial and birthsign talents, stats (1 each plus 4),
  traits, desires, a name (the race's two offered), what the Core Talent has you choose (a
  thrall's kind and aspect, formulae, elements and forms and how backlash shows, illusions,
  disciplines, rites, recipes) and its well or pool, the hero crucibles for features, the kit
  (Potions, Coin), and the options (an oath, a standing stone, armor, supplies). `--mode random`
  rolls it all: prefill what the player chose (`--prefill '{"name": "Kazari", "race": "Khajiit",
  "class": "Marksman"}'`). The larger scale starts at level 3, gaining levels 2 and 3 as leveling
  up does; level 0 starts without the Core Talent, which arrives with level 1.
- **Leveling up:** `didact char advance <hero>`: a talent from any class's list (the curses' need
  the blood; a tag's lock is enforced: Master X needs X's spellcasting, Recovery magic to regain,
  Reflect Blows an armor pool, the thrall talents a thrall; register training keeps levels 2 and 3
  to the background's seven skills), the Core Talent's growth (its well, its spellbook; a pool's
  +1d is a prompt naming the pool: a draft can't change another record), and what a talent brings
  (a Novice spellbook, a pool, a Shout). A pool a level brings (a curse's Blood, a talent's own) is
  made and the sheet pointed at it when the level is committed.
- **Side characters:** `didact char new grimscrolls.side-character` (stats as a hero's, one talent,
  a race and a background, no wises tracked). **Followers:** `didact gen run grimscrolls.follower`.
  **The company:** `grimscrolls.party`.
- **Things:** `grimscrolls.arcana` (a relic by the book's recipe), `grimscrolls.treasure` (a
  haul: one of the book's examples, or a Reliquary relic of its tier with its first pool),
  `grimscrolls.weapon`, `grimscrolls.ritual`, `grimscrolls.talent`;
  `grimscrolls.door-under-greywatch` is the first-session story kit. Generators wait for names the
  book doesn't give (labels, faces, rituals' intents and anchors): prefill them.

## Options

Chapter 10's dials are options a campaign sets at session zero (`didact session zero`, then
`didact campaign profile lethality=deadlier flavor=grim-north`). `coin` and `potions`
(standard, grimmer, self-only, shared, softer) are on by default; `wild-magic` is the wild magic
dial. A flavor sets its dials and what they imply in turn (the grim north's deadlier lethality
brings 2d potions, pulp heroics' softer lethality softer ones). Rules and character creation read:
scale (cap 3, or start at 3), lethality (dropped's dice, deadlier's Bleeding Out, the potions it
implies), wild magic, the flavors, Sheogorath's dial, coin, potions (shared: the company's one
pool, made when a session starts, or by `didact do party-potions`), soul-fed, armor, supplies,
encumbrance, weapon styles, rest resets, milestone levels, focused growth, the slower road, level
0, stat progression, by the book, stones from the start, register training, oaths, tick pools,
active vigilance, solo. The law of the land, token initiative and the writers' room are in the
brief. Grimwild's own dials (its magic, wealth and vigor pool, lasting marks, random vex, random
bonds, expanded downtime) are hidden.

## Settled in the book

Where the rulebook was silent or contradicted itself, it was edited (2026-11-11, smallest change,
the author's own voice) and the pack follows it: strain lands on the spellcasting after the potent
spell that takes it; a mook's soul feeds no relic, a tough's restores 2d, an elite's or greater
fills it (the Soul Gem card's giant is an elite, so the card's example is now a sabre cat); a
linked challenge brings its 2 bonus suspense once; a side character has a hero's stats; the
Greywatch barrow's faction pool is the story kit's *6d The Seal Wears Thin*; a daunting quest's
peril is 4d + 4d; a talent that guarantees a reveal turns a grim into one too.

## What stays with the GM

Didact can't know the fiction: vantage and thorns, which stat, the stakes, impact moves and
whether to skip one for suspense, Counter, the suspense moves' timing; the once-per-session and
once-per-scene talent uses that aren't a well (most talents: Warrior's re-roll, Thief's die,
Fighting Stance, Bullseye, …: add their dice with `dice=` or by reading the roll); lighter and
heavier steps; a greater foe losing its next move; conditions and when they clear; reagents,
recipes and draughts' effects; a vampire under the open sun (+1t: `thorns=1`); the hauls a party
holds; standing's thorns; story kits and quests' framing; the law of the land; and what the dials
leave as guidance (stakes more often, rarer permanent conditions). The rules make the pools the
book starts (a bounty, a curse's timer, Bleeding Out, a Prince's Patience, a guild's rise, They
Find You, Corruption, a project, the weather's counter) or take the one of that name already
there; a pool that's done with leaves the sheet (`unset:`), but no rule removes a record, so a
cured or spent curse's timer and a switched-out talent's pool print the `didact rm` to run. Nothing in
Grimscrolls counts per fight (wells and talents go by the scene and the session), so a fight run
with `didact combat start` needs nothing more than the scene does.

## Hidden and inherited

grimwild-ce's items that have no place in Grimscrolls are hidden (`hides` in pack.yaml; `didact
pack info grimscrolls` lists them): its paths and path type, its talents, backgrounds, monsters
and arcana, every one of its tables (Grimscrolls has its own, under the parent's ids where the
procedure is the same: `gm-crucible`, `combat-tiers`, `combat-roles`, `region-map`, …), all its
rules text and glossary (the ten chapters are this pack's reference and glossary), the sorcerer's
twist, the vigor pool, the narrative-break reset, the random potion generator, the noblebright and
sword-and-sorcery scene-end riders, and its options with no place here. `compendium find`, `table
list`, `rules lookup` and `define` show Grimscrolls only. What is inherited is the engine
Grimscrolls shares, listed at the top of this guide, plus the story oracle and the faction turn's
setting; inherited rules print their source as Grimwild's pages. The suspense moves and the
supplies' day are this pack's own (they loop over the party).

## Credits

Grimscrolls is an unofficial, non-commercial fan work, adapted from Grimwild by J. D. Maxwell
(Oddity Press), used under CC BY 4.0, by way of Grimwild: Community Edition (lead developer
Chancey Scott, Groov Games). The Elder Scrolls and its settings, creatures, and trademarks belong
to Bethesda Softworks and ZeniMax Media. Play it at your table, change it, pass it on: just don't
sell it.
