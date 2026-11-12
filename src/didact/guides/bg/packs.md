<!-- translated from b1dfa1159ff4 -->
# Пакети

Пакетът е игрова система, оракул, сетинг, приключение или допълнение, написано като YAML файлове плюс незадължителен плъгин на Python. Това ръководство показва как се пише пакет: превръщане на книга с правила в пакет или добавяне на собствено съдържание.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Пакет може да се направи и от това, което е в библиотеката ви. `didact pack new my-brew --from-overlay my-system` превръща домашното ви съдържание за дадена система (`compendium add`, записи, водени с `--scope system`, лор) в допълнение, а `didact world export --as setting` превръща свят в пакет със сетинг: хората, местата и лора му като записи от компендиума и лор на пакета, които `compendium import` внася в друг свят. И двете пропускат тайните и бележките на водещия, освен с `--secrets`, и никое не е отбелязано като споделимо, докато не зададете лиценза му.

## Структура

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

Един файл съдържа един елемент, списък от елементи или няколко елемента, разделени с `---`. Всеки елемент посочва ID-то си с ключа на своя вид: `table: weather`, `check: save`, `type: pc` или `id: troll` за записи в компендиума. Препращайте към елементи като `pack.id` (`my-system.save`) или само с ID, когато го има само един включен пакет.

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

Един хак посочва основата си в `extends` и съдържа само това, което се различава:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Негов елемент със същото ID заменя този на основата, независимо от вида (таблица, правило, запис от компендиума, справочен раздел, термин от речника). Неговите `settings` се наслагват върху тези на основата ключ по ключ: ключ, който хакът задава, заменя изцяло стойността на основата (неговите таблици `names` заместват тези на основата), а правилата на основата също четат стойностите на хака. `hides` премахва останалото, което не е нужно на хака: `*` съвпада с произволна поредица от знаци, решава последният шаблон, който съвпада с дадено ID, а шаблон, започващ с `!`, запазва елемента. Това, което хакът заменя, никога не се скрива. Видовете са `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` и `term`. `didact pack validate` предупреждава за шаблон, който не съвпада с нищо.

## Изрази

Всяко условие и формула използват езика на заровете (`didact guide dice`), плюс:
- **Стойности:** `@name` чете стойност: `@roll`, `@who.STR`, `@settings.x`. `$name` първо вмъква текста на параметър, така че `@who.$attr` става `@who.STR`. Параметър със свободен текст четете като `@name`, не в кавички (`'$name'`): апостроф в текста му би затворил кавичките (`pack validate` предупреждава).
- **Логика:** `and`, `or`, `not` и `in` (`'deprived' in @who.conditions`).
- **Литерали:** текст (`'travel'`) и `true`/`false`.
- **Функции:** `if(cond, a, b)` хвърля само клона, който избере. `default(@thread.flashpoint, 0)` е стойността или резервната стойност, когато не е зададена. `sum`, `count` (`count(@roll.dice, 6)` брои шестиците), `min`, `max`, `any` и `all` приемат списъци.

## Листове: `schemas/`

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

