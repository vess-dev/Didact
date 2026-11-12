<!-- translated from 7fe144069f94 -->
# Részletek, krónika és hollét

A KM jegyzetei, amelyektől következetes marad a játék: hogy néznek ki a dolgok és mit akarnak, mit csinálnak és mit terveznek, mi történt velük, és hol van minden.

## Részletek

Rövid, névvel ellátott jegyzetek bármely bejegyzésen: személyen, tárgyon, helyszínen, frakción.

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

- **Nevek.** A javasoltak a bejegyzés fajtájától függenek, de bármilyen egyszavas név megfelel:
  - személyek: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - tárgyak: looks, history, where, powers, secret, thoughts;
  - helyszínek: looks, state, history, secret, thoughts;
  - csoportok: wants, plan, state, history, secret, thoughts.

  Egy csomag típusonként saját neveket is javasolhat (`details: [mood, grudge]` egy sémában).
- **Ki mit lát.** A játékosok csak a `looks` részletet látják: a `show` és a `find` a többit kihagyja, a `--gm` pedig mindent megmutat. Amikor a játékosok megtudnak egyet, a `didact reveal sweeney plan` áthelyezi a bejegyzés szövegébe, a `## Revealed` alá.
- **A `thoughts`** a tiéd: miért hoztad létre, hová vezethet, mit kell később beváltani.
- **Tartsd őket naprakészen.** Nem kell mindent feljegyezned. De ha eldöntesz valamit (egy tervet, egy haragot, hogy hová ment valaki), írd le, hogy a következő jelenet vagy a következő alkalom is hű maradjon hozzá.

## A krónika: mi történt kivel

Egy naplóesemény megnevezheti a bejegyzéseket, amelyekre vonatkozik. Ekkor mindegyiken megjelenik.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- A `show` és az `about` felsorolja egy bejegyzés krónikáját: mit tett, és mit tettek vele.
- **A titkos események** a játékosok szeme elől rejtve történnek. Csak a KM-nézetekben jelennek meg (`session show --gm`, `about`, `brief --gm`), az `export --as story` kimenetében soha.
- Használd a `--about` kapcsolót mindenhez, ami megváltoztat valakit vagy valamit: árulás, adósság, halál, ajándék, megszegett ígéret.
- **Esemény javítása:** a `didact beat edit S1.4 --about tom` Tom krónikájára teszi (vagy `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), a `didact beat rm S1.4` pedig eltávolítja. Az azonosítók a `session show` kimenetében vannak, és mindkettő visszavonható.
- **Ha az azonosítók változnak:** egy `merge` vagy egy új slug minden hivatkozást magával visz: kapcsolatokat, részleteket, a bejegyzéseket, amelyekre az események vonatkoznak, a csapatot, a harcot és a csapat helyét. Ha egy bejegyzést az `rm` töröl, kikerül minden csapatból és harcból is. A típusok közötti `merge` megtartja, amihez a megmaradó bejegyzés lapján van mező, és megmondja, mit hagy ki.

## Hollét: hol vannak a dolgok

A tárgyak felszerelésekben vannak, és bármi tarthatja őket: egy karakter, egy helyszín, egy láda.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Egy alkalom közben egy tárgy mozgatása eseményt rögzít az átadóról és az átvevőről („Sword: Freya → Chest”). Így a krónikájukból kiderül, hová kerültek a dolgok.
- **A személyek és a szörnyek** a helyszínek látogatói, nem a tartalmuk: hogy hol vannak, azt a `where` részletükben tartsd.

## Jelenetekben és harcban

- **A `combat status --gm`** minden harcoló `where`, `doing` és `plan` részletét megmutatja. Frissítsd őket, ahogy a harc halad: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **A `brief --gm`** (az összefoglaló, amellyel egy alkalom kezdődik) felsorolja, mi van játékban (a helyszín, a harcolók, akikre a jelenet eseményei vonatkoznak, és a csapat), a where, doing, plan és state részletekkel. A legutóbbi, színfalak mögötti eseményeket is felsorolja.
