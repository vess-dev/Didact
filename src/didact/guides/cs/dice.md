<!-- translated from a81883b64f94 -->
# Kostky

Každou kostkou házejte přes Didact a nikdy si výsledek nevymýšlejte. Každý hod dostane ID (`#r12`), zapíše se do protokolu a dá se přehrát znovu.

```
didact roll 4d6kh3                          #r12 4d6kh3 → [6 5 3 (2)] = 14
didact roll 'd20 <= @STR' --as freya        #r13 1d20 <= @STR → [7] <= @STR(12) = true
didact roll '6d10>=8f1'                     #r14 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
didact roll '{d8, d6}kh1' --reason "Freya attacks with two daggers"
```

**Výraz dejte do uvozovek**, nejlépe jednoduchých: `>`, `<`, `!`, `(`, `{`, `#` a mezery mají pro shell význam. Bez uvozovek `6d10>=8f1` hodí `6d10` a zapíše soubor s názvem `=8f1`.

## Čtení výsledku

`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — reason`

| Značka | Význam |
|---|---|
| `(2)` | odhozená |
| `6!` | explodovala: kvůli ní se přidala další kostka |
| `1→4` | přehozená nebo oříznutá z 1 na 4 |
| `6+6+2` | sčítací kostka: její hody sečtené |
| `6-1` | pronikající kostka: počítá se o jedna méně |
| `9✓` / `1✗` | úspěch / neúspěch |
| `purr:3` | kostka přidaná efektem balíčku |
| `@STR(12)` | proměnná a její hodnota |
| `([1 2])[8 8 8]` | kostky hozené na počet, pak sada kostek |
| `(doubles, max)` | příznaky pro pravidla: `doubles`, `all-same`, `max`, `min`, `exploded`, `rerolled`, `crit`, `fumble`, `capped` |

Didact vypíše kanonický tvar, jak ho přečetl (`4d6k3` → `4d6kh3`), takže jiný výklad nikdy nezůstane bez povšimnutí.

## Zápis

| Co | Zápis | Příklad |
|---|---|---|
| Kostky | `NdX`, `d%` (d100), `dF` (Fate), `d66` (desítky a jednotky) | `3d6`, `4dF` |
| Vlastní kostky a kostky z balíčků | `d{faces}`, `d[name]` | `d{0,0,1,1,2,3}`, `2d[boost]` |
| Ponechat, odhodit | `khN` (nebo `kN`), `klN`, `dlN` (nebo `dN`), `dhN` | `4d6kh3`, `2d20kl1` |
| Exploze | `!` na nejvyšší stěně nebo při podmínce; `!!` sčítá, `!p` proniká, `!o` exploduje jednou | `d6!`, `5d10!>=9` |
| Přehození | `r`, dokud výsledek splňuje podmínku (výchozí: nejnižší stěna), `ro` jednou | `2d6r1`, `d20ro<3` |
| Unikátní | `u` přehazuje duplicity, `uo` jednou | `4d6u` |
| Oříznutí | `minN`, `maxN` | `4d6min2` |
| Úspěchy, neúspěchy | podmínka hned za kostkami; `f` pro neúspěchy | `6d10>=8f1`, `12d6>=5` |
| Sudé, liché | počítá sudé nebo liché kostky | `4d6even` |
| Kritické hody | `cs`, `cf` (+ podmínka) označí kritické hody; součet se nemění | `d20cs>=19` |
| Sady | `mt` počítá sady shod (`mt3`: sady 3+) | `10d10mt` |
| Rozdíl | `ms`: součet − N; s `<=`/`<`: N − součet | `d20ms15`, `d20ms<=@DEX` |
| Řazení | `sa` (nebo `s`), `sd` | `5d6sd` |
| Skupiny | `{a, b}` + ponechat/odhodit/úspěchy | `{d8, d6}kh1` |
| Matematika | `+ - * / // %`, závorky | `(1d6+2)*2`, `3d6*10` |
| Porovnání | `== <> < <= > >=`, s mezerami | `2d6 >= 8` |
| Proměnné | `@name`, `@record.field`, `@{npc:tom.hp}` | `d20 <= @STR`, `(@level)d6` |
| Házený počet | `(expr)dX` | `(2d4)d8` |
| Funkce | `min max abs floor ceil round`; `if(c, a, b)`; `default(@x, 0)` | `max(d6, d8)` |
| Stupně kostek | `step(die, n)`; `step.extended(…)` prochází delší řadu d3–d30 | `step(d6, 1)` → d8 |
| Štítky, popisky | `tag:expr` pojmenuje část; `expr[label]` jí dá popisek | `hope:1d12 + fear:1d12`, `d8[fire]` |
| Opakování | `N#expr` hodí N-krát zvlášť | `6#4d6dl1` |
| Makra balíčků | `pack.name(args)` | `hack.attack(d8, d6)` |

