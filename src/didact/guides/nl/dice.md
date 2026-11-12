<!-- translated from a81883b64f94 -->
# Dobbelstenen

Gooi elke dobbelsteen via Didact, en verzin nooit een uitkomst. Elke worp krijgt een id (`#r12`), komt in het log en kan opnieuw worden afgespeeld.

```
didact roll 4d6kh3                          #r12 4d6kh3 → [6 5 3 (2)] = 14
didact roll 'd20 <= @STR' --as freya        #r13 1d20 <= @STR → [7] <= @STR(12) = true
didact roll '6d10>=8f1'                     #r14 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
didact roll '{d8, d6}kh1' --reason "Freya attacks with two daggers"
```

**Zet de expressie tussen aanhalingstekens**, liefst enkele: `>`, `<`, `!`, `(`, `{`, `#` en spaties betekenen allemaal iets voor de shell. Zonder aanhalingstekens gooit `6d10>=8f1` alleen `6d10` en schrijft het een bestand met de naam `=8f1`.

## Een uitkomst lezen

`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — reason`

| Teken | Betekenis |
|---|---|
| `(2)` | weggelaten |
| `6!` | geëxplodeerd: daardoor kwam de volgende dobbelsteen erbij |
| `1→4` | opnieuw gegooid of begrensd, van 1 naar 4 |
| `6+6+2` | een optellende dobbelsteen: zijn worpen bij elkaar opgeteld |
| `6-1` | een doorbrekende dobbelsteen: hij telt één minder |
| `9✓` / `1✗` | een succes / een mislukking |
| `purr:3` | een dobbelsteen toegevoegd door een pakketeffect |
| `@STR(12)` | een variabele en haar waarde |
| `([1 2])[8 8 8]` | de dobbelstenen voor het aantal, dan de pool |
| `(doubles, max)` | vlaggen voor regels: `doubles`, `all-same`, `max`, `min`, `exploded`, `rerolled`, `crit`, `fumble`, `capped` |

Didact herhaalt de canonieke vorm die het las (`4d6k3` → `4d6kh3`), zodat een andere lezing nooit onopgemerkt blijft.

## Notatie

| Wat | Schrijf | Voorbeeld |
|---|---|---|
| Dobbelstenen | `NdX`, `d%` (d100), `dF` (Fate), `d66` (tientallen en eenheden) | `3d6`, `4dF` |
| Eigen en pakketdobbelstenen | `d{faces}`, `d[name]` | `d{0,0,1,1,2,3}`, `2d[boost]` |
| Houden, weglaten | `khN` (of `kN`), `klN`, `dlN` (of `dN`), `dhN` | `4d6kh3`, `2d20kl1` |
| Exploderen | `!` op de hoogste zijde, of bij een voorwaarde; `!!` telt op, `!p` breekt door, `!o` explodeert één keer | `d6!`, `5d10!>=9` |
| Opnieuw gooien | `r` tot de voorwaarde niet meer geldt (standaard: de laagste zijde), `ro` één keer | `2d6r1`, `d20ro<3` |
| Uniek | `u` gooit dubbele opnieuw, `uo` één keer | `4d6u` |
| Begrenzen | `minN`, `maxN` | `4d6min2` |
| Successen, mislukkingen | een voorwaarde direct na de dobbelstenen; `f` voor mislukkingen | `6d10>=8f1`, `12d6>=5` |
| Even, oneven | telt even of oneven dobbelstenen | `4d6even` |
| Crits | `cs`, `cf` (+ voorwaarde) markeren crits; het totaal verandert niet | `d20cs>=19` |
| Sets | `mt` telt sets van gelijke waarden (`mt3`: sets van 3+) | `10d10mt` |
| Marge | `ms`: totaal − N; met `<=`/`<`: N − totaal | `d20ms15`, `d20ms<=@DEX` |
| Sorteren | `sa` (of `s`), `sd` | `5d6sd` |
| Groepen | `{a, b}` + houden/weglaten/successen | `{d8, d6}kh1` |
| Rekenen | `+ - * / // %`, haakjes | `(1d6+2)*2`, `3d6*10` |
| Vergelijkingen | `== <> < <= > >=`, met spaties | `2d6 >= 8` |
| Variabelen | `@name`, `@record.field`, `@{npc:tom.hp}` | `d20 <= @STR`, `(@level)d6` |
| Gegooide aantallen | `(expr)dX` | `(2d4)d8` |
| Functies | `min max abs floor ceil round`; `if(c, a, b)`; `default(@x, 0)` | `max(d6, d8)` |
| Dobbelsteenstappen | `step(die, n)`; `step.extended(…)` volgt de langere reeks d3–d30 | `step(d6, 1)` → een d8 |
| Tags, labels | `tag:expr` geeft een deel een naam; `expr[label]` geeft het een label | `hope:1d12 + fear:1d12`, `d8[fire]` |
| Herhalen | `N#expr` gooit N keer apart | `6#4d6dl1` |
| Pakketmacro's | `pack.name(args)` | `hack.attack(d8, d6)` |

