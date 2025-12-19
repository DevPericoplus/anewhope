"""Tests para la funcionalidad de envío de SMS usando la API de Infobip."""
import sys
from pathlib import Path

# Añadir el directorio raíz del proyecto al path para imports relativos
test_file_path = Path(__file__)
project_root = test_file_path.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
import importlib.util

# Cargar dinámicamente el módulo common_security
common_security_path = project_root / "src" / "2_shared_application" / "security" / "common_security.py"
spec = importlib.util.spec_from_file_location("common_security", common_security_path)
if spec and spec.loader:
    common_security = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(common_security)
else:
    raise ImportError(f"No se pudo cargar el módulo common_security desde {common_security_path}")


def test_send_sms_with_otp():
    """
    Test que envía un mensaje SMS con código OTP al número de teléfono especificado.
    
    Este test envía un SMS real usando la API de Infobip, por lo que requiere:
    - Credenciales válidas en protected_values.py
    - Conexión a internet
    - Una cuenta de Infobip activa
    """
    # Datos del test
    phone_number = "+34639775978"
    otp_code = "6969"
    
    print(f"\n{'='*60}")
    print("TEST DE ENVÍO DE SMS CON INFOBIP")
    print(f"{'='*60}")
    print(f"Número de teléfono: {phone_number}")
    print(f"Código OTP: {otp_code}")
    print(f"{'='*60}\n")
    
    # Intentar enviar el SMS
    try:
        result = common_security.send_message_by_sms(otp_code, phone_number)
        
        if result:
            print("✅ SMS enviado exitosamente")
            print(f"   El mensaje con OTP '{otp_code}' fue enviado a {phone_number}")
        else:
            print("❌ Error al enviar el SMS")
            print("   Revisa los logs para más detalles")
        
        # El test pasa si la función retorna True
        assert result, "El envío del SMS falló"
        
    except Exception as e:
        print(f"❌ Error durante el test: {e}")
        raise


def test_send_sms_invalid_otp():
    """
    Test que verifica que la función rechaza OTPs inválidos.
    """
    phone_number = "+34639775978"
    
    # Test con OTP vacío
    result = common_security.send_message_by_sms("", phone_number)
    assert not result, "La función debería rechazar un OTP vacío"
    
    # Test con OTP de longitud incorrecta
    result = common_security.send_message_by_sms("123", phone_number)
    assert not result, "La función debería rechazar un OTP de 3 dígitos"
    
    result = common_security.send_message_by_sms("12345", phone_number)
    assert not result, "La función debería rechazar un OTP de 5 dígitos"
    
    # Test con OTP que contiene letras
    result = common_security.send_message_by_sms("12ab", phone_number)
    assert not result, "La función debería rechazar un OTP con letras"
    
    print("✅ Validación de OTP funciona correctamente")


def test_send_sms_invalid_phone():
    """
    Test que verifica que la función rechaza números de teléfono inválidos.
    """
    otp_code = "6969"
    
    # Test con número sin prefijo internacional
    result = common_security.send_message_by_sms(otp_code, "639775978")
    assert not result, "La función debería rechazar un número sin prefijo +"
    
    # Test con número vacío
    result = common_security.send_message_by_sms(otp_code, "")
    assert not result, "La función debería rechazar un número vacío"
    
    print("✅ Validación de número de teléfono funciona correctamente")


if __name__ == "__main__":
    # Ejecutar el test principal
    print("Ejecutando test de envío de SMS...")
    test_send_sms_with_otp()
    print("\nEjecutando tests de validación...")
    test_send_sms_invalid_otp()
    test_send_sms_invalid_phone()
    print("\n✅ Todos los tests completados")

