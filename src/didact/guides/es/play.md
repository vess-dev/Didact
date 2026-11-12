<!-- translated from bef7b2c650cb -->
# Jugar una sesión

Cómo transcurre una partida con Didact: el LLM narra, y Didact guarda cada hecho, cada tirada y cada cambio.

## Antes de la primera sesión

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

Un mundo conserva el sistema con el que se creó, y sus campañas se juegan con él: otro sistema se juega en un mundo propio. `didact campaign close` deja a un lado una campaña (su mundo sigue abierto) y `didact campaign open <id>` la retoma donde se quedó, con su sesión y todo.

`didact world delete <id>` y `didact campaign delete <id>` eliminan uno, con una vista previa antes; `--yes` lo borra, y `didact undo` lo recupera todo.

`session zero` enumera las cuestiones que hay que acordar con el jugador. Primero van las del propio paquete. Entre ellas están las opciones del sistema (sus variantes y reglas opcionales): sus reglas siguen las respuestas, y el resumen dice qué significa cada opción cambiada. Cada informe lleva las respuestas.

## Una sesión

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Turnos:** cada mensaje del jugador abre un turno (el hook de Claude Code llama a `didact capture`, y otros clientes usan `turn begin`). `didact undo --turn` deshace todo lo hecho para ese mensaje: cambios, eventos y tiradas. La transcripción lo conserva.
- **Volver atrás:** `didact undo --to e40` revierte todo lo posterior a #e40, del más reciente al más antiguo (`--dry-run` lo enumera): cada cambio se deshace y cada tirada se marca como deshecha. No se elimina nada: `redo`, o volver a un cambio posterior, lo recupera.
- **Tiempo:** `didact time advance 1 watch` agota los temporizadores, saca los recordatorios y ejecuta los disparadores de tiempo. `didact remind --list` muestra los próximos recordatorios, y `didact remind --cancel 2` quita uno. Una campaña empieza en el inicio del calendario, o en la fecha que da `campaign new --date '4 July 1902'`, y `didact time set '<date>'` la cambia hasta la primera sesión.
- **Lugares:** `didact visit <place>` mueve al grupo y marca el lugar como visitado. `didact map` muestra lo que conoce el grupo, y una salida sin explorar es `?`.
- **Combates:** `didact combat start --party troll`, luego `combat next`, `combat hit freya troll weapon=d8` y `combat end`. Los combatientes entran y salen a mitad de combate: `didact combat join wolf-2` (en modo individual tiran iniciativa) y `didact combat leave troll --why fled`. No se salta el turno de nadie.
- **Cosas:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (o a un cofre, o a un lugar); `didact where rope` la encuentra. `inv add` encuentra un objeto del compendio por su id, su nombre o un alias.
- **Tus notas:** `didact about sweeney plan='…' doing='…' where='…'` guarda lo que has decidido sobre cualquiera o cualquier cosa. Los jugadores solo ven `looks`. `didact log … --about sweeney` pone un evento en su ficha (`--secret` si los jugadores no lo ven). `didact guide details` cuenta más.
- **El mundo sigue adelante:** `didact faction turn`, y los relojes: `didact track new 'The flood' --size 6`. Un comando que solo admite un tipo de ficha toma un nombre que comparten otras como de ese tipo: `didact track roll draugr` tira la reserva que lleva el nombre de un enemigo (igual `track tick` con un contador, `quest done` con una misión y `visit` con un lugar).

## Oráculos, generadores y personajes

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

Nada de lo que hace un generador o una creación de personaje se escribe hasta el `commit`. Describe en `--prefill` lo que quiere el jugador, y el procedimiento rellena los huecos. Una pregunta enumera lo que significa cada opción cuando el paquete lo indica (`- Cutpurse: …`): díselo al jugador, para que elija sabiendo lo que obtiene.

## Secretos

Las vistas son seguras para los jugadores por defecto: `show`, `find`, `sheet`, `map`, `brief`. Omiten:
- las fichas secretas (`knowledge: secret`);
- las secciones `## Secrets` y `## GM notes`;
- los campos `secret: true`.

