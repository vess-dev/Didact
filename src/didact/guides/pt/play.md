<!-- translated from bef7b2c650cb -->
# Jogar uma sessão

Como decorre um jogo com o Didact: o LLM narra, e o Didact guarda cada facto, cada lançamento e cada alteração.

## Antes da primeira sessão

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

Um mundo mantém o sistema com que foi criado, e as suas campanhas jogam-se com ele: outro sistema joga-se num mundo próprio. `didact campaign close` põe uma campanha de lado (o seu mundo continua aberto) e `didact campaign open <id>` retoma-a onde ficou, com a sessão e tudo.

`didact world delete <id>` e `didact campaign delete <id>` eliminam um mundo ou uma campanha, com pré-visualização primeiro; `--yes` elimina, e `didact undo` traz tudo de volta.

`session zero` lista as perguntas a acertar com o jogador. As do pacote vêm primeiro. Entre elas estão as opções do sistema (as suas variantes e regras opcionais): as suas regras seguem as respostas, e o resumo diz o que significa cada opção alterada. Todos os resumos levam as respostas.

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

- **Turnos:** cada mensagem do jogador abre um turno (o hook do Claude Code chama `didact capture`, e os outros clientes usam `turn begin`). `didact undo --turn` anula tudo o que foi feito para essa mensagem: alterações, acontecimentos e lançamentos. A transcrição guarda-o.
- **Retroceder:** `didact undo --to e40` desfaz tudo o que veio depois de #e40, do mais recente para o mais antigo (`--dry-run` mostra a lista): cada alteração é anulada e cada lançamento marcado como anulado. Nada é eliminado: `redo`, ou retroceder até uma alteração posterior, traz tudo de volta.
- **Tempo:** `didact time advance 1 watch` esgota temporizadores, faz surgir os lembretes e executa os gatilhos de tempo. `didact remind --list` mostra os lembretes que aí vêm, e `didact remind --cancel 2` cancela um. Uma campanha começa no início do calendário, ou na data que `campaign new --date '4 July 1902'` indica, e `didact time set '<date>'` muda-a até à primeira sessão.
- **Lugares:** `didact visit <place>` move o grupo e marca o lugar como visitado. `didact map` mostra o que o grupo conhece, e uma saída por explorar é `?`.
- **Combates:** `didact combat start --party troll`, depois `combat next`, `combat hit freya troll weapon=d8` e `combat end`. Os combatentes entram e saem a meio do combate: `didact combat join wolf-2` (no modo individual lançam a iniciativa) e `didact combat leave troll --why fled`. Ninguém perde a vez.
- **Coisas:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (ou para um baú, ou para um lugar); `didact where rope` encontra-a. `inv add` encontra um objeto do compêndio pelo id, pelo nome ou por um alias.
- **As tuas notas:** `didact about sweeney plan='…' doing='…' where='…'` guarda o que decidiste sobre qualquer pessoa ou coisa. Os jogadores só veem `looks`. `didact log … --about sweeney` põe um acontecimento na ficha dele (`--secret` se os jogadores não o virem). Há mais em `didact guide details`.
- **O mundo segue em frente:** `didact faction turn`, e relógios: `didact track new 'The flood' --size 6`. Um comando que só aceita um tipo de ficha toma um nome que outras partilham como sendo desse tipo: `didact track roll draugr` lança a reserva com o nome de um inimigo (o mesmo para `track tick` com um contador, `quest done` com uma missão e `visit` com um lugar).

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

Nada do que um gerador ou a criação faz fica gravado até `commit`. Descreve em `--prefill` o que o jogador quer, e o procedimento preenche o resto. Uma pergunta lista o que significa cada opção quando o pacote o diz (`- Cutpurse: …`): di-lo ao jogador, para que escolha sabendo o que recebe.

## Segredos

Por omissão, as vistas são seguras para os jogadores: `show`, `find`, `sheet`, `map`, `brief`. Omitem:
- as fichas secretas (`knowledge: secret`);
- as secções `## Secrets` e `## GM notes`;
- os campos `secret: true`.

