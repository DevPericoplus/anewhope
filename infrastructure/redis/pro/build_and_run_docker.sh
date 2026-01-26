#!/bin/bash
# Script para construir y ejecutar Redis en Docker para entorno PRODUCCIÓN
# Uso: ./build_and_run_docker.sh [build|run|stop|restart|logs|clean|shell|backup|restore]
# CRÍTICO: Este script gestiona Redis de producción - Requiere aprobación para cambios

set -e

# Colores
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuración
IMAGE_NAME="redis-pro"
IMAGE_TAG="8.4.0"
CONTAINER_NAME="redis-pro"
REDIS_PORT="6379"
VOLUME_DATA="redis-pro-data"
VOLUME_LOGS="redis-pro-logs"
BACKUP_RETENTION_DAYS=30

# Obtener directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Funciones
check_production_approval() {
    echo -e "${RED}⚠️  ENTORNO DE PRODUCCIÓN${NC}"
    echo -e "${ORANGE}Esta operación afecta al servicio de Redis en producción${NC}"
    read -p "¿Tienes aprobación para continuar? (escribe 'APROBADO' para confirmar): " approval
    
    if [ "$approval" != "APROBADO" ]; then
        echo -e "${RED}❌ Operación cancelada - Aprobación requerida${NC}"
        exit 1
    fi
}

build_image() {
    echo -e "${GREEN}📦 Construyendo imagen Docker para Redis PRODUCCIÓN...${NC}"
    
    check_production_approval
    
    # Verificar que redis.conf existe
    if [ ! -f "$SCRIPT_DIR/redis.conf" ]; then
        echo -e "${RED}❌ Error: redis.conf no encontrado en $SCRIPT_DIR${NC}"
        exit 1
    fi
    
    # Advertencia de seguridad
    echo -e "${ORANGE}⚠️  CRÍTICO: Máxima seguridad y estabilidad${NC}"
    
    # Construir imagen
    docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" \
                 -t "${IMAGE_NAME}:latest" \
                 -f "$SCRIPT_DIR/Dockerfile" \
                 "$SCRIPT_DIR"
    
    echo -e "${GREEN}✅ Imagen construida: ${IMAGE_NAME}:${IMAGE_TAG}${NC}"
    docker images | grep "${IMAGE_NAME}"
    
    # Log de auditoría
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Imagen Redis PRO construida por $(whoami)" >> "$SCRIPT_DIR/audit.log"
}

create_volumes() {
    echo -e "${GREEN}📂 Creando volúmenes Docker...${NC}"
    
    # Crear volúmenes si no existen
    docker volume create "${VOLUME_DATA}" 2>/dev/null || true
    docker volume create "${VOLUME_LOGS}" 2>/dev/null || true
    
    echo -e "${GREEN}✅ Volúmenes creados:${NC}"
    docker volume ls | grep "redis-pro"
}

run_container() {
    echo -e "${GREEN}🚀 Iniciando contenedor Redis PRODUCCIÓN...${NC}"
    
    check_production_approval
    
    # Verificar que la imagen existe
    if ! docker images | grep -q "${IMAGE_NAME}"; then
        echo -e "${ORANGE}⚠️  Imagen no encontrada. Construyendo...${NC}"
        build_image
    fi
    
    # Crear volúmenes si no existen
    create_volumes
    
    # Backup automático antes de reiniciar
    if docker ps | grep -q "${CONTAINER_NAME}"; then
        echo -e "${ORANGE}⚠️  Realizando backup automático antes de reiniciar...${NC}"
        backup_silent
    fi
    
    # Detener contenedor existente si está corriendo
    if docker ps -a | grep -q "${CONTAINER_NAME}"; then
        echo -e "${ORANGE}⚠️  Deteniendo contenedor existente...${NC}"
        docker stop "${CONTAINER_NAME}" 2>/dev/null || true
        docker rm "${CONTAINER_NAME}" 2>/dev/null || true
    fi
    
    # Ejecutar contenedor con configuración de producción MÁXIMA
    docker run -d \
        --name "${CONTAINER_NAME}" \
        --restart always \
        -p "${REDIS_PORT}:6379" \
        -v "${VOLUME_DATA}:/var/lib/redis" \
        -v "${VOLUME_LOGS}:/var/log/redis" \
        --health-cmd="redis-cli ping || exit 1" \
        --health-interval=15s \
        --health-timeout=3s \
        --health-retries=5 \
        --memory="8g" \
        --memory-reservation="6g" \
        --cpus="4.0" \
        --log-driver json-file \
        --log-opt max-size=100m \
        --log-opt max-file=5 \
        --security-opt no-new-privileges:true \
        "${IMAGE_NAME}:${IMAGE_TAG}"
    
    echo -e "${GREEN}✅ Contenedor iniciado: ${CONTAINER_NAME}${NC}"
    echo ""
    docker ps | grep "${CONTAINER_NAME}"
    echo ""
    echo -e "${GREEN}🔍 Verificando conexión...${NC}"
    sleep 10
    
    if docker exec "${CONTAINER_NAME}" redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis responde correctamente${NC}"
    else
        echo -e "${RED}❌ Redis no responde - Revisar logs${NC}"
        docker logs --tail 50 "${CONTAINER_NAME}"
        exit 1
    fi
    
    # Log de auditoría
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Redis PRO iniciado por $(whoami)" >> "$SCRIPT_DIR/audit.log"
}

