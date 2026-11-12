<!-- translated from a81883b64f94 -->
# Würfel

Wirf jeden Würfel über Didact und erfinde nie ein Ergebnis. Jeder Wurf bekommt eine ID (`#r12`), landet im Protokoll und lässt sich erneut abspielen.

```
didact roll 4d6kh3                          #r12 4d6kh3 → [6 5 3 (2)] = 14
didact roll 'd20 <= @STR' --as freya        #r13 1d20 <= @STR → [7] <= @STR(12) = true
didact roll '6d10>=8f1'                     #r14 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
didact roll '{d8, d6}kh1' --reason "Freya attacks with two daggers"
```

**Setz den Ausdruck in Anführungszeichen**, am besten in einfache: `>`, `<`, `!`, `(`, `{`, `#` und Leerzeichen bedeuten der Shell alle etwas. Ohne Anführungszeichen würfelt `6d10>=8f1` nur `6d10` und schreibt eine Datei namens `=8f1`.

## Ein Ergebnis lesen

`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — reason`

| Zeichen | Bedeutung |
|---|---|
| `(2)` | verworfen |
| `6!` | explodiert: deswegen kam der nächste Würfel hinzu |
| `1→4` | neu gewürfelt oder begrenzt, von 1 auf 4 |
| `6+6+2` | ein aufaddierender Würfel: seine Würfe zusammengezählt |
| `6-1` | ein durchschlagender Würfel: er zählt eins weniger |
| `9✓` / `1✗` | ein Erfolg / ein Fehlschlag |
| `purr:3` | ein Würfel, den ein Paketeffekt hinzugefügt hat |
| `@STR(12)` | eine Variable und ihr Wert |
| `([1 2])[8 8 8]` | die Würfel für die Anzahl, dann der Pool |
| `(doubles, max)` | Markierungen für Regeln: `doubles`, `all-same`, `max`, `min`, `exploded`, `rerolled`, `crit`, `fumble`, `capped` |

Didact gibt die kanonische Form zurück, die es gelesen hat (`4d6k3` → `4d6kh3`), damit eine abweichende Lesart nie unbemerkt bleibt.

## Notation

| Was | Schreibweise | Beispiel |
|---|---|---|
| Würfel | `NdX`, `d%` (d100), `dF` (Fate), `d66` (Zehner und Einer) | `3d6`, `4dF` |
| Eigene und Paketwürfel | `d{faces}`, `d[name]` | `d{0,0,1,1,2,3}`, `2d[boost]` |
| Behalten, verwerfen | `khN` (oder `kN`), `klN`, `dlN` (oder `dN`), `dhN` | `4d6kh3`, `2d20kl1` |
| Explodieren | `!` auf der höchsten Seite oder bei einer Bedingung; `!!` addiert auf, `!p` schlägt durch, `!o` explodiert einmal | `d6!`, `5d10!>=9` |
| Neu würfeln | `r`, bis die Bedingung verfehlt wird (Standard: die niedrigste Seite), `ro` einmal | `2d6r1`, `d20ro<3` |
| Einmalig | `u` würfelt Doppelte neu, `uo` einmal | `4d6u` |
| Begrenzen | `minN`, `maxN` | `4d6min2` |
| Erfolge, Fehlschläge | eine Bedingung direkt nach den Würfeln; `f` für Fehlschläge | `6d10>=8f1`, `12d6>=5` |
| Gerade, ungerade | zählt gerade oder ungerade Würfel | `4d6even` |
| Kritische | `cs`, `cf` (+ Bedingung) markieren Kritische; die Summe ändert sich nicht | `d20cs>=19` |
| Sätze | `mt` zählt Sätze gleicher Würfel (`mt3`: Sätze ab 3) | `10d10mt` |
| Differenz | `ms`: Summe − N; mit `<=`/`<`: N − Summe | `d20ms15`, `d20ms<=@DEX` |
| Sortieren | `sa` (oder `s`), `sd` | `5d6sd` |
| Gruppen | `{a, b}` + behalten/verwerfen/Erfolge | `{d8, d6}kh1` |
| Rechnen | `+ - * / // %`, Klammern | `(1d6+2)*2`, `3d6*10` |
| Vergleiche | `== <> < <= > >=`, mit Leerzeichen | `2d6 >= 8` |
| Variablen | `@name`, `@record.field`, `@{npc:tom.hp}` | `d20 <= @STR`, `(@level)d6` |
| Gewürfelte Anzahl | `(expr)dX` | `(2d4)d8` |
| Funktionen | `min max abs floor ceil round`; `if(c, a, b)`; `default(@x, 0)` | `max(d6, d8)` |
| Würfelstufen | `step(die, n)`; `step.extended(…)` geht die längere Kette d3–d30 entlang | `step(d6, 1)` → ein d8 |
| Tags, Beschriftungen | `tag:expr` benennt einen Teil; `expr[label]` beschriftet ihn | `hope:1d12 + fear:1d12`, `d8[fire]` |
| Wiederholen | `N#expr` würfelt N-mal getrennt | `6#4d6dl1` |
| Paketmakros | `pack.name(args)` | `hack.attack(d8, d6)` |

