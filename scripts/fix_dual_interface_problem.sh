#!/bin/bash

# Script para solucionar el problema de dos interfaces activas en la misma red
# Esto causa routing asimétrico que bloquea conexiones entrantes

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Solución: Problema de Routing Asimétrico${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Verificar permisos
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}✗ Este script necesita permisos de administrador${NC}"
    echo -e "${YELLOW}  Ejecuta: sudo $0${NC}"
    exit 1
fi

# Detectar interfaces activas
echo -e "${CYAN}[1] Detectando interfaces de red activas...${NC}"
echo ""

INTERFACES=$(ifconfig | grep -E "^en[0-9]:" | grep -v "inactive" | cut -d: -f1)

for iface in $INTERFACES; do
    STATUS=$(ifconfig "$iface" | grep "status:" | awk '{print $2}')
    IP=$(ifconfig "$iface" | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}')

    if [ "$STATUS" = "active" ] && [ -n "$IP" ]; then
        echo -e "${YELLOW}  Interface: ${iface}${NC}"
        echo -e "    IP: ${GREEN}${IP}${NC}"
        echo -e "    Status: ${GREEN}${STATUS}${NC}"
        echo ""
    fi
done

# Mostrar tabla de routing
echo -e "${CYAN}[2] Rutas actuales:${NC}"
netstat -rn | grep -E "^default|^192.168.0" | while read line; do
    echo "    $line"
done
echo ""

# Detectar el problema
EN0_IP=$(ifconfig en0 2>/dev/null | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}')
EN3_IP=$(ifconfig en3 2>/dev/null | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}')

if [ -n "$EN0_IP" ] && [ -n "$EN3_IP" ]; then
    echo -e "${RED}✗ PROBLEMA DETECTADO:${NC}"
    echo -e "  Tienes dos interfaces activas en la misma red:"
    echo -e "    en0: ${YELLOW}${EN0_IP}${NC}"
    echo -e "    en3: ${YELLOW}${EN3_IP}${NC}"
    echo ""
    echo -e "${YELLOW}  Esto causa routing asimétrico:${NC}"
    echo -e "    1. Peticiones llegan a ${EN0_IP} (en0)"
    echo -e "    2. Respuestas salen por ${EN3_IP} (en3)"
    echo -e "    3. El equipo externo descarta las respuestas"
    echo ""

    # Ofrecer soluciones
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}   Soluciones Disponibles${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${GREEN}[A]${NC} Desactivar interfaz en3 (192.168.0.39)"
    echo -e "    ${YELLOW}→${NC} Mantener solo en0 activa"
    echo -e "    ${YELLOW}→${NC} Solución permanente hasta reinicio"
    echo ""
    echo -e "${GREEN}[B]${NC} Ajustar prioridad de rutas"
    echo -e "    ${YELLOW}→${NC} Hacer que en0 sea la interfaz principal"
    echo -e "    ${YELLOW}→${NC} Requiere configuración de Service Order"
    echo ""
    echo -e "${GREEN}[C]${NC} Ver información detallada (solo diagnóstico)"
    echo ""
    echo -e "${GREEN}[Q]${NC} Salir sin cambios"
    echo ""

    read -p "Elige una opción [A/B/C/Q]: " choice

    case "$choice" in
        [Aa])
            echo ""
            echo -e "${YELLOW}Desactivando interfaz en3...${NC}"
            ifconfig en3 down
            echo -e "${GREEN}✓ Interfaz en3 desactivada${NC}"
            echo ""
            echo -e "${YELLOW}Verificando configuración...${NC}"
            sleep 2

            # Verificar que solo quede en0
            ACTIVE_IPS=$(ifconfig | grep "inet " | grep -v "127.0.0.1" | wc -l | tr -d ' ')
            if [ "$ACTIVE_IPS" -eq 1 ]; then
                echo -e "${GREEN}✓ Ahora solo hay una IP activa${NC}"
                echo ""
                echo -e "${GREEN}IP activa: $(ifconfig | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}')${NC}"
                echo ""
                echo -e "${BLUE}Tabla de routing actualizada:${NC}"
                netstat -rn | grep -E "^default|^192.168.0" | head -5
            fi

            echo ""
            echo -e "${GREEN}✓ Solución aplicada${NC}"
            echo -e "${YELLOW}NOTA: Esta configuración se perderá al reiniciar${NC}"
            echo -e "${YELLOW}      Para hacerla permanente, deshabilita en3 desde:${NC}"
            echo -e "${YELLOW}      Preferencias del Sistema → Red${NC}"
            ;;

        [Bb])
            echo ""
            echo -e "${YELLOW}Ajustando prioridad de interfaces...${NC}"
            echo ""
            echo -e "${CYAN}Método: Service Order en Preferencias del Sistema${NC}"
            echo ""
            echo -e "${YELLOW}Pasos manuales:${NC}"
            echo -e "  1. Abre 'Preferencias del Sistema' → 'Red'"
            echo -e "  2. Haz clic en el ícono de engranaje (⚙️) → 'Set Service Order'"
            echo -e "  3. Arrastra 'Ethernet' o 'WiFi (en0)' al primer lugar"
            echo -e "  4. Asegúrate que la interfaz con ${EN0_IP} esté primera"
            echo -e "  5. Haz clic en 'OK' y 'Apply'"
            echo ""
            echo -e "${YELLOW}O ejecuta (requiere reinicio de red):${NC}"
            echo -e "  sudo networksetup -ordernetworkservices"
            echo ""
            ;;

        [Cc])
            echo ""
            echo -e "${CYAN}Información detallada de red:${NC}"
            echo ""
            echo -e "${YELLOW}=== Interface en0 ===${NC}"
            ifconfig en0
            echo ""
            echo -e "${YELLOW}=== Interface en3 ===${NC}"
            ifconfig en3
            echo ""
            echo -e "${YELLOW}=== Tabla de routing completa ===${NC}"
            netstat -rn | head -20
            echo ""
            echo -e "${YELLOW}=== Tabla ARP ===${NC}"
            arp -an | grep "192.168.0"
            ;;

        [Qq])
            echo ""
            echo -e "${YELLOW}Saliendo sin cambios...${NC}"
            exit 0
            ;;

        *)
            echo ""
            echo -e "${RED}Opción inválida${NC}"
            exit 1
            ;;
    esac

else
    echo -e "${GREEN}✓ No se detectó el problema de interfaces duplicadas${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Prueba de Conectividad${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

CURRENT_IP=$(ifconfig | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}' | head -n1)

echo -e "${GREEN}IP actual del sistema: ${CURRENT_IP}${NC}"
echo ""
echo -e "${YELLOW}Desde el equipo externo, intenta:${NC}"
echo -e "  ping ${CURRENT_IP}"
echo -e "  curl -k https://${CURRENT_IP}"
echo ""
echo -e "${YELLOW}Monitorea en este Mac:${NC}"
echo -e "  tail -f /usr/local/var/log/nginx/access.log"
echo ""
echo -e "${YELLOW}Si ves la IP del equipo externo en el log → ${GREEN}SOLUCIONADO${NC}"
echo ""