stop_container() {
    echo -e "${ORANGE}🛑 Deteniendo contenedor Redis PRODUCCIÓN...${NC}"
    
    check_production_approval
    
    # Backup automático antes de detener
    echo -e "${ORANGE}⚠️  Realizando backup automático antes de detener...${NC}"
    backup_silent
    
    docker stop "${CONTAINER_NAME}"
    echo -e "${GREEN}✅ Contenedor detenido${NC}"
    
    # Log de auditoría
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Redis PRO detenido por $(whoami)" >> "$SCRIPT_DIR/audit.log"
}

restart_container() {
    echo -e "${ORANGE}🔄 Reiniciando contenedor Redis PRODUCCIÓN...${NC}"
    
    check_production_approval
    
    # Backup automático antes de reiniciar
    echo -e "${ORANGE}⚠️  Realizando backup automático antes de reiniciar...${NC}"
    backup_silent
    
    docker restart "${CONTAINER_NAME}"
    echo -e "${GREEN}✅ Contenedor reiniciado${NC}"
    sleep 10
    docker exec "${CONTAINER_NAME}" redis-cli ping
    
    # Log de auditoría
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Redis PRO reiniciado por $(whoami)" >> "$SCRIPT_DIR/audit.log"
}

show_logs() {
    echo -e "${GREEN}📋 Logs del contenedor Redis PRODUCCIÓN:${NC}"
    docker logs -f "${CONTAINER_NAME}"
}

backup_silent() {
    BACKUP_DIR="$SCRIPT_DIR/backups"
    BACKUP_FILE="redis-pro-backup-$(date +%Y%m%d_%H%M%S).tar.gz"
    
    mkdir -p "$BACKUP_DIR"
    
    # Forzar guardado en Redis
    docker exec "${CONTAINER_NAME}" redis-cli BGSAVE > /dev/null 2>&1 || true
    sleep 5
    
    # Backup de volúmenes
    docker run --rm \
        -v "${VOLUME_DATA}:/data:ro" \
        -v "$BACKUP_DIR:/backup" \
        alpine tar czf "/backup/$BACKUP_FILE" -C /data . > /dev/null 2>&1
}

