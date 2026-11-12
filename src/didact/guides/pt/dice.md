<!-- translated from a81883b64f94 -->
# Dados

Lança todos os dados através do Didact, e nunca inventes um resultado. Cada lançamento recebe um id (`#r12`), fica no registo e pode ser repetido.

```
didact roll 4d6kh3                          #r12 4d6kh3 → [6 5 3 (2)] = 14
didact roll 'd20 <= @STR' --as freya        #r13 1d20 <= @STR → [7] <= @STR(12) = true
didact roll '6d10>=8f1'                     #r14 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
didact roll '{d8, d6}kh1' --reason "Freya attacks with two daggers"
```

**Põe a expressão entre aspas**, de preferência simples: `>`, `<`, `!`, `(`, `{`, `#` e os espaços têm todos um significado para a shell. Sem aspas, `6d10>=8f1` lança `6d10` e escreve um ficheiro chamado `=8f1`.

## Ler um resultado

`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — reason`

| Marca | Significado |
|---|---|
| `(2)` | descartado |
| `6!` | explodiu: por causa dele juntou-se o dado seguinte |
| `1→4` | relançado ou limitado de 1 para 4 |
| `6+6+2` | um dado cumulativo: os seus lançamentos somados |
| `6-1` | um dado penetrante: conta um a menos |
| `9✓` / `1✗` | um sucesso / uma falha |
| `purr:3` | um dado juntado por um efeito de um pacote |
| `@STR(12)` | uma variável e o seu valor |
| `([1 2])[8 8 8]` | os dados lançados para a quantidade, e depois a reserva |
| `(doubles, max)` | indicadores para as regras: `doubles`, `all-same`, `max`, `min`, `exploded`, `rerolled`, `crit`, `fumble`, `capped` |

O Didact devolve a forma canónica que leu (`4d6k3` → `4d6kh3`), para que uma leitura diferente nunca passe despercebida.

## Notação

| O quê | Escreve | Exemplo |
|---|---|---|
| Dados | `NdX`, `d%` (d100), `dF` (Fate), `d66` (dezenas e unidades) | `3d6`, `4dF` |
| Dados personalizados e de pacotes | `d{faces}`, `d[name]` | `d{0,0,1,1,2,3}`, `2d[boost]` |
| Manter, descartar | `khN` (ou `kN`), `klN`, `dlN` (ou `dN`), `dhN` | `4d6kh3`, `2d20kl1` |
| Explodir | `!` na face máxima, ou uma condição; `!!` acumula, `!p` penetra, `!o` explode uma vez | `d6!`, `5d10!>=9` |
| Relançar | `r` até falhar a condição (por omissão: a face mínima), `ro` uma vez | `2d6r1`, `d20ro<3` |
| Únicos | `u` relança os repetidos, `uo` uma vez | `4d6u` |
| Limitar | `minN`, `maxN` | `4d6min2` |
| Sucessos, falhas | uma condição logo a seguir aos dados; `f` para as falhas | `6d10>=8f1`, `12d6>=5` |
| Pares, ímpares | conta os dados pares ou ímpares | `4d6even` |
| Críticos | `cs`, `cf` (+ condição) marcam críticos; o total não muda | `d20cs>=19` |
| Conjuntos | `mt` conta conjuntos de iguais (`mt3`: conjuntos de 3 ou mais) | `10d10mt` |
| Margem | `ms`: total − N; com `<=`/`<`: N − total | `d20ms15`, `d20ms<=@DEX` |
| Ordenar | `sa` (ou `s`), `sd` | `5d6sd` |
| Grupos | `{a, b}` + manter/descartar/sucessos | `{d8, d6}kh1` |
| Aritmética | `+ - * / // %`, parênteses | `(1d6+2)*2`, `3d6*10` |
| Comparações | `== <> < <= > >=`, com espaços | `2d6 >= 8` |
| Variáveis | `@name`, `@record.field`, `@{npc:tom.hp}` | `d20 <= @STR`, `(@level)d6` |
| Quantidades lançadas | `(expr)dX` | `(2d4)d8` |
| Funções | `min max abs floor ceil round`; `if(c, a, b)`; `default(@x, 0)` | `max(d6, d8)` |
| Degraus de dado | `step(die, n)`; `step.extended(…)` percorre a cadeia mais longa d3–d30 | `step(d6, 1)` → um d8 |
| Etiquetas, rótulos | `tag:expr` dá nome a uma parte; `expr[label]` rotula-a | `hope:1d12 + fear:1d12`, `d8[fire]` |
| Repetir | `N#expr` lança N vezes em separado | `6#4d6dl1` |
| Macros de pacotes | `pack.name(args)` | `hack.attack(d8, d6)` |

**Os espaços contam:** `2d6>=8` conta os dados que mostram 8 ou mais (sempre 0 num d6), enquanto `2d6 >= 8` compara o total. O Didact avisa-te quando uma condição de sucesso é impossível.

**Ordem:** os modificadores aplicam-se sempre por esta ordem, seja qual for a ordem em que os escreves: min/max → explodir → relançar → únicos → manter → descartar → sucessos e falhas → críticos → conjuntos → margem → ordenar.

## Variáveis

- `--as <record>` disponibiliza os campos numéricos da ficha: `@hp`, `@STR`, `@stats.str` e `@<field>` do seu bloco de mecânicas.
- `--var DEX=12` define uma variável, e pode repetir-se.
- `@sweeney.hp` lê um campo de outra ficha; usa `@{npc:tom.hp}` para ids.
- Uma quantidade de dados calculada a partir de variáveis aparece como lançada: `(@level)d6` com nível 2 fica registado como `2d6 → [3 4] = 7`, e o JSON do lançamento guarda a expressão e as variáveis. Uma quantidade lançada mostra os seus próprios dados: `(2d4)d8 → ([1 4])[4 4 2 1 7]`.

## Dados físicos, anular, repetir, probabilidades

- `--got 6,3,4` regista as faces de dados reais, pela ordem em que saíram. Explosões e relançamentos usam a face seguinte.
- `didact report 'the tower falls' --of 'the tower'` regista um resultado que não foi lançado aqui: uma carta tirada, uma torre de blocos, uma moeda. Recebe um número de lançamento e entra no registo de lançamentos, e durante uma sessão é também um acontecimento de resultado. `replay` ignora-o.
- `didact rolls` lista os lançamentos recentes.
- `didact undo --event r12 --reason "…"` marca um lançamento como anulado. Continua no registo, e os números dos lançamentos nunca andam para trás.
- `didact replay` volta a executar todos os lançamentos registados e verifica que cada um se reproduz exatamente. Cada lançamento tira de uma sequência própria com semente, por isso um lançamento nunca altera outro.
- `didact odds '2d6 >= 8'` dá as probabilidades exatas (com o icepool), ou uma simulação quando o cálculo exato não é possível.
- `--seed <text>` tira de uma sequência fixa: a mesma semente dá os mesmos dados.

## Notas sobre dialetos

- `r` relança uma e outra vez (Roll20). O `r` do Foundry relança uma vez, o que no Didact se escreve `ro`.
- `cs` e `cf` só marcam críticos, como no Roll20. No Foundry contam sucessos; aqui isso é uma condição (`>=19`).
- `d` logo a seguir aos dados quer dizer descartar os mais baixos: `4d6d1` é `4d6dl1`.
- `!=` não é permitido. Escreve `!6` para explodir no 6, ou `<>` para «diferente».
