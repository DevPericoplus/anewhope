"""Contenido del panel de Flujos."""

from pathlib import Path
from typing import Any, AsyncGenerator

import asyncio
import importlib.util
import logging
import os
import subprocess
import sys

import reflex as rx


def load_flujos_content() -> str:
    """Carga el contenido del panel Flujos desde el archivo flujos.txt."""

    try:
        current_dir = Path(__file__).parent.parent
        content_file = current_dir / "flujos.txt"
        with content_file.open("r", encoding="utf-8") as file_handler:
            return file_handler.read().strip()
    except OSError:
        return "Flujos operativos y procesos automatizados."


logger = logging.getLogger(__name__)


FLOW_HEADING_MARGIN = "0.6em"
FLOW_BUTTON_MARGIN = "1.5em"
FLOW_BLOCK_PADDING = "1.2em"
FLOW_BOX_PADDING = "1.0em"
FLOW_BOX_PADDING_Y = "0.2em"
FLOW_ARROW_OFFSET = "-1.2em"
FLOW_CARD_OFFSET = "-1.2em"


def _load_projects_db_settings() -> dict[str, str]:
    """Carga credenciales y nombre de base de datos para proyectos."""

    env_settings = _load_env_settings_module("frontend_env_settings")
    protected = env_settings.load_protected_settings()

    return {
        "host": os.environ.get("MARIADB_HOST", str(protected.get("mariadb_host", ""))),
        "port": os.environ.get(
            "MARIADB_PORT", str(protected.get("mariadb_port", 3306))
        ),
        "database": os.environ.get(
            "MARIADB_PROJECTS_DATABASE",
            str(protected.get("mariadb_ai_database", "myllm_projects_db")),
        ),
        "user": os.environ.get(
            "MARIADB_READER_USER", protected.get("mariadb_reader_user", "")
        ),
        "password": os.environ.get(
            "MARIADB_READER_PASSWORD",
            protected.get("mariadb_reader_password", ""),
        ),
        "cli_path": os.environ.get(
            "MARIADB_CLI_PATH", protected.get("mariadb_cli_path", "")
        ),
    }


