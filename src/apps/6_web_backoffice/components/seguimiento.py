"""
Componente Seguimiento para Web Backoffice (Interno)

Integra:
1. Notificaciones (template completo)
2. Calendario (template completo)
3. Visor de Tickets (custom - vista interna)
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
    "primary": "#FF8C00",  # Naranja del tema backoffice
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
    messages: list[Message] = []
    new_message: str = ""
    current_identity: str = "interno"  # Fijo en backoffice
    conversaciones_list: list[dict] = []
    id_conversacion_actual: int = 0
    conversaciones_error: str = ""

    # Filtros y búsqueda
    filtro_estado: str = "todas"  # todas, abierta, en_curso, resuelta
    filtro_prioridad: str = "todas"  # todas, baja, media, alta, urgente
    busqueda_texto: str = ""

    # Información del cliente actual
    cliente_info: dict = {}
    conversacion_actual_info: dict = {}

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

    async def load_conversaciones_organizacion(self):
        """Carga las conversaciones de la organización."""
        engine = await self._get_db_engine()
        if not engine:
            self.conversaciones_error = "Error de conexión a base de datos"
            print("[DEBUG] No se pudo obtener el engine de BD")
            return

        try:
            from web_backoffice.web_backoffice import State as MainState
            conversaciones_adapter = _load_conversaciones_adapter()

            main_state = await self.get_state(MainState)
            org_id = main_state.organization_id
            print(f"[DEBUG] Cargando conversaciones para organization_id={org_id}")

            # Obtener conversaciones de la organización
            conversaciones = conversaciones_adapter.obtener_conversaciones_organizacion(
                engine=engine,
                id_organizacion=org_id,
                solo_activas=True
            )
            print(f"[DEBUG] Conversaciones encontradas: {len(conversaciones)}")
            for conv in conversaciones:
                print(f"[DEBUG]   - Conversación {conv['id_conversacion']}: {conv.get('asunto', 'Sin asunto')} (estado: {conv.get('estado', 'N/A')})")

            self.conversaciones_list = conversaciones

            # Si hay conversaciones, seleccionar la primera
            if conversaciones:
                self.id_conversacion_actual = conversaciones[0]["id_conversacion"]
                print(f"[DEBUG] Conversación seleccionada: {self.id_conversacion_actual}")
                await self.load_messages()
                await self.unirse_a_conversacion()
            else:
                print("[DEBUG] No hay conversaciones para mostrar")

        except Exception as e:
            print(f"[ERROR] Error al cargar conversaciones: {e}")
            import traceback
            traceback.print_exc()
            self.conversaciones_error = f"Error: {str(e)}"

    async def unirse_a_conversacion(self):
        """El usuario interno se une a la conversación actual."""
        if self.id_conversacion_actual == 0:
            return

        engine = await self._get_db_engine()
        if not engine:
            return

        try:
            from web_backoffice.web_backoffice import State as MainState
            conversaciones_adapter = _load_conversaciones_adapter()

            main_state = await self.get_state(MainState)
            user_id = main_state.user_id

            # Unirse a la conversación
            conversaciones_adapter.unirse_a_conversacion(
                engine=engine,
                id_conversacion=self.id_conversacion_actual,
                id_usuario_interno=user_id
            )

        except Exception as e:
            print(f"Error al unirse a conversación: {e}")

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

            # Marcar como leídos por interno
            conversaciones_adapter.marcar_mensajes_como_leidos(
                engine=engine,
                id_conversacion=self.id_conversacion_actual,
                tipo_lector="interno"
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
            from web_backoffice.web_backoffice import State as MainState
            conversaciones_adapter = _load_conversaciones_adapter()

            main_state = await self.get_state(MainState)
            user_id = main_state.user_id

            # Guardar en BD
            conversaciones_adapter.enviar_mensaje(
                engine=engine,
                id_conversacion=self.id_conversacion_actual,
                id_usuario_emisor=user_id,
                tipo_emisor="interno",
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

    # === MÉTODOS ESPECIALES BACKOFFICE ===

    async def seleccionar_conversacion(self, id_conversacion: int):
        """Selecciona una conversación de la lista y carga sus mensajes."""
        self.id_conversacion_actual = id_conversacion
        await self.load_messages()
        await self.cargar_info_conversacion()
        await self.unirse_a_conversacion()

    async def cargar_info_conversacion(self):
        """Carga información detallada de la conversación y el cliente."""
        if self.id_conversacion_actual == 0:
            return

        engine = await self._get_db_engine()
        if not engine:
            return

        try:
            with engine.connect() as conn:
                # Obtener info de la conversación
                query = text("""
                    SELECT c.id_conversacion, c.asunto, c.estado, c.prioridad,
                           c.id_usuario_cliente, c.fecha_creacion,
                           c.mensajes_sin_leer_interno, c.total_mensajes
                    FROM conversaciones c
                    WHERE c.id_conversacion = :id_conv
                """)
                result = conn.execute(query, {"id_conv": self.id_conversacion_actual}).fetchone()

                if result:
                    self.conversacion_actual_info = {
                        "id_conversacion": result[0],
                        "asunto": result[1],
                        "estado": result[2],
                        "prioridad": result[3],
                        "id_usuario_cliente": result[4],
                        "fecha_creacion": result[5],
                        "mensajes_sin_leer": result[6],
                        "total_mensajes": result[7]
                    }

                    # Obtener info del cliente (desde moks porque está en otra BD)
                    # Por ahora guardamos solo el ID
                    self.cliente_info = {
                        "id_usuario": result[4],
                        "nombre": f"Usuario {result[4]}"  # Placeholder
                    }

        except Exception as e:
            print(f"Error al cargar info de conversación: {e}")

    async def cambiar_prioridad(self, nueva_prioridad: str):
        """Cambia la prioridad de la conversación actual."""
        if self.id_conversacion_actual == 0:
            return

        engine = await self._get_db_engine()
        if not engine:
            return

        try:
            with engine.connect() as conn:
                query = text("""
                    UPDATE conversaciones
                    SET prioridad = :prioridad
                    WHERE id_conversacion = :id_conv
                """)
                conn.execute(query, {
                    "prioridad": nueva_prioridad,
                    "id_conv": self.id_conversacion_actual
                })
                conn.commit()

            # Recargar info
            await self.cargar_info_conversacion()
            await self.load_conversaciones_organizacion()

        except Exception as e:
            print(f"Error al cambiar prioridad: {e}")

    async def cambiar_estado_conversacion(self, nuevo_estado: str):
        """Cambia el estado de la conversación actual."""
        if self.id_conversacion_actual == 0:
            return

        engine = await self._get_db_engine()
        if not engine:
            return

        try:
            conversaciones_adapter = _load_conversaciones_adapter()

            if nuevo_estado == "cerrada":
                from web_backoffice.web_backoffice import State as MainState
                main_state = await self.get_state(MainState)
                user_id = main_state.user_id

                conversaciones_adapter.cerrar_conversacion(
                    engine=engine,
                    id_conversacion=self.id_conversacion_actual,
                    id_usuario_cierre=user_id
                )
            else:
                # Cambio de estado simple
                with engine.connect() as conn:
                    query = text("""
                        UPDATE conversaciones
                        SET estado = :estado
                        WHERE id_conversacion = :id_conv
                    """)
                    conn.execute(query, {
                        "estado": nuevo_estado,
                        "id_conv": self.id_conversacion_actual
                    })
                    conn.commit()

            # Recargar conversaciones
            await self.load_conversaciones_organizacion()

        except Exception as e:
            print(f"Error al cambiar estado: {e}")

    def set_filtro_estado(self, estado: str):
        """Cambia el filtro de estado."""
        self.filtro_estado = estado

    def set_filtro_prioridad(self, prioridad: str):
        """Cambia el filtro de prioridad."""
        self.filtro_prioridad = prioridad

    def set_busqueda_texto(self, texto: str):
        """Actualiza el texto de búsqueda."""
        self.busqueda_texto = texto

    @rx.var
    def conversaciones_filtradas(self) -> list[dict]:
        """Retorna las conversaciones filtradas según los criterios actuales."""
        resultado = self.conversaciones_list

        # Filtrar por estado
        if self.filtro_estado != "todas":
            resultado = [c for c in resultado if c.get("estado") == self.filtro_estado]

        # Filtrar por prioridad
        if self.filtro_prioridad != "todas":
            resultado = [c for c in resultado if c.get("prioridad") == self.filtro_prioridad]

        # Filtrar por texto de búsqueda
        if self.busqueda_texto:
            texto_lower = self.busqueda_texto.lower()
            resultado = [
                c for c in resultado
                if (texto_lower in c.get("asunto", "").lower() or
                    texto_lower in c.get("ultimo_mensaje_texto", "").lower())
            ]

        return resultado

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

    async def set_seguimiento_project(self, project_name: str):
        """Cambia el proyecto seleccionado y carga los tickets."""
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
                else:
                    self.seguimiento_project_id = 0
                    self.tickets_list = []

        except Exception as e:
            print(f"Error al obtener project_id: {e}")
            self.tickets_error = f"Error: {str(e)}"

    async def load_tickets(self):
        """Carga los tickets del proyecto seleccionado (VISTA INTERNA - todos los usuarios)."""
        self.is_loading_tickets = True
        self.tickets_error = ""
        engine = await self._get_db_engine()
        if not engine:
            self.tickets_error = "Error de conexión a base de datos"
            self.is_loading_tickets = False
            return

        try:
            from web_backoffice.web_backoffice import State as MainState
            main_state = await self.get_state(MainState)
            org_id = main_state.organization_id

            with engine.connect() as conn:
                # DIFERENCIA: En backoffice se ven TODOS los tickets de la organización
                query = text("""
                    SELECT id, titulo, estado, prioridad, fecha_creacion, fecha_actualizacion, cliente_id
                    FROM myllm_projects_db.tickets
                    WHERE id_organizacion = :org_id
                      AND (id_proyecto = :project_id OR id_proyecto IS NULL)
                    ORDER BY fecha_actualizacion DESC, fecha_creacion DESC
                    LIMIT 50
                """)

                results = conn.execute(query, {
                    "org_id": org_id,
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
                        "cliente_id": row[6],
                    })

        except Exception as e:
            print(f"Error al cargar tickets: {e}")
            self.tickets_error = f"Error: {str(e)}"
        finally:
            self.is_loading_tickets = False

    @rx.event
    async def on_mount_seguimiento(self):
        """Se ejecuta cuando se monta el componente."""
        print("[DEBUG BACKOFFICE] on_mount_seguimiento INICIADO")
        engine = await self._get_db_engine()
        if not engine:
            print("[DEBUG BACKOFFICE] ERROR: No se pudo obtener el engine")
            return

        print("[DEBUG BACKOFFICE] Engine obtenido correctamente")
        try:
            from web_backoffice.web_backoffice import State as MainState
            main_state = await self.get_state(MainState)
            org_id = main_state.organization_id
            print(f"[DEBUG BACKOFFICE] Organization ID: {org_id}")

            # Cargar proyectos
            with engine.connect() as conn:
                query = text("""
                    SELECT nombre FROM myllm_projects_db.proyectos
                    WHERE id_organizacion = :org_id
                    ORDER BY nombre
                """)
                results = conn.execute(query, {"org_id": org_id})
                self.seguimiento_projects_select = [row[0] for row in results]
            print(f"[DEBUG BACKOFFICE] Proyectos cargados: {len(self.seguimiento_projects_select)}")

            # Cargar conversaciones
            print("[DEBUG BACKOFFICE] Llamando a load_conversaciones_organizacion...")
            await self.load_conversaciones_organizacion()
            print("[DEBUG BACKOFFICE] load_conversaciones_organizacion completado")

        except Exception as e:
            print(f"[ERROR BACKOFFICE] Error al cargar proyectos: {e}")
            import traceback
            traceback.print_exc()


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


def conversacion_item(conv: dict) -> rx.Component:
    """Item de conversación en la lista lateral."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(
                    conv.get("asunto", "Sin asunto"),
                    font_weight="700",
                    font_size="1.3em",
                    color=rx.cond(
                        SeguimientoState.id_conversacion_actual == conv.get("id_conversacion"),
                        COLORS["primary"],
                        "#fff"
                    ),
                    no_of_lines=1,
                    flex="1",
                ),
                rx.badge(
                    conv.get("mensajes_sin_leer_interno", 0),
                    color_scheme="red",
                    size="2",
                    display=rx.cond(
                        conv.get("mensajes_sin_leer_interno", 0),
                        "block",
                        "none"
                    ),
                ),
                justify="between",
                width="100%",
                align="center",
            ),
            rx.hstack(
                rx.match(
                    conv.get("prioridad", "media"),
                    ("urgente", rx.box(width="10px", height="10px", bg="#FF4444", border_radius="50%")),
                    ("alta", rx.box(width="10px", height="10px", bg="#FF8800", border_radius="50%")),
                    ("media", rx.box(width="10px", height="10px", bg="#4CAF50", border_radius="50%")),
                    ("baja", rx.box(width="10px", height="10px", bg="#999999", border_radius="50%")),
                    rx.box(width="10px", height="10px", bg="#999999", border_radius="50%"),
                ),
                rx.text(
                    f"Usuario {conv.get('id_usuario_cliente', 'N/A')}",
                    font_size="1.1em",
                    color="#bbb",
                    font_weight="500",
                ),
                spacing="2",
            ),
            rx.text(
                conv.get("ultimo_mensaje_texto", "Sin mensajes"),
                font_size="1.05em",
                color="#888",
                no_of_lines=2,
            ),
            spacing="1",
            width="100%",
        ),
        padding="12px",
        bg=rx.cond(
            SeguimientoState.id_conversacion_actual == conv.get("id_conversacion"),
            COLORS["border"],
            "transparent"
        ),
        border_radius="8px",
        cursor="pointer",
        _hover={"bg": COLORS["border"]},
        on_click=lambda conv=conv: SeguimientoState.seleccionar_conversacion(conv.get("id_conversacion", 0)),
        width="100%",
    )


