#!/bin/bash
# Ejecuta tests de frontend y middleware desde la raíz

set -e

source .venv314/bin/activate

pytest -q --rootdir=src/apps/5_web_frontend src/apps/5_web_frontend/tests
pytest -q --rootdir=src/apps/7_service_frontend src/apps/7_service_frontend/tests
