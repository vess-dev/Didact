# Skyrim: The Elder Scrolls 2e's campaigns and Holds

The setting of The Elder Scrolls 2e book (CC BY-SA 4.0), for either Elder Scrolls system:
`elder-scrolls-2e` (the Cairn hack) or `grimscrolls` (the Grimwild hack). It holds the book's ten
campaign frames, all set in Skyrim in 4E 201: the Main Quest, the Civil War, the Companions, the
College of Winterhold, the Thieves Guild, the Dark Brotherhood, the Daedric Quests, Dawnguard,
Dragonborn and Hearthfire. Each is one of the book's "frames, not railroads": a pitch and its
stakes, tone and touchstones, an arrival, plot beats with their branches, a pointcrawl of places, a
cast, clocks, threats, rewards and a climax. It also holds the gazetteer of the nine Holds and
Solstheim, and the canon they stand on: the Dragon Crisis, the Civil War and the Talos ban, the
Thalmor, the guilds, the Daedric Princes. This is an unofficial, non-commercial fan work; "The
Elder Scrolls" and "Skyrim" are trademarks of Bethesda Softworks / ZeniMax.

The pack requires only `core`, so a world of either system can enable it. Its entries carry each
system's block side by side: Elder Scrolls 2e's numbers (`mechanics.elder-scrolls-2e`), and
Grimscrolls' card where its Bestiary or its Faces has the threat or the person
(`mechanics.grimscrolls`). Didact checks and shows only the world's.

## Enabling it

```
didact world new skyrim --system elder-scrolls-2e     # or --system grimscrolls
didact pack enable elder-scrolls-skyrim               # the world's: every campaign in it
didact campaign new helgen
```

This gives you, at once:

- the calendar (below);
- the lore: the canon comes up when play names it, and the setting's tone is always in the brief;
- the frames as text: `didact rules lookup the civil war clocks`, `didact rules lookup the main quest
  climax`;
- the glossary: `didact define thalmor`;
- the compendium: `didact compendium find delphine`.

Nothing is a record in the world until you bring it in.

## Starting a frame

Pick one, or let `didact table roll elder-scrolls-skyrim.frames` pick one at random. Then:

```
didact gen run elder-scrolls-skyrim.frame --prefill '{"frame": "The Main Quest"}' --auto
didact gen show g1          # what it drafted; `gen edit` to change it
didact gen commit g1
```

The generator reads the world's system:

- under Elder Scrolls 2e, the frame's clocks are clocks of their die;
- under Grimscrolls, they are pools, and what isn't a tracker is said in Grimscrolls' terms;
- under any other system, they are clocks, and each threat keeps both Elder Scrolls systems'
  blocks, which that system doesn't read: give it that system's own.

It also compares the frame's day with the campaign's, and says which command fits (below, "The
calendar"). The draft holds the frame's records:

- **The quest** (`quest:the-main-quest`). The pitch is its goal, and the italic lead is its visible
  text. Its GM notes hold the date, the stakes, the arrival, the plot beats and the climax, the
  frame's other sections by name, its Bestiary creatures by each system's id, and its rewards by
  each system's catalog id. Read them first: `didact show quest:the-main-quest --gm`.
- **The region and its places** (`loc:helgen`, `loc:riverwood`, …). Each place has the frame's text
  in its GM notes and its `region` set. A place that is a Hold's capital or key location (Bleak
  Falls Barrow, Labyrinthian, Markarth, Raven Rock) is the Hold's own record, with the frame's line
  added.
- **The cast**: one record per person, so a line naming several people makes a record for each
  (Ralof and Hadvar; Gormlaith, Hakon and Felldir). Where the book gives a person a stat block, the
  record is a monster with each system's block (Ulfric, Kodlak, Mercer Frey, Serana; Grimscrolls
  has no card for Mercer); the rest are people, with the cast line in their GM notes.
- **The threats**: monsters with each system's block. A threat who is also in the cast is a single
  record (Alduin, Odahviing, Miraak, Lord Harkon). The same person in another form keeps a record
  of their own (Ancano, and Ancano empowered by the Eye).
