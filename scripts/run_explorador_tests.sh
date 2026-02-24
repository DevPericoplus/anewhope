#!/bin/bash

# Script para ejecutar tests del Explorador (Estados de Versión)
# Verifica que los servicios estén corriendo y ejecuta los tests

set -e

# Cargar credenciales desde protected_values.py (nunca hardcodear en scripts)
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MARIADB_WRITER_PASS=$(python3 -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('pv', '$SCRIPT_DIR/infrastructure/environments/macbook/protected_values.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
print(mod.mariadb_writer_password)
" 2>/dev/null || echo "")

echo "=============================================="
echo "Tests del Explorador - Estados de Versión"
echo "=============================================="
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para verificar si un puerto está en uso
check_port() {
    local port=$1
    local service=$2
    if lsof -i :$port > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $service corriendo en puerto $port"
        return 0
    else
        echo -e "${RED}✗${NC} $service NO está corriendo en puerto $port"
        return 1
    fi
}

# Verificar servicios
echo "Verificando servicios necesarios..."
echo ""

services_ok=true

check_port 8003 "Backend Core" || services_ok=false
check_port 8007 "Middleware" || services_ok=false
check_port 8008 "Broker Backend" || services_ok=false
check_port 3306 "MariaDB" || services_ok=false

echo ""

if [ "$services_ok" = false ]; then
    echo -e "${RED}ERROR: Algunos servicios no están corriendo${NC}"
    echo ""
    echo "Inicia los servicios necesarios:"
    echo "  Terminal 1: cd src/apps/3_backend && bash run.sh"
    echo "  Terminal 2: cd src/apps/7_service_frontend && bash run.sh"
    echo "  Terminal 3: cd src/apps/8_service_backend && bash run.sh"
    echo "  MariaDB: mysql.server start"
    echo ""
    exit 1
fi

# Verificar tabla estado_version
echo "Verificando tabla estado_version..."
if /usr/local/opt/mariadb@10.6/bin/mariadb -u myllm_writer -p"$MARIADB_WRITER_PASS" myllm_projects_db -e "DESCRIBE estado_version;" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Tabla estado_version existe"
else
    echo -e "${RED}✗${NC} Tabla estado_version NO existe"
    echo ""
    echo "Crea la tabla con:"
    echo "  /usr/local/opt/mariadb@10.6/bin/mariadb -u root -p'<mariadb_root_password>' myllm_projects_db < infrastructure/database/ddl_estado_version.sql"
    echo ""
    exit 1
fi

echo ""
echo "=============================================="
echo "Ejecutando Tests"
echo "=============================================="
echo ""

# Determinar qué tests ejecutar
TEST_FILTER="${1:-}"

if [ -z "$TEST_FILTER" ]; then
    echo "Ejecutando TODOS los tests..."
    echo ""
else
    echo "Ejecutando tests que coincidan con: $TEST_FILTER"
    echo ""
fi

# Activar entorno virtual del backoffice
source .venv_backoffice313/bin/activate

# Ejecutar tests del backoffice
echo ">>> Tests de Backoffice (flujo completo)"
echo ""

cd src/apps/6_web_backoffice

if [ -z "$TEST_FILTER" ]; then
    pytest tests/test_explorador_version_state.py -v -s
else
    pytest tests/test_explorador_version_state.py -v -s -k "$TEST_FILTER"
fi

backoffice_result=$?

cd ../../..

echo ""
echo "=============================================="

# Ejecutar tests del frontend
echo ""
echo ">>> Tests de Frontend (flujo cliente)"
echo ""

# Activar entorno virtual del frontend
source .venv_frontend313/bin/activate

cd src/apps/5_web_frontend

if [ -z "$TEST_FILTER" ]; then
    pytest tests/test_explorador_version_state.py -v -s
else
    pytest tests/test_explorador_version_state.py -v -s -k "$TEST_FILTER"
fi

frontend_result=$?

cd ../../..

echo ""
echo "=============================================="
echo "Resumen"
echo "=============================================="
echo ""

if [ $backoffice_result -eq 0 ] && [ $frontend_result -eq 0 ]; then
    echo -e "${GREEN}✓ Todos los tests pasaron${NC}"
    exit 0
else
    if [ $backoffice_result -ne 0 ]; then
        echo -e "${RED}✗ Tests de Backoffice fallaron${NC}"
    fi
    if [ $frontend_result -ne 0 ]; then
        echo -e "${RED}✗ Tests de Frontend fallaron${NC}"
    fi
    exit 1
fi
