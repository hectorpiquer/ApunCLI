# apuncli 📚 — tus apuntes de estudio, directos desde la terminal

**apuncli** es un gestor de apuntes de estudio para la terminal. Está pensado
para estudiantes (crecido a partir de los estudios de DAM): crear, organizar,
buscar, repasar, hacerte tests, gestionar los enlaces/PDFs de cada tema y
exportar apuntes sin salir de la consola. Si no recuerdas un comando, abre
`apuncli` a secas y úsalo con el menú de flechas.

Todo se guarda en una base de datos **SQLite** local (`~/.apuncli/apuncli.db`)
y el proyecto usa **solo la librería estándar de Python**: nada que instalar
más allá del propio `apuncli`.

```
$ apuncli crear "Tema 4: árboles binarios" -a "ED" -t "estructuras,arbols" -c "Máx. 2 hijos por nodo."
$ apuncli buscar "hijos"
[1] Tema 4: árboles binarios
    ED (Máx. 2 hijos por nodo.…)
```

---

## Tabla de contenidos

- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Modo menú (sin memorizar nada)](#modo-menú-sin-memorizar-nada)
- [Conceptos básicos](#conceptos-básicos)
- [Comandos](#comandos)
- [Ejemplos de uso real](#ejemplos-de-uso-real)
- [Exportar e importar (Markdown)](#exportar-e-importar-markdown)
- [Recursos: enlaces y ficheros](#recursos-enlaces-y-ficheros)
- [Modo repaso](#modo-repaso)
- [Test automático](#test-automático)
- [Temario](#temario)
- [Variables de entorno](#variables-de-entorno)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Tests](#tests)
- [Licencia](#licencia)

---

## Requisitos

- **Python 3.8 o superior** (con `pip`).
- Linux, macOS o Windows.

## Instalación

```bash
git clone https://github.com/hectorpiquer/ApunCLI.git
cd apuncli
pip install .
```

Y ya está:

```bash
apuncli --help
```

> **Sin dependencias externas.** Todo el proyecto usa módulos estándar de
> Python (`argparse`, `sqlite3`, `unittest`), así que no hay que instalar
> ninguna librería de terceros.

### Ejecutar sin instalar

Si prefieres no instalar nada (o estás probando), puedes ejecutarlo directo
desde el código con la variable `PYTHONPATH` apuntando a `src`:

```bash
cd apuncli
PYTHONPATH=src python3 -m apuncli listar
```

Con esto basta para usarlo desde la carpeta del proyecto (útil en clase).

### Instalación para desarrollar (modo editable)

```bash
pip install -e .
```

Los cambios en el código se notan al instante sin reinstalar.

## Modo menú (sin memorizar nada)

Escribe `apuncli` a secas y se abre un **menú interactivo**: navega con las
flechas ↑/↓ (o `j`/`k`, inicio/fin con `g`/`G`), confirma con Enter y cancela
con `q`/`Esc`/`Ctrl+C`. Desde él puedes hacer todo lo importante sin recordar
ningún comando.

```
$ apuncli
📚 apuncli — menú de estudio
¿Qué quieres hacer?
  ❯ 📋  Ver todos mis apuntes
    👀  Ver un apunte
    ➕  Crear un apunte nuevo
    ✏️   Editar un apunte
    🔎  Buscar texto
    🧠  Repasar (modo ficha)
    📝  Hazme un test
    🔗  Recursos de un apunte
    📚  Generar temario Markdown
    📊  Estadísticas
```

(En tuberías o sin terminal real, `apuncli` muestra la ayuda de siempre.)

## Conceptos básicos

| Concepto    | Qué es                                                                       |
| ----------- | ---------------------------------------------------------------------------- |
| **Apunte**  | La unidad principal: título + contenido + asignatura + etiquetas.            |
| **Asignatura** | Un texto libre por apunte para agrupar (ej: `Programación`, `ED`).        |
| **Etiqueta**| Etiquetas opcionales y plurales por apunte (ej: `tema1`, `examen`).          |

Cada apunte tiene un **id** (número) que verás con `apuncli listar` y que usan
los comandos `ver`, `editar`, `borrar`, `abrir` y `exportar`.

## Comandos

| Comando            | Para qué                                          | Ejemplo                              |
| ------------------ | ------------------------------------------------- | ------------------------------------ |
| `crear`            | Crear un apunte                                   | `apuncli crear "Tema 1" -a ED -t examen -c "..."` |
| `listar` (`ls`)    | Ver todos los apuntes (filtrable)                 | `apuncli ls -a ED -t tema1`          |
| `ver`              | Ver un apunte completo                            | `apuncli ver 3`                      |
| `buscar`           | Buscar por texto en título y contenido            | `apuncli buscar "punteros"`          |
| `editar`           | Cambiar título, contenido, asignatura o etiquetas | `apuncli editar 3 -T "Nuevo título"` |
| `borrar` (`rm`)    | Borrar un apunte (pide confirmación)              | `apuncli borrar 3`                   |
| `abrir`            | Abrir un apunte en tu editor (`$EDITOR`)          | `apuncli abrir 3`                    |
| `exportar`         | Exportar a Markdown (salida estándar)             | `apuncli exportar --todos > apuntes.md` |
| `importar`         | Importar desde un Markdown                        | `apuncli importar apuntes.md`        |
| `repasar`          | Repaso tipo ficha, uno a uno                      | `apuncli repasar -a ED -n 10`        |
| `test`             | Test automático a partir de tus apuntes           | `apuncli test -t examen`             |
| `recurso` (`rec`)  | Adjuntar/abrir enlaces y ficheros a un apunte     | `apuncli recurso anadir 3 https://…` |
| `temario`          | Índice Markdown completo (para imprimir o PDF)    | `apuncli temario -a ED > temario.md` |
| `etiquetas`        | Ver todas las etiquetas                           | `apuncli etiquetas`                  |
| `asignaturas`      | Ver las asignaturas existentes                    | `apuncli asignaturas`                |
| `stats`            | Estadísticas de estudio                           | `apuncli stats`                      |

Todos los comandos aceptan `--help` para ver sus opciones, por ejemplo
`apuncli crear --help`.

### `crear` — las cuatro formas de dar contenido

```bash
# 1. En una línea con -c
apuncli crear "Definición: pila" -c "Estructura LIFO: el último en entrar es el primero en salir."

# 2. Abriendo tu editor (nano, vim, etc.)
apuncli crear "Tema 3: punteros" --editor

# 3. Pegando desde otro programa
echo "apuntes desde un fichero" | apuncli crear "Nota" --stdin

# 4. Interactivo: escribe líneas y termina con Ctrl+D
apuncli crear "Lluvia de ideas"
```

### `buscar`

La búsqueda usa **FTS5** (búsqueda de texto completo de SQLite) cuando está
disponible, así que admite:

```bash
apuncli buscar "punteros"              # coincidencia de palabra
apuncli buscar " ejecu*"               # prefijo (ejecución, ejecutar, ...)
apuncli buscar "punteros Y memoria"    # ambas cosas (Y / O / Y NO)
apuncli buscar '"puntero constante"'   # frase exacta
```

Si la consulta no es válida para FTS5, se busca con `LIKE` automáticamente.

### `abrir`

Edita el apunte completo en formato Markdown en tu editor preferido
(variable `EDITOR`). Al cerrar el editor, los cambios **se guardan solos**:

```bash
export EDITOR=nano   # (o vim, code, etc.)
apuncli abrir 5
```

### `borrar`

Pide confirmación salvo que pases `--si`:

```bash
apuncli borrar 5        # pregunta antes de borrar
apuncli borrar 5 --si   # sin preguntas
```

## Ejemplos de uso real

Una semana de estudio de Estructura de Datos (ED):

```bash
# Lunes: crear los apuntes del tema
apuncli crear "Tema 1: arrays" -a ED -t "tema1,examen" -c "Acceso O(1). Inserción O(n)."
apuncli crear "Tema 2: listas enlazadas" -a ED -t "tema1,examen" -c "Inserción O(1). Acceso O(n)."
apuncli crear "Tema 3: pilas y colas" -a ED -t "tema2,examen" \
    -c "Pila = LIFO (push/pop). Cola = FIFO (enqueue/dequeue)."

# Martes: ampliar un apunte existente al final
apuncli editar 1 --anadir -c "En Java, ArrayList redimensiona al 1,5x."

# Miércoles: buscar algo para el examen
apuncli buscar "LIFO"

# Jueves: repasar lo de ED antes de clase
apuncli repasar -a ED -n 3

# Viernes: estadísticas
apuncli stats
```

## Exportar e importar (Markdown)

`apuncli exportar` imprime en **Markdown** por la salida estándar; redirige a
un fichero con `>`:

```bash
apuncli exportar 3                  # un apunte, por pantalla
apuncli exportar --todos > apuntes.md
apuncli exportar -a ED -t examen > repaso-ed.md
```

El formato generado es Markdown normal con metadatos leíbles, compatible con
cualquier editor de notas:

```markdown
# Tema 3: pilas y colas

asignatura: ED
etiquetas: tema2, examen

Pila = LIFO (push/pop). Cola = FIFO (enqueue/dequeue).
```

`apuncli importar` hace el camino inverso: cada bloque que empieza con
`# Título` se convierte en un apunte (y reconoce las líneas `asignatura:` y
`etiquetas:`). Exporta, edita en VS Code u Obsidian, y vuelve a importar
cuando quieras.

## Recursos: enlaces y ficheros

Cada apunte puede llevar **recursos**: páginas web, PDFs, imágenes, ficheros
en tu disco… Se añaden solos: si escribes una URL o una ruta de fichero dentro
del contenido, `apuncli` la detecta y la guarda como recurso del apunte.

```bash
apuncli crear "Tema 6" -c "Docs aquí: https://docs.python.org"   # se adjunta sola
apuncli recurso anadir 6 ~/apuntes/resumen.pdf --nombre "resumen"
apuncli recurso listar 6
apuncli recurso abrir 2      # abre el navegador o el programa asociado
apuncli recurso borrar 2
```

`apuncli ver 6` muestra los recursos del apunte. Esto hace que tus apuntes
sean un hub de estudio: el texto, el PDF del profe y la web de referencia,
todo en el mismo sitio.

## Modo repaso

`repasar` muestra los apuntes **uno a uno**: primero el título, pulsas Enter,
y entonces ves el contenido. Prioriza los apuntes que aún no has repasado:

```bash
apuncli repasar            # 5 apuntes, prioriza no repasados
apuncli repasar -a ED -n 10
```

Cada apunte que ves suma una vez a su contador de repasos (lo ves en
`apuncli ver` y en `stats`).

## Test automático

Escribe preguntas dentro de tus apuntes con este formato:

```markdown
**Pregunta:** ¿Qué es una pila?
**Respuesta:** Una estructura LIFO: el último en entrar es el primero en salir.
```

Y `apuncli test` te las hace una a una, corrige con tolerancia (ignora
acentos, mayúsculas y puntuación) y te da la **nota sobre 10**:

```bash
$ apuncli test -a ED -t examen
Test con 2 pregunta(s). Responde con tus palabras (Enter vacío para saltar, 'q' para salir).

─ Pregunta 1/2 · de 'Tema 3: pilas y colas' ─
¿Qué es una pila?
Tu respuesta: una estructura lifo
✔ ¡Correcto!
...
Resultado: 2/2 · nota 10.0/10
```

Cada pregunta que respondes cuenta también como repaso del apunte.

## Temario

`apuncli temario` genera un **único documento Markdown** con índice, enlaces
internos a cada apunte, sus recursos y si lo tienes repasado:

```bash
apuncli temario                 # todo, por pantalla
apuncli temario -a ED > ed.md   # solo una asignatura, a fichero
```

Sirve como índice general, para imprimir, para pasar a PDF con pandoc o para
subir el temario a GitHub (Markdown de toda la vida).

## Variables de entorno

| Variable     | Para qué                                                        |
| ------------ | --------------------------------------------------------------- |
| `APUNCLI_DB` | Ruta alternativa de la base de datos (útil para pruebas).         |
| `EDITOR`     | Editor que usan `abrir`, `crear --editor` y `editar --editor`.   |
| `NO_COLOR`   | Si existe, desactiva los colores ANSI.                           |

## Estructura del proyecto

```
apuncli/
├── pyproject.toml           # metadatos del paquete y punto de entrada
├── LICENSE                  # MIT
├── README.md
├── src/apuncli/
│   ├── __main__.py          # entrypoint: main()
│   ├── argumentos.py        # parser de comandos (argparse) y despacho
│   ├── comandos.py          # lógica de cada comando (cmd_*)
│   ├── interfaz.py          # menú interactivo (el 'apuncli' a secas)
│   ├── db.py                # capa de datos SQLite (tablas, CRUD, búsqueda)
│   ├── formato.py           # Markdown <-> apunte, preguntas de test
│   ├── recursos.py          # detectar/abrir URLs y ficheros adjuntos
│   ├── temario.py           # generación de índices/temarios Markdown
│   ├── testmotor.py         # motor del test automático
│   ├── errores.py           # ApuncliError (errores amigables)
│   └── ui.py                # colores, editor y menús con flechas (termios/tty)
└── tests/
    ├── test_db.py           # capa de datos
    ├── test_formato.py      # exportación / importación
    ├── test_novedades.py    # recursos, temario y test automático
    └── test_cli.py          # comandos de extremo a extremo
```

El menú con flechas (en `ui.seleccionar`) usa `termios`/`tty`/`select` de la
librería estándar: pone la terminal en modo crudo, lee tecla a tecla
(flechas, `j`/`k`, Enter, `q`/`Esc`/`Ctrl+C`) y repinta la lista con códigos
ANSI. En Windows o sin tty real (tuberías, tests) cae automáticamente a un
selector numérico.

La separación es la clásica en tres capas: **datos** (`db.py`),
**lógica de presentación/formato** (`formato.py`, `ui.py`) y
**interfaz de línea de órdenes** (`argumentos.py` + `comandos.py`). Así es
fácil de entender, de probar y de ampliar: añadir un comando nuevo es escribir
un `cmd_...` en `comandos.py` y registrarlo en `argumentos.py`.

## Tests

Con `unittest` de la librería estándar:

```bash
python3 -m unittest discover -s tests -v
```

Cubren la capa de datos (crear, editar, borrar, buscar, filtrar, estadísticas),
el formato Markdown (análisis, generación y ciclo completo), los recursos, el
temario, el test automático y los comandos del CLI de extremo a extremo,
incluidos los casos de error (ids inválidos, apuntes inexistentes, títulos
vacíos…).

## Licencia

[MIT](LICENSE) — úsalo, cópialo y modifícalo con total libertad.
