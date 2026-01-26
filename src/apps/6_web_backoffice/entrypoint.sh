#!/bin/bash
# Entrypoint para ejecutar el frontend en contenedor

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export PYTHONPATH="$ROOT_DIR"
cd "$ROOT_DIR/src/apps/5_web_frontend"
reflex run
