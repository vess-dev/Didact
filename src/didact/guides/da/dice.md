<!-- translated from a81883b64f94 -->
# Terninger

Slå alle terninger gennem Didact, og find aldrig selv på et resultat. Hvert slag får et id (`#r12`), kommer i loggen og kan afspilles igen.

```
didact roll 4d6kh3                          #r12 4d6kh3 → [6 5 3 (2)] = 14
didact roll 'd20 <= @STR' --as freya        #r13 1d20 <= @STR → [7] <= @STR(12) = true
didact roll '6d10>=8f1'                     #r14 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
didact roll '{d8, d6}kh1' --reason "Freya attacks with two daggers"
```

**Sæt udtrykket i anførselstegn**, helst enkelte: `>`, `<`, `!`, `(`, `{`, `#` og mellemrum betyder alle noget for skallen. Uden anførselstegn slår `6d10>=8f1` `6d10` og skriver en fil ved navn `=8f1`.

## Sådan læser du et resultat

`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — reason`

| Tegn | Betydning |
|---|---|
| `(2)` | fravalgt |
| `6!` | eksploderet: den næste terning kom med på grund af den |
| `1→4` | slået om eller begrænset fra 1 til 4 |
| `6+6+2` | en akkumulerende terning: dens slag lagt sammen |
| `6-1` | en gennemtrængende terning: den tæller én mindre |
| `9✓` / `1✗` | en succes / en fiasko |
| `purr:3` | en terning, som en pakkeeffekt har tilføjet |
| `@STR(12)` | en variabel og dens værdi |
| `([1 2])[8 8 8]` | terningerne slået for antallet, derefter puljen |
| `(doubles, max)` | markeringer til regler: `doubles`, `all-same`, `max`, `min`, `exploded`, `rerolled`, `crit`, `fumble`, `capped` |

Didact gentager den kanoniske form, den læste (`4d6k3` → `4d6kh3`), så en anden tolkning aldrig går ubemærket hen.

## Notation

| Hvad | Skriv | Eksempel |
|---|---|---|
| Terninger | `NdX`, `d%` (d100), `dF` (Fate), `d66` (tiere og enere) | `3d6`, `4dF` |
| Egne terninger og pakketerninger | `d{faces}`, `d[name]` | `d{0,0,1,1,2,3}`, `2d[boost]` |
| Behold, fravælg | `khN` (eller `kN`), `klN`, `dlN` (eller `dN`), `dhN` | `4d6kh3`, `2d20kl1` |
| Eksplodér | `!` på den højeste side eller en betingelse; `!!` akkumulerer, `!p` trænger igennem, `!o` eksploderer én gang | `d6!`, `5d10!>=9` |
| Slå om | `r` indtil betingelsen ikke er opfyldt (standard: den laveste side), `ro` én gang | `2d6r1`, `d20ro<3` |
| Unikke | `u` slår dubletter om, `uo` én gang | `4d6u` |
| Begræns | `minN`, `maxN` | `4d6min2` |
| Succeser, fiaskoer | en betingelse lige efter terningerne; `f` for fiaskoer | `6d10>=8f1`, `12d6>=5` |
| Lige, ulige | tæl lige eller ulige terninger | `4d6even` |
| Kritiske slag | `cs`, `cf` (+ betingelse) markerer kritiske slag; summen ændres ikke | `d20cs>=19` |
| Sæt | `mt` tæller sæt af ens (`mt3`: sæt på 3+) | `10d10mt` |
| Margin | `ms`: sum − N; med `<=`/`<`: N − sum | `d20ms15`, `d20ms<=@DEX` |
| Sortér | `sa` (eller `s`), `sd` | `5d6sd` |
| Grupper | `{a, b}` + behold/fravælg/succeser | `{d8, d6}kh1` |
| Regning | `+ - * / // %`, parenteser | `(1d6+2)*2`, `3d6*10` |
| Sammenligninger | `== <> < <= > >=`, med mellemrum | `2d6 >= 8` |
| Variabler | `@name`, `@record.field`, `@{npc:tom.hp}` | `d20 <= @STR`, `(@level)d6` |
| Slået antal | `(expr)dX` | `(2d4)d8` |
| Funktioner | `min max abs floor ceil round`; `if(c, a, b)`; `default(@x, 0)` | `max(d6, d8)` |
| Terningtrin | `step(die, n)`; `step.extended(…)` går ad den længere kæde d3–d30 | `step(d6, 1)` → en d8 |
| Mærker, etiketter | `tag:expr` navngiver en del; `expr[label]` giver den en etiket | `hope:1d12 + fear:1d12`, `d8[fire]` |
| Gentag | `N#expr` slår N gange hver for sig | `6#4d6dl1` |
| Pakkemakroer | `pack.name(args)` | `hack.attack(d8, d6)` |

**Mellemrum betyder noget:** `2d6>=8` tæller terninger, der viser 8 eller mere (altid 0 på en d6), mens `2d6 >= 8` sammenligner summen. Didact advarer dig, når en succesbetingelse ikke kan opfyldes.

**Rækkefølge:** modifikatorer anvendes altid i denne rækkefølge, uanset hvordan de er skrevet: min/max → eksplodér → slå om → unikke → behold → fravælg → succeser og fiaskoer → kritiske slag → sæt → margin → sortér.

## Variabler

- `--as <record>` gør opslagets numeriske felter tilgængelige: `@hp`, `@STR`, `@stats.str` og `@<field>` fra dets mechanics-blok.
- `--var DEX=12` sætter én variabel og kan gentages.
- `@sweeney.hp` læser et felt fra et andet opslag; brug `@{npc:tom.hp}` til id'er.
- Et terningantal, der regnes ud fra variabler, vises som slået: `(@level)d6` med level 2 logges som `2d6 → [3 4] = 7`, og slagets JSON gemmer udtrykket og variablerne. Et slået antal viser sine egne terninger: `(2d4)d8 → ([1 4])[4 4 2 1 7]`.

## Fysiske terninger, fortryd, genafspilning, odds

- `--got 6,3,4` registrerer siderne på rigtige terninger i den rækkefølge, de blev slået. Eksplosioner og omslag tager den næste side.
- `didact report 'the tower falls' --of 'the tower'` registrerer et udfald, der ikke blev slået her: et trukket kort, et klodstårn, en mønt. Det får et slagnummer og kommer i slagloggen, og under en spilgang er det også en resultatbegivenhed. `replay` springer det over.
- `didact rolls` viser de seneste slag.
- `didact undo --event r12 --reason "…"` markerer et slag som fortrudt. Det bliver i loggen, og slagnumre spoles aldrig tilbage.
- `didact replay` kører hvert logget slag igen og tjekker, at hvert enkelt giver præcis det samme. Hvert slag trækker fra sin egen seedede strøm, så ét slag aldrig forskyder et andet.
- `didact odds '2d6 >= 8'` giver præcise sandsynligheder (via icepool) eller en simulering, når præcis matematik ikke er mulig.
- `--seed <text>` trækker fra en fast strøm: samme seed giver samme terninger.

## Om dialekter

- `r` slår om igen og igen (Roll20). Foundrys `r` slår om én gang, hvilket Didact skriver som `ro`.
- `cs` og `cf` markerer kun kritiske slag, som i Roll20. I Foundry tæller de succeser; her er det en betingelse (`>=19`).
- `d` lige efter terningerne betyder fravælg laveste: `4d6d1` er `4d6dl1`.
- `!=` er ikke tilladt. Skriv `!6` for at eksplodere på 6, eller `<>` for »ikke lig med«.
