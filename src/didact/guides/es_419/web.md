<!-- translated from 5a088227a31a -->
# La aplicación web

`didact serve` abre tu biblioteca en un navegador web: explora y edita fichas, mira en un grafo cómo se enlazan, lee el diario, ejecuta reglas y tablas, y usa cualquier comando desde un formulario.

```
didact serve                     # http://127.0.0.1:8765/ until Ctrl-C
didact serve --open              # and open it in a browser tab
didact serve --gm                # start with the GM view on
didact serve --port 9000
didact serve --campaign withering --home ~/OtherLibrary
didact serve --demo              # a fresh sample campaign to try things on
```

Funciona sin conexión: las fuentes y los iconos vienen con Didact.

**Modo demo.** `--demo` sirve la campaña de ejemplo (`didact sample`: un valle fluvial, un PJ, personas con las notas del DJ, lugares y caminos, una misión, un reloj y una sesión en curso con un combate) desde una biblioteca propia, junto a la carpeta de caché de Didact. Ahí están instalados todos los paquetes que vienen con Didact. Se crea desde cero cada vez que arranca `--demo`, así que prueba lo que quieras: tu biblioteca no se toca.

## Opciones

| Opción | Por defecto | Qué hace |
|---|---|---|
| `--port <n>` | 8765 | el puerto en el que escucha |
| `--host <address>` | 127.0.0.1 | la dirección en la que escucha: solo esta computadora |
| `--open` | desactivada | abre la aplicación en una pestaña del navegador |
| `--gm` | desactivada | empieza con la vista del DJ activada |
| `--demo` | desactivada | sirve una campaña de ejemplo nueva en lugar de tu biblioteca |

Las opciones globales `--home`, `--world` y `--campaign` se aplican a todo lo que hace la aplicación. Abrir otro mundo u otra campaña en la página Biblioteca de la aplicación cambia a ese mundo o campaña, como hacen `didact world use` y `didact campaign open`, y Cerrar deja a un lado la campaña abierta (`didact campaign close`).

## Qué contiene

- **Vista general:** el informe (mundo, campaña, sesión, escena, grupo, lo pendiente), acciones rápidas (tirar dados, consultar el oráculo con las probabilidades que conoce, anotar un evento, empezar o terminar una sesión, una nueva ficha) y los últimos cambios.
- **Estado:** cómo están las cosas, de un vistazo: la sesión y la escena, la hora y los próximos recordatorios, los números de cada miembro del grupo y lo que lleva, el combate (a quién le toca, estados), las misiones abiertas y los contadores, y dónde está el grupo con sus salidas. Los números se pueden ajustar ahí mismo: − y + en una característica, marcar una casilla de un contador, usar o quitar un objeto, agregar uno, terminar una misión, avanzar el tiempo (un número, y una unidad que conozca el calendario: horas, guardias, días, …), poner un recordatorio (una vez, o cada cierto tiempo) y cancelar uno.
- **Fichas:** todas las fichas, agrupadas por tipo, con un cuadro de filtro y los chips todo, mundo o campaña. La página de una ficha muestra su hoja, su descripción, sus detalles, sus campos, su contenido, sus enlaces en ambos sentidos, su crónica y su historial, con formularios para cambiar cada cosa, y para archivarla o eliminarla. Un personaje cuyo sistema tiene subida de nivel tiene un botón Level up (`char advance`): un borrador que muestra lo que cambia, antes y después, hasta que se confirma.
- **Borradores:** la creación de personajes y los generadores, paso a paso. Crear un personaje (paso a paso o al azar, eligiendo de qué tipo cuando el sistema tiene varios: un personaje jugador, un asalariado, …) y Generar… están en las páginas de Fichas; los borradores pendientes aparecen ahí y en la Vista general. La página de un borrador muestra lo que contiene hasta ahora (sus entidades y sus campos, el mapa que ha dibujado un generador, las tiradas, las preguntas del libro) y la pregunta a la que espera. Cada opción es un botón que dice lo que significa cuando el paquete lo indica (lo que da un trasfondo, lo que hace un talento); elegir varias es una casilla que marcar para cada una; las puntuaciones compradas con un presupuesto son números que cuentan los puntos sobre la marcha; un nombre u otra respuesta abierta se puede escribir; y Que decidan los dados tira solo esa (`char roll c3 --one`). Volver revierte el último paso, así que su pregunta vuelve (`char back c3`: las tiradas que hizo se marcan como deshechas, y Deshacer recupera el paso). Después, Tirar el resto, Editar, Descartar… (pregunta antes) y Confirmar, que abre la ficha del nuevo personaje, o enumera lo que ha creado el generador. El borrador de un generador es del DJ: la vista de jugador solo muestra que existe.
- **Grafo:** las fichas como nodos y los enlaces como aristas. Arrastra los nodos, arrastra el fondo para desplazarte, haz zoom con la rueda; pasa el mouse por encima para iluminar los vecinos de una ficha; haz clic para abrir una. El botón Grafo de la página de una ficha muestra solo su vecindario.
  - **Mapa** (el interruptor encima del grafo, o Abrir el mapa en Estado): los lugares que conoce el grupo, los caminos entre ellos (etiquetados road, trail, …), la región en la que está cada uno (con línea discontinua) y dónde está el grupo. Un camino a un lugar aún no encontrado lleva a un "?"; la vista del DJ muestra todos los lugares.
