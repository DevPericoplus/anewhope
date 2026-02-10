"""
Componente Seguimiento para Web Backoffice (Interno)

Integra:
1. Notificaciones (template completo)
2. Calendario (template completo con integración cambios)
3. Visor de Tickets (custom - vista interna)
"""

import reflex as rx
import datetime
import pydantic
import calendar
import importlib.util
from pathlib import Path
from sqlalchemy import text

from components.org_selector import org_project_selector_bar

# Importar módulos de 2_shared_application usando importlib (directorio con número)
_shared_app_dir = Path(__file__).resolve().parents[3] / "2_shared_application"

_db_helper_spec = importlib.util.spec_from_file_location(
    "db_query_helper", _shared_app_dir / "db_query_helper.py"
)
_db_helper_module = importlib.util.module_from_spec(_db_helper_spec)
_db_helper_spec.loader.exec_module(_db_helper_module)
get_projects_db_engine = _db_helper_module.get_projects_db_engine

_org_helpers_spec = importlib.util.spec_from_file_location(
    "org_selector_helpers", _shared_app_dir / "reflex_shared" / "org_selector_helpers.py"
)
_org_helpers_module = importlib.util.module_from_spec(_org_helpers_spec)
_org_helpers_spec.loader.exec_module(_org_helpers_module)
find_org_id_by_name = _org_helpers_module.find_org_id_by_name
find_project_id_by_name = _org_helpers_module.find_project_id_by_name
load_organizations_for_selector = _org_helpers_module.load_organizations_for_selector
load_projects_for_selector = _org_helpers_module.load_projects_for_selector


# ============================================================================
# COLORS
# ============================================================================

