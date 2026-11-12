<!-- translated from b1dfa1159ff4 -->
# Pacotes

Um pacote é um sistema de jogo, um oráculo, um cenário, uma aventura ou um suplemento, escrito como ficheiros YAML e, opcionalmente, um plugin em Python. Este guia mostra como escrever um: transformar um livro de regras num pacote, ou acrescentar conteúdo caseiro.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Um pacote também pode ser feito a partir do que está na tua biblioteca. `didact pack new my-brew --from-overlay my-system` transforma o teu conteúdo caseiro para um sistema (`compendium add`, fichas guardadas com `--scope system`, lore) num suplemento, e `didact world export --as setting` transforma um mundo num pacote de cenário: as suas pessoas, lugares e lore como entradas do compêndio e lore do pacote, trazidos para outro mundo com `compendium import`. Ambos deixam de fora os segredos e as notas do Mestre, salvo `--secrets`, e nenhum fica marcado como partilhável até definires a sua licença.

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

Um ficheiro contém um item, uma lista de itens, ou vários itens separados por `---`. Cada item indica o seu id com a chave do seu tipo: `table: weather`, `check: save`, `type: pc`, ou `id: troll` para entradas do compêndio. Refere-te aos itens como `pack.id` (`my-system.save`), ou só pelo id quando apenas um pacote ativado o tem.

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

Um hack indica a sua base em `extends` e contém apenas o que difere:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

O seu item com o mesmo id substitui o da base, seja qual for o tipo (uma tabela, uma regra, uma entrada do compêndio, uma secção de referência, um termo do glossário). As suas `settings` sobrepõem-se às da base, chave a chave: uma chave que o hack defina substitui por inteiro o valor da base (as suas tabelas `names` tomam o lugar das da base), e as regras da base também leem os valores do hack. `hides` descarta o que resta e de que o hack não precisa: `*` corresponde a qualquer sequência de caracteres, decide o último padrão que corresponde a um id, e um que começa por `!` mantém o item. O que o hack substitui nunca é ocultado. Os tipos são `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` e `term`. `didact pack validate` avisa sobre um padrão que não corresponde a nada.

## Expressões