- **The factions** the frame plays with (`compendium/factions.yaml`): their agenda and obstacle.
- **The clocks**, as trackers. Under Elder Scrolls 2e each is a clock of the frame's die (`track
  tick`); under Grimscrolls a pool (below); under any other system a clock, as Elder Scrolls 2e
  has it. Two count rather than tick, and are counters under every system: the Companions'
  Harbinger's Hope (witches' heads, 0–5) and Dawnguard's Serana's Trust (1–5, from 3). The Blades'
  Patience starts at 1, and the Thieves Guild's clock, the Guild's Luck, starts full and counts
  down (`didact track tick <it> --by -1`). Two are rules, not timers, and make no tracker: the
  Main Quest's War in the Way and the Dark Brotherhood's Listener's Standing; the generator says
  how to run them, in the terms of the world's system.

The cast, the threats and the clocks come in secret: `didact reveal <id>` as the party meets them.
Places come in known, with their text for the GM only. Write what the party sees with
`didact set <place> description='…'`, and move them there with `didact visit <place>`.

The frames interleave: the Main Quest and the Civil War share Helgen and Season Unending, the
Companions' Ring of Hircine is won in a Daedric quest, Dawnguard needs the Main Quest's Elder
Scroll. Each frame drafts its own records. Where the world already has the person or the place,
fold the new record into the old one: `didact merge <new> <old>`.

The generator is the way to start a frame: it links each place to its region and makes the
clocks the world's system's trackers. To bring in part of a frame by hand, import it by its tags
(an entry needs every tag given): `didact compendium import elder-scrolls-skyrim --tag the-civil-war
--tag place --dry-run` lists the Civil War's places, and without `--dry-run` brings them in (`--tag
cast`, `--tag threat`, `--tag clock`, and `--type npc` beside them). An import takes the entries as
they are: its clocks are clocks, even under Grimscrolls. One entry: `didact spawn
elder-scrolls-skyrim.<id>`. Without a tag, `compendium import` would bring in every frame at once:
don't.

**The Daedric Quests** are a sandbox of fifteen self-contained quests, one per Prince, each built
for a single session (Nocturnal's is the Thieves Guild's). The frame brings in its overview quest,
the Vigilant of Stendarr and the Vigil. Each Prince's quest comes in on its own, with its key
people, when a Prince takes an interest:

```
didact gen run elder-scrolls-skyrim.daedric-quest --prefill '{"quest": "Pieces of the Past"}' --auto
```

Its goal is the hook; its GM notes hold the bargain and the twist, the beats, the key people and
foes (with the Bestiary creature each fights as), and the artifact by each system's id. Refusing
the bargain is always a valid ending.

**Hearthfire** has no cast or clocks: it is the between-adventures frame. It brings in its three
plots (Lakeview Manor, Windstad Manor, Heljarchen Hall) and its stat blocks: the housecarl, and the
troubles that come calling (bandits, a giant, a confidence trickster, an assassin, a spriggan).
Building the home is each system's own business (below).

## Visiting a Hold

```
didact gen run elder-scrolls-skyrim.hold --prefill '{"hold": "The Rift"}' --auto     # or let --auto pick
didact gen commit g2
```

The Hold comes in as a region: its GM notes hold the gazetteer's whole entry, its Jarl, barrow,
ruins, other corners, troubles and faces. Its capital (the region's heart) and its key locations
(the barrow, the Dwemer ruin, the notable sites) come in as places, its Jarl and the rival the war
would seat as people (Solstheim's ruler is Councilor Lleril Morvayn). They come in known: the Jarls
of 4E 201 are no secret. Run the map as it stands at the start of 4E 201, and let the war move the
pieces: should the other side win the Hold, the Jarl is deposed and the rival installed. Under
Elder Scrolls 2e the gazetteer is also its rules text: `didact rules lookup the holds the rift`. By
hand, a Hold's tag brings all of it: `didact compendium import elder-scrolls-skyrim --tag
hold-the-rift --dry-run`.

## The calendar

The book doesn't print a calendar: it assumes the Tamrielic one ("the year 4E 201"). The pack uses
it as the canon gives it: twelve months (Morning Star 31 days, Sun's Dawn 28, First Seed 31, Rain's
Hand 30, Second Seed 31, Midyear 30, Sun's Height 31, Last Seed 31, Hearthfire 30, Frostfall 31,
Sun's Dusk 30, Evening Star 31) and seven days (Sundas, Morndas, Tirdas, Middas, Turdas, Fredas,
Loredas).

It starts at the book's own moment, the day the Main Quest's cart reaches Helgen: **Sundas, 17
Last Seed 4E 201**, the day Skyrim itself opens. Every date Didact shows is written so, with its
era, and a date you give it is read the same way; `didact time show` names the day.

The seasons follow the months' Gregorian equivalents: spring from 20 First Seed, summer from 21
Midyear, fall from 22 Hearthfire, winter from 21 Evening Star. Under Elder Scrolls 2e, each new day
rolls the season's weather by itself. Under Grimscrolls, weather is a drift (Chapter 9): `didact do
drift` each dawn steps the Weather counter (made at 1, calm, the first time).

The book names no holiday with a date, and Skyrim's own calendar gives none. The holidays are six
that the canon dates and keeps all over Tamriel: the **New Life Festival** (1 Morning Star),
**Heart's Day** (16 Sun's Dawn), **Tales and Tallows** (3 Hearthfire), the **Witches' Festival** (13
Frostfall), **Saturalia** (25 Evening Star) and the **Old Life Festival** (31 Evening Star). Three
are a Prince's summoning day too: Clavicus Vile's, Sanguine's and Mephala's.

**Each frame's date.** Every frame is set in 4E 201. The Main Quest has a day of its own, the
calendar's start: Helgen burns that day. The Civil War's classic opening runs out of Helgen too, or
it opens the day the party enlists. The other eight have no day of their own: each opens whenever
play reaches it (Jorrvaskr, the bridge at Winterhold, Brynjolf in the Riften market, a Prince
taking an interest, a land deed), from the calendar's start, the book's moment.

A campaign opens on any date of the calendar, before its start or after it:

- `didact campaign new <id> --date '3 Frostfall 4E 201'` opens a new campaign on it (a weekday in
  front, as the frames write their dates, is fine);
- `didact time set '<date>'` moves an open campaign there, until its first session;
- after that, only `didact time advance` moves the date.

The generator compares the frame's day with the campaign's. A frame with no day of its own opens on
the campaign's today, once the book's moment has come. The Main Quest on another day: before the
first session it gives the `time set`; after, a day behind the campaign is past (open the frame
from today, or in a campaign of its own with `--date`), and one ahead is advanced to. The quest's
GM notes give each frame's date and what reaches it.

| Frame | With | Opens | Open a campaign on it |
|---|---|---|---|
| The Main Quest | a campaign of its own | Sundas, 17 Last Seed 4E 201 | `didact campaign new <id>` |
| The Civil War | a campaign of its own | Sundas, 17 Last Seed 4E 201 out of Helgen, or the day the party enlists | `didact campaign new <id>` |
| The Companions, The College of Winterhold, The Thieves Guild, The Dark Brotherhood | each a campaign of its own | whenever play reaches it, from Sundas, 17 Last Seed 4E 201 | `didact campaign new <id>` |
| The Daedric Quests | a side arc beside any frame | whenever a Prince takes an interest, from Sundas, 17 Last Seed 4E 201 | `didact campaign new <id>` |
| Dawnguard, Dragonborn | side arcs (DLC); Dragonborn pairs with the Main Quest | whenever play reaches it, from Sundas, 17 Last Seed 4E 201 | `didact campaign new <id>` |
| Hearthfire | a side arc (DLC), between adventures | once the party can buy its land, from Sundas, 17 Last Seed 4E 201 | `didact campaign new <id>` |

A frame with no day of its own may open later in the year: give the day with `--date` (`didact
campaign new <id> --date '3 Frostfall 4E 201'`). A side arc usually joins the campaign already in
play, on its today.

Nothing in the frames is played before the start. The history they lean on is lore, and dated:
the Oblivion Crisis (3E 433), the Red Year (4E 5), the Great Collapse of Winterhold (4E 122), the
Great War and the White-Gold Concordat (4E 171–175), the Markarth Incident (4E 174–176), and Gallus's
murder twenty-five years before the Thieves Guild frame.

## Under Elder Scrolls 2e

Everything applies as written, because the frames are written in its terms.

- **Threats** carry its stat blocks. Fight them with `didact combat start --party <it>` and
  `didact do attack attacker=<pc> target=<it> weapon=d8`. A dragon, a giant or Durnehviir fights as
  a detachment (its abilities say so). A block the frame runs as a Bestiary creature names it
  (`elder-scrolls-2e.dragon-priest`), and Sahloknir, run as a Dragon with no line of its own, carries
  the Dragon's numbers. The frames' "Use X from the Bestiary" creatures are listed in the quest's
  notes by id: bring one in with `didact spawn elder-scrolls-2e.<id>`.
- **The Voice** is a force of the world. Player characters get no Shout; Dragonrend in the Main
  Quest and Bend Will in Dragonborn are story devices the party enables but doesn't wield. Run the
  prophecy one of the book's two ways: the Last Dragonborn is an NPC the party fights beside,
  protects or seeks; or a player character is touched by Akatosh, a matter of fiction and Growth
  (one narrow, permanent boon, earned), never a list of Shouts (`didact rules lookup the dragonborn
  and the voice`).
- **Faction Reputation** is on each PC's sheet: `didact do reputation who=<pc> faction=<key>
  step=up why='…'`. The keys of the setting's factions: the Stormcloaks `stormcloaks`, the Imperial
  Legion `legion`, the Thalmor `thalmor`, the Greybeards `greybeards`, the Blades `blades` (opposed
  to the Greybeards once they demand Paarthurnax's death: `paarthurnax=true`), the Forsworn
  `forsworn`, the Companions `companions`, the College `college`, the Thieves Guild
  `thieves_guild`, the Dark Brotherhood `dark_brotherhood`, the Vigil of Stendarr `vigil`, the
  Dawnguard `dawnguard`, the Volkihar `volkihar`, the Skaal `skaal`. The Silver Hand, the Synod, the
  Psijic Order, the Nightingales, the Black-Briars and the Penitus Oculatus have no rung of their
  own: play them by the fiction.
- **Renown** is the party's: `didact new party "The Company" --set members=pc:<id>`, then `didact
  do renown party=<it> step=up deed='…'`, one step a session at most. The frames say what each
  public deed is worth (the Main Quest's Thaneship, dragon-trap and World-Eater: Known, Renowned,
  Hero of Skyrim).
- **Bounty** is kept per Hold: `didact do bounty who=<pc> hold=the_rift amount=<n>`.
- **Companions.** Lydia is the Player's Guide's Sworn Housecarl (`elder-scrolls-2e.sworn-housecarl`,
  Loyalty 4); Serana and Frea are named companions, hardier than a rolled one. Loyalty moves with
  `didact do loyalty who=<them> step=up`; Serana's Trust is her Loyalty, so keep the two together.
  In a fight, `didact do command who=<pc> companion=<them> target=<foe> weapon=d8`, once per fight
  while `combat start` runs it.
- **The curses.** The Companions' beast-blood is the Werewolf of Playing Unusual PCs: `didact do
  become-werewolf who=<pc>`, and the Glenmoril head in the Flame `didact do cure-lycanthropy
  who=<pc>`. Harkon's gift is the Vampire, with its Vampire Lord form: `didact do become-vampire
  who=<pc>`, then `didact do transform who=<pc>` (its touch: `didact do drain who=<pc> target=<foe>
  lord=true`).
- **Homesteads.** Hearthfire runs on Settlements: once the deed is bought, `didact gen run
  elder-scrolls-2e.homestead --prefill '{"plot": "Lakeview Manor"}' --auto` makes the 1/1/1
  homestead with its main hall, and `didact merge loc:lakeview-manor settlement:lakeview-manor`
  folds the frame's plot into it, text and all. Build with `didact do build who=<it>
  building='Smithy' cost=1500 by=<pc>`, and turn each season with `didact do settlement-season
  who=<it>` (a raid's end: `didact do raid-outcome`).
- **Rewards** named in its catalogs are listed by id in the quest's notes
  (`elder-scrolls-2e.wuuthrad`). Give one with `didact inv add <pc> 'Wuuthrad'`. What a frame
  describes itself (the Wolf Armor, the Black Books) is described in place.

## Under Grimscrolls

The numbers in the frames are Elder Scrolls 2e's, not Grimscrolls'. Use Grimscrolls' own rules
instead.

**Which Tamriel** (Chapter 1). Grimscrolls draws on three chronicles and lets the table choose:
this is Skyrim in 4E 201, so a card whose clause gives it to another province or era belongs
elsewhere unless your story wants it. At session zero, turn on its law of the land (Chapter 10):
`didact campaign profile law-of-the-land=skyrim` (Talos worship is a crime, the Thalmor carry the
warrants, and dragons are real again).

**Threats.** "Enemies never roll" (Chapters 2 and 9): a dangerous foe is a task pool. Where
Grimscrolls' Bestiary has the same threat, its card is the record's Grimscrolls block (tier, role,
traits, moves, wants, the note with its pools): the Dragon for Mirmulnir, the Dragon Priest for
Morokei and Nahkriin, the Vampire Lord for Harkon, the Silver Hand for Krev the Skinner. Where its
Faces of Tamriel has the person, the Face is (Paarthurnax, Delphine, Arngeir's Greybeards, Ulfric,
Tullius, Elenwen, Kodlak, Serana, Cicero, Neloth, Barbas): a tier, a role and the one fact. Play the
card, and ignore HP, Armor, STR, DEX and WIL.

- **Pool size by tier** (Chapter 7): mooks are fodder, and a pack is one pool, usually 4d; toughs
  fall one at a time, and a knot of them is a pool, usually 6d; an elite is a challenge unto itself,
  usually 6d; a boss owns the scene at 8d, or as a linked challenge with a fail state.
- **No card.** Frame it as a challenge (Chapter 9): a task pool of 2d to 8d, one or two traits, two
  or three moves, and a fail state when failure has a shape (`didact gen run grimscrolls.challenge`;
  a boss in phases: `grimscrolls.linked-challenge`). Give it a tier and a role (Chapter 7).
- **The fight.** A threat with a card: `didact gen run grimscrolls.foe --prefill '{"creature":
  "Dragon"}' --auto` puts the card in play with its pools (the card's own pool when its Note gives
  one, else its tier's usual; a boss's linked parts, with the 2 bonus suspense once on the first;
  a fail state's timer), and a record of the card: fold that into the frame's record (`didact merge
  monster:dragon monster:mirmulnir`) and its pools follow. A threat's GM notes name its card, and
  the quest's notes the card for each Bestiary creature in the frame. A threat with none (Mercer
  Frey): put its pool on the table under a name of its own (a record's name makes `show`
  ambiguous), `didact track new 'The fight with Mercer Frey' --kind pool --pool task --size 6 --for
  <its id>`, or `--linked 6+4+8` for a linked challenge. Hurt it and roll the pool (`didact track
  roll …`); at 0d it's beaten.