- **Diario:** las sesiones, cada una se despliega en sus escenas, eventos y tiradas. Cada evento tiene Editar y Quitar (pasa el mouse por encima), que abren los formularios de `beat edit` y `beat rm`.
- **Referencia:** busca en todo (los resultados aparecen mientras escribes), ejecuta desde formularios las reglas de los paquetes activados, tira en sus tablas y lee el texto de sus reglas, su glosario y sus guías.
- **Biblioteca:** mundos y campañas (abrir, cerrar, crear, eliminar), paquetes (cada uno con su descripción; activar, desactivar, instalar, desinstalar; los paquetes que vienen con Didact tienen un botón Instalar), el historial (Deshacer, Rehacer, Volver a este punto, Borrar), los puntos de guardado (volver atrás, quitar) y los respaldos (crear uno ahora, restaurar, eliminar, conservar solo los más recientes; los que se hacen al terminar una sesión van marcados como auto). Sin ninguna campaña abierta, la Vista general enumera las campañas del mundo para abrir una.
  - Eliminar un mundo o una campaña pregunta antes, y Deshacer lo recupera todo.
  - Volver a este punto (junto a cada cambio) revierte todo lo posterior a ese cambio (`didact undo --to e40`): su página enumera antes lo que se va. Cada cambio se deshace y cada tirada se marca como deshecha, sin eliminar nada: Rehacer, o volver a un cambio posterior, los recupera. Mostrar cambios más antiguos lista más del historial.
  - El paquete core siempre está activo. Solo se usa un sistema de juego a la vez: el del mundo abierto, que lo conserva para siempre (se elige al crearlo). Otro sistema se juega en un mundo propio: su fila abre un mundo que se juega con él, o crea uno nuevo. Desinstalar un paquete no se puede deshacer: vuelve a instalar su .didactpack.
  - Borrar el historial muestra antes exactamente qué se va y qué deja de funcionar, con un botón para crear antes un respaldo. No se puede deshacer, y eliminar un respaldo tampoco.
  - Empezar de cero: **Restablecer…** vacía la biblioteca, como si Didact estuviera recién instalado, y la numeración vuelve a empezar en #e1. Su página muestra antes lo que se va. Primero se hace un respaldo de la biblioteca, y los respaldos se quedan (también los paquetes instalados, salvo que marques la casilla).
  - Restaurar un respaldo muestra antes lo que contiene junto a la biblioteca actual. Primero se hace un respaldo de la biblioteca tal como estaba: Deshacer no puede revertir una restauración, pero restaurar ese respaldo sí.
