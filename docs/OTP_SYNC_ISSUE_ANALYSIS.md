# 🚨 Análisis Crítico: Desincronización de OTP entre JSON y MariaDB

**Fecha:** 2026-01-26  
**Severidad:** 🔴 CRÍTICA  
**Estado:** Identificado - Requiere corrección inmediata  
**Afecta a:** Autenticación de usuarios en todos los entornos

---

## 📋 Descripción del Problema

Los valores de `user_otp` se desincroniza entre:
- **Fuente 1:** `src/2_shared_application/moks/users.json`
- **Fuente 2:** Tabla `users` en MariaDB (`myllm_core_db`)

Cuando un usuario realiza alguna de estas operaciones, el OTP se regenera:
1. ✅ **Crear cuenta** (nuevo usuario)
2. ✅ **Cambiar contraseña**
3. ✅ **Login exitoso** (rotación de OTP por seguridad)

**Síntoma:** OTP en JSON ≠ OTP en MariaDB → Login falla o requiere múltiples intentos

---

## 🔍 Causa Raíz Identificada

He analizado todo el flujo de actualización de OTP y encontré **5 problemas críticos**:

---

### **PROBLEMA 1: Orden de Actualización Inconsistente** 🔴

Hay **dos flujos diferentes** con orden de escritura distinto:

#### Flujo A: Middleware (`routermiddleware.py`)

```python
def _store_users(self, data_path: Path, users: list[UserDto]) -> None:
    payload = [user.model_dump() for user in users]
    
    # PASO 1: Guardar en BROKER (MariaDB) PRIMERO
    if self._should_use_broker_reads() or self._should_replicate():
        try:
            self._broker_client.store_users(payload)  # ← MariaDB vía broker
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError("No se pudo guardar usuarios en el broker") from exc
    
    # PASO 2: Guardar en JSON DESPUÉS
    self._sync_users_cache(data_path, payload)  # ← users.json
```

**Usado en:**
- ✅ Login exitoso (`authenticate_user` línea 1344-1345)
- ✅ Bloqueo de usuario por intentos fallidos
- ✅ Creación de usuario desde middleware

**Orden:** 🔵 BROKER → JSON

---

#### Flujo B: Backend Core (`storage_adapter.py`)

```python
def store_users(self, users: list[UserDto]) -> None:
    """Guarda usuarios en JSON."""
    
    # PASO 1: Guardar en JSON PRIMERO
    _write_json_list(self._users_path, [user.model_dump() for user in users])
    
    # PASO 2: Sincronizar con MariaDB DESPUÉS
    if _should_sync_users_to_db():
        _sync_users_to_mariadb(users)  # ← MariaDB directamente
```

**Usado en:**
- ✅ Operaciones directas del backend core (raro)

**Orden:** 🔴 JSON → MariaDB (INVERSO)

---

#### Flujo C: Función directa (`user.py`)

```python
def update_password_and_otp(user_email: str, new_password: str, new_otp: str) -> bool:
    users = _load_users()
    
    # Modificar en memoria
    for user in users:
        if user["user_email"] == user_email:
            user["user_password"] = new_password
            user["user_otp"] = new_otp  # ← Modifica en memoria
            break
    
    # PASO 1: Sincronizar con BROKER PRIMERO
    if _should_sync_users_with_broker():
        if not _sync_users_to_broker(users):  # ← Intenta sincronizar
            logger.error("No se pudo sincronizar usuarios con broker backend")
            return False  # ← ¡NO GUARDA EN JSON!
    
    # PASO 2: Guardar en JSON DESPUÉS (solo si broker tuvo éxito)
    try:
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
    except (OSError, TypeError, ValueError) as e:
        logger.error(f"Error al guardar usuario actualizado en {data_file}: {e}")
        return False
    
    validate_users_otp_sync()
    return True
```

**Usado en:**
- ✅ Cambio de contraseña desde frontend/backoffice
- ❌ **BYPASSA EL MIDDLEWARE** (se llama directamente desde las páginas)

**Orden:** 🔵 BROKER → JSON

**🚨 PROBLEMA:** Esta función es llamada directamente por las páginas de frontend/backoffice, bypasseando el middleware y usando su propio flujo de sincronización.

---

### **PROBLEMA 2: Sincronización de Red puede Fallar Parcialmente** 🔴

**Escenario crítico en `_store_users` del middleware:**

