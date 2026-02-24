#!/usr/bin/env python3
"""
Script para crear versiones v001 para todos los proyectos existentes
y generar sus estructuras de carpetas en fmanagement.
"""
import sys
import json
import requests
from pathlib import Path
from datetime import datetime

# Agregar rutas necesarias
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

# Cargar protected_values
import importlib.util
protected_values_path = project_root / "infrastructure" / "environments" / "macbook" / "protected_values.py"
spec = importlib.util.spec_from_file_location("protected_values", protected_values_path)
protected_values = importlib.util.module_from_spec(spec)
spec.loader.exec_module(protected_values)

# Importar PyMySQL
try:
    import pymysql
except ImportError:
    print("❌ Error: pymysql no está instalado")
    print("   Ejecuta: pip install pymysql")
    sys.exit(1)


def get_db_connection():
    """Obtiene conexión a la base de datos."""
    return pymysql.connect(
        host=protected_values.mariadb_host,
        port=int(protected_values.mariadb_port),
        user=protected_values.mariadb_writer_user,
        password=protected_values.mariadb_writer_password,
        database="myllm_projects_db",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_existing_projects(conn):
    """Obtiene lista de proyectos existentes activos."""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT id, nombre, id_organizacion, active, existe
            FROM proyectos
            WHERE active = 1
            ORDER BY id
        """)
        return cursor.fetchall()


def get_organization_name(conn, org_id):
    """Obtiene el nombre de una organización desde myllm_core_db."""
    # Las organizaciones están en myllm_core_db, no en myllm_projects_db
    # Por simplicidad, usaremos org_{id} y si es org 1, usamos "acme"
    if org_id == 1:
        return "acme"
    return f"org_{org_id}"


def check_version_exists(conn, project_id):
    """Verifica si ya existe la versión v001 para un proyecto."""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT id FROM versiones
            WHERE id_proyecto = %s AND id_version = 1
        """, (project_id,))
        return cursor.fetchone() is not None


