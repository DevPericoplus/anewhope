-- ============================================================================
-- Migración: 005_proyectos_roles_base_table.sql
-- Descripción: Tabla catálogo de roles base para proyectos
-- Base de datos: myllm_projects_db
-- Fecha: 2026-02-01
-- ============================================================================
-- 
-- IMPORTANTE: Esta tabla es un catálogo maestro de roles que pueden asignarse
-- a usuarios en proyectos. Es información base reutilizable por todas las
-- aplicaciones del sistema.
--
-- Jerarquía de trabajo del usuario:
--   Organización → Proyectos → Versiones → Contenido
--
-- Reglas de visibilidad:
--   - Si el usuario no tiene registro en proyectos_roles para un proyecto: NO VE el proyecto
--   - Si el registro existe pero active=false: NO VE el proyecto
--   - Si el registro existe pero id_rol=0 (Sin asignar): NO VE el proyecto
--   - Solo ve proyectos donde: registro existe AND active=true AND id_rol IN (3,4,5)
--
-- ============================================================================

USE myllm_projects_db;

-- -----------------------------------------------------------------------------
-- Tabla: proyectos_roles_base
-- Catálogo maestro de roles disponibles para asignar a usuarios en proyectos
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS proyectos_roles_base (
    id INT NOT NULL PRIMARY KEY COMMENT 'ID del rol (0=Sin asignar, 3=Editor, 4=Lector, 5=Auditor)',
    nombre_rol VARCHAR(50) NOT NULL COMMENT 'Nombre visible del rol',
    descripcion VARCHAR(255) DEFAULT NULL COMMENT 'Descripción del rol y sus permisos',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Fecha de creación',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Última actualización'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Catálogo maestro de roles para asignar a usuarios en proyectos';

-- -----------------------------------------------------------------------------
-- Datos iniciales del catálogo de roles
-- -----------------------------------------------------------------------------
INSERT INTO proyectos_roles_base (id, nombre_rol, descripcion) VALUES
    (0, 'Sin asignar', 'Usuario sin rol asignado - No puede ver el proyecto'),
    (3, 'Editor', 'Puede crear, modificar y eliminar contenido del proyecto'),
    (4, 'Lector', 'Solo puede ver el contenido del proyecto (lectura)'),
    (5, 'Auditor', 'Acceso limitado para auditoría y revisión')
ON DUPLICATE KEY UPDATE
    nombre_rol = VALUES(nombre_rol),
    descripcion = VALUES(descripcion);

-- -----------------------------------------------------------------------------
-- Vista para consultar roles base (uso en selectores)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_proyectos_roles_base AS
SELECT 
    id,
    nombre_rol,
    descripcion
FROM proyectos_roles_base
ORDER BY 
    CASE id 
        WHEN 0 THEN 1  -- Sin asignar primero
        WHEN 3 THEN 2  -- Editor
        WHEN 4 THEN 3  -- Lector
        WHEN 5 THEN 4  -- Auditor
    END;

-- -----------------------------------------------------------------------------
-- Verificación
-- -----------------------------------------------------------------------------
SELECT 'Tabla proyectos_roles_base creada exitosamente' AS resultado;
SELECT * FROM view_proyectos_roles_base;
