# Plan de Adaptación del Componente Explorador

**Fecha**: 2026-02-03  
**Componente Origen**: `/Users/administrator/develop/reflex_components_templates/reflex_components_templates/pages/explorador/explorador.py`  
**Líneas Totales**: 1,405 líneas  
**Objetivo**: Adaptar de JSON mockeado a APIs reales

---

## 1. ANÁLISIS DEL COMPONENTE ORIGINAL

### 1.1 Estructura de Datos

#### FolderItem (Pydantic Model)
```python
class FolderItem(pydantic.BaseModel):
    id: str
    name: str
    depth: int
    parent_id: str = ""
    is_expanded: bool = False
    has_children: bool = False
    is_visible: bool = True
    item_type: str = "folder"  # "folder" or "file"
    is_protected: bool = False  # Level 0 and 1 are protected
    is_blocked: bool = False  # Operational block
    size_str: str = ""
    metadata: dict = {}
    version_state_label: str = ""  # Ej: "(Bloqueada)"
    version_state_color: str = ""  # Ej: "#FF8C00"
    is_final_c: bool = False  # Flag cliente
    is_final_i: bool = False  # Flag interno
```

#### ExploradorState (Reflex State)
```python
class ExploradorState(rx.State):
    # Estructura de archivos
    items: list[FolderItem] = []
    fmanagementlist: dict = {}
    selected_item_id: str = ""
    
    # Estado de versión
    id_organizacion: int = 1
    id_proyecto: int = 1
    id_version_int: int = 1
    id_version: str = "v001"
    version_state: str = "Abierta"
    version_protected: bool = False
    version_final_c: bool = False
    version_final_i: bool = False
    version_size_bytes: int = 0
    version_states: dict = {}  # Estados de todas las versiones
    
    # Perfil de usuario
    user_id: int = 0
    user_name: str = "anonimo"
    user_id_organizacion: int = 1
    user_project_id: int = 1
    is_admin: bool = False
    is_internal_user: bool = False  # False = Cliente, True = Interno
    
    # Matriz de permisos
    permisos: dict = {
        "folder_create": False, "folder_delete": False, "folder_rename": False,
        "folder_read": False, "folder_list": False,
        "file_create": False, "file_read": False, "file_update": False,
        "file_delete": False, "file_list": False,
        "version_create": False
    }
```

### 1.2 Métodos Críticos a Adaptar

#### A. Carga de Datos (JSON → API)

1. **`init_page()`** - Inicializa la página
   - **Origen**: Llama a 3 métodos de carga JSON
   - **Destino**: Llamar APIs reales

2. **`load_from_json()`** - Carga estructura de archivos
   - **Origen**: Lee `data/proyecto.json`
   - **Destino**: Llamar `fmanagement_list()` API

3. **`load_version_state()`** - Carga estados de versiones
   - **Origen**: Lee `data/estado_version.json`
   - **Destino**: Llamar `get_version_state()` API

4. **`load_security_profile()`** - Carga permisos de usuario
   - **Origen**: Lee `data/seguridad.json`
   - **Destino**: Usar `SharedSessionState` (permisos ya cargados)

#### B. Operaciones CRUD (Simuladas → API)

5. **`acciones(accion, item)`** - Ejecuta operaciones
   - **Origen**: `rx.window_alert()` (simulación)
   - **Destino**: Llamar `fmanagement_operation()` API
   - **Acciones soportadas**:
     - `delete` → `fmanagement_operation("delete_folder"/"delete_file", params)`
     - `rename` → `fmanagement_operation("rename_folder"/"rename_file", params)`
     - `upload_file` → `fmanagement_operation("create_file", params)`
     - `download` → `fmanagement_operation("download_file", params)`
     - `block_version` → `update_version_state(state="Bloqueada", protected=True)`
     - `unblock_version` → `update_version_state(state="Abierta", protected=False)`

#### C. Lógica de Negocio (Mantener)

