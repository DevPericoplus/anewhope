#!/bin/bash
# Entrypoint para ejecutar el middleware en contenedor
#
# En el contenedor, el Dockerfile copia el repo a /app (WORKDIR) y este script
# a /app/entrypoint.sh, por lo que la raíz del proyecto es el directorio del
# propio script (/app).
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -d "$ROOT_DIR/src/apps/7_service_frontend" ]; then
    ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
fi
export PYTHONPATH="$ROOT_DIR"
cd "$ROOT_DIR"
python -m src.apps.7_service_frontend.main
