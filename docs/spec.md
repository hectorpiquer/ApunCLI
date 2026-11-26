# Spec de apuncli (10 líneas)

**Para quién**: estudiantes (DAM) que toman apuntes en Markdown y quieren estudiar desde la terminal.
**Qué problema resuelve**: apuntes dispersos en ficheros sueltos, sin búsqueda, sin repaso, sin test; y ficheros de descargas sin organizar.
**Qué hace**: dos modos. **Estudio**: guarda apuntes en SQLite, busca (FTS5), repasa con
intervalos (SM-2), genera tests, temarios, respaldos. **Organizador**: explora, crea
documentos, ordena descargas, quita duplicados y temporales, y renombra/clasifica con IA.
Ambos ejecutan acciones definidas fuera del código en `acciones.json`.
**Capa IA**: resume apuntes y genera preguntas de examen con el modelo del centro (Ollama/OpenAI-compatible).
**Órdenes principales**: crear, listar/acciones/ejecutar/comprobar-ia/buscar/stats/ver (`--json`),
repasar, test, temario, respaldo, `acciones`, `validar`,
`ejecutar NOMBRE [carpeta|apunte|asignatura] --simular|--si`, `comprobar-ia`.
**Configuración externa**: acciones en `acciones.json`; IA en `.env`/`ia.env` (jamás en el repo).
**Qué NO hará**: sustituir a un LLM de propósito general, sincronizar en la nube ni GUI.
Lo destructivo: siempre ver la lista antes y confirmar.
**Códigos de salida**: 0 bien · 1 fallo al ejecutar · 2 error de uso · 3 configuración
inválida o acción inexistente · 4 IA no disponible (el resto sigue funcionando).
**Instalación**: `uv tool install` / `pipx install` desde GitHub; comando `apuncli` global.