6. **`interpretacion_estados()`** - Aplica reglas visuales
   - **Sin cambios**: Lógica de negocio basada en estados
   - **Mapeo de estados**:
     ```python
     state_labels = {
         "Abierta": ("(Abierta)", "#228B22"),        # Verde
         "Bloqueada": ("(Bloqueada)", "#FF8C00"),    # Naranja
         "Protegida": ("(Entrenamiento Solicitado)", "#00008B"),  # Azul oscuro
         "Final": ("(Versión Final)", "#8B0000"),     # Rojo oscuro
     }
     ```

7. **`_flatten_recursive(json_items, depth, parent_id)`** - Aplana estructura JSON
   - **Mantener**: Convierte estructura jerárquica en lista plana
   - **Security by Design**: Niveles 0 y 1 protegidos

8. **`_update_visibility()`** - Actualiza visibilidad de items
   - **Mantener**: Colapso/expansión de carpetas

---

## 2. ESTRATEGIA DE ADAPTACIÓN

### 2.1 Integración con SharedSessionState

**Cambio Principal**: `ExploradorState` debe heredar de `SharedSessionState`

```python
from src.2_shared_application.reflex_shared.shared_session_state import SharedSessionState

class ExploradorState(SharedSessionState):
    # Heredamos automáticamente:
    # - user_id, organization_id, identity_type_id
    # - user_name, user_email
    # - is_logged_in, is_active
    # - access_token, session_token
    # - 38 permisos can_*
    
    # Solo añadimos campos específicos del explorador:
    items: list[FolderItem] = []
    fmanagementlist: dict = {}
    selected_item_id: str = ""
    # ... etc
```

**Ventajas**:
- ✅ Permisos automáticos desde sesión Redis
- ✅ Datos de usuario sincronizados
- ✅ Tokens JWT disponibles
- ✅ No duplicar código de seguridad

### 2.2 Adaptación de Métodos de Carga

#### A. `load_from_json()` → `load_from_api()`

**Antes** (JSON):
```python
def load_from_json(self):
    with open("data/proyecto.json", "r") as f:
        self.fmanagementlist = json.load(f)
    self.process_fmanagementlist()
```

**Después** (API):
```python
async def load_from_api(self):
    """Carga estructura de archivos desde fmanagement."""
    try:
        # Construir carpetas desde org/proyecto/versión
        org_folder = f"ORG{str(self.organization_id).zfill(4)}"
        prj_folder = f"PRJ{str(self.id_proyecto).zfill(4)}"
        version_folder = self.id_version  # ej: "v001"
        
        # Llamar API
        response = fmanagement_list(
            org_folder=org_folder,
            prj_folder=prj_folder,
            version_folder=version_folder,
            access_token=self.access_token,
            session_token=self.session_token,
        )
        
        if response.get("success"):
            self.fmanagementlist = {"items": response.get("items", [])}
            self.process_fmanagementlist()
        else:
            print(f"Error cargando fmanagement: {response.get('mensaje')}")
    except Exception as e:
        print(f"Error llamando fmanagement API: {e}")
```

#### B. `load_version_state()` → `load_version_state_from_api()`

**Antes** (JSON):
```python
def load_version_state(self):
    with open("data/estado_version.json", "r") as f:
        data = json.load(f)
        # Procesar array de estados
```

**Después** (API):
```python
async def load_version_state_from_api(self):
    """Carga estado de la versión actual desde API."""
    try:
        response = get_version_state(
            project_id=self.id_proyecto,
            version_id=self.id_version_int,
            access_token=self.access_token,
            session_token=self.session_token,
        )
        
        if response.get("success"):
            state_data = response.get("state", {})
            self.version_state = state_data.get("state", "Abierta")
            self.version_protected = state_data.get("protected", False)
            self.version_final_c = state_data.get("final_c", False)
            self.version_final_i = state_data.get("final_i", False)
            self.version_size_bytes = state_data.get("size_bytes", 0)
            
            # Guardar en diccionario local para interpretacion_estados()
            version_key = f"v{str(self.id_version_int).zfill(3)}"
            self.version_states[version_key] = state_data
        else:
            print(f"Error cargando estado versión: {response.get('mensaje')}")
    except Exception as e:
        print(f"Error llamando version_state API: {e}")
```

#### C. `load_security_profile()` → Eliminar (usar SharedSessionState)

