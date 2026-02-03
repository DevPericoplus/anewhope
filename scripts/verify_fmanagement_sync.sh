#!/bin/bash
# ============================================================================
# Script de verificación de sincronización de fmanagement_paths.yml
# ============================================================================
#
# Propósito: Verificar que los archivos fmanagement_paths.yml están
#            sincronizados entre anewhope y fmanagement para cada entorno.
#
# Uso: ./scripts/verify_fmanagement_sync.sh [entorno]
#      - Sin argumentos: verifica todos los entornos
#      - Con entorno específico: verifica solo ese entorno
#

set -e

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Rutas base
ANEWHOPE_BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FMANAGEMENT_BASE="/Users/administrator/develop/fmanagement"

# Entornos a verificar
ENVIRONMENTS=("macbook" "dev" "pre" "pro")

# Función para verificar un entorno específico
verify_environment() {
    local env=$1
    local anewhope_file="${ANEWHOPE_BASE}/infrastructure/environments/${env}/fmanagement_paths.yml"
    local fmanagement_file="${FMANAGEMENT_BASE}/env/${env}/fmanagement_paths.yml"
    
    echo "Verificando entorno: ${env}"
    echo "  - anewhope:    ${anewhope_file}"
    echo "  - fmanagement: ${fmanagement_file}"
    
    # Verificar que ambos archivos existen
    if [ ! -f "${anewhope_file}" ]; then
        echo -e "  ${RED}❌ ERROR: Archivo no encontrado en anewhope${NC}"
        return 1
    fi
    
    if [ ! -f "${fmanagement_file}" ]; then
        echo -e "  ${RED}❌ ERROR: Archivo no encontrado en fmanagement${NC}"
        return 1
    fi
    
    # Comparar archivos (ignorando la línea de comentario SINCRONIZACIÓN)
    # Esta línea es diferente intencionalmente ya que cada archivo apunta a su contraparte
    if diff -I "^# SINCRONIZACIÓN:" -I "^# /Users/administrator" -q "${anewhope_file}" "${fmanagement_file}" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅ SINCRONIZADO${NC}"
        return 0
    else
        echo -e "  ${RED}❌ DESINCRONIZADO${NC}"
        echo ""
        echo "  Diferencias encontradas (ignorando comentarios de sincronización):"
        diff -I "^# SINCRONIZACIÓN:" -I "^# /Users/administrator" "${anewhope_file}" "${fmanagement_file}" | head -20
        echo ""
        echo "  Para sincronizar:"
        echo "    1. Verificar que las diferencias son intencionales"
        echo "    2. Si son valores de configuración, copiar:"
        echo "       cp ${anewhope_file} ${fmanagement_file}"
        echo "    3. Restaurar el comentario de sincronización en fmanagement"
        echo ""
        return 1
    fi
}

# Main
echo "============================================"
echo "Verificación de sincronización fmanagement"
echo "============================================"
echo ""

total=0
failed=0

if [ -z "$1" ]; then
    # Verificar todos los entornos
    for env in "${ENVIRONMENTS[@]}"; do
        if ! verify_environment "$env"; then
            ((failed++))
        fi
        ((total++))
        echo ""
    done
else
    # Verificar solo el entorno especificado
    if ! verify_environment "$1"; then
        ((failed++))
    fi
    ((total++))
fi

# Resumen
echo "============================================"
echo "Resumen de verificación"
echo "============================================"
echo "Total entornos verificados: ${total}"
echo -e "Sincronizados:   ${GREEN}$((total - failed))${NC}"
echo -e "Desincronizados: ${RED}${failed}${NC}"
echo ""

if [ $failed -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Acción requerida: Sincronizar archivos desincronizados${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Todos los archivos están sincronizados${NC}"
    exit 0
fi