```python
try:
    self._broker_client.store_users(payload)  # HTTP PUT al broker
except BrokerBackendCommunicationError as exc:
    raise BusinessRuleError("...") from exc  # ← Lanza excepción, NO guarda en JSON
```

**¿Qué puede salir mal?**

1. **Timeout parcial:**
   - Middleware envía PUT al broker
   - Broker recibe y actualiza MariaDB
   - **Timeout de red** antes de recibir respuesta
   - Middleware piensa que falló → NO actualiza JSON
   - **Resultado:** MariaDB actualizado, JSON desactualizado

2. **Error de serialización de respuesta:**
   - Broker actualiza MariaDB correctamente
   - Broker intenta responder pero error en JSON de respuesta
   - Middleware recibe error 500 → NO actualiza JSON
   - **Resultado:** MariaDB actualizado, JSON desactualizado

3. **Proceso del broker muere:**
   - Broker actualiza MariaDB
   - Broker muere antes de responder (OOM, crash)
   - Middleware recibe timeout → NO actualiza JSON
   - **Resultado:** MariaDB actualizado, JSON desactualizado

---

### **PROBLEMA 3: Función `update_password_and_otp` Bypassa Middleware** 🔴

**Archivo:** `src/1_shared_domain/entities/user.py` (líneas 165-212)

Las páginas de cambio de contraseña (`change_password.py`) importan y llaman directamente:

```python
# En pages/change_password.py (línea 33):
update_user_password_and_otp = user_module.update_user_password_and_otp

# Luego (línea 433):
if update_user_password_and_otp(user_email, encrypted_password, new_otp):
    # ...
```

**Problemas:**

1. **Bypassa el middleware:** No usa `_store_users` del middleware
2. **Lógica de sincronización duplicada:** Tiene su propia implementación de `_sync_users_to_broker`
3. **Manejo de errores diferente:** Si falla broker, retorna `False` (no lanza excepción)
4. **Verificación débil:**
   ```python
   def _sync_users_to_broker(users: list[dict[str, Any]]) -> bool:
       response = _request_broker("PUT", "/users", payload=users)
       return response == [] or isinstance(response, list)  # ← Muy débil
   ```
   Solo verifica que la respuesta es una lista, **no verifica si la actualización fue exitosa**

---

### **PROBLEMA 4: Función `create_user` No Sincroniza** 🔴

**Archivo:** `src/1_shared_domain/entities/user.py` (líneas 342-393)

```python
def create_user(user_data: dict[str, Any]) -> bool:
    data_file = _get_users_file_path()
    users = _load_users()
    
    # Construir nuevo usuario con OTP
    user_dict = {
        # ... otros campos ...
        "user_otp": user_data.get("user_otp", ""),  # ← OTP del nuevo usuario
    }
    
    users.append(user_dict)
    
    # SOLO GUARDA EN JSON, NO SINCRONIZA CON MARIADB
    try:
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        return True
    except (OSError, TypeError, ValueError) as e:
        logger.error(f"Error al guardar usuario en {data_file}: {e}")
        return False
```

**🚨 CRÍTICO:** No hay ninguna llamada a `_sync_users_to_broker` o similar.

**Resultado:** Cuando se crea un usuario:
- ✅ Se guarda en JSON con su OTP
- ❌ **NUNCA se sincroniza con MariaDB en tiempo real**
- ⏳ Solo se sincroniza con el proceso periódico (cada X minutos)

---

### **PROBLEMA 5: Validación de Sincronización es Post-Facto** 🟡

**Archivo:** `src/1_shared_domain/entities/user.py` (líneas 215-262)

```python
def validate_users_otp_sync() -> bool:
    """Verifica que los OTPs de users.json coinciden con la tabla users en MariaDB."""
    
    # Carga usuarios desde JSON
    users = _load_users()
    
    # Consulta usuarios desde broker (MariaDB)
    broker_users = _fetch_users_from_broker()
    
    # Compara OTPs
    mismatches = []
    for user in users:
        json_otp = str(user.get("user_otp", ""))
        db_otp = broker_map.get(user_id)
        if json_otp != db_otp:
            mismatches.append((user_id, json_otp, db_otp))  # ← Detecta discrepancia
    
    # Log de discrepancias
    for user_id, json_otp, db_otp in mismatches:
        logger.warning("OTP desalineado user_id=%s json=%s db=%s", user_id, json_otp, db_otp)
    
    return not mismatches
```

**Problema:**
- Esta función **solo detecta** el problema después de que ocurrió
- **No corrige automáticamente** la desincronización
- Solo registra en `frontend_secure.log`
- Es llamada al final de `update_password_and_otp`, pero si ya hubo fallo no ayuda