**Leerzeichen zählen:** `2d6>=8` zählt Würfel, die 8 oder mehr zeigen (auf einem d6 immer 0), während `2d6 >= 8` die Summe vergleicht. Didact warnt dich, wenn eine Erfolgsbedingung nicht erfüllbar ist.

**Reihenfolge:** Modifikatoren gelten immer in dieser Reihenfolge, egal wie sie geschrieben sind: min/max → explodieren → neu würfeln → einmalig → behalten → verwerfen → Erfolge und Fehlschläge → Kritische → Sätze → Differenz → sortieren.

## Variablen

- `--as <record>` stellt die Zahlenfelder des Eintrags bereit: `@hp`, `@STR`, `@stats.str` und `@<field>` aus seinem Mechanik-Block.
- `--var DEX=12` setzt eine Variable und lässt sich wiederholen.
- `@sweeney.hp` liest das Feld eines anderen Eintrags; für IDs verwende `@{npc:tom.hp}`.
- Eine aus Variablen berechnete Würfelanzahl erscheint wie gewürfelt: `(@level)d6` mit level 2 wird als `2d6 → [3 4] = 7` protokolliert, und das JSON des Wurfs behält den Ausdruck und die Variablen. Eine gewürfelte Anzahl zeigt ihre eigenen Würfel: `(2d4)d8 → ([1 4])[4 4 2 1 7]`.

## Echte Würfel, Rückgängig, Wiederholung, Wahrscheinlichkeiten

- `--got 6,3,4` hält die Seiten echter Würfel fest, in der Reihenfolge, in der sie geworfen wurden. Explosionen und Neuwürfe nehmen die nächste Seite.
- `didact report 'the tower falls' --of 'the tower'` hält ein Ergebnis fest, das nicht hier gewürfelt wurde: eine gezogene Karte, ein Klötzchenturm, eine Münze. Es bekommt eine Wurfnummer und kommt ins Wurfprotokoll, und während einer Sitzung ist es auch ein Ergebnis-Ereignis. `replay` übergeht es.
- `didact rolls` listet die letzten Würfe auf.
- `didact undo --event r12 --reason "…"` markiert einen Wurf als rückgängig gemacht. Er bleibt im Protokoll, und Wurfnummern werden nie zurückgesetzt.
- `didact replay` führt jeden protokollierten Wurf erneut aus und prüft, dass jeder genau dasselbe ergibt. Jeder Wurf zieht aus seinem eigenen, geseedeten Zufallsstrom, sodass kein Wurf einen anderen verschiebt.
- `didact odds '2d6 >= 8'` liefert exakte Wahrscheinlichkeiten (über icepool) oder eine Simulation, wenn sich nicht exakt rechnen lässt.
- `--seed <text>` zieht aus einem festen Strom: derselbe Seed ergibt dieselben Würfel.

## Hinweise zu Dialekten

- `r` würfelt wieder und wieder neu (Roll20). Foundrys `r` würfelt einmal neu, was Didact als `ro` schreibt.
- `cs` und `cf` markieren nur Kritische, wie in Roll20. In Foundry zählen sie Erfolge; hier ist das eine Bedingung (`>=19`).
- `d` direkt nach den Würfeln heißt „niedrigste verwerfen“: `4d6d1` ist `4d6dl1`.
- `!=` ist nicht erlaubt. Schreib `!6`, um bei 6 zu explodieren, oder `<>` für „ungleich“.
