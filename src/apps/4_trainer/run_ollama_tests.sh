#!/bin/bash

# Script para ejecutar tests de integración con Ollama

echo "=========================================="
echo "Tests de Integración con Ollama - Trainer"
echo "=========================================="
echo ""

# Verificar que Ollama está corriendo
echo "1. Verificando que Ollama está disponible..."
if ! command -v ollama &> /dev/null; then
    echo "❌ ERROR: Ollama no está instalado"
    echo "Instálalo con: curl https://ollama.ai/install.sh | sh"
    exit 1
fi

if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "❌ ERROR: Ollama no está corriendo"
    echo "Inícialo con: ollama serve"
    exit 1
fi

echo "✓ Ollama está disponible"
echo ""

# Listar modelos disponibles
echo "2. Modelos disponibles:"
ollama list
echo ""

# Verificar que el trainer está corriendo
echo "3. Verificando que el trainer está corriendo..."
if ! curl -s http://localhost:8004/trainer/health > /dev/null 2>&1; then
    echo "❌ ERROR: Trainer no está corriendo"
    echo "Inícialo con: cd ~/develop/anewhope/src/apps/4_trainer && python main.py"
    exit 1
fi

echo "✓ Trainer está disponible"
echo ""

# Verificar que la integración con Ollama está activa
echo "4. Verificando integración con Ollama en trainer..."
if curl -s http://localhost:8004/trainer/ollama/health | grep -q "healthy"; then
    echo "✓ Integración con Ollama está activa"
else
    echo "⚠️  WARNING: La integración con Ollama puede no estar activa"
fi
echo ""

# Activar entorno virtual si existe
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
if [ -d "$ROOT_DIR/.venv_trainer312" ]; then
    echo "5. Activando entorno virtual..."
    source "$ROOT_DIR/.venv_trainer312/bin/activate"
    echo "✓ Entorno virtual activado"
    echo ""
fi

# Ejecutar tests
echo "6. Ejecutando tests..."
echo "=========================================="
echo ""

cd tests
pytest test_ollama_integration.py -v -s --tb=short

TEST_EXIT_CODE=$?

echo ""
echo "=========================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ Todos los tests pasaron exitosamente"
else
    echo "❌ Algunos tests fallaron"
fi
echo "=========================================="

exit $TEST_EXIT_CODE
