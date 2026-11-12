<!-- translated from 5a088227a31a -->
# A aplicação no navegador

`didact serve` abre a tua biblioteca num navegador web: explora e edita fichas, vê num grafo como se ligam, lê o diário, executa regras e tabelas, e usa qualquer comando a partir de um formulário.

```
didact serve                     # http://127.0.0.1:8765/ until Ctrl-C
didact serve --open              # and open it in a browser tab
didact serve --gm                # start with the GM view on
didact serve --port 9000
didact serve --campaign withering --home ~/OtherLibrary
didact serve --demo              # a fresh sample campaign to try things on
```

Funciona sem ligação à internet: os tipos de letra e os ícones vêm com o Didact.

**Modo de demonstração.** `--demo` serve a campanha de exemplo (`didact sample`: um vale fluvial, uma PJ, pessoas com as notas do Mestre, lugares e caminhos, uma missão, um relógio e uma sessão a decorrer com um combate) a partir de uma biblioteca própria, ao lado da pasta de cache do Didact. Lá estão instalados todos os pacotes que vêm com o Didact. É construída de raiz sempre que `--demo` arranca, por isso experimenta à vontade: a tua biblioteca não é tocada.

## Opções

| Opção | Por omissão | O que faz |
|---|---|---|
| `--port <n>` | 8765 | a porta onde fica à escuta |
| `--host <address>` | 127.0.0.1 | o endereço onde fica à escuta: só este computador |
| `--open` | desligada | abre a aplicação num separador do navegador |
| `--gm` | desligada | começa com a vista de Mestre ligada |
| `--demo` | desligada | serve uma campanha de exemplo nova em vez da tua biblioteca |

As opções globais `--home`, `--world` e `--campaign` aplicam-se a tudo o que a aplicação faz. Abrir outro mundo ou outra campanha na página Biblioteca da aplicação muda para esse mundo ou campanha, tal como `didact world use` e `didact campaign open`, e Fechar põe de lado a campanha aberta (`didact campaign close`).

## O que tem

- **Visão geral:** o resumo (mundo, campanha, sessão, cena, grupo, o que está pendente), ações rápidas (lançar dados, consultar o oráculo com as probabilidades que conhece, registar um acontecimento, começar ou terminar uma sessão, uma ficha nova) e as últimas alterações.
- **Estado:** o ponto da situação, num relance: a sessão e a cena, a hora e os próximos lembretes, os números de cada membro do grupo e o que leva consigo, o combate (de quem é a vez, condições), as missões e os contadores em aberto, e onde está o grupo e as suas saídas. Os números podem ajustar-se ali mesmo: − e + num atributo, marcar um contador, usar ou largar um objeto, acrescentar um, concluir uma missão, avançar o tempo (um número e uma unidade que o calendário conheça: horas, turnos de vigia, dias, …), definir um lembrete (uma vez, ou periodicamente) e cancelar um.
- **Fichas:** todas as fichas, agrupadas por tipo, com uma caixa de filtro e os botões todas, mundo ou campanha. A página de uma ficha mostra a sua folha, a descrição, os detalhes, os campos, o conteúdo, as ligações nos dois sentidos, a crónica e o histórico, com formulários para alterar cada um deles, e para a arquivar ou eliminar. Uma personagem cujo sistema tem subida de nível tem um botão Level up (`char advance`): um rascunho que mostra o que muda, antes e depois, até ser confirmado.
- **Rascunhos:** criação de personagens e geradores, um passo de cada vez. Criar uma personagem (passo a passo ou ao acaso, escolhendo de que tipo quando o sistema tem vários: uma personagem jogadora, um contratado, …) e Gerar… estão nas páginas Fichas; os rascunhos em espera estão listados aí e na Visão geral. A página de um rascunho mostra o que já contém (as suas entidades e os respetivos campos, o mapa que um gerador desenhou, os lançamentos, as indicações do livro) e a pergunta por que espera. Cada opção é um botão que diz o que significa quando o pacote o diz (o que um antecedente dá, o que um talento faz); escolher várias é uma caixa a marcar para cada uma; os valores comprados com um orçamento são números que contam os pontos à medida que avanças; um nome ou outra resposta aberta pode ser escrito; e Deixar os dados decidir lança só essa (`char roll c3 --one`). Voltar desfaz o último passo, por isso a sua pergunta volta a aparecer (`char back c3`: os lançamentos que fez são marcados como anulados, e Anular traz o passo de volta). Depois, Lançar o resto, Editar, Descartar… (pergunta antes) e Confirmar, que abre a ficha da nova personagem, ou lista o que o gerador criou. O rascunho de um gerador é do Mestre: a vista de jogador só mostra que ele existe.
- **Grafo:** as fichas como nós e as ligações como arestas. Arrasta os nós, arrasta o fundo para deslocar a vista, faz zoom com a roda do rato; passa o cursor para iluminar os vizinhos de uma ficha; clica para abrir uma. O botão Grafo na página de uma ficha mostra só a sua vizinhança.
  - **Mapa** (o interruptor por cima do grafo, ou Abrir o mapa no Estado): os lugares que o grupo conhece, os caminhos entre eles (com rótulos: estrada, trilho, …), a região onde cada um fica (tracejada) e onde está o grupo. Um caminho para um lugar ainda por descobrir leva a um «?»; a vista de Mestre mostra todos os lugares.
