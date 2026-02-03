# Plan de Integración del Componente Explorador de Archivos

## 📋 Resumen del Componente

**Ubicación origen**: `/Users/administrator/develop/reflex_components_templates/reflex_components_templates/pages/explorador/`

**Funcionalidad**: Explorador de archivos jerárquico con gestión de versiones, estados y permisos.

## 🗂️ Archivos JSON utilizados (a migrar a DB)

### 1. `proyecto.json` - Estructura de carpetas y archivos
**Fuente actual**: JSON mockeado  
**Fuente destino**: fmanagement API (`GET /fmo/list`)

```json
{
  "status": "success",
  "path": "/data/files/external/ORG0001/PRJ00001",
  "items": [
    {
      "name": "PRJ00001",
      "is_dir": true,
      "size_bytes": 1500000000,
      "items": [
        {
          "name": "v001",
          "is_dir": true,
          "size_bytes": 850000000,
          "items": [...]
        }
      ]
    }
  ]
}
```

**Acción**: Ya implementado en fmanagement. Llamar desde Backend Core.

---

### 2. `estado_version.json` - Estados de las versiones
**Fuente actual**: JSON mockeado  
**Fuente destino**: Nueva tabla en `myllm_projects_db`

```json
[
  {
    "id_organizacion": 1,
    "id_proyecto": 1,
    "id_version": 1,
    "state": "Bloqueada",
    "protected": true,
    "size": 850427904,
    "final_c": false,
    "final_i": false
  }
]
```

**Tabla a crear**: `version_states`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INT AUTO_INCREMENT | PK |
| `id_organizacion` | INT | FK a organizaciones |
| `id_proyecto` | INT | FK a proyectos |
| `id_version` | INT | Número de versión |
| `state` | ENUM | "Abierta", "Bloqueada", "Protegida", "Final" |
| `protected` | BOOLEAN | Si está protegida (no editable) |
| `size_bytes` | BIGINT | Tamaño total de la versión |
| `final_c` | BOOLEAN | Cliente ha solicitado entrenamiento |
| `final_i` | BOOLEAN | Interno ha confirmado preparación |
| `updated_at` | TIMESTAMP | Última actualización |

**Endpoints a crear**:
- `GET /proyectos/{id}/versiones/{id_version}/estado?org_id={org_id}`
- `PATCH /proyectos/{id}/versiones/{id_version}/estado` (cambiar state, flags)

---

### 3. `seguridad.json` - Perfil de usuario
**Fuente actual**: JSON mockeado  
**Fuente destino**: `SharedSessionState` (ya implementado)

```json
{
  "usuario": {
    "user_id": 1,
    "id_organizacion": 1,
    "identity_type_id": 1,
    "project_id": 1,
    "user_name": "adminone",
    "permisos": {...}
  }
}
```

**Acción**: ✅ Ya implementado en `SharedSessionState`. Reutilizar permisos existentes.

---

### 4. `roles_by_app.json` - Roles del sistema
**Fuente actual**: JSON mockeado  
**Fuente destino**: `low_level_permissions.json` (ya existe)

**Acción**: ✅ Ya implementado. Usar los permisos de `SharedSessionState`.

---

### 5. `evolucion.json` - Eventos de cambios de estado
**Fuente actual**: JSON mockeado  
**Fuente destino**: Nueva tabla en `myllm_projects_db`

```json
[
  {
    "timestamp": "2026-01-28T17:23:14.104590",
    "evento": "ENTRENAMIENTO_DISPONIBLE",
    "id_organizacion": 1,
    "id_proyecto": 1,
    "id_version": "v002",
    "mensaje": "La versión ha sido confirmada como FINAL..."
  }
]
```

**Tabla a crear**: `version_events`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INT AUTO_INCREMENT | PK |
| `id_organizacion` | INT | FK a organizaciones |
| `id_proyecto` | INT | FK a proyectos |
| `id_version` | INT | Número de versión |
| `evento` | VARCHAR(100) | Tipo de evento |
| `mensaje` | TEXT | Descripción del evento |
| `user_id` | INT | Usuario que generó el evento |
| `timestamp` | TIMESTAMP | Cuándo ocurrió |

---

## 🔄 Estados de Versión y Transiciones

### Estados disponibles

