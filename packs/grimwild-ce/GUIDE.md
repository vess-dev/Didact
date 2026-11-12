# Grimwild (Community Edition) in Didact

Grimwild is cinematic fantasy adventure with Moxie: roll only when it's risky, read the highest
die, and let thorns cut the result. This pack holds the Community Edition's text (CC0), its
paths and talents, backgrounds, monsters, crucibles and the rules as commands.

## Rolls

- **Action rolls:** `didact do action who=kestrel stat=agility thorns=1`. Spend spark with
  `spark=1`, add talents or setup with `dice=1`, and helpers with `assist=1` (rolled apart).
  Marks, bloodied, rattled and desperate add their thorns by themselves, and a used mark clears
  (with lasting marks, only a rest clears it). Two or more 6s are a **critical**: thorns can't
  cut it. A disaster gives spark.
  - Vantage sets the thorns: certain (no roll), reasonable (0-1t), doubtful (2t or more),
    impossible (no roll).
  - `stakes=low|regular|high|dire` says what the impact move weighs (regular unless declared;
    low in cozy fantasy): high stakes let a disaster drop the PC, dire stakes drop them on any
    prompted impact move (a prompt for `didact do dropped`). The GM can always skip a prompted
    impact move and take suspense.
  - `interrupt` is a talent's roll to stop an impact move: perfect stops it, messy stops it and
    the GM keeps (or takes) the suspense (Didact adds it), grim lets it land with the interrupter
    sharing it.
  - `spell`: two or more 1s among all the roll's dice, thorns and assists included, bring a
    **magical twist** for a sorcerer (as their twists manifest, chosen at creation: a wild surge
    is a 2d story roll plus the wild surge crucible, vex is `do vex`, a curse adds 1 to the GM's
    suspense), or for any caster with the dangerous magic dial (pick a 1d wild surge, a dark omen,
    or a 6d Corruption pool).
- **Defense rolls** when the GM spends suspense on an impact move:
  `didact do defense who=kestrel stat=brawn` (also `stakes=`, `assist=`). Criticals avoid it,
  uncut. Throwing yourself in front of an ally is a 1d defense roll that shares the risk: add
  `protect`.
- **Story rolls** for luck and what's outside the PC: `didact do story-roll dice=2` (1 for bad
  odds, 3 for good; `who=… spark=1` spends spark); two 6s are a perfect no thorn can cut. They
  are the pack's oracle: `didact ask 'Is the bridge out?' --odds bad|even|good`. Add the GM
  crucible for ideas: `didact table roll gm-crucible`.
- **Montages** zoom out: `didact do montage who=kestrel stat=agility` once for each PC taking
  part (2d each, `dice=1` for Jack of All Trades); the best result is the scene's outcome.
- **Power pools as action rolls:** `didact do pool-action who=kestrel pool=<rite or wand>` reads
  the highest die, then drops each 1-3 from the pool; spark and talent dice roll along and never
  drop; `drop=1` drops dice first for a potent spell. Thorns, criticals and twists as any roll.
- **Quarrels:** `didact do quarrel first=kestrel second=wren` (`helps_first=`, `helps_second=`,
  `third=` joins at 2d, `spark_first=`, `stakes='…'`): the highest die wins, a tie is a
  compromise or another roll, and everyone taking part takes spark.
- **Active vigilance** (an option): `didact do vigilance who=kestrel dice=2 thorns=0` gives a
  reveal, a hint or a strike.

## Damage and pools

- `didact do mark who=… stat=wits` (a second mark is harm), `didact do harm who=…
  kind=bloodied|rattled` (a second of the same kind is desperate; one more that would be
  desperate again drops you), `didact do dropped who=…` (it puts dropped on the sheet; `spark=1`
  adds a die; Dauntless adds one and saves a perfect), `didact do end-story who=…
  end=sacrifice|retirement|another` (a retiring PC dropped again perishes). A dropped PC is back
  when the scene ends (a prompt reminds you to clear it). `didact do vex who=…` for an
  instinctive response (`response=fight|flight|freeze|freakout`; rolled with random vex).
- **Pools:** `didact track new 'Bandits' --kind pool --size 4` (task, pressure, timer, resource,
  power or campaign: `--pool pressure`; linked phases: `--linked 4+4`), then `didact track roll
  bandits` drops every 1-3. Nothing dropped from a task pool? Push: `didact do push who=kestrel
  pool=bandits stat=brawn` (a mark for 1d; at 0d the event or the next phase comes), or pivot.
  The GM can spend suspense to drop 1d from any other pool: `didact do suspense spend=1
  pool=…`. `didact do refresh pool=…` fills a pool back up (per-session pools, Wild Shape each
  scene, a vassal or Patience at 0d); `didact do grow-pool pool=… by=1` adds dice (a core
  talent's growth; wealth's +2d with `most=8`); `didact do tick pool=…` drops exactly 1d (tick
  pools, an option).
