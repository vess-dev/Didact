<!-- translated from 7fe144069f94 -->
# Детали, хроника и местонахождение

Заметки мастера, которые держат игру последовательной: как всё выглядит и чего хочет, что делает и что замышляет, что с ним случилось и где что находится.

## Детали

Короткие именованные заметки к любой записи: человеку, предмету, месту, фракции.

```
didact about sweeney looks='tall, one eye clouded' personality='jovial, greedy'
didact about sweeney wants='buy back the mill' plan='sell the route to the raiders'
didact about sweeney doing='whittling by the fire' where='the back room of the inn'
didact about item:old-sword history='forged for the last king' powers='cuts through wards'
didact about loc:the-ford state='flooded' secret='a drowned shrine under the stones'
didact about sweeney thoughts='built to foreshadow the betrayal; pay it off at the ford'
didact about sweeney                  # the notes, what's still open, chronicle, whereabouts
didact about sweeney --clear doing    # or doing='' 
```

- **Имена.** Предлагаемые имена зависят от вида записи, но подойдёт любое имя из одного слова:
  - люди: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - предметы: looks, history, where, powers, secret, thoughts;
  - места: looks, state, history, secret, thoughts;
  - группы: wants, plan, state, history, secret, thoughts.

  Пакет может предложить свои для каждого типа (`details: [mood, grudge]` в схеме).
- **Кто что видит.** Игроки видят только `looks`: `show` и `find` опускают остальное, а `--gm` показывает всё. Когда игроки что-то узнают, `didact reveal sweeney plan` переносит эту деталь в текст записи под `## Revealed`.
- **`thoughts`** — ваши: зачем вы это придумали, к чему это может привести, что окупить позже.
- **Держите их в актуальном виде.** Записывать всё не обязательно. Но когда вы что-то решаете (план, обиду, куда кто-то ушёл), запишите это, чтобы следующая сцена или следующая сессия этому не противоречила.

## Хроника: что с кем случилось

Событие журнала может называть записи, которых оно касается. Тогда оно показывается в каждой из них.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` и `about` выводят хронику записи: что она сделала и что сделали с ней.
- **Секретные события** происходят вне поля зрения игроков. Они видны только мастеру (`session show --gm`, `about`, `brief --gm`) и никогда не попадают в `export --as story`.
- Используйте `--about` для всего, что меняет кого-то или что-то: предательства, долга, смерти, подарка, нарушенного обещания.
- **Исправление события:** `didact beat edit S1.4 --about tom` помещает его в хронику Тома (или `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), а `didact beat rm S1.4` удаляет его. ID есть в `session show`, и обе команды можно отменить.
- **Когда меняются ID:** `merge` или новый slug переносит с собой все ссылки: связи, детали, записи, которых касаются события, группу, бой и местонахождение группы. Когда запись удаляется через `rm`, она также покидает группу и бой. `merge` между типами сохраняет то, для чего на листе остающейся записи есть поле, и говорит, что опускает.

## Местонахождение: где что находится

Предметы хранятся в инвентарях, и держать их может что угодно: персонаж, место, сундук.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Во время сессии перемещение предмета записывает событие о том, кто отдал и кто получил («Sword: Freya → Chest»). Тогда их хроники говорят, куда ушли вещи.
- **Люди и монстры** — посетители мест, а не их содержимое: храните их местонахождение в детали `where`.

## В сценах и боях

- **`combat status --gm`** показывает `where`, `doing` и `plan` каждого бойца. Обновляйте их по ходу боя: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (сводка, с которой начинается сессия) перечисляет всё, что в игре (место, бойцов, всех, кого касаются события этой сцены, и группу), с where, doing, plan и state. Там же — последние события за кадром.
