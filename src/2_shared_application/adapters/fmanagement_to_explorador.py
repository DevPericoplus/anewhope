"""
Adaptador para convertir la respuesta de fmanagement list al formato del componente explorador.

La respuesta de fmanagement_list retorna una estructura plana:
{
    "success": bool,
    "items": [
        {
            "name": str,
            "type": str,  # "folder" | "file"
            "path": str,
            "size": int | None,
            "modified": str | None
        }
    ]
}

El componente explorador espera una estructura jerárquica:
{
    "status": "success",
    "path": str,
    "items": [
        {
            "name": str,
            "is_dir": bool,
            "size_bytes": int,
            "items": [...]  # recursivo si is_dir
        }
    ]
}

Dado que la página ya tiene selectores de proyecto y versión, el adaptador
construye la jerarquía a partir del nivel de versión.
"""

from typing import Any


def convert_fmanagement_to_explorador(
    fmanagement_response: dict[str, Any],
    org_id: int,
    project_id: int,
    version_name: str,
    org_folder: str = "",
    prj_folder: str = "",
) -> dict[str, Any]:
    """
    Convierte la respuesta plana de fmanagement al formato jerárquico del explorador.

    Args:
        fmanagement_response: Respuesta de fmanagement_list con estructura plana
        org_id: ID de la organización
        project_id: ID del proyecto
        version_name: Nombre de la versión (ej: "v001")
        org_folder: Nombre de la carpeta de organización (ej: "ORG0001")
        prj_folder: Nombre de la carpeta de proyecto (ej: "PRJ00001")

    Returns:
        Diccionario con estructura jerárquica para el explorador:
        {
            "status": "success",
            "path": str,
            "items": [
                {
                    "name": str (nombre del proyecto),
                    "is_dir": true,
                    "size_bytes": int,
                    "items": [
                        {
                            "name": str (nombre de la versión),
                            "is_dir": true,
                            "size_bytes": int,
                            "items": [...contenido de fmanagement...]
                        }
                    ]
                }
            ]
        }
    """
    # Validar respuesta de fmanagement
    if not fmanagement_response.get("success"):
        return {
            "status": "error",
            "path": "",
            "items": [],
            "mensaje": fmanagement_response.get("mensaje", "Error en fmanagement")
        }

    # Obtener items de fmanagement
    fmanagement_items = fmanagement_response.get("items", [])

    # Construir estructura jerárquica a partir de los items de fmanagement
    version_content = _build_hierarchy_from_flat_list(fmanagement_items)

    # Calcular tamaño total de la versión
    version_size = _calculate_total_size(version_content)

    # Construir la versión
    version_item = {
        "name": version_name,
        "is_dir": True,
        "size_bytes": version_size,
        "items": version_content
    }

    # Construir el proyecto (que contiene la versión)
    project_size = version_size  # Por ahora solo una versión
    project_item = {
        "name": prj_folder or f"PRJ{str(project_id).zfill(5)}",
        "is_dir": True,
        "size_bytes": project_size,
        "items": [version_item]
    }

    # Construir respuesta final
    base_path = f"/data/files/external/{org_folder or f'ORG{str(org_id).zfill(5)}'}/{prj_folder or f'PRJ{str(project_id).zfill(5)}'}"

    return {
        "status": "success",
        "path": base_path,
        "items": [project_item]
    }


