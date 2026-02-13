-- ===========================================================================
-- Migración 015: Sistema de Entrenamiento Autónomo con Fine-Tuning LoRA
-- ===========================================================================
-- Fecha: 2026-02-12
-- Descripción: Extensión del sistema de entrenamiento para generar modelos
--              autónomos en formato GGUF mediante fine-tuning con LoRA.
--
-- IMPORTANTE: Esta migración NO modifica tablas existentes, crea nuevas
--             tablas para mantener la compatibilidad con el sistema RAG actual.
-- ===========================================================================

USE myllm_projects_db;

-- ---------------------------------------------------------------------------
-- Tabla: entrenamientos_autonomos
-- ---------------------------------------------------------------------------
-- Almacena información adicional para entrenamientos en modo test/production
-- que incluyen fine-tuning LoRA y exportación a GGUF.
--
-- Relación: 1:1 con tabla `entrenamientos` mediante id_entrenamiento
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS entrenamientos_autonomos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_entrenamiento INT NOT NULL UNIQUE COMMENT 'FK a entrenamientos.id',

    -- Modo de entrenamiento (desde .envglobal)
    training_mode ENUM('simulation', 'test', 'production') NOT NULL DEFAULT 'simulation'
        COMMENT 'Modo: simulation (solo RAG), test (LoRA ligero), production (LoRA completo)',

    -- Dataset generado para fine-tuning
    dataset_path VARCHAR(500) COMMENT 'Ruta del dataset JSONL generado',
    dataset_size INT DEFAULT 0 COMMENT 'Número de ejemplos en el dataset',
    dataset_generated_at DATETIME COMMENT 'Timestamp de generación del dataset',

    -- Fine-tuning LoRA
    lora_config JSON COMMENT 'Configuración LoRA (rank, alpha, epochs, etc.)',
    lora_adapters_path VARCHAR(500) COMMENT 'Ruta de los adaptadores LoRA entrenados',
    lora_training_time_seconds INT COMMENT 'Tiempo de entrenamiento LoRA en segundos',
    lora_final_loss DECIMAL(10, 6) COMMENT 'Loss final del entrenamiento',
    lora_completed_at DATETIME COMMENT 'Timestamp de finalización LoRA',

    -- Modelo autónomo GGUF
    gguf_path VARCHAR(500) COMMENT 'Ruta del archivo GGUF generado',
    gguf_size_mb DECIMAL(10, 2) COMMENT 'Tamaño del GGUF en MB',
    gguf_quantization VARCHAR(20) DEFAULT 'q8_0' COMMENT 'Tipo de cuantización (q8_0, q4_k_m, etc.)',
    gguf_generated_at DATETIME COMMENT 'Timestamp de generación del GGUF',

    -- Paquete entregable para cliente
    package_path VARCHAR(500) COMMENT 'Ruta del ZIP con GGUF + Modelfile + README',
    package_size_mb DECIMAL(10, 2) COMMENT 'Tamaño del paquete en MB',
    package_generated_at DATETIME COMMENT 'Timestamp de generación del paquete',

    -- Metadatos
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Índices
    INDEX idx_id_entrenamiento (id_entrenamiento),
    INDEX idx_training_mode (training_mode),
    INDEX idx_created_at (created_at),

    -- Foreign Key
    CONSTRAINT fk_entrenamientos_autonomos_entrenamiento
        FOREIGN KEY (id_entrenamiento)
        REFERENCES entrenamientos(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Datos extendidos para entrenamientos con fine-tuning LoRA y exportación GGUF';

-- ---------------------------------------------------------------------------
-- Tabla: subfases_autonomas
-- ---------------------------------------------------------------------------
-- Catálogo de las 20 nuevas subfases (6.1 a 9.5) para el proceso de
-- fine-tuning y exportación a GGUF.
--
-- Las subfases 1.x a 5.x ya existen en `evoluciones_entrenamientos`.
-- Estas se añaden para completar el proceso autónomo.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subfases_autonomas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    phase_key VARCHAR(10) NOT NULL COMMENT 'Clave de fase (6, 7, 8, 9)',
    phase_name VARCHAR(100) NOT NULL COMMENT 'Nombre de la fase',
    subfase_key VARCHAR(10) NOT NULL UNIQUE COMMENT 'Clave subfase (6.1, 6.2, ..., 9.5)',
    subfase_name VARCHAR(200) NOT NULL COMMENT 'Nombre descriptivo de la subfase',
    subfase_order INT NOT NULL COMMENT 'Orden de ejecución (17-36)',
    estimated_duration_seconds INT COMMENT 'Duración estimada en segundos',
    description TEXT COMMENT 'Descripción detallada de lo que hace la subfase',

    -- Índices
    INDEX idx_phase_key (phase_key),
    INDEX idx_subfase_order (subfase_order),
    UNIQUE INDEX idx_subfase_key (subfase_key)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Catálogo de subfases para entrenamiento autónomo (fases 6-9)';

-- ---------------------------------------------------------------------------
-- Insertar subfases de la Fase 6: Generación de Dataset
-- ---------------------------------------------------------------------------
INSERT INTO subfases_autonomas (phase_key, phase_name, subfase_key, subfase_name, subfase_order, estimated_duration_seconds, description) VALUES
('6', 'Generación Dataset', '6.1', 'Analizar chunks disponibles', 17, 5, 'Cargar y analizar los chunks generados en la fase 3 desde ChromaDB'),
('6', 'Generación Dataset', '6.2', 'Generar plantillas de preguntas', 18, 30, 'Crear preguntas estructuradas usando templates predefinidos basados en los chunks'),
('6', 'Generación Dataset', '6.3', 'Generar Q&A con LLM', 19, 120, 'Usar Ollama (deepseek-r1) para generar preguntas adicionales automáticamente'),
('6', 'Generación Dataset', '6.4', 'Validar y formatear dataset', 20, 15, 'Validar formato JSONL y estructura de ejemplos para fine-tuning'),
('6', 'Generación Dataset', '6.5', 'Guardar dataset', 21, 5, 'Persistir dataset en formato JSONL en disco');

-- ---------------------------------------------------------------------------
-- Insertar subfases de la Fase 7: Preparación Fine-tuning
-- ---------------------------------------------------------------------------
INSERT INTO subfases_autonomas (phase_key, phase_name, subfase_key, subfase_name, subfase_order, estimated_duration_seconds, description) VALUES
('7', 'Preparación LoRA', '7.1', 'Verificar dependencias', 22, 10, 'Comprobar que llama.cpp, MLX y otras dependencias están instaladas'),
('7', 'Preparación LoRA', '7.2', 'Obtener modelo base', 23, 180, 'Descargar modelo base en formato HuggingFace si no está disponible localmente'),
('7', 'Preparación LoRA', '7.3', 'Configurar parámetros LoRA', 24, 5, 'Establecer rank, alpha, dropout según training_mode (test vs production)'),
('7', 'Preparación LoRA', '7.4', 'Preparar entorno de entrenamiento', 25, 10, 'Inicializar directorios y configurar logs de entrenamiento');

-- ---------------------------------------------------------------------------
-- Insertar subfases de la Fase 8: Entrenamiento LoRA
-- ---------------------------------------------------------------------------
INSERT INTO subfases_autonomas (phase_key, phase_name, subfase_key, subfase_name, subfase_order, estimated_duration_seconds, description) VALUES
('8', 'Entrenamiento LoRA', '8.1', 'Inicializar trainer', 26, 30, 'Cargar modelo base, dataset y configuración en el trainer LoRA'),
('8', 'Entrenamiento LoRA', '8.2', 'Entrenamiento en progreso', 27, 1200, 'Proceso de fine-tuning con actualización periódica de métricas (loss, learning rate)'),
('8', 'Entrenamiento LoRA', '8.3', 'Finalizar entrenamiento', 28, 20, 'Completar última epoch y guardar checkpoints finales'),
('8', 'Entrenamiento LoRA', '8.4', 'Evaluar modelo', 29, 60, 'Ejecutar evaluación en dataset de validación para medir calidad'),
('8', 'Entrenamiento LoRA', '8.5', 'Guardar adaptadores LoRA', 30, 15, 'Persistir adaptadores LoRA (adapter_config.json, adapter_model.safetensors)'),
('8', 'Entrenamiento LoRA', '8.6', 'Validar resultados', 31, 10, 'Verificar que el fine-tuning mejoró las métricas vs baseline');

-- ---------------------------------------------------------------------------
-- Insertar subfases de la Fase 9: Exportación GGUF
-- ---------------------------------------------------------------------------
INSERT INTO subfases_autonomas (phase_key, phase_name, subfase_key, subfase_name, subfase_order, estimated_duration_seconds, description) VALUES
('9', 'Exportación GGUF', '9.1', 'Merge LoRA con modelo base', 32, 120, 'Combinar adaptadores LoRA con el modelo base para crear modelo unificado'),
('9', 'Exportación GGUF', '9.2', 'Convertir a GGUF', 33, 180, 'Usar llama.cpp para convertir el modelo HuggingFace a formato GGUF'),
('9', 'Exportación GGUF', '9.3', 'Crear Modelfile para cliente', 34, 5, 'Generar Modelfile con FROM ./modelo.gguf y configuración SYSTEM'),
('9', 'Exportación GGUF', '9.4', 'Generar README', 35, 5, 'Crear instrucciones para el cliente (ollama create, ollama run)'),
('9', 'Exportación GGUF', '9.5', 'Empaquetar entregable', 36, 30, 'Crear ZIP con GGUF + Modelfile + README para distribución');

-- ---------------------------------------------------------------------------
-- Tabla: evoluciones_autonomas
-- ---------------------------------------------------------------------------
-- Progreso detallado de las subfases 6.x a 9.x para cada entrenamiento
-- autónomo. Similar a `evoluciones_entrenamientos` pero para las fases
-- extendidas.
--
-- Relación: N:1 con tabla `entrenamientos_autonomos`
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evoluciones_autonomas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_entrenamiento INT NOT NULL COMMENT 'FK a entrenamientos.id',

    -- Subfase ejecutada
    phase_key VARCHAR(10) NOT NULL COMMENT 'Fase (6, 7, 8, 9)',
    subfase_key VARCHAR(10) NOT NULL COMMENT 'Subfase (6.1, 6.2, ..., 9.5)',
    subfase_name VARCHAR(200) NOT NULL COMMENT 'Nombre de la subfase',

    -- Estado y tiempos
    status ENUM('pending', 'in_progress', 'completed', 'failed') NOT NULL DEFAULT 'pending',
    started_at DATETIME COMMENT 'Timestamp de inicio',
    completed_at DATETIME COMMENT 'Timestamp de finalización',
    duracion_segundos INT COMMENT 'Duración real en segundos',

    -- Métricas y logs
    metrics JSON COMMENT 'Métricas específicas (loss, accuracy, etc.)',
    error_message TEXT COMMENT 'Mensaje de error si status = failed',

    -- Metadatos
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Índices
    INDEX idx_id_entrenamiento (id_entrenamiento),
    INDEX idx_phase_key (phase_key),
    INDEX idx_subfase_key (subfase_key),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),

    -- Foreign Key
    CONSTRAINT fk_evoluciones_autonomas_entrenamiento
        FOREIGN KEY (id_entrenamiento)
        REFERENCES entrenamientos(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    -- Constraint único: una subfase por entrenamiento
    UNIQUE INDEX idx_unique_subfase_per_entrenamiento (id_entrenamiento, subfase_key)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Progreso detallado de subfases autónomas (fases 6-9) por entrenamiento';

-- ===========================================================================
-- Fin de la migración 015
-- ===========================================================================
