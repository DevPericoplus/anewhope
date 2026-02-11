"""
Endpoints de la API para integración con Ollama.

Este módulo contiene todos los endpoints REST para interactuar con Ollama,
incluyendo chat, generación de texto, embeddings y gestión de modelos.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, status

# Configurar rutas para imports
_current_dir = Path(__file__).resolve().parent
_src_dir = _current_dir.parents[1]  # Llegar a src/
_shared_app_dir = _src_dir / "2_shared_application"

# Agregar src/ al PYTHONPATH para que Python reconozca 2_shared_application como paquete
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

# Usar importlib.util para cargar módulos con estructura de paquete
import importlib.util
from types import ModuleType


def _load_package_module(module_name: str, file_path: Path, is_package: bool = False) -> ModuleType:
    """Carga un módulo o paquete desde una ruta absoluta con soporte para relative imports."""
    spec = importlib.util.spec_from_file_location(
        module_name,
        file_path,
        submodule_search_locations=[str(file_path.parent)] if is_package else None
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar {module_name} desde {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    if is_package:
        module.__path__ = [str(file_path.parent)]

    spec.loader.exec_module(module)
    return module


# Crear la estructura de paquetes para que los relative imports funcionen
# 1. Cargar 2_shared_application como paquete raíz
_shared_init = _shared_app_dir / "__init__.py"
_shared_pkg = _load_package_module("2_shared_application", _shared_init, is_package=True)

# 2. Cargar dtos como subpaquete
_dtos_init = _shared_app_dir / "dtos" / "__init__.py"
_dtos_pkg = _load_package_module("2_shared_application.dtos", _dtos_init, is_package=True)

# 3. Cargar ollama_dtos dentro del paquete dtos
_dtos_path = _shared_app_dir / "dtos" / "ollama_dtos.py"
_dtos_module = _load_package_module("2_shared_application.dtos.ollama_dtos", _dtos_path)

# 4. Cargar adapters como subpaquete
_adapters_init = _shared_app_dir / "adapters" / "__init__.py"
_adapters_pkg = _load_package_module("2_shared_application.adapters", _adapters_init, is_package=True)

# 5. Cargar ollama_adapter (ahora puede hacer from ..dtos.ollama_dtos import)
_adapter_path = _shared_app_dir / "adapters" / "ollama_adapter.py"
_adapter_module = _load_package_module("2_shared_application.adapters.ollama_adapter", _adapter_path)

# Extraer las clases que necesitamos
ChatRequestDto = _dtos_module.ChatRequestDto
ChatResponseDto = _dtos_module.ChatResponseDto
GenerateRequestDto = _dtos_module.GenerateRequestDto
GenerateResponseDto = _dtos_module.GenerateResponseDto
EmbedRequestDto = _dtos_module.EmbedRequestDto
EmbedResponseDto = _dtos_module.EmbedResponseDto
ModelListResponseDto = _dtos_module.ModelListResponseDto
ModelShowRequestDto = _dtos_module.ModelShowRequestDto
ModelInfoDto = _dtos_module.ModelInfoDto
PullModelRequestDto = _dtos_module.PullModelRequestDto
PullModelResponseDto = _dtos_module.PullModelResponseDto
DeleteModelRequestDto = _dtos_module.DeleteModelRequestDto
DeleteModelResponseDto = _dtos_module.DeleteModelResponseDto
CopyModelRequestDto = _dtos_module.CopyModelRequestDto
CopyModelResponseDto = _dtos_module.CopyModelResponseDto
CreateModelRequestDto = _dtos_module.CreateModelRequestDto
CreateModelResponseDto = _dtos_module.CreateModelResponseDto
RunningModelsResponseDto = _dtos_module.RunningModelsResponseDto
VersionResponseDto = _dtos_module.VersionResponseDto

OllamaAdapter = _adapter_module.OllamaAdapter
OllamaError = _adapter_module.OllamaError


logger = logging.getLogger(__name__)

# Instancia global del adaptador de Ollama
_ollama_adapter: OllamaAdapter | None = None


def init_ollama_adapter(host: str = "http://localhost:11434") -> None:
    """
    Inicializa el adaptador de Ollama.

    Args:
        host: URL del servidor Ollama
    """
    global _ollama_adapter
    try:
        # Timeout de 28800 segundos (8 horas) para modelos en CPU con contexto grande
        # En macbook sin GPU, las operaciones de análisis + fusión pueden tardar 6+ horas
        _ollama_adapter = OllamaAdapter(host=host, timeout=28800.0)
        logger.info(f"Adaptador de Ollama inicializado con host: {host}, timeout: 28800s")
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
    def ollama_health_check() -> dict:
        """Verifica el estado de Ollama."""
        try:
            adapter = get_ollama_adapter()
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
        """Genera una respuesta de chat usando un modelo de Ollama."""
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
        """Genera texto a partir de un prompt usando un modelo de Ollama."""
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
        """Genera embeddings para texto(s) usando un modelo de Ollama."""
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
        """Lista todos los modelos de Ollama disponibles localmente."""
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
        """Obtiene información detallada de un modelo de Ollama."""
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
        """Descarga un modelo de Ollama desde el registro."""
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
        """Elimina un modelo de Ollama del almacenamiento local."""
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
        """Copia un modelo de Ollama con un nuevo nombre."""
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
        """Crea un modelo personalizado de Ollama desde un Modelfile."""
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
        """Lista los modelos de Ollama actualmente cargados en memoria."""
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
