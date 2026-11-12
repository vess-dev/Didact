<!-- translated from 5a088227a31a -->
# O aplicativo no navegador

`didact serve` abre sua biblioteca em um navegador: explore e edite fichas, veja em um grafo como elas se vinculam, leia o diário, execute regras e tabelas, e use qualquer comando a partir de um formulário.

```
didact serve                     # http://127.0.0.1:8765/ until Ctrl-C
didact serve --open              # and open it in a browser tab
didact serve --gm                # start with the GM view on
didact serve --port 9000
didact serve --campaign withering --home ~/OtherLibrary
didact serve --demo              # a fresh sample campaign to try things on
```

Funciona offline: as fontes e os ícones vêm com o Didact.

**Modo demo.** `--demo` serve a campanha de exemplo (`didact sample`: um vale de rio, um PJ, pessoas com as anotações do Mestre, lugares e caminhos, uma missão, um relógio e uma sessão em andamento com um combate) a partir de uma biblioteca própria, ao lado da pasta de cache do Didact. Lá estão instalados todos os pacotes que vêm com o Didact. Ela é montada do zero toda vez que `--demo` inicia, então experimente o que quiser: sua biblioteca não é tocada.

## Opções

| Opção | Padrão | O que faz |
|---|---|---|
| `--port <n>` | 8765 | a porta em que escuta |
| `--host <address>` | 127.0.0.1 | o endereço em que escuta: só esta máquina |
| `--open` | desligada | abre o aplicativo em uma aba do navegador |
| `--gm` | desligada | começa com a visão do Mestre ligada |
| `--demo` | desligada | serve uma campanha de exemplo nova em vez da sua biblioteca |

As opções globais `--home`, `--world` e `--campaign` valem para tudo o que o aplicativo faz. Abrir outro mundo ou outra campanha na página Biblioteca do aplicativo troca para esse mundo ou campanha, como fazem `didact world use` e `didact campaign open`, e Fechar deixa de lado a campanha aberta (`didact campaign close`).

## O que tem nele

- **Visão geral:** o resumo (mundo, campanha, sessão, cena, grupo, o que está pendente), ações rápidas (rolar dados, consultar o oráculo com as chances que ele conhece, registrar um acontecimento, iniciar ou encerrar uma sessão, uma nova ficha) e as últimas mudanças.
- **Status:** a situação atual, em um relance: a sessão e a cena, a hora e os próximos lembretes, os números de cada membro do grupo e o que ele carrega, o combate (de quem é a vez, condições), as missões e os contadores abertos, e onde o grupo está, com suas saídas. Os números podem ser ajustados ali mesmo: − e + em um atributo, marcar um contador, usar ou largar um item, adicionar um, concluir uma missão, avançar o tempo (um número e uma unidade que o calendário conhece: horas, vigias, dias, …), definir um lembrete (uma vez, ou periodicamente) e cancelar um.
- **Fichas:** todas as fichas, agrupadas por tipo, com uma caixa de filtro e os botões todas, mundo ou campanha. A página de uma ficha mostra a folha, a descrição, os detalhes, os campos, o conteúdo, os vínculos nos dois sentidos, a crônica e o histórico dela, com formulários para mudar cada um deles, e para arquivá-la ou excluí-la. Um personagem cujo sistema tem subida de nível tem um botão Level up (`char advance`): um rascunho que mostra o que muda, antes e depois, até ser confirmado.
- **Rascunhos:** criação de personagens e geradores, um passo de cada vez. Criar um personagem (passo a passo ou aleatoriamente, escolhendo qual tipo quando o sistema tem vários: um personagem de jogador, um contratado, …) e Gerar… ficam nas páginas Fichas; os rascunhos pendentes são listados ali e na Visão geral. A página de um rascunho mostra o que ele já tem (suas entidades e os campos delas, o mapa que um gerador desenhou, as rolagens, as instruções do livro) e a pergunta que ele aguarda. Cada opção é um botão que diz o que ela significa quando o pacote diz (o que um antecedente dá, o que um talento faz); escolher várias é uma caixa para marcar em cada uma; valores comprados com um orçamento são números que contam os pontos conforme você avança; um nome ou outra resposta aberta pode ser digitado; e Deixar os dados decidirem rola só essa (`char roll c3 --one`). Voltar desfaz o último passo, então a pergunta dele aparece de novo (`char back c3`: as rolagens que ele fez são marcadas como desfeitas, e Desfazer traz o passo de volta). Depois vêm Rolar o resto, Editar, Descartar… (pergunta antes) e Confirmar, que abre a ficha do novo personagem, ou lista o que o gerador criou. O rascunho de um gerador é do Mestre: a visão dos jogadores só mostra que ele existe.
- **Grafo:** fichas como nós e vínculos como arestas. Arraste os nós, arraste o fundo para mover a visão, dê zoom com a roda do mouse; passe o mouse para destacar os vizinhos de uma ficha; clique para abrir uma. O botão Grafo na página de uma ficha mostra só a vizinhança dela.
  - **Mapa** (a chave acima do grafo, ou Abrir o mapa em Status): os lugares que o grupo conhece, os caminhos entre eles (com rótulos: estrada, trilha, …), a região onde cada um fica (tracejada) e onde o grupo está. Um caminho para um lugar ainda não descoberto leva a um “?”; a visão do Mestre mostra todos os lugares.
