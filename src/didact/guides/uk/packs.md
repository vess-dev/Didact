<!-- translated from b1dfa1159ff4 -->
# Пакети

Пакет — це ігрова система, оракул, сетинг, пригода чи доповнення, записані як YAML-файли плюс необов’язковий плагін на Python. Цей посібник показує, як написати пакет: перетворити книгу правил на пакет або додати домашній контент.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Пакет можна зробити й з того, що є у вашій бібліотеці. `didact pack new my-brew --from-overlay my-system` перетворює ваш домашній контент для системи (`compendium add`, записи, збережені з `--scope system`, лор) на доповнення, а `didact world export --as setting` перетворює світ на пакет сетингу: його людей, місця й лор як статті компендіуму та лор пакета, які переносять в інший світ через `compendium import`. Обидва не включають таємниці й нотатки майстра без `--secrets`, і жоден не позначено як придатний для поширення, доки ви не вкажете його ліцензію.

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

Файл містить один елемент, список елементів або кілька елементів, розділених `---`. Кожен елемент задає свій ID ключем свого виду: `table: weather`, `check: save`, `type: pc` або `id: troll` для статей компендіуму. Посилайтеся на елементи як `pack.id` (`my-system.save`) або просто за ID, якщо він є лише в одному ввімкненому пакеті.

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

Хак називає свою основу в `extends` і містить лише те, що відрізняється:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Його елемент із тим самим ID замінює елемент основи, хоч би якого виду він був (таблиця, правило, стаття компендіуму, розділ довідки, термін глосарію). Його `settings` накладаються поверх налаштувань основи, ключ за ключем: ключ, який задає хак, замінює значення основи цілком (його таблиці `names` стають на місце таблиць основи), а правила основи теж читають значення хака. `hides` прибирає решту, що хакові не потрібна: `*` збігається з будь-якою послідовністю символів, вирішує останній шаблон, що збігся з ID, а шаблон, що починається з `!`, зберігає елемент. Те, що хак замінює, ніколи не приховується. Види: `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` і `term`. `didact pack validate` попереджає про шаблон, який ні з чим не збігається.

## Вирази

Усі умови й формули використовують мову костей (`didact guide dice`), а також:
- **Значення:** `@name` читає значення: `@roll`, `@who.STR`, `@settings.x`. `$name` спершу підставляє текст параметра, тож `@who.$attr` стає `@who.STR`. Параметр із вільним текстом читайте як `@name`, а не в лапках (`'$name'`): апостроф у його тексті закрив би лапки (`pack validate` попереджає).
- **Логіка:** `and`, `or`, `not` і `in` (`'deprived' in @who.conditions`).
- **Літерали:** текст (`'travel'`) і `true`/`false`.
- **Функції:** `if(cond, a, b)` кидає лише ту гілку, яку вибирає. `default(@thread.flashpoint, 0)` — це значення або запасне, якщо його не задано. `sum`, `count` (`count(@roll.dice, 6)` лічить шістки), `min`, `max`, `any` і `all` приймають списки.

## Аркуші: `schemas/`

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

