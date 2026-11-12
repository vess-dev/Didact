# The Elder Scrolls 2e in Didact

The Elder Scrolls 2e is Cairn Second Edition with Skyrim's snow on it: the year 4E 201, the
Civil War, the dragons' return, barrows and Dwemer ruins. This pack is a hack of `cairn-2e`
(`extends: [cairn-2e]`): Cairn's machinery runs underneath, and this pack replaces or adds what
the game changes. An unofficial, non-commercial fan work (CC-BY-SA 4.0); The Elder Scrolls and
Skyrim are trademarks of Bethesda Softworks / ZeniMax.

**The golden rule of this hack: the Cairn core is sacred.** Saves, HP, inventory, the Armor cap,
combat, Scars, Critical Damage, detachments, the Fatigue of casting, exploration and Downtime
are Cairn's. **There are no save modifiers, ever**: a power re-rolls a failed save, passes it
automatically, or removes the need for it. Never invent a "+1 to the save".

## What runs as cairn-2e does

These are cairn-2e's rules, unchanged (cairn-2e's GUIDE.md has their details): `save`,
`save-together`, `morale`, `retreat`, `fate`, `steady`, `trap`, `lost`, `fatigue`, `relieve`,
`stabilize`, `attribute-damage`, `blast-targets`, `scar`, `scar-heal`, `attribute-reroll`,
`skip-camp`, `weather`, `faction-action`, `resolve-bond`, `resolve-omen`, and the generators
`cairn-2e.setting-seed`, `dungeon-seed`, `pointcrawl`, `point-of-interest`, `realm`, `faction`,
`monster`, `weapon`, `armor` and `gear` (they roll this pack's tables of the same ids: Skyrim's
cultures, terrain, dungeons, names and Marketplace). Replaced only for this book's words or
numbers: `dungeon-turn` and `watch` (the oil flask, Septims, Skyrim's locations; a wildcrawl is
`place=forest`; the watch's supply hands the Rations to `who=<pc>`, its make camp runs
`make-camp` for every PC, and the clock's night watch rolls its events twice by itself),
`downtime` (Septims; a goal's Milestones tracker made and ticked: below), `attribute-raise`
(`cap=18` where the book says "to 18": the Oghma Infinium, Racial Phylogeny) and growth (`didact
char advance <pc>`: a raised attribute stops at 18, the book's "raise an attribute by 1d4 (to
18)").

## What this game changes, and the command for each

### Fights

`didact combat start --party <foes>`. In round one each PC saves DEX to act (a **Dremora always
acts**), and a rider on an untrained mount also saves WIL: `didact do startled-mount who=<pc>`
(`trained=true` skips it). Then `didact do attack attacker=<a> target=<t> weapon=d8`, as in
Cairn, with these changes:

- **Attack kinds.** `kind=` says what the attack is: `mundane` (the default), `fire`, `frost`,
  `shock`, `poison`, `magic`, `silver`, `sun`, or several (`kind=magic,fire`). A kind in the
  target's `impaired_by` (a Nord's frost, a Dunmer's fire, a ghost's mundane blades) or a
  matching `resist-fire`/`resist-frost`/`resist-shock` condition (a potion, for the scene) makes
  it Impaired; a kind in its `enhanced_by` (fire against a vampire or draugr, silver against the
  beast-blooded, magic against the Apprentice stone's bearer) makes it Enhanced. Bestiary
  entries carry both lists.
- **Impaired and Enhanced cancel**: an attack that would be both rolls the weapon's own die
  (Dragonbane, Enhanced against dragons, against a dragon, which is a detachment).
- **Two weapons, several attackers, a beast's d8+d8** keep the higher: `weapon=2d8kh1` (two of
  a kind) or `weapon='{d8, d6}kh1'`. Impaired or Enhanced, each die becomes a d4 or a d12.
- `pierce=n` ignores n Armor (3: all of it). A **Khajiit's** unarmed claws (`mode=unarmed`) are
  d6, not d4.
- After damage the attack **prompts** for what the attacker's blow carries: its disease
  (`didact do disease who=<t> disease=<id>`) and its venom (`didact do venom who=<t>
  amount=1d4 lingering=true`: only the first time it hits a creature in a fight, and only if
  damage got past Armor). It reminds about Rockjoint and Droops when the attacker carries them.
- **Death:** STR 0 kills, except a **Dremora**, banished to Oblivion (status `banished`) and
  back after a season: `didact do reform who=<pc>`.
- **Panic:** `didact do panic who=<pc>`; a **draugr revenant** is immune to fear.
- Dragons, Alduin, the Mammoth, the Giant and the Dwarven Centurion are `type: detachment`.
- **One fight, one scene.** While the fight tracker runs (`combat start` … `combat end`), each
  PC's once-per-combat uses are counted in `once_per_combat` (the Command action, a vampire's
  restoring drain) and a second is refused; `combat end` clears them (the `fight-over`
  trigger). A table that plays its fights without the tracker counts by hand. When a scene ends
  (`scene end`), the `scene-over` trigger takes off what lasts a scene: a resist potion's
  ward, the Shadow's invisibility, and a form taken (the PC reverts).

