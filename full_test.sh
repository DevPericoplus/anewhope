#!/bin/bash
# Ejecuta tests de frontend y middleware desde la raíz

set -e

source .venv_frontend313/bin/activate

pytest -q --rootdir=src/2_shared_application src/2_shared_application/tests
pytest -q --rootdir=src/apps/5_web_frontend src/apps/5_web_frontend/tests

deactivate

source .venv_middleware313/bin/activate
pytest -q --rootdir=src/apps/7_service_frontend src/apps/7_service_frontend/tests
pytest -q --rootdir=src/apps/8_service_backend src/apps/8_service_backend/tests
pytest -q --rootdir=src/apps/3_backend src/apps/3_backend/tests

deactivate
