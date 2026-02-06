# Guía para Ejecutar Tests de Ollama

## 📋 Pasos para Ejecutar los Tests

### 1. Reiniciar el Trainer con Integración de Ollama

El trainer debe reiniciarse para cargar los endpoints de Ollama:

```bash
# Detener el trainer si está corriendo (Ctrl+C en la terminal donde corre)

# Navegar al directorio del trainer
cd ~/develop/anewhope/src/apps/4_trainer

# Activar entorno virtual
source .venv_trainer313/bin/activate

# Iniciar el trainer
python main.py
```

**Verifica en los logs de inicio que veas:**
```
INFO: Adaptador de Ollama inicializado con host: http://localhost:11434
INFO: Endpoints de Ollama registrados correctamente
```

### 2. Verificar que Todo Está Listo

En otra terminal, ejecuta:

```bash
# Verificar Ollama
curl http://localhost:11434/api/tags

# Verificar Trainer
curl http://localhost:8004/trainer/health

# Verificar integración Ollama
curl http://localhost:8004/trainer/ollama/health
```

**Deberías ver:**
- ✅ Ollama responde con lista de modelos
- ✅ Trainer responde con `"status": "healthy"`
- ✅ Ollama health check responde con `"status": "healthy"`

### 3. Ejecutar los Tests

```bash
cd ~/develop/anewhope/src/apps/4_trainer

# Opción 1: Script automatizado (recomendado)
./run_ollama_tests.sh

# Opción 2: Pytest directo
cd tests
pytest test_ollama_integration.py -v -s
```

## 📊 Tests Ejecutados

El script ejecutará los siguientes tests en orden:

### Test 1: Health Check ✓
Verifica que Ollama esté disponible

### Test 2: Lista de Modelos ✓
Muestra todos los modelos instalados

### Test 3: Generación con llama3.1:8b ✓
- Prompt: "¿Qué es la inteligencia artificial? Responde en máximo 50 palabras."
- Verifica respuesta
- Muestra estadísticas (tiempo, tokens, tokens/seg)

### Test 4: Generación con deepseek-r1:1.5b ✓
- Mismo prompt
- Verifica respuesta
- Muestra estadísticas

### Test 5: Comparación de Modelos ✓
- Usa el mismo prompt en ambos modelos
- Compara respuestas lado a lado
- Muestra tiempos y tokens

### Test 6: Chat Conversacional ✓
- Test de chat con llama3.1:8b
- Pregunta: "¿Cuál es la capital de España?"
- Verifica que responda "Madrid"

### Test 7: Embeddings ✓
- Genera embeddings con nomic-embed-text
- Muestra dimensiones del vector

### Test 8: Información de Modelo ✓
- Obtiene detalles técnicos de llama3.1:8b
- Muestra familia, parámetros, cuantización

### Test 9: Modelos en Ejecución ✓
- Lista modelos actualmente cargados en memoria
- Muestra uso de VRAM

### Test 10: Manejo de Errores ✓
- Intenta usar un modelo inexistente
- Verifica que el error se maneje correctamente

## 🎯 Output Esperado