**Saves and damage.** A save the text calls for is a defense roll, made when trouble comes that the
heroes' own roll didn't invite (Chapter 2): `didact do defense who=<pc> stat=agility`. Agility to
dodge, Brawn to absorb, Wits to see it coming, Presence to keep your nerve. Damage the text deals is
an impact move at the stakes you say (Chapters 2 and 9): low, a mark at most; regular, one harm;
high, moves land double; dire, any move drops them.

**The Voice** (Chapter 5) is an optional talent: ask the table before anyone takes it. A hero who
has it knows one Shout, and Dragonrend is among the Words; the frames' Shouts stay story devices
unless a hero at the table carries them. Alduin's card agrees with the Main Quest: without
Dragonrend his pool can't drop, and he dies only in Sovngarde.

**Clocks are pools** (Chapter 2): a pressure pool for trouble closing in.

- Roll the pool where the clock would tick. Dice landing 1–3 drop, and at 0d the clock's end
  happens.
- Grimscrolls sizes pools 2d (short), 4d (medium) and 8d (long), with 6d between. The generator
  gives a clock as many dice as its die: a d4 clock is a 4d pool, a d6 one 6d. The Blades'
  Patience starts at 3d of 4d. The Guild's Luck, stock running out, is a resource pool.
- For a countdown the table should read like a clock, turn on tick pools (Chapter 10,
  `didact campaign profile tick-pools=on`): a tick pool never rolls, and drops exactly 1d when
  triggered (`didact do tick pool=<it>`).