backup() {
    echo -e "${GREEN}💾 Realizando backup de Redis PRODUCCIÓN...${NC}"
    
    BACKUP_DIR="$SCRIPT_DIR/backups"
    BACKUP_FILE="redis-pro-backup-$(date +%Y%m%d_%H%M%S).tar.gz"
    
    mkdir -p "$BACKUP_DIR"
    
    # Forzar guardado en Redis
    echo "Ejecutando BGSAVE..."
    docker exec "${CONTAINER_NAME}" redis-cli BGSAVE
    sleep 5
    
    # Backup de volúmenes
    echo "Creando archivo de backup..."
    docker run --rm \
        -v "${VOLUME_DATA}:/data:ro" \
        -v "$BACKUP_DIR:/backup" \
        alpine tar czf "/backup/$BACKUP_FILE" -C /data .
    
    echo -e "${GREEN}✅ Backup completado: $BACKUP_DIR/$BACKUP_FILE${NC}"
    
    # Limpiar backups antiguos
    echo "Limpiando backups antiguos (> ${BACKUP_RETENTION_DAYS} días)..."
    find "$BACKUP_DIR" -name "redis-pro-backup-*.tar.gz" -mtime +${BACKUP_RETENTION_DAYS} -delete
    
    # Mostrar backups disponibles
    echo ""
    echo "Backups disponibles:"
    ls -lh "$BACKUP_DIR"/redis-pro-backup-*.tar.gz 2>/dev/null || echo "No hay backups"
    
    # Log de auditoría
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup Redis PRO creado por $(whoami): $BACKUP_FILE" >> "$SCRIPT_DIR/audit.log"
}

restore() {
    echo -e "${RED}⚠️  RESTAURACIÓN DE REDIS PRODUCCIÓN${NC}"
    echo -e "${ORANGE}Esta operación sobrescribirá los datos actuales${NC}"
    
    check_production_approval
    
    # Listar backups disponibles
    echo ""
    echo "Backups disponibles:"
    BACKUP_DIR="$SCRIPT_DIR/backups"
    ls -lh "$BACKUP_DIR"/redis-pro-backup-*.tar.gz 2>/dev/null || {
        echo -e "${RED}❌ No hay backups disponibles${NC}"
        exit 1
    }
    
    echo ""
    read -p "Introduce el nombre del archivo de backup a restaurar: " backup_file
    
    if [ ! -f "$BACKUP_DIR/$backup_file" ]; then
        echo -e "${RED}❌ Archivo de backup no encontrado${NC}"
        exit 1
    fi
    
    # Backup de seguridad antes de restaurar
    echo -e "${ORANGE}Creando backup de seguridad actual...${NC}"
    backup_silent
    
    # Detener Redis
    echo "Deteniendo Redis..."
    docker stop "${CONTAINER_NAME}"
    
    # Restaurar datos
    echo "Restaurando datos desde backup..."
    docker run --rm \
        -v "${VOLUME_DATA}:/data" \
        -v "$BACKUP_DIR:/backup:ro" \
        alpine sh -c "cd /data && rm -rf * && tar xzf /backup/$backup_file"
    
    # Iniciar Redis
    echo "Iniciando Redis..."
    docker start "${CONTAINER_NAME}"
    sleep 10
    
    if docker exec "${CONTAINER_NAME}" redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Restauración completada exitosamente${NC}"
    else
        echo -e "${RED}❌ Error al iniciar Redis tras restauración${NC}"
        exit 1
    fi
    
    # Log de auditoría
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Restauración Redis PRO desde $backup_file por $(whoami)" >> "$SCRIPT_DIR/audit.log"
}

clean_all() {
    echo -e "${RED}⚠️  ADVERTENCIA CRÍTICA PRODUCCIÓN${NC}"
    echo -e "${RED}⚠️  Esto eliminará contenedor, imagen y volúmenes de REDIS PRODUCCIÓN${NC}"
    echo -e "${RED}⚠️  TODAS las sesiones y datos se perderán permanentemente${NC}"
    
    check_production_approval
    
    read -p "Escribe 'ELIMINAR-PRODUCCION' para confirmar: " confirm
    
    if [ "$confirm" = "ELIMINAR-PRODUCCION" ]; then
        # Backup final
        echo -e "${ORANGE}Creando backup final...${NC}"
        backup_silent
        
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
        
        # Log de auditoría
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Redis PRO eliminado completamente por $(whoami)" >> "$SCRIPT_DIR/audit.log"
    else
        echo "Operación cancelada"
    fi
}

open_shell() {
    echo -e "${GREEN}💻 Abriendo shell en contenedor Redis PRODUCCIÓN...${NC}"
    echo -e "${ORANGE}⚠️  Solo para diagnóstico - No modificar configuración${NC}"
    docker exec -it "${CONTAINER_NAME}" /bin/bash
}

