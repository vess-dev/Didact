<!-- translated from b1dfa1159ff4 -->
# Pacotes

Um pacote é um sistema de jogo, um oráculo, um cenário, uma aventura ou um suplemento, escrito como arquivos YAML mais um plugin Python opcional. Este guia mostra como escrever um: transformar um livro de regras em um pacote, ou adicionar conteúdo caseiro.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Um pacote também pode ser feito a partir do que está na sua biblioteca. `didact pack new my-brew --from-overlay my-system` transforma seu conteúdo caseiro para um sistema (`compendium add`, fichas mantidas com `--scope system`, lore) em um suplemento, e `didact world export --as setting` transforma um mundo em um pacote de cenário: suas pessoas, lugares e lore como entradas do compêndio e lore do pacote, trazidos para outro mundo com `compendium import`. Os dois deixam de fora os segredos e as notas do Mestre, a menos que `--secrets`, e nenhum é marcado como compartilhável até você definir a licença.

## Estrutura

```
my-hack/
  pack.yaml        id, name, kind, version, requires, extends, license, plugins, settings
  GUIDE.md         how to run it: an LLM reads this first
  dice.yaml        named dice, macros, dice chains
  schemas/         record types and their fields (sheets)
  tables/          random and lookup tables, decks, bags
  rules/           checks, actions, procedures, triggers
  compendium/      monsters, items, spells, backgrounds…
  reference/       the rules text, one short section per file (Markdown)
  glossary.yaml    terms and definitions
  tests/           examples `pack test` runs
  plugins/         Python, for what YAML can't express (off until trusted)
```

Um arquivo contém um item, uma lista de itens, ou vários itens separados por `---`. Todo item informa seu id com a chave do seu tipo: `table: weather`, `check: save`, `type: pc`, ou `id: troll` para entradas do compêndio. Refira-se aos itens como `pack.id` (`my-system.save`), ou só pelo id quando apenas um pacote ativado o tiver.

```yaml
# pack.yaml
id: my-hack
name: My Hack
kind: system                 # system | oracle | supplement | setting | adventure
version: 0.1.0
alias: hack                  # the name in expressions: hack.attack(d8, d8)
requires: {didact: ">=0.1", packs: [core]}
extends: []                  # for a hack: [my-system]; same-id items replace the base's
license: {spdx: CC-BY-SA-4.0, redistributable: true, attribution: "…"}
settings: {torch_uses: 3}    # rules read these as @settings.torch_uses
```

Um hack informa sua base em `extends` e contém apenas o que difere:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Seu item com o mesmo id substitui o da base, seja qual for o tipo (uma tabela, uma regra, uma entrada do compêndio, uma seção de referência, um termo do glossário). Suas `settings` se sobrepõem às da base, chave por chave: uma chave que o hack define substitui o valor da base por inteiro (suas tabelas `names` tomam o lugar das da base), e as regras da base também leem os valores do hack. `hides` descarta o que sobra e de que o hack não precisa: `*` corresponde a qualquer sequência de caracteres, decide o último padrão que corresponde a um id, e um que começa com `!` mantém o item. O que o hack substitui nunca é ocultado. Os tipos são `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` e `term`. `didact pack validate` avisa sobre um padrão que não corresponde a nada.

## Expressões

Todas as condições e fórmulas usam a linguagem de dados (`didact guide dice`), e mais:
- **Valores:** `@name` lê um valor: `@roll`, `@who.STR`, `@settings.x`. `$name` cola primeiro o texto de um parâmetro, então `@who.$attr` vira `@who.STR`. Leia um parâmetro de texto livre como `@name`, não entre aspas (`'$name'`): um apóstrofo no texto dele fecharia as aspas (`pack validate` avisa).
- **Lógica:** `and`, `or`, `not` e `in` (`'deprived' in @who.conditions`).
- **Literais:** texto (`'travel'`) e `true`/`false`.
- **Funções:** `if(cond, a, b)` só rola o ramo que seguir. `default(@thread.flashpoint, 0)` é o valor, ou o valor reserva quando ele não está definido. `sum`, `count` (`count(@roll.dice, 6)` conta os seis), `min`, `max`, `any` e `all` recebem listas.

## Folhas: `schemas/`

```yaml
type: character
fields:
  STR: {kind: stat, range: [0, 18], roll: 3d6, on_zero: {trigger: death}}
  hp: {kind: resource, min: 0, roll: d6}
  armor: {kind: derived, expr: "min(3, sum(@inventory.armor))"}
  inventory: {kind: slots, capacity: 10, sizes: {petty: 0, normal: 1, bulky: 2},
              when_full: {set: {hp: 0}}}
  fatigue: {kind: counter, min: 0, occupies: inventory}
guidance: "3 HP is an average monster, 6 a hardy one, 10+ a serious threat."
---
type: pc
extends: character
```

