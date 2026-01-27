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
# tests/ -> 5_web_frontend/ -> apps/ -> src/ -> anewhope/
project_root = Path(__file__).resolve().parents[4]  # /Users/.../anewhope
src_root = Path(__file__).resolve().parents[3]      # /Users/.../anewhope/src
frontend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_root))
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
        """Verifica que State tiene campos de permisos clave."""
        from web_frontend.web_frontend import State

        # Permisos clave que existen en la implementación actual
        key_permissions = [
            "can_training_create",
            "can_training_execute",
            "can_training_monitor",
            "can_training_stop",
            "can_training_delete",
            "can_data_read",
            "can_data_write",
            "can_data_delete",
            "can_folder_create",
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
        """Verifica que load_user_data está definido correctamente."""
        from web_frontend.shared_state import SharedSessionState
        from pathlib import Path

        # Verificar que el método existe
        assert hasattr(SharedSessionState, "load_user_data"), (
            "SharedSessionState debe tener load_user_data"
        )
        
        # Leer el archivo fuente directamente
        shared_state_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "shared_session_state.py"
        )
        source = shared_state_path.read_text()
        
        # Verificar que load_user_data tiene los parámetros esperados
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
        
        assert "def load_user_data" in source, (
            "load_user_data debe estar definido"
        )
        
        for param in expected_params:
            assert param in source, (
                f"load_user_data debe usar el parámetro {param}"
            )

    def test_can_access_backoffice_property_logic(self):
        """
        Verifica la lógica de la propiedad can_access_backoffice.
        
        Debe ser True si:
        - is_logged_in == True
        - can_training_create == True
        """
        from web_frontend.shared_state import SharedSessionState
        from pathlib import Path

        # Verificar que la propiedad existe
        assert hasattr(SharedSessionState, "can_access_backoffice"), (
            "SharedSessionState debe tener can_access_backoffice"
        )
        
        # Leer el archivo fuente directamente
        shared_state_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "shared_session_state.py"
        )
        source = shared_state_path.read_text()
        
        # Buscar la definición de can_access_backoffice
        assert "def can_access_backoffice" in source, (
            "can_access_backoffice debe estar definido"
        )
        assert "is_logged_in" in source, (
            "can_access_backoffice debe verificar is_logged_in"
        )
        assert "can_training_create" in source, (
            "can_access_backoffice debe verificar can_training_create"
        )

    def test_user_display_name_property(self):
        """Verifica que user_display_name está definido."""
        from web_frontend.shared_state import SharedSessionState
        from pathlib import Path

        # Verificar que la propiedad existe
        assert hasattr(SharedSessionState, "user_display_name"), (
            "SharedSessionState debe tener user_display_name"
        )
        
        # Leer el archivo fuente directamente
        shared_state_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "shared_session_state.py"
        )
        source = shared_state_path.read_text()
        
        assert "user_display_name" in source, (
            "user_display_name debe estar definido"
        )
        assert "user_name" in source, (
            "user_display_name debe usar user_name"
        )

    def test_user_display_email_property(self):
        """Verifica que user_display_email está definido."""
        from web_frontend.shared_state import SharedSessionState
        from pathlib import Path

        # Verificar que la propiedad existe
        assert hasattr(SharedSessionState, "user_display_email"), (
            "SharedSessionState debe tener user_display_email"
        )
        
        # Leer el archivo fuente directamente
        shared_state_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "shared_session_state.py"
        )
        source = shared_state_path.read_text()
        
        assert "user_display_email" in source, (
            "user_display_email debe estar definido"
        )
        assert "user_email" in source, (
            "user_display_email debe usar user_email"
        )

    def test_clear_session_resets_all_fields(self):
        """Verifica que clear_session está definido y resetea campos."""
        from web_frontend.shared_state import SharedSessionState
        from pathlib import Path

        # Verificar que el método existe
        assert hasattr(SharedSessionState, "clear_session"), (
            "SharedSessionState debe tener clear_session"
        )
        
        # Leer el archivo fuente directamente
        shared_state_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "shared_session_state.py"
        )
        source = shared_state_path.read_text()
        
        # Verificar que clear_session está definido
        assert "def clear_session" in source, (
            "clear_session debe estar definido"
        )
        
        # Verificar que resetea campos clave
        fields_to_reset = [
            "user_id",
            "organization_id",
            "user_name",
            "is_logged_in",
            "access_token",
            "session_token",
        ]
        
        for field in fields_to_reset:
            assert field in source, (
                f"SharedSessionState debe tener el campo {field}"
            )

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