| Вид | Зберігає | Параметри |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | просте значення | min, max; `values` для enum |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: `@hp` — значення, `@hp.max` — межа | range; min; max або max_field; die |
| `counter` | число | min, max, thresholds, occupies (поле slots) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | предмети (`Rope` або `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | те, що вказано в назві | `to` (для refs), `allowed` |
| `derived` | обчислюється, ніколи не зберігається | expr |

Кожне поле також приймає `label`, `help`, `default`, `required` і `roll`: `new pc Hero --fill` або значення `"roll"` кидає його через журнал. Типи з пакета `core` зберігають у `fields` текст, що не залежить від системи. Типи системи зберігають її числа в `mechanics.<system>`. `set hero hp-=2` знаходить поле, обмежує значення й повідомляє про будь-яке переповнення. `+=` додає до списку: `list` (як-от `slots`) зберігає й повторно додане значення, `tags`, `conditions` і `refs` містять його лише раз, а `-=` прибирає всі його копії.

**Хуки** кажуть, що стається, коли значення перетинає межу. Вони спрацьовують за кожної зміни (`set`, `inv`, крок правила `set`), але лише коли межу перетнуто: 3 → 0 спрацьовує, 0 → 0 — ні. Правки з `--force` їх оминають.

| Хук | Спрацьовує, коли |
|---|---|
| `on_zero` | число або `{value}` досягає 0 |
| `on_full` (`when_full` у slots) | воно досягає свого max, size чи capacity |
| `thresholds: {10: …, 20: …}` (counters) | воно піднімається вище кожної позначки |

Дія — це текст (нотатка для LLM), `{set: {hp: 0}}` або `{condition: paralyzed}` на тому самому записі, `{trigger: death}` (запускає це правило з `who` = запис) або список із них.

**Інвентар** (`didact inv …`) працює з полем `slots` аркуша:
- **Місце:** предмети займають `size` × `count`, а лічильники, що `occupies` це поле, — своє значення. Понад `capacity` додати не можна без `--force`.
- **Групи:** `groups: {backpack: 6, body: 4}` дає кожній групі власне місце, а також власні стовпці й суми: `@inventory.body.armor` — лише те, що вдягнене або в руках, `@inventory.body.free` — місце, що в ній лишилося.
- **Використання:** `uses: 3` зменшується з кожним `inv use`. `uses: d8` — кість витрати: 1–2 знижує її на крок. Витрачений предмет зникає, якщо не має `recharge` або `keep: true`. З кількох предметів з однією назвою назва означає перший; щоб витратити використання (`inv use`, `use:` правила, `set …uses-=1`), — перший, у якого воно ще лишилося.
- **Власні ключі предмета:** `didact set freya inventory.sword.damage=d10` (і крок правила `set: who.inventory.$item.damage` теж) змінює один із них, а предмет називають так, як його називає `inv`, частиною назви або всією назвою, з пробілами й крапками (`'inventory.12.7mm pistol.damage=d10'`, у лапках для оболонки); `uses` і `charges` рахуються як поле `uses` (`charges+=2` зупиняється на максимумі), а місце перевіряється так само, як це робить `inv add`. Правило читає такий ключ як `@{who.inventory.$item.damage}` (кість витрати — як її кість, використання — як їхню кількість); предмет або ключ, якого немає, читається як відсутній, тож `default(…)` дає своє запасне значення.
- **Компендіум:** статті типу `item` (або weapon, armor, relic, …, або власного типу пакета, що розширює один із них через `extends`) передають `inv add` свої дані; їх знаходять за ID, за назвою або за псевдонімом (якщо псевдонім спільний для двох — назвіть потрібну як `pack.id`); будь-яка інша назва, разом із `:`, — власна назва предмета.

## Таблиці: `tables/`

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

Інші форми:
- **Зважені списки:** `entries` як список, із `weight:` у кожному рядку.
- **Стовпці:** `columns: [a, b]` кидає за кожним стовпцем рядка окремо. Простий рядок (не список) заповнює всі стовпці, тож `columns: [first, second]` над списком слів означає «кинути за цим списком двічі». `labels: false` прибирає назви стовпців із результату («Abandon · Advantage»). `read: "It's a {first} {second} with {third} {fourth} inside."` читає стовпці як речення.
- **Довідкові таблиці:** `lookup: hp_lost` або `[odds, chaos]` для двовимірної таблиці.
- **Повтори:** `duplicates: reroll | keep | make_it_worse` для «кинути двічі».
- **Два кроки:** рядок, що кидає за іншою таблицею (`{table: lightning}` замість тексту або `then:` після нього), приносить із собою дані цього кидка: правило чи чернетка, що його викидає, читає обидва набори — спершу власні ключі рядка, потім ключі першої таблиці, за якою кидають далі. `--prefill` може назвати рядок нижче, на будь-якій глибині (`Ring of the Hunt`), із даними кожного рядка на шляху: із двох з однією назвою мається на увазі ближчий (потім перший), рядок, що веде далі, кидається далі звідти, а схожий на один із них, але не той самий, відхиляється з указанням найближчого. Покрокова чернетка пропонує перший крок, коли її рядки кажуть, що вони таке (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): вибір рядка кидає за наступною таблицею, як кидок, що на нього випав.
- **Читання в обидва боки:** `both_ways: true` у таблиці d66 додає зворотне прочитання: 31 дає й 13, а читач вибирає.
- **Що означає рядок:** `about: "Knows: {skills}. Also known as: {aka}."` підставляє дані кожного рядка (список читається як `a, b`; `{text}` — сам рядок), щоб сказати, що він дає, коли його пропонує вибір; якщо в рядка є власна `note:`, це каже вона. Якщо немає ні того, ні іншого, рядок, у даних якого є `id`, що називає статтю компендіуму, описує ця стаття.
- **Колоди й торбинки:** `deck: tarot` з `cards` (або `standard: true`); `bag: initiative` з `tokens`.

Перевірка переконується, що кожен результат, який можуть викинути кості, потрапляє на рядок.

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

Дії та процедури — це списки кроків, а тригери — кроки з умовою `when:`. Кроки такі:

| Крок | Що робить |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | кидок із записом до журналу; зв’язує `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`; `{…}` спершу заповнюється, як у будь-якому тексті, тож кості, які значення тримає як текст, кидаються (`{@{who.inventory.$item.damage}}`), і журнал їх показує: значення, яке не кості, відхиляється, як і `roll: "@die"` з таким текстом, що нічого не кидає; набір кидків (`{d8, d6}kh1`) лишається набором |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | обчислює значення; як і у `value` кроку `set`, текст із `{…}` — це шаблон, а голе слово — текст; у будь-якому заповнюваному тексті `{{` і `}}` пишуть саму фігурну дужку |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (або `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | змінює запис: із перевіркою, обмеженням, можливістю скасування; `set: who.$attr` задає поле, вказане параметром, а `set: who.inventory.$item.damage` — ключ предмета, який несе запис (див. «Інвентар»); `-=` прибирає значення зі списку, а значення, якого в ньому немає, нічого не змінює (про це скаже примітка; значення, якого в ньому ніколи не може бути, відхиляється); `unset:` прибирає поле, як `set --unset` |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | дає запису предмет або забирає предмет у нього, як це роблять `inv add` і `inv drop`: дані беруться з компендіуму, досить унікальної частини назви, а місце й хуки поля перевіряються |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | використовує предмет, який несе запис, як це робить `inv use`: використання або заряди зменшуються, кість витрати кидається й на 1–2 знижується на крок, а витрачений предмет зникає, якщо він не перезаряджається і не зберігається; з кількох із такою назвою — перший, у якого лишилося використання; зв’язує `@torch.out` (його останнє використання минуло), `@torch.gone` (від нього нічого не лишилося), `@torch.left`, `@torch.die` і `@torch.rolled` (`as:` за замовчуванням — `use`) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | одразу створює запис, описаний так само, як у кроці `entity` чернетки (нижче), і перевірений за своїм аркушем; `as:` (інакше його `key`, інакше його тип) зв’язує його як запис, який читають і задають як параметр `ref` (`pool: "@bleeding"`, `@bleeding.name`), і ніколи не збігається з назвою параметра; без `key:` жодне поле не вважається ключем (`kind: track` лишається як написано); якщо запис такого типу й з такою назвою тут уже є, його беруть як є, тож повторний запуск правила нічого нового не створює |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | виконує перевірку й зв’язує її результат |
| `do: other-action`, `with: {…}`, `as: trip` | запускає інше правило; `@trip` — його результат, а `@trip.<name>` — те, що воно зв’язало (`@trip.found` для його `let: {found: 2}`, `@trip.luck` для його `roll: d6`, `as: luck`); `as:` за замовчуванням — його ID |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | кидок за таблицею із записом до журналу; зв’язує текст і `data` рядка (`@scar.<key>`, і ключі словника — за їхнім шляхом: `@scar.cost.hp`), а також дані будь-якої таблиці, за якою кидають далі; список предметів (`[Rope, {name: Laser, damage: d8}]`) читається як їхні назви (`count(@scar.gear)`, `'Laser' in @scar.gear`), а переданий кроку як є (`apply: "@scar.gear"`) — це самі предмети; список інших словників читає лише крок |
| `table: "setting-{@drop.difficulty}-terrain"` | обчислювана таблиця: `{…}` і `$param` підставляються |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | кілька результатів списком (`distinct` перекидає повтори) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | розгалуження |
| `repeat: "@count"`, `as: i`, `steps: […]` | цикл: виконує кроки стільки разів, скільки задано, а `@i` лічить від 1 |
| `for: pcs` (або `party`), `as: member`, `steps: […]` | виконує кроки по разу для кожного персонажа гравця (або члена групи), як `@member`: це запис, як той, що його зв’язує `entity:` (`@member.name`, `set: member.fatigue`); `as:` ніколи не бере назву параметра, тож власний `who` правила лишається недоторканим |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | вивід для LLM |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (або `every: 1 day`) | нагадування, що настає з плином ігрового часу, як ті, що ставить `didact remind` |
| `reroll: roll`, `keep_if: "@face == 6"` | перекидає частину костей кидка (механіка ривка) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | кидає за значенням-списком (списки оракула): зв’язує рядок, `@who.choose` (порожній рядок) і `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | кидає, як і `track roll`, пул лічильника, що зменшується (кості з 1-3 вибувають; кості з `drop` прибираються першими, кості з `extra` кидаються разом із ним) або лише прибирає кості (`mode: drop`: ривок, позначка); слідом спрацьовують пов’язані фази й подія пулу; зв’язує `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

Результат перевірки доступний правилу, яке її запустило (`check: … as: answer` дає `@answer`), як і її прапорці: `'random-event' in @answer.flags`. Значення `with:` обчислюються, якщо містять `@`, заповнюються, якщо містять `$param` або `{…}` («Does $npc flee?»), а інакше передаються як написано. Правило з параметром `oracle` отримує запис стану оракула кампанії без явної вказівки. Параметр `ref` із `to: monster` бере запис цього типу: назва, спільна з іншим записом (пул ворога, названий як його картка), означає запис цього типу.

Тригери запускаються самі, коли стається їхня подія, і лише якщо виконується їхня умова `when:`:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Будь-яке правило (зокрема генератор і створення персонажа) може читати `@system` (ID системи, за якою грають у світі, тож сетинг, написаний для двох систем, може їх розрізнити), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` і `@time.is_night`, а з календарем із місяцями — ще й `@time.month`, `@time.month_name`, `@time.day_of_month` і `@time.year`; поки триває бій — `@combat.round` і `@combat.fighters` (ID тих, хто бере в ньому участь). Тригер часу може читати ще й `@time.passed` — щойно минулі секунди; тригер `combat_start` чи `combat_end` читає дані бою, що починається чи закінчується (їх запускають `combat start` і `combat end`; бій не закінчується, коли з нього виходить боєць), а правило, яке запускає тригер, читає те саме, що й тригер. Тригер з обов’язковими параметрами запускається лише через `didact do` або хук поля (`who` = запис). Тригери `on: manual` запускаються лише за викликом. `for: pcs` (або `party`) запускає тригер по разу для кожного персонажа гравця (або члена групи), як `who`: наприклад, досвід після кожної сесії. Тригер, що завершився помилкою, зупиняє команду, яка його викликала, і каже, який це був тригер і як продовжити без нього (`didact override add trigger <id> --data '{"on": "manual"}'`).

Календар задають у `settings` пакета: календар пакета сетингу важливіший за календар системи, а власний календар світу (`calendar:` у його `world.yaml`) — за обидва:

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

`leap: 4` робить місяць на день довшим кожен 4-й рік, а `leap: [4, 100, 400]` — кожен 4-й, але не кожен 100-й, зате знову кожен 400-й: кожне число скасовує попереднє. `weekday` називає день тижня початку (інакше це перший день тижня), а `year` — те, як дата пише свій рік, і в датах, які показує Didact, і в тих, які він читає (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` перевіряє всі три. Кампанія може початися іншою датою календаря, до його початку або після: `didact campaign new <id> --date '4 July 1902'` або `didact time set '<date>'` до її першої сесії. День тижня, написаний перед датою, перевіряється: вирішує дата, а примітка каже, коли вона припадає на інший день.

Опції — це варіанти й необов’язкові правила системи, які кожна кампанія обирає на нульовій сесії:

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

`didact campaign profile lethality=deadly supplies=on` зберігає їх (або сторінка «Налаштування» вебзастосунку). Правила, створення персонажів і генератори читають їх (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): відповідь важливіша за те, що випливає з іншої опції, а те — за значення за замовчуванням. Те, що випливає з опції, простежується до кінця (стиль, який задає смертельність, задає й те, що випливає з цієї смертельності), а з двох наслідків переважає ближчий. Зведення перелічує ті, що відрізняються від значення за замовчуванням, з їхнім змістом, щоб ведучий застосовував те, чого не можуть правила. Генератор, який не може працювати за них, зупиняється кроком `stop:` із причиною, і чернетка не створюється.

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

- **Запитання:** `didact ask '…' --odds likely` виконує перевірку `ask`. Відповідь — її результат (діапазон), і прапорці йдуть разом із ним.
- **Стан:** він зберігається в записі, який перевірка отримує як `oracle`. Перевірка змінює його через `set: oracle.chaos += 1`.
- **Списки:** `lists: {names: […], method: sections, most: 3}` зберігає зважені списки в цьому записі. Ними керують `didact lists add|drop|roll|show`, а правила кидають за ними через `pick`. `sections` кидає спершу розділ із п’яти рядків, потім рядок у ньому (порожній рядок означає «виберіть самі»); `uniform` дає всім рядкам рівні шанси.
- **Додатково для перевірки:** `didact ask '…' --with as_rule=true` передає перевірці оракула додаткові параметри.
- **Журнал:** кожну відповідь нумерують (`#o12`) і записують до журналу, а `didact interpret o12 '…'` зберігає її тлумачення. Запасний варіант — оракул `yes-no` з пакета core.

## Генератори та створення персонажів: `generators/`, `chargen/`

І те, й інше — процедури, що будують **чернетку**. Вони використовують усі кроки правил (`roll`, `table`, `if`, `let`, `prompt`, …), а також ці:

| Крок | Що робить |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | додає запис до чернетки (ключі `poi-1`, `poi-2`, …); поле або зв’язок, що називає ключ, який написав пакет (`key:` або ім’я з `as:`), під час прийняття стає ID цього запису, тож обирайте ключі, яких жодне поле не містить як текст (сутність без жодного з них не має ключа для заміни); `from: "@relic.id"` бере за основу статтю компендіуму (її тип, назву й поля) |
| `choose: {from: [a, b], as: x}` (або `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | вибір; у покроковому режимі чернетка чекає на `choose`; `exclude` виключає попередні варіанти (викинутий кидається знову); `records:` додає до варіантів тутешні записи цього типу, за id (створені в грі); `answer:` робить вибір без запитання, коли його значення — один із варіантів (власний шлях персонажа) |
| `choose_or_roll: {table: backgrounds, as: background}` | вибір, який можуть зробити кості; дані вибраного рядка — `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | кидки в персонажа |
| `swap: {among: [STR, DEX, WIL], optional: true}` | поміняти місцями два значення або залишити |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | розподілити фіксований набір |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | купити значення в межах бюджету (`default: random` у випадковому режимі витрачає його навмання) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | список іде до інвентарю; словник задає поля (списки додаються) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | додає до поля персонажа (або сутності чернетки): числа додаються, решта долучається до списку; якщо додавати нічого — нічого страшного |
| `remove: {field: talents, value: "@old"}` | прибирає щось із поля-списку (замінений талант, вирішені узи); якщо прибирати нічого — нічого страшного |
| `roll_tables: [physique, vice]` | кидає за таблицями в `traits`; `data.gear` рядка йде до інвентарю, а `data.add: {gold: 20}` додає до полів |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | ім’я; `name: {prompt: …}`, якщо кидати нема за чим, чекає на введення, навіть у випадковому режимі |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | запитання, на яке годиться будь-яка відповідь (мета, назва іншого запису): чернетка чекає на нього навіть у випадковому режимі, якщо його не заповнено наперед; `field:` зберігає відповідь |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | пойнткраул: кидок костей на мапу із записом до журналу, шляхи (завжди зв’язні), відстані, приховані шляхи (див. нижче) |

Крок map приймає й інше — для процедур кидання костей на мапу з книги:

| Ключ | Що робить |
|---|---|
| `regions: terrain` | ці сутності теж кидаються; кожне місце входить до найближчої (свій `region`) |
| `hidden: 6`, `conditional: 5` | d6 на кожен шлях: за цього числа або вище — прихований чи умовний шлях (приховані шляхи не видно на мапі гравців) |
| `describe: [path-feature, path-condition]` | таблиці, за якими кидають для кожного шляху, зберігаються як його `details` |
| `entrance: true`, `exit: true` | місце, найближче до краю, — вхід; решту нумерують від нього вздовж шляхів (`map.n`), шляхи ведуть геть від нього, а вихід — далеке місце біля краю, з останнім номером |
| `number: "{@dungeon_name}, room {@n}"` | перейменовує пронумеровані місця (їхні ключі в чернетці йдуть слідом: `room-1` — це кімната 1) |

Таблиця для кидка на мапу може називати наступні таблиці в даних своїх рядків, тож процедура читається як у книзі: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, потім `table: "{@drop.what}"`. Незадані поля-списки (conditions, lists, tags) читаються як порожні списки, тож `'deprived' in @who.conditions` працює від самого початку.

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

Процедура chargen з `advances:` не створює запис, а змінює його: це підвищення рівня в системі.

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

- **Один запис:** генератор із `creates: npc` будує цей запис так само, як створення персонажа будує персонажа (`apply`, `add`, `name`, `field:`); його кроки `entity` додають записи поруч, а посилання `to: character` вказує на нього.
- **Запуск:** `gen run` і `char new` створюють чернетку (`#g7`, `#c3`) і нічого не записують. `stop:` завершує її, нічого не створивши: під `if:`, що читає опцію кампанії, її підказка вказує на опції (`didact session zero`); інакше її власні слова кажуть, що зробити натомість.
- **Рішення:** `--prefill '{…}'` вирішує заздалегідь — за назвою, яку зв’язує крок (`as:`): одне значення відповідає на всі входження, список — по одному на входження (для `choose` з `count` список — це весь вибір цілком). Значення `let` теж можна задати заздалегідь (`{"hp": 6}`), а ім’я, `ask` чи `let` зберігає будь-який текст точно як задано. Значення для вибору серед відомих варіантів (`choose`, рядок таблиці) — це варіант, який воно називає, як написано чи в іншому регістрі, за `id` його рядка або кидком, що потрапляє на нього (`{"group": 3}`), і воно приносить дані цього рядка; значення, близьке до якогось варіанта, але не тотожне жодному, відхиляється із зазначенням найближчого, а будь-яке інше — це власна відповідь, без даних. `--auto` (або `char new --mode random`) залишає решту на волю костей. Інакше чернетка чекає на кожному виборі.
- **Опис:** вибір каже гравцеві, який вибирає, що означає кожен варіант: `note:` рядка таблиці або `about:` його таблиці, інакше стаття компендіуму, яку рядок називає (`id` у його даних), або та, якою є сам варіант (вибір серед ID компендіуму показує назву кожної статті): її `tagline` і `summary`, її `description` чи `effect`, інакше перший абзац її тексту.
- **Крок назад:** `char back` (або `gen back`) скасовує останню відповідь, кидок чи правку, тож чернетка знову ставить те саме запитання; кидки, зроблені на цьому кроці, позначаються скасованими.
- **Продовження:** продовжена чернетка відтворює свій слід: кожне кинуте чи вибране значення, по одному разу й по порядку (включно з кидком на мапу), тож ніщо не кидається двічі й ніщо вже вирішене не змінюється.
- **Запис:** `commit` зберігає записи, перевіряючи їх за аркушами.
- **Розвиток:** чернетка з `advances:` починається з копії запису (з типовими значеннями його аркуша), її кроки читають запис як `@who`, а значення чернетки — як `@character.*`, і `commit` записує лише те, що змінилося, з перевіркою, як у `set`; записи з її кроків `entity` (сюжетна лінія нових уз) створюються поруч: посилання `to: character` вказує на запис, а поле, що називає ключ, містить ID відповідного запису, як і під час створення персонажа (`apply: {blood: "@pool"}`). `stop:` пояснює, чому ще не можна (бракує досвіду), і чернетка не створюється. Система, у якій зростання — це одне правило, натомість називає його у своєму chargen: `advance: {rule: grow}`.
- **Режими:** `modes: [guided]` залишає процедуру лише покроковою: `--mode random` відхиляється.

## Компендіум, довідник і глосарій

- **Статті компендіуму** пишуться як для `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. Значення `"roll 2d8"` кидається, коли зі статті створюється запис. Виконайте `didact spawn troll` або перенесіть статті пакета у світ через `didact compendium import <pack>` (`--type loc`, а `--tag coast` — для статей з усіма вказаними тегами).
- **Для кількох систем:** ключ верхнього рівня потрапляє туди, куди його кладе `set`: до блоку системи, якщо в її аркуші є таке поле, інакше до `fields`. Стаття, яку сетинг пише для кількох систем, подає числа кожної в її власному блоці (`mechanics: {my-system: {hp: 12}}`): `pack validate` звіряє кожен блок з аркушем цієї системи, коли її встановлено, і зазначає ключ верхнього рівня, який є і в цьому аркуші, і в аркуші core. Те, що каже блок, лишається в силі: поруч із `mechanics: {my-system: {role: tactician}}` ключ верхнього рівня `role: innkeeper` — поле core, як і все, що лежить під `fields:`. Блок, що називає пакет, який перевіряють, перевіряється за цим пакетом у тому вигляді, у якому він лежить у своїй теці.
- **Розділи довідника** лежать у `reference/*.md`, із front matter (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` знаходить їх; фраза в лапках, якої там немає, пробується за своїми словами.
- **Глосарій** — це `glossary.yaml`: `term: definition` або список `{term, definition, aliases, see}`. `didact define <term>` читає його.

## Тести: `tests/`

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

## Як ділитися пакетами й видаляти їх

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- Пакет, що оголосив `redistributable: false`, не можна експортувати.
- **core** — частина Didact і ввімкнений завжди: на ньому будується будь-яка система, тому його не можна вимкнути чи видалити.
- Інші пакети, що постачаються з Didact, — це файли `.didactpack` у його теці `packs/`. `pack list` показує їх, доки їх не встановлено, а встановлення одного підтягує й потрібні йому пакети, що постачаються.
- `pack update` шукає новіші версії в теці `packs/` Didact і на GitHub (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` вказує інше місце або порожнє значення, щоб не шукати). Нова версія встановлюється поряд зі старою: кампанії використовують свою, доки не виконано `didact campaign upgrade`.
- Одночасно використовується одна ігрова система — система відкритого світу. Світ зберігає систему, з якою його створено (`didact world new <id> --system <pack>`; світ, створений без системи, отримує першу, яку йому дадуть, через `pack enable` або `world set system=`), його кампанії грають за нею, а пакет, якому потрібна інша система (сетинг, написаний для неї), додати не можна: за іншою системою грають в окремому світі.
- `uninstall` відмовляє, доки світ чи кампанія використовують єдину копію пакета (`--force` однаково видаляє). Це не можна скасувати: встановіть .didactpack знову.

## Від книги правил до пакета: чек-лист

Пройдіться механіками книги в такому порядку. Кожна відповідає чомусь із описаного вище:

1. **Розв’язання:** як кидок стає успіхом (перевірка: `success`, `bands`, `auto`).
2. **Кості:** незвичайні кості, символи, кроки (`dice.yaml`, іменовані кості, ланцюжки).
3. **Аркуш:** атрибути, похідні числа (`schemas/`, похідні поля).
4. **Ресурси:** HP, удача, імпульс (поля resource і counter; кроки `set`).
5. **Стани:** стани та їхні ефекти (поля `conditions`; кроки `if`).
6. **Бій:** атаки, шкода, ініціатива (дії; `bag`/`deck` для порядку ходів).
7. **Процедури:** дослідження, подорожі, відпочинок (процедури з підказками).
8. **Таблиці:** усі випадкові таблиці (`tables/`; `pack import` для таблиць у Markdown).
9. **Бестіарій:** монстри й НІП (`compendium/`).
10. **Предмети:** спорядження, закляття, реліквії (`compendium/`, поля slots).
11. **Поради майстрові:** принципи й рекомендації (`GUIDE.md`, `reference/`, `guidance:` у типів).
12. **Створення персонажа:** як створити персонажа (процедура в `chargen/` або `roll:` у кожного поля).

Зазначайте сторінки через `source:` усюди, щоб прогалини впадали в око. Додайте тест-прогін, який створює персонажа, кидає перевірку, проводить бій і виконує процедуру.
