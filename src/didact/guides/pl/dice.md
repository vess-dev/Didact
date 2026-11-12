<!-- translated from a81883b64f94 -->
# Kości

Rzucaj każdą kością przez Didact i nigdy nie wymyślaj wyniku. Każdy rzut dostaje identyfikator (`#r12`), trafia do logu i można go odtworzyć.

```
didact roll 4d6kh3                          #r12 4d6kh3 → [6 5 3 (2)] = 14
didact roll 'd20 <= @STR' --as freya        #r13 1d20 <= @STR → [7] <= @STR(12) = true
didact roll '6d10>=8f1'                     #r14 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
didact roll '{d8, d6}kh1' --reason "Freya attacks with two daggers"
```

**Ujmij wyrażenie w cudzysłów**, najlepiej pojedynczy: `>`, `<`, `!`, `(`, `{`, `#` i spacje coś znaczą dla powłoki. Bez cudzysłowu `6d10>=8f1` rzuca `6d10` i zapisuje plik o nazwie `=8f1`.

## Odczytywanie wyniku

`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — reason`

| Znak | Znaczenie |
|---|---|
| `(2)` | odrzucona |
| `6!` | eksplodowała: przez nią dodano kolejną kość |
| `1→4` | przerzucona lub przycięta z 1 do 4 |
| `6+6+2` | kość kumulująca: jej rzuty zsumowane |
| `6-1` | kość przebijająca: liczy się o jeden mniej |
| `9✓` / `1✗` | sukces / porażka |
| `purr:3` | kość dodana przez efekt pakietu |
| `@STR(12)` | zmienna i jej wartość |
| `([1 2])[8 8 8]` | kości rzucone na liczbę kości, potem pula |
| `(doubles, max)` | flagi dla zasad: `doubles`, `all-same`, `max`, `min`, `exploded`, `rerolled`, `crit`, `fumble`, `capped` |

Didact powtarza kanoniczną postać, którą odczytał (`4d6k3` → `4d6kh3`), więc inna interpretacja nigdy nie przejdzie niezauważona.

## Notacja

| Co | Zapis | Przykład |
|---|---|---|
| Kości | `NdX`, `d%` (d100), `dF` (Fate), `d66` (dziesiątki i jedności) | `3d6`, `4dF` |
| Kości własne i z pakietów | `d{faces}`, `d[name]` | `d{0,0,1,1,2,3}`, `2d[boost]` |
| Zachowaj, odrzuć | `khN` (lub `kN`), `klN`, `dlN` (lub `dN`), `dhN` | `4d6kh3`, `2d20kl1` |
| Eksplozja | `!` na najwyższej ściance lub przy warunku; `!!` kumuluje, `!p` przebija, `!o` eksploduje raz | `d6!`, `5d10!>=9` |
| Przerzut | `r` dopóki wynik spełnia warunek (domyślnie: najniższa ścianka), `ro` raz | `2d6r1`, `d20ro<3` |
| Unikalne | `u` przerzuca duplikaty, `uo` raz | `4d6u` |
| Przycięcie | `minN`, `maxN` | `4d6min2` |
| Sukcesy, porażki | warunek zaraz po kościach; `f` dla porażek | `6d10>=8f1`, `12d6>=5` |
| Parzyste, nieparzyste | liczy kości parzyste lub nieparzyste | `4d6even` |
| Krytyki | `cs`, `cf` (+ warunek) oznaczają krytyki; suma się nie zmienia | `d20cs>=19` |
| Zestawy | `mt` liczy zestawy takich samych wyników (`mt3`: zestawy 3+) | `10d10mt` |
| Margines | `ms`: suma − N; z `<=`/`<`: N − suma | `d20ms15`, `d20ms<=@DEX` |
| Sortowanie | `sa` (lub `s`), `sd` | `5d6sd` |
| Grupy | `{a, b}` + zachowaj/odrzuć/sukcesy | `{d8, d6}kh1` |
| Matematyka | `+ - * / // %`, nawiasy | `(1d6+2)*2`, `3d6*10` |
| Porównania | `== <> < <= > >=`, ze spacjami | `2d6 >= 8` |
| Zmienne | `@name`, `@record.field`, `@{npc:tom.hp}` | `d20 <= @STR`, `(@level)d6` |
| Wylosowana liczba kości | `(expr)dX` | `(2d4)d8` |
| Funkcje | `min max abs floor ceil round`; `if(c, a, b)`; `default(@x, 0)` | `max(d6, d8)` |
| Stopnie kości | `step(die, n)`; `step.extended(…)` przechodzi dłuższy łańcuch d3–d30 | `step(d6, 1)` → d8 |
| Tagi, etykiety | `tag:expr` nazywa część; `expr[label]` nadaje jej etykietę | `hope:1d12 + fear:1d12`, `d8[fire]` |
| Powtórzenie | `N#expr` rzuca N razy osobno | `6#4d6dl1` |
| Makra pakietów | `pack.name(args)` | `hack.attack(d8, d6)` |

