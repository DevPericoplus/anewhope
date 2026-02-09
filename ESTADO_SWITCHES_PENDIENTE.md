# Estado de los Switches - Pendiente para Mañana

## 🔴 Problema Actual

Los 3 switches **SIGUEN SIN FUNCIONAR**:
- 🔍 "Revisión Interna" (`revision_interna`)
- ⚙️ "Propuesta de Mejoras" (`propuesta_mejoras`)
- 🤖 "Generación Solicitada" (`generacion_llm_solicitada`)

### Síntomas:
- Los switches no cambian de posición
- Posiblemente aparecen errores en consola del navegador
- El usuario reporta: "Siguen fallando"

## ✅ Trabajo Realizado Hoy

### 1. Tests de Backend (✅ PASARON)
- **Archivo:** `tests/test_failing_switches_simple.py`
- **Resultado:** Todos los 3 campos se actualizan correctamente en BD
- **Conclusión:** Backend Core funciona perfectamente

### 2. Cambios en el Código

#### Archivo: `src/apps/6_web_backoffice/pages/estado_proyectos.py`

**A. Agregadas Computed Properties (líneas ~355-375)**
```python
@rx.var
def revision_interna_value(self) -> bool:
    if not self.current_state:
        return False
    return bool(self.current_state.get("revision_interna", False))

@rx.var
def propuesta_mejoras_value(self) -> bool:
    if not self.current_state:
        return False
    return bool(self.current_state.get("propuesta_mejoras", False))

@rx.var
def generacion_llm_solicitada_value(self) -> bool:
    if not self.current_state:
        return False
    return bool(self.current_state.get("generacion_llm_solicitada", False))
```

**B. Reemplazados Switches para usar Computed Properties (líneas ~1014-1055, ~1165-1184)**
- Cambiado de: `_toggle_field("revision_interna", ...)`
- A: Switches inline usando `EstadoProyectosState.revision_interna_value`

**C. Agregados `yield` Statements en `toggle_field()` (líneas ~765-778)**
```python
if result.get("success"):
    async with self:
        self.success_message = f"Campo {field_name} actualizado correctamente"
    yield  # Propagar mensaje

    await self._load_current_state()
    yield  # Propagar estado actualizado
```

**D. Cambiada Firma de `toggle_field()` (línea ~605)**
```python
async def toggle_field(self, field_name: str) -> AsyncGenerator[None, None]:
```

**E. Arreglados Métodos de Selección (líneas ~567-632)**
- `set_organization()` → Agregado `await` y `yield`
- `set_project()` → Agregado `await` y `yield`
- `set_version()` → Agregado `yield`
- Cambiadas firmas a `AsyncGenerator[None, None]`

### 3. Backoffice Reiniciado
- ✅ Proceso corriendo en PID variable
- ✅ App en http://localhost:3200/
- ✅ Backend en http://0.0.0.0:8006
- ✅ No hay RuntimeWarnings de "coroutine was never awaited"
- ✅ Cambios cargados

## 🔍 Diagnóstico Actual

### Lo que SÍ Funciona:
1. ✅ Backend Core actualiza BD correctamente
2. ✅ API devuelve `{"success": True}`
3. ✅ No hay errores de Python en los logs
4. ✅ No hay warnings de "coroutine was never awaited"

### Lo que NO Funciona:
1. ❌ Switches no cambian visualmente en UI
2. ❌ Estado no se refresca después de actualizar
3. ❌ Posiblemente hay errores en consola del navegador

### Errores Reportados en Consola:
```
Error en el mapeo fuente: Error: JSON.parse: unexpected character at line 1 column 1 of the JSON data
URL del mapa fuente: installHook.js.map
```

**Nota:** Este error es sobre source maps de desarrollo, no es el problema principal.

## 🎯 Próximos Pasos para Mañana

### 1. Verificar Estado Actual en Consola del Navegador
- Abrir F12 → Console
- Buscar errores de JavaScript/React específicos
- Verificar si hay errores de red (pestaña Network)

### 2. Verificar Logs del Backoffice
```bash
tail -100 /tmp/backoffice_final.log | grep -E "toggle_field|ERROR|estado_proyectos"
```

### 3. Probar Endpoint Directamente
```bash
python3 tests/test_failing_switches_simple.py
```

### 4. Posibles Causas a Investigar

#### A. Problema con Reflex State Management
- Los computed properties no se están evaluando correctamente
- El estado no se está propagando a través de WebSocket
- Hay algún problema con el binding de Reflex

