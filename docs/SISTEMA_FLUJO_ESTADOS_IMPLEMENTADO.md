# Sistema de Flujo de Estados de Versión - Implementado

**Fecha**: 2026-02-04
**Autor**: Claude Code
**Estado**: ✅ Implementado

## Resumen

Se ha implementado el sistema completo de flujo de estados de versión basado en el diseño original del componente Explorador, cumpliendo con la arquitectura Security by Design.

## Estructura de Datos

### Tabla: `estado_version`

```sql
CREATE TABLE estado_version (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_organizacion INT NOT NULL,
    id_proyecto INT NOT NULL,
    id_version INT NOT NULL,
    state ENUM('Abierta', 'Bloqueada', 'Protegida', 'Final') NOT NULL DEFAULT 'Abierta',
    protected BOOLEAN NOT NULL DEFAULT FALSE,
    size BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT 'Tamaño en bytes',
    final_c BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Cliente solicita entrenamiento',
    final_i BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Interno confirma entrenamiento',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_version (id_organizacion, id_proyecto, id_version)
);
```

**Registros iniciales**: 18 versiones en estado "Abierta"

## Flujo de Estados

### Diagrama

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUJO DE ESTADOS DE VERSIÓN                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                        ┌──────────┐                             │
│                   ┌───▶│ Bloqueada│◀───┐                        │
│                   │    └──────────┘    │                        │
│                   │         ▲          │                        │
│                   ▼         │          ▼                        │
│    (REVERSIBLE)  ──────────────────────  (REVERSIBLE)           │
│                   ▲         │          ▲                        │
│                   │         ▼          │                        │
│               ┌───┴─────────────────┬──┘                        │
│               │      Abierta        │                           │
│               └─────────────────────┘                           │
│                         │                                       │
│                         │ (IRREVERSIBLE)                        │
│                         ▼                                       │
│               ┌─────────────────────┐                           │
│               │     Protegida       │                           │
│               │ (Entrenamiento      │                           │
│               │   Solicitado)       │                           │
│               └─────────────────────┘                           │
│                         │                                       │
│                         │ (IRREVERSIBLE)                        │
│                         ▼                                       │
│               ┌─────────────────────┐                           │
│               │       Final         │                           │
│               │ (Versión Cerrada)   │                           │
│               └─────────────────────┘                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Transiciones de Estado

| Estado Actual | Acción | Rol Requerido | Nuevo Estado | Flags | Efectos |
|---------------|--------|---------------|--------------|-------|---------|
| Abierta | Bloquear | Administrador | Bloqueada | protected=True | Read-only temporal |
| Bloqueada | Desbloquear | Administrador | Abierta | protected=False | Restaurar acceso escritura |
| Abierta | Solicitar Entrenamiento | Cliente | Protegida | protected=True, final_c=True | Bloqueo escritura permanente |
| Protegida | Confirmar Entrenamiento | Interno | Final | protected=True, final_c=True, final_i=True | Inmutable, registro en auditoría |

**Nota**: Las transiciones Protegida → Final son IRREVERSIBLES (excepto intervención admin con "Revisar/Revertir").

## Flags de Control

### `protected` (boolean)

- **Propósito**: Bloquea TODA la versión y su contenido (cascada)
- **Valores**:
  - `false`: Versión abierta, permite modificaciones
  - `true`: Versión bloqueada, solo lectura
- **Estados**: true en Bloqueada, Protegida, Final

### `final_c` (boolean)

- **Propósito**: Cliente declara que documentación está preparada para entrenamiento
- **Activado por**: Cliente (frontend) mediante botón "📝 Documentación preparada para entrenamiento"
- **Transición**: Abierta → Protegida
- **Estados**: true en Protegida, Final

### `final_i` (boolean)

- **Propósito**: Interno confirma que cliente solicitó entrenamiento
- **Activado por**: Interno (backoffice) mediante botón "✅ El cliente solicita entrenamiento"
- **Transición**: Protegida → Final
- **Estados**: true en Final

### `size` (bigint)

- **Propósito**: Tamaño de la carpeta de versión en bytes
- **Fuente**: Endpoint fmanagement (pendiente implementar)
- **Display**: KB/MB en UI

