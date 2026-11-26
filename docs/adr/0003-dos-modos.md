# ADR-0003 · Dos modos en una sola herramienta

**Fecha**: 2026-11-26 · **Estado**: Aceptado

## Contexto

La herramienta nació como gestor de apuntes de estudio (modo **Estudio**). Al
añadirle el sistema de acciones externas aparecieron los usos del "modo
**Organizador**": ordenar descargas, quitar duplicados, limpiar temporales,
renombrar fotos… Esas tareas no son de estudio, pero sí de la misma vida
digital, y usar dos herramientas distintas para una misma terminal es peor
que usar una.

## Decisión

Una CLI, dos modos, un gate al arrancar (sin comandos): un selector con
flechas pregunta **Estudio u Organizador**; la última elección se recuerda
en `~/.apuncli/config.json` y se puede forzar con `--modo`. El modo
organizador (`organizador.py` puro + `organizador_menu.py` de TUI) reutiliza
el **Motor**, `recursos.abrir` y la capa IA existente; nada de UI nueva
pesada (sin Rich: colores propios, flechas propias).

Lo destructivo sigue la misma regla que las acciones del modo estudio:
**listar lo que va a tocar → confirmar** (o `--si` en CLI, `--simular` antes).

## Consecuencias

- ✅ Una sola herramienta, un `--help`, unos códigos de salida, un `acciones.json`.
- ✅ Cada modo vive en su módulo: el de estudio no cambió ni una línea de lógica.
- ⚠️ El menú de estudio gana una opción ("cambiar de modo"): hay que mantenerlo corto.
- ⚠️ La TUI del explorador no se puede testear con pytest (no hay terminal en CI):
  se prueba el organizador puro, la CLI espejo y el gate por PTY (manual).
