#!/bin/bash
# ============================================================================
# Script para crear la estructura completa de carpetas del proyecto
# ============================================================================
#
# Propósito: Crear toda la jerarquía de carpetas necesaria para el proyecto
#            según el entorno especificado
#
# Uso: ./scripts/setup_data_structure.sh <entorno> [servidor]
#      - entorno: macbook, dev, pre, pro
#      - servidor: backend, frontend, trainer (opcional - crea todos si no se especifica)
#
# Ejemplo:
#   ./scripts/setup_data_structure.sh macbook
#   ./scripts/setup_data_structure.sh dev backend
#

set -e

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función de ayuda
show_usage() {
    echo "Uso: $0 <entorno> [servidor]"
    echo ""
    echo "Argumentos:"
    echo "  entorno   : macbook | dev | pre | pro"
    echo "  servidor  : backend | frontend | trainer (opcional)"
    echo ""
    echo "Ejemplos:"
    echo "  $0 macbook              # Crea estructura completa para macbook"
    echo "  $0 dev backend          # Crea solo backend server en dev"
    echo ""
    exit 1
}

# Validar argumentos
if [ -z "$1" ]; then
    echo -e "${RED}Error: Debe especificar un entorno${NC}"
    show_usage
fi

ENVIRONMENT=$1
SERVER=$2

# Validar entorno
if [[ ! "$ENVIRONMENT" =~ ^(macbook|dev|pre|pro)$ ]]; then
    echo -e "${RED}Error: Entorno inválido: $ENVIRONMENT${NC}"
    echo "Entornos válidos: macbook, dev, pre, pro"
    exit 1
fi

# Validar servidor si se especificó
if [ -n "$SERVER" ] && [[ ! "$SERVER" =~ ^(backend|frontend|trainer)$ ]]; then
    echo -e "${RED}Error: Servidor inválido: $SERVER${NC}"
    echo "Servidores válidos: backend, frontend, trainer"
    exit 1
fi

# Determinar ruta base según entorno
if [ "$ENVIRONMENT" == "macbook" ]; then
    BASE_PATH="$HOME/data/anewhope/files"
else
    BASE_PATH="/data"
fi

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}Creando estructura de carpetas${NC}"
echo -e "${BLUE}Entorno: ${ENVIRONMENT}${NC}"
echo -e "${BLUE}Ruta base: ${BASE_PATH}${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Función para crear estructura de backend_server
create_backend_structure() {
    local base=$1
    
    echo -e "${YELLOW}Creando estructura para backend_server...${NC}"
    
    # Logs
    mkdir -p "${base}/backend_core/logs"
    mkdir -p "${base}/service_backend/logs"
    mkdir -p "${base}/fmanagement/logs"
    
    # External (ejemplo con una organización y proyecto)
    mkdir -p "${base}/external/ORG0001/PRJ00001/v001/images"
    mkdir -p "${base}/external/ORG0001/PRJ00001/v001/text"
    
    # Internal
    mkdir -p "${base}/internal/models"
    mkdir -p "${base}/internal/reports"
    
    # Persistencia
    mkdir -p "${base}/Mariadb"
    
    # Imágenes Docker
    mkdir -p "${base}/images"
    
    # Crear archivos .gitkeep para preservar estructura vacía en git
    touch "${base}/backend_core/logs/.gitkeep"
    touch "${base}/service_backend/logs/.gitkeep"
    touch "${base}/fmanagement/logs/.gitkeep"
    touch "${base}/external/.gitkeep"
    touch "${base}/internal/models/.gitkeep"
    touch "${base}/internal/reports/.gitkeep"
    touch "${base}/Mariadb/.gitkeep"
    touch "${base}/images/.gitkeep"
    
    echo -e "${GREEN}✅ Backend server estructura creada${NC}"
}

