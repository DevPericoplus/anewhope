# Prueba de Integración del Adaptador fmanagement → Explorador

## Cambios Realizados

### Frontend (`src/apps/5_web_frontend/components/explorador.py`)

1. **Añadidos campos de autenticación**:
   ```python
   access_token: str = ""
   session_token: str = ""
   is_loading: bool = False
   error_message: str = ""
   ```

2. **Nuevo método `load_from_api()`**:
   - Usa `fmanagement_list_for_explorador()` del adaptador
   - Maneja errores y estados de carga
   - Genera nombres de carpetas automáticamente (ORG0001, PRJ00001)

3. **Método `init_page()` actualizado**:
   - Si tiene tokens → carga desde API (modo producción)
   - Si no tiene tokens → carga desde JSON (modo demo)

### Backoffice (`src/apps/6_web_backoffice/components/explorador.py`)

1. **Método `load_from_api()` actualizado**:
   - Ahora usa `fmanagement_list_for_explorador()` en lugar de `fmanagement_list()` directo
   - El adaptador maneja la conversión de formato automáticamente

---

## Requisitos Previos para Pruebas

### 1. Estructura de Directorios en fmanagement

Asegúrate de que existe la estructura física:
```
/data/files/external/
└── ORG0001/
    └── PRJ00001/
        └── v001/
            ├── docs/
            │   ├── manual.pdf
            │   └── README.md
            ├── src/
            │   ├── main.go
            │   └── utils.go
            └── assets/
                └── logo.svg
```

### 2. Servicios Corriendo

```bash
# Backend Core (puerto 8008)
cd /Users/administrator/develop/anewhope/src/apps/3_backend
reflex run --backend-only

# Middleware (puerto 8007)
cd /Users/administrator/develop/anewhope/src/apps/7_service_frontend
python apife.py

# fmanagement (puerto 1666)
cd /Users/administrator/develop/fmanagement
go run main.go
```

### 3. Base de Datos

Verificar que existen registros en:
- `version_states` para ORG0001/PRJ00001/v001
- `low_level_permissions` para el usuario de prueba

---

## Prueba 1: Verificar Endpoint de fmanagement

### Usando curl

```bash
# Test básico del endpoint list
curl -X GET "http://localhost:1666/fmo/list?iduser=1&basepath=/data/files/external&orgpath=ORG0001&prjpath=PRJ00001&versionpath=v001&identity_type_id=1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-Session-Token: YOUR_SESSION_TOKEN"
```

**Respuesta esperada**:
```json
{
  "status": "success",
  "path": "/data/files/external/ORG0001/PRJ00001/v001",
  "items": [
    {
      "name": "docs",
      "is_dir": true,
      "size_bytes": 0,
      "items": [...]
    },
    {
      "name": "src",
      "is_dir": true,
      "size_bytes": 0,
      "items": [...]
    }
  ]
}
```

---

## Prueba 2: Verificar Adaptador en Aislamiento

### Script de prueba

Crear `/tmp/test_adapter.py`:
```python
import sys
sys.path.insert(0, '/Users/administrator/develop/anewhope/src/2_shared_application/adapters')

from fmanagement_to_explorador import convert_fmanagement_to_explorador

# Simular respuesta de fmanagement
fmanagement_response = {
    "success": True,
    "items": [
        {"name": "docs", "type": "folder", "path": "docs", "size": 0, "modified": None},
        {"name": "README.md", "type": "file", "path": "docs/README.md", "size": 1240, "modified": "2024-01-10"},
        {"name": "src", "type": "folder", "path": "src", "size": 0, "modified": None},
        {"name": "main.go", "type": "file", "path": "src/main.go", "size": 47455, "modified": "2024-01-15"},
    ]
}

# Convertir con el adaptador
result = convert_fmanagement_to_explorador(
    fmanagement_response=fmanagement_response,
    org_id=1,
    project_id=1,
    version_name="v001",
    org_folder="ORG0001",
    prj_folder="PRJ00001"
)

import json
print(json.dumps(result, indent=2))
```

Ejecutar:
```bash
python /tmp/test_adapter.py
```

**Salida esperada**: Estructura jerárquica con PRJ00001 → v001 → contenido

---

## Prueba 3: Verificar Integración en Frontend

### Modo Demo (sin tokens)

1. Crear archivo de datos de demo:
```bash
mkdir -p /Users/administrator/develop/anewhope/src/apps/5_web_frontend/data
cp /Users/administrator/develop/reflex_components_templates/data/proyecto.json \
   /Users/administrator/develop/anewhope/src/apps/5_web_frontend/data/
```

2. Arrancar frontend:
```bash
cd /Users/administrator/develop/anewhope/src/apps/5_web_frontend
reflex run
```

3. Acceder a `http://localhost:3100/explorador`

