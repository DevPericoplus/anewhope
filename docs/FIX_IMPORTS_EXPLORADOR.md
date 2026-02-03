# Fix de Imports - Componente Explorador

**Fecha**: 2026-02-04  
**Problema**: SyntaxError en imports de SharedSessionState  
**Causa**: Nombres de módulos con números (2_shared_application)  
**Solución**: Usar módulo shared_state.py intermedio

---

## 🐛 PROBLEMA DETECTADO

### Error en Frontend:
```
File "/Users/administrator/develop/anewhope/src/apps/5_web_frontend/components/explorador.py", line 18
    from src.apps.2_shared_application.reflex_shared.shared_session_state import (
                   ^
SyntaxError: invalid decimal literal
```

### Error en Backoffice:
```
File "/Users/administrator/develop/anewhope/src/apps/6_web_backoffice/components/explorador.py", line 21
    from src.apps.2_shared_application.reflex_shared.shared_session_state import (
                   ^
SyntaxError: invalid decimal literal
```

---

## 🔍 CAUSA RAÍZ

Python **no permite** nombres de módulos que empiecen con números.

El import incorrecto era:
```python
from src.apps.2_shared_application.reflex_shared.shared_session_state import (
    SharedSessionState,
)
```

`2_shared_application` no es un identificador válido en Python.

---

## ✅ SOLUCIÓN APLICADA

### PASO 7.36 - Frontend

**Archivo**: `src/apps/5_web_frontend/components/explorador.py`

**Cambio**:
```python
# ANTES (❌ INCORRECTO):
try:
    from src.apps.2_shared_application.reflex_shared.shared_session_state import (
        SharedSessionState,
    )
except ImportError:
    from ...2_shared_application.reflex_shared.shared_session_state import (
        SharedSessionState,
    )

# DESPUÉS (✅ CORRECTO):
from web_frontend.shared_state import SharedSessionState
```

---

### PASO 7.37 - Backoffice

**Archivo**: `src/apps/6_web_backoffice/components/explorador.py`

**Cambio**:
```python
# ANTES (❌ INCORRECTO):
try:
    from src.apps.2_shared_application.reflex_shared.shared_session_state import (
        SharedSessionState,
    )
except ImportError:
    from ...2_shared_application.reflex_shared.shared_session_state import (
        SharedSessionState,
    )

# DESPUÉS (✅ CORRECTO):
from web_backoffice.shared_state import SharedSessionState
```

---

## 📚 CONTEXTO

### ¿Por qué funciona `shared_state.py`?

El archivo `web_frontend/shared_state.py` (y su equivalente en backoffice) usa **importación dinámica** con `importlib` para cargar módulos con nombres problemáticos.

**Ejemplo de `shared_state.py`**:
```python
import importlib.util
from pathlib import Path

def load_shared_session_state():
    """Carga SharedSessionState dinámicamente."""
    # Ruta al archivo shared_session_state.py
    shared_state_path = (
        Path(__file__).parent.parent.parent
        / "2_shared_application"
        / "reflex_shared"
        / "shared_session_state.py"
    )
    
    # Carga dinámica
    spec = importlib.util.spec_from_file_location(
        "shared_session_state", shared_state_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    return module.SharedSessionState

SharedSessionState = load_shared_session_state()
```

Este enfoque **evita el SyntaxError** al no usar la sintaxis `import` directamente.

---

## 🔧 PASOS EJECUTADOS

| Paso | Acción | Archivo | Estado |
|------|--------|---------|--------|
| 7.36 | Corregir import Frontend | `5_web_frontend/components/explorador.py` | ✅ |
| 7.37 | Corregir import Backoffice | `6_web_backoffice/components/explorador.py` | ✅ |
| 7.38 | Documentar fix | `docs/FIX_IMPORTS_EXPLORADOR.md` | ✅ |

---

## ✅ VERIFICACIÓN

### Comandos para verificar el fix:

```bash
cd /Users/administrator/develop/anewhope

# Frontend
cd src/apps/5_web_frontend
./run.sh
# Debe arrancar sin SyntaxError

# Backoffice
cd src/apps/6_web_backoffice
./run.sh
# Debe arrancar sin SyntaxError
```

### Esperado:
- ✅ No más `SyntaxError: invalid decimal literal`
- ✅ Apps arrancan correctamente
- ✅ Explorador carga sin errores

---

## 📋 ARCHIVOS MODIFICADOS

1. `src/apps/5_web_frontend/components/explorador.py` (líneas 17-24)
2. `src/apps/6_web_backoffice/components/explorador.py` (líneas 17-24)

**Líneas cambiadas**: 16 líneas (8 por archivo)

---

## 🎯 LECCIÓN APRENDIDA

**Problema**: Cuando copias código de un template externo, verifica que los imports sean compatibles con la estructura del proyecto destino.

**Solución**: Siempre usa los imports que ya funcionan en otros archivos del mismo proyecto (en este caso, `web_frontend.shared_state`).

---

## ⏭️ PRÓXIMO PASO

**PASO 7.39**: Probar que las apps arrancan correctamente

```bash
# Frontend
cd /Users/administrator/develop/anewhope/src/apps/5_web_frontend
./run.sh

# Backoffice (en otro terminal)
cd /Users/administrator/develop/anewhope/src/apps/6_web_backoffice
./run.sh
```

---

**FIN DEL FIX - IMPORTS CORREGIDOS**
