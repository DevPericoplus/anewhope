#!/bin/bash
# Script para construir y ejecutar Redis en Docker para entorno DEV
# Uso: ./build_and_run_docker.sh [build|run|stop|restart|logs|clean|shell]

set -e

# Colores
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuración
IMAGE_NAME="redis-dev"
IMAGE_TAG="8.4.0"
CONTAINER_NAME="redis-dev"
REDIS_PORT="6379"
VOLUME_DATA="redis-dev-data"
VOLUME_LOGS="redis-dev-logs"

# Obtener directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Funciones
build_image() {
    echo -e "${GREEN}📦 Construyendo imagen Docker para Redis DEV...${NC}"
    
    # Verificar que redis.conf existe
    if [ ! -f "$SCRIPT_DIR/redis.conf" ]; then
        echo -e "${RED}❌ Error: redis.conf no encontrado en $SCRIPT_DIR${NC}"
        exit 1
    fi
    
    # Construir imagen
    docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" \
                 -t "${IMAGE_NAME}:latest" \
                 -f "$SCRIPT_DIR/Dockerfile" \
                 "$SCRIPT_DIR"
    
    echo -e "${GREEN}✅ Imagen construida: ${IMAGE_NAME}:${IMAGE_TAG}${NC}"
    docker images | grep "${IMAGE_NAME}"
}

create_volumes() {
    echo -e "${GREEN}📂 Creando volúmenes Docker...${NC}"
    
    # Crear volúmenes si no existen
    docker volume create "${VOLUME_DATA}" 2>/dev/null || true
    docker volume create "${VOLUME_LOGS}" 2>/dev/null || true
    
    echo -e "${GREEN}✅ Volúmenes creados:${NC}"
    docker volume ls | grep "redis-dev"
}

run_container() {
    echo -e "${GREEN}🚀 Iniciando contenedor Redis DEV...${NC}"
    
    # Verificar que la imagen existe
    if ! docker images | grep -q "${IMAGE_NAME}"; then
        echo -e "${ORANGE}⚠️  Imagen no encontrada. Construyendo...${NC}"
        build_image
    fi
    
    # Crear volúmenes si no existen
    create_volumes
    
    # Detener contenedor existente si está corriendo
    if docker ps -a | grep -q "${CONTAINER_NAME}"; then
        echo -e "${ORANGE}⚠️  Deteniendo contenedor existente...${NC}"
        docker stop "${CONTAINER_NAME}" 2>/dev/null || true
        docker rm "${CONTAINER_NAME}" 2>/dev/null || true
    fi
    
    # Ejecutar contenedor
    docker run -d \
        --name "${CONTAINER_NAME}" \
        --restart unless-stopped \
        -p "${REDIS_PORT}:6379" \
        -v "${VOLUME_DATA}:/var/lib/redis" \
        -v "${VOLUME_LOGS}:/var/log/redis" \
        --health-cmd="redis-cli ping || exit 1" \
        --health-interval=30s \
        --health-timeout=3s \
        --health-retries=3 \
        "${IMAGE_NAME}:${IMAGE_TAG}"
    
    echo -e "${GREEN}✅ Contenedor iniciado: ${CONTAINER_NAME}${NC}"
    echo ""
    docker ps | grep "${CONTAINER_NAME}"
    echo ""
    echo -e "${GREEN}🔍 Verificando conexión...${NC}"
    sleep 3
    docker exec "${CONTAINER_NAME}" redis-cli ping || echo -e "${RED}❌ Redis no responde${NC}"
}

stop_container() {
    echo -e "${ORANGE}🛑 Deteniendo contenedor Redis DEV...${NC}"
    docker stop "${CONTAINER_NAME}"
    echo -e "${GREEN}✅ Contenedor detenido${NC}"
}

restart_container() {
    echo -e "${ORANGE}🔄 Reiniciando contenedor Redis DEV...${NC}"
    docker restart "${CONTAINER_NAME}"
    echo -e "${GREEN}✅ Contenedor reiniciado${NC}"
    sleep 3
    docker exec "${CONTAINER_NAME}" redis-cli ping
}

