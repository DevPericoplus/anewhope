#!/bin/bash
set -e

echo ""
echo "================================================================================"
echo "TEST: Verificar actualización de tamaños en BD"
echo "================================================================================"
echo ""

echo "ANTES - Tamaños en BD del proyecto 2:"
/usr/local/opt/mariadb@10.6/bin/mariadb -u myllm_admin -p'<mariadb_admin_password>' myllm_projects_db -e "SELECT id_version, size_bytes, DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i:%s') as updated FROM version_states WHERE id_proyecto = 2 ORDER BY id_version;" 2>/dev/null

echo ""
echo "Reiniciando el frontend para cargar el nuevo código..."
echo "(Debes reiniciar manualmente la aplicación Reflex)"
echo ""
echo "Después de reiniciar, recarga el explorador y selecciona el proyecto PRJ00002"
echo ""
echo "LUEGO ejecuta este comando para verificar:"
echo "/usr/local/opt/mariadb@10.6/bin/mariadb -u myllm_admin -p'<mariadb_admin_password>' myllm_projects_db -e \"SELECT id_version, size_bytes, updated_at FROM version_states WHERE id_proyecto = 2 ORDER BY id_version;\""
echo ""
echo "================================================================================"
