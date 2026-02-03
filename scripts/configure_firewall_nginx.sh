#!/bin/bash

# Script para configurar el firewall de macOS y permitir acceso externo a nginx
# Autor: Sistema anewhope
# Fecha: 2026-02-02

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Configuración de Firewall para Nginx (Acceso Red)  ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Verificar que se ejecuta con sudo si es necesario
check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${YELLOW}⚠️  Este script necesita permisos de administrador${NC}"
        echo -e "${YELLOW}   Ejecuta: sudo $0${NC}"
        exit 1
    fi
}

# Función para verificar nginx
check_nginx() {
    echo -e "${BLUE}[1/6]${NC} Verificando nginx..."

    if ! command -v nginx &> /dev/null; then
        echo -e "${RED}✗ nginx no está instalado${NC}"
        exit 1
    fi

    NGINX_PATH=$(which nginx)
    echo -e "${GREEN}✓ nginx encontrado en: ${NGINX_PATH}${NC}"

    # Verificar si nginx está corriendo
    if pgrep -x nginx > /dev/null; then
        echo -e "${GREEN}✓ nginx está corriendo${NC}"
    else
        echo -e "${YELLOW}⚠️  nginx no está corriendo${NC}"
    fi
}

# Función para verificar puertos
check_ports() {
    echo ""
    echo -e "${BLUE}[2/6]${NC} Verificando puertos de nginx..."

    echo -e "${YELLOW}Puertos esperados: 443, 8080, 8443${NC}"

    if lsof -nP -iTCP -sTCP:LISTEN | grep nginx | grep -E ':(443|8080|8443)' > /dev/null; then
        echo -e "${GREEN}✓ nginx escuchando en los puertos correctos:${NC}"
        lsof -nP -iTCP -sTCP:LISTEN | grep nginx | grep -E ':(443|8080|8443)' | awk '{print "  - Puerto " $9}'
    else
        echo -e "${RED}✗ nginx no está escuchando en los puertos esperados${NC}"
    fi
}

# Función para verificar estado del firewall
check_firewall_status() {
    echo ""
    echo -e "${BLUE}[3/6]${NC} Verificando estado del firewall..."

    FW_STATE=$(/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate)
    echo -e "  ${FW_STATE}"

    if echo "$FW_STATE" | grep -q "enabled"; then
        echo -e "${YELLOW}⚠️  Firewall está ACTIVADO (bloqueando conexiones entrantes)${NC}"
        return 0
    else
        echo -e "${GREEN}✓ Firewall está desactivado (conexiones permitidas)${NC}"
        return 1
    fi
}

# Función para configurar Application Firewall
configure_app_firewall() {
    echo ""
    echo -e "${BLUE}[4/6]${NC} Configurando Application Firewall para nginx..."

    NGINX_PATH=$(which nginx)

    # Añadir nginx a la lista de aplicaciones
    echo -e "  ${YELLOW}→ Añadiendo nginx a aplicaciones permitidas...${NC}"
    /usr/libexec/ApplicationFirewall/socketfilterfw --add "$NGINX_PATH" 2>/dev/null || true

    # Desbloquear nginx
    echo -e "  ${YELLOW}→ Desbloqueando nginx para conexiones entrantes...${NC}"
    /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp "$NGINX_PATH" 2>/dev/null || true

    echo -e "${GREEN}✓ Configuración de Application Firewall completada${NC}"
}

# Función para crear reglas PF (Packet Filter)
configure_pf_rules() {
    echo ""
    echo -e "${BLUE}[5/6]${NC} Configurando reglas PF (Packet Filter)..."

    PF_RULES_FILE="/tmp/nginx_pf_rules.conf"

    cat > "$PF_RULES_FILE" << 'EOF'
# Reglas PF para nginx - Acceso externo
# Permitir tráfico entrante en puertos de nginx

# Puerto HTTPS principal (443)
pass in proto tcp from any to any port 443 keep state

# Puerto HTTP con redirección (8080)
pass in proto tcp from any to any port 8080 keep state

# Puerto HTTPS Backoffice (8443)
pass in proto tcp from any to any port 8443 keep state
EOF

    echo -e "  ${YELLOW}→ Reglas creadas en: ${PF_RULES_FILE}${NC}"
    cat "$PF_RULES_FILE" | grep -v "^#" | grep -v "^$"

    # Nota: pfctl requiere deshabilitar SIP o configuración adicional en macOS moderno
    echo ""
    echo -e "${YELLOW}ℹ️  Nota: En macOS moderno, pfctl puede requerir configuración adicional${NC}"
    echo -e "${YELLOW}   Si el firewall sigue bloqueando, considera desactivarlo temporalmente${NC}"
}

# Función para verificar IP local
get_local_ip() {
    echo ""
    echo -e "${BLUE}[6/6]${NC} Información de red..."

    LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n1)

    if [ -n "$LOCAL_IP" ]; then
        echo -e "${GREEN}✓ IP local detectada: ${LOCAL_IP}${NC}"
        echo ""
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}   URLs para acceso desde otros equipos:${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo -e "${YELLOW}  Frontend:${NC}    https://${LOCAL_IP}"
        echo -e "${YELLOW}  Backoffice:${NC}  https://${LOCAL_IP}:8443"
        echo -e "${YELLOW}  HTTP:${NC}        http://${LOCAL_IP}:8080"
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    else
        echo -e "${RED}✗ No se pudo detectar la IP local${NC}"
    fi
}

# Función para mostrar comandos de verificación
show_verification_commands() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}   Comandos de verificación:${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}1. Ver logs de nginx en tiempo real:${NC}"
    echo -e "   tail -f /usr/local/var/log/nginx/access.log"
    echo ""
    echo -e "${YELLOW}2. Verificar puertos escuchando:${NC}"
    echo -e "   lsof -nP -iTCP -sTCP:LISTEN | grep nginx"
    echo ""
    echo -e "${YELLOW}3. Probar desde este equipo:${NC}"
    echo -e "   curl -k https://\$(ifconfig | grep 'inet ' | grep -v 127.0.0.1 | awk '{print \$2}' | head -n1)"
    echo ""
    echo -e "${YELLOW}4. Ver estado del firewall:${NC}"
    echo -e "   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate"
    echo ""
}

# Función para opciones adicionales
show_additional_options() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}   Opciones adicionales:${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}Si aún no funciona, prueba:${NC}"
    echo ""
    echo -e "${YELLOW}A) Desactivar firewall temporalmente (DESARROLLO):${NC}"
    echo -e "   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off"
    echo ""
    echo -e "${YELLOW}B) Reactivar firewall después de probar:${NC}"
    echo -e "   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on"
    echo ""
    echo -e "${YELLOW}C) Configurar desde Preferencias del Sistema:${NC}"
    echo -e "   Preferencias → Seguridad y Privacidad → Firewall → Opciones"
    echo ""
}

# Función principal
main() {
    check_sudo
    check_nginx
    check_ports

    if check_firewall_status; then
        configure_app_firewall
        configure_pf_rules
    fi

    get_local_ip
    show_verification_commands
    show_additional_options

    echo -e "${GREEN}✓ Configuración completada${NC}"
    echo ""
}

# Ejecutar
main
