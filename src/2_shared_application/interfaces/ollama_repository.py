"""
Interfaz del repositorio de Ollama.

Define el contrato para interactuar con la API de Ollama,
permitiendo múltiples implementaciones (local, remoto, mock).
"""

from typing import Protocol, AsyncIterator

from ..dtos.ollama_dtos import (
    ChatRequestDto,
    ChatResponseDto,
    GenerateRequestDto,
    GenerateResponseDto,
    EmbedRequestDto,
    EmbedResponseDto,
    ModelListResponseDto,
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
    VersionResponseDto,
)


class OllamaRepository(Protocol):
    """
    Contrato para operaciones con Ollama.

    Define todos los métodos disponibles para interactuar con modelos de IA.
    """

    # ========================================================================
    # Operaciones de Chat
    # ========================================================================

    def chat(self, request: ChatRequestDto) -> ChatResponseDto:
        """
        Genera una respuesta de chat.

        Args:
            request: Datos de la solicitud de chat

        Returns:
            Respuesta del modelo con el mensaje generado

        Raises:
            OllamaError: Si hay un error en la comunicación con Ollama
        """
        ...

    async def chat_async(self, request: ChatRequestDto) -> ChatResponseDto:
        """Versión asíncrona de chat."""
        ...

    def chat_stream(self, request: ChatRequestDto) -> AsyncIterator[ChatResponseDto]:
        """
        Genera una respuesta de chat con streaming.

        Args:
            request: Datos de la solicitud de chat (stream=True)

        Yields:
            Fragmentos de la respuesta del modelo

        Raises:
            OllamaError: Si hay un error en la comunicación
        """
        ...

    # ========================================================================
    # Operaciones de Generación de Texto
    # ========================================================================

    def generate(self, request: GenerateRequestDto) -> GenerateResponseDto:
        """
        Genera texto a partir de un prompt.

        Args:
            request: Datos de la solicitud de generación

        Returns:
            Texto generado por el modelo

        Raises:
            OllamaError: Si hay un error en la comunicación
        """
        ...

    async def generate_async(self, request: GenerateRequestDto) -> GenerateResponseDto:
        """Versión asíncrona de generate."""
        ...

    def generate_stream(self, request: GenerateRequestDto) -> AsyncIterator[GenerateResponseDto]:
        """
        Genera texto con streaming.

        Args:
            request: Datos de la solicitud (stream=True)

        Yields:
            Fragmentos del texto generado

        Raises:
            OllamaError: Si hay un error en la comunicación
        """
        ...

    # ========================================================================
    # Operaciones de Embeddings
    # ========================================================================

    def embed(self, request: EmbedRequestDto) -> EmbedResponseDto:
        """
        Genera embeddings para texto(s).

        Args:
            request: Texto o lista de textos para embeddings

        Returns:
            Vector(es) de embeddings

        Raises:
            OllamaError: Si hay un error en la comunicación
        """
        ...

    async def embed_async(self, request: EmbedRequestDto) -> EmbedResponseDto:
        """Versión asíncrona de embed."""
        ...

    # ========================================================================
    # Gestión de Modelos
    # ========================================================================

    def list_models(self) -> ModelListResponseDto:
        """
        Lista todos los modelos disponibles localmente.

        Returns:
            Lista de modelos con sus metadatos

        Raises:
            OllamaError: Si hay un error en la comunicación
        """
        ...

    async def list_models_async(self) -> ModelListResponseDto:
        """Versión asíncrona de list_models."""
        ...

    def show_model(self, request: ModelShowRequestDto) -> ModelInfoDto:
        """
        Obtiene información detallada de un modelo.

        Args:
            request: Nombre del modelo

        Returns:
            Información completa del modelo

        Raises:
            OllamaError: Si el modelo no existe o hay un error
        """
        ...

    async def show_model_async(self, request: ModelShowRequestDto) -> ModelInfoDto:
        """Versión asíncrona de show_model."""
        ...

    def pull_model(self, request: PullModelRequestDto) -> PullModelResponseDto:
        """
        Descarga un modelo desde el registro de Ollama.

        Args:
            request: Nombre del modelo a descargar

        Returns:
            Estado de la descarga

        Raises:
            OllamaError: Si hay un error en la descarga
        """
        ...

    async def pull_model_async(self, request: PullModelRequestDto) -> PullModelResponseDto:
        """Versión asíncrona de pull_model."""
        ...

    def pull_model_stream(self, request: PullModelRequestDto) -> AsyncIterator[PullModelResponseDto]:
        """
        Descarga un modelo con streaming del progreso.

        Args:
            request: Nombre del modelo (stream=True)

        Yields:
            Actualizaciones del progreso de descarga

        Raises:
            OllamaError: Si hay un error en la descarga
        """
        ...

    def delete_model(self, request: DeleteModelRequestDto) -> DeleteModelResponseDto:
        """
        Elimina un modelo local.

        Args:
            request: Nombre del modelo a eliminar

        Returns:
            Confirmación de eliminación

        Raises:
            OllamaError: Si el modelo no existe o hay un error
        """
        ...

    async def delete_model_async(self, request: DeleteModelRequestDto) -> DeleteModelResponseDto:
        """Versión asíncrona de delete_model."""
        ...

    def copy_model(self, request: CopyModelRequestDto) -> CopyModelResponseDto:
        """
        Copia un modelo con un nuevo nombre.

        Args:
            request: Modelo origen y destino

        Returns:
            Confirmación de copia

        Raises:
            OllamaError: Si hay un error en la copia
        """
        ...

    async def copy_model_async(self, request: CopyModelRequestDto) -> CopyModelResponseDto:
        """Versión asíncrona de copy_model."""
        ...

    def create_model(self, request: CreateModelRequestDto) -> CreateModelResponseDto:
        """
        Crea un modelo personalizado desde un Modelfile.

        Args:
            request: Nombre y contenido del Modelfile

        Returns:
            Estado de la creación

        Raises:
            OllamaError: Si hay un error en la creación
        """
        ...

    async def create_model_async(self, request: CreateModelRequestDto) -> CreateModelResponseDto:
        """Versión asíncrona de create_model."""
        ...

    def create_model_stream(self, request: CreateModelRequestDto) -> AsyncIterator[CreateModelResponseDto]:
        """
        Crea un modelo con streaming del progreso.

        Args:
            request: Datos del modelo (stream=True)

        Yields:
            Actualizaciones del progreso

        Raises:
            OllamaError: Si hay un error en la creación
        """
        ...

    # ========================================================================
    # Modelos en Ejecución
    # ========================================================================

    def list_running_models(self) -> RunningModelsResponseDto:
        """
        Lista los modelos actualmente cargados en memoria.

        Returns:
            Lista de modelos en ejecución con uso de recursos

        Raises:
            OllamaError: Si hay un error en la comunicación
        """
        ...

    async def list_running_models_async(self) -> RunningModelsResponseDto:
        """Versión asíncrona de list_running_models."""
        ...

    # ========================================================================
    # Versión y Health Check
    # ========================================================================

    def get_version(self) -> VersionResponseDto:
        """
        Obtiene la versión de Ollama.

        Returns:
            Versión del servidor Ollama

        Raises:
            OllamaError: Si hay un error en la comunicación
        """
        ...

    async def get_version_async(self) -> VersionResponseDto:
        """Versión asíncrona de get_version."""
        ...

    def health_check(self) -> bool:
        """
        Verifica si Ollama está disponible.

        Returns:
            True si Ollama responde correctamente

        Raises:
            OllamaError: Si Ollama no está disponible
        """
        ...

    async def health_check_async(self) -> bool:
        """Versión asíncrona de health_check."""
        ...