```
==================================================
RESUMEN DE MODELOS DISPONIBLES EN OLLAMA
==================================================
NAME                                                    ID              SIZE      MODIFIED
kimi-k2.5:cloud                                         6d1c3246c608    -         3 days ago
deepseek-coder:6.7b                                     ce298d984115    3.8 GB    2 weeks ago
llama3.1:8b                                             46e0c10c039e    4.9 GB    2 months ago
deepseek-r1:1.5b                                        e0979632db5a    1.1 GB    2 months ago
deepseek-r1:8b                                          6995872bfe4c    5.2 GB    2 months ago
nomic-embed-text:latest                                 0a109f422b47    274 MB    2 months ago
==================================================

tests/test_ollama_integration.py::TestOllamaIntegration::test_ollama_health_check

✓ Ollama health check: Ollama está funcionando correctamente
PASSED

tests/test_ollama_integration.py::TestOllamaIntegration::test_list_models

✓ Modelos disponibles: 8
  - llama3.1:8b: 4.87 GB
  - deepseek-r1:8b: 5.18 GB
  - deepseek-r1:1.5b: 1.09 GB
  - nomic-embed-text:latest: 0.27 GB
  - deepseek-coder:6.7b: 3.78 GB
PASSED

tests/test_ollama_integration.py::TestOllamaIntegration::test_generate_with_llama3_1

======================================================================
TEST: Generación con llama3.1:8b
======================================================================
Prompt: ¿Qué es la inteligencia artificial? Responde en máximo 50 palabras.
======================================================================

✓ Respuesta generada exitosamente

Respuesta:
----------------------------------------------------------------------
La inteligencia artificial (IA) es la simulación de procesos de
inteligencia humana mediante máquinas y sistemas informáticos,
incluyendo el aprendizaje, el razonamiento y la autocorrección.
----------------------------------------------------------------------

Estadísticas:
  - Modelo: llama3.1:8b
  - Tiempo total: 3.45s
  - Duración del modelo: 3.42s
  - Tokens generados: 87
  - Tokens/segundo: 25.44
PASSED

tests/test_ollama_integration.py::TestOllamaIntegration::test_generate_with_deepseek_r1

======================================================================
TEST: Generación con deepseek-r1:1.5b
======================================================================
Prompt: ¿Qué es la inteligencia artificial? Responde en máximo 50 palabras.
======================================================================

✓ Respuesta generada exitosamente

Respuesta:
----------------------------------------------------------------------
La inteligencia artificial es la capacidad de las máquinas para
realizar tareas que normalmente requieren inteligencia humana,
como el reconocimiento de voz, la toma de decisiones y el
aprendizaje automático.
----------------------------------------------------------------------

Estadísticas:
  - Modelo: deepseek-r1:1.5b
  - Tiempo total: 2.15s
  - Duración del modelo: 2.12s
  - Tokens generados: 52
  - Tokens/segundo: 24.53
PASSED

tests/test_ollama_integration.py::TestOllamaIntegration::test_compare_models_same_prompt

======================================================================
TEST: Comparación de Modelos
======================================================================
Prompt: Explica qué es Python en una frase.
Modelos: llama3.1:8b, deepseek-r1:1.5b
======================================================================

Generando con llama3.1:8b...
Generando con deepseek-r1:1.5b...

======================================================================
RESULTADOS DE LA COMPARACIÓN
======================================================================

1. Modelo: llama3.1:8b
   Tiempo: 1.85s
   Tokens: 35
   Respuesta:
   ------------------------------------------------------------------
   Python es un lenguaje de programación de alto nivel, interpretado
   y orientado a objetos.
   ------------------------------------------------------------------

2. Modelo: deepseek-r1:1.5b
   Tiempo: 1.23s
   Tokens: 28
   Respuesta:
   ------------------------------------------------------------------
   Python es un lenguaje de programación interpretado, de alto nivel
   y versátil.
   ------------------------------------------------------------------

PASSED

... [más tests] ...

========================================
✅ Todos los tests pasaron exitosamente
========================================
```

## ⚠️ Solución de Problemas

### Si el endpoint /trainer/ollama/health no responde:

**Causa:** El trainer no cargó los endpoints de Ollama

**Solución:**
1. Detener el trainer (Ctrl+C)
2. Verificar que el archivo `apitrainer_ollama.py` existe
3. Reiniciar el trainer
4. Verificar logs de inicio

### Si los tests fallan con "Connection refused":

**Causa:** Trainer o Ollama no están corriendo

**Solución:**
```bash
# Terminal 1: Ollama
ollama serve

# Terminal 2: Trainer
cd ~/develop/anewhope/src/apps/4_trainer
source .venv_trainer313/bin/activate
python main.py
```

### Si un modelo específico falla:

**Causa:** El modelo no está instalado

**Solución:**
```bash
ollama pull llama3.1:8b
ollama pull deepseek-r1:1.5b
ollama pull nomic-embed-text:latest
```

### Si los tests son muy lentos:

**Causa:** Modelos grandes tardan en procesar

**Solución:**
- Usa modelos más pequeños (1.5b en lugar de 8b)
- Reduce `num_predict` en las opciones
- Aumenta el timeout en el test

## 📝 Notas

- Los tests generan output detallado con `-s` (no capturar stdout)
- Cada test muestra estadísticas de performance
- Los tiempos varían según el hardware
- Los primeros requests son más lentos (carga del modelo en memoria)
- Los modelos permanecen en memoria durante 5 minutos después del último uso

## 🎓 Para Más Información

- Ver: `tests/README_OLLAMA_TESTS.md` - Documentación completa
- Ver: `README.md` - Documentación del trainer
- Ver: `AGENTS.md` - Reglas para desarrollo

## ✅ Checklist Final

Antes de ejecutar los tests, verifica:

- [ ] Ollama instalado (`ollama --version`)
- [ ] Ollama corriendo (`curl http://localhost:11434/api/tags`)
- [ ] Modelos descargados (`ollama list`)
- [ ] Trainer reiniciado con integración Ollama
- [ ] Endpoints de Ollama registrados (ver logs)
- [ ] Tests ubicados en `tests/test_ollama_integration.py`
- [ ] Script ejecutable (`chmod +x run_ollama_tests.sh`)

¡Todo listo para ejecutar los tests! 🚀