`--gm` lo muestra todo. Cuando los jugadores descubren algo:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` escribe lo que saben los jugadores como una pequeña web para compartir o leer en el móvil: el grupo, una página por ficha, el diario y el mapa. Siempre es segura para los jugadores, y exportar de nuevo a esa carpeta la actualiza. `didact export --as lonelog` escribe el diario en notación Lonelog (`@ ? d: -> =>`, escenas como `S1`, etiquetas como `[N:Sweeney]`), también seguro para los jugadores.

## Trasfondo: lo que vuelve cuando se menciona algo

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Qué cuenta:** cada PNJ, lugar, objeto y facción es una tarjeta cuyas claves son su nombre y sus alias. Las entradas de trasfondo tienen `keys`, y las resoluciones salen a través de su regla. Se buscan palabras completas, y los plurales cuentan ("wolves" coincide con `wolf`).
- **Cuándo sale el trasfondo:** el hook de Claude Code examina cada mensaje del jugador. `log`, `scene new` y `show` también traen el trasfondo recién activado, y una entrada no se repite durante unos turnos.
- **Ajustar una entrada:** `--secondary` con `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (en turnos o escenas), `--constant` (siempre en el informe) y `--no-recurse`.
- **Ámbitos:** las entradas van a la campaña salvo que `--scope` diga world, system o global. Una búsqueda solo ve esta campaña, su mundo, su sistema y el ámbito global, nunca otro mundo. Una entrada más específica con el mismo id oculta a una más amplia.
- **Lorebooks de otras herramientas:** `didact lore import <file>` lee el World Info de SillyTavern (también el de KoboldAI), el lorebook de una tarjeta de personaje y el `.lorebook` de NovelAI; `didact lore export --to <file>` escribe World Info. Se conservan las claves, la lógica, la prioridad, la probabilidad, los grupos y los tiempos.

## Cambiar la historia

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` cambia el hecho pero guarda el valor antiguo. También marca como desfasados los resúmenes que mencionan a Sweeney, y `audit` lo recoge.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` registra una resolución. A partir de entonces aparece en `rules lookup` y cuando se ejecuta esa regla.
- `didact name npc` tira un nombre nuevo, nunca uno que ya use el mundo. Antes de inventarte uno, compruébalo con `didact names check <name>`. `didact names forget <name>` lo deja libre de nuevo.

## Mantenimiento

- `didact history --clear` muestra lo que se perdería al borrar el historial antiguo; `--yes` lo borra para siempre, fichas eliminadas incluidas, y ya no pueden llegar a él ni deshacer, ni `diff`, ni `rewind`, ni los puntos de guardado anteriores (`--before e120` conserva ese evento y los posteriores, `--rolls` borra también el registro de dados). Ejecuta antes `didact snapshot`.
- `didact save --remove 'before the dragon'` quita un punto de guardado; `didact undo` lo recupera.
- `didact transcript 3 --clear` borra la transcripción de la sesión 3 (`--clear --all`: la de todas las sesiones). `didact undo` la recupera, y el texto sigue en el historial hasta `history --clear`.
- `didact compendium remove <entry>` borra una entrada que añadiste; las fichas creadas a partir de ella se quedan.
- `didact snapshot --keep 3` borra todas las copias de seguridad menos las tres más recientes, y `didact snapshot --remove <name>` borra una. Ninguna de las dos cosas se puede deshacer.
- `didact session end` hace por sí solo una copia de seguridad de la biblioteca (`snapshot-<time>-auto.zip`) y conserva las cinco más recientes de ese tipo; `didact snapshot --list` las marca.
- `didact reset` muestra lo que se llevaría vaciar la biblioteca; `--yes` la deja como recién instalada: se van todos los mundos, campañas y fichas, el historial y el índice de búsqueda, y el siguiente cambio vuelve a ser #e1. Antes hace una copia de seguridad de la biblioteca (`…-before-reset.zip`), y las copias se quedan, igual que los paquetes instalados salvo con `--packs`. Para probar Didact con una campaña ya preparada, `didact sample` monta la de ejemplo en una biblioteca vacía (`--home` le da su propia carpeta), y `didact serve --demo` la sirve desde cero.
- `didact snapshot --restore <name>` muestra lo que contiene una copia de seguridad junto a la biblioteca actual; `--yes` hace una copia de la biblioteca tal como está (`…-before-restore.zip`) y luego pone la copia en su lugar. Los números de evento y de tirada continúan. Deshacer no puede revertir una restauración: restaurar esa copia de seguridad sí.
