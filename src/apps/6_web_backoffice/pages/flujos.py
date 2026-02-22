"""Contenido del panel de Flujos.

Este módulo muestra el diagrama de workflow de versiones de proyectos,
visualizando las 5 fases del ciclo de vida de generación de modelos LLM.

Refactoring DDD (Task #28):
- Consulta tabla estado_version (en lugar de estado)
- Usa campos extendidos de la migración 008
- Mantiene compatibilidad visual con UI existente
- Los triggers de sincronización (migración 009) mantienen ambas tablas actualizadas

Flujo de datos:
1. Usuario selecciona proyecto y versión
2. _refresh_estado() consulta estado_version
3. Mapea campos a actual_workflow_state (12 booleanos)
4. UI renderiza animación de workflow basada en estados
"""

import asyncio
import importlib.util
import logging
from pathlib import Path
from typing import Any, AsyncGenerator

import reflex as rx

# Importar módulos de 2_shared_application usando importlib (directorio con número)
_shared_app_dir = Path(__file__).resolve().parents[3] / "2_shared_application"

_org_helpers_spec = importlib.util.spec_from_file_location(
    "org_selector_helpers", _shared_app_dir / "reflex_shared" / "org_selector_helpers.py"
)
_org_helpers_module = importlib.util.module_from_spec(_org_helpers_spec)
_org_helpers_spec.loader.exec_module(_org_helpers_module)
find_org_id_by_name = _org_helpers_module.find_org_id_by_name
find_project_id_by_name = _org_helpers_module.find_project_id_by_name


def load_flujos_content() -> str:
    """Carga el contenido del panel Flujos desde el archivo flujos.txt."""

    try:
        current_dir = Path(__file__).parent.parent
        content_file = current_dir / "flujos.txt"
        with content_file.open("r", encoding="utf-8") as file_handler:
            return file_handler.read().strip()
    except OSError:
        return "Flujos operativos y procesos automatizados."


logger = logging.getLogger("backoffice")


FLOW_HEADING_MARGIN = "0.6em"
FLOW_BUTTON_MARGIN = "1.5em"
FLOW_BLOCK_PADDING = "1.2em"
FLOW_BOX_PADDING = "1.0em"
FLOW_BOX_PADDING_Y = "0.2em"
FLOW_ARROW_OFFSET = "-1.2em"
FLOW_CARD_OFFSET = "-1.2em"


