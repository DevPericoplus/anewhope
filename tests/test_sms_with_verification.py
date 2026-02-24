#!/usr/bin/env python3
"""
Test directo de envío de SMS con verificación de delivery status.
"""
import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Agregar rutas necesarias
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

# Cargar protected_values
import importlib.util
protected_values_path = project_root / "infrastructure" / "environments" / "macbook" / "protected_values.py"
spec = importlib.util.spec_from_file_location("protected_values", protected_values_path)
protected_values = importlib.util.module_from_spec(spec)
spec.loader.exec_module(protected_values)

# Cargar common_security con delivery checker
common_security_path = project_root / "src" / "2_shared_application" / "security" / "common_security.py"
spec = importlib.util.spec_from_file_location("common_security", common_security_path)
common_security = importlib.util.module_from_spec(spec)

# Inyectar protected_values en el namespace antes de cargar
sys.modules['protected_values'] = protected_values
spec.loader.exec_module(common_security)

def main():
    print("=" * 70)
    print("TEST DE ENVÍO DE SMS CON VERIFICACIÓN DE DELIVERY STATUS")
    print("=" * 70)
    print()

    # Datos de prueba
    test_otp = "7777"
    test_phone = "+34639775978"

    print(f"📱 Número destino: {test_phone}")
    print(f"🔢 OTP de prueba: {test_otp}")
    print(f"⏳ Enviando SMS y verificando entrega (puede tardar hasta 30 segundos)...")
    print()

    try:
        # Llamar a la función de envío de SMS (ahora con verificación integrada)
        result = common_security.send_message_by_sms(test_otp, test_phone)

        print()
        print("=" * 70)
        if result:
            print("✅ SMS ENTREGADO EXITOSAMENTE AL DISPOSITIVO")
            print()
            print("El mensaje fue:")
            print("1. Enviado a Infobip ✅")
            print("2. Aceptado por Infobip ✅")
            print("3. Entregado al operador móvil ✅")
            print("4. Entregado al dispositivo del destinatario ✅")
            print()
            print("Verifica que el SMS llegó al móvil")
        else:
            print("❌ EL SMS NO FUE ENTREGADO")
            print()
            print("Posibles causas:")
            print("- El mensaje fue rechazado por el operador")
            print("- Número de destino inválido o bloqueado")
            print("- Timeout esperando confirmación de entrega")
            print("- Problema con el sender ID o cuenta de Infobip")
        print("=" * 70)

        # Verificar log
        log_file = project_root / "src" / "apps" / "5_web_frontend" / "logs" / "frontend_secure.log"
        if log_file.exists():
            print()
            print("Últimas entradas del log de seguridad:")
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-3:]:
                    if "SMS enviado" in line:
                        print(f"  {line.strip()}")

        return 0 if result else 1

    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ EXCEPCIÓN AL ENVIAR SMS: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
