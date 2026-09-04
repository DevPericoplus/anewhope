#!/usr/bin/env python3
"""
Test completo de creación de versiones.

Este test verifica el flujo completo:
1. Login de usuario
2. Creación de versión a través del API
3. Verificación en base de datos
4. Verificación de carpetas en filesystem

Uso:
    python test_create_version_full.py
"""

import os
import sys
from pathlib import Path
from typing import Any

import pymysql
import requests

# Colores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"

from tests.helpers import get_service_urls
_urls = get_service_urls()

# URLs de servicios
MIDDLEWARE_URL = _urls["middleware"]
BACKEND_CORE_URL = _urls["backend_core"]

# Datos de prueba
TEST_USER = "adminone"  # user_id=1, identity_type_id=1 (superadmin), org_id=1
TEST_PASSWORD = "Password01"
TEST_PROJECT_ID = 2  # botweb
TEST_ORG_ID = 1  # myllm


def print_step(step: str, status: str = "info"):
    """Imprime un paso del proceso con formato."""
    color = BLUE if status == "info" else GREEN if status == "ok" else RED if status == "error" else YELLOW if status == "warning" else CYAN
    symbol = "ℹ" if status == "info" else "✓" if status == "ok" else "✗" if status == "error" else "⚠" if status == "warning" else "→"
    print(f"{color}{symbol} {step}{RESET}")


def get_db_connection():
    """Crea conexión a la base de datos del entorno activo."""
    from tests.helpers import get_db_connection as _get_db_connection

    return _get_db_connection(database="myllm_projects_db")


def get_base_path() -> Path:
    """Obtiene la ruta base de almacenamiento del entorno activo."""
    from tests.helpers import load_env_yaml

    data = load_env_yaml()
    path_str = data.get("fmanagement_base_path") or data.get("backend_core_base_storage")
    if not path_str:
        raise ValueError("fmanagement_base_path not found in env.yaml")
    return Path(os.path.expanduser(str(path_str)))


def test_login() -> dict[str, Any] | None:
    """Prueba el login y retorna los tokens."""
    print_step(f"Haciendo login con usuario '{TEST_USER}'...", "info")

    try:
        from tests.helpers import fetch_user_otp

        otp = fetch_user_otp(TEST_USER)
        response = requests.post(
            f"{MIDDLEWARE_URL}/login",
            json={
                "user_name": TEST_USER,
                "password": TEST_PASSWORD,
                "otp": otp,
            },
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            # Añadir user_name al response para usarlo después
            data['user_name'] = TEST_USER
            print_step("Login exitoso", "ok")
            print(f"  • User ID: {data.get('user_id')}")
            print(f"  • Organization ID: {data.get('organization_id')}")
            print(f"  • Identity Type ID: {data.get('identity_type_id')}")
            return data
        else:
            print_step(f"Login falló: {response.status_code}", "error")
            print(f"  Respuesta: {response.text}")
            return None
    except Exception as e:
        print_step(f"Error en login: {e}", "error")
        return None


def get_current_versions(project_id: int) -> list[dict[str, Any]]:
    """Obtiene las versiones actuales de un proyecto."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, id_proyecto, id_version, fecha_lanzamiento, descripcion
                FROM versiones
                WHERE id_proyecto = %s
                ORDER BY id_version
            """, (project_id,))
            return cursor.fetchall()
    finally:
        conn.close()


