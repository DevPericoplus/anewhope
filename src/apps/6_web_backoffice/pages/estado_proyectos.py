"""Página de gestión de estados de versiones de proyectos (Estado de Proyectos).

Este módulo permite visualizar y editar el estado completo de versiones,
incluyendo todas las fases del ciclo de vida de generación de modelos LLM.

Características:
- Lista de versiones filtradas por asignaciones del usuario
- Vista detallada de estado con todas las fases
- Edición de flags por fase (con validación de permisos)
- Control de permisos: SuperAdmin (todo), Admin/Editor (asignados), Auditor/Lector (solo lectura)
- Visualización de progreso (%)
- Validación de transiciones según reglas de negocio

Arquitectura DDD:
- Consulta tabla estado_version (migración 008)
- Usa campos extendidos para gestión completa
- Preparado para integrar ProjectVersionStateService (Task #31-32)
"""

from pathlib import Path
from typing import Any

import importlib.util
import logging
import os
import subprocess
import sys

import reflex as rx


logger = logging.getLogger(__name__)


# ============================================================================
# Configuración y helpers de base de datos
# ============================================================================


def _load_projects_db_settings() -> dict[str, str]:
    """Carga credenciales y nombre de base de datos para proyectos."""
    env_settings = _load_env_settings_module("estado_proyectos_env_settings")
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
            "Error al consultar base de datos: %s",
            exc.stderr.strip() if exc.stderr else exc,
        )
        return []
    rows: list[list[str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        rows.append(line.split("\t"))
    return rows


def _run_mysql_update(query: str) -> bool:
    """Ejecuta un UPDATE/INSERT SQL y retorna éxito."""
    settings = _load_projects_db_settings()
    # Usar writer user para modificaciones
    user = os.environ.get(
        "MARIADB_WRITER_USER",
        settings.get("user", ""),  # Fallback a reader si no hay writer
    )
    password = os.environ.get(
        "MARIADB_WRITER_PASSWORD",
        settings.get("password", ""),
    )

    cmd = [
        settings["cli_path"],
        "-u",
        user,
        f"-p{password}",
        "--database",
        settings["database"],
        "-N",
        "-B",
        "-e",
        query,
    ]
    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError as exc:
        logger.error(
            "Error al actualizar base de datos: %s",
            exc.stderr.strip() if exc.stderr else exc,
        )
        return False


# ============================================================================
# Estado de la página
# ============================================================================


class EstadoProyectosState(rx.State):
    """Estado de la página de gestión de estados de versiones."""

    # Contexto de usuario
    user_id: int = 0
    organization_id: int = 0
    identity_type_id: int = 0

    # Listas de datos
    organizations: list[dict[str, Any]] = []
    projects: list[dict[str, Any]] = []
    versions: list[dict[str, Any]] = []

    # Selección actual
    selected_org_id: int = 0
    selected_project_id: int = 0
    selected_version_id: int = 0

    # Estado de la versión seleccionada
    current_state: dict[str, Any] = {}

    # UI
    loading: bool = False
    error_message: str = ""
    success_message: str = ""

    # ========================================================================
    # Inicialización
    # ========================================================================

    def initialize_from_session(
        self,
        user_id: int,
        organization_id: int,
        identity_type_id: int,
    ) -> None:
        """Inicializa la página desde la sesión del usuario.

        Args:
            user_id: ID del usuario autenticado
            organization_id: ID de organización del usuario
            identity_type_id: Tipo de identidad (1=SuperAdmin, 2=Admin, etc.)
        """
        self.user_id = user_id
        self.organization_id = organization_id
        self.identity_type_id = identity_type_id

        self._load_organizations()
        self._load_projects()
        self._load_versions()

    # ========================================================================
    # Propiedades computadas
    # ========================================================================

    @rx.var
    def is_super_admin(self) -> bool:
        """Verifica si el usuario es SuperAdmin."""
        return self.identity_type_id == 1

    @rx.var
    def can_edit(self) -> bool:
        """Verifica si el usuario puede editar estados.

        Permisos de escritura:
        - SuperAdmin (1): siempre
        - Admin (2) o Editor (3): con asignación
        - Auditor (5) o Lector (4): nunca
        """
        if self.identity_type_id == 1:
            return True
        if self.identity_type_id in (4, 5):
            return False
        # TODO: Verificar asignación real en Task #30
        return True

    @rx.var
    def organization_names(self) -> list[str]:
        """Nombres de organizaciones para selector."""
        return [org["name"] for org in self.organizations]

    @rx.var
    def project_names(self) -> list[str]:
        """Nombres de proyectos para selector."""
        return [proj["name"] for proj in self.projects]

    @rx.var
    def version_numbers(self) -> list[str]:
        """Números de versión para selector."""
        return [str(v["version_id"]) for v in self.versions]

    @rx.var
    def selected_version_display(self) -> str:
        """Versión seleccionada para mostrar."""
        return str(self.selected_version_id) if self.selected_version_id > 0 else ""

    @rx.var
    def progress_percentage(self) -> float:
        """Calcula el porcentaje de progreso de la versión."""
        if not self.current_state:
            return 0.0

        progress = 0.0

        # Fase 1: Propuesta aprobada (20%)
        if self.current_state.get("final_c") and self.current_state.get("final_i"):
            progress += 20.0

        # Fase 2: Entrenamiento completado (20%)
        if self.current_state.get("entrenamiento_inicial_completado"):
            progress += 20.0

        # Fase 3: Calidad aprobada (20%)
        if self.current_state.get("control_calidad_aprobado"):
            progress += 20.0

        # Fase 4: Generación completada (20%)
        if self.current_state.get("generacion_llm_completada"):
            progress += 20.0

        # Fase 5: Notificación enviada (20%)
        if self.current_state.get("notificacion_descarga_enviada"):
            progress += 20.0

        return progress

    @rx.var
    def state_internal_display(self) -> str:
        """Retorna el nombre legible del estado interno."""
        state_map = {
            "propuesta_cliente": "Propuesta del Cliente",
            "revision_interna": "Revisión Interna",
            "propuesta_mejoras": "Propuesta de Mejoras",
            "aceptacion_cliente": "Aceptación del Cliente",
            "aceptacion_interna": "Aceptación Interna",
            "entrenamiento_inicial": "Entrenamiento Inicial",
            "entrenamiento_inicial_completado": "Entrenamiento Completado",
            "evaluacion_entrenamiento": "Evaluación",
            "reentrenamiento": "Reentrenamiento",
            "optimizacion": "Optimización",
            "aprobacion_calidad": "Aprobación de Calidad",
            "generacion_llm": "Generación del Modelo",
            "generacion_llm_completada": "Modelo Generado",
            "notificacion_descarga": "Notificación Enviada",
        }
        return state_map.get(
            self.current_state.get("state_internal", ""), "Desconocido"
        )

    # ========================================================================
    # Carga de datos
    # ========================================================================

    def _load_organizations(self) -> None:
        """Carga organizaciones según permisos del usuario."""
        if self.is_super_admin:
            # SuperAdmin ve todas las organizaciones
            rows = _run_mysql_query(
                "SELECT organization_id, organization_name "
                "FROM myllm_core_db.organizations "
                "ORDER BY organization_name"
            )
        else:
            # Otros usuarios: filtrar por asignaciones
            rows = _run_mysql_query(
                "SELECT DISTINCT o.organization_id, o.organization_name "
                "FROM myllm_core_db.organizations o "
                "INNER JOIN asignaciones_organizaciones_internas aoi "
                "ON o.organization_id = aoi.id_organizacion "
                f"WHERE aoi.id_usuario = {self.user_id} "
                "AND aoi.active = 1 "
                "ORDER BY o.organization_name"
            )

        self.organizations = [
            {"id": int(row[0]), "name": row[1]} for row in rows if len(row) >= 2
        ]

        # Seleccionar organización por defecto
        if self.organizations:
            if self.selected_org_id == 0:
                # Preferir organización del usuario
                if self.organization_id > 0:
                    self.selected_org_id = self.organization_id
                else:
                    self.selected_org_id = self.organizations[0]["id"]

    def _load_projects(self) -> None:
        """Carga proyectos de la organización seleccionada."""
        if self.selected_org_id <= 0:
            self.projects = []
            self.selected_project_id = 0
            return

        if self.is_super_admin:
            # SuperAdmin ve todos los proyectos de la organización
            rows = _run_mysql_query(
                "SELECT id, nombre "
                "FROM proyectos "
                f"WHERE id_organizacion = {self.selected_org_id} "
                "ORDER BY nombre"
            )
        else:
            # Otros usuarios: filtrar por asignaciones
            rows = _run_mysql_query(
                "SELECT DISTINCT p.id, p.nombre "
                "FROM proyectos p "
                "LEFT JOIN proyectos_roles pr "
                "ON p.id = pr.id_proyecto "
                f"WHERE p.id_organizacion = {self.selected_org_id} "
                f"AND (pr.id_usuario = {self.user_id} AND pr.active = 1) "
                "ORDER BY p.nombre"
            )

        self.projects = [
            {"id": int(row[0]), "name": row[1]} for row in rows if len(row) >= 2
        ]

        # Seleccionar primer proyecto por defecto
        if self.projects:
            if self.selected_project_id == 0:
                self.selected_project_id = self.projects[0]["id"]

    def _load_versions(self) -> None:
        """Carga versiones del proyecto seleccionado."""
        if self.selected_org_id <= 0 or self.selected_project_id <= 0:
            self.versions = []
            self.selected_version_id = 0
            return

        rows = _run_mysql_query(
            "SELECT v.id_version, ev.state_internal, ev.created_at "
            "FROM versiones v "
            "INNER JOIN estado_version ev "
            "ON v.id_organizacion = ev.id_organizacion "
            "AND v.id_proyecto = ev.id_proyecto "
            "AND v.id_version = ev.id_version "
            f"WHERE v.id_organizacion = {self.selected_org_id} "
            f"AND v.id_proyecto = {self.selected_project_id} "
            "ORDER BY v.id_version DESC"
        )

        self.versions = [
            {
                "version_id": int(row[0]),
                "state_internal": row[1] if len(row) > 1 else "",
                "created_at": row[2] if len(row) > 2 else "",
            }
            for row in rows
            if row
        ]

        # Seleccionar primera versión por defecto
        if self.versions:
            if self.selected_version_id == 0:
                self.selected_version_id = self.versions[0]["version_id"]

    def _load_current_state(self) -> None:
        """Carga el estado completo de la versión seleccionada."""
        if (
            self.selected_org_id <= 0
            or self.selected_project_id <= 0
            or self.selected_version_id <= 0
        ):
            self.current_state = {}
            return

        rows = _run_mysql_query(
            "SELECT "
            "id, state, state_internal, protected, size, "
            "final_c, final_i, "
            "revision_interna, propuesta_mejoras, "
            "entrenamiento_inicial_solicitado, entrenamiento_inicial_completado, "
            "entrenamiento_inicial_fecha, "
            "evaluacion_entrenamiento, reentrenamiento, optimizacion, "
            "control_calidad_aprobado, "
            "generacion_llm_solicitada, generacion_llm_completada, "
            "generacion_llm_fecha, ruta_fichero_modelo, "
            "notificacion_descarga_enviada, notificacion_descarga_fecha, "
            "created_at, updated_at, updated_by "
            "FROM estado_version "
            f"WHERE id_organizacion = {self.selected_org_id} "
            f"AND id_proyecto = {self.selected_project_id} "
            f"AND id_version = {self.selected_version_id} "
            "LIMIT 1"
        )

        if not rows or not rows[0]:
            self.current_state = {}
            return

        row = rows[0]
        self.current_state = {
            "id": int(row[0]) if row[0] else 0,
            "state": row[1] if len(row) > 1 else "",
            "state_internal": row[2] if len(row) > 2 else "",
            "protected": row[3] == "1" if len(row) > 3 else False,
            "size": int(row[4]) if len(row) > 4 and row[4] else 0,
            "final_c": row[5] == "1" if len(row) > 5 else False,
            "final_i": row[6] == "1" if len(row) > 6 else False,
            "revision_interna": row[7] == "1" if len(row) > 7 else False,
            "propuesta_mejoras": row[8] == "1" if len(row) > 8 else False,
            "entrenamiento_inicial_solicitado": row[9] == "1" if len(row) > 9 else False,
            "entrenamiento_inicial_completado": row[10] == "1" if len(row) > 10 else False,
            "entrenamiento_inicial_fecha": row[11] if len(row) > 11 else None,
            "evaluacion_entrenamiento": row[12] == "1" if len(row) > 12 else False,
            "reentrenamiento": row[13] == "1" if len(row) > 13 else False,
            "optimizacion": row[14] == "1" if len(row) > 14 else False,
            "control_calidad_aprobado": row[15] == "1" if len(row) > 15 else False,
            "generacion_llm_solicitada": row[16] == "1" if len(row) > 16 else False,
            "generacion_llm_completada": row[17] == "1" if len(row) > 17 else False,
            "generacion_llm_fecha": row[18] if len(row) > 18 else None,
            "ruta_fichero_modelo": row[19] if len(row) > 19 else None,
            "notificacion_descarga_enviada": row[20] == "1" if len(row) > 20 else False,
            "notificacion_descarga_fecha": row[21] if len(row) > 21 else None,
            "created_at": row[22] if len(row) > 22 else None,
            "updated_at": row[23] if len(row) > 23 else None,
            "updated_by": int(row[24]) if len(row) > 24 and row[24] and row[24] != "NULL" else None,
        }

    # ========================================================================
    # Event handlers - Selección
    # ========================================================================

    def set_organization(self, org_name: str) -> None:
        """Cambia la organización seleccionada."""
        for org in self.organizations:
            if org["name"] == org_name:
                self.selected_org_id = org["id"]
                break

        self.selected_project_id = 0
        self.selected_version_id = 0
        self.current_state = {}

        self._load_projects()
        self._load_versions()
        if self.selected_version_id > 0:
            self._load_current_state()

    def set_project(self, project_name: str) -> None:
        """Cambia el proyecto seleccionado."""
        for proj in self.projects:
            if proj["name"] == project_name:
                self.selected_project_id = proj["id"]
                break

        self.selected_version_id = 0
        self.current_state = {}

        self._load_versions()
        if self.selected_version_id > 0:
            self._load_current_state()

    def set_version(self, version_str: str) -> None:
        """Cambia la versión seleccionada."""
        try:
            self.selected_version_id = int(version_str)
        except ValueError:
            self.selected_version_id = 0

        self._load_current_state()

    # ========================================================================
    # Event handlers - Actualización de estado
    # ========================================================================

    async def toggle_field(self, field_name: str) -> None:
        """Alterna el valor de un campo booleano usando la API."""
        if not self.can_edit:
            self.error_message = "No tienes permisos para editar estados"
            return

        if not self.current_state:
            self.error_message = "No hay versión seleccionada"
            return

        state_id = self.current_state.get("id")
        if not state_id:
            self.error_message = "Estado inválido"
            return

        # Obtener tokens de sesión
        from web_backoffice.shared_state import SharedSessionState

        session_state = await self.get_state(SharedSessionState)
        if not session_state:
            self.error_message = "No se pudo obtener sesión"
            return

        access_token = session_state.access_token
        session_token = session_state.session_token

        try:
            # Mapeo de campos a fases y funciones API
            if field_name in ("final_c", "final_i"):
                # Fase de propuesta
                from adapters.api_client import update_proposal_phase

                final_c = self.current_state.get("final_c", False)
                final_i = self.current_state.get("final_i", False)

                # Alternar el campo específico
                if field_name == "final_c":
                    final_c = not final_c
                else:
                    final_i = not final_i

                result = update_proposal_phase(
                    state_id=state_id,
                    aceptacion_cliente=final_c,
                    aceptacion_interna=final_i,
                    access_token=access_token,
                    session_token=session_token,
                )

            elif field_name == "entrenamiento_inicial_completado":
                # Fase de entrenamiento
                from adapters.api_client import update_training_phase

                current_value = self.current_state.get(field_name, False)
                result = update_training_phase(
                    state_id=state_id,
                    completado=not current_value,
                    access_token=access_token,
                    session_token=session_token,
                )

            elif field_name in (
                "evaluacion",
                "reentrenamiento",
                "optimizacion",
                "control_calidad_aprobado",
            ):
                # Fase de evaluación
                from adapters.api_client import update_evaluation_phase

                evaluacion = self.current_state.get("evaluacion", False)
                reentrenamiento = self.current_state.get("reentrenamiento", False)
                optimizacion = self.current_state.get("optimizacion", False)
                calidad_aprobada = self.current_state.get(
                    "control_calidad_aprobado", False
                )

                # Alternar el campo específico
                if field_name == "evaluacion":
                    evaluacion = not evaluacion
                elif field_name == "reentrenamiento":
                    reentrenamiento = not reentrenamiento
                elif field_name == "optimizacion":
                    optimizacion = not optimizacion
                elif field_name == "control_calidad_aprobado":
                    calidad_aprobada = not calidad_aprobada

                result = update_evaluation_phase(
                    state_id=state_id,
                    evaluacion=evaluacion,
                    reentrenamiento=reentrenamiento,
                    optimizacion=optimizacion,
                    calidad_aprobada=calidad_aprobada,
                    access_token=access_token,
                    session_token=session_token,
                )

            elif field_name == "generacion_llm_completada":
                # Fase de generación
                from adapters.api_client import update_generation_phase

                current_value = self.current_state.get(field_name, False)
                result = update_generation_phase(
                    state_id=state_id,
                    generacion_completada=not current_value,
                    access_token=access_token,
                    session_token=session_token,
                )

            elif field_name == "notificacion_descarga_enviada":
                # Fase de notificación
                from adapters.api_client import update_notification_phase

                current_value = self.current_state.get(field_name, False)
                result = update_notification_phase(
                    state_id=state_id,
                    notificacion_enviada=not current_value,
                    access_token=access_token,
                    session_token=session_token,
                )

            else:
                self.error_message = f"Campo {field_name} no soportado"
                return

            # Verificar resultado
            if result.get("success"):
                self.success_message = f"Campo {field_name} actualizado correctamente"
                self._load_current_state()  # Recargar para ver cambios de triggers
            else:
                detail = result.get("detail", "Error desconocido")
                self.error_message = f"Error al actualizar: {detail}"

        except Exception as e:
            self.error_message = f"Error en la actualización: {str(e)}"

    def clear_messages(self) -> None:
        """Limpia mensajes de error/éxito."""
        self.error_message = ""
        self.success_message = ""

    async def on_page_load(self) -> None:
        """Se ejecuta cuando se carga la página."""
        # Obtener datos de sesión desde SharedSessionState
        from web_backoffice.shared_state import SharedSessionState

        # Inicializar con datos de sesión
        session_state = await self.get_state(SharedSessionState)
        if session_state:
            self.initialize_from_session(
                user_id=session_state.user_id,
                organization_id=session_state.organization_id,
                identity_type_id=session_state.identity_type_id,
            )


# ============================================================================
# Componentes UI
# ============================================================================


def estado_proyectos_panel() -> rx.Component:
    """Panel principal de gestión de estados de versiones."""
    return rx.vstack(
        # Header
        rx.heading(
            "Estado de Proyectos",
            size="8",
            color="#f97316",
            margin_bottom="0.5em",
        ),
        rx.text(
            "Gestión completa del ciclo de vida de versiones de proyectos",
            color="#94a3b8",
            font_size="1.1em",
            margin_bottom="1.5em",
        ),

        # Selectores
        rx.hstack(
            rx.vstack(
                rx.text("Organización", font_size="1em", color="#f97316", font_weight="600"),
                rx.select(
                    EstadoProyectosState.organization_names,
                    on_change=EstadoProyectosState.set_organization,
                    placeholder="Seleccione organización",
                    width="100%",
                    size="3",
                ),
                spacing="1",
                width="33%",
            ),
            rx.vstack(
                rx.text("Proyecto", font_size="1em", color="#f97316", font_weight="600"),
                rx.select(
                    EstadoProyectosState.project_names,
                    on_change=EstadoProyectosState.set_project,
                    placeholder="Seleccione proyecto",
                    width="100%",
                    size="3",
                ),
                spacing="1",
                width="33%",
            ),
            rx.vstack(
                rx.text("Versión", font_size="1em", color="#f97316", font_weight="600"),
                rx.select(
                    EstadoProyectosState.version_numbers,
                    value=EstadoProyectosState.selected_version_display,
                    on_change=EstadoProyectosState.set_version,
                    placeholder="Seleccione versión",
                    width="100%",
                    size="3",
                ),
                spacing="1",
                width="33%",
            ),
            spacing="3",
            width="100%",
            margin_bottom="2em",
        ),

        # Mensajes
        rx.cond(
            EstadoProyectosState.error_message != "",
            rx.callout(
                EstadoProyectosState.error_message,
                icon="triangle_alert",
                color_scheme="red",
                size="2",
                on_click=EstadoProyectosState.clear_messages,
            ),
        ),
        rx.cond(
            EstadoProyectosState.success_message != "",
            rx.callout(
                EstadoProyectosState.success_message,
                icon="check",
                color_scheme="green",
                size="2",
                on_click=EstadoProyectosState.clear_messages,
            ),
        ),

        # Estado actual
        rx.cond(
            EstadoProyectosState.selected_version_id > 0,
            rx.vstack(
                # Resumen
                _estado_summary_card(),

                # Fases
                _fase_1_card(),
                _fase_2_card(),
                _fase_3_card(),
                _fase_4_card(),
                _fase_5_card(),

                spacing="3",
                width="100%",
            ),
        ),

        spacing="3",
        width="100%",
        padding="2em",
        on_mount=EstadoProyectosState.on_page_load,
    )


def _estado_summary_card() -> rx.Component:
    """Tarjeta con resumen del estado."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.heading("Resumen de Estado", size="6", color="#f97316"),
                rx.badge(
                    EstadoProyectosState.state_internal_display,
                    color_scheme="blue",
                    size="3",
                ),
                justify="between",
                width="100%",
            ),
            rx.divider(),
            rx.hstack(
                rx.vstack(
                    rx.text("Progreso", font_size="1em", color="#94a3b8"),
                    rx.text(
                        f"{EstadoProyectosState.progress_percentage:.0f}%",
                        font_size="2em",
                        font_weight="bold",
                        color="#22c55e",
                    ),
                    spacing="1",
                ),
                rx.box(
                    rx.progress(
                        value=EstadoProyectosState.progress_percentage.to(int),
                        width="100%",
                        color_scheme="green",
                        size="3",
                    ),
                    width="70%",
                ),
                spacing="4",
                align="center",
                width="100%",
            ),
            spacing="3",
        ),
        padding="1.5em",
        background="#1e293b",
        border_radius="8px",
        border="1px solid #334155",
        width="100%",
        max_width="1800px",
    )


def _fase_1_card() -> rx.Component:
    """Tarjeta de Fase 1: Propuesta/Revisión."""
    return rx.box(
        rx.vstack(
            rx.heading("Fase 1: Propuesta y Revisión", size="5", color="#f97316"),
            rx.divider(),
            rx.grid(
                _toggle_field("revision_interna", "Revisión Interna", "🔍"),
                _toggle_field("propuesta_mejoras", "Propuesta de Mejoras", "⚙️"),
                columns="2",
                spacing="3",
                width="100%",
            ),
            rx.divider(),
            rx.hstack(
                rx.badge(
                    "Aceptación Cliente",
                    color_scheme=rx.cond(
                        EstadoProyectosState.current_state["final_c"],
                        "green",
                        "gray",
                    ),
                    size="3",
                ),
                rx.switch(
                    checked=EstadoProyectosState.current_state["final_c"],
                    on_change=lambda _: EstadoProyectosState.toggle_field("final_c"),
                    disabled=~EstadoProyectosState.can_edit,
                ),
                rx.badge(
                    "Aceptación Interna",
                    color_scheme=rx.cond(
                        EstadoProyectosState.current_state["final_i"],
                        "green",
                        "gray",
                    ),
                    size="3",
                ),
                rx.switch(
                    checked=EstadoProyectosState.current_state["final_i"],
                    on_change=lambda _: EstadoProyectosState.toggle_field("final_i"),
                    disabled=~EstadoProyectosState.can_edit,
                ),
                spacing="4",
                width="100%",
            ),
            spacing="3",
        ),
        padding="1.5em",
        background="#1e293b",
        border_radius="8px",
        border="1px solid #334155",
        width="100%",
        max_width="1800px",
    )


def _fase_2_card() -> rx.Component:
    """Tarjeta de Fase 2: Entrenamiento."""
    return rx.box(
        rx.vstack(
            rx.heading("Fase 2: Entrenamiento Inicial", size="5", color="#f97316"),
            rx.divider(),
            rx.hstack(
                rx.badge(
                    "Solicitado",
                    color_scheme=rx.cond(
                        EstadoProyectosState.current_state["entrenamiento_inicial_solicitado"],
                        "blue",
                        "gray",
                    ),
                    size="3",
                ),
                rx.text(
                    "(Automático con doble aceptación)",
                    font_size="1em",
                    color="#64748b",
                ),
                spacing="2",
            ),
            _toggle_field(
                "entrenamiento_inicial_completado", "Entrenamiento Completado", "✅"
            ),
            rx.cond(
                EstadoProyectosState.current_state.get("entrenamiento_inicial_fecha")
                != None,
                rx.text(
                    f"Completado: {EstadoProyectosState.current_state.get('entrenamiento_inicial_fecha', '')}",
                    font_size="1em",
                    color="#94a3b8",
                ),
            ),
            spacing="3",
        ),
        padding="1.5em",
        background="#1e293b",
        border_radius="8px",
        border="1px solid #334155",
        width="100%",
        max_width="1800px",
    )


def _fase_3_card() -> rx.Component:
    """Tarjeta de Fase 3: Evaluación."""
    return rx.box(
        rx.vstack(
            rx.heading("Fase 3: Evaluación y Reentrenamiento", size="5", color="#f97316"),
            rx.divider(),
            rx.grid(
                _toggle_field("evaluacion_entrenamiento", "Evaluación", "📊"),
                _toggle_field("reentrenamiento", "Reentrenamiento", "🔄"),
                _toggle_field("optimizacion", "Optimización", "⚡"),
                _toggle_field("control_calidad_aprobado", "Calidad Aprobada", "✅"),
                columns="2",
                spacing="3",
                width="100%",
            ),
            spacing="3",
        ),
        padding="1.5em",
        background="#1e293b",
        border_radius="8px",
        border="1px solid #334155",
        width="100%",
        max_width="1800px",
    )


def _fase_4_card() -> rx.Component:
    """Tarjeta de Fase 4: Generación."""
    return rx.box(
        rx.vstack(
            rx.heading("Fase 4: Generación del Modelo LLM", size="5", color="#f97316"),
            rx.divider(),
            _toggle_field("generacion_llm_solicitada", "Generación Solicitada", "🤖"),
            _toggle_field("generacion_llm_completada", "Generación Completada", "✅"),
            rx.cond(
                EstadoProyectosState.current_state.get("generacion_llm_fecha") != None,
                rx.text(
                    f"Completado: {EstadoProyectosState.current_state.get('generacion_llm_fecha', '')}",
                    font_size="1em",
                    color="#94a3b8",
                ),
            ),
            rx.cond(
                EstadoProyectosState.current_state.get("ruta_fichero_modelo") != None,
                rx.text(
                    f"Fichero: {EstadoProyectosState.current_state.get('ruta_fichero_modelo', '')}",
                    font_size="1em",
                    color="#94a3b8",
                ),
            ),
            spacing="3",
        ),
        padding="1.5em",
        background="#1e293b",
        border_radius="8px",
        border="1px solid #334155",
        width="100%",
        max_width="1800px",
    )


def _fase_5_card() -> rx.Component:
    """Tarjeta de Fase 5: Notificación."""
    return rx.box(
        rx.vstack(
            rx.heading("Fase 5: Notificación de Descarga", size="5", color="#f97316"),
            rx.divider(),
            _toggle_field(
                "notificacion_descarga_enviada", "Notificación Enviada", "🔔"
            ),
            rx.cond(
                EstadoProyectosState.current_state.get("notificacion_descarga_fecha")
                != None,
                rx.text(
                    f"Enviado: {EstadoProyectosState.current_state.get('notificacion_descarga_fecha', '')}",
                    font_size="1em",
                    color="#94a3b8",
                ),
            ),
            spacing="3",
        ),
        padding="1.5em",
        background="#1e293b",
        border_radius="8px",
        border="1px solid #334155",
        width="100%",
        max_width="1800px",
    )


def _toggle_field(field_name: str, label: str, emoji: str) -> rx.Component:
    """Campo con switch para alternar valor booleano."""
    return rx.hstack(
        rx.text(emoji, font_size="1.5em"),
        rx.text(label, font_size="1.1em", color="#e2e8f0"),
        rx.spacer(),
        rx.switch(
            checked=EstadoProyectosState.current_state.get(field_name, False),
            on_change=lambda _: EstadoProyectosState.toggle_field(field_name),
            disabled=~EstadoProyectosState.can_edit,
        ),
        spacing="2",
        align="center",
        padding="0.8em",
        background="#0f172a",
        border_radius="6px",
        border="1px solid #1e293b",
        width="100%",
    )
