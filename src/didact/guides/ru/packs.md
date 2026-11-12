<!-- translated from b1dfa1159ff4 -->
# Пакеты

Пакет — это игровая система, оракул, сеттинг, приключение или дополнение, записанные в виде YAML-файлов плюс необязательный плагин на Python. Это руководство показывает, как написать пакет: превратить книгу правил в пакет или добавить домашний контент.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Пакет можно сделать и из того, что уже есть в библиотеке. `didact pack new my-brew --from-overlay my-system` превращает ваш домашний контент для системы (`compendium add`, записи с `--scope system`, лор) в дополнение, а `didact world export --as setting` превращает мир в пакет сеттинга: его люди, места и лор становятся статьями компендиума и лором пакета, а в другой мир их переносит `compendium import`. Оба оставляют за бортом секреты и заметки мастера, если не указан `--secrets`, и ни один не помечается как доступный для распространения, пока вы не укажете его лицензию.

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

Файл содержит один элемент, список элементов или несколько элементов, разделённых `---`. Каждый элемент задаёт свой ID ключом своего вида: `table: weather`, `check: save`, `type: pc` или `id: troll` для статей компендиума. Ссылайтесь на элементы как `pack.id` (`my-system.save`) или просто по ID, если он есть только в одном включённом пакете.

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

Хак называет свою основу в `extends` и содержит только то, что отличается:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Его элемент с тем же ID заменяет элемент основы, какого бы вида он ни был (таблица, правило, статья компендиума, раздел справочника, термин глоссария). Его `settings` накладываются поверх настроек основы, ключ за ключом: ключ, заданный хаком, целиком заменяет значение основы (его таблицы `names` встают на место таблиц основы), а правила основы тоже читают значения хака. `hides` убирает остальное, что хаку не нужно: `*` совпадает с любой последовательностью символов, решает последний шаблон, совпавший с ID, а шаблон, начинающийся с `!`, сохраняет элемент. То, что хак заменяет, никогда не скрывается. Виды: `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` и `term`. `didact pack validate` предупреждает о шаблоне, который ни с чем не совпадает.

## Выражения

Все условия и формулы используют язык костей (`didact guide dice`), а также:
- **Значения:** `@name` читает значение: `@roll`, `@who.STR`, `@settings.x`. `$name` сначала подставляет текст параметра, так что `@who.$attr` превращается в `@who.STR`. Параметр со свободным текстом читайте как `@name`, а не в кавычках (`'$name'`): апостроф в его тексте закрыл бы кавычки (`pack validate` предупреждает).
- **Логика:** `and`, `or`, `not` и `in` (`'deprived' in @who.conditions`).
- **Литералы:** текст (`'travel'`) и `true`/`false`.
- **Функции:** `if(cond, a, b)` бросает только ту ветвь, которую выбирает. `default(@thread.flashpoint, 0)` — это значение или запасное, если оно не задано. `sum`, `count` (`count(@roll.dice, 6)` считает шестёрки), `min`, `max`, `any` и `all` принимают списки.

## Листы: `schemas/`

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