show_logs() {
    echo -e "${GREEN}📋 Logs del contenedor Redis DEV:${NC}"
    docker logs -f "${CONTAINER_NAME}"
}

clean_all() {
    echo -e "${RED}⚠️  ADVERTENCIA: Esto eliminará el contenedor, imagen y volúmenes${NC}"
    read -p "¿Estás seguro? (escribe 'SI' para confirmar): " confirm
    
    if [ "$confirm" = "SI" ]; then
        echo -e "${ORANGE}🧹 Limpiando...${NC}"
        
        # Detener y eliminar contenedor
        docker stop "${CONTAINER_NAME}" 2>/dev/null || true
        docker rm "${CONTAINER_NAME}" 2>/dev/null || true
        
        # Eliminar imagen
        docker rmi "${IMAGE_NAME}:${IMAGE_TAG}" 2>/dev/null || true
        docker rmi "${IMAGE_NAME}:latest" 2>/dev/null || true
        
        # Eliminar volúmenes
        docker volume rm "${VOLUME_DATA}" 2>/dev/null || true
        docker volume rm "${VOLUME_LOGS}" 2>/dev/null || true
        
        echo -e "${GREEN}✅ Limpieza completada${NC}"
    else
        echo "Operación cancelada"
    fi
}

open_shell() {
    echo -e "${GREEN}💻 Abriendo shell en contenedor Redis DEV...${NC}"
    docker exec -it "${CONTAINER_NAME}" /bin/bash
}

status() {
    echo -e "${GREEN}📊 Estado de Redis DEV:${NC}"
    echo ""
    
    # Contenedor
    if docker ps | grep -q "${CONTAINER_NAME}"; then
        echo -e "${GREEN}✅ Contenedor: Corriendo${NC}"
        docker ps | grep "${CONTAINER_NAME}"
    else
        echo -e "${RED}❌ Contenedor: Detenido${NC}"
    fi
    
    echo ""
    
    # Volúmenes
    echo "📦 Volúmenes:"
    docker volume ls | grep "redis-dev"
    
    echo ""
    
    # Healthcheck
    if docker ps | grep -q "${CONTAINER_NAME}"; then
        echo "🏥 Healthcheck:"
        docker inspect "${CONTAINER_NAME}" | grep -A 5 "Health"
        
        echo ""
        echo "🔗 Conexión:"
        docker exec "${CONTAINER_NAME}" redis-cli ping
        
        echo ""
        echo "📊 Info:"
        docker exec "${CONTAINER_NAME}" redis-cli INFO server | grep "redis_version"
        docker exec "${CONTAINER_NAME}" redis-cli INFO stats | grep "connected_clients"
    fi
}

# Comandos
case "$1" in
    build)
        build_image
        ;;
    
    run)
        run_container
        ;;
    
    stop)
        stop_container
        ;;
    
    restart)
        restart_container
        ;;
    
    logs)
        show_logs
        ;;
    
    clean)
        clean_all
        ;;
    
    shell)
        open_shell
        ;;
    
    status)
        status
        ;;
    
    *)
        echo "Script de gestión de Redis DEV en Docker"
        echo ""
        echo "Uso: $0 {build|run|stop|restart|logs|clean|shell|status}"
        echo ""
        echo "Comandos:"
        echo "  build    - Construir imagen Docker"
        echo "  run      - Ejecutar contenedor (construye si es necesario)"
        echo "  stop     - Detener contenedor"
        echo "  restart  - Reiniciar contenedor"
        echo "  logs     - Ver logs en tiempo real"
        echo "  clean    - Eliminar todo (contenedor, imagen, volúmenes)"
        echo "  shell    - Abrir shell en el contenedor"
        echo "  status   - Ver estado del servicio"
        echo ""
        echo "Configuración actual:"
        echo "  Imagen: ${IMAGE_NAME}:${IMAGE_TAG}"
        echo "  Contenedor: ${CONTAINER_NAME}"
        echo "  Puerto: ${REDIS_PORT}"
        echo "  Volumen datos: ${VOLUME_DATA}"
        echo "  Volumen logs: ${VOLUME_LOGS}"
        echo ""
        exit 1
        ;;
esac
