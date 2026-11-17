# Changelog

Formato *Keep a Changelog*; versiones según *Semantic Versioning*.

## [1.0.1] · 2026-11-17

### Añadido
- `tests/conftest.py`: la caja de arena completa (carpeta temporal, HOME y
  USERPROFILE redirigidos, IA y red anuladas) aplicada a TODAS las pruebas.
- Las acciones con IA sin disponible salen con **código de salida 4** y un
  aviso de que el resto de la CLI sigue funcionando.
- Pruebas de la CLI desde fuera (una por código de salida: 0 · 1 · 2 · 3 · 4),
  `ejecutar --simular` probado a través de la orden, y casos feos del validador
  con `@pytest.mark.parametrize`.
- `scripts/revisar.sh` completo: el diff entra por stdin, `timeout 180` y el
  veredicto del revisor se convierte en el código de salida.

### Cambiado
- Sin cambios de comportamiento para el usuario: sigue `apuncli <orden>`.

## [1.0.0] · 2026-11-12

Primera release completa del proyecto.

### Añadido
- Sistema de acciones externas (`acciones.json`): `apuncli acciones`, `validar`
  (códigos de salida 0/1/2/3, errores que señalan el campo exacto) y `ejecutar`
  con `--simular`, `--si` y `--json`.
- Tipos de acción: `mover`, `copiar`, `renombrar`, `borrar`, `duplicados`
  (hash SHA-256), `generar-temario` — en `motor.py`, sin pisar nunca ficheros
  existentes (sufijos `-1`, `-2`…).
- Capa IA con modo sin red: `resumir-ia` y `generar-preguntas-ia` vía
  OpenAI-compatible (Ollama del centro, `qwen3:8b`), clave en `ia.env`/`.env`
  (jamás en el repo), `apuncli comprobar-ia` para el diagnóstico.
- `listar --json` y `acciones --json` para tuberías.
- Excepciones propias (`ConfigError`, `AccionNoValida`, `FalloEjecucion`,
  `SinRedError`) con mensajes humanos: ningún traceback ante errores previsibles.
- 20 tests pytest nuevos del sistema de acciones (caso feliz + casos feos, en
  carpetas temporales), además de los 62 unittest previos.
- CI en GitHub Actions: ubuntu · windows · macos en cada push.
- Documentación del proceso: `docs/spec.md`, ADR-0001 y ADR-0002,
  `docs/prompts.md`, `AGENTS.md`, `opencode.json`, skill + comando + revisor en
  `.opencode/`, `scripts/revisar.sh`, `.gitattributes` y `.env.example`.

### Cambiado
- `--simular` no crea siquiera las carpetas de destino (antes sí).
- La configuración de IA admite `ia.env` además de `.env`
  (variable `APUNCLI_ENV` para elegir el fichero).

## [0.x] · octubre–noviembre 2026

Historial del desarrollo del gestor de apuntes (ver `git log`): apuntes SQLite
+ búsqueda FTS5 con tolerancia de acentos, test y repaso sin IA, recursos,
temarios Markdown, respaldos, TUI con flechas, demo y completado bash.

[1.0.0]: https://github.com/hectorpiquer/ApunCLI/releases/tag/v1.0.0
