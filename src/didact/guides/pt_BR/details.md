<!-- translated from 7fe144069f94 -->
# Detalhes, a crônica e o paradeiro

As anotações do Mestre que mantêm um jogo coerente: a aparência das coisas e o que elas querem, o que estão fazendo e o que planejam a seguir, o que aconteceu com elas e onde tudo está.

## Detalhes

Notas curtas, com nome, em qualquer ficha: uma pessoa, um item, um lugar, uma facção.

```
didact about sweeney looks='tall, one eye clouded' personality='jovial, greedy'
didact about sweeney wants='buy back the mill' plan='sell the route to the raiders'
didact about sweeney doing='whittling by the fire' where='the back room of the inn'
didact about item:old-sword history='forged for the last king' powers='cuts through wards'
didact about loc:the-ford state='flooded' secret='a drowned shrine under the stones'
didact about sweeney thoughts='built to foreshadow the betrayal; pay it off at the ford'
didact about sweeney                  # the notes, what's still open, chronicle, whereabouts
didact about sweeney --clear doing    # or doing='' 
```

- **Nomes.** Os sugeridos dependem do tipo de ficha, e qualquer nome de uma palavra serve:
  - pessoas: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - itens: looks, history, where, powers, secret, thoughts;
  - lugares: looks, state, history, secret, thoughts;
  - grupos: wants, plan, state, history, secret, thoughts.

  Um pacote pode sugerir os seus para cada tipo (`details: [mood, grudge]` em um esquema).
- **Quem vê o quê.** Os jogadores só veem `looks`: `show` e `find` deixam o resto de fora, e `--gm` mostra tudo. Quando os jogadores descobrem um, `didact reveal sweeney plan` o move para o texto da ficha, em `## Revealed`.
- **`thoughts`** são seus: por que você criou aquilo, aonde pode levar, o que retomar mais tarde.
- **Mantenha tudo atualizado.** Você não precisa anotar tudo. Mas, quando decidir algo (um plano, um rancor, para onde alguém foi), escreva, para que a próxima cena, ou a próxima sessão, seja fiel a isso.

## A crônica: o que aconteceu com quem

Um acontecimento do diário pode citar as fichas a que se refere. Ele passa então a aparecer em cada uma delas.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` e `about` listam a crônica de uma ficha: o que ela fez e o que fizeram com ela.
- **Acontecimentos secretos** ocorrem longe da vista dos jogadores. Eles só aparecem nas visões do Mestre (`session show --gm`, `about`, `brief --gm`) e nunca em `export --as story`.
- Use `--about` para tudo o que muda alguém ou alguma coisa: uma traição, uma dívida, uma morte, um presente, uma promessa quebrada.
- **Corrigir um acontecimento:** `didact beat edit S1.4 --about tom` o coloca na crônica do Tom (ou `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), e `didact beat rm S1.4` o remove. Os ids estão em `session show`, e os dois podem ser desfeitos.
- **Quando os ids mudam:** um `merge` ou um novo slug leva junto todas as referências: vínculos, detalhes, as fichas a que os acontecimentos se referem, o grupo, o combate e a localização do grupo. Quando uma ficha é excluída com `rm`, ela também sai de qualquer grupo ou combate. Um `merge` entre tipos mantém aquilo para que a folha da ficha que fica tem campo, e diz o que deixa de fora.

## O paradeiro: onde as coisas estão

Os itens ficam em inventários, e qualquer coisa pode guardá-los: um personagem, um lugar, um baú.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Durante uma sessão, mover um item registra um acontecimento sobre quem dá e quem recebe (“Sword: Freya → Chest”). As crônicas deles passam a dizer para onde as coisas foram.
- **Pessoas e monstros** são visitantes dos lugares, não o conteúdo deles: registre onde estão no detalhe `where`.

## Em cenas e combates

- **`combat status --gm`** mostra o `where`, o `doing` e o `plan` de cada combatente. Atualize-os conforme o combate avança: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (o resumo com que uma sessão começa) lista o que está em jogo (o lugar, os combatentes, aqueles a quem os acontecimentos desta cena se referem, e o grupo) com where, doing, plan e state. Também lista os últimos acontecimentos fora de cena.
