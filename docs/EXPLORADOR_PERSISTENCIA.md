# Persistencia de Acciones del Explorador

## Resumen

El componente Explorador gestiona dos tipos de operaciones que requieren persistencia en diferentes tablas:

1. **Acciones a nivel de versión** → Tabla `version_states`
2. **Acciones con carpetas/archivos** → Tabla `cambios`

---

## 1. Tabla `version_states`

### Estructura
```sql
CREATE TABLE version_states (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_organizacion INT NOT NULL,
    id_proyecto INT NOT NULL,
    id_version INT NOT NULL,
    state ENUM('Abierta', 'Bloqueada', 'Protegida', 'Final') NOT NULL DEFAULT 'Abierta',
    protected TINYINT(1) NOT NULL DEFAULT 0,
    size_bytes BIGINT DEFAULT 0,
    final_c TINYINT(1) NOT NULL DEFAULT 0,
    final_i TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by_user_id INT,
    INDEX idx_org_proj (id_organizacion, id_proyecto),
    INDEX idx_state (state),
    INDEX idx_updated (updated_at)
);
```

### Acciones que actualizan `version_states`

| Acción | Campo(s) Actualizado(s) | Descripción |
|--------|------------------------|-------------|
| `solicitar_entrenamiento()` | `state='Protegida'`, `protected=1`, `final_c=1` | Cliente solicita entrenamiento |
| `confirmar_entrenamiento()` | `state='Final'`, `final_c=1`, `final_i=1` | Documentación lista para entrenamiento |
| `block_version` | `state='Bloqueada'`, `protected=1` | Admin bloquea la versión |
| `unblock_version` | `state='Abierta'`, `protected=0` | Admin desbloquea la versión |
| `review_version` | `state='Abierta'`, `protected=0`, `final_c=0` | Admin revierte a estado abierto |
| `set_version_state()` | `state`, `protected` | Cambio manual de estado |
| `set_version_protected()` | `protected` | Cambio manual de protección |
| `set_version_final_i()` | `final_i` | Cambio manual de flag interno |

### Flujo de estados

```
Abierta → Bloqueada (admin) → Abierta (admin)
   ↓
Protegida (cliente solicita entrenamiento, final_c=1)
   ↓
Final (interno confirma documentación, final_c=1, final_i=1)
```

### Implementación

Las actualizaciones deben realizarse mediante:
```
Frontend/Backoffice → Middleware → Broker → Backend Core → SQL UPDATE
```

Ejemplo de llamada a API:
```python
from adapters.api_client import update_version_state

update_version_state(
    organization_id=1,
    project_id=1,
    version_id=1,
    state="Protegida",
    protected=True,
    final_c=True,
    final_i=False,
    updated_by_user_id=user_id
)
```

---

## 2. Tabla `cambios`

### Estructura
```sql
CREATE TABLE cambios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_version INT NOT NULL,
    fecha_cambio DATE NOT NULL,
    tipo_cambio VARCHAR(255) NOT NULL,
    descripcion TEXT,
    creado_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    id_organizacion INT NOT NULL,
    id_proyecto INT NOT NULL,
    INDEX idx_org_proj (id_organizacion, id_proyecto),
    INDEX idx_version (id_version)
);
```

### Acciones que crean registros en `cambios`

| Acción | tipo_cambio | Descripción | Ejemplo descripcion |
|--------|-------------|-------------|---------------------|
| Crear carpeta | `folder_create` | Usuario crea una carpeta | `Carpeta 'docs' creada en v001/` |
| Renombrar carpeta | `folder_rename` | Usuario renombra carpeta | `Carpeta 'doc' renombrada a 'docs'` |
| Eliminar carpeta | `folder_delete` | Usuario elimina carpeta | `Carpeta 'tmp' eliminada de v001/` |
| Subir archivo | `file_create` | Usuario sube un archivo | `Archivo 'manual.pdf' subido a v001/docs/` |
| Actualizar archivo | `file_update` | Usuario actualiza archivo existente | `Archivo 'readme.txt' actualizado` |
| Renombrar archivo | `file_rename` | Usuario renombra archivo | `Archivo 'doc.txt' renombrado a 'documento.txt'` |
| Eliminar archivo | `file_delete` | Usuario elimina archivo | `Archivo 'temp.log' eliminado` |

