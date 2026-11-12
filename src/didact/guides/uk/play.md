<!-- translated from bef7b2c650cb -->
# Як проходить сесія

Як гра йде через Didact: LLM веде оповідь, а Didact зберігає кожен факт, кидок і зміну.

## Перед першою сесією

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

Світ зберігає систему, з якою його створено, і його кампанії грають за нею: за іншою системою грають в окремому світі. `didact campaign close` відкладає кампанію (її світ залишається відкритим), а `didact campaign open <id>` продовжує її з того самого місця — разом із сесією та всім іншим.

`didact world delete <id>` і `didact campaign delete <id>` видаляють світ чи кампанію, спершу показуючи, що зникне; `--yes` видаляє, а `didact undo` повертає все назад.

`session zero` перелічує запитання, які треба обговорити з гравцем. Спершу йдуть запитання самого пакета. Серед них і опції системи (її варіанти й необов’язкові правила): її правила йдуть за відповідями, а зведення каже, що означає кожна змінена опція. Відповіді потрапляють у кожне зведення.

## Сесія

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Ходи:** кожне повідомлення гравця відкриває хід (хук Claude Code викликає `didact capture`, інші клієнти використовують `turn begin`). `didact undo --turn` скасовує все, що було зроблено у відповідь на це повідомлення: зміни, події та кидки. Стенограма все зберігає.
- **Повернення назад:** `didact undo --to e40` скасовує все після #e40, починаючи з найновішого (`--dry-run` показує перелік): кожна зміна скасовується, а кожен кидок позначається скасованим. Нічого не видаляється: `redo` або повернення до пізнішої зміни поверне все назад.
- **Час:** `didact time advance 1 watch` відлічує таймери, виводить нагадування й запускає тригери часу. `didact remind --list` показує майбутні нагадування, а `didact remind --cancel 2` знімає одне з них. Кампанія починається на початку календаря або тієї дати, яку задає `campaign new --date '4 July 1902'`, а `didact time set '<date>'` змінює її до першої сесії.
- **Місця:** `didact visit <place>` переміщує групу й позначає місце відвіданим. `didact map` показує те, що знає група; недосліджений вихід позначено `?`.
- **Бої:** `didact combat start --party troll`, далі `combat next`, `combat hit freya troll weapon=d8` і `combat end`. Бійці приходять і йдуть посеред бою: `didact combat join wolf-2` (в індивідуальному режимі вони кидають ініціативу) і `didact combat leave troll --why fled`. Нічий хід не пропускається.
- **Речі:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (або до скрині, або на місце); `didact where rope` знаходить предмет. `inv add` знаходить предмет компендіуму за його ID, назвою або псевдонімом.
- **Ваші нотатки:** `didact about sweeney plan='…' doing='…' where='…'` зберігає те, що ви вирішили про когось чи щось. Гравці бачать лише `looks`. `didact log … --about sweeney` додає подію до запису (`--secret`, якщо гравці її не бачать). Докладніше — у `didact guide details`.
- **Світ живе далі:** `didact faction turn`, а також годинники: `didact track new 'The flood' --size 6`. Команда, що бере лише один вид записів, бере назву, спільну з іншими, як запис цього виду: `didact track roll draugr` кидає пул, названий на честь ворога (так само `track tick` лічильник, `quest done` завдання і `visit` місце).

## Оракули, генератори й персонажі

```
didact ask 'Is the ferryman home?' --odds likely        # #o3 ? … → Yes, but…
didact interpret o3 'Home, but drunk and grieving.'     # what it meant, kept with it
didact meaning                                          # two words to interpret: betray · oath
didact gen run pointcrawl --prefill '{"terrain": "Swamp"}' --auto   # a draft: #g4
didact gen edit g4 poi-1.name='Amber Grave'
didact gen commit g4
didact char new                                         # guided: answer with `char choose c5 …`
didact char back c5                                     # take the last answer back: ask it again
didact char new --mode random --prefill '{"name": "Wren", "background": "Cutpurse"}'
didact char advance wren                                # the system's level-up, step by step (#c6)
didact world new fenmoor --system my-system --gen <generator> --prefill '{…}'
```

Нічого зі створеного генератором чи під час створення персонажа не записується до `commit`. Опишіть у `--prefill`, чого хоче гравець, а процедура заповнить прогалини. Запитання перелічує, що означає кожен варіант, якщо це сказано в пакеті (`- Cutpurse: …`): скажіть це гравцеві, щоб він вибирав, знаючи, що отримає.

## Секрети

