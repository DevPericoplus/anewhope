"""DTOs del foro LAIM Web."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ImageKind = Literal["avatar_catalog", "avatar_user", "post_attachment"]
LogRotation = Literal["weekly", "daily", "none"]


class LaimForumImageUploadDto(BaseModel):
    """Payload de subida de imagen (base64)."""

    model_config = ConfigDict(extra="ignore")

    file_name: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., min_length=3, max_length=100)
    data_base64: str = Field(..., min_length=1)
    image_kind: ImageKind = "post_attachment"


class LaimForumImageResponseDto(BaseModel):
    """Metadatos de imagen persistida."""

    id: int = 0
    image_kind: ImageKind = "post_attachment"
    file_name: str = ""
    mime_type: str = ""
    file_size: int = 0
    url_path: str = ""


class LaimForumUserProfileDto(BaseModel):
    """Perfil extendido del usuario en el foro."""

    model_config = ConfigDict(extra="ignore")

    user_id: int
    user_name: str = ""
    avatar_image_id: int | None = None
    avatar_url: str = ""
    forum_display_name: str | None = None
    signature_md: str | None = None
    reputation_avg: float = 0.0
    reputation_votes: int = 0
    notify_mentions: bool = True
    notify_replies: bool = True


class LaimForumUserProfileUpdateDto(BaseModel):
    """Actualización de perfil de foro."""

    model_config = ConfigDict(extra="ignore")

    forum_display_name: str | None = Field(default=None, max_length=100)
    signature_md: str | None = Field(default=None, max_length=2000)
    avatar_image_id: int | None = None
    notify_mentions: bool | None = None
    notify_replies: bool | None = None


class LaimForumCategoryDto(BaseModel):
    """Categoría del foro."""

    id: str
    nombre: str
    descripcion: str = ""
    orden: int = 0
    activa: bool = True


class LaimForumCategoryUpsertDto(BaseModel):
    """Alta/edición de categoría."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., min_length=1, max_length=64)
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: str = Field(default="", max_length=500)
    orden: int = 0
    activa: bool = True


class LaimForumSubcategoryDto(BaseModel):
    """Subcategoría del foro."""

    id: str
    categoria_id: str
    nombre: str
    descripcion: str = ""
    orden: int = 0
    activa: bool = True
    ban_seconds: int = 86400
    log_rotation: LogRotation = "weekly"


class LaimForumSubcategoryUpsertDto(BaseModel):
    """Alta/edición de subcategoría."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., min_length=1, max_length=64)
    categoria_id: str = Field(..., min_length=1, max_length=64)
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: str = Field(default="", max_length=500)
    orden: int = 0
    activa: bool = True
    ban_seconds: int = Field(default=86400, ge=60)
    log_rotation: LogRotation = "weekly"


class LaimForumPrefixDto(BaseModel):
    """Prefijo de hilo."""

    id: str
    texto: str
    color_scheme: str = "green"
    activo: bool = True


class LaimForumPrefixUpsertDto(BaseModel):
    """Alta/edición de prefijo."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., min_length=1, max_length=64)
    texto: str = Field(..., min_length=1, max_length=50)
    color_scheme: str = Field(default="green", max_length=30)
    activo: bool = True


class LaimForumThreadCreateDto(BaseModel):
    """Creación de hilo."""

    model_config = ConfigDict(extra="ignore")

    subcategory_id: str = Field(..., min_length=1, max_length=64)
    prefix_id: str | None = Field(default=None, max_length=64)
    titulo: str = Field(..., min_length=1, max_length=255)
    cuerpo_md: str = Field(..., min_length=1)
    image_ids: list[int] = Field(default_factory=list, max_length=3)


class LaimForumThreadUpdateDto(BaseModel):
    """Edición de hilo."""

    model_config = ConfigDict(extra="ignore")

    titulo: str | None = Field(default=None, max_length=255)
    cuerpo_md: str | None = None
    prefix_id: str | None = Field(default=None, max_length=64)
    fijado: bool | None = None
    cerrado: bool | None = None
    image_ids: list[int] | None = None


class LaimForumPostCreateDto(BaseModel):
    """Creación de respuesta."""

    model_config = ConfigDict(extra="ignore")

    cuerpo_md: str = Field(..., min_length=1)
    image_ids: list[int] = Field(default_factory=list, max_length=3)


class LaimForumPostUpdateDto(BaseModel):
    """Edición de respuesta."""

    model_config = ConfigDict(extra="ignore")

    cuerpo_md: str = Field(..., min_length=1)
    image_ids: list[int] | None = None


