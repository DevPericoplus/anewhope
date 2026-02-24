#!/bin/bash
# Test completo del flujo de entrenamiento con monitorización de todos los mensajes

set -e

# Obtener URLs dinámicamente desde protected_values
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_URLS=$(python3 -c "
import importlib.util, os
from urllib.parse import urlparse
env = os.environ.get('ANEWHOPE_ENV', 'macbook')
spec = importlib.util.spec_from_file_location('pv', '$BASE_DIR/infrastructure/environments/' + env + '/protected_values.py')
pv = importlib.util.module_from_spec(spec); spec.loader.exec_module(pv)
p = urlparse(pv.broker_backend_base_url)
print(f'http://{p.hostname}:8007')
print(pv.core_backend_base_url)
")
MIDDLEWARE_URL=$(echo "$_URLS" | head -n1)
BACKEND_CORE_URL=$(echo "$_URLS" | tail -n1)

echo "================================================================================"
echo "TEST FLUJO COMPLETO DE ENTRENAMIENTO"
echo "================================================================================"

# PASO 1: Autenticación
echo ""
echo "🔐 PASO 1: Autenticando usuario..."
AUTH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  "${MIDDLEWARE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "user_name": "admin",
    "password": "Admin123!"
  }')

HTTP_CODE=$(echo "$AUTH_RESPONSE" | tail -n1)
AUTH_BODY=$(echo "$AUTH_RESPONSE" | sed '$d')

echo "   Status: $HTTP_CODE"

if [ "$HTTP_CODE" != "200" ]; then
  echo "❌ Error en autenticación"
  echo "$AUTH_BODY" | jq '.' 2>/dev/null || echo "$AUTH_BODY"
  exit 1
fi

echo "✅ Autenticación exitosa"
echo "$AUTH_BODY" | jq '{user_id, organization_id, token_length: (.access_token | length)}'

ACCESS_TOKEN=$(echo "$AUTH_BODY" | jq -r '.access_token')
SESSION_TOKEN=$(echo "$AUTH_BODY" | jq -r '.session_token // ""')
USER_ID=$(echo "$AUTH_BODY" | jq -r '.user_id')
ORG_ID=$(echo "$AUTH_BODY" | jq -r '.organization_id')

# PASO 2: Obtener versión
echo ""
echo "📦 PASO 2: Obteniendo versión más reciente..."
VERSIONS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET \
  "${BACKEND_CORE_URL}/core/versions?id_project=1" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Session-Token: ${SESSION_TOKEN}")

HTTP_CODE=$(echo "$VERSIONS_RESPONSE" | tail -n1)
VERSIONS_BODY=$(echo "$VERSIONS_RESPONSE" | sed '$d')

echo "   Status: $HTTP_CODE"

if [ "$HTTP_CODE" != "200" ]; then
  echo "❌ Error obteniendo versiones"
  echo "$VERSIONS_BODY" | jq '.' 2>/dev/null || echo "$VERSIONS_BODY"
  exit 1
fi

VERSION=$(echo "$VERSIONS_BODY" | jq '.[0]')
if [ "$VERSION" == "null" ]; then
  echo "❌ No hay versiones disponibles"
  exit 1
fi

echo "✅ Versión seleccionada"
echo "$VERSION" | jq '{id, nombre, path: .path_version}'

VERSION_ID=$(echo "$VERSION" | jq -r '.id')
VERSION_PATH=$(echo "$VERSION" | jq -r '.path_version // ""')

# PASO 3: Enviar solicitud de entrenamiento
echo ""
echo "🚀 PASO 3: Enviando solicitud de entrenamiento..."

TRAINING_PAYLOAD=$(cat <<EOF
{
  "id_user": ${USER_ID},
  "id_organization": ${ORG_ID},
  "id_project": 1,
  "id_version": ${VERSION_ID},
  "path_version": "${VERSION_PATH}",
  "chunk_size": 500,
  "chunk_overlap": 50,
  "model_type": "nomic-embed-text:latest"
}
EOF
)

echo "   Payload enviado:"
echo "$TRAINING_PAYLOAD" | jq '.'

TRAINING_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  "${MIDDLEWARE_URL}/training/entrenamientos" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "X-Session-Token: ${SESSION_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$TRAINING_PAYLOAD")

