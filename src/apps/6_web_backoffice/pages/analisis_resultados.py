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
from typing import Optional, TypedDict

# Importar SharedSessionState para acceder a tokens sin importación circular
from web_backoffice.shared_state import SharedSessionState

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

    # Estadísticas
    estadisticas_series: list[EstadisticaSerie] = []
    estadisticas_error: str = ""

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
                                    metricas = analisis.get('metricas', {})

                                    rag_quality = float(metricas.get('rag_quality_score', 0))
                                    response_quality = float(metricas.get('response_quality_score', 0))
                                    generation_quality = float(metricas.get('generation_quality_score', 0))
                                    overall_quality = float(metricas.get('overall_quality_score', 0))

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
                                        "titulo": f"Entrenamiento Secuencia #{numero_secuencia}",
                                        "series": puntos,
                                        "resumen": resumen
                                    })

                                series.sort(key=lambda x: int(x["referencia"]))
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

    @rx.event(background=True)
    async def generar_sugerencias(self, id_entrenamiento: int):
        """Genera sugerencias para un entrenamiento."""
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

    @rx.event(background=True)
    async def preparar_reentrenamiento(self, id_sugerencia: int):
        """Prepara el reentrenamiento con parámetros sugeridos."""
        async with self:
            try:
                parent_state = await self.get_state(SharedSessionState)
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
        rx.heading("Filtros de Búsqueda", size="6", margin_bottom="1em"),
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
    return rx.table.row(
        rx.table.cell(training['numero_secuencia']),
        rx.table.cell(
            rx.cond(
                training['fecha_fin'],
                training['fecha_fin'],
                "En progreso"
            )
        ),
        rx.table.cell(training['estado']),
        rx.table.cell(
            rx.cond(
                training['loss_final'],
                training['loss_final'],
                "N/A"
            )
        ),
        rx.table.cell(
            rx.cond(
                training['accuracy_validacion'],
                training['accuracy_validacion'],
                "N/A"
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


def estadisticas_panel() -> rx.Component:
    """Panel de estadísticas con gráficos de evolución de métricas."""
    return rx.box(
        rx.heading("Estadísticas", size="6", margin_bottom="1em"),
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

        # Panel de estadísticas
        estadisticas_panel(),

        # Modal de sugerencias
        suggestions_modal(),

        padding="2em",
        max_width="1400px",
        margin="0 auto",
        on_mount=AnalisisResultadosState.on_mount,
    )
