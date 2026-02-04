-- Tabla estado_version: Gestión de estados de versiones de proyectos
-- Implementa el flujo de estados: Abierta ↔ Bloqueada → Protegida → Final
--
-- Estados:
--   - Abierta: Permite modificaciones (protected=false)
--   - Bloqueada: Modo solo lectura temporal, REVERSIBLE a Abierta (protected=true)
--   - Protegida: Cliente solicitó entrenamiento, IRREVERSIBLE (protected=true, final_c=true)
--   - Final: Interno confirmó entrenamiento, IRREVERSIBLE (protected=true, final_c=true, final_i=true)
--
-- Flags:
--   - protected: Si true, bloquea TODA la versión y su contenido (cascada)
--   - final_c: Activado por cliente (frontend) al solicitar entrenamiento
--   - final_i: Activado por interno (backoffice) al confirmar entrenamiento
--   - size: Tamaño de la carpeta de versión en bytes

DROP TABLE IF EXISTS estado_version;

CREATE TABLE estado_version (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_organizacion INT NOT NULL,
    id_proyecto INT NOT NULL,
    id_version INT NOT NULL,
    state ENUM('Abierta', 'Bloqueada', 'Protegida', 'Final') NOT NULL DEFAULT 'Abierta',
    protected BOOLEAN NOT NULL DEFAULT FALSE,
    size BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT 'Tamaño en bytes',
    final_c BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Cliente solicita entrenamiento',
    final_i BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Interno confirma entrenamiento',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Restricciones
    UNIQUE KEY unique_version (id_organizacion, id_proyecto, id_version),
    INDEX idx_org_project (id_organizacion, id_proyecto),

    -- Reglas de integridad del flujo de estados
    CONSTRAINT chk_state_protected CHECK (
        (state = 'Abierta' AND protected = FALSE AND final_c = FALSE AND final_i = FALSE) OR
        (state = 'Bloqueada' AND protected = TRUE AND final_c = FALSE AND final_i = FALSE) OR
        (state = 'Protegida' AND protected = TRUE AND final_c = TRUE AND final_i = FALSE) OR
        (state = 'Final' AND protected = TRUE AND final_c = TRUE AND final_i = TRUE)
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insertar estados para todas las versiones existentes
-- Por defecto, todas las versiones nuevas empiezan en estado "Abierta"
INSERT INTO estado_version (id_organizacion, id_proyecto, id_version, state, protected, size, final_c, final_i)
SELECT
    p.id_organizacion,
    v.id_proyecto,
    v.id_version AS id_version,  -- IMPORTANTE: Usar id_version (1,2,3...) no v.id
    'Abierta' AS state,
    FALSE AS protected,
    0 AS size,
    FALSE AS final_c,
    FALSE AS final_i
FROM
    versiones v
    JOIN proyectos p ON v.id_proyecto = p.id
ON DUPLICATE KEY UPDATE
    state = VALUES(state);