| Tipo | Contém | Opções |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | um valor simples | min, max; `values` para enum |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: `@hp` é o valor, `@hp.max` o limite | range; min; max ou max_field; die |
| `counter` | um número | min, max, thresholds, occupies (um campo slots) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | itens (`Rope` ou `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | o que o nome diz | `to` (para refs), `allowed` |
| `derived` | calculado, nunca armazenado | expr |

Todo campo também aceita `label`, `help`, `default`, `required` e `roll`: `new pc Hero --fill`, ou um valor `"roll"`, o rola pelo registro. Os tipos do pacote `core` guardam texto independente de sistema em `fields`. Os tipos de um sistema guardam os números dele em `mechanics.<system>`. `set hero hp-=2` encontra o campo, o limita e informa qualquer excesso. `+=` adiciona a uma lista: uma `list` (como `slots`) mantém também um valor adicionado de novo, `tags`, `conditions` e `refs` o guardam uma só vez, e `-=` tira todas as cópias.

**Hooks** dizem o que acontece quando um valor cruza uma linha. Eles disparam a cada mudança (`set`, `inv`, um passo `set` de uma regra), mas só quando a linha é cruzada: 3 → 0 dispara, 0 → 0 não. Edições com `--force` os ignoram.

| Hook | Dispara quando |
|---|---|
| `on_zero` | um número ou `{value}` chega a 0 |
| `on_full` (`when_full` em slots) | chega ao máximo, tamanho ou capacidade |
| `thresholds: {10: …, 20: …}` (counters) | passa de cada marca ao subir |

Uma ação é texto (uma nota para o LLM), `{set: {hp: 0}}` ou `{condition: paralyzed}` na mesma ficha, `{trigger: death}` (executa essa regra com `who` = a ficha), ou uma lista disso.

**O inventário** (`didact inv …`) funciona sobre o campo `slots` da folha:
- **Espaço:** os itens ocupam seu `size` × `count`, e os contadores que ocupam o campo (`occupies`) ocupam seu valor. Passar da `capacity` é recusado, a menos que se use `--force`.
- **Grupos:** `groups: {backpack: 6, body: 4}` dá a cada grupo seu próprio espaço, e também suas próprias colunas e totais: `@inventory.body.armor` é só o que está vestido ou na mão, `@inventory.body.free` o espaço que ainda resta nele.
- **Usos:** `uses: 3` diminui com `inv use`. `uses: d8` é um dado de uso: 1–2 o faz descer um passo. Um item esgotado some, a menos que tenha `recharge` ou `keep: true`. De vários itens com o mesmo nome, o nome indica o primeiro; para gastar um uso (`inv use`, o `use:` de uma regra, `set …uses-=1`), o primeiro que ainda tenha um.
- **Chaves próprias de um item:** `didact set freya inventory.sword.damage=d10` (e também o `set: who.inventory.$item.damage` de uma regra) muda uma delas, com o item indicado como no `inv`, por uma parte do nome ou pelo nome inteiro, com espaços e pontos (`'inventory.12.7mm pistol.damage=d10'`, entre aspas para o shell); `uses` e `charges` contam como um campo `uses` (`charges+=2` não passa do máximo), e o espaço é verificado como no `inv add`. Uma regra lê uma como `@{who.inventory.$item.damage}` (um dado de uso como o dado dele, os usos como a contagem deles); um item ou uma chave que não esteja lá é lido como ausente, então `default(…)` dá o valor reserva dele.
- **Compêndio:** entradas do tipo `item` (ou weapon, armor, relic, …, ou um tipo próprio do pacote que estende um deles com `extends`) emprestam seus detalhes a `inv add`, encontradas pelo id, pelo nome ou por um alias (se duas compartilham um: cite-a como `pack.id`); qualquer outro nome, `:` incluído, é o próprio nome do item.

## Tabelas: `tables/`

```yaml
table: weather
dice: d6                     # any expression: 2d6, d66, d100, d20 + @corruption
clamp: true                  # a total past the ends uses the first or last entry
entries:
  1-2: Clear
  3-4: {text: Rain, data: {travel: slow}}
  5: {text: Storm, then: [{table: lightning}]}
  6: {text: Two fronts, roll: 2}
refs: {noun: nouns}          # "{noun}" in a text rolls on table nouns; "{1d4}" rolls dice
source: "Core Rules p. 12"
```

Outros formatos:
- **Listas com peso:** `entries` como lista, com `weight:` em cada entrada.
- **Colunas:** `columns: [a, b]` rola cada coluna de uma linha separadamente. Uma entrada simples (não uma lista) preenche todas as colunas, então `columns: [first, second]` sobre uma lista de palavras significa “role duas vezes nesta lista”. `labels: false` deixa os nomes das colunas fora do resultado (“Abandon · Advantage”). `read: "It's a {first} {second} with {third} {fourth} inside."` lê as colunas como uma frase.
- **Consultas:** `lookup: hp_lost`, ou `[odds, chaos]` para uma tabela de dupla entrada.
- **Repetidos:** `duplicates: reroll | keep | make_it_worse` para “role duas vezes”.
- **Em duas etapas:** uma entrada que rola em outra tabela (`{table: lightning}` no lugar do texto, ou `then:` depois dele) traz junto os dados dessa rolagem: uma regra ou um rascunho em que ela sair lê os dois conjuntos, primeiro as chaves da própria entrada, depois as da primeira tabela rolada em seguida. Um `--prefill` pode citar uma entrada mais abaixo, em qualquer profundidade (`Ring of the Hunt`), com os dados de cada entrada no caminho: de duas com o mesmo nome vale a mais próxima (depois a primeira), uma que segue rola a partir dali, e uma parecida com alguma delas sem ser nenhuma é recusada, citando a mais próxima. Um rascunho guiado oferece o primeiro passo quando as entradas dele dizem o que são (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): escolher uma rola na tabela seguinte, como uma rolagem que cai nela.
- **Ler nos dois sentidos:** `both_ways: true` em uma tabela d66 acrescenta a outra leitura: 31 também dá 13, e quem lê escolhe.
- **O que uma entrada significa:** `about: "Knows: {skills}. Also known as: {aka}."` preenche os dados de cada entrada (uma lista é lida como `a, b`; `{text}` é a própria entrada) para dizer o que ela dá quando uma escolha a oferece; o `note:` próprio de uma entrada diz isso no lugar. Sem nenhum dos dois, uma entrada cujos dados têm um `id` que nomeia uma entrada do compêndio é descrita por essa entrada.
- **Baralhos e sacos:** `deck: tarot` com `cards` (ou `standard: true`); `bag: initiative` com `tokens`.

A validação confere se todo resultado que os dados podem dar cai em uma entrada.

## Regras: `rules/`

```yaml
check: save
params: {who: ref, attr: {enum: [STR, DEX, WIL]}}
prompt: State the risk before rolling.
before: [{table: chart, with: {odds: $odds}, as: cell}]   # optional: steps first (a `roll` step can replace `roll:`)
roll: d20                              # or several: {action: "d6 + @stat", challenge: 2d10}
success: "@roll <= @who.$attr"         # or bands: {strong: "@roll >= 10", weak: "@roll >= 7", miss: else}
auto: {1: success, 20: failure}        # natural rolls
flags: {crit: "count(@roll.dice, 6) >= 2"}
on: {failure: ["The risk comes true."]}
options:                               # the roll comes back pending: `didact resolve r12 push`
  push: {label: "Push", steps: [{reroll: roll, keep_if: "@face == 6"}]}
```

Ações e procedimentos são listas de passos, e gatilhos são passos com uma guarda `when:`. Os passos são:

| Passo | Faz |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | uma rolagem registrada; vincula `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`; um `{…}` é preenchido primeiro, como em qualquer texto, então os dados que um valor guarda como texto são rolados (`{@{who.inventory.$item.damage}}`), e o registro os mostra: um valor que não é dado é recusado, assim como `roll: "@die"` com esse texto, que não rola nada; um conjunto de rolagens (`{d8, d6}kh1`) continua sendo um |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | calcula valores; como no `value` de `set`, texto com `{…}` é um modelo e uma palavra solta é texto; em qualquer texto preenchido, `{{` e `}}` escrevem a própria chave |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (ou `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | muda uma ficha: validado, limitado, reversível; `set: who.$attr` define o campo que um parâmetro indica, e `set: who.inventory.$item.damage`, uma chave de um item que a ficha carrega (veja Inventário); `-=` tira um valor de uma lista, e um que ela não contém não muda nada (uma nota avisa; um que ela nunca poderia conter é recusado); `unset:` tira um campo, como `set --unset` |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | dá um item a uma ficha ou tira um dela, como `inv add` e `inv drop` fazem: os detalhes vêm do compêndio, basta uma parte única do nome, e o espaço e os hooks do campo são verificados |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | usa um item que a ficha carrega, como `inv use` faz: usos ou cargas diminuem, um dado de uso é rolado e desce um passo com 1–2, e um que se esgota some, a menos que recarregue ou seja guardado; de vários com esse nome, o primeiro que ainda tenha um uso; vincula `@torch.out` (o último uso dele se foi), `@torch.gone` (não sobrou nada dele), `@torch.left`, `@torch.die` e `@torch.rolled` (`as:` é `use` por padrão) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | cria uma ficha imediatamente, descrita como no `entity` de um rascunho (veja abaixo) e verificada contra sua folha; `as:` (senão sua `key`, senão seu tipo) a vincula como ficha, lida e definida como um parâmetro `ref` (`pool: "@bleeding"`, `@bleeding.name`), e nunca é o nome de um parâmetro; sem `key:`, nenhum campo é tomado por uma chave (`kind: track` fica como está); se já houver aqui uma desse tipo e com esse nome, ela é usada como está, então uma regra executada de novo não cria nada novo |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | executa um teste e vincula o resultado |
| `do: other-action`, `with: {…}`, `as: trip` | executa outra regra; `@trip` é o resultado dela e `@trip.<name>` o que ela vinculou (`@trip.found` pelo `let: {found: 2}` dela, `@trip.luck` pelo `roll: d6`, `as: luck` dela); `as:` é o id dela por padrão |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | uma rolagem de tabela registrada; vincula o texto e os `data` da entrada (`@scar.<key>`, e as chaves de um mapeamento pelo caminho delas: `@scar.cost.hp`), junto com os de qualquer tabela rolada em seguida; uma lista de itens (`[Rope, {name: Laser, damage: d8}]`) é lida como os nomes deles (`count(@scar.gear)`, `'Laser' in @scar.gear`), e passada como está para um passo (`apply: "@scar.gear"`) são os próprios itens; uma lista de outros mapeamentos só um passo lê |
| `table: "setting-{@drop.difficulty}-terrain"` | uma tabela calculada: `{…}` e `$param` são preenchidos |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | vários resultados em uma lista (`distinct` rola de novo os repetidos) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | ramificações |
| `repeat: "@count"`, `as: i`, `steps: […]` | um laço: os passos esse número de vezes, com `@i` contando a partir de 1 |
| `for: pcs` (ou `party`), `as: member`, `steps: […]` | os passos uma vez para cada personagem de jogador (ou membro do grupo), como `@member`: uma ficha, tal como a que `entity:` vincula (`@member.name`, `set: member.fatigue`); `as:` nunca recebe o nome de um parâmetro, então o `who` da própria regra continua sendo o dela |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | saída para o LLM |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (ou `every: 1 day`) | um lembrete que vence conforme o tempo de jogo passa, como os que `didact remind` marca |
| `reroll: roll`, `keep_if: "@face == 6"` | rola de novo alguns dados de uma rolagem (mecânicas de forçar) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | rola em um valor de lista (as listas de um oráculo): vincula a entrada, `@who.choose` (uma linha em branco) e `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | rola a reserva decrescente de um contador como `track roll` faz (dados que mostram 1-3 saem; os dados de `drop` saem primeiro, os de `extra` rolam junto) ou só descarta dados (`mode: drop`: forçar, marcar); em seguida vêm as fases vinculadas e o evento da reserva; vincula `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

O resultado de um teste pode ser lido pela regra que o executou (`check: … as: answer` dá `@answer`), e os marcadores dele também: `'random-event' in @answer.flags`. Os valores de `with:` são avaliados quando contêm `@`, preenchidos quando contêm `$param` ou `{…}` (“Does $npc flee?”), e passados como escritos nos outros casos. Uma regra com um parâmetro `oracle` recebe a ficha de estado do oráculo da campanha sem precisar pedir. Um parâmetro `ref` com `to: monster` pega uma ficha desse tipo: um nome que outra ficha compartilha (a reserva de um inimigo, com o nome da carta dele) é a desse tipo.

Gatilhos executam sozinhos quando o evento deles acontece, e só se a condição `when:` for verdadeira:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Qualquer regra (inclusive um gerador e a criação de personagens) pode ler `@system` (o id do sistema com que o mundo é jogado, para que um cenário escrito para dois sistemas consiga diferenciá-los), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` e `@time.is_night` e, com um calendário de meses, `@time.month`, `@time.month_name`, `@time.day_of_month` e `@time.year`; durante um combate, `@combat.round` e `@combat.fighters` (os ids de quem está nele). Um gatilho de tempo também pode ler `@time.passed`, os segundos que acabaram de avançar, um gatilho `combat_start` ou `combat_end` lê o combate que começa ou termina (`combat start` e `combat end` os executam; a saída de um combatente não encerra o combate), e uma regra executada por um gatilho lê o que o gatilho lê. Um gatilho com parâmetros obrigatórios só é executado por `didact do` ou por um hook de campo (`who` = a ficha). Gatilhos `on: manual` só executam quando chamados. `for: pcs` (ou `party`) executa um gatilho uma vez para cada personagem de jogador (ou membro do grupo), como `who`: a experiência depois de cada sessão, por exemplo. Um gatilho que falha para o comando que o disparou, e diz qual gatilho era e como seguir sem ele (`didact override add trigger <id> --data '{"on": "manual"}'`).

O calendário fica nos `settings` de um pacote: o de um pacote de cenário prevalece sobre o do sistema, e o próprio calendário de um mundo (`calendar:` no `world.yaml` dele) sobre os dois:

```yaml
settings:
  watches: [morning, afternoon, night]   # the day's watches
  calendar:
    week: [Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday]
    months: [{name: January, days: 31}, {name: February, days: 28, leap: [4, 100, 400]}, …]
    start: {year: 1890, month: 3, day: 14, weekday: Friday}   # where a campaign opens
    year: "{year} AD"                     # how a date writes its year
    seasons: [{name: spring, month: 3, day: 20}, …]           # each from its first day
    holidays: [{name: Midsummer, month: 6, day: 24, text: "…"}]
```

`leap: 4` deixa um mês um dia mais longo a cada 4 anos, e `leap: [4, 100, 400]` a cada 4, mas não a cada 100, mas sim a cada 400: cada número se sobrepõe ao anterior. `weekday` diz o dia da semana do início (senão, é o primeiro da semana), e `year` é como uma data escreve o ano dela, tanto nas que o Didact mostra quanto nas que ele lê (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` verifica os três. Uma campanha pode começar em outra data do calendário, antes do início dele ou depois: `didact campaign new <id> --date '4 July 1902'`, ou `didact time set '<date>'` até a primeira sessão dela. Um dia da semana escrito antes da data é verificado: a data decide, e uma nota avisa quando ela cai em outro.

As opções são as variantes e regras opcionais do sistema, que cada campanha escolhe na sessão zero:

```yaml
option: lethality                       # rules read it as @option.lethality
ask: How deadly should it be?           # session zero asks it (in place of Didact's own of that key)
choices: {gentle: "…", standard: "As the book has it.", deadly: "…"}   # each with what it means
default: standard
---
option: supplies                        # a flag: on or off (@option.supplies is true or false)
kind: flag
ask: Can the PCs run out of supplies?
help: Each PC has a 4d Supplies pool.
---
option: flavor
choices: {heroic: "…", grimdark: "…"}
implies: {grimdark: {lethality: deadly, supplies: true}}   # a choice that sets others (a flag's: on)
```

`didact campaign profile lethality=deadly supplies=on` as salva (ou a página Configurações do app web). As regras, a criação de personagens e os geradores as leem (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): uma resposta prevalece sobre o que outra opção implica, e isso sobre o valor padrão. O que uma opção implica é seguido até o fim (um estilo que define a letalidade também define o que essa letalidade implica), e, entre duas implicações, prevalece a mais próxima. O resumo lista as que diferem do seu valor padrão, com o que significam, para que o mestre aplique o que as regras não conseguem. Um gerador que não pode rodar com elas para com `stop:` e o motivo, e nenhum rascunho é criado.

## Oráculos: `oracles/`

```yaml
oracle: chart
title: Chart oracle
ask: chart-question          # the check that answers; it may take question, odds and oracle
odds: [unlikely, 50-50, likely]
meaning: [actions, descriptions]   # tables for `didact meaning` (a word from each)
state: {chaos: {start: 5, min: 1, max: 9}}  # kept per campaign; rules read @oracle.chaos
lists: {names: [threads, characters], method: sections}   # weighted lists (`didact lists`)
prompt: Interpret the answer in the fiction.
```

- **Perguntando:** `didact ask '…' --odds likely` executa o teste `ask`. A resposta é o resultado dele (uma faixa), e os marcadores vêm junto.
- **Estado:** fica em uma ficha que o teste recebe como `oracle`. Um teste o muda com `set: oracle.chaos += 1`.
- **Listas:** `lists: {names: […], method: sections, most: 3}` guarda listas com peso nessa ficha. `didact lists add|drop|roll|show` as gerencia, e as regras rolam nelas com `pick`. `sections` rola uma seção de cinco linhas, depois uma linha dentro dela (uma linha em branco significa escolher); `uniform` dá a mesma chance a todas as linhas.
- **Mais para o teste:** `didact ask '…' --with as_rule=true` passa parâmetros extras para o teste do oráculo.
- **O registro:** toda resposta é numerada (`#o12`) e registrada, e `didact interpret o12 '…'` guarda o que ela significou. O oráculo `yes-no` do pacote core é o padrão de reserva.

## Geradores e criação de personagens: `generators/`, `chargen/`

Os dois são procedimentos que montam um **rascunho**. Eles usam todos os passos de regra (`roll`, `table`, `if`, `let`, `prompt`, …) e mais estes:

| Passo | Faz |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | adiciona uma ficha ao rascunho (chaves `poi-1`, `poi-2`, …); um campo ou um link que cita uma chave escrita pelo pacote (`key:`, ou um nome `as:`) vira o id dessa ficha ao confirmar, então escolha chaves que nenhum campo tenha como texto (uma entidade sem nenhuma das duas não tem chave a substituir); `from: "@relic.id"` a cria a partir de uma entrada do compêndio (seu tipo, nome e campos) |
| `choose: {from: [a, b], as: x}` (ou `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | uma escolha; no modo guiado o rascunho aguarda `choose`; `exclude` descarta escolhas anteriores (uma que sair na rolagem é rolada de novo); `records:` adiciona as fichas desse tipo que existem aqui, por id (criadas durante o jogo); `answer:` faz a escolha quando seu valor é uma das opções (o caminho do próprio personagem), sem perguntar |
| `choose_or_roll: {table: backgrounds, as: background}` | uma escolha que os dados podem fazer; os dados de uma entrada escolhida ficam em `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | rola valores para o personagem |
| `swap: {among: [STR, DEX, WIL], optional: true}` | troca dois valores, ou mantém |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | distribui um conjunto fixo |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | compra valores dentro de um orçamento (`default: random` o gasta aleatoriamente no modo aleatório) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | uma lista vai para o inventário; um mapeamento define campos (listas se somam) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | adiciona a um campo do personagem (ou de uma entidade do rascunho): números se somam, o resto entra em uma lista; não ter nada a adicionar não é problema |
| `remove: {field: talents, value: "@old"}` | tira algo de um campo de lista (um talento trocado, um laço resolvido); não ter nada a tirar não é problema |
| `roll_tables: [physique, vice]` | rola tabelas para `traits`; o `data.gear` de uma entrada vai para o inventário e `data.add: {gold: 20}` soma aos campos |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | o nome; `name: {prompt: …}` sem nada de onde rolar aguarda um nome, mesmo no modo aleatório |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | uma pergunta que aceita qualquer resposta (um objetivo, o nome de outra ficha): o rascunho aguarda por ela, mesmo no modo aleatório, a menos que venha preenchida de antemão; `field:` guarda a resposta |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | um pointcrawl: dados jogados sobre o mapa, com registro, caminhos (sempre conectados), distâncias, caminhos ocultos (veja abaixo) |

O passo map aceita mais, para os procedimentos de jogar dados sobre o mapa dos livros:

| Chave | Faz |
|---|---|
| `regions: terrain` | essas entidades também são jogadas; cada lugar entra na mais próxima (sua `region`) |
| `hidden: 6`, `conditional: 5` | um d6 por caminho: no número ou acima dele, um caminho oculto ou condicional (caminhos ocultos ficam fora do mapa dos jogadores) |
| `describe: [path-feature, path-condition]` | tabelas roladas para cada caminho, guardadas como seus `details` |
| `entrance: true`, `exit: true` | o lugar mais perto da borda é a entrada; os demais são numerados a partir dela ao longo dos caminhos (`map.n`), os caminhos se afastam dela, e a saída é um lugar distante perto de uma borda, numerado por último |
| `number: "{@dungeon_name}, room {@n}"` | renomeia os lugares numerados (as chaves deles no rascunho acompanham: `room-1` é a sala 1) |

Uma tabela de jogar dados pode citar as próximas tabelas nos dados das suas entradas, para que o procedimento se leia como o livro: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, e depois `table: "{@drop.what}"`. Campos de lista não definidos (conditions, lists, tags) são lidos como listas vazias, então `'deprived' in @who.conditions` funciona desde o início.

```yaml
chargen: pc
creates: pc
modes: [random, guided]
steps:
  - choose_or_roll: {table: backgrounds, as: background, field: background}
  - apply: "@background.gear"
  - roll: {each: [STR, DEX, WIL], dice: 3d6}
  - swap: {among: [STR, DEX, WIL], optional: true}
  - name: {from: "@background.names"}
```

Um chargen com `advances:` altera uma ficha em vez de criar uma: a subida de nível do sistema.

```yaml
chargen: level-up
advances: pc                   # `didact char advance <pc>`, or Level up on its page
params: {who: ref}
steps:
  - if: "@who.xp < @who.level + 1"
    then: [stop: "{@who.name} needs more XP"]
  - apply: {level: "{@who.level + 1}", xp: "{@who.xp - @who.level - 1}"}
  - choose: {table: paths, as: path, answer: "@who.path"}     # the character's own: not asked
  - choose: {from: "@path.talents", records: talent, as: talent, exclude: "@character.talents"}
  - add: {field: talents, value: "@talent"}
```

- **Uma só ficha:** um gerador com `creates: npc` monta essa ficha como a criação de personagens monta um personagem (`apply`, `add`, `name`, `field:`); seus passos `entity` adicionam fichas ao lado, e um link `to: character` aponta para ela.
- **Executando:** `gen run` e `char new` criam um rascunho (`#g7`, `#c3`) e não salvam nada. Um `stop:` o encerra sem criar nada: sob um `if:` que lê uma opção da campanha, a dica dele aponta para as opções (`didact session zero`); senão, as próprias palavras dele dizem o que fazer em vez disso.
- **Decidindo:** `--prefill '{…}'` decide coisas de antemão, pelo nome que um passo vincula (`as:`): um valor único responde a todas as ocorrências, uma lista a uma ocorrência cada (uma lista para um `choose` com `count` é a escolha inteira). Valores de `let` também podem ser preenchidos de antemão (`{"hp": 6}`), e um nome, um `ask` ou um `let` mantém qualquer texto tal como foi dado. Um valor para uma escolha entre opções conhecidas (um `choose`, a entrada de uma tabela) é a opção que ele nomeia, como está escrita ou com outras maiúsculas e minúsculas, pelo `id` da entrada dela ou por uma rolagem que caia nela (`{"group": 3}`), e traz os dados dessa entrada; um valor próximo de uma opção, mas que não é nenhuma delas, é recusado, indicando a mais próxima, e qualquer outro é uma resposta própria, sem dados. `--auto` (ou `char new --mode random`) deixa os dados decidirem o resto. Caso contrário, o rascunho aguarda em cada escolha.
- **Descrevendo:** uma escolha diz o que cada opção significa, para o jogador que escolhe: o `note:` de uma entrada de tabela ou o `about:` da tabela dela, senão a entrada do compêndio que ela nomeia (o `id` dos dados dela), ou aquela que a própria opção é (uma escolha entre ids do compêndio mostra o nome de cada um): seu `tagline` e `summary`, sua `description` ou `effect`, senão o primeiro parágrafo do texto dela.
- **Voltando:** `char back` (ou `gen back`) desfaz a última resposta, rolagem ou edição, então o rascunho faz essa pergunta de novo; as rolagens que ele fez são marcadas como desfeitas.
- **Retomando:** um rascunho retomado refaz seu percurso: cada valor rolado ou escolhido, cada um usado uma vez e em ordem (inclusive os dados jogados sobre o mapa), então nada é rolado duas vezes e nada do que já foi decidido muda.
- **Salvando:** `commit` grava as fichas, verificadas contra suas folhas.
- **Evoluindo:** um rascunho `advances:` parte de uma cópia da ficha (com os valores padrão da folha dela), seus passos leem a ficha como `@who` e os valores do rascunho como `@character.*`, e `commit` grava só o que mudou, verificado como em `set`; as fichas geradas pelos seus passos `entity` (a trama de um novo laço) são criadas ao lado: um link `to: character` aponta para a ficha, e um campo que cita uma chave guarda o id da ficha correspondente, como quando um personagem é criado (`apply: {blood: "@pool"}`). Um `stop:` diz por que ainda não (XP insuficiente), e nenhum rascunho é criado. Um sistema cujo crescimento é uma única regra a indica no chargen dele, em vez disso: `advance: {rule: grow}`.
- **Modos:** `modes: [guided]` mantém um procedimento passo a passo: `--mode random` é recusado.

## Compêndio, referência e glossário

- **Entradas do compêndio** são escritas como em `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. Um valor `"roll 2d8"` é rolado quando a entrada é criada. Execute `didact spawn troll`, ou traga as entradas de um pacote para o mundo com `didact compendium import <pack>` (`--type loc`, e `--tag coast` para as que têm todas as tags dadas).
- **Para vários sistemas:** uma chave de primeiro nível vai para onde `set` a coloca: para o bloco do sistema quando a ficha dele tem esse campo, senão para `fields`. Uma entrada que um cenário escreve para mais de um sistema dá os números de cada um no próprio bloco (`mechanics: {my-system: {hp: 12}}`): `pack validate` verifica cada bloco contra a ficha desse sistema quando ele está instalado, e aponta uma chave de primeiro nível que essa ficha e a do core têm. O que um bloco diz vale: ao lado de `mechanics: {my-system: {role: tactician}}`, um `role: innkeeper` de primeiro nível é o campo do core, como tudo o que fica sob `fields:`. Um bloco que cita o pacote sendo validado é verificado contra esse pacote como ele está na pasta dele.
- **Seções de referência** ficam em `reference/*.md`, com front matter (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` as encontra; uma frase entre aspas que não aparece é tentada palavra por palavra.
- **O glossário** é `glossary.yaml`: `term: definition`, ou uma lista de `{term, definition, aliases, see}`. `didact define <term>` o lê.

## Testes: `tests/`

```yaml
test: weather-lands     # roll a table many times: every roll must land
table: weather
times: 50
---
test: fair-save         # exact odds
odds: "d20 <= 10"
chance: 0.5
---
test: every-table       # each of the pack's tables (a lookup table once per key)
table: all
---
test: play              # a smoke-play script: real commands in a scratch library
script:
  - world new t --system {pack} --seed smoke    # seeded: it plays the same every time
  - new pc Hero --fill
  - run: do save who=hero attr=STR
    expect: "→"                                  # text the step must print (or a list)
  - run: table list
    expect_not: my-system.spell-fire             # text it must not print (or a list)
  - run: table roll my-system.spell-fire
    fails: true                                  # it must fail (`expect` reads its error too)
```

## Compartilhando e removendo pacotes

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- Um pacote que declara `redistributable: false` não pode ser exportado.
- **core** faz parte do Didact e está sempre ativo: todo sistema se apoia nele, então ele não pode ser desativado nem desinstalado.
- Os outros pacotes que vêm com o Didact são arquivos `.didactpack` na pasta `packs/` dele. `pack list` os mostra até serem instalados, e instalar um traz junto os pacotes de que ele precisa, se também vierem com o Didact.
- `pack update` procura versões mais novas na pasta `packs/` do Didact e no GitHub (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` indica outro lugar, ou nenhum, para não procurar). Uma versão nova é instalada ao lado da antiga: as campanhas mantêm a delas até `didact campaign upgrade`.
- Só um sistema de jogo é usado por vez: o do mundo aberto. Um mundo mantém o sistema com que foi criado (`didact world new <id> --system <pack>`; um mundo criado sem sistema fica com o primeiro que receber, com `pack enable` ou `world set system=`), suas campanhas são jogadas com ele, e não é possível adicionar um pacote que precise de outro sistema (um cenário escrito para ele): outro sistema é jogado num mundo próprio.
- `uninstall` recusa enquanto um mundo ou uma campanha usar a única cópia do pacote (`--force` o remove mesmo assim). Isso não pode ser desfeito: instale o .didactpack de novo.

## Do livro de regras ao pacote: a lista de verificação

Percorra as mecânicas do livro nesta ordem. Cada uma corresponde a algo acima:

1. **Resolução:** como uma rolagem tem sucesso (um teste: `success`, `bands`, `auto`).
2. **Dados:** dados incomuns, símbolos, passos (`dice.yaml`, dados com nome, cadeias).
3. **A folha:** atributos, números derivados (`schemas/`, campos derivados).
4. **Recursos:** PV, sorte, ímpeto (campos resource e counter; passos `set`).
5. **Condições:** estados e o que fazem (campos `conditions`; passos `if`).
6. **Combate:** ataques, dano, iniciativa (ações; `bag`/`deck` para a ordem dos turnos).
7. **Procedimentos:** exploração, viagem, tempo livre (procedimentos com instruções).
8. **Tabelas:** todas as tabelas aleatórias (`tables/`; `pack import` para tabelas em Markdown).
9. **O bestiário:** monstros e PdMs (`compendium/`).
10. **Itens:** equipamento, magias, relíquias (`compendium/`, campos slots).
11. **Orientação para o Mestre:** princípios e conselhos (`GUIDE.md`, `reference/`, `guidance:` nos tipos).
12. **Criação de personagens:** como fazer um personagem (um procedimento em `chargen/`, ou `roll:` em cada campo).

Cite as páginas com `source:` em todo lugar, para que as lacunas apareçam. Adicione um teste de jogo rápido que crie um personagem, role um teste, lute e execute um procedimento.
