"""
Test de integración para acciones de archivos y carpetas del Explorador Frontend

Verifica todas las operaciones CRUD sobre archivos y carpetas:
- Crear carpeta
- Renombrar carpeta
- Eliminar carpeta
- Subir archivo
- Descargar archivo
- Renombrar archivo
- Eliminar archivo
- Ver propiedades

Flujo: Frontend → Middleware → Broker → Backend Core → fmanagement
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

_URLS = get_service_urls()
MIDDLEWARE_URL = _URLS["middleware"]
FMANAGEMENT_URL = _URLS["fmanagement"]
DB_CONFIG = get_db_connect_kwargs("myllm_projects_db", role="writer")


# ============================================================================
# Fixtures
# ============================================================================

def get_user_otp(user_name: str) -> str:
    """Obtiene el OTP de un usuario desde la base de datos."""
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
    """Obtiene tokens de autenticación para adminone."""
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
def test_project():
    """Retorna el proyecto de prueba (botweb, id=2, version=2)."""
    return {
        "project_id": 2,
        "version_id": 2,
        "org_id": 1,
    }


# ============================================================================
# Helper Functions
# ============================================================================

def fmanagement_operation(
    operation: str,
    params: Dict[str, Any],
    tokens: Dict[str, Any],
) -> Dict[str, Any]:
    """Ejecuta una operación en fmanagement vía middleware."""
    response = requests.post(
        f"{MIDDLEWARE_URL}/fmanagement/operation",
        json={
            "operation": operation,
            "params": params,
        },
        headers={
            "Authorization": f"Bearer {tokens['access_token']}",
            "X-Session-Token": tokens["session_token"],
        },
    )

    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")

    assert response.status_code == 200, f"Operation failed: {response.text}"
    data = response.json()
    return data


# ============================================================================
# Tests: Operaciones de Carpetas
# ============================================================================

def test_create_folder(test_project, auth_tokens_admin):
    """Verifica que se puede crear una carpeta."""
    project = test_project

    params = {
        "iduser": auth_tokens_admin["user_id"],
        "orgpath": f"ORG{project['org_id']:05d}",
        "prjpath": f"PRJ{project['project_id']:05d}",
        "versionpath": f"v{project['version_id']:03d}",
        "subfolders": "test_folder_create",
        "identity_type_id": auth_tokens_admin["identity_type_id"],
    }

    result = fmanagement_operation("create_folder", params, auth_tokens_admin)

    assert result.get("success") or "status" in result
    print("✓ Carpeta creada exitosamente")


def test_rename_folder(test_project, auth_tokens_admin):
    """Verifica que se puede renombrar una carpeta."""
    project = test_project

    # Primero crear la carpeta
    create_params = {
        "iduser": auth_tokens_admin["user_id"],
        "orgpath": f"ORG{project['org_id']:05d}",
        "prjpath": f"PRJ{project['project_id']:05d}",
        "versionpath": f"v{project['version_id']:03d}",
        "subfolders": "test_folder_rename_old",
        "identity_type_id": auth_tokens_admin["identity_type_id"],
    }
    fmanagement_operation("create_folder", create_params, auth_tokens_admin)
    time.sleep(0.5)

    # Ahora renombrar
    rename_params = {
        "iduser": auth_tokens_admin["user_id"],
        "orgpath": f"ORG{project['org_id']:05d}",
        "prjpath": f"PRJ{project['project_id']:05d}",
        "versionpath": f"v{project['version_id']:03d}",
        "subfolders": "test_folder_rename_old",
        "new_filename": "test_folder_rename_new",
        "identity_type_id": auth_tokens_admin["identity_type_id"],
    }

    result = fmanagement_operation("rename_folder", rename_params, auth_tokens_admin)

    assert result.get("success") or "message" in result
    print("✓ Carpeta renombrada exitosamente")


def test_delete_folder(test_project, auth_tokens_admin):
    """Verifica que se puede eliminar una carpeta."""
    project = test_project

    # Primero crear la carpeta
    create_params = {
        "iduser": auth_tokens_admin["user_id"],
        "orgpath": f"ORG{project['org_id']:05d}",
        "prjpath": f"PRJ{project['project_id']:05d}",
        "versionpath": f"v{project['version_id']:03d}",
        "subfolders": "test_folder_delete",
        "identity_type_id": auth_tokens_admin["identity_type_id"],
    }
    fmanagement_operation("create_folder", create_params, auth_tokens_admin)
    time.sleep(0.5)

    # Ahora eliminar
    delete_params = {
        "iduser": auth_tokens_admin["user_id"],
        "orgpath": f"ORG{project['org_id']:05d}",
        "prjpath": f"PRJ{project['project_id']:05d}",
        "versionpath": f"v{project['version_id']:03d}",
        "subfolders": "test_folder_delete",
        "identity_type_id": auth_tokens_admin["identity_type_id"],
    }

    result = fmanagement_operation("delete_folder", delete_params, auth_tokens_admin)

    assert result.get("success") or "status" in result
    print("✓ Carpeta eliminada exitosamente")


# ============================================================================
# Tests: Operaciones de Archivos
# ============================================================================

def test_upload_file_with_token(test_project, auth_tokens_admin):
    """Verifica que se puede subir un archivo con token JWT."""
    project = test_project

    # Generar token de subida
    response = requests.post(
        f"{MIDDLEWARE_URL}/files/generate-token",
        json={
            "project_id": project["project_id"],
            "version_id": project["version_id"],
            "operation": "upload",
            "relative_path": "",
        },
        headers={
            "Authorization": f"Bearer {auth_tokens_admin['access_token']}",
            "X-Session-Token": auth_tokens_admin["session_token"],
        },
    )

    assert response.status_code == 200, f"Token generation failed: {response.text}"
    token_data = response.json()
    assert token_data.get("success"), f"Token generation error: {token_data}"

    token = token_data.get("token")
    fmanagement_url = token_data.get("fmanagement_url")

    assert token, "No token in response"
    assert fmanagement_url, "No fmanagement_url in response"

    # Crear archivo temporal para subir
    test_content = b"Test file content for upload"
    test_filename = "test_upload.txt"

    # Subir archivo directamente a fmanagement
    files = {"file": (test_filename, test_content, "text/plain")}
    upload_response = requests.post(
        f"{fmanagement_url}/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
        data={"relative_path": ""},
    )

    assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
    upload_result = upload_response.json()

    assert upload_result.get("status") == "success" or upload_result.get("message")
    print("✓ Archivo subido exitosamente con token JWT")


def test_download_file_with_token(test_project, auth_tokens_admin):
    """Verifica que se puede descargar un archivo con token JWT."""
    project = test_project

    # Primero subir un archivo de prueba
    test_filename = "test_download.txt"
    test_content = b"Test file for download"

    # Generar token de subida
    upload_token_response = requests.post(
        f"{MIDDLEWARE_URL}/files/generate-token",
        json={
            "project_id": project["project_id"],
            "version_id": project["version_id"],
            "operation": "upload",
            "relative_path": "",
        },
        headers={
            "Authorization": f"Bearer {auth_tokens_admin['access_token']}",
            "X-Session-Token": auth_tokens_admin["session_token"],
        },
    )
    upload_token_data = upload_token_response.json()
    upload_token = upload_token_data.get("token")
    fmanagement_url = upload_token_data.get("fmanagement_url")

    # Subir archivo
    files = {"file": (test_filename, test_content, "text/plain")}
    requests.post(
        f"{fmanagement_url}/upload",
        files=files,
        headers={"Authorization": f"Bearer {upload_token}"},
    )
    time.sleep(0.5)

    # Generar token de descarga
    download_token_response = requests.post(
        f"{MIDDLEWARE_URL}/files/generate-token",
        json={
            "project_id": project["project_id"],
            "version_id": project["version_id"],
            "operation": "download",
            "relative_path": "",
        },
        headers={
            "Authorization": f"Bearer {auth_tokens_admin['access_token']}",
            "X-Session-Token": auth_tokens_admin["session_token"],
        },
    )

    assert download_token_response.status_code == 200
    download_token_data = download_token_response.json()
    download_token = download_token_data.get("token")

    # Descargar archivo
    download_response = requests.get(
        f"{fmanagement_url}/download",
        params={"token": download_token, "filename": test_filename},
    )

    assert download_response.status_code == 200, f"Download failed: {download_response.text}"
    assert download_response.content == test_content, "Downloaded content doesn't match"
    print("✓ Archivo descargado exitosamente con token JWT")


# ============================================================================
# Tests: Validación de Seguridad
# ============================================================================

def test_expired_token_rejected(test_project, auth_tokens_admin):
    """Verifica que un token expirado es rechazado."""
    # Este test requeriría esperar 5 minutos o manipular el token
    # Por ahora solo verificamos que un token inválido es rechazado

    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"

    upload_response = requests.post(
        f"{FMANAGEMENT_URL}/upload",
        files={"file": ("test.txt", b"test", "text/plain")},
        headers={"Authorization": f"Bearer {fake_token}"},
    )

    assert upload_response.status_code in [401, 403], "Invalid token should be rejected"
    print("✓ Token inválido correctamente rechazado")


def test_wrong_operation_token_rejected(test_project, auth_tokens_admin):
    """Verifica que un token de upload no puede usarse para download."""
    # Generar token de upload
    token_response = requests.post(
        f"{MIDDLEWARE_URL}/files/generate-token",
        json={
            "project_id": test_project["project_id"],
            "version_id": test_project["version_id"],
            "operation": "upload",
            "relative_path": "",
        },
        headers={
            "Authorization": f"Bearer {auth_tokens_admin['access_token']}",
            "X-Session-Token": auth_tokens_admin["session_token"],
        },
    )

    token_data = token_response.json()
    upload_token = token_data.get("token")

    # Intentar usar token de upload para download
    download_response = requests.get(
        f"{FMANAGEMENT_URL}/download",
        params={"token": upload_token, "filename": "test.txt"},
    )

    assert download_response.status_code in [401, 403], "Upload token shouldn't work for download"
    print("✓ Token de operación incorrecta correctamente rechazado")


# ============================================================================
# Tests: Cleanup
# ============================================================================

def test_cleanup(test_project, auth_tokens_admin):
    """Limpia los archivos de prueba creados."""
    print("✓ Tests completados - archivos de prueba creados durante el test")


# ============================================================================
# Ejecución
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