| Вид | Хранит | Параметры |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | простое значение | min, max; `values` для enum |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: `@hp` — значение, `@hp.max` — предел | range; min; max или max_field; die |
| `counter` | число | min, max, thresholds, occupies (поле slots) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | предметы (`Rope` или `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | то, что указано в названии | `to` (для refs), `allowed` |
| `derived` | вычисляется, никогда не хранится | expr |

Каждое поле также принимает `label`, `help`, `default`, `required` и `roll`: `new pc Hero --fill` или значение `"roll"` бросает его через журнал. Типы из пакета `core` хранят в `fields` текст, не зависящий от системы. Типы системы хранят её числа в `mechanics.<system>`. `set hero hp-=2` находит поле, ограничивает значение и сообщает о любом переполнении. `+=` добавляет в список: `list` (как `slots`) сохраняет и повторно добавленное значение, `tags`, `conditions` и `refs` хранят его один раз, а `-=` убирает все копии.

**Хуки** говорят, что происходит, когда значение пересекает границу. Они срабатывают при каждом изменении (`set`, `inv`, шаг правила `set`), но только когда граница пересечена: 3 → 0 срабатывает, 0 → 0 — нет. Правки с `--force` их пропускают.

| Хук | Срабатывает, когда |
|---|---|
| `on_zero` | число или `{value}` достигает 0 |
| `on_full` (`when_full` у slots) | оно достигает своего max, size или capacity |
| `thresholds: {10: …, 20: …}` (counters) | оно поднимается выше каждой отметки |

Действие — это текст (заметка для LLM), `{set: {hp: 0}}` или `{condition: paralyzed}` на той же записи, `{trigger: death}` (запускает это правило с `who` = запись) или список из них.

**Инвентарь** (`didact inv …`) работает с полем `slots` листа:
- **Место:** предметы занимают `size` × `count`, а счётчики, которые `occupies` это поле, — своё значение. Сверх `capacity` добавить нельзя без `--force`.
- **Группы:** `groups: {backpack: 6, body: 4}` даёт каждой группе своё место, а также свои столбцы и суммы: `@inventory.body.armor` — только то, что надето или в руках, `@inventory.body.free` — оставшееся в ней место.
- **Использования:** `uses: 3` уменьшается с каждым `inv use`. `uses: d8` — кость расхода: 1–2 понижает её на шаг. Израсходованный предмет исчезает, если у него нет `recharge` или `keep: true`. Из нескольких предметов с одним именем имя означает первый; чтобы потратить использование (`inv use`, `use:` правила, `set …uses-=1`), — первый, у которого оно ещё осталось.
- **Собственные ключи предмета:** `didact set freya inventory.sword.damage=d10` (как и `set: who.inventory.$item.damage` в правиле) меняет один из них, а предмет указывается как в `inv`, частью имени или всем именем, с пробелами и точками (`'inventory.12.7mm pistol.damage=d10'`, в кавычках для оболочки); `uses` и `charges` считаются как в поле `uses` (`charges+=2` останавливается на максимуме), а место проверяется так же, как при `inv add`. Правило читает такой ключ как `@{who.inventory.$item.damage}` (кость расхода — как её кость, использования — как их число); предмет или ключ, которого нет, читается как отсутствующий, так что `default(…)` даёт своё запасное значение.
- **Компендиум:** статьи типа `item` (или weapon, armor, relic, …, или собственного типа пакета, который расширяет один из них через `extends`) передают `inv add` свои данные; их находят по ID, по имени или по псевдониму (если псевдоним общий у двух — назовите нужную как `pack.id`); любое другое имя, вместе с `:`, — собственное имя предмета.

## Таблицы: `tables/`

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

Другие формы:
- **Взвешенные списки:** `entries` в виде списка, с `weight:` у каждой строки.
- **Столбцы:** `columns: [a, b]` бросает по каждому столбцу строки отдельно. Простая строка (не список) заполняет все столбцы, так что `columns: [first, second]` над списком слов означает «бросить по этому списку дважды». `labels: false` убирает названия столбцов из результата («Abandon · Advantage»). `read: "It's a {first} {second} with {third} {fourth} inside."` читает столбцы как фразу.
- **Справочные таблицы:** `lookup: hp_lost` или `[odds, chaos]` для двумерной таблицы.
- **Повторы:** `duplicates: reroll | keep | make_it_worse` для «бросить дважды».
- **В два этапа:** строка, которая ведёт к броску по другой таблице (`{table: lightning}` вместо текста или `then:` после него), приносит с собой данные этого броска: правило или черновик, где она выпадает, читает и те и другие — сначала собственные ключи строки, затем ключи первой таблицы, по которой бросают следом. `--prefill` может назвать строку ниже, на любой глубине (`Ring of the Hunt`), с данными каждой строки на пути: из двух с одним именем имеется в виду ближайшая (затем первая), строка, ведущая дальше, бросается дальше оттуда, а похожая на одну из них, но не совпадающая ни с одной, отклоняется с указанием ближайшей. Пошаговый черновик предлагает первый шаг, когда его строки говорят, что они такое (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): выбор строки бросает по следующей таблице, как бросок, который на неё выпал.
- **Чтение в обе стороны:** `both_ways: true` у таблицы d66 добавляет обратное прочтение: 31 даёт и 13, а читающий выбирает.
- **Что означает строка:** `about: "Knows: {skills}. Also known as: {aka}."` подставляет данные каждой строки (список читается как `a, b`; `{text}` — сама строка), чтобы сказать, что она даёт, когда её предлагает выбор; если у строки есть своя `note:`, это говорит она. Если нет ни того, ни другого, строку, в данных которой есть `id`, называющий статью компендиума, описывает эта статья.
- **Колоды и мешочки:** `deck: tarot` с `cards` (или `standard: true`); `bag: initiative` с `tokens`.

Проверка убеждается, что каждый результат, который могут выбросить кости, попадает на строку.

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

Действия и процедуры — это списки шагов, а триггеры — шаги с условием `when:`. Шаги такие:

| Шаг | Что делает |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | бросок с записью в журнал; связывает `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`; `{…}` сначала заполняется, как в любом тексте, так что кости, которые значение хранит как текст, бросаются (`{@{who.inventory.$item.damage}}`), и журнал их показывает: значение, которое не кости, отклоняется, как и `roll: "@die"` с таким текстом, который ничего не бросает; набор бросков (`{d8, d6}kh1`) остаётся набором |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | вычисляет значения; как и в `value` у `set`, текст с `{…}` — это шаблон, а голое слово — текст; в любом заполняемом тексте `{{` и `}}` пишут саму фигурную скобку |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (или `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | меняет запись: с проверкой, ограничением, возможностью отмены; `set: who.$attr` задаёт поле, указанное параметром, а `set: who.inventory.$item.damage` — ключ предмета в инвентаре записи (см. «Инвентарь»); `-=` убирает значение из списка, а значение, которого в нём нет, ничего не меняет (об этом скажет заметка; значение, которого в нём никогда не может быть, отклоняется); `unset:` убирает поле, как `set --unset` |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | даёт записи предмет или забирает его у неё, как это делают `inv add` и `inv drop`: данные берутся из компендиума, достаточно уникальной части названия, а место и хуки поля проверяются |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | использует предмет, который несёт запись, как это делает `inv use`: использования или заряды уменьшаются, кость расхода бросается и на 1–2 понижается на шаг, а израсходованный предмет исчезает, если он не перезаряжается и не сохраняется; из нескольких с таким именем — первый, у которого осталось использование; связывает `@torch.out` (его последнее использование ушло), `@torch.gone` (от него ничего не осталось), `@torch.left`, `@torch.die` и `@torch.rolled` (`as:` по умолчанию — `use`) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | сразу создаёт запись, описанную так же, как в шаге `entity` черновика (см. ниже), и проверяет её по листу; `as:` (иначе её `key`, иначе её тип) связывает её как запись, которую читают и меняют как параметр `ref` (`pool: "@bleeding"`, `@bleeding.name`), и никогда не совпадает с именем параметра; без `key:` ни одно поле не принимается за ключ (`kind: track` остаётся как написано); если запись этого типа с таким именем здесь уже есть, берётся она как есть, так что повторный запуск правила ничего нового не создаёт |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | выполняет проверку и связывает её исход |
| `do: other-action`, `with: {…}`, `as: trip` | запускает другое правило; `@trip` — его исход, а `@trip.<name>` — то, что оно связало (`@trip.found` для его `let: {found: 2}`, `@trip.luck` для его `roll: d6`, `as: luck`); `as:` по умолчанию — его ID |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | бросок по таблице с записью в журнал; связывает текст и `data` строки (`@scar.<key>`, а ключи вложенного словаря — по их пути: `@scar.cost.hp`), а также данные любой таблицы, по которой бросают следом; список предметов (`[Rope, {name: Laser, damage: d8}]`) читается как их имена (`count(@scar.gear)`, `'Laser' in @scar.gear`), а переданный шагу как есть (`apply: "@scar.gear"`) — это сами предметы; список других словарей читает только шаг |
| `table: "setting-{@drop.difficulty}-terrain"` | вычисляемая таблица: `{…}` и `$param` подставляются |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | несколько результатов списком (`distinct` перебрасывает повторы) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | ветвление |
| `repeat: "@count"`, `as: i`, `steps: […]` | цикл: шаги повторяются заданное число раз, а `@i` ведёт счёт с 1 |
| `for: pcs` (или `party`), `as: member`, `steps: […]` | шаги выполняются по разу для каждого персонажа игрока (или члена группы), как `@member`: это запись, подобная той, что связывает `entity:` (`@member.name`, `set: member.fatigue`); `as:` никогда не принимает имя параметра, так что собственный `who` правила остаётся при нём |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | вывод для LLM |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (или `every: 1 day`) | напоминание, которое наступает по мере хода игрового времени, как те, что ставит `didact remind` |
| `reroll: roll`, `keep_if: "@face == 6"` | перебрасывает часть костей броска (механика рывка) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | бросает по значению-списку (списки оракула): связывает строку, `@who.choose` (пустая строка) и `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | бросает убывающий пул счётчика так же, как `track roll` (кости с 1-3 выбывают; кости из `drop` убираются первыми, кости из `extra` бросаются вместе с ним) или только убирает кости (`mode: drop`: рывок, отметка); следом срабатывают связанные фазы и событие пула; связывает `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

Исход проверки доступен правилу, которое её запустило (`check: … as: answer` даёт `@answer`), как и её флаги: `'random-event' in @answer.flags`. Значения `with:` вычисляются, если содержат `@`, заполняются, если содержат `$param` или `{…}` («Does $npc flee?»), а иначе передаются как написаны. Правило с параметром `oracle` получает запись состояния оракула кампании без явного указания. Параметр `ref` с `to: monster` берёт запись этого типа: имя, общее с другой записью (пул врага, названный как его карточка), означает запись этого типа.

Триггеры запускаются сами, когда происходит их событие, и только если выполняется их `when:`:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Любое правило (в том числе генератор и создание персонажей) может читать `@system` (ID системы, по которой играет мир: так сеттинг, написанный для двух систем, может их различить), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` и `@time.is_night`, а при календаре с месяцами — ещё и `@time.month`, `@time.month_name`, `@time.day_of_month` и `@time.year`; пока идёт бой — `@combat.round` и `@combat.fighters` (ID его участников). Триггер времени может читать ещё и `@time.passed` — только что прошедшие секунды, триггер `combat_start` или `combat_end` читает бой, который начинается или заканчивается (их запускают `combat start` и `combat end`; уход бойца не завершает бой), а правило, запущенное триггером, читает то же, что и сам триггер. Триггер с обязательными параметрами запускается только через `didact do` или хук поля (`who` = запись). Триггеры `on: manual` запускаются только по вызову. `for: pcs` (или `party`) запускает триггер по разу для каждого персонажа игрока (или члена группы), как `who`: например, опыт после каждой сессии. Триггер, завершившийся ошибкой, останавливает команду, которая его вызвала, и говорит, какой это был триггер и как продолжить без него (`didact override add trigger <id> --data '{"on": "manual"}'`).

Календарь задаётся в `settings` пакета: календарь пакета сеттинга важнее календаря системы, а собственный календарь мира (`calendar:` в его `world.yaml`) важнее обоих:

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

`leap: 4` делает месяц на день длиннее каждый 4-й год, а `leap: [4, 100, 400]` — каждый 4-й, но не каждый 100-й, зато снова каждый 400-й: каждое число отменяет предыдущее. `weekday` называет день недели начала (иначе это первый день недели), а `year` — то, как дата пишет свой год, и в датах, которые показывает Didact, и в тех, что он читает (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` проверяет все три. Кампания может начаться в другую дату календаря, до его начала или после: `didact campaign new <id> --date '4 July 1902'` или `didact time set '<date>'` до её первой сессии. День недели, написанный перед датой, проверяется: решает дата, а заметка говорит, когда она приходится на другой день.

Опции — это варианты и необязательные правила системы, которые каждая кампания выбирает на нулевой сессии:

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

`didact campaign profile lethality=deadly supplies=on` сохраняет их (или страница «Настройки» веб-приложения). Правила, создание персонажей и генераторы читают их (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): ответ важнее того, что следует из другой опции, а то — важнее значения по умолчанию. То, что следует из опции, учитывается по всей цепочке (стиль, задающий смертоносность, задаёт и то, что следует из этой смертоносности), а из двух следствий важнее более близкое. Сводка перечисляет те, что отличаются от значения по умолчанию, с их смыслом, чтобы ведущий применял то, чего не могут правила. Генератор, который не может работать при них, останавливается шагом `stop:` с причиной, и черновик не создаётся.

## Оракулы: `oracles/`

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

- **Вопросы:** `didact ask '…' --odds likely` выполняет проверку `ask`. Ответ — её исход (диапазон), и флаги идут вместе с ним.
- **Состояние:** оно хранится в записи, которую проверка получает как `oracle`. Проверка меняет его через `set: oracle.chaos += 1`.
- **Списки:** `lists: {names: […], method: sections, most: 3}` хранит взвешенные списки в этой записи. Ими управляют `didact lists add|drop|roll|show`, а правила бросают по ним через `pick`. `sections` бросает сначала раздел из пяти строк, затем строку в нём (пустая строка означает «выберите сами»); `uniform` даёт всем строкам равные шансы.
- **Дополнительно для проверки:** `didact ask '…' --with as_rule=true` передаёт проверке оракула дополнительные параметры.
- **Журнал:** каждый ответ нумеруется (`#o12`) и записывается в журнал, а `didact interpret o12 '…'` сохраняет его толкование. Запасной вариант — оракул `yes-no` из пакета core.

## Генераторы и создание персонажей: `generators/`, `chargen/`

И то и другое — процедуры, которые строят **черновик**. Они используют все шаги правил (`roll`, `table`, `if`, `let`, `prompt`, …), а также эти:

| Шаг | Что делает |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | добавляет запись в черновик (ключи `poi-1`, `poi-2`, …); поле или связь, называющие ключ, который написал пакет (`key:` или имя из `as:`), при принятии становятся ID этой записи, так что выбирайте ключи, которых ни одно поле не содержит как текст (у сущности без того и другого ключа для замены нет); `from: "@relic.id"` берёт за основу статью компендиума (её тип, имя и поля) |
| `choose: {from: [a, b], as: x}` (или `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | выбор; в пошаговом режиме черновик ждёт `choose`; `exclude` исключает прежние варианты (выброшенный бросается заново); `records:` добавляет к вариантам записи этого типа, которые есть здесь, по id (созданные в игре); `answer:` делает выбор без вопроса, когда его значение — один из вариантов (собственный путь персонажа) |
| `choose_or_roll: {table: backgrounds, as: background}` | выбор, который могут сделать кости; данные выбранной строки — `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | броски в персонажа |
| `swap: {among: [STR, DEX, WIL], optional: true}` | поменять местами два значения или оставить |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | распределить фиксированный набор |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | купить значения в пределах бюджета (`default: random` в случайном режиме тратит его случайно) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | список идёт в инвентарь; словарь задаёт поля (списки суммируются) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | добавляет к полю персонажа (или сущности черновика): числа складываются, остальное добавляется в список; если добавлять нечего — ничего страшного |
| `remove: {field: talents, value: "@old"}` | убирает что-то из поля-списка (заменённый талант, разрешённые узы); если убирать нечего — ничего страшного |
| `roll_tables: [physique, vice]` | бросает по таблицам в `traits`; `data.gear` строки идёт в инвентарь, а `data.add: {gold: 20}` добавляет к полям |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | имя; `name: {prompt: …}`, если бросать не по чему, ждёт ввода, даже в случайном режиме |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | вопрос, на который годится любой ответ (цель, имя другой записи): черновик ждёт его даже в случайном режиме, если он не заполнен заранее; `field:` сохраняет ответ |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | пойнткраул: бросок костей на карту с записью в журнал, пути (всегда связные), расстояния, скрытые пути (см. ниже) |

Шаг map принимает и другое — для процедур бросания костей на карту из книги:

| Ключ | Что делает |
|---|---|
| `regions: terrain` | эти сущности тоже бросаются; каждое место входит в ближайшую (свой `region`) |
| `hidden: 6`, `conditional: 5` | d6 на каждый путь: при этом числе или выше — скрытый или условный путь (скрытые пути не видны на карте игроков) |
| `describe: [path-feature, path-condition]` | таблицы, бросаемые для каждого пути, сохраняются как его `details` |
| `entrance: true`, `exit: true` | место, ближайшее к краю, — вход; остальные нумеруются от него вдоль путей (`map.n`), пути ведут прочь от него, а выход — дальнее место у края, с последним номером |
| `number: "{@dungeon_name}, room {@n}"` | переименовывает пронумерованные места (их ключи в черновике следуют за ними: `room-1` — это комната 1) |

Таблица для броска на карту может называть следующие таблицы в данных своих строк, так что процедура читается как в книге: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, затем `table: "{@drop.what}"`. Незаданные поля-списки (conditions, lists, tags) читаются как пустые списки, так что `'deprived' in @who.conditions` работает с самого начала.

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

Процедура chargen с `advances:` не создаёт запись, а меняет её: это повышение уровня в системе.

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

- **Одна запись:** генератор с `creates: npc` строит эту запись так же, как создание персонажа строит персонажа (`apply`, `add`, `name`, `field:`); его шаги `entity` добавляют записи рядом с ней, а ссылка `to: character` указывает на неё.
- **Запуск:** `gen run` и `char new` создают черновик (`#g7`, `#c3`) и ничего не записывают. `stop:` завершает его, ничего не создав: под `if:`, читающим опцию кампании, его подсказка указывает на опции (`didact session zero`); иначе его собственные слова говорят, что сделать вместо этого.
- **Решения:** `--prefill '{…}'` решает заранее — по имени, которое связывает шаг (`as:`): одно значение отвечает на все вхождения, список — по одному на вхождение (для `choose` с `count` список — это весь выбор целиком). Значения `let` тоже можно задать заранее (`{"hp": 6}`), а имя, `ask` или `let` сохраняют любой текст в том виде, в каком он задан. Значение для выбора среди известных вариантов (`choose`, строка таблицы) — это вариант, который оно называет (как он написан или в другом регистре), по `id` его строки или по броску, который на него попадает (`{"group": 3}`), и оно приносит данные этой строки; значение, близкое к одному из вариантов, но не совпадающее ни с одним, отклоняется с указанием ближайшего, а любое другое — это собственный ответ, без данных. `--auto` (или `char new --mode random`) оставляет остальное на волю костей. Иначе черновик ждёт на каждом выборе.
- **Описание:** выбор говорит выбирающему игроку, что означает каждый вариант: `note:` строки таблицы или `about:` её таблицы, иначе статья компендиума, которую строка называет (`id` в её данных), или та, которой является сам вариант (выбор среди ID компендиума показывает имя каждой статьи): её `tagline` и `summary`, её `description` или `effect`, иначе первый абзац её текста.
- **Шаг назад:** `char back` (или `gen back`) отменяет последний ответ, бросок или правку, так что черновик снова задаёт тот же вопрос; сделанные на этом шаге броски отмечаются как отменённые.
- **Продолжение:** продолженный черновик воспроизводит свой след: каждое брошенное или выбранное значение, по одному разу и по порядку (включая бросок на карту), так что ничего не бросается дважды и ничего уже решённого не меняется.
- **Запись:** `commit` сохраняет записи, проверяя их по листам.
- **Развитие:** черновик с `advances:` начинается с копии записи (со значениями по умолчанию из её листа), его шаги читают запись как `@who`, а значения черновика — как `@character.*`, и `commit` записывает только то, что изменилось, с проверкой, как у `set`; записи из его шагов `entity` (сюжетная линия новых уз) создаются рядом с ней: ссылка `to: character` указывает на запись, а поле, называющее ключ, хранит ID соответствующей записи, как при создании персонажа (`apply: {blood: "@pool"}`). `stop:` объясняет, почему пока нельзя (не хватает опыта), и черновик не создаётся. Система, в которой рост — это одно правило, вместо этого называет его в своём chargen: `advance: {rule: grow}`.
- **Режимы:** `modes: [guided]` оставляет процедуру только пошаговой: `--mode random` отклоняется.

## Компендиум, справочник и глоссарий

- **Статьи компендиума** пишутся как для `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. Значение `"roll 2d8"` бросается когда по статье создаётся запись. Выполните `didact spawn troll` или перенесите статьи пакета в мир с помощью `didact compendium import <pack>` (`--type loc`, а `--tag coast` — для статей со всеми указанными тегами).
- **Для нескольких систем:** ключ верхнего уровня попадает туда, куда его кладёт `set`: в блок системы, если в её листе есть такое поле, иначе в `fields`. Статья, которую сеттинг пишет для нескольких систем, даёт числа каждой в её собственном блоке (`mechanics: {my-system: {hp: 12}}`): `pack validate` сверяет каждый блок с листом этой системы, когда она установлена, и отмечает ключ верхнего уровня, который есть и в этом листе, и в листе core. То, что говорит блок, остаётся в силе: рядом с `mechanics: {my-system: {role: tactician}}` ключ верхнего уровня `role: innkeeper` — поле core, как и всё, что лежит под `fields:`. Блок, называющий проверяемый пакет, проверяется по этому пакету в том виде, в каком он лежит в своей папке.
- **Разделы справочника** лежат в `reference/*.md`, с front matter (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` находит их; фраза в кавычках, которой там нет, пробуется по своим словам.
- **Глоссарий** — это `glossary.yaml`: `term: definition` или список `{term, definition, aliases, see}`. `didact define <term>` читает его.

## Тесты: `tests/`

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

## Как делиться пакетами и удалять их

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- Пакет, объявивший `redistributable: false`, нельзя экспортировать.
- **core** — часть Didact и включён всегда: на нём строится любая система, поэтому его нельзя отключить или удалить.
- Остальные пакеты, поставляемые с Didact, — это файлы `.didactpack` в его папке `packs/`. `pack list` показывает их, пока они не установлены, а установка одного подтягивает и нужные ему поставляемые пакеты.
- `pack update` ищет новые версии в папке `packs/` Didact и на GitHub (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` указывает другое место или пустое значение, чтобы не искать). Новая версия устанавливается рядом со старой: кампании используют свою, пока не выполнен `didact campaign upgrade`.
- Одновременно используется одна игровая система — система открытого мира. Мир сохраняет систему, с которой был создан (`didact world new <id> --system <pack>`; мир, созданный без системы, получает первую, которую ему дадут, через `pack enable` или `world set system=`), его кампании играют по ней, а пакет, которому нужна другая система (сеттинг, написанный для неё), добавить нельзя: по другой системе играют в отдельном мире.
- `uninstall` отказывается, пока мир или кампания используют единственную копию пакета (`--force` всё равно удаляет). Это нельзя отменить: установите .didactpack заново.

## От книги правил к пакету: чек-лист

Пройдитесь по механикам книги в таком порядке. Каждая соответствует чему-то из описанного выше:

1. **Разрешение:** как бросок становится успехом (проверка: `success`, `bands`, `auto`).
2. **Кости:** необычные кости, символы, шаги (`dice.yaml`, именованные кости, цепочки).
3. **Лист:** атрибуты, производные числа (`schemas/`, производные поля).
4. **Ресурсы:** HP, удача, импульс (поля resource и counter; шаги `set`).
5. **Состояния:** состояния и их эффекты (поля `conditions`; шаги `if`).
6. **Бой:** атаки, урон, инициатива (действия; `bag`/`deck` для порядка ходов).
7. **Процедуры:** исследование, путешествия, отдых (процедуры с подсказками).
8. **Таблицы:** все случайные таблицы (`tables/`; `pack import` для таблиц в Markdown).
9. **Бестиарий:** монстры и НИП (`compendium/`).
10. **Предметы:** снаряжение, заклинания, реликвии (`compendium/`, поля slots).
11. **Советы мастеру:** принципы и рекомендации (`GUIDE.md`, `reference/`, `guidance:` у типов).
12. **Создание персонажа:** как создать персонажа (процедура в `chargen/` или `roll:` у каждого поля).

Указывайте страницы через `source:` везде, чтобы пробелы бросались в глаза. Добавьте тест-прогон, который создаёт персонажа, бросает проверку, проводит бой и выполняет процедуру.
