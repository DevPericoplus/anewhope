"""DTOs para gestión de estados de versiones de proyectos.

Maneja los estados (Abierta, Bloqueada, Protegida, Final) y eventos
de transición en versiones de proyectos.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class VersionState(str, Enum):
    """Estados posibles de una versión."""
    
    ABIERTA = "Abierta"
    BLOQUEADA = "Bloqueada"
    PROTEGIDA = "Protegida"
    FINAL = "Final"


class VersionEventType(str, Enum):
    """Tipos de eventos en versiones."""
    
    VERSION_CREADA = "VERSION_CREADA"
    VERSION_BLOQUEADA = "VERSION_BLOQUEADA"
    VERSION_DESBLOQUEADA = "VERSION_DESBLOQUEADA"
    ENTRENAMIENTO_SOLICITADO = "ENTRENAMIENTO_SOLICITADO"
    ENTRENAMIENTO_CONFIRMADO = "ENTRENAMIENTO_CONFIRMADO"
    VERSION_REVERTIDA = "VERSION_REVERTIDA"
    CARPETA_CREADA = "CARPETA_CREADA"
    CARPETA_RENOMBRADA = "CARPETA_RENOMBRADA"
    CARPETA_ELIMINADA = "CARPETA_ELIMINADA"
    ARCHIVO_SUBIDO = "ARCHIVO_SUBIDO"
    ARCHIVO_RENOMBRADO = "ARCHIVO_RENOMBRADO"
    ARCHIVO_ELIMINADO = "ARCHIVO_ELIMINADO"


class VersionStateDto(BaseModel):
    """DTO para el estado completo de una versión."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID del registro")
    id_organizacion: int = Field(..., description="ID de la organización")
    id_proyecto: int = Field(..., description="ID del proyecto")
    id_version: int = Field(..., description="Número de versión")
    state: VersionState = Field(default=VersionState.ABIERTA, description="Estado actual")
    state_internal: Optional[str] = Field(None, description="Estado interno del flujo")
    protected: bool = Field(default=False, description="Si está protegida (no editable)")
    size: int = Field(default=0, alias="size_bytes", description="Tamaño total en bytes")
    final_c: bool = Field(default=False, description="Aceptación cliente")
    final_i: bool = Field(default=False, description="Aceptación interna")
    revision_interna: bool = Field(default=False, description="Revisión interna en curso")
    propuesta_mejoras: bool = Field(default=False, description="Propuesta de mejoras generada")
    entrenamiento_inicial_solicitado: bool = Field(default=False, description="Entrenamiento solicitado")
    entrenamiento_inicial_completado: bool = Field(default=False, description="Entrenamiento completado")
    entrenamiento_inicial_fecha: Optional[str] = Field(None, description="Fecha completado entrenamiento")
    evaluacion_entrenamiento: bool = Field(default=False, description="Evaluación en curso")
    reentrenamiento: bool = Field(default=False, description="Reentrenamiento en curso")
    optimizacion: bool = Field(default=False, description="Optimización en curso")
    control_calidad_aprobado: bool = Field(default=False, description="Control calidad aprobado")
    generacion_llm_solicitada: bool = Field(default=False, description="Generación LLM solicitada")
    generacion_llm_completada: bool = Field(default=False, description="Generación LLM completada")
    generacion_llm_fecha: Optional[str] = Field(None, description="Fecha generación LLM")
    ruta_fichero_modelo: Optional[str] = Field(None, description="Ruta del fichero modelo")
    notificacion_descarga_enviada: bool = Field(default=False, description="Notificación enviada")
    notificacion_descarga_fecha: Optional[str] = Field(None, description="Fecha notificación")
    updated_by: Optional[int] = Field(None, description="Usuario que actualizó")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Última actualización")


class CreateVersionStateRequest(BaseModel):
    """Request para crear un estado de versión (al crear versión nueva)."""
    
    id_organizacion: int = Field(..., description="ID de la organización")
    id_proyecto: int = Field(..., description="ID del proyecto")
    id_version: int = Field(..., description="Número de versión")
    user_id: int = Field(..., description="Usuario que crea la versión")
    state: VersionState = Field(default=VersionState.ABIERTA, description="Estado inicial")


class UpdateVersionStateRequest(BaseModel):
    """Request para actualizar el estado de una versión."""
    
    state: Optional[VersionState] = Field(None, description="Nuevo estado")
    protected: Optional[bool] = Field(None, description="Cambiar protección")
    final_c: Optional[bool] = Field(None, description="Flag cliente")
    final_i: Optional[bool] = Field(None, description="Flag interno")
    user_id: int = Field(..., description="Usuario que hace el cambio")


class VersionStateResponse(BaseModel):
    """Response con el estado completo de una versión."""
    
    success: bool = Field(..., description="Si la operación fue exitosa")
    message: str = Field(..., description="Mensaje descriptivo")
    data: Optional[VersionStateDto] = Field(None, description="Datos del estado")


