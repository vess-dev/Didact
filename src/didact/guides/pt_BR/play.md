<!-- translated from bef7b2c650cb -->
# Jogando uma sessão

Como um jogo funciona com o Didact: o LLM narra, e o Didact guarda cada fato, cada rolagem e cada mudança.

## Antes da primeira sessão

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

Um mundo mantém o sistema com que foi criado, e suas campanhas são jogadas com ele: outro sistema é jogado num mundo próprio. `didact campaign close` deixa uma campanha de lado (o mundo dela continua aberto) e `didact campaign open <id>` a retoma de onde parou, com sessão e tudo.

`didact world delete <id>` e `didact campaign delete <id>` excluem um mundo ou uma campanha, com uma prévia antes; `--yes` exclui, e `didact undo` traz tudo de volta.

`session zero` lista as perguntas a combinar com o jogador. As do pacote vêm primeiro. Entre elas estão as opções do sistema (suas variantes e regras opcionais): as regras dele seguem as respostas, e o resumo diz o que significa cada opção alterada. Todo resumo leva as respostas.

## Uma sessão

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Turnos:** cada mensagem do jogador abre um turno (o hook do Claude Code chama `didact capture`, e outros clientes usam `turn begin`). `didact undo --turn` desfaz tudo o que foi feito para aquela mensagem: mudanças, acontecimentos e rolagens. A transcrição guarda tudo.
- **Retrocedendo:** `didact undo --to e40` desfaz tudo o que veio depois de #e40, do mais recente ao mais antigo (`--dry-run` lista tudo): cada alteração é desfeita e cada rolagem marcada como desfeita. Nada é excluído: `redo`, ou retroceder até uma alteração posterior, traz tudo de volta.
- **Tempo:** `didact time advance 1 watch` esgota temporizadores, dispara lembretes e executa gatilhos de tempo. `didact remind --list` mostra os próximos lembretes, e `didact remind --cancel 2` cancela um. Uma campanha começa no início do calendário, ou na data que `campaign new --date '4 July 1902'` informa, e `didact time set '<date>'` a muda até a primeira sessão.
- **Lugares:** `didact visit <place>` move o grupo e marca o lugar como visitado. `didact map` mostra o que o grupo conhece, e uma saída inexplorada é `?`.
- **Combates:** `didact combat start --party troll`, depois `combat next`, `combat hit freya troll weapon=d8` e `combat end`. Combatentes entram e saem no meio do combate: `didact combat join wolf-2` (no modo individual, eles rolam iniciativa) e `didact combat leave troll --why fled`. Ninguém perde a vez.
- **Coisas:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (ou para dentro de um baú, ou para um lugar); `didact where rope` encontra a corda. `inv add` encontra um item do compêndio pelo id, pelo nome ou por um alias.
- **Suas anotações:** `didact about sweeney plan='…' doing='…' where='…'` guarda o que você decidiu sobre qualquer pessoa ou coisa. Os jogadores só veem `looks`. `didact log … --about sweeney` coloca um acontecimento na ficha dele (`--secret` se os jogadores não virem). `didact guide details` tem mais.
- **O mundo segue em frente:** `didact faction turn`, além de relógios: `didact track new 'The flood' --size 6`. Um comando que só aceita um tipo de ficha toma um nome que outras compartilham como sendo desse tipo: `didact track roll draugr` rola a reserva com o nome de um inimigo (o mesmo para `track tick` com um contador, `quest done` com uma missão e `visit` com um lugar).

## Oráculos, geradores e personagens

```
didact ask 'Is the ferryman home?' --odds likely        # #o3 ? … → Yes, but…
didact interpret o3 'Home, but drunk and grieving.'     # what it meant, kept with it
didact meaning                                          # two words to interpret: betray · oath
didact gen run pointcrawl --prefill '{"terrain": "Swamp"}' --auto   # a draft: #g4
didact gen edit g4 poi-1.name='Amber Grave'
didact gen commit g4
didact char new                                         # guided: answer with `char choose c5 …`
didact char back c5                                     # take the last answer back: ask it again
didact char new --mode random --prefill '{"name": "Wren", "background": "Cutpurse"}'
didact char advance wren                                # the system's level-up, step by step (#c6)
didact world new fenmoor --system my-system --gen <generator> --prefill '{…}'
```

Nada do que um gerador ou a criação produz é salvo antes do `commit`. Descreva em `--prefill` o que o jogador quer, e o procedimento preenche as lacunas. Uma pergunta lista o que cada opção significa quando o pacote diz (`- Cutpurse: …`): conte ao jogador, para que ele escolha sabendo o que vai receber.

