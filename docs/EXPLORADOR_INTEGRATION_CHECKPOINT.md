# Checkpoint de Integración - PASO A PASO

**Fecha**: 2026-02-03  
**Estado**: Actualizando create_new_version en Backoffice  
**IDE**: Crashea frecuentemente - Este documento permite retomar

---

## ✅ PASOS COMPLETADOS

### PASO 7.1 - Lectura estructura Frontend ✅
- Archivo: `src/apps/5_web_frontend/web_frontend/web_frontend.py`
- Línea 3402-3509: proyecciones_management_panel() con 3 capas
- Resultado: Frontend 100% integrado

### PASO 7.2 - Verificación imports Frontend ✅
- Línea 40: Import de explorador correcto
- Línea 3495-3496: Uso del explorador en UI
- Resultado: Imports correctos

### PASO 7.3 - Verificación create_new_version Frontend ✅
- Línea 1324-1372: Método implementado correctamente
- Usa create_version_full (API atómica)
- Resultado: Frontend funcional

### PASO 7.4 - Documentación estado Frontend ✅
- Creado: `docs/EXPLORADOR_INTEGRATION_STATUS.md`
- Resultado: Checkpoint inicial documentado

### PASO 7.5 - Verificación imports Backoffice ✅
- Línea 41: Import de explorador correcto
- Línea 3083: Uso del explorador en UI
- Resultado: Imports correctos

### PASO 7.6 - Verificación proyecciones_management_panel Backoffice ✅
- Detectadas 3 funciones duplicadas:
  - Línea 2362-2512 (placeholder sin explorador) ❌
  - Línea 2514-2987 (placeholder sin explorador) ❌
  - Línea 2989-3095 (versión avanzada con explorador) ✅
- Resultado: Detectado problema de duplicados

### PASO 7.7 - Verificación create_new_version Backoffice ✅
- Línea 951-979: Usa create_project_version (API antigua) ❌
- Resultado: Detectado problema - requiere actualización

### PASO 7.8-7.12 - Documentación de limpieza ✅
- Creado: `docs/EXPLORADOR_BACKOFFICE_CLEANUP.md`
- Resultado: Plan de limpieza documentado

### PASO 7.13 - Eliminación de función duplicada ✅
- Ejecutado: `sed -i '' '2390,2541d'` en web_backoffice.py
- Eliminadas: 152 líneas (primera función duplicada)
- Resultado: Solo queda 1 función proyecciones_management_panel

### PASO 7.14 - Verificación de eliminación ✅
- Ejecutado: `grep -n "^def proyecciones_management_panel"`
- Resultado: Solo 1 función en línea 2713 ✅
- Confirmado: Tiene explorador_panel integrado ✅

### PASO 7.15 - Verificación import create_version_full ✅
- Línea 17: `create_version_full` está importado ✅
- Resultado: Import disponible para usar

---

## ⏭️ PASO ACTUAL: 7.16 - Actualizar create_new_version en Backoffice

**Archivo**: `src/apps/6_web_backoffice/web_backoffice/web_backoffice.py`
**Línea actual**: 951-979 (método create_new_version)

### Cambio a realizar:

**ANTES** (líneas 951-979):
```python
def create_new_version(self):
    """Crea una nueva versión para el proyecto seleccionado."""
    if self.proyecciones_project_id <= 0:
        self.proyecciones_error = "Selecciona un proyecto primero"
        return
    
    self.is_loading_versions = True
    self.proyecciones_error = ""
    self.proyecciones_success = ""
    
    try:
        result = create_project_version(  # ← API ANTIGUA
            project_id=self.proyecciones_project_id,
            organization_id=self.organization_id,
            access_token=self.access_token,
            session_token=self.session_token,
        )
        
        if result.get("success"):
            self.proyecciones_success = "Nueva versión creada correctamente"
            self.load_proyecciones_versions()
        else:
            self.proyecciones_error = result.get("mensaje", "Error al crear versión")
    except Exception as e:
        print(f"[ERROR] Error creando versión: {type(e).__name__}: {e}")
        self.proyecciones_error = f"Error creando versión: {e}"
    finally:
        self.is_loading_versions = False
```

**DESPUÉS** (copiar del Frontend):
```python
def create_new_version(self):
    """Crea una nueva versión completa (DB + fmanagement) para el proyecto seleccionado."""
    if self.proyecciones_project_id <= 0:
        self.proyecciones_error = "Selecciona un proyecto primero"
        return
    
    self.is_loading_versions = True
    self.proyecciones_error = ""
    self.proyecciones_success = ""
    yield  # Actualizar UI
    
    try:
        # Generar nombre de versión (V001, V002, etc.)
        existing_versions = len(self.proyecciones_versions)
        version_name = f"V{existing_versions + 1:03d}"
        
        # Llamar al endpoint atómico create_version_full
        result = create_version_full(  # ← API NUEVA ATÓMICA
            project_id=self.proyecciones_project_id,
            organization_id=self.organization_id,
            version_name=version_name,
            user_id=self.user_id,
            user_name=self.user_name,
            description=f"Versión creada automáticamente por {self.user_name}",
            clone_from_version_id=self.proyecciones_version_id if self.proyecciones_version_id > 0 else None,
            initial_state="Abierta",
            protected=False,
            final_c=False,
            final_i=False,
            access_token=self.access_token,
            session_token=self.session_token,
        )
        
        if result.get("success"):
            new_version_id = result.get("version_id", 0)
            self.proyecciones_success = f"✅ Versión {version_name} creada correctamente (ID: {new_version_id})"
            # Recargar versiones
            self.load_proyecciones_versions()
            # Seleccionar automáticamente la nueva versión
            self.proyecciones_version_id = new_version_id
            self.proyecciones_version_folder = version_name
        else:
            self.proyecciones_error = result.get("mensaje", "Error al crear versión")
    except Exception as e:
        print(f"[ERROR] Error creando versión completa: {type(e).__name__}: {e}")
        self.proyecciones_error = f"Error creando versión: {e}"
    finally:
        self.is_loading_versions = False
        yield  # Actualizar UI final
```

---

## ⏭️ PRÓXIMOS PASOS DESPUÉS DE 7.16

### PASO 7.17 - Verificar inicialización ExploradorState
- Buscar llamadas a `explorador_state.init_page()` en Backoffice
- Comparar con Frontend (líneas 1293-1295 y 1317-1319)

### PASO 7.18 - Actualizar EXPLORADOR_PROGRESS.md
- Añadir FASE 7 completada
- Actualizar progreso global

### PASO 7.19 - Actualizar TODOs
- Marcar `explorador-5` como completado

### PASO 7.20 - Commit final
- Commit de toda la integración

---

## 🔄 SI EL IDE CRASHEA, RETOMAR DESDE AQUÍ:

**Último paso completado**: PASO 7.15 ✅  
**Próximo paso**: PASO 7.16 ⏭️  
**Acción**: Actualizar método `create_new_version()` línea 951-979  
**Archivo**: `src/apps/6_web_backoffice/web_backoffice/web_backoffice.py`

---

**Fin del checkpoint actualizado**
