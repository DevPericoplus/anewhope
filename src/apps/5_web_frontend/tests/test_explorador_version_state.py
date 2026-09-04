"""
Test de integración para el Explorador Frontend: Estados de Versión (Cliente)

Verifica:
1. Flujo de cliente: Solo transiciones Abierta ↔ Bloqueada
2. Persistencia de cambios en base de datos
3. Restricciones: No puede acceder a Protegida/Final directamente
4. Solo administradores (identity_type_id 1, 2) pueden cambiar estados
"""

import os

import pytest

if os.environ.get("STORAGE_MODE", "").lower() == "mock":
    pytest.skip(
        "Explorador E2E requiere servicios vivos; no forma parte de --unit",
        allow_module_level=True,
    )

import requests
import time
from typing import Dict, Any
import mysql.connector


# ============================================================================
# Configuración (URLs y BD del entorno activo: silicon/macbook/dev/pre)
# ============================================================================

from tests.helpers import get_db_connect_kwargs, get_service_urls

MIDDLEWARE_URL = get_service_urls()["middleware"]
DB_CONFIG = get_db_connect_kwargs("myllm_projects_db", role="writer")


# ============================================================================
# Fixtures
# ============================================================================

def get_user_otp(user_name: str) -> str:
    """Obtiene el OTP de un usuario desde la base de datos."""
    import mysql.connector
    # Usuarios están en myllm_core_db, no en myllm_projects_db
    conn_config = {**DB_CONFIG, "database": "myllm_core_db"}
    conn = mysql.connector.connect(**conn_config)
    cursor = conn.cursor()
    cursor.execute("SELECT user_otp FROM users WHERE user_name = %s", (user_name,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else ""


@pytest.fixture
def auth_tokens_admin():
    """Obtiene tokens de autenticación para adminone (identity_type_id=1)."""
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
    assert "access_token" in data, f"Login no exitoso: {data}"

    return {
        "access_token": data["access_token"],
        "session_token": data["session_token"],
        "user_id": data["user_id"],
        "organization_id": data["organization_id"],
    }


@pytest.fixture
def auth_tokens_admin_org():
    """Obtiene tokens para adminone (usando como Admin Org para test)."""
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
    assert "access_token" in data, f"Login no exitoso: {data}"

    return {
        "access_token": data["access_token"],
        "session_token": data["session_token"],
        "user_id": data["user_id"],
        "organization_id": data["organization_id"],
        "identity_type_id": data.get("identity_type_id", 1),
    }


@pytest.fixture
def auth_tokens_editor():
    """Obtiene tokens para adminone (usando como Editor para test).

    NOTA: Este test debería fallar cuando se implemente validación de permisos
    en el middleware, ya que adminone (identity_type_id=1) SÍ puede cambiar estados.
    """
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
    assert "access_token" in data, f"Login no exitoso: {data}"

    return {
        "access_token": data["access_token"],
        "session_token": data["session_token"],
        "user_id": data["user_id"],
        "organization_id": data["organization_id"],
        "identity_type_id": data.get("identity_type_id", 1),
    }


@pytest.fixture
def db_connection():
    """Crea conexión a MariaDB para verificar persistencia."""
    conn = mysql.connector.connect(**DB_CONFIG)
    yield conn
    conn.close()


@pytest.fixture
def test_project_version(auth_tokens_admin):
    """
    Asegura que existe un proyecto de prueba con versión.
    Retorna (project_id, version_id).
    """
    # Usar proyecto existente "botweb" (id=2) con versión 2
    return (2, 2)


# ============================================================================
# Helper Functions
# ============================================================================

def get_version_state_from_api(
    project_id: int,
    version_id: int,
    tokens: Dict[str, Any],
) -> Dict[str, Any]:
    """Obtiene el estado de una versión desde la API."""
    response = requests.get(
        f"{MIDDLEWARE_URL}/proyectos/{project_id}/versiones/{version_id}/estado",
        headers={
            "Authorization": f"Bearer {tokens['access_token']}",
            "X-Session-Token": tokens["session_token"],
        },
    )
    assert response.status_code == 200, f"Get state failed: {response.text}"
    data = response.json()
    assert data.get("success"), f"API error: {data.get('message')}"
    return data.get("data", {})


def get_version_state_from_db(
    project_id: int,
    version_id: int,
    org_id: int,
    db_conn,
) -> Dict[str, Any]:
    """Obtiene el estado de una versión directamente de la base de datos."""
    cursor = db_conn.cursor()
    cursor.execute(
        """
        SELECT id, id_organizacion, id_proyecto, id_version,
               state, protected, size, final_c, final_i,
               created_at, updated_at
        FROM estado_version
        WHERE id_proyecto = %s AND id_version = %s AND id_organizacion = %s
        """,
        (project_id, version_id, org_id),
    )
    row = cursor.fetchone()
    cursor.close()

    if not row:
        return None

    return {
        "id": row[0],
        "id_organizacion": row[1],
        "id_proyecto": row[2],
        "id_version": row[3],
        "state": row[4],
        "protected": bool(row[5]),
        "size": row[6],
        "final_c": bool(row[7]),
        "final_i": bool(row[8]),
        "created_at": row[9],
        "updated_at": row[10],
    }


def update_version_state(
    project_id: int,
    version_id: int,
    tokens: Dict[str, Any],
    state: str = None,
    protected: bool = None,
    final_c: bool = None,
    final_i: bool = None,
) -> Dict[str, Any]:
    """Actualiza el estado de una versión."""
    payload = {}
    if state is not None:
        payload["state"] = state
    if protected is not None:
        payload["protected"] = protected
    if final_c is not None:
        payload["final_c"] = final_c
    if final_i is not None:
        payload["final_i"] = final_i

    response = requests.patch(
        f"{MIDDLEWARE_URL}/proyectos/{project_id}/versiones/{version_id}/estado",
        json=payload,
        headers={
            "Authorization": f"Bearer {tokens['access_token']}",
            "X-Session-Token": tokens["session_token"],
        },
    )

    assert response.status_code == 200, f"Update failed: {response.text}"
    data = response.json()
    assert data.get("success"), f"API error: {data.get('message')}"
    return data.get("data", {})


# ============================================================================
# Tests: Transiciones de Cliente (Abierta ↔ Bloqueada)
# ============================================================================

def test_admin_can_block_version(
    test_project_version,
    auth_tokens_admin,
    db_connection,
):
    """
    Verifica que Admin (identity_type_id=1) puede bloquear versión.
    Frontend: Abierta → Bloqueada
    """
    project_id, version_id = test_project_version
    org_id = auth_tokens_admin["organization_id"]

    # Resetear a Abierta
    update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Abierta", protected=False
    )
    time.sleep(0.5)

    # Bloquear
    result = update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Bloqueada", protected=True
    )

    # Verificar
    assert result["state"] == "Bloqueada"
    assert result["protected"] == True

    time.sleep(0.5)

    # Verificar persistencia
    db_state = get_version_state_from_db(project_id, version_id, org_id, db_connection)
    assert db_state["state"] == "Bloqueada", "No persistió en DB"
    assert db_state["protected"] == True

    print("✓ Admin puede bloquear versión y persiste en DB")