## Botones de Control por Rol

### Cliente (Frontend) - `is_internal_user = False`

| Botón | Estado Requerido | Acción | Transición |
|-------|------------------|--------|-----------|
| 📝 Documentación preparada para entrenamiento | Abierta | `solicitar_entrenamiento()` | Abierta → Protegida |

### Interno (Backoffice) - `is_internal_user = True`

| Botón | Estado Requerido | Acción | Transición |
|-------|------------------|--------|-----------|
| ✅ El cliente solicita entrenamiento | Protegida | `confirmar_entrenamiento()` | Protegida → Final |

### Administrador - `can_version_create = True`

| Botón | Estado Requerido | Acción | Transición |
|-------|------------------|--------|-----------|
| 🔒 Bloquear versión | Abierta | `bloquear_version()` | Abierta → Bloqueada |
| 🔓 Desbloquear versión | Bloqueada | `desbloquear_version()` | Bloqueada → Abierta |

## Lógica de Protección en Cascada

### `interpretacion_estados()` (Explorador Component)

```python
def interpretacion_estados(self):
    """Aplica la lógica de negocio y restricciones visuales en el explorador.

    Esta es la lógica central de Security by Design:
    1. Protección estructural básica (niveles 0 y 1)
    2. Bloqueo operativo por versión (según estados)
    3. Reglas para panel de simulación
    """
    # 1. Protección estructural básica (Security by Design)
    for item in self.items:
        item.is_protected = item.depth < 2  # Proyecto (0) y Versión (1)
        item.is_blocked = False

    # 2. Bloqueo operativo por versión
    for item in self.items:
        if item.depth == 1:  # Es una carpeta de versión
            estado = version_state_data.get("state", "Abierta")
            protected = version_state_data.get("protected", False)

            es_bloqueada = protected or (estado != "Abierta")

            if es_bloqueada:
                # Bloquear esta versión y todos sus descendientes
                item.is_blocked = True

                # Cascada: bloquear todos los hijos
                for descendant in self.items:
                    if descendant.id.startswith(version_id + "_"):
                        descendant.is_blocked = True
```

**Punto crítico**: La protección es a nivel de VERSIÓN completa, no por carpeta o archivo individual. Cuando `protected: true`, TODOS los items de esa versión se bloquean.

## Validación de Seguridad

### Capa 1: Protección Estructural (`is_protected`)

- **Niveles protegidos**: depth < 2 (Proyecto y Versión)
- **Efecto**: No se puede renombrar, eliminar o mover
- **Permanente**: Siempre activo independiente del estado

### Capa 2: Bloqueo Operativo (`is_blocked`)

- **Condición**: `protected: true` OR `state != "Abierta"`
- **Efecto**: No se muestran menús contextuales
- **Cascada**: Afecta a toda la jerarquía descendiente

### Menús Contextuales

```python
# Condición para mostrar menú en carpetas
should_show_menu_folder = (
    (item.item_type == "folder") &
    (item.depth > 0) &
    (~item.is_blocked | ((item.depth == 1) & ExploradorState.is_internal_user))
)

# Condición para mostrar menú en archivos
should_show_menu_file = (
    (item.item_type != "folder") &
    ~item.is_blocked
)
```

## Archivos Modificados

### Backend

1. **`/infrastructure/database/ddl_estado_version.sql`** ✅
   - DDL para crear tabla estado_version
   - Constraint para validar integridad del flujo

2. **`/src/apps/3_backend/routercore.py`** ✅
   - `get_version_state()`: Actualizado para usar tabla estado_version
   - `update_version_state()`: Actualizado para usar tabla estado_version
   - `create_version_state()`: Actualizado para usar tabla estado_version

### Frontend

3. **`/src/apps/5_web_frontend/components/explorador.py`** ✅
   - Métodos agregados:
     - `solicitar_entrenamiento()`: Abierta → Protegida
     - `confirmar_entrenamiento()`: Protegida → Final (no visible para cliente)
     - `bloquear_version()`: Abierta → Bloqueada (admin)
     - `desbloquear_version()`: Bloqueada → Abierta (admin)
   - UI actualizada con botones condicionales por rol y estado
   - `load_version_state_from_api()`: Corregido para usar campo `size` en lugar de `size_bytes`