def panel_filtros() -> rx.Component:
    """Panel de filtros y búsqueda."""
    return rx.vstack(
        rx.text("Filtros", font_weight="bold", color=COLORS["primary"], font_size="1.8em"),
        # Filtro por estado
        rx.hstack(
            rx.text("Estado:", font_size="1.3em", color=COLORS["muted_foreground"], font_weight="bold"),
            rx.select(
                ["todas", "abierta", "en_curso", "resuelta"],
                value=SeguimientoState.filtro_estado,
                on_change=SeguimientoState.set_filtro_estado,
                size="2",
            ),
            width="100%",
            justify="between",
            align="center",
        ),
        # Filtro por prioridad
        rx.hstack(
            rx.text("Prioridad:", font_size="1.3em", color=COLORS["muted_foreground"], font_weight="bold"),
            rx.select(
                ["todas", "baja", "media", "alta", "urgente"],
                value=SeguimientoState.filtro_prioridad,
                on_change=SeguimientoState.set_filtro_prioridad,
                size="2",
            ),
            width="100%",
            justify="between",
            align="center",
        ),
        # Búsqueda
        rx.input(
            placeholder="Buscar...",
            value=SeguimientoState.busqueda_texto,
            on_change=SeguimientoState.set_busqueda_texto,
            size="2",
            width="100%",
        ),
        spacing="3",
        padding="12px",
        bg=COLORS["card"],
        border_radius="8px",
        border=f"1px solid {COLORS['border']}",
        width="100%",
    )