class FlujosState(rx.State):
    """Estado del diagrama de flujos."""

    # --- Campos del selector de organización ---
    organizations: list[dict[str, Any]] = []
    selected_org_id: int = 0
    user_id: int = 0
    identity_type_id: int = 0
    session_org_id: int = 0
    fl_access_token: str = ""
    fl_session_token: str = ""

    # --- Campos existentes ---
    projects: list[dict[str, Any]] = []
    selected_project_id: int = 0
    versions: list[int] = []
    selected_version_id: int = 0
    actual_workflow_state: dict[str, bool] = {
        "propuesta_cliente": True,
        "revision_interna": True,
        "propuesta_mejoras": True,
        "aceptacion_cliente": True,
        "aceptacion_interna": True,
        "entrenamiento_inicial": True,
        "evaluacion_entrenamiento": True,
        "reentrenamiento": True,
        "optimizacion": False,
        "aprobacion_calidad": False,
        "generacion_llm": False,
        "notificacion_descarga": False,
    }
    display_state: dict[str, bool] = dict.fromkeys(
        actual_workflow_state.keys(), False
    )
    workflow_sequence: list[str] = [
        "propuesta_cliente",
        "revision_interna",
        "propuesta_mejoras",
        "aceptacion_cliente",
        "aceptacion_interna",
        "entrenamiento_inicial",
        "evaluacion_entrenamiento",
        "reentrenamiento",
        "optimizacion",
        "aprobacion_calidad",
        "generacion_llm",
        "notificacion_descarga",
    ]

    # --- Computed vars del selector ---

    @rx.var
    def organization_names(self) -> list[str]:
        """Nombres de organizaciones para el selector."""
        return [org["name"] for org in self.organizations]

    @rx.var
    def selected_org_display(self) -> str:
        """Organización seleccionada para mostrar."""
        if self.selected_org_id > 0:
            for org in self.organizations:
                if org["id"] == self.selected_org_id:
                    return org["name"]
        return ""

    @rx.var
    def project_names(self) -> list[str]:
        """Nombres de proyectos para el selector."""
        return [proj["name"] for proj in self.projects]

    @rx.var
    def selected_project_display(self) -> str:
        """Proyecto seleccionado para mostrar."""
        if self.selected_project_id > 0:
            for proj in self.projects:
                if proj["id"] == self.selected_project_id:
                    return proj["name"]
        return ""

    @rx.var
    def versions_as_strings(self) -> list[str]:
        """Expone las versiones como strings para el selector."""
        return [str(version) for version in self.versions]

    @rx.var
    def selected_version_value(self) -> str:
        """Devuelve el valor seleccionado para el selector de versiones."""
        if self.selected_version_id > 0:
            return str(self.selected_version_id)
        return ""

    # --- Animación ---

    @rx.event(background=True)
    async def play_startup_flow(self) -> AsyncGenerator[None, None]:
        """Ejecuta la animación secuencial al cargar el diagrama."""
        logger.info("[FLUJOS] play_startup_flow | iniciando animacion")

        async with self:
            self.display_state = dict.fromkeys(
                self.actual_workflow_state.keys(), False
            )
        yield

        for key in self.workflow_sequence:
            await asyncio.sleep(0.5)
            async with self:
                self.display_state[key] = True
            yield

        await asyncio.sleep(1)
        async with self:
            self.display_state = self.actual_workflow_state
        yield

    def toggle_key(self, key: str) -> None:
        """Activa o desactiva un estado de prueba."""

        self.actual_workflow_state[key] = not self.actual_workflow_state[key]
        self.display_state = self.actual_workflow_state

    # --- Inicialización y cambio de selectores ---

    def initialize_from_session(
        self,
        organization_id: int,
        user_id: int = 0,
        identity_type_id: int = 0,
        access_token: str = "",
        session_token: str = "",
    ) -> list[rx.EventHandler]:
        """Inicializa selectores desde la sesión.

        Args:
            organization_id: ID de organización de la sesión.
            user_id: ID del usuario interno.
            identity_type_id: Tipo de identidad del usuario.
            access_token: Token JWT de acceso.
            session_token: Token de sesión.
        """
        self.session_org_id = organization_id
        self.user_id = user_id
        self.identity_type_id = identity_type_id
        self.fl_access_token = access_token
        self.fl_session_token = session_token

        # Cargar organizaciones filtradas por asignaciones via API
        from adapters.api_client import get_accessible_organizations
        orgs, default_org = get_accessible_organizations(
            user_id=user_id,
            identity_type_id=identity_type_id,
            session_org_id=organization_id,
            access_token=access_token,
            session_token=session_token,
        )
        self.organizations = orgs
        self.selected_org_id = default_org

        self._load_projects()
        self._load_versions()
        self._refresh_estado()
        return [type(self).play_startup_flow]

    def set_organization(self, org_name: str) -> list[rx.EventHandler]:
        """Cambia la organización seleccionada y recarga proyectos."""
        logger.info("[FLUJOS] set_organization | org_name=%s", org_name)
        new_org_id = find_org_id_by_name(self.organizations, org_name)
        if new_org_id > 0:
            self.selected_org_id = new_org_id
            self.selected_project_id = 0
            self.selected_version_id = 0
            self._load_projects()
            self._load_versions()
            self._refresh_estado()
        return [type(self).play_startup_flow]

    def set_project(self, project_name: str) -> list[rx.EventHandler]:
        """Actualiza el proyecto activo y recarga versiones."""
        logger.info("[FLUJOS] set_project | project_name=%s", project_name)
        new_id = find_project_id_by_name(self.projects, project_name)
        if new_id > 0:
            self.selected_project_id = new_id
        self.selected_version_id = 0
        self._load_versions()
        self._refresh_estado()
        return [type(self).play_startup_flow]

    def set_version(self, version_value: str) -> list[rx.EventHandler]:
        """Actualiza la versión activa y recarga el estado."""
        logger.info("[FLUJOS] set_version | version=%s", version_value)

        try:
            self.selected_version_id = int(version_value)
        except ValueError:
            self.selected_version_id = 0
        self._refresh_estado()
        return [type(self).play_startup_flow]

    # --- Carga de datos ---

    def _load_projects(self) -> None:
        """Carga proyectos filtrados por asignaciones del usuario."""
        if self.selected_org_id <= 0:
            self.projects = []
            self.selected_project_id = 0
            return

        try:
            from adapters.api_client import get_organization_projects
            raw_projects = get_organization_projects(
                organization_id=self.selected_org_id,
                access_token=self.fl_access_token,
                session_token=self.fl_session_token,
            )
            projects = []
            for p in raw_projects:
                projects.append({
                    "id": p.get("id", p.get("project_id", 0)),
                    "name": p.get("name", p.get("nombre", "")),
                })
            self.projects = projects
            if projects:
                if self.selected_project_id == 0:
                    self.selected_project_id = projects[0]["id"]
            else:
                self.selected_project_id = 0
        except Exception as e:
            logger.error("[FLUJOS] Error cargando proyectos: %s", e)
            self.projects = []
            self.selected_project_id = 0

    def _load_versions(self) -> None:
        """Carga versiones asociadas al proyecto."""

        if self.selected_org_id <= 0 or self.selected_project_id <= 0:
            self.versions = []
            self.selected_version_id = 0
            return
        try:
            from adapters.api_client import get_project_versions
            result = get_project_versions(
                project_id=self.selected_project_id,
                organization_id=self.selected_org_id,
                access_token=self.fl_access_token,
                session_token=self.fl_session_token,
            )
            versiones = result.get("versiones", [])
            self.versions = [
                int(v.get("id_version", 0))
                for v in versiones
                if v.get("id_version", 0) > 0
            ]
            if self.versions:
                if self.selected_version_id not in self.versions:
                    self.selected_version_id = self.versions[0]
            else:
                self.selected_version_id = 0
        except Exception as e:
            logger.error("[FLUJOS] Error cargando versiones: %s", e)
            self.versions = []
            self.selected_version_id = 0

    def _refresh_estado(self) -> None:
        """Actualiza el estado final desde la tabla estado_version (DDD refactoring).

        Mapeo de campos:
        - propuesta_cliente: Siempre 1 (true)
        - revision_interna: revision_interna
        - propuesta_mejoras: propuesta_mejoras
        - aceptacion_cliente: final_c
        - aceptacion_interna: final_i
        - entrenamiento_inicial: entrenamiento_inicial_completado
        - evaluacion_entrenamiento: evaluacion_entrenamiento
        - reentrenamiento: reentrenamiento
        - optimizacion: optimizacion
        - aprobacion_calidad: control_calidad_aprobado
        - generacion_llm: generacion_llm_completada
        - notificacion_descarga: notificacion_descarga_enviada
        """
        if (
            self.selected_org_id <= 0
            or self.selected_project_id <= 0
            or self.selected_version_id <= 0
        ):
            return
        logger.info(
            "[FLUJOS] _refresh_estado | org=%d, project=%d, version=%d",
            self.selected_org_id, self.selected_project_id, self.selected_version_id,
        )
        try:
            from adapters.api_client import get_version_state
            result = get_version_state(
                project_id=self.selected_project_id,
                version_id=self.selected_version_id,
                access_token=self.fl_access_token,
                session_token=self.fl_session_token,
            )
            if not result.get("success"):
                self.actual_workflow_state = dict.fromkeys(
                    self.actual_workflow_state.keys(), False
                )
                return
            state = result.get("state") or result.get("data") or {}
            self.actual_workflow_state = {
                "propuesta_cliente": True,
                "revision_interna": bool(state.get("revision_interna", False)),
                "propuesta_mejoras": bool(state.get("propuesta_mejoras", False)),
                "aceptacion_cliente": bool(state.get("final_c", False)),
                "aceptacion_interna": bool(state.get("final_i", False)),
                "entrenamiento_inicial": bool(state.get("entrenamiento_inicial_completado", False)),
                "evaluacion_entrenamiento": bool(state.get("evaluacion_entrenamiento", False)),
                "reentrenamiento": bool(state.get("reentrenamiento", False)),
                "optimizacion": bool(state.get("optimizacion", False)),
                "aprobacion_calidad": bool(state.get("control_calidad_aprobado", False)),
                "generacion_llm": bool(state.get("generacion_llm_completada", False)),
                "notificacion_descarga": bool(state.get("notificacion_descarga_enviada", False)),
            }
        except Exception as e:
            logger.error("[FLUJOS] Error cargando estado: %s", e)
            self.actual_workflow_state = dict.fromkeys(
                self.actual_workflow_state.keys(), False
            )


