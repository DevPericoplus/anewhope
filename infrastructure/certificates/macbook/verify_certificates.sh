#!/bin/bash

# Script de verificación de certificados SSL
# Verifica que los certificados estén correctamente configurados para acceso externo

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Verificación de Certificados SSL${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

CERT_FILE="tfmmyllm.ai.pem"
KEY_FILE="tfmmyllm.ai-key.pem"
CA_FILE="mkcert-rootCA.crt"

# Test 1: Verificar archivos existen
echo -e "${YELLOW}[1/6] Verificando archivos...${NC}"
FILES_OK=true

if [ -f "$CERT_FILE" ]; then
    echo -e "  ${GREEN}✓${NC} $CERT_FILE existe"
else
    echo -e "  ${RED}✗${NC} $CERT_FILE NO existe"
    FILES_OK=false
fi

if [ -f "$KEY_FILE" ]; then
    echo -e "  ${GREEN}✓${NC} $KEY_FILE existe"
else
    echo -e "  ${RED}✗${NC} $KEY_FILE NO existe"
    FILES_OK=false
fi

if [ -f "$CA_FILE" ]; then
    echo -e "  ${GREEN}✓${NC} $CA_FILE existe"
else
    echo -e "  ${RED}✗${NC} $CA_FILE NO existe"
    FILES_OK=false
fi

if [ "$FILES_OK" = false ]; then
    echo -e "${RED}Ejecuta primero: ./generate_certs.sh${NC}"
    exit 1
fi

# Test 2: Verificar que el certificado del servidor está firmado por la CA actual
echo ""
echo -e "${YELLOW}[2/6] Verificando firma del certificado...${NC}"

CERT_ISSUER=$(openssl x509 -in "$CERT_FILE" -noout -issuer)
CA_SUBJECT=$(openssl x509 -in "$CA_FILE" -noout -subject | sed 's/subject=//')

if echo "$CERT_ISSUER" | grep -q "$CA_SUBJECT"; then
    echo -e "  ${GREEN}✓${NC} Certificado firmado por la CA actual"
    echo -e "     ${BLUE}Emisor:${NC} $CERT_ISSUER"
else
    echo -e "  ${RED}✗${NC} Certificado NO firmado por la CA actual"
    echo -e "     ${YELLOW}Regenera los certificados con: ./generate_certs.sh${NC}"
    exit 1
fi

# Test 3: Verificar IPs incluidas en el certificado
echo ""
echo -e "${YELLOW}[3/6] Verificando IPs incluidas en el certificado...${NC}"

SANs=$(openssl x509 -in "$CERT_FILE" -noout -text | grep -A 2 "Subject Alternative Name" | tail -n 1)

echo -e "  ${BLUE}SANs detectados:${NC}"
echo "     $SANs" | sed 's/DNS:/\n     DNS:/g' | sed 's/IP Address:/\n     IP:/g'

# Obtener IPs locales
LOCAL_IPS=$(ifconfig | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}')

ALL_IPS_OK=true
for ip in $LOCAL_IPS; do
    if echo "$SANs" | grep -q "$ip"; then
        echo -e "  ${GREEN}✓${NC} IP $ip incluida en el certificado"
    else
        echo -e "  ${RED}✗${NC} IP $ip NO incluida en el certificado"
        ALL_IPS_OK=false
    fi
done

if [ "$ALL_IPS_OK" = false ]; then
    echo ""
    echo -e "  ${YELLOW}→ Regenera certificados con: ./generate_certs.sh${NC}"
    echo -e "  ${YELLOW}→ Recarga nginx con: nginx -s reload${NC}"
fi

# Test 4: Verificar fechas de validez
echo ""
echo -e "${YELLOW}[4/6] Verificando validez del certificado...${NC}"

NOT_BEFORE=$(openssl x509 -in "$CERT_FILE" -noout -startdate | cut -d= -f2)
NOT_AFTER=$(openssl x509 -in "$CERT_FILE" -noout -enddate | cut -d= -f2)

echo -e "  ${BLUE}Válido desde:${NC} $NOT_BEFORE"
echo -e "  ${BLUE}Válido hasta:${NC} $NOT_AFTER"

# Verificar si está expirado
if openssl x509 -in "$CERT_FILE" -noout -checkend 0 > /dev/null; then
    echo -e "  ${GREEN}✓${NC} Certificado válido (no expirado)"
else
    echo -e "  ${RED}✗${NC} Certificado EXPIRADO"
    echo -e "  ${YELLOW}→ Regenera con: ./generate_certs.sh${NC}"
fi

# Test 5: Verificar que nginx está usando estos certificados
echo ""
echo -e "${YELLOW}[5/6] Verificando configuración de nginx...${NC}"

NGINX_CONF="/usr/local/etc/nginx/nginx.conf"

if [ -f "$NGINX_CONF" ]; then
    CERT_PATH_IN_CONF=$(grep "ssl_certificate " "$NGINX_CONF" | grep -v "ssl_certificate_key" | head -n1 | awk '{print $2}' | tr -d ';')
    CURRENT_CERT_PATH="$(pwd)/$CERT_FILE"

    if [ "$CERT_PATH_IN_CONF" = "$CURRENT_CERT_PATH" ]; then
        echo -e "  ${GREEN}✓${NC} Nginx configurado con estos certificados"
        echo -e "     ${BLUE}Ruta:${NC} $CERT_PATH_IN_CONF"
    else
        echo -e "  ${YELLOW}⚠️${NC}  Nginx usa certificados de otra ubicación"
        echo -e "     ${BLUE}Configurado:${NC} $CERT_PATH_IN_CONF"
        echo -e "     ${BLUE}Actual:${NC} $CURRENT_CERT_PATH"
    fi
else
    echo -e "  ${YELLOW}⚠️${NC}  No se encontró nginx.conf"
fi

# Test 6: Verificar que nginx está corriendo
echo ""
echo -e "${YELLOW}[6/6] Verificando nginx...${NC}"

if pgrep nginx > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} nginx está corriendo"

    # Test de conexión HTTPS
    LOCAL_IP=$(ifconfig | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}' | head -n1)

    if curl -k -s -o /dev/null -w "%{http_code}" --connect-timeout 3 "https://${LOCAL_IP}" | grep -q "200\|301\|302"; then
        echo -e "  ${GREEN}✓${NC} Conexión HTTPS funciona (https://${LOCAL_IP})"
    else
        echo -e "  ${RED}✗${NC} No se puede conectar via HTTPS"
    fi
