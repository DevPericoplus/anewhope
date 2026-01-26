#!/bin/bash
# Script para clonar 5_web_frontend → 6_web_backoffice
# con cambios específicos para backoffice

set -e

echo "========================================================"
echo "CLONACIÓN: Frontend → Backoffice"
echo "========================================================"
echo ""

# Colores para output
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar que estamos en la raíz del proyecto
if [ ! -d "src/apps/5_web_frontend" ]; then
    echo -e "${RED}❌ Error: No se encuentra src/apps/5_web_frontend${NC}"
    echo "   Ejecuta este script desde la raíz del proyecto"
    exit 1
fi

# Verificar si ya existe backoffice
if [ -d "src/apps/6_web_backoffice" ]; then
    echo -e "${ORANGE}⚠️  Ya existe src/apps/6_web_backoffice${NC}"
    read -p "¿Deseas eliminarlo y recrearlo? (s/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        echo "🗑️  Eliminando directorio existente..."
        rm -rf src/apps/6_web_backoffice
    else
        echo "Operación cancelada"
        exit 0
    fi
fi

# Paso 1: Copiar directorio completo
echo -e "${GREEN}📁 Paso 1: Copiando estructura completa...${NC}"
cp -R src/apps/5_web_frontend src/apps/6_web_backoffice
echo "   ✓ Estructura copiada"

cd src/apps/6_web_backoffice

# Paso 2: Renombrar carpeta principal
echo -e "${GREEN}📝 Paso 2: Renombrando carpeta principal...${NC}"
if [ -d "web_frontend" ]; then
    mv web_frontend web_backoffice
    echo "   ✓ web_frontend → web_backoffice"
fi

# Paso 3: Crear rxconfig.py para backoffice con Redis
echo -e "${GREEN}⚙️  Paso 3: Creando rxconfig.py con Redis...${NC}"
cat > rxconfig.py << 'EOF'
"""
Configuración de Reflex para la aplicación backoffice
Con soporte para sesión compartida mediante Redis
"""
import reflex as rx
import sys
import importlib.util
from pathlib import Path

# Cargar env_settings dinámicamente (evita SyntaxError con nombres numéricos)
env_settings_path = Path(__file__).resolve().parent.parent.parent / "2_shared_application" / "config" / "env_settings.py"
spec = importlib.util.spec_from_file_location("env_settings", env_settings_path)
env_settings = importlib.util.module_from_spec(spec)
sys.modules["env_settings"] = env_settings
spec.loader.exec_module(env_settings)

# Leer configuración de Redis (MISMA configuración que frontend)
REDIS_HOST = env_settings.get_env_value("redis_host", "localhost")
REDIS_PORT = int(env_settings.get_env_value("redis_port", "6379"))
REDIS_PASSWORD = env_settings.get_protected_value("redis_password", None)
REDIS_DB = int(env_settings.get_env_value("redis_db", "0"))  # ⚠️ DEBE SER LA MISMA DB que frontend

# Construir URL de Redis
if REDIS_PASSWORD:
    redis_url = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

config = rx.Config(
    app_name="web_backoffice",
    db_url="sqlite:///backoffice.db",
    
    # Configuración de Redis para sesión compartida (MISMA que frontend)
    # Reflex detecta automáticamente Redis y lo usa como state manager
    redis_url=redis_url,
    
    # Configuración de servidor
    env=rx.Env.PROD,
    backend_port=8006,
    api_url="https://tfmmyllm.ai/backoffice",
    backend_host="0.0.0.0",
    
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)
EOF
echo "   ✓ rxconfig.py creado con configuración Redis"

# Paso 4: Actualizar imports en archivos Python
echo -e "${GREEN}🔄 Paso 4: Actualizando imports...${NC}"
find web_backoffice -name "*.py" -type f -exec sed -i '' \
    -e 's/from web_frontend/from web_backoffice/g' \
    -e 's/import web_frontend/import web_backoffice/g' \
    -e 's/"web_frontend"/"web_backoffice"/g' \
    -e "s/'web_frontend'/'web_backoffice'/g" \
    {} + 2>/dev/null || echo "   ℹ️  Algunos archivos no se pudieron modificar (normal en macOS)"
echo "   ✓ Imports actualizados"

