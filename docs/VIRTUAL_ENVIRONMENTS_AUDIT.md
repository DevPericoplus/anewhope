# 🔍 Auditoría de Entornos Virtuales por Aplicación

**Fecha:** 2026-01-26  
**Estado:** ⚠️ **ERROR CRÍTICO ENCONTRADO**  
**Tarea:** Verificar que cada aplicación usa su propio entorno virtual dedicado  

---

## 📊 Resumen Ejecutivo

| Aplicación | Entorno Virtual | Estado | Problema |
|------------|-----------------|--------|----------|
| **3_backend** | `.venv_backend313` | ✅ Correcto | Ninguno |
| **4_trainer** | (pendiente implementación) | ⚠️ No aplicable | Servicio no implementado |
| **5_web_frontend** | `.venv_frontend313` | ✅ Correcto | Ninguno |
| **6_web_backoffice** | `.venv_backoffice313` | ❌ **ERROR CRÍTICO** | **entrypoint.sh apunta al frontend** |
| **7_service_frontend** | `.venv_middleware313` | ✅ Correcto | Ninguno |
| **8_service_backend** | `.venv_broker313` | ✅ Correcto | Ninguno |

**Total de entornos virtuales:** 5 dedicados (todos diferentes)  
**Compartición de entornos:** ✅ Ninguna (cada app tiene el suyo)  
**Errores encontrados:** ❌ 1 error crítico en backoffice  

---

## 🚨 ERROR CRÍTICO IDENTIFICADO

### **Aplicación:** 6_web_backoffice

**Archivo:** `src/apps/6_web_backoffice/entrypoint.sh`

**Problema:**
```bash
# LÍNEA 8 - ERROR
cd "$ROOT_DIR/src/apps/5_web_frontend"  # ← ¡Apunta al FRONTEND!
```

**Consecuencia:**
- El backoffice en contenedor Docker ejecuta el código del **frontend**
- Esto causa que ambas aplicaciones (frontend y backoffice) ejecuten la misma app
- Pérdida de funcionalidad específica del backoffice

**Solución:**
```bash
# CORRECCIÓN
cd "$ROOT_DIR/src/apps/6_web_backoffice"  # ← Debe apuntar al BACKOFFICE
```

---

## 📋 Análisis Detallado por Aplicación

### **1. Backend Core (3_backend)**

**Puerto:** 8003  
**Entorno Virtual:** `.venv_backend313`  
**Estado:** ✅ **CORRECTO**

#### **run.sh (Ejecución Local)**
```bash
#!/bin/bash
# Script para activar el entorno virtual y ejecutar el backend core

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

# Activar el entorno virtual del backend (Python 3.13)
source "$ROOT_DIR/.venv_backend313/bin/activate"  # ✅ Dedicado

export PYTHONPATH="$ROOT_DIR"
python -m src.apps.3_backend.main
```

**Análisis:**
- ✅ Usa su propio entorno virtual `.venv_backend313`
- ✅ No comparte con otras aplicaciones
- ✅ PYTHONPATH correctamente configurado

#### **entrypoint.sh (Ejecución Docker)**
```bash
#!/bin/bash
# Entrypoint para ejecutar el backend core en contenedor

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export PYTHONPATH="$ROOT_DIR"
python -m src.apps.3_backend.main  # ✅ Correcto
```

**Análisis:**
- ✅ Usa el Python del contenedor (dependencias instaladas en la imagen)
- ✅ No necesita activar venv (ya está en el contenedor)
- ✅ Ejecuta el módulo correcto

---

### **2. Trainer (4_trainer)**

**Puerto:** No definido  
**Entorno Virtual:** Pendiente  
**Estado:** ⚠️ **NO IMPLEMENTADO**

#### **entrypoint.sh (Ejecución Docker)**
```bash
#!/bin/bash
# Entrypoint para ejecutar el trainer (pendiente de implementación)

set -e

echo "Servicio trainer pendiente de implementación"
sleep infinity
```

**Análisis:**
- ⚠️ Servicio no implementado
- ⚠️ No tiene run.sh para ejecución local
- ⚠️ Requiere implementación completa

---

### **3. Frontend (5_web_frontend)**

**Puerto:** 8005  
**Entorno Virtual:** `.venv_frontend313`  
**Estado:** ✅ **CORRECTO**

