#!/bin/bash
# Script para activar el entorno virtual y ejecutar la aplicación Reflex

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

# Activar el entorno virtual del frontend
source "$ROOT_DIR/.venv_frontend/bin/activate"

# Ejecutar la aplicación Reflex desde la ruta actual
export PYTHONPATH="$ROOT_DIR"
reflex run

