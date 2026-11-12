<!-- translated from bef7b2c650cb -->
# Как проходит сессия

Как игра идёт через Didact: LLM ведёт повествование, а Didact хранит каждый факт, бросок и изменение.

## Перед первой сессией

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

Мир сохраняет систему, с которой был создан, и его кампании играют по ней: по другой системе играют в отдельном мире. `didact campaign close` откладывает кампанию (её мир остаётся открытым), а `didact campaign open <id>` продолжает её с того же места — вместе с сессией и всем остальным.

`didact world delete <id>` и `didact campaign delete <id>` удаляют мир или кампанию, сначала показывая, что уйдёт; `--yes` удаляет, а `didact undo` возвращает всё обратно.

`session zero` перечисляет вопросы, которые нужно обсудить с игроком. Сначала идут вопросы самого пакета. Среди них и опции системы (её варианты и необязательные правила): её правила следуют ответам, а сводка говорит, что значит каждая изменённая опция. Ответы попадают в каждую сводку.

## Сессия

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Ходы:** каждое сообщение игрока открывает ход (хук Claude Code вызывает `didact capture`, другие клиенты используют `turn begin`). `didact undo --turn` отменяет всё, что было сделано в ответ на это сообщение: изменения, события и броски. Стенограмма всё сохраняет.
- **Возврат назад:** `didact undo --to e40` отменяет всё после #e40, начиная с самого нового (`--dry-run` показывает список): каждое изменение отменяется, а каждый бросок отмечается как отменённый. Ничего не удаляется: `redo` или возврат к более позднему изменению вернёт всё обратно.
- **Время:** `didact time advance 1 watch` отсчитывает таймеры, выводит напоминания и запускает триггеры времени. `didact remind --list` показывает предстоящие напоминания, а `didact remind --cancel 2` снимает одно из них. Кампания начинается в начале календаря или в дату, которую задаёт `campaign new --date '4 July 1902'`, а `didact time set '<date>'` меняет её до первой сессии.
- **Места:** `didact visit <place>` перемещает группу и отмечает место как посещённое. `didact map` показывает то, что знает группа; неисследованный выход обозначен `?`.
- **Бои:** `didact combat start --party troll`, затем `combat next`, `combat hit freya troll weapon=d8` и `combat end`. Бойцы приходят и уходят посреди боя: `didact combat join wolf-2` (в индивидуальном режиме они бросают инициативу) и `didact combat leave troll --why fled`. Ничей ход не пропускается.
- **Вещи:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (или в сундук, или в место); `didact where rope` находит предмет. `inv add` находит предмет компендиума по его ID, имени или псевдониму.
- **Ваши заметки:** `didact about sweeney plan='…' doing='…' where='…'` сохраняет то, что вы решили о ком-то или о чём-то. Игроки видят только `looks`. `didact log … --about sweeney` добавляет событие в запись (`--secret`, если игроки его не видят). Подробнее — в `didact guide details`.
- **Мир живёт дальше:** `didact faction turn`, а также часы: `didact track new 'The flood' --size 6`. Команда, принимающая только один вид записей, берёт имя, общее с другими, как запись этого вида: `didact track roll draugr` бросает пул, названный по врагу (так же `track tick` счётчик, `quest done` задание и `visit` место).

## Оракулы, генераторы и персонажи

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

Ничего из созданного генератором или при создании персонажа не записывается до `commit`. Опишите, чего хочет игрок, в `--prefill`, а процедура заполнит пробелы. Вопрос перечисляет, что означает каждый вариант, если это сказано в пакете (`- Cutpurse: …`): сообщите это игроку, чтобы он выбирал, зная, что получит.

## Секреты

По умолчанию представления безопасны для игроков: `show`, `find`, `sheet`, `map`, `brief`. Они опускают:
- секретные записи (`knowledge: secret`);
- разделы `## Secrets` и `## GM notes`;
- поля `secret: true`.

