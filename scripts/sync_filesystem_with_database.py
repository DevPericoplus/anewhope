#!/usr/bin/env python3
"""
Script para sincronizar el sistema de archivos con la base de datos.

Este script:
1. Lee todas las organizaciones, proyectos y versiones de la base de datos
2. Verifica qué estructuras de carpetas faltan en el filesystem
3. Crea las carpetas faltantes con estructura estándar (images/, text/)

Uso:
    python sync_filesystem_with_database.py [--dry-run]

Opciones:
    --dry-run    Muestra qué se creará sin crear nada
"""

import os
import sys
from pathlib import Path
from typing import Any

import pymysql

# Colores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"


def print_step(step: str, status: str = "info"):
    """Imprime un paso del proceso con formato."""
    color = BLUE if status == "info" else GREEN if status == "ok" else RED if status == "error" else YELLOW if status == "warning" else CYAN
    symbol = "ℹ" if status == "info" else "✓" if status == "ok" else "✗" if status == "error" else "⚠" if status == "warning" else "→"
    print(f"{color}{symbol} {step}{RESET}")


def get_db_connection():
    """Crea conexión a la base de datos."""
    # Importar protected_values dinámicamente
    import importlib.util
    protected_path = Path(__file__).parent.parent / "infrastructure" / "environments" / "macbook" / "protected_values.py"
    spec = importlib.util.spec_from_file_location("protected_values", protected_path)
    protected = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(protected)

    return pymysql.connect(
        host=protected.mariadb_host,
        port=protected.mariadb_port,
        user=protected.mariadb_reader_user,
        password=protected.mariadb_reader_password,
        database=protected.mariadb_core_database,
        cursorclass=pymysql.cursors.DictCursor
    )


def get_organizations(conn) -> list[dict[str, Any]]:
    """Obtiene todas las organizaciones de la base de datos."""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT organization_id, organization_name
            FROM organizations
            WHERE active = 1
            ORDER BY organization_id
        """)
        results = cursor.fetchall()
        # Generar nombre de carpeta basado en ID
        for org in results:
            org['organization_folder'] = f"ORG{org['organization_id']:04d}"
        return results


def get_projects(conn, id_organization: int) -> list[dict[str, Any]]:
    """Obtiene todos los proyectos de una organización."""
    with conn.cursor() as cursor:
        # Cambiar a la base de datos de proyectos
        cursor.execute("USE myllm_projects_db")
        cursor.execute("""
            SELECT id, nombre as project_name, id_organizacion
            FROM proyectos
            WHERE id_organizacion = %s
            AND active = 1
            AND existe = 1
            ORDER BY id
        """, (id_organization,))
        results = cursor.fetchall()
        # Generar nombre de carpeta basado en ID
        for prj in results:
            prj['project_id'] = prj['id']
            prj['project_folder'] = f"PRJ{prj['id']:05d}"
        # Volver a la base de datos core
        cursor.execute("USE myllm_core_db")
        return results


def get_versions(conn, id_project: int) -> list[dict[str, Any]]:
    """Obtiene todas las versiones de un proyecto."""
    with conn.cursor() as cursor:
        # Cambiar a la base de datos de proyectos
        cursor.execute("USE myllm_projects_db")
        cursor.execute("""
            SELECT id, id_proyecto, id_version, descripcion
            FROM versiones
            WHERE id_proyecto = %s
            ORDER BY id_version
        """, (id_project,))
        results = cursor.fetchall()
        # Generar nombre de carpeta basado en id_version
        for ver in results:
            ver['version_folder'] = f"v{ver['id_version']:03d}"
            ver['version_name'] = ver['version_folder']
        # Volver a la base de datos core
        cursor.execute("USE myllm_core_db")
        return results


def get_base_path() -> Path:
    """Obtiene la ruta base de almacenamiento desde env.yaml."""
    env_yaml_path = Path(__file__).parent.parent / "infrastructure" / "environments" / "macbook" / "env.yaml"

    with open(env_yaml_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("fmanagement_base_path:"):
                path_str = line.split(":", 1)[1].strip()
                return Path(os.path.expanduser(path_str))

    raise ValueError("fmanagement_base_path not found in env.yaml")


def create_folder_structure(base_path: Path, org_folder: str, prj_folder: str, version_folder: str, dry_run: bool = False):
    """Crea la estructura de carpetas para una versión.

    Estructura:
    base_path/
        ORG####/
            PRJ#####/
                v###/
                    images/
                    text/
    """
    version_path = base_path / org_folder / prj_folder / version_folder

    if version_path.exists():
        return False, "Ya existe"

    if dry_run:
        return True, "Se creará (dry-run)"

    # Crear carpeta de versión
    version_path.mkdir(parents=True, exist_ok=True)

    # Crear subcarpetas estándar
    (version_path / "images").mkdir(exist_ok=True)
    (version_path / "text").mkdir(exist_ok=True)

    # Crear archivo README.md con información
    readme_content = f"""# Versión {version_folder}

