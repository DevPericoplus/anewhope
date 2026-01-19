"""Módulo de utilidades criptográficas para cifrado y descifrado de valores sensibles."""
import json
import base64
import logging
import sys
from pathlib import Path
from typing import Optional, Union

from cryptography.fernet import Fernet

# Configurar logging
logger = logging.getLogger(__name__)

# Constantes
SECRET_KEY_FILE_NAME = "basesecuritypass.json"
PROJECT_ROOT_LEVELS_UP = 4


def _get_project_root() -> Path:
    """Obtiene la ruta raíz del proyecto."""
    return Path(__file__).parent.parent.parent.parent


def _get_secret_key_file_path() -> Path:
    """Obtiene la ruta completa del archivo de clave secreta."""
    return Path(__file__).parent / SECRET_KEY_FILE_NAME


def basic_check_access(basic_string_for_checks: str) -> bool:
    """
    Verifica el acceso básico mediante una cadena de autenticación.

    Args:
        basic_string_for_checks: Cadena de autenticación a verificar.

    Returns:
        True si la cadena es válida, False en caso contrario.
    """
    return basic_string_for_checks == "This@2025"


def load_global_shared_key_raw() -> Optional[str]:
    """
    Carga la clave compartida global desde protected_values.py.

    Returns:
        La clave compartida global como string, o None si hay error.
    """
    try:
        project_root = _get_project_root()
        sys.path.insert(0, str(project_root))
        from protected_values import global_shared_key_raw  # noqa: E402

        logger.info(f"Clave compartida global cargada exitosamente: {global_shared_key_raw[:10]}...")
        return global_shared_key_raw
    except ImportError as e:
        logger.error(f"Error al importar global_shared_key_raw desde protected_values.py: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al cargar global_shared_key_raw: {e}")
        return None


def create_fernet_key(global_shared_key_raw: Optional[str]) -> str:
    """
    Crea una clave Fernet a partir de una cadena de clave en bruto.

    Args:
        global_shared_key_raw: Clave compartida global (no se usa actualmente, se genera nueva).

    Returns:
        Clave Fernet generada como string decodificado.
    """
    key = Fernet.generate_key()
    logger.debug(f"Clave Fernet generada (bytes): {key}")
    key_str = key.decode()
    logger.debug(f"Clave Fernet decodificada (string): {key_str}")
    return key_str


def encrypt_value(encrypt_key: Union[str, Fernet], value_to_encrypt: Union[str, bytes]) -> bytes:
    """
    Cifra un valor usando una clave Fernet.

    Args:
        encrypt_key: Clave Fernet como string o objeto Fernet.
        value_to_encrypt: Valor a cifrar como string o bytes.

    Returns:
        Valor cifrado como bytes.
    """
    logger.debug("Cifrando la cadena...")

    # Convertir string a objeto Fernet si es necesario
    if isinstance(encrypt_key, str):
        fernet_key_bytes = encrypt_key.encode()
        fernet_instance = Fernet(fernet_key_bytes)
    else:
        fernet_instance = encrypt_key

    # Convertir valor a bytes si es string
    if isinstance(value_to_encrypt, str):
        value_bytes = value_to_encrypt.encode()
    else:
        value_bytes = value_to_encrypt

    encrypted_value = fernet_instance.encrypt(value_bytes)
    logger.debug("Valor cifrado exitosamente")
    return encrypted_value