def create_version_v001(conn, project_id, org_id):
    """Crea la versión v001 para un proyecto."""
    now = datetime.now()
    today = now.date()

    with conn.cursor() as cursor:
        # Crear versión
        cursor.execute("""
            INSERT INTO versiones (
                id_proyecto,
                id_organizacion,
                id_version,
                fecha_lanzamiento,
                descripcion,
                creado_at,
                actualizado_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (project_id, org_id, 1, today, "Versión inicial v001", now, now))

        version_id = cursor.lastrowid

        # Crear estado de flujo de trabajo para la versión (todos los pasos en 0)
        cursor.execute("""
            INSERT INTO estado (
                id_organizacion,
                id_proyecto,
                id_version,
                propuesta_cliente,
                revision_interna,
                propuesta_mejoras,
                aceptacion_cliente,
                aceptacion_interna,
                entrenamiento_inicial,
                evaluacion_entrenamiento,
                reentrenamiento,
                optimizacion,
                aprobacion_calidad,
                generacion_llm,
                notificacion_descarga,
                creado_at,
                actualizado_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (org_id, project_id, version_id, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, now, now))

        conn.commit()
        return version_id


def create_fmanagement_structure(org_name, project_name, version="v001"):
    """Crea la estructura de carpetas y archivos en fmanagement."""

    # URL de fmanagement
    fmanagement_url = protected_values.fmanagement_api_url

    # Estructura base de carpetas
    folders_to_create = [
        "datos",
        "modelos",
        "evaluaciones",
        "resultados",
    ]

    # Archivos base a crear
    files_to_create = [
        {
            "path": "README.md",
            "content": f"# Proyecto: {project_name}\n\nVersión: {version}\n\nEste es el proyecto {project_name}.\n"
        },
        {
            "path": "datos/datos_entrenamiento.txt",
            "content": "Datos de entrenamiento placeholder\n"
        },
        {
            "path": "modelos/config.json",
            "content": json.dumps({"model": "placeholder", "version": version}, indent=2)
        },
    ]

    print(f"  📁 Creando estructura en fmanagement: {org_name}/{project_name}/{version}")

    # Crear carpetas
    for folder in folders_to_create:
        try:
            response = requests.post(
                f"{fmanagement_url}/create_folder",
                json={
                    "org": org_name,
                    "prj": project_name,
                    "version": version,
                    "folder_name": folder,
                },
                timeout=10,
            )
            if response.status_code == 200:
                print(f"    ✓ Carpeta creada: {folder}")
            else:
                print(f"    ⚠ Error al crear carpeta {folder}: {response.text}")
        except Exception as e:
            print(f"    ⚠ Excepción al crear carpeta {folder}: {e}")

    # Crear archivos
    for file_info in files_to_create:
        try:
            response = requests.post(
                f"{fmanagement_url}/write_file",
                json={
                    "org": org_name,
                    "prj": project_name,
                    "version": version,
                    "file_path": file_info["path"],
                    "content": file_info["content"],
                },
                timeout=10,
            )
            if response.status_code == 200:
                print(f"    ✓ Archivo creado: {file_info['path']}")
            else:
                print(f"    ⚠ Error al crear archivo {file_info['path']}: {response.text}")
        except Exception as e:
            print(f"    ⚠ Excepción al crear archivo {file_info['path']}: {e}")

    print(f"  ✅ Estructura creada para {org_name}/{project_name}/{version}")


def main():
    print("=" * 80)
    print("CREACIÓN DE VERSIONES v001 Y ESTRUCTURAS DE FMANAGEMENT")
    print("=" * 80)
    print()

    # Conectar a la base de datos
    print("📊 Conectando a la base de datos...")
    try:
        conn = get_db_connection()
        print("✅ Conectado exitosamente\n")
    except Exception as e:
        print(f"❌ Error al conectar: {e}")
        return 1

    try:
        # Obtener proyectos existentes
        print("🔍 Consultando proyectos existentes...")
        projects = get_existing_projects(conn)
        print(f"✅ Encontrados {len(projects)} proyectos\n")

        if not projects:
            print("⚠️  No hay proyectos en la base de datos")
            return 0

        # Procesar cada proyecto
        created_count = 0
        skipped_count = 0

        for project in projects:
            project_id = project['id']
            project_name = project['nombre']
            org_id = project['id_organizacion']

            print(f"\n{'='*80}")
            print(f"📦 Proyecto: {project_name} (ID: {project_id})")
            print(f"   Organización ID: {org_id}")
            print(f"   Activo: {project['active']}, Existe: {project['existe']}")

            # Obtener nombre de organización
            org_name = get_organization_name(conn, org_id)
            print(f"   Organización: {org_name}")

            # Verificar si ya existe versión v001
            if check_version_exists(conn, project_id):
                print(f"  ⏭️  La versión v001 ya existe, omitiendo...")
                skipped_count += 1
                continue

            # Crear versión v001
            print(f"  ➕ Creando versión v001 en base de datos...")
            try:
                version_id = create_version_v001(conn, project_id, org_id)
                print(f"  ✅ Versión v001 creada (ID: {version_id})")
                created_count += 1
            except Exception as e:
                print(f"  ❌ Error al crear versión: {e}")
                continue

            # Crear estructura en fmanagement
            try:
                create_fmanagement_structure(org_name, project_name, "v001")
            except Exception as e:
                print(f"  ❌ Error al crear estructura en fmanagement: {e}")

        # Resumen final
        print(f"\n{'='*80}")
        print("RESUMEN FINAL")
        print(f"{'='*80}")
        print(f"✅ Versiones creadas: {created_count}")
        print(f"⏭️  Versiones omitidas (ya existían): {skipped_count}")
        print(f"📊 Total de proyectos procesados: {len(projects)}")
        print(f"{'='*80}\n")

        return 0

    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()
        print("🔌 Conexión cerrada")


if __name__ == "__main__":
    sys.exit(main())