**Antes** (JSON):
```python
def load_security_profile(self):
    with open("data/seguridad.json", "r") as f:
        data = json.load(f)
        self.user_id = data["usuario"]["user_id"]
        self.permisos = data["usuario"]["permisos"]
```

**Después** (Eliminar):
```python
# NO ES NECESARIO - Los datos vienen de SharedSessionState
# - self.user_id (heredado)
# - self.organization_id (heredado)
# - self.can_folder_create (heredado)
# - self.can_file_create (heredado)
# - etc... (38 permisos)
```

#### D. `acciones()` → Conectar con API

**Antes** (Simulado):
```python
def acciones(self, accion: str, item: FolderItem):
    if accion == "delete":
        return rx.window_alert(f"Simulando borrado de: {item.name}")
```

**Después** (API):
```python
async def acciones(self, accion: str, item: FolderItem):
    if item.is_protected and accion not in ["block_version", "unblock_version"]:
        return rx.window_alert(f"Elemento protegido: {item.name}")
    
    if accion == "delete":
        operation = "delete_folder" if item.item_type == "folder" else "delete_file"
        response = fmanagement_operation(
            operation=operation,
            params={
                "org": f"ORG{str(self.organization_id).zfill(4)}",
                "prj": f"PRJ{str(self.id_proyecto).zfill(4)}",
                "version": self.id_version,
                "path": item.name,
            },
            access_token=self.access_token,
            session_token=self.session_token,
        )
        
        if response.get("success"):
            # Recargar estructura
            await self.load_from_api()
            return rx.toast.success(f"Eliminado: {item.name}")
        else:
            return rx.toast.error(f"Error: {response.get('mensaje')}")
    
    elif accion == "block_version":
        response = update_version_state(
            project_id=self.id_proyecto,
            version_id=self.id_version_int,
            state="Bloqueada",
            protected=True,
            updated_by_user_id=self.user_id,
            access_token=self.access_token,
            session_token=self.session_token,
        )
        
        if response.get("success"):
            await self.load_version_state_from_api()
            self.interpretacion_estados()
            return rx.toast.success("Versión bloqueada")
        else:
            return rx.toast.error(f"Error: {response.get('mensaje')}")
    
    # ... otras acciones
```

### 2.3 Roles: Cliente vs Interno

**Mantener la lógica de roles** pero conectar con `SharedSessionState`:

```python
@rx.var
def is_internal_user(self) -> bool:
    """Usuario interno si tiene permiso training_create."""
    return self.can_training_create  # Heredado de SharedSessionState

@rx.var
def current_role_label(self) -> str:
    return "Interno" if self.is_internal_user else "Cliente"
```

---

## 3. PLAN DE IMPLEMENTACIÓN

### 3.1 Fase 6A: Copiar y Adaptar Estructura Base

**Archivos a crear**:
1. `src/apps/5_web_frontend/components/explorador.py`
2. `src/apps/6_web_backoffice/components/explorador.py`

**Cambios iniciales**:
- ✅ Heredar de `SharedSessionState`
- ✅ Importar funciones de `adapters/api_client.py`
- ✅ Mantener `FolderItem` sin cambios
- ✅ Simplificar campos duplicados (usar heredados)

### 3.2 Fase 6B: Adaptar Métodos de Carga

**Orden de implementación**:
1. ✅ `load_from_api()` - Reemplaza `load_from_json()`
2. ✅ `load_version_state_from_api()` - Reemplaza `load_version_state()`
3. ✅ Eliminar `load_security_profile()` - Usar SharedSessionState
4. ✅ Actualizar `init_page()` para llamar métodos async

### 3.3 Fase 6C: Conectar Operaciones CRUD

