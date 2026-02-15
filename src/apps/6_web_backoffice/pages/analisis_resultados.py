"""
Página de Análisis de Resultados de Entrenamientos

Permite:
- Filtrar entrenamientos por organización/proyecto/versión
- Ver métricas y resultados
- Generar sugerencias automáticas
- Comparar parámetros originales vs sugeridos
- Reentrenar con parámetros optimizados
"""

import reflex as rx
import httpx
import logging
from typing import Optional

# Importar el State global para acceder a datos compartidos
from web_backoffice.web_backoffice import State as GlobalState

logger = logging.getLogger(__name__)

# Configuración
MIDDLEWARE_URL = "http://localhost:8007"
CORE_URL = "http://localhost:8003"

# Colores del tema
COLORS = {
    "background": "#0A0A0A",
    "card": "#1A1A1A",
    "border": "#2A2A2A",
    "foreground": "#FFFFFF",
    "muted_foreground": "#A0A0A0",
    "primary": "#3B82F6",
    "success": "#10B981",
    "warning": "#F59E0B",
    "error": "#EF4444",
}


class AnalisisResultadosState(rx.State):
    """Estado para la página de análisis de resultados."""

    # Filtros
    organizaciones: list[dict] = []
    proyectos: list[dict] = []
    versiones: list[dict] = []

    selected_org_id: int = 0
    selected_project_id: int = 0
    selected_version_id: int = 0

    # Lista de entrenamientos
    entrenamientos: list[dict] = []
    loading_entrenamientos: bool = False

    # Sugerencias seleccionadas
    selected_training_id: int = 0
    suggestions_data: Optional[dict] = None
    show_suggestions_modal: bool = False
    loading_suggestions: bool = False

    # Modal de reentrenamiento (reutiliza ventana de entrenamientos)
    show_retrain_modal: bool = False
    retrain_params: dict = {}
    id_sugerencia_to_apply: int = 0

    # Mensajes
    message: str = ""
    message_type: str = ""  # "success", "error", "info"

    def on_mount(self):
        """Se ejecuta al montar la página."""
        logger.info("AnalisisResultadosState montado")
        return self.cargar_organizaciones()

    @rx.event(background=True)
    async def cargar_organizaciones(self):
        """Carga la lista de organizaciones."""
        async with self:
            try:
                # Obtener token del state global
                parent_state = await self.get_state(GlobalState)
                access_token = parent_state.access_token
                session_token = parent_state.session_token

                if not access_token:
                    self.message = "No hay sesión activa"
                    self.message_type = "error"
                    return

                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{MIDDLEWARE_URL}/organizations/list",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "X-Session-Token": session_token
                        },
                        timeout=10.0
                    )

                    if response.status_code == 200:
                        data = response.json()
                        self.organizaciones = data.get("organizaciones", [])
                    else:
                        self.message = f"Error cargando organizaciones: {response.status_code}"
                        self.message_type = "error"

            except Exception as e:
                logger.error(f"Error cargando organizaciones: {e}")
                self.message = f"Error: {str(e)}"
                self.message_type = "error"

    @rx.event(background=True)
    async def on_org_change(self, org_id: str):
        """Se ejecuta cuando cambia la organización seleccionada."""
        async with self:
            self.selected_org_id = int(org_id) if org_id else 0
            self.selected_project_id = 0
            self.selected_version_id = 0
            self.proyectos = []
            self.versiones = []
            self.entrenamientos = []

            if self.selected_org_id > 0:
                await self.cargar_proyectos()

    @rx.event(background=True)
    async def cargar_proyectos(self):
        """Carga proyectos de la organización seleccionada."""
        async with self:
            if self.selected_org_id == 0:
                return

            try:
                parent_state = await self.get_state(GlobalState)
                access_token = parent_state.access_token
                session_token = parent_state.session_token

                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{CORE_URL}/projects/organization/{self.selected_org_id}",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "X-Session-Token": session_token
                        },
                        timeout=10.0
                    )

                    if response.status_code == 200:
                        data = response.json()
                        self.proyectos = data.get("projects", [])
                    else:
                        self.message = f"Error cargando proyectos: {response.status_code}"
                        self.message_type = "error"

            except Exception as e:
                logger.error(f"Error cargando proyectos: {e}")
                self.message = f"Error: {str(e)}"
                self.message_type = "error"

    @rx.event(background=True)
    async def on_project_change(self, project_id: str):
        """Se ejecuta cuando cambia el proyecto seleccionado."""
        async with self:
            self.selected_project_id = int(project_id) if project_id else 0
            self.selected_version_id = 0
            self.versiones = []
            self.entrenamientos = []

            if self.selected_project_id > 0:
                await self.cargar_versiones()

    @rx.event(background=True)
    async def cargar_versiones(self):
        """Carga versiones del proyecto seleccionado."""
        async with self:
            if self.selected_project_id == 0:
                return

            try:
                parent_state = await self.get_state(GlobalState)
                access_token = parent_state.access_token
                session_token = parent_state.session_token

                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{CORE_URL}/projects/{self.selected_project_id}/versions",
                        params={"org_id": self.selected_org_id},
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "X-Session-Token": session_token
                        },
                        timeout=10.0
                    )

                    if response.status_code == 200:
                        data = response.json()
                        self.versiones = data.get("versions", [])
                    else:
                        self.message = f"Error cargando versiones: {response.status_code}"
                        self.message_type = "error"

            except Exception as e:
                logger.error(f"Error cargando versiones: {e}")
                self.message = f"Error: {str(e)}"
                self.message_type = "error"

    @rx.event(background=True)
    async def on_version_change(self, version_id: str):
        """Se ejecuta cuando cambia la versión seleccionada."""
        async with self:
            self.selected_version_id = int(version_id) if version_id else 0
            self.entrenamientos = []

    @rx.event(background=True)
    async def buscar_entrenamientos(self):
        """Busca entrenamientos según los filtros."""
        async with self:
            self.loading_entrenamientos = True
            self.entrenamientos = []
            self.message = ""

            try:
                parent_state = await self.get_state(GlobalState)
                access_token = parent_state.access_token
                session_token = parent_state.session_token

                params = {}
                if self.selected_org_id > 0:
                    params["organization_id"] = self.selected_org_id
                if self.selected_project_id > 0:
                    params["project_id"] = self.selected_project_id
                if self.selected_version_id > 0:
                    params["version_id"] = self.selected_version_id

                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{CORE_URL}/analysis/trainings",
                        params=params,
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "X-Session-Token": session_token
                        },
                        timeout=10.0
                    )

                    if response.status_code == 200:
                        self.entrenamientos = response.json()
                        self.message = f"Se encontraron {len(self.entrenamientos)} entrenamientos"
                        self.message_type = "success"
                    else:
                        self.message = f"Error buscando entrenamientos: {response.status_code}"
                        self.message_type = "error"

            except Exception as e:
                logger.error(f"Error buscando entrenamientos: {e}")
                self.message = f"Error: {str(e)}"
                self.message_type = "error"
            finally:
                self.loading_entrenamientos = False

    @rx.event(background=True)
    async def generar_sugerencias(self, id_entrenamiento: int):
        """Genera sugerencias para un entrenamiento."""
        async with self:
            self.loading_suggestions = True
            self.message = ""

            try:
                parent_state = await self.get_state(GlobalState)
                access_token = parent_state.access_token
                session_token = parent_state.session_token

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{CORE_URL}/analysis/trainings/{id_entrenamiento}/generate-suggestions",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "X-Session-Token": session_token
                        },
                        timeout=30.0
                    )

                    if response.status_code == 200:
                        self.message = "Sugerencias generadas exitosamente"
                        self.message_type = "success"
                        # Recargar lista de entrenamientos
                        await self.buscar_entrenamientos()
                    else:
                        self.message = f"Error generando sugerencias: {response.status_code}"
                        self.message_type = "error"

            except Exception as e:
                logger.error(f"Error generando sugerencias: {e}")
                self.message = f"Error: {str(e)}"
                self.message_type = "error"
            finally:
                self.loading_suggestions = False

    @rx.event(background=True)
    async def ver_sugerencias(self, id_entrenamiento: int):
        """Muestra las sugerencias de un entrenamiento."""
        async with self:
            self.loading_suggestions = True
            self.selected_training_id = id_entrenamiento

            try:
                parent_state = await self.get_state(GlobalState)
                access_token = parent_state.access_token
                session_token = parent_state.session_token

                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{CORE_URL}/analysis/trainings/{id_entrenamiento}/suggestions",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "X-Session-Token": session_token
                        },
                        timeout=10.0
                    )

                    if response.status_code == 200:
                        self.suggestions_data = response.json()
                        self.show_suggestions_modal = True
                    else:
                        self.message = f"Error obteniendo sugerencias: {response.status_code}"
                        self.message_type = "error"

            except Exception as e:
                logger.error(f"Error obteniendo sugerencias: {e}")
                self.message = f"Error: {str(e)}"
                self.message_type = "error"
            finally:
                self.loading_suggestions = False

    def cerrar_modal_sugerencias(self):
        """Cierra el modal de sugerencias."""
        self.show_suggestions_modal = False
        self.suggestions_data = None

    @rx.event(background=True)
    async def preparar_reentrenamiento(self, id_sugerencia: int):
        """Prepara el reentrenamiento con parámetros sugeridos."""
        async with self:
            try:
                parent_state = await self.get_state(GlobalState)
                access_token = parent_state.access_token
                session_token = parent_state.session_token

                # Obtener parámetros sugeridos del backend
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{CORE_URL}/analysis/suggestions/{id_sugerencia}/params",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "X-Session-Token": session_token
                        },
                        timeout=10.0
                    )

                    if response.status_code == 200:
                        self.retrain_params = response.json()
                        self.id_sugerencia_to_apply = id_sugerencia
                        self.show_retrain_modal = True
                        self.show_suggestions_modal = False  # Cerrar modal de sugerencias
                    else:
                        self.message = f"Error obteniendo parámetros: {response.status_code}"
                        self.message_type = "error"

            except Exception as e:
                logger.error(f"Error preparando reentrenamiento: {e}")
                self.message = f"Error: {str(e)}"
                self.message_type = "error"

    def cerrar_modal_reentrenar(self):
        """Cierra el modal de reentrenamiento."""
        self.show_retrain_modal = False
        self.retrain_params = {}

    @rx.event(background=True)
    async def analizar_modelo(self, id_entrenamiento: int):
        """Lanza análisis del modelo generado."""
        async with self:
            self.loading_suggestions = True  # Reutilizar loading
            self.message = ""

            try:
                parent_state = await self.get_state(GlobalState)
                access_token = parent_state.access_token
                session_token = parent_state.session_token

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{CORE_URL}/analysis/trainings/{id_entrenamiento}/analyze",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "X-Session-Token": session_token
                        },
                        timeout=60.0  # Análisis puede tardar
                    )

                    if response.status_code == 200:
                        data = response.json()
                        score = data.get('overall_quality_score', 0)
                        self.message = f"Análisis completado: Score {score:.2%}"
                        self.message_type = "success"
                        # Recargar lista
                        await self.buscar_entrenamientos()
                    else:
                        self.message = f"Error analizando modelo: {response.status_code}"
                        self.message_type = "error"

            except Exception as e:
                logger.error(f"Error analizando modelo: {e}")
                self.message = f"Error: {str(e)}"
                self.message_type = "error"
            finally:
                self.loading_suggestions = False

