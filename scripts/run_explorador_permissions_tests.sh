#!/bin/bash

# Script para ejecutar los tests del sistema de permisos del explorador
# Uso: ./run_explorador_permissions_tests.sh [opciones]
#
# Opciones:
#   all          - Ejecutar todos los tests (por defecto)
#   permissions  - Solo tests de permisos
#   states       - Solo tests de estados de versión
#   files        - Solo tests de operaciones de archivos
#   editor       - Solo tests de permisos de Editor
#   lector       - Solo tests de permisos de Lector
#   auditor      - Solo tests de permisos de Auditor

set -e

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Funciones de utilidad
print_header() {
    echo ""
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
}

print_warning() {
    echo -e "${YELLOW}⚠  $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Verificar que estamos en el directorio correcto
if [ ! -f "README.md" ]; then
    print_error "Este script debe ejecutarse desde la raíz del proyecto"
    exit 1
fi

# Verificar que existe el directorio de tests
TEST_DIR="src/apps/5_web_frontend/tests"
if [ ! -d "$TEST_DIR" ]; then
    print_error "No se encuentra el directorio de tests: $TEST_DIR"
    exit 1
fi

# Verificar servicios requeridos
print_header "Verificando Servicios Requeridos"

check_service() {
    local SERVICE_NAME=$1
    local PORT=$2

    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        print_success "$SERVICE_NAME (puerto $PORT) está corriendo"
        return 0
    else
        print_warning "$SERVICE_NAME (puerto $PORT) NO está corriendo"
        return 1
    fi
}

SERVICES_OK=true

check_service "MariaDB" 3306 || SERVICES_OK=false
check_service "Backend Core" 8003 || SERVICES_OK=false
check_service "Middleware" 8007 || SERVICES_OK=false
check_service "Broker" 8008 || SERVICES_OK=false
check_service "fmanagement" 1666 || SERVICES_OK=false

if [ "$SERVICES_OK" = false ]; then
    echo ""
    print_warning "Algunos servicios no están corriendo. Los tests pueden fallar."
    echo ""
    read -p "¿Desea continuar de todas formas? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Cambiar al directorio de tests
cd "$TEST_DIR"

# Activar entorno virtual si existe
if [ -d "../../../.venv_frontend313" ]; then
    print_header "Activando Entorno Virtual"
    source ../../../.venv_frontend313/bin/activate
    print_success "Entorno virtual activado"
fi

# Determinar qué tests ejecutar
TEST_OPTION="${1:-all}"

print_header "Ejecutando Tests del Explorador"

case "$TEST_OPTION" in
    all)
        print_success "Ejecutando TODOS los tests del explorador"
        pytest test_explorador*.py -v -s
        ;;

    permissions)
        print_success "Ejecutando tests de PERMISOS"
        pytest test_explorador_permissions.py -v -s
        ;;

    states)
        print_success "Ejecutando tests de ESTADOS DE VERSIÓN"
        pytest test_explorador_version_state.py -v -s
        ;;

    files)
        print_success "Ejecutando tests de OPERACIONES DE ARCHIVOS"
        pytest test_explorador_file_actions.py -v -s
        ;;

    editor)
        print_success "Ejecutando tests de permisos de EDITOR"
        pytest test_explorador_permissions.py::test_editor_permissions -v -s
        ;;

    lector)
        print_success "Ejecutando tests de permisos de LECTOR"
        pytest test_explorador_permissions.py::test_lector_permissions -v -s
        ;;

    auditor)
        print_success "Ejecutando tests de permisos de AUDITOR"
        pytest test_explorador_permissions.py::test_auditor_permissions -v -s
        ;;

    *)
        print_error "Opción no válida: $TEST_OPTION"
        echo ""
        echo "Opciones disponibles:"
        echo "  all          - Ejecutar todos los tests (por defecto)"
        echo "  permissions  - Solo tests de permisos"
        echo "  states       - Solo tests de estados de versión"
        echo "  files        - Solo tests de operaciones de archivos"
        echo "  editor       - Solo tests de permisos de Editor"
        echo "  lector       - Solo tests de permisos de Lector"
        echo "  auditor      - Solo tests de permisos de Auditor"
        echo ""
        exit 1
        ;;
esac

# Resultado final
if [ $? -eq 0 ]; then
    print_header "Tests Completados Exitosamente"
    print_success "Todos los tests pasaron ✓"
else
    print_header "Tests Fallidos"
    print_error "Algunos tests fallaron. Revisa el output arriba."
    exit 1
fi
