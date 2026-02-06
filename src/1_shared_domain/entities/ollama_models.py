"""
Entidades del dominio para integración con Ollama.

Este módulo define las entidades de negocio relacionadas con modelos de IA,
generación de texto, chat y embeddings usando Ollama.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MessageRole(str, Enum):
    """Roles de mensajes en conversaciones."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ModelStatus(str, Enum):
    """Estados de modelos en Ollama."""
    AVAILABLE = "available"
    PULLING = "pulling"
    RUNNING = "running"
    NOT_FOUND = "not_found"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class OllamaChatMessage:
    """
    Mensaje individual en una conversación.

    Value Object que representa un mensaje con rol y contenido.
    """
    role: MessageRole
    content: str

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("El contenido del mensaje no puede estar vacío")

    def to_dict(self) -> dict[str, str]:
        """Convierte el mensaje a diccionario para la API."""
        return {
            "role": self.role.value,
            "content": self.content
        }


@dataclass(frozen=False, slots=True)
class OllamaModel:
    """
    Entidad que representa un modelo de IA en Ollama.

    Contiene información del modelo, su estado y metadatos.
    """
    name: str
    model: str
    size: int
    digest: str
    modified_at: datetime | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("El nombre del modelo no puede estar vacío")
        if self.size < 0:
            raise ValueError("El tamaño del modelo no puede ser negativo")

    def get_size_mb(self) -> float:
        """Retorna el tamaño del modelo en MB."""
        return self.size / (1024 * 1024)

    def get_size_gb(self) -> float:
        """Retorna el tamaño del modelo en GB."""
        return self.size / (1024 * 1024 * 1024)

    def is_large_model(self) -> bool:
        """Determina si es un modelo grande (>10GB)."""
        return self.get_size_gb() > 10


@dataclass(frozen=True, slots=True)
class OllamaChatResponse:
    """
    Respuesta de una operación de chat.

    Value Object que encapsula la respuesta del modelo.
    """
    model: str
    message: OllamaChatMessage
    done: bool
    total_duration: int | None = None
    load_duration: int | None = None
    prompt_eval_count: int | None = None
    eval_count: int | None = None
    eval_duration: int | None = None

    def get_total_duration_seconds(self) -> float:
        """Retorna la duración total en segundos."""
        if self.total_duration is None:
            return 0.0
        return self.total_duration / 1_000_000_000

    def get_tokens_per_second(self) -> float:
        """Calcula tokens por segundo."""
        if self.eval_count is None or self.eval_duration is None or self.eval_duration == 0:
            return 0.0
        return (self.eval_count * 1_000_000_000) / self.eval_duration


@dataclass(frozen=True, slots=True)
class OllamaGenerateResponse:
    """
    Respuesta de una operación de generación de texto.

    Value Object que encapsula la respuesta de generación.
    """
    model: str
    response: str
    done: bool
    context: list[int] = field(default_factory=list)
    total_duration: int | None = None
    load_duration: int | None = None
    prompt_eval_count: int | None = None
    eval_count: int | None = None
    eval_duration: int | None = None

    def get_total_duration_seconds(self) -> float:
        """Retorna la duración total en segundos."""
        if self.total_duration is None:
            return 0.0
        return self.total_duration / 1_000_000_000

    def get_tokens_per_second(self) -> float:
        """Calcula tokens por segundo."""
        if self.eval_count is None or self.eval_duration is None or self.eval_duration == 0:
            return 0.0
        return (self.eval_count * 1_000_000_000) / self.eval_duration


@dataclass(frozen=True, slots=True)
class OllamaEmbedding:
    """
    Embedding generado por un modelo.

    Value Object que representa un vector de embedding.
    """
    model: str
    embedding: list[float]
    total_duration: int | None = None
    load_duration: int | None = None
    prompt_eval_count: int | None = None

    def __post_init__(self) -> None:
        if not self.embedding:
            raise ValueError("El embedding no puede estar vacío")

    def get_dimension(self) -> int:
        """Retorna la dimensión del embedding."""
        return len(self.embedding)

    def get_total_duration_seconds(self) -> float:
        """Retorna la duración total en segundos."""
        if self.total_duration is None:
            return 0.0
        return self.total_duration / 1_000_000_000


@dataclass(frozen=False, slots=True)
class OllamaModelInfo:
    """
    Información detallada de un modelo.

    Entidad que contiene metadatos y detalles técnicos del modelo.
    """
    modelfile: str
    parameters: str
    template: str
    details: dict[str, Any] = field(default_factory=dict)
    model_info: dict[str, Any] = field(default_factory=dict)

    def get_parameter_count(self) -> str:
        """Extrae el conteo de parámetros del modelo."""
        return self.details.get("parameter_size", "unknown")

    def get_quantization_level(self) -> str:
        """Extrae el nivel de cuantización."""
        return self.details.get("quantization_level", "unknown")

    def get_family(self) -> str:
        """Extrae la familia del modelo."""
        return self.details.get("family", "unknown")


@dataclass(frozen=False, slots=True)
class OllamaRunningModel:
    """
    Modelo actualmente en ejecución.

    Entidad que representa un modelo cargado en memoria.
    """
    name: str
    model: str
    size: int
    digest: str
    expires_at: datetime | None = None
    size_vram: int = 0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("El nombre del modelo no puede estar vacío")

    def get_vram_mb(self) -> float:
        """Retorna el uso de VRAM en MB."""
        return self.size_vram / (1024 * 1024)

    def get_vram_gb(self) -> float:
        """Retorna el uso de VRAM en GB."""
        return self.size_vram / (1024 * 1024 * 1024)

    def is_expiring_soon(self, minutes: int = 5) -> bool:
        """Determina si el modelo expirará pronto."""
        if self.expires_at is None:
            return False
        time_diff = (self.expires_at - datetime.now()).total_seconds()
        return 0 < time_diff < (minutes * 60)
