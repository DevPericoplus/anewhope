# 🔧 Corrección de Sincronización de OTP - Plan de Implementación

**Fecha:** 2026-01-26  
**Prioridad:** 🔴 CRÍTICA  
**Tiempo estimado:** 4 horas (Fase 1)  
**Archivos a modificar:** 3 archivos críticos

---

## 🎯 Objetivo

Garantizar que el `user_otp` siempre esté sincronizado entre `users.json` y la tabla `users` en MariaDB en los siguientes escenarios:
1. Login exitoso (rotación de OTP)
2. Cambio de contraseña
3. Creación de nuevo usuario

---

## 📝 Cambios a Implementar

### **CAMBIO 1: Agregar Retry en Middleware** 🔴 URGENTE

**Archivo:** `src/apps/7_service_frontend/routermiddleware.py`  
**Línea:** 838 (función `_store_users`)  
**Razón:** Evitar fallo por timeouts temporales de red

**Código actual:**

```python
def _store_users(self, data_path: Path, users: list[UserDto]) -> None:
    """Guarda los usuarios en el archivo JSON."""
    
    payload = [user.model_dump() for user in users]
    if self._should_use_broker_reads() or self._should_replicate():
        try:
            self._broker_client.store_users(payload)
        except BrokerBackendCommunicationError as exc:
            raise BusinessRuleError(
                "No se pudo guardar usuarios en el broker"
            ) from exc
    self._sync_users_cache(data_path, payload)
```

**Código corregido:**

```python
def _store_users(self, data_path: Path, users: list[UserDto]) -> None:
    """Guarda los usuarios en el archivo JSON con retry automático."""
    
    payload = [user.model_dump() for user in users]
    
    if self._should_use_broker_reads() or self._should_replicate():
        max_retries = 3
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                self._broker_client.store_users(payload)
                self._logger.debug(
                    f"Usuarios sincronizados con broker (intento {attempt + 1}/{max_retries})"
                )
                break  # Éxito, salir del loop
            except BrokerBackendCommunicationError as exc:
                last_exception = exc
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    sleep_time = 2 ** attempt
                    self._logger.warning(
                        f"Fallo al sincronizar usuarios con broker "
                        f"(intento {attempt + 1}/{max_retries}). "
                        f"Reintentando en {sleep_time}s: {exc}"
                    )
                    import time
                    time.sleep(sleep_time)
                else:
                    # Último intento falló
                    self._logger.error(
                        f"Todos los intentos de sincronización con broker fallaron "
                        f"tras {max_retries} intentos: {exc}"
                    )
        
        # Si todos los intentos fallaron, lanzar excepción
        if last_exception:
            raise BusinessRuleError(
                f"No se pudo guardar usuarios en broker tras {max_retries} intentos. "
                f"OTP NO sincronizado."
            ) from last_exception
    
    # Guardar en JSON (cache local)
    self._sync_users_cache(data_path, payload)
```

**Agregar import al inicio del archivo:**

```python
import time  # ← Añadir si no existe
```

---

### **CAMBIO 2: Corregir Validación en user.py** 🔴 URGENTE

**Archivo:** `src/1_shared_domain/entities/user.py`  
**Línea:** 320 (función `_sync_users_to_broker`)  
**Razón:** Validación actual es demasiado débil

**Código actual:**

```python
def _sync_users_to_broker(users: list[dict[str, Any]]) -> bool:
    """Sincroniza usuarios hacia broker backend."""
    
    response = _request_broker("PUT", "/users", payload=users)
    return response == [] or isinstance(response, list)  # ← DÉBIL
```

**Código corregido:**

```python
def _sync_users_to_broker(users: list[dict[str, Any]]) -> bool:
    """Sincroniza usuarios hacia broker backend con validación estricta."""
    
    try:
        response = _request_broker("PUT", "/users", payload=users)
        
        # Validación estricta de la respuesta
        if response is None:
            logger.error("Broker retornó respuesta None (posible timeout)")
            return False
        
        if not isinstance(response, (list, dict)):
            logger.error(f"Broker retornó tipo inválido: {type(response)}")
            return False
        
        # Si el broker retorna dict con "success", verificarlo
        if isinstance(response, dict):
            success = response.get("success", False)
            if not success:
                logger.error(f"Broker indicó fallo: {response}")
                return False
        
        # Si todo OK
        logger.debug("Usuarios sincronizados exitosamente con broker")
        return True
        
    except Exception as exc:
        logger.error(f"Excepción al sincronizar con broker: {exc}")
        return False
```

