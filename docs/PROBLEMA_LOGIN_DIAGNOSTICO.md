# Diagnóstico: Problema de Login en Frontend

**Fecha**: 2026-02-04  
**Problema**: "No se pudo autenticar con el middleware"  
**Causa**: ❌ **Middleware (7_service_frontend) NO está corriendo**

---

## 🔍 DIAGNÓSTICO

### Error en Frontend:
```
2026-02-03 13:06:03 | WARNING  | frontend | LOGIN FAILED | user=adminone
No se pudo autenticar con el middleware
```

### Causa Raíz:
El middleware (puerto 8007) **NO está en ejecución**. El Frontend intenta conectarse a `http://localhost:8007/login` pero no hay respuesta.

### Verificación:
```bash
ps aux | grep -E "python.*7_service_frontend" | grep -v grep
# Resultado: Sin procesos (middleware no está corriendo)
```

---

## ✅ SOLUCIÓN: Arrancar los servicios en orden correcto

### Orden de arranque recomendado:

#### 1. **Middleware** (puerto 8007) - PRIMERO
```bash
cd /Users/administrator/develop/anewhope/src/apps/7_service_frontend
./run.sh
```

**Verificar que arranca**: Debe mostrar:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8007
```

---

#### 2. **Backend Core** (puerto 8003) - SEGUNDO (opcional para login básico)
```bash
cd /Users/administrator/develop/anewhope/src/apps/3_backend
./run.sh
```

---

#### 3. **Broker Backend** (puerto 8008) - TERCERO (opcional para login básico)
```bash
cd /Users/administrator/develop/anewhope/src/apps/8_service_backend
./run.sh
```

---

#### 4. **Frontend** (puerto 8005) - CUARTO
```bash
cd /Users/administrator/develop/anewhope/src/apps/5_web_frontend
./run.sh
```

---

#### 5. **Backoffice** (puerto 8006) - QUINTO (opcional)
```bash
cd /Users/administrator/develop/anewhope/src/apps/6_web_backoffice
./run.sh
```

---

## 📊 ARQUITECTURA DE DEPENDENCIAS

```
Frontend (8005)  ────┐
                     ├──> Middleware (8007) ──> Broker (8008) ──> Backend Core (8003)
Backoffice (8006) ───┘
```

**Reglas**:
1. **Middleware DEBE estar corriendo** para que Frontend/Backoffice funcionen
2. Sin Middleware, NO hay login, NO hay autenticación
3. El login básico solo necesita Middleware (modo `STORAGE_MODE=mock`)
4. Para persistencia completa, se necesita también Broker + Backend Core

---

## 🔧 ANTES DE CONTINUAR: Corregir imports del explorador

Hay un error de imports en el componente explorador del Backoffice que debe corregirse antes de arrancar:

```
ImportError: attempted relative import beyond top-level package
File "components/explorador.py", line 23
from ..adapters.api_client import (
```

### Fix necesario:

**Archivo**: `src/apps/6_web_backoffice/components/explorador.py`  
**Línea 23**:

**ANTES (❌)**:
```python
from ..adapters.api_client import (
```

**DESPUÉS (✅)**:
```python
from adapters.api_client import (
```

---

## 🎯 PLAN DE ACCIÓN INMEDIATA

### PASO 1: Corregir imports del explorador (Backoffice y Frontend)
```bash
# Se debe cambiar en ambos archivos:
# - src/apps/5_web_frontend/components/explorador.py (línea 20)
# - src/apps/6_web_backoffice/components/explorador.py (línea 23)
```

### PASO 2: Arrancar Middleware
```bash
cd /Users/administrator/develop/anewhope/src/apps/7_service_frontend
./run.sh
```

### PASO 3: Arrancar Frontend
```bash
cd /Users/administrator/develop/anewhope/src/apps/5_web_frontend
./run.sh
```

### PASO 4: Probar login
```
Usuario: adminone
Password: PassOne1
OTP: (solicitar OTP desde la web)
```

---

## 📝 PRÓXIMOS PASOS DESPUÉS DEL FIX

Una vez que el login funcione:

1. ✅ Crear tablas `version_states` y `version_events` en MariaDB
2. ✅ Insertar versiones v001 para proyectos existentes
3. ✅ Llamar a fmanagement para crear estructuras físicas de carpetas
4. ✅ Probar el explorador de archivos con datos reales

---

## 🚨 RESUMEN EJECUTIVO

**Problema**: Middleware NO está corriendo  
**Solución**: Arrancar middleware ANTES que frontend  
**Bloqueante adicional**: Imports incorrectos en explorador.py  

**Acción inmediata**:
1. Corregir imports en explorador.py (ambos)
2. Arrancar middleware (./run.sh)
3. Arrancar frontend (./run.sh)

---

**ESTADO**: ⏸️ **Bloqueado - requiere arrancar middleware**
