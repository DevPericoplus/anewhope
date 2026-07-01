"""Utilidades de cifrado de contraseñas para LAIM (Fernet compartido)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_cipher_module():
    """Carga custom_cipher_lib dinámicamente."""
    module_path = Path(__file__).resolve().parent / "custom_cipher_lib.py"
    spec = importlib.util.spec_from_file_location("laim_custom_cipher_lib", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar custom_cipher_lib")
    module = importlib.util.module_from_spec(spec)
    sys.modules["laim_custom_cipher_lib"] = module
    spec.loader.exec_module(module)
    return module


def _load_env_settings():
    """Carga env_settings para obtener fernet_key."""
    module_path = (
        Path(__file__).resolve().parents[1] / "config" / "env_settings.py"
    )
    spec = importlib.util.spec_from_file_location("laim_env_settings_crypto", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar env_settings")
    module = importlib.util.module_from_spec(spec)
    sys.modules["laim_env_settings_crypto"] = module
    spec.loader.exec_module(module)
    return module


def _get_fernet_instance():
    """Obtiene instancia Fernet desde protected_values, env o archivo JSON."""
    from cryptography.fernet import Fernet

    env_settings = _load_env_settings()
    cipher_module = _load_cipher_module()
    fernet_key = env_settings.get_protected_value("fernet_key", "")
    if not fernet_key:
        fernet_key = env_settings.get_env_value("FERNET_KEY", "")
    if fernet_key:
        return Fernet(fernet_key.encode())
    key_path = Path(__file__).resolve().parent / "basesecuritypass.json"
    return cipher_module.load_fernet_key_from_file(key_path)


def encrypt_password(plain_password: str) -> str:
    """Cifra una contraseña en texto plano."""
    cipher_module = _load_cipher_module()
    fernet_instance = _get_fernet_instance()
    encrypted_bytes = cipher_module.encrypt_value(fernet_instance, plain_password)
    return encrypted_bytes.decode("utf-8")


def decrypt_password(encrypted_password: str) -> str:
    """Descifra una contraseña almacenada."""
    cipher_module = _load_cipher_module()
    fernet_instance = _get_fernet_instance()
    decrypted_bytes, _ = cipher_module.decrypt_value(
        fernet_instance, encrypted_password.encode("utf-8")
    )
    if not decrypted_bytes:
        raise ValueError("No se pudo descifrar la contraseña")
    return decrypted_bytes.decode("utf-8")