#### B. Problema con el Switch Component
- El componente `rx.switch` tiene un bug
- Necesita alguna prop adicional para funcionar correctamente
- El `on_change` no se está ejecutando

#### C. Problema con la Sesión/Autenticación
- Los tokens expiran y las llamadas fallan
- Hay algún problema con los headers
- La API rechaza las peticiones silenciosamente

#### D. Problema con el Evento `toggle_field`
- El método no se está ejecutando
- Hay algún error que se está tragando
- El `yield` no está funcionando como esperado

### 5. Debug Estratégico

**Paso 1:** Agregar logs en `toggle_field()`
```python
async def toggle_field(self, field_name: str) -> AsyncGenerator[None, None]:
    print(f"[DEBUG] toggle_field called: {field_name}")
    async with self:
        can_edit = self.can_edit
        current_state = self.current_state

    print(f"[DEBUG] can_edit={can_edit}, current_state keys={list(current_state.keys())}")

    # ... resto del código
```

**Paso 2:** Verificar que el evento se ejecute
- Agregar `console.log()` en el JavaScript generado
- O usar breakpoints en Developer Tools

**Paso 3:** Simplificar el Switch
- Crear un switch de prueba ultra-simple:
```python
rx.switch(
    checked=True,
    on_change=lambda _: print("Switch clicked!"),
)
```

**Paso 4:** Verificar WebSocket
- En F12 → Network → WS (WebSocket)
- Ver si hay mensajes de state update
- Verificar si hay errores de conexión

### 6. Alternativas si Nada Funciona

#### Opción A: Usar Estado Local sin API
```python
@rx.var
def revision_interna_local(self) -> bool:
    return self._revision_interna_local

def toggle_revision_interna_local(self):
    self._revision_interna_local = not self._revision_interna_local
```

#### Opción B: Forzar Refresco Completo
```python
def toggle_field(self, field_name: str):
    # ... actualizar API ...
    # Forzar recarga completa de la página
    return rx.redirect("/estado-proyectos")
```

#### Opción C: Usar Callbacks Diferentes
```python
rx.switch(
    checked=EstadoProyectosState.revision_interna_value,
    on_change=EstadoProyectosState.toggle_revision_interna,  # Método específico
)
```

## 📊 Archivos Clave

### Código Modificado:
- `src/apps/6_web_backoffice/pages/estado_proyectos.py` (cambios principales)

### Tests:
- `tests/test_failing_switches_simple.py` (backend test - PASA)
- `tests/test_middleware_switches.py` (middleware test - requiere auth)

### Logs:
- `/tmp/backoffice_final.log` (logs actuales del backoffice)
- `/tmp/backoffice_restart.log` (logs del reinicio anterior)

### Documentación:
- `SOLUCION_SWITCHES.md` (resumen de cambios previos)
- `SOLUCION_FINAL_SWITCHES.md` (documentación completa)
- `ESTADO_SWITCHES_PENDIENTE.md` (este archivo - estado actual)

## 💡 Ideas Adicionales

### Verificar Versión de Reflex
```bash
../../../.venv_backoffice313/bin/python -c "import reflex; print(reflex.__version__)"
```

### Verificar Compatibilidad del Switch Component
- Buscar en docs: https://reflex.dev/docs/library/forms/switch/
- Ver ejemplos de uso correcto
- Verificar si hay algún cambio en la API

### Considerar Rollback Temporal
Si nada funciona, podríamos:
1. Revertir cambios a versión anterior
2. Probar con un switch diferente (checkbox, toggle button)
3. Implementar solución más simple sin computed properties

## 🚀 Comando para Continuar Mañana

```bash
# 1. Verificar que backoffice esté corriendo
ps aux | grep reflex | grep backoffice

# 2. Ver logs recientes
tail -50 /tmp/backoffice_final.log

# 3. Ejecutar test de backend
python3 tests/test_failing_switches_simple.py

# 4. Verificar BD directamente
/usr/local/opt/mariadb@10.6/bin/mariadb -u myllm_admin -p'Us3r@dminP@ss' \
  -D myllm_projects_db \
  -e "SELECT id, revision_interna, propuesta_mejoras, generacion_llm_solicitada FROM estado_version WHERE id=1;"
```

## 📝 Notas Finales

- **Backend funciona perfectamente** ✅
- **Código de Python corregido** ✅
- **Problema está en UI/Frontend** ❌
- **Necesita debug más profundo del lado del navegador**

**Estado:** PENDIENTE - Los switches siguen sin funcionar después de múltiples intentos.

---
**Última actualización:** 2026-02-09 03:30 AM
**Usuario:** Cansado, continuar mañana
