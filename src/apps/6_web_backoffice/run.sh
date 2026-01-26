#!/bin/bash
# Script para activar el entorno virtual y ejecutar la aplicación Reflex

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

# Activar el entorno virtual del frontend (Python 3.13)
source "$ROOT_DIR/.venv_backoffice313/bin/activate"

# Ejecutar la aplicación Reflex desde la ruta actual
export PYTHONPATH="$ROOT_DIR"
reflex run

