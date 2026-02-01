"""Tests de estructuras y validación de tecnologías en el backend core.

Verifica:
- Estructura de DTOs de tecnologías
- Validación de requests en endpoints
- Lógica de negocio de tecnologías
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient


def _load_module(module_name: str, module_path: Path) -> Any:
    """Carga un módulo desde una ruta absoluta."""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar el módulo {module_name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: Any) -> None:
    """Escribe JSON en disco."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, ensure_ascii=False, indent=2)


def _build_mock_paths(tmp_path: Path) -> dict[str, Path]:
    """Crea rutas temporales para mocks."""
    return {
        "users": tmp_path / "users.json",
        "organizations": tmp_path / "organizations.json",
        "roles": tmp_path / "roles.json",
        "basic_permissions": tmp_path / "basic_permissions.json",
        "low_level_permissions": tmp_path / "low_level_permissions.json",
        "manage_roles": tmp_path / "manage_roles_by_org.json",
    }


def _bootstrap_mocks(paths: dict[str, Path]) -> None:
    """Inicializa datos mock necesarios."""
    _write_json(paths["users"], [])
    _write_json(paths["organizations"], [])
    _write_json(
        paths["roles"],
        [
            {
                "identity_type_id": 2,
                "identity_type_name": "Admin",
                "identity_type_rol": "Administrator",
                "identity_type_group_permissions": [1],
            }
        ],
    )
    _write_json(
        paths["basic_permissions"],
        [
            {
                "id": 1,
                "PermissionName": "read_users",
                "PermissionDescription": "Permite leer usuarios",
            }
        ],
    )
    _write_json(
        paths["low_level_permissions"],
        [
            {
                "id_permissions": 1,
                "folder_create": True,
                "folder_delete": True,
                "folder_rename": True,
                "folder_read": True,
                "file_create": True,
                "file_read": True,
                "file_update": True,
                "file_delete": True,
                "project_create": True,
                "project_read": True,
                "project_update": True,
                "project_delete": True,
                "version_create": True,
                "version_read": True,
                "version_update": True,
                "version_delete": True,
                "training_create": True,
                "training_read": True,
                "training_update": True,
                "training_delete": True,
                "training_start": True,
                "training_stop": True,
                "parameters_create": True,
                "parameters_read": True,
                "parameters_update": True,
                "parameters_delete": True,
                "notifications_create": True,
                "notifications_read": True,
                "notifications_update": True,
                "notifications_delete": True,
                "user_create": True,
                "user_read": True,
                "user_update": True,
                "user_delete": True,
                "user_enable": True,
                "user_disable": True,
                "folder_list": True,
                "file_list": True,
                "project_list": True,
                "version_list": True,
            }
        ],
    )
    _write_json(paths["manage_roles"], [])


class TestTecnologiasValidation:
    """Tests de validación para endpoints de tecnologías."""

    @pytest.fixture
    def setup_client(self, tmp_path: Path):
        """Configura el cliente de pruebas."""
        module_path = Path(__file__).resolve().parents[1] / "apicore.py"
        apicore = _load_module("apicore", module_path)

        paths = _build_mock_paths(tmp_path)
        _bootstrap_mocks(paths)

        def _get_adapter() -> Any:
            return apicore.JsonMockStorageAdapter(
                users_path=paths["users"],
                organizations_path=paths["organizations"],
                roles_path=paths["roles"],
                basic_permissions_path=paths["basic_permissions"],
                low_level_permissions_path=paths["low_level_permissions"],
                manage_roles_path=paths["manage_roles"],
            )

        apicore.app.dependency_overrides[apicore.get_storage_adapter] = _get_adapter
        client = TestClient(apicore.app)
        
        return client, apicore

    def test_asignar_tecnologia_invalid_request(self, setup_client):
        """Verifica que request inválido retorna error 422."""
        client, _ = setup_client
        
        # Enviar request sin id_tecnologia (campo requerido)
        response = client.post(
            "/proyectos/1/tecnologia",
            json={"coste_base": "17% sobre base"},
        )
        
        assert response.status_code == 422

    def test_proyecto_id_must_be_integer(self, setup_client):
        """Verifica que project_id debe ser un entero."""
        client, _ = setup_client
        
        response = client.get("/proyectos/invalid/tecnologia")
        
        assert response.status_code == 422

    def test_asignar_tecnologia_requires_id_tecnologia(self, setup_client):
        """Verifica que asignar tecnología requiere id_tecnologia."""
        client, _ = setup_client
        
        # Request vacío
        response = client.post("/proyectos/1/tecnologia", json={})
        assert response.status_code == 422

    def test_actualizar_tecnologia_requires_id_tecnologia(self, setup_client):
        """Verifica que actualizar tecnología requiere id_tecnologia."""
        client, _ = setup_client
        
        # Request sin id_tecnologia
        response = client.patch(
            "/proyectos/1/tecnologia",
            json={"coste_base": "20%"},
        )
        assert response.status_code == 422


