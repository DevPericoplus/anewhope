import reflex as rx
from typing import Optional, Any
import sys
import random
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Agregar el path para importar módulos del dominio
domain_entities_path = Path(__file__).parent.parent.parent.parent / "1_shared_domain" / "entities"
domain_entities_parent = domain_entities_path.parent

# Agregar tanto el directorio de entities como su padre al path
if str(domain_entities_path) not in sys.path:
    sys.path.insert(0, str(domain_entities_path))
if str(domain_entities_parent) not in sys.path:
    sys.path.insert(0, str(domain_entities_parent))

# Intentar importar las funciones de validación de organización
try:
    import importlib.util
    org_module_path = domain_entities_path / "organization.py"
    if org_module_path.exists():
        spec = importlib.util.spec_from_file_location("organization", org_module_path)
        if spec and spec.loader:
            org_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(org_module)
            get_organization_by_name_exist = org_module.get_organization_by_name_exist
            create_organization = org_module.create_organization
        else:
            get_organization_by_name_exist = None
            create_organization = None
    else:
        get_organization_by_name_exist = None
        create_organization = None
except Exception:
    get_organization_by_name_exist = None
    create_organization = None

# Intentar importar las funciones de validación de usuario
try:
    import importlib.util
    user_module_path = domain_entities_path / "user.py"
    if user_module_path.exists():
        spec = importlib.util.spec_from_file_location("user", user_module_path)
        if spec and spec.loader:
            user_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(user_module)
            get_user_by_email_exist = user_module.get_user_by_email_exist
            get_user_by_mobile_exist = user_module.get_user_by_mobile_exist
        else:
            get_user_by_email_exist = None
            get_user_by_mobile_exist = None
    else:
        get_user_by_email_exist = None
        get_user_by_mobile_exist = None
except Exception:
    get_user_by_email_exist = None
    get_user_by_mobile_exist = None

# Intentar importar las clases de dominio (User, ContactInfo, UserExtended)
User = None
ContactInfo = None
UserExtended = None

try:
    import importlib.util
    domain_models_path = domain_entities_path / "domain_models.py"
    
    if not domain_models_path.exists():
        print(f"ERROR: El archivo domain_models.py no existe en: {domain_models_path}")
        logger.warning(f"El archivo domain_models.py no existe en: {domain_models_path}")
    else:
        print(f"INFO: Cargando domain_models desde: {domain_models_path}")
        logger.debug(f"Intentando cargar domain_models desde: {domain_models_path}")
        
        # Intentar importación directa primero (más simple)
        try:
            # Intentar importar directamente si el path está configurado
            import importlib
            domain_models_module = importlib.import_module("entities.domain_models")
            print("INFO: Importación directa exitosa")
        except ModuleNotFoundError as import_error:
            print(f"INFO: Importación directa falló, usando importlib.util: {import_error}")
            # Si falla, usar importlib.util
            spec = importlib.util.spec_from_file_location(
                "domain_models", 
                str(domain_models_path),
                submodule_search_locations=[str(domain_entities_path)]
            )
            if spec is None:
                error_msg = "No se pudo crear el spec para domain_models"
                print(f"ERROR: {error_msg}")
                logger.error(error_msg)
                raise ImportError(error_msg)
            elif spec.loader is None:
                error_msg = "El loader del spec es None para domain_models"
                print(f"ERROR: {error_msg}")
                logger.error(error_msg)
                raise ImportError(error_msg)
            else:
                domain_models_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(domain_models_module)
                print("INFO: Módulo cargado con importlib.util")
        
        # Verificar que las clases existan en el módulo
        if hasattr(domain_models_module, "User"):
            User = domain_models_module.User
            print("INFO: Clase User cargada exitosamente")
            logger.debug("Clase User cargada exitosamente")
        else:
            error_msg = "La clase User no se encuentra en domain_models"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            print(f"DEBUG: Atributos disponibles en el módulo: {dir(domain_models_module)}")
        
        if hasattr(domain_models_module, "ContactInfo"):
            ContactInfo = domain_models_module.ContactInfo
            print("INFO: Clase ContactInfo cargada exitosamente")
            logger.debug("Clase ContactInfo cargada exitosamente")
        else:
            error_msg = "La clase ContactInfo no se encuentra en domain_models"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
        
        if hasattr(domain_models_module, "UserExtended"):
            UserExtended = domain_models_module.UserExtended
            print("INFO: Clase UserExtended cargada exitosamente")
            logger.debug("Clase UserExtended cargada exitosamente")
        else:
            error_msg = "La clase UserExtended no se encuentra en domain_models"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
                
except Exception as e:
    error_msg = f"Error al importar clases de dominio: {e}"
    print(f"ERROR: {error_msg}")
    print(f"ERROR: Traceback: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    logger.error(error_msg, exc_info=True)
    User = None
    ContactInfo = None
    UserExtended = None

# Importar el adaptador
save_user_to_json = None
try:
    import importlib.util
    # Ruta al adaptador
    current_file_path = Path(__file__)
    adapter_path = current_file_path.parent.parent / "adapters" / "api_client.py"
    
    if not adapter_path.exists():
        print(f"ERROR: El archivo api_client.py no existe en: {adapter_path}")
        logger.warning(f"El archivo api_client.py no existe en: {adapter_path}")
    else:
        print(f"INFO: Cargando adaptador desde: {adapter_path}")
        logger.debug(f"Intentando cargar adaptador desde: {adapter_path}")
        
        # Agregar el directorio de adapters al path si no está
        adapters_dir = str(adapter_path.parent)
        if adapters_dir not in sys.path:
            sys.path.insert(0, adapters_dir)
        
        # Usar importlib.util directamente (los módulos con números no se pueden importar directamente)
        spec = importlib.util.spec_from_file_location(
            "api_client",
            str(adapter_path),
            submodule_search_locations=[adapters_dir]
        )
        if spec is None:
            error_msg = "No se pudo crear el spec para api_client"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            raise ImportError(error_msg)
        elif spec.loader is None:
            error_msg = "El loader del spec es None para api_client"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            raise ImportError(error_msg)
        else:
            api_client_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(api_client_module)
            print("INFO: Adaptador cargado con importlib.util")
        
        # Verificar que la función exista en el módulo
        if hasattr(api_client_module, "save_user_to_json"):
            save_user_to_json = api_client_module.save_user_to_json
            print("INFO: Función save_user_to_json cargada exitosamente")
            logger.debug("Función save_user_to_json cargada exitosamente")
        else:
            error_msg = "La función save_user_to_json no se encuentra en api_client"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            print(f"DEBUG: Atributos disponibles en el módulo: {dir(api_client_module)}")
                
except Exception as e:
    error_msg = f"Error al importar adaptador: {e}"
    print(f"ERROR: {error_msg}")
    print(f"ERROR: Traceback: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    logger.error(error_msg, exc_info=True)
    save_user_to_json = None

# Cargar módulo de seguridad común usando importlib (módulo con nombre que empieza con número)
_common_security_module = None
_log_security_action_function = None

try:
    import importlib.util
    common_security_path = (
        Path(__file__).parent.parent.parent.parent
        / "2_shared_application"
        / "security"
        / "common_security.py"
    )
    if common_security_path.exists():
        spec = importlib.util.spec_from_file_location("common_security", common_security_path)
        if spec and spec.loader:
            _common_security_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_common_security_module)
            _log_security_action_function = getattr(_common_security_module, "log_security_action", None)
            if _log_security_action_function:
                logger.info("Módulo common_security cargado exitosamente con log_security_action")
            else:
                logger.warning("Módulo common_security cargado pero log_security_action no encontrado")
except Exception as e:
    logger.error(f"Error al cargar módulo common_security: {e}")

# Ruta del archivo de log de seguridad para esta aplicación
_SECURITY_LOG_PATH = Path(__file__).parent.parent / "logs" / "frontend_secure.log"

# Cargar módulo de cifrado para cifrar contraseñas
_cipher_module = None
_fernet_instance = None

try:
    import importlib.util
    cipher_module_path = (
        Path(__file__).parent.parent.parent.parent
        / "2_shared_application"
        / "security"
        / "custom_cipher_lib.py"
    )
    if cipher_module_path.exists():
        spec = importlib.util.spec_from_file_location("custom_cipher_lib", cipher_module_path)
        if spec and spec.loader:
            _cipher_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_cipher_module)
            
            # Cargar la clave Fernet
            fernet_key_path = cipher_module_path.parent / "basesecuritypass.json"
            _fernet_instance = _cipher_module.load_fernet_key_from_file(fernet_key_path)
            logger.info("Módulo de cifrado cargado exitosamente")
        else:
            logger.warning("No se pudo cargar el módulo de cifrado")
    else:
        logger.warning("El módulo de cifrado no existe")
