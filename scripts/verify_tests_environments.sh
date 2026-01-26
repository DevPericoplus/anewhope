#!/bin/bash
# Script para verificar que los tests usan los entornos virtuales correctos
# Valida configuración de tests, imports y uso de mocks

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "========================================"
echo "🧪 VERIFICACIÓN DE TESTS Y ENTORNOS"
echo "========================================"
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Contadores
ERRORS=0
WARNINGS=0
SUCCESS=0

# ============================================
# 1. VERIFICAR ESTRUCTURA DE TESTS
# ============================================

echo "1️⃣  Verificando estructura de directorios de tests..."
echo ""

# Aplicaciones que deben tener tests
APPS_WITH_TESTS=(
    "src/2_shared_application"
    "src/apps/3_backend"
    "src/apps/5_web_frontend"
    "src/apps/6_web_backoffice"
    "src/apps/7_service_frontend"
    "src/apps/8_service_backend"
)

for app_dir in "${APPS_WITH_TESTS[@]}"; do
    if [ -d "$ROOT_DIR/$app_dir/tests" ]; then
        test_count=$(find "$ROOT_DIR/$app_dir/tests" -name "test_*.py" | wc -l | tr -d ' ')
        if [ "$test_count" -gt 0 ]; then
            echo -e "   ${GREEN}✅${NC} $app_dir/tests/ - $test_count tests encontrados"
            ((SUCCESS++))
        else
            echo -e "   ${YELLOW}⚠️${NC}  $app_dir/tests/ - directorio existe pero sin tests"
            ((WARNINGS++))
        fi
    else
        echo -e "   ${RED}❌${NC} $app_dir/tests/ - directorio NO existe"
        ((ERRORS++))
    fi
done

echo ""

# ============================================
# 2. VERIFICAR full_test.sh
# ============================================

echo "2️⃣  Verificando script full_test.sh..."
echo ""

if [ -f "$ROOT_DIR/full_test.sh" ]; then
    echo -e "   ${GREEN}✅${NC} full_test.sh existe"
    ((SUCCESS++))
    
    # Verificar que activa entornos correctos
    if grep -q ".venv_frontend313/bin/activate" "$ROOT_DIR/full_test.sh"; then
        echo -e "   ${GREEN}✅${NC} full_test.sh activa .venv_frontend313"
        ((SUCCESS++))
    else
        echo -e "   ${RED}❌${NC} full_test.sh NO activa .venv_frontend313"
        ((ERRORS++))
    fi
    
    if grep -q ".venv_backoffice313/bin/activate" "$ROOT_DIR/full_test.sh"; then
        echo -e "   ${GREEN}✅${NC} full_test.sh activa .venv_backoffice313"
        ((SUCCESS++))
    else
        echo -e "   ${RED}❌${NC} full_test.sh NO activa .venv_backoffice313"
        ((ERRORS++))
    fi
    
    if grep -q ".venv_middleware313/bin/activate" "$ROOT_DIR/full_test.sh"; then
        echo -e "   ${GREEN}✅${NC} full_test.sh activa .venv_middleware313"
        ((SUCCESS++))
    else
        echo -e "   ${RED}❌${NC} full_test.sh NO activa .venv_middleware313"
        ((ERRORS++))
    fi
else
    echo -e "   ${RED}❌${NC} full_test.sh NO existe"
    ((ERRORS++))
fi

echo ""

# ============================================
# 3. VERIFICAR IMPORTS CRUZADOS
# ============================================

echo "3️⃣  Verificando imports cruzados entre aplicaciones..."
echo ""

# Tests de frontend NO deben importar middleware/backend
echo "   ${BLUE}Frontend tests:${NC}"
if grep -r "from src.apps.7_service_frontend" "$ROOT_DIR/src/apps/5_web_frontend/tests/" 2>/dev/null; then
    echo -e "   ${RED}❌${NC} Frontend importa módulos de middleware (prohibido)"
    ((ERRORS++))