---

### **CAMBIO 3: Agregar Sincronización en create_user** 🔴 URGENTE

**Archivo:** `src/1_shared_domain/entities/user.py`  
**Línea:** 342 (función `create_user`)  
**Razón:** Actualmente NO sincroniza con MariaDB al crear usuario

**Código actual:**

```python
def create_user(user_data: dict[str, Any]) -> bool:
    data_file = _get_users_file_path()
    users = _load_users()
    
    # Determinar siguiente ID
    if users:
        existing_ids = [
            user.get("user_id", 0)
            for user in users
            if isinstance(user.get("user_id"), int)
        ]
        next_id = max(existing_ids, default=0) + 1
    else:
        next_id = 1
    
    # Construir nuevo usuario
    user_dict = {
        "user_id": next_id,
        # ... otros campos ...
        "user_otp": user_data.get("user_otp", ""),
        # ...
    }
    
    users.append(user_dict)
    
    # SOLO GUARDA EN JSON - NO SINCRONIZA
    try:
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        logger.info(f"Usuario creado exitosamente con ID: {next_id}")
        return True
    except (OSError, TypeError, ValueError) as e:
        logger.error(f"Error al guardar usuario en {data_file}: {e}")
        return False
```

**Código corregido:**

```python
def create_user(user_data: dict[str, Any]) -> bool:
    """
    Crea un nuevo usuario con sincronización completa en JSON y MariaDB.
    
    IMPORTANTE: Ahora sincroniza inmediatamente con broker/MariaDB si es necesario.
    """
    data_file = _get_users_file_path()
    users = _load_users()
    
    # Determinar siguiente ID
    if users:
        existing_ids = [
            user.get("user_id", 0)
            for user in users
            if isinstance(user.get("user_id"), int)
        ]
        next_id = max(existing_ids, default=0) + 1
    else:
        next_id = 1
    
    # Construir nuevo usuario
    user_dict = {
        "user_id": next_id,
        "organization_id": user_data.get("organization_id", 1),
        "identity_type_id": user_data.get("identity_type_id", 1),
        "user_name": user_data.get("user_name", "").strip(),
        "user_password": user_data.get("user_password", ""),
        "user_email": user_data.get("user_email", "").strip().lower(),
        "user_mobile": user_data.get("user_mobile", "").strip(),
        "user_otp": user_data.get("user_otp", ""),
        "active": user_data.get("active", True),
        "blocked": user_data.get("blocked", False),
        "contact_info": user_data.get("contact_info", {}),
        "billing_info": user_data.get("billing_info", {}),
    }
    
    users.append(user_dict)
    
    # SINCRONIZAR CON BROKER PRIMERO (si es necesario)
    if _should_sync_users_with_broker():
        logger.info(f"Sincronizando nuevo usuario (ID: {next_id}) con broker...")
        if not _sync_users_to_broker(users):
            logger.error(
                f"No se pudo sincronizar nuevo usuario con broker. "
                f"Usuario NO será creado para mantener consistencia."
            )
            return False  # ← NO guardar en JSON si broker falló
        logger.debug(f"Usuario {next_id} sincronizado exitosamente con broker")
    
    # GUARDAR EN JSON DESPUÉS (solo si broker tuvo éxito o no es necesario)
    try:
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        logger.info(f"Usuario creado exitosamente con ID: {next_id}")
        
        # Validar sincronización
        validate_users_otp_sync()
        
        return True
    except (OSError, TypeError, ValueError) as e:
        logger.error(f"Error al guardar usuario en {data_file}: {e}")
        
        # Si ya sincronizamos con broker pero falló el JSON, tenemos un problema
        if _should_sync_users_with_broker():
            logger.critical(
                f"INCONSISTENCIA CRÍTICA: Usuario {next_id} guardado en broker "
                f"pero falló guardado en JSON. Requiere corrección manual."
            )
        
        return False
```

---

### **CAMBIO 4: Mejorar update_password_and_otp** 🔴 URGENTE

**Archivo:** `src/1_shared_domain/entities/user.py`  
**Línea:** 165 (función `update_password_and_otp`)  
**Razón:** Agregar retry y mejor logging

**Agregar retry en la sincronización:**

