#!/bin/bash
# Script para activar el entorno virtual y ejecutar el backend IA (trainer)
# NOTA: Usa Python 3.12 por compatibilidad con dependencias de IA (TensorFlow, Keras)

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

# Activar el entorno virtual del trainer (Python 3.12 - requerido por dependencias IA)
source "$ROOT_DIR/.venv_trainer312/bin/activate"

export PYTHONPATH="$ROOT_DIR"
python -m src.apps.4_trainer.main
