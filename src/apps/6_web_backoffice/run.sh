#!/bin/bash
# Script para activar el entorno virtual y ejecutar la aplicación Reflex

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activar el entorno virtual del backoffice (Python 3.13)
source "$ROOT_DIR/.venv_backoffice313/bin/activate"

# Ejecutar la aplicación Reflex desde la ruta actual
export PYTHONPATH="$ROOT_DIR"

# Parchar vite.config.js para permitir hosts personalizados (si existe .web/)
if [ -d "$SCRIPT_DIR/.web" ]; then
    python "$SCRIPT_DIR/patch_vite_config.py" 2>/dev/null || true
fi

reflex run

