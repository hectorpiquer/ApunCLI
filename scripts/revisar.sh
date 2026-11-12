#!/usr/bin/env bash
# Revisión sin pantalla con OpenCode (semana 4): el subagente revisor audita
# los cambios antes del commit. Uso: scripts/revisar.sh
set -euo pipefail
cd "$(dirname "$0")/.."
opencode run --agent revisor "Revisa los cambios sin commitear (git diff). Busca: errores, casos feos sin control, claves en el repo, cosas que romperían 'apuncli validar' o los tests. Sé breve." 
