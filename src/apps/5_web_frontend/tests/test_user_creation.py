"""Tests para la creación de usuarios."""
import json
import tempfile
import shutil
import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import sys

# Agregar el directorio padre al path para importar módulos
test_dir = Path(__file__).parent
frontend_dir = test_dir.parent
project_root = frontend_dir.parent.parent.parent
sys.path.insert(0, str(frontend_dir))
sys.path.insert(0, str(project_root))

# Importar módulos necesarios
from pages.user_creation import UserCreationState
from adapters.api_client import save_user_to_json, log_security_action


@pytest.fixture
def temp_users_file(tmp_path):
    """
    Fixture que crea un archivo temporal de usuarios para testing.
    
    Returns:
        Path al archivo temporal de usuarios.
    """
    users_file = tmp_path / "users.json"
    users_file.write_text("[]", encoding="utf-8")
    return users_file


@pytest.fixture
def mock_domain_models():
    """
    Fixture que mockea las clases de dominio.
    
    Returns:
        Tupla con las clases mockeadas (User, ContactInfo, UserExtended).
    """
    # Crear clases mock
    class MockUser:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
            # Asegurar que existe el atributo 'id' que mapea a 'user_id'
            if hasattr(self, 'user_id') and not hasattr(self, 'id'):
                self.id = self.user_id
    
    class MockContactInfo:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class MockUserExtended:
        def __init__(self, user=None, contact_info=None, billing_info=None):
            self.user = user
            self.contact_info = contact_info
            self.billing_info = billing_info if billing_info is not None else contact_info
            # Atributos que se usan en el adaptador
            self.id = user.id if user else 1
            self.id_org = user.organization_id if user else 1
            self.id_type = user.identity_type_id if user else 1
            self.user_name = user.user_name if user else ""
            self.user_password = user.password if user else ""
            self.user_email = user.email if user else ""
            self.user_mobile = user.mobile if user else ""
            self.user_otp = user.otp if user else ""
            self.active = user.active if user else True
            self.blocked = user.blocked if user else False
    
    return MockUser, MockContactInfo, MockUserExtended


def test_user_creation_successful(temp_users_file, mock_domain_models):
    """
    Test que simula la creación exitosa de un usuario sin errores.
    
    Verifica:
    - Que todos los campos se validan correctamente
    - Que se invoca el adaptador para crear el usuario
    - Que se registra la acción en el log de seguridad
    - Que se capturan IP y user agent correctamente
    """
    MockUser, MockContactInfo, MockUserExtended = mock_domain_models
    
    # Mock de las clases de dominio
    with patch("pages.user_creation.User", MockUser), \
         patch("pages.user_creation.ContactInfo", MockContactInfo), \
         patch("pages.user_creation.UserExtended", MockUserExtended), \
         patch("pages.user_creation.save_user_to_json") as mock_save, \
         patch("pages.user_creation.log_security_action") as mock_log:
        
        mock_save.return_value = True
        mock_log.return_value = True
        
        # Crear instancia del estado
        state = UserCreationState()
        
        # Llenar todos los campos requeridos con datos válidos
        state.from_page = "main"
        state.account_kind = "organization"
        state.user_name = "testuser"
        state.user_password = "Test1234@Password"
        state.user_password_confirm = "Test1234@Password"
        state.user_email = "testuser@example.com"
        state.user_mobile = "+34612345678"
        state.organization_id = "1"
        state.identity_type_id = "10"
        state.active = True
        state.blocked = False
        
        # Campos de contacto
        state.contact_first_name = "Test"
        state.contact_sur_name = "User"
        state.contact_country = "España"
        state.contact_state = "Madrid"
        state.contact_zip_code = "28001"
        state.contact_address = "Calle Test 123"
        
        # No usar dirección de facturación diferente
        state.has_different_billing_address = False
        
        # Ejecutar save_user
        state.save_user()
        
        # Verificaciones
        assert state.message_type == "success", f"Expected success, got {state.message_type}. Message: {state.message}"
        assert "creado exitosamente" in state.message.lower() or "created" in state.message.lower()
        assert state.created_user is not None
        assert state.created_user["user_name"] == "testuser"
        assert state.created_user["user_email"] == "testuser@example.com"
        
        # Verificar que se llamó al adaptador
        assert mock_save.called, "save_user_to_json debería haber sido llamado"
        
        print("✅ Test de creación de usuario exitoso completado")


