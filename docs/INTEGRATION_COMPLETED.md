# ✅ Integración de SharedSessionState COMPLETADA

## 🎉 Estado Final: 7 DE 7 FASES COMPLETADAS (100%)

---

## 📝 CAMBIOS REALIZADOS

### Frontend (`src/apps/5_web_frontend/web_frontend/web_frontend.py`)

#### ✅ Cambio 1: Import de SharedSessionState (línea 17)
```python
from web_frontend.shared_state import SharedSessionState
```

#### ✅ Cambio 2: Herencia de State (línea 31)
```python
class State(SharedSessionState):  # Antes: rx.State
    """Main application state with Redis-based session sharing."""
```

**Campos eliminados (ahora vienen de SharedSessionState):**
- `user_logged_in: bool` 
- `access_token: str`
- `session_token: str`
- `user_id: int`
- `organization_id: int`

**Campos mantenidos (locales del frontend):**
- `user_active_menu: str`
- `user_username: str`
- `user_password: str`
- `user_otp: str`
- `user_active_tab: str`
- `user_permissions: list[dict[str, str]]`
- `login_error: str`
- `otp_request_message: str`

#### ✅ Cambio 3: Método user_login() actualizado
Ahora llama a `self.load_user_data()` con todos los campos:
- Convierte lista de permisos a diccionario
- Carga datos en SharedSessionState (sincroniza automáticamente con Redis)
- Mantiene lista de permisos para compatibilidad con UI existente

#### ✅ Cambio 4: Método user_logout() actualizado
Ahora llama a `self.clear_session()` para limpiar SharedSessionState

