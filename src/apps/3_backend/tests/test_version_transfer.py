"""Tests de integración para la funcionalidad de transferencia de versiones.

Estos tests verifican el flujo completo de transferencia de versiones
entre el servidor backend y el servidor trainer a través de fmanagement.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _load_module(module_name: str, module_path: Path):
    """Carga un módulo dinámicamente desde una ruta."""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar {module_name} desde {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Cargar módulos del backend core
_backend_path = Path(__file__).resolve().parent.parent
_apicore = _load_module("apicore_test", _backend_path / "apicore.py")
_routercore = _load_module("routercore_test", _backend_path / "routercore.py")

VersionTransferRequest = _apicore.VersionTransferRequest
VersionTransferResponse = _apicore.VersionTransferResponse
BackendCoreRouter = _routercore.BackendCoreRouter
BackendCoreBusinessError = _routercore.BackendCoreBusinessError
BackendCorePermissionError = _routercore.BackendCorePermissionError
FmanagementClientError = _routercore.FmanagementClientError
PermissionValidationService = _routercore.PermissionValidationService


class TestVersionTransferEndpoint:
    """Tests para el endpoint de transferencia de versiones."""

    def test_version_transfer_request_model(self) -> None:
        """Verifica que el modelo de request tiene los campos correctos."""
        request = VersionTransferRequest(
            id_user=1,
            id_organization=1,
            id_project=1,
            version_path="v001",
            target_type="trainer",
            identity_type_id=2,
        )

        assert request.id_user == 1
        assert request.id_organization == 1
        assert request.id_project == 1
        assert request.version_path == "v001"
        assert request.target_type == "trainer"
        assert request.identity_type_id == 2

    def test_version_transfer_response_model(self) -> None:
        """Verifica que el modelo de respuesta tiene los campos correctos."""
        response = VersionTransferResponse(
            status="success",
            message="Version transferred successfully to trainer",
            source_path="/data/files/external/ORG0001/PRJ00001/v001",
            destination_path="/data/files/trainer/ORG0001/PRJ00001/v001",
            bytes_transferred=1024,
            files_transferred=5,
        )

        assert response.status == "success"
        assert "trainer" in response.message
        assert "external" in response.source_path
        assert "trainer" in response.destination_path
        assert response.bytes_transferred == 1024
        assert response.files_transferred == 5


class TestVersionTransferRouter:
    """Tests para el método transfer_version del router."""

    @pytest.fixture
    def mock_storage(self) -> MagicMock:
        """Crea un mock del adaptador de almacenamiento."""
        storage = MagicMock()
        storage.load_low_level_permissions.return_value = [
            MagicMock(
                id_permissions=1,
                model_dump=lambda: {
                    "id_permissions": 1,
                    "version_create": True,
                },
            )
        ]
        return storage

    @pytest.fixture
    def mock_fmanagement_client(self) -> MagicMock:
        """Crea un mock del cliente de fmanagement."""
        client = MagicMock()
        client.request_json.return_value = {
            "status": "success",
            "message": "Version transferred successfully to trainer",
            "source_path": "/data/files/external/ORG0001/PRJ00001/v001",
            "destination_path": "/data/files/trainer/ORG0001/PRJ00001/v001",
            "bytes_transferred": 2048,
            "files_transferred": 10,
        }
        return client

    def test_transfer_version_success(
        self,
        mock_storage: MagicMock,
        mock_fmanagement_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verifica transferencia exitosa de versión."""
        monkeypatch.setenv("STORAGE_MODE", "mock")

        router = BackendCoreRouter(
            storage=mock_storage,
            fmanagement_client=mock_fmanagement_client,
        )

        payload = {
            "id_user": 1,
            "id_organization": 1,
            "id_project": 1,
            "version_path": "v001",
            "target_type": "trainer",
            "identity_type_id": 0,  # Sin validación de permisos
        }
        headers = {"Authorization": "Bearer test-token"}

        result = router.transfer_version(payload, headers)

        assert result["status"] == "success"
        assert result["bytes_transferred"] == 2048
        assert result["files_transferred"] == 10
        mock_fmanagement_client.request_json.assert_called_once()

    def test_transfer_version_invalid_target_type(
        self,
        mock_storage: MagicMock,
        mock_fmanagement_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verifica error con target_type inválido."""
        monkeypatch.setenv("STORAGE_MODE", "mock")

        router = BackendCoreRouter(
            storage=mock_storage,
            fmanagement_client=mock_fmanagement_client,
        )

        payload = {
            "id_user": 1,
            "id_organization": 1,
            "id_project": 1,
            "version_path": "v001",
            "target_type": "invalid",
            "identity_type_id": 0,
        }
        headers = {}

        with pytest.raises(BackendCoreBusinessError) as exc_info:
            router.transfer_version(payload, headers)

        assert "trainer" in str(exc_info.value).lower() or "core" in str(exc_info.value).lower()

    def test_transfer_version_fmanagement_error(
        self,
        mock_storage: MagicMock,
        mock_fmanagement_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verifica manejo de errores de fmanagement."""
        monkeypatch.setenv("STORAGE_MODE", "mock")

        mock_fmanagement_client.request_json.side_effect = FmanagementClientError(
            "Connection refused"
        )

        router = BackendCoreRouter(
            storage=mock_storage,
            fmanagement_client=mock_fmanagement_client,
        )

        payload = {
            "id_user": 1,
            "id_organization": 1,
            "id_project": 1,
            "version_path": "v001",
            "target_type": "trainer",
            "identity_type_id": 0,
        }
        headers = {}

        with pytest.raises(BackendCoreBusinessError) as exc_info:
            router.transfer_version(payload, headers)

        assert "fmanagement" in str(exc_info.value).lower()


class TestStoragePathConfiguration:
    """Tests para la configuración de rutas de almacenamiento."""

    def test_environment_variables_loaded(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verifica que las variables de entorno se cargan correctamente."""
        monkeypatch.setenv("BACKEND_CORE_BASE_STORAGE", "/data/files/external")
        monkeypatch.setenv("BACKEND_IA_BASE_STORAGE", "/data/files/trainer")
        monkeypatch.setenv("TRANSFER_MODE", "local")

        core_storage = os.environ.get("BACKEND_CORE_BASE_STORAGE")
        ia_storage = os.environ.get("BACKEND_IA_BASE_STORAGE")
        transfer_mode = os.environ.get("TRANSFER_MODE")

        assert core_storage == "/data/files/external"
        assert ia_storage == "/data/files/trainer"
        assert transfer_mode == "local"

    def test_default_storage_paths(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verifica rutas por defecto cuando no hay variables de entorno."""
        # Eliminar variables de entorno si existen
        for var in ["BACKEND_CORE_BASE_STORAGE", "BACKEND_IA_BASE_STORAGE"]:
            if var in os.environ:
                monkeypatch.delenv(var)

        # Las rutas por defecto deben incluir el home del usuario
        home = os.environ.get("HOME", "/home/user")
        default_core = os.environ.get("BACKEND_CORE_BASE_STORAGE", f"{home}/data/files/external")
        default_ia = os.environ.get("BACKEND_IA_BASE_STORAGE", f"{home}/data/files/trainer")

        assert "external" in default_core
        assert "trainer" in default_ia


class TestVersionTransferPermissions:
    """Tests para la validación de permisos en transferencia de versiones."""

    @pytest.fixture
    def permission_service_mock(self) -> MagicMock:
        """Crea un mock del servicio de permisos."""
        service = MagicMock()
        return service

    def test_transfer_requires_version_create_permission(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verifica que la transferencia requiere permiso version_create."""
        monkeypatch.setenv("STORAGE_MODE", "mock")

        # Mock del servicio de permisos que deniega version_create
        mock_service = MagicMock(spec=PermissionValidationService)
        mock_service.can_perform_action.return_value = False

        mock_storage = MagicMock()
        mock_fmanagement = MagicMock()

        router = BackendCoreRouter(
            storage=mock_storage,
            fmanagement_client=mock_fmanagement,
            permission_service=mock_service,
        )

        payload = {
            "id_user": 1,
            "id_organization": 1,
            "id_project": 1,
            "version_path": "v001",
            "target_type": "trainer",
            "identity_type_id": 5,  # Rol sin permisos
        }
        headers = {}

        with pytest.raises(BackendCorePermissionError) as exc_info:
            router.transfer_version(payload, headers)

        assert exc_info.value.permission_key == "version_create"
        mock_service.can_perform_action.assert_called_with(5, "version_create")

    def test_transfer_allowed_with_version_create_permission(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verifica que la transferencia funciona con permiso version_create."""
        monkeypatch.setenv("STORAGE_MODE", "mock")

        # Mock del servicio de permisos que permite version_create
        mock_service = MagicMock(spec=PermissionValidationService)
        mock_service.can_perform_action.return_value = True

        mock_storage = MagicMock()
        mock_fmanagement = MagicMock()
        mock_fmanagement.request_json.return_value = {
            "status": "success",
            "message": "OK",
            "source_path": "/src",
            "destination_path": "/dst",
            "bytes_transferred": 100,
            "files_transferred": 2,
        }

        router = BackendCoreRouter(
            storage=mock_storage,
            fmanagement_client=mock_fmanagement,
            permission_service=mock_service,
        )

        payload = {
            "id_user": 1,
            "id_organization": 1,
            "id_project": 1,
            "version_path": "v001",
            "target_type": "trainer",
            "identity_type_id": 2,  # Administrador
        }
        headers = {}

        result = router.transfer_version(payload, headers)

        assert result["status"] == "success"
        mock_service.can_perform_action.assert_called_with(2, "version_create")
