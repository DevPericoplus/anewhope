#!/bin/bash
# Script para activar el entorno virtual y ejecutar el broker backend

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

# Activar el entorno virtual del broker (Python 3.13)
source "$ROOT_DIR/.venv_broker313/bin/activate"

export PYTHONPATH="$ROOT_DIR"
python -m src.apps.8_service_backend.main
