#!/bin/bash
# Entrypoint para ejecutar el frontend en contenedor
#
# En el contenedor, el Dockerfile copia el repo a /app (WORKDIR) y este script
# a /app/entrypoint.sh, por lo que la raíz del proyecto es el directorio del
# propio script (/app), no tres niveles por encima.
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -d "$ROOT_DIR/src/apps/5_web_frontend" ]; then
    ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
fi
export PYTHONPATH="$ROOT_DIR"
APP_DIR="$ROOT_DIR/src/apps/5_web_frontend"
cd "$APP_DIR"

# El .web ya se genera y parchea (allowedHosts) durante el build de la imagen
# (ver Dockerfile). Aquí solo se arranca Reflex, que reutiliza ese .web.
exec reflex run --env dev