**Spaties tellen:** `2d6>=8` telt dobbelstenen die 8 of meer tonen (op een d6 altijd 0), terwijl `2d6 >= 8` het totaal vergelijkt. Didact waarschuwt je als een succesvoorwaarde niet te halen is.

**Volgorde:** modifiers gelden altijd in deze volgorde, hoe ze ook geschreven zijn: min/max → exploderen → opnieuw gooien → uniek → houden → weglaten → successen en mislukkingen → crits → sets → marge → sorteren.

## Variabelen

- `--as <record>` maakt de numerieke velden van het item beschikbaar: `@hp`, `@STR`, `@stats.str`, en `@<field>` uit het mechanicablok.
- `--var DEX=12` zet één variabele, en kan herhaald worden.
- `@sweeney.hp` leest een veld van een ander item; gebruik `@{npc:tom.hp}` voor id's.
- Een aantal dobbelstenen dat uit variabelen berekend is, verschijnt als gegooid: `(@level)d6` met level 2 wordt gelogd als `2d6 → [3 4] = 7`, en de JSON van de worp bewaart de expressie en de variabelen. Een gegooid aantal toont zijn eigen dobbelstenen: `(2d4)d8 → ([1 4])[4 4 2 1 7]`.

## Echte dobbelstenen, ongedaan maken, afspelen, kansen

- `--got 6,3,4` legt de zijden van echte dobbelstenen vast, in de volgorde waarin ze gegooid zijn. Explosies en herworpen nemen de volgende zijde.
- `didact report 'the tower falls' --of 'the tower'` legt een uitkomst vast die hier niet gegooid is: een getrokken kaart, een blokkentoren, een munt. Die krijgt een worpnummer en komt in het worpenlog, en tijdens een sessie is het ook een resultaatgebeurtenis. `replay` slaat hem over.
- `didact rolls` toont recente worpen.
- `didact undo --event r12 --reason "…"` markeert een worp als ongedaan gemaakt. Hij blijft in het log, en worpnummers gaan nooit terug.
- `didact replay` voert elke gelogde worp opnieuw uit en controleert of elke worp precies hetzelfde oplevert. Elke worp put uit zijn eigen stroom met seed, dus de ene worp verschuift nooit een andere.
- `didact odds '2d6 >= 8'` geeft exacte kansen (via icepool), of een simulatie als exact rekenen niet kan.
- `--seed <text>` put uit een vaste stroom: dezelfde seed geeft dezelfde dobbelstenen.

## Dialectnotities

- `r` gooit steeds opnieuw (Roll20). De `r` van Foundry gooit één keer opnieuw, wat Didact schrijft als `ro`.
- `cs` en `cf` markeren alleen crits, zoals in Roll20. In Foundry tellen ze successen; hier is dat een voorwaarde (`>=19`).
- `d` direct na de dobbelstenen betekent laagste weglaten: `4d6d1` is `4d6dl1`.
- `!=` mag niet. Schrijf `!6` om bij 6 te exploderen, of `<>` voor “niet gelijk”.
