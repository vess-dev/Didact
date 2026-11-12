<!-- translated from 7fe144069f94 -->
# Detalhes, a crónica e o paradeiro

As notas do Mestre que mantêm um jogo coerente: o aspeto das coisas e o que querem, o que estão a fazer e o que planeiam a seguir, o que lhes aconteceu e onde está tudo.

## Detalhes

Notas curtas, com nome, em qualquer ficha: uma pessoa, um objeto, um lugar, uma fação.

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
  - objetos: looks, history, where, powers, secret, thoughts;
  - lugares: looks, state, history, secret, thoughts;
  - grupos: wants, plan, state, history, secret, thoughts.

  Um pacote pode sugerir os seus próprios para cada tipo (`details: [mood, grudge]` num esquema).
- **Quem vê o quê.** Os jogadores só veem `looks`: `show` e `find` omitem o resto, e `--gm` mostra tudo. Quando os jogadores descobrem um, `didact reveal sweeney plan` passa-o para o texto da ficha, em `## Revealed`.
- **`thoughts`** são teus: porque o criaste, onde pode levar, o que retomar mais tarde.
- **Mantém-nos atualizados.** Não tens de anotar tudo. Mas quando decides algo (um plano, um rancor, para onde alguém foi), escreve-o, para que a cena seguinte, ou a sessão seguinte, lhe seja fiel.

## A crónica: o que aconteceu a quem

Um acontecimento do diário pode nomear as fichas a que diz respeito. Passa então a aparecer em cada uma delas.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` e `about` listam a crónica de uma ficha: o que fez e o que lhe fizeram.
- **Os acontecimentos secretos** passam-se longe da vista dos jogadores. Só aparecem nas vistas de Mestre (`session show --gm`, `about`, `brief --gm`) e nunca em `export --as story`.
- Usa `--about` para tudo o que muda alguém ou alguma coisa: uma traição, uma dívida, uma morte, uma oferta, uma promessa quebrada.
- **Corrigir um acontecimento:** `didact beat edit S1.4 --about tom` põe-no na crónica do Tom (ou `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), e `didact beat rm S1.4` remove-o. Os ids estão em `session show`, e ambos se podem anular.
- **Quando os ids mudam:** um `merge` ou um novo slug leva consigo todas as referências: ligações, detalhes, as fichas de que os acontecimentos falam, o grupo, o combate e a localização do grupo. Quando uma ficha é eliminada com `rm`, sai também de qualquer grupo ou combate. Um `merge` entre tipos guarda aquilo para que a folha da ficha que fica tem campo, e diz o que deixa de fora.

## O paradeiro: onde estão as coisas

Os objetos vivem em inventários, e qualquer coisa os pode guardar: uma personagem, um lugar, um baú.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Durante uma sessão, mover um objeto regista um acontecimento sobre quem dá e quem recebe («Sword: Freya → Chest»). As suas crónicas passam a dizer para onde foram as coisas.
- **Pessoas e monstros** são visitantes dos lugares, não o seu conteúdo: guarda onde estão no detalhe `where`.

## Em cenas e combates

- **`combat status --gm`** mostra o `where`, o `doing` e o `plan` de cada combatente. Atualiza-os à medida que o combate avança: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (o resumo com que uma sessão começa) lista o que está em jogo (o lugar, os combatentes, aqueles de quem falam os acontecimentos desta cena, e o grupo) com where, doing, plan e state. Lista também os últimos acontecimentos fora de cena.
