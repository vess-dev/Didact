<!-- translated from 7fe144069f94 -->
# Деталі, хроніка та місцеперебування

Нотатки майстра, що тримають гру послідовною: як усе виглядає і чого прагне, що робить і що замишляє, що з ним сталося і де що перебуває.

## Деталі

Короткі іменовані нотатки до будь-якого запису: людини, предмета, місця, фракції.

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

- **Назви.** Запропоновані назви залежать від виду запису, але підійде будь-яка назва з одного слова:
  - люди: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - предмети: looks, history, where, powers, secret, thoughts;
  - місця: looks, state, history, secret, thoughts;
  - групи: wants, plan, state, history, secret, thoughts.

  Пакет може запропонувати власні для кожного типу (`details: [mood, grudge]` у схемі).
- **Хто що бачить.** Гравці бачать лише `looks`: `show` і `find` пропускають решту, а `--gm` показує все. Коли гравці щось дізнаються, `didact reveal sweeney plan` переносить цю деталь у текст запису під `## Revealed`.
- **`thoughts`** — ваші: навіщо ви це вигадали, до чого воно може привести, що окупити згодом.
- **Оновлюйте їх.** Записувати все не обов’язково. Але коли ви щось вирішуєте (план, образу, куди хтось подівся), запишіть це, щоб наступна сцена чи наступна сесія цьому не суперечила.

## Хроніка: що з ким сталося

Подія журналу може називати записи, яких вона стосується. Тоді вона показується в кожному з них.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` і `about` виводять хроніку запису: що він зробив і що зробили з ним.
- **Секретні події** відбуваються поза увагою гравців. Їх бачить лише майстер (`session show --gm`, `about`, `brief --gm`), і вони ніколи не потрапляють у `export --as story`.
- Використовуйте `--about` для всього, що змінює когось чи щось: зради, боргу, смерті, подарунка, порушеної обіцянки.
- **Виправлення події:** `didact beat edit S1.4 --about tom` додає її до хроніки Тома (або `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), а `didact beat rm S1.4` видаляє її. ID є в `session show`, і обидві команди можна скасувати.
- **Коли змінюються ID:** `merge` або новий slug переносить із собою всі посилання: зв’язки, деталі, записи, яких стосуються події, групу, бій і місцеперебування групи. Коли запис видаляють через `rm`, він також покидає групу й бій. `merge` між типами зберігає те, для чого на аркуші запису, що лишається, є поле, і каже, що пропускає.

## Місцеперебування: де що є

Предмети зберігаються в інвентарях, і тримати їх може будь-що: персонаж, місце, скриня.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Під час сесії переміщення предмета записує подію про того, хто віддав, і того, хто отримав («Sword: Freya → Chest»). Тоді їхні хроніки кажуть, куди поділися речі.
- **Люди й монстри** — відвідувачі місць, а не їхній вміст: зберігайте їхнє місцеперебування в деталі `where`.

## У сценах і боях

- **`combat status --gm`** показує `where`, `doing` і `plan` кожного бійця. Оновлюйте їх під час бою: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (зведення, з якого починається сесія) перелічує все, що в грі (місце, бійців, усіх, кого стосуються події цієї сцени, і групу), з where, doing, plan і state. Там само — останні події за кадром.
