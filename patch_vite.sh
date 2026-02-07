#!/bin/bash
# Aplica parche de Vite para permitir todos los dominios (allowedHosts)
# Ejecutar DESPUÉS de arrancar las aplicaciones por primera vez

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "=== Aplicando parche de Vite para allowedHosts ==="
echo ""

# ========================================
# Función para aplicar parche de allowedHosts
# ========================================
apply_vite_allowedhosts_patch() {
    local app_dir=$1
    local app_name=$2

    echo "Procesando $app_name..."

    if [ ! -f "$app_dir/.web/vite.config.js" ]; then
        echo "  ⚠ vite.config.js no existe. Arranca la app primero."
        return 1
    fi

    # Backup del original
    if [ ! -f "$app_dir/.web/vite.config.js.original" ]; then
        cp "$app_dir/.web/vite.config.js" "$app_dir/.web/vite.config.js.original"
        echo "  ✓ Backup creado (.original)"
    fi

    # Verificar si ya tiene el parche
    if grep -q "allowedHosts" "$app_dir/.web/vite.config.js"; then
        echo "  ✓ Ya tiene el parche aplicado"
        return 0
    fi

    # Aplicar parche: agregar allowedHosts después de "server: {"
    sed -i.tmp '/server: {/a\
    allowedHosts: "all",
' "$app_dir/.web/vite.config.js"
    rm -f "$app_dir/.web/vite.config.js.tmp"

    echo "  ✓ Parche aplicado: allowedHosts: \"all\""
}

# ========================================
# Aplicar parches
# ========================================
success_count=0
failed_count=0

if apply_vite_allowedhosts_patch "$ROOT_DIR/src/apps/5_web_frontend" "Frontend"; then
    ((success_count++))
else
    ((failed_count++))
fi

echo ""

if apply_vite_allowedhosts_patch "$ROOT_DIR/src/apps/6_web_backoffice" "Backoffice"; then
    ((success_count++))
else
    ((failed_count++))
fi

echo ""
echo "=== Resumen ==="
echo "✓ Parches aplicados exitosamente: $success_count"
echo "⚠ Aplicaciones sin vite.config.js: $failed_count"
echo ""

if [ $failed_count -gt 0 ]; then
    echo "NOTA: Para las apps sin vite.config.js:"
    echo "  1. Arranca la aplicación (reflex run)"
    echo "  2. Espera a que genere los archivos"
    echo "  3. Vuelve a ejecutar este script"
    echo ""
fi

echo "IMPORTANTE: Reinicia las aplicaciones para que el parche tome efecto."
