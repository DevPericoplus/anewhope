#!/bin/bash
# ==============================================================================
# full_test.sh - Ejecuta tests del proyecto anewhope
#
# Uso:
#   ./full_test.sh                         # Todo (entorno de .envglobal)
#   ./full_test.sh --env silicon --unit    # Unitarios con contrato silicon
#   ./full_test.sh --env silicon --all     # Suite completa + compose-contract
#   ./full_test.sh --unit --integration
#   ./full_test.sh --deploy                # Certificación compose (silicon)
# ==============================================================================

set -o pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

PASS=0
FAIL=0
SKIP=0
SECTIONS_RUN=()

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ANSIBLE_ENV_DIR="${ANSIBLE_ENV_DIR:-$HOME/develop/anh_ansible_environments}"

run_section() {
    local name="$1"
    shift
    local cmd="$*"

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
        # shellcheck disable=SC1090
        source "$BASE_DIR/$venv/bin/activate"
        return 0
    else
        echo -e "${YELLOW}  SKIP: venv $venv no encontrado${NC}"
        SKIP=$((SKIP + 1))
        return 1
    fi
}

venv_python() {
    local venv="$1"
    local candidate
    for candidate in "$BASE_DIR/$venv/bin/python3.13" "$BASE_DIR/$venv/bin/python3.12" "$BASE_DIR/$venv/bin/python"; do
        if [ -e "$candidate" ] && "$candidate" -c "import sys" >/dev/null 2>&1; then
            printf '%s' "$candidate"
            return 0
        fi
    done
    if command -v python3.13 >/dev/null 2>&1; then
        if [ -d "$BASE_DIR/$venv/lib/python3.13/site-packages" ]; then
            printf '%s' "$(command -v python3.13)"
            return 0
        fi
    fi
    if command -v python3.12 >/dev/null 2>&1; then
        if [ -d "$BASE_DIR/$venv/lib/python3.12/site-packages" ]; then
            printf '%s' "$(command -v python3.12)"
            return 0
        fi
    fi
    return 1
}

run_pytest_in_venv() {
    local venv="$1"
    shift
    local py site
    if ! py="$(venv_python "$venv")"; then
        echo -e "${YELLOW}  SKIP: no hay Python usable para $venv (¿venv de otra máquina?)${NC}"
        SKIP=$((SKIP + 1))
        return 1
    fi
    if [ -d "$BASE_DIR/$venv/lib/python3.13/site-packages" ]; then
        site="$BASE_DIR/$venv/lib/python3.13/site-packages"
    else
        site="$BASE_DIR/$venv/lib/python3.12/site-packages"
    fi
    PYTHONPATH="$site:$BASE_DIR${PYTHONPATH:+:$PYTHONPATH}" "$py" -m pytest "$@"
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

    if [ "$FAIL" -eq 0 ]; then
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

resolve_envglobal() {
    grep -E '^[[:space:]]*current_environment:' "$BASE_DIR/.envglobal" 2>/dev/null \
        | head -1 \
        | awk -F: '{print $2}' \
        | tr -d " '\""
}

# ==============================================================================
# Parse de argumentos
# ==============================================================================

RUN_UNIT=false
RUN_INTEGRATION=false
RUN_E2E=false
RUN_DEPLOY=false
TEST_ENV=""
EXPLICIT_CATEGORY=false

if [ $# -eq 0 ]; then
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
            EXPLICIT_CATEGORY=true
            ;;
        --unit)
            RUN_UNIT=true
            EXPLICIT_CATEGORY=true
            ;;
        --integration)
            RUN_INTEGRATION=true
            EXPLICIT_CATEGORY=true
            ;;
        --e2e)
            RUN_E2E=true
            EXPLICIT_CATEGORY=true
            ;;
        --deploy)
            RUN_DEPLOY=true
            EXPLICIT_CATEGORY=true
            ;;
        --env)
            shift
            TEST_ENV="${1:-}"
            if [ -z "$TEST_ENV" ]; then
                echo "Falta el valor de --env (macbook|dev|pre|pro|silicon)"
                exit 1
            fi
            ;;
        --help|-h)
            echo "Uso: $0 [--all] [--unit] [--integration] [--e2e] [--deploy] [--env ENTORNO]"
            echo ""
            echo "  --all          Ejecuta unit + integration + e2e"
            echo "  --unit         Tests unitarios (STORAGE_MODE=mock)"
            echo "  --integration  Tests de integración (BD/servicios del entorno)"
            echo "  --e2e          Tests E2E standalone"
            echo "  --deploy       Contrato docker-compose (silicon → plantilla dev/pre)"
            echo "  --env ENTORNO  macbook | dev | pre | pro | silicon"
            echo ""
            echo "Sin categorías: ejecuta --all. Si --env silicon y --all, añade --deploy."
            echo "El entorno no cambia .envglobal; solo exporta ANEWHOPE_ENV/ENVIRONMENT."
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

