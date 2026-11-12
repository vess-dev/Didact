<!-- translated from bef7b2c650cb -->
# Как се играе сесия

Как върви играта чрез Didact: LLM разказва, а Didact пази всеки факт, хвърляне и промяна.

## Преди първата сесия

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

Светът пази системата, с която е създаден, и кампаниите му играят по нея: друга система се играе в собствен свят. `didact campaign close` прибира кампанията (светът ѝ остава отворен), а `didact campaign open <id>` я продължава оттам, където е спряла — заедно със сесията и всичко останало.

`didact world delete <id>` и `didact campaign delete <id>` премахват свят или кампания, като първо показват какво ще изчезне; `--yes` изтрива, а `didact undo` връща всичко.

`session zero` изброява въпросите, които да уточните с играча. Първи са тези на пакета. Опциите на системата (нейните варианти и незадължителни правила) са сред тях: правилата ѝ следват отговорите, а резюмето казва какво означава всяка променена опция. Всеки обзор носи отговорите.

## Сесия

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Ходове:** всяко съобщение на играча отваря ход (куката на Claude Code извиква `didact capture`, а другите клиенти използват `turn begin`). `didact undo --turn` връща всичко, направено за това съобщение: промени, събития и хвърляния. Стенограмата го пази.
- **Връщане назад:** `didact undo --to e40` отменя всичко след #e40, най-новото първо (`--dry-run` го изброява): всяка промяна се отменя и всяко хвърляне се отбелязва като отменено. Нищо не се изтрива: `redo` или връщане към по-късна промяна го връща.
- **Време:** `didact time advance 1 watch` изтича таймерите, повдига напомнянията и пуска тригерите за време. `didact remind --list` показва предстоящите напомняния, а `didact remind --cancel 2` отказва едно. Кампанията започва в началото на календара или на датата, която дава `campaign new --date '4 July 1902'`, а `didact time set '<date>'` я променя до първата сесия.
- **Места:** `didact visit <place>` премества групата и отбелязва мястото като посетено. `didact map` показва какво знае групата, а неизследван изход е `?`.
- **Битки:** `didact combat start --party troll`, после `combat next`, `combat hit freya troll weapon=d8` и `combat end`. Бойци идват и си отиват посред битката: `didact combat join wolf-2` (в индивидуален режим хвърлят за инициатива) и `didact combat leave troll --why fled`. Ничий ход не се пропуска.
- **Вещи:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (или в сандък, или на място); `didact where rope` го намира. `inv add` намира предмет от компендиума по ID, по име или по псевдоним.
- **Вашите бележки:** `didact about sweeney plan='…' doing='…' where='…'` пази каквото сте решили за някого или нещо. Играчите виждат само `looks`. `didact log … --about sweeney` слага събитие в неговия запис (`--secret`, ако играчите не го виждат). Повече има в `didact guide details`.
- **Светът продължава:** `didact faction turn`, плюс часовници: `didact track new 'The flood' --size 6`. Команда, която приема само един вид запис, взима име, което споделят и други, като запис от този вид: `didact track roll draugr` хвърля пула, кръстен на враг (също и `track tick` брояч, `quest done` задача и `visit` място).

## Оракули, генератори и персонажи

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

Нищо, създадено от генератор или при създаване на персонаж, не се записва преди `commit`. Опишете какво иска играчът в `--prefill`, а процедурата попълва празнините. Въпросът изброява какво означава всяка възможност, когато пакетът го казва (`- Cutpurse: …`): кажете го на играча, за да избира, знаейки какво получава.

## Тайни

Изгледите по подразбиране са безопасни за играчите: `show`, `find`, `sheet`, `map`, `brief`. Те пропускат:
- тайните записи (`knowledge: secret`);
- разделите `## Secrets` и `## GM notes`;
- полетата с `secret: true`.