def _load_env_settings_module(module_name: str) -> Any:
    """Carga el módulo de configuración compartida."""

    module_path = (
        Path(__file__).resolve().parents[4]
        / "src/2_shared_application/config/env_settings.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar el módulo de configuración")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _run_mysql_query(query: str) -> list[list[str]]:
    """Ejecuta una consulta SQL y devuelve filas."""

    settings = _load_projects_db_settings()
    cmd = [
        settings["cli_path"],
        "-u",
        settings["user"],
        f"-p{settings['password']}",
        "--database",
        settings["database"],
        "-N",
        "-B",
        "-e",
        query,
    ]
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        logger.error(
            "Error al consultar proyectos: %s",
            exc.stderr.strip() if exc.stderr else exc,
        )
        return []
    rows: list[list[str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        rows.append(line.split("\t"))
    return rows


class FlujosState(rx.State):
    """Estado del diagrama de flujos."""

    organization_id: int = 0
    projects: list[dict[str, Any]] = []
    project_names: list[str] = []
    selected_project_name: str = ""
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

    async def play_startup_flow(self) -> AsyncGenerator[None, None]:
        """Ejecuta la animación secuencial al cargar el diagrama."""

        self.display_state = dict.fromkeys(
            self.actual_workflow_state.keys(), False
        )
        yield
        for key in self.workflow_sequence:
            await asyncio.sleep(0.5)
            self.display_state[key] = True
            yield
        await asyncio.sleep(1)
        self.display_state = self.actual_workflow_state
        yield

    def toggle_key(self, key: str) -> None:
        """Activa o desactiva un estado de prueba."""

        self.actual_workflow_state[key] = not self.actual_workflow_state[key]
        self.display_state = self.actual_workflow_state

    def initialize_from_session(self, organization_id: int) -> list[rx.EventHandler]:
        """Inicializa selectores desde la sesión."""

        self.organization_id = organization_id
        self._load_projects()
        self._load_versions()
        self._refresh_estado()
        return [type(self).play_startup_flow]

    def set_project(self, project_name: str) -> list[rx.EventHandler]:
        """Actualiza el proyecto activo y recarga versiones."""

        self.selected_project_name = project_name
        self.selected_project_id = self._get_project_id(project_name)
        self._load_versions()
        self._refresh_estado()
        return [type(self).play_startup_flow]

    def set_version(self, version_value: str) -> list[rx.EventHandler]:
        """Actualiza la versión activa y recarga el estado."""

        try:
            self.selected_version_id = int(version_value)
        except ValueError:
            self.selected_version_id = 0
        self._refresh_estado()
        return [type(self).play_startup_flow]

    def _get_project_id(self, project_name: str) -> int:
        """Obtiene el id de proyecto a partir del nombre."""

        for project in self.projects:
            if project.get("name") == project_name:
                return int(project.get("id", 0))
        return 0

    def _load_projects(self) -> None:
        """Carga proyectos desde la base de datos."""

        if self.organization_id <= 0:
            self.projects = []
            self.project_names = []
            self.selected_project_name = ""
            self.selected_project_id = 0
            return
        rows = _run_mysql_query(
            "SELECT id, nombre FROM proyectos "
            f"WHERE id_organizacion = {int(self.organization_id)} "
            "ORDER BY nombre"
        )
        self.projects = [
            {"id": int(row[0]), "name": row[1]} for row in rows if len(row) >= 2
        ]
        self.project_names = [project["name"] for project in self.projects]
        if self.project_names:
            if self.selected_project_name not in self.project_names:
                self.selected_project_name = self.project_names[0]
            self.selected_project_id = self._get_project_id(self.selected_project_name)
        else:
            self.selected_project_name = ""
            self.selected_project_id = 0

    def _load_versions(self) -> None:
        """Carga versiones asociadas al proyecto."""

        if self.organization_id <= 0 or self.selected_project_id <= 0:
            self.versions = []
            self.selected_version_id = 0
            return
        rows = _run_mysql_query(
            "SELECT id_version FROM versiones "
            f"WHERE id_organizacion = {int(self.organization_id)} "
            f"AND id_proyecto = {int(self.selected_project_id)} "
            "ORDER BY id_version"
        )
        self.versions = [int(row[0]) for row in rows if row]
        if self.versions:
            if self.selected_version_id not in self.versions:
                self.selected_version_id = self.versions[0]
        else:
            self.selected_version_id = 0

    def _refresh_estado(self) -> None:
        """Actualiza el estado final desde la tabla estado."""

        if (
            self.organization_id <= 0
            or self.selected_project_id <= 0
            or self.selected_version_id <= 0
        ):
            return
        # FIX: estado.id_version almacena el PRIMARY KEY de versiones.id, no el número de versión
        # Por eso usamos un subquery para obtener el id correcto
        rows = _run_mysql_query(
            "SELECT propuesta_cliente, revision_interna, propuesta_mejoras, "
            "aceptacion_cliente, aceptacion_interna, entrenamiento_inicial, "
            "evaluacion_entrenamiento, reentrenamiento, optimizacion, "
            "aprobacion_calidad, generacion_llm, notificacion_descarga "
            "FROM estado "
            f"WHERE id_organizacion = {int(self.organization_id)} "
            f"AND id_proyecto = {int(self.selected_project_id)} "
            f"AND id_version = (SELECT id FROM versiones WHERE id_proyecto = {int(self.selected_project_id)} AND id_version = {int(self.selected_version_id)}) "
            "LIMIT 1"
        )
        if not rows or len(rows[0]) < 12:
            self.actual_workflow_state = dict.fromkeys(
                self.actual_workflow_state.keys(), False
            )
            return
        values = [value == "1" for value in rows[0][:12]]
        keys = list(self.actual_workflow_state.keys())
        self.actual_workflow_state = dict(zip(keys, values))

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
                "Evolucion en la  generación de modelos LLM",
                size="6",
                margin_bottom=FLOW_HEADING_MARGIN,
                color="#22c55e",
            ),
            rx.hstack(
                rx.hstack(
                    rx.text(
                        "Proyecto",
                        font_size="0.85em",
                        color="#e2e8f0",
                        font_weight="bold",
                        min_width="80px",
                    ),
                    rx.select(
                        FlujosState.project_names,
                        value=FlujosState.selected_project_name,
                        on_change=FlujosState.set_project,
                        placeholder="Seleccione un proyecto",
                        background_color="#383854",
                        border_color="#000000",
                        color="#f2f2f5",
                        width="50%",
                    ),
                    spacing="2",
                    align_items="center",
                    width="50%",
                ),
                rx.hstack(
                    rx.text(
                        "Version",
                        font_size="0.85em",
                        color="#e2e8f0",
                        font_weight="bold",
                        min_width="80px",
                    ),
                    rx.select(
                        FlujosState.versions_as_strings,
                        value=FlujosState.selected_version_value,
                        on_change=FlujosState.set_version,
                        placeholder="Seleccione una version",
                        background_color="#383854",
                        border_color="#000000",
                        color="#f2f2f5",
                        width="50%",
                    ),
                    spacing="2",
                    align_items="center",
                    width="50%",
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
