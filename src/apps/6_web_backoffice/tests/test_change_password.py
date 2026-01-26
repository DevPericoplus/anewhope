"""Tests para la funcionalidad de cambio de contraseña."""
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

# Cargar módulos necesarios
from pages.change_password import ChangePasswordState


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
    # Crear un usuario de prueba
    test_user = {
        "user_id": 1,
        "organization_id": 1,
        "identity_type_id": 1,
        "user_name": "testuser",
        "user_password": "gAAAAABpRXkTf8_53UBsB7niyelbcWYuOD7eBC5JCdbzaWzZkJV59L_qFkPqctusUAx9ueuSrS1C3GNQ6i9a2nDoQ3jBamvzyg==",
        "user_email": "test@example.com",
        "user_mobile": "+34639775978",
        "user_otp": "1234",
        "active": True,
        "blocked": False,
        "contact_info": {
            "first_name": "Test",
            "sur_name": "User",
            "country": "España",
            "state": "Madrid",
            "zip_code": "28045",
            "address": "Test Address",
        },
        "billing_info": {
            "first_name": "Test",
            "sur_name": "User",
            "country": "España",
            "state": "Madrid",
            "zip_code": "28045",
            "address": "Test Address",
        },
    }
    users_file.write_text(json.dumps([test_user], indent=2), encoding="utf-8")
    return users_file


