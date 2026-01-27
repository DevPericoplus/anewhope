#!/bin/bash
# Ejecuta tests de frontend, backoffice y middleware desde la raíz

set -e

echo "=========================================="
echo "INICIANDO EJECUCIÓN DE TESTS"
echo "=========================================="
echo ""

# ============================================
# TESTS DE CAPA COMPARTIDA + FRONTEND
# ============================================
source .venv_frontend313/bin/activate

echo "=========================================="
echo "TESTS: src/2_shared_application/tests"
echo "=========================================="
pytest -v --rootdir=src/2_shared_application src/2_shared_application/tests
echo ""

echo "=========================================="
echo "TESTS REDIS: SharedSessionState (shared)"
echo "=========================================="
pytest -v --rootdir=src/2_shared_application src/2_shared_application/tests/test_shared_session_state.py
echo ""

echo "=========================================="
echo "TESTS: src/apps/5_web_frontend/tests"
echo "=========================================="
pytest -v --rootdir=src/apps/5_web_frontend src/apps/5_web_frontend/tests
echo ""

echo "=========================================="
echo "TESTS REDIS: Frontend integration"
echo "=========================================="
pytest -v --rootdir=src/apps/5_web_frontend src/apps/5_web_frontend/tests/test_redis_integration.py
echo ""

deactivate

# ============================================
# TESTS DE BACKOFFICE
# ============================================
source .venv_backoffice313/bin/activate

echo "=========================================="
echo "TESTS: src/apps/6_web_backoffice/tests"
echo "=========================================="
pytest -v --rootdir=src/apps/6_web_backoffice src/apps/6_web_backoffice/tests
echo ""

echo "=========================================="
echo "TESTS REDIS: Backoffice integration"
echo "=========================================="
pytest -v --rootdir=src/apps/6_web_backoffice src/apps/6_web_backoffice/tests/test_redis_integration.py
echo ""

deactivate

# ============================================
# TESTS DE MIDDLEWARE
# ============================================
source .venv_middleware313/bin/activate

echo "=========================================="
echo "TESTS: src/apps/7_service_frontend/tests"
echo "=========================================="
pytest -v --rootdir=src/apps/7_service_frontend src/apps/7_service_frontend/tests
echo ""

echo "=========================================="
echo "TESTS: src/apps/8_service_backend/tests"
echo "=========================================="
pytest -v --rootdir=src/apps/8_service_backend src/apps/8_service_backend/tests
echo ""

echo "=========================================="
echo "TESTS: src/apps/3_backend/tests"
echo "=========================================="
pytest -v --rootdir=src/apps/3_backend src/apps/3_backend/tests
echo ""

echo "=========================================="
echo "TESTS: Version Transfer (3_backend)"
echo "=========================================="
pytest -v --rootdir=src/apps/3_backend src/apps/3_backend/tests/test_version_transfer.py
echo ""

deactivate

# ============================================
# TESTS DE FMANAGEMENT (opcional)
# ============================================
FMANAGEMENT_PATH="../fmanagement"
if [ -d "$FMANAGEMENT_PATH" ] && [ -f "$FMANAGEMENT_PATH/main_test.go" ]; then
    echo "=========================================="
    echo "TESTS: fmanagement (Go API)"
    echo "=========================================="
    cd "$FMANAGEMENT_PATH"
    go test -v -timeout 120s
    cd - > /dev/null
    echo ""
else
    echo "=========================================="
    echo "INFO: fmanagement no encontrado en $FMANAGEMENT_PATH"
    echo "      Omitiendo tests de fmanagement"
    echo "=========================================="
    echo ""
fi

echo "=========================================="
echo "✅ TODOS LOS TESTS COMPLETADOS CON ÉXITO"
echo "=========================================="
echo ""
echo "Resumen de tests ejecutados:"
echo "  ✅ Capa compartida (2_shared_application)"
echo "  ✅ SharedSessionState (Redis integration)"
echo "  ✅ Frontend (5_web_frontend)"
echo "  ✅ Frontend Redis integration"
echo "  ✅ Backoffice (6_web_backoffice)"
echo "  ✅ Backoffice Redis integration"
echo "  ✅ Service Frontend (7_service_frontend)"
echo "  ✅ Service Backend (8_service_backend)"
echo "  ✅ Backend Core (3_backend)"
echo "  ✅ Version Transfer (3_backend)"
if [ -d "$FMANAGEMENT_PATH" ] && [ -f "$FMANAGEMENT_PATH/main_test.go" ]; then
    echo "  ✅ fmanagement (Go API)"
fi
echo ""
