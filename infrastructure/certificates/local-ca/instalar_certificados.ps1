# Instala las CA locales de anewhope (dev y silicon) en el almacén de
# raíz del equipo. Ejecutar como Administrador.
# No toca claves privadas ni quita una CA al instalar la otra.

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdmin)) {
    Write-Host "ERROR: ejecuta este script como Administrador." -ForegroundColor Red
    Write-Host "Clic derecho → Ejecutar con PowerShell como administrador" -ForegroundColor Yellow
    Read-Host "Enter para salir"
    exit 1
}

$here = $PSScriptRoot
$certs = @(
    @{ File = "ca-dev.crt";     Label = "dev (house.loc)" },
    @{ File = "ca-silicon.crt"; Label = "silicon" }
)

Write-Host ""
Write-Host "Instalador de CA locales — anewhope" -ForegroundColor Cyan
Write-Host ""

foreach ($item in $certs) {
    $path = Join-Path $here $item.File
    if (-not (Test-Path $path)) {
        Write-Host "ERROR: no está $($item.File) junto a este script." -ForegroundColor Red
        Read-Host "Enter para salir"
        exit 1
    }

    Write-Host "[$($item.Label)] $($item.File)" -ForegroundColor Yellow

    $incoming = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2 $path
    $roots = Get-ChildItem Cert:\LocalMachine\Root
    $sameThumb = $roots | Where-Object { $_.Thumbprint -eq $incoming.Thumbprint }
    if ($sameThumb) {
        Write-Host "  ya estaba instalado ($($incoming.Subject))" -ForegroundColor Green
        continue
    }

    $sameName = $roots | Where-Object {
        $_.Subject -eq $incoming.Subject -and $_.Thumbprint -ne $incoming.Thumbprint
    }
    if ($sameName -and -not $Force) {
        Write-Host "  hay otra CA con el mismo Subject (huella distinta):" -ForegroundColor Yellow
        $sameName | ForEach-Object { Write-Host "    $($_.Subject)  $($_.Thumbprint)" -ForegroundColor Gray }
        $ans = Read-Host "  ¿sustituirla? (S/N)"
        if ($ans -match '^[Ss]') {
            $sameName | Remove-Item
        }
    }

    Import-Certificate -FilePath $path -CertStoreLocation Cert:\LocalMachine\Root | Out-Null
    Write-Host "  instalado: $($incoming.Subject)" -ForegroundColor Green
}

$hostsPath = Join-Path $env:SystemRoot "System32\drivers\etc\hosts"
$devLines = @(
    "192.168.0.241    frontend.house.loc",
    "192.168.0.241    laimweb.house.loc",
    "192.168.0.241    laim.house.loc",
    "192.168.0.241    artifactory.house.loc",
    "192.168.0.240    util01.house.loc"
)

Write-Host ""
$ansHosts = Read-Host "¿Añadir las entradas de dev a $hostsPath? (S/N)"
if ($ansHosts -match '^[Ss]') {
    $current = Get-Content $hostsPath -ErrorAction Stop
    $added = 0
    foreach ($line in $devLines) {
        $name = ($line -split '\s+')[-1]
        if ($current | Where-Object { $_ -match "(^|\s)$([regex]::Escape($name))(\s|$)" }) {
            Write-Host "  $name ya estaba" -ForegroundColor Gray
            continue
        }
        Add-Content -Path $hostsPath -Value $line
        Write-Host "  añadido $line" -ForegroundColor Green
        $added++
    }
    if ($added -eq 0) {
        Write-Host "  hosts de dev ya estaban completos" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Listo. Cierra Chrome/Edge del todo y abre:" -ForegroundColor Cyan
Write-Host "  https://frontend.house.loc"
Write-Host "  https://laimweb.house.loc"
Write-Host ""
Write-Host "Firefox usa su propio almacén: importar ca-dev.crt en Autoridades." -ForegroundColor Yellow
Write-Host ""
Read-Host "Enter para salir"
