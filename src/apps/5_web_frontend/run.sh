#!/bin/bash
# Script para activar el entorno virtual y ejecutar la aplicación Reflex

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activar el entorno virtual del frontend (Python 3.13)
source "$ROOT_DIR/.venv_frontend313/bin/activate"

# Ejecutar la aplicación Reflex desde la ruta actual
export PYTHONPATH="$ROOT_DIR"

# Si no existe .web/, inicializar Reflex primero para generarlo
if [ ! -d "$SCRIPT_DIR/.web" ]; then
    echo "Inicializando Reflex (generando .web/)..."
    cd "$SCRIPT_DIR"
    reflex init --loglevel info 2>/dev/null || true
fi

# Parchar vite.config.js para permitir hosts personalizados
if [ -f "$SCRIPT_DIR/.web/vite.config.js" ]; then
    echo "Aplicando parche de allowedHosts..."
    python "$SCRIPT_DIR/patch_vite_config.py" 2>/dev/null || true
fi

cd "$SCRIPT_DIR"
reflex run
