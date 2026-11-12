# AGENTS.md · Reglas para agentes en este repo

## Lo que es

CLI en Python (solo stdlib, sin dependencias) para gestionar apuntes de estudio
y acciones sobre ficheros definidas en `acciones.json`.

## Reglas del proyecto

- Python ≥ 3.10, **solo librería estándar** (nada de pip install para el runtime).
- Rutas siempre con `pathlib`, nunca concatenando strings.
- Todo `open`/`read_text`/`write_text` con `encoding="utf-8"` explícito.
- Nada de `shell=True` ni `os.system`: ficheros con `shutil`, procesar con `subprocess.run([...])`.
- Mensajes de error al usuario en español, humanos, sin traceback.
- Códigos de salida: 0 bien · 1 fallo al ejecutar · 2 error de uso · 3 configuración inválida.
- Claves secretas: NUNCA en el repo (usa `ia.env`/`.env`, ya en `.gitignore`).
- Pruebas SIEMPRE en carpetas temporales (`tmp_path`), nunca sobre ficheros reales del usuario.
- Los tests usan la base de datos de prueba (`APUNCLI_DB`); no reescribir la real.

## Órdenes del proyecto

- Tests: `python3 -m unittest discover -s tests` (o `pytest tests/`)
- Ejecutar desde el repo: `PYTHONPATH=src python3 -m apuncli <comando>`
- Prueba aislada: `APUNCLI_DB=/tmp/prueba.db PYTHONPATH=src python3 -m apuncli demo`
- Empaquetado: `pyproject.toml` (entry point `apuncli`).

## Qué NO tocar sin preguntar

- No hacer `git push`, no crear commits (los hace el humano al final del paso).
- No borrar ni reescribir los tests existentes sin justificación.
- No tocar `db.py` sin correr la suite antes y después.
