# Uso del Adaptador fmanagement → Explorador

## Resumen

El adaptador `fmanagement_to_explorador.py` convierte la respuesta plana de fmanagement al formato jerárquico que espera el componente explorador, mostrando los tamaños de archivos a la derecha de cada elemento.

## Ubicación de Archivos

```
src/
├── 2_shared_application/
│   └── adapters/
│       └── fmanagement_to_explorador.py    # Adaptador principal
├── apps/
│   ├── 5_web_frontend/
│   │   ├── adapters/
│   │   │   └── api_client.py               # Incluye fmanagement_list_for_explorador()
│   │   └── components/
│   │       └── explorador.py               # Componente que consume el formato
│   └── 6_web_backoffice/
│       ├── adapters/
│       │   └── api_client.py               # Incluye fmanagement_list_for_explorador()
│       └── components/
│           └── explorador.py               # Componente que consume el formato
```

## Flujo de Datos

```
1. Página con selectores de proyecto y versión
   ↓
2. Llamada a fmanagement_list_for_explorador()
   ↓
3. API Client → Middleware → Broker → Backend → fmanagement
   ↓
4. Respuesta plana de fmanagement
   ↓
5. Adaptador convierte a formato jerárquico
   ↓
6. Componente Explorador renderiza la jerarquía con tamaños
```

## Formato de Entrada (fmanagement)

```json
{
    "success": true,
    "items": [
        {
            "name": "src",
            "type": "folder",
            "path": "src",
            "size": 0,
            "modified": null
        },
        {
            "name": "main.go",
            "type": "file",
            "path": "src/main.go",
            "size": 47455,
            "modified": "2024-01-15"
        },
        {
            "name": "utils.go",
            "type": "file",
            "path": "src/utils.go",
            "size": 12500,
            "modified": "2024-01-15"
        }
    ],
    "mensaje": null
}
```

## Formato de Salida (Explorador)

```json
{
    "status": "success",
    "path": "/data/files/external/ORG0001/PRJ00001",
    "items": [
        {
            "name": "PRJ00001",
            "is_dir": true,
            "size_bytes": 59955,
            "items": [
                {
                    "name": "v001",
                    "is_dir": true,
                    "size_bytes": 59955,
                    "items": [
                        {
                            "name": "src",
                            "is_dir": true,
                            "size_bytes": 0,
                            "items": [
                                {
                                    "name": "main.go",
                                    "is_dir": false,
                                    "size_bytes": 47455
                                },
                                {
                                    "name": "utils.go",
                                    "is_dir": false,
                                    "size_bytes": 12500
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}
```

## Uso en el Frontend

### Opción 1: Usar la función de conveniencia (Recomendado)

```python
from adapters.api_client import fmanagement_list_for_explorador

# En tu State
class ProjectState(rx.State):
    # ... otros campos ...
    explorador_data: dict = {}

    def load_explorador_data(self):
        """Carga los datos del explorador para el proyecto y versión actuales."""
        self.explorador_data = fmanagement_list_for_explorador(
            org_id=self.organization_id,
            project_id=self.project_id,
            version_name=self.current_version,  # ej: "v001"
            access_token=self.access_token,
            session_token=self.session_token,
        )

        # Los datos están listos para ser usados por el componente explorador
        if self.explorador_data.get("status") == "success":
            print("Datos cargados correctamente")
        else:
            print(f"Error: {self.explorador_data.get('mensaje')}")
```

### Opción 2: Usar el adaptador manualmente

```python
from adapters.api_client import fmanagement_list
import importlib.util
from pathlib import Path

def load_explorador_data_manual(self):
    """Carga datos usando el adaptador manualmente."""

    # 1. Obtener respuesta de fmanagement
    fmanagement_response = fmanagement_list(
        org_folder="ORG0001",
        prj_folder="PRJ00001",
        version_folder="v001",
        access_token=self.access_token,
        session_token=self.session_token,
    )

    # 2. Cargar adaptador
    adapter_path = Path(__file__).resolve().parents[3] / "2_shared_application/adapters/fmanagement_to_explorador.py"
    spec = importlib.util.spec_from_file_location("fmanagement_adapter", adapter_path)
    adapter_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter_module)

    # 3. Convertir al formato del explorador
    self.explorador_data = adapter_module.convert_fmanagement_to_explorador(
        fmanagement_response=fmanagement_response,
        org_id=1,
        project_id=1,
        version_name="v001",
        org_folder="ORG0001",
        prj_folder="PRJ00001",
    )
```