# ============================================================================
# Componentes UI
# ============================================================================

def filtros_section() -> rx.Component:
    """Sección de filtros de búsqueda."""
    return rx.box(
        rx.heading("Filtros de Búsqueda", size="6", margin_bottom="1em"),
        rx.hstack(
            rx.box(
                rx.text("Organización", size="2", color=COLORS["muted_foreground"]),
                rx.select(
                    ["Seleccione..."] + [
                        f"{org['organization_id']} - {org['organization_name']}"
                        for org in AnalisisResultadosState.organizaciones
                    ],
                    value=rx.cond(
                        AnalisisResultadosState.selected_org_id > 0,
                        f"{AnalisisResultadosState.selected_org_id} - {[org['organization_name'] for org in AnalisisResultadosState.organizaciones if org['organization_id'] == AnalisisResultadosState.selected_org_id][0] if [org for org in AnalisisResultadosState.organizaciones if org['organization_id'] == AnalisisResultadosState.selected_org_id] else ''}",
                        "Seleccione..."
                    ),
                    on_change=lambda value: AnalisisResultadosState.on_org_change(
                        value.split(" - ")[0] if value != "Seleccione..." else "0"
                    ),
                ),
                width="30%",
            ),
            rx.box(
                rx.text("Proyecto", size="2", color=COLORS["muted_foreground"]),
                rx.select(
                    ["Seleccione..."] + [
                        f"{proj['id']} - {proj['nombre']}"
                        for proj in AnalisisResultadosState.proyectos
                    ],
                    value=rx.cond(
                        AnalisisResultadosState.selected_project_id > 0,
                        f"{AnalisisResultadosState.selected_project_id} - ...",
                        "Seleccione..."
                    ),
                    on_change=lambda value: AnalisisResultadosState.on_project_change(
                        value.split(" - ")[0] if value != "Seleccione..." else "0"
                    ),
                    disabled=AnalisisResultadosState.selected_org_id == 0,
                ),
                width="30%",
            ),
            rx.box(
                rx.text("Versión", size="2", color=COLORS["muted_foreground"]),
                rx.select(
                    ["Seleccione..."] + [
                        f"{ver['id']} - v{ver['id']}"
                        for ver in AnalisisResultadosState.versiones
                    ],
                    value=rx.cond(
                        AnalisisResultadosState.selected_version_id > 0,
                        f"{AnalisisResultadosState.selected_version_id} - v{AnalisisResultadosState.selected_version_id}",
                        "Seleccione..."
                    ),
                    on_change=lambda value: AnalisisResultadosState.on_version_change(
                        value.split(" - ")[0] if value != "Seleccione..." else "0"
                    ),
                    disabled=AnalisisResultadosState.selected_project_id == 0,
                ),
                width="20%",
            ),
            rx.button(
                "Buscar",
                on_click=AnalisisResultadosState.buscar_entrenamientos,
                disabled=AnalisisResultadosState.selected_org_id == 0,
                loading=AnalisisResultadosState.loading_entrenamientos,
                color_scheme="blue",
            ),
            spacing="4",
            width="100%",
        ),
        padding="1.5em",
        background=COLORS["card"],
        border_radius="8px",
        border=f"1px solid {COLORS['border']}",
        margin_bottom="2em",
    )


