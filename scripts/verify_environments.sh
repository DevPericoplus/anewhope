#!/bin/bash
# Script para verificar la configuración de entornos virtuales
# Valida que cada aplicación use su propio entorno virtual dedicado

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "========================================"
echo "🔍 VERIFICACIÓN DE ENTORNOS VIRTUALES"
echo "========================================"
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Contadores
ERRORS=0
WARNINGS=0
SUCCESS=0

# ============================================
# 1. VERIFICAR ENTORNOS VIRTUALES DEDICADOS
# ============================================

echo "1️⃣  Verificando entornos virtuales dedicados..."
echo ""

EXPECTED_VENVS=(
    ".venv_backend313:3_backend:8003"
    ".venv_frontend313:5_web_frontend:8005"
    ".venv_backoffice313:6_web_backoffice:8006"
    ".venv_middleware313:7_service_frontend:8007"
    ".venv_broker313:8_service_backend:8008"
)

for venv_info in "${EXPECTED_VENVS[@]}"; do
    IFS=':' read -r venv_name app_name port <<< "$venv_info"
    
    if [ -d "$ROOT_DIR/$venv_name" ]; then
        echo -e "   ${GREEN}✅${NC} $venv_name → $app_name (puerto $port)"
        ((SUCCESS++))
    else
        echo -e "   ${RED}❌${NC} $venv_name → $app_name (puerto $port) - NO EXISTE"
        ((ERRORS++))
    fi
done

echo ""

# ============================================
# 2. VERIFICAR run.sh (Ejecución Local)
# ============================================

echo "2️⃣  Verificando scripts run.sh..."
echo ""

# Verificar 3_backend
if grep -q ".venv_backend313" "$ROOT_DIR/src/apps/3_backend/run.sh" 2>/dev/null; then
    echo -e "   ${GREEN}✅${NC} 3_backend/run.sh usa .venv_backend313"
    ((SUCCESS++))
else
    echo -e "   ${RED}❌${NC} 3_backend/run.sh NO usa el entorno virtual correcto"
    ((ERRORS++))
fi

# Verificar 5_web_frontend
if grep -q ".venv_frontend313" "$ROOT_DIR/src/apps/5_web_frontend/run.sh" 2>/dev/null; then
    echo -e "   ${GREEN}✅${NC} 5_web_frontend/run.sh usa .venv_frontend313"
    ((SUCCESS++))
else
    echo -e "   ${RED}❌${NC} 5_web_frontend/run.sh NO usa el entorno virtual correcto"
    ((ERRORS++))
fi

# Verificar 6_web_backoffice
if grep -q ".venv_backoffice313" "$ROOT_DIR/src/apps/6_web_backoffice/run.sh" 2>/dev/null; then
    echo -e "   ${GREEN}✅${NC} 6_web_backoffice/run.sh usa .venv_backoffice313"
    ((SUCCESS++))
else
    echo -e "   ${RED}❌${NC} 6_web_backoffice/run.sh NO usa el entorno virtual correcto"
    ((ERRORS++))
fi

# Verificar 7_service_frontend
if grep -q ".venv_middleware313" "$ROOT_DIR/src/apps/7_service_frontend/run.sh" 2>/dev/null; then
    echo -e "   ${GREEN}✅${NC} 7_service_frontend/run.sh usa .venv_middleware313"
    ((SUCCESS++))
else
    echo -e "   ${RED}❌${NC} 7_service_frontend/run.sh NO usa el entorno virtual correcto"
    ((ERRORS++))
fi

# Verificar 8_service_backend
if grep -q ".venv_broker313" "$ROOT_DIR/src/apps/8_service_backend/run.sh" 2>/dev/null; then
    echo -e "   ${GREEN}✅${NC} 8_service_backend/run.sh usa .venv_broker313"
    ((SUCCESS++))
else
    echo -e "   ${RED}❌${NC} 8_service_backend/run.sh NO usa el entorno virtual correcto"
    ((ERRORS++))
fi

echo ""

# ============================================
# 3. VERIFICAR entrypoint.sh (Ejecución Docker)
# ============================================

echo "3️⃣  Verificando scripts entrypoint.sh..."
echo ""

# Verificar 5_web_frontend
if grep -q "cd.*src/apps/5_web_frontend" "$ROOT_DIR/src/apps/5_web_frontend/entrypoint.sh" 2>/dev/null; then
    echo -e "   ${GREEN}✅${NC} 5_web_frontend/entrypoint.sh apunta al directorio correcto"
    ((SUCCESS++))
else
    echo -e "   ${RED}❌${NC} 5_web_frontend/entrypoint.sh NO apunta al directorio correcto"
    ((ERRORS++))
fi

