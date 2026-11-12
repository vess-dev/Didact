<!-- translated from a81883b64f94 -->
# Tärningar

Slå varje tärning genom Didact, och hitta aldrig på ett resultat. Varje slag får ett id (`#r12`), hamnar i loggen och kan spelas upp igen.

```
didact roll 4d6kh3                          #r12 4d6kh3 → [6 5 3 (2)] = 14
didact roll 'd20 <= @STR' --as freya        #r13 1d20 <= @STR → [7] <= @STR(12) = true
didact roll '6d10>=8f1'                     #r14 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
didact roll '{d8, d6}kh1' --reason "Freya attacks with two daggers"
```

**Sätt uttrycket inom citattecken**, helst enkla: `>`, `<`, `!`, `(`, `{`, `#` och mellanslag betyder alla något för skalet. Utan citattecken slår `6d10>=8f1` bara `6d10` och skriver en fil som heter `=8f1`.

## Att läsa ett resultat

`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — reason`

| Märkning | Betydelse |
|---|---|
| `(2)` | bortplockad |
| `6!` | exploderade: nästa tärning lades till på grund av den |
| `1→4` | omslagen eller begränsad från 1 till 4 |
| `6+6+2` | en ackumulerande tärning: dess slag adderade |
| `6-1` | en genomträngande tärning: den räknas som en lägre |
| `9✓` / `1✗` | ett lyckat / ett misslyckat |
| `purr:3` | en tärning som lagts till av en paketeffekt |
| `@STR(12)` | en variabel och dess värde |
| `([1 2])[8 8 8]` | tärningarna som slogs för antalet, sedan poolen |
| `(doubles, max)` | flaggor för regler: `doubles`, `all-same`, `max`, `min`, `exploded`, `rerolled`, `crit`, `fumble`, `capped` |

Didact skriver ut den kanoniska form det läste (`4d6k3` → `4d6kh3`), så att en annan tolkning aldrig går obemärkt förbi.

## Notation

| Vad | Skriv | Exempel |
|---|---|---|
| Tärningar | `NdX`, `d%` (d100), `dF` (Fate), `d66` (tiotal och ental) | `3d6`, `4dF` |
| Egna tärningar och pakettärningar | `d{faces}`, `d[name]` | `d{0,0,1,1,2,3}`, `2d[boost]` |
| Behåll, plocka bort | `khN` (eller `kN`), `klN`, `dlN` (eller `dN`), `dhN` | `4d6kh3`, `2d20kl1` |
| Explodera | `!` på högsta sidan, eller ett villkor; `!!` ackumulerar, `!p` tränger igenom, `!o` exploderar en gång | `d6!`, `5d10!>=9` |
| Slå om | `r` tills villkoret inte uppfylls (standard: lägsta sidan), `ro` en gång | `2d6r1`, `d20ro<3` |
| Unika | `u` slår om dubbletter, `uo` en gång | `4d6u` |
| Begränsa | `minN`, `maxN` | `4d6min2` |
| Lyckade, misslyckade | ett villkor direkt efter tärningarna; `f` för misslyckade | `6d10>=8f1`, `12d6>=5` |
| Jämna, udda | räkna jämna eller udda tärningar | `4d6even` |
| Kritiska | `cs`, `cf` (+ villkor) markerar kritiska; summan ändras inte | `d20cs>=19` |
| Set | `mt` räknar set av lika (`mt3`: set om 3+) | `10d10mt` |
| Marginal | `ms`: summa − N; med `<=`/`<`: N − summa | `d20ms15`, `d20ms<=@DEX` |
| Sortera | `sa` (eller `s`), `sd` | `5d6sd` |
| Grupper | `{a, b}` + behåll/plocka bort/lyckade | `{d8, d6}kh1` |
| Matematik | `+ - * / // %`, parenteser | `(1d6+2)*2`, `3d6*10` |
| Jämförelser | `== <> < <= > >=`, med mellanslag | `2d6 >= 8` |
| Variabler | `@name`, `@record.field`, `@{npc:tom.hp}` | `d20 <= @STR`, `(@level)d6` |
| Slagna antal | `(expr)dX` | `(2d4)d8` |
| Funktioner | `min max abs floor ceil round`; `if(c, a, b)`; `default(@x, 0)` | `max(d6, d8)` |
| Tärningssteg | `step(die, n)`; `step.extended(…)` går längs den längre kedjan d3–d30 | `step(d6, 1)` → en d8 |
| Taggar, etiketter | `tag:expr` namnger en del; `expr[label]` ger den en etikett | `hope:1d12 + fear:1d12`, `d8[fire]` |
| Upprepa | `N#expr` slår N separata gånger | `6#4d6dl1` |
| Paketmakron | `pack.name(args)` | `hack.attack(d8, d6)` |

**Mellanslag spelar roll:** `2d6>=8` räknar tärningar som visar 8 eller mer (alltid 0 på en d6), medan `2d6 >= 8` jämför summan. Didact varnar dig när ett villkor för lyckade inte kan uppfyllas.

**Ordning:** modifierare tillämpas alltid i den här ordningen, hur de än skrivs: min/max → explodera → slå om → unika → behåll → plocka bort → lyckade och misslyckade → kritiska → set → marginal → sortera.

## Variabler

- `--as <record>` gör uppslagets numeriska fält tillgängliga: `@hp`, `@STR`, `@stats.str`, och `@<field>` från dess mechanics-block.
- `--var DEX=12` sätter en variabel och kan upprepas.
- `@sweeney.hp` läser ett annat uppslags fält; använd `@{npc:tom.hp}` för id:n.
- Ett tärningsantal som räknas fram ur variabler visas som slaget: `(@level)d6` med level 2 loggas som `2d6 → [3 4] = 7`, och slagets JSON behåller uttrycket och variablerna. Ett slaget antal visar sina egna tärningar: `(2d4)d8 → ([1 4])[4 4 2 1 7]`.

## Fysiska tärningar, ångra, uppspelning, odds

- `--got 6,3,4` registrerar sidorna på riktiga tärningar, i den ordning de slogs. Explosioner och omslag tar nästa sida.
- `didact report 'the tower falls' --of 'the tower'` registrerar ett utfall som inte slogs här: ett draget kort, ett klosstorn, ett mynt. Det får ett slagnummer och hamnar i slagloggen, och under ett spelmöte är det också en resultathändelse. `replay` hoppar över det.
- `didact rolls` listar de senaste slagen.
- `didact undo --event r12 --reason "…"` markerar ett slag som ångrat. Det finns kvar i loggen, och slagnumren räknas aldrig bakåt.
- `didact replay` kör om varje loggat slag och kontrollerar att vart och ett återskapas exakt. Varje slag drar från sin egen seedade ström, så ett slag förskjuter aldrig ett annat.
- `didact odds '2d6 >= 8'` ger exakta sannolikheter (via icepool), eller en simulering när exakt matematik inte går.
- `--seed <text>` drar från en fast ström: samma seed ger samma tärningar.

## Om dialekter

- `r` slår om gång på gång (Roll20). Foundrys `r` slår om en gång, vilket Didact skriver som `ro`.
- `cs` och `cf` markerar bara kritiska, som i Roll20. I Foundry räknar de lyckade; här är det ett villkor (`>=19`).
- `d` direkt efter tärningarna betyder plocka bort lägsta: `4d6d1` är `4d6dl1`.
- `!=` är inte tillåtet. Skriv `!6` för att explodera på 6, eller `<>` för ”inte lika med”.
