from pathlib import Path
from typing import Optional

import reflex as rx

from adapters.api_client import get_user_permissions, login_user, refresh_tokens

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

# Define the State class for managing application state
class State(rx.State):
    """Main application state."""
    
    # User portal state
    user_active_menu: str = "inicio"
    user_username: str = ""
    user_password: str = ""
    user_otp: str = ""
    user_logged_in: bool = False
    user_active_tab: str = "resumen"
    access_token: str = ""
    session_token: str = ""
    user_id: int = 0
    organization_id: int = 0
    user_permissions: list[dict[str, str]] = []
    login_error: str = ""
    
    def set_user_menu(self, menu: str):
        """Set active menu item for user portal."""
        self.user_active_menu = menu
    
    def set_user_username(self, username: str):
        """Set user username."""
        self.user_username = username
    
    def set_user_password(self, password: str):
        """Set user password."""
        self.user_password = password

    def set_user_otp(self, otp: str):
        """Set user OTP."""
        self.user_otp = otp
    
    def user_login(self):
        """Handle user portal login."""
        if not self.user_username or not self.user_password or not self.user_otp:
            self.login_error = "Debe ingresar usuario, contraseña y OTP"
            return

        response = login_user(self.user_username, self.user_password, self.user_otp)
        access_token = response.get("access_token")
        session_token = response.get("session_token")
        if not access_token or not session_token:
            self.login_error = "No se pudo autenticar con el middleware"
            return

        self.user_id = int(response.get("user_id", 0))
        self.organization_id = int(response.get("organization_id", 0))
        self.access_token = access_token
        self.session_token = session_token
        self.user_logged_in = True
        self.login_error = ""

        permissions_response = get_user_permissions(access_token, session_token)
        self.user_permissions = permissions_response.get("permissions", [])
    
    def user_logout(self):
        """Handle user portal logout."""
        self.user_logged_in = False
        self.user_username = ""
        self.user_password = ""
        self.user_otp = ""
        self.access_token = ""
        self.session_token = ""
        self.user_id = 0
        self.organization_id = 0
        self.user_permissions = []
        self.login_error = ""

    def refresh_session_tokens(self):
        """Renueva los tokens de sesión mediante el middleware."""

        if not self.session_token:
            self.login_error = "No hay sesión activa para renovar"
            return
        response = refresh_tokens(self.session_token)
        access_token = response.get("access_token")
        session_token = response.get("session_token")
        if not access_token or not session_token:
            self.login_error = "No se pudieron renovar los tokens"
            return
        self.access_token = access_token
        self.session_token = session_token
    
    def set_user_tab(self, tab: str):
        """Set active tab for user dashboard."""
        self.user_active_tab = tab