else
    echo -e "  ${RED}✗${NC} nginx NO está corriendo"
    echo -e "  ${YELLOW}→ Inicia nginx con: nginx${NC}"
fi

# Resumen
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Resumen y Próximos Pasos${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if [ "$ALL_IPS_OK" = true ] && [ "$FILES_OK" = true ]; then
    echo -e "${GREEN}✓ Certificados correctamente configurados${NC}"
    echo ""
    echo -e "${YELLOW}Para acceso desde Windows:${NC}"
    echo ""
    echo -e "1. Copia la carpeta 'windows-install-package' a Windows"
    echo -e "2. Ejecuta 'instalar_certificado.ps1' como Administrador"
    echo -e "3. Reinicia el navegador"
    echo -e "4. Accede a: https://${LOCAL_IP}"
    echo ""
    echo -e "${YELLOW}URLs disponibles:${NC}"
    for ip in $LOCAL_IPS; do
        echo -e "  ${GREEN}https://${ip}${NC}"
        echo -e "  ${GREEN}https://${ip}:8443${NC} (Backoffice)"
    done
else
    echo -e "${RED}✗ Hay problemas con los certificados${NC}"
    echo ""
    echo -e "${YELLOW}Acciones recomendadas:${NC}"
    echo -e "  1. Regenerar certificados: ./generate_certs.sh"
    echo -e "  2. Recargar nginx: nginx -s reload"
    echo -e "  3. Volver a ejecutar: ./verify_certificates.sh"
fi

echo ""
