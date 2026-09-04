#!/bin/bash
# Test de renombrado de carpeta en fmanagement (verifica vía API).

set -euo pipefail

echo "==================================================="
echo "Test: Renombrar carpeta en fmanagement"
echo "==================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=e2e_env.sh
source "${SCRIPT_DIR}/e2e_env.sh"

FOLDER_NAME="test_rename_$(date +%s)"
NEW_FOLDER_NAME="renamed_$(date +%s)"
ORG_PATH="ORG00001"
PRJ_PATH="PRJ00001"
VERSION_PATH="v001"
USER_ID=1
IDENTITY_TYPE_ID=1

echo ""
echo "1. Creando carpeta de prueba '${FOLDER_NAME}':"
echo "   URL: ${TEST_FMANAGEMENT_URL}"
echo "-----------------------------------"
RESPONSE=$(curl -sS --max-time 20 -X POST \
    "${TEST_FMANAGEMENT_URL}/fmo/createfolder?iduser=${USER_ID}&basepath=${FMO_BASEPATH}&orgpath=${ORG_PATH}&prjpath=${PRJ_PATH}&versionpath=${VERSION_PATH}&subfolders=${FOLDER_NAME}&identity_type_id=${IDENTITY_TYPE_ID}")
echo "Response: ${RESPONSE}"

sleep 1

echo ""
echo "2. Verificando que la carpeta original existe (API):"
echo "-----------------------------------"
LISTING=$(fmo_list "${ORG_PATH}" "${PRJ_PATH}" "${VERSION_PATH}")
if fmo_contains "${LISTING}" "${FOLDER_NAME}"; then
    echo "✓ Carpeta '${FOLDER_NAME}' existe"
else
    echo "✗ FALLO: Carpeta '${FOLDER_NAME}' NO existe en /fmo/list"
    echo "${LISTING}" | head -c 2000
    echo ""
    exit 1
fi

echo ""
echo "3. Renombrando carpeta a '${NEW_FOLDER_NAME}':"
echo "-----------------------------------"
RESPONSE=$(curl -sS --max-time 20 -X PATCH \
    "${TEST_FMANAGEMENT_URL}/fmo/renamefolder?iduser=${USER_ID}&basepath=${FMO_BASEPATH}&orgpath=${ORG_PATH}&prjpath=${PRJ_PATH}&versionpath=${VERSION_PATH}&subfolders=${FOLDER_NAME}&new_filename=${NEW_FOLDER_NAME}&identity_type_id=${IDENTITY_TYPE_ID}")
echo "Response: ${RESPONSE}"

sleep 1

echo ""
echo "4. Verificando que la carpeta fue renombrada (API):"
echo "-----------------------------------"
LISTING=$(fmo_list "${ORG_PATH}" "${PRJ_PATH}" "${VERSION_PATH}")
if fmo_contains "${LISTING}" "${NEW_FOLDER_NAME}"; then
    echo "✓ ÉXITO: Carpeta renombrada a '${NEW_FOLDER_NAME}'"
else
    echo "✗ FALLO: Carpeta '${NEW_FOLDER_NAME}' NO existe en /fmo/list"
    echo "${LISTING}" | head -c 2000
    echo ""
    exit 1
fi

echo ""
echo "5. Limpiando - eliminando carpeta de prueba:"
echo "-----------------------------------"
RESPONSE=$(curl -sS --max-time 20 -X DELETE \
    "${TEST_FMANAGEMENT_URL}/fmo/deletefolder?iduser=${USER_ID}&basepath=${FMO_BASEPATH}&orgpath=${ORG_PATH}&prjpath=${PRJ_PATH}&versionpath=${VERSION_PATH}&subfolders=${NEW_FOLDER_NAME}&identity_type_id=${IDENTITY_TYPE_ID}")
echo "Response: ${RESPONSE}"

echo ""
echo "==================================================="
echo "Test completado exitosamente"
echo "==================================================="
