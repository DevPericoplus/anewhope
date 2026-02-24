# Flujo de Creación de Versiones

## Resumen

Este documento describe el flujo completo end-to-end para la creación de versiones de proyectos en Anewhope, desde el click en el botón "Crear nueva versión" en el frontend hasta la creación física de carpetas en fmanagement.

## Arquitectura del Flujo

```
Frontend (Reflex)
    ↓ HTTP POST /proyectos/{id}/versiones/crear-completa
Middleware (7_service_frontend)
    ↓ HTTP POST a Broker
Broker (8_service_backend)
    ↓ HTTP POST a Backend Core
Backend Core (3_backend)
    ├──→ MariaDB (bases de datos: versiones, estado, eventos)
    └──→ fmanagement (API Go) → Sistema de archivos físico
```

## Flujo Detallado

### 1. Frontend → Middleware

**Archivo**: `src/apps/5_web_frontend/adapters/api_client.py:create_version_full()`

**Request**:
```python
POST /proyectos/{project_id}/versiones/crear-completa
Headers:
  - Authorization: Bearer {access_token}
  - X-Session-Token: {session_token}
Body:
  {
    "id_organizacion": 1,
    "nombre_version": "v002",  # Opcional, calculado automáticamente
    "user_id": 123,
    "user_name": "usuario@example.com",
    "descripcion": "Nueva versión", # Opcional
    "clone_from_version_id": 1,  # Opcional: clonar desde esta versión
    "initial_state": "Abierta",
    "protected": false,
    "final_c": false,
    "final_i": false
  }
```

### 2. Middleware → Broker

**Archivo**: `src/apps/7_service_frontend/apife.py` y `broker_backend_client.py`

El middleware valida tokens y reenvía al broker sin modificaciones.

### 3. Broker → Backend Core

**Archivo**: `src/apps/8_service_backend/apibe.py` y `interfacetocore.py`

El broker añade traceability y reenvía al backend core.

### 4. Backend Core: Procesamiento

**Archivo**: `src/apps/3_backend/routercore.py:create_version_full()`

#### Paso 1: Calcular siguiente versión

```sql
SELECT COALESCE(MAX(id_version), 0) + 1 as next_version
FROM versiones
WHERE id_proyecto = :project_id AND id_organizacion = :org_id
```

Resultado: `version_id = 3` → `version_folder = "v003"`

#### Paso 2: Insertar en tabla versiones

```sql
INSERT INTO versiones (id_version, id_proyecto, id_organizacion)
VALUES (:id_version, :project_id, :org_id)
```

#### Paso 3: Crear estructura física en fmanagement

**Archivo**: `src/apps/3_backend/clients/fmanagement_client.py`

**Lógica de decisión**:

```python
if version_id == 1:
    # Primera versión: crear vacía con estructura base
    # Usa: create_folder() para crear ORG.../PRJ.../v001/
    # Crea subcarpetas: datos/, modelos/, evaluaciones/, resultados/
    clone_from = None

elif clone_from_version is not None:
    # Clonar desde versión específica
    clone_from = f"v{clone_from_version:03d}"

else:
    # Clonar desde versión anterior (por defecto)
    clone_from = f"v{(version_id - 1):03d}"
```

**Cliente fmanagement**:

```python
# A) Si clone_from is None → Crear versión vacía
client._create_empty_version(
    orgpath="ORG0001",
    prjpath="PRJ00001",
    versionpath="v001",
    identity_type_id=10,
    iduser=123
)
# → POST /fmo/createfolder (múltiples veces)

# B) Si clone_from is not None → Clonar versión
client._clone_version(
    orgpath="ORG0001",
    prjpath="PRJ00001",
    source_version="v002",  # Versión ORIGEN
    identity_type_id=10,
    iduser=123
)
# → POST /fmo/newversion
# fmanagement calcula automáticamente next_version = v003
```

#### Paso 4: Crear estado inicial