### Races and once-per-day powers

Every PC has a race and its one trait (`race`, `trait`): chosen, or 1d10 down the book's list; a
background that names its people fixes it (a Bosmer Hunter is a Bosmer, a Telvanni Mage a
Dunmer: character creation takes it). The always-on traits run by themselves: Nord frost and
Dunmer fire Impaired (`impaired_by`), no cold deprivation for Nords (nor heat and ash for
Dunmer), the Khajiit's claws, the Argonian's water-breathing and immunity to ordinary disease.
The once-a-day ones: `didact do power who=<pc> power=<p>` with `voice-of-the-emperor` (re-rolls
the failed WIL save), `dragonskin`, `adrenaline-rush` (clears a Fatigue), `command-animal
target=<beast>` (its WIL save), `berserker-rage`. The Altmer's **Highborn** spares a casting's
Fatigue: `didact do cast who=<pc> spell=… free=highborn`. Any other once-a-day power (a
background's, a perk's, a Relic's): `power=other name='…'`.

**Once per day lasts until the next dawn.** The sheet's `used_today` lists what's spent; when
game time crosses into a new day (`didact time advance …`), the `new-dawn` trigger clears it and
the day's magical healing (`healed_today`), and reminds a vampire who didn't feed that it's
Deprived.

### Standing Stones (an option, off by default)

`didact campaign profile standing-stones=on`. Character creation then rolls or chooses one
(1d12, never the Serpent). One Stone at a time, changed only in play: `didact do visit-stone
who=<pc> stone='The Serpent'`. The blessings: `didact do power who=<pc> power=the-warrior` (and
`the-thief`, `the-lord`, `the-atronach`, `the-ritual`, `the-lover target=<npc>` (shifts its
disposition a step), `the-shadow` (the `invisible` condition), `the-tower`, `the-serpent
target=<foe>` (d6 poison, then its STR save)); the Mage and the Apprentice (twice a day) through
`cast free=the-mage|the-apprentice`; the Lady through `rest` (a Fatigue more, once a day); the
Steed is always on. The Apprentice adds `magic` to its bearer's `enhanced_by`; the Atronach
makes healing spells (`heal … spell=true`) fizzle.

### Magic

`didact do cast who=<pc> spell='Flames'` as in Cairn (both hands, a Fatigue; deprived or in
danger a WIL save (a fight the tracker runs is danger); `enhance=true` with time and safety). A
Scroll causes no Fatigue and is spent: one the caster carries (`spell='Scroll of Flames'`) is
known by its one use and used up; `scroll=true` for one no sheet holds. Changed: `free=<power>`
(above); **Witbane** calls a WIL save before any Spell Tome, **Brain Rot** a WIL save after or a
Fatigue more; no casting while **Transformed**.

**Healing has limits:** `didact do heal who=<pc>` (`amount=1d6` by default, `amount=all` for a
Greater Healing potion, `magic=false` for bandages, a surgeon's kit or a poultice, which don't
count). Magic mends a creature's STR once per day; more that day restores HP only. A magical
heal also stabilizes one in critical damage.

### Rest, camp, needs and recovery

- `rest`: as Cairn, but not in a fight the tracker runs, not with the **Rattles** (only a
  night's rest then) nor while Transformed; the Lady stone's Fatigue.
- `make-camp`: each PC eats one use of a Ration from their pack (none left: hungry tonight, a
  reminder says so); **Bone Break Fever** keeps one Fatigue; Dremora and draugr need no Ration.
  `watch action=make-camp` runs it for every PC.
- `deprive who=<pc> need=…`: Dremora and draugr revenants are never deprived of food, water,
  sleep or air, Briarhearts of sleep; cold never deprives a Nord or a vampire, heat or ash a
  Dunmer.
- `recover who=<pc>`: a week with a healer or temple, 50 Septims (`cost=0` when free). Not a
  Dremora (`didact do binding-mend who=<pc>`: a willing conjurer, 1d6 STR; or `oblivion=true`, a
  full season reconstituting in Oblivion, whole); a draugr revenant only with `barrow=true` (a
  week in a Nordic barrow: all its lost Attributes) or `didact do absorb-life who=<pc>` (a kill,
  1d6 STR, once a day).
- `coins`: a pouch under 100 Septims is petty (the `coin-weight` option, as in Cairn).
- `downtime who=<pc> action=research|training|ties|other goal='…' gold=<cost>`: a Downtime
  Action, somewhere safe and out of recovery (`abate=true`: a WIL save against the cost). The
  first action on a goal with `size=1`–`5` makes its Milestones tracker ("<PC>: <goal>") and
  completes one; the same `size=` later finds that tracker and ticks the next
  (`milestone-done`); `milestones=<tracker>` ticks one made by hand.

### Diseases, Vampirism and Lycanthropy

- `didact do disease who=<pc> disease=<id>`: a STR save or it takes hold (the sheet's
  `diseases`): `rockjoint`, `ataxia`, `witbane`, `brain-rot`, `bone-break-fever` (a Fatigue that
  stays), `rattles`, `brown-rot` (body armor −1, in the armor formula), `droops`, `greenspore`
  (strangers a step worse: `reaction` counts it), `sanguinare-vampiris` (max HP −1). `pass=true`
  when a power makes the save automatic. Argonians never catch ordinary disease; vampires, the
  beast-blooded, Dremora and draugr none at all.
- `didact do cure-disease who=<pc> how=temple|potion|shrine|vigilant|restoration|other`: any one
  cure clears them all, Sanguinare included; never the curses. A Potion of Cure Disease the
  patient carries is used up.
- **Sanguinare Vampiris** counts each new day uncured (`sanguinare_days`); at the third, the
  `become-vampire` trigger turns the character (`didact do become-vampire who=<pc>` when one is
  turned in the fiction). Cure: `didact do cure-vampirism who=<pc>` (Falion's rite), or taking
  on the Beast Blood.
- **Lycanthropy** is taken on willingly: `didact do become-werewolf who=<pc>`
  (`strain=werebear`: +1 max HP for good); ended by `didact do cure-lycanthropy who=<pc>`, or by
  Vampirism.

### Unusual PCs (the sheet's `nature`)

- **Vampire:** `didact do feed who=<pc> victim=<them>` (once a day: Fatigue and Deprived
  cleared; the victim loses 1d4 STR); `didact do drain who=<pc> target=<t>` (d6, ignores Armor,
  restores the HP dealt once per combat: counted while the fight tracker runs, otherwise
  `restore=false` once it's spent; `helpless=true`: Enhanced, and it always restores); `didact
  do sunlight who=<pc>` and `state=out` (Deprived in it; the drain restores nothing).
- **The change:** `didact do transform who=<pc>` (once a day; `ring=true`: the Ring of Hircine;
  the Vampire Lord costs a Fatigue and needs Molag Bal's deeper gift, its d8 touch is `drain …
  lord=true`). Transformed: the hide's Armor 1, no gear, Spell Tomes or rest. The form ends with
  the scene (`scene end` reverts it, or `didact do revert who=<pc>`; earlier with `early=true`:
  a WIL save; `totem=true`: the Glenmoril totem); a beast then feeds on a fresh kill before the
  next watch ends (a reminder is set).
- **Dremora:** banished at STR 0 (`reform`), mended by `binding-mend`, no mortal needs.
- **Draugr revenant:** `natural_armor` 1 (worn body armor replaces it; a shield or helmet
  adds), immune to fear, disease and gas; mends only in a barrow or by `absorb-life`.
- **Briarheart:** needs no sleep; the briar and the matron's leash are the Warden's to play.

### Hazards (off an attribute, not HP)

`didact do fall who=<pc> feet=30 landing=soft|hard` (1d6 STR per full 10 ft, a DEX save
halves); `drown who=<pc>` (past three rounds; Argonians, Dremora, draugr and `waterbreathing`
are spared; `icy=true` is cold too); `ablaze who=<pc>` each round, `state=out` to put it out,
`state=blaze` in a sustained blaze; `exposure who=<pc>` each watch in the cold (`warm=true`,
`shelter=true`, `extreme=true` for a blizzard, `plunge=true` for icy water) and `warm-up
who=<pc>` by a fire; `lightning who=<pc>`; `venom who=<pc> amount=1d4 lingering=true`, then
`venom-tick who=<pc>` at each of its next three turns, `cure-venom` for an antidote (one the patient carries is spent); `inhale
who=<pc>` each round of gas (1 WIL, a save against hallucination); `skooma who=<pc>` (the
crash).

### Crafting (Downtime Actions at a station)

- `didact do temper who=<pc> item='Steel sword' price=10 material=Steel`: once, to d12 or 3
  Armor; `price` buys the material at ×1 (Iron, Steel), ×5 (Dwarven, Elven, Orcish), ×20 (Glass,
  Ebony, Nordic, Stalhrim) or ×50 (Dragonbone, Daedric); `rushed=true`: a STR save. A piece the
  smith carries is read from their sheet (its die, its Armor and whether it's a suit, whether
  it's tempered or masterwork; a shield or helmet is refused) and marked there; for one no sheet
  of theirs holds, `die=`, `armor=` and `tempered=true` say what it is.
- `didact do brew who=<pc> brew='Potion of Healing'`: 1d4 petty, single-use doses into the
  brewer's inventory (`rushed=true`: WIL).
- `didact do learn-effect who=<pc> item=… effect=…` (unbinding a magic item, which is taken from
  the inventory: the sheet's `effects_known`), `didact do enchant who=<pc> item=… effect=…
  gem=greater worn=true constant=true` (one filled soul gem taken; the item's `enchantment`,
  `charges` and `recharge` set; constant only from greater, grand or black), `didact do recharge
  who=<pc> item=… gem=common` (one gem taken, its soul's charges added up to the maximum;
  `found=true`: a found Relic's own Recharge line rules).

### Skill Books

`didact do read-book who=<pc> book='Mace Etiquette'` (one turn, safe and quiet, not Deprived,
not in a fight the tracker runs): the perk fills one of the five `skill_books` slots and the
book is consumed (one copy taken from the reader's inventory). With five, `forget='<a book>'` is
chosen at the moment of reading. Aevar Stone-Singer's +1 max HP is applied (and taken back when
forgotten). A book the Warden made: `perk='…'`. The perks are reference text: apply them when
they come up (`didact table roll skill-book-perks --with book='Mace Etiquette'`).

### Companions and mounts

- `didact do loyalty who=<companion> step=up|down why='…'`: one step (`betrayed=true`: a
  faction-sworn companion's first real betrayal, two steps down). At 1 they leave at the next
  settlement; at 5 (Sworn) they take a hit for their PC once a day. A beast's only Armor is its
  hide's (the Bestiary's for its kind, or none): the ice wolf, hawk and old hound have none.
- `didact do command who=<pc> companion=<c> target=<foe> weapon=d8`: once per combat, Enhanced
  (`boost=reroll` for a re-rolled save instead); while the fight tracker runs, a second is
  refused until `combat end`.
- Mounts: `didact do travel-time … mount=horse|skyrim-horse` (the whole party mounted: a watch
  of Path or Terrain penalty off; a Skyrim horse also eases Perilous ground; never below the
  distance's watches), `didact do mount-left mount=… where=wild` (the Die of Fate: 3 or under,
  gone), `didact do startled-mount who=<rider>` (a thrown rider: a short fall, nothing but pride
  under 10 ft). Stabling is 5 Septims a night.

### Standing in the world (three separate tracks)

- **Faction Reputation** (`rep_<faction>`, −2 Hunted … +2 Sworn): `didact do reputation
  who=<pc> faction=stormcloaks step=up why='…'`. Rising drops the sworn enemy a step
  (stormcloaks/legion, dawnguard/volkihar, vigil/daedric_cults, thieves_guild/guards, and
  greybeards/blades with `paarthurnax=true`); `opposed=false` if word wouldn't reach it;
  `betrayal=true` for the two-rung first treachery of a faction the background tied them to.
  Factions: companions, college, thieves_guild, dark_brotherhood, stormcloaks, legion,
  greybeards, blades, dawnguard, volkihar, vigil, bards_college, forsworn, thalmor, skaal,
  guards, daedric_cults. It's on each PC's sheet: the book's Background Ties table starts the
  twelve tied backgrounds there, and a tie or a curse is that character's own.
- **Renown** (−3 Reviled … +3 Hero of Skyrim) is the party's one dial, on a party record:
  `didact new party "The Company" --set members=pc:<id>`, then `didact do renown
  party=the-company step=up deed='…'` (one step a session: a second move in the open session is
  refused; public deeds only, `public=false` refuses; `monstrous=true` never lowers it). Between
  arcs: `didact do renown-drift party=…`. It sets where a stranger's Reaction starts: `didact do
  reaction who=<npc> party=… toward=<pc>` (`toward` brings the PC's nature and Greenspore;
  `known=true` when a PC's curse is known; `shift=±n` for anything else: a faction's standing, a
  gift, an Inn on a first visit). A character who earned fame alone may have a party record of
  their own.
- **Bounty** (`bounty_<hold>`, Septims, on each PC's sheet: a crime is the criminal's): `didact
  do bounty who=<pc> hold=the_reach amount=40`, `pay-bounty`, `clear-bounty how=jail|left`.
  Holds: whiterun, haafingar, eastmarch, the_rift, the_reach, falkreath, hjaalmarch, the_pale,
  winterhold, raven_rock.

### Settlements

A `settlement` record computes Population, Defense and Prosperity from its `buildings` (1 each,
+1 for each building that raises it, 1–5; Defense above 2 needs the Palisade & Gate and the
Watchtower counts only with it; Cottages may be built more than once). `didact gen run
elder-scrolls-2e.homestead` makes the 1/1/1 homestead with its main hall. `didact do build
who=<it> building='Smithy' cost=… by=<pc>` (`petty=true` for a comfort, `steward=true` for the
Steward's House's building a season), `didact do raze who=<it> building=…`, `didact do
settlement-season who=<it>` (upkeep, then the d6 raid roll), `didact do raid-outcome who=<it>
outcome=lost building=…` (`outcome=won hardwon=true`: Defense +1).

## Making things

- **Characters:** `didact char new` (guided) or `--mode random`; prefill what the player chose:
  `--prefill '{"background": "Housecarl", "race": "Nord", "name": "Lydia", "youngest": "no"}'`.
  A background (the d50; the five unusual ones only with the `unusual-backgrounds` option), the
  race (a background that names its people, a Bosmer Hunter or a Telvanni Mage, takes it), its
  trait (a Dremora's suppressed), the gear, 3d6 Septims, the two tables, 3d6 ×3 with a swap, 1d6
  HP, traits, a bond, a Standing Stone with the option, 2d20+10 years (the Mer may be far
  older), an omen for the youngest, a name. Every result applies: +1 max HP, extra Septims, a
  masterwork piece in place of the starting one, a Spell Tome of three, 20 Septims of
  Marketplace gear, the Housecarl's chosen result, the companions, mule and hireling some
  backgrounds bring (records beside the character, their stats rolled), a background's faction
  ties, and an unusual background's nature, natural armor and weaknesses. A table result is
  prefilled with its full text (`"housecarl_1": "No one — yet. …"`).
- **Hirelings:** `didact char new elder-scrolls-2e.hireling` (a role and its daily wage) or
  `elder-scrolls-2e.hireling-background`.
- **Generators** (drafts: `gen show`, `gen edit`, `gen commit`): `elder-scrolls-2e.npc` (race, a
  name from that race, quirk, background, goal, virtue, vice; ordinary folk are 10s and 3 HP),
  `adventure-hook` (the job of the week, as a thread), `encounter` (a threat tier, then the
  creature from the Bestiary; a row naming several, one of them), `loot` (the hoard, and the
  table it sends you to), `relic` (the kind, then the relic; `daedric=true` for a Daedric
  Artifact), `spellbook` (the school, then the tome: Destruction's element and column, a
  Scroll's spell, Conjuration's Binding), `skill-book` (the series, then the title),
  `unique-weapon`, `unique-armor`, `forest-seed` (the wildcrawl; name it last), `homestead`,
  plus cairn-2e's generators listed above. Where the book leaves a choice to the Warden (the NPC
  race table's 12, a Spell Tome school's 6, which unique-weapon or unique-armor table, an
  encounter's tier, which creature of a row), a draft that rolls itself picks and says it picked
  for the Warden. A kind, a school or a series chosen (guided) or prefilled rolls its item, as
  the dice would; any item can be prefilled by its name, at any depth (`Ring of the Hunt`,
  `Fireball`, `Soul Trap`), and a row named further down rolls on from there. A Scroll of a
  chosen spell, as the book places them: `spellbook scroll=true` with the spell prefilled.
- **Names:** `didact name npc` (the race d12, then that race's names), `name place`, `name poi`,
  `name faction`, `name realm`.
- **The compendium:** `didact compendium find <words>`; `didact spawn <entry>` for a creature, a
  companion (`sworn-housecarl`, `shadowmere`, `frost`, …) or a horse. Bestiary entries carry
  `impaired_by`, `enhanced_by`, `disease` and `venom`; Relics, unique weapons and armors are
  `type: relic` with a `category`.
- **Tables:** `didact table roll <id>`. The book's two-step tables roll on by themselves:
  `relics` (the kind, then its relic), `skill-books` (the series, then the title), `spellbooks`
  (the school, then the tome: Destruction its element and column, a Scroll row its spell from
  `<table>-scroll`, Conjuration's 19–20 the Binding table); `table show` gives each step's own
  table.

## Options (session zero)

`didact session zero` asks the book's pacing and scope, and the options: `standing-stones`
(off), `unusual-backgrounds` (off), `tone` (heroic, adventurous (the default), gritty, grim; it
replaces Didact's own tone question), `coin-weight` (one-slot), and cairn-2e's
`unusual-weather` (off).

## Left to the Warden (reference text, not automated)

The rule language can't tell when these apply, or the book makes them the Warden's call: each
Skill Book's perk and each background ability (once per combat, "need not save", a contact), the
Stones' narrative blessings (the Tower's lock, the Ritual's servant), Reaction shifts for race
prejudice or a Bigoted NPC, the matron's leash and the briar, a Dremora's oaths, the settlement
buildings' non-numeric effects (the Mead Hall's rumor, the Temple's faster recovery, the Trading
Post's sale), the Jarl's favor and the Civil War, a Sworn faction's favor, the Thalmor's
distrust, enchantments and potions in play (a Resist Fire potion: `didact set <pc>
conditions+=resist-fire`, which the scene's end clears), a found Relic's own Recharge, the cost
of a building and the sum of a bounty, how far a thrown rider falls, Unusual Weather, and Shouts
(no PC has one).

## Settled with the author (and now in the book)

The pack's earlier readings, decided with the game's author and written into the book
(`reference/review-changelog.md` there lists each edit); the pack follows the book:

- **Once per day** ends at the next dawn (Character Creation → Races; the rules inventory).
- **Sanguinare Vampiris** turns at the third dawn uncured; turning vampire or werewolf clears
  the mundane diseases carried (Diseases & Afflictions).
- **Renown** is one dial for the party, on a party record; Faction Reputation and Bounty stay on
  each PC: the twelve faction-tied backgrounds are the book's table (Faction Reputation →
  Background Ties), and a tie or a curse is that character's own.
- **Races** roll on a d10 down the list; a background that names its people fixes the race.
- **Masterwork results** take the place of the starting weapon of their kind (the four rows
  that were ambiguous now say so).
- **Nordic** material is worth ×20, as Stalhrim (Crafting → Material tiers).
- **Animal companions** have only their hide's Armor (the Bestiary's for their kind, or none):
  the ice wolf, hunting hawk and old hound have none.
- **A raised attribute** stops at 18 where the book says "to 18" (growth, the Oghma Infinium,
  Racial Phylogeny); elsewhere the sheet's ceiling is cairn-2e's 20 (the book gives none).
- **A faction-sworn companion** falls two Loyalty steps on the first real betrayal.
- **A draugr revenant's** week in a barrow restores all its lost Attributes, a kill only STR.
- **The Warden's picks** (the NPC race table's 12, a Spell Tome school's 6, the unique-weapon or
  unique-armor table, an encounter's tier) are picked at random by a draft that rolls itself,
  which says so; the Marketplace has no die (each item equally likely when rolled).
- **A Scroll from a tome table** ("roll again for its spell") rolls the same table's spells.

## What is hidden, and what is inherited

`pack.yaml`'s `hides` drops what cairn-2e has that this game doesn't play with (`didact pack
info elder-scrolls-2e` lists it): every cairn-2e compendium entry this pack doesn't replace by
id (Cairn's bestiary, Marketplace goods, relics, spellbooks and companions), Cairn's
backgrounds' tables (`aurifex-1` …), its forest-name tables (a wild is named last, from what it
is) and NPC-name tables (names here go by race), the terrain-synonym tables for terrains this
book's Terrain Synonyms don't name (its tundra is Plains / Tundra, its swamp Bogs / Marsh), the
`spirit-absorbs` and `stone-heart` triggers (Cairn's bonds 10 and 15), all of cairn-2e's rules
text (this pack's 287 reference sections, this book's text, stand for it: `didact rules lookup`
finds only Skyrim's), and the Spellbook glossary term (a Spell Tome here; Petty, Cost,
Background, Companion, Relic, Scroll and Warden are this pack's own words).

Inherited, and played as cairn-2e has them: the rules listed under "What runs as cairn-2e does",
the Scars and their tables (`scars`, `scar-location`, `broken-limb`, `head-wound`), the
Reactions and Die of Fate tables, the seasons' weather tables (the same as this book's), the
`unusual-weather` option, the `new-day`, `still-deprived` and `between-sessions` triggers, the
cairn-2e generators listed there (on this pack's tables), its `npc`, `detachment`, `vehicle`,
`loc` and `faction` record types, its glossary for the shared vocabulary (Save, Fatigue,
Detachment, the seed and Downtime words), and its settings for the watches, the time units and
the faction turn (`pack.yaml` sets only what this book changes: the first round, the names by
race, the session zero questions).

## Credits

The Elder Scrolls 2e is a fan hack of Cairn Second Edition (Yochai Gal, with Adam Hensley and
Derek B.; CC-BY-SA 4.0), shared under the same license: an unofficial, non-commercial fan work.
The Elder Scrolls and Skyrim are trademarks of Bethesda Softworks / ZeniMax.