- When a pool other than a task pool refuses to budge, the GM can spend suspense to drop 1d.
- The Harbinger's Hope and Serana's Trust stay counters.

**The curses** (Chapter 6). The Companions' Circle passes the beast blood on purpose, in a cup: a
4d Sanies Lupinus timer (`didact do curse who=<pc> curse=sanies-lupinus` makes it), rolled each
nightfall, as Didact does when a night passes; at 0d the hero turns (`didact do turn who=<pc>
curse=werewolf` turns one by hand). Harkon's gift makes a vampire at once, as the frame has it
(`didact do turn who=<pc> curse=vampire`). Turned, a hero has the curse's price and none of its
gifts until they take its talent (Chapter 4). Cures are adventures, and one of the chronicles'
cures is the Companions' own: the heads of the Glenmoril witches, burned in a hero's tomb.

**Hard country** (Chapter 6). A blizzard in the Pale, an ash storm off Red Mountain over Solstheim:
+1t while you work in it, or a lingering mark as you push through (`didact do exposure who=<pc>
stat=brawn`). The Sea of Ghosts in winter is the killing kind: a 4d timer, 2d in the water.

**Loot** (Chapters 6 and 8). If a reward is in Grimscrolls' Reliquary, use its card
(`grimscrolls.<id>`, listed in the quest's notes): a minor, major or mythic arcana. A Prince's
artifact comes with the Prince's attention. Anything else is a haul: minor, a good sword or a fat
purse; major, a suit of ebony or a house in town; mythic, a ship and its crew or a dragon's hoard.
Prices in Septims are flavor: a few hundred is a minor haul, a few thousand a major one. Every
hero's money is a 4d Coin pool.

**Crime** (Chapter 6). Each Hold keeps its own ledger: a pressure pool for that Hold, 6d for a theft
or a brawl, 4d for blood (`didact do crime jurisdiction='The Rift'` makes it, `blood` for blood; a
crime added there later rolls it). A thane's title forgives one arrest, and the Thieves Guild can
make a ledger disappear for a price.

**Factions** (Chapter 9). Reputation is standing: honored, trusted, stranger, watched or outlawed.

- Each step a frame gives moves standing one step: `didact do standing who=<faction> shift=±1
  why='…'`. Read the book's Sworn as honored, Trusted as trusted, Unknown as stranger, Distrusted
  as watched, and Hunted as outlawed.
- Outlawed starts a 6d They Find You campaign pool.
- Run a frame's factions as faction pools, rolled between sessions and in downtime (`didact faction
  turn`).

**Guilds** (Chapter 6). The Companions, the College, the Thieves Guild, the Legion: joining one is a
story detail and a set of duties, and the rise is a 6d Rise in the Guild task pool (`didact do guild
who=<pc> guild='The Companions'` makes it; `pool=<it>` rolls it when a contract is finished). Each
time it empties, a rank and something real; the frames' ranks (Ice-Veins to Stormblade, Quaestor
to Legate, Harbinger of the Companions) are what it can bring.

**The Daedric Princes** (Chapter 9) are never a stat block: a voice, a bargain, and a campaign pool.
When a hero accepts a Prince's task, `didact do prince-task who=<pc> prince='Molag Bal'` makes the
Prince's 8d Patience pool, rolled whenever they stall, bargain or disappoint; at 0d the Prince
clears the matter up in person. Each Prince's sphere, wants and pay are Grimscrolls'
(`grimscrolls.molag-bal`, named in each quest's notes, and the generator gives the command). Boethiah's old Champion fights as Grimscrolls' Daedric Champion
(`grimscrolls.daedric-champion`), whose note names him.

**Barrows and ruins** (Chapter 9) are 5-point sites: place the Hoard first, then the Door, the
Riddle, the Twist and the Reckoning (`didact gen run grimscrolls.site`).

**A frame's main line** can run as Grimscrolls' quest if you want one (Chapter 9): linked task pools
racing peril pools, the plot beats as its links (`didact gen run grimscrolls.quest`).

**Followers** (Chapters 4 and 9). Play Serana, Lydia and Frea as followers, built per Speechcraft's
Allure: three tricks, two flaws (`didact gen run grimscrolls.follower`).

**Homes** (Chapters 6 and 9). Raising the house is a downtime project (`didact do downtime who=<pc>
act=pursue project='Build the manor'` makes its task pool and rolls it). Built, Hearthfire's manor
is a holding: it grows on a Stores pool fed by hauls, and each die that drops pays toward the next
asset, a minor one at 4 (a wall, a forge, an alchemy garden) or a major at 8 (`didact gen run
grimscrolls.holding`, then `didact do stores`). Give every asset a face: the steward, the smith,
the bard who won't leave.

**Greywatch.** Grimscrolls has a sandbox of its own (Chapter 9, the Greywatch Powderkeg): a toll town
on the Pale Pass road, the one way between Cyrodiil and Skyrim that stays open in winter, written
for the civil war, with seven factions and a first-session story kit (`didact gen run
grimscrolls.greywatch`, `grimscrolls.door-under-greywatch`). It is Grimscrolls' own and stands apart
from the canon frames: none of its people or places are in them, and the setting doesn't place it.
Run it beside the frames if you like; it replaces none of them.

## Ids, tags and where things are

- **Entries:**
  - a frame's quest: `<frame>` (`the-main-quest`);
  - its region: `<frame>-region`;
  - its places, cast, threats and clocks: `<frame>-<name>` (`the-civil-war-ulfric-stormcloak`);
  - the Daedric Quests' fifteen: `the-daedric-quests-<quest>`, and their people
    `the-daedric-quests-<name>`;
  - the Holds: `hold-<hold>` (`hold-the-rift`), and their capitals, key locations and Jarls
    `hold-<hold>-<name>`;
  - the factions, by name without a leading "the" (`compendium/factions.yaml`); the College's and
    the Dawnguard's end in `-faction`, since their frames have their names.
- **Tags:**
  - a frame's entries carry its id, and one of `region`, `place`, `cast`, `threat` or `clock` (a
    cast member with a stat block is a monster record, and carries both, ally or not);
  - the quest carries `frame`, and `main-campaign` or `side-arc`;
  - a Prince's quest carries `daedric-quest` and its Prince (`molag-bal`); its people carry the
    quest's id;
  - a Hold carries `hold` and its own id (`hold-the-rift`); its places `hold`, the Hold's id and
    their kind (`capital`, `barrow`, `dwemer-ruin`, `great-ruin`, `notable-site`), and, when they are
    a frame's places, `place` and those frames; its people `hold`, the Hold's id, and `jarl`
    (Solstheim's `ruler`) or `rival`. So `--tag <frame> --tag place` imports all of a frame's
    places, and `--tag hold-the-rift` a whole Hold;
  - a faction carries the frames it plays in.
- **Reference:**
  - each frame section: `<frame>-<section>` (`the-civil-war-plot-beats`);
  - each stat block: `<frame>-threats-<name>` or `<frame>-cast-<name>`;
  - each Prince's quest: `the-daedric-quests-<prince>`;
  - the intro: `campaigns-…`;
  - not the Holds: they are elder-scrolls-2e's rules text (`elder-scrolls-2e.the-holds-…`).
- **Tables:**
  - `frames`, `holds` and `daedric-quests`, to pick one;
  - the lookups the three generators read.

From The Elder Scrolls 2e (CC BY-SA 4.0), a Skyrim hack of Cairn Second Edition by Yochai Gal. This
pack is shared under the same license. The Grimscrolls cards and Faces it carries are Grimscrolls'
(an unofficial, non-commercial fan work adapted from Grimwild by J. D. Maxwell, CC BY 4.0, by way of
Grimwild: Community Edition) and keep Grimscrolls' own terms: play them at your table, change them,
pass them on — just don't sell them.