def _build_hierarchy_from_flat_list(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Construye una jerarquía de árbol a partir de una lista plana de items.

    Asume que los items tienen paths relativos separados por '/' que indican
    la estructura de directorios.

    Args:
        items: Lista plana de items con paths

    Returns:
        Lista jerárquica de items
    """
    print(f"DEBUG _build_hierarchy: Procesando {len(items)} items de fmanagement")
    if items and len(items) > 0:
        print(f"DEBUG _build_hierarchy: Ejemplo de item: {items[0]}")

    # Crear un diccionario para mapear paths a nodos
    tree_map: dict[str, dict[str, Any]] = {}
    root_items: list[dict[str, Any]] = []

    # Ordenar items por profundidad (paths más cortos primero)
    sorted_items = sorted(items, key=lambda x: (x.get("path") or "").count("/"))

    for item in sorted_items:
        path = item.get("path") or ""
        name = item.get("name") or ""
        is_folder = item.get("type", "file") == "folder"
        size = item.get("size", 0) or 0

        # Crear nodo
        node = {
            "name": name,
            "is_dir": is_folder,
            "size_bytes": size,
        }

        # Si es carpeta, inicializar array de items
        if is_folder:
            node["items"] = []

        # Guardar en el mapa
        tree_map[path] = node

        # Determinar el padre
        if "/" in path:
            # Tiene padre
            parent_path = "/".join(path.split("/")[:-1])
            if parent_path in tree_map:
                parent = tree_map[parent_path]
                if "items" in parent:
                    parent["items"].append(node)
            else:
                # El padre no existe aún, añadir a raíz temporalmente
                root_items.append(node)
        else:
            # Es un item de raíz
            root_items.append(node)

    return root_items


def _calculate_total_size(items: list[dict[str, Any]]) -> int:
    """
    Calcula el tamaño total de una lista de items recursivamente.

    Args:
        items: Lista de items con size_bytes

    Returns:
        Tamaño total en bytes
    """
    total = 0
    for item in items:
        total += item.get("size_bytes", 0)
        # Verificar que items exista y no sea None
        if item.get("is_dir") and item.get("items") is not None:
            total += _calculate_total_size(item["items"])
    return total


def convert_multiple_versions_to_explorador(
    versions_data: list[dict[str, Any]],
    org_id: int,
    project_id: int,
    org_folder: str = "",
    prj_folder: str = "",
) -> dict[str, Any]:
    """
    Convierte múltiples versiones de fmanagement al formato del explorador.

    Útil cuando se quiere mostrar todas las versiones de un proyecto.

    Args:
        versions_data: Lista de diccionarios, cada uno con:
            {
                "version_name": str,
                "fmanagement_response": dict
            }
        org_id: ID de la organización
        project_id: ID del proyecto
        org_folder: Nombre de la carpeta de organización
        prj_folder: Nombre de la carpeta de proyecto

    Returns:
        Diccionario con estructura jerárquica para el explorador con todas las versiones
    """
    version_items = []
    total_project_size = 0

    for version_data in versions_data:
        version_name = version_data.get("version_name", "")
        fmanagement_response = version_data.get("fmanagement_response", {})

        if not fmanagement_response.get("success"):
            continue

        # Procesar items de esta versión
        # Los items ya vienen en formato jerárquico desde fmanagement
        fmanagement_items = fmanagement_response.get("items", [])
        print(f"DEBUG adaptador: version {version_name} tiene {len(fmanagement_items)} items de fmanagement")
        if fmanagement_items:
            print(f"DEBUG adaptador: Primer item de {version_name}: {fmanagement_items[0]}")
        version_content = fmanagement_items
        version_size = _calculate_total_size(version_content)

        # Añadir versión
        version_items.append({
            "name": version_name,
            "is_dir": True,
            "size_bytes": version_size,
            "items": version_content
        })

        total_project_size += version_size

    # Construir el proyecto con todas las versiones
    project_item = {
        "name": prj_folder or f"PRJ{str(project_id).zfill(5)}",
        "is_dir": True,
        "size_bytes": total_project_size,
        "items": version_items
    }

    # Construir respuesta final
    base_path = f"/data/files/external/{org_folder or f'ORG{str(org_id).zfill(5)}'}/{prj_folder or f'PRJ{str(project_id).zfill(5)}'}"

    return {
        "status": "success",
        "path": base_path,
        "items": [project_item]
    }


# ============================================================================
# Función de ejemplo para testing
# ============================================================================

def example_usage():
    """Ejemplo de uso del adaptador."""

    # Respuesta simulada de fmanagement_list
    fmanagement_response = {
        "success": True,
        "items": [
            {"name": "src", "type": "folder", "path": "src", "size": 0, "modified": None},
            {"name": "main.go", "type": "file", "path": "src/main.go", "size": 47455, "modified": "2024-01-15"},
            {"name": "utils.go", "type": "file", "path": "src/utils.go", "size": 12500, "modified": "2024-01-15"},
            {"name": "docs", "type": "folder", "path": "docs", "size": 0, "modified": None},
            {"name": "README.md", "type": "file", "path": "docs/README.md", "size": 1240, "modified": "2024-01-10"},
            {"name": "assets", "type": "folder", "path": "assets", "size": 0, "modified": None},
            {"name": "logo.svg", "type": "file", "path": "assets/logo.svg", "size": 85000, "modified": "2024-01-12"},
        ]
    }

    # Convertir al formato del explorador
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


if __name__ == "__main__":
    example_usage()
