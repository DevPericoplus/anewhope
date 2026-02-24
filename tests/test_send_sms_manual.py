#!/usr/bin/env python3
"""
Script para probar el envío de SMS a través de Infobip.
Útil para verificar que la API funciona correctamente y ver transacciones en el portal.
"""
import sys
from pathlib import Path

from tests.helpers import load_module_from_path, get_project_root

common_security_module = load_module_from_path(
    "common_security",
    "src/2_shared_application/security/common_security.py",
)
send_message_by_sms = common_security_module.send_message_by_sms

def main():
    """Envía un SMS de prueba."""
    print("=" * 60)
    print("TEST DE ENVÍO DE SMS VIA INFOBIP")
    print("=" * 60)
    print()

    # Datos de prueba
    test_otp = "9999"
    test_phone = "+34639775978"

    print(f"📱 Número destino: {test_phone}")
    print(f"🔢 OTP de prueba: {test_otp}")
    print(f"📤 Enviando SMS a través de Infobip...")
    print()

    try:
        # Llamar a la función de envío de SMS
        result = send_message_by_sms(test_otp, test_phone)

        print()
        print("=" * 60)
        if result:
            print("✅ SMS ENVIADO EXITOSAMENTE")
            print()
            print("Verifica en el portal de Infobip:")
            print("1. Ve a 'Registro de transacciones de la API'")
            print("2. Busca mensajes recientes al número +34639775978")
            print("3. Revisa el estado del mensaje (Status)")
            print("4. Revisa la descripción del estado")
            print()
            print("Estados posibles:")
            print("  - PENDING_ACCEPTED: Aceptado, en proceso de entrega")
            print("  - DELIVERED: Entregado exitosamente")
            print("  - REJECTED: Rechazado (revisar motivo)")
            print("  - UNDELIVERABLE: No se pudo entregar")
        else:
            print("❌ ERROR AL ENVIAR SMS")
            print()
            print("Revisa los logs para más detalles:")
            print("  tail -30 src/apps/5_web_frontend/logs/frontend_secure.log")
        print("=" * 60)

        return 0 if result else 1

    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ EXCEPCIÓN AL ENVIAR SMS: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