**Spacje mają znaczenie:** `2d6>=8` liczy kości, na których wypadło 8 lub więcej (na d6 zawsze 0), a `2d6 >= 8` porównuje sumę. Didact ostrzega, gdy warunku sukcesu nie da się spełnić.

**Kolejność:** modyfikatory zawsze działają w tej kolejności, niezależnie od zapisu: min/max → eksplozja → przerzut → unikalne → zachowaj → odrzuć → sukcesy i porażki → krytyki → zestawy → margines → sortowanie.

## Zmienne

- `--as <record>` udostępnia liczbowe pola wpisu: `@hp`, `@STR`, `@stats.str` i `@<field>` z jego bloku mechaniki.
- `--var DEX=12` ustawia jedną zmienną; można go powtarzać.
- `@sweeney.hp` odczytuje pole innego wpisu; dla identyfikatorów użyj `@{npc:tom.hp}`.
- Liczba kości wyliczona ze zmiennych jest pokazywana jak rzucona: `(@level)d6` przy level 2 trafia do logu jako `2d6 → [3 4] = 7`, a JSON rzutu zachowuje wyrażenie i zmienne. Wylosowana liczba kości pokazuje własne kości: `(2d4)d8 → ([1 4])[4 4 2 1 7]`.

## Prawdziwe kości, cofanie, odtwarzanie, szanse

- `--got 6,3,4` zapisuje ścianki prawdziwych kości w kolejności rzutu. Eksplozje i przerzuty biorą kolejną ściankę.
- `didact report 'the tower falls' --of 'the tower'` zapisuje wynik, którego nie wyrzucono tutaj: wyciągniętą kartę, wieżę z klocków, monetę. Dostaje numer rzutu i trafia do logu rzutów, a podczas sesji jest też wydarzeniem-wynikiem. `replay` go pomija.
- `didact rolls` wyświetla ostatnie rzuty.
- `didact undo --event r12 --reason "…"` oznacza rzut jako cofnięty. Zostaje on w logu, a numeracja rzutów nigdy się nie cofa.
- `didact replay` ponownie wykonuje każdy zapisany rzut i sprawdza, czy każdy odtwarza się dokładnie. Każdy rzut losuje z własnego strumienia z ziarnem, więc jeden rzut nigdy nie przesuwa innego.
- `didact odds '2d6 >= 8'` podaje dokładne prawdopodobieństwa (przez icepool) albo symulację, gdy dokładne obliczenie jest niemożliwe.
- `--seed <text>` losuje ze stałego strumienia: to samo ziarno daje te same kości.

## Uwagi o dialektach

- `r` przerzuca raz za razem (Roll20). `r` w Foundry przerzuca raz, co Didact zapisuje jako `ro`.
- `cs` i `cf` tylko oznaczają krytyki, jak w Roll20. W Foundry liczą sukcesy; tutaj służy do tego warunek (`>=19`).
- `d` zaraz po kościach oznacza odrzucenie najniższej: `4d6d1` to `4d6dl1`.
- `!=` jest niedozwolone. Napisz `!6`, by eksplodować na 6, lub `<>` dla „różne od”.
