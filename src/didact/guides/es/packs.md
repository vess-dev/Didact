<!-- translated from b1dfa1159ff4 -->
# Paquetes

Un paquete es un sistema de juego, un oráculo, una ambientación, una aventura o un suplemento, escrito como archivos YAML más un plugin de Python opcional. Esta guía explica cómo escribir uno: convertir un manual de reglas en un paquete, o añadir contenido casero.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Un paquete también puede crearse a partir de lo que hay en tu biblioteca. `didact pack new my-brew --from-overlay my-system` convierte tu contenido casero para un sistema (`compendium add`, fichas guardadas con `--scope system`, trasfondo) en un suplemento, y `didact world export --as setting` convierte un mundo en un paquete de ambientación: sus personas, lugares y trasfondo como entradas del compendio y trasfondo del paquete, que se traen a otro mundo con `compendium import`. Ambos dejan fuera los secretos y las notas del máster salvo con `--secrets`, y ninguno se marca como compartible hasta que fijes su licencia.

## Estructura

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

Un archivo contiene un elemento, una lista de elementos o varios elementos separados por `---`. Cada elemento indica su id con la clave de su tipo: `table: weather`, `check: save`, `type: pc`, o `id: troll` para las entradas del compendio. Refiérete a los elementos como `pack.id` (`my-system.save`), o solo por el id cuando solo lo tenga un paquete activado.

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

Un hack indica su base en `extends` y contiene solo lo que cambia:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Su elemento con el mismo id sustituye al de la base, sea cual sea el tipo (una tabla, una regla, una entrada del compendio, una sección de referencia, un término del glosario). Sus `settings` se superponen a los de la base, clave a clave: una clave que fija sustituye por completo el valor de la base (sus tablas de `names` ocupan el lugar de las de la base), y las reglas de la base también leen los valores del hack. `hides` descarta lo que queda y el hack no necesita: `*` coincide con cualquier secuencia de caracteres, decide el último patrón que coincide con un id, y uno que empieza por `!` conserva el elemento. Lo que el hack sustituye nunca se oculta. Los tipos son `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` y `term`. `didact pack validate` avisa de un patrón que no coincide con nada.

## Expresiones

Todas las condiciones y fórmulas usan el lenguaje de dados (`didact guide dice`), y además:
- **Valores:** `@name` lee un valor: `@roll`, `@who.STR`, `@settings.x`. `$name` pega antes el texto de un parámetro, así que `@who.$attr` pasa a ser `@who.STR`. Lee un parámetro de texto libre como `@name`, no entre comillas (`'$name'`): un apóstrofo en su texto las cerraría (`pack validate` avisa).
- **Lógica:** `and`, `or`, `not` e `in` (`'deprived' in @who.conditions`).
- **Literales:** texto (`'travel'`) y `true`/`false`.
- **Funciones:** `if(cond, a, b)` solo tira la rama que toma. `default(@thread.flashpoint, 0)` es el valor, o el valor alternativo cuando no está definido. `sum`, `count` (`count(@roll.dice, 6)` cuenta los seises), `min`, `max`, `any` y `all` reciben listas.

## Hojas: `schemas/`

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

