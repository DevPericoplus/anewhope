#!/bin/bash
# Smoke del flujo de entrenamiento: login + comprobación de APIs.
# El entrenamiento real (largo) está en tests/test_training_flow.py y se lanza
# solo con ANEWHOPE_E2E_TRAINING=1.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=e2e_env.sh
source "${SCRIPT_DIR}/e2e_env.sh"

echo "================================================================================"
echo "TEST FLUJO DE ENTRENAMIENTO (smoke, entorno ${ANEWHOPE_ENV})"
echo "================================================================================"

OTP=$(
    PYTHONPATH="${_E2E_ROOT}${PYTHONPATH:+:$PYTHONPATH}" "${_E2E_PY}" -c \
        "from tests.helpers import fetch_user_otp; print(fetch_user_otp('adminone'))"
)

AUTH_RESPONSE=$(curl -sS -w "\n%{http_code}" -X POST \
  "${TEST_MIDDLEWARE_URL}/login" \
  -H "Content-Type: application/json" \
  -d "{\"user_name\":\"adminone\",\"password\":\"Password01\",\"otp\":\"${OTP}\"}")

HTTP_CODE=$(echo "$AUTH_RESPONSE" | tail -n1)
AUTH_BODY=$(echo "$AUTH_RESPONSE" | sed '$d')

echo "   Login status: $HTTP_CODE"
if [ "$HTTP_CODE" != "200" ]; then
  echo "❌ Error en autenticación"
  echo "$AUTH_BODY"
  exit 1
fi
echo "✅ Autenticación exitosa"

ACCESS_TOKEN=$(echo "$AUTH_BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))")
if [ -z "$ACCESS_TOKEN" ]; then
  echo "❌ Login sin access_token"
  exit 1
fi

HEALTH_CODE=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 8 \
  "${TEST_MIDDLEWARE_URL}/docs" || echo "000")
if ! echo "$HEALTH_CODE" | grep -Eq '200|401'; then
  echo "❌ Middleware no responde (${HEALTH_CODE})"
  exit 1
fi
echo "✅ Middleware accesible (${HEALTH_CODE})"

if [ -n "${ANEWHOPE_E2E_TRAINING:-}" ]; then
  echo "ANEWHOPE_E2E_TRAINING=1: delegando en test_training_flow.py"
  PYTHONPATH="${_E2E_ROOT}${PYTHONPATH:+:$PYTHONPATH}" \
    "${_E2E_PY}" "${_E2E_ROOT}/tests/run_e2e.py" "${_E2E_ROOT}/tests/test_training_flow.py"
else
  echo "ℹ️  Entrenamiento real omitido (export ANEWHOPE_E2E_TRAINING=1 para lanzarlo)"
fi

echo "================================================================================"
echo "TEST COMPLETADO"
echo "================================================================================"