| Estado | Descripción | Color | Editable |
|--------|-------------|-------|----------|
| **Abierta** | Versión en desarrollo | Verde (#228B22) | ✅ Sí |
| **Bloqueada** | Versión bloqueada temporalmente | Naranja (#FF8C00) | ❌ No |
| **Protegida** | Cliente solicitó entrenamiento | Azul (#00008B) | ❌ No |
| **Final** | Confirmada para entrenamiento | Rojo (#8B0000) | ❌ No |

### Flags de estado

| Flag | Nombre | Descripción |
|------|--------|-------------|
| `protected` | Protegida | Si está activa, no se puede editar la versión |
| `final_c` | Final Cliente | Cliente ha dado OK para entrenamiento |
| `final_i` | Final Interno | Personal myllm ha confirmado preparación |

### Transiciones de estado

```
[Abierta] ──────────────┐
    ↑                   │
    │                   ↓
    │        [Cliente solicita entrenamiento]
    │                   ↓
    │              [Protegida]
    │               final_c=true
    │                   │
    │                   ↓
    │        [Interno confirma preparación]
    │                   ↓
    │               [Final]
    │          final_c=true, final_i=true
    │                   │
    └──[Admin: Revisar]─┘
         (revertir a Abierta)

[Bloqueada] ←──[Admin: Bloquear/Desbloquear]──→ [Abierta]
```

### Reglas de negocio

1. **Cliente** puede:
   - ✅ Solicitar entrenamiento (Abierta/Bloqueada → Protegida)
   - ❌ NO puede confirmar entrenamiento

2. **Interno** (backoffice) puede:
   - ✅ Confirmar entrenamiento (Protegida → Final)
   - ❌ NO puede solicitar entrenamiento (es rol del cliente)

3. **Admin** puede:
   - ✅ Bloquear/Desbloquear versiones
   - ✅ Revisar versiones (revertir Final/Protegida → Abierta)

4. **Versiones protegidas**:
   - ❌ No se pueden editar carpetas ni archivos
   - ❌ No se pueden crear/subir archivos
   - ✅ Sí se pueden leer y descargar

---

## 🔌 Integración con fmanagement

El componente ya tiene un cliente HTTP (`FManagementClient`) que interactúa con fmanagement:

### Endpoints de fmanagement utilizados

| Operación | Método | Endpoint | Parámetros |
|-----------|--------|----------|------------|
| Listar estructura | GET | `/fmo/list` | orgpath, prjpath, versionpath |
| Crear carpeta | POST | `/fmo/createfolder` | orgpath, prjpath, versionpath, subfolders |
| Renombrar carpeta | PATCH | `/fmo/renamefolder` | orgpath, prjpath, versionpath, subfolders, new_filename |
| Eliminar carpeta | DELETE | `/fmo/deletefolder` | orgpath, prjpath, versionpath, subfolders |
| Crear/Subir archivo | POST | `/fmo/createfile` | orgpath, prjpath, versionpath, subfolders, filename, extfile, [file] |
| Renombrar archivo | PATCH | `/fmo` | operation=rename, ... |
| Eliminar archivo | DELETE | `/fmo/deletefile` | orgpath, prjpath, versionpath, subfolders, filename, extfile |
| Propiedades | GET | `/fmo/readfolder` | orgpath, prjpath, versionpath, subfolders |
| Descargar archivo | GET | `/fmo/download` | orgpath, prjpath, versionpath, subfolders, filename, extfile |

### Parámetros comunes

```python
{
  "iduser": user_id,
  "basepath": "default",  # Puede omitirse (fmanagement lee de su configuración)
  "orgpath": "ORG0001",   # Generado con get_folder_by_id_organization()
  "prjpath": "PRJ00001",  # Generado con get_folder_by_id_project()
  "versionpath": "v001",  # Generado con get_folder_by_id_version()
  "subfolders": "docs/reports",  # Ruta relativa dentro de la versión
  "identity_type_id": identity_type_id  # Para validación de permisos
}
```

---

## 📊 Integración con Backend Core

El flujo debe ser:

```
Frontend/Backoffice → Middleware → Broker → Backend Core → fmanagement
                                                         → MariaDB (estados)
```

### Nuevos endpoints en Backend Core

#### 1. Gestión de estados de versión

```python
# GET /proyectos/{id}/versiones/{id_version}/estado
@app.get("/proyectos/{project_id}/versiones/{version_id}/estado")
async def get_version_state(
    project_id: int,
    version_id: int,
    org_id: int,
) -> VersionStateResponse:
    """Obtiene el estado completo de una versión."""
    pass

# PATCH /proyectos/{id}/versiones/{id_version}/estado
@app.patch("/proyectos/{project_id}/versiones/{version_id}/estado")
async def update_version_state(
    project_id: int,
    version_id: int,
    request: UpdateVersionStateRequest,
) -> VersionStateResponse:
    """Actualiza el estado de una versión."""
    pass
```

#### 2. Operaciones con fmanagement (proxy)

```python
# POST /fmanagement/list
@app.post("/fmanagement/list")
async def fmanagement_list(request: FmanagementListRequest) -> dict:
    """Proxy a fmanagement para listar estructura."""
    pass

# POST /fmanagement/operation
@app.post("/fmanagement/operation")
async def fmanagement_operation(request: FmanagementOperationRequest) -> dict:
    """Proxy genérico para operaciones de fmanagement."""
    pass
```

---

## 🎨 Adaptación del Componente

### Cambios necesarios en el componente

1. **Eliminar JSON locales**: No usar `data/proyecto.json`, etc.

2. **Usar SharedSessionState**: Heredar de `SharedSessionState` para obtener:
   - `user_id`, `organization_id`, `identity_type_id`
   - Permisos (`can_folder_create`, `can_file_update`, etc.)
   - Tokens JWT (`access_token`, `session_token`)

3. **Llamar a API en lugar de JSON**:
   ```python
   # Antes
   with open("data/proyecto.json", "r") as f:
       self.fmanagementlist = json.load(f)
   
   # Después
   from adapters.api_client import get_fmanagement_list
   result = get_fmanagement_list(
       org_folder=self.proyecciones_org_folder,  # "ORG0001"
       prj_folder=self.proyecciones_prj_folder,  # "PRJ0002"
       version_folder=self.proyecciones_version_folder,  # "v003"
       access_token=self.access_token,
       session_token=self.session_token,
   )
   self.fmanagementlist = result
   ```

4. **Persistir estados en DB**:
   ```python
   # Cuando se cambia el estado de una versión
   update_version_state(
       project_id=self.proyecciones_project_id,
       version_id=self.proyecciones_version_id,
       state="Protegida",
       final_c=True,
       access_token=self.access_token,
       session_token=self.session_token,
   )
   ```

5. **Mapear roles**: Cliente/Interno según `training_create` permission

---

## 🗄️ Nuevas Tablas en myllm_projects_db

### Tabla: version_states

```sql
CREATE TABLE `version_states` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `id_organizacion` INT NOT NULL,
  `id_proyecto` INT NOT NULL,
  `id_version` INT NOT NULL,
  `state` ENUM('Abierta', 'Bloqueada', 'Protegida', 'Final') NOT NULL DEFAULT 'Abierta',
  `protected` BOOLEAN NOT NULL DEFAULT FALSE,
  `size_bytes` BIGINT DEFAULT 0,
  `final_c` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Cliente solicitó entrenamiento',
  `final_i` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Interno confirmó preparación',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `updated_by_user_id` INT,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_version` (`id_proyecto`, `id_version`),
  KEY `idx_org_prj` (`id_organizacion`, `id_proyecto`),
  KEY `idx_state` (`state`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### Tabla: version_events

```sql
CREATE TABLE `version_events` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `id_organizacion` INT NOT NULL,
  `id_proyecto` INT NOT NULL,
  `id_version` INT NOT NULL,
  `evento` VARCHAR(100) NOT NULL,
  `mensaje` TEXT,
  `user_id` INT NOT NULL,
  `timestamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_version` (`id_proyecto`, `id_version`),
  KEY `idx_timestamp` (`timestamp` DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 🚀 Plan de Implementación

### Fase 1: Base de datos ✅ CREAR TABLAS

1. Crear tabla `version_states` en `myllm_projects_db`
2. Crear tabla `version_events` en `myllm_projects_db`
3. Documentar en `README_DEPLOYMENT.md`

### Fase 2: Backend Core ✅ CREAR ENDPOINTS

1. DTOs:
   - `VersionStateDto`
   - `VersionStateResponse`
   - `UpdateVersionStateRequest`
   - `VersionEventDto`
   - `FmanagementListRequest`
   - `FmanagementOperationRequest`

2. Métodos en `routercore.py`:
   - `get_version_state()`
   - `update_version_state()`
   - `create_version_event()`
   - `fmanagement_list_proxy()`
   - `fmanagement_operation_proxy()`

3. Endpoints en `apicore.py`:
   - `GET /proyectos/{id}/versiones/{id_version}/estado`
   - `PATCH /proyectos/{id}/versiones/{id_version}/estado`
   - `POST /fmanagement/list`
   - `POST /fmanagement/operation`

### Fase 3: Broker ✅ PROPAGAR ENDPOINTS

1. Replicar DTOs en `apibe.py`
2. Métodos en `routerbroker.py`
3. Métodos en `interfacetocore.py`

### Fase 4: Middleware ✅ PROPAGAR ENDPOINTS

1. Replicar DTOs en `apife.py`
2. Métodos en `routermiddleware.py`
3. Métodos en `broker_backend_client.py`

### Fase 5: Frontend/Backoffice ✅ API CLIENTS

1. Funciones en `adapters/api_client.py`:
   - `get_version_state()`
   - `update_version_state()`
   - `get_fmanagement_list()`
   - `fmanagement_create_folder()`
   - `fmanagement_rename_folder()`
   - `fmanagement_delete_folder()`
   - `fmanagement_upload_file()`
   - `fmanagement_delete_file()`
   - `fmanagement_download_file()`

### Fase 6: Componente Explorador ✅ ADAPTAR CÓDIGO

1. Copiar `explorador.py` a `src/apps/5_web_frontend/` y `src/apps/6_web_backoffice/`
2. Modificar `ExploradorState` para heredar de `SharedSessionState`
3. Eliminar carga de JSON locales
4. Implementar métodos API:
   - `load_from_fmanagement_api()`
   - `load_version_state_from_db()`
   - `save_version_state_to_db()`

### Fase 7: Integración en Proyecciones ✅ INTEGRAR UI

1. Modificar `proyecciones_management_panel()` en frontend/backoffice
2. Reemplazar Layer 3 (placeholder) con el componente explorador real
3. Pasar contexto: `org_folder`, `prj_folder`, `version_folder`

---

## 🔐 Permisos del Componente

El componente usa permisos granulares que YA ESTÁN en `low_level_permissions.json`:

| Permiso componente | Permiso SharedSessionState | Campo en SharedSessionState |
|-------------------|---------------------------|----------------------------|
| `folder_create` | `folder_create` | `can_folder_create` |
| `folder_delete` | `folder_delete` | `can_folder_delete` |
| `folder_rename` | `folder_rename` | `can_folder_rename` |
| `folder_read` | `folder_read` | `can_folder_read` |
| `folder_list` | `folder_list` | `can_folder_list` |
| `file_create` | `file_create` | `can_file_create` |
| `file_read` | `file_read` | `can_file_read` |
| `file_update` | `file_update` | `can_file_update` |
| `file_delete` | `file_delete` | `can_file_delete` |
| `file_list` | `file_list` | `can_file_list` |
| `version_create` | `version_create` | `can_version_create` |
| `trainig_create` | `training_create` | `can_training_create` |

**Acción**: ✅ Reutilizar permisos de `SharedSessionState` directamente. No necesita nuevo sistema de permisos.

---

## 🎯 Determinación de Rol Cliente vs Interno

```python
# En el componente
is_internal_user = state.can_training_create

# Si can_training_create == True → Usuario Interno (backoffice)
# Si can_training_create == False → Usuario Cliente (frontend)
```

---

## 📝 Próximos pasos

1. **Crear DDL de tablas** (`version_states`, `version_events`)
2. **Implementar endpoints** en toda la cadena (Backend Core → Broker → Middleware)
3. **Adaptar componente** para usar API real
4. **Integrar en Proyecciones** (Layer 3)
5. **Crear tests** de integración
6. **Documentar** en README.md

---

## ⚠️ Consideraciones importantes

1. **Crear versión sincronizada**: Cuando se pulsa "Crear nueva versión":
   - Backend Core inserta en tabla `versiones`
   - Backend Core llama a fmanagement `newversion` (clonar carpeta en disco)
   - Backend Core crea entrada en `version_states` con estado="Abierta"
   - Ambas operaciones deben ser atómicas (transacción)

2. **Tamaño de versión**: Calcular desde fmanagement al listar (`/fmo/list` devuelve `size_bytes`)

3. **Security by Design**: Validar permisos en TODAS las capas antes de ejecutar operaciones

4. **Estados persistentes**: Los cambios de estado deben registrarse en `version_events` para auditoría

5. **Rol funcional**: La determinación Cliente/Interno se basa SOLO en `training_create` permission

---

**Documento creado**: 2026-02-03  
**Para revisión antes de implementación**
