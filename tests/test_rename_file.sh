#!/bin/bash
# Test de renombrado de archivo en fmanagement

set -e

echo "==================================================="
echo "Test: Renombrar archivo en fmanagement"
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
FILE_NAME="test_rename_$(date +%s)"
NEW_FILE_NAME="renamed_$(date +%s)"
ORG_PATH="ORG00001"
PRJ_PATH="PRJ00001"
VERSION_PATH="v001"
SUBFOLDER="datos"
EXT_FILE="txt"
USER_ID=1
IDENTITY_TYPE_ID=1

FULL_PATH="${BASE_PATH}/${ORG_PATH}/${PRJ_PATH}/${VERSION_PATH}/${SUBFOLDER}"

echo ""
echo "1. Creando archivo de prueba '${FILE_NAME}.${EXT_FILE}':"
echo "-----------------------------------"
# Crear archivo con contenido
echo "Test content" > "/tmp/${FILE_NAME}.${EXT_FILE}"
RESPONSE=$(curl -s -X POST -F "file=@/tmp/${FILE_NAME}.${EXT_FILE}" "${FMANAGEMENT_URL}/fmo/createfile?iduser=${USER_ID}&basepath=default&orgpath=${ORG_PATH}&prjpath=${PRJ_PATH}&versionpath=${VERSION_PATH}&subfolders=${SUBFOLDER}&filename=${FILE_NAME}&extfile=${EXT_FILE}&identity_type_id=${IDENTITY_TYPE_ID}")
echo "Response: ${RESPONSE}"

sleep 1

echo ""
echo "2. Verificando que el archivo original existe:"
echo "-----------------------------------"
if [ -f "${FULL_PATH}/${FILE_NAME}.${EXT_FILE}" ]; then
    echo "✓ Archivo '${FILE_NAME}.${EXT_FILE}' existe"
    ls -l "${FULL_PATH}/${FILE_NAME}.${EXT_FILE}"
else
    echo "✗ FALLO: Archivo '${FILE_NAME}.${EXT_FILE}' NO existe"
    exit 1
fi

echo ""
echo "3. Renombrando archivo a '${NEW_FILE_NAME}.${EXT_FILE}':"
echo "-----------------------------------"
RESPONSE=$(curl -s -X PATCH "${FMANAGEMENT_URL}/fmo?iduser=${USER_ID}&basepath=default&orgpath=${ORG_PATH}&prjpath=${PRJ_PATH}&versionpath=${VERSION_PATH}&subfolders=${SUBFOLDER}&filename=${FILE_NAME}&extfile=${EXT_FILE}&new_filename=${NEW_FILE_NAME}&new_extfile=${EXT_FILE}&identity_type_id=${IDENTITY_TYPE_ID}&operation=rename")
echo "Response: ${RESPONSE}"

sleep 1

echo ""
echo "4. Verificando que el archivo fue renombrado:"
echo "-----------------------------------"
if [ -f "${FULL_PATH}/${NEW_FILE_NAME}.${EXT_FILE}" ]; then
    echo "✓ ÉXITO: Archivo renombrado a '${NEW_FILE_NAME}.${EXT_FILE}' existe"
    ls -l "${FULL_PATH}/${NEW_FILE_NAME}.${EXT_FILE}"
else
    echo "✗ FALLO: Archivo '${NEW_FILE_NAME}.${EXT_FILE}' NO existe"
    echo ""
    echo "Verificando si el archivo original aún existe:"
    if [ -f "${FULL_PATH}/${FILE_NAME}.${EXT_FILE}" ]; then
        echo "El archivo original '${FILE_NAME}.${EXT_FILE}' todavía existe (no se renombró)"
    else
        echo "El archivo original '${FILE_NAME}.${EXT_FILE}' tampoco existe (se borró)"
    fi
    exit 1
fi

echo ""
echo "5. Verificando que el archivo original ya no existe:"
echo "-----------------------------------"
if [ ! -f "${FULL_PATH}/${FILE_NAME}.${EXT_FILE}" ]; then
    echo "✓ Archivo original '${FILE_NAME}.${EXT_FILE}' ya no existe (correcto)"
else
    echo "✗ ADVERTENCIA: Archivo original '${FILE_NAME}.${EXT_FILE}' todavía existe"
fi

echo ""
echo "6. Limpiando - eliminando archivo de prueba:"
echo "-----------------------------------"
RESPONSE=$(curl -s -X DELETE "${FMANAGEMENT_URL}/fmo/deletefile?iduser=${USER_ID}&basepath=default&orgpath=${ORG_PATH}&prjpath=${PRJ_PATH}&versionpath=${VERSION_PATH}&subfolders=${SUBFOLDER}&filename=${NEW_FILE_NAME}&extfile=${EXT_FILE}&identity_type_id=${IDENTITY_TYPE_ID}")
echo "Response: ${RESPONSE}"

# Limpiar archivo temporal
rm -f "/tmp/${FILE_NAME}.${EXT_FILE}"

echo ""
echo "==================================================="
echo "Test completado exitosamente"
echo "==================================================="
