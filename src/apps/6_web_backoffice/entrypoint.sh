#!/bin/bash
# Entrypoint para ejecutar el backoffice en contenedor

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export PYTHONPATH="$ROOT_DIR"
cd "$ROOT_DIR/src/apps/6_web_backoffice"
reflex run
