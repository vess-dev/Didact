<!-- translated from 5a088227a31a -->
# A böngészős alkalmazás

A `didact serve` webböngészőben nyitja meg a könyvtáradat: bejegyzéseket böngészhetsz és szerkeszthetsz, gráfon láthatod, hogyan kapcsolódnak, olvashatod a naplót, szabályokat és táblázatokat futtathatsz, és minden parancsot használhatsz egy űrlapról.

```
didact serve                     # http://127.0.0.1:8765/ until Ctrl-C
didact serve --open              # and open it in a browser tab
didact serve --gm                # start with the GM view on
didact serve --port 9000
didact serve --campaign withering --home ~/OtherLibrary
didact serve --demo              # a fresh sample campaign to try things on
```

Offline is működik: a betűtípusok és az ikonok a Didacttal együtt érkeznek.

**Bemutató mód.** A `--demo` a mintakampányt szolgálja ki (`didact sample`: egy folyóvölgy, egy JK, személyek a KM jegyzeteivel, helyszínek és utak, egy küldetés, egy óra, és egy folyamatban lévő alkalom egy harccal), egy saját könyvtárból a Didact gyorsítótár-mappája mellett. Ott minden csomag telepítve van, amely a Didacttal érkezik. Minden `--demo` indításkor frissen épül fel, úgyhogy bármit kipróbálhatsz: a saját könyvtáradhoz nem nyúl.

## Kapcsolók

| Kapcsoló | Alapértelmezés | Mit csinál |
|---|---|---|
| `--port <n>` | 8765 | a port, amelyen figyel |
| `--host <address>` | 127.0.0.1 | a cím, amelyen figyel: csak ez a gép |
| `--open` | ki | megnyitja az alkalmazást egy böngészőlapon |
| `--gm` | ki | bekapcsolt KM-nézettel indul |
| `--demo` | ki | a könyvtárad helyett egy friss mintakampányt szolgál ki |

A globális `--home`, `--world` és `--campaign` mindenre vonatkozik, amit az alkalmazás csinál. Ha az alkalmazás Könyvtár oldalán megnyitsz egy másik világot vagy kampányt, arra váltasz át, ahogy a `didact world use` és a `didact campaign open` esetén, a Bezárás pedig félreteszi a megnyitott kampányt (`didact campaign close`).

## Mi van benne

- **Áttekintés:** az összefoglaló (világ, kampány, alkalom, jelenet, csapat, mi esedékes), gyorsműveletek (kockadobás, az orákulum megkérdezése az általa ismert esélyekkel, esemény rögzítése, alkalom indítása vagy befejezése, új bejegyzés) és a legutóbbi változások.
- **Állapot:** hol tartanak a dolgok, egy pillantással: az alkalom és a jelenet, az idő és a közelgő emlékeztetők, a csapattagok számai és hogy mit visznek, a harc (ki van soron, állapotok), a nyitott küldetések és számlálók, és hol van a csapat, a kivezető utakkal. A számok ott helyben módosíthatók: − és + egy értéken, egy számláló bejelölése, egy tárgy használata vagy eldobása, egy új hozzáadása, egy küldetés lezárása, az idő léptetése (egy szám és egy időegység, amelyet a naptár ismer: óra, őrség, nap, …), emlékeztető beállítása (egyszeri vagy ismétlődő) és törlése.
- **Bejegyzések:** minden bejegyzés, típus szerint csoportosítva, szűrőmezővel és Mind, Világ vagy Kampány szűrőgombokkal. Egy bejegyzés oldala megmutatja a lapját, leírását, részleteit, mezőit, tartalmát, a kapcsolatait mindkét irányban, a krónikáját és az előzményeit, űrlapokkal mindegyik módosításához, valamint az archiváláshoz vagy törléshez. Ha egy karakter rendszerében van szintlépés, a karakternek Level up gombja van (`char advance`): egy vázlat, amely a jóváhagyásig megmutatja, mi változik, előtte és utána.
- **Vázlatok:** karakteralkotás és generátorok, lépésről lépésre. A Karakter létrehozása (lépésről lépésre vagy véletlenszerűen, és ha a rendszerben többféle van, a fajta kiválasztásával: játékos karakter, zsoldos, …) és a Generálás… a Bejegyzések oldalain van; a várakozó vázlatok ott és az Áttekintésen is fel vannak sorolva. Egy vázlat oldala megmutatja, mi van benne eddig (az entitásai és a mezőik, a generátor által rajzolt térkép, a dobások, a könyv kérdései), és a kérdést, amelyre vár. Minden lehetőség egy gomb, amely megmondja, mit jelent, ha a csomag megadja (mit ad egy háttér, mit csinál egy tehetség); ha többet kell választani, mindegyikhez tartozik egy bejelölhető négyzet; a keretből vásárolt értékek számok, amelyek menet közben számolják a pontokat; egy név vagy más szabad válasz beírható; a „Döntsenek a kockák” gomb pedig csak azt az egyet dobja ki (`char roll c3 --one`). A Vissza visszavonja az utolsó lépést, így annak kérdése újra megjelenik (`char back c3`: a lépés dobásai visszavontként lesznek megjelölve, a Visszavonás pedig visszahozza a lépést). Aztán jön A többi kidobása, a Szerkesztés, az Elvetés… (előbb rákérdez) és a Jóváhagyás, amely megnyitja az új karakter bejegyzését, vagy felsorolja, mit hozott létre a generátor. A generátor vázlata a KM-é: a játékosnézet csak azt mutatja, hogy létezik.
- **Gráf:** a bejegyzések csomópontok, a kapcsolatok élek. Húzd a csomópontokat, a háttér húzásával mozgasd a nézetet, görgővel nagyíts; vidd fölé az egeret, hogy kiemeld egy bejegyzés szomszédait; kattints egyre a megnyitásához. Egy bejegyzés oldalán a Gráf gomb csak a környezetét mutatja.
  - **Térkép** (a gráf fölötti kapcsoló, vagy a Térkép megnyitása az Állapot oldalon): a csapat által ismert helyszínek, a köztük vezető utak (road, trail, … felirattal), a régió, amelyben mindegyik fekszik (szaggatott vonallal), és hogy hol van a csapat. A még meg nem talált helyre vezető út egy „?”-hez vezet; a KM-nézet minden helyszínt mutat.
