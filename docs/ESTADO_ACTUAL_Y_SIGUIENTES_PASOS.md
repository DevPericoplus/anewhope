# Estado Actual y Siguientes Pasos

**Fecha**: 2026-02-04  
**Hora**: Actualizado con diagnóstico completo  

---

## ✅ LO QUE SE HA HECHO

### Fix de Imports (Commits: `47309f6`, `4cdd8b8`)
1. ✅ Corregidos imports de `SharedSessionState` en ambos explorador.py
2. ✅ Imports de `api_client` ya están correctos (absolutos, no relativos)
3. ✅ Working tree limpio
4. ✅ Código commiteado

### Integración del Explorador (100% completo)
1. ✅ Componente explorador implementado en Frontend y Backoffice
2. ✅ Integrado en página Proyecciones
3. ✅ Botón "Crear nueva versión" implementado con atomicidad
4. ✅ Documentación completa (15 archivos)

---

## 🔍 DIAGNÓSTICO DEL PROBLEMA DE LOGIN

### Problema Reportado:
```
2026-02-03 13:06:03 | WARNING | frontend | LOGIN FAILED | user=adminone
No se pudo autenticar con el middleware
```

### Causa Raíz: ❌ **MIDDLEWARE NO ESTÁ CORRIENDO**

```bash
# Verificación:
ps aux | grep -E "python.*7_service_frontend" | grep -v grep
# Resultado: Sin procesos
```

El Frontend intenta conectarse a `http://localhost:8007/login` pero no hay respuesta porque el middleware (puerto 8007) **NO está ejecutándose**.

---

## ⚠️ ERROR ADICIONAL: ImportError en Backoffice

Al intentar arrancar el Backoffice, aparece:

```
ImportError: attempted relative import beyond top-level package
File "components/explorador.py", line 23
```

**Estado actual de los imports**:
- ✅ Frontend: `from adapters.api_client import` (CORRECTO)
- ✅ Backoffice: `from adapters.api_client import` (CORRECTO)

**Sin embargo**, Reflex puede estar teniendo problemas al resolver estos imports. Necesitamos verificar que los imports funcionen cuando Reflex ejecuta la app.

---

## 🎯 PLAN DE ACCIÓN COMPLETO

### FASE 1: Arrancar servicios en orden correcto

#### PASO 1: Arrancar Middleware (CRÍTICO)
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

#### PASO 2: Arrancar Backend Core (opcional para login básico)
```bash
# En otra terminal:
cd /Users/administrator/develop/anewhope/src/apps/3_backend
./run.sh
```

---

#### PASO 3: Arrancar Broker Backend (opcional para login básico)
```bash
# En otra terminal:
cd /Users/administrator/develop/anewhope/src/apps/8_service_backend
./run.sh
```

---

#### PASO 4: Arrancar Frontend
```bash
# En otra terminal:
cd /Users/administrator/develop/anewhope/src/apps/5_web_frontend
./run.sh
```

**Esperado**:
- ✅ Compila sin `SyntaxError`
- ✅ Arranca en http://localhost:8005
- ❓ Verificar si el import de `adapters.api_client` funciona

---

#### PASO 5: Probar login en Frontend
```
URL: http://localhost:8005
Usuario: adminone
Password: PassOne1
OTP: (solicitar desde la web)
```

**Resultado esperado**:
- ✅ Si middleware está corriendo: Login exitoso
- ❌ Si middleware NO está corriendo: "No se pudo autenticar con el middleware"

---

### FASE 2: Si hay ImportError en explorador.py

Si al arrancar Frontend o Backoffice aparece:
```
ImportError: No module named 'adapters'
```

**Solución**: Necesitamos verificar la estructura de imports de Reflex. Posibles fixes:

**Opción A**: Cambiar a import absoluto completo
```python
# En explorador.py
from web_frontend.adapters.api_client import (  # Frontend
from web_backoffice.adapters.api_client import (  # Backoffice
```

**Opción B**: Añadir `adapters` al sys.path en rxconfig.py

**Opción C**: Mover las funciones de api_client a un módulo compartido

---

### FASE 3: Crear datos iniciales para el explorador

Una vez que el login funcione y las apps arranquen sin errores:

#### PASO 1: Crear tablas en MariaDB
```bash
cd /Users/administrator/develop/anewhope
mysql -u myllm_writer -p myllm_projects_db < infrastructure/database/ddl_version_states.sql
mysql -u myllm_writer -p myllm_projects_db < infrastructure/database/ddl_version_events.sql
```

---

#### PASO 2: Crear script de datos iniciales

Crear `/Users/administrator/develop/anewhope/scripts/create_initial_versions.py`:

```python
#!/usr/bin/env python3
"""Script para crear versiones v001 para proyectos existentes."""

import sys
from pathlib import Path

# Añadir el directorio raíz al sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_dir))

from sqlalchemy import create_engine, text
import requests

def create_initial_versions():
    """Crea versiones v001 para todos los proyectos existentes."""
    
    # Conectar a la base de datos
    engine = create_engine("mysql+pymysql://myllm_writer:PASSWORD@localhost:3306/myllm_projects_db")
    
    with engine.connect() as conn:
        # 1. Obtener proyectos existentes
        result = conn.execute(text("SELECT id_proyecto, id_organizacion, nombre_proyecto FROM proyectos"))
        proyectos = result.fetchall()
        
        for proyecto in proyectos:
            id_proyecto = proyecto[0]
            id_organizacion = proyecto[1]
            nombre_proyecto = proyecto[2]
            
            print(f"Procesando proyecto {id_proyecto}: {nombre_proyecto}")
            
            # 2. Verificar si ya existe versión v001
            result = conn.execute(
                text("SELECT COUNT(*) FROM versiones WHERE id_proyecto = :id_proyecto AND id_version = 1"),
                {"id_proyecto": id_proyecto}
            )
            if result.fetchone()[0] > 0:
                print(f"  ⏭️  Versión v001 ya existe para proyecto {id_proyecto}")
                continue
            
            # 3. Crear versión v001 en tabla versiones
            conn.execute(
                text("""
                    INSERT INTO versiones (id_organizacion, id_proyecto, id_version, nombre_version, created_by_user_id)
                    VALUES (:id_org, :id_prj, 1, 'v001', 1)
                """),
                {"id_org": id_organizacion, "id_prj": id_proyecto}
            )
            conn.commit()
            print(f"  ✅ Versión v001 creada en DB")
            
            # 4. Crear registro en version_states
            conn.execute(
                text("""
                    INSERT INTO version_states 
                    (id_organizacion, id_proyecto, id_version, state, protected, size_bytes, final_c, final_i)
                    VALUES (:id_org, :id_prj, 1, 'Abierta', FALSE, 0, FALSE, FALSE)
                """),
                {"id_org": id_organizacion, "id_prj": id_proyecto}
            )
            conn.commit()
            print(f"  ✅ Estado creado")
            
            # 5. Crear evento de creación
            conn.execute(
                text("""
                    INSERT INTO version_events
                    (id_organizacion, id_proyecto, id_version, evento, mensaje, user_id, user_name, old_state, new_state)
                    VALUES (:id_org, :id_prj, 1, 'VERSION_CREADA', 'Versión v001 creada automáticamente', 1, 'system', NULL, 'Abierta')
                """),
                {"id_org": id_organizacion, "id_prj": id_proyecto}
            )
            conn.commit()
            print(f"  ✅ Evento registrado")
            
            # 6. Llamar a fmanagement para crear estructura física
            try:
                # Formato: ORG0001/PRJ0001/v001
                org_folder = f"ORG{id_organizacion:04d}"
                prj_folder = f"PRJ{id_proyecto:05d}"
                version_folder = "v001"
                
                # Llamar a Backend Core para crear la estructura
                # (Backend Core se encargará de llamar a fmanagement)
                response = requests.post(
                    "http://localhost:8003/create-version-physical",
                    json={
                        "organization_id": id_organizacion,
                        "project_id": id_proyecto,
                        "version_id": 1,
                        "create_sample_files": True,  # Crear archivos de ejemplo
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    print(f"  ✅ Estructura física creada en fmanagement")
                else:
                    print(f"  ⚠️  Error al crear estructura física: {response.status_code}")
            except Exception as e:
                print(f"  ⚠️  Error al llamar a fmanagement: {e}")

if __name__ == "__main__":
    create_initial_versions()
    print("\n✅ Proceso completado")
```

---

#### PASO 3: Ejecutar el script
```bash
cd /Users/administrator/develop/anewhope
python3 scripts/create_initial_versions.py
```

---

### FASE 4: Probar el explorador con datos reales

1. ✅ Login en Frontend (http://localhost:8005)
2. ✅ Ir a página "Proyecciones"
3. ✅ Seleccionar un proyecto
4. ✅ Ver el explorador de archivos con la versión v001
5. ✅ Verificar que se puede navegar por carpetas
6. ✅ Crear una nueva versión v002

---

## 📊 CHECKLIST COMPLETO

### Servicios:
- [ ] Middleware corriendo (puerto 8007)
- [ ] Backend Core corriendo (puerto 8003) (opcional)
- [ ] Broker corriendo (puerto 8008) (opcional)
- [ ] Frontend corriendo (puerto 8005)
- [ ] Backoffice corriendo (puerto 8006) (opcional)

### Base de datos:
- [ ] Tablas `version_states` y `version_events` creadas
- [ ] Versiones v001 insertadas para proyectos existentes
- [ ] Estados y eventos registrados

### Integración fmanagement:
- [ ] Estructuras físicas creadas (ORG####/PRJ#####/v001/)
- [ ] Archivos de ejemplo generados

### Pruebas:
- [ ] Login funciona en Frontend
- [ ] Explorador carga en página Proyecciones
- [ ] Se pueden navegar carpetas/archivos
- [ ] Se puede crear nueva versión

---

## 🚨 ACCIÓN INMEDIATA

**1. Arrancar middleware**:
```bash
cd /Users/administrator/develop/anewhope/src/apps/7_service_frontend
./run.sh
```

**2. Arrancar frontend**:
```bash
cd /Users/administrator/develop/anewhope/src/apps/5_web_frontend
./run.sh
```

**3. Reportar resultado**:
- ✅ Si arranca sin errores → continuar con login
- ❌ Si hay ImportError → reportar error completo

---

**ESTADO**: ⏸️ **Esperando arranque de middleware para continuar**