def load_presentation_content() -> str:
    """Carga el contenido de presentación desde un archivo externo."""
    try:
        # Obtiene la ruta de presentation.txt relativa a este archivo
        current_dir = Path(__file__).parent.parent
        presentation_file = current_dir / "presentation.txt"
        with open(presentation_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except (FileNotFoundError, IOError):
        # Contenido por defecto si el archivo no existe
        return (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
            "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
        )


def load_menu_content(filename: str, fallback_text: str) -> str:
    """Carga contenido de un archivo .txt del menú con fallback."""

    try:
        # Obtiene la ruta del archivo relativa a este archivo
        current_dir = Path(__file__).parent.parent
        content_file = current_dir / filename
        with open(content_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except (FileNotFoundError, IOError):
        # Contenido por defecto si el archivo no existe
        return fallback_text


def logo() -> rx.Component:
    """Logo component."""
    return rx.hstack(
        rx.text("MY", font_weight="bold", font_size="1.5em", color=COLORS["primary"]),
        rx.text("llm", font_size="1.5em", color=COLORS["foreground"]),
        spacing="1",
    )


def login_panel() -> rx.Component:
    """Login panel for user portal."""
    return rx.vstack(
            rx.text("Acceso de Usuario", font_size="1.1em", font_weight="bold", color=COLORS["foreground"]),
            rx.vstack(
                rx.vstack(
                    rx.text("Usuario", font_size="0.9em", color=COLORS["muted_foreground"]),
                    rx.input(
                        placeholder="Ingrese su usuario",
                        on_change=State.set_user_username,
                        value=State.user_username,
                        background_color=COLORS["input"],
                        border_color=COLORS["border"],
                        color=COLORS["foreground"],
                        width="100%",
                        border_radius="5px",
                    ),
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("Contraseña", font_size="0.9em", color=COLORS["muted_foreground"]),
                    rx.input(
                        placeholder="Ingrese su contraseña",
                        type_="password",
                        on_change=State.set_user_password,
                        value=State.user_password,
                        background_color=COLORS["input"],
                        border_color=COLORS["border"],
                        color=COLORS["foreground"],
                        width="100%",
                        border_radius="5px",
                    ),
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("OTP", font_size="0.9em", color=COLORS["muted_foreground"]),
                    rx.input(
                        placeholder="Ingrese su OTP",
                        on_change=State.set_user_otp,
                        value=State.user_otp,
                        background_color=COLORS["input"],
                        border_color=COLORS["border"],
                        color=COLORS["foreground"],
                        width="100%",
                        border_radius="5px",
                    ),
                    spacing="1",
                ),
                spacing="2",
            ),
            rx.button(
                "Iniciar Sesión",
                on_click=State.user_login,
                background_color=COLORS["primary"],
                color=COLORS["background"],
                width="100%",
                font_weight="bold",
            ),
            rx.text(
                State.login_error,
                color="red",
                font_size="0.85em",
                display=rx.cond(State.login_error != "", "block", "none"),
            ),
            rx.vstack(
                rx.link(
                    "Crear nuevo usuario",
                    color=COLORS["primary"],
                    href="/user_creation?from=main",
                    font_size="0.9em",
                ),
                rx.link("Recordar contraseña", color=COLORS["primary"], href="/change_password?from=main", font_size="0.9em"),
                spacing="1",
            ),
            spacing="2",
            padding="1.5em",
            background_color=COLORS["card"],
            border=f"1px solid {COLORS['border']}",
            border_radius="0.5em",
            width="100%",
        )


def sidebar_menu() -> rx.Component:
    """Sidebar menu for navigation."""
    menu_items = ["inicio", "servicios", "proyectos", "soporte", "contacto"]
    
    return rx.vstack(
            rx.text("Menú", font_size="1.1em", font_weight="bold", color=COLORS["foreground"], margin_bottom="1em"),
            rx.vstack(
                *[
                    rx.button(
                        item.title(),
                        on_click=lambda _, i=item: State.set_user_menu(i),
                        background_color=rx.cond(
                            State.user_active_menu == item,
                            COLORS["primary"],
                            "transparent"
                        ),
                        color=rx.cond(
                            State.user_active_menu == item,
                            COLORS["background"],
                            COLORS["foreground"]
                        ),
                        width="100%",
                        justify_content="flex-start",
                        border="none",
                        padding="0.75em",
                        border_radius="0.5em",
                        cursor="pointer",
                        text_align="left",
                        _hover={"opacity": "0.8"},
                    )
                    for item in menu_items
                ],
                spacing="1",
                align_items="flex-start",
                width="100%",
            ),
            align_items="flex-start",
            width="100%",
        )


def info_panel(active_item: str) -> rx.Component:
    """Info panel displaying content based on active menu item."""
    presentation_text = load_presentation_content()
    services_text = load_menu_content(
        "services.txt", "Servicios especializados para impulsar sus proyectos de IA."
    )
    projects_text = load_menu_content(
        "proyectos.txt", "Proyectos y entregas en progreso."
    )
    support_text = load_menu_content(
        "soporte.txt", "Soporte técnico y acompañamiento."
    )
    contact_text = load_menu_content(
        "contacto.txt", "Canales de contacto y atención al cliente."
    )

    heading_text = rx.match(
        active_item,
        ("servicios", "Servicios"),
        ("proyectos", "Proyectos"),
        ("soporte", "Soporte"),
        ("contacto", "Contacto"),
        "Inicio",
    )
    content_text = rx.match(
        active_item,
        ("servicios", services_text),
        ("proyectos", projects_text),
        ("soporte", support_text),
        ("contacto", contact_text),
        presentation_text,
    )
    
    return rx.vstack(
        rx.heading(heading_text, size="8", color=COLORS["foreground"]),
        rx.cond(
            active_item == "inicio",
            rx.box(
                rx.image(
                    src="/logo.jpg",
                    alt="Myllm Logo",
                    width="150px",
                    max_width="100%",
                    height="auto",
                ),
                width="100%",
                display="flex",
                justify_content="center",
                align_items="center",
                margin_y="1em",
            ),
            rx.box(height="0"),
        ),
        rx.text(
            content_text,
            color=COLORS["muted_foreground"],
            font_size="1em",
            line_height="1.5em",
            white_space="pre-line",
            font_family="Inter, system-ui, sans-serif",
            width="100%",
        ),
        rx.flex(
            rx.box(
                rx.vstack(
                    rx.text("Perplejidad", color=COLORS["muted_foreground"], font_size="0.9em"),
                    rx.text("≈30", font_size="2em", font_weight="bold", color=COLORS["foreground"]),
                    spacing="1",
                ),
                padding="1.5em",
                background_color=COLORS["card"],
                border=f"1px solid {COLORS['border']}",
                border_radius="0.5em",
                flex="1",
            ),
            rx.box(
                rx.vstack(
                    rx.text("BLEU Score", color=COLORS["muted_foreground"], font_size="0.9em"),
                    rx.text("0.5+", font_size="2em", font_weight="bold", color=COLORS["foreground"]),
                    spacing="1",
                ),
                padding="1.5em",
                background_color=COLORS["card"],
                border=f"1px solid {COLORS['border']}",
                border_radius="0.5em",
                flex="1",
            ),
            rx.box(
                rx.vstack(
                    rx.text("F1 Score", color=COLORS["muted_foreground"], font_size="0.9em"),
                    rx.text("≈70−80", font_size="2em", font_weight="bold", color=COLORS["foreground"]),
                    spacing="1",
                ),
                padding="1.5em",
                background_color=COLORS["card"],
                border=f"1px solid {COLORS['border']}",
                border_radius="0.5em",
                flex="1",
            ),
            direction="row",
            spacing="4",
            width="100%",
        ),
        spacing="4",
        padding="2em",
        width="100%",
    )


def dashboard_tabs() -> rx.Component:
    """Dashboard with tabs for user portal."""
    tabs_config = [
        ("resumen", "Resumen"),
        ("proyectos", "Proyectos"),
        ("tareas", "Tareas"),
        ("reportes", "Reportes"),
        ("documentos", "Documentos"),
        ("configuracion", "Configuración"),
    ]
    
    active_tab = State.user_active_tab
    set_tab = State.set_user_tab
    
    return rx.vstack(
        rx.hstack(
            *[
                rx.button(
                    label,
                    on_click=lambda _, t=tab_id: set_tab(t),
                    background_color=rx.cond(
                        active_tab == tab_id,
                        COLORS["primary"],
                        "transparent"
                    ),
                    color=rx.cond(
                        active_tab == tab_id,
                        COLORS["background"],
                        COLORS["foreground"]
                    ),
                    border="none",
                    padding="0.75em 1.5em",
                    border_radius="0.5em",
                    cursor="pointer",
                    _hover={"opacity": "0.8"},
                    font_weight="bold",
                )
                for tab_id, label in tabs_config
            ],
            spacing="2",
            padding="1.5em",
            border_bottom=f"1px solid {COLORS['border']}",
            width="100%",
        ),
        rx.cond(
            active_tab == "resumen",
            rx.vstack(
                rx.heading("Resumen General", size="6", color=COLORS["foreground"]),
                rx.flex(
                    rx.box(
                        rx.vstack(
                            rx.text("Proyectos Activos", color=COLORS["muted_foreground"], font_size="0.9em"),
                            rx.text("12", font_size="2.5em", font_weight="bold", color=COLORS["foreground"]),
                            spacing="1",
                        ),
                        padding="1.5em",
                        background_color=COLORS["card"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.5em",
                        flex="1",
                    ),
                    rx.box(
                        rx.vstack(
                            rx.text("Tareas Pendientes", color=COLORS["muted_foreground"], font_size="0.9em"),
                            rx.text("24", font_size="2.5em", font_weight="bold", color=COLORS["foreground"]),
                            spacing="1",
                        ),
                        padding="1.5em",
                        background_color=COLORS["card"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.5em",
                        flex="1",
                    ),
                    rx.box(
                        rx.vstack(
                            rx.text("Reportes Nuevos", color=COLORS["muted_foreground"], font_size="0.9em"),
                            rx.text("36", font_size="2.5em", font_weight="bold", color=COLORS["foreground"]),
                            spacing="1",
                        ),
                        padding="1.5em",
                        background_color=COLORS["card"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.5em",
                        flex="1",
                    ),
                    direction="row",
                    spacing="4",
                    width="100%",
                ),
                spacing="4",
                padding="1.5em",
            ),
        ),
        rx.cond(
            active_tab == "proyectos",
            rx.vstack(
                rx.heading("Proyectos", size="6", color=COLORS["foreground"]),
                *[
                    rx.hstack(
                        rx.vstack(
                            rx.text(f"Proyecto {chr(65+i)}", font_weight="bold", color=COLORS["foreground"]),
                            rx.text("En progreso", color=COLORS["muted_foreground"], font_size="0.9em"),
                            spacing="1",
                        ),
                        rx.text(f"{75 - i*15}% completado", color=COLORS["primary"], font_size="0.9em"),
                        padding="1em",
                        background_color=COLORS["card"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.5em",
                        width="100%",
                        justify_content="space-between",
                    )
                    for i in range(3)
                ],
                spacing="2",
                padding="1.5em",
            ),
        ),
        rx.cond(
            active_tab == "tareas",
            rx.vstack(
                rx.heading("Tareas", size="6", color=COLORS["foreground"]),
                *[
                    rx.hstack(
                        rx.checkbox(checked=False),
                        rx.text(task, color=COLORS["foreground"]),
                        padding="1em",
                        background_color=COLORS["card"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.5em",
                        width="100%",
                        align_items="center",
                    )
                    for task in [
                        "Revisar documentación",
                        "Actualizar sistema",
                        "Reunión con equipo",
                        "Preparar presentación",
                    ]
                ],
                spacing="2",
                padding="1.5em",
            ),
        ),
        rx.cond(
            active_tab == "reportes",
            rx.vstack(
                rx.heading("Reportes", size="6", color=COLORS["foreground"]),
                rx.flex(
                    *[
                        rx.box(
                            rx.vstack(
                                rx.text(report, font_weight="bold", color=COLORS["foreground"]),
                                rx.text("Generado: Nov 2026", color=COLORS["muted_foreground"], font_size="0.9em"),
                                spacing="1",
                            ),
                            padding="1.5em",
                            background_color=COLORS["card"],
                            border=f"1px solid {COLORS['border']}",
                            border_radius="0.5em",
                            flex="1",
                        )
                        for report in [
                            "Reporte Mensual",
                            "Análisis de Rendimiento",
                            "Estadísticas de Uso",
                            "Informe Financiero",
                        ]
                    ],
                    direction="row",
                    spacing="4",
                    width="100%",
                ),
                spacing="4",
                padding="1.5em",
            ),
        ),
        rx.cond(
            active_tab == "documentos",
            rx.vstack(
                rx.heading("Documentos", size="6", color=COLORS["foreground"]),
                *[
                    rx.hstack(
                        rx.text(doc, color=COLORS["foreground"]),
                        rx.link("Descargar", color=COLORS["primary"], href="#", font_size="0.9em"),
                        padding="1em",
                        background_color=COLORS["card"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.5em",
                        width="100%",
                        justify_content="space-between",
                    )
                    for doc in [
                        "Manual de Usuario.pdf",
                        "Guía de Inicio.docx",
                        "Especificaciones Técnicas.pdf",
                        "Contrato de Servicio.pdf",
                    ]
                ],
                spacing="2",
                padding="1.5em",
            ),
        ),
        rx.cond(
            active_tab == "configuracion",
            rx.vstack(
                rx.heading("Configuración", size="6", color=COLORS["foreground"]),
                rx.vstack(
                    rx.vstack(
                        rx.text("Notificaciones por email", color=COLORS["muted_foreground"], font_size="0.9em"),
                        rx.hstack(
                            rx.checkbox(checked=True),
                            rx.text("Activadas", color=COLORS["foreground"]),
                        ),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Idioma", color=COLORS["muted_foreground"], font_size="0.9em"),
                        rx.select(
                            ["Español", "English"],
                            value="Español",
                            background_color=COLORS["input"],
                            border_color=COLORS["border"],
                            color=COLORS["foreground"],
                            width="100%",
                        ),
                        spacing="1",
                    ),
                    spacing="3",
                    padding="1.5em",
                    background_color=COLORS["card"],
                    border=f"1px solid {COLORS['border']}",
                    border_radius="0.5em",
                ),
                spacing="3",
                padding="1.5em",
            ),
        ),
        spacing="0",
        width="100%",
        background_color=COLORS["background"],
    )


def footer() -> rx.Component:
    """Footer component."""
    return rx.vstack(
        rx.hstack(
            rx.vstack(
                rx.text("Productos", font_weight="bold", color=COLORS["foreground"], font_size="0.9em"),
                rx.link("Características", color=COLORS["primary"], href="#", font_size="0.9em"),
                rx.link("Precios", color=COLORS["primary"], href="#", font_size="0.9em"),
                rx.link("Seguridad", color=COLORS["primary"], href="#", font_size="0.9em"),
                spacing="1",
            ),
            rx.vstack(
                rx.text("Empresa", font_weight="bold", color=COLORS["foreground"], font_size="0.9em"),
                rx.link("Nosotros", color=COLORS["primary"], href="#", font_size="0.9em"),
                rx.link("Blog", color=COLORS["primary"], href="#", font_size="0.9em"),
                rx.link("Carreras", color=COLORS["primary"], href="#", font_size="0.9em"),
                spacing="1",
            ),
            rx.vstack(
                rx.text("Recursos", font_weight="bold", color=COLORS["foreground"], font_size="0.9em"),
                rx.link("Documentación", color=COLORS["primary"], href="#", font_size="0.9em"),
                rx.link("Comunidad", color=COLORS["primary"], href="#", font_size="0.9em"),
                rx.link("Soporte", color=COLORS["primary"], href="#", font_size="0.9em"),
                spacing="1",
            ),
            rx.vstack(
                rx.text("Legal", font_weight="bold", color=COLORS["foreground"], font_size="0.9em"),
                rx.link("Privacidad", color=COLORS["primary"], href="#", font_size="0.9em"),
                rx.link("Términos", color=COLORS["primary"], href="#", font_size="0.9em"),
                rx.link("Cookies", color=COLORS["primary"], href="#", font_size="0.9em"),
                spacing="1",
            ),
            spacing="6",
            width="100%",
            padding="2em",
            justify_content="center",
            align="center",
        ),
        rx.divider(margin_y="1em"),
        rx.box(
            rx.text(
                "© 2025 Myllm. Todos los derechos reservados.",
                color=COLORS["muted_foreground"],
                font_size="0.9em",
                text_align="center",
            ),
            width="100%",
            padding="1em",
            display="flex",
            justify_content="center",
            align_items="center",
        ),
        background_color=COLORS["card"],
        border_top=f"1px solid {COLORS['border']}",
        width="100%",
        spacing="0",
    )


def user_portal() -> rx.Component:
    """User portal main page."""
    return rx.cond(
        State.user_logged_in,
        rx.vstack(
            rx.hstack(
                rx.heading("User Portal - Dashboard", size="8", color=COLORS["foreground"]),
                rx.button(
                    "Logout",
                    on_click=State.user_logout,
                    background_color=COLORS["primary"],
                    color=COLORS["background"],
                ),
                width="100%",
                justify_content="space-between",
                padding="1em",
                background_color=COLORS["card"],
                border_bottom=f"1px solid {COLORS['border']}",
            ),
            dashboard_tabs(),
            footer(),
            background_color=COLORS["background"],
            width="100%",
            min_height="100vh",
            spacing="0",
        ),
        rx.vstack(
            rx.hstack(
                logo(),
                rx.box(flex_grow="1"),
                rx.text("Pagina principal", color=COLORS["muted_foreground"], font_size="0.9em"),
                width="100%",
                padding="1em",
                background_color=COLORS["card"],
                border_bottom=f"1px solid {COLORS['border']}",
                align_items="center",
            ),
            rx.hstack(
                rx.box(
                    rx.vstack(
                        login_panel(),
                        sidebar_menu(),
                        spacing="4",
                        padding="1.5em",
                    ),
                    width="25%",
                    padding="1em",
                    background_color=COLORS["card"],
                    border_right=f"1px solid {COLORS['border']}",
                    height="100%",
                ),
                rx.box(
                    info_panel(State.user_active_menu),
                    width="75%",
                    background_color=COLORS["background"],
                    padding="0",
                    height="100%",
                ),
                width="100%",
                spacing="0",
                flex="1",
                align_items="stretch",
            ),
            footer(),
            background_color=COLORS["background"],
            width="100%",
            min_height="100vh",
            spacing="0",
        ),
    )


# Crear la aplicación
app = rx.App(
    style={
        "font_family": "Inter, system-ui, sans-serif",
    },
)

# User portal route
app.add_page(user_portal, route="/", title="Myllm - Pagina principal")

# User creation route
import sys
from pathlib import Path
# Agregar el directorio 5_web_frontend al path para importar pages
frontend_dir = Path(__file__).parent.parent
if str(frontend_dir) not in sys.path:
    sys.path.insert(0, str(frontend_dir))

try:
    from pages.user_creation import user_creation_page
    app.add_page(user_creation_page, route="/user_creation", title="Myllm - Crear Usuario")
    print("✅ Ruta /user_creation registrada exitosamente")
except ImportError as e:
    print(f"⚠️ Warning: Could not import user_creation_page: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Error al registrar ruta /user_creation: {e}")
    import traceback
    traceback.print_exc()

try:
    from pages.change_password import change_password_page
    app.add_page(change_password_page, route="/change_password", title="Myllm - Recordar Contraseña")
    print("✅ Ruta /change_password registrada exitosamente")
except ImportError as e:
    print(f"⚠️ Warning: Could not import change_password_page: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Error al registrar ruta /change_password: {e}")
    import traceback
    traceback.print_exc()
