# Prompts clave usados con OpenCode

Los prompts que dirigieron las etapas importantes del proyecto (con el agente
leyendo el repo y yo aprobando cada diff). Formato: qué pedí y qué salió.

## 1. Espec y esqueleto (semana 1)

> "Quiero una CLI en Python para gestionar apuntes de estudio de DAM: SQLite +
> FTS5, Markdown en el contenido, sin dependencias externas. Dame la spec de
> 10 líneas y el esqueleto del paquete con argparse y entry point."

Resultado: `docs/spec.md`, paquete `src/apuncli` con `db.py`, `argumentos.py`,
`pyproject.toml` con `apuncli = "apuncli.__main__:main"`.

## 2. Motor de búsqueda y formato

> "El contenido de los apuntes es Markdown. El buscador debe ignorar tildes y
> mayúsculas (FTS5 con texto normalizado). Escribe primero los tests."

Resultado: `formato.py` + tests de normalización (acentos, ñ, títulos).

## 3. Test y repaso (semana… «sin IA»)

> "Genera preguntas automáticamente desde listas Markdown y negritas (tipo
> hueco y definición). La corrección debe tolerar acentos y mayúsculas, y
> admitir letra de opción a-d. Sin usar IA."

Resultado: `testmotor.py` con `es_correcta` tolerante.

## 4. Sistema de acciones externas (proyecto 2, semana 2)

> "Quiero que las acciones sobre ficheros vivan en acciones.json, no en el
> código: mover/renombrar/copiar/borrar/duplicados con filtros (extensiones,
> regex, días). El validador debe decir el campo exacto que falla y salir con
> código 3. Ejecutar admite --simular y --si, y nunca pisa ficheros existentes."

Resultado: `config.py` (validador), `motor.py` (con `_sin_colision` y
transaccionalidad básica), `errores.py` con excepciones propias.

## 5. Capa IA con modo sin red (semana 3)

> "Dos acciones IA (resumir y generar-preguntas) vía OpenAI-compatible contra
> Ollama del centro. Clave en ia.env (gitignored). Sin clave o sin red: mensaje
> en una línea y todo lo demás sigue funcionando. Añade comprobar-ia --json."

Resultado: `ai.py` con `SinRedError` y `comprobar()`.

## 6. Casos feos y release

> "Pruébalo todo con: JSON roto, ruta inexistente, nombre repetido en acciones,
> carpetas con tildes, borrado sin filtro. Ningún traceback, siempre código de
> salida claro."

Resultado: suite pytest de casos feos en carpetas temporales.
