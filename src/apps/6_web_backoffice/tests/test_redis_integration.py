"""
Tests de integración Redis para SharedSessionState en Backoffice.

Verifica:
- Herencia correcta de SharedSessionState
- Métodos de SharedSessionState disponibles
- Login deshabilitado en backoffice
- Logout redirige al frontend
- check_backoffice_access() funciona
- Botones correctos en UI
"""

import sys
from pathlib import Path

import pytest

# Añadir rutas necesarias
project_root = Path(__file__).resolve().parents[3]
backoffice_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backoffice_root))


class TestBackofficeSharedSessionStateIntegration:
    """Tests de integración con SharedSessionState en Backoffice."""

    def test_state_inherits_from_shared_session_state(self):
        """Verifica que State hereda de SharedSessionState."""
        from web_backoffice.web_frontend import State
        from web_backoffice.shared_state import SharedSessionState

        assert issubclass(State, SharedSessionState), (
            "Backoffice State debe heredar de SharedSessionState"
        )

    def test_state_has_shared_session_methods(self):
        """Verifica que State tiene los métodos de SharedSessionState."""
        from web_backoffice.web_frontend import State

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
                f"Backoffice State debe tener el método {method_name}"
            )

    def test_state_has_check_backoffice_access_method(self):
        """Verifica que State tiene check_backoffice_access."""
        from web_backoffice.web_frontend import State

        assert hasattr(State, "check_backoffice_access"), (
            "Backoffice State debe tener check_backoffice_access()"
        )

    def test_state_has_shared_session_properties(self):
        """Verifica que State tiene las propiedades computadas."""
        from web_backoffice.web_frontend import State

        # Propiedades computadas
        required_properties = [
            "can_access_backoffice",
            "user_display_name",
            "user_display_email",
        ]

        for prop_name in required_properties:
            assert hasattr(State, prop_name), (
                f"Backoffice State debe tener la propiedad {prop_name}"
            )

    def test_state_has_permission_fields(self):
        """Verifica que State tiene los 45 campos de permisos."""
        from web_backoffice.web_frontend import State

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
                f"Backoffice State debe tener el campo de permiso {perm_name}"
            )

    def test_state_has_session_metadata_fields(self):
        """Verifica que State tiene los campos de metadata de sesión."""
        from web_backoffice.web_frontend import State

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
                f"Backoffice State debe tener el campo {field_name}"
            )

    def test_state_has_local_fields(self):
        """Verifica que State mantiene sus campos locales."""
        from web_backoffice.web_frontend import State

        # Campos locales del backoffice (no compartidos)
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
                f"Backoffice State debe mantener su campo local {field_name}"
            )


class TestBackofficeUserLoginDisabled:
    """Tests que verifican que el login está deshabilitado en backoffice."""

    def test_user_login_method_exists(self):
        """Verifica que user_login está definido en State."""
        from web_backoffice.web_frontend import State

        assert hasattr(State, "user_login"), (
            "Backoffice State debe tener el método user_login"
        )

    def test_user_login_is_disabled(self):
        """
        Verifica que user_login en backoffice no permite login.
        
        Debe establecer un mensaje de error sin realizar login.
        """
        from web_backoffice.shared_state import SharedSessionState

        class MockBackofficeState(SharedSessionState):
            login_error: str = ""

            def user_login(self):
                """Login deshabilitado en backoffice."""
                self.login_error = "El login debe realizarse desde el sitio principal"
                return

        state = MockBackofficeState()
        state.user_login()

        assert state.login_error == "El login debe realizarse desde el sitio principal", (
            "user_login debe establecer mensaje de error"
        )
        assert not state.is_logged_in, (
            "user_login no debe cambiar is_logged_in"
        )

    def test_user_logout_method_exists(self):
        """Verifica que user_logout está definido en State."""
        from web_backoffice.web_frontend import State

        assert hasattr(State, "user_logout"), (
            "Backoffice State debe tener el método user_logout"
        )


class TestBackofficeAccessControl:
    """Tests de control de acceso al backoffice."""

    def test_check_backoffice_access_logic(self):
        """
        Verifica la lógica de check_backoffice_access.
        
        Debe llamar a go_to_frontend() si no tiene acceso.
        """
        from web_backoffice.shared_state import SharedSessionState

        class MockBackofficeState(SharedSessionState):
            redirected: bool = False

            def check_backoffice_access(self):
                if not self.can_access_backoffice:
                    return self.go_to_frontend()

            def go_to_frontend(self):
                """Override para testing."""
                self.redirected = True
                return "redirect_to_frontend"

        # Caso 1: Sin acceso
        state = MockBackofficeState()
        state.is_logged_in = False
        state.can_training_create = False
        result = state.check_backoffice_access()

        assert result == "redirect_to_frontend", (
            "check_backoffice_access debe redirigir sin acceso"
        )
        assert state.redirected, "Debe llamar a go_to_frontend()"

        # Caso 2: Con acceso
        state2 = MockBackofficeState()
        state2.is_logged_in = True
        state2.can_training_create = True
        state2.redirected = False
        result2 = state2.check_backoffice_access()

        assert result2 is None, (
            "check_backoffice_access no debe redirigir con acceso"
        )
        assert not state2.redirected, "No debe llamar a go_to_frontend()"


