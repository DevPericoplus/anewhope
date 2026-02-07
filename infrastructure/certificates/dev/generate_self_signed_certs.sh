#!/bin/bash
# ==============================================================================
# Script para generar certificados SSL autofirmados para el entorno DEV
# ==============================================================================
#
# Propósito:
#   Genera certificados SSL autofirmados para el dominio house.loc en el
#   entorno de desarrollo (VirtualBox en red local).
#
# Uso:
#   bash generate_self_signed_certs.sh
#
# Salida:
#   - house.loc.crt: Certificado público
#   - house.loc.key: Clave privada
#
# IMPORTANTE:
#   Estos certificados son SOLO para desarrollo. El navegador mostrará
#   advertencias de seguridad que deberás aceptar manualmente.
#
# ==============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directorio actual (donde está este script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Dominio del entorno dev (leer de env.yaml si es posible)
DOMAIN="house.loc"
CERT_FILE="${DOMAIN}.crt"
KEY_FILE="${DOMAIN}.key"

# Validez del certificado (en días)
DAYS_VALID=365

echo ""
echo "===================================="
echo "  Generador de Certificados SSL"
echo "  Entorno: DEV (Red Local)"
echo "===================================="
echo ""

# ==============================================================================
# Verificar si ya existen certificados
# ==============================================================================
if [ -f "$CERT_FILE" ] || [ -f "$KEY_FILE" ]; then
    echo -e "${YELLOW}⚠ Advertencia: Ya existen certificados en este directorio${NC}"
    echo ""
    ls -lh "$CERT_FILE" "$KEY_FILE" 2>/dev/null || true
    echo ""
    read -p "¿Deseas regenerarlos? Esto invalidará los certificados actuales. (s/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo -e "${YELLOW}Operación cancelada${NC}"
        exit 0
    fi
    echo ""
fi

# ==============================================================================
# Generar certificado autofirmado
# ==============================================================================
echo -e "${GREEN}→ Generando certificado SSL autofirmado para: ${DOMAIN}${NC}"
echo "  Validez: ${DAYS_VALID} días"
echo ""

# Crear archivo de configuración OpenSSL temporal
cat > openssl.cnf <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
x509_extensions = v3_ca

[dn]
C=ES
ST=Madrid
L=Madrid
O=ANewHope Dev
OU=Development
CN=${DOMAIN}
emailAddress=dev@anewhope.local

[v3_ca]
subjectAltName = @alt_names
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = ${DOMAIN}
DNS.2 = *.${DOMAIN}
DNS.3 = localhost
DNS.4 = frontend.${DOMAIN}
DNS.5 = backend.${DOMAIN}
DNS.6 = trainer.${DOMAIN}
DNS.7 = anewhope.${DOMAIN}
IP.1 = 127.0.0.1
EOF

# Generar certificado
openssl req -x509 \
    -newkey rsa:2048 \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -days "$DAYS_VALID" \
    -nodes \
    -config openssl.cnf

# Limpiar archivo temporal
rm -f openssl.cnf

# Verificar que se generaron correctamente
if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo -e "${RED}✗ Error: No se pudieron generar los certificados${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Certificados generados exitosamente:${NC}"
echo ""
ls -lh "$CERT_FILE" "$KEY_FILE"
echo ""

# ==============================================================================
# Establecer permisos correctos
# ==============================================================================
echo -e "${GREEN}→ Configurando permisos...${NC}"
chmod 644 "$CERT_FILE"
chmod 600 "$KEY_FILE"
echo -e "${GREEN}✓ Permisos configurados${NC}"
echo ""

# ==============================================================================
# Mostrar información del certificado
# ==============================================================================
echo "===================================="
echo "  Información del Certificado"
echo "===================================="
echo ""
openssl x509 -in "$CERT_FILE" -text -noout | grep -E "(Subject:|Issuer:|Not Before|Not After|DNS:|IP:)" | head -20
echo ""

# ==============================================================================
# Instrucciones de despliegue
# ==============================================================================
echo "===================================="
echo "  Próximos Pasos"
echo "===================================="
echo ""
echo "Los certificados se han generado en:"
echo "  📁 $(pwd)"
echo ""
echo "1️⃣  Copiar certificados al servidor DEV:"
echo ""
echo "    # En el servidor frontend de DEV"
echo "    sudo mkdir -p /etc/nginx/ssl"
echo "    sudo cp ${CERT_FILE} /etc/nginx/ssl/"
echo "    sudo cp ${KEY_FILE} /etc/nginx/ssl/"
echo "    sudo chmod 644 /etc/nginx/ssl/${CERT_FILE}"
echo "    sudo chmod 600 /etc/nginx/ssl/${KEY_FILE}"
echo ""
echo "2️⃣  Verificar que nginx.conf apunta a estos archivos:"
echo ""
echo "    ssl_certificate /etc/nginx/ssl/${CERT_FILE};"
echo "    ssl_certificate_key /etc/nginx/ssl/${KEY_FILE};"
echo ""
echo "3️⃣  Reiniciar nginx:"
echo ""
echo "    # En el servidor DEV"
echo "    cd /ruta/a/docker-compose"
echo "    docker-compose restart nginx"
echo ""
echo "4️⃣  Verificar que SSL funciona:"
echo ""
echo "    curl -Ik https://${DOMAIN}"
echo "    # O desde tu navegador: https://${DOMAIN}"
echo ""
echo -e "${YELLOW}⚠ IMPORTANTE:${NC}"
echo "  Los navegadores mostrarán advertencias de seguridad porque"
echo "  el certificado es autofirmado. Deberás aceptar la advertencia"
echo "  manualmente en cada navegador."
echo ""
echo "  Para evitar esto en Chrome/Edge, puedes importar el certificado"
echo "  en el almacén de certificados raíz del sistema operativo."
echo ""
echo -e "${GREEN}✓ Proceso completado${NC}"
echo ""