def node_card(
    name: str, emoji: str, color: str, active: rx.Var[bool]
) -> rx.Component:
    """Crea una tarjeta compacta para un nodo del flujo."""

    return rx.box(
        rx.vstack(
            rx.text(emoji, font_size="1.6em"),
            rx.text(
                name,
                font_weight="bold",
                font_size="0.9em",
                color="#1e293b",
                line_height="1",
                text_align="center",
            ),
            spacing="1",
            align="center",
        ),
        padding="0.9em 0.6em",
        border_radius="10px",
        border=rx.cond(active, f"3px solid {color}", "3px solid #f1f5f9"),
        background="white",
        opacity=rx.cond(active, 1, 0.4),
        box_shadow=rx.cond(active, "0 4px 6px rgba(0, 0, 0, 0.1)", "none"),
        transition="all 0.5s ease-in-out",
        width="150px",
    )


def approval_box(
    title: str, conditions: list[tuple[str, rx.Var[bool]]], active: rx.Var[bool]
) -> rx.Component:
    """Crea una caja de aprobación basada en sub-estados del diccionario."""

    return rx.vstack(
        rx.text(
            title,
            font_size="0.75em",
            color="#64748b",
            font_weight="bold",
            text_transform="uppercase",
            text_align="center",
            width="100%",
        ),
        rx.hstack(
            *[
                rx.badge(
                    name,
                    variant="surface",
                    color_scheme=rx.cond(is_ok, "green", "red"),
                    size="2",
                )
                for name, is_ok in conditions
            ],
            spacing="1",
            justify="center",
            width="100%",
        ),
        spacing="1",
        padding="0.6em 0.9em",
        border="1px dashed #cbd5e1",
        background="#ffffff",
        border_radius="md",
        opacity=rx.cond(active, 1, 0.4),
        width="150px",
        transition="all 0.5s ease-in-out",
        align="center",
    )


