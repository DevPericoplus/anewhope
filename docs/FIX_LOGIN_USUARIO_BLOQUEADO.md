# Fix: Usuario adminone bloqueado

**Fecha**: 2026-02-04  
**Problema**: Login falla con "El usuario no está habilitado"  
**Causa**: Usuario `adminone` tiene `"blocked": true`  
**Fix aplicado**: ✅ Cambiado a `"blocked": false`

---

## 🔍 DIAGNÓSTICO

### Error del middleware:
```json
{"detail":"El usuario no está habilitado"}
```

### Causa raíz:
```json
{
  "user_name": "adminone",
  "active": true,
  "blocked": true,  ← PROBLEMA
}
```

---

## ✅ FIX APLICADO (PASO 7.50)

### Archivo modificado:
`src/2_shared_application/moks/users.json`

### Cambio:
```json
// ANTES:
"blocked": true,

// DESPUÉS:
"blocked": false,
```

---

## ⚠️ MIDDLEWARE NECESITA REINICIO

El middleware cachea los datos de usuarios. **Debe reiniciarse** para cargar los cambios:

```bash
# 1. Detener middleware (Ctrl+C en su terminal)
# 2. Arrancar middleware de nuevo:
cd /Users/administrator/develop/anewhope/src/apps/7_service_frontend
./run.sh
```

---

## 🧪 PRUEBA DESPUÉS DEL REINICIO

```bash
curl -X POST http://localhost:8007/login \
  -H "Content-Type: application/json" \
  -H "X-Client-App: frontend" \
  -d '{"user_name":"adminone","password":"PassOne1","otp":"9893"}'
```

**Resultado esperado**:
```json
{
  "access_token": "eyJ...",
  "session_token": "eyJ...",
  "user_id": 1,
  "user_name": "adminone",
  "organization_id": 1,
  "identity_type_id": 1
}
```

---

## 📝 CREDENCIALES DEL USUARIO

```
Usuario: adminone
Password: PassOne1
OTP actual: 9893
```

---

## 🎯 PRÓXIMOS PASOS

1. ✅ Usuario desbloqueado en `users.json`
2. ⏭️ Reiniciar middleware
3. ⏭️ Probar login desde el Frontend (http://localhost:8005)
4. ⏭️ Si login funciona → Crear datos iniciales para explorador

---

**ESTADO**: ✅ **Fix aplicado - Requiere reinicio del middleware**