- **Diário:** as sessões, cada uma a abrir-se nas suas cenas, acontecimentos e lançamentos. Cada acontecimento tem Editar e Remover (passa o cursor por cima), que abrem os formulários `beat edit` e `beat rm`.
- **Referência:** pesquisa tudo (os resultados aparecem enquanto escreves), executa as regras dos pacotes ativados a partir de formulários, lança as suas tabelas e lê o texto das regras, o glossário e os guias.
- **Biblioteca:** mundos e campanhas (abrir, fechar, criar, eliminar), pacotes (cada um com o que é; ativar, desativar, instalar, desinstalar; os pacotes que vêm com o Didact têm um botão Instalar), o histórico (Anular, Refazer, Retroceder, Limpar), pontos de gravação (recuar, remover) e cópias de segurança (fazer agora, restaurar, eliminar, manter as mais recentes; as feitas ao terminar uma sessão estão marcadas como auto). Sem nenhuma campanha aberta, a Visão geral lista as campanhas do mundo para abrir uma.
  - Eliminar um mundo ou uma campanha pede confirmação primeiro, e Anular traz tudo de volta.
  - Retroceder (ao lado de cada alteração) desfaz tudo o que veio depois dessa alteração (`didact undo --to e40`): a sua página mostra primeiro o que desaparece. Cada alteração é anulada e cada lançamento marcado como anulado, não eliminado: Refazer, ou retroceder até uma alteração posterior, trá-los de volta. Mostrar alterações mais antigas lista mais do histórico.
  - O pacote core está sempre ativo. Só se usa um sistema de jogo de cada vez: o do mundo aberto, que o mantém para sempre (escolhido quando o mundo é criado). Outro sistema joga-se num mundo próprio: a sua linha abre um mundo que se joga com ele, ou cria um novo. Desinstalar um pacote não se pode anular: volta a instalar o seu .didactpack.
  - Limpar o histórico mostra primeiro exatamente o que desaparece e o que deixa de funcionar, com um botão para fazer uma cópia de segurança antes. Não se pode anular, e eliminar uma cópia de segurança também não.
  - Recomeçar: **Repor…** esvazia a biblioteca, como se o Didact tivesse acabado de ser instalado, e a numeração recomeça em #e1. A sua página mostra primeiro o que desaparece. Antes é feita uma cópia de segurança da biblioteca, e as cópias de segurança ficam (os pacotes instalados também, a menos que marques a caixa).
  - Restaurar uma cópia de segurança mostra primeiro o que ela contém ao lado da biblioteca atual. Antes é feita uma cópia de segurança da biblioteca tal como estava: Anular não desfaz um restauro, mas restaurar essa cópia de segurança, sim.
