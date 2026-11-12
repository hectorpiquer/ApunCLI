# ADR-0001 · Las acciones viven fuera del código (acciones.json)

**Fecha**: 2026-11-10 · **Estado**: Aceptado

## Contexto

`apuncli` ya maneja apuntes (crear, buscar, repasar, test). El siguiente paso era
añadir acciones sobre ficheros del sistema: ordenar descargas, limpiar temporales,
renombrar fotos por fecha, detectar duplicados, respaldar PDFs…

La tentación era escribir cada acción como una función y su comando en Python
(`apuncli ordenar-descargas`). Rápido de hacer… y un lastre: cada acción nueva
significaría tocar el código, revalidar tests y actualizar la ayuda.

## Decisión

Las acciones se **describen**, no se programan. Un fichero `acciones.json` en la
carpeta donde se lanza la orden define `nombre`, `descripcion`, `tipo`
(`mover`, `copiar`, `renombrar`, `borrar`, `duplicados`, `resumir-ia`,
`generar-preguntas-ia`, `generar-temario`), `filtro` (extensiones, patrón regex,
edad en días), `plantilla`, `destino` y `confirmar`.

El código solo conoce los **tipos**; el **motor** (`motor.py`) los interpreta sobre
cualquier carpeta. `config.py` valida el JSON ANTES de ejecutar nada y señala el
campo exacto que falla. Añadir una acción nueva no exige tocar una línea de Python.

## Consecuencias

- ✅ El usuario amplía la herramienta sin saber programar.
- ✅ `apuncli validar` + código de salida 3: un JSON roto se explica, no rompe.
- ✅ Seguridad: `--simular` primero y `confirmar` en los tipos destructivos.
- ⚠️ Un JSON sin validar sería peligroso (borrar sin filtro); por eso el validador
  exige filtro en `borrar` y plantilla en `renombrar`.
- ⚠️ El esquema es propio: si algún día cambia, la clave `version` del fichero
  dirá qué lector usar.
