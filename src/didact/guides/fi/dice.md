<!-- translated from a81883b64f94 -->
# Nopat

Heitä jokainen noppa Didactin kautta, äläkä koskaan keksi tulosta itse. Jokainen heitto saa tunnisteen (`#r12`), menee lokiin ja voidaan toistaa.

```
didact roll 4d6kh3                          #r12 4d6kh3 → [6 5 3 (2)] = 14
didact roll 'd20 <= @STR' --as freya        #r13 1d20 <= @STR → [7] <= @STR(12) = true
didact roll '6d10>=8f1'                     #r14 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
didact roll '{d8, d6}kh1' --reason "Freya attacks with two daggers"
```

**Laita lauseke lainausmerkkeihin**, mieluiten yksinkertaisiin: `>`, `<`, `!`, `(`, `{`, `#` ja välilyönnit merkitsevät kaikki jotain komentotulkille. Ilman lainausmerkkejä `6d10>=8f1` heittää vain `6d10` ja kirjoittaa tiedoston nimeltä `=8f1`.

## Tuloksen lukeminen

`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — reason`

| Merkki | Merkitys |
|---|---|
| `(2)` | pudotettu |
| `6!` | räjähti: seuraava noppa lisättiin sen takia |
| `1→4` | heitetty uudelleen tai rajattu 1:stä 4:ään |
| `6+6+2` | kasautuva noppa: sen heitot laskettu yhteen |
| `6-1` | läpäisevä noppa: se lasketaan yhtä pienempänä |
| `9✓` / `1✗` | onnistuminen / epäonnistuminen |
| `purr:3` | paketin vaikutuksen lisäämä noppa |
| `@STR(12)` | muuttuja ja sen arvo |
| `([1 2])[8 8 8]` | lukumäärää varten heitetyt nopat, sitten pooli |
| `(doubles, max)` | liput säännöille: `doubles`, `all-same`, `max`, `min`, `exploded`, `rerolled`, `crit`, `fumble`, `capped` |

Didact näyttää lukemansa kanonisen muodon (`4d6k3` → `4d6kh3`), joten erilainen tulkinta ei koskaan jää huomaamatta.

## Notaatio

| Mitä | Kirjoita | Esimerkki |
|---|---|---|
| Nopat | `NdX`, `d%` (d100), `dF` (Fate), `d66` (kymmenet ja ykköset) | `3d6`, `4dF` |
| Omat nopat ja pakettien nopat | `d{faces}`, `d[name]` | `d{0,0,1,1,2,3}`, `2d[boost]` |
| Pidä, pudota | `khN` (tai `kN`), `klN`, `dlN` (tai `dN`), `dhN` | `4d6kh3`, `2d20kl1` |
| Räjähdys | `!` suurimmalla silmäluvulla tai ehdolla; `!!` kasautuu, `!p` läpäisee, `!o` räjähtää kerran | `d6!`, `5d10!>=9` |
| Uudelleenheitto | `r` kunnes ehto ei enää täyty (oletus: pienin silmäluku), `ro` kerran | `2d6r1`, `d20ro<3` |
| Uniikit | `u` heittää kaksoiskappaleet uudelleen, `uo` kerran | `4d6u` |
| Rajaus | `minN`, `maxN` | `4d6min2` |
| Onnistumiset, epäonnistumiset | ehto heti noppien perässä; `f` epäonnistumisille | `6d10>=8f1`, `12d6>=5` |
| Parilliset, parittomat | laske parilliset tai parittomat nopat | `4d6even` |
| Kriittiset | `cs`, `cf` (+ ehto) merkitsevät kriittiset; summa ei muutu | `d20cs>=19` |
| Sarjat | `mt` laskee samojen lukujen sarjat (`mt3`: vähintään kolmen sarjat) | `10d10mt` |
| Marginaali | `ms`: summa − N; `<=`/`<`-ehdolla: N − summa | `d20ms15`, `d20ms<=@DEX` |
| Lajittelu | `sa` (tai `s`), `sd` | `5d6sd` |
| Ryhmät | `{a, b}` + pidä/pudota/onnistumiset | `{d8, d6}kh1` |
| Laskutoimitukset | `+ - * / // %`, sulkeet | `(1d6+2)*2`, `3d6*10` |
| Vertailut | `== <> < <= > >=`, välilyönnein | `2d6 >= 8` |
| Muuttujat | `@name`, `@record.field`, `@{npc:tom.hp}` | `d20 <= @STR`, `(@level)d6` |
| Heitetyt lukumäärät | `(expr)dX` | `(2d4)d8` |
| Funktiot | `min max abs floor ceil round`; `if(c, a, b)`; `default(@x, 0)` | `max(d6, d8)` |
| Noppaportaat | `step(die, n)`; `step.extended(…)` kulkee pidempää ketjua d3–d30 | `step(d6, 1)` → d8 |
| Tagit, nimilaput | `tag:expr` nimeää osan; `expr[label]` antaa sille nimilapun | `hope:1d12 + fear:1d12`, `d8[fire]` |
| Toisto | `N#expr` heittää N erillistä kertaa | `6#4d6dl1` |
| Pakettien makrot | `pack.name(args)` | `hack.attack(d8, d6)` |

