# Diseño: Sistema de Entrenamiento Autónomo con Fine-Tuning LoRA

## 📋 Objetivo
Extender el proceso de entrenamiento RAG actual para generar modelos autónomos en formato GGUF que funcionen sin dependencias de infraestructura (ChromaDB, modelos base locales).

## 🏗️ Arquitectura

### Proceso Actual (Fases 1-5)
```
1. REGISTRO        → Registrar entrenamiento en BD
2. VALIDACIÓN      → Verificar directorio, escanear archivos, clasificar, validar
3. PREPARACIÓN     → Cargar documentos, chunking, generar embeddings
4. CONFIGURACIÓN   → Conectar ChromaDB, crear colección, insertar docs
5. ENTRENAMIENTO   → Generar Modelfile, registrar en Ollama, test
```
**Resultado:** Modelo que depende de ChromaDB + modelo base local

### Proceso Extendido (Fases 6-9)
```
6. GENERACIÓN DATASET   → Crear pares Q&A desde chunks (híbrido: templates + LLM)
7. PREPARACIÓN LORA     → Configurar entorno LoRA, cargar modelo base
8. ENTRENAMIENTO LORA   → Fine-tuning con adaptadores LoRA
9. EXPORTACIÓN GGUF     → Merge LoRA + base, exportar a GGUF, packaging
```
**Resultado:** Modelo autónomo `.gguf` + `Modelfile` para distribución

## 🔧 Componentes Técnicos

### 1. Variable de Entorno: training_mode

**Ubicación:** `infrastructure/environments/{env}/env.yaml`

```yaml
# Modo de entrenamiento
# - simulation: Solo RAG (fases 1-5), sin fine-tuning
# - test: RAG + fine-tuning reducido (pocas epochs, dataset pequeño)
# - production: RAG + fine-tuning completo (epochs completas, dataset full)
training_mode: simulation
```

**Comportamiento:**
- `simulation` (macbook 16GB): Solo RAG, genera Modelfile tradicional
- `test` (dev con GPU): RAG + LoRA con 100 ejemplos, 1-2 epochs
- `production` (pre/pro con GPU): RAG + LoRA con dataset completo, 3-5 epochs

### 2. Nuevas Subfases (Fase 6-9)

#### Fase 6: Generación de Dataset (6.1 - 6.5)
- **6.1** - Analizar chunks disponibles
- **6.2** - Generar plantillas de preguntas (templates predefinidos)
- **6.3** - Generar Q&A con LLM (usar deepseek-r1 vía Ollama)
- **6.4** - Validar y formatear dataset (JSONL para LoRA)
- **6.5** - Guardar dataset (`/data/.../datasets/ENT{id}_dataset.jsonl`)

#### Fase 7: Preparación LoRA (7.1 - 7.4)
- **7.1** - Verificar dependencias (MLX/Unsloth instalado)
- **7.2** - Descargar modelo base en formato HF (si necesario)
- **7.3** - Configurar parámetros LoRA (rank, alpha, dropout)
- **7.4** - Preparar entorno de entrenamiento

#### Fase 8: Entrenamiento LoRA (8.1 - 8.6)
- **8.1** - Inicializar trainer con dataset
- **8.2** - Epoch 1/N (actualización cada X steps)
- **8.3** - Epoch 2/N
- **8.4** - Epoch N/N
- **8.5** - Evaluar modelo fine-tuned
- **8.6** - Guardar adaptadores LoRA

#### Fase 9: Exportación GGUF (9.1 - 9.5)
- **9.1** - Merge adaptadores LoRA con modelo base
- **9.2** - Convertir a formato GGUF (quantización Q8_0)
- **9.3** - Crear Modelfile para cliente (`FROM ./modelo.gguf`)
- **9.4** - Generar README con instrucciones
- **9.5** - Empaquetar entregable (ZIP con GGUF + Modelfile + README)

### 3. Estructura de Datos

#### Dataset Format (JSONL)
```json
{"instruction": "¿Qué es {concepto} según la documentación?", "input": "", "output": "{contenido_chunk}"}
{"instruction": "Explica {proceso} descrito en el documento", "input": "", "output": "{contenido_chunk}"}
```

