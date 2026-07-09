#!/bin/bash
# Script para activar el entorno virtual y ejecutar LAIM Web
#
# Puerto: 8009 (backend Reflex) / 3109 (frontend Vite)
#
# Uso:
#   ./run.sh          - Inicia normalmente
#   ./run.sh --clean  - Limpia caches antes de iniciar

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
    echo "Limpiando caches de Reflex (LAIM Web)..."
    echo "=========================================="

    if [ -f "$ROOT_DIR/clear_caches.sh" ]; then
        cd "$ROOT_DIR"
        bash clear_caches.sh
        cd "$SCRIPT_DIR"
    else
        echo "ADVERTENCIA: clear_caches.sh no encontrado en $ROOT_DIR"
        rm -rf "$SCRIPT_DIR/.web/.vite" 2>/dev/null || true
        rm -rf "$SCRIPT_DIR/.web/node_modules" 2>/dev/null || true
        rm -rf "$SCRIPT_DIR/.states" 2>/dev/null || true
        find "$SCRIPT_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
    fi

    echo ""
    echo "Caches limpiadas. Iniciando LAIM Web..."
    echo ""
fi

# Activar el entorno virtual dedicado para LAIM Web (Python 3.13)
source "$ROOT_DIR/.venv_laimweb313/bin/activate"

# Exportar PYTHONPATH para acceso a capas compartidas
export PYTHONPATH="$ROOT_DIR"

# Si no existe .web/, inicializar Reflex
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

FORUM_START="$SCRIPT_DIR/scripts/start_laim_forum.sh"
FORUM_STOP="$SCRIPT_DIR/scripts/stop_laim_forum.sh"

cleanup() {
    if [ -x "$FORUM_STOP" ]; then
        bash "$FORUM_STOP" || true
    fi
}
trap cleanup EXIT INT TERM

if [ -x "$FORUM_START" ]; then
    echo "Iniciando daemon del foro LAIM..."
    bash "$FORUM_START"
else
    echo "ADVERTENCIA: no se encontró $FORUM_START"
fi

cd "$SCRIPT_DIR"
echo "=========================================="
echo "LAIM Web — Puerto backend: 8009"
echo "LAIM Web — Puerto frontend: 3109"
echo "LAIM Foro — Daemon API: 8766"
echo "=========================================="
reflex run