`--gm` mostra tudo. Quando os jogadores descobrem alguma coisa:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` escreve o que os jogadores sabem num pequeno site, para partilhar ou ler no telemóvel: o grupo, uma página por ficha, o diário e o mapa. É sempre seguro para os jogadores, e voltar a exportar para essa pasta atualiza-o. `didact export --as lonelog` escreve o diário em notação Lonelog (`@ ? d: -> =>`, cenas como `S1`, etiquetas como `[N:Sweeney]`), também seguro para os jogadores.

## Lore: o que volta quando algo é mencionado

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **O que conta:** cada NPC, lugar, objeto e fação é uma carta com o seu nome e aliases como chaves. As entradas de lore têm `keys`, e as decisões surgem através da sua regra. A correspondência é por palavras inteiras, e os plurais contam («wolves» corresponde a `wolf`).
- **Quando surge a lore:** o hook do Claude Code analisa cada mensagem do jogador. `log`, `scene new` e `show` também trazem a lore acabada de ativar, e uma entrada não se repete durante alguns turnos.
- **Afinar uma entrada:** `--secondary` com `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (em turnos ou cenas), `--constant` (sempre no resumo) e `--no-recurse`.
- **Âmbitos:** as entradas vão para a campanha, a menos que `--scope` diga world, system ou global. Uma análise só vê esta campanha, o seu mundo, o seu sistema e o global, nunca outro mundo. Uma entrada mais restrita com o mesmo id sobrepõe-se a uma mais ampla.
- **Lorebooks de outras ferramentas:** `didact lore import <file>` lê World Info do SillyTavern (também o do KoboldAI), o lorebook de um cartão de personagem e o `.lorebook` do NovelAI; `didact lore export --to <file>` escreve World Info. As chaves, a lógica, a prioridade, a probabilidade, os grupos e os tempos são mantidos.

## Mudar a história

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` muda o facto mas guarda o valor antigo. Marca também como desatualizados os resumos que mencionam o Sweeney, e `audit` lista-os.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` regista uma decisão. Passa então a aparecer em `rules lookup` e quando essa regra é executada.
- `didact name npc` lança um nome novo, nunca um que o mundo já use. Antes de inventares um, verifica-o com `didact names check <name>`. `didact names forget <name>` volta a libertá-lo.

## Arrumação

- `didact history --clear` mostra o que limpar o histórico antigo deitaria fora; `--yes` apaga-o de vez, incluindo as fichas eliminadas, e a anulação, o `diff`, o `rewind` e os pontos de gravação mais antigos deixam de lhe chegar (`--before e120` mantém esse evento e os seguintes, `--rolls` apaga também o registo dos dados). Executa `didact snapshot` antes.
- `didact save --remove 'before the dragon'` remove um ponto de gravação; `didact undo` trá-lo de volta.
- `didact transcript 3 --clear` elimina a transcrição da sessão 3 (`--clear --all`: a de todas as sessões). `didact undo` trá-la de volta, e o texto fica no histórico até `history --clear`.
- `didact compendium remove <entry>` elimina uma entrada que acrescentaste; as fichas criadas a partir dela ficam.
- `didact snapshot --keep 3` elimina todas as cópias de segurança exceto as três mais recentes, e `didact snapshot --remove <name>` elimina uma. Nenhum dos dois se pode anular.
- `didact session end` faz sozinho uma cópia de segurança da biblioteca (`snapshot-<time>-auto.zip`) e guarda as cinco mais recentes dessas; `didact snapshot --list` assinala-as.
- `didact reset` mostra o que esvaziar a biblioteca levaria; `--yes` deixa-a como acabada de instalar: todos os mundos, campanhas e fichas, o histórico e o índice de pesquisa desaparecem, e a alteração seguinte volta a ser #e1. Primeiro faz uma cópia de segurança da biblioteca (`…-before-reset.zip`), e as cópias de segurança ficam, tal como os pacotes instalados, a menos que uses `--packs`. Para experimentar o Didact numa campanha já pronta, `didact sample` constrói a campanha de exemplo numa biblioteca vazia (`--home` dá-lhe uma pasta própria), e `didact serve --demo` serve-a de raiz.
- `didact snapshot --restore <name>` mostra o que uma cópia de segurança contém ao lado da biblioteca atual; `--yes` faz uma cópia de segurança da biblioteca tal como está (`…-before-restore.zip`) e depois põe a cópia no seu lugar. Os números dos eventos e dos lançamentos continuam. A anulação não desfaz um restauro: restaurar essa cópia de segurança, sim.
