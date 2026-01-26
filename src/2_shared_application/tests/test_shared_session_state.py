"""
Tests de integración para SharedSessionState en capa compartida.

Verifica estructura de archivos y contenido de shared_session_state.py
mediante análisis de texto (sin instanciar clases Reflex).
"""

import sys
from pathlib import Path

import pytest

# Añadir rutas necesarias para importación dinámica
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))


class TestSharedSessionStateModuleExists:
    """Tests básicos del módulo SharedSessionState."""

    def test_shared_session_state_file_exists(self):
        """Verifica que existe el archivo shared_session_state.py."""
        module_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "shared_session_state.py"
        )
        assert module_path.exists(), (
            "Debe existir shared_session_state.py"
        )

    def test_init_file_exists(self):
        """Verifica que existe __init__.py."""
        init_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "__init__.py"
        )
        assert init_path.exists(), (
            "Debe existir reflex_shared/__init__.py"
        )


class TestSharedSessionStateContentVerification:
    """Tests de verificación de contenido del archivo."""

    def test_file_contains_shared_session_state_class(self):
        """Verifica que el archivo contiene la clase SharedSessionState."""
        module_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "shared_session_state.py"
        )
        content = module_path.read_text()
        assert "class SharedSessionState" in content, (
            "El archivo debe definir la clase SharedSessionState"
        )
        assert "rx.State" in content, (
            "SharedSessionState debe heredar de rx.State"
        )

    def test_file_contains_user_fields(self):
        """Verifica que el archivo contiene campos de usuario."""
        module_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "shared_session_state.py"
        )
        content = module_path.read_text()
        
        required_fields = [
            "user_id:",
            "organization_id:",
            "identity_type_id:",
            "user_name:",
            "user_email:",
            "user_mobile:",
        ]
        
        for field in required_fields:
            assert field in content, (
                f"El archivo debe contener el campo {field}"
            )

    def test_file_contains_authentication_fields(self):
        """Verifica que el archivo contiene campos de autenticación."""
        module_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "shared_session_state.py"
        )
        content = module_path.read_text()
        
        required_fields = [
            "is_logged_in:",
            "access_token:",
            "session_token:",
            "session_id:",
        ]
        
        for field in required_fields:
            assert field in content, (
                f"El archivo debe contener el campo {field}"
            )

    def test_file_contains_key_permission_fields(self):
        """Verifica que el archivo contiene campos de permisos clave."""
        module_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "shared_session_state.py"
        )
        content = module_path.read_text()
        
        # Muestra de permisos clave (que realmente existen)
        key_permissions = [
            "can_training_create:",
            "can_data_read:",
            "can_folder_create:",
            "can_file_upload:",
        ]
        
        for perm in key_permissions:
            assert perm in content, (
                f"El archivo debe contener el permiso {perm}"
            )

    def test_file_contains_load_user_data_method(self):
        """Verifica que el archivo contiene el método load_user_data."""
        module_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "shared_session_state.py"
        )
        content = module_path.read_text()
        
        assert "def load_user_data" in content, (
            "El archivo debe definir load_user_data()"
        )
        assert "permissions: dict" in content, (
            "load_user_data debe recibir permissions como dict"
        )

    def test_file_contains_clear_session_method(self):
        """Verifica que el archivo contiene el método clear_session."""
        module_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "shared_session_state.py"
        )
        content = module_path.read_text()
        
        assert "def clear_session" in content, (
            "El archivo debe definir clear_session()"
        )

    def test_file_contains_go_to_backoffice_method(self):
        """Verifica que el archivo contiene el método go_to_backoffice."""
        module_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "shared_session_state.py"
        )
        content = module_path.read_text()
        
        assert "def go_to_backoffice" in content, (
            "El archivo debe definir go_to_backoffice()"
        )
        assert "https://tfmmyllm.ai/backoffice" in content, (
            "go_to_backoffice debe redirigir al backoffice"
        )

    def test_file_contains_go_to_frontend_method(self):
        """Verifica que el archivo contiene el método go_to_frontend."""
        module_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "shared_session_state.py"
        )
        content = module_path.read_text()
        
        assert "def go_to_frontend" in content, (
            "El archivo debe definir go_to_frontend()"
        )
        assert "https://tfmmyllm.ai" in content, (
            "go_to_frontend debe redirigir al frontend"
        )

    def test_file_contains_can_access_backoffice_property(self):
        """Verifica que el archivo contiene la propiedad can_access_backoffice."""
        module_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "shared_session_state.py"
        )
        content = module_path.read_text()
        
        assert "@property" in content, (
            "El archivo debe contener propiedades computadas"
        )
        assert "def can_access_backoffice" in content, (
            "El archivo debe definir la propiedad can_access_backoffice"
        )
        assert "is_logged_in and self.can_training_create" in content, (
            "can_access_backoffice debe verificar login y permiso training_create"
        )

    def test_file_contains_user_display_properties(self):
        """Verifica que el archivo contiene las propiedades de display."""
        module_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "shared_session_state.py"
        )
        content = module_path.read_text()
        
        assert "def user_display_name" in content, (
            "El archivo debe definir la propiedad user_display_name"
        )
        assert "def user_display_email" in content, (
            "El archivo debe definir la propiedad user_display_email"
        )


class TestSharedSessionStateDocumentation:
    """Tests de documentación del código."""

    def test_file_has_docstring(self):
        """Verifica que el archivo tiene docstring."""
        module_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "shared_session_state.py"
        )
        content = module_path.read_text()
        
        # Buscar docstrings (""" o ''')
        assert '"""' in content or "'''" in content, (
            "El archivo debe contener docstrings"
        )

    def test_class_has_docstring(self):
        """Verifica que la clase tiene docstring."""
        module_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "shared_session_state.py"
        )
        content = module_path.read_text()
        
        # Verificar que hay un docstring después de la definición de clase
        assert "class SharedSessionState" in content, "Debe existir la clase"
        lines = content.split("\n")
        class_line_idx = next(
            i for i, line in enumerate(lines) if "class SharedSessionState" in line
        )
        # Verificar que hay un docstring en las siguientes líneas
        following_lines = "\n".join(lines[class_line_idx:class_line_idx + 5])
        assert '"""' in following_lines or "'''" in following_lines, (
            "La clase debe tener docstring"
        )


class TestSharedSessionStateInitFile:
    """Tests del __init__.py del paquete."""

    def test_init_exports_shared_session_state(self):
        """Verifica que __init__.py exporta SharedSessionState."""
        init_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "__init__.py"
        )
        content = init_path.read_text()
        
        assert "SharedSessionState" in content, (
            "__init__.py debe mencionar SharedSessionState"
        )
        assert "from .shared_session_state import SharedSessionState" in content, (
            "__init__.py debe importar SharedSessionState"
        )


# Ejecutar tests si se ejecuta directamente
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
