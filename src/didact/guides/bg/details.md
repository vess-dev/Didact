<!-- translated from 7fe144069f94 -->
# Подробности, хроника и местонахождение

Бележките на водещия, които пазят играта последователна: как изглеждат нещата и какво искат, какво правят и какво планират, какво им се е случило и къде се намира всичко.

## Подробности

Кратки именувани бележки към всеки запис: човек, предмет, място, фракция.

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

- **Имена.** Предложените зависят от вида на записа, а става всяко име от една дума:
  - хора: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - предмети: looks, history, where, powers, secret, thoughts;
  - места: looks, state, history, secret, thoughts;
  - групи: wants, plan, state, history, secret, thoughts.

  Пакетът може да предлага свои имена за всеки тип (`details: [mood, grudge]` в схема).
- **Кой какво вижда.** Играчите виждат само `looks`: `show` и `find` пропускат останалото, а `--gm` показва всичко. Когато играчите научат някоя бележка, `didact reveal sweeney plan` я премества в текста на записа под `## Revealed`.
- **`thoughts`** са ваши: защо сте създали нещо, накъде може да води, какво да развиете по-късно.
- **Поддържайте ги актуални.** Не е нужно да записвате всичко. Но когато решите нещо (план, злоба, къде е отишъл някой), запишете го, за да му остане вярна следващата сцена или следващата сесия.

## Хрониката: какво се е случило с кого

Събитие в дневника може да посочи записите, които засяга. Тогава то се показва във всеки от тях.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` и `about` показват хрониката на записа: какво е направил и какво е било направено с него.
- **Тайните събития** се случват скрито от играчите. Появяват се само в изгледите на водещия (`session show --gm`, `about`, `brief --gm`) и никога в `export --as story`.
- Използвайте `--about` за всичко, което променя някого или нещо: предателство, дълг, смърт, подарък, нарушено обещание.
- **Поправка на събитие:** `didact beat edit S1.4 --about tom` го слага в хрониката на Том (или `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), а `didact beat rm S1.4` го изтрива. ID-тата са в `session show`, и двете действия могат да се отменят.
- **Когато ID-тата се сменят:** `merge` или нов slug пренася всяка препратка: връзките, подробностите, записите, които събитията засягат, групата, битката и местоположението на групата. Когато запис се изтрие с `rm`, той напуска и групата или битката. `merge` между типове запазва това, за което листът на оставащия запис има поле, и казва какво пропуска.

## Местонахождение: къде са нещата

Предметите стоят в инвентари и всичко може да ги държи: персонаж, място, сандък.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- По време на сесия преместването на предмет записва събитие за даващия и получаващия („Sword: Freya → Chest“). Така хрониките им казват къде са отишли нещата.
- **Хората и чудовищата** са посетители на местата, а не тяхно съдържание: пазете къде са в подробността им `where`.

## В сцени и битки

- **`combat status --gm`** показва `where`, `doing` и `plan` на всеки боец. Обновявайте ги, докато битката тече: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (обзорът, с който започва сесията) изброява какво е в игра (мястото, бойците, всеки, когото засягат събитията в тази сцена, и групата) с where, doing, plan и state. Изброява и последните събития извън сцената.
