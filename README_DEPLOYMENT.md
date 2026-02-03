# Despliegue

Guía rápida de despliegue y verificación para entornos locales o servidores.

## Verificación de carga en MariaDB

Ejecuta el script de inicialización y revisa los conteos por tabla:

```bash
/usr/local/opt/mariadb@10.6/bin/mysql -u root -p'RootP@ssw0rd2026' --database=myllm_core_db --init-command="SET @users_json_path='/ruta/a/users.json'; SET @permissions_json_path='/ruta/a/basic_permissions.json'; SET @low_level_permissions_json_path='/ruta/a/low_level_permisions.json'; SET @roles_json_path='/ruta/a/roles.json'; SET @organizations_json_path='/ruta/a/organizations.json'; SET @manage_roles_json_path='/ruta/a/manage_roles_by_org.json'; SET @sessions_json_path='/ruta/a/sessions.json';" < /ruta/a/init_myllm_core_db.sql
```

Bloque de verificación (incluido en el script):

```sql
SELECT 'permissions' AS table_name, COUNT(*) AS total FROM permissions
UNION ALL
SELECT 'basic_permissions', COUNT(*) FROM basic_permissions
UNION ALL
SELECT 'low_level_permissions', COUNT(*) FROM low_level_permissions
UNION ALL
SELECT 'identity_types', COUNT(*) FROM identity_types
UNION ALL
SELECT 'identity_type_permissions', COUNT(*) FROM identity_type_permissions
UNION ALL
SELECT 'organizations', COUNT(*) FROM organizations
UNION ALL
SELECT 'users', COUNT(*) FROM users
UNION ALL
SELECT 'user_contact_info', COUNT(*) FROM user_contact_info
UNION ALL
SELECT 'user_billing_info', COUNT(*) FROM user_billing_info
UNION ALL
SELECT 'user_organization_management', COUNT(*) FROM user_organization_management
UNION ALL
SELECT 'sessions', COUNT(*) FROM sessions
UNION ALL
SELECT 'auth_logs', COUNT(*) FROM auth_logs;
```

## Estructura de base de datos (referencia viva)

Este apartado documenta las tablas principales del core. Se irá actualizando
cuando se incorporen nuevas funcionalidades o entidades.
Cada cambio en la estructura debe reflejarse aquí (nuevas tablas, columnas
o relaciones), junto con la fecha y una nota breve del motivo.

**Nota:** La base `myllm_projects_db` no tiene espejo en JSON. Todas las operaciones
deben consultar MariaDB directamente, sin fallback a mocks.

### Tablas actuales

- `permissions`: catálogo de permisos básicos.
- `basic_permissions`: espejo del JSON de permisos básicos para sincronización.
- `low_level_permissions`: permisos de bajo nivel asociados 1 a 1 con `permissions`.
- `identity_types`: tipos de identidad y roles.
- `identity_type_permissions`: relación **1 a 1** entre tipos de identidad y permisos (claves únicas por `identity_type_id` y `permission_id`).
- `organizations`: organizaciones registradas.
- `users`: usuarios registrados.
- `user_contact_info`: información de contacto por usuario.
- `user_billing_info`: información de facturación por usuario.
- `user_organization_management`: relación usuario-organización y estado.
- `sessions`: sesiones activas/inactivas para auditoría y seguridad.
- `auth_logs`: auditoría de login/logout y eventos de autenticación.

### Base de datos de proyectos (`myllm_projects_db`)

Relación esperada: `organizaciones` → `proyectos` → `versiones` → `cambios`.
Relación de flujos: `flujos` ← `proyectos` (cada proyecto tiene un paso actual en el flujo).

- `organizaciones`: organizaciones (PK `organization_id`).
- `proyectos`: proyectos por organización (FK `id_organizacion` → `organizaciones.organization_id`, FK `id_flujo` → `flujos.id_flujo`).
- `versiones`: versiones por proyecto (FK `id_proyecto` → `proyectos.id`, FK `id_organizacion` → `organizaciones.organization_id`).
  - Único por proyecto: `id_proyecto` + `id_version`.
