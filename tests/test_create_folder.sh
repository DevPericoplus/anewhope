#!/bin/bash
# Test de creación de carpeta en fmanagement (verifica vía API, no disco local).

set -euo pipefail

echo "==================================================="
echo "Test: Crear carpeta en fmanagement"
echo "==================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=e2e_env.sh
source "${SCRIPT_DIR}/e2e_env.sh"

FOLDER_NAME="test_$(date +%s)"
ORG_PATH="ORG00001"
PRJ_PATH="PRJ00001"
VERSION_PATH="v001"
USER_ID=1
IDENTITY_TYPE_ID=1

echo ""
echo "1. Llamando a fmanagement para crear carpeta '${FOLDER_NAME}':"
echo "   URL: ${TEST_FMANAGEMENT_URL}"
echo "-----------------------------------"
RESPONSE=$(curl -sS --max-time 20 -X POST \
    "${TEST_FMANAGEMENT_URL}/fmo/createfolder?iduser=${USER_ID}&basepath=${FMO_BASEPATH}&orgpath=${ORG_PATH}&prjpath=${PRJ_PATH}&versionpath=${VERSION_PATH}&subfolders=${FOLDER_NAME}&identity_type_id=${IDENTITY_TYPE_ID}")
echo "Response: ${RESPONSE}"

sleep 2

echo ""
echo "2. Verificando carpeta vía GET /fmo/list:"
echo "-----------------------------------"
LISTING=$(fmo_list "${ORG_PATH}" "${PRJ_PATH}" "${VERSION_PATH}")
if fmo_contains "${LISTING}" "${FOLDER_NAME}"; then
    echo "✓ ÉXITO: La carpeta '${FOLDER_NAME}' aparece en /fmo/list"
else
    echo "✗ FALLO: La carpeta '${FOLDER_NAME}' NO aparece en /fmo/list"
    echo "${LISTING}" | head -c 2000
    echo ""
    exit 1
fi

echo ""
echo "==================================================="
echo "Fin del test"
echo "==================================================="
