"""
DTOs (Data Transfer Objects) para operaciones con Ollama.

Define las estructuras de datos para requests y responses de la API de Ollama.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# DTOs para Mensajes de Chat
# ============================================================================

class ChatMessageDto(BaseModel):
    """DTO para un mensaje de chat."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    role: str = Field(..., description="Rol del mensaje: system, user, assistant")
    content: str = Field(..., description="Contenido del mensaje")


class ChatRequestDto(BaseModel):
    """DTO para solicitud de chat."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    model: str = Field(..., description="Nombre del modelo a usar")
    messages: list[ChatMessageDto] = Field(..., description="Lista de mensajes")
    stream: bool = Field(default=False, description="Habilitar streaming")
    options: dict[str, Any] = Field(default_factory=dict, description="Opciones del modelo")


class ChatResponseDto(BaseModel):
    """DTO para respuesta de chat."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    model: str
    message: ChatMessageDto
    done: bool
    total_duration: int | None = None
    load_duration: int | None = None
    prompt_eval_count: int | None = None
    eval_count: int | None = None
    eval_duration: int | None = None


# ============================================================================
# DTOs para Generación de Texto
# ============================================================================

class GenerateRequestDto(BaseModel):
    """DTO para solicitud de generación de texto."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    model: str = Field(..., description="Nombre del modelo")
    prompt: str = Field(..., description="Prompt para generar")
    stream: bool = Field(default=False, description="Habilitar streaming")
    options: dict[str, Any] = Field(default_factory=dict, description="Opciones")
    system: str | None = Field(default=None, description="Mensaje de sistema")
    template: str | None = Field(default=None, description="Template personalizado")
    context: list[int] = Field(default_factory=list, description="Contexto previo")


class GenerateResponseDto(BaseModel):
    """DTO para respuesta de generación."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    model: str
    response: str
    done: bool
    context: list[int] = Field(default_factory=list)
    total_duration: int | None = None
    load_duration: int | None = None
    prompt_eval_count: int | None = None
    eval_count: int | None = None
    eval_duration: int | None = None


# ============================================================================
# DTOs para Embeddings
# ============================================================================

class EmbedRequestDto(BaseModel):
    """DTO para solicitud de embeddings."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    model: str = Field(..., description="Nombre del modelo")
    input: str | list[str] = Field(..., description="Texto o lista de textos")
    options: dict[str, Any] = Field(default_factory=dict, description="Opciones")


class EmbedResponseDto(BaseModel):
    """DTO para respuesta de embeddings."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    model: str
    embeddings: list[list[float]] = Field(..., description="Lista de embeddings")
    total_duration: int | None = None
    load_duration: int | None = None
    prompt_eval_count: int | None = None


# ============================================================================
# DTOs para Gestión de Modelos
# ============================================================================

class ModelDto(BaseModel):
    """DTO para información de modelo."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    name: str
    model: str
    size: int
    digest: str
    modified_at: datetime | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ModelListResponseDto(BaseModel):
    """DTO para lista de modelos."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    models: list[ModelDto] = Field(default_factory=list)


class ModelInfoDto(BaseModel):
    """DTO para información detallada del modelo."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    modelfile: str
    parameters: str
    template: str
    details: dict[str, Any] = Field(default_factory=dict)
    model_info: dict[str, Any] = Field(default_factory=dict)


class ModelShowRequestDto(BaseModel):
    """DTO para solicitud de información de modelo."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    name: str = Field(..., description="Nombre del modelo")


class PullModelRequestDto(BaseModel):
    """DTO para solicitud de descarga de modelo."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    name: str = Field(..., description="Nombre del modelo a descargar")
    stream: bool = Field(default=False, description="Habilitar streaming del progreso")


class PullModelResponseDto(BaseModel):
    """DTO para respuesta de descarga de modelo."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    status: str
    digest: str | None = None
    total: int | None = None
    completed: int | None = None


class DeleteModelRequestDto(BaseModel):
    """DTO para solicitud de eliminación de modelo."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    name: str = Field(..., description="Nombre del modelo a eliminar")


class DeleteModelResponseDto(BaseModel):
    """DTO para respuesta de eliminación."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    success: bool
    message: str = ""


class CopyModelRequestDto(BaseModel):
    """DTO para solicitud de copia de modelo."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    source: str = Field(..., description="Nombre del modelo origen")
    destination: str = Field(..., description="Nombre del modelo destino")


class CopyModelResponseDto(BaseModel):
    """DTO para respuesta de copia."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    success: bool
    message: str = ""


class CreateModelRequestDto(BaseModel):
    """DTO para solicitud de creación de modelo."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    name: str = Field(..., description="Nombre del nuevo modelo")
    modelfile: str = Field(..., description="Contenido del Modelfile")
    stream: bool = Field(default=False, description="Habilitar streaming")


class CreateModelResponseDto(BaseModel):
    """DTO para respuesta de creación."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    status: str
    message: str = ""


# ============================================================================
# DTOs para Modelos en Ejecución
# ============================================================================

class RunningModelDto(BaseModel):
    """DTO para modelo en ejecución."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    name: str
    model: str
    size: int
    digest: str
    expires_at: datetime | None = None
    size_vram: int = 0


class RunningModelsResponseDto(BaseModel):
    """DTO para lista de modelos en ejecución."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    models: list[RunningModelDto] = Field(default_factory=list)


# ============================================================================
# DTOs para Versión
# ============================================================================

class VersionResponseDto(BaseModel):
    """DTO para respuesta de versión de Ollama."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    version: str


# ============================================================================
# DTOs de Error
# ============================================================================

class OllamaErrorDto(BaseModel):
    """DTO para errores de Ollama."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    error: str
    status_code: int = 500
    details: dict[str, Any] = Field(default_factory=dict)