- `cambios`: cambios por versión (FK `id_version` → `versiones.id`, FK `id_proyecto` → `proyectos.id`, FK `id_organizacion` → `organizaciones.organization_id`).
- `flujos`: catálogo de pasos del flujo de trabajo para generación de modelos LLM.
- `estado`: estado booleano de cada paso del flujo por versión.
- **`version_states`** ✨ *Nuevo 2026-02-03*: Estados y configuraciones de versiones (Abierta, Bloqueada, Protegida, Final). Almacena flags `final_c` (cliente solicitó entrenamiento) y `final_i` (interno confirmó). UK: `id_proyecto` + `id_version`.
- **`version_events`** ✨ *Nuevo 2026-02-03*: Auditoría de eventos de cambios de estado en versiones. Registra transiciones, operaciones de archivos y eventos de entrenamiento. Incluye metadata JSON para información adicional.

#### Tabla `flujos` (catálogo de pasos del flujo de trabajo)

| id_flujo | clave | nombre | emoji | orden |
|----------|-------|--------|-------|-------|
| 1 | propuesta_cliente | Propuesta Cliente | 📝 | 1 |
| 2 | revision_interna | Revisión Interna | 🔍 | 2 |
| 3 | propuesta_mejoras | Propuesta de Mejoras | ⚙️ | 3 |
| 4 | aceptacion_cliente | Aceptación Cliente | ✅ | 4 |
| 5 | aceptacion_interna | Aceptación Interna | ✅ | 5 |
| 6 | entrenamiento_inicial | Entrenamiento Inicial | 🎓 | 6 |
| 7 | evaluacion_entrenamiento | Evaluación Entrenamiento | 📊 | 7 |
| 8 | reentrenamiento | Reentrenamiento | 🔄 | 8 |
| 9 | optimizacion | Optimización | ⚡ | 9 |
| 10 | aprobacion_calidad | Aprobación Calidad | ✅ | 10 |
| 11 | generacion_llm | Generación del Modelo LLM | 🤖 | 11 |
| 12 | notificacion_descarga | Notificación de Descarga | 🔔 | 12 |

**Vista útil:** `view_proyectos_flujo` - muestra proyectos con su paso actual del flujo.

**Migración:** `infrastructure/database/migrations/001_create_flujos_table.sql`

#### Sistema de auditoría de cambios de flujo

El sistema registra automáticamente cada cambio de flujo en proyectos mediante triggers.

**Tablas:**
- `proyecto_flujo_historico`: Registro de cada transición entre pasos del flujo.
- `sesion_contexto`: Contexto temporal de sesión para pasar datos a triggers.

**Triggers:**
- `tr_proyecto_flujo_cambio`: Se dispara en UPDATE de `proyectos.id_flujo`.
- `tr_proyecto_flujo_inicial`: Se dispara en INSERT de proyecto con `id_flujo`.

**Vistas:**
- `view_proyecto_flujo_historico`: Histórico enriquecido con nombres de flujos.
- `view_flujo_metricas`: Métricas de tiempo promedio por cada paso.

**Procedimientos almacenados:**
- `sp_set_sesion_contexto(usuario, ip, app, motivo)`: Establece contexto antes de cambios.
- `sp_clear_sesion_contexto()`: Limpia contexto después de cambios.
- `sp_avanzar_proyecto_flujo(proyecto, usuario, motivo, ip, app)`: Avanza proyecto al siguiente paso.

**Ejemplo de uso desde aplicación:**
```sql
-- Antes de hacer cambios
CALL sp_set_sesion_contexto(123, '192.168.1.100', 'frontend', 'Aprobación del cliente');

-- Actualizar flujo del proyecto
UPDATE proyectos SET id_flujo = 4 WHERE id = 1;

-- O usar el procedimiento de avance
CALL sp_avanzar_proyecto_flujo(1, 123, 'Completada revisión interna', '192.168.1.100', 'backoffice');
```

**Migración:** `infrastructure/database/migrations/002_flujo_historico_y_trigger.sql`

## Almacenamiento de ficheros (fmanagement)

La API `fmanagement` opera sobre un volumen dedicado en el servidor backend:
`/data/files/external`.
La estructura esperada es:

```
/data/files/external/
  ORG0001/
    PRJ00001/
      v001/
      v002/
```