#### **run.sh (Ejecución Local)**
```bash
#!/bin/bash
# Script para activar el entorno virtual y ejecutar la aplicación Reflex

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

# Activar el entorno virtual del frontend (Python 3.13)
source "$ROOT_DIR/.venv_frontend313/bin/activate"  # ✅ Dedicado

# Ejecutar la aplicación Reflex desde la ruta actual
export PYTHONPATH="$ROOT_DIR"
reflex run
```

**Análisis:**
- ✅ Usa su propio entorno virtual `.venv_frontend313`
- ✅ No comparte con otras aplicaciones
- ✅ Ejecuta desde la carpeta correcta

#### **entrypoint.sh (Ejecución Docker)**
```bash
#!/bin/bash
# Entrypoint para ejecutar el frontend en contenedor

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export PYTHONPATH="$ROOT_DIR"
cd "$ROOT_DIR/src/apps/5_web_frontend"  # ✅ Correcto
reflex run
```

**Análisis:**
- ✅ Cambia al directorio correcto (5_web_frontend)
- ✅ Ejecuta reflex desde el directorio correcto
- ✅ No hay problemas

---

### **4. Backoffice (6_web_backoffice)**

**Puerto:** 8006  
**Entorno Virtual:** `.venv_backoffice313`  
**Estado:** ❌ **ERROR CRÍTICO EN ENTRYPOINT**

#### **run.sh (Ejecución Local)**
```bash
#!/bin/bash
# Script para activar el entorno virtual y ejecutar la aplicación Reflex

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

# Activar el entorno virtual del frontend (Python 3.13)
source "$ROOT_DIR/.venv_backoffice313/bin/activate"  # ✅ Dedicado

# Ejecutar la aplicación Reflex desde la ruta actual
export PYTHONPATH="$ROOT_DIR"
reflex run
```

**Análisis:**
- ✅ Usa su propio entorno virtual `.venv_backoffice313`
- ✅ No comparte con otras aplicaciones
- ✅ Ejecuta desde la carpeta correcta

#### **entrypoint.sh (Ejecución Docker)** ❌ **ERROR CRÍTICO**

```bash
#!/bin/bash
# Entrypoint para ejecutar el frontend en contenedor

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export PYTHONPATH="$ROOT_DIR"
cd "$ROOT_DIR/src/apps/5_web_frontend"  # ❌ ERROR: Debería ser 6_web_backoffice
reflex run
```

**Análisis:**
- ❌ **LÍNEA 8:** Cambia al directorio del **FRONTEND** en lugar del **BACKOFFICE**
- ❌ **CONSECUENCIA:** El backoffice en Docker ejecuta el código del frontend
- ❌ **IMPACTO:** El backoffice no funciona correctamente en contenedores

**Corrección Necesaria:**
```bash
cd "$ROOT_DIR/src/apps/6_web_backoffice"  # ← Corrección
```

---

### **5. Middleware (7_service_frontend)**

**Puerto:** 8007  
**Entorno Virtual:** `.venv_middleware313`  
**Estado:** ✅ **CORRECTO**

#### **run.sh (Ejecución Local)**
```bash
#!/bin/bash
# Script para activar el entorno virtual y ejecutar el middleware

# Activar el entorno virtual del middleware (Python 3.13)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
source "$ROOT_DIR/.venv_middleware313/bin/activate"  # ✅ Dedicado

# Ejecutar el middleware desde la ruta actual
export PYTHONPATH="$ROOT_DIR"
python -m src.apps.7_service_frontend.main
```

**Análisis:**
- ✅ Usa su propio entorno virtual `.venv_middleware313`
- ✅ No comparte con otras aplicaciones
- ✅ PYTHONPATH correctamente configurado

#### **entrypoint.sh (Ejecución Docker)**
```bash
#!/bin/bash
# Entrypoint para ejecutar el middleware en contenedor

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export PYTHONPATH="$ROOT_DIR"
python -m src.apps.7_service_frontend.main  # ✅ Correcto
```

**Análisis:**
- ✅ Ejecuta el módulo correcto
- ✅ No hay problemas

---

### **6. Broker Backend (8_service_backend)**

**Puerto:** 8008  
**Entorno Virtual:** `.venv_broker313`  
**Estado:** ✅ **CORRECTO**

#### **run.sh (Ejecución Local)**
```bash
#!/bin/bash
# Script para activar el entorno virtual y ejecutar el broker backend

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

# Activar el entorno virtual del broker (Python 3.13)
source "$ROOT_DIR/.venv_broker313/bin/activate"  # ✅ Dedicado

export PYTHONPATH="$ROOT_DIR"
python -m src.apps.8_service_backend.main
```