def _create_empty_file(file_path: Path) -> bool:
    """
    Crea un archivo vacío.

    Args:
        file_path: Ruta del archivo a crear.

    Returns:
        True si se creó exitosamente.
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        return True
    except OSError as e:
        logger.error(f"Error al crear archivo vacío {file_path}: {e}")
        return False


def store_fernet_key_to_file(encrypted_value: str, file_path: Optional[Path] = None) -> bool:
    """
    Almacena la clave Fernet en formato JSON.

    Args:
        encrypted_value: Clave Fernet a almacenar.
        file_path: Ruta del archivo (opcional, usa la ruta por defecto si no se proporciona).

    Returns:
        True si se almacenó exitosamente, False en caso contrario.
    """
    if file_path is None:
        file_path = _get_secret_key_file_path()

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        data_to_save = {"fernet_key": encrypted_value}
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=4)

        logger.info(f"Clave Fernet almacenada en '{file_path}' exitosamente.")
        logger.debug(f"Clave almacenada: {encrypted_value[:10]}... (parte de la clave)")
        return True
    except (OSError, json.JSONEncodeError) as e:
        logger.error(f"Error al escribir el archivo: {e}")
        return False


def load_fernet_key_from_file(encrypted_value_file: Optional[Path] = None) -> Fernet:
    """
    Carga la clave Fernet desde un archivo JSON.

    Args:
        encrypted_value_file: Ruta del archivo (opcional, usa la ruta por defecto si no se proporciona).

    Returns:
        Objeto Fernet inicializado con la clave cargada.
    """
    if encrypted_value_file is None:
        encrypted_value_file = _get_secret_key_file_path()

    try:
        with open(encrypted_value_file, "r", encoding="utf-8") as f:
            secret_data_loaded = json.load(f)
        fernet_key = secret_data_loaded["fernet_key"]
        fernet_instance = Fernet(fernet_key)
        logger.info("Clave Fernet recuperada y nuevo objeto Fernet creado.")
        return fernet_instance

    except FileNotFoundError:
        logger.warning(f"El archivo '{encrypted_value_file}' no fue encontrado. Generando nueva clave.")
        return _generate_and_store_new_key()

    except json.JSONDecodeError:
        logger.warning(f"El archivo '{encrypted_value_file}' no es un JSON válido. Generando nueva clave.")
        return _generate_and_store_new_key()

    except Exception as e:
        logger.error(f"Error al cargar la clave Fernet desde el archivo: {e}")
        return _generate_and_store_new_key()


def _generate_and_store_new_key() -> Fernet:
    """
    Genera y almacena una nueva clave Fernet.

    Returns:
        Objeto Fernet inicializado con la nueva clave.
    """
    global_shared_key_raw = load_global_shared_key_raw()
    if global_shared_key_raw:
        master_secret_key = create_fernet_key(global_shared_key_raw)
        store_fernet_key_to_file(master_secret_key)
        return Fernet(master_secret_key.encode())
    else:
        # Generar una clave aleatoria si no se puede cargar la clave compartida
        random_key = Fernet.generate_key()
        store_fernet_key_to_file(random_key.decode())
        return Fernet(random_key)


def initialize_fernet_environment() -> Fernet:
    """
    Inicializa el entorno Fernet creando el archivo de clave si no existe.

    Returns:
        Objeto Fernet inicializado.
    """
    secret_key_file = _get_secret_key_file_path()
    _create_empty_file(secret_key_file)

    try:
        global_shared_key_raw = load_global_shared_key_raw()
        if global_shared_key_raw:
            master_secret_key = create_fernet_key(global_shared_key_raw)
            store_fernet_key_to_file(master_secret_key)
            logger.info(f"Clave compartida global cargada exitosamente: {global_shared_key_raw[:10]}...")
            return Fernet(master_secret_key.encode())
        else:
            return _generate_and_store_new_key()
    except Exception as e:
        logger.error(f"Error al inicializar el entorno Fernet: {e}")
        logger.error("Fallo al crear una nueva clave maestra secreta")
        return _generate_and_store_new_key()


def verify_encrypted_value(fernet_instance: Fernet, encrypted_value: bytes) -> bool:
    """
    Verifica que un valor cifrado corresponde a la clave Fernet proporcionada.

    Args:
        fernet_instance: Instancia de Fernet con la clave.
        encrypted_value: Valor cifrado a verificar.

    Returns:
        True si el valor es válido y puede ser descifrado, False en caso contrario.
    """
    try:
        # Intentar descifrar para verificar
        fernet_instance.decrypt(encrypted_value)
        logger.debug("El valor está cifrado y verificado")
        return True
    except Exception as e:
        logger.warning(f"El valor no está cifrado o verificado: {e}")
        return False


def decrypt_value(
    fernet_instance: Fernet, cipher_value_encrypted: bytes
) -> tuple[bytes, str]:
    """
    Descifra un valor cifrado usando una instancia Fernet.

    Args:
        fernet_instance: Instancia de Fernet con la clave de descifrado.
        cipher_value_encrypted: Valor cifrado a descifrar.

    Returns:
        Tupla con (valor descifrado como bytes, valor cifrado como string).
        El segundo valor es una representación segura del cifrado: se intenta
        UTF-8 y, si falla, se usa base64.
    """
    try:
        insecure_values = fernet_instance.decrypt(cipher_value_encrypted)
        encrypted_value_str = _bytes_to_safe_str(cipher_value_encrypted)
        logger.debug(f"Valores inseguros: {cipher_value_encrypted}")
        logger.debug(f"Valor no cifrado: {encrypted_value_str}")
        return insecure_values, encrypted_value_str
    except Exception as e:
        logger.error(f"Error al descifrar: {e}")
        secure_value_encrypted = _bytes_to_safe_str(cipher_value_encrypted)
        logger.debug(f"Valor cifrado seguro: {secure_value_encrypted}")
        return b"", secure_value_encrypted


def _bytes_to_safe_str(value: bytes) -> str:
    """Convierte bytes a string de forma segura (UTF-8 o base64)."""

    try:
        return value.decode("utf-8")
    except UnicodeDecodeError:
        # Evita errores con bytes no UTF-8
        return base64.urlsafe_b64encode(value).decode("ascii")
