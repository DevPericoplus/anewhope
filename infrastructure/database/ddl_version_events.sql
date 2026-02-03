-- ============================================================================
-- Tabla: version_events
-- Descripción: Registro de eventos y cambios en los estados de versiones
-- Base de datos: myllm_projects_db
-- Fecha creación: 2026-02-03
-- ============================================================================

USE myllm_projects_db;

-- Eliminar tabla si existe (solo para desarrollo/testing)
-- DROP TABLE IF EXISTS `version_events`;

CREATE TABLE IF NOT EXISTS `version_events` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'ID autoincremental',
  `id_organizacion` INT NOT NULL COMMENT 'FK a organizaciones (no enforced)',
  `id_proyecto` INT NOT NULL COMMENT 'FK a proyectos',
  `id_version` INT NOT NULL COMMENT 'Número de versión afectada',
  `evento` VARCHAR(100) NOT NULL COMMENT 'Tipo de evento (ej: ENTRENAMIENTO_SOLICITADO)',
  `mensaje` TEXT COMMENT 'Descripción del evento',
  `user_id` INT NOT NULL COMMENT 'Usuario que generó el evento',
  `user_name` VARCHAR(100) DEFAULT NULL COMMENT 'Nombre del usuario (desnormalizado para auditoría)',
  `old_state` VARCHAR(50) DEFAULT NULL COMMENT 'Estado anterior',
  `new_state` VARCHAR(50) DEFAULT NULL COMMENT 'Estado nuevo',
  `metadata` JSON DEFAULT NULL COMMENT 'Información adicional en formato JSON',
  `timestamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Cuándo ocurrió el evento',
  PRIMARY KEY (`id`),
  KEY `idx_version` (`id_proyecto`, `id_version`),
  KEY `idx_timestamp` (`timestamp` DESC),
  KEY `idx_evento` (`evento`),
  KEY `idx_org_prj` (`id_organizacion`, `id_proyecto`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Auditoría de eventos en versiones de proyectos';

-- ============================================================================
-- Eventos estándar soportados (documentación)
-- ============================================================================

-- EVENTO: VERSION_CREADA
-- Descripción: Se creó una nueva versión
-- old_state: NULL, new_state: "Abierta"

-- EVENTO: VERSION_BLOQUEADA
-- Descripción: Admin bloqueó la versión
-- old_state: "Abierta", new_state: "Bloqueada"

-- EVENTO: VERSION_DESBLOQUEADA
-- Descripción: Admin desbloqueó la versión
-- old_state: "Bloqueada", new_state: "Abierta"

-- EVENTO: ENTRENAMIENTO_SOLICITADO
-- Descripción: Cliente solicitó entrenamiento
-- old_state: "Abierta/Bloqueada", new_state: "Protegida"

-- EVENTO: ENTRENAMIENTO_CONFIRMADO
-- Descripción: Interno confirmó preparación para entrenamiento
-- old_state: "Protegida", new_state: "Final"

-- EVENTO: VERSION_REVERTIDA
-- Descripción: Admin revirtió versión a estado Abierta
-- old_state: "Protegida/Final", new_state: "Abierta"

-- EVENTO: CARPETA_CREADA
-- Descripción: Se creó una carpeta en la versión
-- metadata: {"folder_path": "docs/reports", "size_bytes": 0}

-- EVENTO: ARCHIVO_SUBIDO
-- Descripción: Se subió un archivo
-- metadata: {"file_path": "docs/report.pdf", "size_bytes": 1024000}

-- EVENTO: ARCHIVO_ELIMINADO
-- Descripción: Se eliminó un archivo
-- metadata: {"file_path": "docs/old.pdf", "size_bytes": 512000}

-- ============================================================================
-- Datos de ejemplo (solo para desarrollo)
-- ============================================================================

-- Ejemplo de evento de creación de versión
INSERT INTO `version_events` 
  (`id_organizacion`, `id_proyecto`, `id_version`, `evento`, `mensaje`, `user_id`, `user_name`, `old_state`, `new_state`)
VALUES
  (1, 1, 1, 'VERSION_CREADA', 'Versión v001 creada desde el panel de Proyecciones', 1, 'adminone', NULL, 'Abierta'),
  (1, 1, 2, 'VERSION_CREADA', 'Versión v002 creada desde el panel de Proyecciones', 1, 'adminone', NULL, 'Abierta');

-- ============================================================================
-- Verificación de la estructura
-- ============================================================================

-- Verificar que se creó correctamente
SHOW CREATE TABLE `version_events`;

-- Contar registros
SELECT COUNT(*) as total_eventos FROM `version_events`;

-- Ver últimos eventos
SELECT 
  id,
  id_organizacion,
  id_proyecto,
  id_version,
  evento,
  mensaje,
  user_name,
  old_state,
  new_state,
  timestamp
FROM `version_events`
ORDER BY timestamp DESC
LIMIT 10;

-- ============================================================================
-- Consultas útiles para auditoría
-- ============================================================================

-- Ver historial completo de una versión
-- SELECT * FROM version_events 
-- WHERE id_proyecto = 1 AND id_version = 1 
-- ORDER BY timestamp DESC;

-- Ver eventos de un usuario específico
-- SELECT * FROM version_events 
-- WHERE user_id = 1 
-- ORDER BY timestamp DESC 
-- LIMIT 20;

-- Ver cambios de estado en las últimas 24 horas
-- SELECT * FROM version_events 
-- WHERE evento IN ('VERSION_BLOQUEADA', 'VERSION_DESBLOQUEADA', 'ENTRENAMIENTO_SOLICITADO', 'ENTRENAMIENTO_CONFIRMADO')
-- AND timestamp >= NOW() - INTERVAL 24 HOUR
-- ORDER BY timestamp DESC;
