#!/bin/bash

# Script rápido para verificar Modo Sigilo (Stealth Mode)
# Este es el problema más común que bloquea ping y conexiones entrantes

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Verificación Rápida de Modo Sigilo${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Obtener IP local
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n1)
echo -e "${GREEN}IP Local: ${LOCAL_IP}${NC}"
echo ""

# Estado del firewall
echo -e "${YELLOW}[1] Estado del Firewall:${NC}"
FW_STATE=$(/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>/dev/null)
echo "    $FW_STATE"

# Estado del modo sigilo
echo ""
echo -e "${YELLOW}[2] Modo Sigilo (Stealth Mode):${NC}"
STEALTH=$(/usr/libexec/ApplicationFirewall/socketfilterfw --getstealthmode 2>/dev/null)
echo "    $STEALTH"

if echo "$STEALTH" | grep -q "enabled"; then
    echo ""
    echo -e "${RED}❌ PROBLEMA: El Modo Sigilo está ACTIVADO${NC}"
    echo -e "${YELLOW}   → Esto bloquea PING y todas las conexiones entrantes${NC}"
    echo ""
    echo -e "${GREEN}SOLUCIÓN:${NC}"
    echo -e "  sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setstealthmode off"
    echo ""
    echo -e "${YELLOW}O ejecuta el script completo:${NC}"
    echo -e "  sudo ./scripts/fix_network_access.sh"
    echo ""
    exit 1
else
    echo ""
    echo -e "${GREEN}✓ Modo Sigilo está desactivado (correcto)${NC}"
fi

# Verificar nginx
echo ""
echo -e "${YELLOW}[3] Estado de Nginx:${NC}"
if lsof -nP -iTCP -sTCP:LISTEN | grep nginx | grep -E '\*:(443|8080|8443)' > /dev/null 2>&1; then
    echo -e "${GREEN}    ✓ nginx escuchando correctamente${NC}"
    lsof -nP -iTCP -sTCP:LISTEN | grep nginx | grep -E '\*:(443|8080|8443)' | awk '{print "      " $1 " - Puerto " $9}'
else
    echo -e "${RED}    ✗ nginx no está corriendo${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}URLs para acceso externo:${NC}"
echo -e "  https://${LOCAL_IP}"
echo -e "  https://${LOCAL_IP}:8443"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
