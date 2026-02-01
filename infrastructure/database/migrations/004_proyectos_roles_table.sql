-- ============================================================================
-- Migración: Tabla proyectos_roles para asignación de usuarios a proyectos
-- Base de datos: myllm_projects_db
-- Fecha: 2026-01-31
-- Descripción: 
--   - Tabla para gestionar la relación entre usuarios y proyectos
--   - Permite asignar roles específicos a usuarios en proyectos
--   - Roles: 3=Editor, 4=Lector, 5=Auditor
-- ============================================================================

USE myllm_projects_db;
SET NAMES utf8mb4;

-- ============================================================================
-- 1. Tabla proyectos_roles
-- ============================================================================
-- NOTA: Esta tabla puede ya existir. El script verifica antes de crear.

CREATE TABLE IF NOT EXISTS proyectos_roles (
    id INT NOT NULL AUTO_INCREMENT,
    id_usuario INT NOT NULL COMMENT 'ID del usuario (referencia a myllm_core_db.users)',
    id_proyecto INT NOT NULL COMMENT 'ID del proyecto',
    id_organizacion INT NOT NULL COMMENT 'ID de la organización',
    id_rol INT NOT NULL DEFAULT 4 COMMENT 'Rol del usuario en el proyecto: 3=Editor, 4=Lector, 5=Auditor',
    active TINYINT(1) NOT NULL DEFAULT 1 COMMENT 'Indica si la asignación está activa',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Fecha de creación',
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT 'Fecha de última actualización',
    PRIMARY KEY (id),
    UNIQUE KEY uk_usuario_proyecto (id_usuario, id_proyecto, id_organizacion),
    KEY idx_proyecto (id_proyecto),
    KEY idx_organizacion (id_organizacion),
    KEY idx_usuario (id_usuario),
    KEY idx_active (active),
    CONSTRAINT fk_proyectos_roles_proyecto 
        FOREIGN KEY (id_proyecto) REFERENCES proyectos(id) 
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Asignación de usuarios a proyectos con roles específicos';

SELECT 'Tabla proyectos_roles verificada/creada' AS resultado;

-- ============================================================================
-- 2. Catálogo de roles de proyecto (documentación)
-- ============================================================================
-- Los roles de proyecto corresponden a los roles del sistema (myllm_core_db.roles):
--   id_rol = 3 -> Editor: Puede modificar contenido del proyecto
--   id_rol = 4 -> Lector: Solo lectura del proyecto
--   id_rol = 5 -> Auditor: Acceso limitado para auditoría
--
-- Nota: No se incluyen roles 1 (SuperAdmin) y 2 (Admin Org) porque estos
-- tienen acceso implícito a todos los proyectos de la organización.

-- ============================================================================
-- 3. Trigger para registrar cambios de asignación (opcional)
-- ============================================================================
-- Los cambios ya se registran desde Backend Core usando sp_registrar_cambio_proyecto
-- con tipos de cambio:
--   - "Asignación usuario": Cuando se asigna o reactiva un usuario
--   - "Quitar usuario": Cuando se desactiva la asignación

-- ============================================================================
-- 4. Vista para consultar asignaciones con nombres
-- ============================================================================

CREATE OR REPLACE VIEW view_proyectos_roles_detalle AS
SELECT 
    pr.id,
    pr.id_usuario,
    pr.id_proyecto,
    p.nombre AS proyecto_nombre,
    pr.id_organizacion,
    pr.id_rol,
    CASE pr.id_rol
        WHEN 3 THEN 'Editor'
        WHEN 4 THEN 'Lector'
        WHEN 5 THEN 'Auditor'
        ELSE 'Desconocido'
    END AS rol_nombre,
    pr.active,
    pr.created_at,
    pr.updated_at
FROM proyectos_roles pr
INNER JOIN proyectos p ON pr.id_proyecto = p.id
ORDER BY pr.id_organizacion, p.nombre, pr.id_usuario;

SELECT 'Vista view_proyectos_roles_detalle creada' AS resultado;

-- ============================================================================
-- Verificación final
-- ============================================================================
SELECT '========== RESUMEN DE OBJETOS CREADOS ==========' AS info;

SELECT 'Tabla proyectos_roles:' AS tipo,
    CASE WHEN COUNT(*) > 0 THEN 'Existe' ELSE 'No existe' END AS estado
FROM information_schema.tables 
WHERE table_schema = 'myllm_projects_db' 
AND table_name = 'proyectos_roles';

SELECT 'Vista view_proyectos_roles_detalle:' AS tipo,
    CASE WHEN COUNT(*) > 0 THEN 'Existe' ELSE 'No existe' END AS estado
FROM information_schema.views 
WHERE table_schema = 'myllm_projects_db' 
AND table_name = 'view_proyectos_roles_detalle';