Todas as condições e fórmulas usam a linguagem dos dados (`didact guide dice`), e ainda:
- **Valores:** `@name` lê um valor: `@roll`, `@who.STR`, `@settings.x`. `$name` cola primeiro o texto de um parâmetro, por isso `@who.$attr` passa a `@who.STR`. Lê um parâmetro de texto livre como `@name`, não entre aspas (`'$name'`): um apóstrofo no seu texto fechá-las-ia (`pack validate` avisa).
- **Lógica:** `and`, `or`, `not` e `in` (`'deprived' in @who.conditions`).
- **Literais:** texto (`'travel'`) e `true`/`false`.
- **Funções:** `if(cond, a, b)` só lança o ramo que segue. `default(@thread.flashpoint, 0)` é o valor, ou a alternativa quando não está definido. `sum`, `count` (`count(@roll.dice, 6)` conta os seis), `min`, `max`, `any` e `all` recebem listas.

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
| `slots` | objetos (`Rope` ou `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | o que o nome diz | `to` (para refs), `allowed` |
| `derived` | calculado, nunca guardado | expr |

Todos os campos aceitam também `label`, `help`, `default`, `required` e `roll`: `new pc Hero --fill`, ou um valor `"roll"`, lança-o através do registo. Os tipos do pacote `core` guardam texto independente do sistema em `fields`. Os tipos de um sistema guardam os seus números em `mechanics.<system>`. `set hero hp-=2` encontra o campo, limita-o e assinala qualquer excesso. `+=` acrescenta a uma lista: uma `list` (como `slots`) mantém também um valor acrescentado de novo, `tags`, `conditions` e `refs` guardam-no uma só vez, e `-=` retira todas as cópias.

**Os hooks** dizem o que acontece quando um valor passa uma fronteira. Disparam a cada alteração (`set`, `inv`, um passo `set` de uma regra), mas só quando a fronteira é cruzada: 3 → 0 dispara, 0 → 0 não. As edições com `--force` saltam-nos.

| Hook | Dispara quando |
|---|---|
| `on_zero` | um número ou `{value}` chega a 0 |
| `on_full` (`when_full` em slots) | chega ao seu máximo, tamanho ou capacidade |
| `thresholds: {10: …, 20: …}` (counters) | ultrapassa cada marca ao subir |

Uma ação é texto (uma nota para o LLM), `{set: {hp: 0}}` ou `{condition: paralyzed}` na mesma ficha, `{trigger: death}` (executa essa regra com `who` = a ficha), ou uma lista destes.

**O inventário** (`didact inv …`) trabalha sobre o campo `slots` da folha:
- **Espaço:** os objetos ocupam o seu `size` × `count`, e os contadores que ocupam o campo (`occupies`) ocupam o seu valor. Passar da `capacity` é recusado, a menos que uses `--force`.
- **Grupos:** `groups: {backpack: 6, body: 4}` dá a cada grupo o seu próprio espaço, e também as suas próprias colunas e totais: `@inventory.body.armor` é só o que se traz vestido ou na mão, `@inventory.body.free` o espaço que lhe resta.
- **Usos:** `uses: 3` desconta com `inv use`. `uses: d8` é um dado de uso: 1–2 fá-lo descer um degrau. Um objeto gasto desaparece, a menos que tenha `recharge` ou `keep: true`. De vários objetos com o mesmo nome, o nome indica o primeiro; para gastar um uso (`inv use`, o `use:` de uma regra, `set …uses-=1`), o primeiro a que ainda reste um.
- **Chaves próprias de um objeto:** `didact set freya inventory.sword.damage=d10` (e também o `set: who.inventory.$item.damage` de uma regra) altera uma delas, com o objeto indicado como no `inv`, por uma parte do nome ou pelo nome inteiro, com espaços e pontos (`'inventory.12.7mm pistol.damage=d10'`, entre aspas para a shell); `uses` e `charges` contam como um campo `uses` (`charges+=2` não passa do máximo), e o espaço é verificado como no `inv add`. Uma regra lê uma como `@{who.inventory.$item.damage}` (um dado de uso como o seu dado, os usos como o seu número); um objeto ou uma chave que não esteja lá lê-se como ausente, por isso `default(…)` dá o seu valor de recurso.
- **Compêndio:** as entradas do tipo `item` (ou weapon, armor, relic, …, ou um tipo próprio do pacote que estende um deles com `extends`) emprestam os seus detalhes a `inv add`, encontradas pelo id, pelo nome ou por um alias (se duas partilharem um: indica-a como `pack.id`); qualquer outro nome, `:` incluído, é o nome próprio do objeto.

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

Outras formas:
- **Listas ponderadas:** `entries` como lista, com `weight:` em cada entrada.
- **Colunas:** `columns: [a, b]` lança cada coluna de uma linha em separado. Uma entrada simples (não uma lista) preenche todas as colunas, por isso `columns: [first, second]` sobre uma lista de palavras quer dizer «lança duas vezes nesta lista». `labels: false` omite os nomes das colunas no resultado («Abandon · Advantage»). `read: "It's a {first} {second} with {third} {fourth} inside."` lê as colunas como uma frase.
- **Consultas:** `lookup: hp_lost`, ou `[odds, chaos]` para uma tabela de dupla entrada.
- **Repetidos:** `duplicates: reroll | keep | make_it_worse` para «lança duas vezes».
- **Em duas etapas:** uma entrada que lança noutra tabela (`{table: lightning}` em vez de texto, ou `then:` depois dele) traz consigo os dados desse lançamento: uma regra ou um rascunho em que ela saia lê uns e outros, primeiro as chaves da própria entrada, depois as da primeira tabela lançada a seguir. Um `--prefill` pode indicar uma entrada mais abaixo, a qualquer profundidade (`Ring of the Hunt`), com os dados de cada entrada pelo caminho: de duas com o mesmo nome conta a mais próxima (depois a primeira), uma que segue lança a partir daí, e uma próxima de alguma delas sem o ser é recusada, indicando a mais próxima. Um rascunho guiado oferece o primeiro passo quando as suas entradas dizem o que são (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): escolher uma lança na tabela seguinte, como um lançamento que lhe calha.
- **Ler nos dois sentidos:** `both_ways: true` numa tabela d66 acrescenta a outra leitura: 31 também dá 13, e quem lê escolhe.
- **O que uma entrada significa:** `about: "Knows: {skills}. Also known as: {aka}."` preenche os dados de cada entrada (uma lista lê-se `a, b`; `{text}` é a própria entrada) para dizer o que ela dá quando uma escolha a oferece; o `note:` próprio de uma entrada di-lo em vez disso. Sem nenhum dos dois, uma entrada cujos dados têm um `id` que nomeia uma entrada do compêndio é descrita por essa entrada.
- **Baralhos e sacos:** `deck: tarot` com `cards` (ou `standard: true`); `bag: initiative` com `tokens`.

A validação verifica que cada resultado que os dados podem dar cai numa entrada.

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

As ações e os procedimentos são listas de passos, e os gatilhos são passos com uma guarda `when:`. Os passos são:

| Passo | Faz |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | um lançamento registado; associa `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`; um `{…}` é preenchido primeiro, como em qualquer texto, por isso os dados que um valor guarda como texto são lançados (`{@{who.inventory.$item.damage}}`), e o registo mostra-os: um valor que não seja dados é recusado, tal como `roll: "@die"` com esse texto, que não lança nada; um conjunto de lançamentos (`{d8, d6}kh1`) continua a sê-lo |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | calcula valores; como no `value` de `set`, o texto com `{…}` é um modelo e uma palavra solta é texto; em qualquer texto que se preenche, `{{` e `}}` escrevem a própria chaveta |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (ou `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | altera uma ficha: validado, limitado, anulável; `set: who.$attr` define o campo que um parâmetro indica, e `set: who.inventory.$item.damage`, uma chave de um objeto que a ficha leva (ver Inventário); `-=` tira um valor de uma lista, e um que ela não contém não muda nada (uma nota di-lo; um que nunca poderia conter é recusado); `unset:` tira um campo, como `set --unset` |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | dá um objeto a uma ficha ou tira-lhe um, como fazem `inv add` e `inv drop`: os seus detalhes vêm do compêndio, basta uma parte única do seu nome, e o espaço e os hooks do campo são verificados |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | usa um objeto que a ficha leva, como `inv use` faz: os usos ou as cargas descontam, um dado de uso é lançado e desce um degrau com 1–2, e um que se esgote desaparece, a menos que recarregue ou seja guardado; de vários com esse nome, o primeiro a que reste um uso; associa `@torch.out` (o seu último uso foi-se), `@torch.gone` (nada dele resta), `@torch.left`, `@torch.die` e `@torch.rolled` (`as:` é `use` por omissão) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | cria de imediato uma ficha, descrita como no `entity` de um rascunho (ver abaixo) e verificada contra a sua folha; `as:` (senão a sua `key`, senão o seu tipo) associa-a como ficha, lida e definida como um parâmetro `ref` (`pool: "@bleeding"`, `@bleeding.name`), e nunca é o nome de um parâmetro; sem `key:`, nenhum campo é tomado por uma chave (`kind: track` fica tal como está); se já houver aqui uma desse tipo e com esse nome, é usada tal como está, por isso uma regra executada outra vez não cria nada de novo |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | executa um teste e associa o seu resultado |
| `do: other-action`, `with: {…}`, `as: trip` | executa outra regra; `@trip` é o seu resultado e `@trip.<name>` o que ela associou (`@trip.found` pelo seu `let: {found: 2}`, `@trip.luck` pelo seu `roll: d6`, `as: luck`); `as:` é o seu id por omissão |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | um lançamento de tabela registado; associa o texto e os `data` da entrada (`@scar.<key>`, e as chaves de um mapeamento pelo seu caminho: `@scar.cost.hp`), juntamente com os de qualquer tabela lançada a seguir; uma lista de objetos (`[Rope, {name: Laser, damage: d8}]`) lê-se como os seus nomes (`count(@scar.gear)`, `'Laser' in @scar.gear`), e passada tal como está a um passo (`apply: "@scar.gear"`) são os próprios objetos; uma lista de outros mapeamentos só um passo a lê |
| `table: "setting-{@drop.difficulty}-terrain"` | uma tabela calculada: `{…}` e `$param` são preenchidos |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | vários resultados numa lista (`distinct` relança os repetidos) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | ramificações |
| `repeat: "@count"`, `as: i`, `steps: […]` | um ciclo: os passos esse número de vezes, com `@i` a contar a partir de 1 |
| `for: pcs` (ou `party`), `as: member`, `steps: […]` | os passos uma vez por cada personagem jogadora (ou membro do grupo), como `@member`: uma ficha, tal como a que `entity:` associa (`@member.name`, `set: member.fatigue`); `as:` nunca recebe o nome de um parâmetro, por isso o `who` da própria regra continua a ser o seu |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | saída para o LLM |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (ou `every: 1 day`) | um lembrete que chega à hora à medida que o tempo de jogo passa, como os que `didact remind` define |
| `reroll: roll`, `keep_if: "@face == 6"` | relança alguns dos dados de um lançamento (mecânicas de forçar) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | lança sobre um valor de lista (as listas de um oráculo): associa a entrada, `@who.choose` (uma linha em branco) e `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | lança a reserva decrescente de um contador como faz `track roll` (os dados que mostram 1-3 saem; os dados de `drop` saem primeiro, os de `extra` são lançados com os outros) ou apenas retira dados (`mode: drop`: forçar, marcar); seguem-se as fases ligadas e o evento da reserva; associa `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

O resultado de um teste pode ser lido pela regra que o executou (`check: … as: answer` dá `@answer`), e os seus indicadores também: `'random-event' in @answer.flags`. Os valores de `with:` são avaliados quando contêm `@`, preenchidos quando contêm `$param` ou `{…}` («Does $npc flee?»), e passados tal como estão escritos nos outros casos. Uma regra com um parâmetro `oracle` recebe a ficha de estado do oráculo da campanha sem ser preciso dizer-lho. Um parâmetro `ref` com `to: monster` toma uma ficha desse tipo: um nome que outra ficha partilha (a reserva de um inimigo, com o nome da sua carta) é a desse tipo.

Os gatilhos executam-se sozinhos quando o seu evento acontece, e só se a sua condição `when:` se verificar:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Qualquer regra (incluindo um gerador e a criação de personagens) pode ler `@system` (o id do sistema com que o mundo se joga, para que um cenário escrito para dois sistemas os possa distinguir), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` e `@time.is_night` e, com um calendário de meses, `@time.month`, `@time.month_name`, `@time.day_of_month` e `@time.year`; enquanto decorre um combate, `@combat.round` e `@combat.fighters` (os ids de quem está nele). Um gatilho de tempo pode também ler `@time.passed`, os segundos acabados de avançar, um gatilho `combat_start` ou `combat_end` lê o combate que começa ou termina (`combat start` e `combat end` executam-nos; a saída de um combatente não termina o combate), e uma regra executada por um gatilho lê o que o gatilho lê. Um gatilho com parâmetros obrigatórios só é executado por `didact do` ou por um hook de campo (`who` = a ficha). Os gatilhos `on: manual` só se executam quando chamados. `for: pcs` (ou `party`) executa um gatilho uma vez por cada personagem jogadora (ou membro do grupo), como `who`: a experiência depois de cada sessão, por exemplo. Um gatilho que falhe para o comando que o disparou, e diz que gatilho era e como continuar sem ele (`didact override add trigger <id> --data '{"on": "manual"}'`).

O calendário está nos `settings` de um pacote: o de um pacote de cenário prevalece sobre o do sistema, e o próprio calendário de um mundo (`calendar:` no seu `world.yaml`) sobre ambos:

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

`leap: 4` torna um mês um dia mais longo de 4 em 4 anos, e `leap: [4, 100, 400]` de 4 em 4, mas não de 100 em 100, embora sim de 400 em 400: cada número sobrepõe-se ao anterior. `weekday` indica o dia da semana do início (senão, é o primeiro da semana), e `year` é a forma como uma data escreve o seu ano, tanto nas que o Didact mostra como nas que lê (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` verifica os três. Uma campanha pode começar noutra data do calendário, antes do seu início ou depois: `didact campaign new <id> --date '4 July 1902'`, ou `didact time set '<date>'` até à sua primeira sessão. Um dia da semana escrito antes da data é verificado: decide a data, e uma nota di-lo quando ela calha noutro.

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

`didact campaign profile lethality=deadly supplies=on` guarda-as (ou a página Definições da aplicação web). As regras, a criação de personagens e os geradores leem-nas (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): uma resposta prevalece sobre o que outra opção implica, e isso sobre o valor predefinido. O que uma opção implica é seguido até ao fim (um estilo que define a letalidade também define o que essa letalidade implica), e, de duas implicações, prevalece a mais próxima. O resumo lista as que diferem do seu valor predefinido, com o que significam, para que o mestre aplique o que as regras não conseguem. Um gerador que não pode funcionar com elas para com `stop:` e o motivo, e não é criado nenhum rascunho.

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

- **Perguntar:** `didact ask '…' --odds likely` executa o teste `ask`. A resposta é o seu resultado (uma faixa), e os seus indicadores vêm junto.
- **Estado:** vive numa ficha que o teste recebe como `oracle`. Um teste altera-o com `set: oracle.chaos += 1`.
- **Listas:** `lists: {names: […], method: sections, most: 3}` guarda listas ponderadas nessa ficha. `didact lists add|drop|roll|show` gere-as, e as regras lançam sobre elas com `pick`. `sections` lança para uma secção de cinco linhas e depois para uma linha dentro dela (uma linha em branco quer dizer escolher); `uniform` dá a todas as linhas a mesma probabilidade.
- **Mais para o teste:** `didact ask '…' --with as_rule=true` passa parâmetros extra ao teste do oráculo.
- **O registo:** cada resposta é numerada (`#o12`) e registada, e `didact interpret o12 '…'` guarda o que ela quis dizer. O oráculo `yes-no` do pacote core é o recurso por omissão.

## Geradores e criação de personagens: `generators/`, `chargen/`

Ambos são procedimentos que constroem um **rascunho**. Usam todos os passos das regras (`roll`, `table`, `if`, `let`, `prompt`, …) e ainda estes:

| Passo | Faz |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | acrescenta uma ficha ao rascunho (chaves `poi-1`, `poi-2`, …); um campo ou uma ligação que nomeie uma chave escrita pelo pacote (`key:`, ou um nome `as:`) passa a ser o id dessa ficha ao confirmar, por isso escolhe chaves que nenhum campo tenha como texto (uma entidade sem nenhuma das duas não tem chave a substituir); `from: "@relic.id"` cria-a a partir de uma entrada do compêndio (o seu tipo, nome e campos) |
| `choose: {from: [a, b], as: x}` (ou `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | uma escolha; no modo guiado o rascunho espera por `choose`; `exclude` exclui escolhas anteriores (uma que saia nos dados volta a ser lançada); `records:` acrescenta as fichas desse tipo que existem aqui, por id (criadas em jogo); `answer:` faz a escolha quando o seu valor é uma das opções (o caminho próprio de uma personagem), sem perguntar |
| `choose_or_roll: {table: backgrounds, as: background}` | uma escolha que os dados podem fazer; os dados de uma entrada escolhida ficam em `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | lança para a personagem |
| `swap: {among: [STR, DEX, WIL], optional: true}` | troca dois valores, ou mantém |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | distribui um conjunto fixo |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | compra valores dentro de um orçamento (`default: random` gasta-o ao acaso no modo aleatório) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | uma lista vai para o inventário; um mapeamento define campos (as listas somam-se) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | acrescenta a um campo da personagem (ou de uma entidade do rascunho): os números somam-se, o resto junta-se a uma lista; não haver nada a acrescentar não é problema |
| `remove: {field: talents, value: "@old"}` | retira algo de um campo de lista (um talento trocado, um vínculo resolvido); não haver nada a retirar não é problema |
| `roll_tables: [physique, vice]` | lança tabelas para `traits`; o `data.gear` de uma entrada vai para o inventário e `data.add: {gold: 20}` soma aos campos |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | o nome; `name: {prompt: …}` sem nada de onde lançar espera por um, mesmo no modo aleatório |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | uma pergunta a que qualquer resposta serve (um objetivo, o nome de outra ficha): o rascunho espera por ela, mesmo no modo aleatório, a não ser que venha preenchida de antemão; `field:` guarda a resposta |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | um pointcrawl: dados largados sobre o mapa, com registo, caminhos (sempre ligados), distâncias, caminhos ocultos (ver abaixo) |

O passo map aceita mais, para os procedimentos de largar dados sobre o mapa dos livros:

| Chave | Faz |
|---|---|
| `regions: terrain` | estas entidades também são largadas; cada lugar junta-se à mais próxima (a sua `region`) |
| `hidden: 6`, `conditional: 5` | um d6 por caminho: igual ou acima do número, um caminho oculto ou condicional (os caminhos ocultos ficam fora do mapa dos jogadores) |
| `describe: [path-feature, path-condition]` | tabelas lançadas para cada caminho, guardadas como os seus `details` |
| `entrance: true`, `exit: true` | o lugar mais perto da margem é a entrada; os restantes são numerados a partir dela ao longo dos caminhos (`map.n`), os caminhos afastam-se dela, e a saída é um lugar distante perto de uma margem, numerado em último |
| `number: "{@dungeon_name}, room {@n}"` | renomeia os lugares numerados (as suas chaves no rascunho acompanham: `room-1` é a sala 1) |

Uma tabela de largar dados pode nomear as tabelas seguintes nos dados das suas entradas, para que o procedimento se leia como o livro: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, e depois `table: "{@drop.what}"`. Os campos de lista por definir (conditions, lists, tags) leem-se como listas vazias, por isso `'deprived' in @who.conditions` funciona desde o início.

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

- **Uma só ficha:** um gerador com `creates: npc` constrói essa ficha como a criação de personagens constrói uma personagem (`apply`, `add`, `name`, `field:`); os seus passos `entity` acrescentam fichas ao lado, e uma ligação `to: character` aponta para ela.
- **Executar:** `gen run` e `char new` fazem um rascunho (`#g7`, `#c3`) e não gravam nada. Um `stop:` termina-o sem criar nada: sob um `if:` que lê uma opção da campanha, a sua pista remete para as opções (`didact session zero`); senão, as suas próprias palavras dizem o que fazer em vez disso.
- **Decidir:** `--prefill '{…}'` decide coisas de antemão, pelo nome que um passo associa (`as:`): um valor único responde a todas as ocorrências, uma lista a uma ocorrência cada (uma lista para um `choose` com `count` é a escolha inteira). Os valores de `let` também podem ser pré-preenchidos (`{"hp": 6}`), e um nome, um `ask` ou um `let` mantém qualquer texto tal como foi dado. Um valor para uma escolha entre opções conhecidas (um `choose`, a entrada de uma tabela) é a opção que nomeia, tal como está escrita ou com outras maiúsculas e minúsculas, pelo `id` da sua entrada, ou por um lançamento que caia nela (`{"group": 3}`), e traz os dados dessa entrada; um valor próximo de uma opção, mas que não é nenhuma delas, é recusado, com a indicação da mais próxima, e qualquer outro é uma resposta própria, sem dados. `--auto` (ou `char new --mode random`) deixa os dados decidir o resto. Caso contrário, o rascunho espera em cada escolha.
- **Descrever:** uma escolha diz o que significa cada opção, para o jogador que escolhe: o `note:` de uma entrada de tabela ou o `about:` da sua tabela, senão a entrada do compêndio que ela nomeia (o `id` dos seus dados), ou aquela que a própria opção é (uma escolha entre ids do compêndio mostra o nome de cada um): o seu `tagline` e `summary`, a sua `description` ou `effect`, senão o primeiro parágrafo do seu texto.
- **Voltar atrás:** `char back` (ou `gen back`) desfaz a última resposta, lançamento ou edição, por isso o rascunho volta a fazer essa pergunta; os lançamentos que fez são marcados como anulados.
- **Retomar:** um rascunho retomado repete o seu percurso: cada valor lançado ou escolhido, cada um usado uma vez e por ordem (incluindo os dados largados sobre o mapa), por isso nada é lançado duas vezes e nada do que já foi decidido muda.
- **Gravar:** `commit` grava as fichas, verificadas contra as suas folhas.
- **Avançar:** um rascunho `advances:` parte de uma cópia da ficha (com os valores predefinidos da sua folha), os seus passos leem a ficha como `@who` e os valores do rascunho como `@character.*`, e `commit` grava só o que mudou, verificado como em `set`; as fichas geradas pelos seus passos `entity` (o enredo de um novo vínculo) são criadas ao lado: uma ligação `to: character` aponta para a ficha, e um campo que nomeie uma chave guarda o id da ficha correspondente, como quando se cria uma personagem (`apply: {blood: "@pool"}`). Um `stop:` diz porque é que ainda não é possível (XP insuficiente), e nenhum rascunho é criado. Um sistema cujo crescimento é uma única regra indica-a, em vez disso, no seu chargen: `advance: {rule: grow}`.
- **Modos:** `modes: [guided]` mantém um procedimento passo a passo: `--mode random` é recusado.

## Compêndio, referência e glossário

- **As entradas do compêndio** escrevem-se como em `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. Um valor `"roll 2d8"` é lançado quando a entrada é criada. Executa `didact spawn troll`, ou traz as entradas de um pacote para o mundo com `didact compendium import <pack>` (`--type loc`, e `--tag coast` para as que têm todas as etiquetas dadas).
- **Para vários sistemas:** uma chave de primeiro nível vai para onde `set` a põe: para o bloco do sistema quando a sua ficha tem esse campo, senão para `fields`. Uma entrada que um cenário escreve para mais de um sistema dá os números de cada um no seu próprio bloco (`mechanics: {my-system: {hp: 12}}`): `pack validate` verifica cada bloco face à ficha desse sistema quando está instalado, e assinala uma chave de primeiro nível que essa ficha e a de core têm ambas. O que um bloco diz mantém-se: ao lado de `mechanics: {my-system: {role: tactician}}`, um `role: innkeeper` de primeiro nível é o campo de core, como tudo o que está sob `fields:`. Um bloco que nomeie o pacote a ser validado é verificado contra esse pacote tal como está na sua pasta.
- **As secções de referência** vão em `reference/*.md`, com front matter (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` encontra-as; uma frase entre aspas que não esteja lá é experimentada palavra a palavra.
- **O glossário** é `glossary.yaml`: `term: definition`, ou uma lista de `{term, definition, aliases, see}`. `didact define <term>` lê-o.

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

## Partilhar e remover pacotes

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
- **core** faz parte do Didact e está sempre ativo: todos os sistemas assentam nele, por isso não pode ser desativado nem desinstalado.
- Os outros pacotes que vêm com o Didact são ficheiros `.didactpack` na sua pasta `packs/`. `pack list` mostra-os até serem instalados, e instalar um traz também os pacotes de que precisa, se vierem com o Didact.
- `pack update` procura versões mais recentes na pasta `packs/` do Didact e no GitHub (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` indica outro sítio, ou nenhum para não procurar). Uma versão nova instala-se ao lado da antiga: as campanhas mantêm a sua até `didact campaign upgrade`.
- Só se usa um sistema de jogo de cada vez: o do mundo aberto. Um mundo mantém o sistema com que foi criado (`didact world new <id> --system <pack>`; um mundo criado sem sistema fica com o primeiro que lhe for dado, com `pack enable` ou `world set system=`), as suas campanhas jogam-se com ele, e não se pode acrescentar um pacote que precise de outro sistema (um cenário escrito para ele): outro sistema joga-se num mundo próprio.
- `uninstall` recusa enquanto um mundo ou uma campanha usar a única cópia do pacote (`--force` remove-o na mesma). Não se pode anular: volta a instalar o .didactpack.

## Do livro de regras ao pacote: a lista de verificação

Percorre as mecânicas do livro por esta ordem. Cada uma corresponde a algo acima:

1. **Resolução:** como um lançamento tem sucesso (um teste: `success`, `bands`, `auto`).
2. **Dados:** dados invulgares, símbolos, degraus (`dice.yaml`, dados com nome, cadeias).
3. **A folha:** atributos, números derivados (`schemas/`, campos derivados).
4. **Recursos:** PV, sorte, ímpeto (campos resource e counter; passos `set`).
5. **Condições:** estados e o que fazem (campos `conditions`; passos `if`).
6. **Combate:** ataques, dano, iniciativa (ações; `bag`/`deck` para a ordem dos turnos).
7. **Procedimentos:** exploração, viagem, tempo livre (procedimentos com indicações).
8. **Tabelas:** todas as tabelas aleatórias (`tables/`; `pack import` para tabelas em Markdown).
9. **O bestiário:** monstros e NPC (`compendium/`).
10. **Objetos:** equipamento, feitiços, relíquias (`compendium/`, campos slots).
11. **Orientação para o Mestre:** princípios e conselhos (`GUIDE.md`, `reference/`, `guidance:` nos tipos).
12. **Criação de personagens:** como fazer uma personagem (um procedimento em `chargen/`, ou `roll:` em cada campo).

Cita as páginas com `source:` em todo o lado, para que as lacunas se vejam. Acrescenta um teste de jogo rápido que crie uma personagem, lance um teste, combata e execute um procedimento.
