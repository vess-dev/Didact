<!-- translated from a81883b64f94 -->
# Dados

Tira todos los dados con Didact y nunca te inventes un resultado. Cada tirada recibe un id (`#r12`), queda en el registro y se puede reproducir.

```
didact roll 4d6kh3                          #r12 4d6kh3 → [6 5 3 (2)] = 14
didact roll 'd20 <= @STR' --as freya        #r13 1d20 <= @STR → [7] <= @STR(12) = true
didact roll '6d10>=8f1'                     #r14 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
didact roll '{d8, d6}kh1' --reason "Freya attacks with two daggers"
```

**Pon la expresión entre comillas**, mejor simples: `>`, `<`, `!`, `(`, `{`, `#` y los espacios significan algo para la shell. Sin comillas, `6d10>=8f1` tira `6d10` y escribe un archivo llamado `=8f1`.

## Cómo leer un resultado

`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — reason`

| Marca | Significado |
|---|---|
| `(2)` | descartado |
| `6!` | explotó: por él se añadió el dado siguiente |
| `1→4` | vuelto a tirar o acotado de 1 a 4 |
| `6+6+2` | un dado acumulativo: sus tiradas sumadas |
| `6-1` | un dado penetrante: cuenta uno menos |
| `9✓` / `1✗` | un éxito / un fallo |
| `purr:3` | un dado añadido por un efecto de un paquete |
| `@STR(12)` | una variable y su valor |
| `([1 2])[8 8 8]` | los dados tirados para la cantidad, y luego la reserva |
| `(doubles, max)` | indicadores para las reglas: `doubles`, `all-same`, `max`, `min`, `exploded`, `rerolled`, `crit`, `fumble`, `capped` |

Didact repite la forma canónica que ha leído (`4d6k3` → `4d6kh3`), así que una lectura distinta nunca pasa desapercibida.

## Notación

| Qué | Se escribe | Ejemplo |
|---|---|---|
| Dados | `NdX`, `d%` (d100), `dF` (Fate), `d66` (decenas y unidades) | `3d6`, `4dF` |
| Dados personalizados y de paquete | `d{faces}`, `d[name]` | `d{0,0,1,1,2,3}`, `2d[boost]` |
| Quedarse, descartar | `khN` (o `kN`), `klN`, `dlN` (o `dN`), `dhN` | `4d6kh3`, `2d20kl1` |
| Explotar | `!` en la cara máxima, o una condición; `!!` acumula, `!p` penetra, `!o` explota una vez | `d6!`, `5d10!>=9` |
| Volver a tirar | `r` hasta que no cumpla la condición (por defecto: la cara mínima), `ro` una vez | `2d6r1`, `d20ro<3` |
| Únicos | `u` vuelve a tirar los duplicados, `uo` una vez | `4d6u` |
| Acotar | `minN`, `maxN` | `4d6min2` |
| Éxitos, fallos | una condición justo después de los dados; `f` para los fallos | `6d10>=8f1`, `12d6>=5` |
| Pares, impares | cuenta los dados pares o impares | `4d6even` |
| Críticos | `cs`, `cf` (+ condición) marcan críticos; el total no cambia | `d20cs>=19` |
| Juegos | `mt` cuenta juegos de coincidencias (`mt3`: juegos de 3 o más) | `10d10mt` |
| Margen | `ms`: total − N; con `<=`/`<`: N − total | `d20ms15`, `d20ms<=@DEX` |
| Ordenar | `sa` (o `s`), `sd` | `5d6sd` |
| Grupos | `{a, b}` + quedarse/descartar/éxitos | `{d8, d6}kh1` |
| Operaciones | `+ - * / // %`, paréntesis | `(1d6+2)*2`, `3d6*10` |
| Comparaciones | `== <> < <= > >=`, con espacios | `2d6 >= 8` |
| Variables | `@name`, `@record.field`, `@{npc:tom.hp}` | `d20 <= @STR`, `(@level)d6` |
| Cantidades tiradas | `(expr)dX` | `(2d4)d8` |
| Funciones | `min max abs floor ceil round`; `if(c, a, b)`; `default(@x, 0)` | `max(d6, d8)` |
| Pasos de dado | `step(die, n)`; `step.extended(…)` recorre la cadena más larga de d3 a d30 | `step(d6, 1)` → un d8 |
| Etiquetas | `tag:expr` da nombre a una parte; `expr[label]` le pone una etiqueta | `hope:1d12 + fear:1d12`, `d8[fire]` |
| Repetir | `N#expr` tira N veces por separado | `6#4d6dl1` |
| Macros de paquete | `pack.name(args)` | `hack.attack(d8, d6)` |

**Los espacios importan:** `2d6>=8` cuenta los dados que sacan 8 o más (siempre 0 en un d6), mientras que `2d6 >= 8` compara el total. Didact te avisa cuando una condición de éxito no se puede cumplir.

**Orden:** los modificadores se aplican siempre en este orden, se escriban como se escriban: min/max → explotar → volver a tirar → únicos → quedarse → descartar → éxitos y fallos → críticos → juegos → margen → ordenar.

## Variables

- `--as <record>` pone a tu disposición los campos numéricos de la ficha: `@hp`, `@STR`, `@stats.str`, y `@<field>` de su bloque de mecánicas.
- `--var DEX=12` fija una variable, y se puede repetir.
- `@sweeney.hp` lee un campo de otra ficha; usa `@{npc:tom.hp}` para los ids.
- Una cantidad de dados calculada a partir de variables se muestra como tirada: `(@level)d6` con nivel 2 queda registrado como `2d6 → [3 4] = 7`, y el JSON de la tirada conserva la expresión y las variables. Una cantidad tirada muestra sus propios dados: `(2d4)d8 → ([1 4])[4 4 2 1 7]`.

## Dados físicos, deshacer, reproducir, probabilidades

- `--got 6,3,4` registra las caras de dados reales, en el orden en que se tiraron. Las explosiones y las repeticiones toman la cara siguiente.
- `didact report 'the tower falls' --of 'the tower'` registra un resultado que no se tiró aquí: una carta sacada, una torre de bloques, una moneda. Recibe un número de tirada y va al registro de tiradas, y durante una sesión también es un evento de resultado. `replay` lo omite.
- `didact rolls` muestra las tiradas recientes.
- `didact undo --event r12 --reason "…"` marca una tirada como deshecha. Sigue en el registro, y los números de tirada nunca retroceden.
- `didact replay` vuelve a ejecutar cada tirada registrada y comprueba que se reproduce exactamente. Cada tirada sale de su propio flujo con semilla, así que una tirada nunca altera otra.
- `didact odds '2d6 >= 8'` da las probabilidades exactas (con icepool), o una simulación cuando no se pueden calcular con exactitud.
- `--seed <text>` saca de un flujo fijo: la misma semilla da los mismos dados.

## Notas sobre dialectos

- `r` vuelve a tirar una y otra vez (Roll20). La `r` de Foundry vuelve a tirar una sola vez, y Didact lo escribe `ro`.
- `cs` y `cf` solo marcan críticos, como en Roll20. En Foundry cuentan éxitos; aquí eso es una condición (`>=19`).
- `d` justo después de los dados significa descartar el más bajo: `4d6d1` es `4d6dl1`.
- `!=` no está permitido. Escribe `!6` para explotar con un 6, o `<>` para "distinto de".
