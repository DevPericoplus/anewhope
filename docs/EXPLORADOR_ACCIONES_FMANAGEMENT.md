# Mapeo de Acciones del Explorador a Endpoints de fmanagement

## Resumen

Este documento mapea cada acción del componente explorador a sus correspondientes endpoints REST de fmanagement, describiendo el flujo completo de cada operación.

## Flujo General

```
1. Usuario interactúa con el explorador (clic derecho → acción)
   ↓
2. Componente valida permisos locales (security by design - UI)
   ↓
3. Llamada a función del api_client
   ↓
4. Frontend → Middleware → Broker → Backend Core → fmanagement
   ↓
5. fmanagement valida permisos (segunda capa con low_level_permissions)
   ↓
6. fmanagement ejecuta operación en disco
   ↓
7. Se registra en tabla cambios (backend core)
   ↓
8. Respuesta exitosa → Refrescar explorador con nuevo list
   ↓
9. Usuario ve el resultado actualizado
```

---

## OPERACIONES CON CARPETAS

### 1. Crear Carpeta

**Acción del explorador**: `acciones("create_folder", item)`

**Endpoint**: `POST /fmo/createfolder`

**Parámetros**:
```
Body (application/x-www-form-urlencoded):
- iduser: int (ID del usuario)
- orgpath: str (ej: "ORG0001")
- prjpath: str (ej: "PRJ00001")
- versionpath: str (ej: "v001")
- subfolders: str (ruta relativa donde crear, ej: "docs/images")
- folder_name: str (nombre de la carpeta a crear, ej: "nueva_carpeta")
- identity_type_id: int (para validación de permisos)

Headers:
- Authorization: Bearer {access_token}
- X-Session-Token: {session_token}
```

**Respuesta exitosa**:
```json
{
    "status": "success",
    "message": "Folder created successfully",
    "path": "/data/files/external/ORG0001/PRJ00001/v001/docs/images/nueva_carpeta"
}
```

**Permiso requerido**: `folder_create`

**Registro en BD**:
- Tabla: `cambios`
- tipo_cambio: `"folder_create"`
- descripcion: `"Carpeta 'nueva_carpeta' creada en docs/images/"`

---

### 2. Renombrar Carpeta

**Acción del explorador**: `acciones("rename", item)` (cuando item es carpeta)

**Endpoint**: `PATCH /fmo/renamefolder`

**Parámetros**:
```
Body (application/x-www-form-urlencoded):
- iduser: int
- orgpath: str
- prjpath: str
- versionpath: str
- subfolders: str (ruta hasta la carpeta padre, ej: "docs")
- new_filename: str (nuevo nombre de la carpeta, sin path)
- identity_type_id: int

Headers:
- Authorization: Bearer {access_token}
- X-Session-Token: {session_token}
```

**Respuesta exitosa**:
```json
{
    "status": "success",
    "message": "Folder renamed successfully",
    "old": "old_folder_name",
    "new": "new_folder_name"
}
```

**Permiso requerido**: `folder_rename`

**Registro en BD**:
- Tabla: `cambios`
- tipo_cambio: `"folder_rename"`
- descripcion: `"Carpeta 'old_name' renombrada a 'new_name'"`

---

### 3. Eliminar Carpeta

**Acción del explorador**: `acciones("delete", item)` (cuando item es carpeta)

**Endpoint**: `DELETE /fmo/deletefolder`

**Parámetros**:
```
Query params:
- iduser: int
- orgpath: str
- prjpath: str
- versionpath: str
- subfolders: str (ruta completa a la carpeta, ej: "docs/images/carpeta_a_eliminar")
- identity_type_id: int

Headers:
- Authorization: Bearer {access_token}
- X-Session-Token: {session_token}
```

**Respuesta exitosa**:
```json
{
    "status": "success",
    "message": "Folder deleted successfully",
    "path": "/data/files/external/ORG0001/PRJ00001/v001/docs/images/carpeta_eliminada"
}
```

**Permiso requerido**: `folder_delete`

**Protecciones**:
- No permite eliminar carpetas de nivel 0 (proyecto) o nivel 1 (versión)
- Validación `is_protected` en el frontend

**Registro en BD**:
- Tabla: `cambios`
- tipo_cambio: `"folder_delete"`
- descripcion: `"Carpeta 'folder_name' eliminada de path/"`

---

### 4. Ver Propiedades de Carpeta

**Acción del explorador**: `acciones("properties", item)` (cuando item es carpeta)

**Endpoint**: `GET /fmo/readfolder`

**Parámetros**:
```
Query params:
- iduser: int
- orgpath: str
- prjpath: str
- versionpath: str
- subfolders: str (ruta a la carpeta)
- identity_type_id: int

Headers:
- Authorization: Bearer {access_token}
- X-Session-Token: {session_token}
```

