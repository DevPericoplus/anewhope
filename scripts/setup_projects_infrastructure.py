#!/usr/bin/env python3
"""Script para crear infraestructura de proyectos existentes.

Este script:
1. Consulta proyectos sin versiones
2. Crea registros de v001 en la tabla versiones
3. Crea estructuras de carpetas en fmanagement
"""

import sys
import pymysql
from pathlib import Path

# Añadir src al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Importar usando importlib para manejar nombres con números
import importlib.util

# Cargar FmanagementClient
spec = importlib.util.spec_from_file_location(
    "fmanagement_client",
    Path(__file__).parent.parent / "src/apps/3_backend/clients/fmanagement_client.py"
)
fmanagement_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fmanagement_module)
FmanagementClient = fmanagement_module.FmanagementClient

# Cargar storage_access_structure
spec2 = importlib.util.spec_from_file_location(
    "storage_access_structure",
    Path(__file__).parent.parent / "src/2_shared_application/storage_access_structure.py"
)
storage_module = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(storage_module)
get_folder_by_id_organization = storage_module.get_folder_by_id_organization
get_folder_by_id_project = storage_module.get_folder_by_id_project
get_folder_by_id_version = storage_module.get_folder_by_id_version

# Configuración de MariaDB (desde protected_values.py)
MARIADB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "myllm_admin",
    "password": "Us3r@dminP@ss",
    "database": "myllm_projects_db",
}

# Cliente de fmanagement
fmanagement = FmanagementClient(base_url="http://localhost:1666")


def get_db_connection():
    """Crea conexión a MariaDB."""
    return pymysql.connect(**MARIADB_CONFIG)


def get_table_structure():
    """Consulta la estructura de la tabla versiones."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DESCRIBE versiones;")
    columns = cursor.fetchall()

    print("\n=== Estructura tabla versiones ===")
    for col in columns:
        print(f"  {col[0]:20s} {col[1]:20s} NULL={col[2]} KEY={col[3]}")

    cursor.close()
    conn.close()
    return columns


def get_projects_without_versions():
    """Consulta proyectos que no tienen versiones."""
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    query = """
        SELECT p.id, p.nombre, p.id_organizacion, p.descripcion
        FROM proyectos p
        LEFT JOIN versiones v ON p.id = v.id_proyecto
        WHERE v.id_proyecto IS NULL
        ORDER BY p.id_organizacion, p.id
    """

    cursor.execute(query)
    projects = cursor.fetchall()

    cursor.close()
    conn.close()
    return projects


def get_all_projects():
    """Consulta todos los proyectos."""
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT id, nombre, id_organizacion, descripcion
        FROM proyectos
        ORDER BY id_organizacion, id
    """)
    projects = cursor.fetchall()

    cursor.close()
    conn.close()
    return projects


def check_existing_versions():
    """Verifica qué versiones ya existen."""
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT id_proyecto, COUNT(*) as num_versiones
        FROM versiones
        GROUP BY id_proyecto
    """)
    versions = cursor.fetchall()

    cursor.close()
    conn.close()
    return {v["id_proyecto"]: v["num_versiones"] for v in versions}


def create_version_record(project_id: int, org_id: int):
    """Crea un registro de v001 en la tabla versiones.

    Args:
        project_id: ID del proyecto
        org_id: ID de la organización

    Returns:
        ID de la versión creada
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Primero verificar estructura real de la tabla
    cursor.execute("SHOW COLUMNS FROM versiones;")
    columns = [col[0] for col in cursor.fetchall()]
    print(f"    Columnas disponibles: {columns}")

    # Insertar v001 (ajustar según campos reales)
    # Campos comunes: id_proyecto, id_organizacion, id_version (int), state
    query = """
        INSERT INTO versiones (id_proyecto, id_organizacion, id_version, state)
        VALUES (%s, %s, %s, %s)
    """

    cursor.execute(query, (project_id, org_id, 1, "open"))
    version_id = cursor.lastrowid
    conn.commit()

    cursor.close()
    conn.close()
    return version_id


def create_fmanagement_structure(org_id: int, project_id: int):
    """Crea la estructura de carpetas en fmanagement para v001.

    Args:
        org_id: ID de la organización
        project_id: ID del proyecto

    Returns:
        Resultado de la creación
    """
    org_folder = get_folder_by_id_organization(org_id)
    prj_folder = get_folder_by_id_project(project_id)
    version_folder = get_folder_by_id_version(1)  # v001

    print(f"    Creando estructura: {org_folder}/{prj_folder}/{version_folder}")

    # Usar create_version del cliente que crea estructura vacía
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
    """Ejecuta el proceso de setup de infraestructura."""
    print("="*70)
    print("SETUP DE INFRAESTRUCTURA DE PROYECTOS")
    print("="*70)

    # 1. Consultar estructura de versiones
    print("\n[1/5] Consultando estructura de tabla versiones...")
    get_table_structure()

    # 2. Consultar proyectos existentes
    print("\n[2/5] Consultando proyectos...")
    all_projects = get_all_projects()
    print(f"  Total proyectos: {len(all_projects)}")

    # 3. Verificar versiones existentes
    print("\n[3/5] Verificando versiones existentes...")
    existing_versions = check_existing_versions()

    projects_without_versions = []
    for project in all_projects:
        num_versions = existing_versions.get(project["id"], 0)
        status = f"{num_versions} versiones" if num_versions > 0 else "SIN VERSIONES"
        print(f"  Proyecto {project['id']:2d} ({project['nombre']:20s}): {status}")

        if num_versions == 0:
            projects_without_versions.append(project)

    if not projects_without_versions:
        print("\n  ✅ Todos los proyectos ya tienen versiones.")
        return

    print(f"\n  ⚠️  {len(projects_without_versions)} proyectos necesitan v001")

    # 4. Crear registros en versiones y estructuras en fmanagement
    print("\n[4/5] Creando registros de v001 y estructuras en fmanagement...")

    for project in projects_without_versions:
        project_id = project["id"]
        org_id = project["id_organizacion"]
        nombre = project["nombre"]

        print(f"\n  Proyecto {project_id}: {nombre}")

        try:
            # Crear registro en versiones
            print(f"    Creando registro v001 en base de datos...")
            version_id = create_version_record(project_id, org_id)
            print(f"    ✅ Versión creada (ID: {version_id})")

            # Crear estructura en fmanagement
            print(f"    Creando estructura de carpetas en fmanagement...")
            result = create_fmanagement_structure(org_id, project_id)

            if result.get("status") == "success" or "error" not in result:
                print(f"    ✅ Estructura creada correctamente")
            else:
                print(f"    ⚠️  Error: {result.get('error', 'Desconocido')}")

        except Exception as e:
            print(f"    ❌ Error: {type(e).__name__}: {e}")

    # 5. Verificación final
    print("\n[5/5] Verificación final...")
    final_versions = check_existing_versions()

    for project in all_projects:
        num_versions = final_versions.get(project["id"], 0)
        status = "✅" if num_versions > 0 else "❌"
        print(f"  {status} Proyecto {project['id']:2d}: {num_versions} versiones")

    print("\n" + "="*70)
    print("PROCESO COMPLETADO")
    print("="*70)


if __name__ == "__main__":
    main()
