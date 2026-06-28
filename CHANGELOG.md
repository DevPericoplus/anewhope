# Changelog

## [2026-06-29] - Corrección de bugs críticos: Organizaciones y Versiones

### Bug 1: Nuevas organizaciones no aparecen en selectores

**Síntoma:** Las organizaciones creadas desde el panel de backoffice no aparecían
en los selectores de organización para usuarios no-SuperAdmin.

**Causa raíz:**
1. `store_organizations()` en `storage_adapter.py` solo escribía en JSON local,
   sin persistir en MariaDB. Los selectores en modo `db_only` leen directamente
   de la tabla `myllm_core_db.organizations`.
2. `routermiddleware.create_organization()` no delegaba la escritura al broker
   en modo `db_only`, quedando los datos solo en el JSON local.
3. Al crear una organización, no se generaba automáticamente la asignación en
   `asignaciones_organizaciones_internas`, por lo que usuarios no-SuperAdmin
   nunca podían ver la organización.

**Correcciones aplicadas:**
- `src/apps/3_backend/4_infrastructure/persistence/storage_adapter.py`:
  - `store_organizations()` ahora sincroniza con MariaDB (INSERT ... ON DUPLICATE
    KEY UPDATE) cuando `storage_mode=db_only`.
  - Nueva función `_sync_organizations_to_mariadb()` implementa la persistencia.
- `src/apps/7_service_frontend/routermiddleware.py`:
  - `create_organization()` ahora replica al broker en modo `db_only` para
    garantizar persistencia end-to-end.
- `src/apps/3_backend/routercore.py`:
  - `create_organization()` ahora auto-asigna todos los SuperAdmin activos a la
    nueva organización mediante `_auto_assign_superadmins_to_org()`.

---

### Bug 2: Nuevas versiones no reflejan contenido en explorador

**Síntoma:** Al crear una nueva versión en la página Proyecciones, el backend
reportaba éxito pero el explorador no mostraba la nueva carpeta de versión.
Las versiones existentes previamente sí funcionaban.

**Causa raíz:**
1. `create_version_full()` usaba `/fmo/newversion` (clone) que requiere que la
   versión origen exista físicamente. Para proyectos nuevos sin carpeta en disco,
   la operación fallaba silenciosamente.
2. El backend retornaba `success: True` incluso cuando fmanagement fallaba,
   causando desincronización entre BD y filesystem.
3. `clone_from_version_id` se fijaba siempre a la versión SELECCIONADA en la UI
   (típicamente la primera), en vez de la última existente.

**Correcciones aplicadas:**
- `src/apps/3_backend/routercore.py`:
  - `create_version_full()` ahora siempre usa `_create_empty_version` (POST
    `/fmo/createfolder`) que crea la jerarquía completa ORG/PRJ/version sin
    depender de que exista una versión previa en disco.
  - Si fmanagement falla, se hace rollback de la transacción SQL y se retorna
    `success: False` con el error específico.
- `src/apps/6_web_backoffice/web_backoffice/web_backoffice.py`:
  - `create_new_version()` ahora usa la ÚLTIMA versión existente como fuente de
    clonación, no la versión seleccionada en la UI.
- `src/apps/5_web_frontend/web_frontend/web_frontend.py`:
  - Misma corrección que en backoffice para consistencia.

---

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `src/apps/3_backend/4_infrastructure/persistence/storage_adapter.py` | Persistencia de organizaciones en MariaDB |
| `src/apps/3_backend/routercore.py` | Auto-asignación SuperAdmin + rollback fmanagement + versión vacía |
| `src/apps/7_service_frontend/routermiddleware.py` | Replicación al broker en db_only |
| `src/apps/6_web_backoffice/web_backoffice/web_backoffice.py` | Clone desde última versión |
| `src/apps/5_web_frontend/web_frontend/web_frontend.py` | Clone desde última versión |

### Entornos verificados

- [x] MacBook (desarrollo local)
- [x] AWS Pre (producción)
