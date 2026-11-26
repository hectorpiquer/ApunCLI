# Guion de defensa · apuncli (6 minutos, con demostración en vivo)

> Todo lo que demuestro aquí lo probé contra el código y contra el servidor
> del centro. Cada orden, ejecutable tal cual.

## 0 · Apertura (30 s)

Repo: `github.com/hectorpiquer/ApunCLI` — 4 releases (v1.0.4→v1.0.7), 3 PRs
fusionados, CI en ubuntu/windows/macOS, 144 pruebas pytest + 62 unittest.
Una herramienta, dos modos: **estudio** (apuntes) y **organizador** (ficheros).

## 1 · Existe e instala en una orden (60 s)

```bash
uv tool install git+https://github.com/hectorpiquer/ApunCLI.git@v1.0.7
apuncli version          # apuncli 1.0.7
apuncli --help
```

Muestro: `--help` completo (argparse), ayuda de subcomando (`ejecutar --help`),
y que `python -m apuncli` también funciona (entry point bien declarado).

## 2 · Acciones externas, sin tocar código (60 s)

```bash
apuncli acciones                       # las 8 del JSON de ejemplo
apuncli --config /nope/acciones.json validar    # → "error de configuración", $?=3
apuncli ejecutar ordenar-descargas --simular    # plan, no toca nada
```

Caso feo demostrado: JSON roto → campo exacto (`acciones[0].tipo: …`),
código **3**. Explico el ADR-0001: por qué fuera del código y qué gano.

## 3 · IA con modo sin red (90 s)

```bash
apuncli demo                       # crea apuntes de ejemplo
apuncli comprobar-ia --json        # ✅ con el centro (ia.simarro)
apuncli listar --json | head       # id de un apunte (p. ej. 2)
apuncli ejecutar resumir-ia 2      # resumen real de un apunte
# modo sin red: la URL no existe → código 4 y el resto sigue vivo
APUNCLI_IA_URL=http://127.0.0.1:9/v1 apuncli ejecutar resumir-ia 2; echo $?
```

Explico el ADR-0002: clave en `ia.env` (gitignored, historial limpio),
`CENTRO_IA_*` como OpenCode, saneado del nombre propuesto por el modelo
(`../../etc/shadow` → `etc-shadow.md`) y por qué un ProveedorFalso (tests
sin red, sin clave, sin tokens).

## 4 · Robustez ofensiva (90 s) — "¿y si…?"

| Ataque que hago en vivo | Qué responde |
| --- | --- |
| `apuncli organizar espacio /` | no recorre `/proc`/`/sys`/`/dev`, sin permisos → omitido, en décimas de segundo |
| `apuncli organizar espacio /etc/passwd` | "es un fichero, no una carpeta" |
| `apuncli crear-doc /ruta/~rara/x.md` | error humano, sin traceback |
| enlace simbólico en `duplicados --borrar` | el enlace se omite; la víctima, intacta |
| `apuncli ver abc` / `ejecutar inventada` | $1 y $3 con mensaje útil |
| `respaldo restaurar` | pregunta siempre ($2 si sin terminal) |

Cierre: ningún camino previsible acaba en traceback; lo demuestro con el
código de salida (`echo $?`) en cada uno.

## 5 · Pruebas y proceso (60 s)

```bash
python -m pytest tests/            # 144
python -m unittest discover -s tests   # 62
```

- Caja de arena (`conftest.py`): ninguna prueba toca mis carpetas ni la red.
- **Mutación** que hice a propósito (sesión 4, paso 3): saqué el `mkdir` del
  `if not simular` → 2 pruebas en rojo → devuelto → verde. Lo cuento y lo
  tengo anotado en `docs/prompts.md`.
- Historial: commits pequeños que cuentan el proceso, ramas `release-1.0`,
  PRs, CHANGELOG, `docs/adr/` (3 decisiones justificadas), `docs/spec.md`.

## 6 · La puse a trabajar de verdad (30 s)

```bash
apuncli registro
```

Muestro el log: ordenó mis descargas reales (53 ficheros), borró 7 duplicados
verificados por hash, e hizo copias de seguridad. El hilo del proyecto 2
cerrado: detecté la tarea → una orden → la reutilizo.

## Batería de preguntas (y dónde está la respuesta)

1. **¿Por qué JSON y no código?** → ADR-0001 + el validador en `config.py`.
2. **¿Qué viaja por la red en una acción IA?** → system+user al `/v1/chat/completions`;
   clave en cabecera, jamás en repo (`ia.env` gitignored, historial auditado).
3. **¿Qué pasa sin red?** → código 4 + mensaje; `comprobar-ia` lo diagnostica.
4. **¿Qué protege `--simular`?** → `test_simular_no_toca_nada` y la mutación.
5. **¿Por qué ProveedorFalso?** → pruebas deterministas sin red ni gasto.
6. **¿Qué corregiste del agente?** → rutas Windows (`~` en `C:\Users\RUNNER~1`),
   `/dev/null` en un test, el CHANGELOG inflado, la extensión duplicada de
   `a_nombre_seguro` (en `docs/prompts.md`).
7. **¿Por qué dos modos?** → ADR-0003; mismo motor, mismo `--help`, mismos
   códigos de salida.
8. **¿Qué harías si cambia el esquema?** → campo `version` en acciones.json +
   lector por versión (mencionado en el ADR-0001).

## Cierre (15 s)

"La herramienta la uso a diario: el registro de `apuncli registro` es la
prueba de que la utilicé para ordenar mis propios ficheros antes de entregar."