if [ -z "$TEST_ENV" ]; then
    if [ -n "$ANEWHOPE_ENV" ]; then
        TEST_ENV="$ANEWHOPE_ENV"
    elif [ -n "$ENVIRONMENT" ]; then
        TEST_ENV="$ENVIRONMENT"
    else
        TEST_ENV="$(resolve_envglobal)"
        TEST_ENV="${TEST_ENV:-macbook}"
    fi
fi

case "$TEST_ENV" in
    macbook|dev|pre|pro|silicon) ;;
    *)
        echo "Entorno no válido: $TEST_ENV"
        exit 1
        ;;
esac

if [ "$TEST_ENV" = "silicon" ] && [ "$EXPLICIT_CATEGORY" = false ]; then
    RUN_DEPLOY=true
fi
if [ "$TEST_ENV" = "silicon" ] && [ "$RUN_UNIT" = true ] && [ "$RUN_INTEGRATION" = true ] && [ "$RUN_E2E" = true ]; then
    RUN_DEPLOY=true
fi

export ANEWHOPE_ENV="$TEST_ENV"
export ENVIRONMENT="$TEST_ENV"
export PYTHONPATH="$BASE_DIR${PYTHONPATH:+:$PYTHONPATH}"

if MW_PY="$(venv_python ".venv_middleware313")"; then
    eval "$("$MW_PY" -c "import sys; sys.path.insert(0, '$BASE_DIR'); from tests.helpers import emit_shell_exports; print(emit_shell_exports('$TEST_ENV'))")"
else
    eval "$(/opt/homebrew/bin/python3.13 -c "import sys; sys.path.insert(0, '$BASE_DIR'); from tests.helpers import emit_shell_exports; print(emit_shell_exports('$TEST_ENV'))" 2>/dev/null || true)"
    export TEST_MIDDLEWARE_URL="${TEST_MIDDLEWARE_URL:-}"
