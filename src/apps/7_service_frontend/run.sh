#!/bin/bash
# Script para activar el entorno virtual y ejecutar el middleware

# Activar el entorno virtual del middleware
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
source "$ROOT_DIR/.venv_middleware/bin/activate"

# Ejecutar el middleware desde la ruta actual
export PYTHONPATH="$ROOT_DIR"
python -m src.apps.7_service_frontend.main