| Вид | Съдържа | Опции |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | обикновена стойност | min, max; `values` за enum |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: `@hp` е стойността, `@hp.max` — горната граница | range; min; max или max_field; die |
| `counter` | число | min, max, thresholds, occupies (поле от тип slots) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | предмети (`Rope` или `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | каквото казва името | `to` (за refs), `allowed` |
| `derived` | изчислява се, никога не се съхранява | expr |

Всяко поле приема също `label`, `help`, `default`, `required` и `roll`: `new pc Hero --fill` или стойност `"roll"` го хвърля чрез дневника. Типовете от пакета `core` държат независим от системата текст във `fields`. Типовете на една система държат числата ѝ в `mechanics.<system>`. `set hero hp-=2` намира полето, ограничава го и съобщава за всяко препълване. `+=` добавя към списък: `list` (като `slots`) пази и повторно добавена стойност, `tags`, `conditions` и `refs` я държат само веднъж, а `-=` маха всички нейни копия.

**Куките** казват какво става, когато стойност премине граница. Задействат се при всяка промяна (`set`, `inv`, стъпка `set` в правило), но само когато границата бъде премината: 3 → 0 задейства, 0 → 0 не. Редакциите с `--force` ги пропускат.

| Кука | Задейства се, когато |
|---|---|
| `on_zero` | число или `{value}` стигне 0 |
| `on_full` (`when_full` при slots) | стигне максимума, размера или капацитета си |
| `thresholds: {10: …, 20: …}` (броячи) | мине всяка отметка |

Действието е текст (бележка за LLM), `{set: {hp: 0}}` или `{condition: paralyzed}` върху същия запис, `{trigger: death}` (пуска това правило с `who` = записа) или списък от тях.

**Инвентарът** (`didact inv …`) работи с полето `slots` на листа:
- **Място:** предметите заемат своя `size` × `count`, а броячите, които заемат полето чрез `occupies`, заемат стойността си. Над `capacity` се отказва, освен с `--force`.
- **Групи:** `groups: {backpack: 6, body: 4}` дава на всяка група собствено място, както и собствени колони и сборове: `@inventory.body.armor` е само онова, което е облечено или държано в ръка, а `@inventory.body.free` — оставащото ѝ място.
- **Употреби:** `uses: 3` намалява с `inv use`. `uses: d8` е зар за употреба: 1–2 го смъква с една стъпка. Изхабеният предмет изчезва, освен ако няма `recharge` или `keep: true`. От няколко предмета с едно и също име името означава първия; при харчене на употреба (`inv use`, `use:` на правило, `set …uses-=1`) — първия, на който му е останала употреба.
- **Собствени ключове на предмет:** `didact set freya inventory.sword.damage=d10` (както и `set: who.inventory.$item.damage` в правило) променя един от тях, като предметът се посочва така, както го посочва `inv`, с част от името или с цялото име, с интервали и точки (`'inventory.12.7mm pistol.damage=d10'`, в кавички заради обвивката); `uses` и `charges` се броят като поле `uses` (`charges+=2` спира при максимума), а мястото се проверява така, както го проверява `inv add`. Правило чете такъв ключ като `@{who.inventory.$item.damage}` (зар за употреба — като своя зар, употребите — като броя им); предмет или ключ, който го няма, се чете като липсващ, така че `default(…)` дава резервната си стойност.
- **Компендиум:** записите от тип `item` (или weapon, armor, relic, …, или собствен тип на пакета, който разширява някой от тях чрез `extends`) заемат на `inv add` своите подробности; намират се по ID, по име или по псевдоним (ако два го споделят: посочете нужния като `pack.id`); всяко друго име, заедно с `:`, е собственото име на предмета.

## Таблици: `tables/`

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

Други форми:
- **Претеглени списъци:** `entries` като списък, с `weight:` за всеки запис.
- **Колони:** `columns: [a, b]` хвърля поотделно за всяка колона на реда. Обикновен запис (не списък) попълва всички колони, така че `columns: [first, second]` върху списък с думи означава „хвърли два пъти по този списък“. `labels: false` пропуска имената на колоните в резултата („Abandon · Advantage“). `read: "It's a {first} {second} with {third} {fourth} inside."` прочита колоните като изречение.
- **Справочни таблици:** `lookup: hp_lost` или `[odds, chaos]` за двумерна таблица.
- **Повторения:** `duplicates: reroll | keep | make_it_worse` за „хвърли два пъти“.
- **Двустепенни хвърляния:** запис, който хвърля по друга таблица (`{table: lightning}` вместо собствен резултат или `then:` след него), носи със себе си данните от това хвърляне: правило или чернова, на които се падне този запис, четат и двете — първо собствените му ключове, после тези на първата таблица, по която се хвърля след това. `--prefill` може да посочи запис по-надолу, на всякаква дълбочина (`Ring of the Hunt`), с данните на всеки запис по пътя: от два с едно име се има предвид по-близкият (после първият), запис, който води нататък, хвърля нататък оттам, а запис, близък до някой от тях, но не съвпадащ с нито един, се отхвърля, като се посочва най-близкият. Черновата с водене предлага първата стъпка, когато записите ѝ казват какво са (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): изборът на запис хвърля по следващата таблица, както хвърляне, което се е паднало на него.
- **Прочит в двете посоки:** `both_ways: true` при таблица d66 добавя другия прочит: 31 дава и 13, а читателят избира.
- **Какво означава записът:** `about: "Knows: {skills}. Also known as: {aka}."` попълва данните на всеки запис (списък се чете като `a, b`; `{text}` е самият запис), за да каже какво дава той, когато изборът го предлага; собственото `note:` на записа казва това вместо него. Ако няма нито едното, нито другото, запис, чиито данни имат `id`, посочващо запис в компендиума, се описва от онзи запис.
- **Тестета и торби:** `deck: tarot` с `cards` (или `standard: true`); `bag: initiative` с `tokens`.

Валидацията проверява, че всеки резултат, който заровете могат да дадат, попада на запис.

## Правила: `rules/`

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

Действията и процедурите са списъци от стъпки, а тригерите са стъпки с условие `when:`. Стъпките са:

| Стъпка | Какво прави |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | записано хвърляне; свързва `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`; `{…}` първо се попълва, както във всеки текст, така че заровете, които една стойност държи като текст, се хвърлят (`{@{who.inventory.$item.damage}}`), а дневникът ги показва: стойност, която не е зарове, се отхвърля, както и `roll: "@die"` с такъв текст, който не хвърля нищо; набор от хвърляния (`{d8, d6}kh1`) остава набор |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | изчислява стойности; както при `value` на `set`, текст с `{…}` е шаблон, а самостоятелна дума е текст; във всеки попълван текст `{{` и `}}` пишат самата скоба |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (или `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | променя запис: проверено, ограничено, с възможност за отмяна; `set: who.$attr` задава полето, посочено от параметър, а `set: who.inventory.$item.damage` — ключ на предмет, който записът носи (вж. „Инвентар“); `-=` маха стойност от списък, а стойност, която той не съдържа, не променя нищо (бележка казва това; стойност, която той никога не би могъл да съдържа, се отхвърля); `unset:` маха поле, както `set --unset` |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | дава предмет на запис или взима такъв от него, както правят `inv add` и `inv drop`: подробностите му идват от компендиума, стига уникална част от името му, а мястото и куките на полето се проверяват |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | използва носен предмет, както го прави `inv use`: употребите или зарядите намаляват, зарът за употреба се хвърля и при 1–2 се смъква с една стъпка, а изхабеният изчезва, освен ако не се презарежда или не се пази; от няколко с това име — първия, на който му е останала употреба; свързва `@torch.out` (последната му употреба отиде), `@torch.gone` (от него не е останало нищо), `@torch.left`, `@torch.die` и `@torch.rolled` (`as:` по подразбиране е `use`) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | създава запис веднага, описан така, както го описва стъпката `entity` на чернова (по-долу), и проверен спрямо листа си; `as:` (иначе неговият `key`, иначе типът му) го свързва като запис, който се чете и задава като параметър `ref` (`pool: "@bleeding"`, `@bleeding.name`), и никога не съвпада с име на параметър; без `key:` никое поле не се взима за ключ (`kind: track` остава, както е написано); ако тук вече има запис от този тип и с това име, той се взима такъв, какъвто е, така че правило, изпълнено отново, не създава нищо ново |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | изпълнява проверка и свързва изхода ѝ |
| `do: other-action`, `with: {…}`, `as: trip` | изпълнява друго правило; `@trip` е неговият изход, а `@trip.<name>` — това, което то е свързало (`@trip.found` за неговото `let: {found: 2}`, `@trip.luck` за неговото `roll: d6`, `as: luck`); `as:` по подразбиране е неговото ID |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | записано хвърляне по таблица; свързва текста и `data` на записа (`@scar.<key>`, а ключовете на речник — по пътя им: `@scar.cost.hp`), заедно с данните на всяка таблица, по която се хвърля след това; списък от предмети (`[Rope, {name: Laser, damage: d8}]`) се чете като имената им (`count(@scar.gear)`, `'Laser' in @scar.gear`), а подаден на стъпка такъв, какъвто е (`apply: "@scar.gear"`), е самите предмети; списък от други речници се чете само от стъпка |
| `table: "setting-{@drop.difficulty}-terrain"` | изчислена таблица: `{…}` и `$param` се попълват |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | няколко резултата като списък (`distinct` прехвърля повторенията) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | разклонения |
| `repeat: "@count"`, `as: i`, `steps: […]` | цикъл: изпълнява стъпките съответния брой пъти, като `@i` брои от 1 |
| `for: pcs` (или `party`), `as: member`, `steps: […]` | изпълнява стъпките по веднъж за всеки персонаж на играч (или член на групата), като `@member`: запис, също като онзи, който свързва `entity:` (`@member.name`, `set: member.fatigue`); `as:` никога не приема името на параметър, така че собственото `who` на правилото остава непокътнато |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | изход за LLM |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (или `every: 1 day`) | напомняне, което настъпва с течение на игровото време, като онези, които задава `didact remind` |
| `reroll: roll`, `keep_if: "@face == 6"` | прехвърля някои зарове от хвърляне (механики за натиск) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | хвърля по стойност-списък (списъците на оракул): свързва записа, `@who.choose` (празен ред) и `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | хвърля намаляващия пул на брояч, както прави `track roll` (заровете с 1-3 отпадат; заровете от `drop` се махат първи, заровете от `extra` се хвърлят заедно с тях) или само маха зарове (`mode: drop`: натиск, отметка); следват свързаните фази и събитието на пула; свързва `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

Изходът на проверка може да се чете от правилото, което я е изпълнило (`check: … as: answer` дава `@answer`), както и флаговете ѝ: `'random-event' in @answer.flags`. Стойностите в `with:` се изчисляват, когато съдържат `@`, попълват се, когато съдържат `$param` или `{…}` („Does $npc flee?“), а иначе се подават както са написани. Правило с параметър `oracle` получава записа със състоянието на оракула на кампанията, без да е нужно да се казва. Параметър `ref` с `to: monster` взима запис от този тип: име, което споделя друг запис (пулът на враг, кръстен като картата му), означава записа от този тип.

Тригерите се изпълняват сами, когато настъпи тяхното събитие, и само ако условието им `when:` е вярно:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Всяко правило (включително генераторите и създаването на персонажи) може да чете `@system` (ID-то на системата, по която играе светът, така че сетинг, писан за две системи, да може да ги различи), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` и `@time.is_night`, а при календар с месеци — и `@time.month`, `@time.month_name`, `@time.day_of_month` и `@time.year`; докато тече битка — също `@combat.round` и `@combat.fighters` (ID-тата на участниците в нея). Тригер за време може да чете и `@time.passed` — секундите, с които времето току-що е придвижено, тригер `combat_start` или `combat_end` чете битката, която започва или свършва (`combat start` и `combat end` ги изпълняват; ако боец напусне, битката не свършва), а правило, изпълнено от тригер, чете същото, което чете и тригерът. Тригер със задължителни параметри се изпълнява само от `didact do` или от кука на поле (`who` = записа). Тригерите с `on: manual` се изпълняват само когато бъдат извикани. `for: pcs` (или `party`) изпълнява тригера по веднъж за всеки персонаж на играч (или член на групата), като `who`: например опит след всяка сесия. Тригер, който се провали, спира командата, която го е задействала, и казва кой тригер е бил и как да се продължи без него (`didact override add trigger <id> --data '{"on": "manual"}'`).

Календарът е в `settings` на пакет: този на пакет със сетинг надделява над този на системата, а собственият календар на света (`calendar:` в неговия `world.yaml`) — и над двата:

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

`leap: 4` прави месеца с един ден по-дълъг всяка 4-та година, а `leap: [4, 100, 400]` — всяка 4-та, но не всяка 100-тна, а пък всяка 400-тна: всяко число отменя предишното. `weekday` назовава деня от седмицата, в който е началото (иначе е първият ден на седмицата), а `year` е как датата пише годината си, както в датите, които Didact показва, така и в тези, които чете (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` проверява и трите. Кампания може да започне на друга дата от календара, преди началото му или след него: `didact campaign new <id> --date '4 July 1902'`, или `didact time set '<date>'` до първата ѝ сесия. Ден от седмицата, написан пред датата, се проверява: решава датата, а бележка казва, когато тя се пада на друг ден.

Опциите са вариантите и незадължителните правила на системата, избирани за всяка кампания на нулевата сесия:

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

`didact campaign profile lethality=deadly supplies=on` ги запазва (или страницата „Настройки“ на уеб приложението). Правилата, създаването на персонажи и генераторите ги четат (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): отговорът има предимство пред това, което друга опция подразбира, а то — пред стойността по подразбиране. Това, което една опция подразбира, се проследява докрай (настроение, което задава смъртоносността, задава и онова, което тази смъртоносност подразбира), а когато две опции подразбират различни неща, печели по-близката. Резюмето изброява онези, които се различават от стойността си по подразбиране, с това какво означават, за да прилага водещият онова, което правилата не могат. Генератор, който не може да работи при тях, спира със `stop:` и причината, и нищо не се създава като чернова.

## Оракули: `oracles/`

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

- **Питане:** `didact ask '…' --odds likely` изпълнява проверката `ask`. Отговорът е нейният изход (диапазон), а флаговете ѝ идват с него.
- **Състояние:** живее в запис, който проверката получава като `oracle`. Проверката го променя със `set: oracle.chaos += 1`.
- **Списъци:** `lists: {names: […], method: sections, most: 3}` пази претеглени списъци в този запис. `didact lists add|drop|roll|show` ги управляват, а правилата хвърлят по тях с `pick`. `sections` хвърля за раздел от пет реда, после за ред в него (празен ред означава „изберете“); `uniform` дава на всеки ред еднакъв шанс.
- **Още за проверката:** `didact ask '…' --with as_rule=true` подава допълнителни параметри на проверката на оракула.
- **Дневникът:** всеки отговор се номерира (`#o12`) и записва, а `didact interpret o12 '…'` пази какво е означавал. Оракулът `yes-no` от пакета core е резервният.

## Генератори и създаване на персонажи: `generators/`, `chargen/`

И двете са процедури, които изграждат **чернова**. Те използват всяка стъпка на правилата (`roll`, `table`, `if`, `let`, `prompt`, …) плюс тези:

| Стъпка | Какво прави |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | добавя запис към черновата (ключове `poi-1`, `poi-2`, …); поле или връзка, която посочва ключ, написан от пакета (`key:` или име от `as:`), става ID-то на този запис при приемане, така че избирайте ключове, които никое поле не съдържа като текст (същност без нито едното, нито другото няма ключ за замяна); `from: "@relic.id"` го създава въз основа на запис в компендиума (типа, името и полетата му) |
| `choose: {from: [a, b], as: x}` (или `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | избор; в режим с насоки черновата чака `choose`; `exclude` изключва по-ранни избори (хвърлен такъв се хвърля отново); `records:` добавя към вариантите записите от този тип тук, по id (създадени в играта); `answer:` прави избора, без да пита, когато стойността му е един от вариантите (собственият път на персонажа) |
| `choose_or_roll: {table: backgrounds, as: background}` | избор, който заровете могат да направят; данните на избрания запис са `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | хвърля в персонажа |
| `swap: {among: [STR, DEX, WIL], optional: true}` | разменя две стойности или ги оставя |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | разпределя фиксиран набор |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | купува стойности в рамките на бюджет (`default: random` го харчи случайно в случаен режим) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | списък отива в инвентара; речник задава полета (списъците се добавят) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | добавя към поле на персонажа (или на обект в черновата): числата се събират, всичко друго се добавя към списък; ако няма какво да се добави, няма проблем |
| `remove: {field: talents, value: "@old"}` | маха нещо от поле-списък (сменен талант, разрешена обвързаност); ако го няма, няма проблем |
| `roll_tables: [physique, vice]` | хвърля по таблици в `traits`; `data.gear` на записа отива в инвентара, а `data.add: {gold: 20}` добавя към полета |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | името; `name: {prompt: …}` без откъде да се хвърли чака име дори в случаен режим |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | въпрос, на който става всеки отговор (цел, името на друг запис): черновата го чака дори в случаен режим, освен ако не е попълнен предварително; `field:` запазва отговора |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | pointcrawl: записано пускане на зарове, пътища (винаги свързани), разстояния, скрити пътища (вж. по-долу) |

Стъпката map приема и още, за процедурите с пускане на зарове от книгата:

| Ключ | Какво прави |
|---|---|
| `regions: terrain` | тези обекти също се пускат; всяко място се присъединява към най-близкия (неговия `region`) |
| `hidden: 6`, `conditional: 5` | d6 за всеки път: на или над числото пътят е скрит или условен (скритите пътища не се показват на картата на играчите) |
| `describe: [path-feature, path-condition]` | таблици, хвърлени за всеки път, пазят се като негови `details` |
| `entrance: true`, `exit: true` | мястото, най-близо до ръба, е входът; останалите се номерират от него по пътищата (`map.n`), пътищата водят навън от него, а изходът е далечно място близо до ръб, номерирано последно |
| `number: "{@dungeon_name}, room {@n}"` | преименува номерираните места (ключовете им в черновата следват: `room-1` е стая 1) |

Таблица за пускане на зарове може да посочи следващите таблици в данните на записите си, така че процедурата се чете като в книгата: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, после `table: "{@drop.what}"`. Незададените полета-списъци (conditions, lists, tags) се четат като празни списъци, така че `'deprived' in @who.conditions` работи от самото начало.

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

Процедура chargen с `advances:` променя запис, вместо да създава нов: това е качването на ниво в системата.

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

- **Един запис:** генератор с `creates: npc` изгражда този запис така, както създаването на персонаж изгражда персонаж (`apply`, `add`, `name`, `field:`); стъпките му `entity` добавят записи до него, а връзка `to: character` сочи към него.
- **Пускане:** `gen run` и `char new` правят чернова (`#g7`, `#c3`) и не записват нищо. `stop:` прекратява изпълнението, без да създаде чернова: под `if:`, който чете опция на кампанията, подсказката му сочи опциите (`didact session zero`); иначе собствените му думи казват какво да се направи вместо това.
- **Решаване:** `--prefill '{…}'` решава неща предварително по името, което стъпката свързва (`as:`): единична стойност отговаря на всяко срещане, списък — по едно срещане на елемент (списък за `choose` с `count` е целият избор). Стойностите на `let` също могат да се попълнят предварително (`{"hp": 6}`), а име, `ask` или `let` пази всеки текст така, както е даден. Стойност за избор между известни варианти (`choose`, запис в таблица) е вариантът, който тя посочва — както е написан (независимо от главни и малки букви), чрез `id` на неговия запис или чрез хвърляне, което попада на него (`{"group": 3}`) — и носи данните на този запис; стойност, близка до някой вариант, но различна от всички тях, се отхвърля, като се посочва най-близкият, а всяка друга е собствен отговор, без данни. `--auto` (или `char new --mode random`) оставя заровете да решат останалото. Иначе черновата чака при всеки избор.
- **Описване:** изборът казва на играча, който избира, какво означава всяка възможност: `note:` на записа в таблицата или `about:` на таблицата му, иначе записът в компендиума, който той посочва (`id` в данните му), или този, който е самата възможност (избор между ID-та от компендиума показва името на всеки): неговите `tagline` и `summary`, неговото `description` или `effect`, иначе първия абзац от текста му.
- **Връщане назад:** `char back` (или `gen back`) отменя последния отговор, хвърляне или редакция, така че черновата отново задава същия въпрос; хвърлянията, направени в тази стъпка, се отбелязват като отменени.
- **Продължаване:** продължената чернова възпроизвежда следата си: всяка хвърлена или избрана стойност, всяка веднъж и по ред (включително пускането на зарове за картата), така че нищо не се хвърля два пъти и нищо вече решено не се променя.
- **Записване:** `commit` записва записите, проверени спрямо листовете им.
- **Развитие:** чернова с `advances:` започва от копие на записа (със стойностите по подразбиране от листа му), стъпките ѝ четат записа като `@who`, а стойностите на черновата — като `@character.*`, и `commit` записва само промененото, проверено като при `set`; записите от стъпките ѝ `entity` (сюжетната линия на нова обвързаност) се създават до него: връзка `to: character` сочи към записа, а поле, което посочва ключ, съдържа ID-то на записа, в който се превръща този ключ, както при създаване на персонаж (`apply: {blood: "@pool"}`). `stop:` казва защо още не може (няма достатъчно опит) и не се създава чернова. Система, чийто растеж е едно-единствено правило, вместо това го посочва в своя chargen: `advance: {rule: grow}`.
- **Режими:** `modes: [guided]` запазва процедурата стъпка по стъпка: `--mode random` се отхвърля.

## Компендиум, справочник и речник на термините

- **Записите в компендиума** се пишат като при `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. Стойност `"roll 2d8"` се хвърля, когато записът бъде създаден. Пуснете `didact spawn troll` или внесете записите на пакет в света с `didact compendium import <pack>` (`--type loc`, и `--tag coast` за онези, които имат всеки даден етикет).
- **За няколко системи:** ключ на най-горно ниво отива там, където го слага `set`: в блока на системата, когато листът ѝ има такова поле, иначе във `fields`. Запис, който сетинг пише за повече от една система, дава числата на всяка в собствен блок (`mechanics: {my-system: {hp: 12}}`): `pack validate` проверява всеки блок спрямо листа на съответната система, когато тя е инсталирана, и отбелязва ключ на най-горно ниво, който имат и този лист, и листът на core. Каквото казва блокът, остава: до `mechanics: {my-system: {role: tactician}}` ключът на най-горно ниво `role: innkeeper` е поле на core, както и всичко под `fields:`. Блок, който посочва проверявания пакет, се проверява спрямо този пакет такъв, какъвто е в папката си.
- **Разделите на справочника** отиват в `reference/*.md`, с front matter (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` ги намира; фраза в кавички, която я няма, се пробва по думите си.
- **Речникът на термините** е `glossary.yaml`: `term: definition` или списък от `{term, definition, aliases, see}`. `didact define <term>` го чете.

## Тестове: `tests/`

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

## Споделяне и премахване на пакети

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- Пакет, който декларира `redistributable: false`, не може да се експортира.
- **core** е част от Didact и е винаги включен: всяка система стъпва върху него, затова не може да се изключи или деинсталира.
- Другите пакети, които идват с Didact, са файлове `.didactpack` в неговата папка `packs/`. `pack list` ги показва, докато не бъдат инсталирани, а инсталирането на един довежда и нужните му пакети, които също идват с Didact.
- `pack update` търси по-нови версии в папката `packs/` на Didact и в GitHub (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` посочва друго място или нищо, за да не се търси). Новата версия се инсталира до старата: кампаниите пазят своята до `didact campaign upgrade`.
- В даден момент се използва една игрова система: тази на отворения свят. Светът пази системата, с която е създаден (`didact world new <id> --system <pack>`; свят, създаден без система, приема първата, която му бъде дадена, с `pack enable` или `world set system=`), кампаниите му играят по нея, а пакет, който изисква друга система (сетинг, писан за нея), не може да се добави: друга система се играе в собствен свят.
- `uninstall` отказва, докато свят или кампания използва единственото копие на пакета (`--force` го премахва въпреки това). Не може да се отмени: инсталирайте отново .didactpack.

## От книга с правила до пакет: списъкът

Минете през механиките на книгата в този ред. Всяка съответства на нещо от описаното по-горе:

1. **Разрешаване:** как хвърлянето успява (проверка: `success`, `bands`, `auto`).
2. **Зарове:** необичайни зарове, символи, стъпки (`dice.yaml`, именувани зарове, вериги).
3. **Листът:** атрибути, изчислявани числа (`schemas/`, полета derived).
4. **Ресурси:** HP, късмет, инерция (полета resource и counter; стъпки `set`).
5. **Състояния:** състоянията и какво правят (полета `conditions`; стъпки `if`).
6. **Битка:** атаки, щети, инициатива (действия; `bag`/`deck` за реда на ходовете).
7. **Процедури:** изследване, пътуване, почивка (процедури с насоки).
8. **Таблици:** всяка случайна таблица (`tables/`; `pack import` за таблици в Markdown).
9. **Бестиарият:** чудовища и НИП (`compendium/`).
10. **Предмети:** екипировка, заклинания, реликви (`compendium/`, полета slots).
11. **Насоки за водещия:** принципи и съвети (`GUIDE.md`, `reference/`, `guidance:` в типовете).
12. **Създаване на персонаж:** как се прави персонаж (процедура в `chargen/` или `roll:` за всяко поле).

Цитирайте страници със `source:` навсякъде, за да личат пропуските. Добавете smoke-play тест, който създава персонаж, хвърля проверка, води битка и изпълнява процедура.