def training_row(training: dict) -> rx.Component:
    """Fila de la tabla de entrenamientos."""
    return rx.table.row(
        rx.table.cell(f"#{training['numero_secuencia']}"),
        rx.table.cell(training['fecha_fin'][:10] if training.get('fecha_fin') else "En progreso"),
        rx.table.cell(training['estado']),
        rx.table.cell(f"{training['loss_final']:.4f}" if training.get('loss_final') else "N/A"),
        rx.table.cell(f"{training['accuracy_validacion']:.2%}" if training.get('accuracy_validacion') else "N/A"),
        rx.table.cell(
            rx.cond(
                training['tiene_sugerencias'],
                rx.text("✓", color=COLORS["success"]),
                rx.text("✗", color=COLORS["muted_foreground"]),
            )
        ),
        rx.table.cell(
            rx.hstack(
                # Botón Analizar
                rx.button(
                    rx.icon("bar-chart", size=16),
                    "Analizar",
                    on_click=lambda: AnalisisResultadosState.analizar_modelo(training['id']),
                    size="1",
                    color_scheme="purple",
                ),

                # Botones de sugerencias
                rx.cond(
                    training['tiene_sugerencias'],
                    rx.button(
                        "Ver Sugerencias",
                        on_click=lambda: AnalisisResultadosState.ver_sugerencias(training['id']),
                        size="1",
                        color_scheme="blue",
                    ),
                    rx.button(
                        "Generar",
                        on_click=lambda: AnalisisResultadosState.generar_sugerencias(training['id']),
                        size="1",
                        color_scheme="gray",
                    ),
                ),

                # Botón Reentrenar
                rx.cond(
                    training['tiene_sugerencias'],
                    rx.button(
                        rx.icon("play", size=16),
                        "Reentrenar",
                        on_click=lambda: AnalisisResultadosState.preparar_reentrenamiento(training['id']),
                        size="1",
                        color_scheme="green",
                    ),
                    rx.fragment(),
                ),
                spacing="2",
            )
        ),
    )