class VersionEventDto(BaseModel):
    """DTO para un evento de versión."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="ID del evento")
    id_organizacion: int = Field(..., description="ID de la organización")
    id_proyecto: int = Field(..., description="ID del proyecto")
    id_version: int = Field(..., description="Número de versión")
    evento: VersionEventType = Field(..., description="Tipo de evento")
    mensaje: str = Field(..., description="Descripción del evento")
    user_id: int = Field(..., description="Usuario que generó el evento")
    user_name: Optional[str] = Field(None, description="Nombre del usuario")
    old_state: Optional[str] = Field(None, description="Estado anterior")
    new_state: Optional[str] = Field(None, description="Estado nuevo")
    metadata: Optional[dict] = Field(None, description="Información adicional")
    timestamp: datetime = Field(..., description="Cuándo ocurrió")


class CreateVersionEventRequest(BaseModel):
    """Request para crear un evento de versión."""
    
    id_organizacion: int = Field(..., description="ID de la organización")
    id_proyecto: int = Field(..., description="ID del proyecto")
    id_version: int = Field(..., description="Número de versión")
    evento: VersionEventType = Field(..., description="Tipo de evento")
    mensaje: str = Field(..., description="Descripción del evento")
    user_id: int = Field(..., description="Usuario que genera el evento")
    user_name: Optional[str] = Field(None, description="Nombre del usuario")
    old_state: Optional[str] = Field(None, description="Estado anterior")
    new_state: Optional[str] = Field(None, description="Estado nuevo")
    metadata: Optional[dict] = Field(None, description="Metadata adicional")


class VersionEventListResponse(BaseModel):
    """Response con lista de eventos de una versión."""
    
    success: bool = Field(..., description="Si la operación fue exitosa")
    message: str = Field(..., description="Mensaje descriptivo")
    data: list[VersionEventDto] = Field(default_factory=list, description="Lista de eventos")
    total: int = Field(default=0, description="Total de eventos")


class FmanagementListRequest(BaseModel):
    """Request para listar estructura de archivos via fmanagement."""
    
    org_folder: str = Field(..., description="Carpeta organización (ej: ORG00001)")
    prj_folder: str = Field(..., description="Carpeta proyecto (ej: PRJ0001)")
    version_folder: str = Field(..., description="Carpeta versión (ej: v001)")
    user_id: int = Field(..., description="ID del usuario que solicita")
    identity_type_id: int = Field(..., description="Tipo de identidad del usuario")


class FmanagementOperationRequest(BaseModel):
    """Request genérico para operaciones con fmanagement."""
    
    operation: str = Field(..., description="Tipo de operación (create_folder, delete_file, etc)")
    org_folder: str = Field(..., description="Carpeta organización")
    prj_folder: str = Field(..., description="Carpeta proyecto")
    version_folder: str = Field(..., description="Carpeta versión")
    subfolders: Optional[str] = Field(None, description="Subcarpetas relativas")
    filename: Optional[str] = Field(None, description="Nombre de archivo")
    extfile: Optional[str] = Field(None, description="Extensión de archivo")
    new_filename: Optional[str] = Field(None, description="Nuevo nombre (para rename)")
    user_id: int = Field(..., description="ID del usuario")
    identity_type_id: int = Field(..., description="Tipo de identidad")
    metadata: Optional[dict] = Field(None, description="Metadata adicional")


class FmanagementResponse(BaseModel):
    """Response genérica de operaciones con fmanagement."""
    
    success: bool = Field(..., description="Si la operación fue exitosa")
    message: str = Field(..., description="Mensaje descriptivo")
    data: Optional[dict] = Field(None, description="Datos de respuesta")


class CreateVersionFullRequest(BaseModel):
    """Request completo para crear una nueva versión (DB + fmanagement)."""
    
    id_organizacion: int = Field(..., description="ID de la organización")
    id_proyecto: int = Field(..., description="ID del proyecto")
    version_name: str = Field(..., description="Nombre de la versión (ej: V001)")
    user_id: int = Field(..., description="Usuario que crea la versión")
    identity_type_id: int = Field(..., description="Tipo de identidad del usuario")
    descripcion: Optional[str] = Field(None, description="Descripción de la versión")
    clone_from_version: Optional[int] = Field(None, description="ID versión a clonar (opcional)")


class CreateVersionFullResponse(BaseModel):
    """Response completa de creación de versión."""
    
    success: bool = Field(..., description="Si la operación fue exitosa")
    message: str = Field(..., description="Mensaje descriptivo")
    version_id: Optional[int] = Field(None, description="ID de la versión creada")
    version_state_id: Optional[int] = Field(None, description="ID del estado creado")
    fmanagement_result: Optional[dict] = Field(None, description="Resultado de fmanagement")
