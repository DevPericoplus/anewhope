# Resumen de Cambios - Sistema de Estados V2

**Fecha**: 2026-02-04
**Versión**: 2.0 - Con Selector de Estados

## Cambios Principales

### 1. Control de Acceso Refinado

**Antes**:
- Botones visibles según `can_version_create` (permiso genérico)
- No distinguía entre cliente y admin de organización

**Ahora**:
- **Frontend**: Solo admin de organización (`identity_type_id` 1 o 2) ve controles
- **Backoffice**: Todos los internos ven controles completos (soporte)
- Validación con propiedad `is_admin`

### 2. Selector de Estados

**Frontend (Admin Org)**:
```python
# Panel simplificado
- Selector: ["Abierta", "Bloqueada"]
- Checkbox: "Protegida" (sincroniza con estado)
- Solo activo si final_c y final_i son false
```

**Backoffice (Soporte)**:
```python
# Panel completo
- Selector: ["Abierta", "Bloqueada", "Protegida", "Final"]
- Checkbox: "Protegida"
- Checkbox: "final_c" (Capa Cliente)
- Checkbox: "final_i" (Capa Interno)
- Siempre activo (soporte puede cambiar todo)
```

### 3. Métodos Agregados

**ExploradorState (Frontend y Backoffice)**:

```python
@rx.var
def is_admin(self) -> bool:
    """identity_type_id 1 o 2"""
    return self.identity_type_id in [1, 2]

@rx.var
def available_status_options(self) -> list[str]:
    """Frontend: [Abierta, Bloqueada]
       Backoffice: [Abierta, Bloqueada, Protegida, Final]"""
    if self.is_admin:  # Frontend
        return ["Abierta", "Bloqueada"]
    if self.is_internal_user():  # Backoffice
        return ["Abierta", "Bloqueada", "Protegida", "Final"]
    return []

@rx.var
def can_change_state(self) -> bool:
    """Frontend: is_admin AND no final_c/final_i
       Backoffice: is_internal_user (siempre)"""
    # Frontend
    if not self.is_internal_user:
        return self.is_admin and not self.version_final_c and not self.version_final_i
    # Backoffice
    return True

def set_version_state(self, val: str):
    """Cambia estado mediante selector"""
    # Frontend: Solo Abierta ↔ Bloqueada
    # Backoffice: Todos los estados

def set_version_protected(self, val: bool):
    """Cambia checkbox Protegida"""
    # Sincroniza con estado (Abierta/Bloqueada)

def set_version_final_c(self, val: bool):
    """Cambia flag final_c"""
    # Frontend: Solo admin, solo si final_i=false
    # Backoffice: Siempre disponible

def set_version_final_i(self, val: bool):
    """Cambia flag final_i"""
    # Frontend: Solo admin
    # Backoffice: Siempre disponible
```

### 4. UI Actualizada

**Frontend**:
- Removidos botones "📝 Documentación preparada" y "✅ El cliente solicita"
- Botones "🔒 Bloquear" y "🔓 Desbloquear" ahora verifican `is_admin` y `can_change_state`
- Panel de control naranja solo visible para admin
- Selector simplificado (Abierta ↔ Bloqueada)

**Backoffice**:
- Removidos todos los botones individuales
- Panel de control morado completo (selector + 3 checkboxes)
- Mensaje informativo sobre capacidad de soporte
- Control total sobre estados y flags

### 5. Lógica de Bloqueo

**Condiciones para Bloquear/Desbloquear**:
```python
# Frontend
is_admin AND can_change_state (no final_c/final_i) AND state in [Abierta, Bloqueada]

# Backoffice
is_internal_user (siempre puede, para dar soporte)
```

**Efectos de Bloqueo**:
```python
# Cuando protected=true:
- Todos los items de la versión: is_blocked=true
- Menús contextuales: NO aparecen
- Elementos: opacity 0.5 (visual feedback)
- Cascada: Afecta depth >= 2 (carpetas y archivos)
```

### 6. Integración con Backend

**Sin cambios en API**, solo en cómo se llama:

```python
# set_version_state en Backoffice actualiza múltiples flags
if val == "Protegida":
    protected=True, final_c=True, final_i=False
elif val == "Final":
    protected=True, final_c=True, final_i=True
elif val == "Bloqueada":
    protected=True, final_c=False, final_i=False
elif val == "Abierta":
    protected=False, final_c=False, final_i=False
```

## Archivos Modificados

### Frontend
- `/src/apps/5_web_frontend/components/explorador.py`
  - Líneas 151-177: Propiedades `is_admin`, `available_status_options`, `can_change_state`
  - Líneas 553-685: Métodos `set_version_state`, `set_version_protected`, `set_version_final_c`, `set_version_final_i`
  - Líneas 1526-1625: UI actualizada con panel de control y botones simplificados