- **Diário:** as sessões, cada uma se abrindo em suas cenas, acontecimentos e rolagens. Cada acontecimento tem Editar e Remover (passe o mouse sobre ele), que abrem os formulários `beat edit` e `beat rm`.
- **Referência:** busque em tudo (os resultados aparecem enquanto você digita), execute as regras dos pacotes ativados a partir de formulários, role as tabelas deles e leia o texto das regras, o glossário e os guias.
- **Biblioteca:** mundos e campanhas (abrir, fechar, criar, excluir), pacotes (cada um com o que ele é; ativar, desativar, instalar, desinstalar; os pacotes que vêm com o Didact têm um botão Instalar), o histórico (Desfazer, Refazer, Retroceder, Limpar), pontos de salvamento (voltar no tempo, remover) e backups (fazer agora, restaurar, excluir, manter os mais recentes; os feitos ao encerrar uma sessão são marcados como auto). Sem campanha aberta, a Visão geral lista as campanhas do mundo para você abrir uma.
  - Excluir um mundo ou uma campanha pede confirmação antes, e Desfazer traz tudo de volta.
  - Retroceder (ao lado de cada alteração) desfaz tudo o que veio depois dessa alteração (`didact undo --to e40`): a página dele mostra antes o que some. Cada alteração é desfeita e cada rolagem marcada como desfeita, não excluída: Refazer, ou retroceder até uma alteração posterior, traz tudo de volta. Mostrar alterações mais antigas lista mais do histórico.
  - O pacote core está sempre ativo. Só um sistema de jogo é usado por vez: o do mundo aberto, que o mantém para sempre (escolhido quando o mundo é criado). Outro sistema é jogado num mundo próprio: a linha dele abre um mundo em que ele é jogado, ou cria um novo. Desinstalar um pacote não pode ser desfeito: instale o .didactpack dele de novo.
  - Limpar o histórico mostra antes exatamente o que some e o que para de funcionar, com um botão para fazer um backup antes. Isso não pode ser desfeito, nem excluir um backup.
  - Recomeçar: **Redefinir…** esvazia a biblioteca, como se o Didact tivesse acabado de ser instalado, e a numeração recomeça em #e1. A página dele mostra antes o que some. Antes é feito um backup da biblioteca, e os backups continuam (os pacotes instalados também, a menos que você marque a caixa).
  - Restaurar um backup mostra antes o que ele contém ao lado da biblioteca atual. Antes é feito um backup da biblioteca como ela estava: Desfazer não reverte uma restauração, mas restaurar esse backup, sim.
