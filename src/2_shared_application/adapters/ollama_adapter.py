"""
Adaptador para integración con Ollama.

Implementa la interfaz OllamaRepository usando el cliente oficial de Python.
"""

import logging
from typing import AsyncIterator, Any

try:
    import ollama
    from ollama import Client, AsyncClient, ResponseError
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    Client = None  # type: ignore
    AsyncClient = None  # type: ignore
    ResponseError = Exception  # type: ignore

from ..dtos.ollama_dtos import (
    ChatRequestDto,
    ChatResponseDto,
    ChatMessageDto,
    GenerateRequestDto,
    GenerateResponseDto,
    EmbedRequestDto,
    EmbedResponseDto,
    ModelListResponseDto,
    ModelDto,
    ModelInfoDto,
    ModelShowRequestDto,
    PullModelRequestDto,
    PullModelResponseDto,
    DeleteModelRequestDto,
    DeleteModelResponseDto,
    CopyModelRequestDto,
    CopyModelResponseDto,
    CreateModelRequestDto,
    CreateModelResponseDto,
    RunningModelsResponseDto,
    RunningModelDto,
    VersionResponseDto,
    OllamaErrorDto,
)


logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Excepción personalizada para errores de Ollama."""
    def __init__(self, message: str, status_code: int = 500, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class OllamaAdapter:
    """
    Adaptador para interactuar con Ollama.

    Implementa todas las operaciones definidas en OllamaRepository.
    """

    def __init__(
        self,
        host: str = "http://localhost:11434",
        headers: dict[str, str] | None = None,
        timeout: float = 300.0,
    ) -> None:
        """
        Inicializa el adaptador de Ollama.

        Args:
            host: URL del servidor Ollama
            headers: Headers HTTP opcionales (ej. para autenticación)
            timeout: Timeout en segundos para operaciones
        """
        if not OLLAMA_AVAILABLE:
            raise ImportError(
                "El paquete 'ollama' no está instalado. "
                "Instálalo con: pip install ollama"
            )

        self._host = host
        self._headers = headers or {}
        self._timeout = timeout
        self._client = Client(host=host, headers=self._headers, timeout=timeout)
        self._async_client = AsyncClient(host=host, headers=self._headers, timeout=timeout)

        logger.info(f"OllamaAdapter inicializado con host: {host}")

    # ========================================================================
    # Operaciones de Chat
    # ========================================================================

    def chat(self, request: ChatRequestDto) -> ChatResponseDto:
        """Genera una respuesta de chat."""
        try:
            logger.debug(f"Chat request: model={request.model}, messages={len(request.messages)}")

            messages = [msg.model_dump() for msg in request.messages]
            response = self._client.chat(
                model=request.model,
                messages=messages,
                stream=False,
                options=request.options,
            )

            return self._parse_chat_response(response)

        except ResponseError as e:
            logger.error(f"Error en chat: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado en chat: {e}")
            raise OllamaError(f"Error en operación de chat: {str(e)}") from e

    async def chat_async(self, request: ChatRequestDto) -> ChatResponseDto:
        """Versión asíncrona de chat."""
        try:
            logger.debug(f"Async chat request: model={request.model}")

            messages = [msg.model_dump() for msg in request.messages]
            response = await self._async_client.chat(
                model=request.model,
                messages=messages,
                stream=False,
                options=request.options,
            )

            return self._parse_chat_response(response)

        except ResponseError as e:
            logger.error(f"Error en chat async: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado en chat async: {e}")
            raise OllamaError(f"Error en operación de chat async: {str(e)}") from e

    def chat_stream(self, request: ChatRequestDto) -> AsyncIterator[ChatResponseDto]:
        """Genera una respuesta de chat con streaming."""
        # Nota: implementar si se necesita streaming
        raise NotImplementedError("Streaming de chat no implementado aún")

    # ========================================================================
    # Operaciones de Generación de Texto
    # ========================================================================

    def generate(self, request: GenerateRequestDto) -> GenerateResponseDto:
        """Genera texto a partir de un prompt."""
        try:
            logger.debug(f"Generate request: model={request.model}, prompt_length={len(request.prompt)}")

            response = self._client.generate(
                model=request.model,
                prompt=request.prompt,
                stream=False,
                options=request.options,
                system=request.system,
                template=request.template,
                context=request.context,
            )

            return self._parse_generate_response(response)

        except ResponseError as e:
            logger.error(f"Error en generate: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado en generate: {e}")
            raise OllamaError(f"Error en operación de generación: {str(e)}") from e

    async def generate_async(self, request: GenerateRequestDto) -> GenerateResponseDto:
        """Versión asíncrona de generate."""
        try:
            logger.debug(f"Async generate request: model={request.model}")

            response = await self._async_client.generate(
                model=request.model,
                prompt=request.prompt,
                stream=False,
                options=request.options,
                system=request.system,
                template=request.template,
                context=request.context,
            )

            return self._parse_generate_response(response)

        except ResponseError as e:
            logger.error(f"Error en generate async: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado en generate async: {e}")
            raise OllamaError(f"Error en operación de generación async: {str(e)}") from e

    def generate_stream(self, request: GenerateRequestDto) -> AsyncIterator[GenerateResponseDto]:
        """Genera texto con streaming."""
        raise NotImplementedError("Streaming de generación no implementado aún")

    # ========================================================================
    # Operaciones de Embeddings
    # ========================================================================

    def embed(self, request: EmbedRequestDto) -> EmbedResponseDto:
        """Genera embeddings para texto(s)."""
        try:
            logger.debug(f"Embed request: model={request.model}")

            response = self._client.embed(
                model=request.model,
                input=request.input,
                options=request.options,
            )

            return EmbedResponseDto(
                model=response.get("model", request.model),
                embeddings=response.get("embeddings", []),
                total_duration=response.get("total_duration"),
                load_duration=response.get("load_duration"),
                prompt_eval_count=response.get("prompt_eval_count"),
            )

        except ResponseError as e:
            logger.error(f"Error en embed: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado en embed: {e}")
            raise OllamaError(f"Error en operación de embeddings: {str(e)}") from e

    async def embed_async(self, request: EmbedRequestDto) -> EmbedResponseDto:
        """Versión asíncrona de embed."""
        try:
            logger.debug(f"Async embed request: model={request.model}")

            response = await self._async_client.embed(
                model=request.model,
                input=request.input,
                options=request.options,
            )

            return EmbedResponseDto(
                model=response.get("model", request.model),
                embeddings=response.get("embeddings", []),
                total_duration=response.get("total_duration"),
                load_duration=response.get("load_duration"),
                prompt_eval_count=response.get("prompt_eval_count"),
            )

        except ResponseError as e:
            logger.error(f"Error en embed async: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado en embed async: {e}")
            raise OllamaError(f"Error en operación de embeddings async: {str(e)}") from e

    # ========================================================================
    # Gestión de Modelos
    # ========================================================================

    def list_models(self) -> ModelListResponseDto:
        """Lista todos los modelos disponibles."""
        try:
            logger.debug("Listing models")

            response = self._client.list()
            models_data = response.get("models", [])

            models = [
                ModelDto(
                    name=m.get("name", ""),
                    model=m.get("model", ""),
                    size=m.get("size", 0),
                    digest=m.get("digest", ""),
                    modified_at=m.get("modified_at"),
                    details=m.get("details", {}),
                )
                for m in models_data
            ]

            return ModelListResponseDto(models=models)

        except ResponseError as e:
            logger.error(f"Error listando modelos: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado listando modelos: {e}")
            raise OllamaError(f"Error al listar modelos: {str(e)}") from e

    async def list_models_async(self) -> ModelListResponseDto:
        """Versión asíncrona de list_models."""
        try:
            logger.debug("Async listing models")

            response = await self._async_client.list()
            models_data = response.get("models", [])

            models = [
                ModelDto(
                    name=m.get("name", ""),
                    model=m.get("model", ""),
                    size=m.get("size", 0),
                    digest=m.get("digest", ""),
                    modified_at=m.get("modified_at"),
                    details=m.get("details", {}),
                )
                for m in models_data
            ]

            return ModelListResponseDto(models=models)

        except ResponseError as e:
            logger.error(f"Error listando modelos async: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado listando modelos async: {e}")
            raise OllamaError(f"Error al listar modelos async: {str(e)}") from e

    def show_model(self, request: ModelShowRequestDto) -> ModelInfoDto:
        """Obtiene información detallada de un modelo."""
        try:
            logger.debug(f"Show model: {request.name}")

            response = self._client.show(request.name)

            return ModelInfoDto(
                modelfile=response.get("modelfile", ""),
                parameters=response.get("parameters", ""),
                template=response.get("template", ""),
                details=response.get("details", {}),
                model_info=response.get("model_info", {}),
            )

        except ResponseError as e:
            logger.error(f"Error mostrando modelo: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado mostrando modelo: {e}")
            raise OllamaError(f"Error al mostrar modelo: {str(e)}") from e

    async def show_model_async(self, request: ModelShowRequestDto) -> ModelInfoDto:
        """Versión asíncrona de show_model."""
        try:
            logger.debug(f"Async show model: {request.name}")

            response = await self._async_client.show(request.name)

            return ModelInfoDto(
                modelfile=response.get("modelfile", ""),
                parameters=response.get("parameters", ""),
                template=response.get("template", ""),
                details=response.get("details", {}),
                model_info=response.get("model_info", {}),
            )

        except ResponseError as e:
            logger.error(f"Error mostrando modelo async: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado mostrando modelo async: {e}")
            raise OllamaError(f"Error al mostrar modelo async: {str(e)}") from e

    def pull_model(self, request: PullModelRequestDto) -> PullModelResponseDto:
        """Descarga un modelo."""
        try:
            logger.info(f"Pulling model: {request.name}")

            response = self._client.pull(request.name, stream=False)

            return PullModelResponseDto(
                status=response.get("status", "success"),
                digest=response.get("digest"),
                total=response.get("total"),
                completed=response.get("completed"),
            )

        except ResponseError as e:
            logger.error(f"Error descargando modelo: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado descargando modelo: {e}")
            raise OllamaError(f"Error al descargar modelo: {str(e)}") from e

    async def pull_model_async(self, request: PullModelRequestDto) -> PullModelResponseDto:
        """Versión asíncrona de pull_model."""
        try:
            logger.info(f"Async pulling model: {request.name}")

            response = await self._async_client.pull(request.name, stream=False)

            return PullModelResponseDto(
                status=response.get("status", "success"),
                digest=response.get("digest"),
                total=response.get("total"),
                completed=response.get("completed"),
            )

        except ResponseError as e:
            logger.error(f"Error descargando modelo async: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado descargando modelo async: {e}")
            raise OllamaError(f"Error al descargar modelo async: {str(e)}") from e

    def pull_model_stream(self, request: PullModelRequestDto) -> AsyncIterator[PullModelResponseDto]:
        """Descarga un modelo con streaming del progreso."""
        raise NotImplementedError("Streaming de pull no implementado aún")

    def delete_model(self, request: DeleteModelRequestDto) -> DeleteModelResponseDto:
        """Elimina un modelo local."""
        try:
            logger.info(f"Deleting model: {request.name}")

            self._client.delete(request.name)

            return DeleteModelResponseDto(
                success=True,
                message=f"Modelo {request.name} eliminado correctamente"
            )

        except ResponseError as e:
            logger.error(f"Error eliminando modelo: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado eliminando modelo: {e}")
            raise OllamaError(f"Error al eliminar modelo: {str(e)}") from e

    async def delete_model_async(self, request: DeleteModelRequestDto) -> DeleteModelResponseDto:
        """Versión asíncrona de delete_model."""
        try:
            logger.info(f"Async deleting model: {request.name}")

            await self._async_client.delete(request.name)

            return DeleteModelResponseDto(
                success=True,
                message=f"Modelo {request.name} eliminado correctamente"
            )

        except ResponseError as e:
            logger.error(f"Error eliminando modelo async: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado eliminando modelo async: {e}")
            raise OllamaError(f"Error al eliminar modelo async: {str(e)}") from e

    def copy_model(self, request: CopyModelRequestDto) -> CopyModelResponseDto:
        """Copia un modelo con un nuevo nombre."""
        try:
            logger.info(f"Copying model: {request.source} -> {request.destination}")

            self._client.copy(request.source, request.destination)

            return CopyModelResponseDto(
                success=True,
                message=f"Modelo copiado de {request.source} a {request.destination}"
            )

        except ResponseError as e:
            logger.error(f"Error copiando modelo: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado copiando modelo: {e}")
            raise OllamaError(f"Error al copiar modelo: {str(e)}") from e

    async def copy_model_async(self, request: CopyModelRequestDto) -> CopyModelResponseDto:
        """Versión asíncrona de copy_model."""
        try:
            logger.info(f"Async copying model: {request.source} -> {request.destination}")

            await self._async_client.copy(request.source, request.destination)

            return CopyModelResponseDto(
                success=True,
                message=f"Modelo copiado de {request.source} a {request.destination}"
            )

        except ResponseError as e:
            logger.error(f"Error copiando modelo async: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado copiando modelo async: {e}")
            raise OllamaError(f"Error al copiar modelo async: {str(e)}") from e

    def create_model(self, request: CreateModelRequestDto) -> CreateModelResponseDto:
        """Crea un modelo personalizado desde un Modelfile."""
        try:
            logger.info(f"Creating model: {request.name}")

            response = self._client.create(
                model=request.name,
                modelfile=request.modelfile,
                stream=False,
            )

            return CreateModelResponseDto(
                status=response.get("status", "success"),
                message=f"Modelo {request.name} creado correctamente"
            )

        except ResponseError as e:
            logger.error(f"Error creando modelo: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado creando modelo: {e}")
            raise OllamaError(f"Error al crear modelo: {str(e)}") from e

    async def create_model_async(self, request: CreateModelRequestDto) -> CreateModelResponseDto:
        """Versión asíncrona de create_model."""
        try:
            logger.info(f"Async creating model: {request.name}")

            response = await self._async_client.create(
                model=request.name,
                modelfile=request.modelfile,
                stream=False,
            )

            return CreateModelResponseDto(
                status=response.get("status", "success"),
                message=f"Modelo {request.name} creado correctamente"
            )

        except ResponseError as e:
            logger.error(f"Error creando modelo async: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado creando modelo async: {e}")
            raise OllamaError(f"Error al crear modelo async: {str(e)}") from e

    def create_model_stream(self, request: CreateModelRequestDto) -> AsyncIterator[CreateModelResponseDto]:
        """Crea un modelo con streaming del progreso."""
        raise NotImplementedError("Streaming de creación no implementado aún")

    # ========================================================================
    # Modelos en Ejecución
    # ========================================================================

    def list_running_models(self) -> RunningModelsResponseDto:
        """Lista los modelos actualmente cargados en memoria."""
        try:
            logger.debug("Listing running models")

            response = self._client.ps()
            models_data = response.get("models", [])

            models = [
                RunningModelDto(
                    name=m.get("name", ""),
                    model=m.get("model", ""),
                    size=m.get("size", 0),
                    digest=m.get("digest", ""),
                    expires_at=m.get("expires_at"),
                    size_vram=m.get("size_vram", 0),
                )
                for m in models_data
            ]

            return RunningModelsResponseDto(models=models)

        except ResponseError as e:
            logger.error(f"Error listando modelos en ejecución: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado listando modelos en ejecución: {e}")
            raise OllamaError(f"Error al listar modelos en ejecución: {str(e)}") from e

    async def list_running_models_async(self) -> RunningModelsResponseDto:
        """Versión asíncrona de list_running_models."""
        try:
            logger.debug("Async listing running models")

            response = await self._async_client.ps()
            models_data = response.get("models", [])

            models = [
                RunningModelDto(
                    name=m.get("name", ""),
                    model=m.get("model", ""),
                    size=m.get("size", 0),
                    digest=m.get("digest", ""),
                    expires_at=m.get("expires_at"),
                    size_vram=m.get("size_vram", 0),
                )
                for m in models_data
            ]

            return RunningModelsResponseDto(models=models)

        except ResponseError as e:
            logger.error(f"Error listando modelos en ejecución async: {e}")
            raise OllamaError(str(e.error), status_code=e.status_code) from e
        except Exception as e:
            logger.error(f"Error inesperado listando modelos en ejecución async: {e}")
            raise OllamaError(f"Error al listar modelos en ejecución async: {str(e)}") from e

    # ========================================================================
    # Versión y Health Check
    # ========================================================================

    def get_version(self) -> VersionResponseDto:
        """Obtiene la versión de Ollama."""
        try:
            # El cliente de Python no expone directamente la versión
            # Intentamos hacer un health check como alternativa
            self.health_check()
            return VersionResponseDto(version="unknown")

        except Exception as e:
            logger.error(f"Error obteniendo versión: {e}")
            raise OllamaError(f"Error al obtener versión: {str(e)}") from e

    async def get_version_async(self) -> VersionResponseDto:
        """Versión asíncrona de get_version."""
        try:
            await self.health_check_async()
            return VersionResponseDto(version="unknown")

        except Exception as e:
            logger.error(f"Error obteniendo versión async: {e}")
            raise OllamaError(f"Error al obtener versión async: {str(e)}") from e

    def health_check(self) -> bool:
        """Verifica si Ollama está disponible."""
        try:
            # Intentamos listar modelos como health check
            self._client.list()
            logger.debug("Health check OK")
            return True

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise OllamaError(f"Ollama no está disponible: {str(e)}") from e

    async def health_check_async(self) -> bool:
        """Versión asíncrona de health_check."""
        try:
            await self._async_client.list()
            logger.debug("Async health check OK")
            return True

        except Exception as e:
            logger.error(f"Async health check failed: {e}")
            raise OllamaError(f"Ollama no está disponible: {str(e)}") from e

    # ========================================================================
    # Métodos auxiliares
    # ========================================================================

    def _parse_chat_response(self, response: dict[str, Any]) -> ChatResponseDto:
        """Parsea una respuesta de chat de Ollama."""
        message_data = response.get("message", {})
        message = ChatMessageDto(
            role=message_data.get("role", "assistant"),
            content=message_data.get("content", "")
        )

        return ChatResponseDto(
            model=response.get("model", ""),
            message=message,
            done=response.get("done", True),
            total_duration=response.get("total_duration"),
            load_duration=response.get("load_duration"),
            prompt_eval_count=response.get("prompt_eval_count"),
            eval_count=response.get("eval_count"),
            eval_duration=response.get("eval_duration"),
        )

    def _parse_generate_response(self, response: dict[str, Any]) -> GenerateResponseDto:
        """Parsea una respuesta de generación de Ollama."""
        return GenerateResponseDto(
            model=response.get("model", ""),
            response=response.get("response", ""),
            done=response.get("done", True),
            context=response.get("context", []),
            total_duration=response.get("total_duration"),
            load_duration=response.get("load_duration"),
            prompt_eval_count=response.get("prompt_eval_count"),
            eval_count=response.get("eval_count"),
            eval_duration=response.get("eval_duration"),
        )
