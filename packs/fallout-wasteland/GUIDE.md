# The Wasteland: Fallout 2e's campaigns and vaults

The setting of the Fallout 2e book (CC BY-SA 4.0), for either Fallout system: `fallout-2e` (the
Cairn hack) or `grimfall` (the Grimwild hack). It holds the book's 21 campaign frames, from the
Capital Wasteland in 2277 to Atlantic City in 2105. Each frame is "enough structure for four to
ten sessions": a pitch, tone and touchstones, an arrival, plot beats, a pointcrawl of places, a
cast, clocks, threats, rewards and a climax with several endings. It also holds the catalog of 39
vaults, and the canon they stand on: the Great War, Vault-Tec, FEV, the factions, the lands. This
is an unofficial, non-commercial fan work; "Fallout" is a trademark of Bethesda Softworks / ZeniMax.

The pack requires only `core`, so a world of either system can enable it. Its entries carry each
system's numbers side by side (`mechanics.fallout-2e`, `mechanics.grimfall`). Didact checks and
shows only the world's.

## Enabling it

```
didact world new capital --system fallout-2e      # or --system grimfall
didact pack enable fallout-wasteland              # the world's: every campaign in it
didact campaign new purity                        # opens on Tuesday, 23 October 2277
```

This gives you, at once:

- the calendar (below);
- the lore: the canon comes up when play names it, and the setting's tone is always in the brief;
- the frames and vaults as text: `didact rules lookup fallout 3 clocks`, `didact rules lookup vault 11`;
- the glossary: `didact define geck`;
- the compendium: `didact compendium find vault 22`.

Nothing is a record in the world until you bring it in.

## Starting a frame

Pick one, or let `didact table roll fallout-wasteland.frames` pick one at random. Open the
campaign on the frame's date (each frame's is in the table under "The calendar"), then draft the
frame:

```
didact campaign new reclamation --date 'Monday, 23 October 2102'
didact gen run fallout-wasteland.frame --prefill '{"frame": "Fallout 76"}' --auto
didact gen show g1          # what it drafted; `gen edit` to change it
didact gen commit g1
```

A campaign already open moves to the frame's date with `didact time set '<date>'`, until its first
session. The generator compares the frame's date with the campaign's, and says which command fits.

The generator reads the world's system:

- under Fallout 2e, the frame's clocks are clocks of their die;
- under Grimfall, they are pools;
- under any other system, they are clocks, and each threat keeps both Fallout systems' numbers,
  which that system doesn't read: give it that system's own.

The draft holds the frame's records:

- **The quest** (`quest:fallout-3`). The pitch is its goal, and the italic hook is its visible text.
  Its GM notes hold the date and how to reach it, the arrival, the plot beats and the climax. They
  also hold the frame's Bestiary creatures by each system's id, and its rewards by each system's
  catalog id. Read them first: `didact show quest:fallout-3 --gm`.
- **The region and its places** (`loc:capital-wasteland`, `loc:megaton`, …). Each place has its
  text in its GM notes and its `region` set. A place that is a cataloged vault is the vault's own
  record.
- **The cast**: one record per person, so a line naming several people makes a record for each.
  Each record has the role the book gives them, and the whole cast line in its GM notes. Where the
  line says what they want, that goes in `details.wants`.
- **The threats**: monsters with each system's numbers. A cast member who is also a threat is a
  single record (Colonel Autumn, Benny, Kellogg …). The same person in another form keeps a record
  of its own (the Mechanist throned and unseated; Blackburn as a behemoth).
- **The factions** the frame plays with (`compendium/factions.yaml`): their agenda and obstacle.
- **The clocks**, as trackers. Under Fallout 2e (and any other system) each is a clock of the
  frame's die (`track tick`). Under Grimfall each is a pool (`track roll`, below). Three clocks are rules, not timers: the
  Karma Clock, and the ambient clocks (Dead Money's Cloud, Lonesome Road's Rads). They make no
  tracker, and the generator says how to run them. The Cloud has its own roll:
  `didact table roll fallout-wasteland.cloud-clock`.