# Función para crear estructura de frontend_server
create_frontend_structure() {
    local base=$1
    
    echo -e "${YELLOW}Creando estructura para frontend_server...${NC}"
    
    # Logs
    mkdir -p "${base}/frontend/logs"
    mkdir -p "${base}/backoffice/logs"
    mkdir -p "${base}/middleware/logs"
    
    # Persistencia
    mkdir -p "${base}/persistence/redis"
    
    # Imágenes Docker
    mkdir -p "${base}/images"
    
    # Crear archivos .gitkeep
    touch "${base}/frontend/logs/.gitkeep"
    touch "${base}/backoffice/logs/.gitkeep"
    touch "${base}/middleware/logs/.gitkeep"
    touch "${base}/persistence/redis/.gitkeep"
    touch "${base}/images/.gitkeep"
    
    echo -e "${GREEN}✅ Frontend server estructura creada${NC}"
}

# Función para crear estructura de trainer_server
create_trainer_structure() {
    local base=$1
    
    echo -e "${YELLOW}Creando estructura para trainer_server...${NC}"
    
    # Logs
    mkdir -p "${base}/backend_ia/logs"
    
    # External (sincronizado desde backend)
    mkdir -p "${base}/external"
    
    # Internal
    mkdir -p "${base}/internal/models"
    mkdir -p "${base}/internal/reports"
    
    # Persistencia
    mkdir -p "${base}/persistence/chroma"
    
    # Imágenes Docker
    mkdir -p "${base}/images"
    
    # Crear archivos .gitkeep
    touch "${base}/backend_ia/logs/.gitkeep"
    touch "${base}/external/.gitkeep"
    touch "${base}/internal/models/.gitkeep"
    touch "${base}/internal/reports/.gitkeep"
    touch "${base}/persistence/chroma/.gitkeep"
    touch "${base}/images/.gitkeep"
    
    echo -e "${GREEN}✅ Trainer server estructura creada${NC}"
}

# Verificar permisos antes de crear
if [ "$ENVIRONMENT" != "macbook" ] && [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}Error: Se requieren permisos de root para crear estructura en ${BASE_PATH}${NC}"
    echo "Ejecute: sudo $0 $*"
    exit 1
fi

# Crear estructura según servidor especificado
if [ -n "$SERVER" ]; then
    # Crear solo para el servidor especificado
    case $SERVER in
        backend)
            if [ "$ENVIRONMENT" == "macbook" ]; then
                create_backend_structure "${BASE_PATH}/backend_server"
            else
                create_backend_structure "${BASE_PATH}"
            fi
            ;;
        frontend)
            if [ "$ENVIRONMENT" == "macbook" ]; then
                create_frontend_structure "${BASE_PATH}/frontend_server"
            else
                create_frontend_structure "${BASE_PATH}"
            fi
            ;;
        trainer)
            if [ "$ENVIRONMENT" == "macbook" ]; then
                create_trainer_structure "${BASE_PATH}/trainer_server"
            else
                create_trainer_structure "${BASE_PATH}"
            fi
            ;;
    esac
else
    # Crear para todos los servidores
    if [ "$ENVIRONMENT" == "macbook" ]; then
        # Crear carpeta docs
        mkdir -p "$HOME/data/anewhope/docs"
        touch "$HOME/data/anewhope/docs/.gitkeep"
        
        create_backend_structure "${BASE_PATH}/backend_server"
        create_frontend_structure "${BASE_PATH}/frontend_server"
        create_trainer_structure "${BASE_PATH}/trainer_server"
    else
        # En producción cada servidor tiene su propia estructura
        echo -e "${YELLOW}En entornos de producción, ejecute este script en cada servidor:${NC}"
        echo "  - Backend server: $0 $ENVIRONMENT backend"
        echo "  - Frontend server: $0 $ENVIRONMENT frontend"
        echo "  - Trainer server: $0 $ENVIRONMENT trainer"
        exit 0
    fi
fi

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Estructura de carpetas creada exitosamente${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# Mostrar estructura creada
if command -v tree &> /dev/null; then
    echo "Estructura creada:"
    if [ "$ENVIRONMENT" == "macbook" ]; then
        tree -L 4 "$HOME/data/anewhope/" -I 'node_modules|.git'
    else
        tree -L 3 "${BASE_PATH}/" -I 'node_modules|.git'
    fi
else
    echo "Tip: Instala 'tree' para visualizar la estructura creada"
    echo "  macOS: brew install tree"
    echo "  Linux: sudo apt-get install tree"
fi
