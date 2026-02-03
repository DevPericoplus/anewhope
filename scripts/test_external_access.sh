#!/bin/bash

# Script de verificación rápida de acceso externo a nginx
# Autor: Sistema anewhope
# Fecha: 2026-02-02

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Test de Acceso Externo a Nginx${NC}"
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo ""

# Obtener IP local
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n1)

if [ -z "$LOCAL_IP" ]; then
    echo -e "${RED}✗ No se pudo obtener la IP local${NC}"
    exit 1
fi

echo -e "${GREEN}✓ IP Local: ${LOCAL_IP}${NC}"
echo ""

# Test 1: Verificar nginx corriendo
echo -e "${YELLOW}[1/4] Verificando nginx...${NC}"
if pgrep nginx > /dev/null 2>&1; then
    echo -e "${GREEN}  ✓ nginx está corriendo${NC}"
else
    echo -e "${RED}  ✗ nginx NO está corriendo${NC}"
    echo -e "${YELLOW}  → Ejecuta: nginx${NC}"
    exit 1
fi

# Test 2: Verificar puertos
echo ""
echo -e "${YELLOW}[2/4] Verificando puertos...${NC}"
PORTS_OK=true
for PORT in 443 8080 8443; do
    if lsof -nP -iTCP:$PORT -sTCP:LISTEN | grep nginx > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Puerto $PORT: ESCUCHANDO${NC}"
    else
        echo -e "${RED}  ✗ Puerto $PORT: NO ESCUCHANDO${NC}"
        PORTS_OK=false
    fi
done

if [ "$PORTS_OK" = false ]; then
    echo -e "${YELLOW}  → Verifica la configuración de nginx${NC}"
    exit 1
fi

# Test 3: Verificar firewall
echo ""
echo -e "${YELLOW}[3/4] Verificando firewall...${NC}"
FW_STATE=$(/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>/dev/null || echo "unknown")
if echo "$FW_STATE" | grep -q "enabled"; then
    echo -e "${YELLOW}  ⚠️  Firewall ACTIVADO (puede bloquear conexiones)${NC}"
    echo -e "${YELLOW}  → Ejecuta: sudo ./scripts/configure_firewall_nginx.sh${NC}"
else
    echo -e "${GREEN}  ✓ Firewall desactivado o configurado${NC}"
fi

# Test 4: Test de conectividad local
echo ""
echo -e "${YELLOW}[4/4] Test de conectividad desde localhost...${NC}"

# Test puerto 443
if curl -k -s -o /dev/null -w "%{http_code}" --max-time 5 https://${LOCAL_IP} 2>/dev/null | grep -q "200\|301\|302"; then
    echo -e "${GREEN}  ✓ Puerto 443 (HTTPS): ACCESIBLE${NC}"
else
    echo -e "${RED}  ✗ Puerto 443 (HTTPS): NO ACCESIBLE${NC}"
fi

# Test puerto 8080
if curl -k -s -o /dev/null -w "%{http_code}" --max-time 5 http://${LOCAL_IP}:8080 2>/dev/null | grep -q "301\|302"; then
    echo -e "${GREEN}  ✓ Puerto 8080 (HTTP): ACCESIBLE (redirige)${NC}"
else
    echo -e "${RED}  ✗ Puerto 8080 (HTTP): NO ACCESIBLE${NC}"
fi

# Test puerto 8443
if curl -k -s -o /dev/null -w "%{http_code}" --max-time 5 https://${LOCAL_IP}:8443 2>/dev/null | grep -q "200\|301\|302"; then
    echo -e "${GREEN}  ✓ Puerto 8443 (Backoffice): ACCESIBLE${NC}"
else
    echo -e "${RED}  ✗ Puerto 8443 (Backoffice): NO ACCESIBLE${NC}"
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   URLs para acceso externo:${NC}"
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Frontend:    https://${LOCAL_IP}${NC}"
echo -e "${GREEN}  Backoffice:  https://${LOCAL_IP}:8443${NC}"
echo -e "${GREEN}  HTTP:        http://${LOCAL_IP}:8080${NC}"
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Para monitorear accesos en tiempo real:${NC}"
echo -e "  tail -f /usr/local/var/log/nginx/access.log"
echo ""
