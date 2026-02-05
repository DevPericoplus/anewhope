"""
Componente Seguimiento para Web Frontend (Cliente)

Integra:
1. Notificaciones (template completo)
2. Calendario (template completo)
3. Visor de Tickets (custom)
"""

import reflex as rx
import datetime
import pydantic
import calendar
from sqlalchemy import text


# ============================================================================
# COLORS
# ============================================================================

COLORS = {
    "background": "#0B1120",
    "card": "#141b2d",
    "border": "#1e2744",
    "primary": "#22c55e",  # Verde del tema frontend
    "foreground": "#ffffff",
    "muted_foreground": "#94a3b8",
}


# ============================================================================
# NOTIFICACIONES (desde template)
# ============================================================================

class Message(pydantic.BaseModel):
    text: str
    sender: str  # "interno" o "cliente"
    time: str = ""


def get_formatted_time():
    now = datetime.datetime.now()
    meses = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }
    return f"{now.day} de {meses[now.month]} de {now.year} a las {now.strftime('%H:%M')}"


# ============================================================================
# CALENDARIO (desde template)
# ============================================================================

class DayInfo(pydantic.BaseModel):
    day: int
    border_color: str = "transparent"
    has_event: bool = False
    is_today: bool = False
    events: list[dict] = []


# ============================================================================
# SEGUIMIENTO STATE (combina notificaciones, calendario y tickets)
# ============================================================================

