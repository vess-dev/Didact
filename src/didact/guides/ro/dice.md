<!-- translated from a81883b64f94 -->
# Zaruri

Aruncă fiecare zar prin Didact și nu inventa niciodată un rezultat. Fiecare aruncare primește un ID (`#r12`), intră în jurnal și poate fi rejucată.

```
didact roll 4d6kh3                          #r12 4d6kh3 → [6 5 3 (2)] = 14
didact roll 'd20 <= @STR' --as freya        #r13 1d20 <= @STR → [7] <= @STR(12) = true
didact roll '6d10>=8f1'                     #r14 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
didact roll '{d8, d6}kh1' --reason "Freya attacks with two daggers"
```

**Pune expresia între ghilimele**, de preferință simple: `>`, `<`, `!`, `(`, `{`, `#` și spațiile înseamnă ceva pentru shell. Fără ghilimele, `6d10>=8f1` aruncă `6d10` și scrie un fișier numit `=8f1`.

## Citirea unui rezultat

`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — reason`

| Semn | Înțeles |
|---|---|
| `(2)` | eliminat |
| `6!` | a explodat: din cauza lui s-a adăugat zarul următor |
| `1→4` | rearuncat sau limitat de la 1 la 4 |
| `6+6+2` | un zar cumulativ: aruncările lui adunate |
| `6-1` | un zar penetrant: contează cu unu mai puțin |
| `9✓` / `1✗` | un succes / un eșec |
| `purr:3` | un zar adăugat de un efect al unui pachet |
| `@STR(12)` | o variabilă și valoarea ei |
| `([1 2])[8 8 8]` | zarurile aruncate pentru număr, apoi rezerva |
| `(doubles, max)` | indicatori pentru reguli: `doubles`, `all-same`, `max`, `min`, `exploded`, `rerolled`, `crit`, `fumble`, `capped` |

Didact afișează forma canonică pe care a citit-o (`4d6k3` → `4d6kh3`), așa că o citire diferită nu trece niciodată neobservată.

## Notație

| Ce | Scrii | Exemplu |
|---|---|---|
| Zaruri | `NdX`, `d%` (d100), `dF` (Fate), `d66` (zeci și unități) | `3d6`, `4dF` |
| Zaruri personalizate și din pachete | `d{faces}`, `d[name]` | `d{0,0,1,1,2,3}`, `2d[boost]` |
| Păstrare, eliminare | `khN` (sau `kN`), `klN`, `dlN` (sau `dN`), `dhN` | `4d6kh3`, `2d20kl1` |
| Explozie | `!` pe fața maximă, sau o condiție; `!!` cumulează, `!p` penetrează, `!o` explodează o dată | `d6!`, `5d10!>=9` |
| Rearuncare | `r` până nu mai îndeplinește condiția (implicit: fața minimă), `ro` o dată | `2d6r1`, `d20ro<3` |
| Unice | `u` rearuncă dublurile, `uo` o dată | `4d6u` |
| Limitare | `minN`, `maxN` | `4d6min2` |
| Succese, eșecuri | o condiție imediat după zaruri; `f` pentru eșecuri | `6d10>=8f1`, `12d6>=5` |
| Par, impar | numără zarurile pare sau impare | `4d6even` |
| Critice | `cs`, `cf` (+ condiție) marchează criticele; totalul nu se schimbă | `d20cs>=19` |
| Seturi | `mt` numără seturile de potriviri (`mt3`: seturi de 3+) | `10d10mt` |
| Marjă | `ms`: total − N; cu `<=`/`<`: N − total | `d20ms15`, `d20ms<=@DEX` |
| Sortare | `sa` (sau `s`), `sd` | `5d6sd` |
| Grupuri | `{a, b}` + păstrare/eliminare/succese | `{d8, d6}kh1` |
| Calcule | `+ - * / // %`, paranteze | `(1d6+2)*2`, `3d6*10` |
| Comparații | `== <> < <= > >=`, cu spații | `2d6 >= 8` |
| Variabile | `@name`, `@record.field`, `@{npc:tom.hp}` | `d20 <= @STR`, `(@level)d6` |
| Număr aruncat | `(expr)dX` | `(2d4)d8` |
| Funcții | `min max abs floor ceil round`; `if(c, a, b)`; `default(@x, 0)` | `max(d6, d8)` |
| Trepte de zar | `step(die, n)`; `step.extended(…)` parcurge lanțul mai lung d3–d30 | `step(d6, 1)` → un d8 |
| Etichete | `tag:expr` numește o parte; `expr[label]` o etichetează | `hope:1d12 + fear:1d12`, `d8[fire]` |
| Repetare | `N#expr` aruncă de N ori separat | `6#4d6dl1` |
| Macrouri din pachete | `pack.name(args)` | `hack.attack(d8, d6)` |