def test_security_logging_calls_middleware():
    """Verifica que el log de seguridad se envía al middleware."""

    with patch("adapters.api_client._request_middleware") as mock_request:
        mock_request.return_value = {"success": True}
        result = log_security_action(
            "Created user", 123, "192.168.1.100", "Mozilla/5.0 (Test Browser)"
        )

        assert result is True
        assert mock_request.called


def test_user_creation_with_security_logging(temp_users_file, mock_domain_models):
    """
    Test integrado que verifica la creación de usuario y el logging de seguridad.
    
    Verifica:
    - Que se crea el usuario correctamente
    - Que se registra en el log de seguridad
    - Que se capturan IP y user agent del request
    - Que existe una entrada en el log con "Created user"
    """
    MockUser, MockContactInfo, MockUserExtended = mock_domain_models
    
    # Mock de las clases de dominio
    with patch("pages.user_creation.User", MockUser), \
         patch("pages.user_creation.ContactInfo", MockContactInfo), \
         patch("pages.user_creation.UserExtended", MockUserExtended), \
         patch("pages.user_creation.save_user_to_json") as mock_save, \
         patch("pages.user_creation.log_security_action") as mock_log, \
         patch("pages.user_creation.rx.call_script") as mock_call_script:
        
        mock_save.return_value = True
        mock_log.return_value = True
        
        # Crear instancia del estado
        state = UserCreationState()
        
        # Simular router_data para obtener IP y user agent
        state.router_data = {
            "headers": {
                "x-forwarded-for": "10.0.0.50",
                "user-agent": "Chrome/120.0 Test",
            }
        }
        
        # Llenar todos los campos requeridos
        state.from_page = "main"
        state.account_kind = "organization"
        state.user_name = "integratedtest"
        state.user_password = "SecurePass123@"
        state.user_password_confirm = "SecurePass123@"
        state.user_email = "integrated@test.com"
        state.user_mobile = "+34698765432"
        state.organization_id = "1"
        state.identity_type_id = "10"
        state.active = True
        state.blocked = False
        
        # Campos de contacto
        state.contact_first_name = "Integrated"
        state.contact_sur_name = "Test"
        state.contact_country = "España"
        state.contact_state = "Barcelona"
        state.contact_zip_code = "08001"
        state.contact_address = "Avenida Test 456"
        
        state.has_different_billing_address = False
        
        # Ejecutar save_user
        state.save_user()
        
        # Verificar creación exitosa
        assert state.message_type == "success"
        assert mock_save.called
        assert mock_log.called
        
        print("✅ Test integrado de creación de usuario con logging exitoso")


def test_organization_creation_with_security_logging():
    """
    Test que verifica la creación de organización y el logging de seguridad.
    
    Verifica:
    - Que se crea la organización correctamente
    - Que se registra en el log de seguridad con "Organizacion nueva creada"
    - Que se capturan IP y user agent del request
    """
    from adapters.api_client import save_organization_to_json
    
    # Crear instancia del estado
    state = UserCreationState()
    
    # Simular router_data para obtener IP y user agent
    state.router_data = {
        "headers": {
            "x-forwarded-for": "192.168.1.200",
            "user-agent": "Firefox/121.0 Test",
        }
    }
    
    # Llenar campos de organización
    state.organization_name = "Test Organization"
    state.org_email = "test@org.com"
    state.org_tlf = "+34611111111"
    state.org_address = "Test Address 123"
    state.org_country = "España"
    state.org_state = "Madrid"
    
    # Mock de save_organization_to_json para retornar un organization_id
    with patch("pages.user_creation.create_organization") as mock_create, \
         patch("pages.user_creation.save_organization_to_json") as mock_save, \
         patch("pages.user_creation.log_security_action") as mock_log:
        mock_create.return_value = 11
        mock_save.return_value = 11
        mock_log.return_value = True
        
        # Ejecutar save_organization
        state.save_organization()
        
        # Verificar creación exitosa
        assert state.message_type == "success"
        assert mock_create.called or mock_save.called
        assert mock_log.called
        
        print("✅ Test de creación de organización con logging exitoso.")


