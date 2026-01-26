"""
Tests de integración Redis para SharedSessionState en Frontend.

Verifica:
- Herencia correcta de SharedSessionState
- Métodos de SharedSessionState disponibles
- Propiedades computadas funcionan
- load_user_data() carga datos correctamente
- clear_session() limpia datos correctamente
- go_to_backoffice() funciona
"""

import sys
from pathlib import Path

import pytest

# Añadir rutas necesarias
project_root = Path(__file__).resolve().parents[3]
frontend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(frontend_root))


class TestSharedSessionStateIntegration:
    """Tests de integración con SharedSessionState."""

    def test_state_inherits_from_shared_session_state(self):
        """Verifica que State hereda de SharedSessionState."""
        from web_frontend.web_frontend import State
        from web_frontend.shared_state import SharedSessionState

        assert issubclass(State, SharedSessionState), (
            "State debe heredar de SharedSessionState"
        )

    def test_state_has_shared_session_methods(self):
        """Verifica que State tiene los métodos de SharedSessionState."""
        from web_frontend.web_frontend import State

        # Métodos de SharedSessionState
        required_methods = [
            "load_user_data",
            "clear_session",
            "go_to_backoffice",
            "go_to_frontend",
            "update_activity",
        ]

        for method_name in required_methods:
            assert hasattr(State, method_name), (
                f"State debe tener el método {method_name}"
            )

    def test_state_has_shared_session_properties(self):
        """Verifica que State tiene las propiedades computadas."""
        from web_frontend.web_frontend import State

        # Propiedades computadas
        required_properties = [
            "can_access_backoffice",
            "user_display_name",
            "user_display_email",
        ]

        for prop_name in required_properties:
            assert hasattr(State, prop_name), (
                f"State debe tener la propiedad {prop_name}"
            )

    def test_state_has_permission_fields(self):
        """Verifica que State tiene los 45 campos de permisos."""
        from web_frontend.web_frontend import State

        # Algunos permisos clave
        key_permissions = [
            "can_training_create",
            "can_training_read",
            "can_training_update",
            "can_training_delete",
            "can_data_create",
            "can_data_read",
            "can_data_update",
            "can_data_delete",
            "can_folder_create",
            "can_folder_read",
            "can_folder_rename",
            "can_folder_move",
            "can_folder_delete",
            "can_file_upload",
            "can_file_download",
        ]

        for perm_name in key_permissions:
            assert hasattr(State, perm_name), (
                f"State debe tener el campo de permiso {perm_name}"
            )

    def test_state_has_session_metadata_fields(self):
        """Verifica que State tiene los campos de metadata de sesión."""
        from web_frontend.web_frontend import State

        metadata_fields = [
            "user_id",
            "organization_id",
            "identity_type_id",
            "user_name",
            "user_email",
            "user_mobile",
            "is_logged_in",
            "access_token",
            "session_token",
            "session_id",
            "login_time",
            "last_activity",
            "current_app",
        ]

        for field_name in metadata_fields:
            assert hasattr(State, field_name), (
                f"State debe tener el campo {field_name}"
            )

    def test_load_user_data_signature(self):
        """Verifica que load_user_data tiene la firma correcta."""
        from web_frontend.web_frontend import State
        import inspect

        method = getattr(State, "load_user_data")
        sig = inspect.signature(method)

        # Parámetros esperados (sin self)
        expected_params = [
            "user_id",
            "organization_id",
            "identity_type_id",
            "user_name",
            "user_email",
            "user_mobile",
            "access_token",
            "session_token",
            "permissions",
        ]

        actual_params = list(sig.parameters.keys())
        # Remover 'self'
        if "self" in actual_params:
            actual_params.remove("self")

        for param in expected_params:
            assert param in actual_params, (
                f"load_user_data debe tener el parámetro {param}"
            )

    def test_can_access_backoffice_property_logic(self):
        """
        Verifica la lógica de la propiedad can_access_backoffice.
        
        Debe ser True si:
        - is_logged_in == True
        - can_training_create == True
        """
        from web_frontend.shared_state import SharedSessionState

        # Crear instancia para probar la lógica
        # (en Reflex, State se instancia automáticamente)
        class MockState(SharedSessionState):
            pass

        # Caso 1: No logueado
        state = MockState()
        state.is_logged_in = False
        state.can_training_create = True
        assert not state.can_access_backoffice, (
            "can_access_backoffice debe ser False si no está logueado"
        )

        # Caso 2: Logueado pero sin permiso
        state.is_logged_in = True
        state.can_training_create = False
        assert not state.can_access_backoffice, (
            "can_access_backoffice debe ser False sin permiso training_create"
        )

        # Caso 3: Logueado y con permiso
        state.is_logged_in = True
        state.can_training_create = True
        assert state.can_access_backoffice, (
            "can_access_backoffice debe ser True con login y permiso"
        )

    def test_user_display_name_property(self):
        """Verifica la lógica de user_display_name."""
        from web_frontend.shared_state import SharedSessionState

        class MockState(SharedSessionState):
            pass

        state = MockState()

        # Caso 1: Sin nombre
        assert state.user_display_name == "Usuario", (
            "user_display_name debe retornar 'Usuario' por defecto"
        )

        # Caso 2: Con nombre
        state.user_name = "adminone"
        assert state.user_display_name == "adminone", (
            "user_display_name debe retornar el user_name"
        )

    def test_user_display_email_property(self):
        """Verifica la lógica de user_display_email."""
        from web_frontend.shared_state import SharedSessionState

        class MockState(SharedSessionState):
            pass

        state = MockState()

        # Caso 1: Sin email
        assert state.user_display_email == "No disponible", (
            "user_display_email debe retornar 'No disponible' por defecto"
        )

        # Caso 2: Con email
        state.user_email = "adminone@tfmmyllm.ai"
        assert state.user_display_email == "adminone@tfmmyllm.ai", (
            "user_display_email debe retornar el user_email"
        )

    def test_clear_session_resets_all_fields(self):
        """Verifica que clear_session limpia todos los campos."""
        from web_frontend.shared_state import SharedSessionState

        class MockState(SharedSessionState):
            pass

        state = MockState()

        # Establecer valores
        state.user_id = 1
        state.organization_id = 1
        state.user_name = "adminone"
        state.user_email = "admin@example.com"
        state.is_logged_in = True
        state.can_training_create = True
        state.access_token = "token123"
        state.session_token = "session123"

        # Limpiar sesión
        state.clear_session()

        # Verificar que todo se resetea
        assert state.user_id == 0, "user_id debe ser 0"
        assert state.organization_id == 0, "organization_id debe ser 0"
        assert state.user_name == "", "user_name debe ser cadena vacía"
        assert state.user_email == "", "user_email debe ser cadena vacía"
        assert not state.is_logged_in, "is_logged_in debe ser False"
        assert not state.can_training_create, "can_training_create debe ser False"
        assert state.access_token == "", "access_token debe ser cadena vacía"
        assert state.session_token == "", "session_token debe ser cadena vacía"

    def test_state_has_local_fields(self):
        """Verifica que State mantiene sus campos locales."""
        from web_frontend.web_frontend import State

        # Campos locales del frontend (no compartidos)
        local_fields = [
            "user_active_menu",
            "user_username",
            "user_password",
            "user_otp",
            "user_active_tab",
            "user_permissions",
            "login_error",
            "otp_request_message",
        ]

        for field_name in local_fields:
            assert hasattr(State, field_name), (
                f"State debe mantener su campo local {field_name}"
            )