class SeguimientoState(rx.State):
    """Estado combinado para seguimiento."""

    # Selector de proyecto
    seguimiento_projects_select: list[str] = []
    seguimiento_project_name: str = ""
    seguimiento_project_id: int = 0

    # === NOTIFICACIONES ===
    messages: list[Message] = [
        Message(text="¡Buenas! Soy el interface de notificaciones", sender="interno", time="27 de enero de 2026 a las 23:00"),
        Message(text="Te tendré informado en todo momento de los pasos a seguir", sender="interno", time="27 de enero de 2026 a las 23:01"),
        Message(text="¿En mensajes como este puedo solicitar información o comunicar cambios?", sender="cliente", time="27 de enero de 2026 a las 23:05"),
        Message(text="Sí, la idea es asesorarte sobre ellas y consensuar los cambios", sender="interno", time="27 de enero de 2026 a las 23:06"),
    ]
    new_message: str = ""
    current_identity: str = "cliente"

    # === CALENDARIO ===
    current_year: int = datetime.datetime.now().year
    current_month: int = datetime.datetime.now().month
    years: list[str] = [str(y) for y in range(2020, 2031)]
    month_names: list[str] = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    months: list[str] = month_names
    _month_map = {name: i+1 for i, name in enumerate(month_names)}
    selected_year: str = str(datetime.datetime.now().year)
    selected_month: str = month_names[datetime.datetime.now().month - 1]
    events_data: list[dict] = []

    # === TICKETS ===
    tickets_list: list[dict] = []
    is_loading_tickets: bool = False
    tickets_error: str = ""

    def _get_db_engine(self):
        """Obtiene el engine de la base de datos desde el State principal."""
        try:
            from ..web_frontend.web_frontend import State as MainState
            state = self.get_state(MainState)
            return state._db_engine
        except Exception as e:
            print(f"Error obteniendo engine: {e}")
            return None

    # === MÉTODOS NOTIFICACIONES ===

    def format_and_add_message(self, sender: str, text: str):
        """Añade mensajes desde aplicaciones externas"""
        formatted_text = text[0].upper() + text[1:] if len(text) > 0 else text
        if not formatted_text.endswith((".", "!", "?")):
            formatted_text += "."

        self.messages.append(
            Message(
                text=formatted_text,
                sender=sender,
                time=get_formatted_time()
            )
        )
        return rx.scroll_to("chat_bottom")

    def send_message(self):
        """Envía el mensaje escrito en el input"""
        if self.new_message:
            self.format_and_add_message(self.current_identity, self.new_message)
            self.new_message = ""

    def handle_keypress(self, key: str):
        if key == "Enter":
            return self.send_message()

    def set_identity_interno(self):
        self.current_identity = "interno"

    def set_identity_cliente(self):
        self.current_identity = "cliente"

    # === MÉTODOS CALENDARIO ===

    def load_events_data(self):
        """Adapter to load events (placeholder)."""
        self.events_data = []

    @rx.var
    def month_days_with_events(self) -> list[list[DayInfo]]:
        """Returns a matrix of DayInfo objects for the selected month."""
        try:
            y = int(self.selected_year)
            m = self._month_map.get(self.selected_month, 1)

            now = datetime.datetime.now()
            today_day = now.day
            today_month = now.month
            today_year = now.year

            cal = calendar.Calendar(firstweekday=0)
            raw_weeks = cal.monthdayscalendar(y, m)

            processed_weeks = []
            for week in raw_weeks:
                processed_week = []
                for day in week:
                    if day == 0:
                        processed_week.append(DayInfo(day=0))
                        continue

                    is_today = (day == today_day and m == today_month and y == today_year)

                    processed_week.append(DayInfo(
                        day=day,
                        border_color="transparent",
                        has_event=False,
                        is_today=is_today,
                        events=[]
                    ))
                processed_weeks.append(processed_week)

            return processed_weeks

        except Exception as e:
            print(f"Error calculando días: {e}")
            return []

    def set_year(self, year: str):
        self.selected_year = year
        self.current_year = int(year)

    def set_month(self, month: str):
        self.selected_month = month
        self.current_month = self._month_map.get(month, 1)

    # === MÉTODOS TICKETS ===

    def set_seguimiento_project(self, project_name: str):
        """Cambia el proyecto seleccionado y carga los tickets."""
        self.seguimiento_project_name = project_name
        engine = self._get_db_engine()
        if not engine:
            self.tickets_error = "Error de conexión a base de datos"
            return

        try:
            with engine.connect() as conn:
                query = text("""
                    SELECT id FROM myllm_projects_db.proyectos
                    WHERE nombre = :nombre
                    LIMIT 1
                """)
                result = conn.execute(query, {"nombre": project_name}).fetchone()

                if result:
                    self.seguimiento_project_id = result[0]
                    yield self.load_tickets()
                else:
                    self.seguimiento_project_id = 0
                    self.tickets_list = []

        except Exception as e:
            print(f"Error al obtener project_id: {e}")
            self.tickets_error = f"Error: {str(e)}"

    def load_tickets(self):
        """Carga los tickets del proyecto seleccionado."""
        self.is_loading_tickets = True
        self.tickets_error = ""
        engine = self._get_db_engine()
        if not engine:
            self.tickets_error = "Error de conexión a base de datos"
            self.is_loading_tickets = False
            return

        try:
            from ..web_frontend.web_frontend import State as MainState
            main_state = self.get_state(MainState)
            user_id = main_state.user_id
            org_id = main_state.organization_id

            with engine.connect() as conn:
                query = text("""
                    SELECT id, titulo, estado, prioridad, fecha_creacion, fecha_actualizacion
                    FROM myllm_projects_db.tickets
                    WHERE id_organizacion = :org_id
                      AND cliente_id = :user_id
                      AND (id_proyecto = :project_id OR id_proyecto IS NULL)
                    ORDER BY fecha_actualizacion DESC, fecha_creacion DESC
                    LIMIT 50
                """)

                results = conn.execute(query, {
                    "org_id": org_id,
                    "user_id": user_id,
                    "project_id": self.seguimiento_project_id if self.seguimiento_project_id > 0 else None
                })

                self.tickets_list = []
                for row in results:
                    self.tickets_list.append({
                        "id": row[0],
                        "titulo": row[1],
                        "estado": row[2],
                        "prioridad": row[3],
                        "fecha_creacion": row[4].strftime("%Y-%m-%d %H:%M") if row[4] else "",
                        "fecha_actualizacion": row[5].strftime("%Y-%m-%d %H:%M") if row[5] else "",
                    })

        except Exception as e:
            print(f"Error al cargar tickets: {e}")
            self.tickets_error = f"Error: {str(e)}"
        finally:
            self.is_loading_tickets = False

    @rx.event
    async def on_mount_seguimiento(self):
        """Se ejecuta cuando se monta el componente."""
        engine = self._get_db_engine()
        if not engine:
            return

        try:
            from ..web_frontend.web_frontend import State as MainState
            main_state = self.get_state(MainState)
            org_id = main_state.organization_id

            with engine.connect() as conn:
                query = text("""
                    SELECT nombre FROM myllm_projects_db.proyectos
                    WHERE id_organizacion = :org_id
                    ORDER BY nombre
                """)
                results = conn.execute(query, {"org_id": org_id})
                self.seguimiento_projects_select = [row[0] for row in results]

        except Exception as e:
            print(f"Error al cargar proyectos: {e}")


# ============================================================================
# COMPONENTE NOTIFICACIONES (desde template)
# ============================================================================

