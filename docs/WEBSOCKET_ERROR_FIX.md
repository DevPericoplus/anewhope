# 🔧 Corrección de Error WebSocket

**Fecha:** 2026-01-26  
**Error:** `Cannot connect to server: timeout. Check if server is reachable at wss://tfmmyllm.ai/_event`  
**Estado:** ✅ **RESUELTO**  

---

## 📋 Resumen del Problema

El frontend de Reflex no podía conectar al backend WebSocket, mostrando el error:

```
Cannot connect to server: timeout.
Check if server is reachable at wss://tfmmyllm.ai/_event
```

### Diagnóstico Inicial

```bash
# Servicios corriendo ANTES de la corrección:
✅ Nginx (puerto 443) - CORRIENDO
✅ Frontend UI (puerto 3001) - CORRIENDO  
❌ Frontend Backend/WebSocket (puerto 8005) - NO CORRIENDO
```

**Causa raíz:** El backend de Reflex no se iniciaba debido a errores de compilación en el código Python.

---

## 🐛 Errores Encontrados y Corregidos

### Error 1: Atributo inexistente `user_logged_in`

**Archivo:** `src/apps/5_web_frontend/web_frontend/web_frontend.py`

**Problema:**
```python
# Línea 856
State.user_logged_in  # ❌ Atributo no existe

# Líneas 887, 898, 935, 946
sidebar_menu(State.user_logged_in)  # ❌ Atributo no existe
```

**Error en compilación:**
```
AttributeError: type object 'State' has no attribute 'user_logged_in'. 
Did you mean: 'is_logged_in'?
```

**Solución:**
```python
# Reemplazar TODOS los usos de user_logged_in por is_logged_in
State.is_logged_in  # ✅ Correcto
sidebar_menu(State.is_logged_in)  # ✅ Correcto
```

**Total de correcciones:** 7 ocurrencias

---

### Error 2: Decorator incorrecto en computed vars

**Archivo:** `src/2_shared_application/reflex_shared/shared_session_state.py`

**Problema:**
```python
@property  # ❌ Incorrecto para Reflex
def can_access_backoffice(self) -> bool:
    return self.is_logged_in and self.can_training_create

@property  # ❌ Incorrecto para Reflex
def user_display_name(self) -> str:
    return self.user_name if self.is_logged_in else ""

@property  # ❌ Incorrecto para Reflex
def user_display_email(self) -> str:
    return self.user_email if self.is_logged_in else ""
```

**Error en compilación:**
```
TypeError: Unsupported type <class 'property'> for LiteralVar.
```

**Explicación:**
En Reflex, las propiedades computadas que se usan en `rx.cond()` o componentes reactivos deben estar decoradas con `@rx.var`, no con `@property`.

**Solución:**
```python
@rx.var  # ✅ Correcto para Reflex
def can_access_backoffice(self) -> bool:
    return self.is_logged_in and self.can_training_create

@rx.var  # ✅ Correcto para Reflex
def user_display_name(self) -> str:
    return self.user_name if self.is_logged_in else ""

@rx.var  # ✅ Correcto para Reflex
def user_display_email(self) -> str:
    return self.user_email if self.is_logged_in else ""
```

**Total de correcciones:** 3 propiedades

---

## 🔧 Pasos de Corrección Aplicados

### 1. Detener procesos anteriores
```bash
ps aux | grep "reflex\|node.*300" | grep -v grep | awk '{print $2}' | xargs kill -9
```

### 2. Limpiar caché de Reflex
```bash
cd src/apps/5_web_frontend
rm -rf .web public .reflex
```

### 3. Corregir código Python
- Reemplazar `user_logged_in` → `is_logged_in` (7 ocurrencias)
- Reemplazar `@property` → `@rx.var` (3 ocurrencias)

### 4. Reiniciar Reflex
```bash
source .venv_frontend313/bin/activate
cd src/apps/5_web_frontend
reflex run --env prod
```

---

## ✅ Resultado Final

### Servicios DESPUÉS de la corrección:

```bash
# Verificación de puertos:
✅ Nginx (puerto 443) - CORRIENDO
✅ Frontend UI (puerto 3002) - CORRIENDO
✅ Frontend Backend/WebSocket (puerto 8005) - CORRIENDO (múltiples workers)
```

### Tests de conectividad:

```bash
# Test directo al backend:
curl -I http://127.0.0.1:8005
# HTTP/1.1 200 OK ✅

# Test WebSocket endpoint:
curl -I http://127.0.0.1:8005/_event
# HTTP/1.1 200 OK ✅

# Test HTTPS principal:
curl -Ik https://tfmmyllm.ai
# HTTP/1.1 200 OK ✅
```

---

## 📊 Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `src/apps/5_web_frontend/web_frontend/web_frontend.py` | 7 correcciones: `user_logged_in` → `is_logged_in` |
| `src/2_shared_application/reflex_shared/shared_session_state.py` | 3 correcciones: `@property` → `@rx.var` |

---

## 🎓 Lecciones Aprendidas

### 1. Nombres de atributos en SharedSessionState

**Regla:** Usar siempre `is_logged_in`, nunca `user_logged_in`.

El `SharedSessionState` define:
```python
is_logged_in: bool = False  # ✅ Nombre correcto
```

### 2. Decorators en Reflex computed vars

**Regla:** Para propiedades computadas que se usan en componentes reactivos:

```python
# ❌ INCORRECTO (causa TypeError)
@property
def my_computed_var(self) -> bool:
    return self.some_value

# ✅ CORRECTO (funciona en componentes)
@rx.var
def my_computed_var(self) -> bool:
    return self.some_value
```

### 3. Importancia del caché de Reflex

**Regla:** Después de correcciones en el código, SIEMPRE limpiar el caché:

```bash
rm -rf .web public .reflex
```

El caché puede contener versiones compiladas antiguas del código.

---

## 🔍 Troubleshooting Futuro

Si aparece el mismo error de WebSocket:

### Paso 1: Verificar puertos
```bash
lsof -i :8005 | grep LISTEN
```

**Esperado:** Múltiples procesos Python escuchando en 8005  
**Si no hay procesos:** Backend no se inició → revisar logs

### Paso 2: Ver logs de Reflex
```bash
# Logs en tiempo real
tail -f /path/to/terminal/output

# O verificar directamente
reflex run --env prod
```

**Buscar:** Errores de compilación, AttributeError, TypeError

### Paso 3: Verificar configuración
```bash
# Archivo: src/apps/5_web_frontend/rxconfig.py
grep -E "(api_url|backend_port|env)" rxconfig.py
```

**Esperado:**
```python
env=rx.Env.PROD,
backend_port=8005,
api_url="https://tfmmyllm.ai",
```

### Paso 4: Limpiar y reiniciar
```bash
# Limpiar caché
rm -rf .web public .reflex

# Reiniciar
reflex run --env prod
```

---

## 📚 Referencias

- **Documentación oficial:** `README.md` (Problema 7: Error de WebSocket)
- **Shared Session State:** `src/2_shared_application/reflex_shared/shared_session_state.py`
- **Frontend State:** `src/apps/5_web_frontend/web_frontend/web_frontend.py`
- **Reflex Computed Vars:** https://reflex.dev/docs/state/computed-vars/

---

## ✅ Checklist de Verificación

Usar este checklist cuando aparezca un error de WebSocket:

- [ ] Puerto 443 (Nginx) está escuchando
- [ ] Puerto 8005 (Backend WebSocket) está escuchando
- [ ] No hay errores en logs de Reflex
- [ ] `rxconfig.py` tiene configuración correcta
- [ ] Caché de Reflex limpiado (`.web`, `public`, `.reflex`)
- [ ] Código Python sin `user_logged_in` (usar `is_logged_in`)
- [ ] Computed vars usan `@rx.var` (no `@property`)
- [ ] Tests de conectividad pasan

---

**Última actualización:** 2026-01-26  
**Tiempo de resolución:** ~40 minutos  
**Estado:** ✅ Resuelto y documentado