## Segredos

Por padrão, as visões são seguras para os jogadores: `show`, `find`, `sheet`, `map`, `brief`. Elas deixam de fora:
- fichas secretas (`knowledge: secret`);
- as seções `## Secrets` e `## GM notes`;
- campos `secret: true`.

`--gm` mostra tudo. Quando os jogadores descobrem algo:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` grava o que os jogadores sabem como um pequeno site para compartilhar ou ler no celular: o grupo, uma página por ficha, o diário e o mapa. Ele é sempre seguro para os jogadores, e exportar de novo para essa pasta o atualiza. `didact export --as lonelog` grava o diário em notação Lonelog (`@ ? d: -> =>`, cenas como `S1`, tags como `[N:Sweeney]`), também seguro para os jogadores.

## Lore: o que volta quando algo é mencionado

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **O que conta:** cada PdM, lugar, item e facção é uma carta cujas chaves são o nome e os apelidos. As entradas de lore têm `keys`, e as decisões aparecem por meio da regra delas. A correspondência é por palavras inteiras, e plurais contam (“wolves” corresponde a `wolf`).
- **Quando a lore aparece:** o hook do Claude Code analisa cada mensagem do jogador. `log`, `scene new` e `show` também trazem a lore recém-ativada, e uma entrada não se repete por alguns turnos.
- **Ajustando uma entrada:** `--secondary` com `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (em turnos ou cenas), `--constant` (sempre no resumo) e `--no-recurse`.
- **Escopos:** as entradas vão para a campanha, a menos que `--scope` diga world, system ou global. Uma análise só vê esta campanha, o mundo dela, o sistema dela e o global, nunca outro mundo. Uma entrada mais restrita com o mesmo id se sobrepõe a uma mais ampla.
- **Lorebooks de outras ferramentas:** `didact lore import <file>` lê World Info do SillyTavern (o do KoboldAI também), o lorebook de um cartão de personagem e o `.lorebook` do NovelAI; `didact lore export --to <file>` grava World Info. Chaves, lógica, prioridade, probabilidade, grupos e tempos são mantidos.

## Mudando a história

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` muda o fato, mas guarda o valor antigo. Também marca como desatualizados os resumos que mencionam o Sweeney, e `audit` os lista.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` registra uma decisão. Ela então aparece em `rules lookup` e quando essa regra é executada.
- `didact name npc` rola um nome novo, nunca um que o mundo já use. Antes de inventar um, confira com `didact names check <name>`. `didact names forget <name>` libera um de novo.

## Manutenção

- `didact history --clear` mostra o que limpar o histórico antigo descartaria; `--yes` o descarta de vez, incluindo fichas excluídas, e desfazer, `diff`, `rewind` e pontos de salvamento mais antigos não o alcançam mais (`--before e120` mantém esse evento e os seguintes, `--rolls` descarta também o registro dos dados). Execute `didact snapshot` antes.
- `didact save --remove 'before the dragon'` remove um ponto de salvamento; `didact undo` o traz de volta.
- `didact transcript 3 --clear` exclui a transcrição da sessão 3 (`--clear --all`: a de todas as sessões). `didact undo` a traz de volta, e o texto continua no histórico até `history --clear`.
- `didact compendium remove <entry>` exclui uma entrada que você adicionou; as fichas criadas a partir dela continuam.
- `didact snapshot --keep 3` exclui todos os backups, menos os três mais recentes, e `didact snapshot --remove <name>` exclui um. Nenhum dos dois pode ser desfeito.
- `didact session end` faz sozinho um backup da biblioteca (`snapshot-<time>-auto.zip`), mantendo os cinco mais recentes desses; `didact snapshot --list` os marca.
- `didact reset` mostra o que esvaziar a biblioteca levaria; `--yes` a deixa como recém-instalada: todos os mundos, campanhas e fichas, o histórico e o índice de busca somem, e a próxima mudança volta a ser #e1. Antes, ele faz um backup da biblioteca (`…-before-reset.zip`), e os backups continuam, assim como os pacotes instalados, a menos que você use `--packs`. Para experimentar o Didact em uma campanha pronta, `didact sample` monta a campanha de exemplo em uma biblioteca vazia (`--home` dá a ela uma pasta própria), e `didact serve --demo` a serve do zero.
- `didact snapshot --restore <name>` mostra o que um backup contém ao lado da biblioteca atual; `--yes` faz um backup da biblioteca como ela está (`…-before-restore.zip`) e depois coloca o backup no lugar dela. Os números de eventos e rolagens continuam. Desfazer não reverte uma restauração: restaurar esse backup de segurança, sim.