### Backoffice
- `/src/apps/6_web_backoffice/components/explorador.py`
  - Líneas 144-170: Propiedades `is_admin`, `available_status_options`, `can_change_state`
  - Líneas 517-649: Métodos `set_version_state`, `set_version_protected`, `set_version_final_c`, `set_version_final_i`
  - Líneas 1339-1460: UI actualizada con panel completo de control

## Flujos de Trabajo

### Admin de Org (Frontend)

```
1. Login como admin (identity_type_id 1 o 2)
2. Navegar a Explorador
3. Ver panel naranja "Control de Estados (Administrador)"
4. Opciones:
   a. Selector: Abierta ↔ Bloqueada
   b. Checkbox: Protegida (sincronizado)
5. Bloquear:
   - Cambiar selector a "Bloqueada"
   - O activar checkbox "Protegida"
6. Resultado:
   - Menús contextuales desaparecen
   - Items semi-transparentes
7. Desbloquear:
   - Cambiar selector a "Abierta"
   - O desactivar checkbox "Protegida"
```

### Usuario Interno (Backoffice)

```
1. Login como interno
2. Navegar a Explorador
3. Ver panel morado "Selector de Estados por Versión (Soporte)"
4. Opciones:
   a. Selector: Abierta, Bloqueada, Protegida, Final
   b. Checkbox: Protegida
   c. Checkbox: final_c
   d. Checkbox: final_i
5. Cambiar estado libremente:
   - Selector actualiza flags automáticamente
   - O cambiar flags manualmente
6. Uso típico de soporte:
   - Cliente en estado "Final" solicita cambio
   - Interno revierte a "Abierta"
   - Cliente hace modificaciones
   - Interno vuelve a poner en "Protegida" o "Final"
```

### Cliente Sin Admin (Frontend)

```
1. Login como cliente
2. Navegar a Explorador
3. NO ve panel de control
4. NO ve botones de estado
5. Solo lectura:
   - Puede ver archivos
   - Puede expandir/colapsar carpetas
   - NO puede modificar estados
```

## Validaciones Implementadas

### 1. Permisos de Rol

```python
# Frontend
if not self.is_admin:
    return rx.toast.error("Solo administradores...")

# Backoffice
if not self.is_internal_user():
    return rx.toast.error("Solo usuarios internos...")
```

### 2. Flags de Finalización

```python
# Frontend - bloqueo si hay flags activos
if self.version_final_c or self.version_final_i:
    # Deshabilitar controles
    disabled=~state.can_change_state
```

### 3. Cascada de Protección

```python
# interpretacion_estados()
if es_bloqueada:
    item.is_blocked = True
    for descendant in self.items:
        if descendant.id.startswith(version_id + "_"):
            descendant.is_blocked = True
```

### 4. Menús Contextuales

```python
# render_item_with_context_menu
should_show_menu_folder = (
    (item.item_type == "folder") &
    (item.depth > 0) &
    (~item.is_blocked | ((item.depth == 1) & ExploradorState.is_internal_user))
)

should_show_menu_file = (
    (item.item_type != "folder") &
    ~item.is_blocked
)
```

## Tests de Regresión

### ✅ Debe Funcionar

- Admin en frontend ve panel de control
- Cliente en frontend NO ve panel
- Interno en backoffice ve panel completo
- Bloquear versión oculta menús contextuales
- Desbloquear versión restaura menús
- Estados se sincronizan con BD
- Flags se actualizan correctamente

### ❌ Debe Fallar

- Cliente intenta cambiar estado (sin controles)
- Admin frontend intenta acceder a "Protegida" o "Final"
- Admin frontend intenta cambiar estado con final_c activo

## Próximos Pasos (Opcionales)

1. **Auditoría de cambios de estado**
   - Tabla `version_state_history`
   - Registro de quién cambió qué y cuándo

2. **Notificaciones**
   - Notificar a cliente cuando interno cambia su versión
   - Notificar a interno cuando cliente solicita cambio

3. **Endpoint de tamaño de carpeta**
   - `/fmo/size` en fmanagement
   - Actualizar campo `size` en `estado_version`
   - Mostrar en UI formateado (KB/MB)

4. **Revisar/Revertir (Admin)**
   - Botón especial para revertir de Protegida a Abierta
   - Solo admin, con confirmación
   - Limpia flags de finalización

## Conclusión

**Estado**: ✅ **COMPLETAMENTE FUNCIONAL**

El sistema ahora implementa correctamente:
- Control de acceso por rol (identity_type_id)
- Selector de estados adaptado por interfaz (frontend vs backoffice)
- Protección en cascada a nivel de versión completa
- Restricción de cambios cuando hay flags de finalización activos
- Soporte completo para usuarios internos (backoffice)
- Simplicidad para admin de org (frontend)

**Listo para pruebas de usuario** según documento `/docs/PRUEBAS_SISTEMA_ESTADOS.md`