def chat_bubble(msg: Message) -> rx.Component:
    is_cliente = (msg.sender == "cliente")

    return rx.hstack(
        rx.vstack(
            rx.box(
                rx.text(msg.text, color="black", font_size="1.3em", line_height="1.4"),
                bg=rx.cond(is_cliente, "#f3c7d6", "white"),
                padding="14px 20px",
                border_radius=rx.cond(
                    is_cliente,
                    "24px 24px 6px 24px",
                    "24px 24px 24px 6px"
                ),
                max_width="100%",
                box_shadow="0px 2px 4px rgba(0,0,0,0.1)",
            ),
            rx.text(
                msg.time,
                font_size="0.95em",
                color="#00008B",
                padding_x="10px",
                margin_top="4px",
            ),
            align_items=rx.cond(is_cliente, "end", "start"),
            spacing="0",
            max_width="85%",
        ),
        id=rx.cond(SeguimientoState.messages[-1].text == msg.text, "chat_bottom", ""),
        width="100%",
        justify=rx.cond(is_cliente, "end", "start"),
        padding_x="14px",
        padding_y="12px",
    )


def notificaciones_component() -> rx.Component:
    """Chat estilo móvil (desde template)."""
    return rx.vstack(
        # Pantalla del chat
        rx.vstack(
            rx.auto_scroll(
                rx.vstack(
                    rx.foreach(SeguimientoState.messages, chat_bubble),
                    width="100%",
                    padding_top="2.5em",
                    padding_bottom="40px",
                ),
                height="100%",
                style={
                    "&::-webkit-scrollbar": {"display": "none"},
                    "scrollbar-width": "none",
                    "-ms-overflow-style": "none",
                },
            ),
            flex="1",
            width="100%",
            bg="transparent",
            padding_x="12px",
            overflow="hidden",
        ),
        # Barra de entrada inferior
        rx.vstack(
            # Selector de emisor
            rx.hstack(
                rx.box(
                    rx.vstack(
                        rx.icon(tag="user", size=26, color=rx.cond(SeguimientoState.current_identity == "cliente", "#222", "#999")),
                        rx.text("Cliente", size="3", color="#666"),
                        spacing="1",
                        align="center",
                    ),
                    on_click=SeguimientoState.set_identity_cliente,
                    cursor="pointer",
                    padding="10px",
                    bg=rx.cond(SeguimientoState.current_identity == "cliente", "#f3c7d6", "transparent"),
                    border_radius="14px",
                ),
                rx.box(
                    rx.vstack(
                        rx.icon(tag="shield-check", size=26, color=rx.cond(SeguimientoState.current_identity == "interno", "#222", "#999")),
                        rx.text("Interno", size="3", color="#666"),
                        spacing="1",
                        align="center",
                    ),
                    on_click=SeguimientoState.set_identity_interno,
                    cursor="pointer",
                    padding="10px",
                    bg=rx.cond(SeguimientoState.current_identity == "interno", "white", "transparent"),
                    border_radius="14px",
                ),
                spacing="6",
                margin_bottom="10px",
            ),
            rx.hstack(
                rx.icon(tag="circle-plus", color="#666", size=26),
                rx.input(
                    placeholder="Escribe un mensaje...",
                    value=SeguimientoState.new_message,
                    on_change=SeguimientoState.set_new_message,
                    bg="white",
                    border="1px solid #ddd",
                    border_radius="28px",
                    flex="1",
                    color="black",
                    font_size="1.15em",
                    _placeholder={"color": "#999", "font_size": "1.15em"},
                    on_key_down=SeguimientoState.handle_keypress,
                    height="52px",
                ),
                rx.icon(
                    tag="send",
                    color="#666",
                    size=26,
                    on_click=SeguimientoState.send_message,
                    cursor="pointer",
                ),
                width="100%",
                padding="12px 20px",
                bg="#e0e0e0",
                border_radius="38px",
                spacing="4",
                align="center",
                box_shadow="0px 4px 15px rgba(0,0,0,0.2)",
            ),
            # Home Bar del móvil
            rx.center(
                rx.box(
                    width="100px",
                    height="5px",
                    bg="#222",
                    border_radius="10px",
                    opacity="0.2",
                    margin_top="12px",
                ),
                width="100%",
            ),
            width="100%",
            padding_x="18px",
            padding_bottom="25px",
            spacing="0",
        ),
        width="520px",
        height="calc(100vh - 140px)",
        border="5px solid #222",
        border_radius="70px",
        bg="linear-gradient(180deg, #FFFF00 0%, #00FFFF 100%)",
        box_shadow="0px 25px 70px rgba(0,0,0,0.3)",
        spacing="0",
        overflow="hidden",
        position="relative",
    )


# ============================================================================
# COMPONENTE CALENDARIO (desde template)
# ============================================================================

