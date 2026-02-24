#!/bin/bash
# Test de renombrado de carpeta en fmanagement

set -e

echo "==================================================="
echo "Test: Renombrar carpeta en fmanagement"
echo "==================================================="

# Configuración - obtener valores dinámicamente
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FMANAGEMENT_URL=$(python3 -c "
import importlib.util, os
env = os.environ.get('ANEWHOPE_ENV', 'macbook')
spec = importlib.util.spec_from_file_location('pv', '$BASE_DIR/infrastructure/environments/' + env + '/protected_values.py')
pv = importlib.util.module_from_spec(spec); spec.loader.exec_module(pv)
from urllib.parse import urlparse
p = urlparse(pv.broker_backend_base_url)
print(f'http://{p.hostname}:1666')
")
BASE_PATH=$(python3 -c "
import yaml, os
env = os.environ.get('ANEWHOPE_ENV', 'macbook')
with open('$BASE_DIR/infrastructure/environments/' + env + '/env.yaml') as f:
    d = yaml.safe_load(f)
print(os.path.expanduser(d.get('fmanagement_base_path', '/tmp')) + '/external')
" 2>/dev/null || echo "/Users/administrator/data/anewhope/files/backend_server/external")
FOLDER_NAME="test_rename_$(date +%s)"
NEW_FOLDER_NAME="renamed_$(date +%s)"
ORG_PATH="ORG00001"
PRJ_PATH="PRJ00001"
VERSION_PATH="v001"
USER_ID=1
IDENTITY_TYPE_ID=1

FULL_PATH="${BASE_PATH}/${ORG_PATH}/${PRJ_PATH}/${VERSION_PATH}"

echo ""
echo "1. Creando carpeta de prueba '${FOLDER_NAME}':"
echo "-----------------------------------"
RESPONSE=$(curl -s -X POST "${FMANAGEMENT_URL}/fmo/createfolder?iduser=${USER_ID}&basepath=default&orgpath=${ORG_PATH}&prjpath=${PRJ_PATH}&versionpath=${VERSION_PATH}&subfolders=${FOLDER_NAME}&identity_type_id=${IDENTITY_TYPE_ID}")
echo "Response: ${RESPONSE}"

sleep 1

echo ""
echo "2. Verificando que la carpeta original existe:"
echo "-----------------------------------"
if [ -d "${FULL_PATH}/${FOLDER_NAME}" ]; then
    echo "✓ Carpeta '${FOLDER_NAME}' existe"
    ls -ld "${FULL_PATH}/${FOLDER_NAME}"
else
    echo "✗ FALLO: Carpeta '${FOLDER_NAME}' NO existe"
    exit 1
fi

echo ""
echo "3. Renombrando carpeta a '${NEW_FOLDER_NAME}':"
echo "-----------------------------------"
RESPONSE=$(curl -s -X PATCH "${FMANAGEMENT_URL}/fmo/renamefolder?iduser=${USER_ID}&basepath=default&orgpath=${ORG_PATH}&prjpath=${PRJ_PATH}&versionpath=${VERSION_PATH}&subfolders=${FOLDER_NAME}&new_filename=${NEW_FOLDER_NAME}&identity_type_id=${IDENTITY_TYPE_ID}")
echo "Response: ${RESPONSE}"

sleep 1

echo ""
echo "4. Verificando que la carpeta fue renombrada:"
echo "-----------------------------------"
if [ -d "${FULL_PATH}/${NEW_FOLDER_NAME}" ]; then
    echo "✓ ÉXITO: Carpeta renombrada a '${NEW_FOLDER_NAME}' existe"
    ls -ld "${FULL_PATH}/${NEW_FOLDER_NAME}"
else
    echo "✗ FALLO: Carpeta '${NEW_FOLDER_NAME}' NO existe"
    echo ""
    echo "Verificando si la carpeta original aún existe:"
    if [ -d "${FULL_PATH}/${FOLDER_NAME}" ]; then
        echo "La carpeta original '${FOLDER_NAME}' todavía existe (no se renombró)"
    else
        echo "La carpeta original '${FOLDER_NAME}' tampoco existe (se borró)"
    fi
    exit 1
fi

echo ""
echo "5. Verificando que la carpeta original ya no existe:"
echo "-----------------------------------"
if [ ! -d "${FULL_PATH}/${FOLDER_NAME}" ]; then
    echo "✓ Carpeta original '${FOLDER_NAME}' ya no existe (correcto)"
else
    echo "✗ ADVERTENCIA: Carpeta original '${FOLDER_NAME}' todavía existe"
fi

echo ""
echo "6. Limpiando - eliminando carpeta de prueba:"
echo "-----------------------------------"
RESPONSE=$(curl -s -X DELETE "${FMANAGEMENT_URL}/fmo/deletefolder?iduser=${USER_ID}&basepath=default&orgpath=${ORG_PATH}&prjpath=${PRJ_PATH}&versionpath=${VERSION_PATH}&subfolders=${NEW_FOLDER_NAME}&identity_type_id=${IDENTITY_TYPE_ID}")
echo "Response: ${RESPONSE}"

echo ""
echo "==================================================="
echo "Test completado exitosamente"
echo "==================================================="