def panel_acciones() -> rx.Component:
    """Panel de acciones para la conversación actual."""
    return rx.vstack(
        rx.text("Acciones", font_weight="bold", color=COLORS["primary"], font_size="1.2em"),
        rx.vstack(
            # Cambiar prioridad
            rx.vstack(
                rx.text("Prioridad:", font_size="0.85em", color=COLORS["muted_foreground"]),
                rx.hstack(
                    rx.button(
                        "Baja",
                        size="1",
                        variant="soft",
                        on_click=lambda: SeguimientoState.cambiar_prioridad("baja"),
                    ),
                    rx.button(
                        "Media",
                        size="1",
                        variant="soft",
                        on_click=lambda: SeguimientoState.cambiar_prioridad("media"),
                    ),
                    rx.button(
                        "Alta",
                        size="1",
                        variant="soft",
                        color_scheme="orange",
                        on_click=lambda: SeguimientoState.cambiar_prioridad("alta"),
                    ),
                    rx.button(
                        "Urgente",
                        size="1",
                        variant="soft",
                        color_scheme="red",
                        on_click=lambda: SeguimientoState.cambiar_prioridad("urgente"),
                    ),
                    spacing="2",
                    wrap="wrap",
                ),
                spacing="2",
                width="100%",
            ),
            # Cambiar estado
            rx.vstack(
                rx.text("Estado:", font_size="0.85em", color=COLORS["muted_foreground"]),
                rx.hstack(
                    rx.button(
                        "En Curso",
                        size="1",
                        variant="soft",
                        on_click=lambda: SeguimientoState.cambiar_estado_conversacion("en_curso"),
                    ),
                    rx.button(
                        "Resuelta",
                        size="1",
                        variant="soft",
                        color_scheme="green",
                        on_click=lambda: SeguimientoState.cambiar_estado_conversacion("resuelta"),
                    ),
                    rx.button(
                        "Cerrar",
                        size="1",
                        variant="soft",
                        color_scheme="red",
                        on_click=lambda: SeguimientoState.cambiar_estado_conversacion("cerrada"),
                    ),
                    spacing="2",
                    wrap="wrap",
                ),
                spacing="2",
                width="100%",
            ),
            spacing="4",
            width="100%",
        ),
        spacing="3",
        padding="12px",
        bg=COLORS["card"],
        border_radius="8px",
        border=f"1px solid {COLORS['border']}",
        width="100%",
    )