def entrenamientos_table() -> rx.Component:
    """Tabla de entrenamientos."""
    return rx.box(
        rx.heading("Entrenamientos Completados", size="6", margin_bottom="1em"),
        rx.cond(
            AnalisisResultadosState.loading_entrenamientos,
            rx.spinner(),
            rx.cond(
                AnalisisResultadosState.entrenamientos.length() > 0,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Secuencia"),
                            rx.table.column_header_cell("Fecha"),
                            rx.table.column_header_cell("Estado"),
                            rx.table.column_header_cell("Loss Final"),
                            rx.table.column_header_cell("Accuracy"),
                            rx.table.column_header_cell("Sugerencias"),
                            rx.table.column_header_cell("Acciones"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(
                            AnalisisResultadosState.entrenamientos,
                            training_row
                        )
                    ),
                ),
                rx.text("No hay entrenamientos para mostrar", color=COLORS["muted_foreground"]),
            )
        ),
        padding="1.5em",
        background=COLORS["card"],
        border_radius="8px",
        border=f"1px solid {COLORS['border']}",
    )


def comparison_row(comparison: dict) -> rx.Component:
    """Fila de la tabla de comparación."""
    # Determinar color según prioridad
    bg_color = rx.cond(
        comparison['prioridad'] == 1,
        "rgba(239, 68, 68, 0.1)",  # Rojo para críticos
        rx.cond(
            comparison['prioridad'] == 2,
            "rgba(245, 158, 11, 0.1)",  # Naranja para importantes
            "transparent"
        )
    )

    return rx.table.row(
        rx.table.cell(comparison['parametro']),
        rx.table.cell(str(comparison['original'])),
        rx.table.cell(
            rx.hstack(
                rx.text(str(comparison['sugerido'])),
                rx.cond(
                    comparison['cambio'] == 'aumentar',
                    rx.icon("arrow-up", size=16, color="green"),
                    rx.cond(
                        comparison['cambio'] == 'disminuir',
                        rx.icon("arrow-down", size=16, color="red"),
                        rx.icon("minus", size=16, color="gray"),
                    )
                ),
                spacing="2",
            )
        ),
        rx.table.cell(
            rx.badge(
                comparison['cambio'],
                color_scheme=rx.cond(
                    comparison['cambio'] == 'aumentar',
                    "green",
                    rx.cond(
                        comparison['cambio'] == 'disminuir',
                        "red",
                        "gray"
                    )
                )
            )
        ),
        rx.table.cell(
            rx.text(comparison['razon'], size="2", max_width="400px", white_space="normal"),
        ),
        style={"background": bg_color}
    )