| Tipo | Contiene | Opciones |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | un valor simple | min, max; `values` para enum |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: `@hp` es el valor, `@hp.max` el tope | range; min; max o max_field; die |
| `counter` | un número | min, max, thresholds, occupies (un campo slots) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | objetos (`Rope` o `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | lo que dice su nombre | `to` (para refs), `allowed` |
| `derived` | calculado, nunca guardado | expr |

Todos los campos admiten además `label`, `help`, `default`, `required` y `roll`: `new pc Hero --fill`, o un valor `"roll"`, lo tira a través del registro. Los tipos del paquete `core` guardan en `fields` prosa independiente del sistema. Los tipos de un sistema guardan sus números en `mechanics.<system>`. `set hero hp-=2` encuentra el campo, lo acota e informa de cualquier exceso. `+=` añade a una lista: un campo `list` (como `slots`) conserva un valor que se vuelve a añadir, `tags`, `conditions` y `refs` lo guardan una sola vez, y `-=` quita todas sus copias.

**Los ganchos** dicen qué pasa cuando un valor cruza un límite. Se disparan con cada cambio (`set`, `inv`, un paso `set` de una regla), pero solo cuando se cruza el límite: 3 → 0 lo dispara, 0 → 0 no. Las ediciones con `--force` se los saltan.

| Gancho | Se dispara cuando |
|---|---|
| `on_zero` | un número o `{value}` llega a 0 |
| `on_full` (`when_full` en slots) | llega a su máximo, tamaño o capacidad |
| `thresholds: {10: …, 20: …}` (contadores) | supera cada marca |

Una acción es texto (una nota para el LLM), `{set: {hp: 0}}` o `{condition: paralyzed}` sobre la misma ficha, `{trigger: death}` (ejecuta esa regla con `who` = la ficha), o una lista de estas.

**El inventario** (`didact inv …`) funciona sobre el campo `slots` de la hoja:
- **Espacio:** los objetos ocupan su `size` × `count`, y los contadores con `occupies` sobre el campo ocupan su valor. Pasarse de `capacity` se rechaza salvo con `--force`.
- **Grupos:** `groups: {backpack: 6, body: 4}` da a cada grupo su propio espacio, y sus propias columnas y totales: `@inventory.body.armor` es solo lo que se lleva puesto o en la mano, `@inventory.body.free` el espacio que le queda.
- **Usos:** `uses: 3` se descuenta con `inv use`. `uses: d8` es un dado de uso: con 1–2 baja un paso. Un objeto agotado desaparece salvo que tenga `recharge` o `keep: true`. De varios objetos con el mismo nombre, el nombre indica el primero; para gastar un uso (`inv use`, el `use:` de una regla, `set …uses-=1`), el primero al que le quede uno.
- **Claves propias de un objeto:** `didact set freya inventory.sword.damage=d10` (y también el `set: who.inventory.$item.damage` de una regla) cambia una de ellas, nombrando el objeto como lo nombra `inv`, por una parte de su nombre o por el nombre entero, con espacios y puntos (`'inventory.12.7mm pistol.damage=d10'`, entre comillas para la shell); `uses` y `charges` se cuentan como en un campo `uses` (`charges+=2` se queda en su máximo), y el espacio se comprueba como lo comprueba `inv add`. Una regla lee una como `@{who.inventory.$item.damage}` (un dado de uso como su dado, los usos como su número); un objeto o una clave que no está se lee como ausente, así que `default(…)` da su valor de reserva.
- **Compendio:** las entradas de tipo `item` (o weapon, armor, relic, …, o un tipo propio del paquete que extiende uno con `extends`) prestan sus detalles a `inv add`, encontradas por su id, su nombre o un alias (si dos comparten uno, nombra la que quieras como `pack.id`); cualquier otro nombre, `:` incluido, es el nombre propio del objeto.

## Tablas: `tables/`

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

Otras formas:
- **Listas ponderadas:** `entries` como lista, con `weight:` en cada entrada.
- **Columnas:** `columns: [a, b]` tira por separado cada columna de una fila. Una entrada simple (no una lista) llena todas las columnas, así que `columns: [first, second]` sobre una lista de palabras significa "tira dos veces en esta lista". `labels: false` deja los nombres de las columnas fuera del resultado ("Abandon · Advantage"). `read: "It's a {first} {second} with {third} {fourth} inside."` lee las columnas como una frase.
- **Consultas:** `lookup: hp_lost`, o `[odds, chaos]` para una tabla de doble entrada.
- **Duplicados:** `duplicates: reroll | keep | make_it_worse` para "tira dos veces".
- **Dos pasos:** una entrada que tira en otra tabla (`{table: lightning}` en vez de un texto, o `then:` tras él) trae consigo los datos de esa tirada: una regla o un borrador que la saca lee unos y otros, primero las claves propias de la entrada y luego las de la primera tabla que se tira a continuación. Un `--prefill` puede nombrar una entrada más abajo, a cualquier profundidad (`Ring of the Hunt`), con los datos de cada entrada del camino: de dos con el mismo nombre vale la más cercana (y luego la primera), una que sigue tira desde ahí, y una parecida a alguna de ellas sin ser ninguna se rechaza, nombrando la más cercana. Un borrador guiado ofrece el primer paso cuando sus entradas dicen lo que son (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): elegir una tira en la tabla siguiente, como una tirada que cae en ella.
- **Lectura en ambos sentidos:** `both_ways: true` en una tabla d66 añade la otra lectura: 31 también da 13, y quien lee elige.
- **Qué significa una entrada:** `about: "Knows: {skills}. Also known as: {aka}."` se rellena con los datos de cada entrada (una lista se lee `a, b`; `{text}` es la propia entrada) para decir lo que da cuando una elección la ofrece; el `note:` propio de una entrada lo dice en su lugar. Sin ninguno de los dos, una entrada cuyos datos tienen un `id` que nombra una entrada del compendio se describe con esa entrada.
- **Mazos y bolsas:** `deck: tarot` con `cards` (o `standard: true`); `bag: initiative` con `tokens`.

La validación comprueba que cada resultado que pueden sacar los dados cae en una entrada.

## Reglas: `rules/`

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

Las acciones y los procedimientos son listas de pasos, y los disparadores son pasos con una condición `when:`. Los pasos son:

| Paso | Qué hace |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | una tirada registrada; asigna `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`; un `{…}` se rellena primero, como en cualquier texto, así que se tiran los dados que un valor guarda como texto (`{@{who.inventory.$item.damage}}`), y el registro los muestra: un valor que no son dados se rechaza, y también `roll: "@die"` con ese texto, que no tira nada; un conjunto de tiradas (`{d8, d6}kh1`) sigue siéndolo |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | calcula valores; como en el `value` de `set`, un texto con `{…}` es una plantilla y una palabra suelta es texto; en cualquier texto que se rellena, `{{` y `}}` escriben la propia llave |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (o `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | cambia una ficha: se valida, se acota y se puede deshacer; `set: who.$attr` fija el campo que indica un parámetro, y `set: who.inventory.$item.damage`, una clave de un objeto que lleva la ficha (ver Inventario); `-=` quita un valor de una lista, y uno que no contiene no cambia nada (una nota lo dice; uno que nunca podría contener se rechaza); `unset:` quita un campo, como `set --unset` |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | da un objeto a una ficha o le quita uno, como hacen `inv add` e `inv drop`: sus detalles vienen del compendio, basta una parte única de su nombre, y se comprueban el espacio y los ganchos del campo |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | usa un objeto que lleva la ficha como lo hace `inv use`: los usos o las cargas se descuentan, un dado de uso se tira y baja un paso con 1–2, y uno que se agota desaparece salvo que se recargue o se conserve; de varios con ese nombre, el primero al que le quede un uso; asigna `@torch.out` (se fue su último uso), `@torch.gone` (no queda nada de él), `@torch.left`, `@torch.die` y `@torch.rolled` (`as:` es `use` por defecto) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | crea una ficha de inmediato, descrita como en el paso `entity` de un borrador (más abajo) y comprobada contra su hoja; `as:` (si no, su `key`, y si no, su tipo) la asigna como ficha, que se lee y se cambia como un parámetro `ref` (`pool: "@bleeding"`, `@bleeding.name`), y nunca es el nombre de un parámetro; sin `key:`, ningún campo se toma por una clave (`kind: track` queda tal cual); si ya hay aquí una de ese tipo y con ese nombre, se toma tal cual, así que una regla que se vuelve a ejecutar no crea nada nuevo |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | ejecuta una prueba y asigna su resultado |
| `do: other-action`, `with: {…}`, `as: trip` | ejecuta otra regla; `@trip` es su resultado y `@trip.<name>` lo que asignó (`@trip.found` por su `let: {found: 2}`, `@trip.luck` por su `roll: d6`, `as: luck`); `as:` es su id por defecto |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | una tirada en tabla registrada; asigna el texto y los `data` de la entrada (`@scar.<key>`, y las claves de un mapeo por su ruta: `@scar.cost.hp`), junto con los de cualquier tabla en la que tire a continuación; una lista de objetos (`[Rope, {name: Laser, damage: d8}]`) se lee como sus nombres (`count(@scar.gear)`, `'Laser' in @scar.gear`), y pasada tal cual a un paso (`apply: "@scar.gear"`) son los objetos mismos; una lista de otros mapeos solo la lee un paso |
| `table: "setting-{@drop.difficulty}-terrain"` | una tabla calculada: `{…}` y `$param` se rellenan |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | varios resultados como lista (`distinct` vuelve a tirar los repetidos) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | ramas |
| `repeat: "@count"`, `as: i`, `steps: […]` | un bucle: ejecuta los pasos tantas veces como indique su valor, y `@i` cuenta desde 1 |
| `for: pcs` (o `party`), `as: member`, `steps: […]` | ejecuta los pasos una vez por cada personaje jugador (o miembro del grupo), como `@member`: una ficha, como la que asigna `entity:` (`@member.name`, `set: member.fatigue`); `as:` nunca toma el nombre de un parámetro, así que el `who` de la propia regla sigue siendo el suyo |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | salida para el LLM |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (o `every: 1 day`) | un recordatorio que llega a medida que pasa el tiempo de juego, como los que pone `didact remind` |
| `reroll: roll`, `keep_if: "@face == 6"` | vuelve a tirar algunos dados de una tirada (mecánicas de forzar la tirada) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | tira en un valor de lista (las listas de un oráculo): asigna la entrada, `@who.choose` (una línea en blanco) y `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | tira la reserva menguante de un contador como hace `track roll` (los dados que sacan 1-3 se descartan; los dados de `drop` se descartan primero, los de `extra` se tiran a la vez) o solo descarta dados (`mode: drop`: forzar, marcar una casilla); siguen las fases enlazadas y el evento de la reserva; asigna `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

El resultado de una prueba lo puede leer la regla que la ejecutó (`check: … as: answer` da `@answer`), y también sus indicadores: `'random-event' in @answer.flags`. Los valores de `with:` se evalúan cuando contienen `@`, se rellenan cuando contienen `$param` o `{…}` ("Does $npc flee?"), y en los demás casos se pasan tal cual. Una regla con un parámetro `oracle` recibe la ficha de estado del oráculo de la campaña sin que se lo digan. Un parámetro `ref` con `to: monster` toma una ficha de ese tipo: un nombre que comparte otra ficha (la reserva de un enemigo, llamada como su carta) es la de ese tipo.

Los disparadores se ejecutan solos cuando ocurre su evento, y solo si se cumple su `when:`:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Cualquier regla (incluidos los generadores y la creación de personajes) puede leer `@system` (el id del sistema de juego del mundo, para que una ambientación escrita para dos sistemas pueda distinguirlos), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` y `@time.is_night`, y, con un calendario de meses, `@time.month`, `@time.month_name`, `@time.day_of_month` y `@time.year`; mientras haya un combate en curso, `@combat.round` y `@combat.fighters` (los ids de quienes participan en él). Un disparador de tiempo también puede leer `@time.passed`, los segundos que se acaban de avanzar, un disparador `combat_start` o `combat_end` lee el combate que empieza o termina (los ejecutan `combat start` y `combat end`; que un combatiente se vaya no pone fin al combate), y una regla ejecutada por un disparador lee lo mismo que el disparador. Un disparador con parámetros obligatorios solo lo ejecuta `didact do` o un gancho de campo (`who` = la ficha). Los disparadores `on: manual` solo se ejecutan cuando se les llama. `for: pcs` (o `party`) ejecuta un disparador una vez por cada personaje jugador (o miembro del grupo), como `who`: la experiencia tras cada sesión, por ejemplo. Un disparador que falla detiene el comando que lo lanzó, y dice qué disparador era y cómo seguir sin él (`didact override add trigger <id> --data '{"on": "manual"}'`).

El calendario está en los `settings` de un paquete: el de un paquete de ambientación prevalece sobre el del sistema, y el propio de un mundo (`calendar:` en su `world.yaml`), sobre ambos:

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

`leap: 4` alarga un mes un día cada 4 años, y `leap: [4, 100, 400]` cada 4, pero no cada 100, aunque sí cada 400: cada número anula el anterior. `weekday` nombra el día de la semana del inicio (si no, es el primero de la semana), y `year` es cómo escribe una fecha su año, tanto en las que muestra Didact como en las que lee (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` comprueba los tres. Una campaña puede empezar en otra fecha del calendario, antes de su inicio o después: `didact campaign new <id> --date '4 July 1902'`, o `didact time set '<date>'` hasta su primera sesión. Un día de la semana escrito delante de la fecha se comprueba: la fecha decide, y una nota lo dice cuando cae en otro.

Las opciones son las variantes y reglas opcionales del sistema, que cada campaña elige en la sesión cero:

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

`didact campaign profile lethality=deadly supplies=on` las guarda (o la página Ajustes de la aplicación web). Las reglas, la creación de personajes y los generadores las leen (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): una respuesta prevalece sobre lo que otra opción implica, y eso sobre el valor por defecto. Lo que implica una opción se sigue hasta el final (un estilo que fija la letalidad fija también lo que implica esa letalidad), y de dos implicaciones prevalece la más cercana. El resumen enumera las que difieren de su valor por defecto, con lo que significan, para que el máster aplique lo que las reglas no pueden. Un generador que no puede funcionar con ellas se detiene con `stop:` y el motivo, y no se crea ningún borrador.

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

- **Preguntar:** `didact ask '…' --odds likely` ejecuta la prueba `ask`. La respuesta es su resultado (una banda), y sus indicadores la acompañan.
- **Estado:** vive en una ficha que la prueba recibe como `oracle`. Una prueba lo cambia con `set: oracle.chaos += 1`.
- **Listas:** `lists: {names: […], method: sections, most: 3}` guarda listas ponderadas en esa ficha. `didact lists add|drop|roll|show` las gestiona, y las reglas tiran en ellas con `pick`. `sections` tira por una sección de cinco líneas y luego por una línea dentro de ella (una línea en blanco significa elegir); `uniform` da a cada línea la misma probabilidad.
- **Más para la prueba:** `didact ask '…' --with as_rule=true` pasa parámetros adicionales a la prueba del oráculo.
- **El registro:** cada respuesta se numera (`#o12`) y se registra, y `didact interpret o12 '…'` guarda lo que significó. El oráculo `yes-no` del paquete core es el de reserva.

## Generadores y creación de personajes: `generators/`, `chargen/`

Los dos son procedimientos que construyen un **borrador**. Usan todos los pasos de las reglas (`roll`, `table`, `if`, `let`, `prompt`, …) y además estos:

| Paso | Qué hace |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | añade una ficha al borrador (claves `poi-1`, `poi-2`, …); un campo o un enlace que nombra una clave que escribió el paquete (`key:`, o un nombre `as:`) pasa a ser el id de esa ficha al confirmar, así que elige claves que ningún campo tenga como texto (una entidad sin ninguna de las dos no tiene clave que sustituir); `from: "@relic.id"` la crea a partir de una entrada del compendio (su tipo, nombre y campos) |
| `choose: {from: [a, b], as: x}` (o `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | una elección; en modo guiado el borrador espera a `choose`; `exclude` descarta elecciones anteriores (si sale una tirada, se vuelve a tirar); `records:` añade las fichas de ese tipo que hay aquí, por id (creadas durante el juego); `answer:` hace la elección cuando su valor es una de las opciones (la senda propia de un personaje), sin preguntar |
| `choose_or_roll: {table: backgrounds, as: background}` | una elección que pueden hacer los dados; los datos de una entrada elegida son `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | tira valores para el personaje |
| `swap: {among: [STR, DEX, WIL], optional: true}` | intercambia dos puntuaciones, o las deja como están |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | reparte una serie fija |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | compra puntuaciones con un presupuesto (`default: random` lo gasta al azar en modo aleatorio) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | una lista va al inventario; un mapeo fija campos (las listas se suman) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | añade a un campo del personaje (o de una entidad del borrador): los números se suman, lo demás se une a una lista; si no hay nada que añadir, no pasa nada |
| `remove: {field: talents, value: "@old"}` | quita algo de un campo de lista (un talento cambiado por otro, un vínculo resuelto); si no está, no pasa nada |
| `roll_tables: [physique, vice]` | tira tablas y las guarda en `traits`; el `data.gear` de una entrada va al inventario y `data.add: {gold: 20}` suma a campos |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | el nombre; `name: {prompt: …}` sin nada en lo que tirar espera a que se le dé uno, incluso en modo aleatorio |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | una pregunta a la que vale cualquier respuesta (un objetivo, el nombre de otra ficha): el borrador la espera, incluso en modo aleatorio, salvo que venga rellenada de antemano; `field:` guarda la respuesta |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | un pointcrawl: una caída de dados registrada, caminos (siempre conectados), distancias, caminos ocultos (ver más abajo) |

El paso map admite más, para los procedimientos de caída de dados del libro:

| Clave | Qué hace |
|---|---|
| `regions: terrain` | estas entidades también caen; cada lugar se une a la más cercana (su `region`) |
| `hidden: 6`, `conditional: 5` | un d6 por camino: si iguala o supera el número, un camino oculto o condicional (los caminos ocultos no salen en el mapa de los jugadores) |
| `describe: [path-feature, path-condition]` | tablas que se tiran para cada camino, guardadas como sus `details` |
| `entrance: true`, `exit: true` | el lugar más cercano al borde es la entrada; los demás se numeran a partir de ella siguiendo los caminos (`map.n`), los caminos se alejan de ella, y la salida es un lugar lejano cerca de un borde, numerado el último |
| `number: "{@dungeon_name}, room {@n}"` | renombra los lugares numerados (sus claves de borrador cambian con ellos: `room-1` es la sala 1) |

Una tabla de caída de dados puede nombrar las siguientes tablas en los datos de sus entradas, para que el procedimiento se lea como el libro: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, y luego `table: "{@drop.what}"`. Los campos de lista sin valor (conditions, lists, tags) se leen como listas vacías, así que `'deprived' in @who.conditions` funciona desde el principio.

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

Un chargen con `advances:` cambia una ficha en lugar de crear una: la subida de nivel del sistema.

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

- **Una sola ficha:** un generador con `creates: npc` construye esa ficha igual que la creación de personajes construye un personaje (`apply`, `add`, `name`, `field:`); sus pasos `entity` añaden fichas junto a ella, y un enlace `to: character` apunta a ella.
- **Ejecutar:** `gen run` y `char new` crean un borrador (`#g7`, `#c3`) y no escriben nada. Un `stop:` lo termina sin crear nada: bajo un `if:` que lee una opción de la campaña, su pista remite a las opciones (`didact session zero`); si no, sus propias palabras dicen qué hacer en su lugar.
- **Decidir:** `--prefill '{…}'` decide cosas de antemano, por el nombre que asigna un paso (`as:`): un valor único responde a todas las apariciones, una lista a una aparición por elemento (una lista para `choose` con `count` es la elección entera). Los valores de `let` también se pueden rellenar de antemano (`{"hp": 6}`), y un nombre, un `ask` o un `let` conserva cualquier texto tal como se dio. Un valor para una elección entre opciones conocidas (un `choose`, una entrada de una tabla) es la opción que nombra, tal como está escrita o con otras mayúsculas y minúsculas, por el `id` de su entrada o por una tirada que cae en ella (`{"group": 3}`), y trae los datos de esa entrada; uno que se parece a una opción sin ser ninguna de ellas se rechaza, indicando la más cercana, y cualquier otro es una respuesta propia, sin datos. `--auto` (o `char new --mode random`) deja que los dados decidan el resto. Si no, el borrador espera en cada elección.
- **Describir:** una elección dice lo que significa cada opción, para el jugador que elige: el `note:` de una entrada de tabla o el `about:` de su tabla; si no, la entrada del compendio que nombra (el `id` de sus datos), o la que es la propia opción (una elección entre ids del compendio muestra el nombre de cada entrada): su `tagline` y su `summary`, su `description` o su `effect`; si no, el primer párrafo de su texto.
- **Volver atrás:** `char back` (o `gen back`) revierte la última respuesta, tirada o edición, así que el borrador vuelve a hacer esa pregunta; las tiradas que hizo ese paso se marcan como deshechas.
- **Reanudar:** un borrador reanudado repite su rastro: cada valor tirado o elegido, cada uno una vez y en orden (también la caída de dados del mapa), así que nada se tira dos veces y nada de lo ya decidido cambia.
- **Escribir:** `commit` escribe las fichas, comprobadas contra sus hojas.
- **Avanzar:** un borrador `advances:` parte de una copia de la ficha (con los valores predeterminados de su hoja), sus pasos leen la ficha como `@who` y los valores del borrador como `@character.*`, y `commit` escribe solo lo que ha cambiado, comprobado como con `set`; las fichas de sus pasos `entity` (la trama de un vínculo nuevo) se crean junto a ella: un enlace `to: character` apunta a la ficha, y un campo que nombra una clave guarda el id de la ficha de esa clave, como cuando se crea un personaje (`apply: {blood: "@pool"}`). Un `stop:` dice por qué todavía no (no hay suficientes PX), y no se crea ningún borrador. Un sistema cuyo crecimiento es una sola regla la nombra, en cambio, en su chargen: `advance: {rule: grow}`.
- **Modos:** `modes: [guided]` mantiene un procedimiento paso a paso: `--mode random` se rechaza.

## Compendio, referencia y glosario

- **Las entradas del compendio** se escriben como con `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. Un valor `"roll 2d8"` se tira cuando aparece la entrada. Ejecuta `didact spawn troll`, o trae al mundo las entradas de un paquete con `didact compendium import <pack>` (`--type loc`, y `--tag coast` para las que tengan todas las etiquetas dadas).
- **Para varios sistemas:** una clave de primer nivel va donde la pone `set`: al bloque del sistema cuando su hoja tiene ese campo, y si no, a `fields`. Una entrada que una ambientación escribe para más de un sistema da los números de cada uno en su propio bloque (`mechanics: {my-system: {hp: 12}}`): `pack validate` comprueba cada bloque con la hoja de ese sistema cuando está instalado, y señala una clave de primer nivel que tienen tanto esa hoja como la de core. Lo que dice un bloque se mantiene: junto a `mechanics: {my-system: {role: tactician}}`, un `role: innkeeper` de primer nivel es el campo de core, como todo lo que va bajo `fields:`. Un bloque que nombra el paquete que se está validando se comprueba contra ese paquete tal como está en su carpeta.
- **Las secciones de referencia** van en `reference/*.md`, con front matter (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` las encuentra; una frase entre comillas que no aparece se prueba palabra por palabra.
- **El glosario** es `glossary.yaml`: `term: definition`, o una lista de `{term, definition, aliases, see}`. `didact define <term>` lo lee.

## Tests: `tests/`

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

## Compartir y quitar paquetes

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- Un paquete que declara `redistributable: false` no se puede exportar.
- **core** forma parte de Didact y siempre está activo: todos los sistemas se basan en él, así que no se puede desactivar ni desinstalar.
- Los demás paquetes que vienen con Didact son archivos `.didactpack` en su carpeta `packs/`. `pack list` los muestra hasta que se instalan, e instalar uno trae también los paquetes que necesita, si vienen con Didact.
- `pack update` busca versiones más nuevas en la carpeta `packs/` de Didact y en GitHub (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` indica otro sitio, o nada para no buscar). Una versión nueva se instala junto a la antigua: las campañas conservan la suya hasta `didact campaign upgrade`.
- Solo se usa un sistema de juego a la vez: el del mundo abierto. Un mundo conserva el sistema con el que se creó (`didact world new <id> --system <pack>`; uno creado sin sistema toma el primero que se le dé, con `pack enable` o `world set system=`), sus campañas se juegan con él, y no se puede añadir un paquete que necesite otro sistema (una ambientación escrita para él): otro sistema se juega en un mundo propio.
- `uninstall` se niega mientras un mundo o una campaña use la única copia del paquete (`--force` lo quita igualmente). No se puede deshacer: vuelve a instalar el .didactpack.

## Del manual al paquete: la lista de comprobación

Repasa las mecánicas del libro en este orden. Cada una corresponde a algo de lo anterior:

1. **Resolución:** cómo tiene éxito una tirada (una prueba: `success`, `bands`, `auto`).
2. **Dados:** dados inusuales, símbolos, pasos (`dice.yaml`, dados con nombre, cadenas).
3. **La hoja:** atributos, números derivados (`schemas/`, campos derivados).
4. **Recursos:** PG, suerte, impulso (campos resource y counter; pasos `set`).
5. **Estados:** los estados y lo que hacen (campos `conditions`; pasos `if`).
6. **Combate:** ataques, daño, iniciativa (acciones; `bag`/`deck` para el orden de turnos).
7. **Procedimientos:** exploración, viajes, tiempo libre (procedimientos con indicaciones).
8. **Tablas:** todas las tablas aleatorias (`tables/`; `pack import` para tablas en Markdown).
9. **El bestiario:** monstruos y PNJ (`compendium/`).
10. **Objetos:** equipo, conjuros, reliquias (`compendium/`, campos slots).
11. **Consejos para el máster:** principios y consejos (`GUIDE.md`, `reference/`, `guidance:` en los tipos).
12. **Creación de personajes:** cómo se hace un personaje (un procedimiento `chargen/`, o `roll:` en cada campo).

Cita las páginas con `source:` en todas partes, para que se vean los huecos. Añade un test de humo con partida que cree un personaje, tire una prueba, luche y ejecute un procedimiento.