- **Resting:** `didact do rest who=…` clears marks and harm. `didact do downtime who=…` is a
  month or a season: a full heal and the per-session talents' reset, then the GM rolls the
  faction pools (`didact faction turn`) and depletes one (`didact do faction-goal
  who=<faction> pool=<pool>`). With expanded downtime (an option) each PC picks an action
  instead: `act=rest|plan|pursue|unwind|venture` (`also=` for a second when treasure is sold
  off; `plan='…'`; `goal=<task pool>`, retraining a talent ends in `didact do switch-talent`).
  `didact do carouse who=…` in a settlement: a montage roll and spark (wealth: `coins=<pool>`
  gains 2d; sword & sorcery: +1 XP).

## The GM's suspense, sessions and experience

- **Suspense** lives on the story oracle's state (`didact oracle show`, or `didact do
  suspense`). Didact adds it where the book says the GM takes it: at pre-session (1), for the
  party's rest reset (2, once for the party: the first PC's rest takes it, and a new scene or
  session starts the next reset), a sorcerer's curse (1) and an interrupt's messy (1). The
  suspense moves take it too: `didact do suspense-move move=build-up|clue-in|resolve` (Build Up
  prompts each PC's spark; Foreshadow takes none). The GM's own choices are commands: `didact do
  suspense take=1 why=…` for a skipped impact move or a dark omen, `spend=1` to prompt an impact
  move at any time. A challenge keeps its own 2 bonus suspense for moves relating to it, from the
  moment it's made: `didact do suspense spend=1 challenge=<challenge>`.
- **Sessions:** when a session after the first starts, Didact runs `pre-session` for each PC
  (spark; thread reset to 2, 3 with Bardic Lore and +1 for each talent that gives a thread per
  session; the per-session talents' reset: Augury's omens rolled onto the sheet, Magnum Opus's 3
  touchstones, Herbalism's two herb names, Oathsworn's Affirmation, and a prompt to refresh talent
  and arcana pools); the GM takes suspense and is reminded to recap. With rest resets (an
  option), spark, thread and talents come with `didact do rest` instead, and `didact do reset
  who=… heal=…` is a narrative break's reset (1 harm healed); the GM takes 2 suspense once per
  reset.
- **Experience:** when a session ends each PC takes 1 XP (not side characters, not with milestone
  levels). More with `didact do experience who=… why=…`: `standout` (or `bonus`, about 1 session in
  4), `theme` (focused growth: Didact asks at each session's end), `bond-or-arc` (cozy fantasy:
  given by Didact at the session's end when a bond changed or an arc was completed), `carousing`
  (sword & sorcery), `arc` and `quest` (a solo quest's arcs, 1 each, and the quest, +1). `didact do
  change-bond who=… toward=… bond='growing respect' old='…'` gives the other PC spark; `didact do
  resolve-arc who=… arc='…' next='…'` gives spark.
- **Levels:** level L to L+1 takes L+1 XP (twice with slow progression or focused growth: each
  box slashed first). `didact char advance <pc>` (the Level up button) levels up step by step,
  and nothing changes until `char commit`:
  - a new talent: the list first (`talent_list`: your path's, any other path's, the background
    talents, or with your GM's OK the legacy talents, which the dice never pick), then the talent
    (`talent`): never another path's core, nor your path's own half core talent (a bard can't
    take Warcry); talents made with the GM (`gen run grimwild-ce.talent`) join the list; a half
    core talent brings its own choices (Arcane Training's 3 theorems, Divine Blessing's rite,
    Eldritch Affinity's magic, Natural Moxie's skills);
  - with stat progression (an option), +1 to a stat (at most 3) instead of the talent, once;
  - the core talent's growth at its levels (2, 4, 6 or 3, 6), written to `path_notes`, with what
    it has you choose: a wizard's theorem, a witch's 2 words of power, a psion's bastion, a
    rogue's skill, a sorcerer's magic path or technique, a warlock's Eldritch Talent, a vassal's
    aspect, an artificer's 2 touchstones (and a prompt for the major arcana); a cleric's rites and
    a druid's Wild Shape grow with `do grow-pool` once the level is committed (a level-up
    makes new records, but doesn't change the pools that exist);
  - the cap: 7, or 3 at smaller scale and in low or cozy fantasy; past it, `didact do
    switch-talent who=… drop=… take=…` at milestones (also for retraining, or a warlock changing
    an Eldritch Talent).
- **Level 0** (an option): no core talent and 3 stat points; 1 XP brings level 1, the core talent
  with its choices and pools (a cleric's rites, a warlock's Patience, …, made by the level-up)
  and the last stat point. A half core talent taken at level 0 gives way to the core, and another
  talent is chosen in its place.

## Making things

- **Characters:** `didact char new` walks through backgrounds and wises, traits and desires, a
  path with its core talent and one more talent (from any list, as a level-up offers them; the
  background talents link it to a heritage), what the path's page has you decide (a bard's songs,
  a paladin's tenet, a warlock's patron, …, kept in `path_notes`), stats (1 each plus 4 points), a
  name, then what the core talent has you choose, in `path_notes` and in `skills`, `bastions`,
  `magic`, `words`, `aspects` and `touchstones` (a fighter's style, a rogue's 3 skills, a
  sorcerer's 4 magic paths and techniques and how their twists manifest, a warlock's Eldritch
  Talent, a witch's 6 words, a wizard's 4 theorems, a cleric's rites, …) and its pools (a
  cleric's rites, a druid's Wild Shape, a summoner's vassal, a warlock's 8d Patience), the levels
  a campaign starts above 1 with, and the other pools: a talent's own per-session pool (Grenades,
  Luck, Favor, …) whenever the talent is taken, at creation or a level; the options' vigor,
  supplies, coins and armor; sword & sorcery's 4d Renown. Then starting arcana, features, arcs and
  bonds (crucibles rolled for ideas). `--mode random` rolls everything but the name: give one with
  `--prefill '{"name": "Wren"}'` or `char choose`.
- **Side characters** (solo party mode): `didact char new grimwild-ce.side-character`: one path
  talent and no path, 1 trait and 1 desire (and the negatives), backgrounds without wises; marks
  become harm, and they take no spark, thread or XP and don't advance.
- **Everything else** has a generator that follows the book's own procedure (choose each thing,
  or let the dice): on the Records page, or `didact gen run grimwild-ce.<generator>` (`--auto`
  lets the dice decide the rest).
  - The table: `party` (session zero: 2 concepts and 1 you aren't, the group arc, group-building
    questions; kept as a constant lore entry the brief always shows).
  - People and foes: `npc`, `monster`, `challenge` (a task pool with its 2 bonus suspense),
    `linked-challenge` (a whole in 2-5 parts, each its own pool and suspense), `battleground`.
  - Things: `arcana`, `potion`, `treasure`, `weapon`, `ritual` (a source, 2-3 anchors, the
    invocation's task pool).
  - The world: `region`, `settlement`, `site`, `faction` (its goals' pools, listed on it as
    pool_1, pool_2 for `didact faction turn`), `quest` (linked task and peril pools),
    `community-asset`.
  - The book has no name tables, so a generator waits for a name (a faction for its goals, a
    ritual for its intent and source, a linked challenge for its parts): prefill them.
- **A new talent** made with the GM: `didact gen run grimwild-ce.talent`; the talent it makes is
  offered at the next level-up.
- **Exploration tokens:** `didact do tokens who=… take=3` for each PC when the GM expands the map
  (the GM takes 3 too), `spend=2 buys='a point: …'`, `thread` to spend a thread as one, `clear`
  when the map is done.
- **Factions:** `didact faction turn` rolls every faction's listed pools; at 0d the goal comes to
  pass and a story roll from the faction's side says how.

## Options

The setting dials, the flavors and the optional rules are options a campaign chooses at session
zero (`didact session zero`, then `didact campaign profile flavor=grimdark rest-resets=on`, or
the web app's Settings page). An answer given wins over what a flavor implies.

- **Magic:** none takes the magical paths (and their talent lists) and arcana out; rare (and low
  fantasy) prompts that the party has one magic user at most; common starts PCs with a minor
  arcana; dangerous lets any spell twist.
- **Scale:** smaller caps levels at 3; larger starts PCs at level 3. **Lethality** sets the
  dropped story roll (gentle 3d, deadly 1d) and deadly gives a desperate PC an urgent condition.
- **Flavors:** grimdark sets deadly lethality, supplies, lasting marks, random vex and random
  bonds; low fantasy deadly lethality, the smaller scale, encumbrance, wealth and slow
  progression; sword & sorcery vigor pools and slow progression, plus a 1d dropped roll, marks
  and harm cleared when each scene ends, a Renown pool per PC and +1 XP for carousing;
  noblebright gentle lethality, a start at level 2 with a minor arcana, and a prompt to clear
  rattled after an intense scene; high fantasy the larger scale and token initiative, and 2 minor
  or 1 major arcana; cozy fantasy slow progression, low stakes by default, a cap at level 3, and
  +1 XP for a changed bond or a completed arc. The rest of each flavor is guidance in the brief.
- **Optional rules:** vigor (`do vigor`), armor (chosen at creation; `do armor`), supplies (and a
  reminder to roll it as each day passes), wealth, encumbrance and weapon styles at creation;
  rest resets (`do rest`, `do reset`); stat progression, level 0, slow progression, milestone
  levels and focused growth change advancement; active vigilance (`do vigilance`), tick pools
  (`do tick`); expanded downtime (`do downtime act=…`); the solo rules (the action roll asks the
  messy questions, reading the GM's suspense, and adds peril on a disaster or at dire stakes).
  Token initiative and the writers' room are in the brief.

## Readings where the book leaves room

- A witch's 6 starting words are 3 from each of the crucible's two tables, and each growth brings
  1 from each; a sorcerer's 4 are a magic path, a technique and 2 of either, and their twists
  manifest in one way chosen at creation (a custom one lists all three when it comes up).
- A twist counts every die of the roll: the caster's, assists' and thorns.
- A faction's depleted goal gets a 2d story roll read from the faction's side ("in their
  favor"); the GM can call the odds 1d or 3d.
- Sword & sorcery's 1d dropped roll is its own: its lethality dial ("strong enough to meet it")
  isn't the lethal end, so it doesn't bring deadly's urgent conditions; grimdark's and low
  fantasy's dials are, so they imply deadly. Low fantasy's "max level of 3" is the smaller
  scale; cozy fantasy's cap is its own (the smaller scale's threats don't fit it).
- Starting arcana don't add up: high fantasy's 2 minor or 1 major, else noblebright's or common
  magic's 1 minor; none at all without magic.
- Rest resets: a full rest still clears every mark and harm; a narrative break's reset heals 1
  harm (desperate first, unless `heal=` says which). The GM's 2 suspense come once per reset of
  the party (the first PC's rest or reset, until a new scene or session starts). The GM's
  pre-session suspense and recap stay.
- Slow progression slashes level 0's single box too (2 XP to level 1).
- Cozy fantasy's +1 XP is once per session, whether a bond changed, an arc ended, or both.
- A quarrel's spark comes whatever the result, a tie included; a messy defense roll at dire
  stakes lessens what would have dropped the PC.
- A level 0 PC may take their path's half core talent, with its own choices; at level 1 the core
  replaces it and another talent is chosen, and its choices stay on the sheet (keep what still
  fits). A level 0 PC makes the core talent's choices at level 1. A warlock's Eldritch Talents are
  on the talents list and noted in `path_notes`; a vassal's thematic talent is its aspect, not the
  summoner's talent.
- Without magic, the magical paths' lists are out; other paths' talents that grant spellcasting
  stay, to be reflavored as skill or technology.

## What stays with the GM

Didact can't know the fiction, so these are prompts or the GM's call: vantage and thorns;
choosing and narrating impact moves (the solo consequences table helps), and whether to skip
one for suspense; declaring stakes; when to make a suspense move (`do suspense-move` takes its
suspense; Build Up's spark is each PC's `do take-spark`); the solo messy's questions about a
challenge in the scene or a quest's last pool (the suspense one Didact answers); per-session
talent uses (inspiration, smite, competence), and the pools talents make in play (Animate
Objects, a duplicate, a spirit: `track new`); conditions and their pools; treatment; whether a
scene was intense (noblebright) or a milestone was reached (switching talents); one magic user
under rare magic; mooks, tiers and combat roles; token initiative, the writers' room and the
encumbrance slots (counted by hand); the GM's own exploration tokens; and most talents' special
cases (Maelstrom's 5s and 4s, Teamwork's 5s, Folk Hero, Luck's bonus die: add them with `dice=`
or by reading the roll).

## Credits

Grimwild: Community Edition (Preview 5.3), lead developer Chancey Scott (Groov Games), text
dedicated to the public domain (CC0 1.0); based on Grimwild by J. D. Maxwell / Oddity Press
(CC BY 4.0), subject to the original's non-commercial derivative terms.
