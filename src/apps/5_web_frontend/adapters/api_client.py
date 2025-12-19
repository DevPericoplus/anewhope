"""Adaptador para comunicación con la capa de dominio."""
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Ruta al módulo de dominio de usuarios
_domain_entities_path = (
    Path(__file__).parent.parent.parent.parent / "1_shared_domain" / "entities"
)
_user_module_path = _domain_entities_path / "user.py"

# Cargar el módulo de dominio de usuarios
_create_user_function = None
if _user_module_path.exists():
    try:
        spec = importlib.util.spec_from_file_location("user", _user_module_path)
        if spec and spec.loader:
            user_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(user_module)
            _create_user_function = user_module.create_user
    except Exception as e:
        logger.error(f"Error al cargar el módulo de usuarios: {e}")


def save_user_to_json(user_extended: Any) -> bool:
    """
    Guarda un usuario UserExtended en el archivo users.json a través del adaptador.
    
    Convierte el objeto UserExtended a un diccionario y lo pasa a la función
    create_user de la capa de dominio.
    
    Args:
        user_extended: Objeto UserExtended a guardar.
    
    Returns:
        True si el usuario se guardó exitosamente, False en caso contrario.
    """
    if _create_user_function is None:
        logger.error("La función create_user no está disponible")
        return False
    
    try:
        # Convertir UserExtended a diccionario
        user_dict = _user_extended_to_dict(user_extended)
        
        # Llamar a la función de dominio
        return _create_user_function(user_dict)
    except Exception as e:
        logger.error(f"Error al guardar usuario a través del adaptador: {e}")
        return False


def _user_extended_to_dict(user_extended: Any) -> dict[str, Any]:
    """
    Convierte un objeto UserExtended a un diccionario.
    
    Args:
        user_extended: Objeto UserExtended a convertir.
    
    Returns:
        Diccionario con los datos del usuario.
    """
    # Extraer información de contacto
    contact_info = user_extended.contact_info
    billing_info = user_extended.billing_info
    
    return {
        "user_id": user_extended.id,
        "organization_id": user_extended.id_org,
        "identity_type_id": user_extended.id_type,
        "user_name": user_extended.user_name,
        "user_password": user_extended.user_password,
        "user_email": user_extended.user_email,
        "user_mobile": user_extended.user_mobile,
        "user_otp": user_extended.user_otp,
        "active": user_extended.active,
        "blocked": user_extended.blocked,
        "contact_info": {
            "first_name": contact_info.first_name,
            "sur_name": contact_info.sur_name,
            "country": contact_info.country,
            "state": contact_info.state,
            "zip_code": contact_info.zip_code,
            "address": contact_info.address,
        },
        "billing_info": {
            "first_name": billing_info.first_name,
            "sur_name": billing_info.sur_name,
            "country": billing_info.country,
            "state": billing_info.state,
            "zip_code": billing_info.zip_code,
            "address": billing_info.address,
        },
    }

