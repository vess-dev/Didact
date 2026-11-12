<!-- translated from 7fe144069f94 -->
# Detalles, la crónica y el paradero

Las notas del máster que mantienen coherente una partida: qué aspecto tienen las cosas y qué quieren, qué están haciendo y qué planean, qué les ha pasado y dónde está todo.

## Detalles

Notas breves con nombre en cualquier ficha: una persona, un objeto, un lugar, una facción.

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

- **Nombres.** Los sugeridos dependen del tipo de ficha, y sirve cualquier nombre de una sola palabra:
  - personas: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - objetos: looks, history, where, powers, secret, thoughts;
  - lugares: looks, state, history, secret, thoughts;
  - grupos: wants, plan, state, history, secret, thoughts.

  Un paquete puede sugerir los suyos para cada tipo (`details: [mood, grudge]` en un esquema).
- **Quién ve qué.** Los jugadores solo ven `looks`: `show` y `find` omiten el resto, y `--gm` lo muestra todo. Cuando los jugadores descubren uno, `didact reveal sweeney plan` lo pasa al texto de la ficha, bajo `## Revealed`.
- **`thoughts`** son tuyos: por qué lo creaste, adónde podría llevar, qué retomar más adelante.
- **Mantenlos al día.** No hace falta apuntarlo todo. Pero cuando decidas algo (un plan, un rencor, adónde fue alguien), apúntalo, para que la siguiente escena, o la siguiente sesión, sea fiel a ello.

## La crónica: qué le pasó a quién

Un evento del diario puede nombrar las fichas a las que se refiere. Entonces aparece en cada una de ellas.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` y `about` muestran la crónica de una ficha: lo que hizo y lo que le hicieron.
- **Los eventos secretos** ocurren fuera de la vista de los jugadores. Solo aparecen en las vistas de máster (`session show --gm`, `about`, `brief --gm`), y nunca en `export --as story`.
- Usa `--about` para todo lo que cambie a alguien o algo: una traición, una deuda, una muerte, un regalo, una promesa rota.
- **Corregir un evento:** `didact beat edit S1.4 --about tom` lo pone en la crónica de Tom (o `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), y `didact beat rm S1.4` lo elimina. Los ids están en `session show`, y los dos se pueden deshacer.
- **Cuando cambian los ids:** un `merge` o un slug nuevo arrastra consigo todas las referencias: enlaces, detalles, las fichas a las que se refieren los eventos, el grupo, el combate y la ubicación del grupo. Cuando se borra una ficha con `rm`, también sale de cualquier grupo o combate. Un `merge` entre tipos conserva aquello para lo que la hoja de la ficha que queda tiene campo, y dice lo que deja fuera.

## El paradero: dónde están las cosas

Los objetos viven en inventarios, y cualquier cosa puede tenerlos: un personaje, un lugar, un cofre.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Durante una sesión, mover un objeto registra un evento sobre quien lo da y quien lo recibe ("Sword: Freya → Chest"). Así sus crónicas cuentan adónde fueron las cosas.
- **Las personas y los monstruos** son visitantes de los lugares, no su contenido: guarda dónde están en su detalle `where`.

## En escenas y combates

- **`combat status --gm`** muestra el `where`, el `doing` y el `plan` de cada combatiente. Actualízalos a medida que avanza el combate: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (el informe con el que empieza una sesión) enumera lo que está en juego (el lugar, los combatientes, aquellos a quienes se refieren los eventos de esta escena, y el grupo) con su where, doing, plan y state. También enumera los últimos eventos ocurridos fuera de escena.
