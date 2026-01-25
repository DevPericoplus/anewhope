#!/bin/bash
# Ejecuta tests de frontend y middleware desde la raíz

set -e

echo "========================================"
echo "INICIANDO EJECUCIÓN DE TESTS"
echo "========================================"
echo ""

source .venv_frontend313/bin/activate

echo "========================================"
echo "TESTS: src/2_shared_application/tests"
echo "========================================"
pytest -v --rootdir=src/2_shared_application src/2_shared_application/tests
echo ""

echo "========================================"
echo "TESTS: src/apps/5_web_frontend/tests"
echo "========================================"
pytest -v --rootdir=src/apps/5_web_frontend src/apps/5_web_frontend/tests
echo ""

deactivate

source .venv_middleware313/bin/activate

echo "========================================"
echo "TESTS: src/apps/7_service_frontend/tests"
echo "========================================"
pytest -v --rootdir=src/apps/7_service_frontend src/apps/7_service_frontend/tests
echo ""

echo "========================================"
echo "TESTS: src/apps/8_service_backend/tests"
echo "========================================"
pytest -v --rootdir=src/apps/8_service_backend src/apps/8_service_backend/tests
echo ""

echo "========================================"
echo "TESTS: src/apps/3_backend/tests"
echo "========================================"
pytest -v --rootdir=src/apps/3_backend src/apps/3_backend/tests
echo ""

deactivate

echo "========================================"
echo "TODOS LOS TESTS COMPLETADOS CON ÉXITO"
echo "========================================"