```python
def update_password_and_otp(user_email: str, new_password: str, new_otp: str) -> bool:
    """
    Actualiza la contraseña y el OTP de un usuario existente.
    
    IMPORTANTE: Ahora incluye retry automático para sincronización con broker.
    """
    data_file = _get_users_file_path()
    users = _load_users()
    if not users:
        logger.warning("No hay usuarios en el archivo")
        return False
    
    normalized_input = user_email.strip().lower()
    user_found = False
    user_id = None
    
    for user in users:
        user_email_value = user.get("user_email", "")
        if user_email_value.strip().lower() == normalized_input:
            user["user_password"] = new_password
            user["user_otp"] = new_otp
            user_id = user.get("user_id")
            user_found = True
            logger.info(
                f"Usuario {user_email} (ID: {user_id}) actualizado: "
                f"contraseña y OTP modificados"
            )
            break
    
    if not user_found:
        logger.warning(f"Usuario con email {user_email} no encontrado")
        return False
    
    # SINCRONIZAR CON BROKER CON RETRY
    if _should_sync_users_with_broker():
        max_retries = 3
        sync_success = False
        
        for attempt in range(max_retries):
            if _sync_users_to_broker(users):
                logger.debug(
                    f"Usuario {user_id} sincronizado con broker "
                    f"(intento {attempt + 1}/{max_retries})"
                )
                sync_success = True
                break
            else:
                if attempt < max_retries - 1:
                    sleep_time = 2 ** attempt
                    logger.warning(
                        f"Fallo al sincronizar usuario {user_id} con broker "
                        f"(intento {attempt + 1}/{max_retries}). "
                        f"Reintentando en {sleep_time}s..."
                    )
                    import time
                    time.sleep(sleep_time)
        
        if not sync_success:
            logger.error(
                f"No se pudo sincronizar usuario {user_id} con broker backend "
                f"tras {max_retries} intentos. OTP NO será actualizado para "
                f"mantener consistencia."
            )
            return False  # ← NO guardar en JSON si todos los intentos fallaron
    
    # GUARDAR EN JSON
    try:
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        logger.info(f"Usuario {user_id} guardado en JSON con nuevo OTP")
    except (OSError, TypeError, ValueError) as e:
        logger.error(f"Error al guardar usuario actualizado en {data_file}: {e}")
        
        # Si ya sincronizamos con broker pero falló JSON, inconsistencia crítica
        if _should_sync_users_with_broker():
            logger.critical(
                f"INCONSISTENCIA CRÍTICA: Usuario {user_id} actualizado en broker "
                f"pero falló guardado en JSON. OTP desincronizado. "
                f"Requiere corrección manual o sincronización periódica."
            )
        
        return False
    
    # VALIDAR SINCRONIZACIÓN
    validate_users_otp_sync()
    return True
```

**Agregar import al inicio del archivo si no existe:**

```python
import time  # Para sleep en retry
```

---

### **CAMBIO 2: Mejorar Validación de _sync_users_to_broker** 🔴 URGENTE

**Archivo:** `src/1_shared_domain/entities/user.py`  
**Línea:** 320 (función `_sync_users_to_broker`)  
**Razón:** Validación actual es muy débil y puede dar falsos positivos

**Código actual:**

```python
def _sync_users_to_broker(users: list[dict[str, Any]]) -> bool:
    """Sincroniza usuarios hacia broker backend."""
    
    response = _request_broker("PUT", "/users", payload=users)
    return response == [] or isinstance(response, list)  # ← DÉBIL
```

**Código corregido:**

```python
def _sync_users_to_broker(users: list[dict[str, Any]]) -> bool:
    """
    Sincroniza usuarios hacia broker backend con validación estricta.
    
    Returns:
        True si la sincronización fue exitosa, False en caso contrario.
    """
    try:
        response = _request_broker("PUT", "/users", payload=users)
        
        # Validación estricta de la respuesta
        if response is None:
            logger.error("Broker retornó None (posible timeout o error de servidor)")
            return False
        
        # Si el broker retorna dict con "success", verificarlo
        if isinstance(response, dict):
            success = response.get("success", False)
            if success:
                logger.debug("Broker confirmó sincronización exitosa")
                return True
            else:
                error_detail = response.get("detail", "Unknown error")
                logger.error(f"Broker indicó fallo en sincronización: {error_detail}")
                return False
        
        # Si retorna lista, considerar éxito (retro-compatibilidad)
        if isinstance(response, list):
            logger.debug("Broker retornó lista (sincronización asumida como exitosa)")
            return True
        
        # Cualquier otro tipo de respuesta es inválida
        logger.error(f"Broker retornó tipo inválido: {type(response)}")
        return False
        
    except Exception as exc:
        logger.error(f"Excepción al sincronizar con broker: {exc}", exc_info=True)
        return False
```

