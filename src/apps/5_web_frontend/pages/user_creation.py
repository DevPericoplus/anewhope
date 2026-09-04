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

create_organization = None

# Intentar importar el adaptador para organizaciones
try:
    import importlib.util
    adapter_path = Path(__file__).parent.parent / "adapters" / "api_client.py"
    if adapter_path.exists():
        spec = importlib.util.spec_from_file_location("api_client", adapter_path)
        if spec and spec.loader:
            api_client_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(api_client_module)
            if hasattr(api_client_module, "check_organization_name_exists"):
                check_organization_name_exists = api_client_module.check_organization_name_exists
            else:
                check_organization_name_exists = None
            if hasattr(api_client_module, "save_organization_to_json"):
                save_organization_to_json = api_client_module.save_organization_to_json
            else:
                save_organization_to_json = None
            if hasattr(api_client_module, "create_organization"):
                create_organization = api_client_module.create_organization
            else:
                create_organization = None
            print("INFO: Funciones de organización del adaptador cargadas exitosamente")
            logger.debug("Funciones de organización del adaptador cargadas exitosamente")
        else:
            check_organization_name_exists = None
            save_organization_to_json = None
            create_organization = None
            logger.warning("No se pudo cargar el adaptador de organizaciones")
    else:
        check_organization_name_exists = None
        save_organization_to_json = None
        create_organization = None
        logger.warning("El adaptador no existe")
