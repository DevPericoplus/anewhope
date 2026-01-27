"""
Implementación del repositorio de usuarios usando JSON como almacenamiento.

Este adaptador implementa el contrato UserRepository definido en interfaces/
y proporciona acceso a datos de usuarios desde el archivo users.json.

Nota: Este módulo reemplaza las funciones que estaban en
1_shared_domain/entities/user.py, siguiendo el principio de
separación de responsabilidades de Clean Architecture.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _load_env_settings_module(module_name: str) -> Any:
    """Carga el módulo de configuración compartida."""

    module_path = (
        Path(__file__).resolve().parents[1] / "config/env_settings.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar el módulo de configuración")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class JsonUserRepository:
    """
    Implementación del repositorio de usuarios usando JSON.
    
    Este adaptador implementa el contrato UserRepository y proporciona
    métodos para acceder y modificar usuarios almacenados en users.json.
    
    Attributes:
        _data_path: Ruta al archivo users.json
        _broker_base_url: URL del broker para sincronización con DB
    """
    
    def __init__(
        self,
        data_path: Path | None = None,
        broker_base_url: str | None = None,
    ) -> None:
        """
        Inicializa el repositorio.
        
        Args:
            data_path: Ruta al archivo JSON. Si es None, usa la ruta por defecto.
            broker_base_url: URL del broker para sincronización.
        """
        self._data_path = data_path or self._get_default_path()
        self._broker_base_url = broker_base_url or self._get_broker_base_url()
        self._logger = logging.getLogger("json_user_repository")
    
    def _get_default_path(self) -> Path:
        """Obtiene la ruta por defecto del archivo de usuarios."""
        return Path(__file__).resolve().parents[1] / "moks/users.json"
    
    def _get_broker_base_url(self) -> str:
        """Obtiene la URL base del broker backend."""
        env_settings = _load_env_settings_module("json_user_repo_env")
        protected_base_url = env_settings.get_protected_value(
            "broker_backend_base_url", "http://localhost:8008"
        )
        return os.environ.get("BROKER_BACKEND_BASE_URL", protected_base_url).rstrip("/")
    
    def _should_sync_with_broker(self) -> bool:
        """Determina si se debe sincronizar con el broker backend."""
        storage_mode = os.environ.get("STORAGE_MODE")
        if storage_mode is None:
            env_settings = _load_env_settings_module("json_user_repo_env_mode")
            storage_mode = env_settings.get_env_value("STORAGE_MODE", "mock")
        return storage_mode in {"mock_and_db", "db_only"}
    
    def _load_users(self) -> list[dict[str, Any]]:
        """Carga los usuarios desde el archivo JSON."""
        if not self._data_path.exists():
            self._logger.warning(f"El archivo de usuarios no existe: {self._data_path}")
            return []
        
        try:
            with self._data_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            self._logger.error(f"Error al cargar usuarios desde {self._data_path}: {e}")
            return []
    
    def _save_users(self, users: list[dict[str, Any]]) -> bool:
        """Guarda los usuarios en el archivo JSON."""
        try:
            self._data_path.parent.mkdir(parents=True, exist_ok=True)
            with self._data_path.open("w", encoding="utf-8") as f:
                json.dump(users, f, indent=2, ensure_ascii=False)
            return True
        except (OSError, TypeError, ValueError) as e:
            self._logger.error(f"Error al guardar usuarios en {self._data_path}: {e}")
            return False
    
    def _request_broker(
        self, method: str, path: str, payload: Any | None = None
    ) -> list[dict[str, Any]]:
        """Ejecuta una petición al broker backend."""
        url = f"{self._broker_base_url}{path}"
        body = None
        headers = {"Content-Type": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                return list(data or [])
        except urllib.error.URLError as exc:
            self._logger.error(f"Error al conectar con broker backend: {exc}")
            return []
        except json.JSONDecodeError:
            self._logger.error("Respuesta del broker backend no es JSON válido")
            return []
    
    def _sync_to_broker(self, users: list[dict[str, Any]]) -> bool:
        """Sincroniza usuarios hacia broker backend."""
        try:
            response = self._request_broker("PUT", "/users", payload=users)
            if response is None:
                return False
            if isinstance(response, dict):
                return response.get("success", False)
            return True
        except Exception as exc:
            self._logger.error(f"Error al sincronizar con broker: {exc}")
            return False
    
    # === Métodos del contrato UserRepository ===
    
    def get_by_id(self, user_id: int) -> dict[str, Any] | None:
        """Obtiene un usuario por su identificador."""
        users = self._load_users()
        for user in users:
            if user.get("user_id") == user_id:
                return user
        return None
    
    def get_by_email(self, user_email: str) -> dict[str, Any] | None:
        """Obtiene un usuario por su email."""
        users = self._load_users()
        if not users:
            return None
        
        normalized_input = user_email.strip().lower()
        for user in users:
            user_email_value = user.get("user_email", "")
            if user_email_value.strip().lower() == normalized_input:
                return user
        return None
    
    def get_by_name(self, user_name: str) -> dict[str, Any] | None:
        """Obtiene un usuario por su nombre de usuario."""
        users = self._load_users()
        if not users:
            return None
        
        normalized_input = user_name.strip().lower()
        for user in users:
            user_name_value = user.get("user_name", "")
            if user_name_value.strip().lower() == normalized_input:
                return user
        return None
    
    def exists_by_email(self, user_email: str) -> bool:
        """Verifica si existe un usuario por email."""
        return self.get_by_email(user_email) is not None
    
    def exists_by_mobile(self, user_mobile: str) -> bool:
        """Verifica si existe un usuario por teléfono."""
        users = self._load_users()
        if not users:
            return False
        
        normalized_input = "".join(c for c in user_mobile.strip() if c.isdigit() or c == "+")
        for user in users:
            user_mobile_value = user.get("user_mobile", "")
            normalized_mobile = "".join(c for c in user_mobile_value.strip() if c.isdigit() or c == "+")
            if normalized_mobile == normalized_input:
                return True
        return False
    
    def exists_by_name(self, user_name: str) -> bool:
        """Verifica si existe un usuario por nombre de usuario."""
        return self.get_by_name(user_name) is not None
    
    def save(self, user_data: dict[str, Any]) -> dict[str, Any] | None:
        """Crea o actualiza un usuario."""
        users = self._load_users()
        user_id = user_data.get("user_id")
        
        if user_id:
            # Actualizar usuario existente
            for i, user in enumerate(users):
                if user.get("user_id") == user_id:
                    users[i] = {**user, **user_data}
                    break
            else:
                # No encontrado, agregar como nuevo
                users.append(user_data)
        else:
            # Nuevo usuario, asignar ID
            existing_ids = [u.get("user_id", 0) for u in users if isinstance(u.get("user_id"), int)]
            next_id = max(existing_ids, default=0) + 1
            user_data["user_id"] = next_id
            users.append(user_data)
        
        # Sincronizar con broker si es necesario
        if self._should_sync_with_broker():
            if not self._sync_to_broker(users):
                self._logger.error("No se pudo sincronizar usuario con broker")
                return None
        
        if self._save_users(users):
            return user_data
        return None
    
    def update_password_and_otp(
        self, user_email: str, new_password: str, new_otp: str
    ) -> bool:
        """Actualiza contraseña y OTP del usuario identificado por email."""
        users = self._load_users()
        normalized_input = user_email.strip().lower()
        user_found = False
        user_id = None
        
        for user in users:
            user_email_value = user.get("user_email", "")
            if user_email_value.strip().lower() == normalized_input:
                user["user_password"] = new_password
                user["user_otp"] = new_otp
                user_id = user.get("user_id")
                user_found = True
                self._logger.info(
                    f"Usuario {user_email} (ID: {user_id}) actualizado: "
                    f"contraseña y OTP modificados"
                )
                break
        
        if not user_found:
            self._logger.warning(f"Usuario con email {user_email} no encontrado")
            return False
        
        # Sincronizar con broker
        if self._should_sync_with_broker():
            max_retries = 3
            sync_success = False
            
            for attempt in range(max_retries):
                if self._sync_to_broker(users):
                    sync_success = True
                    break
                else:
                    if attempt < max_retries - 1:
                        sleep_time = 2 ** attempt
                        self._logger.warning(
                            f"Fallo al sincronizar usuario {user_id} con broker "
                            f"(intento {attempt + 1}/{max_retries}). "
                            f"Reintentando en {sleep_time}s..."
                        )
                        time.sleep(sleep_time)
            
            if not sync_success:
                self._logger.error(
                    f"No se pudo sincronizar usuario {user_id} con broker backend "
                    f"tras {max_retries} intentos."
                )
                return False
        
        return self._save_users(users)
    
    def get_all(self) -> list[dict[str, Any]]:
        """Obtiene todos los usuarios."""
        return self._load_users()
    
    def count(self) -> int:
        """Retorna el número total de usuarios."""
        return len(self._load_users())
    
    def delete(self, user_id: int) -> bool:
        """Elimina un usuario por su identificador."""
        users = self._load_users()
        original_count = len(users)
        users = [u for u in users if u.get("user_id") != user_id]
        
        if len(users) == original_count:
            return False  # No se encontró el usuario
        
        if self._should_sync_with_broker():
            if not self._sync_to_broker(users):
                self._logger.error("No se pudo sincronizar eliminación con broker")
                return False
        
        return self._save_users(users)