HTTP_CODE=$(echo "$TRAINING_RESPONSE" | tail -n1)
TRAINING_BODY=$(echo "$TRAINING_RESPONSE" | sed '$d')

echo "   Status: $HTTP_CODE"

if [ "$HTTP_CODE" != "200" ]; then
  echo "❌ Error enviando entrenamiento"
  echo "   Response:"
  echo "$TRAINING_BODY" | jq '.' 2>/dev/null || echo "$TRAINING_BODY"
  exit 1
fi

echo "✅ Respuesta del entrenamiento recibida:"
echo "$TRAINING_BODY" | jq '.'

# VERIFICAR CAMPOS CRÍTICOS
echo ""
echo "🔍 CAMPOS CRÍTICOS RECIBIDOS:"
ID_ENTRENAMIENTO=$(echo "$TRAINING_BODY" | jq -r '.id_entrenamiento // 0')
COLLECTION_NAME=$(echo "$TRAINING_BODY" | jq -r '.collection_name // ""')
NUMERO_SECUENCIA=$(echo "$TRAINING_BODY" | jq -r '.numero_secuencia // 0')

echo "   id_entrenamiento: $ID_ENTRENAMIENTO"
echo "   collection_name: $COLLECTION_NAME"
echo "   numero_secuencia: $NUMERO_SECUENCIA"

if [ "$ID_ENTRENAMIENTO" == "0" ] || [ "$ID_ENTRENAMIENTO" == "null" ]; then
  echo "⚠️  WARNING: id_entrenamiento es 0 o null - El polling NO funcionará"
  echo ""
  echo "❌ TEST FALLIDO: No se recibió un id_entrenamiento válido"
  exit 1
else
  echo "✅ id_entrenamiento válido: $ID_ENTRENAMIENTO"
fi

# PASO 4: Polling del progreso
echo ""
echo "📊 PASO 4: Iniciando polling del progreso (id=$ID_ENTRENAMIENTO)..."

MAX_POLLS=120  # 120 polls * 2s = 4 minutos máximo
POLL_INTERVAL=2
COMPLETED=false

for ((i=1; i<=MAX_POLLS; i++)); do
  sleep $POLL_INTERVAL

  POLL_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET \
    "${BACKEND_CORE_URL}/core/entrenamientos/${ID_ENTRENAMIENTO}/progress" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "X-Session-Token: ${SESSION_TOKEN}")

  HTTP_CODE=$(echo "$POLL_RESPONSE" | tail -n1)
  POLL_BODY=$(echo "$POLL_RESPONSE" | sed '$d')

  if [ "$HTTP_CODE" != "200" ]; then
    echo "   Poll #$i: Error $HTTP_CODE"
    continue
  fi

  ESTADO=$(echo "$POLL_BODY" | jq -r '.estado // "unknown"')
  FASE_ACTUAL=$(echo "$POLL_BODY" | jq -r '.fase_actual // "unknown"')
  COMPLETED_COUNT=$(echo "$POLL_BODY" | jq '[.subfases[] | select(.status == "completed")] | length')

  echo "   Poll #$i: estado=$ESTADO, fase=$FASE_ACTUAL, subfases=$COMPLETED_COUNT/16"

  # Mostrar última subfase completada
  LAST_COMPLETED=$(echo "$POLL_BODY" | jq -r '[.subfases[] | select(.status == "completed")] | last | "\(.subfase_key) - \(.subfase_name)"')
  if [ "$LAST_COMPLETED" != "null" ] && [ -n "$LAST_COMPLETED" ]; then
    echo "      Última completada: $LAST_COMPLETED"
  fi

  # Verificar si terminó
  if [ "$ESTADO" == "completed" ]; then
    echo ""
    echo "✅ ENTRENAMIENTO COMPLETADO"
    echo "   Progreso final:"
    echo "$POLL_BODY" | jq '.'
    COMPLETED=true
    break
  elif [ "$ESTADO" == "failed" ]; then
    echo ""
    echo "❌ ENTRENAMIENTO FALLÓ"
    echo "   Progreso final:"
    echo "$POLL_BODY" | jq '.'
    break
  fi
done

if [ "$COMPLETED" != "true" ] && [ "$ESTADO" != "failed" ]; then
  echo ""
  echo "⏱️  Tiempo de polling agotado (entrenamiento aún en progreso)"
fi

echo ""
echo "================================================================================"
echo "TEST COMPLETADO"
echo "================================================================================"