#### Tabla BD: `entrenamientos` (columnas nuevas)
```sql
ALTER TABLE entrenamientos ADD COLUMN training_mode VARCHAR(20) DEFAULT 'simulation';
ALTER TABLE entrenamientos ADD COLUMN dataset_path VARCHAR(500);
ALTER TABLE entrenamientos ADD COLUMN lora_path VARCHAR(500);
ALTER TABLE entrenamientos ADD COLUMN gguf_path VARCHAR(500);
ALTER TABLE entrenamientos ADD COLUMN package_path VARCHAR(500);
```

#### Tabla BD: `evoluciones_entrenamientos` (nuevas subfases)
- Se agregan 20 subfases (6.1 a 9.5) a las 16 existentes
- Total: 36 subfases por entrenamiento completo en modo `production`

### 4. Stack Tecnológico

#### Para Fine-Tuning LoRA (Mac M3)
**Opción A: MLX-LM (Apple Silicon)** ⭐ Recomendada
```python
# Instalación
pip install mlx mlx-lm

# Ventajas:
# - Optimizado para Apple Silicon
# - Bajo uso de memoria (16GB suficiente)
# - Rápido en Mac M-series
```

**Opción B: Unsloth (Fallback)**
```python
pip install unsloth
# - Compatible con Mac (con limitaciones)
# - 2x más rápido que métodos tradicionales
```

#### Para Conversión GGUF
```bash
# llama.cpp con scripts de conversión
git clone https://github.com/ggerganov/llama.cpp
pip install -r requirements.txt

# Uso:
python convert-hf-to-gguf.py modelo_finetuned/ \
  --outfile modelo-autonomo.gguf \
  --outtype q8_0
```

### 5. Flujo de UI/UX

#### Botón en "Versiones preparadas para entrenamiento inicial"
```python
# Estado actual: Botón "Enviar al trainer" → Abre modal
# Estado nuevo: DOS botones por versión

[Entrenamiento RAG]  # Actual, abre modal, fases 1-5
[Entrenamiento Completo]  # Nuevo, abre panel evolución, fases 1-9 (según training_mode)
```

#### Panel "Evolución del entrenamiento"
- Mostrar 16 subfases (simulation) o 36 subfases (test/production)
- Indicador visual de training_mode activo
- Estimación de tiempo según modo:
  - simulation: 1-3 minutos
  - test: 15-30 minutos
  - production: 1-4 horas

### 6. Estructura de Archivos

```
/data/anewhope/files/trainer_server/
├── internal/
│   ├── models/
│   │   └── ORG00001/PRJ00001/v002/
│   │       ├── Modelfile_ENT33              # RAG (actual)
│   │       ├── ENT33_dataset.jsonl         # Dataset Q&A
│   │       ├── ENT33_lora/                 # Adaptadores LoRA
│   │       │   ├── adapter_config.json
│   │       │   └── adapter_model.safetensors
│   │       └── ENT33_autonomous.gguf       # Modelo final autónomo
│   └── datasets/                           # Datasets generados
└── deliverables/                           # Paquetes para cliente
    └── ORG00001_PRJ00001_v002_ENT33.zip
        ├── modelo-dptocomercial-v002.gguf
        ├── Modelfile
        └── README.md
```

### 7. Estimación de Recursos

#### Mac M3 (16GB RAM) - Modo `simulation`
- Solo RAG: 1-3 min
- No fine-tuning

#### Mac M3 (16GB RAM) - Modo `test` (si se ejecuta)
- RAG: 1-3 min
- Dataset: 2-5 min (100 ejemplos con LLM)
- LoRA: 10-20 min (1-2 epochs, rank=8)
- Export: 2-5 min
- **Total:** ~20-35 minutos

#### GPU Server (32GB+ VRAM) - Modo `production`
- RAG: 1-3 min
- Dataset: 5-15 min (todos los chunks)
- LoRA: 30-120 min (3-5 epochs, rank=16-32)
- Export: 5-10 min
- **Total:** ~45-150 minutos

### 8. Parámetros de LoRA

