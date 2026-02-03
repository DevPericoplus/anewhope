#!/bin/bash

# Diagnóstico completo de conectividad de red
# Ayuda a identificar por qué no llegan conexiones desde equipos externos

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Diagnóstico Completo de Conectividad${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Obtener información de red
echo -e "${CYAN}[1] Información de Red${NC}"
echo -e "${YELLOW}Interfaces de red activas:${NC}"
ifconfig | grep -A 5 "^en" | grep -E "inet |status"
echo ""

LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n1)
INTERFACE=$(ifconfig | grep -B 5 "$LOCAL_IP" | grep "^en" | awk -F: '{print $1}')

echo -e "${GREEN}IP Local detectada: ${LOCAL_IP}${NC}"
echo -e "${GREEN}Interface detectada: ${INTERFACE}${NC}"
echo ""

# Verificar ruta por defecto
echo -e "${CYAN}[2] Ruta por Defecto${NC}"
GATEWAY=$(netstat -nr | grep "^default" | awk '{print $2}' | head -n1)
echo -e "${GREEN}Gateway: ${GATEWAY}${NC}"
echo ""

# Verificar firewall
echo -e "${CYAN}[3] Estado del Firewall de macOS${NC}"
FW_STATE=$(/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>/dev/null)
STEALTH=$(/usr/libexec/ApplicationFirewall/socketfilterfw --getstealthmode 2>/dev/null)

if echo "$FW_STATE" | grep -q "enabled"; then
    echo -e "${YELLOW}⚠️  Firewall: ACTIVADO${NC}"
else
    echo -e "${GREEN}✓ Firewall: DESACTIVADO${NC}"
fi

if echo "$STEALTH" | grep -q "enabled"; then
    echo -e "${RED}✗ Modo Sigilo: ACTIVADO (BLOQUEANDO PING)${NC}"
else
    echo -e "${GREEN}✓ Modo Sigilo: DESACTIVADO${NC}"
fi
echo ""

# Verificar PF (Packet Filter)
echo -e "${CYAN}[4] Packet Filter (PF)${NC}"
if sudo pfctl -s info 2>/dev/null | grep -q "Status: Enabled"; then
    echo -e "${YELLOW}⚠️  PF está activo${NC}"
    echo -e "${YELLOW}Reglas activas:${NC}"
    sudo pfctl -s rules 2>/dev/null | head -10
else
    echo -e "${GREEN}✓ PF no está activo o no está bloqueando${NC}"
fi
echo ""

# Verificar puertos escuchando
echo -e "${CYAN}[5] Puertos de Nginx${NC}"
echo -e "${YELLOW}Puertos escuchando:${NC}"
if lsof -nP -iTCP -sTCP:LISTEN | grep nginx | grep -E ':(443|8080|8443)' > /dev/null; then
    lsof -nP -iTCP -sTCP:LISTEN | grep nginx | grep -E ':(443|8080|8443)' | while read line; do
        PORT=$(echo $line | awk '{print $9}')
        echo -e "  ${GREEN}✓${NC} $PORT"
    done
else
    echo -e "${RED}✗ nginx no está escuchando${NC}"
fi
echo ""

# Test de auto-conexión
echo -e "${CYAN}[6] Test de Auto-Conexión (desde este Mac)${NC}"
echo -e "${YELLOW}Probando conectividad local...${NC}"

# Test puerto 443
if curl -k -s -o /dev/null -w "%{http_code}" --connect-timeout 3 https://${LOCAL_IP} 2>/dev/null | grep -q "200\|301\|302"; then
    echo -e "  ${GREEN}✓ Puerto 443 (HTTPS): ACCESIBLE${NC}"
else
    echo -e "  ${RED}✗ Puerto 443 (HTTPS): NO ACCESIBLE${NC}"
fi

# Test puerto 8443
if curl -k -s -o /dev/null -w "%{http_code}" --connect-timeout 3 https://${LOCAL_IP}:8443 2>/dev/null | grep -q "200\|301\|302"; then
    echo -e "  ${GREEN}✓ Puerto 8443 (Backoffice): ACCESIBLE${NC}"
else
    echo -e "  ${RED}✗ Puerto 8443 (Backoffice): NO ACCESIBLE${NC}"
