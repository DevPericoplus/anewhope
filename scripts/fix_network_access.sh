#!/bin/bash

# Script para solucionar problemas de conectividad de red entrante en macOS
# Autor: Sistema anewhope
# Fecha: 2026-02-02

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Diagnóstico y Solución de Conectividad de Red       ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Verificar que se ejecuta con sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}✗ Este script necesita permisos de administrador${NC}"
    echo -e "${YELLOW}  Ejecuta: sudo $0${NC}"
    exit 1
fi

# Obtener IP local
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n1)
echo -e "${GREEN}✓ IP Local: ${LOCAL_IP}${NC}"
echo ""

# Test 1: Verificar estado del firewall
echo -e "${BLUE}[1/5] Verificando Application Firewall...${NC}"
FW_STATE=$(/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate)
echo "  $FW_STATE"

if echo "$FW_STATE" | grep -q "enabled"; then
    echo -e "${YELLOW}  ⚠️  Firewall ACTIVADO${NC}"

    # Verificar modo sigilo
    echo ""
    echo -e "${BLUE}[2/5] Verificando Modo Sigilo (Stealth Mode)...${NC}"
    STEALTH=$(/usr/libexec/ApplicationFirewall/socketfilterfw --getstealthmode)
    echo "  $STEALTH"

    if echo "$STEALTH" | grep -q "enabled"; then
        echo -e "${RED}  ✗ PROBLEMA ENCONTRADO: Modo Sigilo ACTIVADO${NC}"
        echo -e "${YELLOW}  → El Modo Sigilo bloquea TODOS los pings y conexiones entrantes${NC}"
        echo ""
        echo -e "${YELLOW}¿Desactivar Modo Sigilo? (s/n): ${NC}"
        read -r response
        if [[ "$response" =~ ^[Ss]$ ]]; then
            /usr/libexec/ApplicationFirewall/socketfilterfw --setstealthmode off
            echo -e "${GREEN}  ✓ Modo Sigilo DESACTIVADO${NC}"
        fi
    else
        echo -e "${GREEN}  ✓ Modo Sigilo desactivado${NC}"
    fi
else
    echo -e "${GREEN}  ✓ Firewall desactivado${NC}"
fi

# Test 3: Verificar PF (Packet Filter)
echo ""
echo -e "${BLUE}[3/5] Verificando PF (Packet Filter)...${NC}"
if pfctl -s info 2>/dev/null | grep -q "Status: Enabled"; then
    echo -e "${YELLOW}  ⚠️  PF está activo${NC}"
    pfctl -s rules 2>/dev/null | head -5
else
    echo -e "${GREEN}  ✓ PF no está bloqueando${NC}"
fi

# Test 4: Configurar firewall para permitir conexiones
echo ""
echo -e "${BLUE}[4/5] Configurando firewall para nginx...${NC}"

NGINX_PATH=$(which nginx)
/usr/libexec/ApplicationFirewall/socketfilterfw --add "$NGINX_PATH" 2>/dev/null || true
/usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp "$NGINX_PATH" 2>/dev/null || true

echo -e "${GREEN}  ✓ nginx configurado en el firewall${NC}"

# Test 5: Verificar puertos escuchando
echo ""
echo -e "${BLUE}[5/5] Verificando puertos de nginx...${NC}"
if lsof -nP -iTCP -sTCP:LISTEN | grep nginx | grep -E '\*:(443|8080|8443)' > /dev/null; then
    echo -e "${GREEN}  ✓ nginx escuchando en todas las interfaces (*)${NC}"
    lsof -nP -iTCP -sTCP:LISTEN | grep nginx | grep -E '\*:(443|8080|8443)' | awk '{print "    " $1 " - Puerto " $9}'
else
    echo -e "${RED}  ✗ nginx no está escuchando correctamente${NC}"
fi

# Resumen y pruebas
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Resumen de Configuración${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}PRUEBAS DESDE EQUIPO EXTERNO:${NC}"
echo ""
echo -e "${GREEN}1. Prueba de PING (debe funcionar ahora):${NC}"
echo -e "   ping ${LOCAL_IP}"
echo ""
echo -e "${GREEN}2. Prueba de CONEXIÓN HTTPS (puerto 443):${NC}"
echo -e "   Abre navegador en: https://${LOCAL_IP}"
echo ""
echo -e "${GREEN}3. Prueba de BACKOFFICE (puerto 8443):${NC}"
echo -e "   Abre navegador en: https://${LOCAL_IP}:8443"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Opciones adicionales
echo -e "${YELLOW}OPCIONES ADICIONALES:${NC}"
echo ""
echo -e "${YELLOW}A) Desactivar firewall completamente (SOLO DESARROLLO):${NC}"
echo -e "   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off"
echo ""
echo -e "${YELLOW}B) Ver logs de firewall en tiempo real:${NC}"
echo -e "   sudo log stream --predicate 'process == \"socketfilterfw\"' --level debug"
echo ""
echo -e "${YELLOW}C) Monitorear accesos nginx:${NC}"
echo -e "   tail -f /usr/local/var/log/nginx/access.log"
echo ""

# Preguntar si quiere desactivar firewall
echo -e "${YELLOW}¿Deseas DESACTIVAR el firewall completamente para probar? (s/n): ${NC}"
read -r response
if [[ "$response" =~ ^[Ss]$ ]]; then
    /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off
    echo -e "${GREEN}✓ Firewall DESACTIVADO${NC}"
    echo -e "${YELLOW}  IMPORTANTE: Reactivar después de probar con:${NC}"
    echo -e "${YELLOW}  sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on${NC}"
fi

echo ""
echo -e "${GREEN}✓ Configuración completada${NC}"
echo -e "${YELLOW}  → Ahora prueba el ping desde el equipo externo${NC}"
echo ""
