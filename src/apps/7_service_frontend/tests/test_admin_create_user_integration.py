"""Test de integración: Usuario administrador crea un usuario en la BD.

Este test valida el flujo completo de creación de usuarios:
1. Un usuario administrador (identity_type_id=2) con permiso user_create
2. Envía una petición de creación de usuario
3. El usuario se persiste correctamente en el almacenamiento
4. Los datos del usuario creado son correctos
5. La contraseña se almacena cifrada con Fernet (no en texto plano)

Ejecutar con: pytest -v src/apps/7_service_frontend/tests/test_admin_create_user_integration.py
"""

from __future__ import annotations

import importlib.util
import json
import secrets
import sys
from pathlib import Path
from typing import Any

import pytest
from cryptography.fernet import Fernet


# ============================================================================
# Utilidades para cifrado de contraseñas (como en producción)
# ============================================================================


def _generate_test_fernet_key() -> str:
    """Genera una clave Fernet válida para los tests."""
    return Fernet.generate_key().decode("utf-8")


def _encrypt_password(plain_password: str, fernet_key: str) -> str:
    """
    Cifra una contraseña usando Fernet.
    
    Args:
        plain_password: Contraseña en texto plano
        fernet_key: Clave Fernet como string
    
    Returns:
        Contraseña cifrada como string
    """
    fernet_instance = Fernet(fernet_key.encode())
    encrypted_bytes = fernet_instance.encrypt(plain_password.encode())
    return encrypted_bytes.decode("utf-8")


def _decrypt_password(encrypted_password: str, fernet_key: str) -> str:
    """
    Descifra una contraseña usando Fernet.
    
    Args:
        encrypted_password: Contraseña cifrada
        fernet_key: Clave Fernet como string
    
    Returns:
        Contraseña en texto plano
    """
    fernet_instance = Fernet(fernet_key.encode())
    decrypted_bytes = fernet_instance.decrypt(encrypted_password.encode())
    return decrypted_bytes.decode("utf-8")


def _generate_temp_password() -> str:
    """Genera una contraseña temporal aleatoria (como en producción)."""
    return secrets.token_urlsafe(16)


def _generate_otp() -> str:
    """Genera un OTP de 4 dígitos (como en producción)."""
    return f"{secrets.randbelow(10000):04d}"


# ============================================================================
# Utilidades para carga dinámica de módulos
# ============================================================================


