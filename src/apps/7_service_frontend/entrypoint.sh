#!/bin/bash
# Entrypoint para ejecutar el middleware en contenedor

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export PYTHONPATH="$ROOT_DIR"
python -m src.apps.7_service_frontend.main
