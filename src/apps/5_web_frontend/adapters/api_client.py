"""Adaptador para comunicación con la capa de dominio."""
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Ruta al módulo de dominio de usuarios y organizaciones
_domain_entities_path = (
    Path(__file__).parent.parent.parent.parent / "1_shared_domain" / "entities"
)
_user_module_path = _domain_entities_path / "user.py"
_organization_module_path = _domain_entities_path / "organization.py"

# Cargar el módulo de dominio de usuarios
_create_user_function = None
_get_user_by_name_exist_function = None
if _user_module_path.exists():
    try:
        spec = importlib.util.spec_from_file_location("user", _user_module_path)
        if spec and spec.loader:
            user_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(user_module)
            _create_user_function = user_module.create_user
            _get_user_by_name_exist_function = getattr(user_module, "get_user_by_name_exist", None)
    except Exception as e:
        logger.error(f"Error al cargar el módulo de usuarios: {e}")

# Cargar el módulo de dominio de organizaciones
_create_organization_function = None
_get_organization_by_name_exist_function = None
if _organization_module_path.exists():
    try:
        spec = importlib.util.spec_from_file_location("organization", _organization_module_path)
        if spec and spec.loader:
            organization_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(organization_module)
            _create_organization_function = organization_module.create_organization
            _get_organization_by_name_exist_function = getattr(
                organization_module, "get_organization_by_name_exist", None
            )
    except Exception as e:
        logger.error(f"Error al cargar el módulo de organizaciones: {e}")


def check_user_name_exists(user_name: str) -> bool:
    """
    Verifica si existe un usuario con el nombre de usuario dado.
    
    Utiliza la función get_user_by_name_exist del módulo de dominio.
    
    Args:
        user_name: Nombre de usuario a verificar.
    
    Returns:
        True si el usuario existe, False en caso contrario.
    """
    if _get_user_by_name_exist_function is None:
        logger.warning("La función get_user_by_name_exist no está disponible")
        return False
    
    try:
        return _get_user_by_name_exist_function(user_name)
    except Exception as e:
        logger.error(f"Error al verificar nombre de usuario: {e}")
        return False


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


def check_organization_name_exists(organization_name: str) -> bool:
    """
    Verifica si existe una organización con el nombre dado.
    
    Utiliza la función get_organization_by_name_exist del módulo de dominio.
    
    Args:
        organization_name: Nombre de la organización a verificar.
    
    Returns:
        True si la organización existe, False en caso contrario.
    """
    if _get_organization_by_name_exist_function is None:
        logger.warning("La función get_organization_by_name_exist no está disponible")
        return False
    
    try:
        return _get_organization_by_name_exist_function(organization_name)
    except Exception as e:
        logger.error(f"Error al verificar nombre de organización: {e}")
        return False


def save_organization_to_json(organization_data: dict[str, Any]) -> int | None:
    """
    Guarda una organización en el archivo organizations.json a través del adaptador.
    
    Convierte el diccionario de datos de organización a un objeto simple
    y lo pasa a la función create_organization de la capa de dominio.
    
    Args:
        organization_data: Diccionario con los datos de la organización.
            Debe contener las siguientes claves:
            - organization_name (str): Nombre de la organización
            - organization_email (str): Email de la organización
            - organization_tlf (str, opcional): Teléfono de la organización
            - organization_address (str, opcional): Dirección de la organización
            - organization_country (str, opcional): País de la organización
            - organization_state (str, opcional): Estado/Provincia de la organización
    
    Returns:
        organization_id (int) si la organización se guardó exitosamente, None en caso contrario.
    """
    if _create_organization_function is None:
        logger.error("La función create_organization no está disponible")
        return None
    
    try:
        # Crear un objeto simple que simule Organization para create_organization
        # create_organization espera un objeto con atributos organization_*
        class SimpleOrganization:
            def __init__(self, name: str, email: str, tlf: str = "", address: str = "", country: str = "", state: str = ""):
                self.organization_name = name
                self.organization_email = email
                self.organization_tlf = tlf
                self.organization_address = address
                self.organization_country = country
                self.organization_state = state
        
        org_obj = SimpleOrganization(
            name=organization_data.get("organization_name", "").strip(),
            email=organization_data.get("organization_email", "").strip(),
            tlf=organization_data.get("organization_tlf", "").strip(),
            address=organization_data.get("organization_address", "").strip(),
            country=organization_data.get("organization_country", "").strip(),
            state=organization_data.get("organization_state", "").strip(),
        )
        
        # Llamar a la función de dominio
        if _create_organization_function(org_obj):
            # Obtener el organization_id de la organización recién creada
            # Buscar la organización por nombre en el archivo JSON
            import json
            org_file_path = (
                Path(__file__).parent.parent.parent.parent
                / "2_shared_application"
                / "moks"
                / "organizations.json"
            )
            if org_file_path.exists():
                try:
                    with open(org_file_path, "r", encoding="utf-8") as f:
                        orgs = json.load(f)
                    # Buscar la organización por nombre (normalizado)
                    org_name = organization_data.get("organization_name", "").strip()
                    for org in orgs:
                        if org.get("organization_name", "").strip() == org_name:
                            org_id = org.get("organization_id")
                            if isinstance(org_id, int):
                                logger.info(f"Organización creada con ID: {org_id}")
                                return org_id
                    logger.warning(f"No se encontró el ID de la organización '{org_name}' después de crearla")
                except Exception as e:
                    logger.error(f"Error al leer organizations.json para obtener el ID: {e}")
            return None
        else:
            return None
    except Exception as e:
        logger.error(f"Error al guardar organización a través del adaptador: {e}")
        return None