# Verificar 6_web_backoffice - CRÍTICO
if grep -q "cd.*src/apps/6_web_backoffice" "$ROOT_DIR/src/apps/6_web_backoffice/entrypoint.sh" 2>/dev/null; then
    echo -e "   ${GREEN}✅${NC} 6_web_backoffice/entrypoint.sh apunta al directorio correcto"
    ((SUCCESS++))
    
    # Verificar que NO apunta al frontend (error anterior)
    if grep -q "cd.*src/apps/5_web_frontend" "$ROOT_DIR/src/apps/6_web_backoffice/entrypoint.sh" 2>/dev/null; then
        echo -e "   ${RED}❌ ERROR CRÍTICO:${NC} 6_web_backoffice/entrypoint.sh apunta al FRONTEND"
        ((ERRORS++))
    fi
else
    echo -e "   ${RED}❌ ERROR CRÍTICO:${NC} 6_web_backoffice/entrypoint.sh NO apunta al directorio correcto"
    ((ERRORS++))
fi

# Verificar 3_backend
if grep -q "python -m src.apps.3_backend.main" "$ROOT_DIR/src/apps/3_backend/entrypoint.sh" 2>/dev/null; then
    echo -e "   ${GREEN}✅${NC} 3_backend/entrypoint.sh ejecuta el módulo correcto"
    ((SUCCESS++))
else
    echo -e "   ${RED}❌${NC} 3_backend/entrypoint.sh NO ejecuta el módulo correcto"
    ((ERRORS++))
fi

# Verificar 7_service_frontend
if grep -q "python -m src.apps.7_service_frontend.main" "$ROOT_DIR/src/apps/7_service_frontend/entrypoint.sh" 2>/dev/null; then
    echo -e "   ${GREEN}✅${NC} 7_service_frontend/entrypoint.sh ejecuta el módulo correcto"
    ((SUCCESS++))
else
    echo -e "   ${RED}❌${NC} 7_service_frontend/entrypoint.sh NO ejecuta el módulo correcto"
    ((ERRORS++))
fi

# Verificar 8_service_backend
if grep -q "python -m src.apps.8_service_backend.main" "$ROOT_DIR/src/apps/8_service_backend/entrypoint.sh" 2>/dev/null; then
    echo -e "   ${GREEN}✅${NC} 8_service_backend/entrypoint.sh ejecuta el módulo correcto"
    ((SUCCESS++))
else
    echo -e "   ${RED}❌${NC} 8_service_backend/entrypoint.sh NO ejecuta el módulo correcto"
    ((ERRORS++))
fi

echo ""

# ============================================
# 4. VERIFICAR COMPARTICIÓN DE ENTORNOS
# ============================================

echo "4️⃣  Verificando que no hay compartición de entornos..."
echo ""

# Contar cuántas veces aparece cada entorno virtual
VENV_COUNT=$(grep -h "source.*venv" src/apps/*/run.sh 2>/dev/null | sort | uniq -c | awk '$1 > 1 {print}')

if [ -z "$VENV_COUNT" ]; then
    echo -e "   ${GREEN}✅${NC} No hay compartición de entornos virtuales"
    ((SUCCESS++))
else
    echo -e "   ${RED}❌${NC} Entornos virtuales compartidos detectados:"
    echo "$VENV_COUNT"
    ((ERRORS++))
fi

echo ""

# ============================================
# 5. VERIFICAR TRAINER (WARNING)
# ============================================

echo "5️⃣  Verificando estado del trainer..."
echo ""

if [ -f "$ROOT_DIR/src/apps/4_trainer/entrypoint.sh" ]; then
    if grep -q "pendiente de implementación" "$ROOT_DIR/src/apps/4_trainer/entrypoint.sh" 2>/dev/null; then
        echo -e "   ${YELLOW}⚠️${NC}  4_trainer está pendiente de implementación"
        ((WARNINGS++))
    else
        echo -e "   ${GREEN}✅${NC} 4_trainer está implementado"
        ((SUCCESS++))
    fi
else
    echo -e "   ${YELLOW}⚠️${NC}  4_trainer/entrypoint.sh no existe"
    ((WARNINGS++))
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
    echo -e "${GREEN}✅ TODOS LOS ENTORNOS VIRTUALES ESTÁN CORRECTAMENTE CONFIGURADOS${NC}"
    echo ""
    echo "Entornos virtuales dedicados:"
    echo "  • .venv_backend313      → 3_backend (8003)"
    echo "  • .venv_frontend313     → 5_web_frontend (8005)"
    echo "  • .venv_backoffice313   → 6_web_backoffice (8006)"
    echo "  • .venv_middleware313   → 7_service_frontend (8007)"
    echo "  • .venv_broker313       → 8_service_backend (8008)"
    echo ""
    echo "✅ No hay compartición de entornos entre aplicaciones"
    echo ""
    exit 0
else
    echo -e "${RED}❌ SE ENCONTRARON $ERRORS ERRORES EN LA CONFIGURACIÓN${NC}"
    echo ""
    echo "Por favor, revisa la documentación en:"
    echo "  docs/VIRTUAL_ENVIRONMENTS_AUDIT.md"
    echo ""
    exit 1
fi