**Comportamiento esperado**:
- Consola muestra: "Cargando desde JSON (modo demo - sin tokens)"
- Explorador muestra estructura del JSON

### Modo Producción (con tokens)

1. Iniciar sesión en la aplicación para obtener tokens

2. Los tokens se guardan automáticamente en el estado

3. Navegar a la página del explorador

4. Verificar en logs del navegador:
```
✓ Explorador cargado: X items
```

**Verificaciones**:
- ¿Se muestran los items del proyecto/versión correcta?
- ¿Los tamaños aparecen a la derecha de cada elemento?
- ¿La jerarquía (proyecto → versión → carpetas → archivos) es correcta?
- ¿Se puede expandir/colapsar carpetas?

---

## Prueba 4: Verificar Integración en Backoffice

```bash
cd /Users/administrator/develop/anewhope/src/apps/6_web_backoffice
reflex run
```

1. Iniciar sesión

2. Navegar a la página del explorador

3. Verificar logs del backend:
```
INFO: Cargando estructura fmanagement con adaptador: org=ORG0001, prj=PRJ00001, version=v001
INFO: Estructura cargada con adaptador: path=/data/files/external/ORG0001/PRJ00001
```

---

## Verificación de Tamaños

Los tamaños deben mostrarse correctamente:

- **Archivos**: Tamaño individual
- **Carpetas**: Suma de todo el contenido recursivamente
- **Versión**: Suma de todo su contenido
- **Proyecto**: Suma de todas sus versiones

Formato esperado:
- `manual.pdf` → `1.21 KB`
- `main.go` → `46.34 KB`
- `docs/` → `5.00 MB` (suma de todos los archivos dentro)
- `v001/` → `850.00 MB` (suma total de la versión)

---

## Debugging

### Logs del Frontend

```bash
tail -f /Users/administrator/develop/anewhope/src/apps/5_web_frontend/logs/frontend_console.log
```

Buscar:
- `"Cargando datos desde fmanagement"`
- `"Datos cargados exitosamente"`
- `"Error al cargar datos"`

### Logs de fmanagement

```bash
# Si fmanagement usa logs
tail -f /Users/administrator/develop/fmanagement/logs/fmanagement.log
```

### Console del Navegador

Abrir DevTools → Console

Buscar:
- `✓ Explorador cargado: X items`
- `✗ Error al cargar explorador: ...`

---

## Problemas Comunes

### 1. Error: "No se pudo cargar el adaptador de fmanagement"

**Causa**: Ruta incorrecta al adaptador

**Solución**: Verificar que existe:
```bash
ls -la /Users/administrator/develop/anewhope/src/2_shared_application/adapters/fmanagement_to_explorador.py
```

### 2. Error: "403 Forbidden"

**Causa**: Tokens inválidos o permisos insuficientes

**Solución**:
- Verificar que los tokens no han expirado
- Verificar `low_level_permissions` para el usuario
- Verificar que `identity_type_id` es correcto

### 3. Error: "404 Not Found"

**Causa**: La estructura física no existe en disco

**Solución**:
```bash
# Crear estructura de prueba
mkdir -p /data/files/external/ORG0001/PRJ00001/v001/docs
echo "Test file" > /data/files/external/ORG0001/PRJ00001/v001/docs/README.md
```

### 4. Explorador vacío

**Causa**: La respuesta de fmanagement no tiene items

**Solución**:
- Verificar que la carpeta de versión tiene contenido
- Verificar que fmanagement puede leer la carpeta
- Comprobar permisos del filesystem

### 5. Tamaños incorrectos (todos en 0 bytes)

**Causa**: fmanagement no está calculando tamaños

**Solución**: Verificar que fmanagement incluye `size_bytes` en su respuesta

---

## Siguientes Pasos

Una vez verificado que el adaptador funciona:

1. ✅ Integración del adaptador completa
2. ✅ Visualización de estructura jerárquica
3. ✅ Visualización de tamaños
4. ⏳ **Implementar acciones** (crear, renombrar, eliminar carpetas/archivos)
5. ⏳ Refrescar automático después de cada acción
6. ⏳ Diálogos de confirmación
7. ⏳ Manejo de errores mejorado

---

## Checklist de Verificación

- [ ] fmanagement responde correctamente a `/fmo/list`
- [ ] Adaptador convierte formato plano a jerárquico
- [ ] Frontend carga datos en modo demo (sin tokens)
- [ ] Frontend carga datos en modo producción (con tokens)
- [ ] Backoffice carga datos correctamente
- [ ] Se muestra jerarquía: Proyecto → Versión → Contenido
- [ ] Los tamaños aparecen a la derecha de cada elemento
- [ ] Se pueden expandir/colapsar carpetas
- [ ] Los iconos de archivos se muestran según extensión
- [ ] Los estados de versión se muestran correctamente
- [ ] No hay errores en logs ni consola