---

### **CAMBIO 3: Agregar Sincronización en create_user** 🔴 URGENTE

Ver CAMBIO 1 de la sección anterior (ya documentado).

---

### **CAMBIO 4: Verificar Respuesta del Broker Backend** 🟡 ALTA

**Archivo:** `src/apps/8_service_backend/apibe.py`  
**Línea:** 214 (endpoint `store_users`)  
**Razón:** Retornar respuesta más informativa

**Código actual:**

```python
@app.put("/users")
def store_users(
    payload: list[dict[str, Any]],
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Guarda usuarios."""
    
    try:
        router.store_users(payload)
        return {"success": True}  # ← Solo retorna success
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
```

**Código mejorado:**

```python
@app.put("/users")
def store_users(
    payload: list[dict[str, Any]],
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Guarda usuarios con confirmación detallada."""
    
    try:
        router.store_users(payload)
        
        # Retornar respuesta más informativa
        return {
            "success": True,
            "users_count": len(payload),
            "timestamp": datetime.now().isoformat(),
        }
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
```

**Agregar import:**

```python
from datetime import datetime
```

---

## 🧪 Tests a Crear

### Test 1: Sincronización con Timeout

**Archivo:** `src/apps/7_service_frontend/tests/test_otp_sync_timeout.py` (NUEVO)

```python
"""Test de sincronización OTP con timeout simulado."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

def test_otp_sync_with_broker_timeout_retries():
    """Verifica que se reintenta tras timeout del broker."""
    
    # Mock del broker que falla 2 veces y tiene éxito la 3ra
    mock_broker = MagicMock()
    mock_broker.store_users.side_effect = [
        Exception("Timeout"),  # Intento 1
        Exception("Timeout"),  # Intento 2
        None,  # Intento 3: éxito
    ]
    
    # ... configurar router con mock_broker ...
    
    # Crear usuario y actualizar OTP
    result = router._store_users(users_path, users)
    
    # Verificar que se intentó 3 veces
    assert mock_broker.store_users.call_count == 3
    
    # Verificar que finalmente se guardó en JSON
    assert result is True


def test_otp_sync_all_retries_fail():
    """Verifica que NO se guarda en JSON si todos los reintentos fallan."""
    
    # Mock del broker que siempre falla
    mock_broker = MagicMock()
    mock_broker.store_users.side_effect = Exception("Network error")
    
    # ... configurar router con mock_broker ...
    
    # Leer JSON antes
    json_before = read_json(users_path)
    
    # Intentar actualizar (debería fallar)
    with pytest.raises(BusinessRuleError):
        router._store_users(users_path, users)
    
    # Verificar que JSON NO se modificó
    json_after = read_json(users_path)
    assert json_before == json_after, "JSON no debería haberse modificado"
```

---

### Test 2: Sincronización tras Login

**Archivo:** `src/apps/7_service_frontend/tests/test_login_otp_rotation_sync.py` (NUEVO)

```python
"""Test de rotación y sincronización de OTP tras login exitoso."""

def test_login_rotates_and_syncs_otp():
    """Verifica que login rota OTP y sincroniza en JSON y MariaDB."""
    
    # Crear usuario con OTP inicial
    user = create_test_user(otp="1234")
    
    # Simular login exitoso
    tokens = router.authenticate_user(
        user_name=user["user_name"],
        password="TestPass123!",
        otp="1234",
    )
    
    assert tokens is not None, "Login debería ser exitoso"
    
    # Verificar OTP rotado
    json_user = get_user_from_json(user["user_email"])
    db_user = get_user_from_mariadb(user["user_email"])
    
    # OTP debe haber cambiado
    assert json_user["user_otp"] != "1234", "OTP debería haber rotado en JSON"
    assert db_user["user_otp"] != "1234", "OTP debería haber rotado en MariaDB"
    
    # OTP debe ser el mismo en ambos lugares
    assert json_user["user_otp"] == db_user["user_otp"], "OTP desincronizado"
    
    # OTP debe ser numérico de 4 dígitos
    new_otp = json_user["user_otp"]
    assert len(new_otp) == 4, "OTP debe tener 4 dígitos"
    assert new_otp.isdigit(), "OTP debe ser numérico"
```

---

### Test 3: Creación de Usuario Sincroniza

**Archivo:** `src/2_shared_application/tests/test_create_user_sync.py` (NUEVO)

