#!/bin/bash
# Script para construir y ejecutar Redis en Docker para entorno PRE
# Uso: ./build_and_run_docker.sh [build|run|stop|restart|logs|clean|shell]
# IMPORTANTE: Esta configuración es idéntica a producción para pruebas reales

set -e

# Colores
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuración
IMAGE_NAME="redis-pre"
IMAGE_TAG="8.4.0"
CONTAINER_NAME="redis-pre"
REDIS_PORT="6379"
VOLUME_DATA="redis-pre-data"
VOLUME_LOGS="redis-pre-logs"

# Obtener directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Funciones
build_image() {
    echo -e "${GREEN}📦 Construyendo imagen Docker para Redis PRE...${NC}"
    
    # Verificar que redis.conf existe
    if [ ! -f "$SCRIPT_DIR/redis.conf" ]; then
        echo -e "${RED}❌ Error: redis.conf no encontrado en $SCRIPT_DIR${NC}"
        exit 1
    fi
    
    # Advertencia sobre configuración
    echo -e "${ORANGE}⚠️  IMPORTANTE: Configuración idéntica a producción${NC}"
    
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
    docker volume ls | grep "redis-pre"
}

run_container() {
    echo -e "${GREEN}🚀 Iniciando contenedor Redis PRE...${NC}"
    
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
    
    # Ejecutar contenedor con configuración de pre-producción
    docker run -d \
        --name "${CONTAINER_NAME}" \
        --restart always \
        -p "${REDIS_PORT}:6379" \
        -v "${VOLUME_DATA}:/var/lib/redis" \
        -v "${VOLUME_LOGS}:/var/log/redis" \
        --health-cmd="redis-cli ping || exit 1" \
        --health-interval=20s \
        --health-timeout=3s \
        --health-retries=3 \
        --memory="2g" \
        --cpus="2.0" \
        "${IMAGE_NAME}:${IMAGE_TAG}"
    
    echo -e "${GREEN}✅ Contenedor iniciado: ${CONTAINER_NAME}${NC}"
    echo ""
    docker ps | grep "${CONTAINER_NAME}"
    echo ""
    echo -e "${GREEN}🔍 Verificando conexión...${NC}"
    sleep 5
    docker exec "${CONTAINER_NAME}" redis-cli ping || echo -e "${RED}❌ Redis no responde${NC}"
}

stop_container() {
    echo -e "${ORANGE}🛑 Deteniendo contenedor Redis PRE...${NC}"
    docker stop "${CONTAINER_NAME}"
    echo -e "${GREEN}✅ Contenedor detenido${NC}"
}

restart_container() {
    echo -e "${ORANGE}🔄 Reiniciando contenedor Redis PRE...${NC}"
    docker restart "${CONTAINER_NAME}"
    echo -e "${GREEN}✅ Contenedor reiniciado${NC}"
    sleep 5
    docker exec "${CONTAINER_NAME}" redis-cli ping
}

show_logs() {
    echo -e "${GREEN}📋 Logs del contenedor Redis PRE:${NC}"
    docker logs -f "${CONTAINER_NAME}"
}

clean_all() {
    echo -e "${RED}⚠️  ADVERTENCIA PRE-PRODUCCIÓN: Esto eliminará contenedor, imagen y volúmenes${NC}"
    echo -e "${RED}⚠️  Los datos de sesiones se perderán permanentemente${NC}"
    read -p "¿Estás seguro? (escribe 'SI-CONFIRMO' para confirmar): " confirm
    
    if [ "$confirm" = "SI-CONFIRMO" ]; then
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
    echo -e "${GREEN}💻 Abriendo shell en contenedor Redis PRE...${NC}"
    docker exec -it "${CONTAINER_NAME}" /bin/bash
}

backup() {
    echo -e "${GREEN}💾 Realizando backup de Redis PRE...${NC}"
    
    BACKUP_DIR="./backups"
    BACKUP_FILE="redis-pre-backup-$(date +%Y%m%d_%H%M%S).tar.gz"
    
    mkdir -p "$BACKUP_DIR"
    
    # Forzar guardado en Redis
    docker exec "${CONTAINER_NAME}" redis-cli BGSAVE
    sleep 5
    
    # Backup de volúmenes
    docker run --rm \
        -v "${VOLUME_DATA}:/data:ro" \
        -v "$SCRIPT_DIR/$BACKUP_DIR:/backup" \
        alpine tar czf "/backup/$BACKUP_FILE" -C /data .
    
    echo -e "${GREEN}✅ Backup completado: $BACKUP_DIR/$BACKUP_FILE${NC}"
}

status() {
    echo -e "${GREEN}📊 Estado de Redis PRE:${NC}"
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
    docker volume ls | grep "redis-pre"
    
    echo ""
    
    # Stats
    if docker ps | grep -q "${CONTAINER_NAME}"; then
        echo "📊 Recursos:"
        docker stats "${CONTAINER_NAME}" --no-stream
        
        echo ""
        echo "🏥 Healthcheck:"
        docker inspect "${CONTAINER_NAME}" | grep -A 5 "Health"
        
        echo ""
        echo "🔗 Conexión:"
        docker exec "${CONTAINER_NAME}" redis-cli ping
        
        echo ""
        echo "📊 Info Redis:"
        docker exec "${CONTAINER_NAME}" redis-cli INFO server | grep "redis_version"
        docker exec "${CONTAINER_NAME}" redis-cli INFO memory | grep "used_memory_human"
        docker exec "${CONTAINER_NAME}" redis-cli INFO stats | grep "connected_clients"
        docker exec "${CONTAINER_NAME}" redis-cli DBSIZE
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
    
    backup)
        backup
        ;;
    
    status)
        status
        ;;
    
    *)
        echo "Script de gestión de Redis PRE-PRODUCCIÓN en Docker"
        echo ""
        echo "Uso: $0 {build|run|stop|restart|logs|clean|shell|backup|status}"
        echo ""
        echo "Comandos:"
        echo "  build    - Construir imagen Docker"
        echo "  run      - Ejecutar contenedor (construye si es necesario)"
        echo "  stop     - Detener contenedor"
        echo "  restart  - Reiniciar contenedor"
        echo "  logs     - Ver logs en tiempo real"
        echo "  clean    - Eliminar todo (contenedor, imagen, volúmenes)"
        echo "  shell    - Abrir shell en el contenedor"
        echo "  backup   - Realizar backup de datos"
        echo "  status   - Ver estado detallado del servicio"
        echo ""
        echo "Configuración actual:"
        echo "  Imagen: ${IMAGE_NAME}:${IMAGE_TAG}"
        echo "  Contenedor: ${CONTAINER_NAME}"
        echo "  Puerto: ${REDIS_PORT}"
        echo "  Volumen datos: ${VOLUME_DATA}"
        echo "  Volumen logs: ${VOLUME_LOGS}"
        echo "  Memoria límite: 2GB"
        echo "  CPUs límite: 2.0"
        echo ""
        exit 1
        ;;
esac
