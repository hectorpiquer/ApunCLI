---
name: acciones-json
description: Reglas del esquema de acciones.json de apuncli. Cargar al tocar acciones.
---

# Reglas de acciones.json

- Raíz: `{ "version": 1, "acciones": [ … ] }`. UTF-8, JSON estricto (sin comentarios).
- Cada acción: `nombre` (minúsculas, dígitos y guiones, único), `descripcion`
  (frase), `tipo`, y según tipo:
  - `mover` / `copiar`: `destino` (admite `~`), opcional `origen`, `filtro`.
  - `renombrar`: `plantilla` (`{fecha:%Y-%m-%d}`, `{n:03}`, `{ext}`, `{nombre}`) + `filtro`.
  - `borrar`: `filtro` OBLIGATORIO (nunca borrar sin filtro).
  - `duplicados`: solo informe, no borra nada.
  - `resumir-ia` / `generar-preguntas-ia`: sin campos extra; el "CARPETA" de la
    orden es el id del apunte. Necesitan ia.env; sin red avisan y no rompen.
  - `generar-temario`: CARPETA = nombre de asignatura (opcional).
- `filtro`: `extensiones` (lista con punto), `patron` (regex válida sobre el
  nombre), `mas_antiguo_que_dias` (entero).
- `confirmar`: true en destructivos por defecto; `--si` lo salta en scripts,
  `--simular` no toca nada.
- El validador (`apuncli validar`) rechaza: nombre repetido/mal, tipo unknown,
  borrar sin filtro, plantilla ausente, regex inválida → código de salida 3.
