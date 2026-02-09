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
import importlib.util
from pathlib import Path
from sqlalchemy import create_engine, text


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


def _load_conversaciones_adapter():
    """Carga el adapter de conversaciones usando importlib."""
    adapter_path = (
        Path(__file__).resolve().parents[3]
        / "2_shared_application/adapters/conversaciones_adapter.py"
    )
    spec = importlib.util.spec_from_file_location("conversaciones_adapter", adapter_path)
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar el adaptador de conversaciones")

    adapter_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter_module)
    return adapter_module


def _load_cambios_adapter():
    """Carga el adapter de cambios usando importlib."""
    adapter_path = (
        Path(__file__).resolve().parents[3]
        / "2_shared_application/adapters/cambios_adapter.py"
    )
    spec = importlib.util.spec_from_file_location("cambios_adapter", adapter_path)
    if spec is None or spec.loader is None:
        raise ImportError("No se pudo cargar el adaptador de cambios")

    adapter_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter_module)
    return adapter_module


# ============================================================================
# CALENDARIO (desde template)
# ============================================================================

class DayInfo(pydantic.BaseModel):
    day: int
    border_color: str = "transparent"
    has_event: bool = False
    is_today: bool = False
    events: list[dict] = []
    event_color: str = "transparent"
    tooltip_text: str = ""
    is_mixed: bool = False


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
    messages: list[Message] = []
    new_message: str = ""
    current_identity: str = "cliente"  # Fijo en frontend
    id_conversacion_actual: int = 0
    conversaciones_error: str = ""

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

    # Modal de eventos del calendario
    modal_eventos_abierto: bool = False
    modal_eventos_fecha: str = ""
    modal_eventos_contenido: str = ""

    # === TICKETS ===
    tickets_list: list[dict] = []
    is_loading_tickets: bool = False
    tickets_error: str = ""

    async def _get_db_engine(self):
        """Crea el engine de la base de datos para myllm_projects_db."""
        try:
            # Crear engine para myllm_projects_db
            DB_USER = "myllm_admin"
            DB_PASS = "Us3r%40dminP%40ss"  # URL-encoded
            DB_HOST = "localhost"
            engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/myllm_projects_db")
            return engine
        except Exception as e:
            print(f"Error creando engine: {e}")
            return None

    def set_new_message(self, value: str):
        """Setter explícito para new_message."""
        self.new_message = value

    # === MÉTODOS NOTIFICACIONES ===

    async def load_or_create_conversacion(self):
        """Carga o crea la conversación del usuario actual con su organización."""
        engine = await self._get_db_engine()
        if not engine:
            self.conversaciones_error = "Error de conexión a base de datos"
            return

        try:
            from web_frontend.web_frontend import State as MainState
            conversaciones_adapter = _load_conversaciones_adapter()

            main_state = await self.get_state(MainState)
            user_id = main_state.user_id
            org_id = main_state.organization_id

            # Buscar conversación existente del usuario
            with engine.connect() as conn:
                query = text("""
                    SELECT id_conversacion
                    FROM myllm_projects_db.conversaciones
                    WHERE id_organizacion = :org_id
                      AND id_usuario_cliente = :user_id
                      AND estado IN ('abierta', 'en_curso')
                    ORDER BY fecha_ultima_actualizacion DESC
                    LIMIT 1
                """)
                result = conn.execute(query, {"org_id": org_id, "user_id": user_id}).fetchone()

                if result:
                    self.id_conversacion_actual = result[0]
                else:
                    # Crear nueva conversación
                    self.id_conversacion_actual = conversaciones_adapter.crear_conversacion(
                        engine=engine,
                        id_organizacion=org_id,
                        id_usuario_cliente=user_id,
                        asunto="Consulta sobre proyecto",
                        prioridad="media"
                    )

            # Cargar mensajes
            await self.load_messages()

        except Exception as e:
            print(f"Error al cargar/crear conversación: {e}")
            self.conversaciones_error = f"Error: {str(e)}"

    async def load_messages(self):
        """Carga los mensajes de la conversación actual desde la BD."""
        engine = await self._get_db_engine()
        if not engine or self.id_conversacion_actual == 0:
            return

        try:
            conversaciones_adapter = _load_conversaciones_adapter()

            mensajes = conversaciones_adapter.obtener_mensajes_conversacion(
                engine=engine,
                id_conversacion=self.id_conversacion_actual
            )

            self.messages = []
            for msg in mensajes:
                self.messages.append(Message(
                    text=msg["texto_mensaje"],
                    sender=msg["tipo_emisor"],
                    time=msg["fecha_envio"].strftime("%d de %B de %Y a las %H:%M") if msg["fecha_envio"] else ""
                ))

            # Marcar como leídos por cliente
            conversaciones_adapter.marcar_mensajes_como_leidos(
                engine=engine,
                id_conversacion=self.id_conversacion_actual,
                tipo_lector="cliente"
            )

        except Exception as e:
            print(f"Error al cargar mensajes: {e}")
            self.conversaciones_error = f"Error: {str(e)}"

    async def send_message(self):
        """Envía el mensaje a la base de datos."""
        if not self.new_message or self.id_conversacion_actual == 0:
            return

        engine = await self._get_db_engine()
        if not engine:
            return

        try:
            from web_frontend.web_frontend import State as MainState
            conversaciones_adapter = _load_conversaciones_adapter()

            main_state = await self.get_state(MainState)
            user_id = main_state.user_id

            # Guardar en BD
            conversaciones_adapter.enviar_mensaje(
                engine=engine,
                id_conversacion=self.id_conversacion_actual,
                id_usuario_emisor=user_id,
                tipo_emisor="cliente",
                texto_mensaje=self.new_message
            )

            # Recargar mensajes
            self.new_message = ""
            await self.load_messages()

        except Exception as e:
            print(f"Error al enviar mensaje: {e}")
            self.conversaciones_error = f"Error: {str(e)}"

    async def handle_keypress(self, key: str):
        if key == "Enter":
            await self.send_message()

    # === MÉTODOS CALENDARIO ===

    async def load_events_data(self):
        """Carga eventos del calendario desde la tabla cambios."""
        print("[DEBUG CALENDARIO FRONTEND] load_events_data INICIADO")

        # Obtener organización del usuario desde MainState
        try:
            from web_frontend.web_frontend import State as MainState
            main_state = await self.get_state(MainState)
            org_id = main_state.organization_id

            if org_id == 0:
                print("[DEBUG CALENDARIO FRONTEND] No hay organización en sesión")
                self.events_data = []
                return
        except Exception as e:
            print(f"[DEBUG CALENDARIO FRONTEND] Error obteniendo org_id: {e}")
            self.events_data = []
            return

        engine = await self._get_db_engine()
        if not engine:
            print("[DEBUG CALENDARIO FRONTEND] No se pudo obtener engine")
            self.events_data = []
            return

        try:
            cambios_adapter = _load_cambios_adapter()

            # Obtener mes y año seleccionados
            mes = self._month_map.get(self.selected_month, datetime.datetime.now().month)
            anio = int(self.selected_year)

            # Determinar id_proyecto (None si no hay proyecto seleccionado)
            id_proyecto = self.seguimiento_project_id if self.seguimiento_project_id > 0 else None

            print(f"[DEBUG CALENDARIO FRONTEND] Consultando eventos para:")
            print(f"[DEBUG CALENDARIO FRONTEND]   org_id={org_id}")
            print(f"[DEBUG CALENDARIO FRONTEND]   mes={mes} ({self.selected_month})")
            print(f"[DEBUG CALENDARIO FRONTEND]   año={anio}")
            print(f"[DEBUG CALENDARIO FRONTEND]   proyecto_id={id_proyecto}")

            # Obtener eventos agrupados por día
            eventos = cambios_adapter.obtener_cambios_agrupados_por_dia(
                engine=engine,
                id_organizacion=org_id,
                mes=mes,
                anio=anio,
                id_proyecto=id_proyecto
            )

            self.events_data = eventos
            print(f"[DEBUG CALENDARIO FRONTEND] Eventos cargados: {len(eventos)} días con eventos")
            for evento in eventos[:3]:  # Mostrar primeros 3
                print(f"[DEBUG CALENDARIO FRONTEND]   - {evento['date']}: {evento['count']} evento(s), color={evento['color']}")

        except Exception as e:
            print(f"[ERROR CALENDARIO FRONTEND] Error al cargar eventos: {e}")
            import traceback
            traceback.print_exc()
            self.events_data = []

    @rx.var
    def month_days_with_events(self) -> list[list[DayInfo]]:
        """Returns a matrix of DayInfo objects for the selected month with events."""
        try:
            y = int(self.selected_year)
            m = self._month_map.get(self.selected_month, 1)

            print(f"[DEBUG CALENDARIO FRONTEND] month_days_with_events calculando para {self.selected_month}/{y}")
            print(f"[DEBUG CALENDARIO FRONTEND] events_data tiene {len(self.events_data)} días con eventos")

            now = datetime.datetime.now()
            today_day = now.day
            today_month = now.month
            today_year = now.year

            cal = calendar.Calendar(firstweekday=0)
            raw_weeks = cal.monthdayscalendar(y, m)

            # Crear diccionario de eventos por día
            events_by_day = {}
            for event in self.events_data:
                # event['date'] es una cadena en formato ISO (YYYY-MM-DD)
                event_date = datetime.datetime.fromisoformat(event['date'])
                if event_date.year == y and event_date.month == m:
                    day_num = event_date.day
                    events_by_day[day_num] = event
                    print(f"[DEBUG CALENDARIO FRONTEND] Evento agregado para día {day_num}: color={event['color']}")

            print(f"[DEBUG CALENDARIO FRONTEND] events_by_day tiene {len(events_by_day)} días")

            processed_weeks = []
            for week in raw_weeks:
                processed_week = []
                for day in week:
                    if day == 0:
                        processed_week.append(DayInfo(day=0))
                        continue

                    is_today = (day == today_day and m == today_month and y == today_year)

                    # Verificar si hay eventos para este día
                    event_info = events_by_day.get(day)
                    if event_info:
                        processed_week.append(DayInfo(
                            day=day,
                            border_color="transparent",
                            has_event=True,
                            is_today=is_today,
                            events=[],
                            event_color=event_info.get('color', 'transparent'),
                            tooltip_text=event_info.get('tooltip', ''),
                            is_mixed=event_info.get('has_mixed', False)
                        ))
                    else:
                        processed_week.append(DayInfo(
                            day=day,
                            border_color="transparent",
                            has_event=False,
                            is_today=is_today,
                            events=[],
                            event_color="transparent",
                            tooltip_text="",
                            is_mixed=False
                        ))
                processed_weeks.append(processed_week)

            return processed_weeks

        except Exception as e:
            print(f"Error calculando días: {e}")
            import traceback
            traceback.print_exc()
            return []

    def set_year(self, year: str):
        self.selected_year = year
        self.current_year = int(year)
        return SeguimientoState.load_events_data

    def set_month(self, month: str):
        self.selected_month = month
        self.current_month = self._month_map.get(month, 1)
        return SeguimientoState.load_events_data

    def abrir_modal_eventos(self, dia: int):
        """Abre el modal con los eventos del día seleccionado."""
        if dia == 0:
            return

        # Buscar evento en events_data para este día
        y = int(self.selected_year)
        m = self._month_map.get(self.selected_month, 1)

        contenido = ""
        evento_encontrado = False
        for event in self.events_data:
            event_date = datetime.datetime.fromisoformat(event['date'])
            if event_date.year == y and event_date.month == m and event_date.day == dia:
                contenido = event.get('tooltip', 'Sin información disponible')
                evento_encontrado = True
                break

        # Solo abrir modal si hay eventos
        if not evento_encontrado:
            return

        # Construir fecha formateada
        self.modal_eventos_fecha = f"{dia} de {self.selected_month} de {self.selected_year}"
        self.modal_eventos_contenido = contenido
        self.modal_eventos_abierto = True

    def cerrar_modal_eventos(self):
        """Cierra el modal de eventos."""
        self.modal_eventos_abierto = False
        self.modal_eventos_fecha = ""
        self.modal_eventos_contenido = ""

    # === MÉTODOS TICKETS ===

    async def set_seguimiento_project(self, project_name: str):
        """Cambia el proyecto seleccionado y carga tickets y eventos del calendario."""
        self.seguimiento_project_name = project_name
        engine = await self._get_db_engine()
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
                    await self.load_tickets()
                    # Recargar eventos del calendario con el proyecto seleccionado
                    await self.load_events_data()
                else:
                    self.seguimiento_project_id = 0
                    self.tickets_list = []
                    # Recargar eventos (sin filtro de proyecto)
                    await self.load_events_data()

        except Exception as e:
            print(f"Error al obtener project_id: {e}")
            self.tickets_error = f"Error: {str(e)}"

    async def load_tickets(self):
        """Carga los tickets del proyecto seleccionado."""
        self.is_loading_tickets = True
        self.tickets_error = ""
        engine = await self._get_db_engine()
        if not engine:
            self.tickets_error = "Error de conexión a base de datos"
            self.is_loading_tickets = False
            return

        try:
            from web_frontend.web_frontend import State as MainState
            main_state = await self.get_state(MainState)
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
        engine = await self._get_db_engine()
        if not engine:
            return

        try:
            from web_frontend.web_frontend import State as MainState
            main_state = await self.get_state(MainState)
            org_id = main_state.organization_id

            # Cargar proyectos
            with engine.connect() as conn:
                query = text("""
                    SELECT nombre FROM myllm_projects_db.proyectos
                    WHERE id_organizacion = :org_id
                    ORDER BY nombre
                """)
                results = conn.execute(query, {"org_id": org_id})
                self.seguimiento_projects_select = [row[0] for row in results]

            # Cargar conversación y mensajes
            await self.load_or_create_conversacion()

            # Cargar eventos del calendario
            await self.load_events_data()

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
            # Indicador de identidad (solo cliente en frontend)
            rx.hstack(
                rx.box(
                    rx.vstack(
                        rx.icon(tag="user", size=26, color="#222"),
                        rx.text("Cliente", size="3", color="#666"),
                        spacing="1",
                        align="center",
                    ),
                    padding="10px",
                    bg="#f3c7d6",
                    border_radius="14px",
                ),
                spacing="6",
                margin_bottom="10px",
                justify="center",
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
    """Render a single day cell with event colors."""
    # Determinar color de fondo según prioridad: evento > today > default
    bg_color = rx.cond(
        day_info.has_event,
        day_info.event_color,  # Color del evento si hay evento
        rx.cond(
            day_info.is_today,
            "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",  # Morado si es hoy
            "transparent"  # Transparente por defecto
        )
    )

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
        bg=bg_color,
        box_shadow=rx.cond(
            day_info.has_event | day_info.is_today,
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
        cursor=rx.cond(day_info.has_event, "pointer", "default"),
        title=day_info.tooltip_text,  # Tooltip con info del evento
        on_click=SeguimientoState.abrir_modal_eventos(day_info.day)
    )

    return rx.center(
        cell_visual,
        width="36px",
        height="36px",
    )


def modal_eventos_calendario() -> rx.Component:
    """Modal para mostrar eventos del día seleccionado."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Header del modal
                rx.hstack(
                    rx.heading(
                        "Eventos del día",
                        size="6",
                        color=COLORS["primary"],
                    ),
                    rx.dialog.close(
                        rx.icon("x", size=24, cursor="pointer"),
                    ),
                    justify="between",
                    width="100%",
                    margin_bottom="1em",
                ),

                # Fecha
                rx.text(
                    SeguimientoState.modal_eventos_fecha,
                    font_weight="bold",
                    font_size="1.2em",
                    color=COLORS["foreground"],
                    margin_bottom="1em",
                ),

                # Contenido de los eventos
                rx.box(
                    rx.text(
                        SeguimientoState.modal_eventos_contenido,
                        color=COLORS["muted_foreground"],
                        font_size="1.1em",
                        line_height="1.6",
                        white_space="pre-wrap",  # Preservar saltos de línea
                    ),
                    width="100%",
                    padding="1em",
                    background_color=f"{COLORS['card']}80",
                    border=f"1px solid {COLORS['border']}",
                    border_radius="0.5em",
                    max_height="400px",
                    overflow_y="auto",
                ),

                # Botón cerrar
                rx.dialog.close(
                    rx.button(
                        "Cerrar",
                        size="3",
                        background_color=COLORS["primary"],
                        color=COLORS["background"],
                        cursor="pointer",
                        width="100%",
                        margin_top="1em",
                    ),
                ),

                spacing="3",
                width="100%",
            ),
            max_width="600px",
            background_color=COLORS["card"],
            border=f"1px solid {COLORS['border']}",
            padding="2em",
        ),
        open=SeguimientoState.modal_eventos_abierto,
        on_open_change=SeguimientoState.cerrar_modal_eventos,
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
    # Colores oscuros personalizados para estados
    estado_styles = {
        "abierto": {"background": "#1e40af", "color": "#ffffff"},  # Azul oscuro
        "en_espera": {"background": "#d97706", "color": "#ffffff"},  # Ámbar oscuro
        "resuelto": {"background": "#15803d", "color": "#ffffff"},  # Verde oscuro
        "cerrado": {"background": "#52525b", "color": "#ffffff"},  # Gris oscuro
    }

    # Colores oscuros personalizados para prioridades
    prioridad_styles = {
        "baja": {"background": "#52525b", "color": "#ffffff"},  # Gris oscuro
        "media": {"background": "#0891b2", "color": "#ffffff"},  # Cyan oscuro
        "alta": {"background": "#ea580c", "color": "#ffffff"},  # Naranja oscuro
        "urgente": {"background": "#dc2626", "color": "#ffffff"},  # Rojo oscuro
    }

    # Obtener estilos según estado y prioridad
    estado_style = estado_styles.get(ticket["estado"], {"background": "#52525b", "color": "#ffffff"})
    prioridad_style = prioridad_styles.get(ticket["prioridad"], {"background": "#52525b", "color": "#ffffff"})

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
            # Badge de estado con colores oscuros personalizados
            rx.box(
                rx.text(
                    ticket["estado"],
                    color=estado_style["color"],
                    font_weight="600",
                    font_size="14px",
                ),
                background_color=estado_style["background"],
                padding="6px 12px",
                border_radius="6px",
                display="inline-block",
            ),
            # Badge de prioridad con colores oscuros personalizados
            rx.box(
                rx.text(
                    ticket["prioridad"],
                    color=prioridad_style["color"],
                    font_weight="600",
                    font_size="14px",
                ),
                background_color=prioridad_style["background"],
                padding="6px 12px",
                border_radius="6px",
                display="inline-block",
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

            # DERECHA: Selector + Calendario + Tickets
            rx.vstack(
                # Selector de Proyecto (arriba)
                selector_proyecto_component(),

                # Calendario (medio)
                rx.center(
                    calendario_component(),
                    width="100%",
                    padding="1em",
                    background_color=COLORS["background"],
                    border=f"1px solid {COLORS['border']}",
                    border_radius="0.5em",
                ),

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

        # Modal de eventos del calendario
        modal_eventos_calendario(),

        width="100%",
        spacing="1",
        on_mount=SeguimientoState.on_mount_seguimiento,
    )
