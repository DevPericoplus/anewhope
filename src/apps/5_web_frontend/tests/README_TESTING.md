# Guía de Testing para Web Frontend

## Tests de Solicitud de OTP

### Tests Específicos para Usuario adminone

Se han creado tests automatizados que simulan el flujo completo de solicitud de código OTP para el usuario `adminone`.

#### Tests Disponibles

1. **`test_request_otp_for_adminone_user`**
   - Simula el flujo exitoso de solicitud de OTP
   - Verifica que se envía el SMS con el código correcto
   - Usuario: `adminone@myllm.ai`
   - Teléfono: `+34639775978`
   - OTP esperado: `8379`

2. **`test_request_otp_adminone_sms_delivery_failure`**
   - Simula fallo en el envío de SMS
   - Verifica el manejo correcto de errores

### Cómo Ejecutar los Tests

#### Ejecutar test específico de adminone

```bash
cd ~/develop/anewhope

# Activar entorno virtual (si no está activado)
source .venv_frontend313/bin/activate

# Ejecutar test de solicitud OTP exitosa
python -m pytest src/apps/5_web_frontend/tests/test_change_password.py::test_request_otp_for_adminone_user -v

# Ejecutar test de fallo de SMS
python -m pytest src/apps/5_web_frontend/tests/test_change_password.py::test_request_otp_adminone_sms_delivery_failure -v
```

#### Ejecutar todos los tests de change_password

```bash
python -m pytest src/apps/5_web_frontend/tests/test_change_password.py -v
```

#### Ejecutar todos los tests del frontend

```bash
python -m pytest src/apps/5_web_frontend/tests/ -v
```

### Qué Verifica el Test de adminone

El test `test_request_otp_for_adminone_user` simula exactamente lo que harías manualmente:

1. ✅ Ingresa el email `adminone@myllm.ai` en el formulario
2. ✅ Hace clic en el botón "Solicitar código OTP"
3. ✅ Verifica que:
   - Se busca el usuario por email
   - Se obtiene el OTP del usuario (8379)
   - Se obtiene el teléfono del usuario (+34639775978)
   - Se llama a `send_message_by_sms(otp="8379", phone="+34639775978")`
   - La interfaz avanza al paso 2
   - Se muestra mensaje de éxito

### Cuándo Ejecutar Estos Tests

**Ejecuta estos tests regularmente para verificar:**

- ✅ Después de cambios en `pages/change_password.py`
- ✅ Después de cambios en `common_security.py` (función SMS)
- ✅ Después de cambios en `api_client.py`
- ✅ Antes de hacer deploy a producción
- ✅ Si sospechas que la funcionalidad de OTP dejó de funcionar

### Interpretación de Resultados

#### ✅ Test PASSED
```
test_request_otp_for_adminone_user PASSED
✅ Test exitoso: La funcionalidad de solicitud de OTP funciona correctamente para adminone
```
**Significado**: El código de la aplicación funciona correctamente. Si los SMS no llegan en producción, el problema está en:
- Configuración de Infobip (sender ID, créditos, etc.)
- Credenciales API incorrectas
- Problemas de red/firewall

#### ❌ Test FAILED
```
test_request_otp_for_adminone_user FAILED
AssertionError: El OTP enviado debe ser 8379, pero se envió XXXX
```
**Significado**: Hay un bug en el código de la aplicación. Revisa:
- `pages/change_password.py::request_otp()`
- `api_client.py::get_user_by_email()`
- `common_security.py::send_message_by_sms()`

### Diagnóstico de Problemas SMS

Si el test **pasa** pero los SMS **no llegan** en la aplicación real:

1. **Verificar logs de frontend**:
   ```bash
   tail -50 src/apps/5_web_frontend/logs/frontend_secure.log | grep SMS
   ```

2. **Buscar errores específicos**:
   - `Error:requests module not installed` → Instalar requests en venv
   - `Status:PENDING_ACCEPTED` → El problema está en Infobip, no en el código
   - `Error:Número de teléfono inválido` → Verificar formato del número
   - `Error:OTP inválido` → Verificar que el OTP tiene 4 dígitos

3. **Verificar credenciales de Infobip**:
   ```bash
   grep -E "sms_api_url|sms_api_key|sms_sender_id" infrastructure/environments/macbook/protected_values.py
   ```

4. **Probar llamada directa a Infobip**:
   ```bash
   # Desde el venv del frontend
   python -c "
   from src.2_shared_application.security.common_security import send_message_by_sms
   result = send_message_by_sms('1234', '+34639775978')
   print(f'Resultado: {result}')
   "
   ```

### Problema Actual Conocido (2026-02-02)

**Síntoma**: La aplicación muestra "Código OTP enviado por SMS" pero los SMS no llegan.

**Causa**: Infobip acepta los mensajes (`PENDING_ACCEPTED`) pero no los entrega. Esto NO es un problema del código.

**Solución**: Verificar en el portal de Infobip:
- Saldo de créditos SMS
- Estado del Sender ID "getmylllm.com" (debe estar aprobado)
- Número de destino verificado (si es cuenta trial)
- Logs de entrega de mensajes

### Contacto Infobip

Portal: https://portal.infobip.com/
Soporte: https://www.infobip.com/support

---

**Última actualización**: 2026-02-02
**Versión**: 1.0