```sql
INSERT INTO version_states (
    id_organizacion, id_proyecto, id_version,
    state, protected, size_bytes, final_c, final_i,
    updated_by_user_id
) VALUES (
    :org_id, :project_id, :version_id,
    'Abierta', FALSE, 0, FALSE, FALSE,
    :user_id
)
```

#### Paso 5: Registrar evento

```sql
INSERT INTO version_events (
    id_organizacion, id_proyecto, id_version,
    evento, mensaje, user_id, user_name
) VALUES (
    :org_id, :project_id, :version_id,
    'VERSION_CREADA',
    'Versión v003 creada desde Proyecciones (clonada desde v002)',
    :user_id,
    :user_name
)
```

### 5. fmanagement: Operaciones en Disco

**Aplicación**: `~/develop/fmanagement` (Go)

**Base de archivos**: `/tmp/tfmmyllm/files/default/` (configurable)

#### A) Crear versión vacía (v001)

**Endpoint**: `POST /fmo/createfolder` (múltiples llamadas)

**Estructura creada**:
```
/tmp/tfmmyllm/files/default/
└── ORG0001/
    └── PRJ00001/
        └── v001/
            ├── datos/
            ├── modelos/
            ├── evaluaciones/
            └── resultados/
```

#### B) Clonar versión (v002+)

**Endpoint**: `POST /fmo/newversion`

**Request**:
```json
{
  "iduser": 123,
  "basepath": "default",
  "orgpath": "ORG0001",
  "prjpath": "PRJ00001",
  "versionpath": "v002",  // Versión ORIGEN (a clonar)
  "identity_type_id": 10
}
```

**Proceso interno en fmanagement**:
1. Recibe `versionpath = "v002"` (origen)
2. Calcula automáticamente `next_version = "v003"` con `incrementVersion()`
3. Clona recursivamente: `ORG.../PRJ.../v002/` → `ORG.../PRJ.../v003/`

**Response**:
```json
{
  "status": "success",
  "message": "New version created successfully",
  "old_version": "v002",
  "new_version": "v003",
  "path": "/tmp/tfmmyllm/files/default/ORG0001/PRJ00001/v003"
}
```

## Casos de Uso

### Caso 1: Crear primera versión (v001)

**Acción**: Usuario hace click en "Crear nueva versión" en proyecto sin versiones

**Flujo**:
1. Frontend detecta que no hay versiones previas
2. Envía `clone_from_version_id = None`
3. Backend calcula `version_id = 1`
4. Backend crea estructura vacía con `create_folder`
5. Se crean carpetas: `v001/datos/`, `v001/modelos/`, etc.

**Resultado**: `ORG0001/PRJ00001/v001/` con estructura base vacía

### Caso 2: Crear versión clonando la anterior (v002 desde v001)

**Acción**: Usuario hace click en "Crear nueva versión" con v001 seleccionada

**Flujo**:
1. Frontend envía `clone_from_version_id = None` (usar anterior automática)
2. Backend calcula `version_id = 2`
3. Backend determina `clone_from = "v001"` (versión anterior)
4. Backend llama a fmanagement con `/fmo/newversion` pasando `versionpath="v001"`
5. fmanagement clona `v001/` → `v002/`

**Resultado**: `ORG0001/PRJ00001/v002/` con copia completa de v001

### Caso 3: Crear versión clonando una específica (v007 desde v003)

**Acción**: Usuario selecciona v003, hace click en "Crear nueva versión"

**Flujo**:
1. Frontend envía `clone_from_version_id = 3`
2. Backend calcula `version_id = 7` (siguiente disponible)
3. Backend determina `clone_from = "v003"` (especificada)
4. Backend llama a fmanagement con `/fmo/newversion` pasando `versionpath="v003"`
5. fmanagement clona `v003/` → `v004` (ERROR!)

**IMPORTANTE**: fmanagement calcula automáticamente la SIGUIENTE versión.
Si se pasa `versionpath=v003`, creará `v004`, no `v007`.

