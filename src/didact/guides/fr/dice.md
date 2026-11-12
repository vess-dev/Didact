<!-- translated from a81883b64f94 -->
# Dés

Lancez chaque dé via Didact, et n'inventez jamais un résultat. Chaque jet reçoit un identifiant (`#r12`), est inscrit au journal et peut être rejoué.

```
didact roll 4d6kh3                          #r12 4d6kh3 → [6 5 3 (2)] = 14
didact roll 'd20 <= @STR' --as freya        #r13 1d20 <= @STR → [7] <= @STR(12) = true
didact roll '6d10>=8f1'                     #r14 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
didact roll '{d8, d6}kh1' --reason "Freya attacks with two daggers"
```

**Mettez l'expression entre guillemets**, de préférence simples : `>`, `<`, `!`, `(`, `{`, `#` et les espaces ont tous un sens pour le shell. Sans guillemets, `6d10>=8f1` lance `6d10` et écrit un fichier nommé `=8f1`.

## Lire un résultat

`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — reason`

| Marque | Signification |
|---|---|
| `(2)` | écarté |
| `6!` | explosé : le dé suivant a été ajouté à cause de lui |
| `1→4` | relancé ou borné de 1 à 4 |
| `6+6+2` | un dé cumulatif : ses jets additionnés |
| `6-1` | un dé pénétrant : il compte un de moins |
| `9✓` / `1✗` | une réussite / un échec |
| `purr:3` | un dé ajouté par un effet de pack |
| `@STR(12)` | une variable et sa valeur |
| `([1 2])[8 8 8]` | les dés lancés pour le nombre, puis la réserve |
| `(doubles, max)` | des indicateurs pour les règles : `doubles`, `all-same`, `max`, `min`, `exploded`, `rerolled`, `crit`, `fumble`, `capped` |

Didact renvoie la forme canonique qu'il a lue (`4d6k3` → `4d6kh3`), pour qu'une lecture différente ne passe jamais inaperçue.

## Notation

| Quoi | Écriture | Exemple |
|---|---|---|
| Dés | `NdX`, `d%` (d100), `dF` (Fate), `d66` (dizaines et unités) | `3d6`, `4dF` |
| Dés personnalisés et de pack | `d{faces}`, `d[name]` | `d{0,0,1,1,2,3}`, `2d[boost]` |
| Garder, écarter | `khN` (ou `kN`), `klN`, `dlN` (ou `dN`), `dhN` | `4d6kh3`, `2d20kl1` |
| Explosion | `!` sur la face maximale, ou une condition ; `!!` cumule, `!p` pénètre, `!o` explose une fois | `d6!`, `5d10!>=9` |
| Relance | `r` jusqu'à ne plus remplir la condition (par défaut : la plus petite face), `ro` une fois | `2d6r1`, `d20ro<3` |
| Uniques | `u` relance les doublons, `uo` une fois | `4d6u` |
| Bornes | `minN`, `maxN` | `4d6min2` |
| Réussites, échecs | une condition juste après les dés ; `f` pour les échecs | `6d10>=8f1`, `12d6>=5` |
| Pair, impair | compte les dés pairs ou impairs | `4d6even` |
| Critiques | `cs`, `cf` (+ condition) marquent les critiques ; le total ne change pas | `d20cs>=19` |
| Séries | `mt` compte les séries de dés identiques (`mt3` : séries de 3 ou plus) | `10d10mt` |
| Marge | `ms` : total − N ; avec `<=`/`<` : N − total | `d20ms15`, `d20ms<=@DEX` |
| Tri | `sa` (ou `s`), `sd` | `5d6sd` |
| Groupes | `{a, b}` + garder/écarter/réussites | `{d8, d6}kh1` |
| Calcul | `+ - * / // %`, parenthèses | `(1d6+2)*2`, `3d6*10` |
| Comparaisons | `== <> < <= > >=`, avec des espaces | `2d6 >= 8` |
| Variables | `@name`, `@record.field`, `@{npc:tom.hp}` | `d20 <= @STR`, `(@level)d6` |
| Nombre de dés tiré | `(expr)dX` | `(2d4)d8` |
| Fonctions | `min max abs floor ceil round` ; `if(c, a, b)` ; `default(@x, 0)` | `max(d6, d8)` |
| Échelons de dés | `step(die, n)` ; `step.extended(…)` parcourt la chaîne plus longue d3–d30 | `step(d6, 1)` → un d8 |
| Étiquettes | `tag:expr` nomme une partie ; `expr[label]` l'étiquette | `hope:1d12 + fear:1d12`, `d8[fire]` |
| Répétition | `N#expr` lance N fois séparément | `6#4d6dl1` |
| Macros de pack | `pack.name(args)` | `hack.attack(d8, d6)` |

**Les espaces comptent :** `2d6>=8` compte les dés qui font 8 ou plus (toujours 0 sur un d6), alors que `2d6 >= 8` compare le total. Didact vous prévient quand une condition de réussite est impossible.

**Ordre :** les modificateurs s'appliquent toujours dans cet ordre, quelle que soit leur écriture : min/max → explosion → relance → uniques → garder → écarter → réussites et échecs → critiques → séries → marge → tri.

## Variables

- `--as <record>` rend disponibles les champs numériques de la fiche : `@hp`, `@STR`, `@stats.str`, et `@<field>` depuis son bloc de mécaniques.
- `--var DEX=12` définit une variable, et peut être répété.
- `@sweeney.hp` lit le champ d'une autre fiche ; utilisez `@{npc:tom.hp}` pour les identifiants.
- Un nombre de dés calculé à partir de variables s'affiche comme lancé : `(@level)d6` avec un niveau 2 est journalisé comme `2d6 → [3 4] = 7`, et le JSON du jet garde l'expression et les variables. Un nombre tiré aux dés montre ses propres dés : `(2d4)d8 → ([1 4])[4 4 2 1 7]`.

## Dés physiques, annulation, rejeu, probabilités

- `--got 6,3,4` enregistre les faces de vrais dés, dans l'ordre où ils ont été lancés. Explosions et relances prennent la face suivante.
- `didact report 'the tower falls' --of 'the tower'` enregistre un résultat qui n'a pas été tiré ici : une carte tirée, une tour de blocs, une pièce. Il reçoit un numéro de jet et va dans le journal des jets, et pendant une séance c'est aussi un événement de résultat. `replay` le saute.
- `didact rolls` liste les jets récents.
- `didact undo --event r12 --reason "…"` marque un jet comme annulé. Il reste dans le journal, et les numéros de jet ne reviennent jamais en arrière.
- `didact replay` relance chaque jet journalisé et vérifie que chacun se reproduit à l'identique. Chaque jet tire de son propre flux à graine, donc un jet n'en décale jamais un autre.
- `didact odds '2d6 >= 8'` donne les probabilités exactes (via icepool), ou une simulation quand le calcul exact n'est pas possible.
- `--seed <text>` tire d'un flux fixe : la même graine donne les mêmes dés.

## Notes sur les dialectes

- `r` relance encore et encore (Roll20). Le `r` de Foundry relance une fois, ce que Didact écrit `ro`.
- `cs` et `cf` ne font que marquer les critiques, comme dans Roll20. Dans Foundry, ils comptent des réussites ; ici, c'est une condition (`>=19`).
- `d` juste après les dés signifie écarter le plus bas : `4d6d1` équivaut à `4d6dl1`.
- `!=` n'est pas autorisé. Écrivez `!6` pour exploser sur 6, ou `<>` pour « différent de ».
