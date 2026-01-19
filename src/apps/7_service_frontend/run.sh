#!/bin/bash
# Script para activar el entorno virtual y ejecutar el middleware

# Activar el entorno virtual del middleware (Python 3.13)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
source "$ROOT_DIR/.venv_middleware313/bin/activate"

# Ejecutar el middleware desde la ruta actual
export PYTHONPATH="$ROOT_DIR"
python -m src.apps.7_service_frontend.main