def create_version(
    project_id: int,
    org_id: int,
    user_data: dict[str, Any]
) -> dict[str, Any] | None:
    """Crea una nueva versión."""
    print_step(f"Creando nueva versión para proyecto {project_id}...", "info")

    # Obtener versiones actuales para calcular el nombre
    current_versions = get_current_versions(project_id)
    next_version_num = len(current_versions) + 1
    version_name = f"V{next_version_num:03d}"

    print(f"  • Versiones actuales: {len(current_versions)}")
    print(f"  • Nueva versión: {version_name}")

    try:
        response = requests.post(
            f"{BACKEND_CORE_URL}/proyectos/{project_id}/versiones/crear-completa",
            headers={
                "Authorization": f"Bearer {user_data['access_token']}",
                "X-Session-Token": user_data['session_token'],
                "Content-Type": "application/json",
            },
            json={
                "id_organizacion": org_id,
                "nombre_version": version_name,
                "user_id": user_data['user_id'],
                "user_name": user_data['user_name'],
                "identity_type_id": user_data['identity_type_id'],
                "descripcion": f"Test version created by test_create_version_full.py",
            },
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()
            print_step("Versión creada exitosamente", "ok")
            print(f"  • Version ID: {data.get('version_id')}")
            print(f"  • Version Folder: {data.get('version_folder')}")
            return data
        else:
            print_step(f"Error al crear versión: {response.status_code}", "error")
            print(f"  Respuesta: {response.text}")
            return None
    except Exception as e:
        print_step(f"Excepción al crear versión: {e}", "error")
        import traceback
        traceback.print_exc()
        return None


def verify_version_in_database(project_id: int, expected_version_id: int) -> bool:
    """Verifica que la versión se haya creado en la base de datos."""
    print_step(f"Verificando versión en base de datos...", "info")

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Verificar en tabla versiones
            cursor.execute("""
                SELECT id, id_proyecto, id_version, fecha_lanzamiento, descripcion
                FROM versiones
                WHERE id_proyecto = %s AND id_version = %s
            """, (project_id, expected_version_id))
            version = cursor.fetchone()

            if not version:
                print_step("Versión NO encontrada en tabla versiones", "error")
                return False

            print_step("Versión encontrada en tabla versiones", "ok")
            print(f"  • ID (autoincrement): {version['id']}")
            print(f"  • ID Proyecto: {version['id_proyecto']}")
            print(f"  • ID Versión: {version['id_version']}")
            print(f"  • Fecha: {version['fecha_lanzamiento']}")

            version_db_id = version['id']

            # estado.id_version es el número de versión (1, 2, 17), no el PK
            cursor.execute("""
                SELECT id, id_organizacion, id_proyecto, id_version
                FROM estado
                WHERE id_proyecto = %s AND id_version = %s
            """, (project_id, expected_version_id))
            estado = cursor.fetchone()

            if estado:
                print_step("Estado inicial creado correctamente", "ok")
                print(f"  • Estado ID: {estado['id']}")
            else:
                print_step("Estado NO encontrado", "error")
                return False

            # Verificar en tabla cambios
            cursor.execute("""
                SELECT id, tipo_cambio, descripcion
                FROM cambios
                WHERE id_version = %s
            """, (version_db_id,))
            cambio = cursor.fetchone()

            if cambio:
                print_step("Evento VERSION_CREADA registrado", "ok")
                print(f"  • Tipo: {cambio['tipo_cambio']}")
            else:
                print_step("Evento NO registrado", "warning")

            return True

    except Exception as e:
        print_step(f"Error verificando BD: {e}", "error")
        return False
    finally:
        conn.close()


def verify_version_in_filesystem(
    org_id: int,
    project_id: int,
    version_id: int
) -> bool:
    """Verifica que la carpeta de versión exista en el filesystem."""
    print_step("Verificando carpeta en filesystem...", "info")

    from tests.helpers import get_org_folder, get_prj_folder, get_ver_folder

    base_path = get_base_path()
    org_folder = get_org_folder(org_id)
    prj_folder = get_prj_folder(project_id)
    version_folder = get_ver_folder(version_id)

    version_path = base_path / org_folder / prj_folder / version_folder

    print(f"  • Ruta esperada: {version_path}")

    from tests.helpers import is_local_storage_path

    if not is_local_storage_path(base_path):
        print_step(
            "Storage no es local (silicon/remoto); se omite comprobación de disco",
            "warning",
        )
        return True

    if not version_path.exists():
        print_step("Carpeta de versión NO existe", "error")
        return False

    print_step("Carpeta de versión existe", "ok")

    # Verificar subcarpetas
    images_path = version_path / "images"
    text_path = version_path / "text"

    checks = []

    if images_path.exists() and images_path.is_dir():
        print_step("  Subcarpeta images/ existe", "ok")
        checks.append(True)
    else:
        print_step("  Subcarpeta images/ NO existe", "error")
        checks.append(False)

    if text_path.exists() and text_path.is_dir():
        print_step("  Subcarpeta text/ existe", "ok")
        checks.append(True)
    else:
        print_step("  Subcarpeta text/ NO existe", "error")
        checks.append(False)

    # Verificar README.md (opcional)
    readme_path = version_path / "README.md"
    if readme_path.exists():
        print_step("  Archivo README.md existe", "action")

    return all(checks)


def cleanup_test_version(
    project_id: int,
    version_id: int,
    org_id: int
) -> bool:
    """Limpia la versión de prueba creada."""
    print_step("Limpiando versión de prueba...", "info")

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Obtener el ID autoincremental
            cursor.execute("""
                SELECT id FROM versiones
                WHERE id_proyecto = %s AND id_version = %s
            """, (project_id, version_id))
            result = cursor.fetchone()

            if not result:
                print_step("Versión no encontrada para limpiar", "warning")
                return False

            version_db_id = result['id']

            # Eliminar de estado (CASCADE lo eliminará de cambios)
            cursor.execute("DELETE FROM estado WHERE id_version = %s", (version_db_id,))
            # Eliminar de cambios
            cursor.execute("DELETE FROM cambios WHERE id_version = %s", (version_db_id,))
            # Eliminar versión
            cursor.execute("DELETE FROM versiones WHERE id = %s", (version_db_id,))

            conn.commit()
            print_step("Versión eliminada de BD", "ok")

            # Eliminar carpeta del filesystem
            from tests.helpers import get_org_folder, get_prj_folder, get_ver_folder

            base_path = get_base_path()
            org_folder = get_org_folder(org_id)
            prj_folder = get_prj_folder(project_id)
            version_folder = get_ver_folder(version_id)
            version_path = base_path / org_folder / prj_folder / version_folder

            if version_path.exists():
                import shutil
                shutil.rmtree(version_path)
                print_step("Carpeta eliminada del filesystem", "ok")

            return True

    except Exception as e:
        print_step(f"Error limpiando: {e}", "error")
        return False
    finally:
        conn.close()


def main():
    """Ejecuta el test completo."""
    print("\n" + "=" * 70)
    print("TEST COMPLETO DE CREACIÓN DE VERSIONES")
    print("=" * 70 + "\n")

    # Paso 1: Login
    print("▶ PASO 1: Login\n")
    user_data = test_login()
    if not user_data:
        print_step("\n❌ Test falló: No se pudo hacer login", "error")
        return 1

    # Obtener versiones actuales
    current_versions = get_current_versions(TEST_PROJECT_ID)
    next_version_id = len(current_versions) + 1

    print(f"\n{CYAN}Proyecto de prueba: PRJ{TEST_PROJECT_ID:05d}{RESET}")
    print(f"{CYAN}Versiones actuales: {len(current_versions)}{RESET}")
    print(f"{CYAN}Siguiente versión: v{next_version_id:03d}{RESET}\n")

    # Paso 2: Crear versión
    print("▶ PASO 2: Crear nueva versión\n")
    result = create_version(TEST_PROJECT_ID, TEST_ORG_ID, user_data)
    if not result or not result.get("success"):
        print_step("\n❌ Test falló: No se pudo crear la versión", "error")
        return 1

    # Paso 3: Verificar en BD
    print("\n▶ PASO 3: Verificar en base de datos\n")
    db_ok = verify_version_in_database(TEST_PROJECT_ID, next_version_id)
    if not db_ok:
        print_step("\n❌ Test falló: Versión no encontrada en BD", "error")
        return 1

    # Paso 4: Verificar en filesystem
    print("\n▶ PASO 4: Verificar en filesystem\n")
    fs_ok = verify_version_in_filesystem(TEST_ORG_ID, TEST_PROJECT_ID, next_version_id)
    if not fs_ok:
        print_step("\n❌ Test falló: Carpeta no encontrada en filesystem", "error")
        return 1

    # Resumen
    print("\n" + "=" * 70)
    print("RESUMEN DEL TEST")
    print("=" * 70 + "\n")

    results = [
        ("Login exitoso", user_data is not None),
        ("Versión creada en BD", db_ok),
        ("Carpeta creada en filesystem", fs_ok),
    ]

    for test_name, passed in results:
        status = "ok" if passed else "error"
        print_step(f"{test_name}: {'✓' if passed else '✗'}", status)

    all_ok = all(passed for _, passed in results)

    if all_ok:
        print_step("\n✅ TODOS LOS TESTS PASARON", "ok")
        print(f"\n{GREEN}La versión v{next_version_id:03d} fue creada correctamente en:{RESET}")
        print(f"  • Base de datos: tabla versiones, estado, cambios")
        from tests.helpers import get_org_folder, get_prj_folder, get_ver_folder

        print(
            f"  • Filesystem: .../external/"
            f"{get_org_folder(TEST_ORG_ID)}/{get_prj_folder(TEST_PROJECT_ID)}/"
            f"{get_ver_folder(next_version_id)}/"
        )

        # Preguntar si limpiar
        print(f"\n{YELLOW}¿Deseas eliminar esta versión de prueba? (s/n):{RESET} ", end="")
        try:
            if sys.stdin.isatty():
                response = input().strip().lower()
                if response == "s":
                    cleanup_test_version(TEST_PROJECT_ID, next_version_id, TEST_ORG_ID)
            else:
                print("sin TTY: se conserva la versión de prueba")
        except (KeyboardInterrupt, EOFError):
            print("\n")

        return 0
    else:
        print_step("\n⚠ ALGUNOS TESTS FALLARON", "warning")
        return 1


if __name__ == "__main__":
    sys.exit(main())
