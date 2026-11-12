# Spec de apuncli (10 líneas)

**Para quién**: estudiantes (DAM) que toman apuntes en Markdown y quieren estudiar desde la terminal.
**Qué problema resuelve**: apuntes dispersos en ficheros sueltos, sin búsqueda, sin repaso, sin test.
**Qué hace**: guarda apuntes en SQLite, busca (FTS5), repasa, genera tests, temarios, respaldos
y ejecuta acciones definidas fuera del código en `acciones.json` (ordenar, limpiar, duplicados…).
**Capa IA**: resume apuntes y genera preguntas de examen con el modelo del centro (Ollama/OpenAI-compatible).
**Órdenes principales**: crear, listar (`--json`), buscar, repasar, test, temario, respaldo,
`acciones`, `validar`, `ejecutar NOMBRE [carpeta] --simular|--si`, `comprobar-ia`.
**Configuración externa**: acciones en `acciones.json`; IA en `.env`/`ia.env` (jamás en el repo).
**Qué NO hará**: sustituir a un LLM de propósito general, sincronizar en la nube ni GUI.
**Códigos de salida**: 0 bien · 1 fallo al ejecutar · 2 error de uso · 3 configuración inválida.
**Instalación**: `uv tool install` / `pipx install` desde GitHub; comando `apuncli` global.
