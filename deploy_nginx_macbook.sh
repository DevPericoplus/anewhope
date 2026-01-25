#!/bin/bash
# Script para desplegar nginx en macbook con Homebrew

set -e

echo "========================================"
echo "DESPLIEGUE DE NGINX EN MACBOOK"
echo "========================================"
echo ""

# Verificar si nginx está instalado
if ! command -v nginx &> /dev/null; then
    echo "📦 Nginx no está instalado. Instalando con Homebrew..."
    brew install nginx
    echo "✅ Nginx instalado correctamente"
else
    echo "✅ Nginx ya está instalado"
fi

echo ""
echo "📋 Copiando configuración de nginx..."
cp infrastructure/servers/macbook/nginx/nginx.conf /usr/local/etc/nginx/nginx.conf
echo "✅ Configuración copiada"

echo ""
echo "🔍 Validando sintaxis de nginx.conf..."
if nginx -t; then
    echo "✅ Sintaxis correcta"
else
    echo "❌ Error en la sintaxis de nginx.conf"
    exit 1
fi

echo ""
echo "🔄 Verificando estado de nginx..."
if brew services list | grep nginx | grep started &> /dev/null; then
    echo "🔄 Nginx está en ejecución. Reiniciando..."
    brew services restart nginx
    echo "✅ Nginx reiniciado correctamente"
else
    echo "🚀 Nginx no está en ejecución. Iniciando..."
    brew services start nginx
    echo "✅ Nginx iniciado correctamente"
fi

echo ""
echo "========================================"
echo "DESPLIEGUE COMPLETADO"
echo "========================================"
echo ""
echo "📊 Estado actual de nginx:"
brew services list | grep nginx
echo ""
echo "🌐 Nginx está escuchando en: http://localhost:8080"