# Paso 5: Cambiar colores verde → naranja
echo -e "${GREEN}🎨 Paso 5: Cambiando colores verde → naranja...${NC}"
find web_backoffice -name "*.py" -type f -exec sed -i '' \
    -e 's/#00FF00/#FF8C00/g' \
    -e 's/#0f0/#FF8C00/g' \
    -e 's/#008000/#FF8C00/g' \
    -e 's/color="#00FF00"/color="#FF8C00"/g' \
    -e 's/color_scheme="green"/color_scheme="orange"/g' \
    -e 's/bg_color="green"/bg_color="orange"/g' \
    -e 's/background_color="green"/background_color="orange"/g' \
    {} + 2>/dev/null
echo "   ✓ Colores actualizados"

# Paso 6: Renombrar entorno virtual si existe
echo -e "${GREEN}🐍 Paso 6: Manejando entorno virtual...${NC}"
if [ -d "../../../.venv_frontend313" ]; then
    echo "   ℹ️  El entorno virtual frontend existe en la raíz"
    echo "   📋 Deberás crear uno nuevo para backoffice:"
    echo "      python3.13 -m venv ../../../.venv_backoffice313"
else
    echo "   ℹ️  No se encontró entorno virtual en raíz"
fi

# Paso 7: Actualizar run.sh
echo -e "${GREEN}📜 Paso 7: Actualizando run.sh...${NC}"
if [ -f "run.sh" ]; then
    sed -i '' 's/.venv_frontend313/.venv_backoffice313/g' run.sh
    sed -i '' 's/web_frontend/web_backoffice/g' run.sh
    sed -i '' 's/8005/8006/g' run.sh
    echo "   ✓ run.sh actualizado"
fi

# Paso 8: Limpiar directorios de build
echo -e "${GREEN}🧹 Paso 8: Limpiando directorios de build...${NC}"
rm -rf .web public __pycache__ .states 2>/dev/null
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null
echo "   ✓ Build limpio"

# Volver a la raíz
cd ../../..

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ CLONACIÓN COMPLETADA${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "📋 Estructura creada:"
echo "   src/apps/6_web_backoffice/"
echo "   ├── web_backoffice/"
echo "   ├── rxconfig.py"
echo "   ├── run.sh"
echo "   └── requirements.txt"
echo ""
echo -e "${ORANGE}⚠️  TAREAS PENDIENTES (manuales):${NC}"
echo ""
echo "1. Crear entorno virtual:"
echo "   ${GREEN}python3.13 -m venv .venv_backoffice313${NC}"
echo ""
echo "2. Activar e instalar dependencias:"
echo "   ${GREEN}source .venv_backoffice313/bin/activate${NC}"
echo "   ${GREEN}cd src/apps/6_web_backoffice${NC}"
echo "   ${GREEN}pip install -r requirements.txt${NC}"
echo ""
echo "3. Eliminar panel 'Acceso de Usuario' en:"
echo "   ${GREEN}src/apps/6_web_backoffice/web_backoffice/web_backoffice.py${NC}"
echo "   (Buscar y eliminar la función/componente correspondiente)"
echo ""
echo "4. Implementar SessionManager compartido:"
echo "   ${GREEN}src/2_shared_application/session_manager.py${NC}"
echo ""
echo "5. Añadir botón 'Backoffice' en frontend:"
echo "   ${GREEN}src/apps/5_web_frontend/web_frontend/web_frontend.py${NC}"
echo ""
echo "6. Añadir botón 'Volver' en backoffice:"
echo "   ${GREEN}src/apps/6_web_backoffice/web_backoffice/web_backoffice.py${NC}"
echo ""
echo "7. Probar compilación:"
echo "   ${GREEN}cd src/apps/6_web_backoffice${NC}"
echo "   ${GREEN}source ../../../.venv_backoffice313/bin/activate${NC}"
echo "   ${GREEN}reflex init${NC}"
echo "   ${GREEN}reflex export --no-zip${NC}"
echo ""
echo "8. Ejecutar en producción:"
echo "   ${GREEN}reflex run --env prod${NC}"
echo ""
echo "📚 Documentación completa en:"
echo "   ${GREEN}docs/SWITCHING_DESIGN.md${NC}"
echo ""