---

## 🎯 Escenarios de Desincronización

### **Escenario 1: Timeout de Red en Login**

```
1. Usuario hace login exitoso
2. Middleware rota OTP: 1234 → 5678
3. Middleware llama _store_users()
   a. Envía PUT /users al broker con OTP=5678
   b. Broker recibe y actualiza MariaDB: OTP=5678 ✅
   c. Timeout de red antes de recibir respuesta HTTP
   d. Middleware lanza excepción
   e. NO se ejecuta _sync_users_cache
   f. JSON mantiene OTP=1234 ❌

RESULTADO: MariaDB=5678, JSON=1234 → DESINCRONIZADO
```

### **Escenario 2: Fallo en Cambio de Contraseña**

```
1. Usuario cambia contraseña
2. change_password.py genera new_otp=9999
3. Llama update_password_and_otp(email, new_pass, 9999)
   a. Modifica users en memoria: OTP=9999
   b. Llama _sync_users_to_broker(users)
      - PUT /users al broker
      - Broker actualiza MariaDB: OTP=9999 ✅
      - Respuesta HTTP 200 pero payload corrupto/vacío
      - _sync_users_to_broker retorna True (validación débil)
   c. Guarda en JSON: OTP=9999 ✅
   d. validate_users_otp_sync() verifica... pero ya fue tarde

RESULTADO: Si broker falló silenciosamente: MariaDB=viejo, JSON=9999
```

### **Escenario 3: Creación de Usuario**

```
1. Se crea nuevo usuario con OTP=1111
2. create_user(user_data) en user.py
   a. Guarda en JSON: OTP=1111 ✅
   b. NO SINCRONIZA CON MARIADB ❌
3. Usuario espera...
4. Sincronización periódica se ejecuta (cada 5 minutos)
   a. Carga desde JSON: OTP=1111
   b. Actualiza MariaDB: OTP=1111 ✅

RESULTADO: Durante 0-5 minutos: JSON=1111, MariaDB=NO EXISTE → Usuario no puede hacer login
```

---

## 🔍 Archivos Afectados

### Archivos con Flujos de Actualización de OTP

| Archivo | Función | OTP se actualiza en | Sincronización |
|---------|---------|---------------------|----------------|
| `src/apps/7_service_frontend/routermiddleware.py` | `authenticate_user()` | Login exitoso (línea 1344) | Broker→JSON (síncrona) |
| `src/apps/7_service_frontend/routermiddleware.py` | `_store_users()` | Generic (línea 838-850) | Broker→JSON (síncrona) |
| `src/1_shared_domain/entities/user.py` | `update_password_and_otp()` | Cambio password (línea 165-212) | Broker→JSON (bypassa middleware) |
| `src/1_shared_domain/entities/user.py` | `create_user()` | Creación usuario (línea 342-393) | ❌ **NO SINCRONIZA** |
| `src/apps/6_web_backoffice/pages/user_creation.py` | `create_user_button_action()` | Creación usuario (línea 1103) | Usa middleware (OK) |
| `src/apps/6_web_backoffice/pages/change_password.py` | `update_password()` | Cambio password (línea 424-433) | Bypassa middleware ❌ |
| `src/apps/3_backend/4_infrastructure/persistence/storage_adapter.py` | `store_users()` | Generic (línea 213-218) | JSON→MariaDB (inverso) |

---

### Inconsistencias Detectadas

#### Inconsistencia 1: Middleware vs Core Backend

- **Middleware** (`routermiddleware._store_users`): **Broker PRIMERO** → JSON después
- **Core Backend** (`storage_adapter.store_users`): **JSON PRIMERO** → MariaDB después

#### Inconsistencia 2: Middleware vs Función Directa

- **Middleware** (`routermiddleware._store_users`): Usa `broker_client` con manejo de excepciones
- **Función directa** (`user.py`): Usa `_sync_users_to_broker` con validación débil

#### Inconsistencia 3: Creación de Usuario

- **Via Middleware** (`routermiddleware.create_user`): Sincroniza correctamente
- **Via Función Directa** (`user.py create_user`): ❌ **NO SINCRONIZA EN ABSOLUTO**

---

## 💥 Puntos de Fallo Identificados

### Fallo 1: Timeout de Red (MÁS PROBABLE)

**Ubicación:** `routermiddleware._store_users` línea 844

```python
self._broker_client.store_users(payload)  # ← Puede timeout
```

