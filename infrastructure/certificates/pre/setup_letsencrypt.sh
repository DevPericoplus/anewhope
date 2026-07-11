#!/bin/bash
# ==============================================================================
# Script para configurar certificados Let's Encrypt en AWS
# ==============================================================================
#
# Propósito:
#   Obtiene certificados SSL válidos de Let's Encrypt para el dominio
#   getmylllm.com en el entorno PRE (AWS con IP pública).
#
# Requisitos previos:
#   1. Dominio getmylllm.com debe apuntar a la IP pública del servidor
#   2. Puerto 80 debe estar abierto en el firewall/security group
#   3. Nginx debe estar corriendo (certbot usa el método webroot)
#
# Uso:
#   sudo bash setup_letsencrypt.sh
#
# Salida:
#   Certificados en: /etc/letsencrypt/live/getmylllm.com/
#     - fullchain.pem: Certificado + cadena
#     - privkey.pem: Clave privada
#
# ==============================================================================

set -e

# Verificar que se ejecuta como root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Este script debe ejecutarse como root (usa sudo)"
    exit 1
fi

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
DOMAIN="getmylllm.com"
WWW_DOMAIN="www.${DOMAIN}"
EMAIL="admin@${DOMAIN}"  # Cambiar por email real del administrador
WEBROOT="/var/www/html"  # Directorio webroot para validación

echo ""
echo "============================================"
echo "  Configuración de Let's Encrypt"
echo "  Entorno: PRE (AWS)"
echo "  Dominio: ${DOMAIN}"
echo "============================================"
echo ""

# ==============================================================================
# Verificar requisitos previos
# ==============================================================================
echo -e "${BLUE}→ Verificando requisitos previos...${NC}"
echo ""

# Verificar que el dominio apunta a este servidor
PUBLIC_IP=$(curl -s ifconfig.me || curl -s icanhazip.com)
DOMAIN_IP=$(dig +short ${DOMAIN} @8.8.8.8 | tail -n1)

echo "  IP pública de este servidor: ${PUBLIC_IP}"
echo "  IP del dominio ${DOMAIN}: ${DOMAIN_IP}"
echo ""

if [ "$PUBLIC_IP" != "$DOMAIN_IP" ]; then
    echo -e "${YELLOW}⚠ ADVERTENCIA: El dominio no apunta a este servidor${NC}"
    echo "  Debes configurar el DNS para que ${DOMAIN} apunte a ${PUBLIC_IP}"
    echo ""
    read -p "¿Deseas continuar de todas formas? (s/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo -e "${YELLOW}Operación cancelada${NC}"
        exit 0
    fi
fi

# ==============================================================================
# Instalar certbot si no está instalado
# ==============================================================================
if ! command -v certbot &> /dev/null; then
    echo -e "${BLUE}→ Instalando certbot...${NC}"

    # Detectar sistema operativo
    if [ -f /etc/oracle-release ]; then
        # Oracle Linux
        dnf install -y certbot python3-certbot-nginx
    elif [ -f /etc/redhat-release ]; then
        # RHEL/CentOS
        yum install -y certbot python3-certbot-nginx
    elif [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        apt update
        apt install -y certbot python3-certbot-nginx
    else
        echo -e "${RED}✗ Sistema operativo no soportado${NC}"
        echo "  Instala certbot manualmente: https://certbot.eff.org/"
        exit 1
    fi

    echo -e "${GREEN}✓ Certbot instalado${NC}"
else
    echo -e "${GREEN}✓ Certbot ya está instalado${NC}"
fi

echo ""

# ==============================================================================
# Configurar email para notificaciones
# ==============================================================================
echo -e "${BLUE}→ Configuración de email para notificaciones${NC}"
echo ""
echo "  Email actual configurado: ${EMAIL}"
echo ""
read -p "¿Deseas usar este email? (S/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Nn]$ ]]; then
    read -p "Introduce el email del administrador: " EMAIL
    echo ""
fi

# ==============================================================================
# Método de validación
# ==============================================================================
echo -e "${BLUE}→ Selecciona el método de validación${NC}"
echo ""
echo "  1) Nginx (recomendado) - Certbot configura nginx automáticamente"
echo "  2) Standalone - Detiene nginx temporalmente para validación"
echo "  3) Webroot - Usa un directorio para validación (nginx debe estar corriendo)"
echo ""
read -p "Método (1-3): " -n 1 -r METHOD
echo ""
echo ""

# ==============================================================================
# Obtener certificados según el método elegido
# ==============================================================================
case $METHOD in
    1)
        echo -e "${GREEN}→ Obteniendo certificados usando plugin de Nginx...${NC}"
        echo ""
        certbot --nginx \
            -d ${DOMAIN} \
            -d ${WWW_DOMAIN} \
            --email ${EMAIL} \
            --agree-tos \
            --no-eff-email \
            --redirect
        ;;

    2)
        echo -e "${GREEN}→ Obteniendo certificados en modo standalone...${NC}"
        echo -e "${YELLOW}  ⚠ Nginx se detendrá temporalmente${NC}"
        echo ""

        # Detener nginx si está corriendo
        if systemctl is-active --quiet nginx 2>/dev/null; then
            systemctl stop nginx
        elif docker ps | grep -q nginx; then
            docker stop nginx 2>/dev/null || true
        fi

        certbot certonly --standalone \
            -d ${DOMAIN} \
            -d ${WWW_DOMAIN} \
            --email ${EMAIL} \
            --agree-tos \
            --no-eff-email

        # Reiniciar nginx
        if systemctl is-enabled --quiet nginx 2>/dev/null; then
            systemctl start nginx
        elif docker ps -a | grep -q nginx; then
            docker start nginx 2>/dev/null || true
        fi
        ;;

    3)
        echo -e "${GREEN}→ Obteniendo certificados usando webroot...${NC}"
        echo ""
        read -p "Directorio webroot [${WEBROOT}]: " CUSTOM_WEBROOT
        WEBROOT=${CUSTOM_WEBROOT:-$WEBROOT}

        # Crear directorio webroot si no existe
        mkdir -p ${WEBROOT}/.well-known/acme-challenge

        certbot certonly --webroot \
            -w ${WEBROOT} \
            -d ${DOMAIN} \
            -d ${WWW_DOMAIN} \
            --email ${EMAIL} \
            --agree-tos \
            --no-eff-email
        ;;

    *)
        echo -e "${RED}✗ Opción inválida${NC}"
        exit 1
        ;;
