#!/bin/bash
# Script para activar el entorno virtual y ejecutar el backend core

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

# Activar el entorno virtual del backend (Python 3.13)
source "$ROOT_DIR/.venv_backend313/bin/activate"

export PYTHONPATH="$ROOT_DIR"
python -m src.apps.3_backend.main
