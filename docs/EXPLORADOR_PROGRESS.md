# Progreso de Integración del Componente Explorador

**Fecha inicio**: 2026-02-03  
**Estado**: 🔄 En progreso (20% completado)

---

## 📊 Resumen Ejecutivo

Se está integrando el componente explorador de archivos desde el repositorio `reflex_components_templates` hacia el proyecto principal `anewhope`. Este componente gestiona la visualización y manipulación de archivos/carpetas de versiones de proyectos con estados (Abierta, Bloqueada, Protegida, Final).

**Complejidad**: Alta  
**Estimación total**: 7 fases con ~30 pasos  
**Progreso actual**: Fase 2 de 7 (20%)

---

## ✅ FASE 1: Base de Datos (100% COMPLETADA)

### PASO 1.1 - DDL tabla version_states ✅
**Archivo**: `infrastructure/database/ddl_version_states.sql`

**Tabla creada**: `version_states` en `myllm_projects_db`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INT AUTO_INCREMENT | PK |
| `id_organizacion` | INT | FK a organizaciones |
| `id_proyecto` | INT | FK a proyectos |
| `id_version` | INT | Número de versión |
| `state` | ENUM | 'Abierta', 'Bloqueada', 'Protegida', 'Final' |
| `protected` | BOOLEAN | Si está protegida (no editable) |
| `size_bytes` | BIGINT | Tamaño total en bytes |
| `final_c` | BOOLEAN | Cliente solicitó entrenamiento |
| `final_i` | BOOLEAN | Interno confirmó preparación |
| `created_at` | TIMESTAMP | Fecha de creación |
| `updated_at` | TIMESTAMP | Última actualización |
| `updated_by_user_id` | INT | Usuario que actualizó |

**Unique Key**: (`id_proyecto`, `id_version`)

---

### PASO 1.2 - DDL tabla version_events ✅
**Archivo**: `infrastructure/database/ddl_version_events.sql`

**Tabla creada**: `version_events` en `myllm_projects_db`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INT AUTO_INCREMENT | PK |
| `id_organizacion` | INT | FK a organizaciones |
| `id_proyecto` | INT | FK a proyectos |
| `id_version` | INT | Número de versión |
| `evento` | VARCHAR(100) | Tipo de evento |
| `mensaje` | TEXT | Descripción |
| `user_id` | INT | Usuario que generó el evento |
| `user_name` | VARCHAR(100) | Nombre usuario (desnormalizado) |
| `old_state` | VARCHAR(50) | Estado anterior |
| `new_state` | VARCHAR(50) | Estado nuevo |
| `metadata` | JSON | Información adicional |
| `timestamp` | TIMESTAMP | Cuándo ocurrió |

**Eventos soportados**:
- `VERSION_CREADA`
- `VERSION_BLOQUEADA` / `VERSION_DESBLOQUEADA`
- `ENTRENAMIENTO_SOLICITADO`
- `ENTRENAMIENTO_CONFIRMADO`
- `VERSION_REVERTIDA`
- `CARPETA_CREADA` / `CARPETA_RENOMBRADA` / `CARPETA_ELIMINADA`
- `ARCHIVO_SUBIDO` / `ARCHIVO_RENOMBRADO` / `ARCHIVO_ELIMINADO`

---

### PASO 1.3 - Actualizar README_DEPLOYMENT.md ✅
**Archivo**: `README_DEPLOYMENT.md`

**Cambios**:
- Añadidas 2 nuevas tablas en la sección "Base de datos de proyectos"
- Documentados estados de versión y eventos
- Fecha de cambio: 2026-02-03

---

## ✅ FASE 2: DTOs y Backend Core (100% COMPLETADA)

### PASO 2.1 - DTOs para estados de versión ✅
**Archivo**: `src/apps/3_backend/dtos/version_state_dtos.py`

**DTOs creados**:

| DTO | Propósito |
|-----|-----------|
| `VersionState` | Enum con estados (Abierta, Bloqueada, Protegida, Final) |
| `VersionEventType` | Enum con tipos de eventos |
| `VersionStateDto` | Entidad completa de estado de versión |
| `CreateVersionStateRequest` | Request para crear estado (al crear versión) |
| `UpdateVersionStateRequest` | Request para actualizar estado |
| `VersionStateResponse` | Response con estado |
| `VersionEventDto` | Entidad de evento |
| `CreateVersionEventRequest` | Request para crear evento |
| `VersionEventListResponse` | Response con lista de eventos |
| `FmanagementListRequest` | Request para listar estructura vía fmanagement |
| `FmanagementOperationRequest` | Request genérico para operaciones fmanagement |
| `FmanagementResponse` | Response genérica de fmanagement |
| `CreateVersionFullRequest` | Request completo (DB + fmanagement) |
| `CreateVersionFullResponse` | Response de creación completa |

**Líneas de código**: ~250 líneas con documentación completa

---

### PASO 2.2 - Cliente HTTP para fmanagement ✅
**Archivo**: `src/apps/3_backend/clients/fmanagement_client.py`

**Clase**: `FmanagementClient`

**Métodos implementados**:

#### Listado y lectura
- `list_structure()` → `GET /fmo/list`
- `read_folder()` → `GET /fmo/readfolder`

#### Operaciones de carpetas
- `create_folder()` → `POST /fmo/createfolder`
- `rename_folder()` → `PATCH /fmo/renamefolder`
- `delete_folder()` → `DELETE /fmo/deletefolder`

#### Operaciones de archivos
- `create_file()` → `POST /fmo/createfile`
- `rename_file()` → `PATCH /fmo` (operation=rename)
- `delete_file()` → `DELETE /fmo/deletefile`
- `download_file()` → `GET /fmo/download`

#### Gestión de versiones
- `create_version()` → `POST /fmo/newversion` ⚠️ **Requiere verificación en fmanagement**

**Líneas de código**: ~350 líneas con manejo de errores

**Características**:
- Timeout configurable
- Logger integrado
- Manejo robusto de errores HTTP
- Soporte para clonación de versiones

---

### PASO 2.3 - Inicializar módulo clients ✅
**Archivo**: `src/apps/3_backend/clients/__init__.py`

Exporta `FmanagementClient` para importación limpia.

---

### PASO 2.4 - Métodos en routercore.py ✅
**Estado**: Completado

**Métodos implementados** (10 nuevos métodos):

#### Gestión de estados de versión:
1. ✅ `get_version_state(project_id, version_id, org_id)` → Consulta estado actual
2. ✅ `update_version_state(project_id, version_id, org_id, update_data)` → Actualiza estado
3. ✅ `create_version_state(project_id, version_id, org_id, user_id)` → Crea estado inicial
4. ✅ `create_version_event(event_data)` → Registra evento en auditoría
5. ✅ `get_version_events(project_id, version_id, org_id, limit)` → Lista eventos de versión

#### Integración con fmanagement:
6. ✅ `fmanagement_list(org_folder, prj_folder, version_folder, user_id, identity_type_id)` → Proxy a list_structure()
7. ✅ `fmanagement_operation(operation, params)` → Proxy genérico a fmanagement
8. ✅ `create_version_full(...)` → **Crea versión completa (DB + fmanagement, atómico)**

**Características implementadas**:
- ✅ Transacciones atómicas en `create_version_full()`
- ✅ Manejo de errores robusto con rollback automático
- ✅ Soporte para clonación de versiones
- ✅ Registro automático de eventos
- ✅ Logging detallado en cada operación
- ✅ Metadata JSON en eventos

**Líneas añadidas**: ~700 líneas con documentación completa

---

### PASO 2.5 - Endpoints en apicore.py ✅
**Estado**: Completado

**DTOs añadidos** (10 nuevos DTOs):
1. ✅ `VersionStateDto` - Estado completo de versión
2. ✅ `VersionStateResponse` - Response de estado
3. ✅ `UpdateVersionStateRequest` - Request para actualizar
4. ✅ `VersionEventDto` - Evento de auditoría
5. ✅ `VersionEventsResponse` - Lista de eventos
6. ✅ `CreateVersionFullRequest` - Request creación completa
7. ✅ `CreateVersionFullResponse` - Response creación completa
8. ✅ `FmanagementListRequest` - Request para listar
9. ✅ `FmanagementListResponse` - Response listado
10. ✅ `FmanagementOperationRequest` - Request operación genérica
11. ✅ `FmanagementOperationResponse` - Response operación

**Endpoints implementados** (6 nuevos endpoints):

