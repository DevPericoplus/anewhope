#!/bin/bash
# Test de renombrado de archivo en fmanagement (verifica vía API).

set -euo pipefail

echo "==================================================="
echo "Test: Renombrar archivo en fmanagement"
echo "==================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=e2e_env.sh
source "${SCRIPT_DIR}/e2e_env.sh"

FILE_NAME="test_rename_$(date +%s)"
NEW_FILE_NAME="renamed_$(date +%s)"
ORG_PATH="ORG00001"
PRJ_PATH="PRJ00001"
VERSION_PATH="v001"
SUBFOLDER="e2e_rename_$$"
EXT_FILE="txt"
USER_ID=1
IDENTITY_TYPE_ID=1

echo ""
echo "1. Creando carpeta de prueba '${SUBFOLDER}':"
echo "   URL: ${TEST_FMANAGEMENT_URL}"
echo "-----------------------------------"
RESPONSE=$(curl -sS --max-time 20 -X POST \
    "${TEST_FMANAGEMENT_URL}/fmo/createfolder?iduser=${USER_ID}&basepath=${FMO_BASEPATH}&orgpath=${ORG_PATH}&prjpath=${PRJ_PATH}&versionpath=${VERSION_PATH}&subfolders=${SUBFOLDER}&identity_type_id=${IDENTITY_TYPE_ID}")
echo "Response: ${RESPONSE}"

echo ""
echo "2. Creando archivo de prueba '${FILE_NAME}.${EXT_FILE}':"
echo "-----------------------------------"
echo "Test content" > "/tmp/${FILE_NAME}.${EXT_FILE}"
RESPONSE=$(curl -sS --max-time 20 -X POST \
    -F "file=@/tmp/${FILE_NAME}.${EXT_FILE}" \
    -F "iduser=${USER_ID}" \
    -F "identity_type_id=${IDENTITY_TYPE_ID}" \
    -F "basepath=${FMO_BASEPATH}" \
    -F "orgpath=${ORG_PATH}" \
    -F "prjpath=${PRJ_PATH}" \
    -F "versionpath=${VERSION_PATH}" \
    -F "subfolders=${SUBFOLDER}" \
    -F "filename=${FILE_NAME}" \
    -F "extfile=${EXT_FILE}" \
    "${TEST_FMANAGEMENT_URL}/fmo/createfile")
echo "Response: ${RESPONSE}"

sleep 1

echo ""
echo "3. Verificando que el archivo original existe (API):"
echo "-----------------------------------"
LISTING=$(fmo_list "${ORG_PATH}" "${PRJ_PATH}" "${VERSION_PATH}")
if fmo_contains "${LISTING}" "${FILE_NAME}"; then
    echo "✓ Archivo '${FILE_NAME}.${EXT_FILE}' existe"
else
    echo "✗ FALLO: Archivo '${FILE_NAME}.${EXT_FILE}' NO existe en /fmo/list"
    echo "${LISTING}" | head -c 2000
    echo ""
    rm -f "/tmp/${FILE_NAME}.${EXT_FILE}"
    curl -sS --max-time 15 -X DELETE \
        "${TEST_FMANAGEMENT_URL}/fmo/deletefolder?iduser=${USER_ID}&basepath=${FMO_BASEPATH}&orgpath=${ORG_PATH}&prjpath=${PRJ_PATH}&versionpath=${VERSION_PATH}&subfolders=${SUBFOLDER}&identity_type_id=${IDENTITY_TYPE_ID}" >/dev/null || true
    exit 1
fi

echo ""
echo "4. Renombrando archivo a '${NEW_FILE_NAME}.${EXT_FILE}':"
echo "-----------------------------------"
RESPONSE=$(curl -sS --max-time 20 -X PATCH \
    "${TEST_FMANAGEMENT_URL}/fmo?iduser=${USER_ID}&basepath=${FMO_BASEPATH}&orgpath=${ORG_PATH}&prjpath=${PRJ_PATH}&versionpath=${VERSION_PATH}&subfolders=${SUBFOLDER}&filename=${FILE_NAME}&extfile=${EXT_FILE}&new_filename=${NEW_FILE_NAME}&new_extfile=${EXT_FILE}&identity_type_id=${IDENTITY_TYPE_ID}&operation=rename")
echo "Response: ${RESPONSE}"

sleep 1

echo ""
echo "5. Verificando que el archivo fue renombrado (API):"
echo "-----------------------------------"
LISTING=$(fmo_list "${ORG_PATH}" "${PRJ_PATH}" "${VERSION_PATH}")
if fmo_contains "${LISTING}" "${NEW_FILE_NAME}"; then
    echo "✓ ÉXITO: Archivo renombrado a '${NEW_FILE_NAME}.${EXT_FILE}'"
else
    echo "✗ FALLO: Archivo '${NEW_FILE_NAME}.${EXT_FILE}' NO existe en /fmo/list"
    echo "${LISTING}" | head -c 2000
    echo ""
    rm -f "/tmp/${FILE_NAME}.${EXT_FILE}"
    curl -sS --max-time 15 -X DELETE \
        "${TEST_FMANAGEMENT_URL}/fmo/deletefolder?iduser=${USER_ID}&basepath=${FMO_BASEPATH}&orgpath=${ORG_PATH}&prjpath=${PRJ_PATH}&versionpath=${VERSION_PATH}&subfolders=${SUBFOLDER}&identity_type_id=${IDENTITY_TYPE_ID}" >/dev/null || true
    exit 1
fi

echo ""
echo "6. Limpiando carpeta de prueba:"
echo "-----------------------------------"
RESPONSE=$(curl -sS --max-time 20 -X DELETE \
    "${TEST_FMANAGEMENT_URL}/fmo/deletefolder?iduser=${USER_ID}&basepath=${FMO_BASEPATH}&orgpath=${ORG_PATH}&prjpath=${PRJ_PATH}&versionpath=${VERSION_PATH}&subfolders=${SUBFOLDER}&identity_type_id=${IDENTITY_TYPE_ID}")
echo "Response: ${RESPONSE}"
rm -f "/tmp/${FILE_NAME}.${EXT_FILE}"

echo ""
echo "==================================================="
echo "Test completado exitosamente"
echo "==================================================="