def calendar_cell(day_info: DayInfo):
    """Render a single day cell."""
    cell_visual = rx.center(
        rx.cond(
            day_info.day == 0,
            rx.text(""),
            rx.text(
                f"{day_info.day}",
                font_weight="500",
                color="white",
                font_size="0.9em"
            )
        ),
        width="28px",
        height="28px",
        border_radius="12px",
        bg=rx.cond(
            day_info.is_today,
            "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            "transparent"
        ),
        box_shadow=rx.cond(
            day_info.is_today,
            "0 4px 10px rgba(118, 75, 162, 0.4)",
            "none"
        ),
        transition="all 0.2s ease",
        _hover={
            "bg": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            "color": "white",
            "transform": "scale(1.1)",
            "box_shadow": "0 4px 10px rgba(118, 75, 162, 0.4)"
        },
        cursor="pointer"
    )

    return rx.center(
        cell_visual,
        width="36px",
        height="36px",
    )


def calendario_component():
    """Calendario widget (desde template)."""
    return rx.vstack(
        # Header
        rx.text(
            "Calendario",
            font_size="1.5em",
            font_weight="800",
            background_image="linear-gradient(45deg, #667eea 0%, #764ba2 100%)",
            background_clip="text",
            color="transparent",
            margin_bottom="15px",
            letter_spacing="-0.5px"
        ),

        # Selectors
        rx.hstack(
            rx.hstack(
                rx.text("Año:", color="yellow", font_weight="bold", font_size="0.9em"),
                rx.select(
                    SeguimientoState.years,
                    value=SeguimientoState.selected_year,
                    on_change=SeguimientoState.set_year,
                    size="2",
                    radius="medium",
                    width="100px",
                    bg="rgba(255,255,255,0.1)",
                    color="yellow",
                    border="1px solid yellow",
                    font_size="1.1em",
                    font_weight="bold"
                ),
                align="center",
                spacing="2"
            ),
            rx.hstack(
                rx.text("Mes:", color="yellow", font_weight="bold", font_size="0.9em"),
                rx.select(
                    SeguimientoState.months,
                    value=SeguimientoState.selected_month,
                    on_change=SeguimientoState.set_month,
                    size="2",
                    radius="medium",
                    width="80px",
                    bg="rgba(255,255,255,0.1)",
                    color="yellow",
                    border="1px solid yellow",
                    font_size="1.1em",
                    font_weight="bold"
                ),
                align="center",
                spacing="2"
            ),
            justify="between",
            width="100%",
            padding_x="10px",
            margin_bottom="20px"
        ),

        # Weekday Headers
        rx.hstack(
            *[rx.center(
                rx.text(d, font_weight="700", font_size="0.75em", color="#a0aec0"),
                width="36px"
            ) for d in ["L", "M", "X", "J", "V", "S", "D"]],
            spacing="1",
            width="100%",
            justify="center",
            margin_bottom="10px"
        ),

        # Days Grid
        rx.vstack(
            rx.foreach(
                SeguimientoState.month_days_with_events,
                lambda week: rx.hstack(
                    rx.foreach(week, calendar_cell),
                    spacing="1",
                    justify="center"
                )
            ),
            spacing="1",
            width="100%"
        ),

        # Container Styling
        bg="black",
        backdrop_filter="blur(10px)",
        padding="25px",
        border_radius="24px",
        box_shadow="0 20px 40px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.1)",
        align="center",
        width="100%",
        max_width="340px",
        border="1px solid rgba(255,255,255,0.1)"
    )


# ============================================================================
# COMPONENTE TICKETS
# ============================================================================

def ticket_row(ticket: dict) -> rx.Component:
    """Fila que muestra un ticket."""
    estado_colors = {
        "abierto": "blue",
        "en_espera": "yellow",
        "resuelto": "green",
        "cerrado": "gray",
    }

    prioridad_colors = {
        "baja": "gray",
        "media": "blue",
        "alta": "orange",
        "urgente": "red",
    }

    return rx.box(
        rx.hstack(
            rx.text(
                ticket["titulo"],
                font_weight="medium",
                color=COLORS["foreground"],
                font_size="1.5em",
                flex="1",
                overflow="hidden",
                text_overflow="ellipsis",
                white_space="nowrap",
            ),
            rx.badge(
                ticket["estado"],
                color_scheme=estado_colors.get(ticket["estado"], "gray"),
                variant="soft",
                size="3",
            ),
            rx.badge(
                ticket["prioridad"],
                color_scheme=prioridad_colors.get(ticket["prioridad"], "gray"),
                variant="outline",
                size="3",
            ),
            spacing="3",
            align="center",
            width="100%",
        ),
        width="100%",
        padding="0.6em 1em",
        background_color=COLORS["card"],
        border=f"1px solid {COLORS['border']}",
        border_radius="0.4em",
        _hover={
            "background_color": f"{COLORS['primary']}15",
            "border_color": COLORS["primary"],
        },
        cursor="pointer",
    )


