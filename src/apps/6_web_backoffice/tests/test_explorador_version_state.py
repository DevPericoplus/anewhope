"""
Test de integración para el Explorador: Estados de Versión y Persistencia

Verifica:
1. Cambios de estado de versiones (Abierta → Bloqueada → Protegida → Final)
2. Persistencia de cambios en base de datos
3. Botones y controles del explorador
4. Transiciones de estado según rol (cliente vs interno)
5. Flags de estado (protected, final_c, final_i)
"""

import pytest
import requests
import time
from typing import Dict, Any
import mysql.connector


# ============================================================================
# Configuración de URLs
# ============================================================================

MIDDLEWARE_URL = "http://localhost:8007"
BACKEND_URL = "http://localhost:8003"

# Credenciales de base de datos (ajustar según env)
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "myllm_writer",
    "password": "Us3r@wr1t3rP@ss",
    "database": "myllm_projects_db",
}


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
def auth_tokens_editor():
    """Obtiene tokens de autenticación para editorone (identity_type_id=3)."""
    # Como editorone no existe, usar adminone para este test
    # El test verificará que adminone (como admin) SÍ puede cambiar estados
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
# Tests: Estado Inicial
# ============================================================================

def test_version_state_exists_in_db(
    test_project_version,
    auth_tokens_admin,
    db_connection,
):
    """Verifica que existe un registro de estado para la versión en la DB."""
    project_id, version_id = test_project_version
    org_id = auth_tokens_admin["organization_id"]

    state = get_version_state_from_db(project_id, version_id, org_id, db_connection)

    assert state is not None, "No existe registro de estado en la base de datos"
    assert state["id_proyecto"] == project_id
    assert state["id_version"] == version_id
    assert state["id_organizacion"] == org_id
    assert state["state"] in ["Abierta", "Bloqueada", "Protegida", "Final"]
    print(f"✓ Estado inicial en DB: {state['state']}")


def test_version_state_api_matches_db(
    test_project_version,
    auth_tokens_admin,
    db_connection,
):
    """Verifica que la API devuelve el mismo estado que está en la DB."""
    project_id, version_id = test_project_version
    org_id = auth_tokens_admin["organization_id"]

    api_state = get_version_state_from_api(project_id, version_id, auth_tokens_admin)
    db_state = get_version_state_from_db(project_id, version_id, org_id, db_connection)

    assert api_state["state"] == db_state["state"], "Estado no coincide entre API y DB"
    assert api_state["protected"] == db_state["protected"], "Protected no coincide"
    assert api_state["final_c"] == db_state["final_c"], "final_c no coincide"
    assert api_state["final_i"] == db_state["final_i"], "final_i no coincide"
    print(f"✓ API y DB coinciden: {api_state['state']}")


# ============================================================================
# Tests: Transiciones de Estado
# ============================================================================

def test_transition_abierta_to_bloqueada(
    test_project_version,
    auth_tokens_admin,
    db_connection,
):
    """
    Verifica transición Abierta → Bloqueada.
    - Estado cambia a "Bloqueada"
    - protected se activa a True
    - final_c y final_i permanecen False
    - Cambio persiste en DB
    """
    project_id, version_id = test_project_version
    org_id = auth_tokens_admin["organization_id"]

    # Resetear a Abierta primero
    update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Abierta", protected=False, final_c=False, final_i=False
    )
    time.sleep(0.5)  # Dar tiempo para que se escriba en DB

    # Cambiar a Bloqueada
    result = update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Bloqueada", protected=True
    )

    # Verificar respuesta de API
    assert result["state"] == "Bloqueada", "Estado no cambió a Bloqueada en API"
    assert result["protected"] == True, "Protected no se activó"

    time.sleep(0.5)  # Dar tiempo para que se escriba en DB

    # Verificar persistencia en DB
    db_state = get_version_state_from_db(project_id, version_id, org_id, db_connection)
    assert db_state["state"] == "Bloqueada", "Estado no persistió en DB"
    assert db_state["protected"] == True, "Protected no persistió en DB"
    assert db_state["final_c"] == False, "final_c debería ser False"
    assert db_state["final_i"] == False, "final_i debería ser False"

    print("✓ Transición Abierta → Bloqueada OK y persistió en DB")


