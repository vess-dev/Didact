# Cairn (Second Edition) in Didact

Cairn 2e by Yochai Gal (CC-BY-SA 4.0, cairnrpg.com): adventurers exploring a dark and
mysterious Wood. This pack holds the whole game: rules, tables, the bestiary, the marketplace,
spellbooks, relics, the seed procedures and character creation. `cairn-2e-vald` adds the
implied setting (calendar, holidays, faiths and factions).

## Running it

- **The Warden's principles are always in the brief.** Give information freely, telegraph
  danger, roll only when there's risk, and never kill without warning.
- **Saves:** `didact do save who=freya attr=DEX`. Opposed: whoever is most at risk rolls.
  Acting together: `didact do save-together who=freya partner=lucius attr=STR` (the lower
  attribute rolls).

### Fights

`didact combat start --party wolf`. In round one each PC saves DEX to act (a panicked PC
doesn't act), then sides alternate. `didact combat hit freya wolf weapon=d8` (or `didact do
attack attacker=freya target=wolf weapon=d8`) runs the whole chain:

- armor comes off the damage; HP to exactly 0 gives a PC a **scar**, applied at once;
- damage past 0 comes off STR and forces a critical damage save with the new STR. A PC who
  fails is `critical`: they can only crawl, and die within the hour unless stabilized. The
  attack sets a game-time reminder for that hour (`didact remind --list`); `didact do stabilize
  who=freya` saves them (then spend the bandages: `didact inv use <pc> Bandages`).
  An NPC who fails dies; a detachment is routed. A monster's own critical effect (its
  `critical` line) follows a failed save.
- STR 0 is death (a detachment: destroyed); DEX 0 paralysis, WIL 0 delirium.
- **Two weapons or several attackers** keep the single highest die: the book writes `d8+d8`,
  Didact writes `weapon='{d8, d8}kh1'` (`'{d8, d6, d4}kh1'` for three attackers). The bestiary
  and the gear already store them that way.
- `mode=impaired` (d4: cover, bound hands, a very distant target), `mode=enhanced` (d12: a
  helpless foe, a daring move), `mode=unarmed` (always d4). Impaired and enhanced attacks roll
  a d4 or d12 for each die the weapon combines (two d4s for twin daggers), keeping the highest
  (`dice=n` overrides the count). A **panicked** attacker is impaired on its own.
- A **helpless or unaware** target can't rely on HP: `direct=true` sends the damage (less
  armor) straight to STR.
- **Blast** hits everyone in the area, rolled per target (`blast=true` each time); unsure how
  many? `didact do blast-targets weapon=d8`.
- **Detachments** (`didact new detachment Bandits …`): an individual's attack on one is
  impaired unless it blasts; its attacks on individuals are enhanced. Explicit modes win.
- **Morale:** enemies save WIL at their first casualty and at half their number, lone foes at
  0 HP (the attack reminds you): `didact do morale who=bandits` (a group that uses its
  leader's WIL: `leader=<record>` or `wil=13`, as the Bandits' Loyal). Never for PCs.
- **Retreat:** `didact do retreat who=freya`: a DEX save, and only with somewhere safe to run.
- **A doomed PC** (scar 12): the next critical damage save kills on a failure; on a success
  the doom lifts and 3d6 goes against max HP.

### Scars

The attack runs `didact do scar who=<pc> lost=<n>` by itself: where, which limb or which
attribute is rolled, and the result applies. Rerolls take the new result only when it's higher
("if the total is higher than your max HP, take the new result"); a new max raises the current
score by as much (HP after a scar changes only its max: rest restores the rest). Wounds that
heal later become conditions: walloped, `broken-leg`/`arm`/`rib`/`skull`, diseased, hamstrung,
deafened, mortal-wound. When the fiction heals one: `didact do scar-heal who=freya
scar=broken-leg` (2d6 against max HP). A mortal wound kills in an hour unless stabilized (a
reminder is set for the hour).
`recover` heals walloped, hamstrung and a mortal wound by itself ("after recovery"). Every scar
is written on the sheet (`scars`). HP lost past 12 reads as 12 (Doomed): the book's table stops
there, since max HP can pass 12.

### Out of combat

- **Traps and falls** hurt attributes, not HP: `didact do attribute-damage target=freya
  attr=DEX amount=d6` (`armor=true` when armor helps). `didact do trap` (2-in-6 when unwitting).
- **Luck and people:** `didact do fate` (4+ favors the PCs), `didact do reaction who=<npc>`.
- **Fear:** `didact do panic who=…` (`alone=true` for a PC acting alone: bond 13's wounded
  beast keeps them from panicking), `didact do steady who=…` to overcome it.
- **Magic:** `didact do cast who=freya spell='Sniff'` adds the Fatigue (`danger=true`, or
  deprived: a WIL save; `enhance=true` with time and safety: more power at no cost;
  `scroll=true`: no Fatigue, and the scroll is used up with `inv use`).
- **Fatigue:** `didact do fatigue who=…` refuses when there's no free slot: drop an item
  first, as the book says, then add it.
- **Deprivation:** `didact do deprive who=freya need=food` once for each day the need goes
  unmet (the first day adds nothing, each later day a Fatigue; `days=3` counts three at once).
  A new day reminds you who's still deprived. `didact do relieve who=freya` when it's met.
- **Healing:** `didact do rest who=…` restores HP (never while deprived, panicked or carrying
  a full inventory; in a dungeon `turn=true`: it takes a turn, a light and a safe spot, and
  counts as lingering). `didact do stabilize who=…` saves the dying. `didact do recover
  who=… cost=50` is a week with a healer: attributes back, critical damage, paralysis and
  delirium over, and the "after recovery" scars healed.

### Dungeons and the wilderness

- **Dungeons:** `didact do dungeon-turn trigger=hurried` (an event when lingering, hurrying,
  entering new areas or making noise); light with `didact inv use freya torch`. A turn counts
  as ten minutes here (the book gives it no length: `time_units` in `pack.yaml`).
- **Forestcrawls:** the dungeon procedures with Wilderness Events instead: `didact do
  dungeon-turn trigger=new-area place=forest`; going off-trail always rolls one
  (`trigger=off-trail`).
- **Watches:** `didact do watch action=travel path=trail` (`shift=-1` makes getting lost a step
  less likely: a map, a guide, a Fletchwind scout; `shift=1` more), `action=supply helpers=1
  bonus=1` (bonus steps for experience or gear), `night=true` (two events), then `didact time
  advance 1 watch`.
- **Weather:** `didact do weather season=fall`. A new day reminds you (a calendar with
  spring, summer, fall and winter seasons rolls it by itself; Vald's rolls it too).
- **Travel time:** `didact do travel-time path=wilderness distance=long terrain=perilous
  weather=Extreme`, plus `vast=1|2` (especially vast terrain), `sleepless=true` (the terrain a
  step harder) and `bonus=n` (watches saved by mounts, guides or maps). One leg at a time for
  mixed terrain; waterways use the surrounding terrain.
- **Camp:** `didact do make-camp who=freya` (a Ration each, mounts too; Fatigue cleared, HP
  back; `interrupted=true` for a broken night). Skipping it: `didact do skip-camp who=freya` (a
  Fatigue and deprived of sleep).

### Inventory, coins and mounts

- 10 slots: `body` (4, what's carried comfortably) and the `backpack` (6); `inv add` fills the
  body first (`--to backpack` to stow, `didact inv move freya Rope backpack` later). Items made
  with the character have no group yet (Didact can't place them at creation): they count toward
  the ten all the same, as carried. Bulky 2, petty 0; Fatigue fills slots; a full inventory
  sets HP to 0.
- **Armor** counts only while worn or held, up to 3: armor stowed in the backpack doesn't
  (`didact inv move freya Shield backpack` takes a shield off; back to `body` to use it). Items
  not yet in a group count as carried.
- **Coins:** under 100gp is petty. More takes room by the `coin-weight` option (one slot, the
  default; `per-100`; `off`): `didact do coins who=freya` after the gold changes (the pack's
  own rules that spend gold run it).
- **Mounts and vehicles** are records of their own that carry their own load, outside their
  rider's ten slots: `didact spawn horse` (+4 slots), `mule` (+6, slow), `cart` (+4, bulky:
  pulled with both hands), `wagon` (+8, slow); then `didact inv add horse Rope`.
  `didact party add horse --as companion` brings one along.

### Downtime

`didact do downtime who=freya action=training goal='the two-handed parry' gold=20
milestones=<tracker>` pays a Milestone's Cost (`cost='a favor owed'` for one that isn't gold;
`abate=true` tries a WIL save to avoid it) and ticks the tracker. It refuses somewhere unsafe
(`safe=false`) or while in recovery (dying, stabilized, mortally wounded). Make the Milestones
first: `didact track new 'the two-handed parry' --kind track --size 3 --for freya`. When the
session ends, each PC is reminded of downtime and growth.

### Factions

Factions act on their own: `didact faction turn` rolls Faction Actions for each faction
(`didact do faction-action who=<faction> opposed=true` when another opposes it).

### Growth

Cairn has no XP: characters change from what happens to them. `didact char advance freya` (or
Advance on the character's page in the web app) drafts it step by step, and nothing changes
until `didact char commit c4`:

1. **What brings it:** a trigger in the fiction, a resolved bond or omen, or Downtime work.
   A trigger needs at least two of: a focused pattern of behavior, an obvious risk with serious
   consequences, a unique item, creature or entity. Fewer, and the draft stops ("Keep playing").
   Growth is the Warden's call, step by step: `--mode random` is refused for it.
2. **What happened**, in a sentence: it goes on the sheet (`growth`).
3. **The change:** `reroll` an attribute (3d6) or HP (d6, 2d6 or 3d6) and keep it if higher;
   `raise` one (by 1, d4, d6 or d8); or a new `ability`. A new max raises the current score by
   as much; attributes stop at 20 (a save of 20 always fails anyway).
4. **Its cost** (a flaw, a weakness, a new need), or none: it goes with the ability, or on the
   sheet as a flaw.

Answer any step up front: `didact char advance ox source=fiction pattern=yes risk=yes
unique=no trigger="Drank the murderer's spirit" how=reroll attr=WIL cost='a WIL save when a foe
is at his mercy'`, then `didact char commit c4`.

**Bonds and omens are threads** (`didact quest list`): character creation makes one for each
bond and omen. `didact do resolve-bond who=freya bond=<thread>` takes it off the sheet (a
lifted Stone Heart weighs nothing any more) and asks for growth: `didact char advance freya
source=bond`, where the Warden can also give a new bond (chosen or rolled, with its item and
its own thread on commit). `didact do resolve-omen omen=<thread>
who=<pc>` (or no `who`: the party as a whole). For a character made before this, make its
thread first: `didact quest new "Bond: Stone Heart" --type thread --goal "<the bond's text>"`.

**Scars** are growth without a trigger: the attack applies them (above).

Bond effects the pack runs: the Mischievous Spirit (bond 10) absorbs a Fatigue each new day; the
Stone Heart (bond 15) is the `burden` counter, a slot more each month of the calendar (Vald's,
or your world's own); the core rules have no months, so without them a month is 30 days. The
wounded beast (bond 13) stops panic when acting alone.

## Making things

- **Characters:** `didact char new` (guided) or `--mode random`. Every background result
  applies: a second bond (a Fieldwarden, an Outrider who pays their debts), a private omen (a
  Foundling, a Mountebank's true prophecy: a secret thread), +d4 HP, gear bought from the
  Marketplace (a Kettlewright's 20gp, a Rill Runner's single item), and the companions and
  vehicles some bring (an Outrider's horse, a falcon, a familiar, a hollow wolf, a homunculus, a
  werewolf form, a donkey, a burial wagon) as records beside the character. The party's youngest
  rolls an omen (the draft asks; in random mode prefill it: `--prefill '{"youngest": "no"}'`).
  Prefill what the player already chose: `--prefill '{"background": "Cutpurse", "name": "Ivy"}'`.
- **Hirelings:** `didact char new hireling` (a role and its wage, attributes, HP, all eight
  traits) or `didact char new hireling-background` (the book's other way: a background, its
  tables, Rations, gold, attributes, HP and age).
- **People:** `didact gen run cairn-2e.npc` (the NPC tables: background, goal, quirk, virtue,
  vice, a reaction and a name) and `cairn-2e.faction` (type, agent, traits, advantages,
  agenda and obstacle).
- **Monsters and gear:** `didact compendium find wolf`, `didact spawn wolf`. A new monster:
  describe it and write it (`didact template monster` has the guidance), or roll prompts with
  `didact gen run cairn-2e.monster`. From the book's lists: `cairn-2e.weapon`, `cairn-2e.armor`
  and `cairn-2e.gear` (the Marketplace), `cairn-2e.relic` (the Reliquary) and
  `cairn-2e.spellbook`.
- **Places** (drafts first; `gen show`, `gen edit`, then `gen commit` writes them with the map):
  - `didact gen run cairn-2e.realm`: a realm's rule and name, for its regions to join.
  - `didact gen run cairn-2e.setting-seed`: a region with terrain, landmarks, the Heart and
    its points of interest, factions, and paths with watches (Unusual Weather around each
    terrain with the `unusual-weather` option: `didact campaign profile unusual-weather=on`).
  - `didact gen run cairn-2e.pointcrawl region=loc:<place>`: one stretch of terrain with its
    points of interest and 1–4 paths from each.
  - `didact gen run cairn-2e.point-of-interest region=loc:<place>`: a single point of interest.
  - `didact gen run cairn-2e.forest-seed region=loc:<place>`: a forestcrawl from an entrance
    to an exit, with trails.
  - `didact gen run cairn-2e.dungeon-seed region=loc:<place>`: a dungeon's history, denizens,
    factions and rooms numbered from the entrance.

  Without `--auto`, a draft asks at each choice the book leaves to the Warden (a background, the
  Heart, Waypoint or Settlement): answer it, or let the dice decide. The web app runs every one
  of these step by step. Hidden paths stay off the players' map until found.
- **Names:** `didact name npc`, `didact name place`, `didact name faction`, `didact name poi`.

## Readings where the book is silent

- **Attributes stop at 20:** growth and scars can raise one past 18; a save of 20 fails anyway.
- **A reroll's new max** raises the current score by the same amount (a full score stays full, a
  damaged one stays damaged); HP from a scar changes only its max.
- **HP lost past 12** reads as scar 12 (Doomed).
- **Direct damage** to a helpless or unaware target still loses the target's armor first.
- **Deprivation** counts days one call at a time: each day past the first adds a Fatigue.
- **Coins of 100gp or more** take one slot unless the `coin-weight` option says otherwise.
- **A turn** is ten minutes; **a month** (the Stone Heart) is the calendar's, or 30 days when
  it has none (a skip past several months counts the ones before the last as 30 days each).
- **A background hireling's Rations** are one ration pack (3 uses), like every background's.
- **The Marketplace** has no die: every item, role or transport is equally likely.

## Credits

Cairn Second Edition is by Yochai Gal, with Adam Hensley and Derek B.; the text is used under
CC-BY-SA 4.0. This pack is shared under the same license.