#### Modo `test` (desarrollo)
```python
lora_config = {
    "r": 8,              # rank (bajo = menos parámetros)
    "lora_alpha": 16,
    "lora_dropout": 0.05,
    "target_modules": ["q_proj", "v_proj"],
    "epochs": 1,
    "batch_size": 2,
    "learning_rate": 2e-4
}
```

#### Modo `production`
```python
lora_config = {
    "r": 16,             # rank (más parámetros = mejor calidad)
    "lora_alpha": 32,
    "lora_dropout": 0.1,
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
    "epochs": 3,
    "batch_size": 4,
    "learning_rate": 1e-4
}
```

## 🚀 Plan de Implementación

### Sprint 1: Infraestructura Base (2-3 días)
1. Añadir `training_mode` a env.yaml
2. Crear migraciones BD (nuevas columnas + subfases)
3. Instalar dependencias MLX/Unsloth
4. Crear estructura de carpetas

### Sprint 2: Generación de Dataset (2-3 días)
1. Implementar templates de preguntas
2. Integrar generación automática con Ollama
3. Formateo y validación JSONL
4. Actualizar subfases 6.1-6.5 en BD

### Sprint 3: Fine-Tuning LoRA (3-4 días)
1. Wrapper de MLX para LoRA training
2. Monitoreo de progreso (subfases 7.1-8.6)
3. Callback para actualizar BD cada epoch
4. Manejo de errores y recovery

### Sprint 4: Exportación GGUF (2 días)
1. Merge LoRA + base model
2. Conversión a GGUF con llama.cpp
3. Generación de Modelfile + README
4. Empaquetado ZIP (subfases 9.1-9.5)

### Sprint 5: Integración UI (2-3 días)
1. Botón "Entrenamiento Completo" en viewer
2. Extender panel evolución (36 subfases)
3. Indicadores de training_mode
4. Descarga de paquete final

### Sprint 6: Testing y Optimización (2-3 días)
1. Tests en macbook (simulation)
2. Tests en dev (test mode)
3. Validación de modelo autónomo
4. Documentación final

**Total estimado: 13-18 días de desarrollo**

## 📦 Entregable al Cliente

### Contenido del ZIP
```
modelo-dptocomercial-v002/
├── modelo-dptocomercial-v002.gguf  (3-5 GB)
├── Modelfile
└── README.md
```

### README.md (ejemplo)
```markdown
# Modelo IA - dptocomercial v002

Modelo de inteligencia artificial entrenado con la documentación del proyecto dptocomercial.

## Requisitos
- Ollama instalado (https://ollama.com)
- 8GB RAM mínimo
- 6GB espacio en disco

## Instalación

1. Extraer el ZIP en una carpeta
2. Abrir terminal en esa carpeta
3. Ejecutar:
   ```bash
   ollama create dptocomercial-v002 -f Modelfile
   ```

## Uso

```bash
ollama run dptocomercial-v002 "¿Qué información tienes sobre [tu pregunta]?"
```

## Metadatos
- Organización: myllm
- Proyecto: dptocomercial
- Versión: v002
- Documentos: 10
- Fecha: 2026-02-12
```

## ⚠️ Consideraciones

### Limitaciones Técnicas
1. **Tamaño del modelo:** GGUF resultante será 3-6 GB (base 8b + LoRA)
2. **Pérdida de conocimiento:** Fine-tuning no es perfecto, puede perder contexto vs. RAG
3. **Overfitting:** Con pocos documentos, riesgo de memorización excesiva

### Mitigaciones
1. **Data augmentation:** Generar múltiples variaciones de preguntas
2. **Regularization:** Dropout y early stopping en LoRA
3. **Evaluation:** Test set para validar no overfitting

### Alternativa Futura: Hybrid Model
- Modelo base fine-tuned + RAG ligero embebido
- Mejores resultados pero más complejo
- Para versión 2.0 del sistema

## 🎯 Próximos Pasos

1. ¿Apruebas este diseño?
2. ¿Empezamos con Sprint 1 (infraestructura)?
3. ¿Algún ajuste o pregunta sobre el diseño?