#### Estados de versión:
1. ✅ `GET /proyectos/{id}/versiones/{id_version}/estado` → Obtener estado
2. ✅ `PATCH /proyectos/{id}/versiones/{id_version}/estado` → Actualizar estado
3. ✅ `GET /proyectos/{id}/versiones/{id_version}/eventos` → Historial eventos

#### Versiones completas:
4. ✅ `POST /proyectos/{id}/versiones/crear-completa` → Crear versión (DB + fmanagement)

#### Integración fmanagement:
5. ✅ `POST /fmanagement/list` → Listar estructura
6. ✅ `POST /fmanagement/operation` → Operación genérica

**Tags OpenAPI**:
- `version-states`: Endpoints de estados
- `versiones`: Endpoints de versiones
- `fmanagement`: Integración con fmanagement

**Líneas añadidas**: ~350 líneas con documentación completa

---

## ✅ FASE 3: Broker Backend (100% COMPLETADA)

### PASO 3.1 - Verificación de estructura ✅
**Estado**: Completado

Verificada la estructura del broker backend en `src/apps/8_service_backend/`.

---

### PASO 3.2 - Endpoints en apibe.py ✅
**Estado**: Completado

**Endpoints añadidos** (6 nuevos endpoints):

#### Estados de versión:
1. ✅ `GET /proyectos/{id}/versiones/{id_version}/estado` → Obtener estado
2. ✅ `PATCH /proyectos/{id}/versiones/{id_version}/estado` → Actualizar estado
3. ✅ `GET /proyectos/{id}/versiones/{id_version}/eventos` → Historial eventos

#### Versiones completas:
4. ✅ `POST /proyectos/{id}/versiones/crear-completa` → Crear versión completa

#### Integración fmanagement:
5. ✅ `POST /fmanagement/list` → Listar estructura
6. ✅ `POST /fmanagement/operation` → Operación genérica

**Características**:
- Manejo de errores con `BrokerBusinessError`
- Logging detallado con `[broker]` prefix
- Propagación correcta de `client_app`

**Líneas añadidas**: ~220 líneas

---

### PASO 3.3 - Métodos en routerbroker.py ✅
**Estado**: Completado

**Métodos implementados** (6 nuevos métodos):

#### Gestión de estados:
1. ✅ `get_version_state(project_id, version_id, org_id)`
2. ✅ `update_version_state(project_id, version_id, org_id, update_data)`
3. ✅ `get_version_events(project_id, version_id, org_id, limit)`
4. ✅ `create_version_full(project_id, request_data)`

#### Integración fmanagement:
5. ✅ `fmanagement_list(request_data)`
6. ✅ `fmanagement_operation(request_data)`

**Características**:
- Delegación a `_core_client`
- Conversión de errores a `BrokerBusinessError`
- Logging contextual con `client_app`

**Líneas añadidas**: ~130 líneas

---

### PASO 3.4 - Métodos en interfacetocore.py ✅
**Estado**: Completado (ya existían, corregido 1 método)

**Métodos verificados** (6 métodos):
1. ✅ `get_version_state()` → GET endpoint
2. ✅ `update_version_state()` → PATCH endpoint
3. ✅ `get_version_events()` → GET endpoint
4. ✅ `create_version_full()` → POST endpoint
5. ✅ `fmanagement_list()` → POST endpoint
6. ✅ `fmanagement_operation()` → POST endpoint (corregida firma)

**Corrección realizada**:
- `fmanagement_operation()`: Cambiado de `(operation, params)` a `(request_data)` para consistencia

**Líneas modificadas**: ~5 líneas

---

## ✅ FASE 4: Middleware (100% COMPLETADA)

### PASO 4.1 - Verificación de estructura ✅
**Estado**: Completado

Verificada la estructura del middleware en `src/apps/7_service_frontend/`.

---

### PASO 4.2 - DTOs en apife.py ✅
**Estado**: Completado

**DTOs añadidos** (14 nuevos DTOs):

#### Estados de versión:
1. ✅ `VersionStateDto` → Estado completo de versión
2. ✅ `CreateVersionStateRequest` → Crear estado
3. ✅ `UpdateVersionStateRequest` → Actualizar estado
4. ✅ `VersionStateResponse` → Response con estado
5. ✅ `VersionEventDto` → Evento de auditoría
6. ✅ `CreateVersionEventRequest` → Crear evento
7. ✅ `VersionEventsResponse` → Lista de eventos