- **Napló:** az alkalmak, mindegyik kinyitható a jeleneteire, eseményeire és dobásaira. Minden eseménynél van Szerkesztés és Eltávolítás (vidd fölé az egeret), amelyek a `beat edit` és a `beat rm` űrlapját nyitják meg.
- **Kézikönyv:** keresés mindenben (a találatok gépelés közben jelennek meg), a bekapcsolt csomagok szabályainak futtatása űrlapokról, dobás a táblázataikon, és a szabályszövegük, szószedetük és útmutatóik olvasása.
- **Könyvtár:** világok és kampányok (megnyitás, bezárás, létrehozás, törlés), csomagok (mindegyik azzal, hogy micsoda; bekapcsolás, kikapcsolás, telepítés, eltávolítás; a Didacttal együtt érkező csomagoknak Telepítés gombjuk van), az előzmények (Visszavonás, Mégis, Visszaugrás, Törlés), a mentési pontok (visszatekerés, eltávolítás) és a biztonsági mentések (biztonsági mentés most, visszaállítás, törlés, a legújabbak megtartása; az alkalom befejezésekor készültek auto jelölést kapnak). Ha nincs megnyitott kampány, az Áttekintés felsorolja a világ kampányait, hogy megnyithass egyet.
  - Egy világ vagy kampány törlése előbb rákérdez, és a Visszavonás mindent visszahoz.
  - A Visszaugrás (minden változás mellett) mindent visszavon, ami az adott változás után történt (`didact undo --to e40`): az oldala előbb megmutatja, mi kerül visszavonásra. Minden változás visszavonódik, és minden dobás visszavontként lesz megjelölve, nem törlődik: a Mégis, vagy egy későbbi változáshoz való visszaugrás visszahozza őket. A Régebbi változások megjelenítése az előzmények további részét listázza.
  - A core csomag mindig be van kapcsolva. Egyszerre egy játékrendszer van használatban: a megnyitott világé, amely végleg megtartja (a létrehozásakor választják ki). Másik rendszer saját világban játszható: a sora megnyit egy világot, amely azzal játszik, vagy újat hoz létre. Egy csomag eltávolítása nem vonható vissza: telepítsd újra a .didactpack fájlját.
  - Az előzmények törlése előbb pontosan megmutatja, mi tűnik el és mi nem működik többé, egy gombbal, amellyel előbb biztonsági mentést készíthetsz. Nem vonható vissza, ahogy egy biztonsági mentés törlése sem.
  - Újrakezdés: az **Alaphelyzet…** kiüríti a könyvtárat, mintha a Didact frissen lenne telepítve, és a számozás újra #e1-től indul. Az oldala előbb megmutatja, mi tűnik el. A könyvtárról előbb biztonsági mentés készül, és a biztonsági mentések megmaradnak (a telepített csomagok is, hacsak be nem jelölöd a négyzetet).
  - Egy biztonsági mentés visszaállítása előbb megmutatja, mi van benne, a mostani könyvtár mellett. A könyvtár addigi állapotáról előbb biztonsági mentés készül: a Visszavonás nem vonja vissza a visszaállítást, de annak a mentésnek a visszaállítása igen.