**Solución actual**: El parámetro `clone_from_version_id` clona desde esa versión pero crea la SIGUIENTE secuencial, no permite saltar versiones.

## Limitaciones Actuales

### 1. No se pueden saltar versiones

**Problema**: fmanagement siempre calcula la siguiente versión secuencial.

**Ejemplo**: Si existe v001, v002, v003, y quieres crear v007 clonando desde v002:
- Backend calcula correctamente `version_id = 4` (siguiente en DB)
- Backend pasa `versionpath="v002"` a fmanagement
- fmanagement crea `v003` (siguiente a v002), no `v004`

**Impacto**: Hay desalineación entre DB y filesystem.

**Solución propuesta**: Modificar fmanagement para aceptar `target_version` como parámetro.

### 2. No hay rollback de filesystem en caso de error

**Problema**: Si la transacción DB falla después de crear carpetas en fmanagement, las carpetas quedan huérfanas.

**Solución propuesta**: Implementar rollback físico usando endpoint `/fmo/deletefolder` en caso de error.

## Tablas de Base de Datos Involucradas

### versiones

```sql
CREATE TABLE versiones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_proyecto INT NOT NULL,
    id_organizacion INT NOT NULL,
    id_version INT NOT NULL,  -- Número secuencial 1, 2, 3...
    fecha_lanzamiento DATE NOT NULL,
    descripcion TEXT,
    archivo_bloqueo BLOB,
    creado_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY (id_proyecto, id_organizacion, id_version)
);
```

### version_states (si existe)

Guarda el estado de cada versión: Abierta, Bloqueada, Protegida, Final.

### version_events (si existe)

Auditoría de eventos: VERSION_CREADA, VERSION_BLOQUEADA, etc.

## Configuración

### fmanagement

**Archivo**: `infrastructure/config/fmanagement.yaml` o similar

```yaml
base_url: http://localhost:1666
base_path: /tmp/tfmmyllm/files/default
timeout: 30
```

### Backend Core

**Carga configuración** en: `src/apps/3_backend/routercore.py:load_fmanagement_settings()`

## Testing

### Test Manual

```bash
# 1. Crear primera versión (v001)
curl -X POST http://localhost:8000/proyectos/1/versiones/crear-completa \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_organizacion": 1,
    "user_id": 1,
    "user_name": "test@example.com",
    "identity_type_id": 10
  }'

# 2. Crear segunda versión clonando v001
curl -X POST http://localhost:8000/proyectos/1/versiones/crear-completa \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_organizacion": 1,
    "user_id": 1,
    "user_name": "test@example.com",
    "identity_type_id": 10,
    "clone_from_version_id": 1
  }'
```

### Verificar Resultado

```bash
# Verificar en DB
mysql -u myllm_writer -p myllm_projects_db \
  -e "SELECT * FROM versiones WHERE id_proyecto = 1"

# Verificar en filesystem
ls -la /tmp/tfmmyllm/files/default/ORG0001/PRJ00001/
```

## Próximos Pasos / TODOs

1. ✅ Implementar creación de v001 vacía
2. ✅ Implementar clonación de versiones
3. ⏳ Añadir soporte para especificar versión target en fmanagement
4. ⏳ Implementar rollback de filesystem en caso de error DB
5. ⏳ Añadir validaciones de permisos en cada paso
6. ⏳ Implementar eventos asíncronos para notificar creación de versión
7. ⏳ Añadir métricas y monitoring del proceso

## Referencias

- **fmanagement API**: `~/develop/fmanagement/README.md`
- **fmanagement Swagger**: `~/develop/fmanagement/swagger.yaml`
- **Backend Core Router**: `src/apps/3_backend/routercore.py`
- **Cliente fmanagement**: `src/apps/3_backend/clients/fmanagement_client.py`
- **Frontend API Client**: `src/apps/5_web_frontend/adapters/api_client.py`