#### Integración fmanagement:
8. ✅ `FmanagementListRequest` → Listar estructura
9. ✅ `FmanagementItemDto` → Item de estructura
10. ✅ `FmanagementListResponse` → Response listado
11. ✅ `FmanagementOperationRequest` → Operación genérica
12. ✅ `FmanagementOperationResponse` → Response operación

#### Versión completa:
13. ✅ `CreateVersionFullRequest` → Crear versión completa
14. ✅ `CreateVersionFullResponse` → Response versión completa

**Líneas añadidas**: ~175 líneas

---

### PASO 4.3 - Métodos en broker_backend_client.py ✅
**Estado**: Completado (ya existían)

**Métodos verificados** (6 métodos):
1. ✅ `get_version_state()` → GET a broker
2. ✅ `update_version_state()` → PATCH a broker
3. ✅ `get_version_events()` → GET a broker
4. ✅ `create_version_full()` → POST a broker
5. ✅ `fmanagement_list()` → POST a broker
6. ✅ `fmanagement_operation()` → POST a broker

**Líneas verificadas**: ~60 líneas

---

### PASO 4.4 - Métodos en routermiddleware.py ✅
**Estado**: Completado (ya existían)

**Métodos implementados** (6 métodos):

#### Gestión de estados:
1. ✅ `get_version_state(project_id, version_id, org_id, session)`
2. ✅ `update_version_state(project_id, version_id, org_id, update_data, session)`
3. ✅ `get_version_events(project_id, version_id, org_id, session, limit)`
4. ✅ `create_version_full(project_id, request_data, session)`

#### Integración fmanagement:
5. ✅ `fmanagement_list(request_data, session)`
6. ✅ `fmanagement_operation(request_data, session)`

**Características**:
- Configuración de seguridad con `_configure_broker_security(session)`
- Logging contextual con `[middleware]` prefix
- Delegación a `_broker_client`
- Conversión de errores a `BusinessRuleError`

**Líneas verificadas**: ~140 líneas

---

### PASO 4.5 - Endpoints en apife.py ✅
**Estado**: Completado (ya existían)

**Endpoints implementados** (6 nuevos endpoints):

#### Estados de versión:
1. ✅ `GET /proyectos/{id}/versiones/{id_version}/estado` → Obtener estado
2. ✅ `PATCH /proyectos/{id}/versiones/{id_version}/estado` → Actualizar estado
3. ✅ `GET /proyectos/{id}/versiones/{id_version}/eventos` → Historial eventos

#### Versiones completas:
4. ✅ `POST /proyectos/{id}/versiones/crear-completa` → Crear versión completa (atómica)

#### Integración fmanagement:
5. ✅ `POST /fmanagement/list` → Listar estructura
6. ✅ `POST /fmanagement/operation` → Operación genérica (CRUD archivos/carpetas)

**Características**:
- Validación de permisos por organización
- Manejo de errores con `BusinessRuleError`
- Logging detallado con `[middleware]` prefix
- Documentación completa del flujo de datos
- Tags FastAPI: `version-states`, `versiones`, `fmanagement`

**Líneas verificadas**: ~230 líneas

---

## ✅ FASE 5: Frontend/Backoffice API Clients (100% COMPLETADA)

### PASO 5.1 - Funciones en api_client.py (Frontend) ✅
**Estado**: Completado

**Archivo**: `src/apps/5_web_frontend/adapters/api_client.py`

**Funciones añadidas** (6 nuevas funciones):

#### Estados de versión:
1. ✅ `get_version_state(project_id, version_id, access_token, session_token)`
2. ✅ `update_version_state(project_id, version_id, state, protected, size_bytes, final_c, final_i, updated_by_user_id, access_token, session_token)`
3. ✅ `get_version_events(project_id, version_id, limit, access_token, session_token)`
4. ✅ `create_version_full(project_id, organization_id, version_name, user_id, user_name, description, clone_from_version_id, initial_state, protected, final_c, final_i, access_token, session_token)`

#### Integración fmanagement:
5. ✅ `fmanagement_list(org_folder, prj_folder, version_folder, access_token, session_token)`
6. ✅ `fmanagement_operation(operation, params, access_token, session_token)`

**Características**:
- Uso de `_request_middleware()` helper
- Headers con `X-Client-App: frontend`
- Propagación de tokens JWT (access + session)
- Documentación completa con ejemplos
- Manejo de errores con fallback a `{"success": False}`

