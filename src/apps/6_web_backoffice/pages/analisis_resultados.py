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
import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Optional, TypedDict

# Importar SharedSessionState para acceder a tokens sin importación circular
from web_backoffice.shared_state import SharedSessionState

logger = logging.getLogger("backoffice")


def _load_env_settings():
    """Carga el módulo de configuración compartida."""
    module_path = (
        Path(__file__).resolve().parents[4]
        / "src/2_shared_application/config/env_settings.py"
    )
    spec = importlib.util.spec_from_file_location("env_settings_analisis", module_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Configuración - resolución dinámica desde entorno
try:
    _env_settings = _load_env_settings()
    MIDDLEWARE_URL = (
        _env_settings.get_env_value("MIDDLEWARE_BASE_URL", "http://localhost:8007")
        if _env_settings else "http://localhost:8007"
    )
    CORE_URL = (
        _env_settings.get_protected_value("core_backend_base_url", "http://localhost:8003")
        if _env_settings else "http://localhost:8003"
    )
except Exception:
    MIDDLEWARE_URL = "http://localhost:8007"
    CORE_URL = "http://localhost:8003"


def _build_pat_version(id_org: int, id_proj: int, id_ver: int) -> str:
    """Construye la ruta estática completa de la versión para el trainer."""
    helpers = importlib.import_module("src.2_shared_application.storage_access_structure")
    env_mod = importlib.import_module("src.2_shared_application.config.env_settings")
    base_storage = env_mod.get_env_value(
        "backend_ia_base_storage",
        "~/data/anewhope/files/trainer_server/external",
    )
    org_folder = helpers.get_folder_by_id_organization(id_org)
    prj_folder = helpers.get_folder_by_id_project(id_proj)
    ver_folder = helpers.get_folder_by_id_version(id_ver)
    return f"{base_storage}/{org_folder}/{prj_folder}/{ver_folder}"

# Colores del tema (alineados con backoffice naranja)
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


# Tipos para estadísticas
class EstadisticaPunto(TypedDict):
    """Punto de datos en una serie estadística."""
    clave: str
    valor: float
    valor_grafico: float


class EstadisticaSerie(TypedDict):
    """Serie de estadísticas de un entrenamiento."""
    referencia: str
    titulo: str
    series: list[EstadisticaPunto]
    resumen: str


class SubfaseProgreso(TypedDict):
    """Subfase del entrenamiento."""
    key: str
    name: str
    status: str
    tiempo: str


class FaseProgreso(TypedDict):
    """Fase del entrenamiento."""
    key: str
    name: str
    subfases: list[SubfaseProgreso]


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
    has_searched: bool = False

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

    # Estadísticas
    estadisticas_series: list[EstadisticaSerie] = []
    estadisticas_error: str = ""

    # Modal de progreso de reentrenamiento
    show_progress_modal: bool = False
    progress_training_id: int = 0
    progress_training_seq: int = 0
    progress_phases: list[FaseProgreso] = []
    progress_polling_active: bool = False

    @rx.var
    def org_options(self) -> list[str]:
        """Opciones para el select de organizaciones."""
        return ["Seleccione..."] + [
            org['organization_name']
            for org in self.organizaciones
        ]

    @rx.var
    def project_options(self) -> list[str]:
        """Opciones para el select de proyectos."""
        return ["Seleccione..."] + [
            proj['nombre']
            for proj in self.proyectos
        ]

    @rx.var
    def version_options(self) -> list[str]:
        """Opciones para el select de versiones."""
        logger.info(f"version_options called - versiones count: {len(self.versiones)}")
        if self.versiones:
            logger.info(f"First version: {self.versiones[0]}")
        options = ["Seleccione..."] + [
            ver['version_folder']
            for ver in self.versiones
        ]
        logger.info(f"version_options result: {options}")
        return options

    @rx.var
    def selected_org_display(self) -> str:
        """Valor display para organización seleccionada."""
        if self.selected_org_id == 0:
            return "Seleccione..."
        for org in self.organizaciones:
            if org['organization_id'] == self.selected_org_id:
                return org['organization_name']
        return "Seleccione..."

    @rx.var
    def selected_project_display(self) -> str:
        """Valor display para proyecto seleccionado."""
        if self.selected_project_id == 0:
            return "Seleccione..."
        for proj in self.proyectos:
            if proj['id'] == self.selected_project_id:
                return proj['nombre']
        return "Seleccione..."

    @rx.var
    def selected_version_display(self) -> str:
        """Valor display para versión seleccionada."""
        if self.selected_version_id == 0:
            return "Seleccione..."
        for ver in self.versiones:
            if ver['id_version'] == self.selected_version_id:
                return ver['version_folder']
        return "Seleccione..."

    @rx.var
    def comparaciones_list(self) -> list[dict]:
        """Lista de comparaciones para el modal."""
        if self.suggestions_data and 'comparaciones' in self.suggestions_data:
            return self.suggestions_data['comparaciones']
        return []

    def on_org_select(self, value: str):
        """Handler para selección de organización."""
        logger.info("[ANALISIS] on_org_select | value=%s", value)
        if value == "Seleccione...":
            yield AnalisisResultadosState.on_org_change("0")
        else:
            # Buscar el ID de la organización por nombre
            org_id = "0"
            for org in self.organizaciones:
                if org['organization_name'] == value:
                    org_id = str(org['organization_id'])
                    break
            yield AnalisisResultadosState.on_org_change(org_id)

    def on_project_select(self, value: str):
        """Handler para selección de proyecto."""
        if value == "Seleccione...":
            yield AnalisisResultadosState.on_project_change("0")
        else:
            # Buscar el ID del proyecto por nombre
            project_id = "0"
            for proj in self.proyectos:
                if proj['nombre'] == value:
                    project_id = str(proj['id'])
                    break
            yield AnalisisResultadosState.on_project_change(project_id)

    def on_version_select(self, value: str):
        """Handler para selección de versión."""
        logger.info("[ANALISIS] on_version_select | value=%s", value)
        if value == "Seleccione...":
            yield AnalisisResultadosState.on_version_change("0")
        else:
            # Buscar el ID de la versión por version_folder
            version_id = "0"
            for ver in self.versiones:
                if ver['version_folder'] == value:
                    version_id = str(ver['id_version'])
                    break
            yield AnalisisResultadosState.on_version_change(version_id)

    def on_mount(self):
        """Se ejecuta al montar la página."""
        logger.info("AnalisisResultadosState montado")
        yield AnalisisResultadosState.cargar_organizaciones

    @rx.event(background=True)
    async def cargar_organizaciones(self):
        """Carga la lista de organizaciones."""
        async with self:
            try:
                # Obtener token del state global
                parent_state = await self.get_state(SharedSessionState)
                access_token = parent_state.access_token
                session_token = parent_state.session_token

                if not access_token:
                    self.message = "No hay sesión activa"
                    self.message_type = "error"
                    return

                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{CORE_URL}/organizations",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "X-Session-Token": session_token
                        },
                        timeout=10.0
                    )

                    if response.status_code == 200:
                        # El endpoint devuelve directamente una lista
                        self.organizaciones = response.json()
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

            # Cargar proyectos si hay una organización seleccionada
            if self.selected_org_id > 0:
                try:
                    parent_state = await self.get_state(SharedSessionState)
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
    async def cargar_proyectos(self):
        """Carga proyectos de la organización seleccionada."""
        async with self:
            if self.selected_org_id == 0:
                return

            try:
                parent_state = await self.get_state(SharedSessionState)
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

            logger.info(f"on_project_change: project_id={project_id}, selected_project_id={self.selected_project_id}, selected_org_id={self.selected_org_id}")

            # Cargar versiones si hay un proyecto seleccionado
            if self.selected_project_id > 0:
                try:
                    parent_state = await self.get_state(SharedSessionState)
                    access_token = parent_state.access_token
                    session_token = parent_state.session_token

                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            f"{CORE_URL}/proyectos/{self.selected_project_id}/versiones",
                            params={"org_id": self.selected_org_id},
                            headers={
                                "Authorization": f"Bearer {access_token}",
                                "X-Session-Token": session_token
                            },
                            timeout=10.0
                        )

                        if response.status_code == 200:
                            data = response.json()
                            self.versiones = data.get("versiones", [])
                            logger.info(f"Versiones cargadas: {len(self.versiones)} versiones - Data: {self.versiones}")
                        else:
                            self.message = f"Error cargando versiones: {response.status_code}"
                            self.message_type = "error"
                            logger.error(f"Error HTTP {response.status_code} cargando versiones")

                except Exception as e:
                    logger.error(f"Error cargando versiones: {e}", exc_info=True)
                    self.message = f"Error: {str(e)}"
                    self.message_type = "error"

    @rx.event(background=True)
    async def cargar_versiones(self):
        """Carga versiones del proyecto seleccionado."""
        async with self:
            if self.selected_project_id == 0:
                return

            try:
                parent_state = await self.get_state(SharedSessionState)
                access_token = parent_state.access_token
                session_token = parent_state.session_token

                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{CORE_URL}/proyectos/{self.selected_project_id}/versiones",
                        params={"org_id": self.selected_org_id},
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "X-Session-Token": session_token
                        },
                        timeout=10.0
                    )

                    if response.status_code == 200:
                        data = response.json()
                        self.versiones = data.get("versiones", [])
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
        logger.info("[ANALISIS] buscar_entrenamientos | org=%s, project=%s, version=%s",
                     self.selected_org_id, self.selected_project_id, self.selected_version_id)
        async with self:
            self.loading_entrenamientos = True
            self.entrenamientos = []
            self.message = ""

            try:
                parent_state = await self.get_state(SharedSessionState)
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
                        logger.info("[ANALISIS] buscar_entrenamientos resultado | count=%d", len(self.entrenamientos))
                        self.message = f"Se encontraron {len(self.entrenamientos)} entrenamientos"
                        self.message_type = "success"

                        # Cargar estadísticas con los mismos filtros
                        response_metrics = await client.get(
                            f"{CORE_URL}/analysis/metrics",
                            params=params,
                            headers={
                                "Authorization": f"Bearer {access_token}",
                                "X-Session-Token": session_token
                            },
                            timeout=10.0
                        )

                        if response_metrics.status_code == 200:
                            analisis_list = response_metrics.json()
                            if analisis_list:
                                # Procesar estadísticas
                                series = []
                                for analisis in analisis_list:
                                    numero_secuencia = analisis.get('numero_secuencia', 0)
                                    fecha_fin = analisis.get('fecha_fin', '')
                                    metricas = analisis.get('metricas', {})

                                    rag_quality = float(metricas.get('rag_quality_score', 0))
                                    response_quality = float(metricas.get('response_quality_score', 0))
                                    generation_quality = float(metricas.get('generation_quality_score', 0))
                                    overall_quality = float(metricas.get('overall_quality_score', 0))

                                    fecha_label = f" ({fecha_fin[:10]})" if fecha_fin else ""

                                    puntos = [
                                        {"clave": "RAG", "valor": round(rag_quality * 100, 1), "valor_grafico": round(rag_quality * 100, 1)},
                                        {"clave": "Response", "valor": round(response_quality * 100, 1), "valor_grafico": round(response_quality * 100, 1)},
                                        {"clave": "Generation", "valor": round(generation_quality * 100, 1), "valor_grafico": round(generation_quality * 100, 1)},
                                        {"clave": "Overall", "valor": round(overall_quality * 100, 1), "valor_grafico": round(overall_quality * 100, 1)}
                                    ]

                                    resumen = f"""RAG Quality: {round(rag_quality * 100, 1)}%
Response Quality: {round(response_quality * 100, 1)}%
Generation Quality: {round(generation_quality * 100, 1)}%
Overall Quality: {round(overall_quality * 100, 1)}%"""

                                    series.append({
                                        "referencia": str(numero_secuencia),
                                        "fecha_fin": fecha_fin or "",
                                        "titulo": f"Secuencia #{numero_secuencia}{fecha_label}",
                                        "series": puntos,
                                        "resumen": resumen
                                    })
                                self.estadisticas_series = series
                                self.estadisticas_error = ""
                            else:
                                self.estadisticas_error = "No hay análisis disponibles"
                                self.estadisticas_series = []
                        else:
                            self.estadisticas_error = f"Error cargando métricas: {response_metrics.status_code}"
                            self.estadisticas_series = []
                    else:
                        self.message = f"Error buscando entrenamientos: {response.status_code}"
                        self.message_type = "error"

            except Exception as e:
                logger.error(f"Error buscando entrenamientos: {e}")
                self.message = f"Error: {str(e)}"
                self.message_type = "error"
            finally:
                self.loading_entrenamientos = False
                self.has_searched = True

    @rx.event(background=True)
    async def generar_sugerencias(self, id_entrenamiento: int):
        """Genera sugerencias para un entrenamiento."""
        logger.info("[ANALISIS] generar_sugerencias | id_entrenamiento=%d", id_entrenamiento)
        async with self:
            self.loading_suggestions = True
            self.message = ""

            try:
                parent_state = await self.get_state(SharedSessionState)
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
                        self.message = "Sugerencias generadas exitosamente. Recarga la página para ver los resultados actualizados."
                        self.message_type = "success"
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
        logger.info("[ANALISIS] ver_sugerencias | id_entrenamiento=%d", id_entrenamiento)
        async with self:
            self.loading_suggestions = True
            self.selected_training_id = id_entrenamiento

            try:
                parent_state = await self.get_state(SharedSessionState)
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

    def cerrar_modal_progreso(self):
        """Cierra el modal de progreso."""
        self.show_progress_modal = False
        self.progress_polling_active = False
        self.progress_phases = []

    def _init_progress_phases(self):
        """Inicializa las fases del entrenamiento."""
        self.progress_phases = [
            {"key": "2", "name": "Validación", "subfases": [
                {"key": "2.1", "name": "Verificar directorio", "status": "pending", "tiempo": ""},
                {"key": "2.2", "name": "Escaneo de archivos", "status": "pending", "tiempo": ""},
                {"key": "2.3", "name": "Clasificación por tipo", "status": "pending", "tiempo": ""},
                {"key": "2.4", "name": "Validación de contenido", "status": "pending", "tiempo": ""},
            ]},
            {"key": "3", "name": "Preparación", "subfases": [
                {"key": "3.1", "name": "Carga de documentos", "status": "pending", "tiempo": ""},
                {"key": "3.2", "name": "Chunking", "status": "pending", "tiempo": ""},
                {"key": "3.3", "name": "Generación de embeddings", "status": "pending", "tiempo": ""},
            ]},
            {"key": "4", "name": "Configuración", "subfases": [
                {"key": "4.1", "name": "Conexión ChromaDB", "status": "pending", "tiempo": ""},
                {"key": "4.2", "name": "Crear colección", "status": "pending", "tiempo": ""},
                {"key": "4.3", "name": "Inserción de documentos", "status": "pending", "tiempo": ""},
                {"key": "4.4", "name": "Verificación de integridad", "status": "pending", "tiempo": ""},
            ]},
            {"key": "5", "name": "Entrenamiento", "subfases": [
                {"key": "5.1", "name": "Obtener nombres", "status": "pending", "tiempo": ""},
                {"key": "5.2", "name": "Generar Modelfile", "status": "pending", "tiempo": ""},
                {"key": "5.3", "name": "Guardar Modelfile", "status": "pending", "tiempo": ""},
                {"key": "5.4", "name": "Registrar en Ollama", "status": "pending", "tiempo": ""},
                {"key": "5.5", "name": "Test de verificación", "status": "pending", "tiempo": ""},
            ]},
        ]

    @rx.event(background=True)
    async def poll_training_progress(self):
        """Polling del progreso del entrenamiento."""
        import asyncio
        import sys

        # Wait for training_id to be set (max 5 seconds)
        for i in range(10):
            async with self:
                training_id = self.progress_training_id
                if training_id > 0:
                    break
            print(f"[POLLING PROGRESS] Esperando training_id... intento {i+1}", file=sys.stderr, flush=True)
            await asyncio.sleep(0.5)

        async with self:
            training_id = self.progress_training_id

        print(f"[POLLING PROGRESS] Iniciando polling para training_id={training_id}", file=sys.stderr, flush=True)

        if training_id == 0:
            print(f"[POLLING PROGRESS] ❌ training_id sigue en 0, abortando", file=sys.stderr, flush=True)
            return

        while True:
            async with self:
                if not self.progress_polling_active:
                    print(f"[POLLING PROGRESS] Detenido por polling_active=False", file=sys.stderr, flush=True)
                    break

                training_id = self.progress_training_id

            try:
                parent_state = await self.get_state(SharedSessionState)
                access_token = parent_state.access_token
                session_token = parent_state.session_token

                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{CORE_URL}/training/entrenamientos/{training_id}/progress",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "X-Session-Token": session_token
                        },
                        timeout=10.0
                    )

                    if response.status_code == 200:
                        response_data = response.json()
                        inner_data = response_data.get('data', {}) or {}
                        estado = inner_data.get('estado', '')
                        phases_data = inner_data.get('phases', {})

                        print(f"[POLLING PROGRESS] Estado={estado}, Fases={len(phases_data)}", file=sys.stderr, flush=True)

                        async with self:
                            # Actualizar subfases
                            for phase in self.progress_phases:
                                phase_key = phase['key']
                                if phase_key in phases_data:
                                    phase_info = phases_data[phase_key]
                                    for subfase in phase['subfases']:
                                        subfase_key = subfase['key']
                                        if subfase_key in phase_info.get('subfases', {}):
                                            subfase_info = phase_info['subfases'][subfase_key]
                                            subfase['status'] = subfase_info.get('status', 'pending')
                                            subfase['tiempo'] = subfase_info.get('elapsed_time', '')

                            # Si está completado o en error, detener polling
                            if estado in ['completado', 'error', 'cancelado']:
                                self.progress_polling_active = False

                        yield

                    else:
                        print(f"[POLLING PROGRESS] Error status={response.status_code}", file=sys.stderr, flush=True)

            except Exception as e:
                print(f"[POLLING PROGRESS] Exception: {e}", file=sys.stderr, flush=True)

            await asyncio.sleep(2)

    def iniciar_reentrenamiento(self, id_sugerencia: int):
        """Inicia el proceso de reentrenamiento.

        Prepara la UI (cierra modal de sugerencias, muestra modal de progreso)
        y lanza el background event que ejecuta el reentrenamiento real.
        """
        logger.info("[REENTRENAR] iniciar_reentrenamiento llamado con id_sugerencia=%s", id_sugerencia)
        self.show_suggestions_modal = False
        self.message = f"Preparando reentrenamiento..."
        self.message_type = "info"
        self.id_sugerencia_to_apply = id_sugerencia
        return [type(self).reentrenar_directo(id_sugerencia)]

    @rx.event(background=True)
    async def reentrenar_directo(self, id_sugerencia: int):
        """Lanza reentrenamiento usando los parámetros sugeridos vía middleware.

        Flujo: Backoffice → Middleware → Broker → Trainer
        Usa la misma función send_entrenamiento_to_trainer que la página Entrenamientos.
        """
        logger.info("[REENTRENAR DIRECTO] Iniciando con id_sugerencia=%s", id_sugerencia)

        # Leer tokens del state
        async with self:
            parent_state = await self.get_state(SharedSessionState)
            access_token = parent_state.access_token
            session_token = parent_state.session_token

        if not access_token:
            async with self:
                self.message = "No hay sesión activa"
                self.message_type = "error"
            return

        # Obtener parámetros y metadata fuera del lock
        try:
            async with httpx.AsyncClient() as client:
                response_params = await client.get(
                    f"{CORE_URL}/analysis/suggestions/{id_sugerencia}/params",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "X-Session-Token": session_token,
                    },
                    timeout=30.0,
                )

                if response_params.status_code != 200:
                    async with self:
                        self.message = f"Error obteniendo parámetros: {response_params.status_code}"
                        self.message_type = "error"
                    return

                params = response_params.json()

                response_meta = await client.get(
                    f"{CORE_URL}/analysis/suggestions/{id_sugerencia}",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "X-Session-Token": session_token,
                    },
                    timeout=10.0,
                )

                if response_meta.status_code != 200:
                    async with self:
                        self.message = f"Error obteniendo metadata: {response_meta.status_code}"
                        self.message_type = "error"
                    return

                metadata = response_meta.json()

        except Exception as e:
            logger.error("[REENTRENAR] Error HTTP: %s", e, exc_info=True)
            async with self:
                self.message = f"Error de conexión: {str(e)}"
                self.message_type = "error"
            return

        # Construir pat_version usando helpers compartidos
        try:
            helpers_mod = importlib.import_module(
                "src.2_shared_application.storage_access_structure"
            )
            env_mod = importlib.import_module(
                "src.2_shared_application.config.env_settings"
            )

            base_storage = env_mod.get_env_value(
                "backend_ia_base_storage",
                "~/data/anewhope/files/trainer_server/external",
            )
            org_folder = helpers_mod.get_folder_by_id_organization(
                metadata["id_organizacion"]
            )
            prj_folder = helpers_mod.get_folder_by_id_project(
                metadata["id_proyecto"]
            )
            ver_folder = helpers_mod.get_folder_by_id_version(
                metadata["id_version"]
            )
            pat_version = f"{base_storage}/{org_folder}/{prj_folder}/{ver_folder}"

            payload = {
                "id_organizacion": metadata["id_organizacion"],
                "id_proyecto": metadata["id_proyecto"],
                "id_version": metadata["id_version"],
                "pat_version": pat_version,
                "learning_rate": float(params.get("learning_rate", 0.001)),
                "batch_size": int(params.get("batch_size", 32)),
                "epochs": int(params.get("epochs", 10)),
                "embedding_dimension": int(params.get("embedding_dimension", 384)),
                "sequence_length": int(params.get("sequence_length", 512)),
                "hidden_units": int(params.get("hidden_units", 256)),
                "dropout_rate": float(params.get("dropout_rate", 0.2)),
                "chunk_size": int(params.get("chunk_size", 500)),
                "chunk_overlap": int(params.get("chunk_overlap", 50)),
                "temperature": float(params.get("temperature", 0.7)),
                "max_tokens": int(params.get("max_tokens", 2048)),
                "distance_metric": str(params.get("distance_metric", "cosine")),
                "top_k": int(params.get("top_k", 5)),
                "loss_function": str(params.get("loss_function", "categorical_crossentropy")),
                "optimizer": str(params.get("optimizer", "adam")),
                "model_type": str(params.get("model_type", "llama3.2:latest")),
            }

            logger.info("[REENTRENAR] Enviando al middleware con pat_version=%s", pat_version)

            api_client_mod = importlib.import_module("adapters.api_client")
            result = api_client_mod.send_entrenamiento_to_trainer(
                payload=payload,
                access_token=access_token,
                session_token=session_token,
            )

        except Exception as e:
            logger.error("[REENTRENAR] Error preparando payload: %s", e, exc_info=True)
            async with self:
                self.message = f"Error: {str(e)}"
                self.message_type = "error"
            return

        if result.get("success"):
            id_ent = result.get("id_entrenamiento", 0)
            seq = result.get("numero_secuencia", 0)
            logger.info("[REENTRENAR] Entrenamiento iniciado: ID=%s SEQ=%s", id_ent, seq)

            async with self:
                self.message = f"Reentrenamiento #{seq} iniciado (ID: {id_ent})"
                self.message_type = "success"
                self.progress_training_id = id_ent
                self.progress_training_seq = seq
                self.show_progress_modal = True
                self.progress_polling_active = True
                self._init_progress_phases()
            yield

            # Polling: consultar progreso hasta completar
            import asyncio
            from adapters.api_client import get_training_progress

            while True:
                async with self:
                    if not self.progress_polling_active:
                        break

                try:
                    progress = get_training_progress(
                        id_entrenamiento=id_ent,
                        access_token=access_token,
                        session_token=session_token,
                    )
                    if progress.get("success") and progress.get("data"):
                        data = progress["data"]
                        estado = data.get("estado", "")
                        phases_data = data.get("phases", {})
                        logger.info("[REENTRENAR POLL] estado=%s, phases=%s", estado, list(phases_data.keys()) if phases_data else "none")

                        async with self:
                            for phase in self.progress_phases:
                                phase_key = phase["key"]
                                if phase_key in phases_data:
                                    phase_info = phases_data[phase_key]
                                    for subfase in phase["subfases"]:
                                        subfase_key = subfase["key"]
                                        if subfase_key in phase_info.get("subfases", {}):
                                            sf_info = phase_info["subfases"][subfase_key]
                                            subfase["status"] = sf_info.get("status", "pending")
                                            subfase["tiempo"] = sf_info.get("elapsed_time", "")

                            if estado in ("completado", "error", "cancelado"):
                                self.progress_polling_active = False
                                if estado == "completado":
                                    self.message = f"Entrenamiento completado exitosamente"
                                    self.message_type = "success"
                                elif estado == "error":
                                    self.message = f"Entrenamiento finalizado con error"
                                    self.message_type = "error"
                                else:
                                    self.message = f"Entrenamiento cancelado"
                                    self.message_type = "warning"
                                logger.info("[REENTRENAR POLL] Training terminado: estado=%s", estado)

                        yield
                    elif progress.get("error"):
                        logger.warning("[REENTRENAR POLL] Error en respuesta: %s", progress.get("detail", "desconocido"))
                except Exception as poll_exc:
                    logger.warning("[REENTRENAR POLL] Excepción: %s", poll_exc)

                await asyncio.sleep(2)

        else:
            async with self:
                self.message = f"Error enviando entrenamiento: {result.get('message', 'desconocido')}"
                self.message_type = "error"
                logger.error("[REENTRENAR] Error: %s", self.message)

    def cerrar_modal_reentrenar(self):
        """Cierra el modal de reentrenamiento."""
        self.show_retrain_modal = False
        self.retrain_params = {}

    @rx.event(background=True)
    async def analizar_modelo(self, id_entrenamiento: int):
        """Lanza análisis del modelo generado."""
        logger.info("[ANALISIS] analizar_modelo | id_entrenamiento=%d", id_entrenamiento)
        async with self:
            self.loading_suggestions = True  # Reutilizar loading
            self.message = ""

            try:
                parent_state = await self.get_state(SharedSessionState)
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
                        self.message = f"Análisis completado: Score {score:.2%}. Recarga la página para ver los resultados actualizados."
                        self.message_type = "success"
                    else:
                        self.message = f"Error analizando modelo: {response.status_code}"
                        self.message_type = "error"

            except Exception as e:
                logger.error(f"Error analizando modelo: {e}")
                self.message = f"Error: {str(e)}"
                self.message_type = "error"
            finally:
                self.loading_suggestions = False

    @rx.event(background=True)
    async def cargar_estadisticas(self):
        """Carga las estadísticas de los entrenamientos para mostrar en gráficos."""
        async with self:
            try:
                parent_state = await self.get_state(SharedSessionState)
                access_token = parent_state.access_token
                session_token = parent_state.session_token

                # Usar los mismos filtros que buscar_entrenamientos
                params = {}
                if self.selected_org_id > 0:
                    params["organization_id"] = self.selected_org_id
                if self.selected_project_id > 0:
                    params["project_id"] = self.selected_project_id
                if self.selected_version_id > 0:
                    params["version_id"] = self.selected_version_id

                # Obtener análisis de entrenamientos con métricas
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{CORE_URL}/analysis/metrics",
                        params=params,
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "X-Session-Token": session_token
                        },
                        timeout=10.0
                    )

                    if response.status_code != 200:
                        self.estadisticas_error = f"Error cargando métricas: {response.status_code}"
                        self.estadisticas_series = []
                        return

                    analisis_list = response.json()

                    if not analisis_list:
                        self.estadisticas_error = "No hay análisis disponibles para los filtros seleccionados"
                        self.estadisticas_series = []
                        return

                    # Procesar cada análisis para crear series de gráficos
                    series = []
                    for analisis in analisis_list:
                        numero_secuencia = analisis.get('numero_secuencia', 0)
                        metricas = analisis.get('metricas', {})

                        # Seleccionar métricas clave para el gráfico
                        # Usamos 4 métricas principales para mantener el gráfico legible
                        rag_quality = float(metricas.get('rag_quality_score', 0))
                        response_quality = float(metricas.get('response_quality_score', 0))
                        generation_quality = float(metricas.get('generation_quality_score', 0))
                        overall_quality = float(metricas.get('overall_quality_score', 0))

                        # Crear puntos para el gráfico
                        puntos = [
                            {
                                "clave": "RAG",
                                "valor": round(rag_quality * 100, 1),
                                "valor_grafico": round(rag_quality * 100, 1)
                            },
                            {
                                "clave": "Response",
                                "valor": round(response_quality * 100, 1),
                                "valor_grafico": round(response_quality * 100, 1)
                            },
                            {
                                "clave": "Generation",
                                "valor": round(generation_quality * 100, 1),
                                "valor_grafico": round(generation_quality * 100, 1)
                            },
                            {
                                "clave": "Overall",
                                "valor": round(overall_quality * 100, 1),
                                "valor_grafico": round(overall_quality * 100, 1)
                            }
                        ]

                        # Crear resumen con las métricas principales
                        resumen = f"""RAG Quality: {round(rag_quality * 100, 1)}%
Response Quality: {round(response_quality * 100, 1)}%
Generation Quality: {round(generation_quality * 100, 1)}%
Overall Quality: {round(overall_quality * 100, 1)}%"""

                        series.append({
                            "referencia": str(numero_secuencia),
                            "titulo": f"Entrenamiento Secuencia #{numero_secuencia}",
                            "series": puntos,
                            "resumen": resumen
                        })

                    # Ordenar por secuencia
                    series.sort(key=lambda x: int(x["referencia"]))

                    self.estadisticas_series = series
                    self.estadisticas_error = ""

            except Exception as e:
                logger.error(f"Error cargando estadísticas: {e}")
                self.estadisticas_error = f"Error: {str(e)}"
                self.estadisticas_series = []