**Análisis:**
- ✅ Usa su propio entorno virtual `.venv_broker313`
- ✅ No comparte con otras aplicaciones
- ✅ PYTHONPATH correctamente configurado

#### **entrypoint.sh (Ejecución Docker)**
```bash
#!/bin/bash
# Entrypoint para ejecutar el broker backend en contenedor

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export PYTHONPATH="$ROOT_DIR"
python -m src.apps.8_service_backend.main  # ✅ Correcto
```

**Análisis:**
- ✅ Ejecuta el módulo correcto
- ✅ No hay problemas

---

## 📊 Matriz de Entornos Virtuales

### **Entornos Virtuales Dedicados**

| Entorno Virtual | Aplicación | Puerto | Compartido | Estado |
|-----------------|------------|--------|------------|--------|
| `.venv_backend313` | 3_backend | 8003 | ❌ No | ✅ Correcto |
| `.venv_frontend313` | 5_web_frontend | 8005 | ❌ No | ✅ Correcto |
| `.venv_backoffice313` | 6_web_backoffice | 8006 | ❌ No | ✅ Correcto |
| `.venv_middleware313` | 7_service_frontend | 8007 | ❌ No | ✅ Correcto |
| `.venv_broker313` | 8_service_backend | 8008 | ❌ No | ✅ Correcto |

**Total:** 5 entornos virtuales dedicados  
**Compartición:** ✅ **NINGUNA** (cada aplicación tiene el suyo propio)  

---

## ✅ Conclusiones

### **Aspectos Correctos:**

1. ✅ **Aislamiento de Entornos:**
   - Cada aplicación tiene su propio entorno virtual dedicado
   - No hay compartición de entornos entre aplicaciones
   - Nomenclatura clara y consistente (`.venv_<app>313`)

2. ✅ **Scripts run.sh (Ejecución Local):**
   - Todos los scripts activan correctamente su propio entorno virtual
   - PYTHONPATH configurado correctamente
   - Cada script ejecuta su propia aplicación

3. ✅ **Scripts entrypoint.sh (Ejecución Docker):**
   - 5 de 6 scripts están correctos
   - Ejecutan los módulos Python correctos
   - PYTHONPATH configurado correctamente

---

### **Problemas Identificados:**

#### **1. ERROR CRÍTICO: Backoffice entrypoint.sh**

**Archivo:** `src/apps/6_web_backoffice/entrypoint.sh`  
**Línea:** 8  
**Error:** Apunta al directorio del frontend en lugar del backoffice

**Impacto:**
- ❌ El backoffice en Docker ejecuta el código del frontend
- ❌ Funcionalidad específica del backoffice no disponible
- ❌ Confusión en deployment y debugging

**Prioridad:** 🔴 CRÍTICA - Debe corregirse inmediatamente

---

#### **2. WARNING: Trainer no implementado**

**Aplicación:** 4_trainer  
**Estado:** Pendiente de implementación  
**Prioridad:** 🟡 BAJA - No afecta al sistema actual

---

## 🔧 Correcciones Necesarias

### **Corrección 1: Backoffice entrypoint.sh** (CRÍTICA)

**Archivo a modificar:** `src/apps/6_web_backoffice/entrypoint.sh`

**Cambio:**
```bash
# ANTES (LÍNEA 8)
cd "$ROOT_DIR/src/apps/5_web_frontend"

# DESPUÉS (CORRECCIÓN)
cd "$ROOT_DIR/src/apps/6_web_backoffice"
```

**Archivo completo corregido:**
```bash
#!/bin/bash
# Entrypoint para ejecutar el backoffice en contenedor

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export PYTHONPATH="$ROOT_DIR"
cd "$ROOT_DIR/src/apps/6_web_backoffice"  # ← CORREGIDO
reflex run
```

---

### **Corrección 2: Comentario en run.sh del backoffice** (MENOR)

**Archivo a modificar:** `src/apps/6_web_backoffice/run.sh`

**Cambio:**
```bash
# ANTES (LÍNEA 8)
# Activar el entorno virtual del frontend (Python 3.13)

# DESPUÉS (CORRECCIÓN)
# Activar el entorno virtual del backoffice (Python 3.13)
```

---

## 🧪 Verificación Post-Corrección

### **Test 1: Verificar Entornos Virtuales**

```bash
# Verificar que cada entorno virtual existe
ls -la .venv_backend313/
ls -la .venv_frontend313/
ls -la .venv_backoffice313/
ls -la .venv_middleware313/
ls -la .venv_broker313/
```

