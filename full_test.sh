#!/bin/bash
# ==============================================================================
# full_test.sh - Ejecuta tests del proyecto anewhope
#
# Uso:
#   ./full_test.sh              # Ejecuta todo (equivale a --all)
#   ./full_test.sh --all        # Ejecuta todo
#   ./full_test.sh --unit       # Solo tests unitarios
#   ./full_test.sh --integration # Solo tests de integración
#   ./full_test.sh --e2e        # Solo tests E2E (standalone)
#   ./full_test.sh --unit --integration  # Combinación
# ==============================================================================

set -o pipefail

# Directorio base del proyecto
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

# Contadores
PASS=0
FAIL=0
SKIP=0
SECTIONS_RUN=()

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ==============================================================================
# Funciones auxiliares
# ==============================================================================

run_section() {
    local name="$1"
    shift
    local cmd="$@"

    echo ""
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE}  $name${NC}"
    echo -e "${BLUE}==========================================${NC}"

    if eval "$cmd"; then
        echo -e "${GREEN}  PASS: $name${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}  FAIL: $name${NC}"
        FAIL=$((FAIL + 1))
    fi
    SECTIONS_RUN+=("$name")
}

activate_venv() {
    local venv="$1"
    if [ -d "$BASE_DIR/$venv" ]; then
        source "$BASE_DIR/$venv/bin/activate"
        return 0
    else
        echo -e "${YELLOW}  SKIP: venv $venv no encontrado${NC}"
        SKIP=$((SKIP + 1))
        return 1
    fi
}

print_summary() {
    echo ""
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE}  RESUMEN DE TESTS${NC}"
    echo -e "${BLUE}==========================================${NC}"
    echo ""

    for section in "${SECTIONS_RUN[@]}"; do
        echo -e "  ${GREEN}[*]${NC} $section"
    done

    echo ""
    echo -e "  ${GREEN}PASS:${NC} $PASS"
    echo -e "  ${RED}FAIL:${NC} $FAIL"
    echo -e "  ${YELLOW}SKIP:${NC} $SKIP"
    echo ""

    if [ $FAIL -eq 0 ]; then
        echo -e "${GREEN}==========================================${NC}"
        echo -e "${GREEN}  TODOS LOS TESTS COMPLETADOS CON EXITO${NC}"
        echo -e "${GREEN}==========================================${NC}"
    else
        echo -e "${RED}==========================================${NC}"
        echo -e "${RED}  $FAIL SECCIONES FALLARON${NC}"
        echo -e "${RED}==========================================${NC}"
    fi
    echo ""
}

# ==============================================================================
# Parse de argumentos
# ==============================================================================

RUN_UNIT=false
RUN_INTEGRATION=false
RUN_E2E=false

if [ $# -eq 0 ]; then
    # Sin argumentos = ejecutar todo
    RUN_UNIT=true
    RUN_INTEGRATION=true
    RUN_E2E=true
fi

while [ $# -gt 0 ]; do
    case "$1" in
        --all)
            RUN_UNIT=true
            RUN_INTEGRATION=true
            RUN_E2E=true
            ;;
        --unit)
            RUN_UNIT=true
            ;;
        --integration)
            RUN_INTEGRATION=true
            ;;
        --e2e)
            RUN_E2E=true
            ;;
        --help|-h)
            echo "Uso: $0 [--all] [--unit] [--integration] [--e2e]"
            echo ""
            echo "  --all          Ejecuta todos los tests (default si no se pasan flags)"
            echo "  --unit         Tests unitarios (src/apps/*/tests/ + tests/unit/)"
            echo "  --integration  Tests de integración (tests/integration/)"
            echo "  --e2e          Tests E2E standalone (tests/test_*.py + tests/test_*.sh)"
            echo ""
            exit 0
            ;;
        *)
            echo "Opción desconocida: $1"
            echo "Usa --help para ver las opciones disponibles"
            exit 1
            ;;
    esac
    shift