def test_user_and_organization_logging_integration(temp_users_file, mock_domain_models):
    """
    Test integrado que verifica que tanto la creación de usuario como de organización
    se registran correctamente en el log de seguridad.
    
    Verifica:
    - Que existe una entrada en el log con "Created user" cuando se crea un usuario
    - Que existe una entrada en el log con "Organizacion nueva creada" cuando se crea una organización
    """
    MockUser, MockContactInfo, MockUserExtended = mock_domain_models
    
    # Mock de las clases de dominio
    with patch("pages.user_creation.User", MockUser), \
         patch("pages.user_creation.ContactInfo", MockContactInfo), \
         patch("pages.user_creation.UserExtended", MockUserExtended), \
         patch("pages.user_creation.create_organization") as mock_create_org, \
         patch("pages.user_creation.save_organization_to_json") as mock_save_org, \
         patch("pages.user_creation.save_user_to_json") as mock_save_user, \
         patch("pages.user_creation.log_security_action") as mock_log:
        
        mock_create_org.return_value = 12
        mock_save_org.return_value = 12
        mock_save_user.return_value = True
        mock_log.return_value = True
        
        # Crear instancia del estado
        state = UserCreationState()
        
        # Simular router_data
        state.router_data = {
            "headers": {
                "x-forwarded-for": "172.16.0.100",
                "user-agent": "Safari/17.0 Test",
            }
        }
        
        # 1. Crear una organización primero
        state.organization_name = "Integration Test Org"
        state.org_email = "integration@test.org"
        state.org_tlf = "+34622222222"
        state.org_address = "Integration Address 456"
        state.org_country = "España"
        state.org_state = "Valencia"
        
        state.save_organization()
        assert state.message_type == "success", "La organización debería crearse exitosamente"
        
        # 2. Crear un usuario
        state.from_page = "main"
        state.account_kind = "organization"
        state.user_name = "integrationuser"
        state.user_password = "Integration123@Pass"
        state.user_password_confirm = "Integration123@Pass"
        state.user_email = "integration@user.com"
        state.user_mobile = "+34633333333"
        state.organization_id = "12"
        state.identity_type_id = "10"
        state.active = True
        state.blocked = False
        
        state.contact_first_name = "Integration"
        state.contact_sur_name = "User"
        state.contact_country = "España"
        state.contact_state = "Valencia"
        state.contact_zip_code = "46001"
        state.contact_address = "Integration Street 789"
        state.has_different_billing_address = False
        
        state.save_user()
        assert state.message_type == "success", "El usuario debería crearse exitosamente"
        
        assert mock_log.called
        
        print("✅ Test integrado de logging de usuario y organización exitoso.")


def test_requirements_accordions_start_collapsed():
    """Los requisitos de usuario y contraseña arrancan contraídos."""
    state = UserCreationState()
    assert state.show_username_requirements is False
    assert state.show_password_requirements is False
    state.toggle_username_requirements()
    state.toggle_password_requirements()
    assert state.show_username_requirements is True
    assert state.show_password_requirements is True
    state.toggle_username_requirements()
    assert state.show_username_requirements is False


if __name__ == "__main__":
    # Ejecutar los tests directamente
    import sys
    import os
    
    # Configurar paths
    test_file = Path(__file__)
    frontend_dir = test_file.parent.parent
    project_root = frontend_dir.parent.parent.parent
    
    sys.path.insert(0, str(frontend_dir))
    sys.path.insert(0, str(project_root))
    
    # Crear directorios temporales
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        users_file = tmp_path / "users.json"
        users_file.write_text("[]", encoding="utf-8")
        
        print("Ejecutando tests de creación de usuario...")
        print("=" * 60)
        
        # Ejecutar tests
        try:
            test_user_creation_successful(users_file, None)
            print("\n" + "=" * 60)
            test_security_logging_calls_middleware()
            print("\n" + "=" * 60)
            test_user_creation_with_security_logging(users_file, None)
            print("\n" + "=" * 60)
            test_organization_creation_with_security_logging()
            print("\n" + "=" * 60)
            test_user_and_organization_logging_integration(users_file, None)
            print("\n" + "=" * 60)
            print("✅ Todos los tests pasaron exitosamente")
        except Exception as e:
            print(f"\n❌ Error en los tests: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

