"""Tests para los adaptadores JSON de repositorios."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Agregar rutas al path
_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_root))

# Cargar los adaptadores usando importlib
import importlib.util


def _load_user_repository():
    """Carga el repositorio de usuarios."""
    module_path = _root / "src/2_shared_application/adapters/json_user_repository.py"
    spec = importlib.util.spec_from_file_location("json_user_repo_test", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_org_repository():
    """Carga el repositorio de organizaciones."""
    module_path = _root / "src/2_shared_application/adapters/json_organization_repository.py"
    spec = importlib.util.spec_from_file_location("json_org_repo_test", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_user_repo = _load_user_repository()
_org_repo = _load_org_repository()

JsonUserRepository = _user_repo.JsonUserRepository
JsonOrganizationRepository = _org_repo.JsonOrganizationRepository


class TestJsonUserRepository:
    """Tests para el repositorio de usuarios JSON."""

    def test_repository_creation_with_custom_path(self):
        """Verifica que se puede crear con ruta personalizada."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump([], f)
            f.flush()
            repo = JsonUserRepository(data_path=Path(f.name))
            assert repo is not None

    def test_load_users_from_empty_file(self):
        """Verifica carga desde archivo vacío."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump([], f)
            f.flush()
            repo = JsonUserRepository(data_path=Path(f.name))
            users = repo.get_all()
            assert users == []

    def test_get_by_email(self):
        """Verifica obtención por email."""
        users_data = [
            {"user_id": 1, "user_email": "test@example.com", "user_name": "Test"},
            {"user_id": 2, "user_email": "other@example.com", "user_name": "Other"},
        ]
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(users_data, f)
            f.flush()
            repo = JsonUserRepository(data_path=Path(f.name))
            
            user = repo.get_by_email("test@example.com")
            assert user is not None
            assert user["user_id"] == 1
            
            # Case insensitive
            user_upper = repo.get_by_email("TEST@EXAMPLE.COM")
            assert user_upper is not None
            assert user_upper["user_id"] == 1

    def test_get_by_email_not_found(self):
        """Verifica que retorna None si no se encuentra."""
        users_data = [{"user_id": 1, "user_email": "test@example.com"}]
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(users_data, f)
            f.flush()
            repo = JsonUserRepository(data_path=Path(f.name))
            
            user = repo.get_by_email("notfound@example.com")
            assert user is None

    def test_exists_by_email(self):
        """Verifica exists_by_email."""
        users_data = [{"user_id": 1, "user_email": "test@example.com"}]
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(users_data, f)
            f.flush()
            repo = JsonUserRepository(data_path=Path(f.name))
            
            assert repo.exists_by_email("test@example.com") is True
            assert repo.exists_by_email("notfound@example.com") is False

    def test_exists_by_mobile(self):
        """Verifica exists_by_mobile."""
        users_data = [{"user_id": 1, "user_email": "test@example.com", "user_mobile": "+34612345678"}]
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(users_data, f)
            f.flush()
            repo = JsonUserRepository(data_path=Path(f.name))
            
            assert repo.exists_by_mobile("+34612345678") is True
            assert repo.exists_by_mobile("+34999999999") is False

    def test_get_by_name(self):
        """Verifica obtención por nombre."""
        users_data = [
            {"user_id": 1, "user_email": "a@b.com", "user_name": "TestUser"},
        ]
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(users_data, f)
            f.flush()
            repo = JsonUserRepository(data_path=Path(f.name))
            
            user = repo.get_by_name("TestUser")
            assert user is not None
            assert user["user_id"] == 1
            
            # Case insensitive
            user_lower = repo.get_by_name("testuser")
            assert user_lower is not None

    def test_count(self):
        """Verifica count."""
        users_data = [
            {"user_id": 1, "user_email": "a@b.com"},
            {"user_id": 2, "user_email": "c@d.com"},
        ]
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(users_data, f)
            f.flush()
            repo = JsonUserRepository(data_path=Path(f.name))
            
            assert repo.count() == 2


class TestJsonOrganizationRepository:
    """Tests para el repositorio de organizaciones JSON."""

    def test_repository_creation(self):
        """Verifica que se puede crear el repositorio."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump([], f)
            f.flush()
            repo = JsonOrganizationRepository(data_path=Path(f.name))
            assert repo is not None

    def test_get_by_id(self):
        """Verifica obtención por ID."""
        orgs_data = [
            {"organization_id": 1, "organization_name": "Org 1"},
            {"organization_id": 2, "organization_name": "Org 2"},
        ]
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(orgs_data, f)
            f.flush()
            repo = JsonOrganizationRepository(data_path=Path(f.name))
            
            org = repo.get_by_id(1)
            assert org is not None
            assert org["organization_name"] == "Org 1"

    def test_get_by_name(self):
        """Verifica obtención por nombre."""
        orgs_data = [
            {"organization_id": 1, "organization_name": "Test Organization"},
        ]
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(orgs_data, f)
            f.flush()
            repo = JsonOrganizationRepository(data_path=Path(f.name))
            
            org = repo.get_by_name("Test Organization")
            assert org is not None
            assert org["organization_id"] == 1
            
            # Normalización de texto (case insensitive)
            org_lower = repo.get_by_name("test organization")
            assert org_lower is not None

    def test_exists_by_name(self):
        """Verifica exists_by_name."""
        orgs_data = [{"organization_id": 1, "organization_name": "Existing Org"}]
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(orgs_data, f)
            f.flush()
            repo = JsonOrganizationRepository(data_path=Path(f.name))
            
            assert repo.exists_by_name("Existing Org") is True
            assert repo.exists_by_name("Non Existing") is False

    def test_save_new_organization(self):
        """Verifica guardar nueva organización."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump([], f)
            f.flush()
            repo = JsonOrganizationRepository(data_path=Path(f.name))
            
            org_data = {"organization_name": "New Org"}
            saved = repo.save(org_data)
            
            assert saved is not None
            assert saved["organization_id"] == 1
            assert repo.count() == 1

    def test_save_update_organization(self):
        """Verifica actualizar organización existente."""
        orgs_data = [{"organization_id": 1, "organization_name": "Old Name"}]
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(orgs_data, f)
            f.flush()
            repo = JsonOrganizationRepository(data_path=Path(f.name))
            
            updated_data = {"organization_id": 1, "organization_name": "New Name"}
            saved = repo.save(updated_data)
            
            assert saved is not None
            assert saved["organization_name"] == "New Name"
            assert repo.count() == 1

    def test_delete_organization(self):
        """Verifica eliminar organización."""
        orgs_data = [
            {"organization_id": 1, "organization_name": "Org 1"},
            {"organization_id": 2, "organization_name": "Org 2"},
        ]
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(orgs_data, f)
            f.flush()
            repo = JsonOrganizationRepository(data_path=Path(f.name))
            
            result = repo.delete(1)
            assert result is True
            assert repo.count() == 1
            assert repo.get_by_id(1) is None
            assert repo.get_by_id(2) is not None

    def test_delete_non_existent_returns_false(self):
        """Verifica que eliminar inexistente retorna False."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump([], f)
            f.flush()
            repo = JsonOrganizationRepository(data_path=Path(f.name))
            
            result = repo.delete(999)
            assert result is False

    def test_get_all(self):
        """Verifica get_all."""
        orgs_data = [
            {"organization_id": 1, "organization_name": "Org 1"},
            {"organization_id": 2, "organization_name": "Org 2"},
        ]
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(orgs_data, f)
            f.flush()
            repo = JsonOrganizationRepository(data_path=Path(f.name))
            
            all_orgs = repo.get_all()
            assert len(all_orgs) == 2
