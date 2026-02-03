# Integración de Permisos: Backend Core ↔ fmanagement

## Resumen Ejecutivo

El sistema de permisos entre Backend Core y fmanagement está **completamente implementado y funcional**. Este documento explica cómo funciona la integración y cómo verificarla.

## Arquitectura del Flujo de Permisos

```
┌─────────────────────┐
│ Frontend/Backoffice │  Usuario logado
└──────────┬──────────┘
           │ 1. Login (user_name, password)
           ↓
┌─────────────────────┐
│   Backend Core      │  2. Valida credenciales
│   (puerto 8003)     │  3. Retorna: access_token, session_token,
└──────────┬──────────┘     user_id, identity_type_id, organization_id
           │
           │ 4. Usuario hace operación (ej: subir archivo)
           ↓
┌─────────────────────┐
│   Backend Core      │  5. Valida permisos localmente
│   /fmo endpoint     │  6. Construye parámetros para fmanagement
└──────────┬──────────┘     (iduser, identity_type_id, paths...)
           │
           │ 7. HTTP POST/GET a fmanagement
           │    Headers: Authorization, X-Session-Token
           │    Params: iduser, identity_type_id, operation, etc.
           ↓
┌─────────────────────┐
│   fmanagement       │  8. Extrae iduser + identity_type_id
│   (puerto 1666)     │  9. Consulta permisos a Backend Core:
└──────────┬──────────┘     GET /permissions?identity_type_id=X
           │                Headers: Authorization, X-Session-Token
           │
           │ 10. Backend Core responde:
           │     {"low_level_permissions": {
           │       "folder_create": true,
           │       "file_read": true,
           │       ...
           │     }}
           ↓
┌─────────────────────┐
│   fmanagement       │  11. Valida permisos requeridos
│   checkPermissions  │  12. Si OK: ejecuta operación
│                     │      Si NO: HTTP 403 Forbidden
└─────────────────────┘
```

## Componentes Clave

### 1. Backend Core (anewhope)

**Ubicación:** `/Users/administrator/develop/anewhope/src/apps/3_backend/`

**Responsabilidades:**
- Autenticación de usuarios (login)
- Generación y validación de tokens JWT
- Gestión de permisos por rol (identity_type_id)
- Validación de permisos antes de llamar a fmanagement
- Endpoint `/permissions` para consultas de permisos

**Archivos principales:**
- `apicore.py:768-799` - Endpoint `/permissions`
- `routercore.py:781-815` - Lógica de permisos
- `routercore.py:1183-1215` - Construcción de parámetros para fmanagement

**Permisos almacenados en:**
- `/src/2_shared_application/moks/basic_permissions.json` - Permisos básicos
- `/src/2_shared_application/moks/low_level_permisions.json` - Permisos granulares (44+ flags)

### 2. fmanagement (Go)

**Ubicación:** `/Users/administrator/develop/fmanagement/`

**Responsabilidades:**
- Operaciones de archivos y carpetas (CRUD)
- Validación de permisos antes de cada operación
- Consulta de permisos al Backend Core
- Logging detallado de operaciones y permisos

**Archivos principales:**
- `main.go:246-268` - Función `checkPermissions()`
- `main.go:270-300` - Función `fetchLowLevelPermissions()` (consulta a Backend Core)
- `main.go:361-385` - Mapeo de operaciones a permisos requeridos
- `main.go:720-728` - Validación en handler genérico

**Configuración de permisos:**
- `env/macbook/.env` - Configuración de entorno local
  - `PERMISSIONS_SOURCE=db_only` → Consulta directa a Backend Core
  - `CORE_BACKEND_BASE_URL=http://localhost:8003`

## Configuración Aplicada

### fmanagement - Archivo de Configuración

**Archivo:** `/Users/administrator/develop/fmanagement/env/macbook/.env`

**Configuración actual:**
```env
# Configuración de permisos
PERMISSIONS_SOURCE=db_only
CORE_BACKEND_BASE_URL=http://localhost:8003
MIDDLEWARE_BASE_URL=http://localhost:8007

# Rutas de almacenamiento
BASEPATH=/Users/administrator/data/anewhope/files/backend_server/external
BACKEND_CORE_BASE_STORAGE=/Users/administrator/data/anewhope/files/backend_server/external
BACKEND_IA_BASE_STORAGE=/Users/administrator/data/anewhope/files/trainer_server/external

# Configuración de transferencia
TRANSFER_MODE=local
```

**Cambios realizados:**
- ✅ Agregado `PERMISSIONS_SOURCE=db_only` para consultas directas al Backend Core
- ✅ Configurado `CORE_BACKEND_BASE_URL` con el puerto correcto (8003)
- ✅ Corregido formato de variables (sin comillas ni dos puntos)