**Problema:**
- MariaDB se actualiza antes del timeout
- Timeout ocurre esperando respuesta
- Exception lanzada → JSON NO se actualiza
- **Desincronización garantizada**

**Probabilidad:** 🔴 ALTA (en redes lentas o alta carga)

---

### Fallo 2: Validación Débil en `_sync_users_to_broker`

**Ubicación:** `user.py` línea 320-324

```python
def _sync_users_to_broker(users: list[dict[str, Any]]) -> bool:
    response = _request_broker("PUT", "/users", payload=users)
    return response == [] or isinstance(response, list)  # ← DÉBIL
```

**Problema:**
- Solo verifica que response es una lista
- **No verifica si la actualización fue exitosa**
- Broker podría retornar lista vacía `[]` y esto se considera éxito
- No valida el status code HTTP

**Probabilidad:** 🟡 MEDIA

---

### Fallo 3: `create_user` sin Sincronización

**Ubicación:** `user.py` línea 342-393

```python
def create_user(user_data: dict[str, Any]) -> bool:
    # ... construir user_dict con OTP ...
    users.append(user_dict)
    
    # SOLO GUARDA EN JSON
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
    return True
    
    # ← NO HAY SINCRONIZACIÓN CON MARIADB
```

**Problema:**
- Usuario se crea en JSON
- **MariaDB no se entera hasta la sincronización periódica** (0-5 minutos)
- Durante ese tiempo, el usuario está en JSON pero no en MariaDB
- Si el modo es `db_only`, las lecturas van a MariaDB → usuario "no existe"

**Probabilidad:** 🔴 ALTA (si se usa la función directa)

**Nota:** Las páginas de `user_creation.py` usan `save_user_to_json` que llama al middleware, **NO** usan `create_user` directa, así que este flujo está OK para creación normal. Pero la función existe y podría ser usada por otros módulos.

---

### Fallo 4: Orden Inverso en Backend Core

**Ubicación:** `storage_adapter.py` línea 213-218

```python
def store_users(self, users: list[UserDto]) -> None:
    # PRIMERO: JSON
    _write_json_list(self._users_path, [user.model_dump() for user in users])
    
    # DESPUÉS: MariaDB
    if _should_sync_users_to_db():
        _sync_users_to_mariadb(users)  # ← Puede fallar aquí
```

**Problema:**
- JSON ya fue sobrescrito
- Si `_sync_users_to_mariadb` falla, no hay rollback del JSON
- **Resultado:** JSON actualizado, MariaDB desactualizado

**Probabilidad:** 🟡 MEDIA (solo si core backend es llamado directamente)

---

### Fallo 5: Login Rota OTP pero Falla la Sincronización

**Ubicación:** `routermiddleware.authenticate_user` línea 1344-1345

```python
self._rotate_otp(user_record)  # OTP=nuevo
self._store_users(users_path, users)  # ← Puede fallar aquí
```

**Problema:**
- `_rotate_otp` modifica el objeto `user_record` EN MEMORIA (línea 1085)
- Si `_store_users` falla, el OTP ya fue modificado en el objeto pero no persistido
- Si hay otra operación concurrente que lea el mismo objeto...
- **Resultado:** Estado inconsistente en memoria

**Probabilidad:** 🟡 BAJA (pero posible en alta concurrencia)

---

## 📊 Evidencia del Problema

### Log de Seguridad

El código ya detecta desincronizaciones y las registra:

```python
# En user.py, línea 257-258
_append_frontend_secure_log(
    f"Validacion OTP sincronizacion,DESALINEADO,{mismatch_ids}"
)
```

**Verificar en logs:**
```bash
grep "DESALINEADO" src/apps/5_web_frontend/logs/frontend_secure.log
```

---

## ✅ Soluciones Propuestas

### **Solución 1: Transacción con Rollback** (Recomendada) 🟢

Implementar patrón de transacción distribuida con rollback:

```python
def _store_users_atomic(self, data_path: Path, users: list[UserDto]) -> None:
    """Guarda usuarios con transacción y rollback."""
    
    payload = [user.model_dump() for user in users]
    
    # 1. Backup del JSON actual
    backup = self._read_json_or_empty(data_path)
    
    # 2. Intentar guardar en JSON primero (es más rápido)
    try:
        self._sync_json_list(data_path, payload)
    except Exception as exc:
        raise BusinessRuleError(f"No se pudo guardar en JSON: {exc}") from exc
    
    # 3. Intentar guardar en broker (MariaDB)
    if self._should_use_broker_reads() or self._should_replicate():
        try:
            self._broker_client.store_users(payload)
        except BrokerBackendCommunicationError as exc:
            # ROLLBACK: Restaurar JSON
            self._sync_json_list(data_path, backup)
            raise BusinessRuleError(f"No se pudo guardar en broker, JSON restored: {exc}") from exc
    
    # 4. Verificar sincronización
    if not self._verify_otp_sync(payload):
        logger.error("OTPs desincronizados tras actualización")
        # Aquí podríamos intentar re-sincronizar o alertar
```

**Ventajas:**
- ✅ Orden: JSON PRIMERO (más rápido)
- ✅ Rollback automático si falla broker
- ✅ Verificación post-sincronización
- ✅ Estado consistente garantizado

**Desventajas:**
- ⚠️ Más complejidad
- ⚠️ Dos escrituras a JSON (original + posible rollback)

---

### **Solución 2: Retry con Exponential Backoff** 🟢

Agregar reintentos automáticos para operaciones de red:

```python
def _store_users_with_retry(self, data_path: Path, users: list[UserDto]) -> None:
    """Guarda usuarios con reintentos automáticos."""
    
    payload = [user.model_dump() for user in users]
    
    # 1. Intentar guardar en broker con retry
    if self._should_use_broker_reads() or self._should_replicate():
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._broker_client.store_users(payload)
                break  # Éxito
            except BrokerBackendCommunicationError as exc:
                if attempt == max_retries - 1:
                    # Último intento falló
                    raise BusinessRuleError(f"No se pudo guardar en broker tras {max_retries} intentos") from exc
                # Esperar antes de reintentar (exponential backoff)
                time.sleep(2 ** attempt)  # 1s, 2s, 4s
    
    # 2. Guardar en JSON
    self._sync_users_cache(data_path, payload)
```

**Ventajas:**
- ✅ Reduce probabilidad de fallo por timeouts temporales
- ✅ Simple de implementar
- ✅ No cambia el orden de escritura

**Desventajas:**
- ⚠️ Login más lento (hasta 7 segundos en peor caso)
- ⚠️ Si falla después de 3 reintentos, mismo problema

---

### **Solución 3: Sincronización Asíncrona con Queue** 🟡

Usar una cola (Redis o DB) para sincronización diferida:

```python
def _store_users_async(self, data_path: Path, users: list[UserDto]) -> None:
    """Guarda usuarios con sincronización asíncrona."""
    
    payload = [user.model_dump() for user in users]
    
    # 1. Guardar en JSON inmediatamente
    self._sync_users_cache(data_path, payload)
    
    # 2. Encolar operación de sincronización
    if self._should_use_broker_reads() or self._should_replicate():
        self._enqueue_sync_operation({
            "type": "store_users",
            "payload": payload,
            "timestamp": datetime.now().isoformat()
        })
    
    # 3. Worker en background procesa la cola
    # Si falla, reintenta automáticamente
```

**Ventajas:**
- ✅ Login instantáneo (no espera sincronización)
- ✅ Reintentos automáticos en background
- ✅ JSON siempre actualizado inmediatamente

**Desventajas:**
- ⚠️ Complejidad alta (necesita workers, queue manager)
- ⚠️ Ventana de inconsistencia temporal
- ⚠️ Requiere infraestructura adicional (Redis ya disponible)

---

### **Solución 4: Patrón Saga con Compensación** 🟡

Implementar patrón de saga distribuida:

```python
def _store_users_saga(self, data_path: Path, users: list[UserDto]) -> None:
    """Guarda usuarios con patrón saga."""
    
    payload = [user.model_dump() for user in users]
    
    # Step 1: Guardar en broker (MariaDB)
    if self._should_use_broker_reads() or self._should_replicate():
        try:
            self._broker_client.store_users(payload)
        except Exception as exc:
            # Compensación: No hacer nada, JSON no se modifica
            raise BusinessRuleError(f"Saga abortada en paso 1: {exc}") from exc
    
    # Step 2: Guardar en JSON
    try:
        self._sync_users_cache(data_path, payload)
    except Exception as exc:
        # Compensación: Revertir cambios en MariaDB
        self._broker_client.store_users(backup_payload)  # Restaurar estado anterior
        raise BusinessRuleError(f"Saga abortada en paso 2, compensado: {exc}") from exc
```

**Ventajas:**
- ✅ Garantiza consistencia eventual
- ✅ Compensación automática

