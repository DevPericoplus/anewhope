#!/bin/bash
set -e

echo ""
echo "================================================================================"
echo "TEST: Verificar actualización de tamaños en BD"
echo "================================================================================"
echo ""

# Obtener configuración dinámicamente
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_CONFIG=$(python3 -c "
import importlib.util, os
env = os.environ.get('ANEWHOPE_ENV', 'macbook')
spec = importlib.util.spec_from_file_location('pv', '$BASE_DIR/infrastructure/environments/' + env + '/protected_values.py')
pv = importlib.util.module_from_spec(spec); spec.loader.exec_module(pv)
print(pv.mariadb_cli_path)
print(pv.mariadb_admin_user)
print(pv.mariadb_admin_password)
print(pv.mariadb_host)
")
MARIADB_PATH=$(echo "$_CONFIG" | sed -n '1p')
DB_USER=$(echo "$_CONFIG" | sed -n '2p')
DB_PASS=$(echo "$_CONFIG" | sed -n '3p')
DB_HOST=$(echo "$_CONFIG" | sed -n '4p')

echo "ANTES - Tamaños en BD del proyecto 2:"
$MARIADB_PATH -u "$DB_USER" -p"$DB_PASS" -h "$DB_HOST" myllm_projects_db -e "SELECT id_version, size_bytes, DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i:%s') as updated FROM version_states WHERE id_proyecto = 2 ORDER BY id_version;" 2>/dev/null

echo ""
echo "Reiniciando el frontend para cargar el nuevo código..."
echo "(Debes reiniciar manualmente la aplicación Reflex)"
echo ""
echo "Después de reiniciar, recarga el explorador y selecciona el proyecto PRJ00002"
echo ""
echo "LUEGO ejecuta este comando para verificar:"
echo "$MARIADB_PATH -u $DB_USER -p'...' -h $DB_HOST myllm_projects_db -e \"SELECT id_version, size_bytes, updated_at FROM version_states WHERE id_proyecto = 2 ORDER BY id_version;\""
echo ""
echo "================================================================================"