done

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}  INICIANDO EJECUCION DE TESTS${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""
echo -e "  Unit:        $RUN_UNIT"
echo -e "  Integration: $RUN_INTEGRATION"
echo -e "  E2E:         $RUN_E2E"

# ==============================================================================
# UNIT TESTS
# ==============================================================================

if [ "$RUN_UNIT" = true ]; then

    # --- Capa compartida + Frontend (venv_frontend313) ---
    if activate_venv ".venv_frontend313"; then

        run_section "shared_application tests" \
            "pytest -v --rootdir=src/2_shared_application src/2_shared_application/tests"

        run_section "Frontend tests (5_web_frontend)" \
            "pytest -v --rootdir=src/apps/5_web_frontend src/apps/5_web_frontend/tests"

        deactivate
    fi

    # --- Backoffice (venv_backoffice313) ---
    if activate_venv ".venv_backoffice313"; then

        run_section "Backoffice tests (6_web_backoffice)" \
            "pytest -v --rootdir=src/apps/6_web_backoffice src/apps/6_web_backoffice/tests"

        deactivate
    fi

    # --- Middleware, Backend, Broker, Service Backend (venv_middleware313) ---
    if activate_venv ".venv_middleware313"; then

        run_section "Service Frontend tests (7_service_frontend)" \
            "pytest -v --rootdir=src/apps/7_service_frontend src/apps/7_service_frontend/tests"

        run_section "Service Backend tests (8_service_backend)" \
            "pytest -v --rootdir=src/apps/8_service_backend src/apps/8_service_backend/tests"

        run_section "Backend Core tests (3_backend)" \
            "pytest -v --rootdir=src/apps/3_backend src/apps/3_backend/tests"

        # --- tests/unit/ ---
        run_section "tests/unit/" \
            "pytest -v tests/unit/"

        deactivate
    fi

    # --- fmanagement (Go, opcional) ---
    FMANAGEMENT_PATH="../fmanagement"
    if [ -d "$FMANAGEMENT_PATH" ] && [ -f "$FMANAGEMENT_PATH/main_test.go" ]; then
        run_section "fmanagement (Go tests)" \
            "cd '$FMANAGEMENT_PATH' && go test -v -timeout 120s && cd '$BASE_DIR'"
    else
        echo ""
        echo -e "${YELLOW}  INFO: fmanagement no encontrado en $FMANAGEMENT_PATH, omitiendo${NC}"
    fi

fi

# ==============================================================================
# INTEGRATION TESTS
# ==============================================================================

if [ "$RUN_INTEGRATION" = true ]; then

    if activate_venv ".venv_middleware313"; then

        run_section "tests/integration/" \
            "pytest -v tests/integration/"

        deactivate
    fi

fi

# ==============================================================================
# E2E TESTS (standalone scripts)
# ==============================================================================

if [ "$RUN_E2E" = true ]; then

    if activate_venv ".venv_middleware313"; then

        # Ejecutar cada test_*.py en tests/ (excluyendo subdirectorios)
        echo ""
        echo -e "${BLUE}==========================================${NC}"
        echo -e "${BLUE}  E2E Python Tests${NC}"
        echo -e "${BLUE}==========================================${NC}"

        for test_file in tests/test_*.py; do
            test_name=$(basename "$test_file" .py)
            run_section "E2E: $test_name" \
                "python3 '$test_file'"
        done

        deactivate
    fi

    # Ejecutar cada test_*.sh en tests/
    echo ""
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE}  E2E Shell Tests${NC}"
    echo -e "${BLUE}==========================================${NC}"

    for test_file in tests/test_*.sh; do
        test_name=$(basename "$test_file" .sh)
        # Saltar test_proyecto_completo.sh porque requiere input interactivo
        if [ "$test_name" = "test_proyecto_completo" ]; then
            echo -e "${YELLOW}  SKIP: $test_name (requiere input interactivo)${NC}"
            SKIP=$((SKIP + 1))
            continue
        fi
        run_section "E2E: $test_name" \
            "bash '$test_file'"
    done

fi

# ==============================================================================
# RESUMEN FINAL
# ==============================================================================

print_summary

# Exit code != 0 si hubo fallos
[ $FAIL -eq 0 ]