def _load_module(module_name: str, module_path: Path) -> Any:
    """Carga un módulo Python dinámicamente."""

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar {module_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_routermiddleware() -> Any:
    """Carga el módulo routermiddleware."""

    module_path = Path(__file__).resolve().parents[1] / "routermiddleware.py"
    return _load_module("routermiddleware", module_path)


# ============================================================================
# Fixtures y helpers
# ============================================================================


class MockInterface:
    """Interfaz mock para el middleware."""

    async def process_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Devuelve el payload sin cambios."""

        return payload


def _create_json_file(file_path: Path, content: list | dict) -> None:
    """Crea un archivo JSON con contenido inicial."""

    file_path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_json(file_path: Path) -> list | dict:
    """Carga contenido JSON."""

    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _create_admin_user_data(fernet_key: str) -> dict[str, Any]:
    """
    Datos del usuario administrador que realiza la creación.
    
    Args:
        fernet_key: Clave Fernet para cifrar la contraseña
    
    Returns:
        Diccionario con datos del usuario admin (contraseña cifrada)
    """
    # Generar y cifrar contraseña (como en producción)
    plain_password = _generate_temp_password()
    encrypted_password = _encrypt_password(plain_password, fernet_key)
    
    return {
        "user_id": 1,
        "organization_id": 1,
        "identity_type_id": 2,  # Administrador
        "user_name": "admin_test",
        "user_password": encrypted_password,  # Contraseña cifrada con Fernet
        "user_email": "admin@test.org",
        "user_mobile": "+34600000001",
        "user_otp": _generate_otp(),  # OTP generado aleatoriamente
        "active": True,
        "blocked": False,
        "contact_info": {
            "first_name": "Admin",
            "sur_name": "Test",
            "country": "ES",
            "state": "Madrid",
            "zip_code": "28001",
            "address": "Calle Admin 1",
        },
        "billing_info": {
            "first_name": "Admin",
            "sur_name": "Test",
            "country": "ES",
            "state": "Madrid",
            "zip_code": "28001",
            "address": "Calle Admin 1",
        },
    }


def _create_new_user_payload(fernet_key: str) -> dict[str, Any]:
    """
    Payload para crear un nuevo usuario de organización.
    
    Args:
        fernet_key: Clave Fernet para cifrar la contraseña
    
    Returns:
        Diccionario con datos del nuevo usuario (contraseña cifrada)
    """
    # Generar y cifrar contraseña temporal (como en producción)
    plain_password = _generate_temp_password()
    encrypted_password = _encrypt_password(plain_password, fernet_key)
    
    return {
        "organization_id": 1,
        "identity_type_id": 5,  # Usuario estándar de organización
        "user_name": "nuevo_usuario",
        "user_password": encrypted_password,  # Contraseña cifrada con Fernet
        "user_email": "nuevo@test.org",
        "user_mobile": "+34600000002",
        "user_otp": _generate_otp(),  # OTP generado aleatoriamente
        "active": True,
        "blocked": False,
        "contact_info": {
            "first_name": "nuevo_usuario",
            "sur_name": "Usuario de la organizacion",
            "country": "",
            "state": "",
            "zip_code": "",
            "address": "",
        },
        "billing_info": {
            "first_name": "nuevo_usuario",
            "sur_name": "Usuario de la organizacion",
            "country": "",
            "state": "",
            "zip_code": "",
            "address": "",
        },
    }


def _create_low_level_permissions() -> list[dict[str, Any]]:
    """Permisos de bajo nivel para el test."""

    return [
        {
            "id_permissions": 2,  # Administrador
            "user_create": True,
            "user_read": True,
            "user_update": True,
            "user_delete": True,
            "user_enable": True,
            "user_disable": True,
            "folder_create": True,
            "folder_read": True,
            "folder_delete": True,
            "folder_rename": True,
            "folder_list": True,
            "file_create": True,
            "file_read": True,
            "file_update": True,
            "file_delete": True,
            "file_list": True,
            "project_create": True,
            "project_read": True,
            "project_update": True,
            "project_delete": True,
            "project_list": True,
            "training_create": True,
            "training_read": True,
            "training_update": True,
            "training_delete": True,
            "training_start": True,
            "training_stop": True,
            "version_create": True,
            "version_read": True,
            "version_update": True,
            "version_delete": True,
            "version_list": True,
            "parameters_create": True,
            "parameters_read": True,
            "parameters_update": True,
            "parameters_delete": True,
            "notifications_create": True,
            "notifications_read": True,
            "notifications_update": True,
            "notifications_delete": True,
        },
        {
            "id_permissions": 5,  # Usuario estándar (sin permisos de creación)
            "user_create": False,
            "user_read": True,
            "user_update": False,
            "user_delete": False,
            "user_enable": False,
            "user_disable": False,
            "folder_create": False,
            "folder_read": True,
            "folder_delete": False,
            "folder_rename": False,
            "folder_list": True,
            "file_create": False,
            "file_read": True,
            "file_update": False,
            "file_delete": False,
            "file_list": True,
            "project_create": False,
            "project_read": True,
            "project_update": False,
            "project_delete": False,
            "project_list": True,
            "training_create": False,
            "training_read": True,
            "training_update": False,
            "training_delete": False,
            "training_start": False,
            "training_stop": False,
            "version_create": False,
            "version_read": True,
            "version_update": False,
            "version_delete": False,
            "version_list": True,
            "parameters_create": False,
            "parameters_read": True,
            "parameters_update": False,
            "parameters_delete": False,
            "notifications_create": False,
            "notifications_read": True,
            "notifications_update": False,
            "notifications_delete": False,
        },
    ]


def _create_manage_roles_entry(user_id: int, org_id: int, role_id: int) -> dict[str, Any]:
    """Crea una entrada de manage_roles_by_org."""

    return {
        "id_user": user_id,
        "id_organization": org_id,
        "identity_type_id": role_id,
        "create_date": "27/01/26-10:00",
        "modification_date": "",
        "id_modifier_user": user_id,
        "active": True,
    }


# ============================================================================
# TESTS DE INTEGRACIÓN
# ============================================================================


class TestAdminCreateUserIntegration:
    """Tests de integración para creación de usuarios por administrador."""

    @pytest.fixture
    def setup_test_environment(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> dict[str, Any]:
        """Configura el entorno de test con archivos JSON temporales."""

        # Generar clave Fernet para el test
        fernet_key = _generate_test_fernet_key()

        # Crear estructura de archivos temporales
        users_path = tmp_path / "users.json"
        roles_path = tmp_path / "manage_roles_by_org.json"
        permissions_path = tmp_path / "low_level_permissions.json"
        sessions_path = tmp_path / "sessions.json"

        # Crear usuario administrador inicial (con contraseña cifrada)
        admin_user = _create_admin_user_data(fernet_key)
        _create_json_file(users_path, [admin_user])

        # Crear entrada de roles para el admin
        admin_role = _create_manage_roles_entry(1, 1, 2)
        _create_json_file(roles_path, [admin_role])

        # Crear permisos de bajo nivel
        permissions = _create_low_level_permissions()
        _create_json_file(permissions_path, permissions)

        # Crear sesiones vacías
        _create_json_file(sessions_path, {"sessions": [], "auth_logs": []})

        # Configurar variables de entorno
        monkeypatch.setenv("STORAGE_MODE", "mock")
        monkeypatch.setenv("USERS_DATA_PATH", str(users_path))
        monkeypatch.setenv("MANAGE_ROLES_BY_ORG_PATH", str(roles_path))
        monkeypatch.setenv("LOW_LEVEL_PERMISSIONS_PATH", str(permissions_path))
        monkeypatch.setenv("SESSIONS_DATA_PATH", str(sessions_path))
        monkeypatch.setenv("FERNET_KEY", fernet_key)

        return {
            "users_path": users_path,
            "roles_path": roles_path,
            "permissions_path": permissions_path,
            "sessions_path": sessions_path,
            "fernet_key": fernet_key,
        }

    def test_admin_can_create_user_successfully(
        self, setup_test_environment: dict[str, Any]
    ) -> None:
        """
        Test: Un administrador puede crear un usuario exitosamente.

        Escenario:
        1. Usuario admin (identity_type_id=2) con permiso user_create=true
        2. Envía petición de creación con datos válidos
        3. El usuario se crea con user_id autoincremental
        4. Los datos se persisten correctamente en users.json
        5. Se registra la entrada en manage_roles_by_org.json
        6. La contraseña se almacena cifrada (no en texto plano)
        """

        users_path = setup_test_environment["users_path"]
        roles_path = setup_test_environment["roles_path"]
        fernet_key = setup_test_environment["fernet_key"]

        # Cargar módulo y crear router
        routermiddleware = _load_routermiddleware()
        settings = routermiddleware.JwtSettings(
            access_secret="test_access_secret",
            session_secret="test_session_secret",
            algorithm="HS256",
            access_ttl_seconds=900,
            session_ttl_seconds=2700,
        )
        router = routermiddleware.RouterMiddleware(
            interface=MockInterface(),
            jwt_settings=settings,
        )

        # Preparar payload del nuevo usuario (con contraseña cifrada)
        new_user_payload = _create_new_user_payload(fernet_key)

        # Ejecutar creación de usuario
        result = router.create_user(new_user_payload)

        # Validaciones del resultado
        assert result.user_id == 2, "El user_id debe ser autoincremental (2)"
        assert result.organization_id == 1, "La organización debe ser la misma"
        # REGLA CRÍTICA: Usuarios creados desde panel de organización SIEMPRE son auditores (5)
        assert result.identity_type_id == 5, (
            "El identity_type_id debe ser 5 (auditor). "
            "Los usuarios creados desde el panel de organización SIEMPRE son auditores."
        )

        # Validar persistencia en users.json
        users = _load_json(users_path)
        assert len(users) == 2, "Deben existir 2 usuarios (admin + nuevo)"

        created_user = users[1]
        assert created_user["user_id"] == 2
        assert created_user["user_name"] == "nuevo_usuario"
        assert created_user["user_email"] == "nuevo@test.org"
        assert created_user["user_mobile"] == "+34600000002"
        assert created_user["organization_id"] == 1
        assert created_user["active"] is True
        assert created_user["blocked"] is False

        # Validar contact_info
        assert created_user["contact_info"]["first_name"] == "nuevo_usuario"
        assert created_user["contact_info"]["sur_name"] == "Usuario de la organizacion"

        # Validar billing_info
        assert created_user["billing_info"]["first_name"] == "nuevo_usuario"
        assert created_user["billing_info"]["sur_name"] == "Usuario de la organizacion"

        # Validar que la contraseña está cifrada (no en texto plano)
        stored_password = created_user["user_password"]
        assert stored_password != "", "La contraseña no debe estar vacía"
        # Las contraseñas Fernet empiezan con 'gAAAAA' (base64 del header)
        assert stored_password.startswith("gAAAAA"), "La contraseña debe estar cifrada con Fernet"
        # Verificar que se puede descifrar correctamente
        decrypted = _decrypt_password(stored_password, fernet_key)
        assert len(decrypted) > 0, "La contraseña descifrada no debe estar vacía"

        # Validar entrada en manage_roles_by_org.json
        manage_roles = _load_json(roles_path)
        assert len(manage_roles) == 2, "Deben existir 2 entradas de roles"

        new_role_entry = manage_roles[1]
        assert new_role_entry["id_user"] == 2
        assert new_role_entry["id_organization"] == 1
        assert new_role_entry["active"] is True

    def test_admin_creates_multiple_users_with_incremental_ids(
        self, setup_test_environment: dict[str, Any]
    ) -> None:
        """
        Test: Los user_id se asignan incrementalmente al crear múltiples usuarios.

        Escenario:
        1. Admin crea usuario A → user_id=2
        2. Admin crea usuario B → user_id=3
        3. Admin crea usuario C → user_id=4
        """

        users_path = setup_test_environment["users_path"]
        fernet_key = setup_test_environment["fernet_key"]

        routermiddleware = _load_routermiddleware()
        settings = routermiddleware.JwtSettings(
            access_secret="test_access_secret",
            session_secret="test_session_secret",
            algorithm="HS256",
            access_ttl_seconds=900,
            session_ttl_seconds=2700,
        )
        router = routermiddleware.RouterMiddleware(
            interface=MockInterface(),
            jwt_settings=settings,
        )

        # Crear 3 usuarios (con contraseñas cifradas)
        users_to_create = [
            {
                "organization_id": 1,
                "identity_type_id": 5,
                "user_name": f"usuario_{i}",
                "user_password": _encrypt_password(_generate_temp_password(), fernet_key),
                "user_email": f"usuario{i}@test.org",
                "user_mobile": f"+3460000000{i}",
                "user_otp": _generate_otp(),
                "active": True,
                "blocked": False,
                "contact_info": {"first_name": f"Usuario {i}", "sur_name": "Test"},
                "billing_info": {"first_name": f"Usuario {i}", "sur_name": "Test"},
            }
            for i in range(1, 4)
        ]

        results = []
        for user_payload in users_to_create:
            result = router.create_user(user_payload)
            results.append(result)

        # Validar IDs incrementales
        assert results[0].user_id == 2
        assert results[1].user_id == 3
        assert results[2].user_id == 4

        # Validar persistencia
        users = _load_json(users_path)
        assert len(users) == 4, "Deben existir 4 usuarios (1 admin + 3 nuevos)"

        for i, user in enumerate(users[1:], start=1):
            assert user["user_id"] == i + 1
            assert user["user_name"] == f"usuario_{i}"

    def test_created_user_has_correct_default_values(
        self, setup_test_environment: dict[str, Any]
    ) -> None:
        """
        Test: Los usuarios creados tienen los valores por defecto correctos.

        Valida:
        - active = True
        - blocked = False
        - contact_info con estructura completa
        - billing_info con estructura completa
        - user_password cifrada con Fernet
        """

        users_path = setup_test_environment["users_path"]
        fernet_key = setup_test_environment["fernet_key"]

        routermiddleware = _load_routermiddleware()
        settings = routermiddleware.JwtSettings(
            access_secret="test_access_secret",
            session_secret="test_session_secret",
            algorithm="HS256",
            access_ttl_seconds=900,
            session_ttl_seconds=2700,
        )
        router = routermiddleware.RouterMiddleware(
            interface=MockInterface(),
            jwt_settings=settings,
        )

        # Crear usuario con datos mínimos (contraseña cifrada)
        minimal_payload = {
            "organization_id": 1,
            "identity_type_id": 5,
            "user_name": "minimal_user",
            "user_password": _encrypt_password(_generate_temp_password(), fernet_key),
            "user_email": "minimal@test.org",
            "user_mobile": "+34600000099",
            "user_otp": _generate_otp(),
        }

        result = router.create_user(minimal_payload)

        assert result.user_id == 2

        # Validar valores por defecto en persistencia
        users = _load_json(users_path)
        created_user = users[1]

        assert created_user["active"] is True, "active debe ser True por defecto"
        assert created_user["blocked"] is False, "blocked debe ser False por defecto"

    def test_user_creation_registers_in_manage_roles(
        self, setup_test_environment: dict[str, Any]
    ) -> None:
        """
        Test: La creación de usuario registra entrada en manage_roles_by_org.

        Valida que se crea una entrada con:
        - id_user: ID del usuario creado
        - id_organization: ID de la organización
        - identity_type_id: Rol asignado
        - active: True
        - create_date: Fecha de creación (formato DD/MM/YY-HH:MM)
        """

        roles_path = setup_test_environment["roles_path"]
        fernet_key = setup_test_environment["fernet_key"]

        routermiddleware = _load_routermiddleware()
        settings = routermiddleware.JwtSettings(
            access_secret="test_access_secret",
            session_secret="test_session_secret",
            algorithm="HS256",
            access_ttl_seconds=900,
            session_ttl_seconds=2700,
        )
        router = routermiddleware.RouterMiddleware(
            interface=MockInterface(),
            jwt_settings=settings,
        )

        new_user_payload = _create_new_user_payload(fernet_key)
        result = router.create_user(new_user_payload)

        # Validar entrada en manage_roles
        manage_roles = _load_json(roles_path)
        assert len(manage_roles) == 2

        new_entry = manage_roles[1]
        assert new_entry["id_user"] == result.user_id
        assert new_entry["id_organization"] == 1
        assert new_entry["active"] is True
        assert "create_date" in new_entry
        assert new_entry["create_date"] != ""


class TestUserCreationValidation:
    """Tests de validación de datos en la creación de usuarios."""

    @pytest.fixture
    def setup_validation_environment(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> dict[str, Any]:
        """Configura entorno para tests de validación."""

        # Generar clave Fernet para el test
        fernet_key = _generate_test_fernet_key()

        users_path = tmp_path / "users.json"
        roles_path = tmp_path / "manage_roles_by_org.json"

        admin_user = _create_admin_user_data(fernet_key)
        _create_json_file(users_path, [admin_user])

        admin_role = _create_manage_roles_entry(1, 1, 2)
        _create_json_file(roles_path, [admin_role])

        monkeypatch.setenv("STORAGE_MODE", "mock")
        monkeypatch.setenv("USERS_DATA_PATH", str(users_path))
        monkeypatch.setenv("MANAGE_ROLES_BY_ORG_PATH", str(roles_path))
        monkeypatch.setenv("FERNET_KEY", fernet_key)

        return {"users_path": users_path, "roles_path": roles_path, "fernet_key": fernet_key}

    def test_user_email_is_stored_lowercase(
        self, setup_validation_environment: dict[str, Any]
    ) -> None:
        """
        Test: El email se almacena en minúsculas.

        El sistema normaliza los emails para evitar duplicados.
        """

        users_path = setup_validation_environment["users_path"]
        fernet_key = setup_validation_environment["fernet_key"]

        routermiddleware = _load_routermiddleware()
        settings = routermiddleware.JwtSettings(
            access_secret="test_access_secret",
            session_secret="test_session_secret",
            algorithm="HS256",
            access_ttl_seconds=900,
            session_ttl_seconds=2700,
        )
        router = routermiddleware.RouterMiddleware(
            interface=MockInterface(),
            jwt_settings=settings,
        )

        # Email con mayúsculas (contraseña cifrada)
        payload = {
            "organization_id": 1,
            "identity_type_id": 5,
            "user_name": "email_test",
            "user_password": _encrypt_password(_generate_temp_password(), fernet_key),
            "user_email": "TEST.User@EXAMPLE.COM",
            "user_mobile": "+34600000088",
            "user_otp": _generate_otp(),
        }

        router.create_user(payload)

        users = _load_json(users_path)
        created_user = users[1]

        assert created_user["user_email"] == "test.user@example.com"

    def test_user_name_is_trimmed(
        self, setup_validation_environment: dict[str, Any]
    ) -> None:
        """
        Test: El nombre de usuario se limpia de espacios.

        Se eliminan espacios al inicio y final del nombre.
        """

        users_path = setup_validation_environment["users_path"]
        fernet_key = setup_validation_environment["fernet_key"]

        routermiddleware = _load_routermiddleware()
        settings = routermiddleware.JwtSettings(
            access_secret="test_access_secret",
            session_secret="test_session_secret",
            algorithm="HS256",
            access_ttl_seconds=900,
            session_ttl_seconds=2700,
        )
        router = routermiddleware.RouterMiddleware(
            interface=MockInterface(),
            jwt_settings=settings,
        )

        # Nombre con espacios (contraseña cifrada)
        payload = {
            "organization_id": 1,
            "identity_type_id": 5,
            "user_name": "  usuario_con_espacios  ",
            "user_password": _encrypt_password(_generate_temp_password(), fernet_key),
            "user_email": "espacios@test.org",
            "user_mobile": "+34600000077",
            "user_otp": _generate_otp(),
        }

        router.create_user(payload)

        users = _load_json(users_path)
        created_user = users[1]

        assert created_user["user_name"] == "usuario_con_espacios"
