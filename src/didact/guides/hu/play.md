<!-- translated from bef7b2c650cb -->
# Egy alkalom játszása

Így megy a játék a Didacttal: az LLM mesél, a Didact pedig megőriz minden tényt, dobást és változást.

## Az első alkalom előtt

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

Egy világ megtartja azt a rendszert, amellyel létrehozták, és a kampányai azzal játszanak: másik rendszer saját világban játszható. A `didact campaign close` félreteszi a kampányt (a világa nyitva marad), a `didact campaign open <id>` pedig ott folytatja, ahol abbamaradt, a folyamatban lévő alkalommal együtt.

A `didact world delete <id>` és a `didact campaign delete <id>` töröl egyet, előbb megmutatva, mi megy; a `--yes` töröl, a `didact undo` pedig mindent visszahoz.

A `session zero` felsorolja a kérdéseket, amelyeket a játékossal tisztázni kell. A csomag saját kérdései jönnek elsőként. Köztük vannak a rendszer beállításai is (változatai és választható szabályai): a szabályai a válaszokat követik, az összefoglaló pedig megmondja, mit jelent minden megváltozott beállítás. A válaszok minden összefoglalóban benne vannak.

## Egy alkalom

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Körök:** minden játékosüzenet új kört nyit (a Claude Code hook a `didact capture` parancsot hívja, más kliensek a `turn begin` parancsot). A `didact undo --turn` visszavesz mindent, ami arra az üzenetre történt: változásokat, eseményeket és dobásokat. Az átirat megőrzi.
- **Visszaugrás:** a `didact undo --to e40` mindent visszavesz #e40 után, a legújabbal kezdve (a `--dry-run` kilistázza): minden változás visszavonódik, és minden dobás visszavontként lesz megjelölve. Semmi sem törlődik: a `redo`, vagy egy későbbi változáshoz való visszaugrás visszahozza.
- **Idő:** a `didact time advance 1 watch` lejártatja az időzítőket, előhozza az emlékeztetőket és lefuttatja az időkiváltókat. A `didact remind --list` megmutatja a közelgő emlékeztetőket, a `didact remind --cancel 2` pedig töröl egyet. Egy kampány a naptár kezdetén kezdődik, vagy azon a dátumon, amelyet a `campaign new --date '4 July 1902'` megad, és a `didact time set '<date>'` az első alkalomig megváltoztathatja.
- **Helyszínek:** a `didact visit <place>` odaviszi a csapatot, és meglátogatottnak jelöli a helyet. A `didact map` megmutatja, amit a csapat ismer; a felderítetlen kijárat `?`.
- **Harc:** `didact combat start --party troll`, aztán `combat next`, `combat hit freya troll weapon=d8` és `combat end`. A harcolók harc közben jöhetnek és mehetnek: `didact combat join wolf-2` (egyéni módban kezdeményezést dobnak) és `didact combat leave troll --why fled`. Senkinek a köre nem marad ki.
- **Tárgyak:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (vagy egy ládába, vagy egy helyszínre); a `didact where rope` megtalálja. Az `inv add` azonosító, név vagy álnév alapján találja meg a kompendium tárgyait.
- **A jegyzeteid:** a `didact about sweeney plan='…' doing='…' where='…'` megőrzi, amit bárkiről vagy bármiről eldöntöttél. A játékosok csak a `looks` részletet látják. A `didact log … --about sweeney` eseményt tesz a bejegyzésére (`--secret`, ha a játékosok nem látják). Bővebben: `didact guide details`.
- **A világ halad tovább:** `didact faction turn`, plusz órák: `didact track new 'The flood' --size 6`. Az egyféle bejegyzést váró parancs a mások által is viselt nevet ilyen fajtának veszi: a `didact track roll draugr` az ellenség nevét viselő készlettel dob (ugyanígy a `track tick` egy számlálóval, a `quest done` egy küldetéssel és a `visit` egy hellyel).

## Orákulumok, generátorok és karakterek

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

Semmi, amit egy generátor vagy a karakteralkotás létrehoz, nem íródik be a `commit` előtt. Írd le a `--prefill` részben, mit szeretne a játékos, és az eljárás kitölti a hiányokat. Egy kérdés felsorolja, mit jelentenek az egyes lehetőségek, ha a csomag megadja (`- Cutpurse: …`): mondd el a játékosnak, hogy annak tudatában válasszon, mit kap.

## Titkok

A nézetek alapból biztonságosak a játékosok számára: `show`, `find`, `sheet`, `map`, `brief`. Kihagyják:
- a titkos bejegyzéseket (`knowledge: secret`);
- a `## Secrets` és `## GM notes` szakaszokat;
- a `secret: true` mezőket.

A `--gm` mindent megmutat. Amikor a játékosok megtudnak valamit:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

A `didact export --as site --to ~/Desktop/withering-site` kis weboldalként kiírja, amit a játékosok tudnak, hogy megoszthasd vagy telefonon olvashasd: a csapatot, bejegyzésenként egy oldalt, a naplót és a térképet. Mindig biztonságos a játékosok számára, és ha újra ugyanabba a mappába exportálsz, frissíti. A `didact export --as lonelog` Lonelog jelöléssel írja ki a naplót (`@ ? d: -> =>`, a jelenetek `S1`-ként, címkék, mint `[N:Sweeney]`), és ez is biztonságos a játékosok számára.

