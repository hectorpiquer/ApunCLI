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


## 7. Semana 4: pruebas, mutación y release

> "Antes de escribir las pruebas, dime qué fixtures en conftest.py garantizan que
> ninguna prueba toca mis carpetas reales ni llama al servidor del centro. Casos
> feos: JSON roto, borrar sin filtro, colisiones, IA sin clave/red/simulada."

### La mutación que hice a propósito (paso 3)

Saqué `destino.mkdir()` del `if not simular:` en `motor.py` (también creaba la
carpeta al simular), guardé y pasé pytest. Se pusieron en rojo DOS pruebas:
`test_simular_no_toca_nada` (pytest) y `test_ejecutar_simular_desde_la_orden_no_toca_el_disco`
(CLI por fuera). Devuelto con `git checkout`, las 94 otra vez en verde.
Conclusión: las pruebas protegen de verdad, no decoran.

### Qué corregí de lo que hizo el agente

- **CHANGELOG**: el borrador mencionaba funciones internas (`hash_de`) con
  detalle de implementación; lo reescribí mirando a quien USA la herramienta.
- **Tests de IA en la CI**: el agente los dejó sin aislar del todo y Windows
  se colgaba/reintentaba contra direcciones reales. Fix: `conftest.py` con
  `aislado` (autouse) + IP de documentación 192.0.2.1 + proxy falso.
- **Rutas Windows**: la detección de ficheros no aceptaba `\` ni `~` en rutas
  (`C:\Users\RUNNER~1\...`): era un fallo real multiplataforma que solo se
  veía en Actions, no en mi Linux. Arreglado en `recursos.py` con su prueba.
- **`test_hash_de_estable`**: usaba `/dev/null`, que no existe en Windows.
  Reescrito con ficheros temporales.
