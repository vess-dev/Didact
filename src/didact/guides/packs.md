# Packs

A pack is a game system, oracle, setting, adventure or supplement, written as YAML files plus an optional Python plugin. This guide shows how to write one: turning a rulebook into a pack, or adding house content.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

A pack can also be made from what's in your library. `didact pack new my-brew --from-overlay my-system` turns your homebrew for a system (`compendium add`, records kept `--scope system`, lore) into a supplement, and `didact world export --as setting` turns a world into a setting pack: its people, places and lore as compendium entries and pack lore, brought into another world with `compendium import`. Both leave out secrets and the GM's notes unless `--secrets`, and neither is marked shareable until you set its licence.

## Layout

```
my-hack/
  pack.yaml        id, name, kind, version, requires, extends, license, plugins, settings
  GUIDE.md         how to run it: an LLM reads this first
  dice.yaml        named dice, macros, dice chains
  schemas/         record types and their fields (sheets)
  tables/          random and lookup tables, decks, bags
  rules/           checks, actions, procedures, triggers
  compendium/      monsters, items, spells, backgrounds…
  reference/       the rules text, one short section per file (Markdown)
  glossary.yaml    terms and definitions
  tests/           examples `pack test` runs
  plugins/         Python, for what YAML can't express (off until trusted)
```

A file holds one item, a list of items, or several items separated by `---`. Every item names its id with its kind's key: `table: weather`, `check: save`, `type: pc`, or `id: troll` for compendium entries. Refer to items as `pack.id` (`my-system.save`), or by bare id when only one enabled pack has it.

```yaml
# pack.yaml
id: my-hack
name: My Hack
kind: system                 # system | oracle | supplement | setting | adventure
version: 0.1.0
alias: hack                  # the name in expressions: hack.attack(d8, d8)
requires: {didact: ">=0.1", packs: [core]}
extends: []                  # for a hack: [my-system]; same-id items replace the base's
license: {spdx: CC-BY-SA-4.0, redistributable: true, attribution: "…"}
settings: {torch_uses: 3}    # rules read these as @settings.torch_uses
```

A hack names its base in `extends` and holds only what differs:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Its item with the same id replaces the base's, whatever the kind (a table, a rule, a compendium entry, a reference section, a glossary term). Its `settings` go on top of the base's, key by key: a key it sets replaces the base's value whole (its `names` tables stand in for the base's), and the base's rules read the hack's values too. `hides` drops what is left that the hack has no use for: `*` matches any run of characters, the last pattern that matches an id decides, and one that starts with `!` keeps the item. What the hack replaces is never hidden. The kinds are `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` and `term`. `didact pack validate` warns about a pattern that matches nothing.

## Expressions

Every condition and formula uses the dice language (`didact guide dice`), plus:
- **Values:** `@name` reads a value: `@roll`, `@who.STR`, `@settings.x`. `$name` pastes a parameter's text first, so `@who.$attr` becomes `@who.STR`. Read a parameter of free text as `@name`, not quoted (`'$name'`): an apostrophe in its text would end the quotes (`pack validate` warns).
- **Logic:** `and`, `or`, `not`, and `in` (`'deprived' in @who.conditions`).
- **Literals:** text (`'travel'`) and `true`/`false`.
- **Functions:** `if(cond, a, b)` rolls only the branch it takes. `default(@thread.flashpoint, 0)` is the value, or the fallback when it isn't set. `sum`, `count` (`count(@roll.dice, 6)` counts the sixes), `min`, `max`, `any` and `all` take lists.

## Sheets: `schemas/`

```yaml
type: character
fields:
  STR: {kind: stat, range: [0, 18], roll: 3d6, on_zero: {trigger: death}}
  hp: {kind: resource, min: 0, roll: d6}
  armor: {kind: derived, expr: "min(3, sum(@inventory.armor))"}
  inventory: {kind: slots, capacity: 10, sizes: {petty: 0, normal: 1, bulky: 2},
              when_full: {set: {hp: 0}}}
  fatigue: {kind: counter, min: 0, occupies: inventory}
guidance: "3 HP is an average monster, 6 a hardy one, 10+ a serious threat."
---
type: pc
extends: character
```