- **Comandos:** cada comando como um formulário, e uma caixa que aceita uma linha de comando inteira. Cada caixa aceita o que o argumento dela aceita: um número, um id ou um evento (`e12`) pelo padrão dele, uma quantidade de tempo de jogo como um número e uma unidade, e uma lista para escolher entre as fichas, rascunhos, pacotes, pontos de salvamento, oráculos, tabelas e regras daqui.
- **Configurações:** as opções da campanha (as variantes e regras opcionais do sistema dela, que as regras, a criação de personagens e os geradores seguem; cada uma diz o que faz: uma regra opcional, o que muda ao ligá-la; uma escolha, o que significa cada um dos valores dela; e um padrão definido por outra opção diz qual), o idioma do aplicativo, o dicionário de sinônimos (o idioma que as buscas usam para os sinônimos: baixar um, com uma barra de progresso, alternar entre os baixados, remover um) e a documentação do código.
  - O aplicativo, seus guias e o que os comandos exibem nele estão disponíveis em 24 idiomas. Sem uma escolha, o aplicativo segue o idioma do navegador. A linha de comando e os LLMs que a usam continuam em inglês: o idioma escolhido aqui vale só para o app.
  - O botão de código na barra do cabeçalho abre a documentação da API do código. Ela é gerada a partir do código na primeira vez, e de novo sempre que o código muda (`didact docs build`).

Toda mudança executa um comando `didact` de verdade, então ela é verificada, registrada e pode ser desfeita exatamente como na linha de comando. O aplicativo mostra o comando que executou a cada vez (`didact set sweeney hp-=2`), com um botão Desfazer quando há algo para desfazer.

Uma caixa só aceita o que o comando dela aceita. Um id (de um mundo ou de uma campanha) e um tipo de ficha aceitam letras minúsculas, dígitos e hífens: espaços viram hífens e maiúsculas viram minúsculas enquanto você digita. O nome de um campo não aceita espaços (eles viram sublinhados), o nome de um detalhe é uma só palavra, e caixas de números só aceitam números. O que uma caixa aceita fica escrito embaixo dela, e o comando verifica de novo de qualquer forma.

Salvar nunca sobrescreve uma mudança que você não viu. Se a ficha mudou depois que a página a mostrou (um LLM a alterou pela linha de comando, por exemplo, ou outra aba), o salvamento é recusado e diz o que está lá agora. Uma descrição que você estava editando continua no editor, ao lado da nova versão, para você mesclar e salvar de novo. − e + sempre passam: eles se somam.

## Visão dos jogadores e visão do Mestre

O aplicativo mostra o que os jogadores sabem, como `didact show`: fichas secretas, seções `## Secrets`, campos secretos e detalhes só do Mestre ficam de fora. O botão **GM** na barra do cabeçalho liga a visão do Mestre, e uma faixa avisa (“Visão do Mestre: spoilers visíveis”). O navegador lembra a escolha.

Na visão dos jogadores:
- uma descrição com linhas só do Mestre não pode ser editada (salvá-la as perderia): ligue a visão do Mestre antes;
- um detalhe do Mestre ou um campo secreto que a página não mostra não pode ser sobrescrito, embora seja possível adicionar uma nova anotação para o Mestre;
- o histórico cita o comando e as fichas que os jogadores conhecem (`set · Freya`), nunca os valores, e Desfazer diz qual mudança desfez, não o que ela era.

## Segurança

O aplicativo pode mudar sua biblioteca, então, por padrão, ele só escuta esta máquina.

- `--host` com outro endereço permite que outras máquinas o acessem, e o Didact avisa sobre isso. Use só em uma rede em que você confia.
- Ele só responde a requisições endereçadas a ele mesmo (o próprio endereço, `localhost`, `127.0.0.1` ou `[::1]`, com a porta dele). Isso impede que outros sites o alcancem com truques de DNS.
- Toda mudança exige um formulário do próprio aplicativo: um token secreto em cada formulário precisa corresponder a um cookie que outros sites não conseguem ler nem enviar.
- Não há login. Qualquer pessoa que possa usar o navegador deste computador pode usar o aplicativo.
