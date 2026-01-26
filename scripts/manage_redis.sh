#!/bin/bash
# Script para gestionar Redis en macbook

set -e

# Colores
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

case "$1" in
    install)
        echo -e "${GREEN}📦 Instalando Redis...${NC}"
        if command -v redis-server &> /dev/null; then
            echo -e "${ORANGE}⚠️  Redis ya está instalado${NC}"
            redis-server --version
        else
            echo "Instalando con Homebrew..."
            brew install redis
            echo -e "${GREEN}✅ Redis instalado${NC}"
        fi
        ;;
        
    start)
        echo -e "${GREEN}🚀 Iniciando Redis...${NC}"
        if brew services list | grep redis | grep started > /dev/null; then
            echo -e "${ORANGE}⚠️  Redis ya está corriendo${NC}"
        else
            brew services start redis
            sleep 2
            echo -e "${GREEN}✅ Redis iniciado${NC}"
        fi
        redis-cli ping
        ;;
        
    stop)
        echo -e "${ORANGE}🛑 Deteniendo Redis...${NC}"
        brew services stop redis
        echo -e "${GREEN}✅ Redis detenido${NC}"
        ;;
        
    restart)
        echo -e "${ORANGE}🔄 Reiniciando Redis...${NC}"
        brew services restart redis
        sleep 2
        echo -e "${GREEN}✅ Redis reiniciado${NC}"
        redis-cli ping
        ;;
        
    status)
        echo -e "${GREEN}📊 Estado de Redis:${NC}"
        echo ""
        brew services list | grep redis
        echo ""
        if redis-cli ping > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Redis está respondiendo${NC}"
            echo ""
            redis-cli INFO server | grep "redis_version"
            redis-cli INFO stats | grep "connected_clients"
            redis-cli DBSIZE
        else
            echo -e "${RED}❌ Redis no está respondiendo${NC}"
        fi
        ;;
        
    cli)
        echo -e "${GREEN}💻 Abriendo Redis CLI...${NC}"
        redis-cli
        ;;
        
    flush)
        echo -e "${ORANGE}⚠️  ADVERTENCIA: Esto eliminará TODOS los datos${NC}"
        read -p "¿Estás seguro? (escribe 'SI' para confirmar): " confirm
        if [ "$confirm" = "SI" ]; then
            redis-cli FLUSHALL
            echo -e "${GREEN}✅ Base de datos limpiada${NC}"
        else
            echo "Operación cancelada"
        fi
        ;;
        
    sessions)
        echo -e "${GREEN}📋 Sesiones activas en Redis:${NC}"
        echo ""
        redis-cli KEYS "reflex:session:*" | while read key; do
            if [ -n "$key" ]; then
                echo "🔑 $key"
                redis-cli TTL "$key" | xargs -I {} echo "   ⏱️  Expira en {} segundos"
            fi
        done
        echo ""
        total=$(redis-cli KEYS "reflex:session:*" | wc -l)
        echo -e "${GREEN}Total: $total sesiones activas${NC}"
        ;;
        
    monitor)
        echo -e "${GREEN}👁️  Monitoreando Redis en tiempo real...${NC}"
        echo "Presiona Ctrl+C para salir"
        echo ""
        redis-cli MONITOR
        ;;
        
    *)
        echo "Gestor de Redis para anewhope"
        echo ""
        echo "Uso: $0 {install|start|stop|restart|status|cli|flush|sessions|monitor}"
        echo ""
        echo "Comandos:"
        echo "  install   - Instalar Redis con Homebrew"
        echo "  start     - Iniciar servicio de Redis"
        echo "  stop      - Detener servicio de Redis"
        echo "  restart   - Reiniciar servicio de Redis"
        echo "  status    - Ver estado del servicio"
        echo "  cli       - Abrir Redis CLI"
        echo "  flush     - Limpiar toda la base de datos (¡CUIDADO!)"
        echo "  sessions  - Listar sesiones activas"
        echo "  monitor   - Monitorear comandos en tiempo real"
        echo ""
        exit 1
        ;;
esac