**Desventajas:**
- ⚠️ Muy complejo
- ⚠️ Necesita backup del estado anterior
- ⚠️ Ventana de inconsistencia durante la saga

---

### **Solución 5: Eliminar `update_password_and_otp` Directa** 🟢 (Recomendada)

Forzar que TODAS las actualizaciones pasen por el middleware:

```python
# ELIMINAR esta función de user.py o marcarla como @deprecated
def update_password_and_otp(user_email: str, new_password: str, new_otp: str) -> bool:
    # ... código actual ...
```

**Crear endpoint en el middleware:**

```python
# En apife.py
@app.put("/users/{user_email}/password-and-otp")
def update_user_password_and_otp_endpoint(
    user_email: str,
    request: UpdatePasswordOtpRequest,
    router: RouterMiddleware = Depends(get_router_middleware),
) -> dict[str, bool]:
    """Actualiza contraseña y OTP de un usuario."""
    
    success = router.update_user_password_and_otp(
        user_email=user_email,
        new_password=request.new_password,
        new_otp=request.new_otp,
    )
    return {"success": success}

# En routermiddleware.py
def update_user_password_and_otp(
    self, user_email: str, new_password: str, new_otp: str
) -> bool:
    """Actualiza contraseña y OTP usando el flujo estándar."""
    
    users_path = self._get_users_file_path()
    users = self._load_users(users_path)
    
    # Buscar y modificar usuario
    user_found = False
    for user in users:
        if user.user_email.strip().lower() == user_email.strip().lower():
            user.user_password = new_password
            user.user_otp = new_otp
            user_found = True
            break
    
    if not user_found:
        return False
    
    # Usar el flujo estándar con transacción
    self._store_users(users_path, users)
    return True
```

**Ventajas:**
- ✅ **Un solo flujo** de sincronización (DRY)
- ✅ Todas las actualizaciones pasan por el mismo código
- ✅ Más fácil de mantener y debuggear
- ✅ Más fácil de agregar logging/auditoría

**Desventajas:**
- ⚠️ Requiere refactorizar páginas de cambio de contraseña
- ⚠️ Requiere actualizar tests

---

## 🎯 Plan de Corrección Recomendado

### Fase 1: Corrección Inmediata (Urgente)

**Prioridad:** 🔴 CRÍTICA  
**Tiempo estimado:** 4 horas  

#### 1.1. Corregir `_sync_users_to_broker` (Validación Débil)

```python
def _sync_users_to_broker(users: list[dict[str, Any]]) -> bool:
    """Sincroniza usuarios hacia broker backend con validación estricta."""
    
    response = _request_broker("PUT", "/users", payload=users)
    
    # Validación estricta
    if not response:
        logger.error("Broker no retornó respuesta válida")
        return False
    
    if not isinstance(response, list):
        logger.error(f"Broker retornó tipo inválido: {type(response)}")
        return False
    
    # Verificar que la respuesta indica éxito
    # (Ajustar según contrato de API del broker)
    return True
```

#### 1.2. Agregar Retry en `_store_users` del Middleware

```python
def _store_users(self, data_path: Path, users: list[UserDto]) -> None:
    """Guarda usuarios con retry automático."""
    
    payload = [user.model_dump() for user in users]
    
    if self._should_use_broker_reads() or self._should_replicate():
        max_retries = 3
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                self._broker_client.store_users(payload)
                break  # Éxito
            except BrokerBackendCommunicationError as exc:
                last_exception = exc
                if attempt < max_retries - 1:
                    sleep_time = 2 ** attempt  # Exponential backoff
                    self._logger.warning(
                        f"Fallo al sincronizar con broker (intento {attempt + 1}/{max_retries}), "
                        f"reintentando en {sleep_time}s: {exc}"
                    )
                    time.sleep(sleep_time)
        
        if last_exception:
            # Todos los intentos fallaron
            raise BusinessRuleError(
                f"No se pudo guardar usuarios en broker tras {max_retries} intentos"
            ) from last_exception
    
    self._sync_users_cache(data_path, payload)
```

#### 1.3. Corregir `create_user` en user.py