fi

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}  INICIANDO EJECUCION DE TESTS${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""
echo -e "  Entorno:     $TEST_ENV"
echo -e "  Unit:        $RUN_UNIT"
echo -e "  Integration: $RUN_INTEGRATION"
echo -e "  E2E:         $RUN_E2E"
echo -e "  Deploy:      $RUN_DEPLOY"
echo -e "  Core URL:    ${TEST_BACKEND_CORE_URL:-n/a}"
echo -e "  Middleware:  ${TEST_MIDDLEWARE_URL:-n/a}"
echo ""

# ==============================================================================
# UNIT TESTS (aislados: STORAGE_MODE=mock)
# ==============================================================================

if [ "$RUN_UNIT" = true ]; then
    export STORAGE_MODE=mock

    export STORAGE_MODE=mock
    export ANEWHOPE_ENV="$TEST_ENV"
    export ENVIRONMENT="$TEST_ENV"

    if [ -d "$BASE_DIR/.venv_frontend313" ]; then
        run_section "shared_application tests" \
            "run_pytest_in_venv .venv_frontend313 -v --rootdir=src/2_shared_application src/2_shared_application/tests"

        run_section "Frontend tests (5_web_frontend)" \
            "run_pytest_in_venv .venv_frontend313 -v --rootdir=src/apps/5_web_frontend src/apps/5_web_frontend/tests"
    else
        echo -e "${YELLOW}  SKIP: .venv_frontend313 no encontrado${NC}"
        SKIP=$((SKIP + 2))
    fi

    if [ -d "$BASE_DIR/.venv_backoffice313" ]; then
        run_section "Backoffice tests (6_web_backoffice)" \
            "run_pytest_in_venv .venv_backoffice313 -v --rootdir=src/apps/6_web_backoffice src/apps/6_web_backoffice/tests"
    else
        echo -e "${YELLOW}  SKIP: .venv_backoffice313 no encontrado${NC}"
        SKIP=$((SKIP + 1))
    fi

    if [ -d "$BASE_DIR/.venv_middleware313" ]; then
        run_section "Service Frontend tests (7_service_frontend)" \
            "run_pytest_in_venv .venv_middleware313 -v --rootdir=src/apps/7_service_frontend src/apps/7_service_frontend/tests"

        run_section "Service Backend tests (8_service_backend)" \
            "run_pytest_in_venv .venv_middleware313 -v --rootdir=src/apps/8_service_backend src/apps/8_service_backend/tests"

        run_section "Backend Core tests (3_backend)" \
            "run_pytest_in_venv .venv_middleware313 -v --rootdir=src/apps/3_backend src/apps/3_backend/tests"

        run_section "tests/unit/" \
            "run_pytest_in_venv .venv_middleware313 -v tests/unit/"
    else
        echo -e "${YELLOW}  SKIP: .venv_middleware313 no encontrado${NC}"
        SKIP=$((SKIP + 4))
    fi

    if [ -d "$BASE_DIR/.venv_trainer312" ]; then
        run_section "Trainer tests (4_trainer)" \
            "run_pytest_in_venv .venv_trainer312 -v --rootdir=src/apps/4_trainer src/apps/4_trainer/tests"
    else
        echo -e "${YELLOW}  SKIP: .venv_trainer312 no encontrado${NC}"
        SKIP=$((SKIP + 1))
    fi

    if [ -d "$BASE_DIR/.venv_laimweb313" ]; then
        run_section "LAIM Web tests (9_laimweb)" \
            "run_pytest_in_venv .venv_laimweb313 -v --rootdir=src/apps/9_laimweb src/apps/9_laimweb/tests"
    else
        echo -e "${YELLOW}  SKIP: .venv_laimweb313 no encontrado${NC}"
        SKIP=$((SKIP + 1))
    fi

    FMANAGEMENT_PATH="../fmanagement"
    if [ -d "$FMANAGEMENT_PATH" ] && [ -f "$FMANAGEMENT_PATH/main_test.go" ]; then
        run_section "fmanagement (Go tests)" \
            "cd '$FMANAGEMENT_PATH' && go test -v -timeout 120s && cd '$BASE_DIR'"
    else
        echo ""
        echo -e "${YELLOW}  INFO: fmanagement no encontrado en $FMANAGEMENT_PATH, omitiendo${NC}"
    fi

    unset STORAGE_MODE
fi

# ==============================================================================
# INTEGRATION TESTS (apuntan al entorno --env)
# ==============================================================================

if [ "$RUN_INTEGRATION" = true ]; then
    export ANEWHOPE_ENV="$TEST_ENV"
    export ENVIRONMENT="$TEST_ENV"
    if [ -d "$BASE_DIR/.venv_middleware313" ]; then
        run_section "tests/integration/" \
            "run_pytest_in_venv .venv_middleware313 -v tests/integration/"
    else
        echo -e "${YELLOW}  SKIP: .venv_middleware313 no encontrado${NC}"
        SKIP=$((SKIP + 1))
    fi
fi

# ==============================================================================
# E2E TESTS (standalone scripts)
# ==============================================================================

if [ "$RUN_E2E" = true ]; then
    export ANEWHOPE_ENV="$TEST_ENV"
    export ENVIRONMENT="$TEST_ENV"
    if E2E_PY="$(venv_python ".venv_middleware313")"; then
        echo ""
        echo -e "${BLUE}==========================================${NC}"
        echo -e "${BLUE}  E2E Python Tests${NC}"
        echo -e "${BLUE}==========================================${NC}"

        E2E_SITE="$BASE_DIR/.venv_middleware313/lib/python3.13/site-packages"
        for test_file in tests/test_*.py; do
            test_name=$(basename "$test_file" .py)
            if [ "$test_name" = "test_send_sms_manual" ] || [ "$test_name" = "test_sms_with_verification" ]; then
                if [ -z "${ANEWHOPE_E2E_SMS:-}" ]; then
                    echo -e "${YELLOW}  SKIP: $test_name (SMS real; export ANEWHOPE_E2E_SMS=1 para ejecutarlo)${NC}"
                    SKIP=$((SKIP + 1))
                    continue
                fi
            fi
            run_section "E2E: $test_name" \
                "PYTHONPATH='$BASE_DIR:$E2E_SITE' '$E2E_PY' '$BASE_DIR/tests/run_e2e.py' '$BASE_DIR/$test_file'"
        done
    else
        echo -e "${YELLOW}  SKIP: E2E Python (sin intérprete para .venv_middleware313)${NC}"
        SKIP=$((SKIP + 1))
    fi

    echo ""
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE}  E2E Shell Tests${NC}"
    echo -e "${BLUE}==========================================${NC}"

    for test_file in tests/test_*.sh; do
        test_name=$(basename "$test_file" .sh)
        if [ "$test_name" = "test_proyecto_completo" ]; then
            echo -e "${YELLOW}  SKIP: $test_name (requiere input interactivo)${NC}"
            SKIP=$((SKIP + 1))
            continue
        fi
        run_section "E2E: $test_name" \
            "ANEWHOPE_ENV='$TEST_ENV' ENVIRONMENT='$TEST_ENV' bash '$test_file'"
    done
fi

# ==============================================================================
# DEPLOY / CONTRATO COMPOSE (plantilla silicon)
# ==============================================================================

if [ "$RUN_DEPLOY" = true ]; then
    if [ "$TEST_ENV" != "silicon" ]; then
        echo -e "${YELLOW}  INFO: --deploy está certificado para silicon; entorno=$TEST_ENV${NC}"
    fi
    WRAPPER="$ANSIBLE_ENV_DIR/ansible-playbook-wrapper.sh"
    PLAYBOOK="$ANSIBLE_ENV_DIR/test/test_silicon_deploy.yml"
    if [ -x "$WRAPPER" ] && [ -f "$PLAYBOOK" ]; then
        run_section "silicon compose-contract" \
            "cd '$ANSIBLE_ENV_DIR' && ./ansible-playbook-wrapper.sh -i env/silicon/host test/test_silicon_deploy.yml -e deploy_env=silicon --tags compose-contract"
    else
        echo -e "${YELLOW}  SKIP: playbook compose-contract no encontrado en $ANSIBLE_ENV_DIR${NC}"
        SKIP=$((SKIP + 1))
    fi
fi

print_summary

[ "$FAIL" -eq 0 ]