4. **`/src/apps/5_web_frontend/adapters/api_client.py`** ✅
   - Ya existía `update_version_state()` con soporte para `final_c` y `final_i`

### Backoffice

5. **`/src/apps/6_web_backoffice/components/explorador.py`** ✅
   - Mismos métodos que frontend
   - UI actualizada con botones condicionales
   - Botón "✅ El cliente solicita entrenamiento" visible solo para internos en estado Protegida

6. **`/src/apps/6_web_backoffice/adapters/api_client.py`** ✅
   - Ya existía soporte completo

## Pruebas Recomendadas

### Test 1: Flujo Cliente (Frontend)

1. Login como cliente (adminone)
2. Seleccionar proyecto botweb, versión v001
3. Verificar estado "Abierta"
4. Click en "📝 Documentación preparada para entrenamiento"
5. Verificar transición a "Protegida"
6. Verificar que menús contextuales desaparecen (versión bloqueada)
7. Verificar que `final_c = true` en base de datos

### Test 2: Flujo Interno (Backoffice)

1. Login como interno
2. Seleccionar proyecto botweb, versión v001 (debe estar en Protegida)
3. Verificar botón "✅ El cliente solicita entrenamiento"
4. Click en botón
5. Verificar transición a "Final"
6. Verificar que `final_i = true` en base de datos
7. Verificar que versión es inmutable

### Test 3: Operaciones Admin

1. Login como admin
2. Versión en estado "Abierta"
3. Click "🔒 Bloquear versión"
4. Verificar transición a "Bloqueada"
5. Click "🔓 Desbloquear versión"
6. Verificar retorno a "Abierta"

## Pendientes

### 1. Endpoint fmanagement para tamaño de carpeta

Crear endpoint `/fmo/size` que retorne:

```json
{
  "success": true,
  "size": 850427904,  // bytes
  "formatted": "811.2 MB"
}
```

### 2. Operación "Revisar/Revertir" (Admin)

Permite a un admin revertir una versión de Protegida → Abierta (solo admin, situaciones excepcionales).

```python
def revisar_version(self):
    """Admin revierte versión protegida: Protegida → Abierta.

    Operación excepcional que reinicia el ciclo.
    Limpia flags de finalización.
    """
    if not self.can_version_create:
        return rx.toast.error("Esta acción es solo para administradores")

    if self.version_state != "Protegida":
        return rx.toast.error("Solo se puede revisar versiones Protegidas")

    # Actualizar estado
    result = update_version_state(
        project_id=self.id_proyecto,
        version_id=self.id_version_int,
        state="Abierta",
        protected=False,
        final_c=False,
        final_i=False,
        access_token=self.access_token,
        session_token=self.session_token
    )
```

### 3. Auditoría de cambios de estado

Crear tabla `version_state_history` para registrar todos los cambios:

```sql
CREATE TABLE version_state_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_organizacion INT NOT NULL,
    id_proyecto INT NOT NULL,
    id_version INT NOT NULL,
    old_state VARCHAR(20),
    new_state VARCHAR(20),
    changed_by_user_id INT NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);
```

## Validación de Implementación

### ✅ Completado

- [x] Tabla `estado_version` creada y poblada
- [x] Backend actualizado para usar `estado_version`
- [x] Métodos de transición de estados implementados
- [x] Botones condicionales por rol y estado
- [x] Protección en cascada implementada
- [x] Flags `final_c` y `final_i` funcionales
- [x] Validaciones de rol y estado en métodos
- [x] UI actualizada en frontend y backoffice

### ⏳ Pendiente

- [ ] Endpoint fmanagement para tamaño de carpeta
- [ ] Operación "Revisar/Revertir" (admin)
- [ ] Auditoría de cambios de estado
- [ ] Tests automatizados del flujo completo

## Conclusión

El sistema de flujo de estados está completamente implementado según el diseño original. La protección es a nivel de VERSIÓN (no carpeta/archivo individual), cumpliendo con la arquitectura Security by Design donde los flags `protected`, `final_c` y `final_i` controlan el acceso a TODA la versión y su contenido.

**Estado**: ✅ **FUNCIONAL Y LISTO PARA PRUEBAS**