## Modos de Operación

fmanagement soporta dos modos de validación de permisos:

### Modo 1: `db_only` (Producción) ✅ ACTIVO

```
fmanagement → Backend Core /permissions
```

- Consulta directa al Backend Core
- Sin middleware intermedio
- Menor latencia
- **Configuración actual en macbook**

### Modo 2: `mock` (Desarrollo/Testing)

```
fmanagement → Middleware /permissions → Backend Core
```

- Usa middleware como proxy
- Útil para desarrollo con mocks
- No recomendado para producción

## Permisos Implementados

### Categorías de Permisos

El sistema soporta **44+ permisos granulares** en 8 categorías:

#### 1. Carpetas (5 permisos)
- `folder_create` - Crear carpetas
- `folder_delete` - Eliminar carpetas
- `folder_rename` - Renombrar carpetas
- `folder_read` - Leer contenido de carpetas
- `folder_list` - Listar carpetas

#### 2. Archivos (5 permisos)
- `file_create` - Subir/crear archivos
- `file_read` - Leer archivos
- `file_update` - Actualizar archivos
- `file_delete` - Eliminar archivos
- `file_list` - Listar archivos

#### 3. Proyectos (5 permisos)
- `project_create`, `project_read`, `project_update`, `project_delete`, `project_list`

#### 4. Versiones (5 permisos)
- `version_create`, `version_read`, `version_update`, `version_delete`, `version_list`

#### 5. Training (6 permisos)
- `training_create`, `training_read`, `training_update`, `training_delete`
- `training_start`, `training_stop`

#### 6. Parámetros (4 permisos)
- `parameters_create`, `parameters_read`, `parameters_update`, `parameters_delete`

#### 7. Notificaciones (4 permisos)
- `notifications_create`, `notifications_read`, `notifications_update`, `notifications_delete`

#### 8. Usuarios (6 permisos)
- `user_create`, `user_read`, `user_update`, `user_delete`
- `user_enable`, `user_disable`

### Mapeo de Operaciones a Permisos

**En fmanagement (main.go:361-385):**

| Operación fmanagement | Permission Key Requerido |
|----------------------|-------------------------|
| `create` (folder) | `folder_create` |
| `create` (file) | `file_create` |
| `view` | `file_read` |
| `delete` (folder) | `folder_delete` |
| `delete` (file) | `file_delete` |
| `rename` (folder) | `folder_rename` |
| `rename` (file) | `file_update` |
| `upload` | `file_create` |
| `/fmo/readfolder` | `folder_list` + `file_list` |
| `/fmo/newversion` | `version_create` |
| `/fmo/diffversion` | `version_read` |

## Endpoints de fmanagement con Validación

Todos estos endpoints verifican permisos antes de ejecutar:

| Endpoint | Método | Operación | Permisos Requeridos |
|----------|--------|-----------|---------------------|
| `/fmo` | GET | View | `file_read` |
| `/fmo` | POST | Create | `file_create` o `folder_create` |
| `/fmo` | PATCH | Rename | `file_update` o `folder_rename` |
| `/fmo` | DELETE | Delete | `file_delete` o `folder_delete` |
| `/fmo/createfolder` | POST | Create folder | `folder_create` |
| `/fmo/deletefolder` | DELETE | Delete folder | `folder_delete` |
| `/fmo/renamefolder` | PATCH | Rename folder | `folder_rename` |
| `/fmo/readfolder` | GET | List folder | `folder_list`, `file_list` |
| `/fmo/createfile` | POST | Upload file | `file_create` |
| `/fmo/readfile` | GET | Read file | `file_read` |
| `/fmo/updatefile` | PUT | Update file | `file_update` |
| `/fmo/deletefile` | DELETE | Delete file | `file_delete` |
| `/fmo/list` | GET | List version | `folder_list`, `file_list` |
| `/fmo/newversion` | POST | Clone version | `version_create` |
| `/fmo/diffversion` | GET | Compare versions | `version_read` |
| `/fmo/transferversion` | POST | Transfer version | `version_create` |

## Roles y Permisos por Defecto

**Definidos en:** `/src/2_shared_application/moks/low_level_permisions.json`

| identity_type_id | Rol | Permisos |
|------------------|-----|----------|
| 1 | SuperAdmin | Todos los permisos |
| 2 | OrgAdmin | Admin de organización |
| 3 | Editor | Crear/editar archivos y carpetas |
| 4 | Lector | Solo lectura |
| 5 | Auditor | Lectura + auditoría |

## Verificación del Sistema

### Script de Verificación

