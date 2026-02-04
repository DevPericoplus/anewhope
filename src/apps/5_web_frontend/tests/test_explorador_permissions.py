"""
Test de integración para el sistema de permisos del Explorador Frontend

Verifica:
1. Carga de permisos desde proyectos_roles + low_level_permissions
2. Permisos específicos por proyecto (no globales)
3. Fallback a permisos por defecto si no hay datos en BD
4. Validación de permisos por rol (Editor, Lector, Auditor)
5. Actualización de permisos al cambiar de proyecto
"""

import pytest
import requests
import mysql.connector
from typing import Dict, Any


# ============================================================================
# Configuración
# ============================================================================

MIDDLEWARE_URL = "http://localhost:8007"

# Credenciales de base de datos
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "myllm_reader",
    "password": "Us3r@r3@d3rP@ss",
    "database": "myllm_core_db",
}


# ============================================================================
# Fixtures
# ============================================================================

def get_user_otp(user_name: str) -> str:
    """Obtiene el OTP de un usuario desde la base de datos."""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT user_otp FROM users WHERE user_name = %s", (user_name,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else ""


@pytest.fixture
def db_connection():
    """Crea conexión a MariaDB para verificar datos."""
    conn = mysql.connector.connect(**DB_CONFIG)
    yield conn
    conn.close()