status() {
    echo -e "${GREEN}📊 Estado de Redis PRODUCCIÓN:${NC}"
    echo ""
    
    # Contenedor
    if docker ps | grep -q "${CONTAINER_NAME}"; then
        echo -e "${GREEN}✅ Contenedor: Corriendo${NC}"
        docker ps | grep "${CONTAINER_NAME}"
    else
        echo -e "${RED}❌ Contenedor: Detenido - CRÍTICO${NC}"
        return 1
    fi
    
    echo ""
    
    # Volúmenes y tamaño
    echo "📦 Volúmenes:"
    docker volume ls | grep "redis-pro"
    echo ""
    docker system df -v | grep "redis-pro"
    
    echo ""
    
    # Stats en tiempo real
    echo "📊 Recursos:"
    docker stats "${CONTAINER_NAME}" --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
    
    echo ""
    echo "🏥 Healthcheck:"
    docker inspect "${CONTAINER_NAME}" | jq '.[0].State.Health'
    
    echo ""
    echo "🔗 Conexión:"
    if docker exec "${CONTAINER_NAME}" redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis responde${NC}"
    else
        echo -e "${RED}❌ Redis no responde - REVISAR INMEDIATAMENTE${NC}"
    fi
    
    echo ""
    echo "📊 Info Redis:"
    docker exec "${CONTAINER_NAME}" redis-cli INFO server | grep -E "redis_version|uptime_in_days"
    docker exec "${CONTAINER_NAME}" redis-cli INFO memory | grep -E "used_memory_human|maxmemory_human"
    docker exec "${CONTAINER_NAME}" redis-cli INFO stats | grep -E "connected_clients|total_commands_processed"
    docker exec "${CONTAINER_NAME}" redis-cli INFO persistence | grep -E "rdb_last_save_time|aof_enabled"
    docker exec "${CONTAINER_NAME}" redis-cli DBSIZE
    
    echo ""
    echo "💾 Último backup:"
    ls -lht "$SCRIPT_DIR/backups"/redis-pro-backup-*.tar.gz 2>/dev/null | head -1 || echo "No hay backups"
}

audit_log() {
    echo -e "${GREEN}📋 Log de auditoría:${NC}"
    if [ -f "$SCRIPT_DIR/audit.log" ]; then
        tail -50 "$SCRIPT_DIR/audit.log"
    else
        echo "No hay registro de auditoría"
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
    
    restore)
        restore
        ;;
    
    status)
        status
        ;;
    
    audit)
        audit_log
        ;;
    
    *)
        echo "Script de gestión de Redis PRODUCCIÓN en Docker"
        echo ""
        echo "Uso: $0 {build|run|stop|restart|logs|clean|shell|backup|restore|status|audit}"
        echo ""
        echo "Comandos:"
        echo "  build    - Construir imagen Docker (REQUIERE APROBACIÓN)"
        echo "  run      - Ejecutar contenedor (REQUIERE APROBACIÓN)"
        echo "  stop     - Detener contenedor (REQUIERE APROBACIÓN)"
        echo "  restart  - Reiniciar contenedor (REQUIERE APROBACIÓN)"
        echo "  logs     - Ver logs en tiempo real"
        echo "  clean    - Eliminar todo (REQUIERE APROBACIÓN)"
        echo "  shell    - Abrir shell en el contenedor"
        echo "  backup   - Realizar backup de datos"
        echo "  restore  - Restaurar desde backup (REQUIERE APROBACIÓN)"
        echo "  status   - Ver estado detallado del servicio"
        echo "  audit    - Ver log de auditoría"
        echo ""
        echo "Configuración actual:"
        echo "  Imagen: ${IMAGE_NAME}:${IMAGE_TAG}"
        echo "  Contenedor: ${CONTAINER_NAME}"
        echo "  Puerto: ${REDIS_PORT}"
        echo "  Volumen datos: ${VOLUME_DATA}"
        echo "  Volumen logs: ${VOLUME_LOGS}"
        echo "  Memoria límite: 8GB"
        echo "  CPUs límite: 4.0"
        echo "  Retención backups: ${BACKUP_RETENTION_DAYS} días"
        echo ""
        echo "⚠️  ENTORNO DE PRODUCCIÓN - Todas las operaciones requieren aprobación"
        echo ""
        exit 1
        ;;
esac
