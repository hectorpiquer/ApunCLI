#!/usr/bin/env bash
# Revisa lo que vas a commitear con el subagente revisor (solo lectura), sin abrir la TUI.
# Uso: git add … && scripts/revisar.sh   (sale con 0 si el revisor dice OK, 1 si CAMBIAR)
# El diff entra por la entrada estándar: el agente no necesita permiso para leerlo.
# timeout 180: si el servidor del centro no responde, el script no se queda colgado.
# Sin nadie delante, un permiso "ask" se trata como "deny": por eso NUNCA --auto.
set -euo pipefail
cd "$(dirname "$0")/.."

if git diff --staged --quiet; then
    echo "No hay nada preparado: haz git add primero." >&2
    exit 1
fi

if ! command -v opencode >/dev/null 2>&1; then
    echo "opencode no está instalado en esta máquina (no es obligatorio para el proyecto)." >&2
    exit 0
fi

revision=$(git diff --staged | timeout 180 opencode run --agent revisor \
  "Revisa este diff (te llega por la entrada estándar) con tus normas. Acaba con una línea: VEREDICTO: OK o VEREDICTO: CAMBIAR.")

echo "$revision"
grep -q "^VEREDICTO: OK" <<< "$revision"