`--gm` показва всичко. Когато играчите научат нещо:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` записва каквото знаят играчите като малък уебсайт, който да споделите или да четете на телефона: групата, страница за всеки запис, дневника и картата. Винаги е безопасен за играчите, а повторен експорт в същата папка го обновява. `didact export --as lonelog` записва дневника в нотация Lonelog (`@ ? d: -> =>`, сцените като `S1`, етикети като `[N:Sweeney]`), също безопасен за играчите.

## Лор: какво изплува, когато нещо бъде споменато

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Какво се брои:** всеки НИП, място, предмет и фракция е карта с ключове името и псевдонимите си. Записите в лора имат `keys`, а решенията по правилата изплуват чрез своето правило. Съвпадението е по цели думи и множественото число се брои („wolves“ съвпада с `wolf`).
- **Кога изплува лорът:** куката на Claude Code сканира всяко съобщение на играча. `log`, `scene new` и `show` също носят новозадействан лор, а един запис не се повтаря няколко хода.
- **Настройка на запис:** `--secondary` с `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (в ходове или сцени), `--constant` (винаги в обзора) и `--no-recurse`.
- **Обхвати:** записите отиват в кампанията, освен ако `--scope` не каже world, system или global. Сканирането вижда само тази кампания, нейния свят, нейната система и global, никога друг свят. По-тесен запис със същото ID засенчва по-широкия.
- **Лор книги от други инструменти:** `didact lore import <file>` чете SillyTavern World Info (и тази на KoboldAI), лор книгата на карта на персонаж и `.lorebook` на NovelAI; `didact lore export --to <file>` записва World Info. Ключовете, логиката, приоритетът, вероятността, групите и времето се пренасят.

## Промяна на историята

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` сменя факта, но пази старата стойност. Освен това отбелязва обобщенията, които споменават Sweeney, като остарели, и `audit` ги изброява.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` записва решение по правилата. То после се показва в `rules lookup` и когато това правило се изпълнява.
- `didact name npc` хвърля ново име, никога такова, което светът вече използва. Преди да измислите име, проверете го с `didact names check <name>`. `didact names forget <name>` освобождава име отново.

## Поддръжка

- `didact history --clear` показва какво би отпаднало при изчистване на старата история; `--yes` го премахва завинаги, включително изтритите записи, и отмяната, `diff`, `rewind` и по-старите точки на запазване вече не могат да го достигнат (`--before e120` пази това събитие и следващите, `--rolls` премахва и историята на заровете). Първо пуснете `didact snapshot`.
- `didact save --remove 'before the dragon'` премахва точка на запазване; `didact undo` я връща.
- `didact transcript 3 --clear` изтрива стенограмата на сесия 3 (`--clear --all`: на всички сесии). `didact undo` я връща, а текстът остава в историята до `history --clear`.
- `didact compendium remove <entry>` изтрива запис, който сте добавили; записите, създадени от него, остават.
- `didact snapshot --keep 3` изтрива всички резервни копия освен трите най-нови, а `didact snapshot --remove <name>` изтрива едно. Нито едното, нито другото може да се отмени.
- `didact session end` сам прави резервно копие на библиотеката (`snapshot-<time>-auto.zip`) и пази петте най-нови от тях; `didact snapshot --list` ги отбелязва.
- `didact reset` показва какво би отнело изпразването на библиотеката; `--yes` я прави като току-що инсталирана: изчезват всички светове, кампании и записи, историята и индексът за търсене, а следващата промяна отново е #e1. Преди това прави резервно копие на библиотеката (`…-before-reset.zip`), а резервните копия остават, както и инсталираните пакети, освен ако няма `--packs`. За да пробвате Didact с готова кампания, `didact sample` създава примерната кампания в празна библиотека (`--home` ѝ дава собствена папка), а `didact serve --demo` я показва всеки път наново.
- `didact snapshot --restore <name>` показва какво съдържа резервното копие до сегашната библиотека; `--yes` прави резервно копие на библиотеката в сегашния ѝ вид (`…-before-restore.zip`), после слага резервното копие на нейно място. Номерата на събитията и хвърлянията продължават. „Отмени“ не може да върне възстановяване: възстановяването на това предпазно резервно копие може.
