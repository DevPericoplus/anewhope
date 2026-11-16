# Changelog

## [2026-11-16] - Cap de silicon con la site key nueva (como dev)

**Por qué:** el `env.yaml` de silicon ya usaba la site key nueva (`3f9ea24d4c`)
en la ruta pública, pero el siteverify interno seguía con la anterior
(`dcbb5f3bb8`): el despliegue paraba en «misma site key» y el alta fallaba.

**Qué:** las dos rutas de silicon usan `3f9ea24d4c`, igual que dev. El secret
de esa clave se rota con el job `silicon/Rotate_Cap_Secret` y se guarda en el
vault (`env/silicon/backend.yml › laim_cap_secret`).

## [2026-11-15] - Canal de paquetes Linux en /check_last_version (LAIM pkg148)

**Por qué:** una instalación deb/rpm de LAIM está en `/opt/laim`, de root, y
no puede reemplazarse con un parche: LAIM 3.2.10 (pkg148) se actualiza con el
paquete firmado y la confirmación sudo del administrador.

**Qué:** `/check_last_version` acepta `artifact=package` en `linux_deb` y
`linux_rpm` (núcleo, sin plugin) y ofrece el `.deb`/`.rpm` de
`<storage>/<edición>/packages/linux/{deb,rpm}/latest` con la carga firmada
`edition|platform|package|<versión>|<fichero>|sha256=<hex>`. `/product/download`
sirve `artifact_type=package` con la misma guarda de ruta. Middleware y broker
pasan `artifact`; sin él, el canal de parches no cambia. Sin paquete, sin SHA o
con extensión equivocada no hay oferta.

**Archivos:** `src/apps/3_backend/apicore.py`, `src/apps/7_service_frontend/{apife,routermiddleware,broker_backend_client}.py`,
`src/apps/8_service_backend/{apibe,routerbroker,interfacetocore}.py`, tests
nuevos en las tres apps, `versions.yml` (backend_core 0.8.35, broker 0.8.13,
middleware 0.8.17), `AGENTS.md` § 37.2.

## [2026-11-15] - Cap de dev con la site key nueva (como silicon y pre)

**Síntoma:** en `infrastructure/environments/dev/env.yaml` la ruta pública de
Cap ya usaba la site key nueva de dev (`4d019fa90c`), pero
`laim_cap_verify_endpoint` (siteverify interno, :3301 y :3300) seguía con la
antigua (`6f5eec940d`). El navegador pedía el reto con una clave y el backend
lo verificaba con otra: el alta fallaba, `test_cap_siteverify` también y el
despliegue de dev se paraba en la comprobación de `backend.yml`
(anh_ansible_environments: misma site key en las dos rutas).

**Fix:** las dos rutas de dev usan `4d019fa90c`. El secret de esa site key va
en el vault de dev (`laim_cap_secret`, anh_ansible_environments
`env/dev/backend.yml`).

**Archivos:** `infrastructure/environments/dev/env.yaml`.

## [2026-11-15] - /check_last_version firmado con el SHA del parche (LAIM 3.2.10)

**Síntoma:** producción respondía «hay actualización» sin firma: no existía la
clave `exchange` del major 3 en `laim_exchange_keys` y nada la sembraba. LAIM
descarta una respuesta sin firma, así que nunca se ofrecía la actualización.

**Fix:**
- La clave `exchange` se siembra en el primer `/check_last_version`, igual que
  `serial_signing` (fila → `LAIM_EXCHANGE_KEY` → constante de producto, solo
  para el major de producto).
- La carga firmada lleva el SHA-256 del parche servido
  (`…|<fichero>|sha256=<hex>`), como exige LAIM 3.2.10 (pkg139).
- Sin clave o sin SHA, no se ofrece la actualización (nunca una respuesta sin
  firma).
- `key_fingerprint` en la respuesta y
  `scripts/laim_exchange_key_fingerprint.py` para comparar la clave de
  laimweb con la de LAIM sin revelarlas.

**Archivos:** `src/2_shared_application/security/laim_update_signing.py`
(nuevo), `adapters/laim_exchange_key.py`, `security/laim_serial.py`,
`src/apps/3_backend/apicore.py`, `scripts/laim_exchange_key_fingerprint.py`,
tests en `src/apps/3_backend/tests/test_laim_update_signing.py`.

---

## [2026-06-29] - Fix refresco del explorador tras operaciones de menú contextual

### Bug 4: El explorador no refresca la vista al crear carpetas

**Síntoma:** Al crear una carpeta mediante el menú contextual del explorador, el mensaje
de éxito aparecía ("Carpeta creada exitosamente") pero la vista no se actualizaba visualmente.
El usuario debía navegar fuera y volver para ver los cambios.

**Causa raíz:** El método `process_fmanagementlist()` reconstruía todos los items desde cero
con `is_expanded=depth < 1`, lo que significa que las carpetas de versión (depth 1) se colapsaban
al refrescar. El usuario tenía la versión expandida para ver su contenido, pero tras el refresh
la versión se colapsaba, ocultando la nueva carpeta creada.

**Fix:** Se preserva el estado de expansión (`is_expanded`) de los items existentes antes de
reconstruir el árbol, y se restaura después. Así los nodos que el usuario tenía abiertos
permanecen abiertos tras la operación.

**Archivos corregidos:**
- `src/apps/5_web_frontend/components/explorador.py` - `process_fmanagementlist()`
- `src/apps/6_web_backoffice/components/explorador.py` - `process_fmanagementlist()`