| Kind | Holds | Options |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | a plain value | min, max; `values` for enum |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: `@hp` is the value, `@hp.max` the cap | range; min; max or max_field; die |
| `counter` | a number | min, max, thresholds, occupies (a slots field) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | items (`Rope` or `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | as named | `to` (for refs), `allowed` |
| `derived` | computed, never stored | expr |

Every field also takes `label`, `help`, `default`, `required` and `roll`: `new pc Hero --fill`, or a value of `"roll"`, rolls it through the log. Types from the `core` pack hold system-agnostic prose in `fields`. A system's types hold its numbers in `mechanics.<system>`. `set hero hp-=2` finds the field, clamps it, and reports any overflow. `+=` adds to a list: a `list` (like `slots`) keeps a value added again, `tags`, `conditions` and `refs` hold it once, and `-=` takes every copy off.

**Hooks** say what happens when a value crosses a line. They fire on every change (`set`, `inv`, a rule's `set` step), but only when the line is crossed: 3 → 0 fires, 0 → 0 doesn't. `--force` edits skip them.

| Hook | Fires when |
|---|---|
| `on_zero` | a number or `{value}` reaches 0 |
| `on_full` (`when_full` on slots) | it reaches its max, size or capacity |
| `thresholds: {10: …, 20: …}` (counters) | it climbs past each mark |

An action is text (a note for the LLM), `{set: {hp: 0}}` or `{condition: paralyzed}` on the same record, `{trigger: death}` (runs that rule with `who` = the record), or a list of these.

**Inventory** (`didact inv …`) works on the sheet's `slots` field:
- **Room:** items take their `size` × `count`, and counters that `occupies` the field take their value. Past `capacity` is refused unless `--force`.
- **Groups:** `groups: {backpack: 6, body: 4}` gives each group its own room, and its own columns and totals: `@inventory.body.armor` is only what's worn or held, `@inventory.body.free` its room left.
- **Uses:** `uses: 3` counts down with `inv use`. `uses: d8` is a usage die: 1–2 steps it down. A used-up item is gone unless it has `recharge` or `keep: true`. Of several items of one name, the name means the first; to spend a use (`inv use`, a rule's `use:`, `set …uses-=1`), the first with a use left.
- **An item's own keys:** `didact set freya inventory.sword.damage=d10` (a rule's `set: who.inventory.$item.damage` too) changes one, the item named as `inv` names it, by a part of its name or all of it, spaces and dots too (`'inventory.12.7mm pistol.damage=d10'`, quoted for the shell); `uses` and `charges` count like a `uses` field (`charges+=2` stops at its max), and the room is checked as `inv add` checks it. A rule reads one as `@{who.inventory.$item.damage}` (a usage die as its die, uses as their count); an item or a key that isn't there reads as absent, so `default(…)` gives its fallback.
- **Compendium:** entries of type `item` (or weapon, armor, relic, …, or a type of the pack's own that `extends` one) lend `inv add` their details, found by id, by name or by an alias (two that share one: name it as `pack.id`); any other name, `:` and all, is the item's own.

## Tables: `tables/`

```yaml
table: weather
dice: d6                     # any expression: 2d6, d66, d100, d20 + @corruption
clamp: true                  # a total past the ends uses the first or last entry
entries:
  1-2: Clear
  3-4: {text: Rain, data: {travel: slow}}
  5: {text: Storm, then: [{table: lightning}]}
  6: {text: Two fronts, roll: 2}
refs: {noun: nouns}          # "{noun}" in a text rolls on table nouns; "{1d4}" rolls dice
source: "Core Rules p. 12"
```

Other shapes:
- **Weighted lists:** `entries` as a list, with `weight:` per entry.
- **Columns:** `columns: [a, b]` rolls each column of a row separately. A plain entry (not a list) fills every column, so `columns: [first, second]` over a word list means "roll twice on this list". `labels: false` leaves the column names out of the result ("Abandon · Advantage"), and `read: "It's a {first} {second} with {third} {fourth} inside."` reads the columns into a sentence.
- **Lookups:** `lookup: hp_lost`, or `[odds, chaos]` for a 2-D chart.
- **Duplicates:** `duplicates: reroll | keep | make_it_worse` for "roll twice".
- **Two steps:** an entry that rolls another table (`{table: lightning}` instead, or `then:` after it) brings that roll's data along: a rule or a draft that rolls it reads both, the entry's own keys first, then those of the first table rolled next. A `--prefill` can name an entry further down, at any depth (`Ring of the Hunt`), with the data of every entry on the way: of two of a name the nearer is meant (then the first), one that goes on rolls on from there, and one close to any of them but none is refused, naming the nearest. A guided draft offers the first step when its entries say what they are (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): choosing one rolls the next table, as a roll landing on it does.
- **Read both ways:** `both_ways: true` on a d66 table adds the other reading: 31 also gives 13, and the reader picks.
- **What an entry means:** `about: "Knows: {skills}. Also known as: {aka}."` fills in each entry's data (a list reads `a, b`; `{text}` is the entry itself) to say what it gives when a choice offers it; an entry's own `note:` says it instead. Without either, an entry whose data has an `id` naming a compendium entry is described by that entry.
- **Decks and bags:** `deck: tarot` with `cards` (or `standard: true`); `bag: initiative` with `tokens`.

Validation checks that every result the dice can roll lands on an entry.

## Rules: `rules/`

```yaml
check: save
params: {who: ref, attr: {enum: [STR, DEX, WIL]}}
prompt: State the risk before rolling.
before: [{table: chart, with: {odds: $odds}, as: cell}]   # optional: steps first (a `roll` step can replace `roll:`)
roll: d20                              # or several: {action: "d6 + @stat", challenge: 2d10}
success: "@roll <= @who.$attr"         # or bands: {strong: "@roll >= 10", weak: "@roll >= 7", miss: else}
auto: {1: success, 20: failure}        # natural rolls
flags: {crit: "count(@roll.dice, 6) >= 2"}
on: {failure: ["The risk comes true."]}
options:                               # the roll comes back pending: `didact resolve r12 push`
  push: {label: "Push", steps: [{reroll: roll, keep_if: "@face == 6"}]}
```

Actions and procedures are step lists, and triggers are steps with a `when:` guard. The steps are:

| Step | Does |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | a logged roll; binds `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`; a `{…}` is filled in first, as in any text, so dice a value holds as text roll (`{@{who.inventory.$item.damage}}`), the log showing them: a value that isn't dice is refused, and so is `roll: "@die"` of such text, which rolls nothing; a set of rolls (`{d8, d6}kh1`) stays one |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | computes values; like `set`'s `value`, `{…}` text is a template and a bare word is text; in any text filled in, `{{` and `}}` write a brace itself |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (or `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | changes a record: validated, clamped, undoable; `set: who.$attr` sets the field a parameter names, and `set: who.inventory.$item.damage` a key of an item it carries (see Inventory); `-=` takes a value off a list, and one it doesn't hold changes nothing (a note says so; one it could never hold is refused); `unset:` takes a field off, as `set --unset` does |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | hands a record an item or takes one from it, as `inv add` and `inv drop` do: its details from the compendium, a unique part of its name will do, and the room and the field's hooks are checked |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | uses a carried item as `inv use` does: uses or charges count down, a usage die rolls and steps down on 1–2, and one that runs out is gone unless it recharges or is kept; of several of that name, the first with a use left; binds `@torch.out` (its last use went), `@torch.gone` (none of it is left), `@torch.left`, `@torch.die` and `@torch.rolled` (`as:` defaults to `use`) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | makes a record at once, described as a draft's `entity` is (below) and checked against its sheet; `as:` (else its `key`, else its type) binds it as a record, read and set like a `ref` parameter (`pool: "@bleeding"`, `@bleeding.name`), and is never a parameter's name; without a `key:` no field is taken for one (`kind: track` stays as written); one of that type and name already here is taken as it is, so a rule run again makes nothing new |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | runs a check and binds its outcome |
| `do: other-action`, `with: {…}`, `as: trip` | runs another rule; `@trip` is its outcome and `@trip.<name>` what it bound (`@trip.found` for its `let: {found: 2}`, `@trip.luck` for its `roll: d6`, `as: luck`); `as:` defaults to its id |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | a logged table roll; binds the text and the entry's `data` (`@scar.<key>`, and a mapping's keys by their path: `@scar.cost.hp`), with that of any table it rolls next; a list of items (`[Rope, {name: Laser, damage: d8}]`) reads as their names (`count(@scar.gear)`, `'Laser' in @scar.gear`), and handed to a step as it is (`apply: "@scar.gear"`) it is the items themselves; a list of other mappings is for a step to read |
| `table: "setting-{@drop.difficulty}-terrain"` | a computed table: `{…}` and `$param` fill in |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | several results as a list (`distinct` rerolls repeats) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | branches |
| `repeat: "@count"`, `as: i`, `steps: […]` | a loop: the steps that many times, `@i` counting from 1 |
| `for: pcs` (or `party`), `as: member`, `steps: […]` | the steps once for each player character (or party member), as `@member`: a record, like the one `entity:` binds (`@member.name`, `set: member.fatigue`); `as:` never takes a parameter's name, so the rule's own `who` stays its own |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | output for the LLM |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (or `every: 1 day`) | a reminder that comes due as game time passes, as `didact remind` sets |
| `reroll: roll`, `keep_if: "@face == 6"` | rerolls some of a roll's dice (push mechanics) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | rolls on a list value (an oracle's lists): binds the entry, `@who.choose` (a blank line) and `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | rolls a tracker's diminishing pool as `track roll` does (1-3s drop; `drop` dice go first, `extra` dice roll along), or only drops dice (`mode: drop`: a push, a tick); linked phases and the pool's event follow; binds `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