def arrow_right() -> rx.Component:
    """Flecha horizontal."""

    return rx.icon(
        "arrow-right",
        color="#cbd5e1",
        size=24,
        margin_top=FLOW_ARROW_OFFSET,
    )


def arrow_down_small() -> rx.Component:
    """Flecha vertical compacta."""

    return rx.icon("arrow-down", color="#cbd5e1", size=16)


def flujos_diagram() -> rx.Component:
    """Renderiza el diagrama de flujos."""

    return rx.box(
        rx.vstack(
            rx.heading(
                "Evolución en la generación de modelos LLM",
                size="6",
                margin_bottom=FLOW_HEADING_MARGIN,
                color="#FF8C00",
            ),
            rx.hstack(
                rx.hstack(
                    rx.text(
                        "Organización",
                        font_size="1.1em",
                        color="#FF8C00",
                        font_weight="bold",
                        min_width="100px",
                    ),
                    rx.select(
                        FlujosState.organization_names,
                        value=FlujosState.selected_org_display,
                        on_change=FlujosState.set_organization,
                        placeholder="Seleccione organización",
                        size="3",
                        width="60%",
                        background_color="#3a3a3a",
                        color="#f2f2f5",
                        border_color="#555",
                    ),
                    spacing="2",
                    align_items="center",
                    width="33%",
                ),
                rx.hstack(
                    rx.text(
                        "Proyecto",
                        font_size="1.1em",
                        color="#FF8C00",
                        font_weight="bold",
                        min_width="80px",
                    ),
                    rx.select(
                        FlujosState.project_names,
                        value=FlujosState.selected_project_display,
                        on_change=FlujosState.set_project,
                        placeholder="Seleccione proyecto",
                        size="3",
                        width="60%",
                        background_color="#3a3a3a",
                        color="#f2f2f5",
                        border_color="#555",
                    ),
                    spacing="2",
                    align_items="center",
                    width="33%",
                ),
                rx.hstack(
                    rx.text(
                        "Versión",
                        font_size="1.1em",
                        color="#FF8C00",
                        font_weight="bold",
                        min_width="80px",
                    ),
                    rx.select(
                        FlujosState.versions_as_strings,
                        value=FlujosState.selected_version_value,
                        on_change=FlujosState.set_version,
                        placeholder="Seleccione versión",
                        size="3",
                        width="60%",
                        background_color="#3a3a3a",
                        color="#f2f2f5",
                        border_color="#555",
                    ),
                    spacing="2",
                    align_items="center",
                    width="33%",
                ),
                spacing="4",
                width="100%",
                align_items="center",
            ),
            rx.box(
                rx.hstack(
                    rx.vstack(
                        rx.box(
                            rx.hstack(
                                rx.box(
                                    rx.vstack(
                                        node_card(
                                            "Propuesta Cliente",
                                            "📝",
                                            "#3b82f6",
                                            active=FlujosState.display_state[
                                                "propuesta_cliente"
                                            ],
                                        ),
                                        arrow_down_small(),
                                        node_card(
                                            "Revisión Interna",
                                            "🔍",
                                            "#8b5cf6",
                                            active=FlujosState.display_state[
                                                "revision_interna"
                                            ],
                                        ),
                                        arrow_down_small(),
                                        node_card(
                                            "Propuesta de mejoras",
                                            "⚙️",
                                            "#f59e0b",
                                            active=FlujosState.display_state[
                                                "propuesta_mejoras"
                                            ],
                                        ),
                                        spacing="2",
                                        align="center",
                                    ),
                                    padding=FLOW_BLOCK_PADDING,
                                    border="2px dashed #cbd5e1",
                                    border_radius="15px",
                                    position="relative",
                                ),
                                rx.box(
                                    rx.icon(
                                        "rotate-ccw",
                                        color="#cbd5e1",
                                        size=20,
                                    ),
                                    position="absolute",
                                    right="-10px",
                                    top="50%",
                                    transform="translateY(-50%)",
                                    background="#f8fafc",
                                    padding="5px 0",
                                ),
                                position="relative",
                            ),
                        ),
                        approval_box(
                            "Validacion",
                            [
                                (
                                    "Cli",
                                    FlujosState.display_state[
                                        "aceptacion_cliente"
                                    ],
                                ),
                                (
                                    "Int",
                                    FlujosState.display_state[
                                        "aceptacion_interna"
                                    ],
                                ),
                            ],
                            active=FlujosState.display_state["aceptacion_cliente"]
                            | FlujosState.display_state["aceptacion_interna"],
                        ),
                        spacing="4",
                        align="center",
                    ),
                    arrow_right(),
                    rx.box(
                        node_card(
                            "Entrenamiento inicial",
                            "🎓",
                            "#10b981",
                            active=FlujosState.display_state[
                                "entrenamiento_inicial"
                            ],
                        ),
                        margin_top=FLOW_CARD_OFFSET,
                    ),
                    arrow_right(),
                    rx.vstack(
                        rx.box(
                            rx.hstack(
                                rx.box(
                                    rx.vstack(
                                        node_card(
                                            "Evaluación Entrenamiento",
                                            "📊",
                                            "#6366f1",
                                            active=FlujosState.display_state[
                                                "evaluacion_entrenamiento"
                                            ],
                                        ),
                                        arrow_down_small(),
                                        node_card(
                                            "Reentrenamiento",
                                            "🔄",
                                            "#ec4899",
                                            active=FlujosState.display_state[
                                                "reentrenamiento"
                                            ],
                                        ),
                                        arrow_down_small(),
                                        node_card(
                                            "Optimización",
                                            "⚡",
                                            "#06b6d4",
                                            active=FlujosState.display_state[
                                                "optimizacion"
                                            ],
                                        ),
                                        spacing="2",
                                        align="center",
                                    ),
                                    padding=FLOW_BLOCK_PADDING,
                                    border="2px dashed #cbd5e1",
                                    border_radius="15px",
                                    position="relative",
                                ),
                                rx.box(
                                    rx.icon(
                                        "rotate-ccw",
                                        color="#cbd5e1",
                                        size=20,
                                    ),
                                    position="absolute",
                                    right="-10px",
                                    top="50%",
                                    transform="translateY(-50%)",
                                    background="#f8fafc",
                                    padding="5px 0",
                                ),
                                position="relative",
                            ),
                        ),
                        approval_box(
                            "Control Calidad",
                            [
                                (
                                    "Calidad",
                                    FlujosState.display_state[
                                        "aprobacion_calidad"
                                    ],
                                )
                            ],
                            active=FlujosState.display_state["aprobacion_calidad"],
                        ),
                        spacing="4",
                        align="center",
                    ),
                    arrow_right(),
                    rx.box(
                        node_card(
                            "Generación del modelo LLM",
                            "🤖",
                            "#10b981",
                            active=FlujosState.display_state["generacion_llm"],
                        ),
                        margin_top=FLOW_CARD_OFFSET,
                    ),
                    arrow_right(),
                    rx.box(
                        node_card(
                            "Notificación de descarga",
                            "🔔",
                            "#10b981",
                            active=FlujosState.display_state["notificacion_descarga"],
                        ),
                        margin_top=FLOW_CARD_OFFSET,
                    ),
                    spacing="2",
                    align="center",
                    padding="1.2em",
                    width="max-content",
                ),
                width="100%",
                overflow_x="auto",
                padding_y=FLOW_BOX_PADDING_Y,
                margin_top="-0.4em",
            ),
            align="center",
            width="100%",
            spacing="0",
        ),
        width="100%",
        background="#1a1a1a",
        padding=FLOW_BOX_PADDING,
        border_radius="12px",
        border="1px solid #e2e8f0",
    )