**Välilyönneillä on väliä:** `2d6>=8` laskee nopat, jotka näyttävät 8 tai enemmän (d6:lla aina 0), kun taas `2d6 >= 8` vertaa summaa. Didact varoittaa, kun onnistumisen ehto ei voi täyttyä.

**Järjestys:** muokkaimet sovelletaan aina tässä järjestyksessä, kirjoitettiinpa ne miten tahansa: min/max → räjähdys → uudelleenheitto → uniikit → pidä → pudota → onnistumiset ja epäonnistumiset → kriittiset → sarjat → marginaali → lajittelu.

## Muuttujat

- `--as <record>` tuo merkinnän numeeriset kentät käyttöön: `@hp`, `@STR`, `@stats.str` ja `@<field>` sen mechanics-lohkosta.
- `--var DEX=12` asettaa yhden muuttujan, ja sen voi toistaa.
- `@sweeney.hp` lukee toisen merkinnän kentän; tunnisteille käytä muotoa `@{npc:tom.hp}`.
- Muuttujista laskettu noppien lukumäärä näytetään heitettynä: `(@level)d6`, kun level on 2, kirjataan muodossa `2d6 → [3 4] = 7`, ja heiton JSON säilyttää lausekkeen ja muuttujat. Heitetty lukumäärä näyttää omat noppansa: `(2d4)d8 → ([1 4])[4 4 2 1 7]`.

## Fyysiset nopat, kumoaminen, toisto, todennäköisyydet

- `--got 6,3,4` kirjaa oikeiden noppien silmäluvut siinä järjestyksessä kuin ne heitettiin. Räjähdykset ja uudelleenheitot ottavat seuraavan silmäluvun.
- `didact report 'the tower falls' --of 'the tower'` kirjaa tuloksen, jota ei heitetty täällä: nostetun kortin, palikkatornin, kolikon. Se saa heittonumeron ja menee heittolokiin, ja pelikerran aikana se on myös tulostapahtuma. `replay` ohittaa sen.
- `didact rolls` luettelee viimeisimmät heitot.
- `didact undo --event r12 --reason "…"` merkitsee heiton kumotuksi. Se jää lokiin, eivätkä heittojen numerot koskaan palaa taaksepäin.
- `didact replay` suorittaa jokaisen kirjatun heiton uudelleen ja tarkistaa, että jokainen toistuu täsmälleen samana. Jokainen heitto ottaa lukunsa omasta siemennetystä virrastaan, joten yksi heitto ei koskaan siirrä toista.
- `didact odds '2d6 >= 8'` antaa tarkat todennäköisyydet (icepoolin avulla) tai simulaation, kun tarkka laskenta ei onnistu.
- `--seed <text>` ottaa luvut kiinteästä virrasta: sama siemen antaa samat nopat.

## Murre-eroista

- `r` heittää uudelleen yhä uudestaan (Roll20). Foundryn `r` heittää uudelleen kerran, minkä Didact kirjoittaa `ro`.
- `cs` ja `cf` vain merkitsevät kriittiset, kuten Roll20:ssä. Foundryssa ne laskevat onnistumisia; täällä se tehdään ehdolla (`>=19`).
- `d` heti noppien perässä tarkoittaa pienimmän pudottamista: `4d6d1` on `4d6dl1`.
- `!=` ei ole sallittu. Kirjoita `!6`, kun haluat räjähdyksen kuutosella, tai `<>`, kun tarkoitat ”eri suuri kuin”.
