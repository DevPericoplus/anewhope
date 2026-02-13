# Sprint 1: Infraestructura Base - COMPLETADO ✅

## Fecha: 2026-02-13

## Objetivos Completados

### 1. ✅ Configuración de Entorno
- **`.envglobal`**: Variable `training_mode` agregada
- **`env.yaml` (4 entornos)**:
  - `macbook`: `training_mode: simulation`
  - `dev`: `training_mode: test`
  - `pre`: `training_mode: production`
  - `pro`: `training_mode: production`

### 2. ✅ Migraciones de Base de Datos
**Archivo**: `infrastructure/database/migrations/015_autonomous_training.sql`

**Tablas creadas** (en `myllm_projects_db`):

#### `entrenamientos_autonomos`
- Datos extendidos para entrenamientos con fine-tuning
- Campos: training_mode, dataset_path, lora_path, gguf_path, package_path
- Relación 1:1 con `entrenamientos`

#### `subfases_autonomas`
- Catálogo de 20 nuevas subfases (6.1 a 9.5)
- Fase 6: Generación Dataset (5 subfases)
- Fase 7: Preparación LoRA (4 subfases)
- Fase 8: Entrenamiento LoRA (6 subfases)
- Fase 9: Exportación GGUF (5 subfases)

#### `evoluciones_autonomas`
- Progreso detallado de subfases 6.x-9.x
- Similar a `evoluciones_entrenamientos` pero para fases extendidas
- Almacena métricas, tiempos, errores por subfase

**Verificación**:
```bash
# Total subfases insertadas: 20
# Rango de orden: 17-36 (después de las 16 subfases RAG existentes)
```

### 3. ✅ Estructura de Carpetas en 4_trainer

```
4_trainer/
├── lib/
│   └── llama.cpp/          # En proceso de clonado desde GitHub
├── templates/
│   └── models/             # Para almacenar modelos base HuggingFace
└── autonomous_training/
    ├── datasets/           # Datasets JSONL generados
    ├── lora_adapters/      # Adaptadores LoRA entrenados
    ├── gguf_models/        # Modelos GGUF exportados
    ├── packages/           # ZIPs para distribución a clientes
    └── logs/               # Logs de fine-tuning y exportación
```

## Especificaciones Técnicas

### Plataforma de Desarrollo
- **Mac Intel i7** (16GB RAM)
- **macOS** (actual)
- **Oracle Linux 10** (dev/pre/pro) con CUDA

### Dependencias Descargadas
- **llama.cpp**: ✅ Clonado exitosamente en `4_trainer/lib/llama.cpp/`
  - 2276 archivos descargados
  - Scripts disponibles:
    - `convert_hf_to_gguf.py` (HuggingFace → GGUF)
    - `convert_lora_to_gguf.py` (LoRA → GGUF)
  - Soporte para cuantización (q8_0, q4_k_m, etc.)

### Pendientes Sprint 2

#### Dependencias a Instalar
```bash
# Para Intel Mac (sin GPU integrada Apple)
pip install torch torchvision torchaudio  # CPU version

# Para fine-tuning (elegir uno):
# Opción A: Unsloth (Mac compatible)
pip install unsloth

# Opción B: PEFT + Transformers (más genérico)
pip install transformers peft accelerate bitsandbytes

# Para generación de datasets
pip install datasets jinja2

# Para conversión GGUF (desde llama.cpp)
cd lib/llama.cpp
pip install -r requirements.txt
```

#### Archivos a Crear
1. `autonomous_training/dataset_generator.py`
   - Generar Q&A desde chunks
   - Templates + generación con Ollama

2. `autonomous_training/lora_trainer.py`
   - Wrapper de Unsloth o PEFT
   - Callbacks para actualizar BD

3. `autonomous_training/gguf_exporter.py`
   - Merge LoRA + base model
   - Conversión a GGUF con llama.cpp

4. `autonomous_training/package_builder.py`
   - Crear Modelfile
   - Generar README
   - Empaquetar ZIP

## Tiempo Invertido
- Configuración entornos: 15 min
- Migraciones BD: 30 min
- Estructura carpetas: 10 min
- Descarga llama.cpp: En progreso (5-10 min)
- **Total Sprint 1**: ~1 hora

## Próximo Sprint

### Sprint 2: Generación de Dataset (2-3 días)
**Objetivo**: Implementar la Fase 6 completa (subfases 6.1-6.5)

**Tareas**:
1. Recuperar chunks desde ChromaDB/BD
2. Crear templates de preguntas (plantillas predefinidas)
3. Generar Q&A automático con Ollama
4. Formatear a JSONL para LoRA
5. Actualizar `evoluciones_autonomas` en BD

**Entregable**: Dataset JSONL listo para fine-tuning

## Notas Importantes

### Compatibilidad con Sistema Actual
- ✅ No se modificaron tablas existentes
- ✅ Sistema RAG (fases 1-5) sigue funcionando igual
- ✅ Nuevas tablas separadas para extensión autónoma

### Modo Simulation (Desarrollo)
- Solo ejecuta fases 1-5 (RAG)
- No genera dataset ni fine-tuning
- Tiempo: 1-3 minutos
- Ideal para desarrollo sin GPU

### Modo Test (Dev con GPU)
- Ejecuta fases 1-9 completas
- Dataset reducido (~100 ejemplos)
- LoRA ligero (rank=8, 1-2 epochs)
- Tiempo: ~30 minutos

### Modo Production (Pre/Pro con GPU CUDA)
- Ejecuta fases 1-9 completas
- Dataset completo (todos los chunks)
- LoRA optimizado (rank=16-32, 3-5 epochs)
- Tiempo: 1-4 horas

## Referencias
- Diseño completo: `/TRAINING_AUTONOMOUS_DESIGN.md`
- Migración BD: `infrastructure/database/migrations/015_autonomous_training.sql`
- Configuración: `infrastructure/environments/{env}/env.yaml`