fi
echo ""

# Verificar otros firewalls de terceros
echo -e "${CYAN}[7] Software de Seguridad de Terceros${NC}"
SECURITY_APPS=("Little Snitch" "Lulu" "Hands Off" "Radio Silence" "TripMode")
FOUND=0
for app in "${SECURITY_APPS[@]}"; do
    if ps aux | grep -i "$app" | grep -v grep > /dev/null; then
        echo -e "  ${YELLOW}⚠️  Detectado: $app${NC}"
        FOUND=1
    fi
done
if [ $FOUND -eq 0 ]; then
    echo -e "  ${GREEN}✓ No se detectaron aplicaciones de firewall de terceros${NC}"
fi
echo ""

# Información sobre el router
echo -e "${CYAN}[8] Información del Router${NC}"
echo -e "${YELLOW}Tu red local:${NC}"
echo -e "  IP Local: ${GREEN}${LOCAL_IP}${NC}"
echo -e "  Gateway:  ${GREEN}${GATEWAY}${NC}"
echo -e "  Red:      ${GREEN}192.168.0.0/24${NC}"
echo ""
echo -e "${YELLOW}Posible causa si el ping no funciona:${NC}"
echo -e "  ${YELLOW}→${NC} Algunos routers tienen 'Aislamiento de Cliente WiFi' activado"
echo -e "  ${YELLOW}→${NC} Esta función bloquea la comunicación entre dispositivos WiFi"
echo -e "  ${YELLOW}→${NC} Verifica la configuración del router (AP Isolation / Client Isolation)"
echo ""

# Comandos de prueba desde equipo externo
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Comandos para Probar desde Equipo Externo${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Desde el equipo externo (192.168.0.17), ejecuta:${NC}"
echo ""
echo -e "${GREEN}1. Test de PING:${NC}"
echo -e "   ping ${LOCAL_IP}"
echo ""
echo -e "${GREEN}2. Test de puerto TCP (Windows PowerShell):${NC}"
echo -e "   Test-NetConnection -ComputerName ${LOCAL_IP} -Port 443"
echo ""
echo -e "${GREEN}3. Test de puerto TCP (Linux/Mac):${NC}"
echo -e "   nc -zv ${LOCAL_IP} 443"
echo -e "   nc -zv ${LOCAL_IP} 8443"
echo ""
echo -e "${GREEN}4. Test HTTP simple (cualquier sistema):${NC}"
echo -e "   curl -k https://${LOCAL_IP}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Posibles soluciones
echo -e "${YELLOW}POSIBLES SOLUCIONES:${NC}"
echo ""
echo -e "${CYAN}A) Si el problema es el Modo Sigilo:${NC}"
echo -e "   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setstealthmode off"
echo ""
echo -e "${CYAN}B) Si el problema es el Firewall:${NC}"
echo -e "   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off"
echo ""
echo -e "${CYAN}C) Si hay Aislamiento de Cliente en el Router:${NC}"
echo -e "   1. Accede al panel de administración del router"
echo -e "   2. Busca 'AP Isolation', 'Client Isolation' o 'WiFi Isolation'"
echo -e "   3. DESACTIVA esta opción"
echo -e "   4. Reinicia el router si es necesario"
echo ""
echo -e "${CYAN}D) Si ambos equipos usan WiFi (común en routers modernos):${NC}"
echo -e "   → Conecta uno de los equipos por cable Ethernet"
echo -e "   → O desactiva 'WiFi Isolation' en el router"
echo ""
echo -e "${CYAN}E) Ejecutar script de solución automática:${NC}"
echo -e "   sudo ./scripts/fix_network_access.sh"
echo ""

# Logs para monitoreo
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Monitoreo en Tiempo Real${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Para ver intentos de conexión en tiempo real:${NC}"
echo -e "  tail -f /usr/local/var/log/nginx/access.log"
echo ""
echo -e "${YELLOW}Si no ves líneas nuevas cuando el equipo externo intenta conectar:${NC}"
echo -e "  ${RED}→ El problema está en la red (router o firewall)${NC}"
echo -e "  ${RED}→ Las peticiones NO están llegando al Mac${NC}"
echo ""
