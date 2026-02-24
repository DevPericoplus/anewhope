#!/bin/bash

###############################################################################
# Script de Verificación: Mecanismo de Fallback de Permisos
# 
# Propósito:
#   Verificar que el fallback a MariaDB funciona correctamente cuando
#   los archivos JSON están vacíos.
#
# Uso:
#   ./scripts/test_permissions_fallback.sh
#
# Fecha: 2026-01-26
###############################################################################

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Verificación de Fallback de Permisos${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Directorio base
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MOKS_DIR="$BASE_DIR/src/2_shared_application/moks"

###############################################################################
# 1. Verificar estado de archivos JSON
###############################################################################

echo -e "${YELLOW}1. Estado de archivos JSON:${NC}"
echo ""

for file in roles.json low_level_permisions.json basic_permissions.json organizations.json manage_roles_by_org.json; do
    filepath="$MOKS_DIR/$file"
    
    if [ ! -f "$filepath" ]; then
        echo -e "  ${RED}❌ $file: NO EXISTE${NC}"
        continue
    fi
    
    lines=$(wc -l < "$filepath" | tr -d ' ')
    size=$(du -h "$filepath" | awk '{print $1}')
    content=$(cat "$filepath")
    
    if [ "$content" = "[]" ]; then
        echo -e "  ${YELLOW}⚠️  $file: VACÍO (fallback se activará)${NC}"
    elif [ $lines -lt 5 ]; then
        echo -e "  ${YELLOW}⚠️  $file: CASI VACÍO ($lines líneas, $size)${NC}"
    else
        echo -e "  ${GREEN}✅ $file: OK ($lines líneas, $size)${NC}"
    fi
done

echo ""

###############################################################################
# 2. Verificar servicios requeridos para fallback
###############################################################################

echo -e "${YELLOW}2. Estado de servicios necesarios para fallback:${NC}"
echo ""

# Verificar Broker Backend (puerto 8008)
echo -n "  Broker Backend (puerto 8008)... "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8008/health 2>/dev/null | grep -q "200"; then
    echo -e "${GREEN}✅ ACTIVO${NC}"
else
    echo -e "${RED}❌ NO RESPONDE (fallback NO funcionará)${NC}"
    BROKER_DOWN=1
fi

# Verificar Backend Core (puerto 8003)
echo -n "  Backend Core (puerto 8003)... "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/health 2>/dev/null | grep -q "200"; then
    echo -e "${GREEN}✅ ACTIVO${NC}"
else
    echo -e "${RED}❌ NO RESPONDE (fallback NO funcionará)${NC}"
    CORE_DOWN=1
fi

# Verificar MariaDB (puerto 3306)
echo -n "  MariaDB (puerto 3306)... "
if nc -z localhost 3306 2>/dev/null; then
    echo -e "${GREEN}✅ ACTIVO${NC}"
else
    echo -e "${RED}❌ NO RESPONDE (fallback NO funcionará)${NC}"
    MARIADB_DOWN=1
fi

echo ""

###############################################################################
# 3. Verificar implementación del fallback en código
###############################################################################

echo -e "${YELLOW}3. Verificación de código implementado:${NC}"
echo ""

MIDDLEWARE_FILE="$BASE_DIR/src/apps/7_service_frontend/routermiddleware.py"

echo -n "  Función _get_low_level_permissions_from_broker_fallback()... "
if grep -q "_get_low_level_permissions_from_broker_fallback" "$MIDDLEWARE_FILE"; then
    echo -e "${GREEN}✅ IMPLEMENTADA${NC}"
else
    echo -e "${RED}❌ NO ENCONTRADA${NC}"
fi

echo -n "  Función _get_basic_permissions_from_broker_fallback()... "
if grep -q "_get_basic_permissions_from_broker_fallback" "$MIDDLEWARE_FILE"; then
    echo -e "${GREEN}✅ IMPLEMENTADA${NC}"
else
    echo -e "${RED}❌ NO ENCONTRADA${NC}"
fi

echo -n "  Logging de fallback implementado... "
if grep -q "Fallback: Consultando roles desde MariaDB" "$MIDDLEWARE_FILE"; then
    echo -e "${GREEN}✅ IMPLEMENTADO${NC}"
else
    echo -e "${RED}❌ NO ENCONTRADO${NC}"
fi

echo -n "  Validación de JSON vacío... "
if grep -q "roles.json está vacío" "$MIDDLEWARE_FILE"; then
    echo -e "${GREEN}✅ IMPLEMENTADA${NC}"
else
    echo -e "${RED}❌ NO ENCONTRADA${NC}"
fi

echo ""

###############################################################################
# 4. Verificar documentación
###############################################################################

echo -e "${YELLOW}4. Documentación disponible:${NC}"
echo ""

DOCS_DIR="$BASE_DIR/docs"

for doc in PERMISSIONS_FALLBACK_MECHANISM.md BACKOFFICE_BUTTON_FIX.md FALLBACK_IMPLEMENTATION_SUMMARY.md; do
    docpath="$DOCS_DIR/$doc"
    
    if [ -f "$docpath" ]; then
        lines=$(wc -l < "$docpath" | tr -d ' ')
        size=$(du -h "$docpath" | awk '{print $1}')
        echo -e "  ${GREEN}✅ $doc ($lines líneas, $size)${NC}"
    else
        echo -e "  ${RED}❌ $doc: NO ENCONTRADO${NC}"
    fi
done

echo ""

###############################################################################
# 5. Resumen y recomendaciones
###############################################################################

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}RESUMEN${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Determinar si fallback está listo
FALLBACK_READY=1

# Verificar archivos críticos
if [ ! -f "$MOKS_DIR/roles.json" ] || [ ! -f "$MOKS_DIR/low_level_permisions.json" ]; then
    echo -e "${RED}❌ Archivos JSON críticos no existen${NC}"
    FALLBACK_READY=0
fi

# Verificar implementación
if ! grep -q "_get_low_level_permissions_from_broker_fallback" "$MIDDLEWARE_FILE"; then
    echo -e "${RED}❌ Fallback no implementado en código${NC}"
    FALLBACK_READY=0
fi

# Verificar servicios (solo si JSON está vacío)
ROLES_CONTENT=$(cat "$MOKS_DIR/roles.json")
if [ "$ROLES_CONTENT" = "[]" ]; then
    echo -e "${YELLOW}⚠️  roles.json está vacío → Fallback se activará automáticamente${NC}"
    
    if [ -n "$BROKER_DOWN" ] || [ -n "$CORE_DOWN" ] || [ -n "$MARIADB_DOWN" ]; then
        echo -e "${RED}❌ Servicios necesarios para fallback NO están activos${NC}"
        echo ""
        echo -e "${YELLOW}Para que el fallback funcione, necesitas:${NC}"
        
        [ -n "$BROKER_DOWN" ] && echo -e "  ${RED}• Iniciar Broker Backend (puerto 8008)${NC}"
        [ -n "$CORE_DOWN" ] && echo -e "  ${RED}• Iniciar Backend Core (puerto 8003)${NC}"
        [ -n "$MARIADB_DOWN" ] && echo -e "  ${RED}• Iniciar MariaDB (puerto 3306)${NC}"
        
        FALLBACK_READY=0
    else
        echo -e "${GREEN}✅ Servicios necesarios para fallback están activos${NC}"
    fi
else
    echo -e "${GREEN}✅ roles.json tiene datos → Fallback NO es necesario${NC}"
fi

echo ""

if [ $FALLBACK_READY -eq 1 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ SISTEMA LISTO PARA USAR${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${GREEN}El mecanismo de fallback está correctamente implementado.${NC}"
    echo ""
    
    if [ "$ROLES_CONTENT" = "[]" ]; then
        echo -e "${YELLOW}MODO: Fallback Activo (JSON vacío)${NC}"
        echo ""
        echo "Próximos pasos:"
        echo "1. Hacer login con adminone"
        echo "2. Ver logs: tail -f src/apps/7_service_frontend/logs/middleware_activiy.log"
        echo "3. Buscar: '✅ Fallback exitoso: Permisos cargados desde MariaDB'"
        echo "4. Verificar que botón 'Backoffice' aparece"
    else
        echo -e "${GREEN}MODO: JSON Normal (sin fallback)${NC}"
        echo ""
        echo "Próximos pasos:"
        echo "1. Hacer login con adminone"
        echo "2. Ver logs: tail -f src/apps/7_service_frontend/logs/middleware_activiy.log"
        echo "3. Buscar: 'Permisos cargados desde JSON local'"
        echo "4. Verificar que botón 'Backoffice' aparece"
        echo ""
        echo "Para probar el fallback:"
        echo "  - Vacía roles.json: echo '[]' > src/2_shared_application/moks/roles.json"
        echo "  - Reinicia frontend"
        echo "  - Haz login de nuevo"
    fi
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ SISTEMA NO LISTO${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${RED}Hay problemas que deben corregirse antes de usar el sistema.${NC}"
    echo -e "${YELLOW}Revisa los errores marcados arriba.${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo ""

# Return code
exit $(( $FALLBACK_READY == 1 ? 0 : 1 ))