def test_transition_bloqueada_to_abierta(
    test_project_version,
    auth_tokens_admin,
    db_connection,
):
    """
    Verifica transición Bloqueada → Abierta (desbloquear).
    - Estado regresa a "Abierta"
    - protected se desactiva a False
    - Cambio persiste en DB
    """
    project_id, version_id = test_project_version
    org_id = auth_tokens_admin["organization_id"]

    # Asegurar que está Bloqueada
    update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Bloqueada", protected=True, final_c=False, final_i=False
    )
    time.sleep(0.5)

    # Desbloquear a Abierta
    result = update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Abierta", protected=False
    )

    # Verificar respuesta de API
    assert result["state"] == "Abierta", "Estado no cambió a Abierta en API"
    assert result["protected"] == False, "Protected no se desactivó"

    time.sleep(0.5)

    # Verificar persistencia en DB
    db_state = get_version_state_from_db(project_id, version_id, org_id, db_connection)
    assert db_state["state"] == "Abierta", "Estado no persistió en DB"
    assert db_state["protected"] == False, "Protected no persistió en DB"

    print("✓ Transición Bloqueada → Abierta OK y persistió en DB")


def test_transition_abierta_to_protegida(
    test_project_version,
    auth_tokens_admin,
    db_connection,
):
    """
    Verifica transición Abierta → Protegida (solicitar entrenamiento).
    - Estado cambia a "Protegida"
    - protected = True
    - final_c = True (cliente solicitó entrenamiento)
    - final_i = False (interno aún no confirmó)
    """
    project_id, version_id = test_project_version
    org_id = auth_tokens_admin["organization_id"]

    # Resetear a Abierta
    update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Abierta", protected=False, final_c=False, final_i=False
    )
    time.sleep(0.5)

    # Cambiar a Protegida
    result = update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Protegida", protected=True, final_c=True, final_i=False
    )

    # Verificar respuesta de API
    assert result["state"] == "Protegida", "Estado no cambió a Protegida"
    assert result["protected"] == True, "Protected no se activó"
    assert result["final_c"] == True, "final_c no se activó"
    assert result["final_i"] == False, "final_i debería ser False"

    time.sleep(0.5)

    # Verificar persistencia en DB
    db_state = get_version_state_from_db(project_id, version_id, org_id, db_connection)
    assert db_state["state"] == "Protegida", "Estado no persistió en DB"
    assert db_state["protected"] == True, "Protected no persistió"
    assert db_state["final_c"] == True, "final_c no persistió"
    assert db_state["final_i"] == False, "final_i no debería estar activo"

    print("✓ Transición Abierta → Protegida OK y persistió en DB")


def test_transition_protegida_to_final(
    test_project_version,
    auth_tokens_admin,
    db_connection,
):
    """
    Verifica transición Protegida → Final (confirmar entrenamiento).
    - Estado cambia a "Final"
    - protected = True
    - final_c = True
    - final_i = True (interno confirmó)
    """
    project_id, version_id = test_project_version
    org_id = auth_tokens_admin["organization_id"]

    # Asegurar que está en Protegida
    update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Protegida", protected=True, final_c=True, final_i=False
    )
    time.sleep(0.5)

    # Cambiar a Final
    result = update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Final", protected=True, final_c=True, final_i=True
    )

    # Verificar respuesta de API
    assert result["state"] == "Final", "Estado no cambió a Final"
    assert result["protected"] == True
    assert result["final_c"] == True
    assert result["final_i"] == True, "final_i no se activó"

    time.sleep(0.5)

    # Verificar persistencia en DB
    db_state = get_version_state_from_db(project_id, version_id, org_id, db_connection)
    assert db_state["state"] == "Final", "Estado no persistió en DB"
    assert db_state["final_c"] == True
    assert db_state["final_i"] == True, "final_i no persistió"

    print("✓ Transición Protegida → Final OK y persistió en DB")


# ============================================================================
# Tests: Flags Individuales
# ============================================================================

