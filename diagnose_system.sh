#!/bin/bash
# Script de diagnóstico para nginx y servicios en macbook

echo "========================================"
echo "DIAGNÓSTICO DEL SISTEMA"
echo "========================================"
echo ""

echo "=== Estado de Nginx ==="
brew services list | grep nginx
echo ""
lsof -i :443 | grep nginx || echo "⚠️ Nginx no está escuchando en puerto 443"
echo ""

echo "=== Estado del Frontend (8005) ==="
lsof -i :8005 || echo "⚠️ Frontend no está corriendo en puerto 8005"
echo ""

echo "=== Estado del Middleware (8007) ==="
lsof -i :8007 || echo "⚠️ Middleware no está corriendo en puerto 8007"
echo ""

echo "=== Estado del Backend Core (8003) ==="
lsof -i :8003 || echo "⚠️ Backend Core no está corriendo en puerto 8003"
echo ""

echo "=== Estado del Broker Backend (8008) ==="
lsof -i :8008 || echo "⚠️ Broker Backend no está corriendo en puerto 8008"
echo ""

echo "=== Verificar certificados ==="
if [ -f "infrastructure/certificates/macbook/tfmmyllm.ai.pem" ]; then
    echo "✅ Certificado público encontrado"
    openssl x509 -in infrastructure/certificates/macbook/tfmmyllm.ai.pem -noout -dates
else
    echo "❌ Certificado público NO encontrado"
fi
echo ""

if [ -f "infrastructure/certificates/macbook/tfmmyllm.ai-key.pem" ]; then
    echo "✅ Clave privada encontrada"
else
    echo "❌ Clave privada NO encontrada"
fi
echo ""

echo "=== Test de conectividad HTTPS ==="
curl -I https://tfmmyllm.ai 2>&1 | head -5
echo ""

echo "=== Test directo al frontend (HTTP) ==="
curl -I http://127.0.0.1:8005 2>&1 | head -5
echo ""

echo "=== Verificar /etc/hosts ==="
grep tfmmyllm.ai /etc/hosts || echo "⚠️ Entrada tfmmyllm.ai NO encontrada en /etc/hosts"
echo ""

echo "=== Logs recientes de nginx (access) ==="
tail -5 /usr/local/var/log/nginx/access.log 2>/dev/null || echo "No hay logs de acceso"
echo ""

echo "=== Logs recientes de nginx (error) ==="
tail -5 /usr/local/var/log/nginx/error.log 2>/dev/null || echo "No hay logs de error"
echo ""

echo "========================================"
echo "DIAGNÓSTICO COMPLETADO"
echo "========================================"