def lista_conversaciones() -> rx.Component:
    """Panel lateral con lista de conversaciones."""
    return rx.vstack(
        rx.text(
            "Conversaciones",
            font_weight="bold",
            font_size="1.2em",
            color=COLORS["primary"],
        ),
        panel_filtros(),
        rx.vstack(
            rx.foreach(
                SeguimientoState.conversaciones_filtradas,
                conversacion_item
            ),
            spacing="2",
            width="100%",
            overflow_y="auto",
            max_height="calc(100vh - 400px)",
        ),
        spacing="3",
        width="320px",
        min_width="320px",
        height="100%",
        padding="16px",
        bg=COLORS["card"],
        border_right=f"1px solid {COLORS['border']}",
        overflow_y="auto",
    )


def chat_area_compacta() -> rx.Component:
    """Área de chat estilo móvil - integrado como en el frontend."""
    return rx.box(
        rx.vstack(
            # Área de mensajes con scroll
            rx.vstack(
                rx.auto_scroll(
                    rx.vstack(
                        rx.foreach(SeguimientoState.messages, chat_bubble),
                        width="100%",
                        padding_top="2em",
                        padding_bottom="2em",
                        padding_x="1em",
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
                overflow="hidden",
            ),

            # Barra inferior con identidad e input (DENTRO del componente)
            rx.vstack(
                # Indicador de identidad
                rx.hstack(
                    rx.box(
                        rx.vstack(
                            rx.icon(tag="shield-check", size=24, color=COLORS["primary"]),
                            rx.text("Interno", size="2", color=COLORS["primary"], font_weight="bold"),
                            spacing="1",
                            align="center",
                        ),
                        padding="10px",
                        bg=COLORS["card"],
                        border_radius="12px",
                    ),
                    spacing="3",
                    margin_bottom="10px",
                    justify="center",
                ),
                # Input de mensaje
                rx.hstack(
                    rx.icon(tag="circle-plus", color=COLORS["primary"], size=24),
                    rx.input(
                        placeholder="Escribe un mensaje...",
                        value=SeguimientoState.new_message,
                        on_change=SeguimientoState.set_new_message,
                        bg=COLORS["card"],
                        border=f"1px solid {COLORS['border']}",
                        border_radius="28px",
                        flex="1",
                        color=COLORS["foreground"],
                        font_size="1.1em",
                        on_key_down=SeguimientoState.handle_keypress,
                        height="50px",
                    ),
                    rx.icon(
                        tag="send",
                        color=COLORS["primary"],
                        size=24,
                        on_click=SeguimientoState.send_message,
                        cursor="pointer",
                    ),
                    width="100%",
                    padding="12px 20px",
                    bg=COLORS["background"],
                    border_radius="35px",
                    spacing="3",
                    align="center",
                ),
                width="100%",
                padding_x="18px",
                padding_bottom="20px",
                spacing="0",
            ),

            width="100%",
            height="750px",
            spacing="0",
        ),
        width="100%",
        border=f"3px solid {COLORS['border']}",
        border_radius="25px",
        bg="linear-gradient(180deg, #1a1a2e 0%, #16213e 100%)",
        overflow="hidden",
    )


def notificaciones_component() -> rx.Component:
    """Componente de notificaciones completo para backoffice - Layout vertical."""
    return rx.vstack(
        # 1. Título
        rx.hstack(
            rx.icon("message-circle", size=24, color=COLORS["primary"]),
            rx.heading("Notificaciones", size="7", color=COLORS["primary"]),
            rx.badge(
                "Vista Interna",
                color_scheme="green",
                variant="soft",
                size="1",
            ),
            spacing="3",
            align="center",
            width="100%",
        ),

        # 2. Área de chat compacta
        chat_area_compacta(),

        # 3. Filtros
        panel_filtros(),

        # 4. Lista de conversaciones
        rx.vstack(
            rx.text(
                "Conversaciones",
                font_weight="bold",
                font_size="1.8em",
                color=COLORS["primary"],
            ),
            rx.box(
                rx.vstack(
                    rx.foreach(
                        SeguimientoState.conversaciones_filtradas,
                        conversacion_item
                    ),
                    spacing="2",
                    width="100%",
                ),
                width="100%",
                max_height="400px",
                overflow_y="auto",
                padding="8px",
                bg=COLORS["background"],
                border=f"1px solid {COLORS['border']}",
                border_radius="8px",
            ),
            spacing="2",
            width="100%",
        ),

        # 5. Información y acciones (solo si hay conversación seleccionada)
        rx.cond(
            SeguimientoState.id_conversacion_actual > 0,
            rx.vstack(
                # Información
                rx.vstack(
                    rx.text("Información", font_weight="bold", color=COLORS["primary"], font_size="1.2em"),
                    rx.vstack(
                        rx.hstack(
                            rx.text("Estado:", font_size="0.85em", color=COLORS["muted_foreground"]),
                            rx.badge(
                                SeguimientoState.conversacion_actual_info.get("estado", "N/A"),
                                color_scheme="blue",
                            ),
                            justify="between",
                            width="100%",
                        ),
                        rx.hstack(
                            rx.text("Prioridad:", font_size="0.85em", color=COLORS["muted_foreground"]),
                            rx.badge(
                                SeguimientoState.conversacion_actual_info.get("prioridad", "N/A"),
                                color_scheme="orange",
                            ),
                            justify="between",
                            width="100%",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    spacing="2",
                    padding="12px",
                    bg=COLORS["card"],
                    border_radius="8px",
                    border=f"1px solid {COLORS['border']}",
                    width="100%",
                ),
                # Acciones
                panel_acciones(),
                spacing="3",
                width="100%",
            ),
            rx.fragment(),
        ),

        width="100%",
        spacing="3",
        padding="1em",
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
            rx.badge(
                "Vista Interna",
                color_scheme="green",
                variant="soft",
                size="1",
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
            rx.badge(
                "Vista Interna",
                color_scheme="green",
                variant="soft",
                size="1",
            ),
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
                overflow_y="auto",
                max_height="calc(100vh - 150px)",
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