`--gm` показывает всё. Когда игроки что-то узнают:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` записывает то, что знают игроки, в виде небольшого сайта, которым можно поделиться или читать с телефона: группа, страница на каждую запись, журнал и карта. Он всегда безопасен для игроков, а повторный экспорт в ту же папку его обновляет. `didact export --as lonelog` записывает журнал в нотации Lonelog (`@ ? d: -> =>`, сцены как `S1`, теги вида `[N:Sweeney]`), тоже безопасно для игроков.

## Лор: что всплывает, когда о чём-то упоминают

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Что учитывается:** каждый НИП, место, предмет и фракция — это карточка с ключами из имени и псевдонимов. У записей лора есть `keys`, а решения всплывают через своё правило. Совпадение ищется по целым словам, и множественное число тоже считается («wolves» совпадает с `wolf`).
- **Когда всплывает лор:** хук Claude Code сканирует каждое сообщение игрока. `log`, `scene new` и `show` тоже приносят только что сработавший лор, а запись не повторяется несколько ходов.
- **Настройка записи:** `--secondary` вместе с `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (в ходах или сценах), `--constant` (всегда в сводке) и `--no-recurse`.
- **Области:** записи попадают в кампанию, если `--scope` не указывает world, system или global. Сканирование видит только эту кампанию, её мир, её систему и global, но никогда другой мир. Более узкая запись с тем же ID перекрывает более широкую.
- **Лорбуки других программ:** `didact lore import <file>` читает World Info из SillyTavern (и KoboldAI), лорбук карточки персонажа и `.lorebook` из NovelAI; `didact lore export --to <file>` записывает World Info. Ключи, логика, приоритет, вероятность, группы и тайминги переносятся.

## Изменение истории

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` меняет факт, но сохраняет старое значение. Заодно помечает сводки, где упоминается Суини, как устаревшие, а `audit` их перечисляет.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` записывает решение. Затем оно появляется в `rules lookup` и при запуске этого правила.
- `didact name npc` выбрасывает новое имя — никогда не то, что уже есть в мире. Прежде чем придумать имя самому, проверьте его через `didact names check <name>`. `didact names forget <name>` снова освобождает имя.

## Уборка

- `didact history --clear` показывает, что уйдёт при очистке старой истории; `--yes` удаляет это навсегда, включая удалённые записи, и после этого undo, `diff`, `rewind` и более старые точки сохранения туда уже не дотянутся (`--before e120` сохраняет это событие и более поздние, `--rolls` удаляет и журнал бросков). Сначала выполните `didact snapshot`.
- `didact save --remove 'before the dragon'` удаляет точку сохранения; `didact undo` возвращает её.
- `didact transcript 3 --clear` удаляет стенограмму сессии 3 (`--clear --all` — всех сессий). `didact undo` возвращает её, а текст остаётся в истории до `history --clear`.
- `didact compendium remove <entry>` удаляет добавленную вами статью компендиума; записи, созданные из неё, остаются.
- `didact snapshot --keep 3` удаляет все резервные копии, кроме трёх самых новых, а `didact snapshot --remove <name>` удаляет одну. Ни то ни другое нельзя отменить.
- `didact session end` сам создаёт резервную копию библиотеки (`snapshot-<time>-auto.zip`) и хранит пять самых новых таких копий; `didact snapshot --list` их помечает.
- `didact reset` показывает, что заберёт очистка библиотеки; `--yes` делает её как только что установленной: уходят все миры, кампании и записи, история и поисковый индекс, а следующее изменение снова будет #e1. Сначала создаётся резервная копия библиотеки (`…-before-reset.zip`); резервные копии остаются, как и установленные пакеты, если не указан `--packs`. Чтобы вместо этого попробовать Didact на готовой кампании, `didact sample` собирает пример кампании в пустой библиотеке (`--home` даёт ей отдельную папку), а `didact serve --demo` каждый раз запускает её заново.
- `didact snapshot --restore <name>` показывает содержимое резервной копии рядом с текущей библиотекой; `--yes` создаёт резервную копию библиотеки в нынешнем виде (`…-before-restore.zip`), а затем ставит на её место выбранную. Нумерация событий и бросков продолжается. Отменить восстановление через undo нельзя, а вот восстановить ту страховочную копию — можно.