# ============================================================================
# Componentes UI
# ============================================================================

def filtros_section() -> rx.Component:
    """Sección de filtros de búsqueda."""
    return rx.box(
        rx.heading("Filtros de Búsqueda", size="6", margin_bottom="1em", color="#E8913A"),
        rx.hstack(
            rx.box(
                rx.text("Organización", size="2", color=COLORS["muted_foreground"]),
                rx.select(
                    AnalisisResultadosState.org_options,
                    value=AnalisisResultadosState.selected_org_display,
                    on_change=AnalisisResultadosState.on_org_select,
                ),
                width="30%",
            ),
            rx.box(
                rx.text("Proyecto", size="2", color=COLORS["muted_foreground"]),
                rx.select(
                    AnalisisResultadosState.project_options,
                    value=AnalisisResultadosState.selected_project_display,
                    on_change=AnalisisResultadosState.on_project_select,
                    disabled=AnalisisResultadosState.selected_org_id == 0,
                ),
                width="30%",
            ),
            rx.box(
                rx.text("Versión", size="2", color=COLORS["muted_foreground"]),
                rx.select(
                    AnalisisResultadosState.version_options,
                    value=AnalisisResultadosState.selected_version_display,
                    on_change=AnalisisResultadosState.on_version_select,
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
    _cell_color = "white"
    return rx.table.row(
        rx.table.cell(rx.text(training['numero_secuencia'], color=_cell_color)),
        rx.table.cell(
            rx.cond(
                training['fecha_fin'],
                rx.text(training['fecha_fin'], color=_cell_color),
                rx.text("En progreso", color=_cell_color),
            )
        ),
        rx.table.cell(rx.text(training['estado'], color=_cell_color)),
        rx.table.cell(
            rx.cond(
                training['loss_final'],
                rx.text(training['loss_final'], color=_cell_color),
                rx.text("N/A", color=_cell_color),
            )
        ),
        rx.table.cell(
            rx.cond(
                training['accuracy_validacion'],
                rx.text(training['accuracy_validacion'], color=_cell_color),
                rx.text("N/A", color=_cell_color),
            )
        ),
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
                        on_click=lambda: AnalisisResultadosState.iniciar_reentrenamiento(training['id_sugerencia']),
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
        rx.heading("Entrenamientos Completados", size="6", margin_bottom="1em", color="#E8913A"),
        rx.cond(
            AnalisisResultadosState.loading_entrenamientos,
            rx.spinner(),
            rx.cond(
                AnalisisResultadosState.entrenamientos.length() > 0,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Secuencia", style={"color": "white"}),
                            rx.table.column_header_cell("Fecha", style={"color": "white"}),
                            rx.table.column_header_cell("Estado", style={"color": "white"}),
                            rx.table.column_header_cell("Loss Final", style={"color": "white"}),
                            rx.table.column_header_cell("Accuracy", style={"color": "white"}),
                            rx.table.column_header_cell("Sugerencias", style={"color": "white"}),
                            rx.table.column_header_cell("Acciones", style={"color": "white"}),
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


def estadisticas_panel() -> rx.Component:
    """Panel de estadísticas con gráficos de evolución de métricas."""
    return rx.box(
        rx.heading("Estadísticas", size="6", margin_bottom="1em", color="#E8913A"),
        rx.text(
            "Visualiza las puntuaciones clave generadas durante la evaluación de modelos.",
            color=COLORS["muted_foreground"],
            margin_bottom="1em",
        ),
        rx.cond(
            AnalisisResultadosState.estadisticas_error != "",
            rx.callout(
                AnalisisResultadosState.estadisticas_error,
                color_scheme="red",
                margin_bottom="1em",
            ),
            rx.fragment(),
        ),
        rx.cond(
            AnalisisResultadosState.estadisticas_series.length() == 0,
            rx.text(
                "No hay datos disponibles. Busca entrenamientos y genera análisis para ver estadísticas.",
                color=COLORS["muted_foreground"],
            ),
            rx.vstack(
                rx.foreach(
                    AnalisisResultadosState.estadisticas_series,
                    lambda item: rx.box(
                        rx.vstack(
                            rx.heading(item["titulo"], size="5", margin_bottom="0.5em"),
                            rx.hstack(
                                # Lista de métricas a la izquierda
                                rx.vstack(
                                    rx.foreach(
                                        item["series"],
                                        lambda punto: rx.hstack(
                                            rx.text(
                                                punto["clave"],
                                                font_family="monospace",
                                                color=COLORS["muted_foreground"],
                                                size="2",
                                            ),
                                            rx.text(
                                                punto["valor"],
                                                font_family="monospace",
                                                color=COLORS["foreground"],
                                                size="2",
                                            ),
                                            spacing="2",
                                            align="center",
                                        ),
                                    ),
                                    spacing="2",
                                    align="start",
                                    width="140px",
                                ),
                                # Gráfico de líneas
                                rx.recharts.line_chart(
                                    rx.recharts.cartesian_grid(stroke_dasharray="3 3", stroke=COLORS["border"]),
                                    rx.recharts.x_axis(
                                        data_key="clave",
                                        type="category",
                                        stroke=COLORS["muted_foreground"],
                                        tick={"fill": COLORS["muted_foreground"], "fontSize": 12},
                                        tick_line=False,
                                        axis_line=False,
                                    ),
                                    rx.recharts.y_axis(
                                        data_key="valor_grafico",
                                        type="number",
                                        stroke=COLORS["muted_foreground"],
                                        tick={"fill": COLORS["muted_foreground"], "fontSize": 12},
                                        tick_line=False,
                                        axis_line=False,
                                    ),
                                    rx.recharts.tooltip(),
                                    rx.recharts.line(
                                        rx.recharts.label_list(
                                            data_key="valor",
                                            position="top",
                                            style={"fill": COLORS["foreground"], "fontSize": 12},
                                        ),
                                        data_key="valor_grafico",
                                        type="monotone",
                                        stroke="#00c9a7",
                                        stroke_width=3,
                                        dot={
                                            "r": 6,
                                            "fill": "#00b49a",
                                            "stroke": "#006b5c",
                                            "strokeWidth": 1.5,
                                        },
                                        active_dot={
                                            "r": 9,
                                            "fill": "#00d8b3",
                                            "stroke": "#00594d",
                                        },
                                        connect_nulls=True,
                                    ),
                                    data=item["series"],
                                    height=300,
                                    width="100%",
                                ),
                                spacing="3",
                                align="stretch",
                                width="100%",
                            ),
                            # Resumen debajo del gráfico
                            rx.box(
                                rx.text(
                                    item["resumen"],
                                    font_family="monospace",
                                    white_space="pre-wrap",
                                    size="2",
                                    color=COLORS["foreground"],
                                ),
                                width="100%",
                            ),
                            spacing="3",
                            align="stretch",
                            width="100%",
                        ),
                        padding="1.5em",
                        background=COLORS["card"],
                        border_radius="8px",
                        border=f"1px solid {COLORS['border']}",
                        width="100%",
                    ),
                ),
                spacing="4",
                width="100%",
            ),
        ),
        padding="1.5em",
        background=COLORS["card"],
        border_radius="8px",
        border=f"1px solid {COLORS['border']}",
        margin_top="2em",
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
                                    AnalisisResultadosState.comparaciones_list,
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
                    rx.button(
                        "Cerrar",
                        on_click=AnalisisResultadosState.cerrar_modal_sugerencias,
                        color_scheme="gray",
                    ),
                    rx.cond(
                        AnalisisResultadosState.suggestions_data != None,
                        rx.button(
                            rx.icon("play", margin_right="0.5em"),
                            "Reentrenar con estos parámetros",
                            on_click=lambda: AnalisisResultadosState.iniciar_reentrenamiento(
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


def render_subfase(subfase: dict) -> rx.Component:
    """Renderiza una subfase individual."""
    return rx.hstack(
        rx.cond(
            subfase['status'] == 'completed',
            rx.icon("check-circle", size=14, color="#10b981"),
            rx.cond(
                subfase['status'] == 'in_progress',
                rx.spinner(size="1"),
                rx.icon("circle", size=14, color=COLORS["border"]),
            ),
        ),
        rx.text(
            f"{subfase['key']} - {subfase['name']}",
            font_size="0.9em",
            color=rx.cond(
                subfase['status'] == 'completed',
                COLORS["success"],
                rx.cond(
                    subfase['status'] == 'in_progress',
                    COLORS["primary"],
                    COLORS["muted_foreground"],
                ),
            ),
        ),
        rx.cond(
            subfase.get('tiempo', '') != '',
            rx.text(
                subfase.get('tiempo', ''),
                font_size="0.8em",
                color=COLORS["muted_foreground"],
            ),
            rx.fragment(),
        ),
        spacing="2",
        align_items="center",
        padding_left="1.5em",
    )


def render_phase(phase: dict) -> rx.Component:
    """Renderiza una fase con sus subfases."""
    return rx.vstack(
        rx.hstack(
            rx.icon("chevron-right", size=16, color=COLORS["primary"]),
            rx.text(
                f"Fase {phase['key']}: {phase['name']}",
                font_weight="bold",
                font_size="1em",
            ),
            spacing="2",
        ),
        rx.vstack(
            rx.foreach(
                phase['subfases'],
                render_subfase,
            ),
            spacing="1",
            width="100%",
        ),
        spacing="2",
        width="100%",
        margin_bottom="1em",
    )


def progress_modal() -> rx.Component:
    """Modal que muestra el progreso del reentrenamiento en tiempo real."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("activity", size=24, color=COLORS["primary"]),
                    rx.text("Progreso del Entrenamiento", font_weight="bold"),
                    spacing="2",
                    align_items="center",
                ),
            ),
            rx.vstack(
                # Info del entrenamiento
                rx.hstack(
                    rx.badge(
                        f"Entrenamiento #{AnalisisResultadosState.progress_training_seq}",
                        color_scheme="blue",
                        size="2",
                    ),
                    rx.badge(
                        f"ID: {AnalisisResultadosState.progress_training_id}",
                        color_scheme="purple",
                        size="2",
                    ),
                    spacing="2",
                ),

                rx.separator(margin_y="1em"),

                # Fases y subfases
                rx.foreach(
                    AnalisisResultadosState.progress_phases,
                    render_phase,
                ),

                rx.separator(margin_y="1em"),

                # Botón cerrar
                rx.button(
                    "Cerrar",
                    on_click=AnalisisResultadosState.cerrar_modal_progreso,
                    size="2",
                    color_scheme="gray",
                ),

                spacing="3",
                width="100%",
            ),
            max_width="600px",
            padding="1.5em",
        ),
        open=AnalisisResultadosState.show_progress_modal,
    )


def analisis_resultados_page() -> rx.Component:
    """Página principal de análisis de resultados."""
    return rx.box(
        rx.heading("Análisis de Resultados", size="8", margin_bottom="1em", color="#E8913A"),
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

        # Panel de estadísticas (solo visible cuando hay datos)
        rx.cond(
            AnalisisResultadosState.estadisticas_series.length() > 0,
            estadisticas_panel(),
            rx.fragment(),
        ),

        # Modal de sugerencias
        suggestions_modal(),

        # Modal de progreso de reentrenamiento
        progress_modal(),

        padding="2em",
        max_width="1400px",
        margin="0 auto",
        on_mount=AnalisisResultadosState.on_mount,
    )
