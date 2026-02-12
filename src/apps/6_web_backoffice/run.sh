#!/bin/bash
# Script para activar el entorno virtual y ejecutar la aplicación Reflex
#
# Uso:
#   ./run.sh          - Inicia normalmente
#   ./run.sh --clean  - Limpia caches antes de iniciar (recomendado después de cambios en State)

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Verificar si se solicitó limpiar caches
CLEAN_CACHE=false
if [[ "$1" == "--clean" ]] || [[ "$1" == "-c" ]]; then
    CLEAN_CACHE=true
fi

# Limpiar caches si se solicitó
if [ "$CLEAN_CACHE" = true ]; then
    echo "=========================================="
    echo "Limpiando caches de Reflex..."
    echo "=========================================="

    if [ -f "$ROOT_DIR/clear_caches.sh" ]; then
        cd "$ROOT_DIR"
        bash clear_caches.sh
        cd "$SCRIPT_DIR"
    else
        echo "ADVERTENCIA: clear_caches.sh no encontrado en $ROOT_DIR"
        echo "Limpiando caches localmente..."
        rm -rf "$SCRIPT_DIR/.web/.vite" 2>/dev/null || true
        rm -rf "$SCRIPT_DIR/.web/node_modules" 2>/dev/null || true
        rm -rf "$SCRIPT_DIR/.states" 2>/dev/null || true
        find "$SCRIPT_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
    fi

    echo ""
    echo "Caches limpiadas. Iniciando backoffice..."
    echo ""
fi

# Activar el entorno virtual del backoffice (Python 3.13)
source "$ROOT_DIR/.venv_backoffice313/bin/activate"

# Ejecutar la aplicación Reflex desde la ruta actual
export PYTHONPATH="$ROOT_DIR"

# Parchar vite.config.js para permitir hosts personalizados (si existe .web/)
if [ -d "$SCRIPT_DIR/.web" ]; then
    python "$SCRIPT_DIR/patch_vite_config.py" 2>/dev/null || true
fi

reflex run

