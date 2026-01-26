#!/bin/bash
# Script de verificación de sincronización OTP
# Uso: ./scripts/verify_otp_sync.sh

set -e

echo "============================================="
echo "  Verificación de Sincronización OTP"
echo "============================================="
echo ""

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Rutas
FRONTEND_LOG="src/apps/5_web_frontend/logs/frontend_secure.log"
MIDDLEWARE_LOG="src/apps/7_service_frontend/logs/middleware_activiy.log"

# 1. Verificar desincronizaciones en logs
echo "1. Verificando desincronizaciones OTP..."
if [ -f "$FRONTEND_LOG" ]; then
    DESYNC_COUNT=$(grep "DESALINEADO" "$FRONTEND_LOG" 2>/dev/null | wc -l | tr -d ' ')
    echo "   Desincronizaciones detectadas: $DESYNC_COUNT"
    
    if [ "$DESYNC_COUNT" -gt "0" ]; then
        echo -e "   ${RED}⚠️  ALERTA: Se detectaron desincronizaciones${NC}"
        echo ""
        echo "   Últimas 10 desincronizaciones:"
        grep "DESALINEADO" "$FRONTEND_LOG" | tail -10
        echo ""
    else
        echo -e "   ${GREEN}✅ No se detectaron desincronizaciones${NC}"
    fi
else
    echo -e "   ${YELLOW}⚠️  Log de frontend no encontrado: $FRONTEND_LOG${NC}"
fi
echo ""

# 2. Verificar reintentos de sincronización
echo "2. Verificando reintentos de sincronización..."
if [ -f "$MIDDLEWARE_LOG" ]; then
    RETRY_COUNT=$(grep "Reintentando" "$MIDDLEWARE_LOG" 2>/dev/null | wc -l | tr -d ' ')
    echo "   Reintentos de sincronización: $RETRY_COUNT"
    
    if [ "$RETRY_COUNT" -gt "0" ]; then
        echo -e "   ${YELLOW}ℹ️  Se detectaron reintentos (esto es normal)${NC}"
        echo ""
        echo "   Últimos 5 reintentos:"
        grep "Reintentando" "$MIDDLEWARE_LOG" | tail -5
        echo ""
    else
        echo -e "   ${GREEN}✅ No hubo necesidad de reintentos${NC}"
    fi
else
    echo -e "   ${YELLOW}⚠️  Log de middleware no encontrado: $MIDDLEWARE_LOG${NC}"
fi
echo ""

# 3. Verificar fallos totales de sincronización
echo "3. Verificando fallos totales de sincronización..."
if [ -f "$MIDDLEWARE_LOG" ]; then
    FAIL_COUNT=$(grep "No se pudo guardar usuarios en broker tras" "$MIDDLEWARE_LOG" 2>/dev/null | wc -l | tr -d ' ')
    echo "   Fallos totales de sincronización: $FAIL_COUNT"
    
    if [ "$FAIL_COUNT" -gt "0" ]; then
        echo -e "   ${RED}🚨 CRÍTICO: Fallos totales de sincronización detectados${NC}"
        echo ""
        echo "   Últimos 5 fallos:"
        grep "No se pudo guardar usuarios en broker tras" "$MIDDLEWARE_LOG" | tail -5
        echo ""
    else
        echo -e "   ${GREEN}✅ No se detectaron fallos totales${NC}"
    fi
else
    echo -e "   ${YELLOW}⚠️  Log de middleware no encontrado: $MIDDLEWARE_LOG${NC}"
fi
echo ""

# 4. Verificar inconsistencias críticas
echo "4. Verificando inconsistencias críticas..."
if [ -f "$FRONTEND_LOG" ]; then
    CRITICAL_COUNT=$(grep "INCONSISTENCIA CRÍTICA" "$FRONTEND_LOG" 2>/dev/null | wc -l | tr -d ' ')
    echo "   Inconsistencias críticas: $CRITICAL_COUNT"
    
    if [ "$CRITICAL_COUNT" -gt "0" ]; then
        echo -e "   ${RED}🚨 CRÍTICO: Inconsistencias detectadas${NC}"
        echo ""
        grep "INCONSISTENCIA CRÍTICA" "$FRONTEND_LOG" | tail -10
        echo ""
    else
        echo -e "   ${GREEN}✅ No se detectaron inconsistencias críticas${NC}"
    fi
fi
echo ""

# 5. Resumen
echo "============================================="
echo "  Resumen de Verificación"
echo "============================================="
if [ "$DESYNC_COUNT" -eq "0" ] && [ "$FAIL_COUNT" -eq "0" ] && [ "$CRITICAL_COUNT" -eq "0" ]; then
    echo -e "${GREEN}✅ SISTEMA SALUDABLE${NC}"
    echo ""
    echo "No se detectaron problemas de sincronización OTP."
    exit 0
elif [ "$FAIL_COUNT" -gt "0" ] || [ "$CRITICAL_COUNT" -gt "0" ]; then
    echo -e "${RED}🚨 ACCIÓN REQUERIDA${NC}"
    echo ""
    echo "Se detectaron problemas críticos que requieren atención inmediata."
    echo "Revisa los logs detallados arriba."
    exit 1
elif [ "$DESYNC_COUNT" -gt "0" ]; then
    echo -e "${YELLOW}⚠️  ADVERTENCIA${NC}"
    echo ""
    echo "Se detectaron desincronizaciones pero no errores críticos."
    echo "Monitorea la situación y considera ejecutar sincronización manual."
    exit 0
else
    echo -e "${GREEN}✅ ESTADO OK${NC}"
    if [ "$RETRY_COUNT" -gt "0" ]; then
        echo ""
        echo "Nota: Se detectaron reintentos, lo cual es normal en redes lentas."
    fi
    exit 0
fi