```python
"""Test de sincronización al crear usuario."""

def test_create_user_syncs_to_mariadb():
    """Verifica que create_user sincroniza inmediatamente con MariaDB."""
    
    # Configurar storage_mode
    monkeypatch.setenv("STORAGE_MODE", "mock_and_db")
    
    # Crear usuario
    user_data = {
        "user_name": "testuser",
        "user_password": "encrypted_password",
        "user_email": "test@example.com",
        "user_mobile": "+1234567890",
        "user_otp": "5678",
        "organization_id": 1,
        "identity_type_id": 1,
    }
    
    result = create_user(user_data)
    assert result is True, "Creación debería ser exitosa"
    
    # Verificar en JSON
    json_users = load_users_from_json()
    json_user = next((u for u in json_users if u["user_email"] == "test@example.com"), None)
    assert json_user is not None, "Usuario debe estar en JSON"
    assert json_user["user_otp"] == "5678", "OTP incorrecto en JSON"
    
    # Verificar en MariaDB
    db_users = load_users_from_mariadb()
    db_user = next((u for u in db_users if u["user_email"] == "test@example.com"), None)
    assert db_user is not None, "Usuario debe estar en MariaDB"
    assert db_user["user_otp"] == "5678", "OTP incorrecto en MariaDB"
```

---

## 📋 Checklist de Implementación

### Antes de Empezar

- [ ] Backup de `users.json` en todos los entornos
- [ ] Backup de tabla `users` en MariaDB
- [ ] Crear rama de desarrollo: `fix/otp-sync-issue`
- [ ] Leer análisis completo: `docs/OTP_SYNC_ISSUE_ANALYSIS.md`

### Implementación

- [ ] Aplicar CAMBIO 1: Retry en middleware (4 archivos)
- [ ] Aplicar CAMBIO 2: Mejorar validación `_sync_users_to_broker`
- [ ] Aplicar CAMBIO 3: Sincronización en `create_user`
- [ ] Aplicar CAMBIO 4: Mejorar `update_password_and_otp`
- [ ] Agregar imports necesarios (`time`, `datetime`)

### Testing

- [ ] Ejecutar tests existentes: `./full_test.sh`
- [ ] Crear Test 1: Timeout con retry
- [ ] Crear Test 2: Login rota y sincroniza OTP
- [ ] Crear Test 3: Creación sincroniza inmediatamente
- [ ] Ejecutar tests nuevos
- [ ] Test manual: Login, cambio de contraseña, creación de usuario
- [ ] Verificar logs: No debe haber "DESALINEADO"

### Verificación en Producción (Post-Deploy)

- [ ] Monitorear `frontend_secure.log` por 48 horas
- [ ] Ejecutar `grep "DESALINEADO" logs/frontend_secure.log`
- [ ] Si hay desincronizaciones, ejecutar sincronización manual
- [ ] Verificar performance: Login no debe tomar > 3 segundos

---

## 🚨 Riesgos y Mitigaciones

### Riesgo 1: Retry hace Login más Lento

**Mitigación:**
- Timeout de cada intento: 3 segundos (ajustable)
- Máximo 3 intentos: Máximo 7 segundos en peor caso
- En la práctica, el 99% de los intentos tendrán éxito en primer intento

### Riesgo 2: Inconsistencia Durante Retry

**Mitigación:**
- La lista `users` solo existe en memoria durante la operación
- No hay concurrencia dentro de la misma petición HTTP
- Si hay múltiples peticiones concurrentes, el último que escribe gana

### Riesgo 3: Introducir Bugs Nuevos

**Mitigación:**
- Tests exhaustivos antes de desplegar
- Desplegar primero en DEV
- Monitoreo intensivo en PRE
- Rollback plan documentado

---

## 📊 Impacto de los Cambios

### Archivos Modificados: 3

1. `src/apps/7_service_frontend/routermiddleware.py` - Función `_store_users`
2. `src/1_shared_domain/entities/user.py` - Funciones `update_password_and_otp`, `create_user`, `_sync_users_to_broker`
3. `src/apps/8_service_backend/apibe.py` - Endpoint `store_users` (opcional)

### Tests Nuevos: 3

1. `test_otp_sync_timeout.py`
2. `test_login_otp_rotation_sync.py`
3. `test_create_user_sync.py`

### Líneas de Código Añadidas: ~200

- Retry logic: ~50 líneas
- Validación mejorada: ~30 líneas
- Logging adicional: ~40 líneas
- Tests: ~80 líneas

---