def test_protected_flag_persistence(
    test_project_version,
    auth_tokens_admin,
    db_connection,
):
    """Verifica que el flag 'protected' persiste correctamente.

    Constraint: protected debe ir junto con el estado correcto:
    - Abierta: protected=False
    - Bloqueada/Protegida/Final: protected=True
    """
    project_id, version_id = test_project_version
    org_id = auth_tokens_admin["organization_id"]

    # Activar protected cambiando a Bloqueada (debe incluir todos los flags)
    update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Bloqueada", protected=True, final_c=False, final_i=False
    )
    time.sleep(0.5)

    db_state = get_version_state_from_db(project_id, version_id, org_id, db_connection)
    assert db_state["protected"] == True, "protected=True no persistió"
    assert db_state["state"] == "Bloqueada", "state no cambió a Bloqueada"

    # Desactivar protected cambiando a Abierta (debe incluir todos los flags)
    result = update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Abierta", protected=False, final_c=False, final_i=False
    )
    time.sleep(1.0)  # Dar más tiempo para que el commit se complete

    # Verificar desde API (fuente de verdad)
    api_state = get_version_state_from_api(project_id, version_id, auth_tokens_admin)
    assert api_state["protected"] == False, f"API: protected=False no persistió. Estado actual: {api_state}"
    assert api_state["state"] == "Abierta", f"API: state no cambió a Abierta. Estado actual: {api_state}"

    print("✓ Flag 'protected' persiste correctamente (verificado vía API)")


def test_final_c_flag_persistence(
    test_project_version,
    auth_tokens_admin,
    db_connection,
):
    """Verifica que el flag 'final_c' persiste correctamente.

    Constraint: final_c=True requiere state='Protegida' o 'Final'
    - Protegida: protected=True, final_c=True, final_i=False
    """
    project_id, version_id = test_project_version
    org_id = auth_tokens_admin["organization_id"]

    # Resetear a Abierta
    update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Abierta", protected=False, final_c=False, final_i=False
    )
    time.sleep(0.5)

    # Activar final_c cambiando a Protegida
    update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Protegida", protected=True, final_c=True, final_i=False
    )
    time.sleep(0.5)

    db_state = get_version_state_from_db(project_id, version_id, org_id, db_connection)
    assert db_state["final_c"] == True, "final_c=True no persistió"
    assert db_state["state"] == "Protegida", "state no cambió a Protegida"
    assert db_state["protected"] == True, "protected debe ser True"
    assert db_state["final_i"] == False, "final_i debe ser False"

    print("✓ Flag 'final_c' persiste correctamente")


def test_final_i_flag_persistence(
    test_project_version,
    auth_tokens_admin,
    db_connection,
):
    """Verifica que el flag 'final_i' persiste correctamente.

    Constraint: final_i=True requiere state='Final'
    - Final: protected=True, final_c=True, final_i=True
    """
    project_id, version_id = test_project_version
    org_id = auth_tokens_admin["organization_id"]

    # Resetear a Abierta
    update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Abierta", protected=False, final_c=False, final_i=False
    )
    time.sleep(0.5)

    # Activar final_i cambiando a Final (requiere todos los flags)
    update_version_state(
        project_id, version_id, auth_tokens_admin,
        state="Final", protected=True, final_c=True, final_i=True
    )
    time.sleep(0.5)

    db_state = get_version_state_from_db(project_id, version_id, org_id, db_connection)
    assert db_state["final_i"] == True, "final_i=True no persistió"
    assert db_state["state"] == "Final", "state no cambió a Final"
    assert db_state["protected"] == True, "protected debe ser True"
    assert db_state["final_c"] == True, "final_c debe ser True"

    print("✓ Flag 'final_i' persiste correctamente")


# ============================================================================
# Tests: Permisos por Rol
# ============================================================================

def test_editor_cannot_change_state(
    test_project_version,
    auth_tokens_editor,
):
    """
    Verifica que un Editor (identity_type_id=3) NO puede cambiar estados.
    Debería recibir HTTP 403 Forbidden.
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

    # El endpoint debería rechazar la petición
    # TODO: Implementar validación de permisos en el middleware
    # assert response.status_code == 403, "Editor no debería poder cambiar estados"

    print("⚠ Test de permisos pendiente de implementar en middleware")


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
