# Solución: Switches que no actualizan

## 🔍 Diagnóstico

### Tests Ejecutados:

1. **✅ Backend Core** - Funciona perfectamente
   - `revision_interna` se actualiza correctamente en BD
   - `propuesta_mejoras` se actualiza correctamente en BD
   - `generacion_llm_solicitada` se actualiza correctamente en BD

2. **⚠️ Middleware** - Requiere autenticación (comportamiento correcto)

3. **❌ UI/Reflex** - No refrescaba el estado después de actualizar

### Problema Encontrado:

En el método `toggle_field()` de `estado_proyectos.py`:

```python
# ANTES (PROBLEMA):
if result.get("success"):
    async with self:
        self.success_message = f"Campo {field_name} actualizado correctamente"
    await self._load_current_state()  # ❌ Sin yield después
```

El problema: Aunque la API devolvía éxito y la BD se actualizaba, el estado recargado **NO se propagaba a la UI** porque faltaban los `yield`.

En Reflex, cuando usas `@rx.event(background=True)`, **debes usar `yield` para enviar actualizaciones de estado al frontend**.

### Solución Aplicada:

```python
# DESPUÉS (SOLUCIONADO):
if result.get("success"):
    async with self:
        self.success_message = f"Campo {field_name} actualizado correctamente"
    yield  # ✅ Propagar mensaje de éxito

    await self._load_current_state()  # Recargar estado desde BD
    yield  # ✅ Propagar estado actualizado a la UI
```

También se actualizó la firma del método:

```python
# ANTES:
async def toggle_field(self, field_name: str) -> None:

# DESPUÉS:
async def toggle_field(self, field_name: str) -> AsyncGenerator[None, None]:
```

## 🧪 Verificación

### Test 1: Backend Core (YA EJECUTADO - PASÓ ✅)

```bash
python3 tests/test_failing_switches_simple.py
```

Resultado: Todos los 3 campos se actualizan correctamente en la base de datos.

### Test 2: Verificación UI (EJECUTAR AHORA)

1. Recargar el backoffice (Ctrl+R o F5)
2. Ir a la página "Estado Proyectos"
3. Seleccionar Organización, Proyecto y Versión
4. Probar los 3 switches:
   - ✅ "Revisión Interna"
   - ✅ "Propuesta de Mejoras"
   - ✅ "Generación Solicitada"

**Comportamiento esperado:**
- ✅ Aparece mensaje verde: "Campo XXX actualizado correctamente"
- ✅ El switch cambia de posición visualmente
- ✅ Si recargas la página, el switch mantiene su nueva posición
- ✅ La BD refleja el cambio

## 📝 Archivos Modificados

- `src/apps/6_web_backoffice/pages/estado_proyectos.py`
  - Línea 605: Cambió firma del método `toggle_field`
  - Líneas 763-776: Agregó `yield` statements para propagar estado

## 🎯 Resultado

Los 3 switches ahora deberían:
1. Llamar a la API correctamente ✅
2. Actualizar la BD correctamente ✅
3. **Refrescar la UI correctamente** ✅ (NUEVO)
4. Mantener el estado al recargar ✅

## 🔧 Tests de Validación

Se crearon 2 tests automatizados:

1. **test_failing_switches_simple.py** - Test de backend (API directa)
2. **test_middleware_switches.py** - Test de middleware (requiere auth)

Ambos tests están en `/tests/` y pueden ejecutarse para validar el comportamiento.