## ⏱️ Plan de Despliegue

### Paso 1: Desarrollo y Testing (4h)

```bash
# Crear rama
git checkout -b fix/otp-sync-issue

# Aplicar cambios
# ... editar archivos ...

# Ejecutar tests
./full_test.sh

# Tests específicos
pytest src/apps/7_service_frontend/tests/test_otp_sync_timeout.py -v
pytest src/apps/7_service_frontend/tests/test_login_otp_rotation_sync.py -v
pytest src/2_shared_application/tests/test_create_user_sync.py -v
```

### Paso 2: Deploy en DEV (30min)

```bash
# Merge a dev
git checkout dev
git merge fix/otp-sync-issue

# Deploy
# ... despliegue según proceso ...

# Monitorear logs
tail -f src/apps/5_web_frontend/logs/frontend_secure.log
```

### Paso 3: Validación en DEV (24h)

```bash
# Test manual
# 1. Login de usuario
# 2. Cambiar contraseña
# 3. Crear nuevo usuario

# Verificar sincronización
grep "DESALINEADO" src/apps/5_web_frontend/logs/frontend_secure.log
# No debe haber resultados

# Verificar que no hay errores de retry
grep "Fallo al sincronizar" src/apps/7_service_frontend/logs/middleware_activiy.log
```

### Paso 4: Deploy en PRE (1h)

Solo si DEV estuvo estable por 24h.

### Paso 5: Deploy en PRO (2h)

Solo si PRE estuvo estable por 1 semana.

---

## 🔍 Verificación Post-Deploy

### Script de Verificación Inmediata

```bash
#!/bin/bash
# scripts/verify_otp_sync.sh

echo "=== Verificación de Sincronización OTP ==="

# 1. Verificar que no hay desincronizaciones en logs
DESYNC_COUNT=$(grep -c "DESALINEADO" src/apps/5_web_frontend/logs/frontend_secure.log 2>/dev/null || echo "0")
echo "Desincronizaciones detectadas: $DESYNC_COUNT"

if [ "$DESYNC_COUNT" -gt "0" ]; then
    echo "⚠️  ALERTA: Se detectaron desincronizaciones"
    grep "DESALINEADO" src/apps/5_web_frontend/logs/frontend_secure.log | tail -10
else
    echo "✅ No se detectaron desincronizaciones"
fi

# 2. Verificar reintentos de sincronización
RETRY_COUNT=$(grep -c "Reintentando" src/apps/7_service_frontend/logs/middleware_activiy.log 2>/dev/null || echo "0")
echo "Reintentos de sincronización: $RETRY_COUNT"

# 3. Verificar fallos totales de sincronización
FAIL_COUNT=$(grep -c "No se pudo guardar usuarios en broker tras" src/apps/7_service_frontend/logs/middleware_activiy.log 2>/dev/null || echo "0")
echo "Fallos totales de sincronización: $FAIL_COUNT"

if [ "$FAIL_COUNT" -gt "0" ]; then
    echo "🚨 CRÍTICO: Fallos totales de sincronización detectados"
    grep "No se pudo guardar usuarios en broker tras" src/apps/7_service_frontend/logs/middleware_activiy.log | tail -10
fi

echo ""
echo "=== Fin de Verificación ==="
```

### Verificación en Base de Datos

```sql
-- Verificar OTPs en MariaDB
USE myllm_core_db;

SELECT 
    u.user_id,
    u.user_name,
    u.user_email,
    u.user_otp,
    LENGTH(u.user_otp) as otp_length,
    u.active,
    u.blocked
FROM users u
WHERE LENGTH(u.user_otp) != 4  -- OTPs inválidos
   OR u.user_otp NOT REGEXP '^[0-9]{4}$';  -- OTPs no numéricos

-- Debería retornar 0 filas
```

---

## 📚 Referencias

- **Análisis del problema:** `docs/OTP_SYNC_ISSUE_ANALYSIS.md`
- **Código afectado:**
  - `src/apps/7_service_frontend/routermiddleware.py`
  - `src/1_shared_domain/entities/user.py`
  - `src/apps/3_backend/4_infrastructure/persistence/storage_adapter.py`
- **AGENTS.md:** Reglas de sincronización (líneas 76-91)
- **README.md:** Modos de almacenamiento (líneas 1264-1283)

---

**Preparado por:** @backend-conductor  
**Fecha:** 2026-01-26  
**Estado:** 📝 Listo para implementar  
**Próximo paso:** Aplicar cambios y ejecutar tests