esac

# ==============================================================================
# Verificar que los certificados se obtuvieron correctamente
# ==============================================================================
CERT_PATH="/etc/letsencrypt/live/${DOMAIN}"

if [ ! -d "$CERT_PATH" ]; then
    echo ""
    echo -e "${RED}✗ Error: No se pudieron obtener los certificados${NC}"
    echo "  Revisa los logs de certbot para más información"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Certificados obtenidos exitosamente${NC}"
echo ""

# ==============================================================================
# Copiar certificados a la ubicación esperada por nginx (si es necesario)
# ==============================================================================
echo -e "${BLUE}→ Configurando symlinks para nginx...${NC}"

mkdir -p /etc/nginx/ssl

# Crear symlinks (para que nginx use rutas simples)
ln -sf ${CERT_PATH}/fullchain.pem /etc/nginx/ssl/${DOMAIN}.crt
ln -sf ${CERT_PATH}/privkey.pem /etc/nginx/ssl/${DOMAIN}.key

echo -e "${GREEN}✓ Symlinks creados:${NC}"
echo "  /etc/nginx/ssl/${DOMAIN}.crt -> ${CERT_PATH}/fullchain.pem"
echo "  /etc/nginx/ssl/${DOMAIN}.key -> ${CERT_PATH}/privkey.pem"
echo ""

# ==============================================================================
# Configurar renovación automática
# ==============================================================================
echo -e "${BLUE}→ Configurando renovación automática...${NC}"

# Verificar que el timer de certbot está habilitado
if systemctl list-timers | grep -q certbot; then
    echo -e "${GREEN}✓ Timer de renovación ya está configurado${NC}"
else
    # Crear cron job para renovación
    CRON_JOB="0 3 * * * certbot renew --quiet --post-hook 'docker-compose -f /ruta/a/docker-compose.yml restart nginx || systemctl reload nginx'"

    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

    echo -e "${GREEN}✓ Cron job de renovación configurado${NC}"
    echo "  Los certificados se renovarán automáticamente cada día a las 3:00 AM"
fi

echo ""

# ==============================================================================
# Mostrar información de los certificados
# ==============================================================================
echo "============================================"
echo "  Información de los Certificados"
echo "============================================"
echo ""
openssl x509 -in ${CERT_PATH}/fullchain.pem -text -noout | grep -E "(Subject:|Issuer:|Not Before|Not After|DNS:)" | head -10
echo ""

# ==============================================================================
# Instrucciones finales
# ==============================================================================
echo "============================================"
echo "  Configuración Completada"
echo "============================================"
echo ""
echo "📁 Los certificados están en:"
echo "   ${CERT_PATH}/"
echo ""
echo "🔗 Symlinks para nginx:"
echo "   /etc/nginx/ssl/${DOMAIN}.crt"
echo "   /etc/nginx/ssl/${DOMAIN}.key"
echo ""
echo "✅ Próximos pasos:"
echo ""
echo "1️⃣  Verificar que nginx.conf usa las rutas correctas:"
echo ""
echo "    ssl_certificate /etc/nginx/ssl/${DOMAIN}.crt;"
echo "    ssl_certificate_key /etc/nginx/ssl/${DOMAIN}.key;"
echo ""
echo "2️⃣  Actualizar docker-compose.yml para montar los certificados:"
echo ""
echo "    nginx:"
echo "      volumes:"
echo "        - /etc/nginx/ssl:/etc/nginx/ssl:ro"
echo "        - /etc/letsencrypt:/etc/letsencrypt:ro"
echo ""
echo "3️⃣  Reiniciar nginx:"
echo ""
echo "    docker-compose restart nginx"
echo ""
echo "4️⃣  Verificar que SSL funciona:"
echo ""
echo "    curl -Ik https://${DOMAIN}"
echo "    curl -Ik https://${WWW_DOMAIN}"
echo ""
echo "5️⃣  Probar renovación automática:"
echo ""
echo "    certbot renew --dry-run"
echo ""
echo -e "${GREEN}✓ Configuración completada exitosamente${NC}"
echo ""