except Exception as e:
    logger.error(f"Error al cargar módulo de cifrado: {e}")

# Función para registrar acciones de seguridad (será llamada desde el endpoint API)
def _register_security_action(action: str, entity_id: Optional[int], request: Any) -> bool:
    """
    Función auxiliar para registrar acciones de seguridad.
    Será llamada desde el endpoint API que se creará en web_frontend.py.
    
    Args:
        action: Descripción de la acción realizada.
        entity_id: Identificador opcional de la entidad relacionada.
        request: Objeto de solicitud HTTP (puede ser None).
    
    Returns:
        True si el log se escribió exitosamente, False en caso contrario.
    """
    if _log_security_action_function:
        return _log_security_action_function(
            request=request,
            action=action,
            entity_id=entity_id,
            log_file_path=_SECURITY_LOG_PATH,
        )
    else:
        logger.error("log_security_action_function no está disponible")
        return False

# Importar los colores de la página principal
COLORS = {
    "background": "#1a1a1a",
    "card": "#6B6B6B",
    "foreground": "#f2f2f5",
    "primary": "#22c55e",
    "secondary": "#383854",
    "border": "#000000",
    "input": "#383854",
    "muted_foreground": "#E0E0E0",
    "accent": "#22c55e",
}


class UserCreationState(rx.State):
    """Estado para el formulario de creación de usuario."""
    
    # Parámetro de query string para validar acceso
    from_page: str = ""
    
    # Campos de User
    user_id: str = ""
    organization_id: str = ""
    organization_name: str = ""
    identity_type_id: str = ""
    user_name: str = ""
    user_password: str = ""
    user_password_confirm: str = ""
    user_email: str = ""
    user_mobile: str = ""
    user_otp: str = ""
    active: bool = True
    blocked: bool = False
    
    # Campos de ContactInfo (contact_info)
    contact_first_name: str = ""
    contact_sur_name: str = ""
    contact_country: str = ""
    contact_state: str = ""
    contact_zip_code: str = ""
    contact_address: str = ""
    
    # Campos de ContactInfo (billing_info)
    billing_first_name: str = ""
    billing_sur_name: str = ""
    billing_country: str = ""
    billing_state: str = ""
    billing_zip_code: str = ""
    billing_address: str = ""
    has_different_billing_address: bool = False
    
    # Mensaje de estado
    message: str = ""
    message_type: str = ""  # "success" o "error"
    show_org_error_modal: bool = False  # Controla si se muestra el modal de error de organización
    show_org_creation_modal: bool = False  # Controla si se muestra el modal de creación de organización
    show_password_validation_modal: bool = False  # Controla si se muestra el modal de validación de contraseña
    show_password_match_error_modal: bool = False  # Controla si se muestra el modal de error de coincidencia de contraseñas
    
    # Campos para el formulario de creación de organización
    org_email: str = ""
    org_tlf: str = ""
    org_address: str = ""
    org_country: str = ""
    org_state: str = ""
    
    # Diccionario con los datos del usuario creado (serializable para Reflex)
    created_user: Optional[dict] = None
    
    # Variables para almacenar IP y user agent del request actual
    _current_client_ip: str = ""
    _current_user_agent: str = ""
    
    def secure_access(self):
        """
        Valida el acceso desde la página principal y limpia todos los campos del formulario.
        Se ejecuta automáticamente al cargar la página.
        """
        # Limpiar todos los campos del formulario
        self.user_id = ""
        self.organization_id = ""
        self.organization_name = ""
        self.identity_type_id = ""
        self.user_name = ""
        self.user_password = ""
        self.user_password_confirm = ""
        self.user_email = ""
        self.user_mobile = ""
        self.user_otp = ""
        self.active = True
        self.blocked = False
        
        # Limpiar campos de ContactInfo
        self.contact_first_name = ""
        self.contact_sur_name = ""
        self.contact_country = ""
        self.contact_state = ""
        self.contact_zip_code = ""
        self.contact_address = ""
        
        # Limpiar campos de billing_info
        self.billing_first_name = ""
        self.billing_sur_name = ""
        self.billing_country = ""
        self.billing_state = ""
        self.billing_zip_code = ""
        self.billing_address = ""
        self.has_different_billing_address = False
        
        # Limpiar campos de organización
        self.org_email = ""
        self.org_tlf = ""
        self.org_address = ""
        self.org_country = ""
        self.org_state = ""
        
        # Limpiar mensajes y modales
        self.message = ""
        self.message_type = ""
        self.show_org_error_modal = False
        self.show_org_creation_modal = False
        self.show_password_match_error_modal = False
        self.created_user = None
        
        # Validar acceso desde la página principal
        # Verificar si se accedió desde la página principal usando parámetros de query string
        # En Reflex, los parámetros de query string se pueden obtener del router
        # Si no se accedió desde la página principal (from_page != "main"), redirigir
        # Nota: El parámetro from_page se establece automáticamente desde la URL si existe
        if self.from_page != "main":
            # Redirigir a la página principal si se accede directamente por URL
            return rx.redirect("/")
    
    def log_user_creation_security(self, user_id: int):
        """
        Registra la creación del usuario en el log de seguridad.
        
        En Reflex 0.8.21, podemos obtener IP y user agent desde router_data.headers.
        Usamos estos valores para crear un request mock que se pasa a la función de logging.
        
        Args:
            user_id: Identificador del usuario creado.
        """
        try:
            logger.debug(f"Intentando registrar log de seguridad para usuario {user_id}")
            
            # Crear un objeto request mock con IP y user agent
            class MockRequest:
                """Mock del request HTTP con IP y user agent."""
                def __init__(self, ip: str, user_agent: str):
                    self.headers = {"user-agent": user_agent}
                    self.client = type("Client", (), {"host": ip})()
                    self.scope = {"client": (ip, 0)}
            
            # Intentar obtener IP y user agent desde router_data
            request_mock = None
            ip = None
            user_agent = None
            
            try:
                # En Reflex 0.8.21, podemos acceder a los headers desde router_data
                if hasattr(self, "router_data"):
                    headers = self.router_data.get("headers", {})
                    
                    # Obtener la IP desde x-forwarded-for (para proxies) o usar 127.0.0.1 como fallback
                    ip = headers.get("x-forwarded-for", "127.0.0.1")
                    # Si hay múltiples IPs (proxies), tomar la primera
                    if "," in ip:
                        ip = ip.split(",")[0].strip()
                    
                    # Obtener el User-Agent
                    user_agent = headers.get("user-agent", "Unknown Browser")
                    
                    # Crear request mock con los valores obtenidos
                    request_mock = MockRequest(ip, user_agent)
                    logger.debug(f"IP obtenida desde router_data: {ip}, User agent: {user_agent[:50]}")
                else:
                    logger.debug("router_data no está disponible en el estado")
            except Exception as e:
                logger.debug(f"Error al obtener IP/user agent desde router_data: {e}")
            
            # Registrar usando la función de logging
            if _log_security_action_function:
                result = _register_security_action("Created user", user_id, request_mock)
                if result:
                    logger.info(f"Log de seguridad registrado para usuario {user_id} (IP: {ip or 'N/A'}, UA: {user_agent[:30] if user_agent else 'N/A'})")
                else:
                    logger.warning(f"No se pudo registrar el log de seguridad para usuario {user_id}")
            else:
                logger.error("Función de logging de seguridad no disponible")
        except Exception as e:
            logger.error(f"Error al registrar log de seguridad: {e}", exc_info=True)
    
    def on_mount(self):
        """Se ejecuta automáticamente cuando se monta el componente."""
        # Obtener parámetros de query string del router
        # En Reflex, los parámetros de query string se pueden obtener usando rx.router
        # Si la URL contiene ?from=main, establecer from_page
        try:
            # Obtener la URL actual y extraer parámetros de query string
            # En Reflex 0.8.21, podemos usar el router para obtener los parámetros
            # Por ahora, el parámetro from_page se establece desde la URL si existe
            # Si la URL es /user_creation?from=main, from_page será "main"
            pass
        except Exception:
            pass
        # Ejecutar secure_access que limpiará campos y validará acceso
        self.secure_access()
    
    def close_org_error_modal(self):
        """Cierra el modal de error de organización."""
        self.show_org_error_modal = False
        self.message = ""
        self.message_type = ""
    
    def close_org_creation_modal(self):
        """Cierra el modal de creación de organización."""
        self.show_org_creation_modal = False
        # Limpiar campos del formulario
        self.org_email = ""
        self.org_tlf = ""
        self.org_address = ""
        self.org_country = ""
        self.org_state = ""
    
    def set_org_email(self, value: str):
        self.org_email = value
    
    def set_org_tlf(self, value: str):
        self.org_tlf = value
    
    def set_org_address(self, value: str):
        self.org_address = value
    
    def set_org_country(self, value: str):
        self.org_country = value
    
    def set_org_state(self, value: str):
        self.org_state = value
    
    def save_organization(self):
        """Guarda la nueva organización usando create_organization."""
        try:
            # Validaciones básicas
            if not self.organization_name or not self.organization_name.strip():
                self.message = "El nombre de organización es requerido"
                self.message_type = "error"
                return
            
            if not self.org_email or not self.org_email.strip():
                self.message = "El email de la organización es requerido"
                self.message_type = "error"
                return
            
            # Crear un objeto simple que simule Organization para create_organization
            # create_organization espera un objeto con atributos organization_*
            class SimpleOrganization:
                def __init__(self, name, email, tlf, address, country, state):
                    self.organization_name = name
                    self.organization_email = email
                    self.organization_tlf = tlf
                    self.organization_address = address
                    self.organization_country = country
                    self.organization_state = state
            
            org_obj = SimpleOrganization(
                name=self.organization_name.strip(),
                email=self.org_email.strip(),
                tlf=self.org_tlf.strip() if self.org_tlf else "",
                address=self.org_address.strip() if self.org_address else "",
                country=self.org_country.strip() if self.org_country else "",
                state=self.org_state.strip() if self.org_state else "",
            )
            
            # Llamar a create_organization si está disponible
            if create_organization is None:
                self.message = "Error: función create_organization no disponible"
                self.message_type = "error"
                return
            
            if create_organization(org_obj):
                self.message = f"Organización '{self.organization_name.strip()}' creada exitosamente"
                self.message_type = "success"
                # Cerrar el modal
                self.show_org_creation_modal = False
                # Limpiar campos del formulario
                self.org_email = ""
                self.org_tlf = ""
                self.org_address = ""
                self.org_country = ""
                self.org_state = ""
            else:
                self.message = "Error al guardar la organización"
                self.message_type = "error"
                
        except Exception as e:
            self.message = f"Error al crear la organización: {str(e)}"
            self.message_type = "error"
    
    def set_user_id(self, value: str):
        self.user_id = value
    
    def set_organization_id(self, value: str):
        self.organization_id = value
    
    def set_organization_name(self, value: str):
        self.organization_name = value
    
    def on_organization_name_blur(self):
        """Se ejecuta cuando se pierde el foco en el campo de nombre de organización."""
        # Validar solo cuando se pierde el foco
        if self.organization_name and self.organization_name.strip():
            self.validate_organization_name()
        else:
            # Limpiar mensaje si el campo está vacío
            if self.message_type == "error" and "organización" in self.message.lower():
                self.message = ""
                self.message_type = ""
                self.show_org_error_modal = False
            self.show_org_creation_modal = False
    
    def validate_organization_name(self):
        """Valida si el nombre de organización ya existe cuando cambia el valor."""
        if not self.organization_name or not self.organization_name.strip():
            # Limpiar mensaje si el campo está vacío
            if self.message_type == "error" and "organización" in self.message.lower():
                self.message = ""
                self.message_type = ""
            return  # No validar si está vacío
        
        # Verificar si la función de validación está disponible
        if get_organization_by_name_exist is None:
            return  # No hacer nada si la función no está disponible
        
        try:
            # Verificar si la organización existe
            if get_organization_by_name_exist(self.organization_name.strip()):
                self.message = f"La organización '{self.organization_name.strip()}' ya existe en el sistema"
                self.message_type = "error"
                self.show_org_error_modal = True  # Mostrar el modal
            else:
                # Si la organización NO existe y el campo tiene al menos 3 caracteres, mostrar el modal de creación
                # Solo mostrar si no está ya abierto para evitar múltiples aperturas
                if not self.show_org_creation_modal:
                    self.show_org_creation_modal = True
                # Limpiar mensaje si la validación es exitosa
                if self.message_type == "error" and "organización" in self.message.lower():
                    self.message = ""
                    self.message_type = ""
                    self.show_org_error_modal = False
        except Exception as e:
            # Log del error para debugging
            print(f"Error validando organización: {e}")
    
    def set_identity_type_id(self, value: str):
        self.identity_type_id = value
    
    def set_user_name(self, value: str):
        self.user_name = value
    
    def set_user_password(self, value: str):
        self.user_password = value
    
    def password_validation(self) -> bool:
        """
        Valida que la contraseña cumple con las siguientes reglas:
        - Longitud mínima de 8 caracteres
        - Al menos un carácter en mayúsculas
        - Al menos un carácter numérico
        - Al menos uno de los caracteres especiales: @#|.$%&
        
        Returns:
            bool: True si la contraseña cumple todas las reglas, False en caso contrario
        """
        password = self.user_password
        
        # Validar longitud mínima
        if len(password) < 8:
            return False
        
        # Validar al menos una mayúscula
        if not any(c.isupper() for c in password):
            return False
        
        # Validar al menos un número
        if not any(c.isdigit() for c in password):
            return False
        
        # Validar al menos un carácter especial
        special_chars = "@#|.$%&"
        if not any(c in special_chars for c in password):
            return False
        
        return True
    
    def on_password_blur(self):
        """Se ejecuta cuando se pierde el foco en el campo de contraseña."""
        # Solo validar si hay contenido
        if self.user_password and self.user_password.strip():
            if not self.password_validation():
                self.show_password_validation_modal = True
        else:
            # Si está vacío, cerrar el modal si está abierto
            self.show_password_validation_modal = False
    
    def close_password_validation_modal(self):
        """Cierra el modal de validación de contraseña y devuelve el foco al input de contraseña."""
        self.show_password_validation_modal = False
        # El foco se devolverá mediante JavaScript en el componente del botón
    
    def set_user_password_confirm(self, value: str):
        self.user_password_confirm = value

    def on_password_confirm_blur(self):
        """Se ejecuta cuando se pierde el foco en el campo de confirmación de contraseña."""
        # Validar que ambas contraseñas tengan contenido y coincidan
        if self.user_password_confirm and self.user_password_confirm.strip():
            if self.user_password != self.user_password_confirm:
                self.show_password_match_error_modal = True
            else:
                self.show_password_match_error_modal = False
        else:
            self.show_password_match_error_modal = False

    def close_password_match_error_modal(self):
        """Cierra el modal de error de coincidencia de contraseñas y devuelve el foco al input de confirmación."""
        self.show_password_match_error_modal = False
    
    def set_user_email(self, value: str):
        self.user_email = value
    
    def on_user_email_blur(self):
        """Valida si el email ya existe cuando se pierde el foco."""
        if not self.user_email or not self.user_email.strip():
            # Limpiar mensaje si el campo está vacío
            if self.message_type == "error" and "email" in self.message.lower():
                self.message = ""
                self.message_type = ""
            return  # No validar si está vacío
        
        # Verificar si la función de validación está disponible
        if get_user_by_email_exist is None:
            return  # No hacer nada si la función no está disponible
        
        try:
            # Verificar si el email existe
            if get_user_by_email_exist(self.user_email.strip()):
                self.message = f"El email '{self.user_email.strip()}' ya está registrado en el sistema"
                self.message_type = "error"
            else:
                # Limpiar mensaje si la validación es exitosa
                if self.message_type == "error" and "email" in self.message.lower():
                    self.message = ""
                    self.message_type = ""
        except Exception:
            # En caso de error, no mostrar mensaje para no interrumpir al usuario
            pass
    
    def set_user_mobile(self, value: str):
        self.user_mobile = value
    
    def on_user_mobile_blur(self):
        """Valida si el teléfono ya existe cuando se pierde el foco."""
        if not self.user_mobile or not self.user_mobile.strip():
            # Limpiar mensaje si el campo está vacío
            if self.message_type == "error" and "teléfono" in self.message.lower() or "móvil" in self.message.lower():
                self.message = ""
                self.message_type = ""
            return  # No validar si está vacío
        
        # Verificar si la función de validación está disponible
        if get_user_by_mobile_exist is None:
            return  # No hacer nada si la función no está disponible
        
        try:
            # Verificar si el teléfono existe
            if get_user_by_mobile_exist(self.user_mobile.strip()):
                self.message = f"El teléfono '{self.user_mobile.strip()}' ya está registrado en el sistema"
                self.message_type = "error"
            else:
                # Limpiar mensaje si la validación es exitosa
                if self.message_type == "error" and ("teléfono" in self.message.lower() or "móvil" in self.message.lower()):
                    self.message = ""
                    self.message_type = ""
        except Exception:
            # En caso de error, no mostrar mensaje para no interrumpir al usuario
            pass
    
    def set_user_otp(self, value: str):
        self.user_otp = value
    
    def set_active(self, value: bool):
        self.active = value
    
    def set_blocked(self, value: bool):
        self.blocked = value
    
    def set_contact_first_name(self, value: str):
        self.contact_first_name = value
    
    def set_contact_sur_name(self, value: str):
        self.contact_sur_name = value
    
    def set_contact_country(self, value: str):
        self.contact_country = value
    
    def set_contact_state(self, value: str):
        self.contact_state = value
    
    def set_contact_zip_code(self, value: str):
        self.contact_zip_code = value
    
    def set_contact_address(self, value: str):
        self.contact_address = value
    
    def set_billing_first_name(self, value: str):
        self.billing_first_name = value
    
    def set_billing_sur_name(self, value: str):
        self.billing_sur_name = value
    
    def set_billing_country(self, value: str):
        self.billing_country = value
    
    def set_billing_state(self, value: str):
        self.billing_state = value
    
    def set_billing_zip_code(self, value: str):
        self.billing_zip_code = value
    
    def set_billing_address(self, value: str):
        self.billing_address = value
    
    def set_has_different_billing_address(self, value: bool):
        """Establece si el usuario tiene una dirección de facturación diferente."""
        self.has_different_billing_address = value
    
    def save_user(self):
        """Crea el objeto UserExtended en memoria."""
        try:
            # Generar ID de usuario dinámicamente (usando timestamp como base)
            import time
            user_id_int = int(time.time() * 1000) % 1000000  # ID basado en timestamp
            
            if not self.user_name or not self.user_name.strip():
                self.message = "El nombre de usuario es requerido"
                self.message_type = "error"
                return
            
            if not self.user_password or len(self.user_password) < 8:
                self.message = "La contraseña debe tener al menos 8 caracteres"
                self.message_type = "error"
                return
            
            if not self.user_email or "@" not in self.user_email:
                self.message = "El email es requerido y debe ser válido"
                self.message_type = "error"
                return
            
            # Verificar si el email ya existe
            if get_user_by_email_exist is not None:
                try:
                    if get_user_by_email_exist(self.user_email.strip()):
                        self.message = f"El email '{self.user_email.strip()}' ya está registrado en el sistema"
                        self.message_type = "error"
                        return
                except Exception:
                    pass  # Continuar si hay error en la verificación
            
            if not self.user_mobile or not self.user_mobile.strip():
                self.message = "El número de móvil es requerido"
                self.message_type = "error"
                return
            
            # Verificar si el teléfono ya existe
            if get_user_by_mobile_exist is not None:
                try:
                    if get_user_by_mobile_exist(self.user_mobile.strip()):
                        self.message = f"El teléfono '{self.user_mobile.strip()}' ya está registrado en el sistema"
                        self.message_type = "error"
                        return
                except Exception:
                    pass  # Continuar si hay error en la verificación
            
            # Generar OTP aleatorio de 4 dígitos si no está presente o no es válido
            if not self.user_otp or len(self.user_otp) != 4 or not self.user_otp.isdigit():
                self.user_otp = f"{random.randint(1000, 9999)}"
            
            # Validar campos de contacto
            if not self.contact_first_name or not self.contact_first_name.strip():
                self.message = "El nombre de contacto es requerido"
                self.message_type = "error"
                return
            
            if not self.contact_sur_name or not self.contact_sur_name.strip():
                self.message = "Los apellidos de contacto son requeridos"
                self.message_type = "error"
                return
            
            if not self.contact_country or not self.contact_country.strip():
                self.message = "El país de contacto es requerido"
                self.message_type = "error"
                return
            
            if not self.contact_state or not self.contact_state.strip():
                self.message = "El estado/provincia de contacto es requerido"
                self.message_type = "error"
                return
            
            if not self.contact_zip_code or not self.contact_zip_code.strip():
                self.message = "El código postal de contacto es requerido"
                self.message_type = "error"
                return
            
            if not self.contact_address or not self.contact_address.strip():
                self.message = "La dirección de contacto es requerida"
                self.message_type = "error"
                return
            
            # Convertir IDs a enteros
            try:
                org_id_int = int(self.organization_id) if self.organization_id else 1
                identity_id_int = int(self.identity_type_id) if self.identity_type_id else 1
            except ValueError:
                self.message = "Los IDs deben ser números válidos"
                self.message_type = "error"
                return
            
            # Crear el objeto UserExtended usando las clases de dominio
            if User is None or ContactInfo is None or UserExtended is None:
                self.message = "Error: Las clases de dominio no están disponibles"
                self.message_type = "error"
                return
            
            if save_user_to_json is None:
                self.message = "Error: El adaptador no está disponible"
                self.message_type = "error"
                return
            
            try:
                # Cifrar la contraseña antes de crear el objeto User
                encrypted_password = self.user_password  # Por defecto, sin cifrar
                try:
                    if _cipher_module and _fernet_instance:
                        # Cifrar la contraseña usando el módulo y la instancia Fernet cargados
                        encrypted_password_bytes = _cipher_module.encrypt_value(_fernet_instance, self.user_password)
                        # Convertir bytes a string para almacenar en JSON
                        encrypted_password = encrypted_password_bytes.decode('utf-8')
                        logger.debug("Contraseña cifrada exitosamente")
                    else:
                        logger.warning("El módulo de cifrado no está disponible, la contraseña se guardará sin cifrar")
                except Exception as e:
                    logger.error(f"Error al cifrar la contraseña: {e}")
                    # Continuar sin cifrar si hay error
                
                # Crear objeto User con la contraseña cifrada
                user = User(
                    user_id=user_id_int,
                    organization_id=org_id_int,
                    identity_type_id=identity_id_int,
                    user_name=self.user_name.strip(),
                    password=encrypted_password,
                    email=self.user_email.strip().lower(),
                    mobile=self.user_mobile.strip(),
                    otp=self.user_otp,
                    active=self.active,
                    blocked=self.blocked,
                )
                
                # Crear objeto ContactInfo para información de contacto
                contact_info = ContactInfo(
                    first_name=self.contact_first_name.strip(),
                    sur_name=self.contact_sur_name.strip(),
                    country=self.contact_country.strip(),
                    state=self.contact_state.strip(),
                    zip_code=self.contact_zip_code.strip(),
                    address=self.contact_address.strip(),
                )
                
                # Crear objeto ContactInfo para información de facturación
                # Si no hay dirección de facturación diferente, usar la de contacto
                billing_info = ContactInfo(
                    first_name=self.billing_first_name.strip() if self.billing_first_name.strip() else self.contact_first_name.strip(),
                    sur_name=self.billing_sur_name.strip() if self.billing_sur_name.strip() else self.contact_sur_name.strip(),
                    country=self.billing_country.strip() if self.billing_country.strip() else self.contact_country.strip(),
                    state=self.billing_state.strip() if self.billing_state.strip() else self.contact_state.strip(),
                    zip_code=self.billing_zip_code.strip() if self.billing_zip_code.strip() else self.contact_zip_code.strip(),
                    address=self.billing_address.strip() if self.billing_address.strip() else self.contact_address.strip(),
                )
                
                # Crear objeto UserExtended
                user_extended = UserExtended(
                    user=user,
                    contact_info=contact_info,
                    billing_info=billing_info if self.has_different_billing_address else None,
                )
                
                # Guardar el usuario usando el adaptador
                if save_user_to_json(user_extended):
                    # Convertir UserExtended a diccionario para almacenarlo en el estado (serializable)
                    self.created_user = {
                        "user_id": user_extended.id,
                        "organization_id": user_extended.id_org,
                        "identity_type_id": user_extended.id_type,
                        "user_name": user_extended.user_name,
                        "user_email": user_extended.user_email,
                        "user_mobile": user_extended.user_mobile,
                        "active": user_extended.active,
                        "blocked": user_extended.blocked,
                    }
                    self.message = f"Usuario {self.user_name} creado exitosamente (ID: {user_id_int})"
                    self.message_type = "success"
                    
                    # Registrar la creación del usuario en el log de seguridad
                    # Intentamos obtener IP y user agent desde el cliente usando JavaScript
                    # y luego llamamos al endpoint API
                    self.log_user_creation_security(user_id_int)
                else:
                    self.message = "Error al guardar el usuario en el sistema"
                    self.message_type = "error"
            except Exception as e:
                self.message = f"Error al crear el usuario: {str(e)}"
                self.message_type = "error"
            
        except Exception as e:
            self.message = f"Error al crear el usuario: {str(e)}"
            self.message_type = "error"


