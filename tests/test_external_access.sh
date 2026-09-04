#!/bin/bash
# Verificación de acceso HTTP a frontend/nginx del entorno activo.

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=e2e_env.sh
source "${SCRIPT_DIR}/e2e_env.sh"

echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Test de Acceso Externo (entorno ${ANEWHOPE_ENV})${NC}"
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo ""

check_url() {
    local label="$1"
    local url="$2"
    local code
    code=$(curl -k -sS -o /dev/null -w "%{http_code}" --max-time 8 "${url}" || echo "000")
    if echo "${code}" | grep -Eq '200|301|302|401|403'; then
        echo -e "${GREEN}  ✓ ${label}: ${url} → ${code}${NC}"
        return 0
    fi
    echo -e "${RED}  ✗ ${label}: ${url} → ${code}${NC}"
    return 1
}

FAILED=0

if [ "${ANEWHOPE_ENV}" = "silicon" ]; then
    echo -e "${YELLOW}[1/3] Frontend / Backoffice / Middleware (FQDN silicon)${NC}"
    check_url "Frontend" "${TEST_FRONTEND_URL}/ping" || FAILED=1
    check_url "Backoffice" "${TEST_BACKOFFICE_URL}/ping" || FAILED=1
    check_url "Middleware" "${TEST_MIDDLEWARE_URL}/docs" || FAILED=1

    echo ""
    echo -e "${YELLOW}[2/3] Backend Core / fmanagement${NC}"
    check_url "Backend Core" "${TEST_BACKEND_CORE_URL}/docs" || FAILED=1
    check_url "fmanagement" "${TEST_FMANAGEMENT_URL}/fmo/list" || FAILED=1

    echo ""
    echo -e "${YELLOW}[3/3] Nginx público (si está publicado)${NC}"
    FRONTEND_HOST=$(printf '%s' "${TEST_FRONTEND_URL}" | sed -E 's#https?://([^/:]+).*#\1#')
    check_url "Nginx HTTP" "http://${FRONTEND_HOST}" || true
else
    echo -e "${YELLOW}[1/4] Verificando nginx local...${NC}"
    if pgrep nginx > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ nginx está corriendo${NC}"
    else
        echo -e "${RED}  ✗ nginx NO está corriendo${NC}"
        exit 1
    fi

    echo ""
    echo -e "${YELLOW}[2/4] Servicios del entorno${NC}"
    check_url "Frontend" "${TEST_FRONTEND_URL}" || FAILED=1
    check_url "Backoffice" "${TEST_BACKOFFICE_URL}" || FAILED=1
    check_url "Middleware" "${TEST_MIDDLEWARE_URL}/docs" || FAILED=1
fi

echo ""
if [ "${FAILED}" -ne 0 ]; then
    echo -e "${RED}Algunos endpoints no respondieron${NC}"
    exit 1
fi
echo -e "${GREEN}Acceso externo OK${NC}"