except Exception as e:
    error_msg = f"Error al importar adaptador de organizaciones: {e}"
    print(f"ERROR: {error_msg}")
    print(f"ERROR: Traceback: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    logger.error(error_msg, exc_info=True)
    check_organization_name_exists = None
    save_organization_to_json = None
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
log_security_action = None
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
        
        # Verificar que las funciones existan en el módulo
        if hasattr(api_client_module, "save_user_to_json"):
            save_user_to_json = api_client_module.save_user_to_json
            print("INFO: Función save_user_to_json cargada exitosamente")
            logger.debug("Función save_user_to_json cargada exitosamente")
        else:
            error_msg = "La función save_user_to_json no se encuentra en api_client"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            print(f"DEBUG: Atributos disponibles en el módulo: {dir(api_client_module)}")

        if hasattr(api_client_module, "log_security_action"):
            log_security_action = api_client_module.log_security_action
            print("INFO: Función log_security_action cargada exitosamente")
            logger.debug("Función log_security_action cargada exitosamente")
        else:
            log_security_action = None
            logger.warning("La función log_security_action no se encuentra en api_client")
        
        # Cargar función para verificar duplicados de nombre de usuario
        if hasattr(api_client_module, "check_user_name_exists"):
            check_user_name_exists = api_client_module.check_user_name_exists
            print("INFO: Función check_user_name_exists cargada exitosamente")
            logger.debug("Función check_user_name_exists cargada exitosamente")
        else:
            check_user_name_exists = None
            logger.warning("La función check_user_name_exists no se encuentra en api_client")
                
except Exception as e:
    error_msg = f"Error al importar adaptador: {e}"
    print(f"ERROR: {error_msg}")
    print(f"ERROR: Traceback: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    logger.error(error_msg, exc_info=True)
    save_user_to_json = None
    check_user_name_exists = None
    log_security_action = None

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

def _log_security_action(action: str, entity_id: Optional[int], ip: str, user_agent: str) -> None:
    """Envía el log de seguridad al middleware."""

    if log_security_action is None:
        logger.warning("log_security_action no está disponible")
        return
    try:
        result = log_security_action(action, entity_id, ip, user_agent)
        if not result:
            logger.warning("No se pudo registrar el log de seguridad en el middleware")
    except Exception as exc:
        logger.error(f"Error al registrar log en middleware: {exc}", exc_info=True)

from portal_crt import COLORS, CRT_SHELL_CLASS

MODAL_SURFACE = COLORS.get("modal", "#061206")
MODAL_OVERLAY = "rgba(0, 0, 0, 0.88)"
LABEL_FONT_SIZE = "1.1em"
BODY_FONT_SIZE = "1.05em"
USERNAME_REQUIREMENTS = (
    "Mínimo 3 caracteres, máximo 20 caracteres",
    "Solo letras, números y guiones bajos (_)",
    "Sin espacios en blanco",
)
PASSWORD_REQUIREMENTS = (
    "Mínimo 8 caracteres",
    "Al menos una letra mayúscula",
    "Al menos un número",
    "Al menos un carácter especial (@ # | . $ % &)",
)


def _field_label(text: str) -> rx.Component:
    """Etiqueta de campo con tipografía de registro."""
    return rx.text(
        text,
        font_size=LABEL_FONT_SIZE,
        color=COLORS["primary"],
        font_weight="bold",
    )


def _text_input(**kwargs) -> rx.Component:
    """Input de registro con tamaño y contraste CRT."""
    return rx.input(
        size="3",
        width="100%",
        border_radius="6px",
        class_name="crt-input",
        background_color=COLORS["input"],
        border_color=COLORS["border"],
        color=COLORS["foreground"],
        **kwargs,
    )


def _modal_overlay(z_index: str = "1000") -> rx.Component:
    """Fondo oscuro opaco detrás de un modal."""
    return rx.box(
        width="100vw",
        height="100vh",
        background_color=MODAL_OVERLAY,
        position="fixed",
        top="0",
        left="0",
        z_index=z_index,
    )


def _modal_panel(
    content: rx.Component,
    *,
    min_width: str = "440px",
    max_width: str = "640px",
    z_index: str = "1001",
) -> rx.Component:
    """Contenedor de modal con fondo opaco para leer el texto."""
    return rx.box(
        content,
        class_name="crt-modal-surface crt-panel",
        background_color=MODAL_SURFACE,
        border=f"2px solid {COLORS['border']}",
        border_radius="0.85em",
        box_shadow="0 16px 48px rgba(0, 0, 0, 0.85)",
        position="fixed",
        top="50%",
        left="50%",
        transform="translate(-50%, -50%)",
        z_index=z_index,
        min_width=min_width,
        max_width=max_width,
        max_height="90vh",
        overflow_y="auto",
    )


def _collapsible_requirements(
    title: str,
    items: tuple[str, ...],
    is_open,
    toggle,
) -> rx.Component:
    """Acordeón de requisitos contraído por defecto."""
    return rx.vstack(
        rx.box(
            rx.hstack(
                rx.text(
                    title,
                    font_size=LABEL_FONT_SIZE,
                    font_weight="bold",
                    color=COLORS["primary"],
                ),
                rx.cond(
                    is_open,
                    rx.icon("chevron-down", size=20, color=COLORS["primary"]),
                    rx.icon("chevron-right", size=20, color=COLORS["primary"]),
                ),
                justify="between",
                align_items="center",
                width="100%",
            ),
            class_name="crt-accordion-trigger",
            on_click=toggle,
            cursor="pointer",
            width="100%",
        ),
        rx.cond(
            is_open,
            rx.vstack(
                *[
                    rx.hstack(
                        rx.text("•", color=COLORS["primary"], font_weight="bold"),
                        rx.text(
                            item,
                            font_size=BODY_FONT_SIZE,
                            color=COLORS["foreground"],
                        ),
                        spacing="2",
                        align_items="start",
                    )
                    for item in items
                ],
                spacing="2",
                class_name="crt-accordion-body",
                width="100%",
            ),
        ),
        spacing="0",
        width="100%",
    )


class UserCreationState(rx.State):
    """Estado para el formulario de creación de usuario."""
    
    # Parámetro de query string para validar acceso
    from_page: str = ""
    
    # Campos de User
    user_id: str = ""
    organization_id: str = ""
    organization_name: str = ""
    identity_type_id: str = ""
    account_kind: str = ""
    organization_acronym: str = ""
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
    show_username_validation_modal: bool = False  # Controla si se muestra el modal de validación de nombre de usuario
    show_username_duplicate_modal: bool = False  # Controla si se muestra el modal de error de nombre de usuario duplicado
    show_account_kind_modal: bool = True
    show_contact_modal: bool = False
    show_username_requirements: bool = False
    show_password_requirements: bool = False
    
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
        self.account_kind = ""
        self.organization_acronym = ""
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
        self.show_username_validation_modal = False
        self.show_username_duplicate_modal = False
        self.show_account_kind_modal = True
        self.show_contact_modal = False
        self.show_username_requirements = False
        self.show_password_requirements = False
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
            
            # Intentar obtener IP y user agent desde router_data
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
                    
                    logger.debug(f"IP obtenida desde router_data: {ip}, User agent: {user_agent[:50]}")
                else:
                    logger.debug("router_data no está disponible en el estado")
            except Exception as e:
                logger.debug(f"Error al obtener IP/user agent desde router_data: {e}")
            
            if ip is None:
                ip = "127.0.0.1"
            if user_agent is None:
                user_agent = "Unknown Browser"
            _log_security_action("Created user", user_id, ip, user_agent)
        except Exception as e:
            logger.error(f"Error al registrar log de seguridad: {e}", exc_info=True)
    
    def log_organization_creation_security(self, organization_id: int):
        """
        Registra la creación de la organización en el log de seguridad.
        
        En Reflex 0.8.21, podemos obtener IP y user agent desde router_data.headers.
        Usamos estos valores para crear un request mock que se pasa a la función de logging.
        
        Args:
            organization_id: Identificador de la organización creada.
        """
        try:
            logger.debug(f"Intentando registrar log de seguridad para organización {organization_id}")
            
            # Intentar obtener IP y user agent desde router_data
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
                    
                    logger.debug(f"IP obtenida desde router_data: {ip}, User agent: {user_agent[:50]}")
                else:
                    logger.debug("router_data no está disponible en el estado")
            except Exception as e:
                logger.debug(f"Error al obtener IP/user agent desde router_data: {e}")
            
            if ip is None:
                ip = "127.0.0.1"
            if user_agent is None:
                user_agent = "Unknown Browser"
            _log_security_action("Organizacion nueva creada", organization_id, ip, user_agent)
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
        """Guarda la nueva organización usando el adaptador."""
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
            
            # Verificar que el adaptador esté disponible
            save_org = create_organization or save_organization_to_json
            if save_org is None:
                self.message = "Error: adaptador de organizaciones no disponible"
                self.message_type = "error"
                logger.error("El adaptador save_organization_to_json no está disponible")
                return
            
            # Crear diccionario con los datos de la organización
            organization_data = {
                "organization_name": self.organization_name.strip(),
                "organization_email": self.org_email.strip(),
                "organization_tlf": self.org_tlf.strip() if self.org_tlf else "",
                "organization_address": self.org_address.strip() if self.org_address else "",
                "organization_country": self.org_country.strip() if self.org_country else "",
                "organization_state": self.org_state.strip() if self.org_state else "",
            }
            
            # Llamar al adaptador para guardar la organización
            created = save_org(organization_data)
            organization_id = (
                created.get("organization_id") if isinstance(created, dict) else created
            )
            if organization_id is not None:
                if isinstance(created, dict):
                    self.organization_acronym = str(
                        created.get("organization_acronym") or ""
                    )
                self.message = f"Organización '{self.organization_name.strip()}' creada exitosamente"
                self.message_type = "success"
                logger.info(f"Organización '{self.organization_name.strip()}' creada exitosamente a través del adaptador con ID: {organization_id}")
                
                # Asignar el ID de la organización creada al formulario de usuario
                self.organization_id = str(organization_id)
                
                # Registrar la creación en el log de seguridad
                self.log_organization_creation_security(organization_id)
                
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
                logger.error("Error al guardar la organización a través del adaptador")
                
        except Exception as e:
            error_msg = f"Error al crear la organización: {str(e)}"
            self.message = error_msg
            self.message_type = "error"
            logger.error(error_msg, exc_info=True)
    
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
        """Valida si el nombre de organización ya existe usando el adaptador."""
        if not self.organization_name or not self.organization_name.strip():
            # Limpiar mensaje si el campo está vacío
            if self.message_type == "error" and "organización" in self.message.lower():
                self.message = ""
                self.message_type = ""
            return  # No validar si está vacío
        
        # Verificar si la función del adaptador está disponible
        if check_organization_name_exists is None:
            logger.warning("La función check_organization_name_exists del adaptador no está disponible")
            return  # No hacer nada si la función no está disponible
        
        try:
            # Verificar si la organización existe usando el adaptador
            if check_organization_name_exists(self.organization_name.strip()):
                self.message = f"La organización '{self.organization_name.strip()}' ya existe en el sistema"
                self.message_type = "error"
                self.show_org_error_modal = True  # Mostrar el modal
                logger.info(f"Organización duplicada detectada: {self.organization_name.strip()}")
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
            logger.error(f"Error validando organización: {e}", exc_info=True)
    
    def set_identity_type_id(self, value: str):
        self.identity_type_id = value

    def choose_individual_account(self):
        """Alta pública de cuenta individual (identity 6, sin organización)."""
        self.account_kind = "individual"
        self.identity_type_id = "6"
        self.organization_id = ""
        self.organization_name = ""
        self.organization_acronym = ""
        self.show_account_kind_modal = False
        self.show_org_creation_modal = False

    def choose_organization_account(self):
        """Alta pública del primer administrador de organización (identity 2)."""
        self.account_kind = "organization"
        self.identity_type_id = "2"
        self.show_account_kind_modal = False

    def open_contact_modal(self):
        self.show_contact_modal = True

    def close_contact_modal(self):
        self.show_contact_modal = False

    def toggle_username_requirements(self):
        """Expande o contrae los requisitos del nombre de usuario."""
        self.show_username_requirements = not self.show_username_requirements

    def toggle_password_requirements(self):
        """Expande o contrae los requisitos de la contraseña."""
        self.show_password_requirements = not self.show_password_requirements

    def open_organization_modal(self):
        self.show_org_creation_modal = True

    def reopen_account_kind_modal(self):
        self.show_account_kind_modal = True
    
    def set_user_name(self, value: str):
        """Establece el nombre de usuario y elimina espacios en blanco automáticamente."""
        # Eliminar espacios en blanco automáticamente
        self.user_name = value.replace(" ", "")
        # Limpiar mensaje de error previo de nombre de usuario cuando el usuario está escribiendo
        # (solo si el mensaje es sobre nombre de usuario)
        if self.message_type == "error" and "nombre de usuario" in self.message.lower():
            self.message = ""
            self.message_type = ""
    
    def username_validation(self) -> bool:
        """
        Valida que el nombre de usuario cumple con las siguientes reglas:
        - Longitud mínima de 3 caracteres
        - Longitud máxima de 20 caracteres
        - Solo caracteres alfanuméricos y guiones bajos
        - Sin espacios en blanco
        
        Returns:
            bool: True si el nombre de usuario cumple todas las reglas, False en caso contrario
        """
        username = self.user_name.strip()
        
        # Validar longitud mínima
        if len(username) < 3:
            return False
        
        # Validar longitud máxima
        if len(username) > 20:
            return False
        
        # Validar que solo contenga caracteres alfanuméricos y guiones bajos
        if not username.replace("_", "").isalnum():
            return False
        
        # Validar que no tenga espacios (aunque ya se eliminan en set_user_name)
        if " " in username:
            return False
        
        return True
    
    def on_user_name_blur(self):
        """Valida el nombre de usuario cuando pierde el foco."""
        logger.info(f"on_user_name_blur llamado con user_name: '{self.user_name}'")
        if self.user_name and self.user_name.strip():
            username_stripped = self.user_name.strip()
            logger.info(f"Validando nombre de usuario: '{username_stripped}'")
            if not self.username_validation():
                # Si no pasa la validación de formato, mostrar modal
                logger.info(f"Nombre de usuario '{username_stripped}' no pasa validación de formato")
                self.show_username_validation_modal = True
                # Limpiar mensaje de error previo si había uno de duplicado
                if self.message_type == "error" and "ya está registrado" in self.message.lower():
                    self.message = ""
                    self.message_type = ""
            else:
                # Si pasa la validación de formato, verificar duplicados
                logger.info(f"Nombre de usuario '{username_stripped}' pasa validación de formato, verificando duplicados...")
                self.show_username_validation_modal = False
                if check_user_name_exists is not None:
                    try:
                        username_exists = check_user_name_exists(username_stripped)
                        logger.info(f"Resultado de check_user_name_exists('{username_stripped}'): {username_exists}")
                        if username_exists:
                            # Usuario duplicado encontrado - mostrar modal
                            logger.warning(f"Nombre de usuario duplicado detectado: {username_stripped}")
                            self.show_username_duplicate_modal = True
                            # Limpiar mensaje de error previo si había uno
                            self.message = ""
                            self.message_type = ""
                        else:
                            # Usuario no existe, cerrar modal si estaba abierto
                            logger.info(f"Nombre de usuario '{username_stripped}' no existe, está disponible")
                            self.show_username_duplicate_modal = False
                            # Limpiar mensaje de error si había uno de nombre de usuario
                            if self.message_type == "error" and "nombre de usuario" in self.message.lower() and "ya está registrado" in self.message.lower():
                                self.message = ""
                                self.message_type = ""
                    except Exception as e:
                        error_msg = f"Error al verificar duplicados de nombre de usuario: {e}"
                        logger.error(error_msg, exc_info=True)
                        self.message = f"Error al verificar el nombre de usuario. Por favor, intente nuevamente."
                        self.message_type = "error"
                else:
                    logger.warning("check_user_name_exists no está disponible")
                    self.message = "Error: El sistema de validación no está disponible. Por favor, contacte al administrador."
                    self.message_type = "error"
        else:
            # Si está vacío, cerrar el modal si está abierto
            logger.info("Nombre de usuario vacío, cerrando modal")
            self.show_username_validation_modal = False
            # No limpiar el mensaje si está vacío, puede ser que el usuario esté editando
    
    def close_username_validation_modal(self):
        """Cierra el modal de validación de nombre de usuario y devuelve el foco al input."""
        self.show_username_validation_modal = False
    
    def close_username_duplicate_modal(self):
        """Cierra el modal de error de nombre de usuario duplicado."""
        self.show_username_duplicate_modal = False
    
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
            # Limpiar mensaje solo si es un error de email (no de nombre de usuario)
            if self.message_type == "error" and "email" in self.message.lower() and "nombre de usuario" not in self.message.lower():
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
                # Limpiar mensaje solo si es un error de email (no de nombre de usuario)
                if self.message_type == "error" and "email" in self.message.lower() and "nombre de usuario" not in self.message.lower():
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
            # Limpiar mensaje solo si es un error de teléfono (no de nombre de usuario)
            if self.message_type == "error" and ("teléfono" in self.message.lower() or "móvil" in self.message.lower()) and "nombre de usuario" not in self.message.lower():
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
                # Limpiar mensaje solo si es un error de teléfono (no de nombre de usuario)
                if self.message_type == "error" and ("teléfono" in self.message.lower() or "móvil" in self.message.lower()) and "nombre de usuario" not in self.message.lower():
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
            
            # Validar formato del nombre de usuario
            if not self.username_validation():
                self.message = "El nombre de usuario no cumple con los requisitos de formato"
                self.message_type = "error"
                self.show_username_validation_modal = True
                return
            
            # Verificar duplicados a través del adaptador
            if check_user_name_exists is not None:
                try:
                    if check_user_name_exists(self.user_name.strip()):
                        self.message = f"El nombre de usuario '{self.user_name.strip()}' ya está registrado en el sistema"
                        self.message_type = "error"
                        return
                except Exception as e:
                    logger.error(f"Error al verificar duplicados de nombre de usuario: {e}")
                    # Continuar si hay error en la verificación
            
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
            
            # Convertir IDs a enteros según tipo de cuenta pública
            try:
                if self.account_kind == "individual":
                    org_id_int = 0
                    identity_id_int = 6
                elif self.account_kind == "organization":
                    org_id_int = int(self.organization_id) if self.organization_id else 0
                    identity_id_int = 2
                    if org_id_int <= 0:
                        self.message = "Debe crear o asociar una organización"
                        self.message_type = "error"
                        return
                else:
                    self.message = "Seleccione el tipo de cuenta"
                    self.message_type = "error"
                    self.show_account_kind_modal = True
                    return
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
                if save_user_to_json(user_extended, account_kind=self.account_kind):
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


def account_kind_modal() -> rx.Component:
    """Modal inicial: cuenta individual o de organización."""
    return rx.cond(
        UserCreationState.show_account_kind_modal,
        rx.fragment(
            _modal_overlay("1100"),
            _modal_panel(
                rx.vstack(
                    rx.heading(
                        "Tipo de cuenta",
                        size="6",
                        color=COLORS["primary"],
                    ),
                    rx.text(
                        "Una cuenta individual no pertenece a ninguna organización. "
                        "Si más adelante necesita organización, cree otro usuario.",
                        color=COLORS["foreground"],
                        font_size=BODY_FONT_SIZE,
                    ),
                    rx.hstack(
                        rx.button(
                            "Cuenta individual",
                            on_click=UserCreationState.choose_individual_account,
                            class_name="crt-btn",
                        ),
                        rx.button(
                            "Cuenta de organización",
                            on_click=UserCreationState.choose_organization_account,
                            class_name="crt-btn",
                        ),
                        spacing="4",
                    ),
                    spacing="4",
                    align_items="center",
                    padding="2em",
                ),
                min_width="480px",
                max_width="640px",
                z_index="1101",
            ),
        ),
    )


def organization_error_modal() -> rx.Component:
    """Modal centrado para mostrar el error de organización duplicada."""
    return rx.cond(
        UserCreationState.show_org_error_modal,
        rx.fragment(
            _modal_overlay(),
            _modal_panel(
                rx.vstack(
                    rx.heading(
                        "La Organización ya existe en el sistema",
                        size="6",
                        color=COLORS["primary"],
                        margin_bottom="1em",
                    ),
                    rx.text(
                        UserCreationState.message,
                        color=COLORS["foreground"],
                        font_size=BODY_FONT_SIZE,
                        text_align="center",
                        margin_bottom="2em",
                    ),
                    rx.button(
                        "Entendido",
                        on_click=UserCreationState.close_org_error_modal,
                        class_name="crt-btn",
                        width="200px",
                    ),
                    spacing="2",
                    align_items="center",
                    padding="2em",
                ),
            ),
        ),
    )


def organization_creation_modal() -> rx.Component:
    """Modal centrado para crear una nueva organización."""
    return rx.cond(
        UserCreationState.show_org_creation_modal,
        rx.fragment(
            _modal_overlay(),
            _modal_panel(
                rx.vstack(
                    rx.heading(
                        "Crear Nueva Organización",
                        size="6",
                        color=COLORS["primary"],
                        margin_bottom="0.5em",
                    ),
                    rx.text(
                        UserCreationState.organization_name,
                        color=COLORS["foreground"],
                        font_size=BODY_FONT_SIZE,
                        font_weight="bold",
                        margin_bottom="1.2em",
                    ),
                    rx.vstack(
                        rx.vstack(
                            _field_label("Email *"),
                            _text_input(
                                placeholder="email@organizacion.com",
                                on_change=UserCreationState.set_org_email,
                                value=UserCreationState.org_email,
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        rx.vstack(
                            _field_label("Teléfono"),
                            _text_input(
                                placeholder="+1234567890",
                                on_change=UserCreationState.set_org_tlf,
                                value=UserCreationState.org_tlf,
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        rx.vstack(
                            _field_label("Dirección"),
                            _text_input(
                                placeholder="Dirección de la organización",
                                on_change=UserCreationState.set_org_address,
                                value=UserCreationState.org_address,
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        rx.hstack(
                            rx.vstack(
                                _field_label("País"),
                                _text_input(
                                    placeholder="País",
                                    on_change=UserCreationState.set_org_country,
                                    value=UserCreationState.org_country,
                                ),
                                spacing="1",
                                flex="1",
                            ),
                            rx.vstack(
                                _field_label("Estado/Provincia"),
                                _text_input(
                                    placeholder="Estado o Provincia",
                                    on_change=UserCreationState.set_org_state,
                                    value=UserCreationState.org_state,
                                ),
                                spacing="1",
                                flex="1",
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    rx.hstack(
                        rx.button(
                            "Guardar",
                            on_click=UserCreationState.save_organization,
                            class_name="crt-btn",
                        ),
                        rx.button(
                            "Cancelar",
                            on_click=UserCreationState.close_org_creation_modal,
                            class_name="crt-btn",
                        ),
                        spacing="3",
                        justify_content="center",
                        width="100%",
                        margin_top="1em",
                    ),
                    spacing="3",
                    align_items="center",
                    padding="2em",
                    width="100%",
                ),
                min_width="560px",
                max_width="720px",
            ),
        ),
    )
def password_match_error_modal() -> rx.Component:
    """Modal centrado para mostrar el error de coincidencia de contraseñas."""
    return rx.cond(
        UserCreationState.show_password_match_error_modal,
        rx.fragment(
            _modal_overlay(),
            _modal_panel(
                rx.vstack(
                    rx.heading(
                        "Error de Contraseña",
                        size="6",
                        color=COLORS["primary"],
                        margin_bottom="1em",
                    ),
                    rx.text(
                        "La contraseña no coincide",
                        color=COLORS["foreground"],
                        font_size=BODY_FONT_SIZE,
                        text_align="center",
                        margin_bottom="2em",
                    ),
                    rx.button(
                        "Entendido",
                        on_click=UserCreationState.close_password_match_error_modal,
                        class_name="crt-btn",
                        width="200px",
                    ),
                    spacing="2",
                    align_items="center",
                    padding="2em",
                ),
            ),
        ),
    )


def password_validation_modal() -> rx.Component:
    """Modal centrado para mostrar las reglas de validación de contraseña."""
    return rx.cond(
        UserCreationState.show_password_validation_modal,
        rx.fragment(
            _modal_overlay(),
            _modal_panel(
                rx.vstack(
                    rx.heading(
                        "Requisitos de Contraseña",
                        size="6",
                        color=COLORS["primary"],
                        margin_bottom="1em",
                    ),
                    rx.text(
                        "La contraseña debe cumplir las siguientes reglas:",
                        color=COLORS["foreground"],
                        font_size=BODY_FONT_SIZE,
                        margin_bottom="1em",
                    ),
                    rx.vstack(
                        *[
                            rx.text(
                                f"• {item}",
                                color=COLORS["foreground"],
                                font_size=BODY_FONT_SIZE,
                            )
                            for item in PASSWORD_REQUIREMENTS
                        ],
                        spacing="2",
                        align_items="flex-start",
                        margin_bottom="2em",
                    ),
                    rx.button(
                        "Entendido",
                        on_click=UserCreationState.close_password_validation_modal,
                        class_name="crt-btn",
                        width="200px",
                    ),
                    spacing="2",
                    align_items="center",
                    padding="2em",
                ),
            ),
        ),
    )


def username_validation_modal() -> rx.Component:
    """Modal centrado para mostrar las reglas de validación de nombre de usuario."""
    return rx.cond(
        UserCreationState.show_username_validation_modal,
        rx.fragment(
            _modal_overlay(),
            _modal_panel(
                rx.vstack(
                    rx.heading(
                        "Requisitos de Nombre de Usuario",
                        size="6",
                        color=COLORS["primary"],
                        margin_bottom="1em",
                    ),
                    rx.text(
                        "El nombre de usuario debe cumplir las siguientes reglas:",
                        color=COLORS["foreground"],
                        font_size=BODY_FONT_SIZE,
                        margin_bottom="1em",
                    ),
                    rx.vstack(
                        *[
                            rx.text(
                                f"• {item}",
                                color=COLORS["foreground"],
                                font_size=BODY_FONT_SIZE,
                            )
                            for item in USERNAME_REQUIREMENTS
                        ],
                        spacing="2",
                        align_items="flex-start",
                        margin_bottom="2em",
                    ),
                    rx.button(
                        "Entendido",
                        on_click=UserCreationState.close_username_validation_modal,
                        class_name="crt-btn",
                        width="200px",
                    ),
                    spacing="2",
                    align_items="center",
                    padding="2em",
                ),
            ),
        ),
    )


def username_duplicate_error_modal() -> rx.Component:
    """Modal centrado para mostrar el error de nombre de usuario duplicado."""
    return rx.cond(
        UserCreationState.show_username_duplicate_modal,
        rx.fragment(
            _modal_overlay(),
            _modal_panel(
                rx.vstack(
                    rx.heading(
                        "Nombre de Usuario No Disponible",
                        size="6",
                        color=COLORS["primary"],
                        margin_bottom="1em",
                    ),
                    rx.vstack(
                        rx.text(
                            "El nombre de usuario",
                            color=COLORS["foreground"],
                            font_size=BODY_FONT_SIZE,
                            text_align="center",
                        ),
                        rx.text(
                            UserCreationState.user_name,
                            color=COLORS["primary"],
                            font_size="1.2em",
                            font_weight="bold",
                            text_align="center",
                        ),
                        rx.text(
                            "ya está registrado en el sistema. Por favor, elija otro nombre de usuario.",
                            color=COLORS["foreground"],
                            font_size=BODY_FONT_SIZE,
                            text_align="center",
                        ),
                        spacing="2",
                        align_items="center",
                        margin_bottom="2em",
                    ),
                    rx.button(
                        "Entendido",
                        on_click=UserCreationState.close_username_duplicate_modal,
                        class_name="crt-btn",
                        width="200px",
                    ),
                    spacing="2",
                    align_items="center",
                    padding="2em",
                ),
            ),
        ),
    )


def contact_billing_modal() -> rx.Component:
    """Modal opaco de contacto y facturación."""
    return rx.cond(
        UserCreationState.show_contact_modal,
        rx.fragment(
            _modal_overlay("1100"),
            _modal_panel(
                rx.vstack(
                    rx.hstack(
                        rx.heading(
                            "Información de Contacto",
                            size="6",
                            color=COLORS["primary"],
                        ),
                        rx.button(
                            "Cerrar",
                            on_click=UserCreationState.close_contact_modal,
                            class_name="crt-btn",
                        ),
                        justify="between",
                        align_items="center",
                        width="100%",
                    ),
                    rx.hstack(
                        rx.vstack(
                            _field_label("Nombre *"),
                            _text_input(
                                placeholder="Nombre",
                                on_change=UserCreationState.set_contact_first_name,
                                value=UserCreationState.contact_first_name,
                            ),
                            spacing="1",
                            flex="1",
                        ),
                        rx.vstack(
                            _field_label("Apellidos *"),
                            _text_input(
                                placeholder="Apellidos",
                                on_change=UserCreationState.set_contact_sur_name,
                                value=UserCreationState.contact_sur_name,
                            ),
                            spacing="1",
                            flex="1",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    rx.hstack(
                        rx.vstack(
                            _field_label("País *"),
                            _text_input(
                                placeholder="País",
                                on_change=UserCreationState.set_contact_country,
                                value=UserCreationState.contact_country,
                            ),
                            spacing="1",
                            flex="1",
                        ),
                        rx.vstack(
                            _field_label("Estado/Provincia *"),
                            _text_input(
                                placeholder="Estado o Provincia",
                                on_change=UserCreationState.set_contact_state,
                                value=UserCreationState.contact_state,
                            ),
                            spacing="1",
                            flex="1",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    rx.vstack(
                        _field_label("Código Postal *"),
                        _text_input(
                            placeholder="Código Postal",
                            on_change=UserCreationState.set_contact_zip_code,
                            value=UserCreationState.contact_zip_code,
                        ),
                        spacing="1",
                        width="100%",
                    ),
                    rx.vstack(
                        _field_label("Dirección *"),
                        _text_input(
                            placeholder="Dirección completa",
                            on_change=UserCreationState.set_contact_address,
                            value=UserCreationState.contact_address,
                        ),
                        spacing="1",
                        width="100%",
                    ),
                    rx.checkbox(
                        "Tengo una dirección de facturación diferente",
                        checked=UserCreationState.has_different_billing_address,
                        on_change=UserCreationState.set_has_different_billing_address,
                        color=COLORS["foreground"],
                        margin_top="0.5em",
                    ),
                    rx.cond(
                        UserCreationState.has_different_billing_address,
                        rx.vstack(
                            rx.heading(
                                "Información de Facturación",
                                size="6",
                                color=COLORS["primary"],
                            ),
                            rx.text(
                                "Si no se completa, se usará la información de contacto",
                                font_size=BODY_FONT_SIZE,
                                color=COLORS["foreground"],
                            ),
                            rx.hstack(
                                rx.vstack(
                                    _field_label("Nombre"),
                                    _text_input(
                                        placeholder="Nombre de facturación",
                                        on_change=UserCreationState.set_billing_first_name,
                                        value=UserCreationState.billing_first_name,
                                    ),
                                    spacing="1",
                                    flex="1",
                                ),
                                rx.vstack(
                                    _field_label("Apellidos"),
                                    _text_input(
                                        placeholder="Apellidos de facturación",
                                        on_change=UserCreationState.set_billing_sur_name,
                                        value=UserCreationState.billing_sur_name,
                                    ),
                                    spacing="1",
                                    flex="1",
                                ),
                                spacing="3",
                                width="100%",
                            ),
                            rx.hstack(
                                rx.vstack(
                                    _field_label("País"),
                                    _text_input(
                                        placeholder="País de facturación",
                                        on_change=UserCreationState.set_billing_country,
                                        value=UserCreationState.billing_country,
                                    ),
                                    spacing="1",
                                    flex="1",
                                ),
                                rx.vstack(
                                    _field_label("Estado/Provincia"),
                                    _text_input(
                                        placeholder="Estado o Provincia de facturación",
                                        on_change=UserCreationState.set_billing_state,
                                        value=UserCreationState.billing_state,
                                    ),
                                    spacing="1",
                                    flex="1",
                                ),
                                spacing="3",
                                width="100%",
                            ),
                            rx.vstack(
                                _field_label("Código Postal"),
                                _text_input(
                                    placeholder="Código Postal de facturación",
                                    on_change=UserCreationState.set_billing_zip_code,
                                    value=UserCreationState.billing_zip_code,
                                ),
                                spacing="1",
                                width="100%",
                            ),
                            rx.vstack(
                                _field_label("Dirección"),
                                _text_input(
                                    placeholder="Dirección de facturación",
                                    on_change=UserCreationState.set_billing_address,
                                    value=UserCreationState.billing_address,
                                ),
                                spacing="1",
                                width="100%",
                            ),
                            spacing="3",
                            width="100%",
                        ),
                    ),
                    rx.button(
                        "Listo",
                        on_click=UserCreationState.close_contact_modal,
                        class_name="crt-btn",
                    ),
                    spacing="4",
                    align_items="stretch",
                    padding="2em",
                    width="100%",
                ),
                min_width="640px",
                max_width="820px",
                z_index="1101",
            ),
        ),
    )


def _account_kind_card() -> rx.Component:
    """Tarjeta lateral con el tipo de cuenta seleccionado."""
    return rx.cond(
        UserCreationState.account_kind == "organization",
        rx.vstack(
            _field_label("Organización"),
            rx.button(
                rx.cond(
                    UserCreationState.organization_name != "",
                    UserCreationState.organization_name,
                    "Completar datos de organización",
                ),
                on_click=UserCreationState.open_organization_modal,
                class_name="crt-btn",
                width="100%",
            ),
            rx.cond(
                UserCreationState.organization_acronym != "",
                rx.hstack(
                    rx.text("Login:", font_size=BODY_FONT_SIZE, color=COLORS["primary"]),
                    rx.text(UserCreationState.user_name, font_size=BODY_FONT_SIZE, color=COLORS["primary"]),
                    rx.text("@", font_size=BODY_FONT_SIZE, color=COLORS["primary"]),
                    rx.text(
                        UserCreationState.organization_acronym,
                        font_size=BODY_FONT_SIZE,
                        color=COLORS["primary"],
                    ),
                    spacing="1",
                ),
            ),
            spacing="2",
            flex="1",
            width="100%",
        ),
        rx.vstack(
            rx.text(
                "Cuenta individual",
                font_size=LABEL_FONT_SIZE,
                color=COLORS["primary"],
                font_weight="bold",
            ),
            rx.text(
                "Accederás solo con tu nombre de usuario, sin @ ni acrónimo.",
                font_size=BODY_FONT_SIZE,
                color=COLORS["foreground"],
            ),
            spacing="2",
            flex="1",
            width="100%",
        ),
    )


def user_creation_page() -> rx.Component:
    """Página de creación de usuario."""
    return rx.vstack(
        account_kind_modal(),
        organization_error_modal(),
        organization_creation_modal(),
        password_validation_modal(),
        password_match_error_modal(),
        username_validation_modal(),
        username_duplicate_error_modal(),
        contact_billing_modal(),
        rx.box(
            rx.heading(
                "Crear Nuevo Usuario",
                size="8",
                color=COLORS["primary"],
                margin_bottom="0.25em",
            ),
            rx.text(
                "Completa tus datos. Los requisitos se muestran al pulsar cada apartado.",
                font_size=BODY_FONT_SIZE,
                color=COLORS["foreground"],
            ),
            width="100%",
            max_width="1080px",
            padding="1.5em 2em 0.5em",
            margin="0 auto",
        ),
        rx.vstack(
            rx.box(
                rx.vstack(
                    rx.heading(
                        "Información de Usuario",
                        size="6",
                        color=COLORS["primary"],
                    ),
                    rx.hstack(
                        rx.vstack(
                            _field_label("Nombre de Usuario *"),
                            _text_input(
                                placeholder="Mínimo 3 caracteres, solo letras, números y _",
                                on_change=UserCreationState.set_user_name,
                                on_blur=UserCreationState.on_user_name_blur,
                                value=UserCreationState.user_name,
                            ),
                            spacing="1",
                            flex="1",
                            width="100%",
                        ),
                        _account_kind_card(),
                        spacing="5",
                        width="100%",
                        align_items="start",
                    ),
                    _collapsible_requirements(
                        "Requisitos del nombre de usuario:",
                        USERNAME_REQUIREMENTS,
                        UserCreationState.show_username_requirements,
                        UserCreationState.toggle_username_requirements,
                    ),
                    rx.hstack(
                        rx.vstack(
                            _field_label("Contraseña *"),
                            _text_input(
                                placeholder="Mínimo 8 caracteres",
                                type_="password",
                                id="user_password_input",
                                on_change=UserCreationState.set_user_password,
                                on_blur=UserCreationState.on_password_blur,
                                value=UserCreationState.user_password,
                            ),
                            spacing="1",
                            flex="1",
                            width="100%",
                        ),
                        rx.vstack(
                            _field_label("Repita la contraseña *"),
                            _text_input(
                                placeholder="Repita la contraseña",
                                type_="password",
                                id="user_password_confirm_input",
                                on_change=UserCreationState.set_user_password_confirm,
                                on_blur=UserCreationState.on_password_confirm_blur,
                                value=UserCreationState.user_password_confirm,
                            ),
                            spacing="1",
                            flex="1",
                            width="100%",
                        ),
                        spacing="5",
                        width="100%",
                    ),
                    _collapsible_requirements(
                        "Requisitos de la contraseña:",
                        PASSWORD_REQUIREMENTS,
                        UserCreationState.show_password_requirements,
                        UserCreationState.toggle_password_requirements,
                    ),
                    rx.hstack(
                        rx.vstack(
                            _field_label("Email *"),
                            _text_input(
                                placeholder="usuario@ejemplo.com",
                                on_change=UserCreationState.set_user_email,
                                on_blur=UserCreationState.on_user_email_blur,
                                value=UserCreationState.user_email,
                            ),
                            spacing="1",
                            flex="1",
                            width="100%",
                        ),
                        rx.vstack(
                            _field_label("Teléfono Móvil *"),
                            _text_input(
                                placeholder="+1234567890",
                                on_change=UserCreationState.set_user_mobile,
                                on_blur=UserCreationState.on_user_mobile_blur,
                                value=UserCreationState.user_mobile,
                            ),
                            spacing="1",
                            flex="1",
                            width="100%",
                        ),
                        spacing="5",
                        width="100%",
                    ),
                    rx.hstack(
                        rx.button(
                            "Contacto y facturación",
                            on_click=UserCreationState.open_contact_modal,
                            class_name="crt-btn",
                        ),
                        rx.button(
                            "Cambiar tipo de cuenta",
                            on_click=UserCreationState.reopen_account_kind_modal,
                            class_name="crt-btn",
                        ),
                        rx.spacer(),
                        rx.button(
                            "Guardar",
                            on_click=UserCreationState.save_user,
                            class_name="crt-btn",
                        ),
                        rx.link(
                            rx.button("Regresar", class_name="crt-btn"),
                            href="/",
                        ),
                        spacing="3",
                        width="100%",
                        align_items="center",
                    ),
                    rx.cond(
                        rx.cond(
                            UserCreationState.message != "",
                            rx.cond(
                                UserCreationState.show_org_error_modal,
                                False,
                                True,
                            ),
                            False,
                        ),
                        rx.box(
                            rx.text(
                                UserCreationState.message,
                                color=rx.cond(
                                    UserCreationState.message_type == "success",
                                    COLORS["primary"],
                                    COLORS["error"],
                                ),
                                font_size=BODY_FONT_SIZE,
                                font_weight="bold",
                            ),
                            padding="0.9em 1em",
                            background_color=MODAL_SURFACE,
                            border=f"1px solid {COLORS['border']}",
                            border_radius="0.45em",
                            width="100%",
                        ),
                    ),
                    spacing="4",
                    width="100%",
                ),
                class_name="crt-register-card crt-panel",
                background_color=MODAL_SURFACE,
                border=f"1px solid {COLORS['border']}",
                border_radius="0.75em",
                padding="2em",
                width="100%",
            ),
            spacing="2",
            padding="1em 2em 2.5em",
            width="100%",
            max_width="1080px",
            margin="0 auto",
        ),
        background_color=COLORS["background"],
        width="100%",
        min_height="100vh",
        spacing="0",
        class_name=CRT_SHELL_CLASS,
    )