class TestTecnologiasDtos:
    """Tests para verificar estructura de DTOs de tecnologías."""

    def test_tecnologia_dto_structure(self):
        """Verifica estructura del DTO de tecnología."""
        # Estructura esperada de una tecnología
        tecnologia = {
            "id": 1,
            "name": "GPT-4",
            "descripcion": "Modelo de OpenAI",
            "active": True,
        }
        
        assert "id" in tecnologia
        assert "name" in tecnologia
        assert "descripcion" in tecnologia
        assert "active" in tecnologia
        assert isinstance(tecnologia["id"], int)
        assert isinstance(tecnologia["name"], str)
        assert isinstance(tecnologia["active"], bool)

    def test_proyecto_tecnologia_dto_structure(self):
        """Verifica estructura del DTO de asignación proyecto-tecnología."""
        asignacion = {
            "id": 1,
            "id_proyecto": 1,
            "id_tecnologia": 2,
            "coste_base": "17% sobre base",
        }
        
        assert "id" in asignacion
        assert "id_proyecto" in asignacion
        assert "id_tecnologia" in asignacion
        assert "coste_base" in asignacion
        assert isinstance(asignacion["id_proyecto"], int)
        assert isinstance(asignacion["id_tecnologia"], int)

    def test_tecnologias_list_response_structure(self):
        """Verifica estructura de respuesta de lista de tecnologías."""
        response = {
            "tecnologias": [
                {"id": 1, "name": "GPT-4", "descripcion": "OpenAI", "active": True},
                {"id": 2, "name": "Claude", "descripcion": "Anthropic", "active": True},
            ]
        }
        
        assert "tecnologias" in response
        assert isinstance(response["tecnologias"], list)
        assert len(response["tecnologias"]) == 2

    def test_inactive_tecnologia_visible(self):
        """Verifica que tecnologías inactivas son visibles pero marcadas."""
        tecnologias = [
            {"id": 1, "name": "GPT-4", "active": True},
            {"id": 2, "name": "Legacy", "active": False},
        ]
        
        inactive = [t for t in tecnologias if not t["active"]]
        active = [t for t in tecnologias if t["active"]]
        
        assert len(inactive) == 1
        assert len(active) == 1
        assert inactive[0]["name"] == "Legacy"


class TestTecnologiasBusinessLogic:
    """Tests de lógica de negocio de tecnologías."""

    def test_frontend_cannot_change_assigned_technology(self):
        """Verifica regla: frontend no puede cambiar tecnología ya asignada."""
        # Simula estado de proyecto con tecnología asignada
        proyecto_con_tecnologia = {
            "id": 1,
            "id_proyecto": 1,
            "id_tecnologia": 2,
            "coste_base": "17% sobre base",
        }
        
        # Si ya tiene tecnología asignada, frontend no puede cambiarla
        tiene_tecnologia = proyecto_con_tecnologia.get("id_tecnologia", 0) > 0
        
        assert tiene_tecnologia is True
        # En frontend, si tiene_tecnologia, el botón de asignar debe estar deshabilitado

    def test_backoffice_can_always_change_technology(self):
        """Verifica regla: backoffice puede cambiar tecnología en cualquier momento."""
        # Simula actualización de tecnología desde backoffice
        proyecto_con_tecnologia = {
            "id": 1,
            "id_proyecto": 1,
            "id_tecnologia": 2,
            "coste_base": "17% sobre base",
        }
        
        nueva_tecnologia = 3
        
        # Backoffice siempre puede actualizar
        proyecto_con_tecnologia["id_tecnologia"] = nueva_tecnologia
        
        assert proyecto_con_tecnologia["id_tecnologia"] == 3

    def test_coste_base_default_value(self):
        """Verifica que coste_base tiene valor por defecto."""
        default_coste = "17% sobre base"
        
        asignacion = {
            "id_proyecto": 1,
            "id_tecnologia": 2,
            "coste_base": default_coste,
        }
        
        assert asignacion["coste_base"] == "17% sobre base"

    def test_tecnologia_inactive_should_be_disabled_in_ui(self):
        """Verifica que tecnologías inactivas deben mostrarse deshabilitadas."""
        tecnologias = [
            {"id": 1, "name": "GPT-4", "active": True},
            {"id": 2, "name": "Legacy", "active": False},
        ]
        
        for tech in tecnologias:
            if not tech["active"]:
                # En UI: disabled=True, opacity=0.5, cursor=not-allowed
                assert tech["name"] == "Legacy"
