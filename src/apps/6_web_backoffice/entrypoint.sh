#!/bin/bash
# Entrypoint para ejecutar el backoffice en contenedor
#
# En el contenedor, el Dockerfile copia el repo a /app (WORKDIR) y este script
# a /app/entrypoint.sh, por lo que la raíz del proyecto es el directorio del
# propio script (/app), no tres niveles por encima.
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Si el código no está bajo esta raíz (ejecución nativa desde src/apps/...),
# retroceder tres niveles como fallback.
if [ ! -d "$ROOT_DIR/src/apps/6_web_backoffice" ]; then
    ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
fi
export PYTHONPATH="$ROOT_DIR"
APP_DIR="$ROOT_DIR/src/apps/6_web_backoffice"
cd "$APP_DIR"

# El .web ya se genera y parchea (allowedHosts) durante el build (ver Dockerfile).
exec reflex run --env dev
