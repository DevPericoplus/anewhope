import reflex as rx
from typing import Optional, Any
import sys
import random
import logging
from pathlib import Path

logger = logging.getLogger("backoffice")

# Agregar el path para importar módulos del dominio
domain_entities_path = Path(__file__).parent.parent.parent.parent / "1_shared_domain" / "entities"
domain_entities_parent = domain_entities_path.parent

# Agregar tanto el directorio de entities como su padre al path
if str(domain_entities_path) not in sys.path:
    sys.path.insert(0, str(domain_entities_path))
if str(domain_entities_parent) not in sys.path:
    sys.path.insert(0, str(domain_entities_parent))

# Intentar importar las funciones de usuario
get_user_by_email = None
update_user_password_and_otp = None

try:
    import importlib.util
    user_module_path = domain_entities_path / "user.py"
    if user_module_path.exists():
        spec = importlib.util.spec_from_file_location("user", user_module_path)
        if spec and spec.loader:
            user_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(user_module)
            get_user_by_email = user_module.get_user_by_email
            update_user_password_and_otp = user_module.update_user_password_and_otp
except Exception as e:
    logger.error(f"Error al cargar módulo de usuarios: {e}")

# Cargar módulo de seguridad común
_common_security_module = None
_send_message_by_sms = None
log_security_action = None

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
            _send_message_by_sms = getattr(_common_security_module, "send_message_by_sms", None)
            if _send_message_by_sms:
                logger.info("Módulo common_security cargado exitosamente")
except Exception as e:
    logger.error(f"Error al cargar módulo common_security: {e}")

# Intentar importar el adaptador para logging de seguridad
try:
    import importlib.util
    adapter_path = Path(__file__).parent.parent / "adapters" / "api_client.py"
    if adapter_path.exists():
        spec = importlib.util.spec_from_file_location("api_client", adapter_path)
        if spec and spec.loader:
            api_client_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(api_client_module)
            if hasattr(api_client_module, "log_security_action"):
                log_security_action = api_client_module.log_security_action
                logger.info("Función log_security_action cargada exitosamente")
            else:
                log_security_action = None
                logger.warning("log_security_action no está disponible en api_client")
    else:
        log_security_action = None
        logger.warning("api_client.py no existe para logging")
except Exception as e:
    log_security_action = None
    logger.error(f"Error al cargar api_client para logging: {e}")

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

from portal_crt import COLORS, CRT_SHELL_CLASS, SELECT_STYLE