**Na mezerách záleží:** `2d6>=8` počítá kostky, na kterých padlo 8 nebo víc (na d6 vždy 0), kdežto `2d6 >= 8` porovnává součet. Didact vás upozorní, když podmínku úspěchu nelze splnit.

**Pořadí:** modifikátory se vždy uplatní v tomto pořadí, ať jsou zapsané jakkoli: min/max → exploze → přehození → unikátní → ponechat → odhodit → úspěchy a neúspěchy → kritické hody → sady → rozdíl → řazení.

## Proměnné

- `--as <record>` zpřístupní číselná pole záznamu: `@hp`, `@STR`, `@stats.str` a `@<field>` z jeho bloku mechanik.
- `--var DEX=12` nastaví jednu proměnnou a dá se opakovat.
- `@sweeney.hp` čte pole jiného záznamu; pro ID použijte `@{npc:tom.hp}`.
- Počet kostek spočítaný z proměnných se zobrazí jako hozený: `(@level)d6` při level 2 se zapíše jako `2d6 → [3 4] = 7` a JSON hodu si ponechá výraz i proměnné. Házený počet ukazuje vlastní kostky: `(2d4)d8 → ([1 4])[4 4 2 1 7]`.

## Fyzické kostky, vracení, přehrávání, šance

- `--got 6,3,4` zaznamená stěny skutečných kostek v pořadí, v jakém padly. Exploze a přehození berou další stěnu.
- `didact report 'the tower falls' --of 'the tower'` zaznamená výsledek, který se tu neházel: vytaženou kartu, věž z kostek, minci. Dostane číslo hodu a zapíše se do protokolu hodů a během sezení je to také událost výsledku. `replay` ho přeskočí.
- `didact rolls` vypíše nedávné hody.
- `didact undo --event r12 --reason "…"` označí hod jako vrácený. Zůstane v protokolu a čísla hodů se nikdy nevracejí.
- `didact replay` znovu provede každý zapsaný hod a ověří, že každý vyjde přesně stejně. Každý hod čerpá z vlastního proudu se semínkem, takže jeden hod nikdy neposune jiný.
- `didact odds '2d6 >= 8'` dá přesné pravděpodobnosti (přes icepool), nebo simulaci, když přesný výpočet není k dispozici.
- `--seed <text>` čerpá z pevného proudu: stejné semínko dá stejné kostky.

## Poznámky k dialektům

- `r` přehazuje znovu a znovu (Roll20). `r` ve Foundry přehazuje jednou, což Didact zapisuje jako `ro`.
- `cs` a `cf` jen označují kritické hody, jako v Roll20. Ve Foundry počítají úspěchy; tady na to slouží podmínka (`>=19`).
- `d` hned za kostkami znamená odhodit nejnižší: `4d6d1` je `4d6dl1`.
- `!=` není povoleno. Pro explozi na 6 napište `!6`, pro „nerovná se“ `<>`.
