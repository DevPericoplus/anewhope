#!/bin/bash
# Script para generar certificados SSL para tfmmyllm.ai con mkcert

set -e

echo "========================================"
echo "GENERACIÓN DE CERTIFICADOS SSL"
echo "Dominio: tfmmyllm.ai"
echo "========================================"
echo ""

# Verificar si mkcert está instalado
if ! command -v mkcert &> /dev/null; then
    echo "❌ mkcert no está instalado"
    echo ""
    echo "Por favor, instálalo con:"
    echo "  brew install mkcert nss"
    echo "  mkcert -install"
    exit 1
fi

echo "✅ mkcert está instalado"
echo ""

# Verificar si la CA está instalada
if ! mkcert -CAROOT &> /dev/null; then
    echo "⚠️  CA de mkcert no está instalada"
    echo "Instalando CA local..."
    mkcert -install
else
    echo "✅ CA de mkcert instalada en: $(mkcert -CAROOT)"
fi

echo ""
echo "📋 Generando certificados para:"
echo "  - tfmmyllm.ai"
echo "  - *.tfmmyllm.ai (wildcard)"
echo "  - localhost"
echo "  - 127.0.0.1"
echo "  - ::1"
echo ""

# Navegar al directorio de certificados
cd "$(dirname "$0")"

# Generar certificados
mkcert -key-file tfmmyllm.ai-key.pem \
       -cert-file tfmmyllm.ai.pem \
       tfmmyllm.ai "*.tfmmyllm.ai" localhost 127.0.0.1 ::1

echo ""
echo "✅ Certificados generados exitosamente"
echo ""
echo "📄 Archivos creados:"
echo "  - tfmmyllm.ai.pem (certificado público)"
echo "  - tfmmyllm.ai-key.pem (clave privada)"
echo ""

# Verificar certificado
echo "🔍 Información del certificado:"
echo ""
openssl x509 -in tfmmyllm.ai.pem -noout -subject -issuer -dates
echo ""
echo "📋 Dominios incluidos (SANs):"
openssl x509 -in tfmmyllm.ai.pem -noout -text | grep -A 1 "Subject Alternative Name" | tail -n 1
echo ""

echo "========================================"
echo "CERTIFICADOS LISTOS PARA USAR"
echo "========================================"
echo ""
echo "Ubicación: $(pwd)"
echo ""
echo "Próximos pasos:"
echo "1. Configurar nginx con estos certificados"
echo "2. Ejecutar: ./deploy_nginx_macbook.sh"
echo "3. Acceder a: https://tfmmyllm.ai:8443"
