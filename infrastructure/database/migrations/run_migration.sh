#!/bin/bash
# ============================================================================
# Script para ejecutar migraciones de base de datos
# Uso: ./run_migration.sh [migration_file.sql]
# ============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Cargar configuración del entorno
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
fi

# Variables de conexión (ajustar según entorno)
MARIADB_HOST="${MARIADB_HOST:-localhost}"
MARIADB_PORT="${MARIADB_PORT:-3306}"
MARIADB_USER="${MARIADB_ADMIN_USER:-myllm_admin}"
MARIADB_PASSWORD="${MARIADB_ADMIN_PASSWORD}"
MARIADB_CLI="${MARIADB_CLI_PATH:-/opt/homebrew/bin/mariadb}"

# Verificar argumentos
if [ -z "$1" ]; then
    echo -e "${YELLOW}Uso: $0 <migration_file.sql>${NC}"
    echo ""
    echo "Migraciones disponibles:"
    ls -1 "$SCRIPT_DIR"/*.sql 2>/dev/null || echo "  (ninguna encontrada)"
    exit 1
fi

MIGRATION_FILE="$1"

# Si no es ruta absoluta, buscar en el directorio de migraciones
if [[ ! "$MIGRATION_FILE" = /* ]]; then
    MIGRATION_FILE="$SCRIPT_DIR/$MIGRATION_FILE"
fi

# Verificar que el archivo existe
if [ ! -f "$MIGRATION_FILE" ]; then
    echo -e "${RED}Error: No se encontró el archivo $MIGRATION_FILE${NC}"
    exit 1
fi

# Verificar que tenemos la contraseña
if [ -z "$MARIADB_PASSWORD" ]; then
    echo -e "${YELLOW}Introduce la contraseña de MariaDB para $MARIADB_USER:${NC}"
    read -s MARIADB_PASSWORD
fi

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Ejecutando migración: $(basename "$MIGRATION_FILE")${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Host: $MARIADB_HOST:$MARIADB_PORT"
echo "Usuario: $MARIADB_USER"
echo "Archivo: $MIGRATION_FILE"
echo ""

# Ejecutar migración
"$MARIADB_CLI" \
    -h "$MARIADB_HOST" \
    -P "$MARIADB_PORT" \
    -u "$MARIADB_USER" \
    -p"$MARIADB_PASSWORD" \
    < "$MIGRATION_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Migración ejecutada correctamente${NC}"
else
    echo ""
    echo -e "${RED}❌ Error al ejecutar la migración${NC}"
    exit 1
fi