def suggestions_modal() -> rx.Component:
    """Modal que muestra comparativa de parámetros originales vs sugeridos."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.dialog.title("Comparativa de Parámetros"),

                # Header con scores
                rx.cond(
                    AnalisisResultadosState.suggestions_data != None,
                    rx.hstack(
                        rx.badge(
                            f"Confianza: {AnalisisResultadosState.suggestions_data['confianza_score']:.1f}%",
                            color_scheme="blue",
                            size="3",
                        ),
                        rx.badge(
                            f"Mejora esperada: {AnalisisResultadosState.suggestions_data['mejora_esperada_pct']:.1f}%",
                            color_scheme="green",
                            size="3",
                        ),
                        spacing="4",
                        margin_bottom="1em",
                    ),
                    rx.fragment(),
                ),

                # Razón general
                rx.cond(
                    AnalisisResultadosState.suggestions_data != None,
                    rx.box(
                        rx.heading("Análisis General", size="4", margin_bottom="0.5em"),
                        rx.text(
                            AnalisisResultadosState.suggestions_data['razon_sugerencia'],
                            size="2",
                            color=COLORS["muted_foreground"],
                            white_space="pre-wrap",
                        ),
                        padding="1em",
                        background=COLORS["card"],
                        border_radius="8px",
                        margin_bottom="1em",
                    ),
                    rx.fragment(),
                ),

                # Tabla comparativa
                rx.cond(
                    AnalisisResultadosState.suggestions_data != None,
                    rx.box(
                        rx.heading("Cambios Sugeridos", size="4", margin_bottom="0.5em"),
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("Parámetro", width="15%"),
                                    rx.table.column_header_cell("Original", width="10%"),
                                    rx.table.column_header_cell("Sugerido", width="10%"),
                                    rx.table.column_header_cell("Tipo", width="10%"),
                                    rx.table.column_header_cell("Razón", width="55%"),
                                )
                            ),
                            rx.table.body(
                                rx.foreach(
                                    AnalisisResultadosState.suggestions_data['comparaciones'],
                                    comparison_row
                                )
                            ),
                            width="100%",
                        ),
                        max_height="400px",
                        overflow_y="auto",
                    ),
                    rx.fragment(),
                ),

                # Leyenda de prioridades
                rx.hstack(
                    rx.box(
                        rx.text("● Crítico", size="2"),
                        background="rgba(239, 68, 68, 0.1)",
                        padding="0.5em",
                        border_radius="4px",
                    ),
                    rx.box(
                        rx.text("● Importante", size="2"),
                        background="rgba(245, 158, 11, 0.1)",
                        padding="0.5em",
                        border_radius="4px",
                    ),
                    rx.box(
                        rx.text("● Opcional", size="2"),
                        padding="0.5em",
                        border_radius="4px",
                    ),
                    spacing="3",
                    margin_top="1em",
                    margin_bottom="1em",
                ),

                # Botones de acción
                rx.hstack(
                    rx.dialog.close(
                        rx.button(
                            "Cerrar",
                            color_scheme="gray",
                        )
                    ),
                    rx.cond(
                        AnalisisResultadosState.suggestions_data != None,
                        rx.button(
                            rx.icon("play", margin_right="0.5em"),
                            "Reentrenar con estos parámetros",
                            on_click=lambda: AnalisisResultadosState.preparar_reentrenamiento(
                                AnalisisResultadosState.suggestions_data['id']
                            ),
                            color_scheme="green",
                        ),
                        rx.fragment(),
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="1200px",
            padding="2em",
        ),
        open=AnalisisResultadosState.show_suggestions_modal,
    )


def analisis_resultados_page() -> rx.Component:
    """Página principal de análisis de resultados."""
    return rx.box(
        rx.heading("Análisis de Resultados", size="8", margin_bottom="1em"),
        rx.text(
            "Analiza resultados de entrenamientos y recibe sugerencias automáticas para optimizar hiperparámetros",
            color=COLORS["muted_foreground"],
            margin_bottom="2em",
        ),
        rx.cond(
            AnalisisResultadosState.message != "",
            rx.callout(
                AnalisisResultadosState.message,
                color_scheme=rx.cond(
                    AnalisisResultadosState.message_type == "success",
                    "green",
                    rx.cond(
                        AnalisisResultadosState.message_type == "error",
                        "red",
                        "blue"
                    )
                ),
                margin_bottom="1em",
            ),
            rx.fragment(),
        ),
        filtros_section(),
        entrenamientos_table(),

        # Modal de sugerencias
        suggestions_modal(),

        padding="2em",
        max_width="1400px",
        margin="0 auto",
    )
