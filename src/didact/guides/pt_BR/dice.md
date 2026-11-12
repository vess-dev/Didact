<!-- translated from a81883b64f94 -->
# Dados

Role todos os dados pelo Didact, e nunca invente um resultado. Cada rolagem recebe um id (`#r12`), vai para o registro e pode ser reproduzida.

```
didact roll 4d6kh3                          #r12 4d6kh3 → [6 5 3 (2)] = 14
didact roll 'd20 <= @STR' --as freya        #r13 1d20 <= @STR → [7] <= @STR(12) = true
didact roll '6d10>=8f1'                     #r14 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
didact roll '{d8, d6}kh1' --reason "Freya attacks with two daggers"
```

**Coloque a expressão entre aspas**, de preferência simples: `>`, `<`, `!`, `(`, `{`, `#` e os espaços têm significado para o shell. Sem aspas, `6d10>=8f1` rola `6d10` e grava um arquivo chamado `=8f1`.

## Lendo um resultado

`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — reason`

| Marca | Significado |
|---|---|
| `(2)` | descartado |
| `6!` | explodiu: o dado seguinte foi somado por causa dele |
| `1→4` | rolado de novo ou limitado de 1 para 4 |
| `6+6+2` | um dado cumulativo: suas rolagens somadas |
| `6-1` | um dado penetrante: vale um a menos |
| `9✓` / `1✗` | um sucesso / uma falha |
| `purr:3` | um dado adicionado por um efeito de pacote |
| `@STR(12)` | uma variável e seu valor |
| `([1 2])[8 8 8]` | os dados rolados para a quantidade, depois a parada |
| `(doubles, max)` | marcadores para as regras: `doubles`, `all-same`, `max`, `min`, `exploded`, `rerolled`, `crit`, `fumble`, `capped` |

O Didact repete a forma canônica que leu (`4d6k3` → `4d6kh3`), para que uma leitura diferente nunca passe despercebida.

## Notação

| O quê | Escreva | Exemplo |
|---|---|---|
| Dados | `NdX`, `d%` (d100), `dF` (Fate), `d66` (dezenas e unidades) | `3d6`, `4dF` |
| Dados personalizados e de pacotes | `d{faces}`, `d[name]` | `d{0,0,1,1,2,3}`, `2d[boost]` |
| Manter, descartar | `khN` (ou `kN`), `klN`, `dlN` (ou `dN`), `dhN` | `4d6kh3`, `2d20kl1` |
| Explodir | `!` na face máxima, ou uma condição; `!!` acumula, `!p` penetra, `!o` explode uma vez | `d6!`, `5d10!>=9` |
| Rolar de novo | `r` até não cumprir a condição (padrão: a face mínima), `ro` uma vez | `2d6r1`, `d20ro<3` |
| Únicos | `u` rola de novo os repetidos, `uo` uma vez | `4d6u` |
| Limitar | `minN`, `maxN` | `4d6min2` |
| Sucessos, falhas | uma condição logo depois dos dados; `f` para falhas | `6d10>=8f1`, `12d6>=5` |
| Pares, ímpares | conta os dados pares ou ímpares | `4d6even` |
| Críticos | `cs`, `cf` (+ condição) marcam críticos; o total não muda | `d20cs>=19` |
| Conjuntos | `mt` conta conjuntos de iguais (`mt3`: conjuntos de 3 ou mais) | `10d10mt` |
| Margem | `ms`: total − N; com `<=`/`<`: N − total | `d20ms15`, `d20ms<=@DEX` |
| Ordenar | `sa` (ou `s`), `sd` | `5d6sd` |
| Grupos | `{a, b}` + manter/descartar/sucessos | `{d8, d6}kh1` |
| Matemática | `+ - * / // %`, parênteses | `(1d6+2)*2`, `3d6*10` |
| Comparações | `== <> < <= > >=`, com espaços | `2d6 >= 8` |
| Variáveis | `@name`, `@record.field`, `@{npc:tom.hp}` | `d20 <= @STR`, `(@level)d6` |
| Quantidades roladas | `(expr)dX` | `(2d4)d8` |
| Funções | `min max abs floor ceil round`; `if(c, a, b)`; `default(@x, 0)` | `max(d6, d8)` |
| Passos de dado | `step(die, n)`; `step.extended(…)` percorre a cadeia mais longa d3–d30 | `step(d6, 1)` → um d8 |
| Tags, rótulos | `tag:expr` dá nome a uma parte; `expr[label]` a rotula | `hope:1d12 + fear:1d12`, `d8[fire]` |
| Repetir | `N#expr` rola N vezes separadas | `6#4d6dl1` |
| Macros de pacotes | `pack.name(args)` | `hack.attack(d8, d6)` |

**Os espaços importam:** `2d6>=8` conta os dados que mostram 8 ou mais (sempre 0 em um d6), enquanto `2d6 >= 8` compara o total. O Didact avisa quando uma condição de sucesso é impossível.

**Ordem:** os modificadores sempre se aplicam nesta ordem, não importa como sejam escritos: min/max → explodir → rolar de novo → únicos → manter → descartar → sucessos e falhas → críticos → conjuntos → margem → ordenar.

## Variáveis

- `--as <record>` disponibiliza os campos numéricos da ficha: `@hp`, `@STR`, `@stats.str` e `@<field>` do bloco de mecânicas dela.
- `--var DEX=12` define uma variável, e pode ser repetido.
- `@sweeney.hp` lê um campo de outra ficha; use `@{npc:tom.hp}` para ids.
- Uma quantidade de dados calculada a partir de variáveis aparece como rolada: `(@level)d6` com nível 2 é registrado como `2d6 → [3 4] = 7`, e o JSON da rolagem guarda a expressão e as variáveis. Uma quantidade rolada mostra os próprios dados: `(2d4)d8 → ([1 4])[4 4 2 1 7]`.

## Dados físicos, desfazer, reproduzir, probabilidades

- `--got 6,3,4` registra as faces de dados reais, na ordem em que foram rolados. Explosões e novas rolagens usam a face seguinte.
- `didact report 'the tower falls' --of 'the tower'` registra um resultado que não foi rolado aqui: uma carta tirada, uma torre de blocos, uma moeda. Ele recebe um número de rolagem e entra no registro de rolagens, e durante uma sessão também é um acontecimento de resultado. `replay` o ignora.
- `didact rolls` lista as rolagens recentes.
- `didact undo --event r12 --reason "…"` marca uma rolagem como desfeita. Ela continua no registro, e os números das rolagens nunca voltam atrás.
- `didact replay` refaz todas as rolagens registradas e confere se cada uma se reproduz exatamente. Cada rolagem tira de uma sequência própria com semente, então uma rolagem nunca altera outra.
- `didact odds '2d6 >= 8'` dá as probabilidades exatas (via icepool), ou uma simulação quando o cálculo exato não é possível.
- `--seed <text>` tira de uma sequência fixa: a mesma semente dá os mesmos dados.

## Notas sobre dialetos

- `r` rola de novo repetidamente (Roll20). O `r` do Foundry rola de novo uma vez, o que o Didact escreve como `ro`.
- `cs` e `cf` só marcam críticos, como no Roll20. No Foundry eles contam sucessos; aqui isso é uma condição (`>=19`).
- `d` logo depois dos dados significa descartar os menores: `4d6d1` é `4d6dl1`.
- `!=` não é permitido. Escreva `!6` para explodir no 6, ou `<>` para “diferente”.
