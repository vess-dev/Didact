<!-- translated from a81883b64f94 -->
# Dadi

Tira ogni dado tramite Didact, e non inventare mai un risultato. Ogni tiro riceve un id (`#r12`), finisce nel registro e può essere ripetuto.

```
didact roll 4d6kh3                          #r12 4d6kh3 → [6 5 3 (2)] = 14
didact roll 'd20 <= @STR' --as freya        #r13 1d20 <= @STR → [7] <= @STR(12) = true
didact roll '6d10>=8f1'                     #r14 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
didact roll '{d8, d6}kh1' --reason "Freya attacks with two daggers"
```

**Metti l'espressione tra virgolette**, preferibilmente singole: `>`, `<`, `!`, `(`, `{`, `#` e gli spazi hanno tutti un significato per la shell. Senza virgolette, `6d10>=8f1` tira `6d10` e scrive un file chiamato `=8f1`.

## Leggere un risultato

`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — reason`

| Segno | Significato |
|---|---|
| `(2)` | scartato |
| `6!` | esploso: il dado successivo è stato aggiunto per causa sua |
| `1→4` | ritirato o limitato da 1 a 4 |
| `6+6+2` | un dado cumulativo: i suoi tiri sommati |
| `6-1` | un dado penetrante: conta uno in meno |
| `9✓` / `1✗` | un successo / un fallimento |
| `purr:3` | un dado aggiunto da un effetto di un pack |
| `@STR(12)` | una variabile e il suo valore |
| `([1 2])[8 8 8]` | i dadi tirati per il numero, poi la riserva |
| `(doubles, max)` | indicatori per le regole: `doubles`, `all-same`, `max`, `min`, `exploded`, `rerolled`, `crit`, `fumble`, `capped` |

Didact riporta la forma canonica che ha letto (`4d6k3` → `4d6kh3`), così una lettura diversa non passa mai inosservata.

## Notazione

| Cosa | Scrivi | Esempio |
|---|---|---|
| Dadi | `NdX`, `d%` (d100), `dF` (Fate), `d66` (decine e unità) | `3d6`, `4dF` |
| Dadi personalizzati e dei pack | `d{faces}`, `d[name]` | `d{0,0,1,1,2,3}`, `2d[boost]` |
| Tenere, scartare | `khN` (o `kN`), `klN`, `dlN` (o `dN`), `dhN` | `4d6kh3`, `2d20kl1` |
| Esplosione | `!` sulla faccia massima, o una condizione; `!!` cumula, `!p` penetra, `!o` esplode una volta | `d6!`, `5d10!>=9` |
| Ritiro | `r` finché non manca la condizione (predefinita: la faccia più bassa), `ro` una volta | `2d6r1`, `d20ro<3` |
| Unici | `u` ritira i doppioni, `uo` una volta | `4d6u` |
| Limiti | `minN`, `maxN` | `4d6min2` |
| Successi, fallimenti | una condizione subito dopo i dadi; `f` per i fallimenti | `6d10>=8f1`, `12d6>=5` |
| Pari, dispari | conta i dadi pari o dispari | `4d6even` |
| Critici | `cs`, `cf` (+ condizione) segnano i critici; il totale non cambia | `d20cs>=19` |
| Serie | `mt` conta le serie di dadi uguali (`mt3`: serie di 3 o più) | `10d10mt` |
| Margine | `ms`: totale − N; con `<=`/`<`: N − totale | `d20ms15`, `d20ms<=@DEX` |
| Ordinamento | `sa` (o `s`), `sd` | `5d6sd` |
| Gruppi | `{a, b}` + tenere/scartare/successi | `{d8, d6}kh1` |
| Calcoli | `+ - * / // %`, parentesi | `(1d6+2)*2`, `3d6*10` |
| Confronti | `== <> < <= > >=`, con gli spazi | `2d6 >= 8` |
| Variabili | `@name`, `@record.field`, `@{npc:tom.hp}` | `d20 <= @STR`, `(@level)d6` |
| Numero di dadi tirato | `(expr)dX` | `(2d4)d8` |
| Funzioni | `min max abs floor ceil round`; `if(c, a, b)`; `default(@x, 0)` | `max(d6, d8)` |
| Gradini dei dadi | `step(die, n)`; `step.extended(…)` percorre la catena più lunga d3–d30 | `step(d6, 1)` → un d8 |
| Tag, etichette | `tag:expr` dà un nome a una parte; `expr[label]` la etichetta | `hope:1d12 + fear:1d12`, `d8[fire]` |
| Ripetizione | `N#expr` tira N volte separatamente | `6#4d6dl1` |
| Macro dei pack | `pack.name(args)` | `hack.attack(d8, d6)` |

**Gli spazi contano:** `2d6>=8` conta i dadi che mostrano 8 o più (sempre 0 su un d6), mentre `2d6 >= 8` confronta il totale. Didact ti avvisa quando una condizione di successo è impossibile.

**Ordine:** i modificatori si applicano sempre in quest'ordine, comunque siano scritti: min/max → esplosione → ritiro → unici → tenere → scartare → successi e fallimenti → critici → serie → margine → ordinamento.

## Variabili

- `--as <record>` rende disponibili i campi numerici della scheda: `@hp`, `@STR`, `@stats.str`, e `@<field>` dal suo blocco di meccaniche.
- `--var DEX=12` imposta una variabile, e si può ripetere.
- `@sweeney.hp` legge il campo di un'altra scheda; usa `@{npc:tom.hp}` per gli id.
- Un numero di dadi ricavato da variabili appare come tirato: `(@level)d6` con livello 2 viene registrato come `2d6 → [3 4] = 7`, e il JSON del tiro conserva l'espressione e le variabili. Un numero tirato ai dadi mostra i propri dadi: `(2d4)d8 → ([1 4])[4 4 2 1 7]`.

## Dadi fisici, annullamento, ripetizione, probabilità

- `--got 6,3,4` registra le facce di dadi veri, nell'ordine in cui sono stati tirati. Esplosioni e ritiri prendono la faccia successiva.
- `didact report 'the tower falls' --of 'the tower'` registra un risultato non tirato qui: una carta pescata, una torre di blocchi, una moneta. Riceve un numero di tiro e va nel registro dei tiri, e durante una sessione è anche un evento di risultato. `replay` lo salta.
- `didact rolls` elenca i tiri recenti.
- `didact undo --event r12 --reason "…"` segna un tiro come annullato. Resta nel registro, e i numeri dei tiri non tornano mai indietro.
- `didact replay` rifà ogni tiro registrato e controlla che ognuno si riproduca esattamente. Ogni tiro attinge al proprio flusso con seme, quindi un tiro non ne sposta mai un altro.
- `didact odds '2d6 >= 8'` dà le probabilità esatte (tramite icepool), o una simulazione quando il calcolo esatto non è disponibile.
- `--seed <text>` attinge a un flusso fisso: lo stesso seme dà gli stessi dadi.

## Note sui dialetti

- `r` ritira ancora e ancora (Roll20). La `r` di Foundry ritira una volta, cosa che Didact scrive `ro`.
- `cs` e `cf` segnano solo i critici, come in Roll20. In Foundry contano i successi; qui si usa una condizione (`>=19`).
- `d` subito dopo i dadi significa scartare il più basso: `4d6d1` equivale a `4d6dl1`.
- `!=` non è ammesso. Scrivi `!6` per esplodere sul 6, o `<>` per "diverso da".