class LaimForumPostRatingDto(BaseModel):
    """Valoración de respuesta (1-5)."""

    model_config = ConfigDict(extra="ignore")

    valoracion: int = Field(..., ge=1, le=5)


class LaimForumThreadRatingDto(BaseModel):
    """Valoración de hilo (1-5, una por usuario)."""

    model_config = ConfigDict(extra="ignore")

    valoracion: int = Field(..., ge=1, le=5)


class LaimForumAvatarCatalogItemDto(BaseModel):
    """Entrada del catálogo de avatares."""

    id: int
    image_id: int
    label: str
    is_default: bool = False
    sort_order: int = 0
    active: bool = True
    url_path: str = ""


class LaimForumAvatarCatalogCreateDto(BaseModel):
    """Alta de avatar en catálogo (imagen ya subida)."""

    model_config = ConfigDict(extra="ignore")

    image_id: int = Field(..., gt=0)
    label: str = Field(..., min_length=1, max_length=100)
    is_default: bool = False
    sort_order: int = 0


class LaimForumSettingsDto(BaseModel):
    """Configuración singleton de moderación."""

    anunciar_ban_en_log: bool = True
    plantilla_ban: str = ""
    plantilla_eliminacion: str = ""


class LaimForumWordRuleDto(BaseModel):
    """Regla automática de palabras."""

    id: int = 0
    palabra: str
    accion: str
    mensaje: str = ""
    activo: bool = True


class LaimForumWordRuleUpsertDto(BaseModel):
    """Alta/edición de regla."""

    model_config = ConfigDict(extra="ignore")

    palabra: str = Field(..., min_length=1, max_length=100)
    accion: str = Field(..., min_length=1, max_length=50)
    mensaje: str = Field(default="", max_length=500)
    activo: bool = True


class LaimForumAllowedUrlDto(BaseModel):
    """Dominio permitido en markdown."""

    id: int = 0
    dominio: str
    descripcion: str = ""
    activo: bool = True


class LaimForumAllowedUrlUpsertDto(BaseModel):
    """Alta/edición de URL permitida."""

    model_config = ConfigDict(extra="ignore")

    dominio: str = Field(..., min_length=1, max_length=255)
    descripcion: str = Field(default="", max_length=255)
    activo: bool = True


class LaimForumModeratorDto(BaseModel):
    """Moderador asignado a subcategoría."""

    id: int
    user_id: int
    user_name: str
    subcategory_id: str
    activo: bool = True


class LaimForumModeratorAssignDto(BaseModel):
    """Asignación de moderador."""

    model_config = ConfigDict(extra="ignore")

    user_id: int = Field(..., gt=0)
    user_name: str = Field(..., min_length=1, max_length=255)
    subcategory_id: str = Field(..., min_length=1, max_length=64)


class LaimForumBanDto(BaseModel):
    """Baneo activo o histórico."""

    id: int
    user_id: int
    subcategory_id: str
    motivo: str
    moderador_user_id: int | None = None
    moderador_user_name: str | None = None
    expires_at: str | None = None
    activo: bool = True
    automatico: bool = False


class LaimForumNotificationDto(BaseModel):
    """Notificación pendiente."""

    id: int
    tipo: str
    titulo: str
    mensaje: str
    category_id: str | None = None
    subcategory_id: str | None = None
    thread_id: int | None = None
    post_id: int | None = None
    created_at: str = ""


class LaimForumHealthDto(BaseModel):
    """Estado del subsistema foro."""

    ok: bool = True
    activo: bool = True
    categorias: int = 0
    subcategorias: int = 0
    hilos: int = 0
    respuestas: int = 0


class LaimForumAdminSubcategoryStatsDto(BaseModel):
    """Actividad agregada por subcategoría."""

    subcategory_id: str
    subcategory_name: str
    category_name: str
    hilos: int = 0
    respuestas: int = 0


class LaimForumAdminTopUserDto(BaseModel):
    """Usuario con mayor reputación en el foro."""

    user_id: int
    display_name: str
    reputation_avg: float = 0.0
    reputation_votes: int = 0


class LaimForumAdminStatsDto(BaseModel):
    """Estadísticas globales del foro (panel admin)."""

    categorias: int = 0
    subcategorias: int = 0
    hilos: int = 0
    respuestas: int = 0
    valoraciones: int = 0
    valoracion_promedio: float = 0.0
    usuarios_activos: int = 0
    baneos_activos: int = 0
    infracciones_hoy: int = 0
    adjuntos: int = 0
    subcategorias_detalle: list[LaimForumAdminSubcategoryStatsDto] = Field(
        default_factory=list
    )
    top_reputacion: list[LaimForumAdminTopUserDto] = Field(default_factory=list)
