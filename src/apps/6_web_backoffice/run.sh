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

# Cargar variables de entorno desde protected_values.py
PROTECTED_VALUES="$ROOT_DIR/infrastructure/environments/macbook/protected_values.py"
if [ -f "$PROTECTED_VALUES" ]; then
    echo "Cargando variables protegidas..."
    # Extraer y exportar variables SMS
    export SMS_API_URL=$(python3 -c "exec(open('$PROTECTED_VALUES').read()); print(sms_api_url)" 2>/dev/null || echo "")
    export SMS_API_KEY=$(python3 -c "exec(open('$PROTECTED_VALUES').read()); print(sms_api_key)" 2>/dev/null || echo "")
    export SMS_SENDER_ID=$(python3 -c "exec(open('$PROTECTED_VALUES').read()); print(sms_sender_id)" 2>/dev/null || echo "")
    echo "  → Variables SMS cargadas"
fi

# Si no existe .web/, inicializar Reflex primero para generarlo
if [ ! -d "$SCRIPT_DIR/.web" ]; then
    echo "Inicializando Reflex (generando .web/)..."
    cd "$SCRIPT_DIR"
    reflex init --loglevel info 2>/dev/null || true
fi

# Función para aplicar el parche de allowedHosts
apply_allowed_hosts_patch() {
    if [ -f "$SCRIPT_DIR/.web/vite.config.js" ]; then
        echo "Aplicando parche de allowedHosts..."

        # Verificar si el archivo ya tiene allowedHosts: "all" o el array de hosts
        if grep -q 'allowedHosts.*:.*"all"' "$SCRIPT_DIR/.web/vite.config.js"; then
            echo "  → Parche ya aplicado (allowedHosts: \"all\")"
            return 0
        fi

        if grep -q "allowedHosts.*:.*\[.*tfmmyllm\.ai" "$SCRIPT_DIR/.web/vite.config.js"; then
            echo "  → Parche ya aplicado (array de hosts)"
            return 0
        fi

        # Si existe el script Python, usarlo
        if [ -f "$SCRIPT_DIR/patch_vite_config.py" ]; then
            python "$SCRIPT_DIR/patch_vite_config.py" 2>/dev/null || {
                echo "  → Error ejecutando patch_vite_config.py, aplicando parche manual..."
                manual_patch
            }
        else
            echo "  → patch_vite_config.py no encontrado, aplicando parche manual..."
            manual_patch
        fi
    else
        echo "ADVERTENCIA: vite.config.js no encontrado en .web/"
    fi
}

# Función de parche manual usando sed
manual_patch() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' 's/server: {/server: {\n    allowedHosts: "all",/' "$SCRIPT_DIR/.web/vite.config.js"
    else
        # Linux
        sed -i 's/server: {/server: {\n    allowedHosts: "all",/' "$SCRIPT_DIR/.web/vite.config.js"
    fi
    echo "  → Parche aplicado manualmente"
}

# Aplicar el parche siempre antes de iniciar
apply_allowed_hosts_patch

cd "$SCRIPT_DIR"
reflex run

