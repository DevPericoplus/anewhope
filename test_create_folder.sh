#!/bin/bash
# Test de creación de carpeta en fmanagement

set -e

echo "==================================================="
echo "Test: Crear carpeta en fmanagement"
echo "==================================================="

# Configuración
FMANAGEMENT_URL="http://127.0.0.1:1666"
FOLDER_NAME="test_$(date +%s)"
BASE_PATH="/Users/administrator/data/anewhope/files/backend_server"
ORG_PATH="ORG00001"
PRJ_PATH="PRJ00001"
VERSION_PATH="v001"
USER_ID=1
IDENTITY_TYPE_ID=1

FULL_PATH="${BASE_PATH}/external/${ORG_PATH}/${PRJ_PATH}/${VERSION_PATH}"

echo ""
echo "1. Estado inicial del directorio:"
echo "-----------------------------------"
ls -la "${FULL_PATH}" | head -15

echo ""
echo "2. Llamando a fmanagement para crear carpeta '${FOLDER_NAME}':"
echo "-----------------------------------"
RESPONSE=$(curl -s -X POST "${FMANAGEMENT_URL}/fmo/createfolder?iduser=${USER_ID}&basepath=default&orgpath=${ORG_PATH}&prjpath=${PRJ_PATH}&versionpath=${VERSION_PATH}&subfolders=${FOLDER_NAME}&identity_type_id=${IDENTITY_TYPE_ID}")

echo "Response: ${RESPONSE}"
echo ""

# Esperar un momento
sleep 2

echo "3. Verificando si la carpeta se creó en disco:"
echo "-----------------------------------"
if [ -d "${FULL_PATH}/${FOLDER_NAME}" ]; then
    echo "✓ ÉXITO: La carpeta '${FOLDER_NAME}' existe en disco"
    ls -la "${FULL_PATH}/${FOLDER_NAME}"
else
    echo "✗ FALLO: La carpeta '${FOLDER_NAME}' NO existe en disco"
    echo ""
    echo "Contenido actual del directorio:"
    ls -la "${FULL_PATH}"
fi

echo ""
echo "4. Verificando permisos del directorio padre:"
echo "-----------------------------------"
ls -ld "${FULL_PATH}"
stat -f "Owner: %Su:%Sg Permissions: %Sp" "${FULL_PATH}"

echo ""
echo "5. Verificando permisos del usuario actual:"
echo "-----------------------------------"
whoami
id

echo ""
echo "==================================================="
echo "Fin del test"
echo "==================================================="
