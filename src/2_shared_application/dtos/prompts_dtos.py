"""DTOs for Prompt Management (Gestión de Prompts).

This module defines data transfer objects for managing AI prompts across 4 categories:
- identidades: Defines the AI's role/identity
- contexto: Provides domain-specific context
- solicitudes: Defines the task/request type
- modalidad: Specifies response format/style
"""

from datetime import datetime
from pydantic import BaseModel, Field


class PromptDto(BaseModel):
    """DTO for complete prompt data (response)."""

    id_prompt: int
    name: str
    description: str | None = None
    prompt: str
    active: bool
    created_at: datetime
    updated_at: datetime
    created_by: int | None = None
    updated_by: int | None = None


class CreatePromptDto(BaseModel):
    """DTO for creating a new prompt (request)."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    prompt: str = Field(..., min_length=1)


class UpdatePromptDto(BaseModel):
    """DTO for updating an existing prompt (request)."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    prompt: str = Field(..., min_length=1)


class TogglePromptDto(BaseModel):
    """DTO for toggling prompt active status (request)."""

    active: bool


class PromptListItemDto(BaseModel):
    """DTO for prompt list view (simplified response)."""

    id_prompt: int
    name: str
    description: str | None = None
    active: bool
    created_at: datetime
    updated_at: datetime