**Mapeo de acciones**:
| Acción Original | API Destino | Parámetros |
|-----------------|-------------|------------|
| `delete` (folder) | `fmanagement_operation("delete_folder", params)` | org, prj, version, path |
| `delete` (file) | `fmanagement_operation("delete_file", params)` | org, prj, version, path |
| `rename` (folder) | `fmanagement_operation("rename_folder", params)` | org, prj, version, old_name, new_name |
| `rename` (file) | `fmanagement_operation("rename_file", params)` | org, prj, version, old_name, new_name |
| `upload_file` | `fmanagement_operation("create_file", params)` | org, prj, version, folder, file_name, content |
| `download` | `fmanagement_operation("download_file", params)` | org, prj, version, file_path |
| `block_version` | `update_version_state(state="Bloqueada", protected=True)` | project_id, version_id |
| `unblock_version` | `update_version_state(state="Abierta", protected=False)` | project_id, version_id |

### 3.4 Fase 6D: Testing y Ajustes

**Validaciones**:
- ✅ Permisos por rol (cliente vs interno)
- ✅ Protección de niveles 0 y 1
- ✅ Estados de versión (Abierta, Bloqueada, Protegida, Final)
- ✅ Visualización de tamaños
- ✅ Colapso/expansión de carpetas

---

## 4. CONSIDERACIONES CRÍTICAS

### 4.1 Asincronía en Reflex

**Problema**: Reflex no soporta async/await en event handlers directamente.

**Solución**: Usar `yield` y llamadas síncronas con wrappers:

```python
def load_from_api(self):
    """Wrapper síncrono para llamada HTTP."""
    # Reflex maneja httpx internamente de forma síncrona
    response = fmanagement_list(...)  # Ya es síncrono en api_client.py
    if response.get("success"):
        self.fmanagementlist = {"items": response.get("items", [])}
        self.process_fmanagementlist()
    yield  # Actualiza UI
```

### 4.2 Endpoint fmanagement POST /fmo/newversion

**CRÍTICO**: Verificar si existe en el proyecto Go `fmanagement`.

**Si no existe**:
- Implementar en Go para soportar clonación de versiones
- Parámetros: `org_folder`, `prj_folder`, `version_folder`, `clone_from_version` (opcional)

### 4.3 Sincronización de Tamaños

**Problema**: `version_states.size_bytes` puede desincronizarse.

**Solución**:
- Backend Core calcula tamaño después de operaciones en fmanagement
- `update_version_state(size_bytes=calculated_size)`

---

## 5. RESUMEN DE CAMBIOS POR ARCHIVO

### Componente Explorador (Frontend/Backoffice)

| Elemento | Antes (JSON) | Después (API) | Líneas Afectadas |
|----------|--------------|---------------|------------------|
| `ExploradorState` | Hereda `rx.State` | Hereda `SharedSessionState` | 1 línea |
| `load_from_json()` | Lee JSON local | `fmanagement_list()` API | ~30 líneas |
| `load_version_state()` | Lee JSON local | `get_version_state()` API | ~40 líneas |
| `load_security_profile()` | Lee JSON local | **Eliminar** (usa SharedSessionState) | -40 líneas |
| `acciones()` | `rx.window_alert()` | `fmanagement_operation()` + `update_version_state()` | ~150 líneas |
| `interpretacion_estados()` | Sin cambios | Sin cambios | 0 líneas |
| `_flatten_recursive()` | Sin cambios | Sin cambios | 0 líneas |

**Total estimado**: ~180 líneas modificadas (de 1,405 líneas totales = 12.8%)

---

## 6. PRÓXIMOS PASOS

1. ✅ **PASO 6.3**: Crear `explorador.py` en Frontend
2. ✅ **PASO 6.4**: Crear `explorador.py` en Backoffice
3. ✅ **PASO 6.5**: Adaptar métodos de carga (JSON → API)
4. ✅ **PASO 6.6**: Conectar operaciones CRUD
5. ✅ **PASO 6.7**: Testing de integración

---

## 7. RIESGOS Y MITIGACIONES

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Endpoint `POST /fmo/newversion` no existe | Alto | Verificar Go fmanagement, implementar si falta |
| Asincronía en Reflex | Medio | Usar wrappers síncronos con `yield` |
| Tamaños desincronizados | Bajo | Actualizar `size_bytes` después de cada operación |
| Permisos inconsistentes | Alto | Validar en todas las capas (Security by Design) |
| Estructura JSON diferente | Medio | Adaptar `process_fmanagementlist()` según response real |

---

**Fin del documento**