A check's outcome is readable by the rule that ran it (`check: … as: answer` gives `@answer`), and so are its flags: `'random-event' in @answer.flags`. `with:` values are evaluated when they hold `@`, filled in when they hold `$param` or `{…}` ("Does $npc flee?"), and passed as written otherwise. A rule with an `oracle` parameter gets the campaign oracle's state record without being told. A `ref` parameter with `to: monster` takes a record of that type: a name another record shares (a foe's pool, named as its card) is the one of that type.

Triggers run by themselves when their event happens, and only if their `when:` holds:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Any rule (a generator and character creation too) can read `@system` (the id of the system the world plays, so a setting written for two systems tells them apart), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` and `@time.is_night`, and with a calendar of months `@time.month`, `@time.month_name`, `@time.day_of_month` and `@time.year`; while a fight is on, `@combat.round` and `@combat.fighters` (the ids of those in it). A time trigger can also read `@time.passed`, the seconds just advanced, a `combat_start` or `combat_end` trigger reads the fight that starts or ends (`combat start` and `combat end` run them; a fighter leaving doesn't end the fight), and a rule a trigger runs reads what the trigger reads. A trigger with required parameters is only run by `didact do` or a field hook (`who` = the record). `on: manual` triggers run only when called. `for: pcs` (or `party`) runs a trigger once for each player character (or party member), as `who`: experience after each session, say. A trigger that fails stops the command that fired it, and says which trigger it was and how to go on without it (`didact override add trigger <id> --data '{"on": "manual"}'`).

The calendar is in a pack's `settings`: a setting pack's wins over the system's, and a world's own (`calendar:` in its `world.yaml`) over both:

```yaml
settings:
  watches: [morning, afternoon, night]   # the day's watches
  calendar:
    week: [Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday]
    months: [{name: January, days: 31}, {name: February, days: 28, leap: [4, 100, 400]}, …]
    start: {year: 1890, month: 3, day: 14, weekday: Friday}   # where a campaign opens
    year: "{year} AD"                     # how a date writes its year
    seasons: [{name: spring, month: 3, day: 20}, …]           # each from its first day
    holidays: [{name: Midsummer, month: 6, day: 24, text: "…"}]
```

`leap: 4` makes a month a day longer every 4th year, and `leap: [4, 100, 400]` every 4th, but not every 100th, but every 400th: each number overrules the one before. `weekday` names the start's day of the week (else it's the week's first), and `year` is how a date writes its year, in those Didact shows and those it reads (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` checks all three. A campaign can open on another date of the calendar, before its start or after: `didact campaign new <id> --date '4 July 1902'`, or `didact time set '<date>'` until its first session. A day of the week written before the date is checked: the date decides, and a note says when it falls on another.

Options are the system's variant and optional rules, chosen for each campaign at session zero:

```yaml
option: lethality                       # rules read it as @option.lethality
ask: How deadly should it be?           # session zero asks it (in place of Didact's own of that key)
choices: {gentle: "…", standard: "As the book has it.", deadly: "…"}   # each with what it means
default: standard
---
option: supplies                        # a flag: on or off (@option.supplies is true or false)
kind: flag
ask: Can the PCs run out of supplies?
help: Each PC has a 4d Supplies pool.
---
option: flavor
choices: {heroic: "…", grimdark: "…"}
implies: {grimdark: {lethality: deadly, supplies: true}}   # a choice that sets others (a flag's: on)
```

`didact campaign profile lethality=deadly supplies=on` saves them (or the web app's Settings page). Rules, character creation and generators read them (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` for `rest-resets`): an answer wins over what another option implies, which wins over the default. What an option implies is followed all the way (a flavor that sets the lethality also sets what that lethality implies), and of two implications the nearer one wins. The brief lists those that differ from their default, with what they mean, for the GM to apply what the rules can't. A generator that can't run under them `stop:`s with the reason, and nothing is drafted.

## Oracles: `oracles/`

```yaml
oracle: chart
title: Chart oracle
ask: chart-question          # the check that answers; it may take question, odds and oracle
odds: [unlikely, 50-50, likely]
meaning: [actions, descriptions]   # tables for `didact meaning` (a word from each)
state: {chaos: {start: 5, min: 1, max: 9}}  # kept per campaign; rules read @oracle.chaos
lists: {names: [threads, characters], method: sections}   # weighted lists (`didact lists`)
prompt: Interpret the answer in the fiction.
```

- **Asking:** `didact ask '…' --odds likely` runs the `ask` check. The answer is its outcome (a band), and its flags ride along.
- **State:** it lives in a record the check receives as `oracle`. A check changes it with `set: oracle.chaos += 1`.
- **Lists:** `lists: {names: […], method: sections, most: 3}` keeps weighted lists on that record. `didact lists add|drop|roll|show` manage them, and rules roll them with `pick`. `sections` rolls for a section of five lines, then a line in it (a blank line means choose); `uniform` gives every line the same chance.
- **More for the check:** `didact ask '…' --with as_rule=true` passes extra parameters to the oracle's check.
- **The log:** every answer is numbered (`#o12`) and logged, and `didact interpret o12 '…'` keeps what it meant. The core pack's `yes-no` oracle is the fallback.

## Generators and character creation: `generators/`, `chargen/`

Both are procedures that build a **draft**. They use every rule step (`roll`, `table`, `if`, `let`, `prompt`, …) plus these:

| Step | Does |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | adds a record to the draft (keys `poi-1`, `poi-2`, …); a field or a link naming a key the pack wrote (`key:`, or an `as:` name) becomes that record's id on commit, so pick keys no field holds as text (an entity with neither has none to swap); `from: "@relic.id"` starts it from a compendium entry (its type, name and fields) |
| `choose: {from: [a, b], as: x}` (or `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | a choice; in guided mode the draft waits for `choose`; `exclude` rules out earlier picks (a rolled one is rolled again); `records:` adds the records of that type here, by id (made in play); `answer:` makes the choice when its value is one of the options (a character's own path), without asking |
| `choose_or_roll: {table: backgrounds, as: background}` | a choice the dice can make; a chosen entry's data is `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | rolls into the character |
| `swap: {among: [STR, DEX, WIL], optional: true}` | swap two scores, or keep |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | spread a fixed array |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | buy scores within a budget (`default: random` spends it at random in random mode) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | a list goes to the inventory; a mapping sets fields (lists add up) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | adds to a field of the character (or of a drafted entity): numbers add up, anything else joins a list; nothing to add is fine |
| `remove: {field: talents, value: "@old"}` | takes something off a list field (a talent switched out, a bond resolved); nothing there is fine |
| `roll_tables: [physique, vice]` | rolls tables into `traits`; an entry's `data.gear` goes to the inventory and `data.add: {gold: 20}` adds to fields |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | the name; `name: {prompt: …}` with nothing to roll from waits for one, even in random mode |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | a question any answer will do (a goal, another record's name): the draft waits for it, even in random mode, unless it's prefilled; `field:` stores the answer |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | a pointcrawl: a logged die drop, paths (always connected), distances, hidden paths (see below) |

The map step takes more, for the book's die-drop procedures:

| Key | Does |
|---|---|
| `regions: terrain` | these entities drop too; each place joins the nearest one (its `region`) |
| `hidden: 6`, `conditional: 5` | a d6 per path: at or over the number, a hidden or conditional path (hidden paths stay off the players' map) |
| `describe: [path-feature, path-condition]` | tables rolled for each path, kept as its `details` |
| `entrance: true`, `exit: true` | the place nearest the edge is the entrance; the rest are numbered from it along the paths (`map.n`), paths lead away from it, and the exit is a far place near an edge, numbered last |
| `number: "{@dungeon_name}, room {@n}"` | renames the numbered places (their draft keys follow: `room-1` is room 1) |

A die-drop table can name the next tables in its entries' data, so the procedure reads like the book: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, then `table: "{@drop.what}"`. Unset list fields (conditions, lists, tags) read as empty lists, so `'deprived' in @who.conditions` works from the start.

```yaml
chargen: pc
creates: pc
modes: [random, guided]
steps:
  - choose_or_roll: {table: backgrounds, as: background, field: background}
  - apply: "@background.gear"
  - roll: {each: [STR, DEX, WIL], dice: 3d6}
  - swap: {among: [STR, DEX, WIL], optional: true}
  - name: {from: "@background.names"}
```

A chargen with `advances:` changes a record instead of making one: the system's level-up.

```yaml
chargen: level-up
advances: pc                   # `didact char advance <pc>`, or Level up on its page
params: {who: ref}
steps:
  - if: "@who.xp < @who.level + 1"
    then: [stop: "{@who.name} needs more XP"]
  - apply: {level: "{@who.level + 1}", xp: "{@who.xp - @who.level - 1}"}
  - choose: {table: paths, as: path, answer: "@who.path"}     # the character's own: not asked
  - choose: {from: "@path.talents", records: talent, as: talent, exclude: "@character.talents"}
  - add: {field: talents, value: "@talent"}
```

- **One record:** a generator with `creates: npc` builds that record as character creation builds a character (`apply`, `add`, `name`, `field:`); its `entity` steps add records beside it, and a link `to: character` points at it.
- **Running:** `gen run` and `char new` make a draft (`#g7`, `#c3`) and write nothing. A `stop:` ends one with nothing drafted: under an `if:` that reads a campaign option, its hint points at the options (`didact session zero`); otherwise its own words say what to do instead.
- **Deciding:** `--prefill '{…}'` decides things in advance, by the name a step binds (`as:`): a single value answers every occurrence, a list one occurrence each (a list for `choose` with `count` is the whole pick). `let` values can be prefilled too (`{"hp": 6}`), and a name, an `ask` or a `let` keeps any text as given. A value for a choice among known options (a `choose`, a table's entry) is the option it names, as written or in another letter case, by its entry's `id`, or by a roll that lands on it (`{"group": 3}`), and brings that entry's data; one close to an option but none of them is refused, naming the nearest, and any other is an answer of one's own, without data. `--auto` (or `char new --mode random`) lets the dice decide the rest. Otherwise the draft waits at each choice.
- **Describing:** a choice says what each option means, for the player choosing: a table entry's `note:` or its table's `about:`, else the compendium entry it names (its data's `id`), or the one the option is (a choice among compendium ids shows each one's name): its `tagline` and `summary`, its `description` or `effect`, else its text's first paragraph.
- **Going back:** `char back` (or `gen back`) takes the last answer, roll or edit back, so the draft asks that question again; the rolls it made are marked undone.
- **Resuming:** a resumed draft replays its trail: every value rolled or chosen, each used once and in order (the map's die drop too), so nothing is rolled twice and nothing already decided changes.
- **Writing:** `commit` writes the records, checked against their sheets.
- **Advancing:** an `advances:` draft starts from a copy of the record (with its sheet's defaults), its steps read the record as `@who` and the draft's values as `@character.*`, and `commit` writes only what changed, checked like `set`; records its `entity` steps make (a new bond's thread) are created beside it: a link `to: character` points at the record, and a field naming a key holds that record's id, as when a character is made (`apply: {blood: "@pool"}`). A `stop:` says why not yet (not enough XP), and nothing is drafted. A system whose growth is a single rule names it on its chargen instead: `advance: {rule: grow}`.
- **Modes:** `modes: [guided]` keeps a procedure step by step: `--mode random` is refused.

## Compendium, reference and glossary

- **Compendium entries** are written like `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. A value of `"roll 2d8"` rolls when the entry spawns. Run `didact spawn troll`, or bring a pack's entries into the world with `didact compendium import <pack>` (`--type loc`, and `--tag coast` for those with every tag given).
- **For several systems:** a top-level key goes where `set` puts it, into the system's block when its sheet has that field, else into `fields`. An entry a setting writes for more than one system gives each one's numbers in its own block (`mechanics: {my-system: {hp: 12}}`): `pack validate` checks each against that system's sheet when it's installed, and notes a top-level key that sheet and core's both have. What a block says stands: beside `mechanics: {my-system: {role: tactician}}`, a top-level `role: innkeeper` is core's field, as anything under `fields:` is. A block naming the pack being validated is checked against that pack as it is in its folder.
- **Reference sections** go in `reference/*.md`, with front matter (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` finds them; a quoted phrase that isn't there is tried as its words.
- **The glossary** is `glossary.yaml`: `term: definition`, or a list of `{term, definition, aliases, see}`. `didact define <term>` reads it.

## Tests: `tests/`

```yaml
test: weather-lands     # roll a table many times: every roll must land
table: weather
times: 50
---
test: fair-save         # exact odds
odds: "d20 <= 10"
chance: 0.5
---
test: every-table       # each of the pack's tables (a lookup table once per key)
table: all
---
test: play              # a smoke-play script: real commands in a scratch library
script:
  - world new t --system {pack} --seed smoke    # seeded: it plays the same every time
  - new pc Hero --fill
  - run: do save who=hero attr=STR
    expect: "→"                                  # text the step must print (or a list)
  - run: table list
    expect_not: my-system.spell-fire             # text it must not print (or a list)
  - run: table roll my-system.spell-fire
    fails: true                                  # it must fail (`expect` reads its error too)
```

## Sharing and removing packs

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- A pack that declares `redistributable: false` can't be exported.
- **core** is part of Didact and always on: every system builds on it, so it can't be disabled or uninstalled.
- The other packs that ship with Didact are `.didactpack` files in its `packs/` folder. `pack list` shows them until they're installed, and installing one brings the packs it needs that ship too.
- `pack update` looks for newer versions in Didact's `packs/` folder and on GitHub (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` names another place, or nothing not to look). A new version installs beside the old one: campaigns keep theirs until `didact campaign upgrade`.
- One game system is in use at a time: the open world's. A world keeps the system it was made with (`didact world new <id> --system <pack>`; one made without a system takes the first it's given, with `pack enable` or `world set system=`), its campaigns play it, and a pack that needs another system (a setting written for it) can't be added: another system plays in a world of its own.
- `uninstall` refuses while a world or campaign uses the pack's only copy (`--force` removes it anyway). It can't be undone: install the .didactpack again.

## From rulebook to pack: the checklist

Go through the book's mechanics in this order. Each one maps onto something above:

1. **Resolution:** how a roll succeeds (a check: `success`, `bands`, `auto`).
2. **Dice:** unusual dice, symbols, steps (`dice.yaml`, named dice, chains).
3. **The sheet:** attributes, derived numbers (`schemas/`, derived fields).
4. **Resources:** HP, luck, momentum (resource and counter fields; `set` steps).
5. **Conditions:** states and what they do (`conditions` fields; `if` steps).
6. **Combat:** attacks, damage, initiative (actions; `bag`/`deck` for turn order).
7. **Procedures:** exploration, travel, downtime (procedures with prompts).
8. **Tables:** every random table (`tables/`; `pack import` for Markdown tables).
9. **The bestiary:** monsters and NPCs (`compendium/`).
10. **Items:** gear, spells, relics (`compendium/`, slots fields).
11. **GM guidance:** principles and advice (`GUIDE.md`, `reference/`, `guidance:` on types).
12. **Character creation:** how to make a character (a `chargen/` procedure, or `roll:` on each field).

Cite pages with `source:` everywhere, so gaps show up. Add a smoke-play test that makes a character, rolls a check, fights, and runs a procedure.