class ChangePasswordState(rx.State):
    """Estado para el formulario de cambio de contraseña."""
    
    # Parámetro de query string para validar acceso
    from_page: str = ""
    
    # Campos del formulario
    user_email: str = ""
    otp_code: str = ""
    new_password: str = ""
    new_password_confirm: str = ""
    
    # Estados del proceso
    step: int = 1  # 1: Email, 2: OTP, 3: Nueva contraseña
    user_found: bool = False
    user_data: Optional[dict] = None
    otp_sent: bool = False
    otp_validated: bool = False
    show_update_button: bool = False
    
    # Mensajes de estado
    message: str = ""
    message_type: str = ""  # "success" o "error"
    show_password_validation_modal: bool = False
    show_password_match_error_modal: bool = False
    
    def secure_access(self):
        """
        Valida el acceso desde la página principal y limpia todos los campos.
        Se ejecuta automáticamente al cargar la página.
        """
        # Limpiar todos los campos
        self.user_email = ""
        self.otp_code = ""
        self.new_password = ""
        self.new_password_confirm = ""
        self.step = 1
        self.user_found = False
        self.user_data = None
        self.otp_sent = False
        self.otp_validated = False
        self.show_update_button = False
        self.message = ""
        self.message_type = ""
        self.show_password_validation_modal = False
        self.show_password_match_error_modal = False
        
        # Validar acceso desde la página principal
        # En Reflex, los parámetros de query string se pueden obtener del router
        if self.from_page != "main":
            # Redirigir a la página principal si se accede directamente por URL
            return rx.redirect("/")
    
    def on_mount(self):
        """Se ejecuta automáticamente cuando se monta el componente."""
        # Ejecutar secure_access que limpiará campos y validará acceso
        self.secure_access()
    
    def set_user_email(self, value: str):
        self.user_email = value
    
    def set_otp_code(self, value: str):
        self.otp_code = value
    
    def set_new_password(self, value: str):
        self.new_password = value
        self._update_show_update_button()
    
    def set_new_password_confirm(self, value: str):
        self.new_password_confirm = value
        self._update_show_update_button()
    
    def _update_show_update_button(self):
        """Actualiza el estado de show_update_button basado en las contraseñas."""
        self.show_update_button = (
            self.new_password != ""
            and self.new_password_confirm != ""
            and self.new_password == self.new_password_confirm
        )
    
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
        password = self.new_password
        
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
        if self.new_password and self.new_password.strip():
            if not self.password_validation():
                self.show_password_validation_modal = True
        else:
            self.show_password_validation_modal = False
    
    def close_password_validation_modal(self):
        """Cierra el modal de validación de contraseña."""
        self.show_password_validation_modal = False
    
    def on_password_confirm_blur(self):
        """Se ejecuta cuando se pierde el foco en el campo de confirmación de contraseña."""
        if self.new_password_confirm and self.new_password_confirm.strip():
            if self.new_password != self.new_password_confirm:
                self.show_password_match_error_modal = True
            else:
                self.show_password_match_error_modal = False
        else:
            self.show_password_match_error_modal = False
    
    def close_password_match_error_modal(self):
        """Cierra el modal de error de coincidencia de contraseñas."""
        self.show_password_match_error_modal = False
    
    def request_otp(self):
        """Solicita el código OTP enviándolo por SMS al usuario."""
        try:
            if not self.user_email or not self.user_email.strip():
                self.message = "Por favor, ingrese su email"
                self.message_type = "error"
                return
            
            # Buscar usuario por email
            if get_user_by_email is None:
                self.message = "Error: función de búsqueda de usuario no disponible"
                self.message_type = "error"
                return
            
            user = get_user_by_email(self.user_email.strip())
            if not user:
                self.message = "El email ingresado no está registrado en el sistema"
                self.message_type = "error"
                return
            
            self.user_data = user
            self.user_found = True
            
            # Obtener OTP y número de teléfono del usuario
            user_otp = user.get("user_otp", "")
            user_mobile = user.get("user_mobile", "")
            user_id = user.get("user_id", "N/A")
            
            logger.info(f"Usuario encontrado - ID: {user_id}, Email: {self.user_email.strip()}, OTP: {user_otp}, Mobile: {user_mobile}")
            
            if not user_otp or len(user_otp) != 4:
                logger.error(f"OTP inválido para usuario {user_id}: '{user_otp}' (longitud: {len(user_otp) if user_otp else 0})")
                self.message = "Error: OTP del usuario no válido"
                self.message_type = "error"
                return
            
            if not user_mobile or not user_mobile.strip():
                logger.error(f"Usuario {user_id} no tiene número de teléfono registrado")
                self.message = "Error: El usuario no tiene número de teléfono registrado"
                self.message_type = "error"
                return
            
            # Enviar SMS con el OTP
            if _send_message_by_sms is None:
                logger.error("Función _send_message_by_sms no está disponible")
                self.message = "Error: función de envío de SMS no disponible"
                self.message_type = "error"
                return
            
            logger.info(f"Enviando SMS - OTP: {user_otp}, Teléfono: {user_mobile.strip()}, Usuario ID: {user_id}")
            sms_result = _send_message_by_sms(user_otp, user_mobile.strip())
            logger.info(f"Resultado del envío de SMS: {sms_result}")
            
            if sms_result:
                self.otp_sent = True
                self.step = 2
                self.message = "Código OTP enviado exitosamente a su teléfono"
                self.message_type = "success"
                
                # Registrar en log de seguridad
                user_id = user.get("user_id")
                self.log_security_action("Solicitado cambio de contraseña", user_id)
            else:
                self.message = "Error al enviar el código OTP. Por favor, intente nuevamente"
                self.message_type = "error"
                
        except Exception as e:
            logger.error(f"Error al solicitar OTP: {e}", exc_info=True)
            self.message = f"Error al procesar la solicitud: {str(e)}"
            self.message_type = "error"
    
    def validate_otp(self):
        """Valida el código OTP ingresado por el usuario."""
        try:
            if not self.otp_code or not self.otp_code.strip():
                self.message = "Por favor, ingrese el código OTP"
                self.message_type = "error"
                return
            
            if not self.user_data:
                self.message = "Error: No se encontró información del usuario"
                self.message_type = "error"
                return
            
            # Comparar OTP ingresado con el almacenado
            stored_otp = self.user_data.get("user_otp", "")
            entered_otp = self.otp_code.strip()
            
            if stored_otp == entered_otp:
                self.otp_validated = True
                self.step = 3
                self.message = "Código OTP validado correctamente"
                self.message_type = "success"
                
                # Registrar en log de seguridad
                user_id = self.user_data.get("user_id")
                self.log_security_action("OTP validado para cambio de contraseña", user_id)
            else:
                self.message = "El código OTP ingresado no es correcto"
                self.message_type = "error"
                
                # Registrar intento fallido en log
                user_id = self.user_data.get("user_id")
                self.log_security_action("Intento fallido de validación OTP", user_id)
                
        except Exception as e:
            logger.error(f"Error al validar OTP: {e}", exc_info=True)
            self.message = f"Error al validar el código OTP: {str(e)}"
            self.message_type = "error"
    
    def update_password(self):
        """Actualiza la contraseña del usuario."""
        try:
            if not self.user_data:
                self.message = "Error: No se encontró información del usuario"
                self.message_type = "error"
                return
            
            if not self.new_password or len(self.new_password) < 8:
                self.message = "La contraseña debe tener al menos 8 caracteres"
                self.message_type = "error"
                return
            
            if not self.password_validation():
                self.message = "La contraseña no cumple con los requisitos de seguridad"
                self.message_type = "error"
                self.show_password_validation_modal = True
                return
            
            if self.new_password != self.new_password_confirm:
                self.message = "Las contraseñas no coinciden"
                self.message_type = "error"
                self.show_password_match_error_modal = True
                return
            
            # Cifrar la nueva contraseña
            encrypted_password = self.new_password
            try:
                if _cipher_module and _fernet_instance:
                    encrypted_password_bytes = _cipher_module.encrypt_value(_fernet_instance, self.new_password)
                    encrypted_password = encrypted_password_bytes.decode('utf-8')
                    logger.debug("Contraseña cifrada exitosamente")
                else:
                    logger.warning("El módulo de cifrado no está disponible, la contraseña se guardará sin cifrar")
            except Exception as e:
                logger.error(f"Error al cifrar la contraseña: {e}")
                self.message = "Error al cifrar la contraseña"
                self.message_type = "error"
                return
            
            # Generar nuevo OTP aleatorio de 4 dígitos
            new_otp = f"{random.randint(1000, 9999)}"
            
            # Actualizar contraseña y OTP del usuario
            if update_user_password_and_otp is None:
                self.message = "Error: función de actualización no disponible"
                self.message_type = "error"
                return
            
            user_email = self.user_data.get("user_email", "")
            if update_user_password_and_otp(user_email, encrypted_password, new_otp):
                self.message = "Contraseña actualizada exitosamente"
                self.message_type = "success"
                
                # Registrar en log de seguridad
                user_id = self.user_data.get("user_id")
                self.log_security_action("Contraseña actualizada", user_id)
                
                # Limpiar campos y resetear estado
                self.new_password = ""
                self.new_password_confirm = ""
                self.otp_code = ""
                self.step = 1
                self.user_found = False
                self.user_data = None
                self.otp_sent = False
                self.otp_validated = False
                self.show_update_button = False
            else:
                self.message = "Error al actualizar la contraseña"
                self.message_type = "error"
                
        except Exception as e:
            logger.error(f"Error al actualizar contraseña: {e}", exc_info=True)
            self.message = f"Error al actualizar la contraseña: {str(e)}"
            self.message_type = "error"
    
    def log_security_action(self, action: str, user_id: Optional[int]):
        """
        Registra una acción de seguridad en el log.
        
        Args:
            action: Descripción de la acción realizada.
            user_id: Identificador del usuario.
        """
        try:
            # Intentar obtener IP y user agent desde router_data
            ip = None
            user_agent = None
            
            try:
                if hasattr(self, "router_data"):
                    headers = self.router_data.get("headers", {})
                    ip = headers.get("x-forwarded-for", "127.0.0.1")
                    if "," in ip:
                        ip = ip.split(",")[0].strip()
                    user_agent = headers.get("user-agent", "Unknown Browser")
                    logger.debug(f"IP obtenida desde router_data: {ip}, User agent: {user_agent[:50]}")
            except Exception as e:
                logger.debug(f"Error al obtener IP/user agent desde router_data: {e}")
            
            if ip is None:
                ip = "127.0.0.1"
            if user_agent is None:
                user_agent = "Unknown Browser"
            _log_security_action(action, user_id, ip, user_agent)
        except Exception as e:
            logger.error(f"Error al registrar log de seguridad: {e}", exc_info=True)