**Resultado esperado:** 5 directorios diferentes

---

### **Test 2: Verificar Scripts run.sh**

```bash
# Verificar que cada script activa su propio venv
grep "source.*venv" src/apps/*/run.sh

# Resultado esperado:
# 3_backend/run.sh:    source "$ROOT_DIR/.venv_backend313/bin/activate"
# 5_web_frontend/run.sh:    source "$ROOT_DIR/.venv_frontend313/bin/activate"
# 6_web_backoffice/run.sh:    source "$ROOT_DIR/.venv_backoffice313/bin/activate"
# 7_service_frontend/run.sh:    source "$ROOT_DIR/.venv_middleware313/bin/activate"
# 8_service_backend/run.sh:    source "$ROOT_DIR/.venv_broker313/bin/activate"
```

---

### **Test 3: Verificar Directorios en entrypoint.sh**

```bash
# Verificar directorios de ejecución en Docker
grep "cd.*apps" src/apps/*/entrypoint.sh

# Resultado esperado (después de corrección):
# 5_web_frontend/entrypoint.sh:    cd "$ROOT_DIR/src/apps/5_web_frontend"
# 6_web_backoffice/entrypoint.sh:    cd "$ROOT_DIR/src/apps/6_web_backoffice"  ← CORREGIDO
```

---

### **Test 4: Probar Backoffice en Docker**

```bash
# Después de la corrección, probar el backoffice en Docker
cd infrastructure/servers/backoffice
docker-compose up -d

# Verificar logs
docker-compose logs -f backoffice

# Acceder
curl http://localhost:8006
```

**Resultado esperado:** 
- ✅ Backoffice se ejecuta correctamente
- ✅ No ejecuta el código del frontend
- ✅ Interfaz de backoffice visible

---

## 📚 Recomendaciones

### **1. Nomenclatura Consistente**

✅ **Actual (Correcto):**
- `.venv_backend313`
- `.venv_frontend313`
- `.venv_backoffice313`
- `.venv_middleware313`
- `.venv_broker313`

**Mantener:** Esta nomenclatura es clara y consistente.

---

### **2. Documentación de Entornos**

Crear un archivo `ENVIRONMENTS.md` en la raíz con:
- Lista de todos los entornos virtuales
- Aplicación asociada a cada entorno
- Versión de Python requerida
- Dependencias principales

---

### **3. Script de Verificación**

Crear un script `scripts/verify_environments.sh` que:
- Verifique que todos los entornos virtuales existen
- Verifique que no hay compartición
- Valide que los scripts apuntan a los directorios correctos

---

### **4. CI/CD**

Agregar verificación en CI/CD para:
- Validar que los entornos virtuales están configurados correctamente
- Verificar que los entrypoint.sh apuntan a los directorios correctos
- Alertar si se detecta compartición de entornos

---

## ✅ Checklist de Implementación

- [ ] Corregir `src/apps/6_web_backoffice/entrypoint.sh` (línea 8)
- [ ] Corregir comentario en `src/apps/6_web_backoffice/run.sh` (línea 8)
- [ ] Verificar que todos los entornos virtuales existen
- [ ] Probar backoffice en Docker después de la corrección
- [ ] Crear script de verificación automática
- [ ] Actualizar documentación de deployment
- [ ] Agregar verificación en CI/CD

---

## 📊 Estado Final Esperado

Después de las correcciones:

| Aplicación | Entorno Virtual | Estado |
|------------|-----------------|--------|
| 3_backend | `.venv_backend313` | ✅ Correcto |
| 4_trainer | (pendiente) | ⚠️ No implementado |
| 5_web_frontend | `.venv_frontend313` | ✅ Correcto |
| 6_web_backoffice | `.venv_backoffice313` | ✅ **CORREGIDO** |
| 7_service_frontend | `.venv_middleware313` | ✅ Correcto |
| 8_service_backend | `.venv_broker313` | ✅ Correcto |

**Compartición de entornos:** ✅ NINGUNA  
**Errores:** ✅ TODOS CORREGIDOS  

---

**Auditoría realizada por:** @backend-conductor  
**Fecha:** 2026-01-26  
**Archivos revisados:** 11 archivos (5 run.sh + 6 entrypoint.sh)  
**Errores encontrados:** 1 crítico + 1 menor  
**Estado:** ⚠️ Requiere corrección inmediata del backoffice