**Respuesta exitosa**:
```json
{
    "status": "success",
    "path": "/data/files/external/ORG0001/PRJ00001/v001/docs",
    "items": [
        {
            "name": "manual.pdf",
            "is_dir": false,
            "size_bytes": 1024000,
            "size_kb": 1000.0
        },
        {
            "name": "images",
            "is_dir": true,
            "size_bytes": 0,
            "size_kb": 0.0,
            "items": [...]
        }
    ]
}
```

**Permiso requerido**: `folder_read`

**No modifica BD** (solo lectura)

---

## OPERACIONES CON ARCHIVOS

### 5. Subir Archivo

**Acción del explorador**: `acciones("upload_file", item)`

**Endpoint**: `POST /fmo/createfile`

**Parámetros**:
```
Query params:
- iduser: int
- orgpath: str
- prjpath: str
- versionpath: str
- subfolders: str (ruta donde subir, ej: "docs")
- filename: str (nombre sin extensión, ej: "manual")
- extfile: str (extensión sin punto, ej: "pdf")
- identity_type_id: int

Body (multipart/form-data):
- file: binary (contenido del archivo)

Headers:
- Authorization: Bearer {access_token}
- X-Session-Token: {session_token}
```

**Respuesta exitosa**:
```json
{
    "status": "success",
    "message": "File created successfully",
    "path": "/data/files/external/ORG0001/PRJ00001/v001/docs/manual.pdf"
}
```

**Permiso requerido**: `file_create`

**Registro en BD**:
- Tabla: `cambios`
- tipo_cambio: `"file_create"`
- descripcion: `"Archivo 'manual.pdf' subido a docs/"`

---

### 6. Descargar Archivo

**Acción del explorador**: `acciones("download", item)`

**Endpoint**: `GET /fmo` (con operation=view)

**Parámetros**:
```
Query params:
- iduser: int
- orgpath: str
- prjpath: str
- versionpath: str
- subfolders: str (ruta del archivo)
- filename: str (nombre sin extensión)
- extfile: str (extensión sin punto)
- operation: "view"
- identity_type_id: int

Headers:
- Authorization: Bearer {access_token}
- X-Session-Token: {session_token}
```

**Respuesta exitosa**:
- Content-Type: según el tipo de archivo
- Body: contenido binario del archivo

**Permiso requerido**: `file_read`

**No modifica BD** (solo lectura)

---

### 7. Renombrar Archivo

**Acción del explorador**: `acciones("rename", item)` (cuando item es archivo)

**Endpoint**: `PATCH /fmo` (con operation=rename)

**Parámetros**:
```
Query params:
- iduser: int
- orgpath: str
- prjpath: str
- versionpath: str
- subfolders: str (ruta del archivo)
- filename: str (nombre actual sin extensión)
- extfile: str (extensión actual)
- new_filename: str (nuevo nombre sin extensión)
- new_extfile: str (nueva extensión)
- operation: "rename"
- identity_type_id: int

Headers:
- Authorization: Bearer {access_token}
- X-Session-Token: {session_token}
```

**Respuesta exitosa**:
```json
{
    "message": "Renamed successfully",
    "old": "old_file.txt",
    "new": "new_file.txt"
}
```

**Permiso requerido**: `file_update`

**Registro en BD**:
- Tabla: `cambios`
- tipo_cambio: `"file_rename"`
- descripcion: `"Archivo 'old.txt' renombrado a 'new.txt'"`

---

### 8. Eliminar Archivo

**Acción del explorador**: `acciones("delete", item)` (cuando item es archivo)

**Endpoint**: `DELETE /fmo/deletefile`

**Parámetros**:
```
Query params:
- iduser: int
- orgpath: str
- prjpath: str
- versionpath: str
- subfolders: str (ruta del archivo)
- filename: str (nombre sin extensión)
- extfile: str (extensión)
- identity_type_id: int

Headers:
- Authorization: Bearer {access_token}
- X-Session-Token: {session_token}
```

**Respuesta exitosa**:
```json
{
    "status": "success",
    "message": "File deleted successfully",
    "path": "/data/files/external/ORG0001/PRJ00001/v001/docs/file.txt"
}
```

**Permiso requerido**: `file_delete`

**Registro en BD**:
- Tabla: `cambios`
- tipo_cambio: `"file_delete"`
- descripcion: `"Archivo 'file.txt' eliminado de docs/"`

---

### 9. Ver Propiedades de Archivo

**Acción del explorador**: `acciones("properties", item)` (cuando item es archivo)

**Endpoint**: `GET /fmo/readfile`

**Parámetros**:
```
Query params:
- iduser: int
- orgpath: str
- prjpath: str
- versionpath: str
- subfolders: str (ruta del archivo)
- filename: str (nombre sin extensión)
- extfile: str (extensión)
- identity_type_id: int

Headers:
- Authorization: Bearer {access_token}
- X-Session-Token: {session_token}
```

**Respuesta exitosa**:
```json
{
    "status": "success",
    "name": "manual",
    "extension": "pdf",
    "path": "/data/files/external/ORG0001/PRJ00001/v001/docs/manual.pdf",
    "size_bytes": 1024000,
    "size_kb": 1000.0
}
```

**Permiso requerido**: `file_read`

