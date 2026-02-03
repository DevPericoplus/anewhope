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
