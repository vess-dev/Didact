<!-- translated from a81883b64f94 -->
# Kockák

Minden kockát a Didacton keresztül dobj, és soha ne találj ki eredményt. Minden dobás kap egy azonosítót (`#r12`), bekerül a naplóba, és újrajátszható.

```
didact roll 4d6kh3                          #r12 4d6kh3 → [6 5 3 (2)] = 14
didact roll 'd20 <= @STR' --as freya        #r13 1d20 <= @STR → [7] <= @STR(12) = true
didact roll '6d10>=8f1'                     #r14 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
didact roll '{d8, d6}kh1' --reason "Freya attacks with two daggers"
```

**Tedd idézőjelbe a kifejezést**, lehetőleg egyszeres idézőjelbe: a `>`, `<`, `!`, `(`, `{`, `#` és a szóköz mind jelent valamit a shellnek. Idézőjel nélkül a `6d10>=8f1` a `6d10` kifejezést dobja, és létrehoz egy `=8f1` nevű fájlt.

## Az eredmény olvasása

`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — reason`

| Jelölés | Jelentés |
|---|---|
| `(2)` | eldobva |
| `6!` | robbant: miatta a következő kocka is hozzáadódott |
| `1→4` | újradobva vagy korlátozva 1-ről 4-re |
| `6+6+2` | halmozódó kocka: a dobásai összeadva |
| `6-1` | átütő kocka: eggyel kevesebbet ér |
| `9✓` / `1✗` | siker / kudarc |
| `purr:3` | egy csomaghatás által hozzáadott kocka |
| `@STR(12)` | egy változó és az értéke |
| `([1 2])[8 8 8]` | a darabszámra dobott kockák, aztán a készlet |
| `(doubles, max)` | jelzők a szabályoknak: `doubles`, `all-same`, `max`, `min`, `exploded`, `rerolled`, `crit`, `fumble`, `capped` |

A Didact visszaírja a kanonikus alakot, ahogy értelmezte (`4d6k3` → `4d6kh3`), így egy eltérő értelmezés sosem marad észrevétlen.

## Jelölés

| Mi | Írásmód | Példa |
|---|---|---|
| Kockák | `NdX`, `d%` (d100), `dF` (Fate), `d66` (tízesek és egyesek) | `3d6`, `4dF` |
| Saját és csomagkockák | `d{faces}`, `d[name]` | `d{0,0,1,1,2,3}`, `2d[boost]` |
| Megtartás, eldobás | `khN` (vagy `kN`), `klN`, `dlN` (vagy `dN`), `dhN` | `4d6kh3`, `2d20kl1` |
| Robbanás | `!` a legnagyobb lapon, vagy egy feltétel; `!!` halmoz, `!p` átüt, `!o` egyszer robban | `d6!`, `5d10!>=9` |
| Újradobás | `r`, amíg nem teljesül a feltétel (alapértelmezés: a legkisebb lap), `ro` egyszer | `2d6r1`, `d20ro<3` |
| Egyedi értékek | `u` újradobja az ismétlődőket, `uo` egyszer | `4d6u` |
| Korlátozás | `minN`, `maxN` | `4d6min2` |
| Sikerek, kudarcok | feltétel közvetlenül a kockák után; `f` a kudarcokhoz | `6d10>=8f1`, `12d6>=5` |
| Páros, páratlan | a páros vagy páratlan kockák számolása | `4d6even` |
| Kritikusok | a `cs`, `cf` (+ feltétel) kritikusnak jelöl; az összeg nem változik | `d20cs>=19` |
| Egyezések | az `mt` az egyező csoportokat számolja (`mt3`: legalább 3-as csoportok) | `10d10mt` |
| Különbség | `ms`: összeg − N; `<=`/`<` esetén: N − összeg | `d20ms15`, `d20ms<=@DEX` |
| Rendezés | `sa` (vagy `s`), `sd` | `5d6sd` |
| Csoportok | `{a, b}` + megtartás/eldobás/sikerek | `{d8, d6}kh1` |
| Matematika | `+ - * / // %`, zárójelek | `(1d6+2)*2`, `3d6*10` |
| Összehasonlítás | `== <> < <= > >=`, szóközökkel | `2d6 >= 8` |
| Változók | `@name`, `@record.field`, `@{npc:tom.hp}` | `d20 <= @STR`, `(@level)d6` |
| Dobott darabszám | `(expr)dX` | `(2d4)d8` |
| Függvények | `min max abs floor ceil round`; `if(c, a, b)`; `default(@x, 0)` | `max(d6, d8)` |
| Kockalépcső | `step(die, n)`; a `step.extended(…)` a hosszabb d3–d30 láncon lépked | `step(d6, 1)` → d8 |
| Címkék, feliratok | a `tag:expr` elnevez egy részt; az `expr[label]` felirattal látja el | `hope:1d12 + fear:1d12`, `d8[fire]` |
| Ismétlés | az `N#expr` N külön dobást végez | `6#4d6dl1` |
| Csomagmakrók | `pack.name(args)` | `hack.attack(d8, d6)` |