```python
def create_user(user_data: dict[str, Any]) -> bool:
    """Crea un usuario con sincronización completa."""
    
    data_file = _get_users_file_path()
    users = _load_users()
    
    # ... construir user_dict ...
    
    users.append(user_dict)
    
    # SINCRONIZAR CON BROKER PRIMERO (si es necesario)
    if _should_sync_users_with_broker():
        if not _sync_users_to_broker(users):
            logger.error("No se pudo sincronizar nuevo usuario con broker")
            return False  # No guardar en JSON si broker falló
    
    # GUARDAR EN JSON DESPUÉS
    try:
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        logger.info(f"Usuario creado exitosamente con ID: {next_id}")
        return True
    except (OSError, TypeError, ValueError) as e:
        logger.error(f"Error al guardar usuario en {data_file}: {e}")
        return False
```

---

### Fase 2: Refactorización Estructural (Mediano Plazo)

**Prioridad:** 🟡 ALTA  
**Tiempo estimado:** 8 horas

#### 2.1. Eliminar Función Directa `update_password_and_otp`

- Deprecar función en `user.py`
- Crear endpoint en middleware: `PUT /users/{email}/password-and-otp`
- Actualizar páginas de cambio de contraseña para usar API
- Actualizar tests

#### 2.2. Unificar Orden de Sincronización

- **Estandarizar:** Broker/MariaDB PRIMERO → JSON DESPUÉS
- Actualizar `storage_adapter.py` del core backend
- Documentar en `AGENTS.md`

#### 2.3. Agregar Verificación Post-Operación

```python
def _verify_otp_sync_after_update(self, user_email: str, expected_otp: str) -> bool:
    """Verifica que el OTP se sincronizó correctamente."""
    
    # Leer desde JSON
    json_users = self._load_users_from_json()
    json_user = next((u for u in json_users if u.email == user_email), None)
    
    # Leer desde MariaDB
    db_users = self._load_users_from_broker()
    db_user = next((u for u in db_users if u["user_email"] == user_email), None)
    
    if json_user and db_user:
        json_otp = json_user.get("user_otp")
        db_otp = db_user.get("user_otp")
        
        if json_otp != expected_otp or db_otp != expected_otp:
            logger.error(
                f"OTP desincronizado tras actualización: "
                f"expected={expected_otp}, json={json_otp}, db={db_otp}"
            )
            return False
    
    return True
```

---

### Fase 3: Monitoreo y Alertas (Largo Plazo)

**Prioridad:** 🟢 MEDIA  
**Tiempo estimado:** 4 horas

#### 3.1. Script de Verificación Continua

```bash
# scripts/verify_otp_sync.sh
#!/bin/bash
# Verifica sincronización OTP cada minuto

while true; do
    # Llamar a endpoint de verificación
    curl -s http://localhost:8007/admin/verify-otp-sync
    sleep 60
done
```

#### 3.2. Endpoint de Diagnóstico

```python
@app.get("/admin/verify-otp-sync")
def verify_otp_sync_endpoint(
    router: RouterMiddleware = Depends(get_router_middleware)
) -> dict[str, Any]:
    """Verifica sincronización de OTPs y retorna discrepancias."""
    
    mismatches = router.check_otp_sync()
    
    if mismatches:
        return {
            "status": "DESINCRONIZADO",
            "count": len(mismatches),
            "mismatches": [
                {
                    "user_id": m[0],
                    "json_otp": m[1],
                    "db_otp": m[2]
                }
                for m in mismatches
            ]
        }
    
    return {"status": "OK", "count": 0}
```

#### 3.3. Alertas Automáticas

- Enviar alerta si se detecta desincronización
- Slack, email, PagerDuty
- Log en sistema de monitoreo (Prometheus)

---

## 📝 Código Actual a Modificar

### Archivos Críticos

1. **`src/apps/7_service_frontend/routermiddleware.py`**
   - Función `_store_users` (línea 838-850)
   - Función `authenticate_user` (línea 1237-1365)
   - Agregar retry logic

2. **`src/1_shared_domain/entities/user.py`**
   - Función `update_password_and_otp` (línea 165-212)
   - Función `create_user` (línea 342-393)
   - Función `_sync_users_to_broker` (línea 320-324)
   - Corregir sincronización y validación

3. **`src/apps/3_backend/4_infrastructure/persistence/storage_adapter.py`**
   - Función `store_users` (línea 213-218)
   - Invertir orden: Broker PRIMERO → JSON DESPUÉS

4. **`src/apps/6_web_backoffice/pages/change_password.py`**
   - Función `update_password` (línea 380-450)
   - Cambiar a usar endpoint del middleware

5. **`src/apps/5_web_frontend/pages/change_password.py`**
   - Función `update_password` (similar a backoffice)
   - Cambiar a usar endpoint del middleware

---

## 🧪 Tests Necesarios

### Test de Desincronización