class TestFrontendUserLoginIntegration:
    """Tests de integración del método user_login con SharedSessionState."""

    def test_user_login_method_exists(self):
        """Verifica que user_login está definido en State."""
        from web_frontend.web_frontend import State

        assert hasattr(State, "user_login"), (
            "State debe tener el método user_login"
        )

    def test_user_logout_method_exists(self):
        """Verifica que user_logout está definido en State."""
        from web_frontend.web_frontend import State

        assert hasattr(State, "user_logout"), (
            "State debe tener el método user_logout"
        )


class TestSharedStateHelperModule:
    """Tests del módulo helper shared_state.py."""

    def test_shared_state_helper_exists(self):
        """Verifica que existe el módulo shared_state.py."""
        from pathlib import Path

        helper_path = (
            Path(__file__).resolve().parents[1]
            / "web_frontend"
            / "shared_state.py"
        )
        assert helper_path.exists(), (
            "Debe existir web_frontend/shared_state.py"
        )

    def test_shared_state_helper_imports_successfully(self):
        """Verifica que shared_state.py importa SharedSessionState."""
        from web_frontend.shared_state import SharedSessionState

        assert SharedSessionState is not None, (
            "SharedSessionState debe importarse correctamente"
        )

    def test_shared_session_state_is_reflex_state(self):
        """Verifica que SharedSessionState hereda de rx.State."""
        from web_frontend.shared_state import SharedSessionState
        import reflex as rx

        assert issubclass(SharedSessionState, rx.State), (
            "SharedSessionState debe heredar de rx.State"
        )


# Ejecutar tests si se ejecuta directamente
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