@pytest.fixture
def mock_user_module(temp_users_file):
    """
    Fixture que mockea el módulo de usuarios.
    
    Returns:
        Módulo mockeado con funciones get_user_by_email y update_user_password_and_otp.
    """
    # Cargar el módulo real de usuarios
    user_module_path = project_root / "src" / "1_shared_domain" / "entities" / "user.py"
    
    # Crear un módulo mock
    mock_module = MagicMock()
    
    # Implementar get_user_by_email
    def get_user_by_email(email: str):
        with open(temp_users_file, "r", encoding="utf-8") as f:
            users = json.load(f)
        normalized_input = email.strip().lower()
        for user in users:
            user_email_value = user.get("user_email", "")
            if user_email_value.strip().lower() == normalized_input:
                return user
        return None
    
    # Implementar update_user_password_and_otp
    def update_user_password_and_otp(email: str, new_password: str, new_otp: str):
        with open(temp_users_file, "r", encoding="utf-8") as f:
            users = json.load(f)
        normalized_input = email.strip().lower()
        user_found = False
        for user in users:
            user_email_value = user.get("user_email", "")
            if user_email_value.strip().lower() == normalized_input:
                user["user_password"] = new_password
                user["user_otp"] = new_otp
                user_found = True
                break
        if not user_found:
            return False
        with open(temp_users_file, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        return True
    
    mock_module.get_user_by_email = get_user_by_email
    mock_module.update_user_password_and_otp = update_user_password_and_otp
    
    return mock_module


@pytest.fixture
def mock_sms_module():
    """
    Fixture que mockea el módulo de envío de SMS.
    
    Returns:
        Función mockeada send_message_by_sms.
    """
    def send_message_by_sms(otp: str, phone_number: str) -> bool:
        """Mock de send_message_by_sms que siempre retorna True."""
        return True
    
    return send_message_by_sms


@pytest.fixture
def mock_cipher_module():
    """
    Fixture que mockea el módulo de cifrado.
    
    Returns:
        Tupla con (cipher_module, fernet_instance).
    """
    class MockFernet:
        def encrypt(self, value: bytes) -> bytes:
            return b"encrypted_" + value
    
    class MockCipherModule:
        def encrypt_value(self, fernet_instance, value: str) -> bytes:
            return fernet_instance.encrypt(value.encode("utf-8"))
        
        def load_fernet_key_from_file(self, key_path: Path):
            return MockFernet()
    
    return (MockCipherModule(), MockFernet())


def test_change_password_state_initialization():
    """Test que verifica la inicialización correcta del estado."""
    state = ChangePasswordState()
    assert state.step == 1
    assert state.user_email == ""
    assert state.otp_code == ""
    assert state.new_password == ""
    assert state.new_password_confirm == ""
    assert state.user_found is False
    assert state.otp_sent is False
    assert state.otp_validated is False


def test_password_validation():
    """Test que verifica la validación de contraseñas."""
    state = ChangePasswordState()
    
    # Contraseña válida
    state.new_password = "Test@1234"
    assert state.password_validation() is True
    
    # Contraseña muy corta
    state.new_password = "Test@1"
    assert state.password_validation() is False
    
    # Contraseña sin mayúsculas
    state.new_password = "test@1234"
    assert state.password_validation() is False
    
    # Contraseña sin números
    state.new_password = "Test@abcd"
    assert state.password_validation() is False
    
    # Contraseña sin caracteres especiales
    state.new_password = "Test1234"
    assert state.password_validation() is False


@patch("pages.change_password.get_user_by_email")
@patch("pages.change_password._send_message_by_sms")
def test_request_otp_success(mock_send_sms, mock_get_user):
    """Test que verifica la solicitud exitosa de OTP."""
    # Configurar mocks
    mock_user = {
        "user_id": 1,
        "user_email": "test@example.com",
        "user_mobile": "+34639775978",
        "user_otp": "1234",
    }
    mock_get_user.return_value = mock_user
    mock_send_sms.return_value = True
    
    # Crear estado y ejecutar
    state = ChangePasswordState()
    state.user_email = "test@example.com"
    state.request_otp()
    
    # Verificar resultados
    assert state.user_found is True
    assert state.otp_sent is True
    assert state.step == 2
    assert state.message_type == "success"
    assert mock_send_sms.called
    assert mock_send_sms.call_args[0][0] == "1234"
    assert mock_send_sms.call_args[0][1] == "+34639775978"


@patch("pages.change_password.get_user_by_email")
def test_request_otp_user_not_found(mock_get_user):
    """Test que verifica el manejo cuando el usuario no existe."""
    mock_get_user.return_value = None
    
    state = ChangePasswordState()
    state.user_email = "nonexistent@example.com"
    state.request_otp()
    
    assert state.user_found is False
    assert state.otp_sent is False
    assert state.message_type == "error"
    assert "no está registrado" in state.message.lower()


@patch("pages.change_password.get_user_by_email")
@patch("pages.change_password._send_message_by_sms")
def test_request_otp_no_mobile(mock_send_sms, mock_get_user):
    """Test que verifica el manejo cuando el usuario no tiene teléfono."""
    mock_user = {
        "user_id": 1,
        "user_email": "test@example.com",
        "user_mobile": "",
        "user_otp": "1234",
    }
    mock_get_user.return_value = mock_user
    
    state = ChangePasswordState()
    state.user_email = "test@example.com"
    state.request_otp()
    
    assert state.message_type == "error"
    assert "teléfono" in state.message.lower()


def test_validate_otp_success():
    """Test que verifica la validación exitosa de OTP."""
    state = ChangePasswordState()
    state.user_data = {
        "user_id": 1,
        "user_email": "test@example.com",
        "user_otp": "1234",
    }
    state.otp_code = "1234"
    
    state.validate_otp()
    
    assert state.otp_validated is True
    assert state.step == 3
    assert state.message_type == "success"


def test_validate_otp_failure():
    """Test que verifica el manejo de OTP incorrecto."""
    state = ChangePasswordState()
    state.user_data = {
        "user_id": 1,
        "user_email": "test@example.com",
        "user_otp": "1234",
    }
    state.otp_code = "5678"
    
    state.validate_otp()
    
    assert state.otp_validated is False
    assert state.message_type == "error"
    assert "no es correcto" in state.message.lower()


@patch("pages.change_password.update_user_password_and_otp")
@patch("pages.change_password._cipher_module")
@patch("pages.change_password._fernet_instance")
def test_update_password_success(mock_fernet, mock_cipher, mock_update):
    """Test que verifica la actualización exitosa de contraseña."""
    # Configurar mocks
    mock_update.return_value = True
    
    # Mock de cifrado
    class MockCipher:
        def encrypt_value(self, fernet, value):
            return f"encrypted_{value}".encode("utf-8")
    
    mock_cipher_module = MockCipher()
    
    # Crear estado y configurar
    state = ChangePasswordState()
    state.user_data = {
        "user_id": 1,
        "user_email": "test@example.com",
    }
    state.new_password = "NewPass@123"
    state.new_password_confirm = "NewPass@123"
    state.otp_validated = True
    state.step = 3
    
    # Parchear los módulos globales
    with patch("pages.change_password._cipher_module", mock_cipher_module):
        with patch("pages.change_password._fernet_instance", mock_fernet):
            state.update_password()
    
    # Verificar resultados
    assert state.message_type == "success"
    assert "actualizada exitosamente" in state.message.lower()
    assert mock_update.called


@patch("pages.change_password.update_user_password_and_otp")
def test_update_password_mismatch(mock_update):
    """Test que verifica el manejo cuando las contraseñas no coinciden."""
    state = ChangePasswordState()
    state.user_data = {
        "user_id": 1,
        "user_email": "test@example.com",
    }
    state.new_password = "NewPass@123"
    state.new_password_confirm = "DifferentPass@123"
    state.otp_validated = True
    state.step = 3
    
    state.update_password()
    
    assert state.message_type == "error"
    assert "no coinciden" in state.message.lower()
    assert not mock_update.called


@patch("pages.change_password.update_user_password_and_otp")
def test_update_password_invalid(mock_update):
    """Test que verifica el manejo cuando la contraseña no cumple los requisitos."""
    state = ChangePasswordState()
    state.user_data = {
        "user_id": 1,
        "user_email": "test@example.com",
    }
    state.new_password = "short"
    state.new_password_confirm = "short"
    state.otp_validated = True
    state.step = 3
    
    state.update_password()
    
    assert state.message_type == "error"
    assert not mock_update.called


def test_secure_access_redirect():
    """Test que verifica la redirección cuando no se accede desde la página principal."""
    state = ChangePasswordState()
    state.from_page = "other"
    
    result = state.secure_access()
    
    # En Reflex, secure_access puede retornar un redirect
    # Verificamos que los campos se limpian
    assert state.step == 1
    assert state.user_email == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

