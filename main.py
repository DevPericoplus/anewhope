"""Punto de entrada principal del proyecto Anewhope."""
import importlib.util
import logging
import sys
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Importar valores protegidos de forma explícita
try:
    from protected_values import global_shared_key_raw  # noqa: E402
except ImportError as e:
    logger.warning(f"No se pudo importar protected_values: {e}")
    global_shared_key_raw = None

# Agregar src al path para importar módulos
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Importar módulo de seguridad desde la nueva ubicación usando importlib
security_module_path = (
    project_root / "src" / "2_shared_application" / "security" / "custom_cipher_lib.py"
)
spec = importlib.util.spec_from_file_location("custom_cipher_lib", security_module_path)
if spec is None or spec.loader is None:
    raise ImportError(f"No se pudo cargar el módulo de seguridad desde {security_module_path}")

security = importlib.util.module_from_spec(spec)
spec.loader.exec_module(security)

# Constantes
READY_TO_USE = True
BASIC_STRING_FOR_CHECKS = "This@2025"
SECURITY_LOCAL_FOLDER = "src/2_shared_application/security"
SECURITY_FILE_NAME = "basesecuritypass.json"


def main() -> None:
    """Función principal del programa."""
    logger.info("After close the door always exists a new hope")
    logger.info("Verificando el estado actual")

    if READY_TO_USE:
        logger.info("El sistema está listo para usar")
        logger.info(f"Sistema operativo: {sys.platform}")
    else:
        logger.warning("El sistema necesita iniciarse para poder estar listo para usar")

    # Uso de seguridad
    if security.basic_check_access(BASIC_STRING_FOR_CHECKS):
        logger.info("El sistema de cifrado está disponible")
    else:
        logger.warning("El sistema de cifrado no está disponible")

    security_path = project_root / SECURITY_LOCAL_FOLDER / SECURITY_FILE_NAME
    if security_path.exists():
        logger.info("El archivo de seguridad está disponible")
    else:
        logger.warning("El archivo de seguridad no está disponible")

    # Valor solo para verificación
    insecure_value_to_encrypt = "This@2026"
    logger.info(f"Valor original a cifrar solo para verificación: {insecure_value_to_encrypt}")
    logger.info("--------------------------------")

    # Iniciar el proceso de seguridad
    secret_key_file = project_root / SECURITY_LOCAL_FOLDER / SECURITY_FILE_NAME

    if secret_key_file.exists():
        fernet_key = security.load_fernet_key_from_file(secret_key_file)
        logger.debug(f"Clave Fernet: {fernet_key}")
        logger.info("--------------------------------")

        encrypted_value = security.encrypt_value(fernet_key, insecure_value_to_encrypt)
        logger.info(f"Valor cifrado: {encrypted_value}")
        logger.info("--------------------------------")

        decrypted_value, _ = security.decrypt_value(fernet_key, encrypted_value)
        logger.info(
            f"Valor original recuperado del valor cifrado: {decrypted_value}"
        )
    else:
        logger.warning(f"Error: el archivo {secret_key_file} no existe")
        security.initialize_fernet_environment()
        logger.info("Archivo Fernet creado")
        fernet_key = security.load_fernet_key_from_file(secret_key_file)
        logger.debug(f"Clave Fernet: {fernet_key}")
        encrypted_value = security.encrypt_value(fernet_key, insecure_value_to_encrypt)
        logger.info(f"Valor cifrado: {encrypted_value}")
        logger.info("--------------------------------")
        decrypted_value, _ = security.decrypt_value(fernet_key, encrypted_value)
        logger.info(
            f"Valor original recuperado del valor cifrado: {decrypted_value}"
        )


if __name__ == "__main__":
    main()