def organization_error_modal() -> rx.Component:
    """Modal centrado para mostrar el error de organización duplicada."""
    return rx.cond(
        UserCreationState.show_org_error_modal,
        rx.fragment(
            # Overlay oscuro de fondo
            rx.box(
                width="100vw",
                height="100vh",
                background_color="rgba(0, 0, 0, 0.7)",
                position="fixed",
                top="0",
                left="0",
                z_index="1000",
            ),
            # Modal centrado
            rx.box(
                rx.vstack(
                    rx.heading(
                        "La Organización ya existe en el sistema",
                        size="6",
                        color=COLORS["foreground"],
                        margin_bottom="1em",
                    ),
                    rx.text(
                        UserCreationState.message,
                        color=COLORS["foreground"],
                        font_size="1em",
                        text_align="center",
                        margin_bottom="2em",
                    ),
                    rx.button(
                        "Entendido",
                        on_click=UserCreationState.close_org_error_modal,
                        background_color=COLORS["primary"],
                        color=COLORS["background"],
                        font_weight="bold",
                        padding="0.75em 2em",
                        border_radius="0.5em",
                        width="200px",
                    ),
                    spacing="2",
                    align_items="center",
                    padding="2em",
                ),
                background_color=COLORS["card"],
                border=f"2px solid {COLORS['border']}",
                border_radius="1em",
                box_shadow="0 10px 40px rgba(0, 0, 0, 0.5)",
                position="fixed",
                top="50%",
                left="50%",
                transform="translate(-50%, -50%)",
                z_index="1001",
                min_width="400px",
                max_width="600px",
            ),
        ),
    )