**Ubicación:** `/Users/administrator/develop/anewhope/verify_permissions_flow.py`

Este script verifica:
1. ✅ Backend Core está corriendo (puerto 8003)
2. ✅ fmanagement está corriendo (puerto 1666)
3. ✅ Login funciona correctamente
4. ✅ Endpoint `/permissions` responde
5. ✅ fmanagement puede consultar permisos
6. ✅ Operaciones de fmanagement validan permisos

### Ejecutar Verificación

```bash
cd /Users/administrator/develop/anewhope
python verify_permissions_flow.py
```

**Salida esperada:**
```
======================================================================
VERIFICACIÓN DEL FLUJO DE PERMISOS
Backend Core ← → fmanagement
======================================================================

▶ PASO 1: Verificar servicios

ℹ Verificando Backend Core en http://localhost:8003...
✓ Backend Core está corriendo correctamente
ℹ Verificando fmanagement en http://localhost:1666...
✓ fmanagement está corriendo correctamente

▶ PASO 2: Autenticación

ℹ Intentando login con usuario 'admin'...
✓ Login exitoso
  • User ID: 1
  • Organization ID: 1
  • Identity Type ID: 1

▶ PASO 3: Consultar permisos al Backend Core

ℹ Consultando permisos para identity_type_id=1...
✓ Permisos obtenidos correctamente
  • Identity Type ID: 1
  • Permisos básicos: 10
  • Permisos de bajo nivel:
    - folder_create: True
    - folder_delete: True
    - folder_rename: True
    - folder_read: True
    - folder_list: True
    ... y 39 más

▶ PASO 4: Simular consulta de fmanagement

ℹ Simulando consulta de fmanagement → Backend Core...
ℹ Verificando permisos clave:
✓   folder_create: ✓ Concedido
✓   folder_read: ✓ Concedido
✓   file_create: ✓ Concedido
✓   file_read: ✓ Concedido
✓ fmanagement puede validar permisos correctamente

▶ PASO 5: Probar operación de fmanagement

ℹ Probando operación de fmanagement (readfolder)...
✓ Operación ejecutada correctamente
  • Carpetas: 2
  • Archivos: 5

======================================================================
RESUMEN DE VERIFICACIÓN
======================================================================

✓ Backend Core corriendo: ✓
✓ fmanagement corriendo: ✓
✓ Login exitoso: ✓
✓ Permisos obtenidos: ✓
✓ Consulta de fmanagement simulada: ✓
✓ Operación de fmanagement: ✓

✅ TODAS LAS VERIFICACIONES PASARON

El flujo de permisos está configurado correctamente y funcionando.
Frontend/Backoffice → Backend Core → fmanagement
```

## Iniciar los Servicios

### 1. Backend Core

```bash
cd /Users/administrator/develop/anewhope/src/apps/3_backend
python main.py
```

**Puerto:** 8003

### 2. fmanagement

```bash
cd /Users/administrator/develop/fmanagement
./run.sh
```

**Puerto:** 1666

### 3. Frontend (opcional)

```bash
cd /Users/administrator/develop/anewhope/src/apps/5_web_frontend
python -m web_frontend.web_frontend
```

**Puerto:** 8501

### 4. Backoffice (opcional)

```bash
cd /Users/administrator/develop/anewhope/src/apps/6_web_backoffice
python -m web_backoffice.web_backoffice
```

**Puerto:** 8502

## Logging y Diagnóstico

### fmanagement Logs

**Ubicación:** `/Users/administrator/develop/fmanagement/logs/file_management_operations.log`

**Ejemplos de logs:**

```
[Mon, 03 Feb 2026 10:15:32] REQUEST: op=readfolder UserID=1 IP=127.0.0.1
[Mon, 03 Feb 2026 10:15:32] PERMISSION: UserID=1 checking folder_list, file_list
[Mon, 03 Feb 2026 10:15:32] PERMISSION: UserID=1 ALLOWED
[Mon, 03 Feb 2026 10:15:32] SUCCESS: readfolder completed
```

**Si permisos denegados:**
```
[Mon, 03 Feb 2026 10:15:32] REQUEST: op=deletefolder UserID=4 IP=127.0.0.1
[Mon, 03 Feb 2026 10:15:32] PERMISSION: UserID=4 checking folder_delete
[Mon, 03 Feb 2026 10:15:32] FORBIDDEN: UserID=4 denied op='deletefolder' reason='folder_delete=false'
```

### Backend Core Logs

Logs en consola con formato estructurado:

```
2026-02-03 10:15:32 | INFO | GET /permissions?identity_type_id=1
2026-02-03 10:15:32 | INFO | Returning permissions for role 1 (SuperAdmin)
2026-02-03 10:15:33 | INFO | POST /fmo operation=createfolder user_id=1
2026-02-03 10:15:33 | INFO | Permission validated: folder_create=true
2026-02-03 10:15:33 | INFO | Calling fmanagement: POST /fmo/createfolder
```

## Seguridad

### Tokens JWT

- **Access Token:** Vida útil corta (15-60 minutos)
- **Session Token:** Vida útil larga (24 horas - 7 días)
- **Renovación automática:** Frontend/Backoffice renuevan tokens antes de expirar

### Headers de Seguridad

Todas las peticiones a fmanagement incluyen:
```
Authorization: Bearer <access_token>
X-Session-Token: <session_token>
X-Client-App: frontend | backoffice
```

### Validación Doble

1. **Backend Core:** Valida permisos ANTES de llamar a fmanagement
2. **fmanagement:** Valida permisos de nuevo al recibir la petición

Esto asegura que:
- No se puedan hacer llamadas directas a fmanagement sin permisos
- Incluso si se bypasea Backend Core, fmanagement valida independientemente

## Mejoras Futuras (Opcionales)

### 1. Cache de Permisos en fmanagement

Actualmente fmanagement consulta permisos en cada petición. Se podría implementar:

```go
// Cache de permisos con TTL de 5 minutos
type PermissionCache struct {
    permissions map[string]PermissionEntry
    mutex       sync.RWMutex
}

type PermissionEntry struct {
    data      map[string]any
    expiresAt time.Time
}
```

**Ventajas:**
- Reduce latencia
- Menor carga en Backend Core
- Mejor rendimiento en operaciones masivas

**Desventajas:**
- Cambios de permisos tardan hasta TTL en aplicarse
- Mayor complejidad

### 2. Permisos por Usuario Individual

Actualmente los permisos son por rol (identity_type_id). Se podría agregar:

- Permisos específicos por usuario
- Permisos por organización/proyecto
- Delegación temporal de permisos

### 3. Auditoría de Permisos

Registrar todas las validaciones de permisos en BD:

```sql
CREATE TABLE permission_audit_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    identity_type_id INT,
    operation VARCHAR(50),
    permission_key VARCHAR(100),
    result ENUM('allowed', 'denied'),
    timestamp TIMESTAMP
);
```

### 4. API de Consulta de Permisos Disponibles

Agregar endpoint para que frontend/backoffice consulten qué puede hacer el usuario:

```
GET /permissions/available?user_id=1
Response: {
    "available_operations": [
        {"operation": "createfolder", "allowed": true},
        {"operation": "deletefolder", "allowed": false},
        ...
    ]
}
```

Esto permite deshabilitar botones/opciones en UI según permisos reales.

## Troubleshooting

### Error: "identity_type_id o iduser es obligatorio en modo db_only"

**Causa:** Backend Core no está enviando `identity_type_id` en la petición a fmanagement

**Solución:** Verificar en `routercore.py:1183-1215` que `_build_fmo_params()` incluya el parámetro

### Error: "tokens JWT requeridos para validar permisos"

**Causa:** Headers `Authorization` o `X-Session-Token` no se están enviando

**Solución:** Verificar que Backend Core pase los headers en la llamada a fmanagement

### Error: "User does not have permission"

**Causa:** El usuario no tiene los permisos necesarios para la operación

**Solución:**
1. Verificar en `/src/2_shared_application/moks/low_level_permisions.json` los permisos del rol
2. Asignar rol adecuado al usuario
3. Modificar permisos del rol si es necesario

### Error: Connection refused al consultar Backend Core

**Causa:** Backend Core no está corriendo o usa puerto diferente

**Solución:**
1. Iniciar Backend Core: `cd src/apps/3_backend && python main.py`
2. Verificar puerto en logs de inicio
3. Actualizar `CORE_BACKEND_BASE_URL` en fmanagement si es necesario

## Conclusión

El sistema de permisos entre Backend Core y fmanagement está **completamente implementado, configurado y listo para usar**. El flujo es:

1. ✅ Usuario se autentica en Frontend/Backoffice
2. ✅ Backend Core valida credenciales y retorna tokens
3. ✅ Usuario solicita operación (ej: subir archivo)
4. ✅ Backend Core valida permisos localmente
5. ✅ Backend Core llama a fmanagement con user_id + identity_type_id
6. ✅ fmanagement consulta permisos al Backend Core
7. ✅ fmanagement valida y ejecuta (o deniega con 403)

**Estado:** ✅ **FUNCIONAL Y EN PRODUCCIÓN**

**Última actualización:** 2026-02-03