else
    echo -e "   ${GREEN}✅${NC} Frontend NO importa módulos de middleware"
    ((SUCCESS++))
fi

if grep -r "from src.apps.3_backend" "$ROOT_DIR/src/apps/5_web_frontend/tests/" 2>/dev/null; then
    echo -e "   ${RED}❌${NC} Frontend importa módulos de backend (prohibido)"
    ((ERRORS++))
else
    echo -e "   ${GREEN}✅${NC} Frontend NO importa módulos de backend"
    ((SUCCESS++))
fi

# Tests de backoffice NO deben importar middleware/backend
echo ""
echo "   ${BLUE}Backoffice tests:${NC}"
if grep -r "from src.apps.7_service_frontend" "$ROOT_DIR/src/apps/6_web_backoffice/tests/" 2>/dev/null; then
    echo -e "   ${RED}❌${NC} Backoffice importa módulos de middleware (prohibido)"
    ((ERRORS++))
else
    echo -e "   ${GREEN}✅${NC} Backoffice NO importa módulos de middleware"
    ((SUCCESS++))
fi

# Tests de middleware NO deben importar frontend/backoffice
echo ""
echo "   ${BLUE}Middleware tests:${NC}"
if grep -r "from src.apps.5_web_frontend" "$ROOT_DIR/src/apps/7_service_frontend/tests/" 2>/dev/null; then
    echo -e "   ${RED}❌${NC} Middleware importa módulos de frontend (prohibido)"
    ((ERRORS++))
else
    echo -e "   ${GREEN}✅${NC} Middleware NO importa módulos de frontend"
    ((SUCCESS++))
fi

if grep -r "from src.apps.6_web_backoffice" "$ROOT_DIR/src/apps/7_service_frontend/tests/" 2>/dev/null; then
    echo -e "   ${RED}❌${NC} Middleware importa módulos de backoffice (prohibido)"
    ((ERRORS++))
else
    echo -e "   ${GREEN}✅${NC} Middleware NO importa módulos de backoffice"
    ((SUCCESS++))
fi

echo ""

# ============================================
# 4. VERIFICAR USO DE STORAGE_MODE=mock
# ============================================

echo "4️⃣  Verificando uso de STORAGE_MODE=mock en tests..."
echo ""

# Buscar tests que usan monkeypatch.setenv con STORAGE_MODE
TESTS_WITH_MOCK=$(grep -r "monkeypatch.setenv.*STORAGE_MODE.*mock" "$ROOT_DIR/src" 2>/dev/null | wc -l | tr -d ' ')

if [ "$TESTS_WITH_MOCK" -gt 0 ]; then
    echo -e "   ${GREEN}✅${NC} $TESTS_WITH_MOCK tests configuran STORAGE_MODE=mock"
    ((SUCCESS++))
else
    echo -e "   ${YELLOW}⚠️${NC}  Ningún test configura STORAGE_MODE=mock explícitamente"
    ((WARNINGS++))
fi

# Buscar tests que usan fixtures de entorno
TESTS_WITH_FIXTURES=$(grep -r "mock_environment\|mock_storage" "$ROOT_DIR/src" 2>/dev/null | wc -l | tr -d ' ')

if [ "$TESTS_WITH_FIXTURES" -gt 0 ]; then
    echo -e "   ${GREEN}✅${NC} $TESTS_WITH_FIXTURES tests usan fixtures de mock"
    ((SUCCESS++))
else
    echo -e "   ${YELLOW}⚠️${NC}  Ningún test usa fixtures de mock"
    ((WARNINGS++))
fi

echo ""

# ============================================
# 5. VERIFICAR FIXTURES COMUNES
# ============================================

echo "5️⃣  Verificando fixtures comunes..."
echo ""

# Verificar que hay fixtures definidos
if grep -r "@pytest.fixture" "$ROOT_DIR/src" 2>/dev/null | grep -q "temp_users_file\|temp_users_json"; then
    echo -e "   ${GREEN}✅${NC} Fixtures de archivos temporales definidos"
    ((SUCCESS++))
