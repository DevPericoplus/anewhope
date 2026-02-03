-- ============================================================================
-- Tabla: version_states
-- Descripción: Almacena los estados y configuraciones de cada versión de proyecto
-- Base de datos: myllm_projects_db
-- Fecha creación: 2026-02-03
-- ============================================================================

USE myllm_projects_db;

-- Eliminar tabla si existe (solo para desarrollo/testing)
-- DROP TABLE IF EXISTS `version_states`;

CREATE TABLE IF NOT EXISTS `version_states` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'ID autoincremental',
  `id_organizacion` INT NOT NULL COMMENT 'FK a tabla organizaciones (no enforced)',
  `id_proyecto` INT NOT NULL COMMENT 'FK a tabla proyectos',
  `id_version` INT NOT NULL COMMENT 'Número de versión (no string)',
  `state` ENUM('Abierta', 'Bloqueada', 'Protegida', 'Final') NOT NULL DEFAULT 'Abierta' COMMENT 'Estado actual de la versión',
  `protected` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Si TRUE, no se puede editar',
  `size_bytes` BIGINT DEFAULT 0 COMMENT 'Tamaño total de la versión en bytes',
  `final_c` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Cliente solicitó entrenamiento',
  `final_i` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Interno confirmó preparación',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Cuándo se creó el registro',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Última actualización',
  `updated_by_user_id` INT DEFAULT NULL COMMENT 'Usuario que hizo el último cambio',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_version` (`id_proyecto`, `id_version`) COMMENT 'Una versión única por proyecto',
  KEY `idx_org_prj` (`id_organizacion`, `id_proyecto`),
  KEY `idx_state` (`state`),
  KEY `idx_updated_at` (`updated_at` DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Estados y configuraciones de versiones de proyectos';

-- ============================================================================
-- Datos de ejemplo (solo para desarrollo)
-- ============================================================================

-- Insertar estados para versiones existentes (si ya hay versiones en la tabla 'versiones')
INSERT INTO `version_states` 
  (`id_organizacion`, `id_proyecto`, `id_version`, `state`, `protected`, `size_bytes`, `final_c`, `final_i`)
SELECT 
  v.id_organizacion,
  v.id_proyecto,
  v.id_version,
  'Abierta' as state,
  FALSE as protected,
  0 as size_bytes,
  FALSE as final_c,
  FALSE as final_i
FROM versiones v
WHERE NOT EXISTS (
  SELECT 1 FROM version_states vs 
  WHERE vs.id_proyecto = v.id_proyecto 
  AND vs.id_version = v.id_version
)
ON DUPLICATE KEY UPDATE
  `state` = VALUES(`state`);

-- ============================================================================
-- Verificación de la estructura
-- ============================================================================

-- Verificar que se creó correctamente
SHOW CREATE TABLE `version_states`;

-- Contar registros insertados
SELECT COUNT(*) as total_estados FROM `version_states`;

-- Ver ejemplos
SELECT 
  id,
  id_organizacion,
  id_proyecto,
  id_version,
  state,
  protected,
  final_c,
  final_i,
  created_at
FROM `version_states`
ORDER BY id_organizacion, id_proyecto, id_version
LIMIT 10;