### Campos requeridos

- `id_organizacion`: ID de la organización del contexto
- `id_proyecto`: ID del proyecto del contexto
- `id_version`: ID de la versión donde ocurrió el cambio
- `fecha_cambio`: Fecha de la operación (date)
- `tipo_cambio`: Tipo de operación (uno de los valores de la tabla anterior)
- `descripcion`: Descripción detallada de la operación

### Implementación

Las operaciones con archivos deben:
1. Ejecutar la operación en el filesystem (vía fmanagement)
2. Registrar el cambio en la tabla `cambios`

Ejemplo:
```python
from adapters.api_client import fmanagement_operation, register_change
from datetime import date

# 1. Ejecutar operación en filesystem
response = fmanagement_operation(
    operation="create_folder",
    path="/v001/docs",
    organization_id=1,
    project_id=1
)

# 2. Registrar en cambios si la operación fue exitosa
if response["success"]:
    register_change(
        id_organizacion=1,
        id_proyecto=1,
        id_version=1,
        fecha_cambio=date.today(),
        tipo_cambio="folder_create",
        descripcion=f"Carpeta 'docs' creada en v001/"
    )
```

---

## 3. Flujo completo de una operación

### Ejemplo: Usuario crea una carpeta

```
1. Usuario hace clic derecho → "Crear Carpeta"
   ↓
2. Frontend/Backoffice: ExploradorState.acciones("create_folder", item)
   ↓
3. API Client: fmanagement_operation(operation="create_folder", ...)
   ↓
4. Middleware: Valida token, forward a Broker
   ↓
5. Broker: Enruta a Backend Core
   ↓
6. Backend Core: Llama a fmanagement service
   ↓
7. fmanagement: Crea carpeta en filesystem
   ↓
8. Backend Core: Registra en tabla cambios
   ↓
9. Response → Frontend: Actualiza UI
```

### Ejemplo: Usuario solicita entrenamiento

```
1. Usuario hace clic en "El cliente solicita entrenamiento"
   ↓
2. Frontend: ExploradorState.solicitar_entrenamiento()
   ↓
3. API Client: update_version_state(state="Protegida", protected=True, final_c=True)
   ↓
4. Middleware → Broker → Backend Core
   ↓
5. Backend Core: UPDATE version_states SET state='Protegida', protected=1, final_c=1
   ↓
6. Response → Frontend: Actualiza estado local y UI
```

---

## 4. Notas importantes

### Security by Design
- Todas las operaciones pasan por el flujo de autenticación/autorización
- Se validan permisos del usuario antes de ejecutar
- Se registra el user_id que ejecutó la acción

### Consistencia
- Las operaciones de filesystem y registro en `cambios` deben ser transaccionales
- Si falla la operación en fmanagement, no se registra en `cambios`
- Si falla el registro en `cambios`, se debe revertir la operación de filesystem

### Auditoría
- La tabla `cambios` sirve como historial completo de operaciones
- Permite reconstruir el timeline de modificaciones por versión
- Útil para debugging y auditorías de seguridad

### Diferencia entre tablas
- `version_states`: Estado actual de cada versión (1 registro por versión)
- `cambios`: Historial de todas las operaciones (múltiples registros por versión)

---

## 5. Próximos pasos

1. Implementar funciones de persistencia en `api_client.py`:
   - `update_version_state()` ✓ (probablemente ya existe)
   - `register_change()` (pendiente)

2. Integrar llamadas de persistencia en métodos del explorador:
   - `acciones()`: Añadir registro en `cambios`
   - `solicitar_entrenamiento()`: Confirmar actualización en `version_states`
   - `confirmar_entrenamiento()`: Actualizar y registrar en evolución

3. Crear adaptador para transformar salida de fmanagement_list a formato explorador

4. Implementar manejo de errores y rollback en caso de fallos