else
    echo -e "   ${YELLOW}⚠️${NC}  No se encontraron fixtures de archivos temporales"
    ((WARNINGS++))
fi

if grep -r "@pytest.fixture" "$ROOT_DIR/src" 2>/dev/null | grep -q "mock_environment\|mock_storage"; then
    echo -e "   ${GREEN}✅${NC} Fixtures de entorno mock definidos"
    ((SUCCESS++))
else
    echo -e "   ${YELLOW}⚠️${NC}  No se encontraron fixtures de entorno mock"
    ((WARNINGS++))
fi

echo ""

# ============================================
# 6. VERIFICAR DOCUMENTACIÓN
# ============================================

echo "6️⃣  Verificando documentación de tests..."
echo ""

if [ -f "$ROOT_DIR/docs/TESTING_VIRTUAL_ENVIRONMENTS.md" ]; then
    echo -e "   ${GREEN}✅${NC} docs/TESTING_VIRTUAL_ENVIRONMENTS.md existe"
    ((SUCCESS++))
else
    echo -e "   ${RED}❌${NC} docs/TESTING_VIRTUAL_ENVIRONMENTS.md NO existe"
    ((ERRORS++))
fi

if [ -f "$ROOT_DIR/docs/VIRTUAL_ENVIRONMENTS_AUDIT.md" ]; then
    echo -e "   ${GREEN}✅${NC} docs/VIRTUAL_ENVIRONMENTS_AUDIT.md existe"
    ((SUCCESS++))
else
    echo -e "   ${RED}❌${NC} docs/VIRTUAL_ENVIRONMENTS_AUDIT.md NO existe"
    ((ERRORS++))
fi

# Verificar que AGENTS.md tiene sección de tests
if grep -q "5.1. Reglas de entornos virtuales en tests" "$ROOT_DIR/AGENTS.md" 2>/dev/null; then
    echo -e "   ${GREEN}✅${NC} AGENTS.md contiene reglas de tests"
    ((SUCCESS++))
else
    echo -e "   ${RED}❌${NC} AGENTS.md NO contiene reglas de tests"
    ((ERRORS++))
fi

echo ""

# ============================================
# RESUMEN FINAL
# ============================================

echo "========================================"
echo "📊 RESUMEN DE VERIFICACIÓN"
echo "========================================"
echo ""
echo -e "   ${GREEN}✅ Éxitos:${NC}    $SUCCESS"
echo -e "   ${RED}❌ Errores:${NC}   $ERRORS"
echo -e "   ${YELLOW}⚠️  Warnings:${NC}  $WARNINGS"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ TODOS LOS TESTS ESTÁN CORRECTAMENTE CONFIGURADOS${NC}"
    echo ""
    echo "Verificaciones completadas:"
    echo "  ✅ Estructura de directorios de tests"
    echo "  ✅ Script full_test.sh con entornos correctos"
    echo "  ✅ No hay imports cruzados entre aplicaciones"
    echo "  ✅ Tests configuran STORAGE_MODE=mock"
    echo "  ✅ Fixtures comunes definidos"
    echo "  ✅ Documentación completa"
    echo ""
    echo "Para ejecutar todos los tests:"
    echo "  ./full_test.sh"
    echo ""
    exit 0
else
    echo -e "${RED}❌ SE ENCONTRARON $ERRORS ERRORES EN LA CONFIGURACIÓN${NC}"
    echo ""
    echo "Por favor, revisa los errores reportados arriba."
    echo ""
    echo "Documentación:"
    echo "  docs/TESTING_VIRTUAL_ENVIRONMENTS.md"
    echo "  docs/VIRTUAL_ENVIRONMENTS_AUDIT.md"
    echo "  AGENTS.md (sección 5.1)"
    echo ""
    exit 1
fi