def password_validation_modal() -> rx.Component:
    """Modal centrado para mostrar las reglas de validación de contraseña."""
    return rx.cond(
        ChangePasswordState.show_password_validation_modal,
        rx.fragment(
            rx.box(
                width="100vw",
                height="100vh",
                background_color="rgba(0, 0, 0, 0.7)",
                position="fixed",
                top="0",
                left="0",
                z_index="1000",
            ),
            rx.box(
                rx.vstack(
                    rx.heading(
                        "Requisitos de Contraseña",
                        size="6",
                        color=COLORS["primary"],
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
                        on_click=ChangePasswordState.close_password_validation_modal,
                        background_color=COLORS["primary"],
                        color="black",
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


def password_match_error_modal() -> rx.Component:
    """Modal centrado para mostrar el error de coincidencia de contraseñas."""
    return rx.cond(
        ChangePasswordState.show_password_match_error_modal,
        rx.fragment(
            rx.box(
                width="100vw",
                height="100vh",
                background_color="rgba(0, 0, 0, 0.7)",
                position="fixed",
                top="0",
                left="0",
                z_index="1000",
            ),
            rx.box(
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
                        font_size="1em",
                        text_align="center",
                        margin_bottom="2em",
                    ),
                    rx.button(
                        "Entendido",
                        on_click=ChangePasswordState.close_password_match_error_modal,
                        background_color=COLORS["primary"],
                        color="black",
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


def change_password_page() -> rx.Component:
    """Página de cambio de contraseña."""
    return rx.vstack(
        # Modales
        password_validation_modal(),
        password_match_error_modal(),
        
        # Header
        rx.hstack(
            rx.heading("Recordar Contraseña", size="6", color=COLORS["primary"]),
            width="100%",
            padding="1em",
            background_color=COLORS["card"],
            border_bottom=f"1px solid {COLORS['border']}",
        ),
        
        # Contenido principal
        rx.vstack(
            # Panel informativo
            rx.vstack(
                rx.heading("Proceso de Recuperación de Contraseña", size="5", color=COLORS["primary"], margin_bottom="1em"),
                rx.vstack(
                    rx.text(
                        "Para recuperar su contraseña, siga estos pasos:",
                        color=COLORS["muted_foreground"],
                        font_size="1em",
                        margin_bottom="0.5em",
                    ),
                    rx.text(
                        "1. Ingrese su dirección de email registrada en el sistema.",
                        color=COLORS["foreground"],
                        font_size="0.95em",
                    ),
                    rx.text(
                        "2. Haga clic en 'Solicitar código OTP' para recibir un código de verificación por SMS.",
                        color=COLORS["foreground"],
                        font_size="0.95em",
                    ),
                    rx.text(
                        "3. Ingrese el código OTP recibido en su teléfono móvil.",
                        color=COLORS["foreground"],
                        font_size="0.95em",
                    ),
                    rx.text(
                        "4. Una vez validado el código, podrá establecer una nueva contraseña segura.",
                        color=COLORS["foreground"],
                        font_size="0.95em",
                    ),
                    spacing="1",
                    align_items="flex-start",
                ),
                padding="1.5em",
                background_color=COLORS["card"],
                border=f"1px solid {COLORS['border']}",
                border_radius="0.5em",
                width="100%",
                margin_bottom="1em",
            ),
            
            # Paso 1: Email
            rx.cond(
                ChangePasswordState.step == 1,
                rx.vstack(
                    rx.vstack(
                        rx.heading("Paso 1: Ingrese su Email", size="5", color=COLORS["primary"], margin_bottom="1em"),
                        rx.vstack(
                            rx.text("Email *", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="usuario@ejemplo.com",
                                on_change=ChangePasswordState.set_user_email,
                                value=ChangePasswordState.user_email,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                        ),
                        rx.button(
                            "Solicitar código OTP",
                            on_click=ChangePasswordState.request_otp,
                            background_color=COLORS["primary"],
                            color="black",
                            font_weight="bold",
                            padding="0.75em 2em",
                            border_radius="0.5em",
                            margin_top="1em",
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
            ),
            
            # Paso 2: Validar OTP
            rx.cond(
                ChangePasswordState.step == 2,
                rx.vstack(
                    rx.vstack(
                        rx.heading("Paso 2: Validar Código OTP", size="5", color=COLORS["primary"], margin_bottom="1em"),
                        rx.vstack(
                            rx.text("Código OTP *", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="Ingrese el código de 4 dígitos",
                                on_change=ChangePasswordState.set_otp_code,
                                value=ChangePasswordState.otp_code,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                                max_length=4,
                            ),
                            spacing="1",
                        ),
                        rx.button(
                            "Validar código OTP",
                            on_click=ChangePasswordState.validate_otp,
                            background_color=COLORS["primary"],
                            color="black",
                            font_weight="bold",
                            padding="0.75em 2em",
                            border_radius="0.5em",
                            margin_top="1em",
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
            ),
            
            # Paso 3: Nueva contraseña
            rx.cond(
                ChangePasswordState.step == 3,
                rx.vstack(
                    rx.vstack(
                        rx.heading("Paso 3: Nueva Contraseña", size="5", color=COLORS["primary"], margin_bottom="1em"),
                        rx.vstack(
                            rx.text("Contraseña *", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="Mínimo 8 caracteres",
                                type_="password",
                                id="new_password_input",
                                on_change=ChangePasswordState.set_new_password,
                                on_blur=ChangePasswordState.on_password_blur,
                                value=ChangePasswordState.new_password,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Repetir Contraseña *", font_size="0.9em", color=COLORS["muted_foreground"]),
                            rx.input(
                                placeholder="Repita la contraseña",
                                type_="password",
                                id="new_password_confirm_input",
                                on_change=ChangePasswordState.set_new_password_confirm,
                                on_blur=ChangePasswordState.on_password_confirm_blur,
                                value=ChangePasswordState.new_password_confirm,
                                background_color=COLORS["input"],
                                border_color=COLORS["border"],
                                color=COLORS["foreground"],
                                width="100%",
                                border_radius="5px",
                            ),
                            spacing="1",
                        ),
                        rx.cond(
                            ChangePasswordState.show_update_button,
                            rx.button(
                                "Actualizar",
                                on_click=ChangePasswordState.update_password,
                                background_color=COLORS["primary"],
                                color="black",
                                font_weight="bold",
                                padding="0.75em 2em",
                                border_radius="0.5em",
                                margin_top="1em",
                                width="100%",
                            ),
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
            
            # Mensaje de estado
            rx.cond(
                ChangePasswordState.message != "",
                rx.box(
                    rx.text(
                        ChangePasswordState.message,
                        color=rx.cond(
                            ChangePasswordState.message_type == "success",
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
            max_width="800px",
            margin="0 auto",
        ),
        
        # Botón de regreso
        rx.hstack(
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
        
        background_color=COLORS["background"],
        width="100%",
        min_height="100vh",
        spacing="0",
    )