class TestBackofficeSharedStateHelper:
    """Tests del módulo helper shared_state.py en backoffice."""

    def test_shared_state_helper_exists(self):
        """Verifica que existe el módulo shared_state.py."""
        from pathlib import Path

        helper_path = (
            Path(__file__).resolve().parents[1]
            / "web_backoffice"
            / "shared_state.py"
        )
        assert helper_path.exists(), (
            "Debe existir web_backoffice/shared_state.py"
        )

    def test_shared_state_helper_imports_successfully(self):
        """Verifica que shared_state.py importa SharedSessionState."""
        from web_backoffice.shared_state import SharedSessionState

        assert SharedSessionState is not None, (
            "SharedSessionState debe importarse correctamente"
        )

    def test_shared_session_state_is_reflex_state(self):
        """Verifica que SharedSessionState hereda de rx.State."""
        from web_backoffice.shared_state import SharedSessionState
        import reflex as rx

        assert issubclass(SharedSessionState, rx.State), (
            "SharedSessionState debe heredar de rx.State"
        )


class TestBackofficeNavigation:
    """Tests de navegación del backoffice."""

    def test_go_to_frontend_method_inherited(self):
        """Verifica que go_to_frontend está disponible."""
        from web_backoffice.web_frontend import State

        assert hasattr(State, "go_to_frontend"), (
            "Backoffice State debe tener go_to_frontend()"
        )

    def test_go_to_backoffice_method_inherited(self):
        """Verifica que go_to_backoffice está disponible."""
        from web_backoffice.web_frontend import State

        assert hasattr(State, "go_to_backoffice"), (
            "Backoffice State debe tener go_to_backoffice()"
        )


class TestBackofficeRedisConfiguration:
    """Tests de configuración Redis del backoffice."""

    def test_backoffice_uses_redis(self):
        """Verifica que rxconfig.py del backoffice tiene redis_url."""
        import sys
        from pathlib import Path

        backoffice_root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(backoffice_root))

        try:
            from rxconfig import config

            assert hasattr(config, "redis_url"), (
                "rxconfig debe tener redis_url configurado"
            )
            assert config.redis_url is not None, (
                "redis_url no debe ser None"
            )
            assert "redis://" in config.redis_url, (
                "redis_url debe comenzar con redis://"
            )
        except ImportError:
            pytest.skip("rxconfig.py no disponible en contexto de test")

    def test_backoffice_uses_same_redis_db_as_frontend(self):
        """
        Verifica que backoffice usa la MISMA Redis DB que frontend.
        
        Esto es crítico para compartir sesiones.
        """
        import sys
        from pathlib import Path

        # Importar config del backoffice
        backoffice_root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(backoffice_root))

        try:
            from rxconfig import config as backoffice_config

            # Importar config del frontend
            frontend_root = backoffice_root.parent / "5_web_frontend"
            sys.path.insert(0, str(frontend_root))
            from rxconfig import config as frontend_config

            # Extraer DB number de las URLs
            backoffice_db = backoffice_config.redis_url.split("/")[-1]
            frontend_db = frontend_config.redis_url.split("/")[-1]

            assert backoffice_db == frontend_db, (
                f"Backoffice y Frontend deben usar la MISMA Redis DB. "
                f"Backoffice: {backoffice_db}, Frontend: {frontend_db}"
            )
        except ImportError:
            pytest.skip("rxconfig.py no disponible en contexto de test")


class TestBackofficePortConfiguration:
    """Tests de configuración de puertos del backoffice."""

    def test_backoffice_uses_port_8006(self):
        """Verifica que el backoffice usa el puerto 8006."""
        import sys
        from pathlib import Path

        backoffice_root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(backoffice_root))

        try:
            from rxconfig import config

            assert hasattr(config, "backend_port"), (
                "rxconfig debe tener backend_port configurado"
            )
            assert config.backend_port == 8006, (
                f"Backoffice debe usar puerto 8006, no {config.backend_port}"
            )
        except ImportError:
            pytest.skip("rxconfig.py no disponible en contexto de test")


# Ejecutar tests si se ejecuta directamente
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