def tickets_viewer_component() -> rx.Component:
    """Panel visor de tickets."""
    return rx.vstack(
        # Header
        rx.hstack(
            rx.icon("ticket", size=24, color=COLORS["primary"]),
            rx.heading(
                "Tickets de Soporte",
                size="7",
                color=COLORS["primary"],
            ),
            spacing="3",
            align="center",
            width="100%",
            margin_bottom="0.5em",
        ),

        # Lista de tickets
        rx.box(
            rx.cond(
                SeguimientoState.is_loading_tickets,
                rx.center(
                    rx.spinner(size="3", color=COLORS["primary"]),
                    height="100%",
                ),
                rx.cond(
                    SeguimientoState.tickets_list.length() > 0,
                    rx.vstack(
                        rx.foreach(
                            SeguimientoState.tickets_list,
                            ticket_row,
                        ),
                        width="100%",
                        spacing="2",
                    ),
                    rx.center(
                        rx.text(
                            "No hay tickets para este proyecto",
                            color=COLORS["muted_foreground"],
                            font_size="0.9em",
                        ),
                        height="100%",
                    ),
                ),
            ),
            width="100%",
            flex="1",
            overflow_y="auto",
            padding="1em",
            background_color=f"{COLORS['card']}80",
            border=f"1px solid {COLORS['border']}",
            border_radius="0.5em",
        ),

        # Error
        rx.cond(
            SeguimientoState.tickets_error != "",
            rx.text(
                SeguimientoState.tickets_error,
                color="red",
                font_size="0.85em",
            ),
        ),

        width="100%",
        flex="1",
        spacing="2",
    )


# ============================================================================
# PANEL PRINCIPAL SEGUIMIENTO
# ============================================================================

def selector_proyecto_component() -> rx.Component:
    """Selector de proyecto compacto."""
    return rx.vstack(
        rx.hstack(
            rx.icon("folder-kanban", size=24, color=COLORS["primary"]),
            rx.heading("Seguimiento del Proyecto", size="7", color=COLORS["primary"]),
            spacing="3",
            align="center",
        ),
        rx.hstack(
            rx.text("Proyecto:", font_weight="bold", color=COLORS["primary"], font_size="1.5em"),
            rx.select(
                SeguimientoState.seguimiento_projects_select,
                placeholder="Seleccionar proyecto...",
                value=SeguimientoState.seguimiento_project_name,
                on_change=SeguimientoState.set_seguimiento_project,
                width="300px",
                size="3",
            ),
            spacing="3",
            align="center",
            width="100%",
            justify="center",
        ),
        width="100%",
        spacing="2",
        padding="1em",
        background_color=COLORS["card"],
        border=f"1px solid {COLORS['border']}",
        border_radius="0.5em",
    )


def seguimiento_panel() -> rx.Component:
    """Panel principal de seguimiento con tres zonas."""

    return rx.vstack(
        # ===== CONTENIDO: TRES ZONAS (siempre visible) =====
        rx.hstack(
            # IZQUIERDA: Notificaciones (chat móvil)
            rx.box(
                notificaciones_component(),
                flex="1",
                padding="1em",
                background_color=COLORS["background"],
                border=f"1px solid {COLORS['border']}",
                border_radius="0.5em",
                display="flex",
                justify_content="center",
                align_items="flex-start",
            ),

            # DERECHA: Calendario + Selector + Tickets
            rx.vstack(
                # Calendario (arriba)
                rx.center(
                    calendario_component(),
                    width="100%",
                    padding="1em",
                    background_color=COLORS["background"],
                    border=f"1px solid {COLORS['border']}",
                    border_radius="0.5em",
                ),

                # Selector de Proyecto (medio)
                selector_proyecto_component(),

                # Tickets (abajo)
                rx.box(
                    tickets_viewer_component(),
                    width="100%",
                    flex="1",
                    padding="1em",
                    background_color=COLORS["card"],
                    border=f"1px solid {COLORS['border']}",
                    border_radius="0.5em",
                ),

                flex="1",
                spacing="3",
                width="100%",
            ),

            spacing="3",
            width="100%",
            align_items="stretch",
            height="calc(100vh - 120px)",
        ),

        width="100%",
        spacing="1",
        on_mount=SeguimientoState.on_mount_seguimiento,
    )