The cast, the threats and the clocks come in secret: `didact reveal <id>` as the party meets them.
Places come in known, with their text for the GM only. Write what the party sees with
`didact set <place> description='…'`, and move them there with `didact visit <place>`.

A side arc drops into its main campaign whenever play reaches it, and the generator names a main
campaign's side arcs. Some frames continue another: Broken Steel follows Fallout 3, and
Wastelanders follows Fallout 76. Each drafts its own records. Where the world already has the
person or the place, fold the new record into the old one: `didact merge <new> <old>`.

To bring in part of a frame by hand, import it by its tags. Every tag given must match, and
`--dry-run` first shows what would come:

```
didact compendium import fallout-wasteland --tag fallout-3 --type loc --dry-run   # region, places, vaults
didact compendium import fallout-wasteland --tag the-pitt --tag cast             # its people
```

The generator is still the way to start a whole frame: it makes Grimfall's pools, and it leaves out
the clocks that are rules. One entry at a time is `didact spawn fallout-wasteland.<id>`. The ids
are:

- `<frame>-<name>` (`fallout-3-megaton`, `fallout-new-vegas-benny`);
- `<frame>-region`;
- `vault-<n>`.

Without a tag or a type, `didact compendium import fallout-wasteland` brings in all 21 frames and
39 vaults at once. Don't use it that way.

## Finding a vault

```
didact gen run fallout-wasteland.vault --prefill '{"vault": "Vault 11"}' --auto     # or let --auto pick
didact gen commit g2
```

The vault comes in as a place. Its GM notes hold its Premise, Layout, Inhabitants, Reward and Hook,
with the rewards by each system's catalog id. Its **Hidden** note is a secret line: reveal it with
`didact reveal loc:vault-11 '<words from the line>'`, and only when they earn it. Inhabitants that
the catalog gives a stat line come with the vault, as threats.

Run it by the catalog's checklist and its note on Overseers: `didact rules lookup vault checklist`.
Under Grimfall the generator lays the vault out as a 5-point site instead (below). When one of
Vault 96's specimens escapes, roll its quota mutation:
`didact table roll fallout-wasteland.vault-96-mutations`.

## The calendar

The pack uses the real calendar: real months and weekdays, 29 February in leap years, and four
seasons (spring from 20 March, summer from 21 June, fall from 22 September, winter from 21
December).

