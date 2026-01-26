#!/bin/bash
# Limpia caches generadas por las aplicaciones y herramientas de desarrollo

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "=== Limpiando caches en $ROOT_DIR ==="

# ========================================
# Reflex (frontend y backoffice)
# ========================================
echo "Limpiando caches de Reflex (frontend)..."
rm -rf "$ROOT_DIR/src/apps/5_web_frontend/.web"
rm -rf "$ROOT_DIR/src/apps/5_web_frontend/.states"
rm -rf "$ROOT_DIR/src/apps/5_web_frontend/assets/external"
rm -f "$ROOT_DIR/src/apps/5_web_frontend"/*.db

echo "Limpiando caches de Reflex (backoffice)..."
rm -rf "$ROOT_DIR/src/apps/6_web_backoffice/.web"
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
echo "=== Caches eliminadas correctamente ==="