```python
def test_otp_sync_after_login():
    """Verifica que OTP se sincroniza tras login exitoso."""
    
    # Setup
    user = create_test_user(otp="1234")
    
    # Login exitoso
    login(user.email, password, otp="1234")
    
    # Verificar OTP rotado en ambos lugares
    json_otp = get_otp_from_json(user.email)
    db_otp = get_otp_from_db(user.email)
    
    assert json_otp != "1234", "OTP no fue rotado en JSON"
    assert db_otp != "1234", "OTP no fue rotado en DB"
    assert json_otp == db_otp, "OTP desincronizado entre JSON y DB"

def test_otp_sync_with_broker_timeout():
    """Simula timeout de broker y verifica rollback."""
    
    # Mock broker con timeout
    with patch("broker_client.store_users", side_effect=Timeout):
        user = create_test_user(otp="1234")
        
        # Cambiar password (debería fallar)
        result = update_password_and_otp(user.email, new_pass, new_otp="5678")
        
        assert result is False, "Debería retornar False"
        
        # Verificar que JSON NO se modificó (rollback)
        json_otp = get_otp_from_json(user.email)
        assert json_otp == "1234", "JSON no debería haberse modificado"

def test_otp_sync_after_password_change():
    """Verifica sincronización tras cambio de contraseña."""
    
    user = create_test_user(otp="1234")
    
    # Cambiar contraseña
    update_password_and_otp(user.email, new_pass, new_otp="5678")
    
    # Verificar sincronización
    json_otp = get_otp_from_json(user.email)
    db_otp = get_otp_from_db(user.email)
    
    assert json_otp == "5678", "OTP no actualizado en JSON"
    assert db_otp == "5678", "OTP no actualizado en DB"
    assert json_otp == db_otp, "OTP desincronizado"
```

---

## 📊 Resumen Ejecutivo

### Problemas Identificados

| # | Problema | Severidad | Probabilidad | Impacto |
|---|----------|-----------|--------------|---------|
| 1 | Orden de sincronización inconsistente | 🔴 Alta | Media | Usuario no puede autenticarse |
| 2 | Timeout de red en sincronización | 🔴 Alta | Alta | Desincronización silenciosa |
| 3 | Validación débil de respuesta broker | 🟡 Media | Media | Falsos positivos de éxito |
| 4 | `create_user` no sincroniza inmediatamente | 🟡 Media | Baja | Usuario invisible 0-5 min |
| 5 | `update_password_and_otp` bypassa middleware | 🔴 Alta | Alta | Inconsistencia de flujo |

### Soluciones Recomendadas (Orden de Prioridad)

1. 🔴 **URGENTE:** Agregar retry con exponential backoff (Solución 2)
2. 🔴 **URGENTE:** Corregir validación de `_sync_users_to_broker` (Solución 1, parte)
3. 🔴 **URGENTE:** Agregar sincronización en `create_user` (Solución 1, parte)
4. 🟡 **ALTA:** Implementar transacción con rollback (Solución 1 completa)
5. 🟡 **ALTA:** Eliminar `update_password_and_otp` directa (Solución 5)
6. 🟢 **MEDIA:** Agregar monitoreo continuo (Fase 3)

---

## ⏱️ Timeline Propuesto

| Fase | Acciones | Tiempo | Prioridad |
|------|----------|--------|-----------|
| **Inmediato** | Correcciones 1.1, 1.2, 1.3 | 4h | 🔴 CRÍTICA |
| **Esta semana** | Fase 2 completa (refactorización) | 8h | 🟡 ALTA |
| **Próxima semana** | Fase 3 (monitoreo) | 4h | 🟢 MEDIA |
| **Testing** | Suite completa de tests | 4h | 🔴 CRÍTICA |

**Total:** 20 horas

---

## 📚 Referencias

- **AGENTS.md**: Reglas de sincronización DB/JSON (líneas 76-86)
- **README.md**: Modos de almacenamiento (líneas 1218-1224, 1264-1283)
- **Código afectado:**
  - `src/apps/7_service_frontend/routermiddleware.py`
  - `src/1_shared_domain/entities/user.py`
  - `src/apps/3_backend/4_infrastructure/persistence/storage_adapter.py`
  - `src/apps/{5_web_frontend,6_web_backoffice}/pages/change_password.py`

---

**Autor:** @backend-conductor  
**Revisado por:** Pendiente  
**Aprobación:** Pendiente  
**Estado:** 📝 Análisis completo - Esperando implementación