**Líneas añadidas**: ~380 líneas

---

### PASO 5.2 - Funciones en api_client.py (Backoffice) ✅
**Estado**: Completado

**Archivo**: `src/apps/6_web_backoffice/adapters/api_client.py`

**Funciones añadidas** (6 nuevas funciones):

#### Estados de versión:
1. ✅ `get_version_state(project_id, version_id, access_token, session_token)`
2. ✅ `update_version_state(project_id, version_id, state, protected, size_bytes, final_c, final_i, updated_by_user_id, access_token, session_token)`
3. ✅ `get_version_events(project_id, version_id, limit, access_token, session_token)`
4. ✅ `create_version_full(project_id, organization_id, version_name, user_id, user_name, description, clone_from_version_id, initial_state, protected, final_c, final_i, access_token, session_token)`

#### Integración fmanagement:
5. ✅ `fmanagement_list(org_folder, prj_folder, version_folder, access_token, session_token)`
6. ✅ `fmanagement_operation(operation, params, access_token, session_token)`

**Características**:
- Uso de `urllib.request` (sin httpx)
- Headers con `X-Client-App: backoffice`
- Propagación de tokens JWT (access + session)
- Timeout de 15s para `create_version_full` (operación compleja)
- Manejo de errores HTTP con `urllib.error.HTTPError`

**Líneas añadidas**: ~350 líneas

---

## ⏭️ FASE 6: Adaptar Componente Explorador (0% PENDIENTE)

### Archivo origen:
`/Users/administrator/develop/reflex_components_templates/reflex_components_templates/pages/explorador/explorador.py`

### Cambios necesarios:

#### 1. Heredar de SharedSessionState
```python
class ExploradorState(SharedSessionState):  # Antes: rx.State
    # Eliminar campos duplicados (user_id, organization_id, etc)
    # Reutilizar permisos de SharedSessionState
```

#### 2. Eliminar JSON locales
- ❌ `data/proyecto.json` → API `get_fmanagement_list()`
- ❌ `data/estado_version.json` → API `get_version_state()`
- ❌ `data/seguridad.json` → `SharedSessionState`
- ❌ `data/roles_by_app.json` → `low_level_permissions.json` (ya existe)
- ❌ `data/evolucion.json` → API `create_version_event()`

#### 3. Implementar métodos API
```python
def load_from_fmanagement_api(self):
    """Reemplaza load_from_json()"""
    result = get_fmanagement_list(...)
    self.fmanagementlist = result
    self.process_fmanagementlist()

def load_version_state_from_db(self):
    """Reemplaza load_version_state()"""
    result = get_version_state(...)
    # Mapear a version_states dict

def save_version_state_to_db(self):
    """Persiste cambios en DB"""
    update_version_state(...)
```

#### 4. Mapear roles
```python
# Determinar Cliente vs Interno
self.is_internal_user = self.can_training_create
```

**Estimación**: ~300 líneas de refactoring

---

## ⏭️ FASE 7: Integrar en Proyecciones (0% PENDIENTE)

### Archivos a modificar:
- `src/apps/5_web_frontend/web_frontend/web_frontend.py`
- `src/apps/6_web_backoffice/web_backoffice/web_backoffice.py`

### Cambios necesarios:

#### 1. Importar componente explorador
```python
from .explorador_component import ExploradorState, explorador_panel
```

#### 2. Integrar en proyecciones_management_panel()
```python
# Layer 3: Reemplazar placeholder con explorador real
rx.box(
    explorador_panel(
        org_folder=State.proyecciones_org_folder,
        prj_folder=State.proyecciones_prj_folder,
        version_folder=State.proyecciones_version_folder,
    ),
    height="60vh",
)
```

#### 3. Conectar botón "Crear nueva versión"
```python
def create_new_version(self):
    """Crea versión en DB + fmanagement."""
    result = create_version_full(
        id_organizacion=self.organization_id,
        id_proyecto=self.proyecciones_project_id,
        version_name=f"V{next_version:03d}",
        user_id=self.user_id,
        identity_type_id=self.identity_type_id,
        clone_from_version=self.proyecciones_version_id,
    )
    if result["success"]:
        self.load_proyecciones_versions()  # Refrescar lista
        self.proyecciones_version_id = result["version_id"]
        # Cargar explorador con nueva versión
```

