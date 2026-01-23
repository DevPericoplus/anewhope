"""Creación automática de agentes por proyecto."""

from __future__ import annotations

import importlib.util
import json
import os
import secrets
import string
from pathlib import Path
from typing import Callable

from src.1_shared_domain.entities.agents import AGENT_ROLE_SPECS, build_agent_record


def add_agents_for_project(
    organization_id: int,
    organization_name: str,
    project_name: str,
    users_path: Path | None = None,
    encrypt_password: Callable[[str], str] | None = None,
    otp_generator: Callable[[], str] | None = None,
) -> list[dict[str, object]]:
    """Crea agentes para un proyecto y los persiste en JSON + broker."""

    users_path = users_path or _get_users_file_path()
    users = _load_users(users_path)
    base_user_id = _next_user_id(users)
    admin_user = _get_admin_user(users, organization_id)

    password_encryptor = encrypt_password or _encrypt_password
    otp_generator = otp_generator or _generate_otp

    agents = []
    for index, role_spec in enumerate(AGENT_ROLE_SPECS):
        user_id = base_user_id + index
        plain_password = _generate_secure_password()
        encrypted_password = password_encryptor(plain_password)
        otp_value = otp_generator()
        agents.append(
            build_agent_record(
                user_id=user_id,
                organization_id=organization_id,
                role_spec=role_spec,
                organization_name=organization_name,
                project_name=project_name,
                password_encrypted=encrypted_password,
                otp=otp_value,
                contact_info_source=_get_contact_info(admin_user),
            )
        )

    users.extend(agents)
    _write_users(users_path, users)
    if _should_sync_with_broker():
        _sync_users_to_broker(users)
    return agents


def _get_users_file_path() -> Path:
    """Obtiene la ruta de users.json."""

    return (
        Path(__file__).resolve().parents[2]
        / "2_shared_application"
        / "moks"
        / "users.json"
    )


def _load_users(users_path: Path) -> list[dict[str, object]]:
    """Carga usuarios desde JSON."""

    if not users_path.exists():
        return []
    with users_path.open("r", encoding="utf-8") as file_handler:
        data = json.load(file_handler)
    if not isinstance(data, list):
        raise ValueError("users.json debe ser una lista")
    return data


def _write_users(users_path: Path, users: list[dict[str, object]]) -> None:
    """Guarda usuarios en JSON."""

    users_path.parent.mkdir(parents=True, exist_ok=True)
    with users_path.open("w", encoding="utf-8") as file_handler:
        json.dump(users, file_handler, ensure_ascii=False, indent=2)


def _next_user_id(users: list[dict[str, object]]) -> int:
    """Obtiene el siguiente user_id disponible."""

    existing = [int(user.get("user_id", 0)) for user in users]
    return max(existing, default=0) + 1


def _generate_secure_password(length: int = 12) -> str:
    """Genera una contraseña con reglas de complejidad."""

    if length < 8:
        length = 8
    digits = string.digits
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    special = "@#|.$%&"
    alphabet = digits + lower + upper + special

    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(char in upper for char in password)
            and any(char in digits for char in password)
            and any(char in special for char in password)
        ):
            return password


def _generate_otp() -> str:
    """Genera un OTP de 4 dígitos."""

    return f"{secrets.randbelow(10000):04d}"


def _encrypt_password(password: str) -> str:
    """Cifra la contraseña usando el módulo de seguridad."""

    cipher_module = _load_cipher_module()
    fernet_instance = _load_fernet_instance()
    encrypted = cipher_module.encrypt_value(fernet_instance, password)
    return encrypted.decode("utf-8")


def _load_cipher_module():
    """Carga el módulo de cifrado compartido."""

    module_path = Path(__file__).resolve().parent / "custom_cipher_lib.py"
    spec = importlib.util.spec_from_file_location("custom_cipher_lib", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar custom_cipher_lib")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_fernet_instance():
    """Carga la clave Fernet desde basesecuritypass.json."""

    cipher_module = _load_cipher_module()
    key_path = Path(__file__).resolve().parent / "basesecuritypass.json"
    return cipher_module.load_fernet_key_from_file(key_path)


def _should_sync_with_broker() -> bool:
    """Determina si se debe sincronizar con broker backend."""

    storage_mode = os.environ.get("STORAGE_MODE")
    if storage_mode is None:
        storage_mode = _load_storage_mode_from_protected()
    return storage_mode in {"mock_and_db", "db_only"}


def _load_storage_mode_from_protected() -> str:
    """Obtiene storage_mode desde protected_values.py."""

    try:
        from protected_values import storage_mode  # type: ignore

        return str(storage_mode)
    except Exception:
        return "mock"


def _sync_users_to_broker(users: list[dict[str, object]]) -> None:
    """Envía usuarios al broker backend."""

    import urllib.request

    url = f"{_get_broker_base_url()}/users"
    payload = json.dumps(users).encode("utf-8")
    request = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="PUT"
    )
    with urllib.request.urlopen(request, timeout=10):
        return None


def _get_broker_base_url() -> str:
    """Obtiene la URL base del broker backend."""

    try:
        from protected_values import broker_backend_base_url  # type: ignore
    except Exception:
        broker_backend_base_url = "http://localhost:8008"
    return os.environ.get("BROKER_BACKEND_BASE_URL", broker_backend_base_url).rstrip(
        "/"
    )


def _get_admin_user(
    users: list[dict[str, object]], organization_id: int
) -> dict[str, object] | None:
    """Obtiene el primer administrador de la organización."""

    org_users = [
        user
        for user in users
        if int(user.get("organization_id", 0)) == int(organization_id)
    ]
    admin_users = [
        user
        for user in org_users
        if int(user.get("identity_type_id", 0)) == 2
    ]
    if admin_users:
        return sorted(admin_users, key=lambda entry: int(entry.get("user_id", 0)))[0]
    if org_users:
        return sorted(org_users, key=lambda entry: int(entry.get("user_id", 0)))[0]
    return None


def _get_contact_info(user: dict[str, object] | None) -> dict[str, str]:
    """Obtiene contact_info del usuario admin."""

    if user is None:
        return {}
    contact_info = user.get("contact_info", {})
    if isinstance(contact_info, dict):
        return {key: str(value) for key, value in contact_info.items()}
    return {}
