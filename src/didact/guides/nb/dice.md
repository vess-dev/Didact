<!-- translated from a81883b64f94 -->
# Terninger

Kast alle terninger gjennom Didact, og dikt aldri opp et resultat. Hvert kast får en ID (`#r12`), havner i loggen og kan spilles av på nytt.

```
didact roll 4d6kh3                          #r12 4d6kh3 → [6 5 3 (2)] = 14
didact roll 'd20 <= @STR' --as freya        #r13 1d20 <= @STR → [7] <= @STR(12) = true
didact roll '6d10>=8f1'                     #r14 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
didact roll '{d8, d6}kh1' --reason "Freya attacks with two daggers"
```

**Sett uttrykket i anførselstegn**, helst enkle: `>`, `<`, `!`, `(`, `{`, `#` og mellomrom betyr alle noe for skallet. Uten anførselstegn kaster `6d10>=8f1` `6d10` og skriver en fil som heter `=8f1`.

## Slik leser du et resultat

`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — reason`

| Merke | Betydning |
|---|---|
| `(2)` | forkastet |
| `6!` | eksplodert: neste terning kom med på grunn av den |
| `1→4` | kastet om eller begrenset fra 1 til 4 |
| `6+6+2` | en akkumulerende terning: kastene lagt sammen |
| `6-1` | en gjennomtrengende terning: den teller én mindre |
| `9✓` / `1✗` | en suksess / en fiasko |
| `purr:3` | en terning lagt til av en pakkeeffekt |
| `@STR(12)` | en variabel og verdien dens |
| `([1 2])[8 8 8]` | terningene kastet for antallet, deretter puljen |
| `(doubles, max)` | markeringer for regler: `doubles`, `all-same`, `max`, `min`, `exploded`, `rerolled`, `crit`, `fumble`, `capped` |

Didact gjentar den kanoniske formen den leste (`4d6k3` → `4d6kh3`), så en annen tolkning aldri går upåaktet hen.

## Notasjon

| Hva | Skriv | Eksempel |
|---|---|---|
| Terninger | `NdX`, `d%` (d100), `dF` (Fate), `d66` (tiere og enere) | `3d6`, `4dF` |
| Egne terninger og pakketerninger | `d{faces}`, `d[name]` | `d{0,0,1,1,2,3}`, `2d[boost]` |
| Behold, forkast | `khN` (eller `kN`), `klN`, `dlN` (eller `dN`), `dhN` | `4d6kh3`, `2d20kl1` |
| Eksploder | `!` på høyeste side, eller en betingelse; `!!` akkumulerer, `!p` trenger gjennom, `!o` eksploderer én gang | `d6!`, `5d10!>=9` |
| Kast om | `r` til betingelsen ikke er oppfylt (standard: laveste side), `ro` én gang | `2d6r1`, `d20ro<3` |
| Unike | `u` kaster duplikater om, `uo` én gang | `4d6u` |
| Begrens | `minN`, `maxN` | `4d6min2` |
| Suksesser, fiaskoer | en betingelse rett etter terningene; `f` for fiaskoer | `6d10>=8f1`, `12d6>=5` |
| Partall, oddetall | tell terninger med partall eller oddetall | `4d6even` |
| Kritiske kast | `cs`, `cf` (+ betingelse) markerer kritiske kast; summen endres ikke | `d20cs>=19` |
| Sett | `mt` teller sett av like (`mt3`: sett på 3+) | `10d10mt` |
| Margin | `ms`: sum − N; med `<=`/`<`: N − sum | `d20ms15`, `d20ms<=@DEX` |
| Sorter | `sa` (eller `s`), `sd` | `5d6sd` |
| Grupper | `{a, b}` + behold/forkast/suksesser | `{d8, d6}kh1` |
| Regning | `+ - * / // %`, parenteser | `(1d6+2)*2`, `3d6*10` |
| Sammenligninger | `== <> < <= > >=`, med mellomrom | `2d6 >= 8` |
| Variabler | `@name`, `@record.field`, `@{npc:tom.hp}` | `d20 <= @STR`, `(@level)d6` |
| Kastet antall | `(expr)dX` | `(2d4)d8` |
| Funksjoner | `min max abs floor ceil round`; `if(c, a, b)`; `default(@x, 0)` | `max(d6, d8)` |
| Terningtrinn | `step(die, n)`; `step.extended(…)` går langs den lengre kjeden d3–d30 | `step(d6, 1)` → en d8 |
| Merker, etiketter | `tag:expr` gir en del et navn; `expr[label]` gir den en etikett | `hope:1d12 + fear:1d12`, `d8[fire]` |
| Gjenta | `N#expr` kaster N ganger hver for seg | `6#4d6dl1` |
| Pakkemakroer | `pack.name(args)` | `hack.attack(d8, d6)` |

**Mellomrom betyr noe:** `2d6>=8` teller terninger som viser 8 eller mer (alltid 0 på en d6), mens `2d6 >= 8` sammenligner summen. Didact advarer deg når en suksessbetingelse ikke kan oppfylles.

**Rekkefølge:** modifikatorer brukes alltid i denne rekkefølgen, uansett hvordan de er skrevet: min/max → eksploder → kast om → unike → behold → forkast → suksesser og fiaskoer → kritiske kast → sett → margin → sorter.

## Variabler

- `--as <record>` gjør oppslagets numeriske felter tilgjengelige: `@hp`, `@STR`, `@stats.str` og `@<field>` fra mechanics-blokken.
- `--var DEX=12` setter én variabel, og kan gjentas.
- `@sweeney.hp` leser et felt fra et annet oppslag; bruk `@{npc:tom.hp}` for ID-er.
- Et terningantall regnet ut fra variabler vises som kastet: `(@level)d6` med level 2 logges som `2d6 → [3 4] = 7`, og kastets JSON tar vare på uttrykket og variablene. Et kastet antall viser sine egne terninger: `(2d4)d8 → ([1 4])[4 4 2 1 7]`.

## Fysiske terninger, angre, avspilling, odds

- `--got 6,3,4` registrerer sidene på ekte terninger, i den rekkefølgen de ble kastet. Eksplosjoner og omkast tar neste side.
- `didact report 'the tower falls' --of 'the tower'` registrerer et utfall som ikke ble kastet her: et trukket kort, et klosstårn, en mynt. Det får et kastnummer og havner i kastloggen, og under en økt er det også en resultathendelse. `replay` hopper over det.
- `didact rolls` viser de siste kastene.
- `didact undo --event r12 --reason "…"` markerer et kast som angret. Det blir værende i loggen, og kastnumre spoles aldri tilbake.
- `didact replay` kjører hvert logget kast på nytt og sjekker at hvert av dem gir nøyaktig det samme. Hvert kast trekker fra sin egen seedede strøm, så ett kast aldri forskyver et annet.
- `didact odds '2d6 >= 8'` gir eksakte sannsynligheter (via icepool), eller en simulering når eksakt matematikk ikke er mulig.
- `--seed <text>` trekker fra en fast strøm: samme seed gir samme terninger.

## Om dialekter

- `r` kaster om igjen og igjen (Roll20). Foundrys `r` kaster om én gang, noe Didact skriver som `ro`.
- `cs` og `cf` markerer bare kritiske kast, som i Roll20. I Foundry teller de suksesser; her er det en betingelse (`>=19`).
- `d` rett etter terningene betyr forkast laveste: `4d6d1` er `4d6dl1`.
- `!=` er ikke tillatt. Skriv `!6` for å eksplodere på 6, eller `<>` for «ikke lik».