def organization_creation_modal() -> rx.Component:
    """Modal centrado para crear una nueva organización."""
    return rx.cond(
        UserCreationState.show_org_creation_modal,
        rx.fragment(
            # Overlay oscuro de fondo
            rx.box(
                width="100vw",
                height="120vh",
                background_color="rgba(0, 0, 0, 0.7)",
                position="fixed",
                top="0",
                left="0",
                z_index="1000",
            ),
            # Modal centrado con formulario
            rx.box(
                rx.vstack(
                    rx.heading(
                        "Crear Nueva Organización",
                        size="6",
                        color=COLORS["foreground"],
                        margin_bottom="0.5em",
                    ),
                    rx.text(
                        f"Nombre: {UserCreationState.organization_name}",
                        color=COLORS["muted_foreground"],
                        font_size="1em",
                        font_weight="bold",
                        margin_bottom="1.5em",
                    ),
                    # Formulario de organización
                    rx.vstack(
                        rx.vstack(
                            rx.text("Email *", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="email@organizacion.com",
                                on_change=UserCreationState.set_org_email,
                                value=UserCreationState.org_email,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Teléfono", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="+1234567890",
                                on_change=UserCreationState.set_org_tlf,
                                value=UserCreationState.org_tlf,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Dirección", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="Dirección de la organización",
                                on_change=UserCreationState.set_org_address,
                                value=UserCreationState.org_address,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                        ),
                        rx.hstack(
                            rx.vstack(
                                rx.text("País", font_size="0.9em", color=COLORS["muted_foreground"]),
                                rx.input(
                                    placeholder="País",
                                    on_change=UserCreationState.set_org_country,
                                    value=UserCreationState.org_country,
                                    background_color=COLORS["input"],
                                    border_color=COLORS["border"],
                                    color=COLORS["foreground"],
                                    width="100%",
                                    border_radius="5px",
                                ),
                                spacing="1",
                                flex="1",
                            ),
                            rx.vstack(
                                rx.text("Estado/Provincia", font_size="0.9em", color=COLORS["muted_foreground"]),
                                rx.input(
                                    placeholder="Estado o Provincia",
                                    on_change=UserCreationState.set_org_state,
                                    value=UserCreationState.org_state,
                                    background_color=COLORS["input"],
                                    border_color=COLORS["border"],
                                    color=COLORS["foreground"],
                                    width="100%",
                                    border_radius="5px",
                                ),
                                spacing="1",
                                flex="1",
                            ),
                            spacing="2",
                            width="100%",
                            border_radius="5px",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    # Botones
                    rx.hstack(
                        rx.button(
                            "Guardar",
                            on_click=UserCreationState.save_organization,
                            background_color=COLORS["primary"],
                            color=COLORS["background"],
                            font_weight="bold",
                            padding="0.75em 2em",
                            border_radius="0.5em",
                        ),
                        rx.button(
                            "Cancelar",
                            on_click=UserCreationState.close_org_creation_modal,
                            background_color=COLORS["secondary"],
                            color=COLORS["foreground"],
                            font_weight="bold",
                            padding="0.75em 2em",
                            border_radius="0.5em",
                        ),
                        spacing="2",
                        justify_content="center",
                        width="100%",
                        margin_top="1em",
                    ),
                    spacing="2",
                    align_items="center",
                    padding="2em",
                ),
                background_color=COLORS["card"],
                border=f"2px solid {COLORS['border']}",
                border_radius="1em",
                box_shadow="0 10px 40px rgba(0, 0, 0, 0.5)",
                position="fixed",
                top="50%",
                left="50%",
                transform="translate(-50%, -50%)",
                z_index="1001",
                min_width="500px",
                max_width="700px",
                max_height="90vh",
                overflow_y="auto",
            ),
            width="100%",
            height="100%",
            position="fixed",
            top="0",
            left="0",
            z_index="1000",
        ),
    )
def password_match_error_modal() -> rx.Component:
    """Modal centrado para mostrar el error de coincidencia de contraseñas."""
    return rx.cond(
        UserCreationState.show_password_match_error_modal,
        rx.fragment(
            # Overlay oscuro de fondo
            rx.box(
                width="100vw",
                height="100vh",
                background_color="rgba(0, 0, 0, 0.7)",
                position="fixed",
                top="0",
                left="0",
                z_index="1000",
            ),
            # Modal centrado
            rx.box(
                rx.vstack(
                    rx.heading(
                        "Error de Contraseña",
                        size="6",
                        color=COLORS["foreground"],
                        margin_bottom="1em",
                    ),
                    rx.text(
                        "La contraseña no coincide",
                        color=COLORS["foreground"],
                        font_size="1em",
                        text_align="center",
                        margin_bottom="2em",
                    ),
                    rx.button(
                        "Entendido",
                        on_click=UserCreationState.close_password_match_error_modal,
                        background_color=COLORS["primary"],
                        color=COLORS["background"],
                        font_weight="bold",
                        padding="0.75em 2em",
                        border_radius="0.5em",
                        width="200px",
                    ),
                    spacing="2",
                    align_items="center",
                    padding="2em",
                ),
                background_color=COLORS["card"],
                border=f"2px solid {COLORS['border']}",
                border_radius="1em",
                box_shadow="0 10px 40px rgba(0, 0, 0, 0.5)",
                position="fixed",
                top="50%",
                left="50%",
                transform="translate(-50%, -50%)",
                z_index="1001",
                min_width="400px",
                max_width="600px",
            ),
        ),
    )


def password_validation_modal() -> rx.Component:
    """Modal centrado para mostrar las reglas de validación de contraseña."""
    return rx.cond(
        UserCreationState.show_password_validation_modal,
        rx.fragment(
            # Overlay oscuro de fondo
            rx.box(
                width="100vw",
                height="100vh",
                background_color="rgba(0, 0, 0, 0.7)",
                position="fixed",
                top="0",
                left="0",
                z_index="1000",
            ),
            # Modal centrado
            rx.box(
                rx.vstack(
                    rx.heading(
                        "Requisitos de Contraseña",
                        size="6",
                        color=COLORS["foreground"],
                        margin_bottom="1em",
                    ),
                    rx.text(
                        "La contraseña debe cumplir las siguientes reglas:",
                        color=COLORS["muted_foreground"],
                        font_size="1em",
                        margin_bottom="1em",
                    ),
                    rx.vstack(
                        rx.text(
                            "• Longitud mínima de 8 caracteres",
                            color=COLORS["foreground"],
                            font_size="0.95em",
                        ),
                        rx.text(
                            "• Al menos un carácter en mayúsculas",
                            color=COLORS["foreground"],
                            font_size="0.95em",
                        ),
                        rx.text(
                            "• Al menos un carácter numérico",
                            color=COLORS["foreground"],
                            font_size="0.95em",
                        ),
                        rx.text(
                            "• Al menos uno de los siguientes caracteres especiales: @ # | . $ % &",
                            color=COLORS["foreground"],
                            font_size="0.95em",
                        ),
                        spacing="1",
                        align_items="flex-start",
                        margin_bottom="2em",
                    ),
                    rx.button(
                        "Entendido",
                        on_click=UserCreationState.close_password_validation_modal,
                        background_color=COLORS["primary"],
                        color=COLORS["background"],
                        font_weight="bold",
                        padding="0.75em 2em",
                        border_radius="0.5em",
                        width="200px",
                    ),
                    spacing="2",
                    align_items="center",
                    padding="2em",
                ),
                background_color=COLORS["card"],
                border=f"2px solid {COLORS['border']}",
                border_radius="1em",
                box_shadow="0 10px 40px rgba(0, 0, 0, 0.5)",
                position="fixed",
                top="50%",
                left="50%",
                transform="translate(-50%, -50%)",
                z_index="1001",
                min_width="400px",
                max_width="600px",
            ),
        ),
    )


def user_creation_page() -> rx.Component:
    """Página de creación de usuario."""
    # Ejecutar secure_access al cargar la página
    # on_mount se ejecutará automáticamente cuando se monte el componente
    return rx.vstack(
        # Modal de error de organización (si está activo)
        organization_error_modal(),
        # Modal de creación de organización (si está activo)
        organization_creation_modal(),
        # Modal de validación de contraseña (si está activo)
        password_validation_modal(),
        # Modal de error de coincidencia de contraseñas (si está activo)
        password_match_error_modal(),
        # Header
        rx.hstack(
            rx.heading("Crear Nuevo Usuario", size="6", color=COLORS["foreground"]),
            width="100%",
            padding="1em",
            background_color=COLORS["card"],
            border_bottom=f"1px solid {COLORS['border']}",
        ),
        # Formulario
        rx.vstack(
            rx.vstack(
                # Sección: Información de Usuario
                rx.heading("Información de Usuario", size="6", color=COLORS["foreground"], margin_bottom="1em"),
                rx.vstack(
                    rx.hstack(
                        rx.vstack(
                            rx.text("Nombre de Usuario *", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="Ingrese el nombre de usuario",
                                on_change=UserCreationState.set_user_name,
                                value=UserCreationState.user_name,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                            flex="1",
                        ),
                        rx.vstack(
                            rx.text("Nombre de organización", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="Ingrese el nombre de la organización",
                                on_change=UserCreationState.set_organization_name,
                                on_blur=UserCreationState.on_organization_name_blur,
                                value=UserCreationState.organization_name,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                            flex="1",
                        ),
                        spacing="4",
                        width="100%",
                    ),
                    rx.hstack(
                        rx.vstack(
                            rx.text("Contraseña *", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="Mínimo 8 caracteres",
                                type_="password",
                                id="user_password_input",
                                on_change=UserCreationState.set_user_password,
                                on_blur=UserCreationState.on_password_blur,
                                value=UserCreationState.user_password,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                            flex="1",
                        ),
                        rx.vstack(
                            rx.text("Repita la contraseña *", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="Repita la contraseña",
                                type_="password",
                                id="user_password_confirm_input",
                                on_change=UserCreationState.set_user_password_confirm,
                                on_blur=UserCreationState.on_password_confirm_blur,
                                value=UserCreationState.user_password_confirm,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                            flex="1",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    rx.hstack(
                        rx.vstack(
                            rx.text("Email *", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="usuario@ejemplo.com",
                                on_change=UserCreationState.set_user_email,
                                on_blur=UserCreationState.on_user_email_blur,
                                value=UserCreationState.user_email,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                            flex="1",
                        ),
                        rx.vstack(
                            rx.text("Teléfono Móvil *", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="+1234567890",
                                on_change=UserCreationState.set_user_mobile,
                                on_blur=UserCreationState.on_user_mobile_blur,
                                value=UserCreationState.user_mobile,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                            flex="1",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    spacing="2",
                ),
                padding="1.5em",
                background_color=COLORS["card"],
                border=f"1px solid {COLORS['border']}",
                border_radius="0.5em",
                width="100%",
                margin_bottom="1em",
            ),
            # Sección: Información de Contacto
            rx.vstack(
                rx.heading("Información de Contacto", size="6", color=COLORS["foreground"], margin_bottom="1em"),
                rx.vstack(
                    rx.hstack(
                        rx.vstack(
                            rx.text("Nombre *", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="Nombre",
                                on_change=UserCreationState.set_contact_first_name,
                                value=UserCreationState.contact_first_name,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                            flex="1",
                        ),
                        rx.vstack(
                            rx.text("Apellidos *", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="Apellidos",
                                on_change=UserCreationState.set_contact_sur_name,
                                value=UserCreationState.contact_sur_name,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                            flex="1",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    rx.hstack(
                        rx.vstack(
                            rx.text("País *", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="País",
                                on_change=UserCreationState.set_contact_country,
                                value=UserCreationState.contact_country,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                            flex="1",
                        ),
                        rx.vstack(
                            rx.text("Estado/Provincia *", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="Estado o Provincia",
                                on_change=UserCreationState.set_contact_state,
                                value=UserCreationState.contact_state,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                            flex="1",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("Código Postal *", font_size="0.9em", color=COLORS["muted_foreground"]),
                        rx.input(
                            placeholder="Código Postal",
                            on_change=UserCreationState.set_contact_zip_code,
                            value=UserCreationState.contact_zip_code,
                            background_color=COLORS["input"],
                            border_color=COLORS["border"],
                            color=COLORS["foreground"],
                            width="100%",
                            border_radius="5px",
                        ),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Dirección *", font_size="0.9em", color=COLORS["muted_foreground"]),
                        rx.input(
                            placeholder="Dirección completa",
                            on_change=UserCreationState.set_contact_address,
                            value=UserCreationState.contact_address,
                            background_color=COLORS["input"],
                            border_color=COLORS["border"],
                            color=COLORS["foreground"],
                            width="110%",
                            border_radius="5px",
                        ),
                        spacing="1",
                        width="110%",
                    ),
                    rx.checkbox(
                        "Tengo una dirección de facturación diferente",
                        checked=UserCreationState.has_different_billing_address,
                        on_change=UserCreationState.set_has_different_billing_address,
                        color=COLORS["foreground"],
                        margin_top="1em",
                    ),
                    spacing="2",
                ),
                padding="1.5em",
                background_color=COLORS["card"],
                border=f"1px solid {COLORS['border']}",
                border_radius="0.5em",
                width="100%",
                margin_bottom="1em",
            ),
            # Sección: Información de Facturación (Opcional) - Solo se muestra si el checkbox está marcado
            rx.cond(
                UserCreationState.has_different_billing_address,
                rx.vstack(
                    rx.heading("Información de Facturación (Opcional)", size="6", color=COLORS["foreground"], margin_bottom="1em"),
                    rx.text(
                        "Si no se completa, se usará la información de contacto",
                        font_size="0.9em",
                        color=COLORS["muted_foreground"],
                        margin_bottom="1em",
                    ),
                rx.vstack(
                    rx.hstack(
                        rx.vstack(
                            rx.text("Nombre", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="Nombre de facturación",
                                on_change=UserCreationState.set_billing_first_name,
                                value=UserCreationState.billing_first_name,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                            flex="1",
                        ),
                        rx.vstack(
                            rx.text("Apellidos", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="Apellidos de facturación",
                                on_change=UserCreationState.set_billing_sur_name,
                                value=UserCreationState.billing_sur_name,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                            flex="1",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    rx.hstack(
                        rx.vstack(
                            rx.text("País", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="País de facturación",
                                on_change=UserCreationState.set_billing_country,
                                value=UserCreationState.billing_country,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                            flex="1",
                        ),
                        rx.vstack(
                            rx.text("Estado/Provincia", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="Estado o Provincia de facturación",
                                on_change=UserCreationState.set_billing_state,
                                value=UserCreationState.billing_state,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                            flex="1",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("Código Postal", font_size="0.9em", color=COLORS["muted_foreground"]),
                        rx.input(
                            placeholder="Código Postal de facturación",
                            on_change=UserCreationState.set_billing_zip_code,
                            value=UserCreationState.billing_zip_code,
                            background_color=COLORS["input"],
                            border_color=COLORS["border"],
                            color=COLORS["foreground"],
                            width="100%",
                            border_radius="5px",
                        ),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Dirección", font_size="0.9em", color=COLORS["muted_foreground"]),
                        rx.input(
                            placeholder="Dirección de facturación",
                            on_change=UserCreationState.set_billing_address,
                            value=UserCreationState.billing_address,
                            background_color=COLORS["input"],
                            border_color=COLORS["border"],
                            color=COLORS["foreground"],
                            width="110%",
                            border_radius="5px",
                        ),
                        spacing="1",
                        width="110%",
                    ),
                    spacing="2",
                ),
                    padding="1.5em",
                    background_color=COLORS["card"],
                    border=f"1px solid {COLORS['border']}",
                    border_radius="0.5em",
                    width="100%",
                    margin_bottom="1em",
                ),
            ),
            # Mensaje de estado (solo para mensajes que no sean de organización)
            # Si show_org_error_modal es True, no mostrar el mensaje normal (se muestra en el modal)
            rx.cond(
                rx.cond(
                    UserCreationState.message != "",
                    rx.cond(
                        UserCreationState.show_org_error_modal,
                        False,  # No mostrar si el modal está activo
                        True,   # Mostrar si no es error de organización
                    ),
                    False,
                ),
                rx.box(
                    rx.text(
                        UserCreationState.message,
                        color=rx.cond(
                            UserCreationState.message_type == "success",
                            COLORS["primary"],
                            "#ff4444",
                        ),
                        font_size="0.9em",
                        font_weight="bold",
                    ),
                    padding="1em",
                    background_color=COLORS["card"],
                    border=f"1px solid {COLORS['border']}",
                    border_radius="0.5em",
                    width="100%",
                    margin_bottom="1em",
                ),
            ),
            spacing="2",
            padding="2em",
            width="100%",
            max_width="1200px",
            margin="0 auto",
        ),
        # Botones de acción
        rx.hstack(
            rx.button(
                "Guardar",
                on_click=UserCreationState.save_user,
                background_color=COLORS["primary"],
                color=COLORS["background"],
                font_weight="bold",
                padding="0.75em 2em",
                border_radius="0.5em",
            ),
            rx.link(
                rx.button(
                    "Regresar",
                    background_color=COLORS["secondary"],
                    color=COLORS["foreground"],
                    font_weight="bold",
                    padding="0.75em 2em",
                    border_radius="0.5em",
                ),
                href="/",
            ),
            spacing="4",
            justify_content="center",
            padding="2em",
            width="100%",
        ),
        # Script para devolver el foco al input de contraseña cuando se cierra el modal
        rx.script(
            """
            // Observar cambios en el estado del modal y devolver el foco cuando se cierre
            if (typeof window.previousPasswordModalState === 'undefined') {
                window.previousPasswordModalState = false;
            }
            const checkModalState = () => {
                // El estado se actualiza en el servidor, así que usamos un pequeño delay
                setTimeout(() => {
                    const input = document.getElementById('user_password_input');
                    if (input) {
                        input.focus();
                    }
                }, 150);
            };
            // Ejecutar el check periódicamente cuando el modal está visible
            setInterval(() => {
                const modal = document.querySelector('[data-modal="password_validation"]');
                if (modal && modal.style.display !== 'none' && !window.previousPasswordModalState) {
                    window.previousPasswordModalState = true;
                } else if ((!modal || modal.style.display === 'none') && window.previousPasswordModalState) {
                    window.previousPasswordModalState = false;
                    checkModalState();
                }
            }, 100);
            """,
        ),
        # Script para devolver el foco al input de confirmación de contraseña cuando se cierra el modal
        rx.script(
            """
            // Observar cambios en el estado del modal de coincidencia y devolver el foco cuando se cierre
            if (typeof window.previousPasswordMatchModalState === 'undefined') {
                window.previousPasswordMatchModalState = false;
            }
            const checkPasswordMatchModalState = () => {
                // El estado se actualiza en el servidor, así que usamos un pequeño delay
                setTimeout(() => {
                    const input = document.getElementById('user_password_confirm_input');
                    if (input) {
                        input.focus();
                    }
                }, 150);
            };
            // Ejecutar el check periódicamente cuando el modal está visible
            setInterval(() => {
                // Buscar el modal por su contenido único (texto "La contraseña no coincide")
                const modals = document.querySelectorAll('[style*="z-index: 1001"]');
                let passwordMatchModal = null;
                for (let modal of modals) {
                    if (modal.textContent && modal.textContent.includes('La contraseña no coincide')) {
                        passwordMatchModal = modal;
                        break;
                    }
                }
                if (passwordMatchModal && passwordMatchModal.style.display !== 'none' && !window.previousPasswordMatchModalState) {
                    window.previousPasswordMatchModalState = true;
                } else if ((!passwordMatchModal || passwordMatchModal.style.display === 'none') && window.previousPasswordMatchModalState) {
                    window.previousPasswordMatchModalState = false;
                    checkPasswordMatchModalState();
                }
            }, 100);
            """,
        ),
        background_color=COLORS["background"],
        width="100%",
        min_height="100vh",
        spacing="0",
    )