## Uso en el Componente Explorador

El componente explorador ya está preparado para recibir este formato:

```python
class ExploradorState(SharedSessionState):
    """Estado del explorador."""
    items: list[FolderItem] = []
    fmanagementlist: dict = {}

    def load_from_api(self):
        """Carga datos desde la API usando el adaptador."""
        # Obtener datos con el formato correcto
        from adapters.api_client import fmanagement_list_for_explorador

        self.fmanagementlist = fmanagement_list_for_explorador(
            org_id=self.organization_id,
            project_id=self.id_proyecto,
            version_name=self.id_version,
            access_token=self.access_token,
            session_token=self.session_token,
        )

        # Procesar la estructura jerárquica
        self.process_fmanagementlist()
```

## Múltiples Versiones

Si necesitas mostrar múltiples versiones en el explorador:

```python
from adapters.api_client import fmanagement_list
import importlib.util
from pathlib import Path

def load_all_versions(self):
    """Carga todas las versiones de un proyecto."""

    # 1. Obtener lista de versiones del proyecto
    versions = ["v001", "v002", "v003"]

    # 2. Obtener datos de fmanagement para cada versión
    versions_data = []
    for version_name in versions:
        fmanagement_response = fmanagement_list(
            org_folder="ORG0001",
            prj_folder="PRJ00001",
            version_folder=version_name,
            access_token=self.access_token,
            session_token=self.session_token,
        )

        versions_data.append({
            "version_name": version_name,
            "fmanagement_response": fmanagement_response
        })

    # 3. Cargar adaptador
    adapter_path = Path(__file__).resolve().parents[3] / "2_shared_application/adapters/fmanagement_to_explorador.py"
    spec = importlib.util.spec_from_file_location("fmanagement_adapter", adapter_path)
    adapter_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter_module)

    # 4. Convertir todas las versiones
    self.explorador_data = adapter_module.convert_multiple_versions_to_explorador(
        versions_data=versions_data,
        org_id=1,
        project_id=1,
        org_folder="ORG0001",
        prj_folder="PRJ00001",
    )
```

## Visualización de Tamaños

El adaptador proporciona el campo `size_bytes` para cada elemento, que el componente explorador formatea y muestra a la derecha:

- **Archivos**: Muestra el tamaño exacto
- **Carpetas**: Muestra la suma de todos sus contenidos recursivamente
- **Versiones**: Muestra el tamaño total de la versión
- **Proyectos**: Muestra la suma de todas sus versiones

Formato de visualización (implementado en el componente explorador):
- < 1024 B → "X B"
- < 1 MB → "X.XX KB"
- < 1 GB → "X.XX MB"
- < 1 TB → "X.XX GB"
- >= 1 TB → "X.XX TB"

## Testing del Adaptador

El adaptador incluye una función de ejemplo para testing:

```bash
cd /Users/administrator/develop/anewhope/src/2_shared_application/adapters
python fmanagement_to_explorador.py
```

Esto ejecutará un ejemplo con datos simulados y mostrará la estructura JSON resultante.

## Errores Comunes

### Error: "No se pudo cargar el adaptador de fmanagement"

**Causa**: La ruta al adaptador es incorrecta.

**Solución**: Verificar que el archivo existe en:
```
src/2_shared_application/adapters/fmanagement_to_explorador.py
```

### Error: "Error al procesar estructura de archivos"

**Causa**: La respuesta de fmanagement tiene un formato inesperado.

**Solución**: Verificar que fmanagement retorna:
```python
{
    "success": True,
    "items": [...]
}
```

### Tamaños incorrectos

**Causa**: El campo `size` en la respuesta de fmanagement es `None` o no está presente.

**Solución**: El adaptador maneja esto asignando 0 bytes. Verificar que fmanagement incluya el campo `size` para archivos.

## Próximos Pasos

1. ✅ Adaptador creado
2. ✅ Funciones de conveniencia añadidas a api_client.py
3. ⏳ Integrar en el componente explorador actual
4. ⏳ Reemplazar load_from_json() por load_from_api()
5. ⏳ Testing con datos reales de fmanagement
6. ⏳ Implementar cache para evitar llamadas repetidas
7. ⏳ Añadir loading states durante la carga