COLORS = {
    "background": "#0B1120",
    "card": "#141b2d",
    "border": "#1e2744",
    "input": "#3a3a3a",
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


def _load_cambios_adapter():
    """Carga el adapter de cambios (calendario) usando importlib."""
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
    is_mixed: bool = False  # True si hay eventos cliente + interno


# ============================================================================
# SEGUIMIENTO STATE (combina notificaciones, calendario y tickets)
# ============================================================================

class SeguimientoState(rx.State):
    """Estado combinado para seguimiento."""

    # === SELECTORES UNIFICADOS DE PÁGINA ===
    seg_organizations: list[dict] = []       # [{id, name}]
    seg_selected_org_id: int = 0
    seg_projects: list[dict] = []            # [{id, name}]
    seg_selected_project_id: int = 0

    @rx.var
    def seg_org_names(self) -> list[str]:
        """Nombres de organizaciones para el selector."""
        return [o["name"] for o in self.seg_organizations]

    @rx.var
    def seg_selected_org_display(self) -> str:
        """Nombre de la organización seleccionada."""
        for o in self.seg_organizations:
            if o["id"] == self.seg_selected_org_id:
                return o["name"]
        return ""

    @rx.var
    def seg_project_names(self) -> list[str]:
        """Nombres de proyectos para el selector."""
        return [p["name"] for p in self.seg_projects]

    @rx.var
    def seg_selected_project_display(self) -> str:
        """Nombre del proyecto seleccionado."""
        for p in self.seg_projects:
            if p["id"] == self.seg_selected_project_id:
                return p["name"]
        return ""

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

    # Modal de eventos del calendario
    modal_eventos_abierto: bool = False
    modal_eventos_fecha: str = ""
    modal_eventos_contenido: str = ""

    # === TICKETS ===
    tickets_list: list[dict] = []
    is_loading_tickets: bool = False
    tickets_error: str = ""

    # Modal de interacción con ticket
    modal_ticket_abierto: bool = False
    ticket_seleccionado_id: int = 0
    ticket_seleccionado: dict = {}
    ticket_respuesta: str = ""
    ticket_nuevo_estado: str = ""

    async def _get_db_engine(self):
        """Crea el engine de la base de datos para myllm_projects_db (centralizado)."""
        return get_projects_db_engine()

    def set_new_message(self, value: str):
        """Setter explícito para new_message."""
        self.new_message = value

    # === MÉTODOS NOTIFICACIONES ===

    async def load_conversaciones_organizacion(self):
        """Carga las conversaciones de la organización seleccionada."""
        org_id = self.seg_selected_org_id
        if org_id <= 0:
            self.conversaciones_list = []
            self.messages = []
            self.id_conversacion_actual = 0
            return

        engine = await self._get_db_engine()
        if not engine:
            self.conversaciones_error = "Error de conexión a base de datos"
            print("[DEBUG] No se pudo obtener el engine de BD")
            return

        try:
            conversaciones_adapter = _load_conversaciones_adapter()
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

    # === MÉTODOS SELECTORES UNIFICADOS ===

    async def set_seg_organization(self, org_name: str):
        """Cambia la organización seleccionada y recarga todos los componentes."""
        new_id = find_org_id_by_name(self.seg_organizations, org_name)
        if new_id <= 0:
            return

        self.seg_selected_org_id = new_id
        self.seg_selected_project_id = 0

        # Cargar proyectos de la organización
        await self._load_seg_projects()

        # Recargar los tres componentes
        await self.load_conversaciones_organizacion()
        await self.load_events_data()
        await self.load_tickets()

    async def set_seg_project(self, project_name: str):
        """Cambia el proyecto seleccionado y recarga calendario y tickets."""
        new_id = find_project_id_by_name(self.seg_projects, project_name)
        if new_id <= 0:
            return

        self.seg_selected_project_id = new_id

        # Recargar calendario y tickets (notificaciones son por org, no por proyecto)
        await self.load_events_data()
        await self.load_tickets()

    async def _load_seg_projects(self):
        """Carga los proyectos de la organización seleccionada (respeta asignaciones)."""
        if self.seg_selected_org_id <= 0:
            self.seg_projects = []
            return

        try:
            from web_backoffice.web_backoffice import State as MainState
            main_state = await self.get_state(MainState)

            projects, default_id = load_projects_for_selector(
                user_id=main_state.user_id,
                identity_type_id=main_state.identity_type_id,
                organization_id=self.seg_selected_org_id,
            )
            self.seg_projects = projects

            # Seleccionar primer proyecto por defecto si hay
            if projects and default_id > 0:
                self.seg_selected_project_id = default_id
            else:
                self.seg_selected_project_id = 0

        except Exception as e:
            print(f"[ERROR] Error al cargar proyectos: {e}")
            self.seg_projects = []

    # === MÉTODOS CALENDARIO ===

    async def load_events_data(self):
        """Carga eventos del calendario desde la tabla cambios."""
        print("[DEBUG CALENDARIO] load_events_data INICIADO")
        if self.seg_selected_org_id <= 0:
            print("[DEBUG CALENDARIO] No hay organización seleccionada, saltando carga de eventos")
            self.events_data = []
            return

        engine = await self._get_db_engine()
        if not engine:
            print("[DEBUG CALENDARIO] No se pudo obtener engine")
            self.events_data = []
            return

        try:
            cambios_adapter = _load_cambios_adapter()

            # Obtener mes y año seleccionados
            mes = self._month_map.get(self.selected_month, datetime.datetime.now().month)
            anio = int(self.selected_year)

            # Determinar id_proyecto (None o el seleccionado)
            id_proyecto = self.seg_selected_project_id if self.seg_selected_project_id > 0 else None

            print(f"[DEBUG CALENDARIO] Consultando eventos para:")
            print(f"[DEBUG CALENDARIO]   org_id={self.seg_selected_org_id}")
            print(f"[DEBUG CALENDARIO]   mes={mes} ({self.selected_month})")
            print(f"[DEBUG CALENDARIO]   año={anio}")
            print(f"[DEBUG CALENDARIO]   proyecto_id={id_proyecto}")

            # Obtener eventos agrupados por día
            eventos = cambios_adapter.obtener_cambios_agrupados_por_dia(
                engine=engine,
                id_organizacion=self.seg_selected_org_id,
                mes=mes,
                anio=anio,
                id_proyecto=id_proyecto
            )

            self.events_data = eventos
            print(f"[DEBUG CALENDARIO] Eventos cargados: {len(eventos)} días con eventos")

        except Exception as e:
            print(f"[ERROR CALENDARIO] Error al cargar eventos: {e}")
            import traceback
            traceback.print_exc()
            self.events_data = []

    @rx.var
    def month_days_with_events(self) -> list[list[DayInfo]]:
        """Returns a matrix of DayInfo objects for the selected month with events."""
        try:
            y = int(self.selected_year)
            m = self._month_map.get(self.selected_month, 1)

            print(f"[DEBUG CALENDARIO] month_days_with_events calculando para {self.selected_month}/{y}")
            print(f"[DEBUG CALENDARIO] events_data tiene {len(self.events_data)} días con eventos")

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
                    print(f"[DEBUG CALENDARIO] Evento agregado para día {day_num}: color={event['color']}")

            print(f"[DEBUG CALENDARIO] events_by_day tiene {len(events_by_day)} días")

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

    async def load_tickets(self):
        """Carga los tickets del proyecto seleccionado (VISTA INTERNA - todos los usuarios)."""
        self.is_loading_tickets = True
        self.tickets_error = ""

        org_id = self.seg_selected_org_id
        project_id = self.seg_selected_project_id

        if org_id <= 0:
            self.tickets_list = []
            self.is_loading_tickets = False
            return

        engine = await self._get_db_engine()
        if not engine:
            self.tickets_error = "Error de conexión a base de datos"
            self.is_loading_tickets = False
            return

        try:
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
                    "project_id": project_id if project_id > 0 else None
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

    async def abrir_modal_ticket(self, ticket_id: int):
        """Abre el modal para interactuar con un ticket."""
        self.ticket_seleccionado_id = ticket_id
        self.ticket_respuesta = ""

        # Buscar el ticket en la lista
        for ticket in self.tickets_list:
            if ticket["id"] == ticket_id:
                self.ticket_seleccionado = ticket
                self.ticket_nuevo_estado = ticket["estado"]
                break

        # Cargar detalles adicionales del ticket desde BD
        engine = await self._get_db_engine()
        if engine:
            try:
                with engine.connect() as conn:
                    # Obtener última consulta del ticket
                    query = text("""
                        SELECT consulta, fecha_consulta
                        FROM myllm_projects_db.ticket_interacciones
                        WHERE ticket_id = :ticket_id
                        ORDER BY fecha_consulta DESC
                        LIMIT 1
                    """)
                    result = conn.execute(query, {"ticket_id": ticket_id}).fetchone()

                    if result:
                        self.ticket_seleccionado["ultima_consulta"] = result[0]
                        self.ticket_seleccionado["fecha_consulta"] = result[1].strftime("%Y-%m-%d %H:%M") if result[1] else ""
                    else:
                        self.ticket_seleccionado["ultima_consulta"] = "Sin consultas registradas"
                        self.ticket_seleccionado["fecha_consulta"] = ""
            except Exception as e:
                print(f"Error cargando detalles del ticket: {e}")

        self.modal_ticket_abierto = True

    def cerrar_modal_ticket(self):
        """Cierra el modal de ticket."""
        self.modal_ticket_abierto = False
        self.ticket_seleccionado_id = 0
        self.ticket_seleccionado = {}
        self.ticket_respuesta = ""
        self.ticket_nuevo_estado = ""

    def on_modal_ticket_change(self, is_open: bool):
        """Handler para cambios en el estado del modal."""
        if not is_open:
            self.cerrar_modal_ticket()

    def set_ticket_respuesta(self, value: str):
        """Setter para ticket_respuesta."""
        self.ticket_respuesta = value

    def set_ticket_nuevo_estado(self, value: str):
        """Setter para ticket_nuevo_estado."""
        self.ticket_nuevo_estado = value

    async def guardar_interaccion_ticket(self):
        """Guarda la respuesta al ticket, actualiza estado y envía mensaje automático."""
        # Permitir cambios de estado sin respuesta obligatoria
        tiene_respuesta = bool(self.ticket_respuesta.strip())
        tiene_cambio_estado = self.ticket_nuevo_estado != self.ticket_seleccionado.get("estado")

        if not tiene_respuesta and not tiene_cambio_estado:
            # No hay ni respuesta ni cambio de estado, no hacer nada
            return

        engine = await self._get_db_engine()
        if not engine:
            return

        try:
            from web_backoffice.web_backoffice import State as MainState
            conversaciones_adapter = _load_conversaciones_adapter()

            main_state = await self.get_state(MainState)
            user_id = main_state.user_id

            with engine.begin() as conn:
                # 1. Guardar interacción en ticket_interacciones solo si hay respuesta
                if tiene_respuesta:
                    insert_interaccion = text("""
                        INSERT INTO myllm_projects_db.ticket_interacciones
                        (ticket_id, autor_consulta_id, autor_respuesta_id, consulta, respuesta, fecha_respuesta)
                        VALUES (:ticket_id, :cliente_id, :autor_id, :consulta, :respuesta, NOW())
                    """)
                    conn.execute(insert_interaccion, {
                        "ticket_id": self.ticket_seleccionado_id,
                        "cliente_id": self.ticket_seleccionado.get("cliente_id"),
                        "autor_id": user_id,
                        "consulta": "",  # Empty for backoffice responses
                        "respuesta": self.ticket_respuesta
                    })

                # 2. Actualizar estado del ticket si cambió
                if tiene_cambio_estado:
                    update_ticket = text("""
                        UPDATE myllm_projects_db.tickets
                        SET estado = :estado, fecha_actualizacion = NOW()
                        WHERE id = :ticket_id
                    """)
                    conn.execute(update_ticket, {
                        "ticket_id": self.ticket_seleccionado_id,
                        "estado": self.ticket_nuevo_estado
                    })

                # 3. Enviar notificación al cliente si hay cambios
                if tiene_respuesta or tiene_cambio_estado:
                    # Obtener conversación asociada al cliente del ticket
                    query_conversacion = text("""
                        SELECT c.id_conversacion
                        FROM myllm_projects_db.conversaciones c
                        WHERE c.id_usuario_cliente = :cliente_id
                          AND c.estado IN ('abierta', 'en_curso')
                        ORDER BY c.fecha_ultima_actualizacion DESC
                        LIMIT 1
                    """)
                    result = conn.execute(query_conversacion, {
                        "cliente_id": self.ticket_seleccionado.get("cliente_id")
                    }).fetchone()

                    if result:
                        id_conversacion = result[0]

                        # Construir mensaje automático
                        mensaje_auto = f"🎫 Actualización de ticket: {self.ticket_seleccionado.get('titulo')}\n\n"

                        if tiene_cambio_estado:
                            mensaje_auto += f"Estado: {self.ticket_nuevo_estado}\n\n"

                        if tiene_respuesta:
                            mensaje_auto += f"Respuesta del soporte:\n{self.ticket_respuesta}"

                        insert_mensaje = text("""
                            INSERT INTO myllm_projects_db.mensajes_conversacion
                                (id_conversacion, id_usuario_emisor, tipo_emisor, texto_mensaje, id_ticket_referenciado)
                            VALUES
                                (:id_conversacion, :id_usuario_emisor, :tipo_emisor, :texto_mensaje, :id_ticket_referenciado)
                        """)
                        conn.execute(insert_mensaje, {
                            "id_conversacion": id_conversacion,
                            "id_usuario_emisor": user_id,
                            "tipo_emisor": "interno",
                            "texto_mensaje": mensaje_auto,
                            "id_ticket_referenciado": self.ticket_seleccionado_id
                        })

                        print(f"[INFO] Mensaje automático enviado a conversación {id_conversacion}")
                    else:
                        print(f"[WARNING] No se encontró conversación activa para el cliente {self.ticket_seleccionado.get('cliente_id')}")

            # 5. Recargar lista de tickets y cerrar modal
            await self.load_tickets()
            self.cerrar_modal_ticket()

        except Exception as e:
            print(f"[ERROR] Error al guardar interacción del ticket: {e}")
            import traceback
            traceback.print_exc()

    @rx.event
    async def on_mount_seguimiento(self):
        """Se ejecuta cuando se monta el componente.

        Carga organizaciones usando load_organizations_for_selector (respeta asignaciones),
        selecciona la primera por defecto y carga todos los datos.
        """
        print("[DEBUG BACKOFFICE] on_mount_seguimiento INICIADO")

        try:
            from web_backoffice.web_backoffice import State as MainState
            main_state = await self.get_state(MainState)
            user_id = main_state.user_id
            identity_type_id = main_state.identity_type_id
            session_org_id = main_state.organization_id
            print(f"[DEBUG BACKOFFICE] user_id={user_id}, identity_type_id={identity_type_id}")

            # 1. Cargar organizaciones (respeta asignaciones)
            orgs, default_id = load_organizations_for_selector(
                user_id=user_id,
                identity_type_id=identity_type_id,
                session_org_id=session_org_id,
            )
            self.seg_organizations = orgs
            print(f"[DEBUG BACKOFFICE] Organizaciones cargadas: {len(orgs)}")

            if not orgs or default_id <= 0:
                print("[DEBUG BACKOFFICE] No hay organizaciones disponibles")
                return

            # 2. Seleccionar organización por defecto
            self.seg_selected_org_id = default_id
            print(f"[DEBUG BACKOFFICE] Org seleccionada: {self.seg_selected_org_display} (ID: {default_id})")

            # 3. Cargar proyectos de la organización
            await self._load_seg_projects()
            print(f"[DEBUG BACKOFFICE] Proyectos cargados: {len(self.seg_projects)}")

            # 4. Cargar datos de los tres componentes
            await self.load_conversaciones_organizacion()
            print("[DEBUG BACKOFFICE] Conversaciones cargadas")

            await self.load_events_data()
            print("[DEBUG BACKOFFICE] Eventos calendario cargados")

            await self.load_tickets()
            print("[DEBUG BACKOFFICE] Tickets cargados")

        except Exception as e:
            print(f"[ERROR BACKOFFICE] Error en on_mount_seguimiento: {e}")
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
            rx.text("Estado:", font_size="1.1em", color=COLORS["primary"], font_weight="bold"),
            rx.select(
                ["todas", "abierta", "en_curso", "resuelta"],
                value=SeguimientoState.filtro_estado,
                on_change=SeguimientoState.set_filtro_estado,
                size="3",
                background_color=COLORS["input"],
                color=COLORS["foreground"],
                border_color=COLORS["border"],
            ),
            width="100%",
            justify="between",
            align="center",
        ),
        # Filtro por prioridad
        rx.hstack(
            rx.text("Prioridad:", font_size="1.1em", color=COLORS["primary"], font_weight="bold"),
            rx.select(
                ["todas", "baja", "media", "alta", "urgente"],
                value=SeguimientoState.filtro_prioridad,
                on_change=SeguimientoState.set_filtro_prioridad,
                size="3",
                background_color=COLORS["input"],
                color=COLORS["foreground"],
                border_color=COLORS["border"],
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
    """Render a single day cell with event colors and tooltips."""
    # Determinar el background: evento, hoy, o transparent
    bg_color = rx.cond(
        day_info.has_event,
        day_info.event_color,
        rx.cond(
            day_info.is_today,
            "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            "transparent"
        )
    )

    # Box shadow para hoy o para eventos mixtos
    box_shadow_value = rx.cond(
        day_info.is_mixed,
        "0 0 15px rgba(255, 215, 0, 0.8)",  # Dorado brillante para mixtos
        rx.cond(
            day_info.is_today,
            "0 4px 10px rgba(118, 75, 162, 0.4)",
            "none"
        )
    )

    cell_content = rx.center(
        rx.cond(
            day_info.day == 0,
            rx.text(""),
            rx.text(
                f"{day_info.day}",
                font_weight="500",
                color="white",
                font_size="1.1em"
            )
        ),
        width="40px",
        height="40px",
        border_radius="14px",
        bg=bg_color,
        box_shadow=box_shadow_value,
        border=rx.cond(
            day_info.has_event,
            f"2px solid {day_info.event_color}",
            "none"
        ),
        transition="all 0.2s ease",
        _hover={
            "bg": rx.cond(
                day_info.has_event,
                day_info.event_color,
                "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
            ),
            "color": "white",
            "transform": "scale(1.1)",
            "box_shadow": "0 4px 10px rgba(118, 75, 162, 0.4)"
        },
        cursor=rx.cond(day_info.has_event, "pointer", "default"),
        on_click=SeguimientoState.abrir_modal_eventos(day_info.day)
    )

    # Usar rx.cond para determinar si mostrar tooltip o no
    cell_visual = rx.cond(
        day_info.has_event,
        rx.tooltip(cell_content, content=day_info.tooltip_text),
        cell_content
    )

    return rx.center(
        cell_visual,
        width="50px",
        height="50px",
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
                        color="black",
                        font_weight="bold",
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
    """Calendario widget con integración de cambios."""
    return rx.vstack(
        # Header
        rx.text(
            "Calendario",
            font_size="1.8em",
            font_weight="800",
            background_image="linear-gradient(45deg, #667eea 0%, #764ba2 100%)",
            background_clip="text",
            color="transparent",
            margin_bottom="18px",
            letter_spacing="-0.5px"
        ),

        # Selectores de Año y Mes (org y proyecto se controlan desde la barra superior)
        rx.hstack(
            rx.hstack(
                rx.text("Año:", color="yellow", font_weight="bold", font_size="1.1em"),
                rx.select(
                    SeguimientoState.years,
                    value=SeguimientoState.selected_year,
                    on_change=SeguimientoState.set_year,
                    size="3",
                    radius="medium",
                    width="140px",
                    bg="rgba(255,255,255,0.1)",
                    color="yellow",
                    border="1px solid yellow",
                    font_size="1.4em",
                    font_weight="bold"
                ),
                align="center",
                spacing="2"
            ),
            rx.hstack(
                rx.text("Mes:", color="yellow", font_weight="bold", font_size="1.1em"),
                rx.select(
                    SeguimientoState.months,
                    value=SeguimientoState.selected_month,
                    on_change=SeguimientoState.set_month,
                    size="3",
                    radius="medium",
                    width="110px",
                    bg="rgba(255,255,255,0.1)",
                    color="yellow",
                    border="1px solid yellow",
                    font_size="1.4em",
                    font_weight="bold"
                ),
                align="center",
                spacing="2"
            ),
            justify="between",
            width="100%",
            padding_x="15px",
            margin_bottom="20px"
        ),

        # Weekday Headers
        rx.hstack(
            *[rx.center(
                rx.text(d, font_weight="700", font_size="0.95em", color="#a0aec0"),
                width="50px"
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
        padding="30px",
        border_radius="24px",
        box_shadow="0 20px 40px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.1)",
        align="center",
        width="100%",
        max_width="480px",
        border="1px solid rgba(255,255,255,0.1)"
    )


# ============================================================================
# COMPONENTE TICKETS
# ============================================================================

def ticket_row(ticket: dict) -> rx.Component:
    """Fila que muestra un ticket con botón de soporte."""
    return rx.box(
        rx.hstack(
            # Título del ticket
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
            # Badge de estado (rx.match para evaluar Var reactivo en rx.foreach)
            rx.badge(
                ticket["estado"],
                color_scheme=rx.match(
                    ticket["estado"],
                    ("abierto", "blue"),
                    ("en_espera", "amber"),
                    ("resuelto", "green"),
                    ("cerrado", "gray"),
                    "gray",
                ),
                variant="solid",
                size="2",
                style={"fontSize": "14px", "padding": "6px 12px", "fontWeight": "600", "color": "black"},
            ),
            # Badge de prioridad (rx.match para evaluar Var reactivo en rx.foreach)
            rx.badge(
                ticket["prioridad"],
                color_scheme=rx.match(
                    ticket["prioridad"],
                    ("baja", "gray"),
                    ("media", "cyan"),
                    ("alta", "orange"),
                    ("urgente", "red"),
                    "gray",
                ),
                variant="solid",
                size="2",
                style={"fontSize": "14px", "padding": "6px 12px", "fontWeight": "600", "color": "black"},
            ),
            # Botón de soporte
            rx.tooltip(
                rx.icon_button(
                    rx.icon("message-square-text", size=20),
                    size="3",
                    variant="soft",
                    color_scheme="blue",
                    on_click=lambda: SeguimientoState.abrir_modal_ticket(ticket["id"]),
                ),
                content="Soporte - Responder al ticket",
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

        # Lista de tickets (sin scroll propio, usa el scroll de la columna)
        rx.box(
            rx.cond(
                SeguimientoState.is_loading_tickets,
                rx.center(
                    rx.spinner(size="3", color=COLORS["primary"]),
                    height="100px",
                ),
                rx.cond(
                    SeguimientoState.tickets_list.length() > 0,
                    rx.vstack(
                        rx.foreach(
                            SeguimientoState.tickets_list,
                            ticket_row,
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    rx.center(
                        rx.text(
                            "No hay tickets para este proyecto",
                            color=COLORS["muted_foreground"],
                            font_size="0.9em",
                        ),
                        height="100px",
                    ),
                ),
            ),
            width="100%",
            padding="8px",
            bg=f"{COLORS['background']}80",
            border=f"1px solid {COLORS['border']}",
            border_radius="8px",
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


def modal_ticket_soporte() -> rx.Component:
    """Modal para interactuar con un ticket de soporte."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Header del modal
                rx.hstack(
                    rx.icon("message-square-text", size=24, color=COLORS["primary"]),
                    rx.heading(
                        "Soporte - Responder Ticket",
                        size="6",
                        color=COLORS["primary"],
                    ),
                    rx.dialog.close(
                        rx.icon_button(
                            rx.icon("x", size=20),
                            variant="soft",
                            color_scheme="gray",
                            on_click=SeguimientoState.cerrar_modal_ticket,
                        ),
                    ),
                    justify="between",
                    align="center",
                    width="100%",
                    margin_bottom="1em",
                ),

                # Información del ticket
                rx.vstack(
                    rx.hstack(
                        rx.text("Ticket:", font_weight="bold", color=COLORS["primary"]),
                        rx.text(
                            SeguimientoState.ticket_seleccionado.get("titulo", ""),
                            color=COLORS["foreground"],
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    rx.hstack(
                        rx.text("Estado actual:", font_weight="bold", color=COLORS["primary"]),
                        rx.badge(
                            SeguimientoState.ticket_seleccionado.get("estado", ""),
                            variant="solid",
                            size="2",
                        ),
                        rx.text("Prioridad:", font_weight="bold", color=COLORS["primary"], margin_left="1em"),
                        rx.badge(
                            SeguimientoState.ticket_seleccionado.get("prioridad", ""),
                            variant="solid",
                            size="2",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    spacing="2",
                    width="100%",
                    padding="1em",
                    background_color=COLORS["card"],
                    border_radius="0.5em",
                    margin_bottom="1em",
                ),

                # Última consulta del cliente
                rx.vstack(
                    rx.text("Última consulta del cliente:", font_weight="bold", color=COLORS["primary"], font_size="0.9em"),
                    rx.box(
                        rx.text(
                            SeguimientoState.ticket_seleccionado.get("ultima_consulta", "Sin consultas"),
                            color=COLORS["foreground"],
                            font_size="0.95em",
                        ),
                        padding="1em",
                        background_color=f"{COLORS['card']}80",
                        border=f"1px solid {COLORS['border']}",
                        border_radius="0.4em",
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                    margin_bottom="1em",
                ),

                # Selector de nuevo estado
                rx.vstack(
                    rx.text("Cambiar estado:", font_weight="bold", color=COLORS["primary"], font_size="1.1em"),
                    rx.select(
                        ["abierto", "en_espera", "resuelto", "cerrado"],
                        value=SeguimientoState.ticket_nuevo_estado,
                        on_change=SeguimientoState.set_ticket_nuevo_estado,
                        size="3",
                        width="100%",
                        background_color=COLORS["input"],
                        color=COLORS["foreground"],
                        border_color=COLORS["border"],
                    ),
                    spacing="1",
                    width="100%",
                    margin_bottom="1em",
                ),

                # Textarea para respuesta
                rx.vstack(
                    rx.text("Tu respuesta:", font_weight="bold", color=COLORS["primary"], font_size="0.9em"),
                    rx.text_area(
                        placeholder="Escribe tu respuesta al ticket aquí...",
                        value=SeguimientoState.ticket_respuesta,
                        on_change=SeguimientoState.set_ticket_respuesta,
                        size="3",
                        width="100%",
                        min_height="150px",
                    ),
                    spacing="1",
                    width="100%",
                    margin_bottom="1em",
                ),

                # Botones de acción
                rx.hstack(
                    rx.dialog.close(
                        rx.button(
                            "Cancelar",
                            on_click=SeguimientoState.cerrar_modal_ticket,
                            variant="soft",
                            color_scheme="gray",
                        ),
                    ),
                    rx.button(
                        rx.icon("send", size=18),
                        "Enviar Respuesta",
                        on_click=SeguimientoState.guardar_interaccion_ticket,
                        variant="solid",
                        color_scheme="blue",
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                ),

                width="100%",
                spacing="3",
            ),
            max_width="600px",
            padding="2em",
            background_color=COLORS["background"],
            border=f"2px solid {COLORS['border']}",
        ),
        open=SeguimientoState.modal_ticket_abierto,
        on_open_change=SeguimientoState.on_modal_ticket_change,
    )


# ============================================================================
# PANEL PRINCIPAL SEGUIMIENTO
# ============================================================================

def seguimiento_panel() -> rx.Component:
    """Panel principal de seguimiento con tres zonas.

    Un único par de selectores org/proyecto en la parte superior controla
    el contenido de notificaciones, calendario y tickets.
    """

    return rx.vstack(
        # ===== BARRA SUPERIOR: Selectores unificados =====
        org_project_selector_bar(
            org_names=SeguimientoState.seg_org_names,
            selected_org_display=SeguimientoState.seg_selected_org_display,
            on_org_change=SeguimientoState.set_seg_organization,
            project_names=SeguimientoState.seg_project_names,
            selected_project_display=SeguimientoState.seg_selected_project_display,
            on_project_change=SeguimientoState.set_seg_project,
            org_placeholder="Seleccione organización",
            project_placeholder="Seleccione proyecto",
        ),

        # ===== CONTENIDO: TRES ZONAS =====
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
                max_height="calc(100vh - 200px)",
            ),

            # DERECHA: Calendario + Tickets (con scroll)
            rx.box(
                rx.vstack(
                    # Calendario (arriba)
                    calendario_component(),

                    # Tickets (abajo)
                    tickets_viewer_component(),

                    spacing="3",
                    width="100%",
                ),
                flex="1",
                padding="1em",
                background_color=COLORS["background"],
                border=f"1px solid {COLORS['border']}",
                border_radius="0.5em",
                overflow_y="scroll",
                height="700px",
            ),

            spacing="3",
            width="100%",
            align_items="stretch",
            height="calc(100vh - 170px)",
        ),

        # Modal de soporte para tickets
        modal_ticket_soporte(),

        # Modal de eventos del calendario
        modal_eventos_calendario(),

        width="100%",
        spacing="1",
        on_mount=SeguimientoState.on_mount_seguimiento,
    )