It starts at the book's own default moment. The book's implied setting, the Commonwealth of Ashes,
is "two centuries after the war that ended the old world" (Player's Guide), and the war was
23 October 2077. So the calendar starts on **Tuesday, 23 October 2277**, the year Fallout 3 opens.
`didact time show` names the day. Under Fallout 2e, each new day rolls the season's weather by
itself. Under Grimfall, weather is its drift (Chapter 9): `didact do drift at=<place>` each dawn.

The holidays are the two the book gives a date: **Christmas Eve** and **Christmas** (Charleston's
flood, in Fallout 76). The book also names Thanksgiving and Fasnacht, but those move from year to
year. Didact's holidays fall on a fixed day, so mark those two by hand.

**Each frame's date.** The book gives each frame's year, or its main campaign's year:

- Fallout 3: 2277, the book's default moment.
- New Vegas: 2281, the year New Canaan burned and Mister House is 261.
- Fallout 4: 2287, when Vault 111's last pod thaws.
- The Appalachian frames: from Reclamation Day, 23 October 2102, to 2105.

For the day:

- Fallout 76 opens on Reclamation Day itself. Broken Steel opens two weeks after Fallout 3's
  climax. Both are as the book says.
- New Vegas opens on 19 October 2281 and Fallout 4 on 23 October 2287: the days the games they
  adapt open.
- Wastelanders, Steel Dawn, Skyline Valley and Atlantic City open on Reclamation Day's
  anniversary.
- A side arc opens on its main frame's date, or whenever play reaches it.

A campaign opens on a frame's date, before the calendar's start or after it:

- `didact campaign new <id> --date '<date>'` opens a new campaign on it;
- `didact time set '<date>'` moves an open campaign there, until its first session;
- after that, only `didact time advance` moves the date. A frame whose date is behind a campaign in
  play opens from that campaign's today.

The quest's GM notes and the generator give the command for each frame.

| Frame | With | Opens | Open a campaign on it |
|---|---|---|---|
| Fallout 3 | main | Tuesday, 23 October 2277 | `didact campaign new <id>` |
| Operation: Anchorage, The Pitt, Point Lookout, Mothership Zeta | Fallout 3 | Tuesday, 23 October 2277 | `didact campaign new <id>` |
| Broken Steel | Fallout 3 | Tuesday, 6 November 2277 | `didact campaign new <id> --date 'Tuesday, 6 November 2277'` |
| Fallout: New Vegas | main | Wednesday, 19 October 2281 | `didact campaign new <id> --date 'Wednesday, 19 October 2281'` |
| Dead Money, Honest Hearts, Old World Blues, Lonesome Road | New Vegas | Wednesday, 19 October 2281 | `didact campaign new <id> --date 'Wednesday, 19 October 2281'` |
| Fallout 4 | main | Sunday, 23 October 2287 | `didact campaign new <id> --date 'Sunday, 23 October 2287'` |
| Automatron, Far Harbor, Vault-Tec Workshop, Nuka-World | Fallout 4 | Sunday, 23 October 2287 | `didact campaign new <id> --date 'Sunday, 23 October 2287'` |
| Fallout 76 | main | Monday, 23 October 2102 (Reclamation Day) | `didact campaign new <id> --date 'Monday, 23 October 2102'` |
| Wastelanders | Fallout 76 | Tuesday, 23 October 2103 ("a year after Reclamation Day") | `didact campaign new <id> --date 'Tuesday, 23 October 2103'` |
| Steel Dawn | Fallout 76 | Thursday, 23 October 2104 | `didact campaign new <id> --date 'Thursday, 23 October 2104'` |
| Skyline Valley, Atlantic City | Fallout 76 | Friday, 23 October 2105 | `didact campaign new <id> --date 'Friday, 23 October 2105'` |

## Under Fallout 2e

Everything applies as written, because the frames and vaults are written in its terms.

- **Threats** carry its stat blocks. Fight them with `didact combat start --party <it>` and
  `didact do attack attacker=<pc> target=<it> weapon=d8`. The frames' "Use X from the Bestiary"
  creatures are listed in the quest's notes by id; bring one in with `didact spawn fallout-2e.<id>`.
- **Rads and saves** work as the text says: `didact do rad who=<pc> source=hot-zone`,
  `didact do save who=<pc> attr=DEX`. Two places carry their rad zone on the record (`rad_zone`):
  - the Glowing Zone is a hot zone: `didact do rad-zone who=<pc> zone=hot scenes=1`;
  - Far Harbor's island is an ambient one, a Rad a watch of travel beyond the condensers:
    `didact do rad-zone who=<pc> watches=2`.
- **Karma.** The Karma Clock is the party's karma ladder:
  `didact do karma party=<it> shift=±1 why='…'`.
- **Faction reputation.** When a frame moves a faction ("that faction's Reputation falls to
  Vilified, one step at a time"), use Fallout 2e's ladder, a step at a time:
  `didact do reputation who=<faction> shift=±1 why='…'`.
  - The book's opposed pairs (Overseer's Guide, Faction Reputation) are the NCR and the Legion,
    the Brotherhood of Steel and the Enclave, the Railroad and the Institute, and the Minutemen and
    raiders as a bloc.
  - To make a pair of the setting's factions opposed, set it in both directions, for example
    `didact set new-california-republic opposed=faction:caesars-legion` and back.
  - Between sessions, `didact faction turn` asks what each faction in play did toward its agenda.
    The setting's factions carry their agenda and obstacle in Fallout 2e's own faction fields.
- **Rewards** named in its catalogs are listed by id in the quest's and the vault's notes
  (`fallout-2e.maria`). Give one with `didact inv add <pc> 'Maria'`. Relics that a frame defines
  itself are described in place.

## Under Grimfall

The numbers in the frames and vaults are Fallout 2e's, not Grimfall's. Use Grimfall's own rules
instead.

**Threats.** "Enemies never roll" (Chapters 2 and 9): a dangerous foe is a task pool. Where
Grimfall's Bestiary has the same threat, its card is the record's Grimfall block (tier, role,
traits, moves, pools). Play the card, and ignore HP, Armor, STR, DEX and WIL.

- **Pool size by tier** (Chapter 7):
  - mooks are fodder, and a pack is one pool, usually 4d;
  - toughs fall one at a time, and a knot of them is a pool, usually 6d;
  - an elite is a challenge unto itself, usually 6d;
  - a boss owns the scene at 8d, or as a linked challenge.
- **No card.** Where Grimfall's Bestiary has no such threat, frame it as a challenge (Chapter 9):
  a task pool of 2d to 8d, one or two traits, two or three moves, and a fail state when failure
  has a shape. Give it a tier, and a role from Chapter 7.
- **The fight.** When a fight starts, put the threat's pool on the table under a name of its own
  (the threat's own name would make `show` ambiguous). For example:
  `didact track new 'The fight with Colonel Autumn' --kind pool --pool task --size 6 --for <its id>`.
  Hurt the threat and roll the pool (`didact track roll …`); at 0d it's beaten.
- The quest's notes name the Grimfall card for each Bestiary creature in the frame.

**Saves and damage.** A save the text calls for is a defense roll, made when trouble comes at the
survivors that their own roll didn't invite (Chapter 2). The GM picks the stat:

- Agility to dodge;
- Brawn to absorb;
- Wits to see it coming;
- Presence to keep your nerve.

Damage the text deals is a Hit Hard impact move, at the stakes you say (Chapters 2 and 9):

- low: a mark at most;
- regular: one harm;
- high: moves land double;
- dire: any move drops them.

**Clocks are pools** (Chapter 2): a pressure pool for trouble closing in, a timer pool for events
unfolding, a campaign pool for long-fuse events between sessions.

- Roll the pool where the clock would tick. Dice landing 1–3 drop, and at 0d the clock's end
  happens.
- Grimfall sizes pools 2d (short), 4d (medium) and 8d (long), with 6d between. The generator gives
  a clock as many dice as its die: a d4 clock is a 4d pool, a d6 one 6d, and d8 and d12 ones 8d.
- The two clocks that count the party's own progress (Evacuation, Isabel) become task pools.
- A clock whose ticks each do something (Glitch, Swamp, Isabel) does it as each die drops.
- Where the text walks a clock back (Fog), give the pool a die back:
  `didact do grow-pool pool=<it> by=1 most=6`. This is a ruling: Grimfall's pools only run down.
- When a pool other than a task pool refuses to budge, the GM can spend suspense to drop 1d:
  `didact do suspense spend=1 pool=<it>`. A task pool that drops nothing can be pushed:
  `didact do push who=<pc> pool=<it> stat=<stat>`.

**Radiation** (Chapter 6) is set dressing until the fiction says otherwise.

- A hot zone is +1t while you work in it, or a rad mark as you push through:
  `didact do rad who=<pc> dose=zone`, with `stat=` for the mark. Hot zones include the Glowing
  Zone, the Courier's Mile, the Divide and Far Harbor's Fog.
- A rad mark lingers until RadAway, a real rest or a perk sheds it.
- A bad dose is a condition: rad-sick or rad-poisoned.
- A lethal dose, like the three hundred rads in Project Purity's chamber, is an urgent 4d Lethal
  Dose (2d for a warhead's embrace), and it drops them at 0d. `didact do rad who=<pc>
  dose=lethal` (or `dose=warhead`) puts the timer on the sheet at once; roll it as time passes
  (`didact track roll <it>`).

**Loot** (Chapters 6 and 8). If a reward is in Grimfall's Armory, use its card (`grimfall.<id>`,
listed in the quest's and the vault's notes): an arcana, minor, major or mythic. Anything else is
a haul:

- minor: a working pistol, a sack of caps;
- major: a suit of combat armor, a caravan's cargo;
- mythic: a reactor, a water chip, a Vertibird.

Prices in caps are flavor: a few hundred caps is a minor haul, a few thousand a major one. Every
survivor's money is a 4d Caps pool.

**Factions** (Chapter 9). Reputation is standing: Idolized, Accepted, Neutral, Shunned or
Vilified.

- Each step a frame gives moves standing one step: `didact do standing who=<faction> shift=±1 why='…'`.
- Vilified starts a 6d They Find You campaign pool: the rule makes it at once and lists it on the
  faction.
- Karma is what the radio says about you. It decides whether Talon Company or the Regulators hold
  your warrant (Bounty Crews, Chapter 7).
- Run a frame's factions as faction pools, rolled between sessions and in downtime (Chapters 6
  and 9). `didact faction turn` rolls the pools each faction lists, and says how to make one for
  a goal. The setting's factions keep their agenda and obstacle as core's fields.

**Vaults** (Chapter 9) are 5-point sites. Place the reward first:

- The Door: the vault's entry.
- The Experiment: its Premise.
- The Twist: its Hidden note.
- The Confrontation: its Inhabitants.
- What Vault-Tec Left: its Reward.

**A frame's main line** can run as Grimfall's quest if you want one (Chapter 9): linked task pools
racing peril pools, with the plot beats as its links.

**Companions.** A cast member who becomes a companion is built per the Charmer's Inspirational
(Chapters 4 and 9): three tricks, two flaws. `didact gen run grimfall.companion --prefill
'{"name": "Dogmeat (companion)"}' --auto` drafts one; after `gen commit`, fold the cast record into
it with `didact merge npc:dogmeat companion:dogmeat-companion`.

## Ids, tags and where things are

- **Entries:**
  - the quest: `<frame>`;
  - its region: `<frame>-region`;
  - its places, cast, threats and clocks: `<frame>-<name>`;
  - the vaults: `vault-<n>`, and their stat-lined inhabitants `vault-<n>-<name>`;
  - the factions, by name (`compendium/factions.yaml`).
- **Tags** (what `compendium import --tag` brings in by):
  - a frame's entries carry its id, and one of `region`, `place`, `cast`, `threat` or `clock` (a
    threat who is also in the cast carries both);
  - the quest carries `frame`, and `main-campaign` or `side-arc`;
  - a vault carries `vault`, its catalog (`vaults-fallout-3`), and the frame whose places include
    it;
  - a vault's stat-lined inhabitant carries `vault`, the vault's id and `threat`;
  - a faction carries the frames it plays in.
- **Reference:**
  - each frame section: `<frame>-<section>` (`fallout-3-plot-beats`);
  - each threat: `<frame>-threats-<name>`;
  - each vault: `vault-<n>`;
  - the intros: `campaigns-…` and `vaults-…`.
- **Tables:**
  - `frames` and `vaults`, to pick one;
  - the lookups the two generators read;
  - `cloud-clock` and `vault-96-mutations`.

From Fallout 2e (CC BY-SA 4.0), a hack of Cairn Second Edition by Yochai Gal. This pack is shared
under the same license. The Grimfall cards it carries are Grimfall's, adapted from Grimwild by
J. D. Maxwell (CC BY 4.0) by way of Grimwild: Community Edition, and keep Grimfall's own terms:
play them at your table, change them, pass them on — just don't sell them.
