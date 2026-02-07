#!/bin/bash
# Limpia caches generadas por las aplicaciones y herramientas de desarrollo
# Incluye parche para errores de Vite con dominios

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "=== Limpiando caches y aplicando parches en $ROOT_DIR ==="

# ========================================
# Función para aplicar parche de Vite
# ========================================
apply_vite_patch() {
    local app_dir=$1
    local app_name=$2

    echo "Aplicando parche de Vite para $app_name..."

    # Crear vite-env.d.ts si no existe
    if [ ! -f "$app_dir/.web/vite-env.d.ts" ]; then
        mkdir -p "$app_dir/.web"
        cat > "$app_dir/.web/vite-env.d.ts" <<EOF
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_TITLE: string
  // más variables de entorno si es necesario
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
EOF
        echo "  ✓ Creado vite-env.d.ts"
    fi

    # Modificar vite.config.js para permitir todos los dominios
    if [ -f "$app_dir/.web/vite.config.js" ]; then
        # Backup del original
        cp "$app_dir/.web/vite.config.js" "$app_dir/.web/vite.config.js.backup" 2>/dev/null || true

        # Agregar allowedHosts si no existe
        if ! grep -q "allowedHosts" "$app_dir/.web/vite.config.js"; then
            # Usar sed para agregar allowedHosts después de la línea "server: {"
            sed -i.tmp '/server: {/a\
    allowedHosts: "all",
' "$app_dir/.web/vite.config.js"
            rm -f "$app_dir/.web/vite.config.js.tmp"
            echo "  ✓ Agregado allowedHosts: \"all\" al vite.config.js"
        else
            echo "  ✓ allowedHosts ya está configurado"
        fi
    fi
}

# ========================================
# Aplicar parches de Vite ANTES de limpiar
# ========================================
apply_vite_patch "$ROOT_DIR/src/apps/5_web_frontend" "Frontend"
apply_vite_patch "$ROOT_DIR/src/apps/6_web_backoffice" "Backoffice"

# ========================================
# Reflex (frontend y backoffice)
# ========================================
echo "Limpiando caches de Reflex (frontend)..."
# No borrar .web completo, solo caches internas
rm -rf "$ROOT_DIR/src/apps/5_web_frontend/.web/.vite"
rm -rf "$ROOT_DIR/src/apps/5_web_frontend/.web/node_modules"
rm -rf "$ROOT_DIR/src/apps/5_web_frontend/.states"
rm -rf "$ROOT_DIR/src/apps/5_web_frontend/assets/external"
rm -f "$ROOT_DIR/src/apps/5_web_frontend"/*.db

echo "Limpiando caches de Reflex (backoffice)..."
# No borrar .web completo, solo caches internas
rm -rf "$ROOT_DIR/src/apps/6_web_backoffice/.web/.vite"
rm -rf "$ROOT_DIR/src/apps/6_web_backoffice/.web/node_modules"
rm -rf "$ROOT_DIR/src/apps/6_web_backoffice/.states"
rm -rf "$ROOT_DIR/src/apps/6_web_backoffice/assets/external"
rm -f "$ROOT_DIR/src/apps/6_web_backoffice"/*.db

# ========================================
# Python caches (global)
# ========================================
echo "Limpiando __pycache__ en todo el proyecto..."
find "$ROOT_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true

echo "Limpiando archivos .pyc y .pyo..."
find "$ROOT_DIR" -type f -name "*.py[cod]" -delete 2>/dev/null || true

# ========================================
# Pytest / coverage / tooling caches
# ========================================
echo "Limpiando caches de pytest y herramientas..."

# Caches en la raíz
rm -rf "$ROOT_DIR/.pytest_cache"
rm -rf "$ROOT_DIR/.mypy_cache"
rm -rf "$ROOT_DIR/.ruff_cache"
rm -rf "$ROOT_DIR/.coverage"
rm -rf "$ROOT_DIR/.coverage.*"
rm -rf "$ROOT_DIR/.hypothesis"

# Caches de pytest dentro de cada app
find "$ROOT_DIR/src/apps" -type d -name ".pytest_cache" -prune -exec rm -rf {} + 2>/dev/null || true
find "$ROOT_DIR/src" -type d -name ".pytest_cache" -prune -exec rm -rf {} + 2>/dev/null || true

# ========================================
# Node.js caches (si existen)
# ========================================
echo "Limpiando caches de Node.js (si existen)..."
rm -rf "$ROOT_DIR/src/apps/5_web_frontend/node_modules/.cache" 2>/dev/null || true
rm -rf "$ROOT_DIR/src/apps/6_web_backoffice/node_modules/.cache" 2>/dev/null || true

echo ""
echo "=== Caches eliminadas y parches aplicados correctamente ==="
echo ""
echo "IMPORTANTE: Si Reflex aún no ha generado los archivos .web/vite.config.js,"
echo "ejecuta primero 'reflex init' en cada app y luego vuelve a ejecutar este script."
