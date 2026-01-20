#!/bin/bash
# Limpia caches generadas por las aplicaciones y herramientas de desarrollo

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "Limpiando caches en $ROOT_DIR"

# Reflex (frontend/backoffice)
rm -rf "$ROOT_DIR/src/apps/5_web_frontend/.web"
rm -rf "$ROOT_DIR/src/apps/5_web_frontend/.states"
rm -rf "$ROOT_DIR/src/apps/6_web_backoffice/.web"
rm -rf "$ROOT_DIR/src/apps/6_web_backoffice/.states"

# Python caches
find "$ROOT_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} +

# Pytest / coverage / tooling caches
rm -rf "$ROOT_DIR/.pytest_cache"
rm -rf "$ROOT_DIR/.mypy_cache"
rm -rf "$ROOT_DIR/.ruff_cache"
rm -rf "$ROOT_DIR/.coverage"
rm -rf "$ROOT_DIR/.coverage.*"
rm -rf "$ROOT_DIR/.hypothesis"

echo "Caches eliminadas."
