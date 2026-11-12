# apuncli 📚 — tus apuntes de estudio, directos desde la terminal

**apuncli** es un gestor de apuntes de estudio para la terminal. Está pensado
para estudiantes (crecido a partir de los estudios de DAM): crear, organizar,
buscar, repasar, hacerte tests, gestionar los enlaces/PDFs de cada tema y
exportar apuntes sin salir de la consola. Si no recuerdas un comando, abre
`apuncli` a secas y úsalo con el menú de flechas.

Todo se guarda en una base de datos **SQLite** local (`~/.apuncli/apuncli.db`)
y el proyecto usa **solo la librería estándar de Python**: nada que instalar
más allá del propio `apuncli`.

### ¿No sabes por dónde empezar? Prueba la demo

```bash
$ apuncli demo            # crea 4 apuntes de ejemplo (etiqueta [demo])
$ apuncli test            # te hace preguntas generadas de esos apuntes
$ apuncli repasar         # modo ficha
$ apuncli limpiar -t demo --si   # y los quitas cuando quieras
```

```
$ apuncli test -n 2
Test con 2 pregunta(s). Responde con tus palabras (Enter vacío para saltar, 'q' para salir).

─ Pregunta 1/2 · de 'Tema 2: pilas y colas' ─
¿Qué coste tiene push en una pila?
Tu respuesta: O(1)
✔ ¡Correcto!

Resultado: 1/1 · nota 10.0/10
```

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
- [Acciones externas: acciones.json](#acciones-externas-accionesjson)
- [IA: resumir y generar preguntas (con modo sin red)](#ia-resumir-y-generar-preguntas-con-modo-sin-red)
- [Ejemplos de uso real](#ejemplos-de-uso-real)
- [Exportar e importar (Markdown)](#exportar-e-importar-markdown)
- [Recursos: enlaces y ficheros](#recursos-enlaces-y-ficheros)
- [Modo repaso](#modo-repaso)
- [Test automático](#test-automático)
- [Temario](#temario)
- [¿Qué estudio hoy?](#qué-estudio-hoy)
- [Copia de seguridad](#copia-de-seguridad)
- [Autocompletado con TAB](#autocompletado-con-tab)
- [Variables de entorno](#variables-de-entorno)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Guía para desarrollar](#guía-para-desarrollar-o-ampliar-el-proyecto)
- [Tests](#tests)
- [Licencia](#licencia)

---

## Requisitos

- **Python 3.8 o superior** (con `pip`).
- Linux, macOS o Windows.

## Instalación

```bash
# con uv o pipx (recomendado): instalable como comando global desde GitHub
uv tool install git+https://github.com/hectorpiquer/ApunCLI.git
# o bien:
pipx install git+https://github.com/hectorpiquer/ApunCLI.git

# y sin uv/pipx, con pip:
pip install git+https://github.com/hectorpiquer/ApunCLI.git
```

Y ya está, desde **cualquier carpeta**:

```bash
apuncli --help
```

> **Sin dependencias externas.** Todo el proyecto usa módulos estándar de
> Python (`argparse`, `sqlite3`, `urllib`, `unittest`), así que no hay que
> instalar ninguna librería de terceros. (Para participar en el desarrollo con
> los tests nuevos solo hace falta `pytest`.)

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
  ❯ 📅  ¿Qué estudio hoy?
    📋  Ver todos mis apuntes
    👀  Ver un apunte
    ➕  Crear un apunte nuevo
    ✏️   Editar un apunte
    🔎  Buscar texto
    🧠  Repasar (modo ficha)
    📝  Hazme un test (autogenerado)
    🔗  Recursos de un apunte
    📚  Generar temario Markdown
    📊  Estadísticas
```

Al **editar** desde el menú nunca borra tu contenido sin avisar: te pregunta
si quieres añadir texto al final, escribir desde cero (con confirmación) o no
tocarlo.

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
| `limpiar`          | Borrar en bloque una asignatura o etiqueta        | `apuncli limpiar -t sin-usar`        |
| `abrir`            | Abrir un apunte en tu editor (`$EDITOR`)          | `apuncli abrir 3`                    |
| `exportar`         | Exportar a Markdown (salida estándar)             | `apuncli exportar --todos > apuntes.md` |
| `importar`         | Importar desde un Markdown                        | `apuncli importar apuntes.md`        |
| `repasar`          | Repaso tipo ficha, uno a uno                      | `apuncli repasar -a ED -n 10`        |
| `test`             | Test automático a partir de tus apuntes           | `apuncli test -t examen`             |
| `recurso` (`rec`)  | Adjuntar/abrir enlaces y ficheros a un apunte     | `apuncli recurso anadir 3 https://…` |
| `temario`          | Índice Markdown completo (para imprimir o PDF)    | `apuncli temario -a ED > temario.md` |
| `hoy`              | Plan rápido: qué estudiar hoy                     | `apuncli hoy`                        |
| `etiquetas`        | Ver etiquetas; o añadir/quitar las de un apunte   | `apuncli etiquetas --anadir 3 repaso` |
| `asignaturas`      | Ver las asignaturas existentes                    | `apuncli asignaturas`                |
| `stats`            | Estadísticas de estudio                           | `apuncli stats`                      |
| `respaldo` (`backup`) | Copia de seguridad y restauración               | `apuncli respaldo hacer`             |
| `completar`        | Configurar el autocompletado (TAB)                | `eval "$(apuncli completar)"`         |
| `demo`             | Apuntes de ejemplo para probarlo todo             | `apuncli demo`                       |
| `acciones`         | Listar las acciones de `acciones.json` (`--json`) | `apuncli acciones`                   |
| `validar`          | Comprobar `acciones.json` (código 3 si falla)     | `apuncli validar`                    |
| `ejecutar`         | Ejecutar una acción (`--simular`, `--si`, `--json`) | `apuncli ejecutar ordenar-descargas ~/Descargas --simular` |
| `comprobar-ia`     | Probar la conexión con el modelo de IA            | `apuncli comprobar-ia`               |

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

### `borrar` y `limpiar`

`borrar` pide confirmación salvo que pases `--si`. `limpiar` borra en bloque
todos los apuntes de una asignatura o etiqueta, enseñando antes la lista:

```bash
apuncli borrar 5                 # pregunta antes
apuncli borrar 5 --si            # sin preguntas
apuncli limpiar -t sin-usar     # borra todos los apuntes con esa etiqueta
apuncli limpiar -a "Asignatura vieja"
```

## Acciones externas: acciones.json

Además de gestionar apuntes, `apuncli` ejecuta **acciones sobre tus ficheros**
que **no están escritas en el código**: se definen en `acciones.json` (la
configuración externa; ver el `acciones.json` de ejemplo del repo y el
[ADR-0001](docs/adr/0001-configuracion-externa.md)). Crear una acción nueva no
exige tocar Python.

```bash
$ apuncli acciones                          # ver las acciones definidas
$ apuncli validar                           # esquema OK… o te dice el campo que falla
$ apuncli ejecutar ordenar-descargas --simular   # enseña qué haría SIN tocar nada
$ apuncli ejecutar ordenar-descargas             # pregunta antes de mover
$ apuncli ejecutar limpiar-temporales ~/pruebas --si   # para scripts
$ apuncli ejecutar respaldo-pdfs --json | jq .hechos   # salida para máquinas
```

| Tipo | Qué hace | Campos |
| ---- | -------- | ------ |
| `mover` / `copiar` | mueve/copian los ficheros que pasan el filtro | `origen` (u opción), `destino`, `filtro` |
| `renombrar` | renombra con plantilla: `{fecha:%Y-%m-%d}`, `{n:03}`, `{ext}`, `{nombre}` | `plantilla`, `filtro` |
| `borrar` | borra lo que pasa el filtro (**filtro obligatorio**) | `filtro`, `confirmar` |
| `duplicados` | informe de duplicados por hash SHA-256 (no borra) | `filtro` opcional |
| `generar-temario` | temario Markdown (CARPETA = asignatura) | — |
| `resumir-ia` / `generar-preguntas-ia` | ven más abajo | — |

`filtro` admite `extensiones` (lista), `patron` (regex sobre el nombre) y
`mas_antiguo_que_dias` (entero). Las rutas con `~` se expanden. Seguridad:
los tipos destructivos preguntan salvo con `--si`, y **nunca se pisa un
fichero existente** (se añade `-1`, `-2`…).

**Códigos de salida**: `0` bien · `1` fallo al ejecutar · `2` error de uso ·
`3` configuración inválida (con `apuncli validar` o JSON roto). Ejemplo de
caso feo controlado:

```bash
$ apuncli --config malas.json validar
error de configuración:
  · acciones[0].nombre: 'MAL' no vale; usa minúsculas, dígitos y guiones (ej: 'ordenar-apuntes').
  · acciones[0].tipo: falta (esperado uno de: borrar, copiar, duplicados, …).
$ echo $?
3
```

## IA: resumir y generar preguntas (con modo sin red)

Dos acciones usan el modelo del centro (Ollama u otra API OpenAI-compatible):

```bash
apuncli ejecutar resumir-ia 3                    # resume el apunte 3 (5-8 viñetas)
apuncli ejecutar generar-preguntas-ia 3          # preguntas => respuestas para 'apuncli test'
apuncli comprobar-ia                             # ¿está el modelo disponible?
```

- **La clave nunca está en el repo**: vive en `ia.env` o `.env` (ambos en
  `.gitignore`, con [.env.example](.env.example) documentado). Variables:
  `APUNCLI_IA_URL`, `APUNCLI_IA_CLAVE`, `APUNCLI_IA_MODELO` (por defecto
  `qwen3:8b`). También puedes señalar el fichero con `APUNCLI_ENV`.
- **Modo sin red**: si no hay conexión, falta la clave o el modelo no
  responde, la CLI **no revienta**: lo explica en una frase y **todo lo demás
  sigue funcionando igual** (justificación: [ADR-0002](docs/adr/0002-capa-ia-sin-red.md)).
- `generar-preguntas-ia` puede guardar las preguntas en el apunte: entran
  directamente en `apuncli test`.

```bash
$ apuncli comprobar-ia            # (sin el centro cerca)
⚠️  IA no disponible
  proveedor: http://192.168.1.50:11434/v1
  modelo:    qwen3:8b
  detalle:   No hay conexión con el proveedor de IA… Sin red la CLI sigue
             funcionando con las acciones que no necesitan IA.
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

# Sábado: organizar (borrar en bloque lo viejo y copias de seguridad)
apuncli limpiar -t apuntes-antiguos
apuncli respaldo hacer
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

`apuncli test` te prepara el examen **él solo**, sin que escribas nada: lee el
contenido de tus apuntes y genera preguntas con reglas simples:

- **Huecos** con términos que remarcaste en **negrita**: `La **pila** es LIFO` →
  «Completa: La ______ es LIFO».
- **Definiciones**: frases tipo `La pila es una estructura LIFO` → «¿qué es
  pila?» con la respuesta exacta.
- **Listas** bajo un apartado `## Operaciones` con 3+ items → «Nombra
  elementos de «Operaciones»» con opción múltiple (a/b/c/d).

Y si además escribes tus propias preguntas, mandan sobre las automáticas:

```markdown
**Pregunta:** ¿Qué coste tiene pop?
**Respuesta:** O(1).
```

Corrige con tolerancia (ignora mayúsculas, acentos y puntuación) y te da la
**nota sobre 10**:

```bash
$ apuncli test -a ED -t examen
Test con 3 pregunta(s). Responde con tus palabras (Enter vacío para saltar, 'q' para salir).

─ Pregunta 1/3 · de 'Tema 3: pilas y colas' ─
¿Qué coste tiene pop?
Tu respuesta: O(1)
✔ ¡Correcto!
...
Resultado: 3/3 · nota 10.0/10
```

`apuncli test --auto` fuerza solo las generadas. Cada respuesta cuenta también
como repaso del apunte. Truco para más preguntas: escribe tus apuntes con
definiciones claras, términos en negrita y listas; el test mejorará solo.

## ¿Qué estudio hoy?

`apuncli hoy` (o la primera opción del menú) te dice de un vistazo qué tienes
sin repasar, qué apuntes tienen preguntas para test y cuáles tocaste hace poco,
con una sugerencia de comando para ponerte.

## Copia de seguridad

Tus apuntes solo viven en un fichero (`~/.apuncli/apuncli.db`), así que
conviene tener red de seguridad:

```bash
apuncli respaldo hacer     # copia de seguridad ahora (junto a la base de datos)
apuncli respaldo listar    # ver las copias que tienes
apuncli respaldo restaurar # restaurar la copia más reciente (pregunta antes)
```

## Autocompletado con TAB

Añade esta línea a tu `~/.bashrc` y reinicia la terminal:

```bash
eval "$(apuncli completar)"
```

A partir de ahí, el TAB autocompleta comandos, ids de apuntes (`apuncli ver 9<TAB>`)
y los valores de `-a`/`-t` con tus asignaturas y etiquetas reales.

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
├── acciones.json            # TUS acciones (fuera del código) · esquema en config.py
├── .env.example             # plantilla de la config de IA (ia.env/.env: ignorados)
├── CHANGELOG.md             # historia de versiones
├── AGENTS.md · opencode.json · .opencode/   # reglas para el agente
├── docs/                    # spec, ADRs y prompts del proceso
├── .github/workflows/       # CI: ubuntu + windows + macos
├── src/apuncli/
│   ├── __main__.py          # entrypoint: main()
│   ├── argumentos.py        # parser de comandos (argparse), despacho y códigos de salida
│   ├── comandos.py          # lógica de cada comando (cmd_*)
│   ├── interfaz.py          # menú interactivo (el 'apuncli' a secas)
│   ├── db.py                # capa de datos SQLite (tablas, CRUD, búsqueda)
│   ├── config.py            # esquema + validador estricto de acciones.json
│   ├── motor.py             # ejecuta acciones sobre ficheros (simular, colisiones…)
│   ├── ai.py                # proveedor IA (OpenAI-compatible) + acciones IA
│   ├── formato.py           # Markdown <-> apunte, preguntas de test
│   ├── recursos.py          # detectar/abrir URLs y ficheros adjuntos
│   ├── temario.py           # generación de índices/temarios Markdown
│   ├── testmotor.py         # motor del test automático
│   ├── errores.py           # excepciones propias (ConfigError, SinRedError…)
│   └── ui.py                # colores, editor y menús con flechas (termios/tty)
└── tests/
    ├── test_db.py           # capa de datos
    ├── test_formato.py      # exportación / importación
    ├── test_novedades.py    # recursos, temario y test automático
    ├── test_cli.py          # comandos de extremo a extremo
    └── test_acciones.py     # pytest: config/motor/validador/IA (casos feos)
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

## Guía para desarrollar (o ampliar el proyecto)

Si quieres tocar el código (o proponer una función nueva):

1. `git clone` tu repositorio y `cd apuncli`.
2. Instala en modo editable o ejecuta directo: `pip install -e .` o bien
   `PYTHONPATH=src python3 -m apuncli ...`.
3. Los tests son tu red de seguridad: **ejecuta siempre antes y después de
   tocar nada**:

   ```bash
   python3 -m unittest discover -s tests
   ```

4. ¿Nuevo comando? La receta:
   - define la opción en `argumentos.py` (`sub.add_parser(...)`,
     `p.add_argument(...)`);
   - escribe la lógica en `comandos.py` (`def cmd_...`) apoyándote en `db.py`;
   - despachalo en `_despachar()`;
   - añade un test en `tests/` (mira `test_cli.py` para copiar el patrón);
   - si debe estar en el menú, añade su línea en `interfaz.py` (lista
     `ACCIONES` y su rama en `_ejecutar`).
5. ¿Cambio en la base de datos? Añade la tabla/columna en `db.inicializar()`
   (usa `CREATE TABLE IF NOT EXISTS` para no romper bases de datos viejas) y
   prueba a abrir una base antigua con el código nuevo.
6. Estilo: comentarios y strings de cara al usuario en español; ids y
   funciones en snake_case; errores de usuario = `ApuncliError` (el CLI los
   imprime en rojo y devuelve código 1).

## Tests

Todo corre en **carpetas temporales** o con `APUNCLI_DB` apuntando a una base de
prueba: las pruebas no tocan nunca tus apuntes reales.

```bash
python3 -m unittest discover -s tests   # 62 tests (solo stdlib)
python3 -m pytest tests/                # 82 tests (necesita pytest)
```

`tests/test_acciones.py` (pytest) cubre el camino feliz **y los casos feos**:
JSON roto o con campos mal (señala el campo exacto), borrar sin filtro,
nombres repetidos, carpetas inexistentes, colisiones al mover, ficheros con
tildes y espacios, IA sin clave, sin red y con proveedor simulado. Las
ejecuta **GitHub Actions en ubuntu, windows y macos** en cada push
([.github/workflows/tests.yml](.github/workflows/tests.yml)).

## Licencia

[MIT](LICENSE) — úsalo, cópialo y modifícalo con total libertad.