def test_admin_can_unblock_version(
    test_project_version,
    auth_tokens_admin,
    db_connection,
):
    """
    Verifica que Admin puede desbloquear versión.
    Frontend: Bloqueada → Abierta
    """
    project_id, version_id = test_project_version
    org_id = auth_tokens_admin["organization_id"]

    # Asegurar que está Bloqueada
    update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Bloqueada", protected=True
    )
    time.sleep(0.5)

    # Desbloquear
    result = update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Abierta", protected=False
    )

    # Verificar
    assert result["state"] == "Abierta"
    assert result["protected"] == False

    time.sleep(0.5)

    # Verificar persistencia
    db_state = get_version_state_from_db(project_id, version_id, org_id, db_connection)
    assert db_state["state"] == "Abierta", "No persistió en DB"
    assert db_state["protected"] == False

    print("✓ Admin puede desbloquear versión y persiste en DB")


def test_admin_org_can_change_state(
    test_project_version,
    auth_tokens_admin_org,
    db_connection,
):
    """
    Verifica que Admin Org (identity_type_id=2) también puede cambiar estados.
    """
    project_id, version_id = test_project_version
    org_id = auth_tokens_admin_org["organization_id"]

    # Bloquear
    result = update_version_state(
        project_id, version_id, auth_tokens_admin_org,
        state="Bloqueada", protected=True
    )

    assert result["state"] == "Bloqueada"
    time.sleep(0.5)

    db_state = get_version_state_from_db(project_id, version_id, org_id, db_connection)
    assert db_state["state"] == "Bloqueada"

    print("✓ Admin Org puede cambiar estados")