- **Comandos:** cada comando como formulário, e uma caixa que aceita uma linha de comando inteira. Cada caixa aceita o que o seu argumento aceita: um número, um id ou um evento (`e12`) segundo o seu padrão, uma quantidade de tempo de jogo como um número e uma unidade, e uma lista para escolher entre as fichas, rascunhos, pacotes, pontos de gravação, oráculos, tabelas e regras daqui.
- **Definições:** as opções da campanha (as variantes e regras opcionais do seu sistema, que as regras, a criação de personagens e os geradores seguem; cada uma diz o que faz: uma regra opcional, o que muda ao ligá-la; uma escolha, o que significa cada um dos seus valores; e um valor predefinido que outra opção define diz qual), o idioma da aplicação, o dicionário de sinónimos (o idioma que as pesquisas usam para os sinónimos: transferir um, com uma barra de progresso, alternar entre os transferidos, remover um) e a documentação do código.
  - A aplicação, os seus guias e o que os comandos mostram nela existem em 24 idiomas. Sem escolha feita, a aplicação segue o idioma do navegador. A linha de comandos e os LLM que a usam continuam em inglês: o idioma escolhido aqui é só o da aplicação.
  - O botão do código na barra do cabeçalho abre a documentação da API do código. É gerada a partir do código da primeira vez, e de novo sempre que o código muda (`didact docs build`).

Cada alteração executa um verdadeiro comando `didact`, por isso é verificada, registada e pode ser anulada exatamente como na linha de comandos. A aplicação mostra sempre o comando que executou (`didact set sweeney hp-=2`), com um botão Anular quando há algo a desfazer.

Uma caixa só aceita o que o seu comando aceita. Um id (de um mundo ou de uma campanha) e um tipo de ficha aceitam letras minúsculas, algarismos e hífenes: os espaços passam a hífenes e as maiúsculas passam a minúsculas à medida que escreves. O nome de um campo não aceita espaços (passam a sublinhados), o nome de um detalhe é uma só palavra, e as caixas de números só aceitam números. O que uma caixa aceita está escrito por baixo dela, e o comando volta a verificar de qualquer forma.

Guardar nunca sobrescreve uma alteração que não viste. Se a ficha mudou depois de a página a mostrar (um LLM alterou-a a partir da linha de comandos, por exemplo, ou outro separador), a gravação é recusada e diz o que lá está agora. Uma descrição que estavas a editar fica no editor, ao lado da nova versão, para juntares as duas e voltares a guardar. − e + passam sempre: somam-se.

## Vista de jogador e vista de Mestre

A aplicação mostra o que os jogadores sabem, tal como `didact show`: as fichas secretas, as secções `## Secrets`, os campos secretos e os detalhes só para o Mestre ficam de fora. O botão **GM** na barra do cabeçalho liga a vista de Mestre, e uma faixa avisa disso («Vista de Mestre: spoilers visíveis»). O navegador lembra-se da escolha.

Na vista de jogador:
- uma descrição com linhas só para o Mestre não pode ser editada (guardá-la perdê-las-ia): liga primeiro a vista de Mestre;
- um detalhe do Mestre ou um campo secreto que a página não mostra não pode ser sobrescrito, embora se possa acrescentar uma nota nova para o Mestre;
- o histórico indica o comando e as fichas que os jogadores conhecem (`set · Freya`), nunca os valores, e Anular diz que alteração desfez, não qual era.

## Segurança

A aplicação pode alterar a tua biblioteca, por isso, por omissão, só aceita ligações deste computador.

- `--host` com outro endereço deixa outras máquinas chegar-lhe, e o Didact avisa disso. Usa-o só numa rede em que confies.
- Só responde a pedidos dirigidos a ela própria (o seu próprio endereço, `localhost`, `127.0.0.1` ou `[::1]`, com a sua porta). Isso impede que outros sites lhe cheguem através de truques de DNS.
- Cada alteração precisa de um formulário da própria aplicação: um token secreto em cada formulário tem de corresponder a um cookie que outros sites não conseguem ler nem enviar.
- Não há início de sessão. Qualquer pessoa que possa usar o navegador deste computador pode usar a aplicação.
