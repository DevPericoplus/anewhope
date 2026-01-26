#!/bin/bash
# Script de verificación rápida de la integración Redis + SharedSessionState
# Ejecuta verificaciones básicas antes de iniciar las aplicaciones

set -e

echo "=========================================="
echo "🔍 VERIFICACIÓN DE INTEGRACIÓN REDIS"
echo "=========================================="
echo ""

# Colores
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# 1. Verificar que Redis está corriendo
echo "1️⃣  Verificando Redis..."
if redis-cli -a PassRedis2025 ping >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis está corriendo${NC}"
else
    echo -e "${RED}❌ Redis NO está corriendo${NC}"
    echo "   Ejecuta: brew services start redis"
    exit 1
fi

# 2. Verificar entornos virtuales
echo ""
echo "2️⃣  Verificando entornos virtuales..."
if [ -d ".venv_frontend313" ]; then
    echo -e "${GREEN}✅ .venv_frontend313 existe${NC}"
else
    echo -e "${RED}❌ .venv_frontend313 NO existe${NC}"
    exit 1
fi

if [ -d ".venv_backoffice313" ]; then
    echo -e "${GREEN}✅ .venv_backoffice313 existe${NC}"
else
    echo -e "${RED}❌ .venv_backoffice313 NO existe${NC}"
    exit 1
fi

# 3. Verificar dependencias Redis
echo ""
echo "3️⃣  Verificando dependencias Redis..."
if .venv_frontend313/bin/pip list | grep -q "redis.*5.2.1"; then
    echo -e "${GREEN}✅ redis==5.2.1 en frontend${NC}"
else
    echo -e "${ORANGE}⚠️  redis==5.2.1 NO encontrado en frontend${NC}"
fi

if .venv_backoffice313/bin/pip list | grep -q "redis.*5.2.1"; then
    echo -e "${GREEN}✅ redis==5.2.1 en backoffice${NC}"
else
    echo -e "${ORANGE}⚠️  redis==5.2.1 NO encontrado en backoffice${NC}"
fi

# 4. Verificar SharedSessionState
echo ""
echo "4️⃣  Verificando SharedSessionState..."
if [ -f "src/2_shared_application/reflex_shared/shared_session_state.py" ]; then
    echo -e "${GREEN}✅ SharedSessionState existe${NC}"
else
    echo -e "${RED}❌ SharedSessionState NO existe${NC}"
    exit 1
fi

if [ -f "src/apps/5_web_frontend/web_frontend/shared_state.py" ]; then
    echo -e "${GREEN}✅ shared_state.py en frontend${NC}"
else
    echo -e "${RED}❌ shared_state.py NO existe en frontend${NC}"
    exit 1
fi

if [ -f "src/apps/6_web_backoffice/web_backoffice/shared_state.py" ]; then
    echo -e "${GREEN}✅ shared_state.py en backoffice${NC}"
else
    echo -e "${RED}❌ shared_state.py NO existe en backoffice${NC}"
    exit 1
fi

# 5. Verificar que los States compilan
echo ""
echo "5️⃣  Verificando compilación..."
cd src/apps/5_web_frontend
if /Users/administrator/develop/anewhope/.venv_frontend313/bin/python -c "
import sys
sys.path.insert(0, '/Users/administrator/develop/anewhope')
sys.path.insert(0, '/Users/administrator/develop/anewhope/src/apps/5_web_frontend')
from web_frontend.web_frontend import State
assert hasattr(State, 'load_user_data')
assert hasattr(State, 'go_to_backoffice')
assert hasattr(State, 'can_access_backoffice')
" 2>/dev/null; then
    echo -e "${GREEN}✅ Frontend State compila correctamente${NC}"
else
    echo -e "${RED}❌ Frontend State tiene errores${NC}"
    exit 1
fi

cd ../6_web_backoffice
if /Users/administrator/develop/anewhope/.venv_backoffice313/bin/python -c "
import sys
sys.path.insert(0, '/Users/administrator/develop/anewhope')
sys.path.insert(0, '/Users/administrator/develop/anewhope/src/apps/6_web_backoffice')
from web_backoffice.web_frontend import State
assert hasattr(State, 'check_backoffice_access')
assert hasattr(State, 'go_to_frontend')
assert hasattr(State, 'can_access_backoffice')
" 2>/dev/null; then
    echo -e "${GREEN}✅ Backoffice State compila correctamente${NC}"
else
    echo -e "${RED}❌ Backoffice State tiene errores${NC}"
    exit 1
fi

cd ../../..

# 6. Verificar configuraciones Redis
echo ""
echo "6️⃣  Verificando configuraciones Redis..."
cd src/apps/5_web_frontend
FRONTEND_REDIS=$(/Users/administrator/develop/anewhope/.venv_frontend313/bin/python -c "
import sys
sys.path.insert(0, '/Users/administrator/develop/anewhope')
from rxconfig import config
print(config.redis_url.split('@')[1])
" 2>/dev/null)
echo -e "   Frontend Redis: ${GREEN}${FRONTEND_REDIS}${NC}"

cd ../6_web_backoffice
BACKOFFICE_REDIS=$(/Users/administrator/develop/anewhope/.venv_backoffice313/bin/python -c "
import sys
sys.path.insert(0, '/Users/administrator/develop/anewhope')
from rxconfig import config
print(config.redis_url.split('@')[1])
" 2>/dev/null)
echo -e "   Backoffice Redis: ${GREEN}${BACKOFFICE_REDIS}${NC}"

if [ "$FRONTEND_REDIS" = "$BACKOFFICE_REDIS" ]; then
    echo -e "${GREEN}✅ Ambas apps usan la MISMA Redis DB${NC}"
else
    echo -e "${RED}❌ Las apps usan diferentes Redis DB${NC}"
    exit 1
fi

cd ../../..

echo ""
echo "=========================================="
echo -e "${GREEN}✅ TODAS LAS VERIFICACIONES PASADAS${NC}"
echo "=========================================="
echo ""
echo "🚀 Listo para iniciar las aplicaciones:"
echo ""
echo "Terminal 1 - Monitoreo:"
echo "  ./scripts/monitor_redis_sessions.py --continuous"
echo ""
echo "Terminal 2 - Frontend:"
echo "  cd src/apps/5_web_frontend"
echo "  source ../../../.venv_frontend313/bin/activate"
echo "  reflex run --env prod"
echo ""
echo "Terminal 3 - Backoffice:"
echo "  cd src/apps/6_web_backoffice"
echo "  source ../../../.venv_backoffice313/bin/activate"
echo "  reflex run --env prod"
echo ""
echo "Terminal 4 - Nginx:"
echo "  ./deploy_nginx_macbook.sh"
echo ""
echo "Navegador:"
echo "  https://tfmmyllm.ai"
echo ""
