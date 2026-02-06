# Tests de Integración con Ollama

Este directorio contiene tests de integración para verificar el funcionamiento de los endpoints de Ollama en el trainer.

## Requisitos Previos

1. **Ollama instalado y corriendo:**
   ```bash
   # Verificar instalación
   ollama --version

   # Iniciar Ollama
   ollama serve
   ```

2. **Modelos descargados:**
   ```bash
   # Listar modelos
   ollama list

   # Descargar modelos necesarios para los tests
   ollama pull llama3.1:8b
   ollama pull deepseek-r1:1.5b
   ollama pull nomic-embed-text:latest
   ```

3. **Trainer corriendo:**
   ```bash
   cd ~/develop/anewhope/src/apps/4_trainer
   source .venv_trainer313/bin/activate
   python main.py
   ```

4. **Dependencias instaladas:**
   ```bash
   pip install pytest httpx
   ```

## Ejecución de Tests

### Opción 1: Script Automatizado (Recomendado)

```bash
cd ~/develop/anewhope/src/apps/4_trainer
./run_ollama_tests.sh
```

Este script:
- ✅ Verifica que Ollama esté corriendo
- ✅ Lista los modelos disponibles
- ✅ Verifica que el trainer esté activo
- ✅ Ejecuta todos los tests con output detallado

### Opción 2: Ejecutar Tests Individuales

```bash
cd ~/develop/anewhope/src/apps/4_trainer/tests

# Todos los tests con output
pytest test_ollama_integration.py -v -s

# Solo un test específico
pytest test_ollama_integration.py::TestOllamaIntegration::test_generate_with_llama3_1 -v -s

# Solo tests de generación
pytest test_ollama_integration.py -k "generate" -v -s
```

### Opción 3: Ejecutar con Python Directamente

```bash
cd ~/develop/anewhope/src/apps/4_trainer/tests
python test_ollama_integration.py
```

## Tests Incluidos

### 1. Health Check
- `test_ollama_health_check`: Verifica que Ollama esté disponible

### 2. Lista de Modelos
- `test_list_models`: Lista todos los modelos disponibles

### 3. Generación de Texto
- `test_generate_with_llama3_1`: Genera texto con llama3.1:8b
- `test_generate_with_deepseek_r1`: Genera texto con deepseek-r1:1.5b
- `test_compare_models_same_prompt`: Compara respuestas de múltiples modelos

### 4. Chat
- `test_chat_with_llama3_1`: Test de chat conversacional

### 5. Embeddings
- `test_embeddings_with_nomic`: Genera embeddings con nomic-embed-text

### 6. Gestión de Modelos
- `test_show_model_info`: Obtiene información detallada de un modelo
- `test_list_running_models`: Lista modelos en ejecución

### 7. Manejo de Errores
- `test_generate_with_nonexistent_model`: Verifica manejo de errores

## Output Esperado

Los tests mostrarán output detallado incluyendo:

```
==================================================
TEST: Generación con llama3.1:8b
==================================================
Prompt: ¿Qué es la inteligencia artificial? Responde en máximo 50 palabras.
==================================================

✓ Respuesta generada exitosamente

Respuesta:
----------------------------------------------------------------------
La inteligencia artificial (IA) es la simulación de procesos de
inteligencia humana por parte de sistemas informáticos. Estos procesos
incluyen el aprendizaje, el razonamiento y la autocorrección...
----------------------------------------------------------------------

Estadísticas:
  - Modelo: llama3.1:8b
  - Tiempo total: 3.45s
  - Duración del modelo: 3.42s
  - Tokens generados: 87
  - Tokens/segundo: 25.44
```

## Resolución de Problemas

### Error: "Ollama no está disponible"

```bash
# Verificar que Ollama está corriendo
curl http://localhost:11434/api/tags

# Si no responde, iniciar Ollama
ollama serve
```

### Error: "Trainer no está corriendo"

```bash
# Verificar estado del trainer
curl http://localhost:8004/trainer/health

# Iniciar el trainer
cd ~/develop/anewhope/src/apps/4_trainer
python main.py
```

### Error: "Model not found"

```bash
# Descargar el modelo faltante
ollama pull llama3.1:8b
ollama pull deepseek-r1:1.5b
ollama pull nomic-embed-text:latest
```

### Error: "Connection timeout"

Los modelos grandes pueden tardar en responder. Si experimentas timeouts:

1. Aumentar el timeout en el test:
   ```python
   TIMEOUT = 120.0  # Aumentar a 2 minutos
   ```

2. Usar modelos más pequeños para tests rápidos:
   ```python
   model = "deepseek-r1:1.5b"  # En lugar de 8b
   ```

## Personalizar Tests

### Cambiar Modelos a Probar

Edita `test_ollama_integration.py` y cambia las variables de modelo:

```python
# En los tests
model = "tu-modelo:tag"
```

### Cambiar Prompts

```python
prompt = "Tu prompt personalizado aquí"
```

### Ajustar Parámetros de Generación

```python
"options": {
    "temperature": 0.7,      # 0.0-1.0 (creatividad)
    "num_predict": 100,      # Máximo de tokens
    "top_p": 0.9,            # Nucleus sampling
    "top_k": 40              # Top-K sampling
}
```

## Métricas de Performance

Los tests muestran automáticamente:
- ⏱️ Tiempo total de generación
- 🔢 Tokens generados
- 🚀 Tokens por segundo
- 💾 Uso de VRAM (para modelos en ejecución)

## Tests de Integración Continua

Para CI/CD, ejecutar en modo silencioso:

```bash
pytest test_ollama_integration.py --tb=short -q
```

## Contribuir

Para agregar nuevos tests:

1. Seguir el patrón existente
2. Usar fixtures `client` o `async_client`
3. Incluir assertions claras
4. Agregar output informativo con print()
5. Documentar el propósito del test

## Recursos

- [Documentación de Ollama](https://ollama.ai/docs)
- [API de Ollama](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Modelos disponibles](https://ollama.ai/library)
- [README del Trainer](../README.md)