---

## [2026-06-29] - Fix conexión fmanagement al crear versiones en AWS

### Bug 3: Error de conexión con fmanagement al crear versiones en AWS

**Síntoma:** Al crear una nueva versión para un proyecto en el entorno AWS (pre),
se producía el error: `[Errno 2] No such file or directory: '/opt/anewhope/app/infrastructure/environments/macbook/env.yaml'`

**Causa raíz:** El archivo `apicore.py` y `routercore.py` importaban el `FmanagementClient`
desde un archivo legacy (`4_infrastructure/web/fmanagement_client.py`) que tenía la ruta
`macbook` hardcodeada en la lógica de resolución de `basepath`. El archivo correcto es
`clients/fmanagement_client.py` que resuelve la configuración dinámicamente.

**Archivos corregidos:**
- `src/apps/3_backend/apicore.py` - Cambiada la ruta de importación de `4_infrastructure/web/` a `clients/`
- `src/apps/3_backend/routercore.py` - Cambiada la ruta de importación y eliminada reimportación redundante
- `src/apps/3_backend/clients/fmanagement_client.py` - Añadida clase `FmanagementClientError`

---

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
  - `create_version_full()` ahora usa `_create_empty_version` para v001 (sin
    clone_from) y `/fmo/newversion` (clone) para versiones posteriores.
  - Si fmanagement falla, se hace rollback de la transacción SQL y se retorna
    `success: False` con el error específico.
- `src/apps/6_web_backoffice/web_backoffice/web_backoffice.py`:
  - `create_new_version()` ahora usa la ÚLTIMA versión existente como fuente de
    clonación, no la versión seleccionada en la UI.
- `src/apps/5_web_frontend/web_frontend/web_frontend.py`:
  - Misma corrección que en backoffice para consistencia.

---

### Bug 2.1: Versiones nuevas creaban subcarpetas internas no deseadas

**Síntoma:** Las carpetas de versión nuevas (v001, v002, etc.) contenían
subcarpetas internas (`datos`, `modelos`, `evaluaciones`, `resultados`) que no
deberían existir. Comparando con PRJ00004 (creado correctamente desde el
explorador), una v001 debe estar **vacía** y las subcarpetas las crea el
usuario manualmente.

**Causa raíz:**
`_create_empty_version()` en `fmanagement_client.py` creaba automáticamente
una "estructura base" con 4 subcarpetas predefinidas. Esto era incorrecto:
la versión debe contener solo lo que el usuario decida crear.

**Correcciones aplicadas:**
- `src/apps/3_backend/clients/fmanagement_client.py`:
  - `_create_empty_version()` ahora solo crea la carpeta raíz de versión (vacía).
    Se eliminó la creación automática de subcarpetas base.
- `src/apps/3_backend/routercore.py`:
  - `create_version_full()` restaura la lógica de clonado: si hay versión previa
    (`clone_from_version > 0`) usa `/fmo/newversion` para copiar el contenido
    existente. Solo la primera versión usa `_create_empty_version` (vacía).
- **Limpieza en AWS**: Se eliminaron las subcarpetas internas erróneas de
  PRJ00014, PRJ00015, PRJ00016, PRJ00017.

**Referencia**: PRJ00004 v001 (vacía, solo contiene `images/` y `text/` creadas
por el usuario) demuestra el comportamiento correcto.

---

### Bug 1.1: organization_id no se asigna tras crear organización en formulario

**Síntoma:** Los usuarios `julio` y `juangarcia` fueron creados con
`organization_id=1` (myllm) a pesar de que se debía crear una organización
nueva para cada uno.

**Causa raíz:**
En `save_organization()` de `user_creation.py` (tanto frontend como backoffice),
tras crear una organización exitosamente y obtener su nuevo `organization_id`,
el valor NO se asignaba a `self.organization_id`. Al guardar el usuario
posteriormente, `self.organization_id` seguía vacío y la línea:
```python
org_id_int = int(self.organization_id) if self.organization_id else 1
```
asignaba `1` (myllm) por defecto.

**Correcciones aplicadas:**
- `src/apps/6_web_backoffice/pages/user_creation.py`:
  - Añadido `self.organization_id = str(organization_id)` tras creación exitosa.
- `src/apps/5_web_frontend/pages/user_creation.py`:
  - Misma corrección que en backoffice.

---

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `src/apps/3_backend/4_infrastructure/persistence/storage_adapter.py` | Persistencia de organizaciones en MariaDB |
| `src/apps/3_backend/routercore.py` | Auto-asignación SuperAdmin + rollback fmanagement + lógica de clonado |
| `src/apps/3_backend/clients/fmanagement_client.py` | Versión vacía sin subcarpetas internas |
| `src/apps/7_service_frontend/routermiddleware.py` | Replicación al broker en db_only |
| `src/apps/6_web_backoffice/web_backoffice/web_backoffice.py` | Clone desde última versión |
| `src/apps/5_web_frontend/web_frontend/web_frontend.py` | Clone desde última versión |
| `src/apps/6_web_backoffice/pages/user_creation.py` | Asignar organization_id al formulario tras crear org |
| `src/apps/5_web_frontend/pages/user_creation.py` | Misma corrección que backoffice |

### Entornos verificados

- [x] MacBook (desarrollo local)
- [x] AWS Pre (producción)
