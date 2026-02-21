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

Arquitectura:
- Flujo: Backoffice → Middleware (8007) → Broker (8008) → Backend Core (8003) → MariaDB
- Usa API client (adapters/api_client.py) para todas las consultas
- No accede directamente a la base de datos
"""

from typing import Any, AsyncGenerator

import logging

import reflex as rx


logger = logging.getLogger("backoffice")


# ============================================================================
# Estado de la página
# ============================================================================


class EstadoProyectosState(rx.State):
    """Estado de la página de gestión de estados de versiones."""

    # Contexto de usuario
    user_id: int = 0
    organization_id: int = 0
    identity_type_id: int = 0

    # Tokens de sesión para API
    access_token: str = ""
    session_token: str = ""

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

    def ep_receive_data(
        self,
        user_id: int,
        organization_id: int,
        identity_type_id: int,
        access_token: str,
        session_token: str,
        organizations: list,
        selected_org_id: int,
        projects: list,
        selected_project_id: int,
        versions: list,
        selected_version_id: int,
        current_state: dict,
    ) -> None:
        """Recibe todos los datos precargados desde el main State.

        Llamado como evento encadenado desde State.ep_init_page().
        Los datos ya fueron cargados via API en el main State (con tokens disponibles).
        """
        self.user_id = user_id
        self.organization_id = organization_id
        self.identity_type_id = identity_type_id
        self.access_token = access_token
        self.session_token = session_token
        self.organizations = organizations
        self.selected_org_id = selected_org_id
        self.projects = projects
        self.selected_project_id = selected_project_id
        self.versions = versions
        self.selected_version_id = selected_version_id
        self.current_state = current_state
        print(f"[EP] ep_receive_data: orgs={len(organizations)}, projects={len(projects)}, versions={len(versions)}, state={'SET' if current_state else 'EMPTY'}")

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
    def selected_org_display(self) -> str:
        """Organización seleccionada para mostrar."""
        if self.selected_org_id > 0:
            for org in self.organizations:
                if org["id"] == self.selected_org_id:
                    return org["name"]
        return ""

    @rx.var
    def selected_project_display(self) -> str:
        """Proyecto seleccionado para mostrar."""
        if self.selected_project_id > 0:
            for proj in self.projects:
                if proj["id"] == self.selected_project_id:
                    return proj["name"]
        return ""

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

    async def _load_organizations(self) -> None:
        """Carga organizaciones via API (Middleware → Broker → Backend)."""
        async with self:
            organization_id = self.organization_id
            selected_org_id = self.selected_org_id
            access_token = self.access_token
            session_token = self.session_token

        logger.info("[ESTADO-PRJ] _load_organizations | tokens=%s", "SET" if access_token else "EMPTY")
        print(f"[DEBUG ESTADO_PROYECTOS] _load_organizations: access_token={'SET' if access_token else 'EMPTY'}, session_token={'SET' if session_token else 'EMPTY'}")

        try:
            from adapters.api_client import get_all_organizations

            orgs_data = get_all_organizations(
                access_token=access_token,
                session_token=session_token,
            )
            print(f"[DEBUG ESTADO_PROYECTOS] _load_organizations: API returned {len(orgs_data)} orgs")
            if orgs_data:
                print(f"[DEBUG ESTADO_PROYECTOS] _load_organizations: first org: {orgs_data[0]}")
        except Exception as e:
            logger.error("[ESTADO-PRJ] _load_organizations error: %s", e)
            print(f"[DEBUG ESTADO_PROYECTOS] _load_organizations: EXCEPTION: {e}")
            orgs_data = []

        organizations = [
            {
                "id": int(org.get("organization_id", org.get("id", 0))),
                "name": org.get("organization_name", org.get("name", "")),
            }
            for org in orgs_data
            if org.get("organization_id", org.get("id", 0))
        ]

        # Seleccionar organización por defecto
        if organizations:
            if selected_org_id == 0:
                if organization_id > 0:
                    selected_org_id = organization_id
                else:
                    selected_org_id = organizations[0]["id"]

        async with self:
            self.organizations = organizations
            if selected_org_id > 0:
                self.selected_org_id = selected_org_id

    async def _load_projects(self) -> None:
        """Carga proyectos via API (Middleware → Broker → Backend)."""
        async with self:
            org_id = self.selected_org_id
            access_token = self.access_token
            session_token = self.session_token

        if org_id <= 0:
            async with self:
                self.projects = []
                self.selected_project_id = 0
            return

        try:
            from adapters.api_client import get_organization_projects

            projects_data = get_organization_projects(
                organization_id=org_id,
                access_token=access_token,
                session_token=session_token,
                include_deleted=False,
            )
        except Exception as e:
            logger.error("[ESTADO-PRJ] _load_projects error: %s", e)
            projects_data = []

        projects = [
            {
                "id": int(p.get("id", 0)),
                "name": p.get("name", p.get("nombre", "")),
            }
            for p in projects_data
            if p.get("active", True) and p.get("existe", True)
        ]

        async with self:
            self.projects = projects

            # Seleccionar primer proyecto por defecto
            if projects:
                if self.selected_project_id == 0:
                    self.selected_project_id = projects[0]["id"]

    async def _load_versions(self) -> None:
        """Carga versiones via API (Middleware → Broker → Backend)."""
        async with self:
            org_id = self.selected_org_id
            project_id = self.selected_project_id
            access_token = self.access_token
            session_token = self.session_token

        if org_id <= 0 or project_id <= 0:
            async with self:
                self.versions = []
                self.selected_version_id = 0
            return

        try:
            from adapters.api_client import get_project_versions

            result = get_project_versions(
                project_id=project_id,
                organization_id=org_id,
                access_token=access_token,
                session_token=session_token,
            )
            versions_data = result.get("versiones", [])
        except Exception as e:
            logger.error("[ESTADO-PRJ] _load_versions error: %s", e)
            versions_data = []

        versions = [
            {
                "version_id": int(v.get("id_version", 0)),
                "state_internal": v.get("state_internal", ""),
                "created_at": v.get("created_at", ""),
            }
            for v in versions_data
            if v.get("id_version", 0)
        ]

        async with self:
            self.versions = versions
            if self.versions and self.selected_version_id == 0:
                self.selected_version_id = self.versions[0]["version_id"]

    async def _load_current_state(self) -> None:
        """Carga estado de versión via API (Middleware → Broker → Backend)."""
        async with self:
            project_id = self.selected_project_id
            version_id = self.selected_version_id

        # Obtener tokens frescos desde SharedSessionState
        from web_backoffice.shared_state import SharedSessionState

        async with self:
            session_state = await self.get_state(SharedSessionState)

        if session_state and session_state.access_token:
            access_token = session_state.access_token
            session_token = session_state.session_token
        else:
            # Fallback a tokens de la página
            async with self:
                access_token = self.access_token
                session_token = self.session_token

        if project_id <= 0 or version_id <= 0:
            async with self:
                self.current_state = {}
            return

        try:
            from adapters.api_client import get_version_state

            result = get_version_state(
                project_id=project_id,
                version_id=version_id,
                access_token=access_token,
                session_token=session_token,
            )
        except Exception as e:
            logger.error("[ESTADO-PRJ] _load_current_state error: %s", e)
            async with self:
                self.current_state = {}
            return

        if not result.get("success") and not result.get("data"):
            async with self:
                self.current_state = {}
            return

        state = result.get("data", result.get("state", result))

        # Normalizar booleanos (la API puede devolver bool o int/str)
        def to_bool(val: Any) -> bool:
            if isinstance(val, bool):
                return val
            if isinstance(val, int):
                return val == 1
            if isinstance(val, str):
                return val in ("1", "true", "True")
            return False

        state_data = {
            "id": int(state.get("id", 0)),
            "state": state.get("state", ""),
            "state_internal": state.get("state_internal", ""),
            "protected": to_bool(state.get("protected", False)),
            "size": int(state.get("size", 0)),
            "final_c": to_bool(state.get("final_c", False)),
            "final_i": to_bool(state.get("final_i", False)),
            "revision_interna": to_bool(state.get("revision_interna", False)),
            "propuesta_mejoras": to_bool(state.get("propuesta_mejoras", False)),
            "entrenamiento_inicial_solicitado": to_bool(state.get("entrenamiento_inicial_solicitado", False)),
            "entrenamiento_inicial_completado": to_bool(state.get("entrenamiento_inicial_completado", False)),
            "entrenamiento_inicial_fecha": state.get("entrenamiento_inicial_fecha"),
            "evaluacion_entrenamiento": to_bool(state.get("evaluacion_entrenamiento", False)),
            "reentrenamiento": to_bool(state.get("reentrenamiento", False)),
            "optimizacion": to_bool(state.get("optimizacion", False)),
            "control_calidad_aprobado": to_bool(state.get("control_calidad_aprobado", False)),
            "generacion_llm_solicitada": to_bool(state.get("generacion_llm_solicitada", False)),
            "generacion_llm_completada": to_bool(state.get("generacion_llm_completada", False)),
            "generacion_llm_fecha": state.get("generacion_llm_fecha"),
            "ruta_fichero_modelo": state.get("ruta_fichero_modelo"),
            "notificacion_descarga_enviada": to_bool(state.get("notificacion_descarga_enviada", False)),
            "notificacion_descarga_fecha": state.get("notificacion_descarga_fecha"),
            "created_at": state.get("created_at"),
            "updated_at": state.get("updated_at"),
            "updated_by": int(state["updated_by"]) if state.get("updated_by") else None,
        }

        async with self:
            self.current_state = state_data

    # ========================================================================
    # Event handlers - Selección
    # ========================================================================

    @rx.event(background=True)
    async def set_organization(self, org_name: str) -> AsyncGenerator[None, None]:
        """Cambia la organización seleccionada."""
        async with self:
            org_id = 0
            for org in self.organizations:
                if org["name"] == org_name:
                    org_id = org["id"]
                    break

            logger.info("[ESTADO-PRJ] set_organization | org_name=%s, org_id=%d", org_name, org_id)
            self.selected_org_id = org_id
            self.selected_project_id = 0
            self.selected_version_id = 0
            self.current_state = {}
        yield

        await self._load_projects()
        yield
        await self._load_versions()
        yield

        async with self:
            version_id = self.selected_version_id

        if version_id > 0:
            await self._load_current_state()
            yield

    @rx.event(background=True)
    async def set_project(self, project_name: str) -> AsyncGenerator[None, None]:
        """Cambia el proyecto seleccionado."""
        async with self:
            project_id = 0
            for proj in self.projects:
                if proj["name"] == project_name:
                    project_id = proj["id"]
                    break

            logger.info("[ESTADO-PRJ] set_project | project_name=%s, project_id=%d", project_name, project_id)
            self.selected_project_id = project_id
            self.selected_version_id = 0
            self.current_state = {}
        yield

        await self._load_versions()
        yield

        async with self:
            version_id = self.selected_version_id

        if version_id > 0:
            await self._load_current_state()

    @rx.event(background=True)
    async def set_version(self, version_str: str) -> AsyncGenerator[None, None]:
        """Cambia la versión seleccionada."""
        try:
            version_id = int(version_str)
        except ValueError:
            version_id = 0

        logger.info("[ESTADO-PRJ] set_version | version_id=%d", version_id)
        async with self:
            self.selected_version_id = version_id
        yield

        await self._load_current_state()
        yield

    # ========================================================================
    # Event handlers - Toggle con feedback visual inmediato
    # ========================================================================
    # Cada handler es un único background event que:
    # 1. Actualiza current_state y hace yield (feedback visual inmediato)
    # 2. Llama a la API con el valor explícito (no depende del snapshot)
    # 3. Recarga desde BD para recoger cambios de triggers
    # Sin encadenamiento de eventos (evita problemas de propagación de estado).

    @rx.event(background=True)
    async def toggle_revision_interna(
        self, value: bool
    ) -> AsyncGenerator[None, None]:
        """Toggle revision_interna con feedback visual inmediato."""
        # 1. Feedback visual inmediato
        async with self:
            self.current_state = {**self.current_state, "revision_interna": value}
        yield

        # 2. Persistir en BD
        await self._persist_proposal_field("revision_interna", value)
        yield

    @rx.event(background=True)
    async def toggle_propuesta_mejoras(
        self, value: bool
    ) -> AsyncGenerator[None, None]:
        """Toggle propuesta_mejoras con feedback visual inmediato."""
        async with self:
            self.current_state = {**self.current_state, "propuesta_mejoras": value}
        yield

        await self._persist_proposal_field("propuesta_mejoras", value)
        yield

    @rx.event(background=True)
    async def toggle_generacion_solicitada(
        self, value: bool
    ) -> AsyncGenerator[None, None]:
        """Toggle generacion_llm_solicitada con feedback visual inmediato."""
        async with self:
            self.current_state = {
                **self.current_state,
                "generacion_llm_solicitada": value,
            }
        yield

        await self._persist_generation_field(value)
        yield

    async def _persist_proposal_field(
        self, field_name: str, new_value: bool
    ) -> None:
        """Persiste un campo de fase propuesta en BD (método interno, no event handler).

        Lee current_state para los campos no modificados y usa new_value
        para el campo que se acaba de cambiar.
        """
        async with self:
            can_edit = self.can_edit
            current_state = self.current_state.copy()

        if not can_edit or not current_state:
            return

        state_id = current_state.get("id")
        if not state_id:
            return

        from web_backoffice.shared_state import SharedSessionState

        async with self:
            session_state = await self.get_state(SharedSessionState)

        if not session_state:
            return

        access_token = session_state.access_token
        session_token = session_state.session_token

        # Construir valores: usar new_value para el campo modificado,
        # current_state para los demás
        field_values = {
            "final_c": current_state.get("final_c", False),
            "final_i": current_state.get("final_i", False),
            "revision_interna": current_state.get("revision_interna", False),
            "propuesta_mejoras": current_state.get("propuesta_mejoras", False),
        }
        field_values[field_name] = new_value

        try:
            from adapters.api_client import update_proposal_phase

            result = update_proposal_phase(
                state_id=state_id,
                aceptacion_cliente=field_values["final_c"],
                aceptacion_interna=field_values["final_i"],
                access_token=access_token,
                session_token=session_token,
                revision_interna=field_values["revision_interna"],
                propuesta_mejoras=field_values["propuesta_mejoras"],
            )

            if result.get("success"):
                async with self:
                    self.success_message = f"Campo {field_name} actualizado"
                await self._load_current_state()
            else:
                detail = result.get("detail", "Error desconocido")
                async with self:
                    self.error_message = f"Error al actualizar: {detail}"
                await self._load_current_state()

        except Exception as e:
            logger.error(
                "Exception al persistir %s: %s", field_name, e
            )
            async with self:
                self.error_message = f"Error: {str(e)}"
            await self._load_current_state()

    async def _persist_generation_field(self, new_value: bool) -> None:
        """Persiste generacion_llm_solicitada en BD (método interno)."""
        async with self:
            can_edit = self.can_edit
            current_state = self.current_state.copy()

        if not can_edit or not current_state:
            return

        state_id = current_state.get("id")
        if not state_id:
            return

        from web_backoffice.shared_state import SharedSessionState

        async with self:
            session_state = await self.get_state(SharedSessionState)

        if not session_state:
            return

        access_token = session_state.access_token
        session_token = session_state.session_token

        try:
            from adapters.api_client import update_generation_phase

            result = update_generation_phase(
                state_id=state_id,
                access_token=access_token,
                session_token=session_token,
                generacion_solicitada=new_value,
            )

            if result.get("success"):
                async with self:
                    self.success_message = "Generación solicitada actualizada"
                await self._load_current_state()
            else:
                detail = result.get("detail", "Error desconocido")
                async with self:
                    self.error_message = f"Error al actualizar: {detail}"
                await self._load_current_state()

        except Exception as e:
            async with self:
                self.error_message = f"Error: {str(e)}"
            await self._load_current_state()

    # ========================================================================
    # Event handlers - Toggle genérico con inversión (legacy)
    # ========================================================================

    @rx.event(background=True)
    async def toggle_field(self, field_name: str) -> AsyncGenerator[None, None]:
        """Alterna el valor de un campo booleano usando la API."""
        logger.info("[ESTADO-PRJ] toggle_field | field=%s", field_name)
        async with self:
            can_edit = self.can_edit
            current_state = self.current_state.copy()

        if not can_edit:
            async with self:
                self.error_message = "No tienes permisos para editar estados"
            return

        if not current_state:
            async with self:
                self.error_message = "No hay versión seleccionada"
            return

        state_id = current_state.get("id")
        if not state_id:
            async with self:
                self.error_message = "Estado inválido"
            return

        # Feedback visual inmediato: invertir el valor del campo en el state
        current_value = current_state.get(field_name, False)
        new_value = not current_value
        async with self:
            self.current_state = {**current_state, field_name: new_value}
        yield

        # Obtener tokens de sesión
        from web_backoffice.shared_state import SharedSessionState

        async with self:
            session_state = await self.get_state(SharedSessionState)

        if not session_state:
            async with self:
                self.error_message = "No se pudo obtener sesión"
                self.current_state = current_state  # Revertir
            yield
            return

        access_token = session_state.access_token
        session_token = session_state.session_token

        try:
            # Mapeo de campos a fases y funciones API
            # Usar new_value (ya calculado arriba) para el campo que cambió
            # y current_state para los campos que no cambiaron
            if field_name in ("final_c", "final_i", "revision_interna", "propuesta_mejoras"):
                # Fase de propuesta - enviar todos los campos juntos
                from adapters.api_client import update_proposal_phase

                proposal_vals = {
                    "final_c": current_state.get("final_c", False),
                    "final_i": current_state.get("final_i", False),
                    "revision_interna": current_state.get("revision_interna", False),
                    "propuesta_mejoras": current_state.get("propuesta_mejoras", False),
                }
                proposal_vals[field_name] = new_value

                result = update_proposal_phase(
                    state_id=state_id,
                    aceptacion_cliente=proposal_vals["final_c"],
                    aceptacion_interna=proposal_vals["final_i"],
                    access_token=access_token,
                    session_token=session_token,
                    revision_interna=proposal_vals["revision_interna"],
                    propuesta_mejoras=proposal_vals["propuesta_mejoras"],
                )

            elif field_name == "entrenamiento_inicial_completado":
                from adapters.api_client import update_training_phase

                result = update_training_phase(
                    state_id=state_id,
                    completado=new_value,
                    access_token=access_token,
                    session_token=session_token,
                )

            elif field_name in (
                "evaluacion_entrenamiento",
                "reentrenamiento",
                "optimizacion",
                "control_calidad_aprobado",
            ):
                # Fase de evaluación - enviar todos los 4 campos juntos
                from adapters.api_client import update_evaluation_phase

                eval_vals = {
                    "evaluacion_entrenamiento": current_state.get("evaluacion_entrenamiento", False),
                    "reentrenamiento": current_state.get("reentrenamiento", False),
                    "optimizacion": current_state.get("optimizacion", False),
                    "control_calidad_aprobado": current_state.get("control_calidad_aprobado", False),
                }
                eval_vals[field_name] = new_value

                result = update_evaluation_phase(
                    state_id=state_id,
                    evaluacion=eval_vals["evaluacion_entrenamiento"],
                    reentrenamiento=eval_vals["reentrenamiento"],
                    optimizacion=eval_vals["optimizacion"],
                    calidad_aprobada=eval_vals["control_calidad_aprobado"],
                    access_token=access_token,
                    session_token=session_token,
                )

            elif field_name == "generacion_llm_completada":
                from adapters.api_client import update_generation_phase

                result = update_generation_phase(
                    state_id=state_id,
                    generacion_completada=new_value,
                    access_token=access_token,
                    session_token=session_token,
                )

            elif field_name == "generacion_llm_solicitada":
                from adapters.api_client import update_generation_phase

                result = update_generation_phase(
                    state_id=state_id,
                    access_token=access_token,
                    session_token=session_token,
                    generacion_solicitada=new_value,
                )

            elif field_name == "notificacion_descarga_enviada":
                from adapters.api_client import update_notification_phase

                result = update_notification_phase(
                    state_id=state_id,
                    notificacion_enviada=new_value,
                    access_token=access_token,
                    session_token=session_token,
                )

            else:
                async with self:
                    self.error_message = f"Campo {field_name} no soportado"
                    self.current_state = current_state  # Revertir
                yield
                return

            # Verificar resultado y recargar desde BD
            if result.get("success"):
                await self._load_current_state()  # Recargar para ver cambios de triggers
                yield
            else:
                detail = result.get("detail", result.get("error", "Error desconocido"))
                logger.error("[ESTADO-PRJ] toggle_field error | field=%s, result=%s", field_name, result)
                print(f"[EP] toggle_field ERROR: field={field_name} result={result}")
                async with self:
                    self.error_message = f"Error al actualizar {field_name}: {detail}"
                    self.current_state = current_state  # Revertir al estado anterior
                yield

        except Exception as e:
            logger.error("[ESTADO-PRJ] toggle_field exception | field=%s: %s", field_name, e)
            print(f"[EP] toggle_field EXCEPTION: field={field_name} error={e}")
            async with self:
                self.error_message = f"Error en la actualización: {str(e)}"
                self.current_state = current_state  # Revertir al estado anterior
            yield

    def clear_messages(self) -> None:
        """Limpia mensajes de error/éxito."""
        self.error_message = ""
        self.success_message = ""

    @rx.event(background=True)
    async def on_page_load(self) -> AsyncGenerator[None, None]:
        """Carga datos iniciales via API.

        Los tokens y datos de sesión deben estar ya en el state
        (puestos por init_from_main_state desde set_internal_menu).
        """
        logger.info("[ESTADO-PRJ] on_page_load")
        async with self:
            has_user = self.user_id > 0
            has_tokens = bool(self.access_token)
            print(f"[DEBUG ESTADO_PROYECTOS] on_page_load: user_id={self.user_id}, has_tokens={has_tokens}")

        if not has_user or not has_tokens:
            # Fallback: intentar obtener tokens de SharedSessionState
            from web_backoffice.shared_state import SharedSessionState

            async with self:
                session_state = await self.get_state(SharedSessionState)
                if session_state and session_state.access_token:
                    self.user_id = session_state.user_id
                    self.organization_id = session_state.organization_id
                    self.identity_type_id = session_state.identity_type_id
                    self.access_token = session_state.access_token
                    self.session_token = session_state.session_token
                    has_user = self.user_id > 0
                    has_tokens = bool(self.access_token)
                    print(f"[DEBUG ESTADO_PROYECTOS] on_page_load fallback: user_id={self.user_id}, has_tokens={has_tokens}")
            yield

        if not has_user or not has_tokens:
            print("[DEBUG ESTADO_PROYECTOS] on_page_load: no user/tokens, skipping load")
            return

        # Cargar datos iniciales
        await self._load_organizations()
        yield

        await self._load_projects()
        yield

        await self._load_versions()
        yield

        await self._load_current_state()
        yield


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
            color="#FF8C00",
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
                rx.text("Organización", font_size="1.1em", color="#FF8C00", font_weight="bold"),
                rx.select(
                    EstadoProyectosState.organization_names,
                    value=EstadoProyectosState.selected_org_display,
                    on_change=EstadoProyectosState.set_organization,
                    placeholder="Seleccione organización",
                    width="100%",
                    size="3",
                    style={"backgroundColor": "#3a3a3a", "color": "#f2f2f5", "borderColor": "#555"},
                ),
                spacing="1",
                width="33%",
            ),
            rx.vstack(
                rx.text("Proyecto", font_size="1.1em", color="#FF8C00", font_weight="bold"),
                rx.select(
                    EstadoProyectosState.project_names,
                    value=EstadoProyectosState.selected_project_display,
                    on_change=EstadoProyectosState.set_project,
                    placeholder="Seleccione proyecto",
                    width="100%",
                    size="3",
                    style={"backgroundColor": "#3a3a3a", "color": "#f2f2f5", "borderColor": "#555"},
                ),
                spacing="1",
                width="33%",
            ),
            rx.vstack(
                rx.text("Versión", font_size="1.1em", color="#FF8C00", font_weight="bold"),
                rx.select(
                    EstadoProyectosState.version_numbers,
                    value=EstadoProyectosState.selected_version_display,
                    on_change=EstadoProyectosState.set_version,
                    placeholder="Seleccione versión",
                    width="100%",
                    size="3",
                    style={"backgroundColor": "#3a3a3a", "color": "#f2f2f5", "borderColor": "#555"},
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
                rx.heading("Resumen de Estado", size="6", color="#FF8C00"),
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
            rx.heading("Fase 1: Propuesta y Revisión", size="5", color="#FF8C00"),
            rx.divider(),
            rx.hstack(
                rx.badge(
                    "Revisión Interna",
                    background="#f97316",
                    color="#000000",
                    font_weight="bold",
                    size="3",
                ),
                rx.switch(
                    checked=EstadoProyectosState.current_state["revision_interna"],
                    on_change=EstadoProyectosState.toggle_revision_interna,
                    disabled=~EstadoProyectosState.can_edit,
                ),
                rx.badge(
                    "Propuesta de Mejoras",
                    background="#f97316",
                    color="#000000",
                    font_weight="bold",
                    size="3",
                ),
                rx.switch(
                    checked=EstadoProyectosState.current_state["propuesta_mejoras"],
                    on_change=EstadoProyectosState.toggle_propuesta_mejoras,
                    disabled=~EstadoProyectosState.can_edit,
                ),
                spacing="4",
                width="100%",
            ),
            rx.divider(),
            rx.hstack(
                rx.badge(
                    "Aceptación Cliente",
                    background="#f97316",
                    color="#000000",
                    font_weight="bold",
                    size="3",
                ),
                rx.switch(
                    checked=EstadoProyectosState.current_state["final_c"],
                    on_change=lambda _: EstadoProyectosState.toggle_field("final_c"),
                    disabled=~EstadoProyectosState.can_edit,
                ),
                rx.badge(
                    "Aceptación Interna",
                    background="#f97316",
                    color="#000000",
                    font_weight="bold",
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
            rx.heading("Fase 2: Entrenamiento Inicial", size="5", color="#FF8C00"),
            rx.divider(),
            rx.hstack(
                rx.badge(
                    "Solicitado",
                    background="#f97316",
                    color="#000000",
                    font_weight="bold",
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
            rx.heading("Fase 3: Evaluación y Reentrenamiento", size="5", color="#FF8C00"),
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
            rx.heading("Fase 4: Generación del Modelo LLM", size="5", color="#FF8C00"),
            rx.divider(),
            rx.hstack(
                rx.badge(
                    "Generación Solicitada",
                    background="#f97316",
                    color="#000000",
                    font_weight="bold",
                    size="3",
                ),
                rx.switch(
                    checked=EstadoProyectosState.current_state["generacion_llm_solicitada"],
                    on_change=EstadoProyectosState.toggle_generacion_solicitada,
                    disabled=~EstadoProyectosState.can_edit,
                ),
                spacing="4",
                width="100%",
            ),
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
            rx.heading("Fase 5: Notificación de Descarga", size="5", color="#FF8C00"),
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
            checked=EstadoProyectosState.current_state[field_name],
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