**No modifica BD** (solo lectura)

---

### 10. Actualizar Archivo

**Acción del explorador**: `acciones("update_file", item)` (nueva acción)

**Endpoint**: `PUT /fmo/updatefile`

**Parámetros**:
```
Body (multipart/form-data):
- iduser: int
- orgpath: str
- prjpath: str
- versionpath: str
- subfolders: str
- filename: str
- extfile: str
- identity_type_id: int
- file: binary (nuevo contenido)
```

**Respuesta exitosa**:
```json
{
    "status": "success",
    "message": "File updated successfully",
    "path": "/data/files/external/ORG0001/PRJ00001/v001/docs/manual.pdf",
    "size_bytes": 1048576,
    "size_kb": 1024.0
}
```

**Permiso requerido**: `file_update`

**Registro en BD**:
- Tabla: `cambios`
- tipo_cambio: `"file_update"`
- descripcion: `"Archivo 'manual.pdf' actualizado"`

---

## OPERACIÓN DE REFRESCO

### 11. Refrescar Explorador

**Acción**: Después de cualquier operación exitosa

**Endpoint**: `GET /fmo/list`

**Parámetros**:
```
Query params:
- iduser: int
- orgpath: str
- prjpath: str
- versionpath: str
- subfolders: "" (vacío para listar desde raíz de versión)
- identity_type_id: int

Headers:
- Authorization: Bearer {access_token}
- X-Session-Token: {session_token}
```

**Respuesta**: Estructura jerárquica completa (ver formato en EXPLORADOR_ADAPTADOR_USO.md)

**Procesamiento**:
1. Respuesta de fmanagement → Adaptador
2. Adaptador → Formato explorador
3. `process_fmanagementlist()` → Actualiza items
4. UI se actualiza automáticamente (Reflex reactivity)

---

## UTILIDADES PARA CONSTRUCCIÓN DE PARÁMETROS

### Extraer información del path de un item

Cada `FolderItem` tiene:
- `id`: ID jerárquico (ej: "0_1_2_3")
- `name`: Nombre del item
- `depth`: Profundidad (0=proyecto, 1=versión, 2+=contenido)
- `parent_id`: ID del padre
- `metadata`: Diccionario con info adicional

**Construcción de `subfolders`**:
```python
def build_subfolders_path(item: FolderItem, items: list[FolderItem]) -> str:
    """Construye la ruta de subfolders para fmanagement."""
    path_parts = []
    current = item

    while current.parent_id and current.depth > 1:
        # Buscar el padre
        parent = next((i for i in items if i.id == current.parent_id), None)
        if not parent:
            break

        if parent.depth > 1:  # Solo añadir si no es proyecto ni versión
            path_parts.insert(0, parent.name)

        current = parent

    return "/".join(path_parts) if path_parts else ""
```

**Separación de nombre y extensión**:
```python
def split_filename(name: str) -> tuple[str, str]:
    """Separa nombre y extensión de un archivo."""
    if "." in name:
        parts = name.rsplit(".", 1)
        return parts[0], parts[1]
    return name, ""
```

---

## FLUJO COMPLETO DE EJEMPLO: CREAR CARPETA

1. **Usuario**: Clic derecho en "docs" → "Crear Carpeta"
2. **UI**: Prompt para nombre → Usuario ingresa "nuevos_archivos"
3. **Validación local**: `can_folder_create == True`?
4. **Construcción de parámetros**:
   ```python
   subfolders = "docs"  # path hasta donde crear
   folder_name = "nuevos_archivos"  # nombre de la nueva carpeta
   ```
5. **Llamada API**:
   ```python
   response = fmanagement_create_folder(
       org_id=1,
       project_id=1,
       version_name="v001",
       subfolders="docs",
       folder_name="nuevos_archivos",
       access_token=state.access_token,
       session_token=state.session_token,
       user_id=state.user_id,
       identity_type_id=state.identity_type_id
   )
   ```
6. **fmanagement**: Valida permisos → Crea carpeta en disco
7. **Backend Core**: Registra en tabla cambios
8. **Respuesta OK**: `{"status": "success", ...}`
9. **Refrescar explorador**:
   ```python
   reload_explorador_data()
   ```
10. **Usuario ve**: Nueva carpeta "nuevos_archivos" dentro de "docs"

---

## PRÓXIMOS PASOS

1. ✅ Documentación completa de mapeo
2. ⏳ Implementar funciones en `api_client.py`:
   - `fmanagement_create_folder()`
   - `fmanagement_rename_folder()`
   - `fmanagement_delete_folder()`
   - `fmanagement_create_file()`
   - `fmanagement_rename_file()`
   - `fmanagement_delete_file()`
   - `fmanagement_download_file()`
   - `fmanagement_read_file_metadata()`
   - `fmanagement_read_folder_metadata()`
3. ⏳ Actualizar método `acciones()` en `ExploradorState`
4. ⏳ Añadir diálogos de confirmación en UI
5. ⏳ Implementar manejo de errores con mensajes al usuario
6. ⏳ Testing de cada operación
