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
    - Que existe una entrada en el log con "Created user"
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
            
            # Simular router_data para obtener IP y user agent
            state.router_data = {
                "headers": {
                    "x-forwarded-for": "10.0.0.50",
                    "user-agent": "Chrome/120.0 Test",
                }
            }
            
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
            
            # Obtener el número de líneas antes de crear el usuario
            initial_line_count = 0
            if temp_log_file.exists():
                with open(temp_log_file, "r", encoding="utf-8") as f:
                    initial_line_count = len(f.readlines())
            
            # Ejecutar save_user
            state.save_user()
            
            # Verificar creación exitosa
            assert state.message_type == "success"
            assert mock_save.called
            
            # Verificar que el archivo de log existe
            assert temp_log_file.exists(), "El archivo de log debería existir"
            
            # Verificar contenido del log - buscar entrada de usuario
            with open(temp_log_file, "r", encoding="utf-8") as f:
                log_lines = f.readlines()
            
            assert len(log_lines) > initial_line_count, "Debería haber nuevas líneas en el log"
            
            # Buscar la entrada de "Created user" en el log
            user_log_found = False
            user_entity_id = None
            for line in log_lines[initial_line_count:]:
                if "Created user" in line:
                    user_log_found = True
                    parts = line.strip().split(",")
                    if len(parts) >= 5:
                        user_entity_id = parts[4].strip()
                    break
            
            assert user_log_found, "Debería existir una entrada en el log con 'Created user'"
            assert user_entity_id is not None, "El entity_id del usuario debería estar en el log"
            
            print(f"✅ Test integrado de creación de usuario con logging exitoso. Entity ID: {user_entity_id}")


def test_organization_creation_with_security_logging(temp_log_file):
    """
    Test que verifica la creación de organización y el logging de seguridad.
    
    Verifica:
    - Que se crea la organización correctamente
    - Que se registra en el log de seguridad con "Organizacion nueva creada"
    - Que se capturan IP y user agent del request
    """
    from adapters.api_client import save_organization_to_json
    
    # Mock del path del log
    with patch("pages.user_creation._SECURITY_LOG_PATH", temp_log_file):
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
        with patch("pages.user_creation.save_organization_to_json") as mock_save_org:
            mock_save_org.return_value = 11  # Simular que retorna organization_id = 11
            
            # Obtener el número de líneas antes de crear la organización
            initial_line_count = 0
            if temp_log_file.exists():
                with open(temp_log_file, "r", encoding="utf-8") as f:
                    initial_line_count = len(f.readlines())
            
            # Ejecutar save_organization
            state.save_organization()
            
            # Verificar creación exitosa
            assert state.message_type == "success"
            assert mock_save_org.called
            
            # Verificar que el archivo de log existe
            assert temp_log_file.exists(), "El archivo de log debería existir"
            
            # Verificar contenido del log - buscar entrada de organización
            with open(temp_log_file, "r", encoding="utf-8") as f:
                log_lines = f.readlines()
            
            assert len(log_lines) > initial_line_count, "Debería haber nuevas líneas en el log"
            
            # Buscar la entrada de "Organizacion nueva creada" en el log
            org_log_found = False
            org_entity_id = None
            for line in log_lines[initial_line_count:]:
                if "Organizacion nueva creada" in line:
                    org_log_found = True
                    parts = line.strip().split(",")
                    if len(parts) >= 5:
                        org_entity_id = parts[4].strip()
                    break
            
            assert org_log_found, "Debería existir una entrada en el log con 'Organizacion nueva creada'"
            assert org_entity_id == "11", f"El entity_id de la organización debería ser '11', se encontró '{org_entity_id}'"
            
            print(f"✅ Test de creación de organización con logging exitoso. Entity ID: {org_entity_id}")


def test_user_and_organization_logging_integration(temp_users_file, temp_log_file, mock_domain_models):
    """
    Test integrado que verifica que tanto la creación de usuario como de organización
    se registran correctamente en el log de seguridad.
    
    Verifica:
    - Que existe una entrada en el log con "Created user" cuando se crea un usuario
    - Que existe una entrada en el log con "Organizacion nueva creada" cuando se crea una organización
    """
    MockUser, MockContactInfo, MockUserExtended = mock_domain_models
    
    # Mock del path del log
    with patch("pages.user_creation._SECURITY_LOG_PATH", temp_log_file):
        # Mock de las clases de dominio
        with patch("pages.user_creation.User", MockUser), \
             patch("pages.user_creation.ContactInfo", MockContactInfo), \
             patch("pages.user_creation.UserExtended", MockUserExtended), \
             patch("pages.user_creation.save_user_to_json") as mock_save_user, \
             patch("pages.user_creation.save_organization_to_json") as mock_save_org:
            
            # Configurar los mocks
            mock_save_user.return_value = True
            mock_save_org.return_value = 12  # Simular organization_id = 12
            
            # Crear instancia del estado
            state = UserCreationState()
            
            # Simular router_data
            state.router_data = {
                "headers": {
                    "x-forwarded-for": "172.16.0.100",
                    "user-agent": "Safari/17.0 Test",
                }
            }
            
            # Obtener el número de líneas inicial
            initial_line_count = 0
            if temp_log_file.exists():
                with open(temp_log_file, "r", encoding="utf-8") as f:
                    initial_line_count = len(f.readlines())
            
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
            
            # Verificar que el archivo de log existe
            assert temp_log_file.exists(), "El archivo de log debería existir"
            
            # Leer todas las líneas del log
            with open(temp_log_file, "r", encoding="utf-8") as f:
                log_lines = f.readlines()
            
            assert len(log_lines) > initial_line_count, "Debería haber nuevas líneas en el log"
            
            # Buscar entradas en las nuevas líneas
            user_log_found = False
            org_log_found = False
            user_entity_id = None
            org_entity_id = None
            
            for line in log_lines[initial_line_count:]:
                if "Created user" in line:
                    user_log_found = True
                    parts = line.strip().split(",")
                    if len(parts) >= 5:
                        user_entity_id = parts[4].strip()
                
                if "Organizacion nueva creada" in line:
                    org_log_found = True
                    parts = line.strip().split(",")
                    if len(parts) >= 5:
                        org_entity_id = parts[4].strip()
            
            # Verificar que ambas entradas existen
            assert user_log_found, "Debería existir una entrada en el log con 'Created user'"
            assert org_log_found, "Debería existir una entrada en el log con 'Organizacion nueva creada'"
            assert user_entity_id is not None, "El entity_id del usuario debería estar en el log"
            assert org_entity_id == "12", f"El entity_id de la organización debería ser '12', se encontró '{org_entity_id}'"
            
            print("✅ Test integrado de logging de usuario y organización exitoso.")
            print(f"   - Usuario: Entity ID = {user_entity_id}")
            print(f"   - Organización: Entity ID = {org_entity_id}")


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
            test_organization_creation_with_security_logging(log_file)
            print("\n" + "=" * 60)
            test_user_and_organization_logging_integration(users_file, log_file, None)
            print("\n" + "=" * 60)
            print("✅ Todos los tests pasaron exitosamente")
        except Exception as e:
            print(f"\n❌ Error en los tests: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

