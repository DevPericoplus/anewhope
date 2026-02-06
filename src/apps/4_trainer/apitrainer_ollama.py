"""
Endpoints de la API para integración con Ollama.

Este módulo contiene todos los endpoints REST para interactuar con Ollama,
incluyendo chat, generación de texto, embeddings y gestión de modelos.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, status

# Importar DTOs de la capa de aplicación compartida
import importlib.util
import sys
from pathlib import Path


def _load_shared_module(module_name: str, relative_path: str) -> any:
    """Carga un módulo compartido dinámicamente."""
    module_path = Path(__file__).resolve().parents[2] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar {module_name} desde {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Cargar DTOs de Ollama
_ollama_dtos = _load_shared_module(
    "ollama_dtos_trainer",
    "2_shared_application/dtos/ollama_dtos.py"
)

# Cargar adaptador de Ollama
_ollama_adapter_module = _load_shared_module(
    "ollama_adapter_trainer",
    "2_shared_application/adapters/ollama_adapter.py"
)

# Importar clases necesarias
ChatRequestDto = _ollama_dtos.ChatRequestDto
ChatResponseDto = _ollama_dtos.ChatResponseDto
GenerateRequestDto = _ollama_dtos.GenerateRequestDto
GenerateResponseDto = _ollama_dtos.GenerateResponseDto
EmbedRequestDto = _ollama_dtos.EmbedRequestDto
EmbedResponseDto = _ollama_dtos.EmbedResponseDto
ModelListResponseDto = _ollama_dtos.ModelListResponseDto
ModelShowRequestDto = _ollama_dtos.ModelShowRequestDto
ModelInfoDto = _ollama_dtos.ModelInfoDto
PullModelRequestDto = _ollama_dtos.PullModelRequestDto
PullModelResponseDto = _ollama_dtos.PullModelResponseDto
DeleteModelRequestDto = _ollama_dtos.DeleteModelRequestDto
DeleteModelResponseDto = _ollama_dtos.DeleteModelResponseDto
CopyModelRequestDto = _ollama_dtos.CopyModelRequestDto
CopyModelResponseDto = _ollama_dtos.CopyModelResponseDto
CreateModelRequestDto = _ollama_dtos.CreateModelRequestDto
CreateModelResponseDto = _ollama_dtos.CreateModelResponseDto
RunningModelsResponseDto = _ollama_dtos.RunningModelsResponseDto
VersionResponseDto = _ollama_dtos.VersionResponseDto

OllamaAdapter = _ollama_adapter_module.OllamaAdapter
OllamaError = _ollama_adapter_module.OllamaError


logger = logging.getLogger(__name__)

# Instancia global del adaptador de Ollama
# Se inicializa al arrancar la aplicación
_ollama_adapter: OllamaAdapter | None = None


def init_ollama_adapter(host: str = "http://localhost:11434") -> None:
    """
    Inicializa el adaptador de Ollama.

    Args:
        host: URL del servidor Ollama
    """
    global _ollama_adapter
    try:
        _ollama_adapter = OllamaAdapter(host=host)
        logger.info(f"Adaptador de Ollama inicializado con host: {host}")
    except Exception as e:
        logger.error(f"Error inicializando adaptador de Ollama: {e}")
        _ollama_adapter = None


def get_ollama_adapter() -> OllamaAdapter:
    """
    Obtiene la instancia del adaptador de Ollama.

    Returns:
        Instancia del adaptador

    Raises:
        HTTPException: Si el adaptador no está inicializado
    """
    if _ollama_adapter is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Adaptador de Ollama no disponible. Verifica que Ollama esté instalado y en ejecución."
        )
    return _ollama_adapter


def register_ollama_routes(app: FastAPI) -> None:
    """
    Registra los endpoints de Ollama en la aplicación FastAPI.

    Args:
        app: Instancia de la aplicación FastAPI
    """

    # ========================================================================
    # Health Check y Versión
    # ========================================================================

    @app.get("/trainer/ollama/health")
    def ollama_health_check(
        adapter: OllamaAdapter = Annotated[OllamaAdapter, lambda: get_ollama_adapter()]
    ) -> dict:
        """Verifica el estado de Ollama."""
        try:
            is_healthy = adapter.health_check()
            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "service": "ollama",
                "message": "Ollama está funcionando correctamente"
            }
        except OllamaError as e:
            logger.error(f"Health check fallido: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Ollama no está disponible: {e.message}"
            ) from e

    @app.get("/trainer/ollama/version", response_model=VersionResponseDto)
    def get_ollama_version() -> VersionResponseDto:
        """Obtiene la versión de Ollama."""
        try:
            adapter = get_ollama_adapter()
            return adapter.get_version()
        except OllamaError as e:
            logger.error(f"Error obteniendo versión: {e}")
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message
            ) from e

    # ========================================================================
    # Operaciones de Chat
    # ========================================================================

    @app.post("/trainer/ollama/chat", response_model=ChatResponseDto)
    def chat(
        request: ChatRequestDto,
        x_client_app: Annotated[str | None, Header()] = None,
    ) -> ChatResponseDto:
        """
        Genera una respuesta de chat usando un modelo de Ollama.

        Args:
            request: Configuración del chat (modelo y mensajes)
            x_client_app: Aplicación cliente (para trazabilidad)

        Returns:
            Respuesta del modelo con el mensaje generado
        """
        try:
            adapter = get_ollama_adapter()
            logger.info(f"Chat request from {x_client_app}: model={request.model}")
            return adapter.chat(request)
        except OllamaError as e:
            logger.error(f"Error en chat: {e}")
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message
            ) from e

    # ========================================================================
    # Operaciones de Generación de Texto
    # ========================================================================

    @app.post("/trainer/ollama/generate", response_model=GenerateResponseDto)
    def generate(
        request: GenerateRequestDto,
        x_client_app: Annotated[str | None, Header()] = None,
    ) -> GenerateResponseDto:
        """
        Genera texto a partir de un prompt usando un modelo de Ollama.

        Args:
            request: Configuración de generación (modelo y prompt)
            x_client_app: Aplicación cliente (para trazabilidad)

        Returns:
            Texto generado por el modelo
        """
        try:
            adapter = get_ollama_adapter()
            logger.info(f"Generate request from {x_client_app}: model={request.model}")
            return adapter.generate(request)
        except OllamaError as e:
            logger.error(f"Error en generate: {e}")
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message
            ) from e

    # ========================================================================
    # Operaciones de Embeddings
    # ========================================================================

    @app.post("/trainer/ollama/embed", response_model=EmbedResponseDto)
    def embed(
        request: EmbedRequestDto,
        x_client_app: Annotated[str | None, Header()] = None,
    ) -> EmbedResponseDto:
        """
        Genera embeddings para texto(s) usando un modelo de Ollama.

        Args:
            request: Configuración de embeddings (modelo y texto)
            x_client_app: Aplicación cliente (para trazabilidad)

        Returns:
            Vector(es) de embeddings
        """
        try:
            adapter = get_ollama_adapter()
            logger.info(f"Embed request from {x_client_app}: model={request.model}")
            return adapter.embed(request)
        except OllamaError as e:
            logger.error(f"Error en embed: {e}")
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message
            ) from e

    # ========================================================================
    # Gestión de Modelos
    # ========================================================================

    @app.get("/trainer/ollama/models", response_model=ModelListResponseDto)
    def list_models(
        x_client_app: Annotated[str | None, Header()] = None,
    ) -> ModelListResponseDto:
        """
        Lista todos los modelos de Ollama disponibles localmente.

        Args:
            x_client_app: Aplicación cliente (para trazabilidad)

        Returns:
            Lista de modelos con sus metadatos
        """
        try:
            adapter = get_ollama_adapter()
            logger.info(f"List models request from {x_client_app}")
            return adapter.list_models()
        except OllamaError as e:
            logger.error(f"Error listando modelos: {e}")
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message
            ) from e

    @app.post("/trainer/ollama/models/show", response_model=ModelInfoDto)
    def show_model(
        request: ModelShowRequestDto,
        x_client_app: Annotated[str | None, Header()] = None,
    ) -> ModelInfoDto:
        """
        Obtiene información detallada de un modelo de Ollama.

        Args:
            request: Nombre del modelo
            x_client_app: Aplicación cliente (para trazabilidad)

        Returns:
            Información completa del modelo (Modelfile, parámetros, etc.)
        """
        try:
            adapter = get_ollama_adapter()
            logger.info(f"Show model request from {x_client_app}: {request.name}")
            return adapter.show_model(request)
        except OllamaError as e:
            logger.error(f"Error mostrando modelo: {e}")
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message
            ) from e

    @app.post("/trainer/ollama/models/pull", response_model=PullModelResponseDto)
    def pull_model(
        request: PullModelRequestDto,
        x_client_app: Annotated[str | None, Header()] = None,
    ) -> PullModelResponseDto:
        """
        Descarga un modelo de Ollama desde el registro.

        Args:
            request: Nombre del modelo a descargar
            x_client_app: Aplicación cliente (para trazabilidad)

        Returns:
            Estado de la descarga
        """
        try:
            adapter = get_ollama_adapter()
            logger.info(f"Pull model request from {x_client_app}: {request.name}")
            return adapter.pull_model(request)
        except OllamaError as e:
            logger.error(f"Error descargando modelo: {e}")
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message
            ) from e

    @app.delete("/trainer/ollama/models/{model_name}", response_model=DeleteModelResponseDto)
    def delete_model(
        model_name: str,
        x_client_app: Annotated[str | None, Header()] = None,
    ) -> DeleteModelResponseDto:
        """
        Elimina un modelo de Ollama del almacenamiento local.

        Args:
            model_name: Nombre del modelo a eliminar
            x_client_app: Aplicación cliente (para trazabilidad)

        Returns:
            Confirmación de eliminación
        """
        try:
            adapter = get_ollama_adapter()
            logger.info(f"Delete model request from {x_client_app}: {model_name}")
            request = DeleteModelRequestDto(name=model_name)
            return adapter.delete_model(request)
        except OllamaError as e:
            logger.error(f"Error eliminando modelo: {e}")
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message
            ) from e

    @app.post("/trainer/ollama/models/copy", response_model=CopyModelResponseDto)
    def copy_model(
        request: CopyModelRequestDto,
        x_client_app: Annotated[str | None, Header()] = None,
    ) -> CopyModelResponseDto:
        """
        Copia un modelo de Ollama con un nuevo nombre.

        Args:
            request: Modelo origen y destino
            x_client_app: Aplicación cliente (para trazabilidad)

        Returns:
            Confirmación de copia
        """
        try:
            adapter = get_ollama_adapter()
            logger.info(f"Copy model request from {x_client_app}: {request.source} -> {request.destination}")
            return adapter.copy_model(request)
        except OllamaError as e:
            logger.error(f"Error copiando modelo: {e}")
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message
            ) from e

    @app.post("/trainer/ollama/models/create", response_model=CreateModelResponseDto)
    def create_model(
        request: CreateModelRequestDto,
        x_client_app: Annotated[str | None, Header()] = None,
    ) -> CreateModelResponseDto:
        """
        Crea un modelo personalizado de Ollama desde un Modelfile.

        Args:
            request: Nombre y contenido del Modelfile
            x_client_app: Aplicación cliente (para trazabilidad)

        Returns:
            Estado de la creación
        """
        try:
            adapter = get_ollama_adapter()
            logger.info(f"Create model request from {x_client_app}: {request.name}")
            return adapter.create_model(request)
        except OllamaError as e:
            logger.error(f"Error creando modelo: {e}")
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message
            ) from e

    # ========================================================================
    # Modelos en Ejecución
    # ========================================================================

    @app.get("/trainer/ollama/ps", response_model=RunningModelsResponseDto)
    def list_running_models(
        x_client_app: Annotated[str | None, Header()] = None,
    ) -> RunningModelsResponseDto:
        """
        Lista los modelos de Ollama actualmente cargados en memoria.

        Args:
            x_client_app: Aplicación cliente (para trazabilidad)

        Returns:
            Lista de modelos en ejecución con uso de recursos (VRAM)
        """
        try:
            adapter = get_ollama_adapter()
            logger.info(f"List running models request from {x_client_app}")
            return adapter.list_running_models()
        except OllamaError as e:
            logger.error(f"Error listando modelos en ejecución: {e}")
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message
            ) from e

    logger.info("Endpoints de Ollama registrados correctamente")
