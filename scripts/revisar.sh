#!/usr/bin/env bash
# Revisa lo que vas a commitear con el subagente revisor (solo lectura), sin abrir la TUI.
# Uso: git add … && scripts/revisar.sh   (0 si el revisor dice OK, 1 si CAMBIAR)
# El diff entra por stdin: el agente no necesita permiso para leerlo.
# Sin nadie delante, un permiso "ask" es "deny" por diseño: NUNCA uses --auto.
set -euo pipefail
cd "$(dirname "$0")/.."

if git diff --staged --quiet; then
    echo "No hay nada preparado: haz git add primero." >&2
    exit 1
fi

if ! command -v opencode >/dev/null 2>&1; then
    echo "opencode no está instalado: el script no puede revisar (no es obligatorio)." >&2
    exit 0
fi

if ! git diff --staged | timeout 180 opencode run --agent revisor \
    "Revisa este diff (te llega por la entrada estándar) con tus normas. Acaba con una línea: VEREDICTO: OK o VEREDICTO: CAMBIAR."; then
    echo "El revisor no terminó (timeout o error): trata el cambio con sospecha." >&2
    exit 1
fi
