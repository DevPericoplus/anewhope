#!/bin/bash

# Script para preparar el certificado CA para instalación en Windows
# Crea un paquete con el certificado e instrucciones

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/windows-install-package"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Preparar Certificado CA para Windows${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Crear directorio de salida
echo -e "${YELLOW}[1/4] Creando paquete de instalación...${NC}"
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Copiar certificado CA
echo -e "${YELLOW}[2/4] Copiando certificado CA...${NC}"
cp "${SCRIPT_DIR}/mkcert-rootCA.crt" "${OUTPUT_DIR}/"

# Copiar instrucciones
echo -e "${YELLOW}[3/4] Copiando instrucciones...${NC}"
cp "${SCRIPT_DIR}/WINDOWS_INSTALL.md" "${OUTPUT_DIR}/INSTRUCCIONES.md"

# Crear archivo de información rápida
cat > "${OUTPUT_DIR}/LEEME.txt" << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║  Instalación de Certificado SSL para Anewhope               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

PASOS RÁPIDOS:

1. Haz doble clic en: mkcert-rootCA.crt

2. Clic en "Instalar certificado..."

3. Selecciona "Equipo local" (necesita admin)

4. Selecciona "Colocar todos los certificados en el siguiente almacén"

5. Examinar → Selecciona: "Entidades de certificación raíz de confianza"

6. Siguiente → Finalizar → Aceptar advertencia de seguridad

7. Reinicia tu navegador

8. Accede a: https://192.168.0.39


Para instrucciones detalladas, consulta: INSTRUCCIONES.md

═══════════════════════════════════════════════════════════════

URLs que funcionarán después de instalar:

  • https://192.168.0.39          (Frontend)
  • https://192.168.0.39:8443     (Backoffice)

═══════════════════════════════════════════════════════════════

⚠️  IMPORTANTE:
   - Solo instala en equipos de confianza de tu red local
   - NO compartas este certificado fuera de tu red
   - Este certificado es solo para desarrollo, no producción

═══════════════════════════════════════════════════════════════
EOF

# Crear script de instalación automática para Windows
cat > "${OUTPUT_DIR}/instalar_certificado.ps1" << 'EOF'
# Script PowerShell para instalar el certificado CA automáticamente
# Debe ejecutarse como Administrador

param(
    [switch]$Force
)

# Verificar permisos de administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: Este script necesita permisos de Administrador" -ForegroundColor Red
    Write-Host ""
    Write-Host "Click derecho en el script → 'Ejecutar como administrador'" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Presiona Enter para salir"
    exit 1
}

# Ruta del certificado
$certPath = Join-Path $PSScriptRoot "mkcert-rootCA.crt"

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Blue
Write-Host "   Instalador de Certificado CA - Anewhope" -ForegroundColor Blue
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Blue
Write-Host ""

# Verificar que existe el certificado
if (-not (Test-Path $certPath)) {
    Write-Host "ERROR: No se encontró el archivo mkcert-rootCA.crt" -ForegroundColor Red
    Read-Host "Presiona Enter para salir"
    exit 1
}

Write-Host "[1/3] Verificando certificado..." -ForegroundColor Yellow
Write-Host "      Archivo: $certPath" -ForegroundColor Gray

# Verificar si ya está instalado
$existingCert = Get-ChildItem -Path Cert:\LocalMachine\Root | Where-Object {$_.Subject -like "*mkcert*"}

if ($existingCert -and -not $Force) {
    Write-Host ""
    Write-Host "⚠️  Ya existe un certificado mkcert instalado:" -ForegroundColor Yellow
    Write-Host "   Subject: $($existingCert.Subject)" -ForegroundColor Gray
    Write-Host "   Thumbprint: $($existingCert.Thumbprint)" -ForegroundColor Gray
    Write-Host ""

    $response = Read-Host "¿Desea reemplazarlo? (S/N)"
    if ($response -notmatch '^[Ss]$') {
        Write-Host "Instalación cancelada" -ForegroundColor Yellow
        Read-Host "Presiona Enter para salir"
        exit 0
    }

    Write-Host ""
    Write-Host "[2/3] Eliminando certificado anterior..." -ForegroundColor Yellow
    $existingCert | Remove-Item
    Write-Host "      ✓ Certificado anterior eliminado" -ForegroundColor Green
} else {
    Write-Host "      ✓ Certificado válido" -ForegroundColor Green
}

# Instalar certificado
Write-Host ""
Write-Host "[3/3] Instalando certificado CA..." -ForegroundColor Yellow

try {
    Import-Certificate -FilePath $certPath -CertStoreLocation Cert:\LocalMachine\Root -ErrorAction Stop | Out-Null
    Write-Host "      ✓ Certificado instalado correctamente" -ForegroundColor Green
} catch {
    Write-Host "      ✗ Error al instalar: $_" -ForegroundColor Red
    Read-Host "Presiona Enter para salir"
    exit 1
}

# Verificar instalación
$installedCert = Get-ChildItem -Path Cert:\LocalMachine\Root | Where-Object {$_.Subject -like "*mkcert*"}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Blue
Write-Host "   ✓ Instalación Completada" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Blue
Write-Host ""
Write-Host "Certificado instalado:" -ForegroundColor Yellow
Write-Host "  Subject: $($installedCert.Subject)" -ForegroundColor Gray
Write-Host "  Válido hasta: $($installedCert.NotAfter)" -ForegroundColor Gray
Write-Host ""
Write-Host "URLs disponibles:" -ForegroundColor Yellow
Write-Host "  • https://192.168.0.39" -ForegroundColor Green
Write-Host "  • https://192.168.0.39:8443" -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTANTE: Reinicia tu navegador para que reconozca el certificado" -ForegroundColor Yellow
Write-Host ""

Read-Host "Presiona Enter para salir"
EOF

# Verificar información del certificado
echo -e "${YELLOW}[4/4] Verificando certificado...${NC}"
echo ""

if command -v openssl &> /dev/null; then
    echo -e "${BLUE}Información del certificado CA:${NC}"
    openssl x509 -in "${SCRIPT_DIR}/mkcert-rootCA.crt" -noout -subject -issuer -dates | sed 's/^/  /'
else
    echo -e "${YELLOW}  (openssl no disponible para mostrar detalles)${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Paquete creado exitosamente${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Ubicación:${NC}"
echo -e "  ${OUTPUT_DIR}"
echo ""
echo -e "${YELLOW}Archivos incluidos:${NC}"
ls -lh "$OUTPUT_DIR" | tail -n +2 | awk '{print "  • " $9}'
echo ""
echo -e "${YELLOW}Para compartir con Windows:${NC}"
echo -e "  1. Copia toda la carpeta 'windows-install-package' al equipo Windows"
echo -e "  2. En Windows, ejecuta 'instalar_certificado.ps1' como Administrador"
echo -e "  3. O sigue las instrucciones en 'LEEME.txt'"
echo ""
echo -e "${YELLOW}Abrir carpeta:${NC}"
echo -e "  open \"${OUTPUT_DIR}\""
echo ""

# Abrir carpeta automáticamente
read -p "¿Abrir la carpeta ahora? (s/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    open "$OUTPUT_DIR"
fi