**Estimación**: ~150 líneas de código

---

## ⚠️ CONSIDERACIONES CRÍTICAS

### 1. Endpoint `/fmo/newversion` en fmanagement
**Estado**: ⚠️ **Requiere verificación**

El método `create_version()` en `FmanagementClient` asume que existe este endpoint en fmanagement (Go). 

**Acciones necesarias**:
1. Verificar en `/Users/administrator/develop/fmanagement/` si existe
2. Si NO existe, implementarlo en Go
3. Debe soportar clonación de versiones con parámetro `clone_from`

**Especificación esperada**:
```go
// POST /fmo/newversion
// Query params:
// - orgpath: string (ej: "ORG0001")
// - prjpath: string (ej: "PRJ0001")
// - versionpath: string (ej: "v003")
// - clone_from: string opcional (ej: "v002")
// - identity_type_id: int
// - iduser: int
// - basepath: string (default: "default")
```

---

### 2. Transacciones atómicas DB + fmanagement
**Criticidad**: 🔴 ALTA

El flujo `create_version_full()` debe ser atómico:

```python
try:
    # 1. Insertar en tabla versiones
    version_id = db.insert_version(...)
    
    # 2. Crear carpeta física vía fmanagement
    fm_result = fmanagement_client.create_version(...)
    
    # 3. Crear estado inicial en version_states
    state_id = db.insert_version_state(...)
    
    # 4. Registrar evento
    db.insert_version_event(...)
    
    db.commit()
except Exception as e:
    db.rollback()
    # Si fmanagement ya creó carpeta, ¿rollback físico?
    raise
```

**Problema**: Si falla paso 3 o 4, la carpeta ya fue creada en disco. ¿Eliminarla?

**Solución propuesta**:
1. Crear en DB primero (rollbackeable)
2. Luego crear en disco
3. Si falla creación en disco, hacer rollback DB y retornar error

---

### 3. Sincronización de tamaños
**Criticidad**: 🟡 MEDIA

`version_states.size_bytes` debe actualizarse cuando:
- Se sube un archivo
- Se elimina un archivo
- Se crea una carpeta con contenido

**Opciones**:
- **A)** Calcular bajo demanda (llamar a fmanagement cada vez)
- **B)** Actualizar en cada operación (más complejo, más preciso)
- **C)** Job periódico que sincroniza tamaños (más simple, eventual consistency)

**Decisión**: Pendiente

---

## 📈 Métricas de Progreso

| Fase | Descripción | Estado | % Completado | Líneas Código |
|------|-------------|--------|--------------|---------------|
| 1 | Base de Datos | ✅ Completada | 100% | ~250 (SQL) |
| 2 | Backend Core DTOs/Clients | ✅ Completada | 100% | ~1750 / 1750 |
| 3 | Broker Backend | ✅ Completada | 100% | ~355 / 355 |
| 4 | Middleware | ✅ Completada | 100% | ~605 / 605 |
| 5 | Frontend/Backoffice Clients | ✅ Completada | 100% | ~730 / 730 |
| 6 | Adaptar Explorador | ⏭️ Pendiente | 0% | 0 / 300 |
| 7 | Integrar en Proyecciones | ⏭️ Pendiente | 0% | 0 / 150 |
| **TOTAL** | | | **84%** | **3690 / 4140** |

---

## 🎯 Próximos Pasos Inmediatos

### Actual (Fase 2 - Backend Core):
1. ✅ PASO 2.1: DTOs creados
2. ✅ PASO 2.2: Cliente fmanagement creado
3. ✅ PASO 2.3: Módulo clients inicializado
4. 🔄 **PASO 2.4**: Implementar métodos en routercore.py (SIGUIENTE)
5. ⏭️ PASO 2.5: Crear endpoints en apicore.py

---

## 📚 Referencias

- **Plan completo**: `docs/EXPLORADOR_INTEGRATION_PLAN.md`
- **Componente origen**: `/Users/administrator/develop/reflex_components_templates/`
- **DDLs**: `infrastructure/database/ddl_version_*.sql`
- **Configuración fmanagement**: `infrastructure/environments/*/fmanagement_paths.yml`

---

**Última actualización**: 2026-02-03 (FASE 5 completada - Progreso 84% ✅)
