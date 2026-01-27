#!/bin/bash
# Entrypoint para ejecutar el backend IA (trainer) en contenedor

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export PYTHONPATH="$ROOT_DIR"
python -m src.apps.4_trainer.main