- **Comandos:** cada comando como formulario, y un cuadro que admite una línea de comandos entera. Cada cuadro admite lo que admite su argumento: un número, un id o un evento (`e12`) según su patrón, una cantidad de tiempo de juego como un número y una unidad, y una lista para elegir entre las fichas, borradores, paquetes, puntos de guardado, oráculos, tablas y reglas que hay.
- **Configuración:** las opciones de la campaña (las variantes y reglas opcionales de su sistema, que siguen sus reglas, la creación de personajes y los generadores; cada una dice lo que hace: en una regla opcional, qué cambia al activarla, en una elección, qué significa cada uno de sus valores, y un valor predeterminado que fija otra opción dice cuál), el idioma de la aplicación, el diccionario de sinónimos (el idioma que usan las búsquedas para los sinónimos: descargar uno, con una barra de progreso, cambiar entre los descargados, quitar uno) y la documentación del código.
  - La aplicación, sus guías y lo que muestran los comandos en ella están en 24 idiomas. Si no eliges ninguno, la aplicación sigue el idioma del navegador. La línea de comandos y los LLM que la usan siguen en inglés: el idioma que elijas aquí es solo el de la app.
  - El botón de código del encabezado abre la documentación de la API del código. Se genera a partir del código la primera vez, y de nuevo cada vez que el código cambia (`didact docs build`).

Cada cambio ejecuta un comando `didact` real, así que se comprueba, se registra y se puede deshacer exactamente igual que en la línea de comandos. La aplicación muestra cada vez el comando que ha ejecutado (`didact set sweeney hp-=2`), con un botón Deshacer cuando hay algo que revertir.

Un cuadro solo admite lo que admite su comando. Un id (de un mundo o de una campaña) y un tipo de ficha admiten letras minúsculas, dígitos y guiones: los espacios se convierten en guiones y las mayúsculas pasan a minúsculas mientras escribes. El nombre de un campo no admite espacios (se convierten en guiones bajos), el nombre de un detalle es una sola palabra, y los campos numéricos solo admiten números. Lo que admite un cuadro está escrito debajo, y el comando lo vuelve a comprobar de todos modos.

Guardar nunca sobrescribe un cambio que no has visto. Si la ficha ha cambiado después de que la página la mostrara (la ha cambiado un LLM desde la línea de comandos, por ejemplo, u otra pestaña), el guardado se rechaza y dice lo que hay ahora. Una descripción que estabas editando se queda en el editor, junto a la versión nueva, para combinarlas y volver a guardar. − y + siempre se aplican: se suman.

## Vista de jugador y vista del DJ

La aplicación muestra lo que saben los jugadores, como hace `didact show`: las fichas secretas, las secciones `## Secrets`, los campos secretos y los detalles solo para el DJ se quedan fuera. El botón **GM** del encabezado activa la vista del DJ, y un aviso lo indica ("Vista del DJ: se muestran spoilers"). El navegador recuerda la elección.

En la vista de jugador:
- una descripción con líneas solo para el DJ no se puede editar (al guardarla se perderían): activa antes la vista del DJ;
- un detalle del DJ o un campo secreto que la página no muestra no se puede sobrescribir, aunque sí se puede agregar una nota nueva para el DJ;
- el historial nombra el comando y las fichas que conocen los jugadores (`set · Freya`), nunca los valores, y Deshacer dice qué cambio ha revertido, no en qué consistía.

## Seguridad

La aplicación puede cambiar tu biblioteca, así que por defecto solo escucha a esta computadora.

- `--host` con otra dirección permite que otras computadoras accedan a ella, y Didact avisa de ello. Úsalo solo en una red de confianza.
- Solo responde a las peticiones dirigidas a ella misma (su propia dirección, `localhost`, `127.0.0.1` o `[::1]`, con su puerto). Así otros sitios web no pueden llegar a ella con trucos de DNS.
- Cada cambio necesita un formulario de la propia aplicación: un token secreto en cada formulario debe coincidir con una cookie que otros sitios no pueden leer ni enviar.
- No hay inicio de sesión. Cualquiera que pueda usar el navegador de esta computadora puede usar la aplicación.
