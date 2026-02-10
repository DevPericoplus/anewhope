-- ============================================================================
-- Migración: 011_jobs_templates_system.sql
-- Base de datos: myllm_projects_db
-- Fecha: 2026-02-10
-- Descripción: Crea el sistema completo de plantillas y jobs para gestión
--              de tareas de IA (análisis documental, entrenamiento, evaluación
--              de resultados y generación de modelos LLM).
--              Incluye 12 tablas organizadas en 3 bloques:
--                BLOQUE 1 - Catálogos (tablas 1-8)
--                BLOQUE 2 - Plantillas core (tabla 9)
--                BLOQUE 3 - Ejecución (tablas 10-12)
-- ============================================================================

USE myllm_projects_db;

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- ============================================================================
-- BLOQUE 1: TABLAS CATÁLOGO
-- ============================================================================

-- ============================================================================
-- 1. jobs_tipos — Catálogo de tipos de job
--    Determina en qué página del backoffice se usa cada plantilla.
-- ============================================================================
CREATE TABLE IF NOT EXISTS jobs_tipos (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    clave           VARCHAR(50)  NOT NULL UNIQUE COMMENT 'Clave interna (snake_case)',
    nombre          VARCHAR(100) NOT NULL        COMMENT 'Nombre visible en UI',
    descripcion     VARCHAR(255) DEFAULT NULL    COMMENT 'Descripción del tipo',
    pagina_backoffice VARCHAR(100) DEFAULT NULL  COMMENT 'Página del backoffice donde se usa',
    activo          TINYINT(1)   DEFAULT 1       COMMENT 'Tipo activo/inactivo',
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_jobs_tipos_clave (clave),
    INDEX idx_jobs_tipos_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Catálogo de tipos de job (uno por página del backoffice)';

-- Seed data: 4 tipos de job
INSERT INTO jobs_tipos (clave, nombre, descripcion, pagina_backoffice) VALUES
('analisis_documentacion', 'Análisis de Documentación', 'Jobs de análisis y procesamiento de documentos del cliente', 'Documentacion'),
('entrenamiento',          'Entrenamiento',             'Jobs de entrenamiento y fine-tuning de modelos',              'Entrenamientos'),
('analisis_resultados',    'Análisis de Resultados',    'Jobs de evaluación y análisis de resultados de entrenamiento','Resultados'),
('crear_modelo_llm',       'Crear Modelo LLM',          'Jobs de generación final de modelos LLM personalizados',     'Generacion')
ON DUPLICATE KEY UPDATE
    nombre          = VALUES(nombre),
    descripcion     = VALUES(descripcion),
    pagina_backoffice = VALUES(pagina_backoffice);

-- ============================================================================
-- 2. jobs_estados — Catálogo de estados de un job
-- ============================================================================
CREATE TABLE IF NOT EXISTS jobs_estados (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    clave           VARCHAR(50)  NOT NULL UNIQUE COMMENT 'Clave interna (snake_case)',
    nombre          VARCHAR(100) NOT NULL        COMMENT 'Nombre visible en UI',
    descripcion     VARCHAR(255) DEFAULT NULL    COMMENT 'Descripción del estado',
    color           VARCHAR(20)  DEFAULT NULL    COMMENT 'Color hexadecimal para badges en UI',
    es_final        TINYINT(1)   DEFAULT 0       COMMENT 'Indica si el estado es terminal',
    activo          TINYINT(1)   DEFAULT 1       COMMENT 'Estado activo/inactivo',
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_jobs_estados_clave (clave),
    INDEX idx_jobs_estados_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Catálogo de estados posibles de un job';

-- Seed data: 4 estados
INSERT INTO jobs_estados (clave, nombre, descripcion, color, es_final) VALUES
('programado',    'Programado',    'Job programado pendiente de ejecución',  '#3b82f6', 0),
('en_ejecucion',  'En Ejecución',  'Job ejecutándose actualmente',           '#f59e0b', 0),
('error',         'Error',         'Job finalizado con error',               '#ef4444', 1),
('finalizado',    'Finalizado',    'Job completado exitosamente',            '#22c55e', 1)
ON DUPLICATE KEY UPDATE
    nombre      = VALUES(nombre),
    descripcion = VALUES(descripcion),
    color       = VALUES(color),
    es_final    = VALUES(es_final);

-- ============================================================================
-- 3. jobs_modelos — Modelos LLM disponibles (ollama list)
-- ============================================================================
CREATE TABLE IF NOT EXISTS jobs_modelos (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    nombre          VARCHAR(200) NOT NULL        COMMENT 'Nombre del modelo (ej: llama3:latest)',
    tag             VARCHAR(100) DEFAULT NULL    COMMENT 'Tag o versión del modelo',
    size_bytes      BIGINT       DEFAULT 0       COMMENT 'Tamaño en bytes',
    digest          VARCHAR(200) DEFAULT NULL    COMMENT 'Hash/digest del modelo',
    familia         VARCHAR(100) DEFAULT NULL    COMMENT 'Familia del modelo (llama, mistral, etc.)',
    activo          TINYINT(1)   DEFAULT 1       COMMENT 'Modelo activo/inactivo',
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_jobs_modelos_nombre (nombre),
    INDEX idx_jobs_modelos_familia (familia),
    INDEX idx_jobs_modelos_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Modelos LLM disponibles (sincronizado con ollama list)';

-- Seed data: Modelos Ollama disponibles (sincronizados 2026-02-10)
INSERT IGNORE INTO jobs_modelos (nombre, tag, size_bytes, digest, familia) VALUES
('gemma3:4b',                                              '4b',        3300000000, 'a2af6cc3eb7f', 'gemma'),
('llama-pro:latest',                                       'latest',    4700000000, 'fc5c0d744444', 'llama'),
('qwen2.5:7b',                                             '7b',        4700000000, '845dbda0ea48', 'qwen'),
('kimi-k2.5:cloud',                                        'cloud',     0,          '6d1c3246c608', 'kimi'),
('deepseek-coder:6.7b',                                    '6.7b',      3800000000, 'ce298d984115', 'deepseek-coder'),
('qwen2.5-coder:1.5b-base',                                '1.5b-base', 986000000,  '02e0f2817a89', 'qwen-coder'),
('nomic-embed-text:latest',                                 'latest',    274000000,  '0a109f422b47', 'nomic'),
('llama3.1:8b',                                             '8b',        4900000000, '46e0c10c039e', 'llama'),
('dagbs/qwen2.5-coder-1.5b-instruct-abliterated:latest',   'latest',    1100000000, '54ec0ee8ed41', 'qwen-coder'),
('deepseek-r1:1.5b',                                        '1.5b',      1100000000, 'e0979632db5a', 'deepseek'),
('deepseek-r1:8b',                                          '8b',        5200000000, '6995872bfe4c', 'deepseek');

-- ============================================================================
-- 4. jobs_salidas — Catálogo de tipos de salida
-- ============================================================================
CREATE TABLE IF NOT EXISTS jobs_salidas (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    clave            VARCHAR(50)  NOT NULL UNIQUE COMMENT 'Clave interna (snake_case)',
    nombre           VARCHAR(100) NOT NULL        COMMENT 'Nombre visible en UI',
    descripcion      VARCHAR(255) DEFAULT NULL    COMMENT 'Descripción del tipo de salida',
    campo_referencia VARCHAR(50)  DEFAULT NULL    COMMENT 'Campo clave de referencia (id_job, path_fichero, etc.)',
    activo           TINYINT(1)   DEFAULT 1       COMMENT 'Tipo de salida activo/inactivo',
    created_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_jobs_salidas_clave (clave),
    INDEX idx_jobs_salidas_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Catálogo de tipos de salida que un job puede producir';

-- Seed data: 4 tipos de salida
INSERT INTO jobs_salidas (clave, nombre, descripcion, campo_referencia) VALUES
('nuevo_job',      'Nuevo Job',      'La salida genera un nuevo job hijo',               'id_job'),
('informe',        'Informe',        'La salida es un fichero de informe generado',       'path_fichero'),
('notificacion',   'Notificación',   'La salida genera una notificación/conversación',    'id_conversacion'),
('ticket',         'Ticket',         'La salida genera o actualiza un ticket de soporte', 'id_ticket')
ON DUPLICATE KEY UPDATE
    nombre           = VALUES(nombre),
    descripcion      = VALUES(descripcion),
    campo_referencia = VALUES(campo_referencia);

-- ============================================================================
-- 5. jobs_documentacion — Plantillas Jinja2 para informes
-- ============================================================================
CREATE TABLE IF NOT EXISTS jobs_documentacion (
    id                    INT AUTO_INCREMENT PRIMARY KEY,
    nombre                VARCHAR(200) NOT NULL           COMMENT 'Nombre descriptivo de la plantilla',
    descripcion           TEXT         DEFAULT NULL        COMMENT 'Para qué sirve la plantilla',
    template_path         VARCHAR(500) NOT NULL           COMMENT 'Path completo al fichero .j2',
    template_filename     VARCHAR(200) NOT NULL           COMMENT 'Nombre del fichero .j2',
    formato_salida        VARCHAR(50)  DEFAULT 'markdown' COMMENT 'Formato del output (markdown, html, pdf, etc.)',
    variables_requeridas  JSON         DEFAULT NULL        COMMENT 'Lista de variables que necesita el template',
    activo                TINYINT(1)   DEFAULT 1           COMMENT 'Plantilla activa/inactiva',
    created_at            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_jobs_doc_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Plantillas Jinja2 para generación de informes';

-- ============================================================================
-- 6. jobs_entrenamientos — Configuraciones de parámetros RAG
-- ============================================================================
CREATE TABLE IF NOT EXISTS jobs_entrenamientos (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    nombre              VARCHAR(200)    NOT NULL                        COMMENT 'Nombre de la configuración',
    descripcion         TEXT            DEFAULT NULL                    COMMENT 'Descripción de la configuración',
    -- Parámetros de entrenamiento
    learning_rate       DECIMAL(10,8)   DEFAULT 0.00100000             COMMENT 'Tasa de aprendizaje',
    batch_size          INT             DEFAULT 32                     COMMENT 'Tamaño de lote',
    epochs              INT             DEFAULT 10                     COMMENT 'Número de épocas',
    embedding_dimension INT             DEFAULT 768                    COMMENT 'Dimensión de embeddings',
    sequence_length     INT             DEFAULT 512                    COMMENT 'Longitud de secuencia',
    hidden_units        INT             DEFAULT 256                    COMMENT 'Unidades ocultas',
    dropout_rate        DECIMAL(5,4)    DEFAULT 0.1000                 COMMENT 'Tasa de dropout',
    -- Parámetros ChromaDB / RAG
    collection_name     VARCHAR(200)    DEFAULT NULL                   COMMENT 'Nombre de la colección ChromaDB',
    distance_metric     VARCHAR(50)     DEFAULT 'cosine'               COMMENT 'Métrica de distancia (cosine, euclidean, etc.)',
    persist_directory   VARCHAR(500)    DEFAULT NULL                   COMMENT 'Directorio de persistencia ChromaDB',
    top_k               INT             DEFAULT 5                      COMMENT 'Número de resultados a recuperar',
    chunk_size          INT             DEFAULT 1000                   COMMENT 'Tamaño de fragmento de texto',
    chunk_overlap       INT             DEFAULT 200                    COMMENT 'Solapamiento entre fragmentos',
    -- Parámetros de generación
    temperature         DECIMAL(4,3)    DEFAULT 0.700                  COMMENT 'Temperatura de generación',
    max_tokens          INT             DEFAULT 2048                   COMMENT 'Máximo de tokens a generar',
    -- Parámetros de optimización
    loss_function       VARCHAR(100)    DEFAULT 'cross_entropy'        COMMENT 'Función de pérdida',
    optimizer           VARCHAR(100)    DEFAULT 'adam'                 COMMENT 'Optimizador',
    -- Control
    activo              TINYINT(1)      DEFAULT 1                      COMMENT 'Configuración activa/inactiva',
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_jobs_entren_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Configuraciones de parámetros de entrenamiento RAG';

-- ============================================================================
-- 7. jobs_resultados — Resultados de ejecución de jobs
-- ============================================================================
CREATE TABLE IF NOT EXISTS jobs_resultados (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    id_job           INT             DEFAULT NULL    COMMENT 'FK a jobs (se vincula cuando exista la tabla)',
    id_documentacion INT             DEFAULT NULL    COMMENT 'FK a jobs_documentacion (template Jinja2 usado)',
    tipo_resultado   VARCHAR(100)    NOT NULL        COMMENT 'Tipo: metricas_entrenamiento, informe_generado, evaluacion_modelo, etc.',
    datos_resultado  JSON            NOT NULL        COMMENT 'Datos flexibles en JSON',
    path_fichero     VARCHAR(500)    DEFAULT NULL    COMMENT 'Path al fichero de salida si aplica',
    nombre_fichero   VARCHAR(200)    DEFAULT NULL    COMMENT 'Nombre del fichero generado',
    created_at       TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_resultado_documentacion
        FOREIGN KEY (id_documentacion) REFERENCES jobs_documentacion(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_jobs_result_job (id_job),
    INDEX idx_jobs_result_tipo (tipo_resultado),
    INDEX idx_jobs_result_doc (id_documentacion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Resultados de ejecución de jobs (métricas, informes, evaluaciones)';

-- ============================================================================
-- 8. jobs_generacion — Modelos LLM generados
-- ============================================================================
CREATE TABLE IF NOT EXISTS jobs_generacion (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    id_modelo_base   INT             DEFAULT NULL    COMMENT 'FK a jobs_modelos (modelo base usado)',
    nombre           VARCHAR(200)    NOT NULL        COMMENT 'Nombre del modelo generado',
    path_modelo      VARCHAR(500)    NOT NULL        COMMENT 'Path interno completo al fichero del modelo',
    size_bytes       BIGINT          DEFAULT 0       COMMENT 'Tamaño del modelo en bytes',
    id_organizacion  INT             NOT NULL        COMMENT 'Organización propietaria',
    id_proyecto      INT             NOT NULL        COMMENT 'Proyecto asociado',
    id_version       INT             NOT NULL        COMMENT 'Versión asociada',
    activo           TINYINT(1)      DEFAULT 1       COMMENT 'Modelo generado activo/inactivo',
    created_at       TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_generacion_modelo
        FOREIGN KEY (id_modelo_base) REFERENCES jobs_modelos(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_jobs_gen_modelo (id_modelo_base),
    INDEX idx_jobs_gen_org_proj_ver (id_organizacion, id_proyecto, id_version),
    INDEX idx_jobs_gen_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Modelos LLM generados a partir de entrenamiento';

-- ============================================================================
-- BLOQUE 2: TABLA CORE DE PLANTILLAS
-- ============================================================================

-- ============================================================================
-- 9. jobs_templates — Plantillas de jobs
--    Tabla central. Cada registro define una plantilla con valores por defecto
--    que los jobs heredan al instanciarse.
-- ============================================================================
CREATE TABLE IF NOT EXISTS jobs_templates (
    id                    INT AUTO_INCREMENT PRIMARY KEY,
    nombre                VARCHAR(200)   NOT NULL        COMMENT 'Nombre de la plantilla',
    descripcion           TEXT           DEFAULT NULL    COMMENT 'Descripción detallada',
    id_tipo               INT            NOT NULL        COMMENT 'FK a jobs_tipos',
    es_programable        TINYINT(1)     DEFAULT 0       COMMENT 'Si los jobs de esta plantilla soportan programación',
    activo                TINYINT(1)     DEFAULT 1       COMMENT 'Plantilla activa/inactiva',
    id_estado_inicial     INT            DEFAULT NULL    COMMENT 'FK a jobs_estados (estado inicial por defecto)',
    id_modelo             INT            DEFAULT NULL    COMMENT 'FK a jobs_modelos (modelo LLM por defecto)',
    id_salida             INT            DEFAULT NULL    COMMENT 'FK a jobs_salidas (tipo de salida por defecto)',
    acepta_entrada        TINYINT(1)     DEFAULT 0       COMMENT 'Si puede ser job hijo (recibe datos de padre)',
    permite_hijos         TINYINT(1)     DEFAULT 0       COMMENT 'Si puede ser job padre (envía datos a hijos)',
    configuracion_defecto JSON           DEFAULT NULL    COMMENT 'Configuración por defecto flexible',
    created_at            TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_template_tipo
        FOREIGN KEY (id_tipo) REFERENCES jobs_tipos(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_template_estado
        FOREIGN KEY (id_estado_inicial) REFERENCES jobs_estados(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_template_modelo
        FOREIGN KEY (id_modelo) REFERENCES jobs_modelos(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_template_salida
        FOREIGN KEY (id_salida) REFERENCES jobs_salidas(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_template_tipo (id_tipo),
    INDEX idx_template_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Plantillas de jobs con valores por defecto heredables';

-- ============================================================================
-- BLOQUE 3: TABLAS DE EJECUCIÓN
-- ============================================================================

-- ============================================================================
-- 10. jobs — Instancias de jobs creados desde plantillas
-- ============================================================================
CREATE TABLE IF NOT EXISTS jobs (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    id_template         INT             NOT NULL        COMMENT 'FK a jobs_templates',
    id_organizacion     INT             NOT NULL        COMMENT 'Organización propietaria',
    id_proyecto         INT             NOT NULL        COMMENT 'Proyecto asociado',
    id_version          INT             NOT NULL        COMMENT 'Versión asociada',
    nombre              VARCHAR(200)    NOT NULL        COMMENT 'Heredado de plantilla, modificable',
    descripcion         TEXT            DEFAULT NULL    COMMENT 'Descripción del job',
    id_tipo             INT             NOT NULL        COMMENT 'FK a jobs_tipos',
    id_estado           INT             NOT NULL        COMMENT 'FK a jobs_estados (actualizado en runtime)',
    id_modelo           INT             DEFAULT NULL    COMMENT 'FK a jobs_modelos',
    id_salida           INT             DEFAULT NULL    COMMENT 'FK a jobs_salidas',
    programado_para     DATETIME        DEFAULT NULL    COMMENT 'Fecha/hora de ejecución programada',
    iniciado_en         DATETIME        DEFAULT NULL    COMMENT 'Cuándo empezó a ejecutarse',
    completado_en       DATETIME        DEFAULT NULL    COMMENT 'Cuándo terminó (para calcular duración)',
    error               TEXT            DEFAULT NULL    COMMENT 'Descripción del error si aplica',
    id_cambio           INT             DEFAULT NULL    COMMENT 'FK a cambios (registro en tabla de cambios)',
    id_job_padre        INT             DEFAULT NULL    COMMENT 'FK a jobs (self-reference para jerarquía)',
    datos_entrada       JSON            DEFAULT NULL    COMMENT 'Datos recibidos del padre (flexible)',
    datos_salida        JSON            DEFAULT NULL    COMMENT 'Datos producidos para hijos (flexible)',
    referencia_salida   VARCHAR(500)    DEFAULT NULL    COMMENT 'path, id_conversacion, id_ticket según tipo',
    configuracion       JSON            DEFAULT NULL    COMMENT 'Config del job (heredada de plantilla + modificaciones)',
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_job_template
        FOREIGN KEY (id_template) REFERENCES jobs_templates(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_job_tipo
        FOREIGN KEY (id_tipo) REFERENCES jobs_tipos(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_job_estado
        FOREIGN KEY (id_estado) REFERENCES jobs_estados(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_job_modelo
        FOREIGN KEY (id_modelo) REFERENCES jobs_modelos(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_job_salida
        FOREIGN KEY (id_salida) REFERENCES jobs_salidas(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_job_padre
        FOREIGN KEY (id_job_padre) REFERENCES jobs(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_jobs_org_proj_ver (id_organizacion, id_proyecto, id_version),
    INDEX idx_jobs_padre (id_job_padre),
    INDEX idx_jobs_estado (id_estado),
    INDEX idx_jobs_tipo (id_tipo),
    INDEX idx_jobs_template (id_template),
    INDEX idx_jobs_programado (programado_para)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Instancias de jobs creados desde plantillas';

-- Añadir FK de jobs_resultados.id_job a jobs ahora que la tabla existe
-- (no se pudo crear antes porque jobs no existía)
SET @fk_exists = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA = 'myllm_projects_db'
      AND TABLE_NAME = 'jobs_resultados'
      AND CONSTRAINT_NAME = 'fk_resultado_job'
);
SET @sql = IF(@fk_exists = 0,
    'ALTER TABLE jobs_resultados ADD CONSTRAINT fk_resultado_job FOREIGN KEY (id_job) REFERENCES jobs(id) ON DELETE SET NULL ON UPDATE CASCADE',
    'SELECT "FK fk_resultado_job ya existe"'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============================================================================
-- 11. jobs_eventos — Log cronológico de ejecución
-- ============================================================================
CREATE TABLE IF NOT EXISTS jobs_eventos (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    referencia_compuesta VARCHAR(200)    NOT NULL        COMMENT 'Calculado: ORG{id}-PRJ{id}-VER{id}-JOB{id}',
    id_job               INT             NOT NULL        COMMENT 'FK a jobs',
    id_organizacion      INT             NOT NULL        COMMENT 'Organización',
    id_proyecto          INT             NOT NULL        COMMENT 'Proyecto',
    id_version           INT             NOT NULL        COMMENT 'Versión',
    tipo_evento          VARCHAR(100)    NOT NULL        COMMENT 'inicio, progreso, error, fin, etc.',
    descripcion          TEXT            DEFAULT NULL    COMMENT 'Descripción del evento',
    datos_evento         JSON            DEFAULT NULL    COMMENT 'Datos adicionales flexibles',
    fecha_evento         TIMESTAMP       DEFAULT CURRENT_TIMESTAMP COMMENT 'Fecha y hora del evento',
    CONSTRAINT fk_evento_job
        FOREIGN KEY (id_job) REFERENCES jobs(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_eventos_job (id_job),
    INDEX idx_eventos_referencia (referencia_compuesta),
    INDEX idx_eventos_fecha (fecha_evento DESC),
    INDEX idx_eventos_tipo (tipo_evento)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Log cronológico de eventos de ejecución de jobs';

-- ============================================================================
-- 12. jobs_entradas — Transferencia de datos padre a hijo
-- ============================================================================
CREATE TABLE IF NOT EXISTS jobs_entradas (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    id_job_padre    INT             NOT NULL        COMMENT 'FK a jobs (job padre)',
    id_job_hijo     INT             NOT NULL        COMMENT 'FK a jobs (job hijo)',
    id_tipo_salida  INT             DEFAULT NULL    COMMENT 'FK a jobs_salidas (qué tipo de dato se transfiere)',
    id_resultado    INT             DEFAULT NULL    COMMENT 'FK a jobs_resultados (si se pasa referencia a resultado)',
    datos           JSON            DEFAULT NULL    COMMENT 'Payload flexible con lo que el padre pasa al hijo',
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_entrada_padre
        FOREIGN KEY (id_job_padre) REFERENCES jobs(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_entrada_hijo
        FOREIGN KEY (id_job_hijo) REFERENCES jobs(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_entrada_tipo_salida
        FOREIGN KEY (id_tipo_salida) REFERENCES jobs_salidas(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_entrada_resultado
        FOREIGN KEY (id_resultado) REFERENCES jobs_resultados(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_entradas_padre (id_job_padre),
    INDEX idx_entradas_hijo (id_job_hijo),
    INDEX idx_entradas_resultado (id_resultado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Transferencia de datos entre jobs padre e hijo';

-- ============================================================================
-- PERMISOS DE BASE DE DATOS
-- ============================================================================

-- Permisos para myllm_writer (lectura y escritura)
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_tipos          TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_estados        TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_modelos        TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_salidas        TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_documentacion  TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_entrenamientos TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_resultados     TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_generacion     TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_templates      TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs                TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_eventos        TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.jobs_entradas       TO 'myllm_writer'@'localhost';

-- Permisos para myllm_reader (solo lectura)
GRANT SELECT ON myllm_projects_db.jobs_tipos          TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_estados        TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_modelos        TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_salidas        TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_documentacion  TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_entrenamientos TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_resultados     TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_generacion     TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_templates      TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs                TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_eventos        TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.jobs_entradas       TO 'myllm_reader'@'localhost';

FLUSH PRIVILEGES;

-- ============================================================================
-- VISTAS ÚTILES
-- ============================================================================

-- Vista: Plantillas con nombres de catálogos resueltos
CREATE OR REPLACE VIEW view_jobs_templates AS
SELECT
    jt.id,
    jt.nombre,
    jt.descripcion,
    jt.id_tipo,
    jtip.clave        AS tipo_clave,
    jtip.nombre       AS tipo_nombre,
    jtip.pagina_backoffice,
    jt.es_programable,
    jt.activo,
    jt.id_estado_inicial,
    jest.clave        AS estado_inicial_clave,
    jest.nombre       AS estado_inicial_nombre,
    jt.id_modelo,
    jmod.nombre       AS modelo_nombre,
    jt.id_salida,
    jsal.clave        AS salida_clave,
    jsal.nombre       AS salida_nombre,
    jt.acepta_entrada,
    jt.permite_hijos,
    jt.configuracion_defecto,
    jt.created_at,
    jt.updated_at
FROM jobs_templates jt
INNER JOIN jobs_tipos jtip   ON jt.id_tipo = jtip.id
LEFT  JOIN jobs_estados jest ON jt.id_estado_inicial = jest.id
LEFT  JOIN jobs_modelos jmod ON jt.id_modelo = jmod.id
LEFT  JOIN jobs_salidas jsal ON jt.id_salida = jsal.id;

-- Vista: Jobs con información completa
CREATE OR REPLACE VIEW view_jobs_completo AS
SELECT
    j.id,
    j.nombre,
    j.descripcion,
    j.id_organizacion,
    j.id_proyecto,
    j.id_version,
    j.id_template,
    jt.nombre         AS template_nombre,
    j.id_tipo,
    jtip.clave        AS tipo_clave,
    jtip.nombre       AS tipo_nombre,
    j.id_estado,
    jest.clave        AS estado_clave,
    jest.nombre       AS estado_nombre,
    jest.color        AS estado_color,
    jest.es_final     AS estado_es_final,
    j.id_modelo,
    jmod.nombre       AS modelo_nombre,
    j.id_salida,
    jsal.clave        AS salida_clave,
    jsal.nombre       AS salida_nombre,
    j.programado_para,
    j.iniciado_en,
    j.completado_en,
    j.error,
    j.id_job_padre,
    j.referencia_salida,
    j.configuracion,
    j.created_at,
    j.updated_at
FROM jobs j
INNER JOIN jobs_templates jt ON j.id_template = jt.id
INNER JOIN jobs_tipos jtip   ON j.id_tipo = jtip.id
INNER JOIN jobs_estados jest ON j.id_estado = jest.id
LEFT  JOIN jobs_modelos jmod ON j.id_modelo = jmod.id
LEFT  JOIN jobs_salidas jsal ON j.id_salida = jsal.id;

-- ============================================================================
-- VERIFICACIÓN FINAL
-- ============================================================================
SELECT '✅ Migración 011 completada: Sistema de Plantillas y Jobs' AS resultado;
SELECT 'Tablas creadas: jobs_tipos, jobs_estados, jobs_modelos, jobs_salidas, jobs_documentacion, jobs_entrenamientos, jobs_resultados, jobs_generacion, jobs_templates, jobs, jobs_eventos, jobs_entradas' AS tablas;
SELECT COUNT(*) AS total_tipos    FROM jobs_tipos;
SELECT COUNT(*) AS total_estados  FROM jobs_estados;
SELECT COUNT(*) AS total_modelos  FROM jobs_modelos;
SELECT COUNT(*) AS total_salidas  FROM jobs_salidas;