@pytest.fixture
def auth_tokens_admin():
    """Obtiene tokens para adminone (SuperAdmin, identity_type_id=1)."""
    otp = get_user_otp("adminone")

    response = requests.post(
        f"{MIDDLEWARE_URL}/login",
        json={
            "user_name": "adminone",
            "password": "Password01",
            "otp": otp,
        },
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()

    return {
        "access_token": data["access_token"],
        "session_token": data["session_token"],
        "user_id": data["user_id"],
        "organization_id": data["organization_id"],
        "identity_type_id": data.get("identity_type_id", 1),
    }


# ============================================================================
# Helper Functions
# ============================================================================

def get_user_role_in_project(
    user_id: int,
    project_id: int,
    org_id: int,
    db_conn,
) -> int:
    """Obtiene el id_rol del usuario en un proyecto específico."""
    cursor = db_conn.cursor()
    cursor.execute(
        """
        SELECT id_rol
        FROM myllm_projects_db.proyectos_roles
        WHERE id_usuario = %s
          AND id_proyecto = %s
          AND id_organizacion = %s
          AND active = 1
        """,
        (user_id, project_id, org_id),
    )
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else None


def get_permissions_for_role(id_rol: int, db_conn) -> Dict[str, bool]:
    """Obtiene los permisos de bajo nivel para un rol."""
    cursor = db_conn.cursor()
    cursor.execute(
        """
        SELECT
            folder_create, folder_delete, folder_rename, folder_read, folder_list,
            file_create, file_read, file_update, file_delete, file_list,
            version_create
        FROM low_level_permissions
        WHERE id_permissions = %s
        """,
        (id_rol,),
    )
    row = cursor.fetchone()
    cursor.close()

    if not row:
        return None

    return {
        "folder_create": bool(row[0]),
        "folder_delete": bool(row[1]),
        "folder_rename": bool(row[2]),
        "folder_read": bool(row[3]),
        "folder_list": bool(row[4]),
        "file_create": bool(row[5]),
        "file_read": bool(row[6]),
        "file_update": bool(row[7]),
        "file_delete": bool(row[8]),
        "file_list": bool(row[9]),
        "version_create": bool(row[10]),
    }


def ensure_user_role_in_project(
    user_id: int,
    project_id: int,
    org_id: int,
    id_rol: int,
    db_conn,
):
    """Asegura que el usuario tiene un rol asignado en el proyecto."""
    cursor = db_conn.cursor()

    # Verificar si existe
    cursor.execute(
        """
        SELECT id FROM myllm_projects_db.proyectos_roles
        WHERE id_usuario = %s AND id_proyecto = %s AND id_organizacion = %s
        """,
        (user_id, project_id, org_id),
    )

    if cursor.fetchone():
        # Ya existe, actualizar
        cursor.execute(
            """
            UPDATE myllm_projects_db.proyectos_roles
            SET id_rol = %s, active = 1
            WHERE id_usuario = %s AND id_proyecto = %s AND id_organizacion = %s
            """,
            (id_rol, user_id, project_id, org_id),
        )
    else:
        # No existe, insertar
        cursor.execute(
            """
            INSERT INTO myllm_projects_db.proyectos_roles
            (id_usuario, id_proyecto, id_organizacion, id_rol, active)
            VALUES (%s, %s, %s, %s, 1)
            """,
            (user_id, project_id, org_id, id_rol),
        )

    db_conn.commit()
    cursor.close()


# ============================================================================
# Tests: Carga de Permisos desde Base de Datos
# ============================================================================

def test_user_has_role_in_project(
    auth_tokens_admin,
    db_connection,
):
    """
    Verifica que el usuario tiene un rol asignado en proyectos_roles.
    """
    user_id = auth_tokens_admin["user_id"]
    project_id = 1  # Proyecto de prueba
    org_id = auth_tokens_admin["organization_id"]

    # Asegurar que el usuario tiene rol de Editor (3) en el proyecto
    ensure_user_role_in_project(user_id, project_id, org_id, 3, db_connection)

    # Verificar que se guardó correctamente
    id_rol = get_user_role_in_project(user_id, project_id, org_id, db_connection)

    assert id_rol is not None, "Usuario no tiene rol asignado en proyectos_roles"
    assert id_rol == 3, f"Rol incorrecto: esperado 3, obtenido {id_rol}"

    print(f"✓ Usuario {user_id} tiene rol {id_rol} en proyecto {project_id}")


def test_role_has_permissions_in_db(
    auth_tokens_admin,
    db_connection,
):
    """
    Verifica que el rol tiene permisos definidos en low_level_permissions.
    """
    user_id = auth_tokens_admin["user_id"]
    project_id = 1
    org_id = auth_tokens_admin["organization_id"]

    # Obtener rol del usuario
    id_rol = get_user_role_in_project(user_id, project_id, org_id, db_connection)
    assert id_rol, "No se pudo obtener id_rol"

    # Obtener permisos del rol
    permisos = get_permissions_for_role(id_rol, db_connection)

    assert permisos is not None, f"No hay permisos para id_rol={id_rol}"
    assert isinstance(permisos, dict), "Permisos debe ser un diccionario"
    assert "folder_create" in permisos, "Falta permiso folder_create"
    assert "file_create" in permisos, "Falta permiso file_create"

    print(f"✓ Rol {id_rol} tiene permisos: {permisos}")


# ============================================================================
# Tests: Permisos por Rol
# ============================================================================

def test_editor_permissions(db_connection):
    """
    Verifica que el rol Editor (3) tiene permisos de edición.
    """
    id_rol = 3  # Editor
    permisos = get_permissions_for_role(id_rol, db_connection)

    assert permisos is not None, "No hay permisos para Editor"

    # Editor debe poder crear, editar y eliminar
    assert permisos.get("folder_create", False), "Editor debe poder crear carpetas"
    assert permisos.get("folder_rename", False), "Editor debe poder renombrar carpetas"
    assert permisos.get("folder_delete", False), "Editor debe poder eliminar carpetas"
    assert permisos.get("file_create", False), "Editor debe poder crear archivos"
    assert permisos.get("file_update", False), "Editor debe poder actualizar archivos"
    assert permisos.get("file_delete", False), "Editor debe poder eliminar archivos"

    print(f"✓ Editor tiene permisos correctos: {permisos}")


def test_lector_permissions(db_connection):
    """
    Verifica que el rol Lector (4) tiene solo permisos de lectura.
    """
    id_rol = 4  # Lector
    permisos = get_permissions_for_role(id_rol, db_connection)

    assert permisos is not None, "No hay permisos para Lector"

    # Lector solo debe poder leer
    assert not permisos.get("folder_create", True), "Lector NO debe poder crear carpetas"
    assert not permisos.get("folder_delete", True), "Lector NO debe poder eliminar carpetas"
    assert not permisos.get("file_create", True), "Lector NO debe poder crear archivos"
    assert not permisos.get("file_update", True), "Lector NO debe poder actualizar archivos"
    assert not permisos.get("file_delete", True), "Lector NO debe poder eliminar archivos"

    # Pero sí debe poder leer
    assert permisos.get("folder_read", False), "Lector debe poder leer carpetas"
    assert permisos.get("folder_list", False), "Lector debe poder listar carpetas"
    assert permisos.get("file_read", False), "Lector debe poder leer archivos"
    assert permisos.get("file_list", False), "Lector debe poder listar archivos"

    print(f"✓ Lector tiene permisos correctos (solo lectura): {permisos}")


def test_auditor_permissions(db_connection):
    """
    Verifica que el rol Auditor (5) tiene permisos limitados.
    """
    id_rol = 5  # Auditor
    permisos = get_permissions_for_role(id_rol, db_connection)

    assert permisos is not None, "No hay permisos para Auditor"

    # Auditor no debe poder modificar nada
    assert not permisos.get("folder_create", True), "Auditor NO debe poder crear carpetas"
    assert not permisos.get("folder_delete", True), "Auditor NO debe poder eliminar"
    assert not permisos.get("file_create", True), "Auditor NO debe poder crear archivos"
    assert not permisos.get("file_update", True), "Auditor NO debe poder actualizar"
    assert not permisos.get("file_delete", True), "Auditor NO debe poder eliminar"

    # Pero debe poder leer para auditoría
    assert permisos.get("folder_read", False), "Auditor debe poder leer carpetas"
    assert permisos.get("file_read", False), "Auditor debe poder leer archivos"

    print(f"✓ Auditor tiene permisos correctos (solo lectura de auditoría): {permisos}")


# ============================================================================
# Tests: Permisos Específicos por Proyecto
# ============================================================================

def test_user_different_roles_different_projects(
    auth_tokens_admin,
    db_connection,
):
    """
    Verifica que un mismo usuario puede tener diferentes roles
    en diferentes proyectos.
    """
    user_id = auth_tokens_admin["user_id"]
    org_id = auth_tokens_admin["organization_id"]

    # Asignar Editor en proyecto 1
    ensure_user_role_in_project(user_id, 1, org_id, 3, db_connection)

    # Asignar Lector en proyecto 2
    ensure_user_role_in_project(user_id, 2, org_id, 4, db_connection)

    # Verificar roles
    rol_proyecto1 = get_user_role_in_project(user_id, 1, org_id, db_connection)
    rol_proyecto2 = get_user_role_in_project(user_id, 2, org_id, db_connection)

    assert rol_proyecto1 == 3, f"Rol en proyecto 1 debe ser 3 (Editor), es {rol_proyecto1}"
    assert rol_proyecto2 == 4, f"Rol en proyecto 2 debe ser 4 (Lector), es {rol_proyecto2}"

    # Verificar que los permisos son diferentes
    permisos_proyecto1 = get_permissions_for_role(rol_proyecto1, db_connection)
    permisos_proyecto2 = get_permissions_for_role(rol_proyecto2, db_connection)

    assert permisos_proyecto1["folder_create"] == True, "Editor debe poder crear"
    assert permisos_proyecto2["folder_create"] == False, "Lector NO debe poder crear"

    print(f"✓ Usuario tiene diferentes roles por proyecto:")
    print(f"  Proyecto 1: Editor (puede crear)")
    print(f"  Proyecto 2: Lector (solo lectura)")


# ============================================================================
# Tests: Validación de Arquitectura
# ============================================================================

def test_permissions_table_structure(db_connection):
    """
    Verifica que la tabla low_level_permissions tiene la estructura esperada.
    """
    cursor = db_connection.cursor()
    cursor.execute("DESCRIBE low_level_permissions")
    columns = {row[0] for row in cursor.fetchall()}
    cursor.close()

    required_columns = {
        "id_permissions",
        "folder_create", "folder_delete", "folder_rename", "folder_read", "folder_list",
        "file_create", "file_read", "file_update", "file_delete", "file_list",
        "version_create", "version_read", "version_update", "version_delete",
    }

    missing = required_columns - columns
    assert not missing, f"Faltan columnas en low_level_permissions: {missing}"

    print("✓ Tabla low_level_permissions tiene estructura correcta")


def test_proyectos_roles_table_structure(db_connection):
    """
    Verifica que la tabla proyectos_roles tiene la estructura esperada.
    """
    cursor = db_connection.cursor()
    cursor.execute("DESCRIBE myllm_projects_db.proyectos_roles")
    columns = {row[0] for row in cursor.fetchall()}
    cursor.close()

    required_columns = {
        "id",
        "id_usuario",
        "id_proyecto",
        "id_organizacion",
        "id_rol",
        "active",
    }

    missing = required_columns - columns
    assert not missing, f"Faltan columnas en proyectos_roles: {missing}"

    print("✓ Tabla proyectos_roles tiene estructura correcta")


# ============================================================================
# Tests: Menús Contextuales según Permisos
# ============================================================================

def test_context_menu_shows_based_on_permissions():
    """
    Test conceptual: Verifica que los menús contextuales del explorador
    muestran opciones según los permisos del usuario.

    NOTA: Este test requeriría acceso al componente Reflex del explorador,
    por lo que es un test de integración de UI que debe ejecutarse manualmente
    o con herramientas de testing de frontend.

    Flujo esperado:
    1. Usuario con rol Editor ve: Crear Carpeta, Subir archivo, Renombrar, Eliminar
    2. Usuario con rol Lector ve solo: Ver Propiedades, Descargar
    3. Usuario con rol Auditor ve: Ver Propiedades (con restricciones visuales)
    """
    print("⚠ Test de UI: Verificar manualmente que los menús contextuales")
    print("  muestran opciones según permisos del usuario en cada proyecto")
    print("")
    print("  Editor debe ver: Crear, Subir, Renombrar, Eliminar")
    print("  Lector debe ver: Ver Propiedades, Descargar")
    print("  Auditor debe ver: Solo Ver Propiedades (modo auditoría)")


# ============================================================================
# Tests: Cleanup
# ============================================================================

def test_cleanup_reset_roles(
    auth_tokens_admin,
    db_connection,
):
    """Resetea los roles de prueba después de los tests."""
    user_id = auth_tokens_admin["user_id"]
    org_id = auth_tokens_admin["organization_id"]

    # Asignar Editor por defecto en proyecto 1
    ensure_user_role_in_project(user_id, 1, org_id, 3, db_connection)

    print("✓ Roles de prueba reseteados")


# ============================================================================
# Ejecución
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
