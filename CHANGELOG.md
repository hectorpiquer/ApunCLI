# Changelog

Formato *Keep a Changelog*; versiones según *Semantic Versioning*.

## [1.0.3] · 2026-11-23

### Añadido
- La capa IA entiende las variables del centro (`CENTRO_IA_URL`, `CENTRO_IA_KEY`,
  `CENTRO_IA_MODELO`, `CENTRO_IA_CA`): las mismas que ya usa OpenCode, así que
  tu CLI habla con el servidor del instituto sin configurar dos veces.
- Soporte de HTTPS con certificado propio (el del centro): `ssl` con CA
  opcional desde `CENTRO_IA_CA` / `NODE_EXTRA_CA_CERTS`.

## [1.0.2] · 2026-11-23

Tras una auditoría completa del proyecto (rúbrica + revisión de código).

### Añadido
- **Repaso con repetición espaciada** (SM-2 simplificado): cada repaso programa
  el siguiente (1, 3, 7, 14, 21, 30 y +30 días). `apuncli hoy` te dice qué toca
  hoy; `apuncli repasar --cola` pasa solo esa cola. Las bases de datos viejas
  se migran solas y sus apuntes entran en la cola.
- `--json` en `buscar`, `stats` y `ver` (la ficha completa con recursos).
- 15 pruebas nuevas: los 6 `--json`, el fallo del motor por consola (código 1),
  base de datos sin permisos, config que es un directorio, `copiar`,
  `generar-temario` por orden, recurso con ruta inexistente y el repaso
  espaciado con su migración. 110 tests pytest en total.

### Arreglado
- `apuncli` ya no suelta un traceback si `APUNCLI_DB` apunta a una ruta sin
  permisos o dañada: mensaje humano y código 1.
- `recurso anadir` con un fichero que no existe ahora falla al añadir (antes
  lo aceptaba y el error salía al abrirlo).
- `--config` apuntando a un directorio sale con 3 y sin traceback.
- Motor multiplataforma: si el destino no se puede crear o un fichero
  desaparece a mitad de la acción, error/omisión limpios sin traceback.
- Acción inexistente: el error se muestra como problema de configuración
  (bloque ordenado, código 3) en lugar de un mensaje genérico a código 1.
- El docstring del motor dejaba entrever transaccionalidad: ahora dice la
  verdad (sin rollback: `--simular` siempre primero).

### Cambiado
- `docs/spec` y README reflejan los cinco códigos de salida (0/1/2/3/4).
- La configuración del agente (`AGENTS.md`, `opencode.json`, `.opencode/`) ya
  no se versiona: es herramienta de clase, no de la CLI.

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
