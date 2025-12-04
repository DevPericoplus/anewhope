import reflex as rx
from typing import Optional
import sys
from pathlib import Path

# Agregar el path para importar módulos del dominio
domain_entities_path = Path(__file__).parent.parent.parent.parent / "1_shared_domain" / "entities"
sys.path.insert(0, str(domain_entities_path))

# Intentar importar la función de validación de organización
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
    
    # Mensaje de estado
    message: str = ""
    message_type: str = ""  # "success" o "error"
    show_org_error_modal: bool = False  # Controla si se muestra el modal de error de organización
    show_org_creation_modal: bool = False  # Controla si se muestra el modal de creación de organización
    
    # Campos para el formulario de creación de organización
    org_email: str = ""
    org_tlf: str = ""
    org_address: str = ""
    org_country: str = ""
    org_state: str = ""
    
    # Objeto UserExtended creado en memoria
    created_user: Optional[dict] = None
    
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
        self.created_user = None
        
        # Validar acceso desde la página principal
        # Verificar si se accedió desde la página principal usando parámetros de query string
        # En Reflex, los parámetros de query string se pueden obtener del router
        # Si no se accedió desde la página principal (from_page != "main"), redirigir
        # Nota: El parámetro from_page se establece automáticamente desde la URL si existe
        if self.from_page != "main":
            # Redirigir a la página principal si se accede directamente por URL
            return rx.redirect("/")
    
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
    
    def set_user_password_confirm(self, value: str):
        self.user_password_confirm = value
    
    def set_user_email(self, value: str):
        self.user_email = value
    
    def set_user_mobile(self, value: str):
        self.user_mobile = value
    
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
            
            if not self.user_mobile or not self.user_mobile.strip():
                self.message = "El número de móvil es requerido"
                self.message_type = "error"
                return
            
            if not self.user_otp or len(self.user_otp) != 4 or not self.user_otp.isdigit():
                self.message = "El OTP debe tener exactamente 4 dígitos"
                self.message_type = "error"
                return
            
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
            
            # Crear el objeto UserExtended en memoria (simulado como diccionario)
            # En el futuro se creará el objeto real de dominio
            self.created_user = {
                "user_id": user_id_int,
                "organization_id": org_id_int,
                "identity_type_id": identity_id_int,
                "user_name": self.user_name.strip(),
                "user_password": self.user_password,
                "user_email": self.user_email.strip().lower(),
                "user_mobile": self.user_mobile.strip(),
                "user_otp": self.user_otp,
                "active": self.active,
                "blocked": self.blocked,
                "contact_info": {
                    "first_name": self.contact_first_name.strip(),
                    "sur_name": self.contact_sur_name.strip(),
                    "country": self.contact_country.strip(),
                    "state": self.contact_state.strip(),
                    "zip_code": self.contact_zip_code.strip(),
                    "address": self.contact_address.strip(),
                },
                "billing_info": {
                    "first_name": self.billing_first_name.strip() if self.billing_first_name.strip() else self.contact_first_name.strip(),
                    "sur_name": self.billing_sur_name.strip() if self.billing_sur_name.strip() else self.contact_sur_name.strip(),
                    "country": self.billing_country.strip() if self.billing_country.strip() else self.contact_country.strip(),
                    "state": self.billing_state.strip() if self.billing_state.strip() else self.contact_state.strip(),
                    "zip_code": self.billing_zip_code.strip() if self.billing_zip_code.strip() else self.contact_zip_code.strip(),
                    "address": self.billing_address.strip() if self.billing_address.strip() else self.contact_address.strip(),
                },
            }
            
            self.message = f"Usuario {self.user_name} creado exitosamente en memoria (ID: {user_id_int})"
            self.message_type = "success"
            
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


def user_creation_page() -> rx.Component:
    """Página de creación de usuario."""
    # Ejecutar secure_access al cargar la página
    # on_mount se ejecutará automáticamente cuando se monte el componente
    return rx.vstack(
        # Modal de error de organización (si está activo)
        organization_error_modal(),
        # Modal de creación de organización (si está activo)
        organization_creation_modal(),
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
                                on_change=UserCreationState.set_user_password,
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
                                on_change=UserCreationState.set_user_password_confirm,
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
                    spacing="2",
                ),
                padding="1.5em",
                background_color=COLORS["card"],
                border=f"1px solid {COLORS['border']}",
                border_radius="0.5em",
                width="100%",
                margin_bottom="1em",
            ),
            # Sección: Información de Facturación (Opcional)
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
        background_color=COLORS["background"],
        width="100%",
        min_height="100vh",
        spacing="0",
    )