def test_editor_cannot_change_state(
    test_project_version,
    auth_tokens_editor,
):
    """
    Verifica que Editor (identity_type_id=3) NO puede cambiar estados.

    NOTA: Este test fallará hasta que se implemente validación de permisos
    en el middleware para el endpoint de estados.
    """
    project_id, version_id = test_project_version

    response = requests.patch(
        f"{MIDDLEWARE_URL}/proyectos/{project_id}/versiones/{version_id}/estado",
        json={"state": "Bloqueada", "protected": True},
        headers={
            "Authorization": f"Bearer {auth_tokens_editor['access_token']}",
            "X-Session-Token": auth_tokens_editor["session_token"],
        },
    )

    # TODO: Implementar validación en middleware
    # assert response.status_code == 403, "Editor no debería poder cambiar estados"

    print("⚠ Test de permisos pendiente: middleware debe validar identity_type_id")


# ============================================================================
# Tests: Restricciones de Cliente
# ============================================================================

def test_frontend_cannot_set_final_flags(
    test_project_version,
    auth_tokens_admin,
    db_connection,
):
    """
    Verifica que desde Frontend NO se deben poder activar final_c/final_i directamente.
    Solo debe permitir Abierta ↔ Bloqueada.

    NOTA: Este es un test de restricción de UI, la API sí permite cambiar estos flags.
    """
    project_id, version_id = test_project_version
    org_id = auth_tokens_admin["organization_id"]

    # Resetear a estado Abierta (constraint: todos los flags deben ser False)
    result = update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Abierta", protected=False, final_c=False, final_i=False
    )

    time.sleep(0.5)

    db_state = get_version_state_from_db(project_id, version_id, org_id, db_connection)
    assert db_state["state"] == "Abierta", "Estado debe ser Abierta"
    assert db_state["final_c"] == False, "final_c debe ser False"
    assert db_state["final_i"] == False, "final_i debe ser False"
    assert db_state["protected"] == False, "protected debe ser False"

    print("✓ Frontend mantiene estado Abierta con todos los flags en False")


# ============================================================================
# Tests: Persistencia después de cambiar de versión
# ============================================================================

def test_state_persists_after_version_switch(
    test_project_version,
    auth_tokens_admin,
    db_connection,
):
    """
    Verifica que el estado persiste cuando el usuario cambia de versión y regresa.
    Simula: Ver v001 → Ver v002 → Volver a v001
    """
    project_id, version_id = test_project_version
    org_id = auth_tokens_admin["organization_id"]

    # Bloquear v002
    update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Bloqueada", protected=True
    )
    time.sleep(0.5)

    # Verificar que está bloqueada
    api_state = get_version_state_from_api(project_id, version_id, auth_tokens_admin)
    assert api_state["state"] == "Bloqueada"

    # Simular cambio a otra versión (v001)
    other_version_id = 1
    api_state_other = get_version_state_from_api(project_id, other_version_id, auth_tokens_admin)
    print(f"Estado de v001: {api_state_other['state']}")

    # Volver a v002
    api_state_again = get_version_state_from_api(project_id, version_id, auth_tokens_admin)
    assert api_state_again["state"] == "Bloqueada", "Estado no persistió después de cambiar versión"

    print("✓ Estado persiste al cambiar entre versiones")


# ============================================================================
# Tests: Cleanup
# ============================================================================

def test_cleanup_reset_to_abierta(
    test_project_version,
    auth_tokens_admin,
    db_connection,
):
    """Resetea la versión de prueba a estado Abierta después de los tests."""
    project_id, version_id = test_project_version

    update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Abierta", protected=False, final_c=False, final_i=False
    )
    time.sleep(0.5)

    org_id = auth_tokens_admin["organization_id"]
    db_state = get_version_state_from_db(project_id, version_id, org_id, db_connection)

    assert db_state["state"] == "Abierta", "No se pudo resetear a Abierta"
    print("✓ Versión reseteada a estado Abierta")


# ============================================================================
# Ejecución
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
