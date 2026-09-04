#!/bin/bash
# Consulta tamaños de versión en MariaDB del entorno activo.

set -euo pipefail

echo ""
echo "================================================================================"
echo "TEST: Verificar tamaños en BD (entorno ${ANEWHOPE_ENV:-activo})"
echo "================================================================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=e2e_env.sh
source "${SCRIPT_DIR}/e2e_env.sh"

PYTHONPATH="${_E2E_ROOT}${PYTHONPATH:+:$PYTHONPATH}" "${_E2E_PY}" - <<'PY'
from tests.helpers import get_db_connection

conn = get_db_connection(database="myllm_projects_db")
try:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id_version, size_bytes,
                   DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i:%s') AS updated
            FROM version_states
            WHERE id_proyecto = 2
            ORDER BY id_version
            """
        )
        rows = cursor.fetchall()
    if not rows:
        print("No hay filas en version_states para id_proyecto=2 (OK si el proyecto no existe)")
    else:
        print("id_version | size_bytes | updated_at")
        for row in rows:
            print(f"{row['id_version']:>9} | {row.get('size_bytes')} | {row.get('updated')}")
finally:
    conn.close()
PY

echo ""
echo "================================================================================"
echo "Consulta completada (host=${TEST_MARIADB_HOST})"
echo "================================================================================"
