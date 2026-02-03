#!/bin/bash
# ============================================================================
# Script para generar .env desde archivos YAML de configuración
# ============================================================================
#
# Propósito: Leer fmanagement_paths.yml y env.yaml para generar un archivo
#            .env compatible con docker-compose
#
# Uso: ./scripts/generate_docker_env.sh <entorno> [servidor]
#      - entorno: macbook, dev, pre, pro
#      - servidor: backend, frontend, trainer (opcional - genera para todos si no se especifica)
#
# Ejemplo:
#   ./scripts/generate_docker_env.sh dev backend
#   ./scripts/generate_docker_env.sh pro
#

set -e

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Rutas base
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENVIRONMENTS_DIR="${PROJECT_ROOT}/infrastructure/environments"

# Función de ayuda
show_usage() {
    echo "Uso: $0 <entorno> [servidor]"
    echo ""
    echo "Argumentos:"
    echo "  entorno   : macbook | dev | pre | pro"
    echo "  servidor  : backend | frontend | trainer (opcional)"
    echo ""
    echo "Ejemplos:"
    echo "  $0 dev backend          # Genera .env solo para backend server en dev"
    echo "  $0 pro                  # Genera .env para todos los servidores en pro"
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

ENV_DIR="${ENVIRONMENTS_DIR}/${ENVIRONMENT}"
FMANAGEMENT_PATHS="${ENV_DIR}/fmanagement_paths.yml"
ENV_YAML="${ENV_DIR}/env.yaml"

# Verificar que existan los archivos
if [ ! -f "$FMANAGEMENT_PATHS" ]; then
    echo -e "${RED}Error: No existe ${FMANAGEMENT_PATHS}${NC}"
    exit 1
fi

if [ ! -f "$ENV_YAML" ]; then
    echo -e "${RED}Error: No existe ${ENV_YAML}${NC}"
    exit 1
fi

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}Generando archivos .env para ${ENVIRONMENT}${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Función para extraer valor de YAML (simple grep/sed - no requiere yq)
get_yaml_value() {
    local file=$1
    local key=$2
    grep "^${key}:" "$file" | sed 's/^[^:]*:[[:space:]]*//' | tr -d '"' | tr -d "'"
}

# Función para generar .env para un servidor específico
generate_env_for_server() {
    local server=$1
    local output_file="${ENV_DIR}/.env.${server}"
    
    echo -e "${YELLOW}Generando: ${output_file}${NC}"
    
    # Header del archivo
    cat > "$output_file" << EOF
# ============================================================================
# Archivo .env generado automáticamente para ${server} server
# Entorno: ${ENVIRONMENT}
# Generado: $(date '+%Y-%m-%d %H:%M:%S')
# ============================================================================
#
# NO EDITAR MANUALMENTE - Este archivo se genera desde:
# - ${FMANAGEMENT_PATHS}
# - ${ENV_YAML}
#
# Para regenerar: ./scripts/generate_docker_env.sh ${ENVIRONMENT} ${server}
#

EOF

    # Agregar variables comunes
    echo "# Entorno" >> "$output_file"
    echo "ENVIRONMENT=${ENVIRONMENT}" >> "$output_file"
    echo "" >> "$output_file"

    # Variables específicas por servidor
    case $server in
        backend)
            echo "# Backend Server - Rutas de almacenamiento" >> "$output_file"
            echo "BACKEND_CORE_BASE_STORAGE=$(get_yaml_value "$FMANAGEMENT_PATHS" "backend_core_base_storage")" >> "$output_file"
            echo "BACKEND_CORE_INTERNAL_STORAGE=$(get_yaml_value "$FMANAGEMENT_PATHS" "backend_core_internal_storage")" >> "$output_file"
            echo "BACKEND_CORE_MODELS_STORAGE=$(get_yaml_value "$FMANAGEMENT_PATHS" "backend_core_models_storage")" >> "$output_file"
            echo "BACKEND_CORE_REPORTS_STORAGE=$(get_yaml_value "$FMANAGEMENT_PATHS" "backend_core_reports_storage")" >> "$output_file"
            echo "" >> "$output_file"
            
            echo "# Backend Server - Logs" >> "$output_file"
            echo "BACKEND_CORE_LOGS_PATH=$(get_yaml_value "$FMANAGEMENT_PATHS" "backend_core_logs_path")" >> "$output_file"
            echo "SERVICE_BACKEND_LOGS_PATH=$(get_yaml_value "$FMANAGEMENT_PATHS" "service_backend_logs_path")" >> "$output_file"
            echo "FMANAGEMENT_LOGS_PATH=$(get_yaml_value "$FMANAGEMENT_PATHS" "fmanagement_logs_path")" >> "$output_file"
            echo "" >> "$output_file"
            
            echo "# Backend Server - Persistencia" >> "$output_file"
            echo "MARIADB_DATA_PATH=$(get_yaml_value "$FMANAGEMENT_PATHS" "mariadb_data_path")" >> "$output_file"
            echo "" >> "$output_file"
            
            echo "# Backend Server - Versiones Docker" >> "$output_file"
            echo "DOCKER_IMAGE_PREFIX=$(get_yaml_value "$FMANAGEMENT_PATHS" "docker_image_name_prefix")" >> "$output_file"
            echo "BACKEND_CORE_IMAGE_VERSION=$(get_yaml_value "$FMANAGEMENT_PATHS" "backend_core_image_version")" >> "$output_file"
            echo "SERVICE_BACKEND_IMAGE_VERSION=$(get_yaml_value "$FMANAGEMENT_PATHS" "service_backend_image_version")" >> "$output_file"
            echo "FMANAGEMENT_IMAGE_VERSION=$(get_yaml_value "$FMANAGEMENT_PATHS" "fmanagement_image_version")" >> "$output_file"
            ;;
            
        frontend)
            echo "# Frontend Server - Logs" >> "$output_file"
            echo "FRONTEND_LOGS_PATH=$(get_yaml_value "$FMANAGEMENT_PATHS" "frontend_logs_path")" >> "$output_file"
            echo "BACKOFFICE_LOGS_PATH=$(get_yaml_value "$FMANAGEMENT_PATHS" "backoffice_logs_path")" >> "$output_file"
            echo "MIDDLEWARE_LOGS_PATH=$(get_yaml_value "$FMANAGEMENT_PATHS" "middleware_logs_path")" >> "$output_file"
            echo "" >> "$output_file"
            
            echo "# Frontend Server - Persistencia" >> "$output_file"
            echo "REDIS_DATA_PATH=$(get_yaml_value "$FMANAGEMENT_PATHS" "redis_data_path")" >> "$output_file"
            echo "" >> "$output_file"
            
            echo "# Frontend Server - Versiones Docker" >> "$output_file"
            echo "DOCKER_IMAGE_PREFIX=$(get_yaml_value "$FMANAGEMENT_PATHS" "docker_image_name_prefix")" >> "$output_file"
            echo "FRONTEND_IMAGE_VERSION=$(get_yaml_value "$FMANAGEMENT_PATHS" "frontend_image_version")" >> "$output_file"
            echo "BACKOFFICE_IMAGE_VERSION=$(get_yaml_value "$FMANAGEMENT_PATHS" "backoffice_image_version")" >> "$output_file"
            echo "MIDDLEWARE_IMAGE_VERSION=$(get_yaml_value "$FMANAGEMENT_PATHS" "middleware_image_version")" >> "$output_file"
            ;;
            
        trainer)
            echo "# Trainer Server - Rutas de almacenamiento" >> "$output_file"
            echo "BACKEND_IA_BASE_STORAGE=$(get_yaml_value "$FMANAGEMENT_PATHS" "backend_ia_base_storage")" >> "$output_file"
            echo "BACKEND_IA_INTERNAL_STORAGE=$(get_yaml_value "$FMANAGEMENT_PATHS" "backend_ia_internal_storage")" >> "$output_file"
            echo "BACKEND_IA_MODELS_STORAGE=$(get_yaml_value "$FMANAGEMENT_PATHS" "backend_ia_models_storage")" >> "$output_file"
            echo "BACKEND_IA_REPORTS_STORAGE=$(get_yaml_value "$FMANAGEMENT_PATHS" "backend_ia_reports_storage")" >> "$output_file"
            echo "" >> "$output_file"
            
            echo "# Trainer Server - Logs" >> "$output_file"
            echo "BACKEND_IA_LOGS_PATH=$(get_yaml_value "$FMANAGEMENT_PATHS" "backend_ia_logs_path")" >> "$output_file"
            echo "" >> "$output_file"
            
            echo "# Trainer Server - Persistencia" >> "$output_file"
            echo "CHROMA_DATA_PATH=$(get_yaml_value "$FMANAGEMENT_PATHS" "chroma_data_path")" >> "$output_file"
            echo "" >> "$output_file"
            
            echo "# Trainer Server - Versiones Docker" >> "$output_file"
            echo "DOCKER_IMAGE_PREFIX=$(get_yaml_value "$FMANAGEMENT_PATHS" "docker_image_name_prefix")" >> "$output_file"
            echo "BACKEND_IA_IMAGE_VERSION=$(get_yaml_value "$FMANAGEMENT_PATHS" "backend_ia_image_version")" >> "$output_file"
            ;;
    esac
    
    echo -e "${GREEN}✅ Generado: ${output_file}${NC}"
}

# Generar para servidores especificados
if [ -n "$SERVER" ]; then
    # Generar solo para el servidor especificado
    generate_env_for_server "$SERVER"
else
    # Generar para todos los servidores
    generate_env_for_server "backend"
    generate_env_for_server "frontend"
    generate_env_for_server "trainer"
fi

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Archivos .env generados exitosamente${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Archivos generados en: ${ENV_DIR}/"
ls -lh "${ENV_DIR}"/.env.* 2>/dev/null || echo "No se encontraron archivos .env.*"