Типово перегляди безпечні для гравців: `show`, `find`, `sheet`, `map`, `brief`. Вони пропускають:
- секретні записи (`knowledge: secret`);
- розділи `## Secrets` і `## GM notes`;
- поля `secret: true`.

`--gm` показує все. Коли гравці щось дізнаються:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` записує те, що знають гравці, як невеликий сайт, яким можна поділитися чи читати з телефона: група, сторінка на кожен запис, журнал і мапа. Він завжди безпечний для гравців, а повторний експорт у ту саму теку його оновлює. `didact export --as lonelog` записує журнал у нотації Lonelog (`@ ? d: -> =>`, сцени як `S1`, теги на кшталт `[N:Sweeney]`), теж безпечно для гравців.

## Лор: що спливає, коли про щось згадують

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Що враховується:** кожен НІП, місце, предмет і фракція — це картка з ключами з імені та псевдонімів. Записи лору мають `keys`, а рішення спливають через своє правило. Збіг шукається за цілими словами, і множина теж рахується («wolves» збігається з `wolf`).
- **Коли спливає лор:** хук Claude Code сканує кожне повідомлення гравця. `log`, `scene new` і `show` теж приносять щойно активований лор, а запис не повторюється кілька ходів.
- **Налаштування запису:** `--secondary` разом із `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (у ходах або сценах), `--constant` (завжди у зведенні) і `--no-recurse`.
- **Області:** записи потрапляють до кампанії, якщо `--scope` не вказує world, system чи global. Сканування бачить лише цю кампанію, її світ, її систему та global, але ніколи інший світ. Вужчий запис із тим самим ID перекриває ширший.
- **Книги лору інших інструментів:** `didact lore import <file>` читає SillyTavern World Info (і KoboldAI), книгу лору картки персонажа та `.lorebook` з NovelAI; `didact lore export --to <file>` записує World Info. Ключі, логіка, пріоритет, імовірність, групи й таймінг переносяться.

## Зміна історії

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` змінює факт, але зберігає старе значення. Заодно позначає зведення, де згадано Свіні, як застарілі, а `audit` їх перелічує.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` записує рішення. Потім воно з’являється в `rules lookup` і під час запуску цього правила.
- `didact name npc` викидає нове ім’я — ніколи не те, що вже є у світі. Перш ніж вигадати ім’я самостійно, перевірте його через `didact names check <name>`. `didact names forget <name>` знову звільняє ім’я.

## Прибирання

- `didact history --clear` показує, що зникне під час очищення старої історії; `--yes` видаляє це назавжди, разом із видаленими записами, і після цього undo, `diff`, `rewind` і старіші точки збереження туди вже не дістануться (`--before e120` зберігає цю подію й пізніші, `--rolls` видаляє також журнал кидків). Спершу виконайте `didact snapshot`.
- `didact save --remove 'before the dragon'` видаляє точку збереження; `didact undo` повертає її.
- `didact transcript 3 --clear` видаляє стенограму сесії 3 (`--clear --all` — усіх сесій). `didact undo` повертає її, а текст залишається в історії до `history --clear`.
- `didact compendium remove <entry>` видаляє додану вами статтю компендіуму; записи, створені з неї, залишаються.
- `didact snapshot --keep 3` видаляє всі резервні копії, крім трьох найновіших, а `didact snapshot --remove <name>` видаляє одну. Ні те, ні інше не можна скасувати.
- `didact session end` сам створює резервну копію бібліотеки (`snapshot-<time>-auto.zip`) і зберігає п’ять найновіших таких копій; `didact snapshot --list` їх позначає.
- `didact reset` показує, що забере очищення бібліотеки; `--yes` робить її наче щойно встановленою: зникають усі світи, кампанії та записи, історія й пошуковий індекс, а наступна зміна знову буде #e1. Спершу створюється резервна копія бібліотеки (`…-before-reset.zip`); резервні копії залишаються, як і встановлені пакети, якщо не вказано `--packs`. Щоб натомість спробувати Didact на готовій кампанії, `didact sample` збирає приклад кампанії в порожній бібліотеці (`--home` дає їй окрему теку), а `didact serve --demo` щоразу запускає її заново.
- `didact snapshot --restore <name>` показує вміст резервної копії поряд із поточною бібліотекою; `--yes` створює резервну копію бібліотеки в теперішньому вигляді (`…-before-restore.zip`), а потім ставить на її місце вибрану. Нумерація подій і кидків триває. Скасувати відновлення через undo не можна, а от відновити ту страхувальну копію — можна.