- **Parancsok:** minden parancs űrlapként, és egy mező, amely egy teljes parancssort fogad. Minden mező azt fogadja, amit az argumentuma: számot, azonosítót vagy eseményt (`e12`) a mintája szerint, játékidő-mennyiséget számként és időegységként, valamint választható listát az itteni bejegyzésekből, vázlatokból, csomagokból, mentési pontokból, orákulumokból, táblázatokból és szabályokból.
- **Beállítások:** a kampány beállításai (a rendszere változatai és választható szabályai, amelyeket a szabályok, a karakteralkotás és a generátorok követnek; mindegyik leírja, mit csinál: egy választható szabály azt, mit változtat a bekapcsolása, egy választós beállítás azt, mit jelentenek az értékei, egy másik beállítás által megadott alapértelmezés pedig azt, melyik beállítás adja), az alkalmazás nyelve, a szinonimaszótár (a nyelv, amelyet a keresés a szinonimákhoz használ: letölthetsz egyet, folyamatjelzővel, válthatsz a letöltöttek között, eltávolíthatsz egyet) és a kód dokumentációja.
  - Az alkalmazás, az útmutatói és az, amit a parancsok benne megjelenítenek, 24 nyelven érhetők el. Ha nem választasz, az alkalmazás a böngésző nyelvét követi. A parancssor és az azt használó nyelvi modellek angolul maradnak: az itt választott nyelv csak az alkalmazásra vonatkozik.
  - A fejlécsávban lévő kód gomb megnyitja a kód API-dokumentációját. Az első alkalommal a kódból készül el, és újra, valahányszor a kód megváltozik (`didact docs build`).

Minden változás egy valódi `didact` parancsot futtat, így pontosan úgy ellenőrzött, naplózott és visszavonható, mint a parancssorban. Az alkalmazás minden alkalommal megmutatja a lefuttatott parancsot (`didact set sweeney hp-=2`), egy Visszavonás gombbal, ha van mit visszavenni.

Egy mező csak azt fogadja el, amit a parancsa. Az azonosító (egy világé vagy kampányé) és a bejegyzéstípus kisbetűket, számjegyeket és kötőjeleket fogad: gépelés közben a szóközökből kötőjel lesz, a nagybetűkből kisbetű. Egy bejegyzésmező neve nem tartalmazhat szóközt (aláhúzásjel lesz belőlük), egy részlet neve egyetlen szó, a számmezők pedig csak számot fogadnak. Hogy egy mező mit fogad, az alatta olvasható, és a parancs úgyis újra ellenőrzi.

A mentés sosem ír felül olyan változást, amelyet nem láttál. Ha a bejegyzés megváltozott, miután az oldal megjelenítette (mondjuk egy LLM módosította a parancssorból, vagy egy másik lap), a mentés elutasításra kerül, és megmondja, mi van ott most. A szerkesztett leírás a szerkesztőben marad, az új változat mellett, hogy összefésüld és újra mentsd. A − és a + mindig átmegy: összeadódnak.

## Játékosnézet és KM-nézet

Az alkalmazás azt mutatja, amit a játékosok tudnak, ahogy a `didact show` is: a titkos bejegyzések, a `## Secrets` szakaszok, a titkos mezők és a csak KM-nek szóló részletek kimaradnak. A fejlécsávban lévő **GM** gomb bekapcsolja a KM-nézetet, és egy sáv jelzi ezt („KM-nézet: spoilerek láthatók”). A böngésző megjegyzi a választást.

A játékosnézetben:
- a csak KM-nek szóló sorokat tartalmazó leírás nem szerkeszthető (mentéskor elvesznének): előbb kapcsold be a KM-nézetet;
- az oldalon nem látható KM-részlet vagy titkos mező nem írható felül, de új jegyzet a KM-nek hozzáadható;
- az előzmények a parancsot és a játékosok által ismert bejegyzéseket nevezik meg (`set · Freya`), az értékeket soha, a Visszavonás pedig megmondja, melyik változást vette vissza, de azt nem, hogy mi volt az.

## Biztonság

Az alkalmazás módosíthatja a könyvtáradat, ezért alapból csak erre a gépre figyel.

- A `--host` egy másik címmel más gépek számára is elérhetővé teszi, és a Didact figyelmeztet erre. Csak megbízható hálózaton használd.
- Csak a neki címzett kérésekre válaszol (a saját címére, `localhost`, `127.0.0.1` vagy `[::1]`, a saját portjával). Ez megakadályozza, hogy más weboldalak DNS-trükkökkel elérjék.
- Minden változáshoz az alkalmazás saját űrlapja kell: az egyes űrlapokban lévő titkos tokennek egyeznie kell egy sütivel, amelyet más oldalak nem tudnak olvasni vagy elküldeni.
- Nincs bejelentkezés. Aki használhatja ennek a számítógépnek a böngészőjét, az alkalmazást is használhatja.
