# Dice

Roll every die through Didact, and never invent a result. Each roll gets an id (`#r12`), goes into the log, and can be replayed.

```
didact roll 4d6kh3                          #r12 4d6kh3 → [6 5 3 (2)] = 14
didact roll 'd20 <= @STR' --as freya        #r13 1d20 <= @STR → [7] <= @STR(12) = true
didact roll '6d10>=8f1'                     #r14 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
didact roll '{d8, d6}kh1' --reason "Freya attacks with two daggers"
```

**Quote the expression**, and prefer single quotes: `>`, `<`, `!`, `(`, `{`, `#` and spaces all mean something to the shell. Unquoted, `6d10>=8f1` rolls `6d10` and writes a file named `=8f1`.

## Reading a result

`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — reason`

| Mark | Meaning |
|---|---|
| `(2)` | dropped |
| `6!` | exploded: the next die was added because of it |
| `1→4` | rerolled or clamped from 1 to 4 |
| `6+6+2` | a compounding die: its rolls added together |
| `6-1` | a penetrating die: it counts one less |
| `9✓` / `1✗` | a success / a failure |
| `purr:3` | a die added by a pack effect |
| `@STR(12)` | a variable and its value |
| `([1 2])[8 8 8]` | the dice rolled for the count, then the pool |
| `(doubles, max)` | flags for rules: `doubles`, `all-same`, `max`, `min`, `exploded`, `rerolled`, `crit`, `fumble`, `capped` |

Didact echoes the canonical form it read (`4d6k3` → `4d6kh3`), so a different reading never goes unnoticed.

## Notation

| What | Write | Example |
|---|---|---|
| Dice | `NdX`, `d%` (d100), `dF` (Fate), `d66` (tens and ones) | `3d6`, `4dF` |
| Custom and pack dice | `d{faces}`, `d[name]` | `d{0,0,1,1,2,3}`, `2d[boost]` |
| Keep, drop | `khN` (or `kN`), `klN`, `dlN` (or `dN`), `dhN` | `4d6kh3`, `2d20kl1` |
| Explode | `!` on the top face, or a condition; `!!` compounds, `!p` penetrates, `!o` explodes once | `d6!`, `5d10!>=9` |
| Reroll | `r` until it misses the condition (default: the lowest face), `ro` once | `2d6r1`, `d20ro<3` |
| Unique | `u` rerolls duplicates, `uo` once | `4d6u` |
| Clamp | `minN`, `maxN` | `4d6min2` |
| Successes, failures | a condition right after the dice; `f` for failures | `6d10>=8f1`, `12d6>=5` |
| Even, odd | count even or odd dice | `4d6even` |
| Crits | `cs`, `cf` (+ condition) mark crits; the total doesn't change | `d20cs>=19` |
| Sets | `mt` counts sets of matches (`mt3`: sets of 3+) | `10d10mt` |
| Margin | `ms`: total − N; with `<=`/`<`: N − total | `d20ms15`, `d20ms<=@DEX` |
| Sort | `sa` (or `s`), `sd` | `5d6sd` |
| Groups | `{a, b}` + keep/drop/successes | `{d8, d6}kh1` |
| Math | `+ - * / // %`, parentheses | `(1d6+2)*2`, `3d6*10` |
| Comparisons | `== <> < <= > >=`, with spaces | `2d6 >= 8` |
| Variables | `@name`, `@record.field`, `@{npc:tom.hp}` | `d20 <= @STR`, `(@level)d6` |
| Rolled counts | `(expr)dX` | `(2d4)d8` |
| Functions | `min max abs floor ceil round`; `if(c, a, b)`; `default(@x, 0)` | `max(d6, d8)` |
| Dice steps | `step(die, n)`; `step.extended(…)` walks the longer d3–d30 chain | `step(d6, 1)` → a d8 |
| Tags, labels | `tag:expr` names a part; `expr[label]` labels it | `hope:1d12 + fear:1d12`, `d8[fire]` |
| Repeat | `N#expr` rolls N separate times | `6#4d6dl1` |
| Pack macros | `pack.name(args)` | `hack.attack(d8, d6)` |

**Spaces matter:** `2d6>=8` counts dice that show 8 or more (always 0 on a d6), while `2d6 >= 8` compares the total. Didact warns you when a success condition can't be met.

**Order:** modifiers always apply in this order, however they are written: min/max → explode → reroll → unique → keep → drop → successes and failures → crits → sets → margin → sort.

## Variables

- `--as <record>` makes the record's numeric fields available: `@hp`, `@STR`, `@stats.str`, and `@<field>` from its mechanics block.
- `--var DEX=12` sets one variable, and can be repeated.
- `@sweeney.hp` reads another record's field; use `@{npc:tom.hp}` for ids.
- A dice count worked out from variables shows as rolled: `(@level)d6` with level 2 logs as `2d6 → [3 4] = 7`, and the roll's JSON keeps the expression and the variables. A rolled count shows its own dice: `(2d4)d8 → ([1 4])[4 4 2 1 7]`.

## Physical dice, undo, replay, odds

- `--got 6,3,4` records the faces of real dice, in the order they were rolled. Explosions and rerolls take the next face.
- `didact report 'the tower falls' --of 'the tower'` records an outcome that wasn't rolled here: a card drawn, a block tower, a coin. It gets a roll number and goes in the roll log, and during a session it's a result beat too. `replay` passes over it.
- `didact rolls` lists recent rolls.
- `didact undo --event r12 --reason "…"` marks a roll undone. It stays in the log, and roll numbers never rewind.
- `didact replay` re-runs every logged roll and checks that each one reproduces exactly. Each roll draws from its own seeded stream, so one roll never shifts another.
- `didact odds '2d6 >= 8'` gives exact probabilities (via icepool), or a simulation when exact math isn't available.
- `--seed <text>` draws from a fixed stream: the same seed gives the same dice.

## Dialect notes

- `r` rerolls again and again (Roll20). Foundry's `r` rerolls once, which Didact writes as `ro`.
- `cs` and `cf` only mark crits, as in Roll20. In Foundry they count successes; here that's a condition (`>=19`).
- `d` right after the dice means drop lowest: `4d6d1` is `4d6dl1`.
- `!=` isn't allowed. Write `!6` to explode on 6, or `<>` for "not equal".