## Háttértudás: mi kerül elő, ha szóba kerül valami

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Mi számít:** minden NJK, helyszín, tárgy és frakció egy kártya, amelyet a neve és az álnevei kulcsolnak. A háttértudás-bejegyzéseknek `keys` kulcsaik vannak, a döntések pedig a szabályukon keresztül kerülnek elő. Az egyezés egész szavakra megy, és a többes szám is számít („wolves” egyezik a `wolf` kulccsal).
- **Mikor kerül elő a háttértudás:** a Claude Code hook minden játékosüzenetet átvizsgál. A `log`, a `scene new` és a `show` is hozza az újonnan kiváltott háttértudást, és egy bejegyzés néhány körig nem ismétlődik.
- **Egy bejegyzés hangolása:** `--secondary` a `--logic` mellett, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (körökben vagy jelenetekben), `--constant` (mindig az összefoglalóban) és `--no-recurse`.
- **Hatókörök:** a bejegyzések a kampányhoz kerülnek, hacsak a `--scope` nem mond világot, rendszert vagy globálisat. Egy vizsgálat csak ezt a kampányt, a világát, a rendszerét és a globálisat látja, más világot soha. Egy szűkebb bejegyzés ugyanazzal az azonosítóval eltakarja a tágabbat.
- **Más eszközök lorebookjai:** a `didact lore import <file>` beolvassa a SillyTavern World Info fájlt (a KoboldAI-ét is), egy karakterkártya lorebookját és a NovelAI `.lorebook` fájlját; a `didact lore export --to <file>` World Info fájlt ír. A kulcsszavak, a logika, a prioritás, a valószínűség, a csoportok és az időzítés átkerülnek.

## A történet módosítása

- A `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` megváltoztatja a tényt, de megőrzi a régi értéket. Elavultnak jelöli a Sweeney-t említő összefoglalókat is, és az `audit` felsorolja őket.
- A `didact ruling add '<question>' '<ruling>' --rule <rule>` döntést rögzít. Ez ezután megjelenik a `rules lookup` kimenetében, és amikor az a szabály lefut.
- A `didact name npc` friss nevet dob, sosem olyat, amit a világ már használ. Mielőtt kitalálsz egyet, ellenőrizd a `didact names check <name>` paranccsal. A `didact names forget <name>` újra felszabadít egyet.

## Karbantartás

- A `didact history --clear` megmutatja, mit dobna el a régi előzmények törlése; a `--yes` végleg eldobja, a törölt bejegyzésekkel együtt, és a visszavonás, a `diff`, a `rewind` és a régebbi mentési pontok többé nem érik el (a `--before e120` megtartja azt az eseményt és a későbbieket, a `--rolls` a kockanaplót is eldobja). Előtte futtasd a `didact snapshot` parancsot.
- A `didact save --remove 'before the dragon'` eltávolít egy mentési pontot; a `didact undo` visszahozza.
- A `didact transcript 3 --clear` törli a 3. alkalom átiratát (`--clear --all`: minden alkalomét). A `didact undo` visszahozza, és a szöveg a `history --clear`-ig az előzményekben marad.
- A `didact compendium remove <entry>` töröl egy általad hozzáadott bejegyzést; a belőle létrehozott bejegyzések megmaradnak.
- A `didact snapshot --keep 3` a legújabb három kivételével minden biztonsági mentést töröl, a `didact snapshot --remove <name>` pedig egyet töröl. Egyik sem vonható vissza.
- A `didact session end` magától biztonsági mentést készít a könyvtárról (`snapshot-<time>-auto.zip`), és ezekből a legújabb ötöt tartja meg; a `didact snapshot --list` megjelöli őket.
- A `didact reset` megmutatja, mit vinne el a könyvtár kiürítése; a `--yes` olyanná teszi, mint frissen telepítve: minden világ, kampány és bejegyzés, az előzmények és a keresési index eltűnik, és a következő változás újra #e1 lesz. Előbb biztonsági mentést készít a könyvtárról (`…-before-reset.zip`), és a biztonsági mentések megmaradnak, ahogy a telepített csomagok is, hacsak nem adod meg a `--packs` kapcsolót. Ha inkább egy kész kampányon próbálnád ki a Didactot, a `didact sample` egy üres könyvtárba építi a mintakampányt (a `--home` saját mappát ad neki), a `didact serve --demo` pedig frissen szolgálja ki.
- A `didact snapshot --restore <name>` megmutatja, mi van egy biztonsági mentésben, a mostani könyvtár mellett; a `--yes` biztonsági mentést készít a könyvtárról a mostani állapotában (`…-before-restore.zip`), aztán a helyére teszi a mentést. Az esemény- és dobásszámozás folytatódik. A visszavonás nem vonja vissza a visszaállítást: annak a biztonsági mentésnek a visszaállítása igen.
