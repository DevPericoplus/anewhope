#!/usr/bin/env python3
"""Script para verificar y crear estructuras de fmanagement para proyectos existentes."""

import sys
import pymysql
from pathlib import Path
import importlib.util

# Cargar FmanagementClient
spec = importlib.util.spec_from_file_location(
    "fmanagement_client",
    Path(__file__).parent / "src/apps/3_backend/clients/fmanagement_client.py"
)
fmanagement_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fmanagement_module)
FmanagementClient = fmanagement_module.FmanagementClient

# Cargar storage_access_structure
spec2 = importlib.util.spec_from_file_location(
    "storage_access_structure",
    Path(__file__).parent / "src/2_shared_application/storage_access_structure.py"
)
storage_module = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(storage_module)
get_folder_by_id_organization = storage_module.get_folder_by_id_organization
get_folder_by_id_project = storage_module.get_folder_by_id_project
get_folder_by_id_version = storage_module.get_folder_by_id_version

# Configuración
MARIADB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "myllm_admin",
    "password": "Us3r@dminP@ss",
    "database": "myllm_projects_db",
}

fmanagement = FmanagementClient(base_url="http://localhost:1666")


def get_all_versions():
    """Consulta todas las versiones de todos los proyectos."""
    conn = pymysql.connect(**MARIADB_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT
            v.id,
            v.id_proyecto,
            v.id_version,
            v.id_organizacion,
            p.nombre as proyecto_nombre
        FROM versiones v
        INNER JOIN proyectos p ON v.id_proyecto = p.id
        ORDER BY v.id_organizacion, v.id_proyecto, v.id_version
    """)
    versions = cursor.fetchall()

    cursor.close()
    conn.close()
    return versions


def check_fmanagement_structure(org_id: int, project_id: int, version_id: int):
    """Verifica si existe la estructura en fmanagement.

    Args:
        org_id: ID de la organización
        project_id: ID del proyecto
        version_id: ID numérico de la versión (1, 2, 3...)

    Returns:
        dict con status y datos
    """
    org_folder = get_folder_by_id_organization(org_id)
    prj_folder = get_folder_by_id_project(project_id)
    version_folder = get_folder_by_id_version(version_id)

    try:
        result = fmanagement.list_structure(
            orgpath=org_folder,
            prjpath=prj_folder,
            versionpath=version_folder,
            iduser=1,
            basepath="default",
        )

        # Si no hay error, la estructura existe
        if "error" not in result:
            return {"exists": True, "result": result}
        else:
            return {"exists": False, "error": result.get("error")}

    except Exception as e:
        return {"exists": False, "error": str(e)}


def create_fmanagement_structure(org_id: int, project_id: int, version_id: int):
    """Crea la estructura de carpetas en fmanagement.

    Args:
        org_id: ID de la organización
        project_id: ID del proyecto
        version_id: ID numérico de la versión (1, 2, 3...)

    Returns:
        Resultado de la creación
    """
    org_folder = get_folder_by_id_organization(org_id)
    prj_folder = get_folder_by_id_project(project_id)
    version_folder = get_folder_by_id_version(version_id)

    print(f"      Creando: {org_folder}/{prj_folder}/{version_folder}")

    result = fmanagement.create_version(
        orgpath=org_folder,
        prjpath=prj_folder,
        versionpath=version_folder,
        identity_type_id=1,  # Admin
        clone_from=None,  # Crear vacía
        iduser=1,
        basepath="default",
    )

    return result


def main():
    """Ejecuta la verificación y creación de estructuras."""
    print("="*70)
    print("VERIFICACIÓN Y CREACIÓN DE ESTRUCTURAS EN FMANAGEMENT")
    print("="*70)

    # 1. Consultar todas las versiones
    print("\n[1/3] Consultando versiones en base de datos...")
    versions = get_all_versions()
    print(f"  Total versiones encontradas: {len(versions)}")

    # 2. Verificar estructuras en fmanagement
    print("\n[2/3] Verificando estructuras en fmanagement...")

    missing_structures = []

    for version in versions:
        org_id = version["id_organizacion"]
        project_id = version["id_proyecto"]
        version_id = version["id_version"]
        project_name = version["proyecto_nombre"]

        org_folder = get_folder_by_id_organization(org_id)
        prj_folder = get_folder_by_id_project(project_id)
        ver_folder = get_folder_by_id_version(version_id)
        path = f"{org_folder}/{prj_folder}/{ver_folder}"

        print(f"\n  Verificando: {path} (Proyecto: {project_name})")

        check_result = check_fmanagement_structure(org_id, project_id, version_id)

        if check_result["exists"]:
            print(f"    ✅ Estructura existe")
        else:
            print(f"    ❌ Estructura NO existe")
            print(f"       Error: {check_result.get('error', 'Desconocido')}")
            missing_structures.append(version)

    if not missing_structures:
        print("\n  ✅ Todas las estructuras existen en fmanagement.")
        return

    # 3. Crear estructuras faltantes
    print(f"\n[3/3] Creando {len(missing_structures)} estructuras faltantes...")

    for version in missing_structures:
        org_id = version["id_organizacion"]
        project_id = version["id_proyecto"]
        version_id = version["id_version"]
        project_name = version["proyecto_nombre"]

        org_folder = get_folder_by_id_organization(org_id)
        prj_folder = get_folder_by_id_project(project_id)
        ver_folder = get_folder_by_id_version(version_id)
        path = f"{org_folder}/{prj_folder}/{ver_folder}"

        print(f"\n  Creando estructura para: {path}")
        print(f"    Proyecto: {project_name}")

        try:
            result = create_fmanagement_structure(org_id, project_id, version_id)

            if result.get("status") == "success" or "error" not in result:
                print(f"      ✅ Estructura creada correctamente")
            else:
                print(f"      ⚠️  Error: {result.get('error', 'Desconocido')}")
                print(f"      Detalles: {result}")

        except Exception as e:
            print(f"      ❌ Excepción: {type(e).__name__}: {e}")

    # 4. Verificación final
    print("\n" + "="*70)
    print("VERIFICACIÓN FINAL")
    print("="*70)

    for version in versions:
        org_id = version["id_organizacion"]
        project_id = version["id_proyecto"]
        version_id = version["id_version"]

        org_folder = get_folder_by_id_organization(org_id)
        prj_folder = get_folder_by_id_project(project_id)
        ver_folder = get_folder_by_id_version(version_id)
        path = f"{org_folder}/{prj_folder}/{ver_folder}"

        check_result = check_fmanagement_structure(org_id, project_id, version_id)
        status = "✅" if check_result["exists"] else "❌"
        print(f"  {status} {path}")

    print("\n" + "="*70)
    print("PROCESO COMPLETADO")
    print("="*70)


if __name__ == "__main__":
    main()
