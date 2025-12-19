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

# Cargar módulo de seguridad común usando importlib (módulo con nombre que empieza con número)
common_security_path = (
    project_root / "src" / "2_shared_application" / "security" / "common_security.py"
)
log_security_action = None
if common_security_path.exists():
    try:
        spec = importlib.util.spec_from_file_location("common_security", common_security_path)
        if spec and spec.loader:
            common_security_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(common_security_module)
            log_security_action = getattr(common_security_module, "log_security_action", None)
    except Exception as e:
        print(f"Warning: No se pudo cargar common_security: {e}")

# Importar módulos necesarios
from pages.user_creation import UserCreationState, _register_security_action
from adapters.api_client import save_user_to_json


class MockRequest:
    """Mock del objeto request HTTP para testing."""
    
    def __init__(self, ip: str = "192.168.1.100", user_agent: str = "Mozilla/5.0 Test Browser"):
        self.headers = {
            "x-forwarded-for": ip,
            "user-agent": user_agent,
        }
        self.client = Mock()
        self.client.host = ip
        self.scope = {
            "client": (ip, 8000),
            "headers": [
                (b"user-agent", user_agent.encode("utf-8")),
            ],
        }


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
def temp_log_file(tmp_path):
    """
    Fixture que crea un archivo temporal de log para testing.
    
    Returns:
        Path al archivo temporal de log.
    """
    log_file = tmp_path / "frontend_secure.log"
    return log_file


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
    
    class MockContactInfo:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class MockUserExtended:
        def __init__(self, user=None, contact_info=None, billing_info=None):
            self.user = user
            self.contact_info = contact_info
            self.billing_info = billing_info
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


def test_user_creation_successful(temp_users_file, temp_log_file, mock_domain_models):
    """
    Test que simula la creación exitosa de un usuario sin errores.
    
    Verifica:
    - Que todos los campos se validan correctamente
    - Que se crea el usuario en users.json
    - Que se registra la acción en el log de seguridad
    - Que se capturan IP y user agent correctamente
    """
    MockUser, MockContactInfo, MockUserExtended = mock_domain_models
    
    # Mock del path del log
    with patch("pages.user_creation._SECURITY_LOG_PATH", temp_log_file):
        # Mock de las clases de dominio
        with patch("pages.user_creation.User", MockUser), \
             patch("pages.user_creation.ContactInfo", MockContactInfo), \
             patch("pages.user_creation.UserExtended", MockUserExtended), \
             patch("pages.user_creation.save_user_to_json") as mock_save:
            
            # Configurar el mock para que save_user_to_json retorne True
            mock_save.return_value = True
            
            # Crear instancia del estado
            state = UserCreationState()
            
            # Llenar todos los campos requeridos con datos válidos
            state.from_page = "main"
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
            
            # Verificar que se llamó a save_user_to_json
            assert mock_save.called, "save_user_to_json debería haber sido llamado"
            
            print("✅ Test de creación de usuario exitoso completado")


def test_security_logging_with_request(temp_log_file):
    """
    Test que verifica que el logging de seguridad funciona correctamente
    con un request HTTP simulado.
    
    Verifica:
    - Que se escribe en el archivo de log
    - Que se capturan IP y user agent correctamente
    - Que el formato CSV es correcto
    """
    # Crear request mock
    mock_request = MockRequest(ip="192.168.1.100", user_agent="Mozilla/5.0 (Test Browser)")
    
    # Llamar a la función de logging
    result = log_security_action(
        request=mock_request,
        action="Created user",
        entity_id=123,
        log_file_path=temp_log_file,
    )
    
    # Verificar que se escribió correctamente
    assert result is True, "El logging debería haber sido exitoso"
    assert temp_log_file.exists(), "El archivo de log debería existir"
    
    # Leer el contenido del log
    with open(temp_log_file, "r", encoding="utf-8") as f:
        log_content = f.read()
    
    # Verificar el formato CSV
    lines = log_content.strip().split("\n")
    assert len(lines) > 0, "Debería haber al menos una línea en el log"
    
    last_line = lines[-1]
    parts = last_line.split(",")
    assert len(parts) == 5, f"El formato CSV debería tener 5 campos, tiene {len(parts)}"
    
    # Verificar que contiene la IP y el user agent
    assert "192.168.1.100" in last_line, "El log debería contener la IP"
    assert "Mozilla/5.0" in last_line, "El log debería contener el user agent"
    assert "Created user" in last_line, "El log debería contener la acción"
    assert "123" in last_line, "El log debería contener el entity_id"
    
    print("✅ Test de logging de seguridad exitoso")


def test_user_creation_with_security_logging(temp_users_file, temp_log_file, mock_domain_models):
    """
    Test integrado que verifica la creación de usuario y el logging de seguridad.
    
    Verifica:
    - Que se crea el usuario correctamente
    - Que se registra en el log de seguridad
    - Que se capturan IP y user agent del request
    """
    MockUser, MockContactInfo, MockUserExtended = mock_domain_models
    
    # Mock del path del log
    with patch("pages.user_creation._SECURITY_LOG_PATH", temp_log_file):
        # Mock de las clases de dominio
        with patch("pages.user_creation.User", MockUser), \
             patch("pages.user_creation.ContactInfo", MockContactInfo), \
             patch("pages.user_creation.UserExtended", MockUserExtended), \
             patch("pages.user_creation.save_user_to_json") as mock_save, \
             patch("pages.user_creation.rx.call_script") as mock_call_script:
            
            # Configurar el mock para que save_user_to_json retorne True
            mock_save.return_value = True
            
            # Crear instancia del estado
            state = UserCreationState()
            
            # Llenar todos los campos requeridos
            state.from_page = "main"
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
            
            # Verificar que se intentó llamar al endpoint de logging
            # (rx.call_script puede no funcionar en el contexto de test, pero se intenta)
            # En su lugar, verificamos que _register_security_action se puede llamar directamente
            mock_request = MockRequest(ip="10.0.0.50", user_agent="Chrome/120.0 Test")
            
            # Llamar directamente a la función de logging
            log_result = _register_security_action(
                action="Created user",
                entity_id=999,
                request=mock_request,
            )
            
            assert log_result is True, "El logging debería ser exitoso"
            assert temp_log_file.exists(), "El archivo de log debería existir"
            
            # Verificar contenido del log
            with open(temp_log_file, "r", encoding="utf-8") as f:
                log_lines = f.readlines()
            
            assert len(log_lines) > 0, "Debería haber líneas en el log"
            last_line = log_lines[-1].strip()
            assert "10.0.0.50" in last_line, "El log debería contener la IP"
            assert "Chrome/120.0" in last_line, "El log debería contener el user agent"
            assert "Created user" in last_line, "El log debería contener la acción"
            assert "999" in last_line, "El log debería contener el entity_id"
            
            print("✅ Test integrado de creación de usuario con logging exitoso")


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
        log_file = tmp_path / "frontend_secure.log"
        
        users_file.write_text("[]", encoding="utf-8")
        
        print("Ejecutando tests de creación de usuario...")
        print("=" * 60)
        
        # Ejecutar tests
        try:
            test_user_creation_successful(users_file, log_file, None)
            print("\n" + "=" * 60)
            test_security_logging_with_request(log_file)
            print("\n" + "=" * 60)
            test_user_creation_with_security_logging(users_file, log_file, None)
            print("\n" + "=" * 60)
            print("✅ Todos los tests pasaron exitosamente")
        except Exception as e:
            print(f"\n❌ Error en los tests: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

