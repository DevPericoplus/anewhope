"""Tests de sincronización OTP entre JSON y MariaDB."""

import importlib.util
import sys
from pathlib import Path


def _load_env_settings_module() -> object:
    """Carga el módulo de configuración de entorno."""

    module_path = (
        Path(__file__).resolve().parents[2]
        / "2_shared_application/config/env_settings.py"
    )
    spec = importlib.util.spec_from_file_location("env_settings", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar env_settings.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["env_settings"] = module
    spec.loader.exec_module(module)
    return module


def _load_user_domain_module() -> object:
    """Carga el módulo de usuario compartido desde ruta."""

    # Primero cargar las variables de entorno
    env_settings = _load_env_settings_module()
    env_settings.load_env_file()
    
    module_path = (
        Path(__file__).resolve().parents[2]
        / "1_shared_domain/entities/user.py"
    )
    spec = importlib.util.spec_from_file_location("shared_user_domain", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar user.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["shared_user_domain"] = module
    spec.loader.exec_module(module)
    return module


def test_validate_users_otp_sync_ok(monkeypatch):
    """Valida sincronización cuando los OTP coinciden."""

    user_domain = _load_user_domain_module()
    monkeypatch.setattr(user_domain, "_should_sync_users_with_broker", lambda: True)
    monkeypatch.setattr(
        user_domain,
        "_load_users",
        lambda: [{"user_id": 1, "user_otp": "1234"}],
    )
    monkeypatch.setattr(
        user_domain,
        "_fetch_users_from_broker",
        lambda: [{"user_id": 1, "user_otp": "1234"}],
    )
    logs = []
    monkeypatch.setattr(
        user_domain, "_append_frontend_secure_log", lambda message: logs.append(message)
    )

    assert user_domain.validate_users_otp_sync() is True
    assert "Validacion OTP sincronizacion,OK" in logs


def test_validate_users_otp_sync_mismatch(monkeypatch):
    """Detecta discrepancias de OTP entre JSON y DB."""

    user_domain = _load_user_domain_module()
    monkeypatch.setattr(user_domain, "_should_sync_users_with_broker", lambda: True)
    monkeypatch.setattr(
        user_domain,
        "_load_users",
        lambda: [{"user_id": 2, "user_otp": "1111"}],
    )
    monkeypatch.setattr(
        user_domain,
        "_fetch_users_from_broker",
        lambda: [{"user_id": 2, "user_otp": "2222"}],
    )
    logs = []
    monkeypatch.setattr(
        user_domain, "_append_frontend_secure_log", lambda message: logs.append(message)
    )

    assert user_domain.validate_users_otp_sync() is False
    assert any("DESALINEADO" in message for message in logs)