#### ✅ Cambio 5: Botón "Backoffice" añadido (línea ~865)
Muestra botón naranja "Backoffice" si `State.can_access_backoffice == True`
- onClick: `State.go_to_backoffice`
- Color: Naranja (#FF8C00)
- Posición: Entre logo y botón "Desconectar"

---

### Backoffice (`src/apps/6_web_backoffice/web_backoffice/web_frontend.py`)

#### ✅ Cambio 1: Import de SharedSessionState (línea 17)
```python
from web_backoffice.shared_state import SharedSessionState
```

#### ✅ Cambio 2: Herencia de State (línea 31)
```python
class State(SharedSessionState):  # Antes: rx.State
    """Backoffice state with Redis-based session sharing."""
```

#### ✅ Cambio 3: Método check_backoffice_access() añadido
Verifica permisos y redirige al frontend si no tiene acceso

#### ✅ Cambio 4: Método user_login() deshabilitado
Login solo se permite en el frontend:
```python
def user_login(self):
    self.login_error = "El login debe realizarse desde el sitio principal"
    return
```

#### ✅ Cambio 5: Método user_logout() actualizado
Llama a `self.clear_session()` y redirige con `self.go_to_frontend()`

#### ✅ Cambio 6: Botones actualizados en header (línea ~835)
- **"Volver al Frontend"**: Verde (#22c55e), onClick: `State.go_to_frontend`
- **"Desconectar"**: Naranja (#FF8C00), onClick: `State.user_logout`

---

## 🧪 TESTING MANUAL

### Preparación

**Terminal 1: Monitoreo Redis**
```bash
cd /Users/administrator/develop/anewhope
./scripts/monitor_redis_sessions.py --continuous
```

**Terminal 2: Frontend**
```bash
cd /Users/administrator/develop/anewhope/src/apps/5_web_frontend
source ../../../.venv_frontend313/bin/activate
reflex run --env prod
```
*Esperar a que cargue completamente (App Running at: http://localhost:3000, Backend running at: http://0.0.0.0:8005)*

**Terminal 3: Backoffice**
```bash
cd /Users/administrator/develop/anewhope/src/apps/6_web_backoffice
source ../../../.venv_backoffice313/bin/activate
reflex run --env prod
```
*Esperar a que cargue completamente (App Running at: http://localhost:3000, Backend running at: http://0.0.0.0:8006)*

**Terminal 4: Nginx**
```bash
cd /Users/administrator/develop/anewhope
./deploy_nginx_macbook.sh
```

---

### Escenarios de Prueba

#### ✅ Escenario 1: Login y verificación de sesión

1. Abrir navegador en `https://tfmmyllm.ai`
2. Introducir credenciales de un usuario con `training_create: true`:
   - Usuario: `adminone`
   - Password: `Password01`
   - OTP: (verificar en DB o users.json)
3. Click en "Iniciar Sesión"
4. **Verificar:**
   - ✅ Login exitoso
   - ✅ Menú cambia a opciones logueadas
   - ✅ En Terminal 1: Aparece nueva sesión en Redis
   - ✅ Aparece botón naranja "Backoffice" en header

#### ✅ Escenario 2: Navegación al Backoffice

1. Desde el frontend logueado, click en botón "Backoffice"
2. **Verificar:**
   - ✅ URL cambia a `https://tfmmyllm.ai/backoffice`
   - ✅ Aparece interface del backoffice (colores naranjas)
   - ✅ En Terminal 1: `current_app` cambia a "backoffice"
   - ✅ Datos del usuario se mantienen (mismo user_id, email, etc.)
   - ✅ Aparece botón verde "Volver al Frontend"
   - ✅ Aparece botón naranja "Desconectar"

#### ✅ Escenario 3: Regreso al Frontend

1. Desde el backoffice, click en botón "Volver al Frontend"
2. **Verificar:**
   - ✅ URL cambia a `https://tfmmyllm.ai`
   - ✅ Aparece interface del frontend (colores verdes)
   - ✅ En Terminal 1: `current_app` cambia a "frontend"
   - ✅ Sesión se mantiene activa
   - ✅ Datos del usuario siguen disponibles

#### ✅ Escenario 4: Logout desde Frontend

1. Desde el frontend logueado, click en "Desconectar"
2. **Verificar:**
   - ✅ Sesión se cierra
   - ✅ Redirect a página pública
   - ✅ En Terminal 1: Sesión desaparece de Redis (o status cambia a "inactive")
   - ✅ Aparece panel de login nuevamente

#### ✅ Escenario 5: Logout desde Backoffice

1. Login en frontend
2. Navegar al backoffice
3. Click en "Desconectar" desde backoffice
4. **Verificar:**
   - ✅ Sesión se cierra en AMBAS aplicaciones
   - ✅ Redirect a `https://tfmmyllm.ai` (frontend público)
   - ✅ En Terminal 1: Sesión desaparece de Redis
   - ✅ No se puede volver al backoffice sin login

#### ✅ Escenario 6: Usuario sin permisos

1. Login con usuario que tiene `training_create: false`
   - Usuario: (cualquier usuario sin permisos de entrenamiento)
2. **Verificar:**
   - ✅ Login exitoso
   - ✅ **NO** aparece botón "Backoffice"
   - ✅ No puede acceder a `https://tfmmyllm.ai/backoffice` directamente

#### ✅ Escenario 7: Intento de login desde Backoffice

1. Acceder directamente a `https://tfmmyllm.ai/backoffice` sin login
2. Intentar introducir credenciales en el panel de login (si aparece)
3. **Verificar:**
   - ✅ Aparece mensaje: "El login debe realizarse desde el sitio principal"
   - ✅ No se permite login
   - ✅ Usuario debe ir al frontend para loguearse

---

## 🐛 TROUBLESHOOTING

### Problema: ImportError: cannot import name 'SharedSessionState'

**Solución:**
```bash
# Verificar que existe el archivo
ls -la src/apps/5_web_frontend/web_frontend/shared_state.py
ls -la src/apps/6_web_backoffice/web_backoffice/shared_state.py

# Si falta, copiar:
cp src/apps/5_web_frontend/web_frontend/shared_state.py \
   src/apps/6_web_backoffice/web_backoffice/shared_state.py
```

### Problema: AttributeError: 'State' object has no attribute 'can_access_backoffice'

**Causa:** SharedSessionState no se cargó correctamente

**Solución:**
1. Verificar que el import está al inicio del archivo
2. Verificar que la herencia es `class State(SharedSessionState)`
3. Reiniciar la aplicación Reflex

### Problema: Botón "Backoffice" no aparece

**Causa:** Usuario no tiene permiso `training_create: true`

**Solución:**
1. Verificar permisos en `src/2_shared_application/moks/low_level_permissions.json`
2. Buscar el `identity_type_id` del usuario
3. Verificar que `training_create: true` para ese rol
4. Reiniciar sesión

### Problema: WebSocket error al navegar

**Solución:**
```bash
# Recargar nginx
./deploy_nginx_macbook.sh

# Limpiar cache de Reflex
cd src/apps/5_web_frontend && rm -rf .web __pycache__
cd ../6_web_backoffice && rm -rf .web __pycache__

# Reiniciar ambas apps
```

### Problema: Sesión no se sincroniza entre apps

**Verificar:**
1. Redis está corriendo: `redis-cli -a PassRedis2025 ping`
2. Ambas apps usan la misma DB: revisar `rxconfig.py` → `redis_db: "0"`
3. Monitoreo muestra la sesión: `./scripts/monitor_redis_sessions.py`

---

## 📊 VERIFICACIÓN DE ESTADO

### Verificar que Redis está funcionando
```bash
redis-cli -a PassRedis2025 ping
# Debe responder: PONG
```

### Verificar sesiones activas
```bash
./scripts/monitor_redis_sessions.py
# Debe mostrar sesiones activas con todos los datos
```

### Verificar configuración frontend
```bash
cd src/apps/5_web_frontend
python -c "from rxconfig import config; print(config.redis_url)"
# Debe mostrar: redis://:PassRedis2025@localhost:6379/0
```

### Verificar configuración backoffice
```bash
cd src/apps/6_web_backoffice
python -c "from rxconfig import config; print(config.redis_url)"
# Debe mostrar: redis://:PassRedis2025@localhost:6379/0 (MISMA DB)
```

---

## ✅ CHECKLIST FINAL

### Infraestructura
- [x] Redis 8.4.0 instalado
- [x] Redis corriendo con password
- [x] Nginx configurado con rutas `/backoffice/*`
- [x] Variables de entorno configuradas

### Código
- [x] SharedSessionState implementado (474 líneas)
- [x] Frontend hereda de SharedSessionState
- [x] Backoffice hereda de SharedSessionState
- [x] Método `load_user_data()` en frontend
- [x] Método `clear_session()` en ambas apps
- [x] Botón "Backoffice" en frontend
- [x] Botón "Volver al Frontend" en backoffice
- [x] Login deshabilitado en backoffice
- [x] Logout redirige correctamente

### Funcionalidad
- [ ] Login exitoso en frontend ⏳ PENDIENTE TEST
- [ ] Navegación frontend → backoffice ⏳ PENDIENTE TEST
- [ ] Datos se sincronizan vía Redis ⏳ PENDIENTE TEST
- [ ] Navegación backoffice → frontend ⏳ PENDIENTE TEST
- [ ] Logout funciona en ambas apps ⏳ PENDIENTE TEST
- [ ] Usuario sin permisos no ve botón "Backoffice" ⏳ PENDIENTE TEST

---

## 🎯 PRÓXIMOS PASOS

1. **Ejecutar los 4 terminales** según las instrucciones de "Preparación"
2. **Realizar todos los escenarios de prueba** uno por uno
3. **Documentar cualquier issue** encontrado
4. **Ajustar según sea necesario**

---

**Documentación generada:** 2026-01-26  
**Estado:** ✅ **INTEGRACIÓN COMPLETADA** - Listo para testing  
**Progreso:** 7 de 7 fases (100%)