**A szóköz számít:** a `2d6>=8` azokat a kockákat számolja, amelyek 8-at vagy többet mutatnak (d6-on mindig 0), míg a `2d6 >= 8` az összeget hasonlítja össze. A Didact figyelmeztet, ha egy sikerfeltétel nem teljesülhet.

**Sorrend:** a módosítók mindig ebben a sorrendben érvényesülnek, akárhogy írod őket: min/max → robbanás → újradobás → egyedi értékek → megtartás → eldobás → sikerek és kudarcok → kritikusok → egyezések → különbség → rendezés.

## Változók

- A `--as <record>` elérhetővé teszi a bejegyzés számmezőit: `@hp`, `@STR`, `@stats.str`, valamint a mechanikai blokkjából a `@<field>` alakúakat.
- A `--var DEX=12` egy változót állít be, és ismételhető.
- A `@sweeney.hp` egy másik bejegyzés mezőjét olvassa; azonosítókhoz használd a `@{npc:tom.hp}` alakot.
- A változókból kiszámolt kockaszám dobottként jelenik meg: a `(@level)d6` 2-es szinttel így kerül a naplóba: `2d6 → [3 4] = 7`, a dobás JSON-ja pedig megőrzi a kifejezést és a változókat. A dobott darabszám a saját kockáit is mutatja: `(2d4)d8 → ([1 4])[4 4 2 1 7]`.

## Valódi kockák, visszavonás, újrajátszás, esélyek

- A `--got 6,3,4` valódi kockák lapjait rögzíti, a dobás sorrendjében. A robbanások és újradobások a következő lapot veszik.
- A `didact report 'the tower falls' --of 'the tower'` olyan eredményt rögzít, amelyet nem itt dobtak: húzott kártyát, kockatornyot, érmét. Dobásszámot kap, bekerül a dobásnaplóba, játékalkalom közben pedig eredményesemény is lesz belőle. A `replay` átugorja.
- A `didact rolls` felsorolja a legutóbbi dobásokat.
- A `didact undo --event r12 --reason "…"` visszavontnak jelöl egy dobást. A naplóban marad, és a dobások számozása sosem ugrik vissza.
- A `didact replay` újrafuttat minden rögzített dobást, és ellenőrzi, hogy mindegyik pontosan ugyanazt adja-e. Minden dobás a saját, magozott sorozatából húz, így egyik dobás sem tolja el a másikat.
- A `didact odds '2d6 >= 8'` pontos valószínűségeket ad (az icepool segítségével), vagy szimulációt, ha nincs pontos számítás.
- A `--seed <text>` egy rögzített sorozatból húz: ugyanaz a mag ugyanazokat a kockákat adja.

## Dialektusok

- Az `r` újra és újra dob (Roll20). A Foundry `r`-je egyszer dob újra, ezt a Didact `ro` alakban írja.
- A `cs` és a `cf` csak kritikusnak jelöl, mint a Roll20-ban. A Foundryban sikereket számolnak; itt erre feltétel való (`>=19`).
- A közvetlenül a kockák utáni `d` a legkisebb eldobását jelenti: a `4d6d1` ugyanaz, mint a `4d6dl1`.
- A `!=` nem megengedett. Írd a `!6` alakot, ha 6-on akarsz robbantani, vagy a `<>` alakot a „nem egyenlő” jelentéshez.