**Spațiile contează:** `2d6>=8` numără zarurile care arată 8 sau mai mult (mereu 0 pe un d6), iar `2d6 >= 8` compară totalul. Didact te avertizează când o condiție de succes nu poate fi îndeplinită.

**Ordinea:** modificatorii se aplică mereu în această ordine, oricum ar fi scriși: min/max → explozie → rearuncare → unice → păstrare → eliminare → succese și eșecuri → critice → seturi → marjă → sortare.

## Variabile

- `--as <record>` pune la dispoziție câmpurile numerice ale fișei: `@hp`, `@STR`, `@stats.str` și `@<field>` din blocul ei de mecanici.
- `--var DEX=12` setează o variabilă și se poate repeta.
- `@sweeney.hp` citește câmpul altei fișe; pentru ID-uri folosește `@{npc:tom.hp}`.
- Un număr de zaruri calculat din variabile apare ca aruncat: `(@level)d6` cu nivelul 2 se notează `2d6 → [3 4] = 7`, iar JSON-ul aruncării păstrează expresia și variabilele. Un număr aruncat își arată propriile zaruri: `(2d4)d8 → ([1 4])[4 4 2 1 7]`.

## Zaruri fizice, desfacere, rejucare, șanse

- `--got 6,3,4` înregistrează fețele unor zaruri reale, în ordinea în care au fost aruncate. Exploziile și rearuncările iau fața următoare.
- `didact report 'the tower falls' --of 'the tower'` înregistrează un rezultat care n-a fost aruncat aici: o carte trasă, un turn de blocuri, o monedă. Primește un număr de aruncare și intră în istoricul aruncărilor, iar într-o sesiune e și un eveniment de rezultat. `replay` îl sare.
- `didact rolls` listează aruncările recente.
- `didact undo --event r12 --reason "…"` marchează o aruncare ca desfăcută. Rămâne în jurnal, iar numerele aruncărilor nu dau niciodată înapoi.
- `didact replay` rulează din nou fiecare aruncare notată și verifică dacă fiecare se reproduce exact. Fiecare aruncare trage din propriul flux cu seed, așa că o aruncare nu o deplasează niciodată pe alta.
- `didact odds '2d6 >= 8'` dă probabilități exacte (prin icepool) sau o simulare când calculul exact nu e posibil.
- `--seed <text>` trage dintr-un flux fix: același seed dă aceleași zaruri.

## Note despre dialecte

- `r` rearuncă iar și iar (Roll20). În Foundry, `r` rearuncă o dată, ceea ce Didact scrie `ro`.
- `cs` și `cf` doar marchează criticele, ca în Roll20. În Foundry ele numără succese; aici pentru asta e o condiție (`>=19`).
- `d` imediat după zaruri înseamnă eliminarea celui mai mic: `4d6d1` este `4d6dl1`.
- `!=` nu e permis. Scrie `!6` ca să explodeze pe 6, sau `<>` pentru „diferit de”.
