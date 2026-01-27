"""Tests para el PermissionValidationService."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Agregar rutas al path
_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_root))

# Cargar el servicio usando importlib
import importlib.util


def _load_security_hierarchy():
    """Carga el módulo de jerarquía de seguridad primero."""
    module_name = "security_hierarchy_for_pvs_test"
    module_path = _root / "src/1_shared_domain/security_hierarchy.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_permission_service():
    """Carga el módulo del servicio de permisos."""
    module_name = "permission_validation_service_test"
    module_path = (
        _root / "src/2_shared_application/services/permission_validation_service.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Cargar primero security_hierarchy
_security = _load_security_hierarchy()
_permission_module = _load_permission_service()

PermissionValidationService = _permission_module.PermissionValidationService
PermissionContext = _permission_module.PermissionContext
PermissionResult = _permission_module.PermissionResult
ALL_PERMISSION_KEYS = _permission_module.ALL_PERMISSION_KEYS
get_permission_service = _permission_module.get_permission_service


class TestMockPermissionsProvider:
    """Proveedor de permisos mock para testing."""
    
    def __init__(self, permissions_by_role: dict[int, dict[str, bool]]):
        self._permissions = permissions_by_role
    
    def get_permissions_for_identity_type(self, identity_type_id: int) -> dict:
        return self._permissions.get(identity_type_id, {})


class TestPermissionValidationService:
    """Tests para el servicio de validación de permisos."""

    def test_service_instantiation(self):
        """Verifica que el servicio se puede instanciar."""
        service = PermissionValidationService()
        assert service is not None

    def test_can_perform_action_with_mock_provider(self):
        """Verifica validación con proveedor mock."""
        mock_provider = TestMockPermissionsProvider({
            2: {
                "folder_create": True,
                "folder_rename": True,
                "folder_delete": False,
                "file_create": True,
            },
            3: {
                "folder_create": False,
                "file_read": True,
            },
        })
        
        service = PermissionValidationService(permissions_provider=mock_provider)
        
        # Rol 2 puede crear carpetas
        assert service.can_perform_action(2, "folder_create") is True
        assert service.can_perform_action(2, "folder_rename") is True
        assert service.can_perform_action(2, "folder_delete") is False
        
        # Rol 3 no puede crear carpetas
        assert service.can_perform_action(3, "folder_create") is False
        assert service.can_perform_action(3, "file_read") is True

    def test_has_any_permission(self):
        """Verifica has_any_permission."""
        mock_provider = TestMockPermissionsProvider({
            2: {
                "folder_create": True,
                "folder_rename": False,
                "folder_delete": False,
            },
        })
        
        service = PermissionValidationService(permissions_provider=mock_provider)
        
        # Tiene al menos uno
        assert service.has_any_permission(2, ["folder_create", "folder_rename"]) is True
        # No tiene ninguno
        assert service.has_any_permission(2, ["folder_rename", "folder_delete"]) is False

    def test_has_all_permissions(self):
        """Verifica has_all_permissions."""
        mock_provider = TestMockPermissionsProvider({
            2: {
                "folder_create": True,
                "folder_rename": True,
                "folder_delete": False,
            },
        })
        
        service = PermissionValidationService(permissions_provider=mock_provider)
        
        # Tiene todos
        assert service.has_all_permissions(2, ["folder_create", "folder_rename"]) is True
        # No tiene todos
        assert service.has_all_permissions(2, ["folder_create", "folder_delete"]) is False

    def test_validate_permission_returns_result(self):
        """Verifica que validate_permission retorna PermissionResult."""
        mock_provider = TestMockPermissionsProvider({
            2: {"folder_create": True},
        })
        
        service = PermissionValidationService(permissions_provider=mock_provider)
        context = PermissionContext(
            user_id=1,
            organization_id=1,
            identity_type_id=2,
        )
        
        result = service.validate_permission(context, "folder_create")
        
        assert isinstance(result, PermissionResult)
        assert result.allowed is True
        assert result.permission_key == "folder_create"
        assert result.context == context

    def test_validate_permission_denied(self):
        """Verifica resultado cuando se deniega permiso."""
        mock_provider = TestMockPermissionsProvider({
            2: {"folder_create": False},
        })
        
        service = PermissionValidationService(permissions_provider=mock_provider)
        context = PermissionContext(
            user_id=1,
            organization_id=1,
            identity_type_id=2,
        )
        
        result = service.validate_permission(context, "folder_create")
        
        assert result.allowed is False
        assert "no tiene permiso" in result.reason

    def test_unknown_permission_returns_false(self):
        """Verifica que permisos desconocidos retornan False."""
        mock_provider = TestMockPermissionsProvider({2: {}})
        service = PermissionValidationService(permissions_provider=mock_provider)
        
        assert service.can_perform_action(2, "unknown_permission") is False

    def test_empty_permission_returns_false(self):
        """Verifica que permiso vacío retorna False."""
        mock_provider = TestMockPermissionsProvider({2: {}})
        service = PermissionValidationService(permissions_provider=mock_provider)
        
        assert service.can_perform_action(2, "") is False

    def test_get_all_permissions(self):
        """Verifica get_all_permissions."""
        mock_provider = TestMockPermissionsProvider({
            2: {
                "folder_create": True,
                "file_create": True,
            },
        })
        
        service = PermissionValidationService(permissions_provider=mock_provider)
        permissions = service.get_all_permissions(2)
        
        # Debe contener todas las claves de ALL_PERMISSION_KEYS
        for key in ALL_PERMISSION_KEYS:
            assert key in permissions

    def test_cache_clear(self):
        """Verifica que se puede limpiar la cache."""
        mock_provider = TestMockPermissionsProvider({2: {"folder_create": True}})
        service = PermissionValidationService(permissions_provider=mock_provider)
        
        # Primera llamada carga la cache
        service.can_perform_action(2, "folder_create")
        
        # Limpiar cache no debería causar errores
        service.clear_cache()
        
        # Segunda llamada debería funcionar igual
        assert service.can_perform_action(2, "folder_create") is True


class TestConvenienceMethods:
    """Tests para métodos de conveniencia."""

    def test_can_manage_folders(self):
        """Verifica can_manage_folders."""
        mock_provider = TestMockPermissionsProvider({
            2: {"folder_create": True, "folder_rename": False, "folder_delete": False},
            3: {"folder_create": False, "folder_rename": False, "folder_delete": False},
        })
        
        service = PermissionValidationService(permissions_provider=mock_provider)
        
        assert service.can_manage_folders(2) is True
        assert service.can_manage_folders(3) is False

    def test_can_manage_files(self):
        """Verifica can_manage_files."""
        mock_provider = TestMockPermissionsProvider({
            2: {"file_create": True, "file_update": False, "file_delete": False},
        })
        
        service = PermissionValidationService(permissions_provider=mock_provider)
        
        assert service.can_manage_files(2) is True

    def test_can_access_backoffice(self):
        """Verifica can_access_backoffice requiere training_create."""
        mock_provider = TestMockPermissionsProvider({
            2: {"training_create": True},
            3: {"training_create": False},
        })
        
        service = PermissionValidationService(permissions_provider=mock_provider)
        
        assert service.can_access_backoffice(2) is True
        assert service.can_access_backoffice(3) is False


class TestPermissionContext:
    """Tests para PermissionContext."""

    def test_context_creation(self):
        """Verifica creación de contexto."""
        context = PermissionContext(
            user_id=1,
            organization_id=2,
            identity_type_id=3,
            project_id=4,
            version_id=5,
        )
        
        assert context.user_id == 1
        assert context.organization_id == 2
        assert context.identity_type_id == 3
        assert context.project_id == 4
        assert context.version_id == 5

    def test_context_optional_fields(self):
        """Verifica que project_id y version_id son opcionales."""
        context = PermissionContext(
            user_id=1,
            organization_id=2,
            identity_type_id=3,
        )
        
        assert context.project_id is None
        assert context.version_id is None


class TestSingletonService:
    """Tests para el servicio singleton."""

    def test_get_permission_service_returns_same_instance(self):
        """Verifica que el singleton retorna la misma instancia."""
        # Nota: Este test puede fallar si se ejecuta después de otros
        # que hayan modificado el estado del singleton
        service1 = get_permission_service()
        service2 = get_permission_service()
        
        assert service1 is service2


class TestAllPermissionKeys:
    """Tests para las claves de permisos."""

    def test_all_permission_keys_are_strings(self):
        """Verifica que todas las claves son strings."""
        for key in ALL_PERMISSION_KEYS:
            assert isinstance(key, str)

    def test_all_permission_keys_follow_naming_convention(self):
        """Verifica que las claves siguen la convención resource_action."""
        valid_prefixes = [
            "folder_", "file_", "project_", "version_",
            "training_", "parameters_", "notifications_", "user_"
        ]
        
        for key in ALL_PERMISSION_KEYS:
            assert any(key.startswith(prefix) for prefix in valid_prefixes), (
                f"Key '{key}' no sigue la convención de nombres"
            )

    def test_contains_expected_permissions(self):
        """Verifica que contiene los permisos esperados."""
        expected = [
            "folder_create", "folder_delete", "folder_rename",
            "file_create", "file_read", "file_update", "file_delete",
            "project_create", "project_read", "project_update",
            "version_create", "version_read",
            "training_create", "training_start",
            "user_create", "user_read",
        ]
        
        for permission in expected:
            assert permission in ALL_PERMISSION_KEYS, (
                f"Permiso esperado '{permission}' no está en ALL_PERMISSION_KEYS"
            )