Esta carpeta contiene los archivos de la versión {version_folder}.

## Estructura

- `images/` - Archivos de imagen (PNG, JPG, etc.)
- `text/` - Archivos de texto (TXT, MD, etc.)

## Metadata

- Organización: {org_folder}
- Proyecto: {prj_folder}
- Versión: {version_folder}
- Creado por: sync_filesystem_with_database.py
"""
    (version_path / "README.md").write_text(readme_content)

    return True, "Creado"


def main():
    """Ejecuta la sincronización."""
    dry_run = "--dry-run" in sys.argv

    print("\n" + "=" * 70)
    print("SINCRONIZACIÓN FILESYSTEM ↔ BASE DE DATOS")
    if dry_run:
        print("(MODO DRY-RUN - NO SE CREARÁ NADA)")
    print("=" * 70 + "\n")

    # Obtener ruta base
    try:
        base_path = get_base_path()
        print_step(f"Ruta base: {base_path}", "info")
    except Exception as e:
        print_step(f"Error obteniendo ruta base: {e}", "error")
        return 1

    # Verificar que la ruta base existe
    if not base_path.exists():
        print_step(f"La ruta base no existe: {base_path}", "error")
        print_step("Creando ruta base...", "info")
        if not dry_run:
            base_path.mkdir(parents=True, exist_ok=True)
            print_step("Ruta base creada", "ok")
        else:
            print_step("Se crearía la ruta base (dry-run)", "warning")

    # Conectar a la base de datos
    print_step("\nConectando a la base de datos...", "info")
    try:
        conn = get_db_connection()
        print_step("Conectado a MariaDB", "ok")
    except Exception as e:
        print_step(f"Error conectando a la base de datos: {e}", "error")
        return 1

    try:
        # Obtener todas las organizaciones
        organizations = get_organizations(conn)
        print_step(f"\nEncontradas {len(organizations)} organizaciones", "info")

        total_created = 0
        total_existing = 0
        total_errors = 0

        for org in organizations:
            org_id = org["organization_id"]
            org_folder = org["organization_folder"]

            print(f"\n{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
            print(f"{CYAN}Organización: {org['organization_name']} (ID: {org_id}){RESET}")
            print(f"{CYAN}Carpeta: {org_folder}{RESET}")
            print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")

            # Obtener proyectos de la organización
            projects = get_projects(conn, org_id)
            print_step(f"Proyectos: {len(projects)}", "info")

            for project in projects:
                project_id = project["project_id"]
                project_folder = project["project_folder"]

                print(f"\n  {YELLOW}▸ Proyecto: {project['project_name']} (ID: {project_id}){RESET}")
                print(f"    Carpeta: {project_folder}")

                # Obtener versiones del proyecto
                versions = get_versions(conn, project_id)
                print(f"    Versiones: {len(versions)}")

                for version in versions:
                    version_id = version["id_version"]
                    version_folder = version["version_folder"]

                    # Crear estructura de carpetas
                    try:
                        created, status = create_folder_structure(
                            base_path, org_folder, project_folder, version_folder, dry_run
                        )

                        if created:
                            print_step(f"      {version_folder} (ID: {version_id}) - {status}", "ok")
                            total_created += 1
                        else:
                            print_step(f"      {version_folder} (ID: {version_id}) - {status}", "action")
                            total_existing += 1
                    except Exception as e:
                        print_step(f"      {version_folder} (ID: {version_id}) - ERROR: {e}", "error")
                        total_errors += 1

        # Resumen final
        print("\n" + "=" * 70)
        print("RESUMEN DE SINCRONIZACIÓN")
        print("=" * 70 + "\n")

        print(f"  Total organizaciones procesadas: {len(organizations)}")
        print(f"  Versiones creadas: {GREEN}{total_created}{RESET}")
        print(f"  Versiones existentes: {CYAN}{total_existing}{RESET}")
        print(f"  Errores: {RED}{total_errors}{RESET}")

        if dry_run:
            print(f"\n{YELLOW}⚠ MODO DRY-RUN - No se creó nada realmente{RESET}")
            print(f"{YELLOW}  Ejecuta sin --dry-run para crear las carpetas{RESET}")
        else:
            print(f"\n{GREEN}✓ Sincronización completada{RESET}")

        # Mostrar estructura creada
        if total_created > 0 and not dry_run:
            print("\n" + "=" * 70)
            print("ESTRUCTURA CREADA")
            print("=" * 70 + "\n")
            print(f"Puedes verificar con:")
            print(f"  tree {base_path}")
            print(f"  ls -la {base_path}")

        return 0

    except Exception as e:
        print_step(f"\nError durante la sincronización: {e}", "error")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
