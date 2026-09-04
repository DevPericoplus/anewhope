"""Capa de API para recibir peticiones del frontend."""

from __future__ import annotations

import asyncio
import logging
import importlib.util
import os
import sys
from pathlib import Path

# Logger a nivel de módulo para uso en endpoints
logger = logging.getLogger(__name__)

SESSION_TOKEN_NOT_PROVIDED_MSG = "Token de sesión no proporcionado"
MEDIA_TYPE_ZIP = "application/zip"
JOB_TEMPLATES_SUPERADMIN_ONLY_MSG = "Solo SuperAdmin puede gestionar plantillas de jobs"
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Annotated, Any, AsyncIterator

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

# Cargar función de configuración de entorno
_repo_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_repo_root / "src"))

# Import with sys.path manipulation for directories starting with digits
import importlib.util
_env_settings_path = _repo_root / "src" / "2_shared_application" / "config" / "env_settings.py"
_spec = importlib.util.spec_from_file_location("env_settings", _env_settings_path)
_env_settings_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_env_settings_module)
get_env_value = _env_settings_module.get_env_value

try:
    from .broker_backend_client import BrokerBackendClient
    from .interfacetobackend import BackendCommunicationError, InterfaceToBackend
    from .routermiddleware import (
        BusinessRuleError,
        MSG_LAIM_INVALID_CREDENTIALS,
        RouterMiddleware,
        SessionContext,
        TokenExpiredError,
        TokenValidationError,
        UserCreationResult,
        get_jwt_settings,
    )
except ImportError:  # pragma: no cover - soporte para ejecuciones fuera de paquete
    from broker_backend_client import BrokerBackendClient
    from interfacetobackend import BackendCommunicationError, InterfaceToBackend
    from routermiddleware import (
        BusinessRuleError,
        MSG_LAIM_INVALID_CREDENTIALS,
        RouterMiddleware,
        SessionContext,
        TokenExpiredError,
        TokenValidationError,
        UserCreationResult,
        get_jwt_settings,
    )


class ProcessDataRequest(BaseModel):
    """Payload de entrada para el procesamiento."""

    payload: dict[str, Any] = Field(default_factory=dict)


class ProcessDataResponse(BaseModel):
    """Respuesta del backend procesada."""

    result: dict[str, Any]
    message: str


class LoginRequest(BaseModel):
    """Payload de autenticación para login."""

    user_name: str
    password: str
    otp: str


class LoginOtpRequest(BaseModel):
    """Payload para solicitar el envío del OTP."""

    user_name: str
    password: str


class LoginResponse(BaseModel):
    """Respuesta del login con tokens."""

    user_id: int
    organization_id: int
    identity_type_id: int
    access_token: str
    session_token: str
    access_expires_at: int
    session_expires_at: int


class LoginOtpResponse(BaseModel):
    """Respuesta de solicitud de OTP.
    
    Devuelve los datos necesarios para que el frontend envíe el SMS.
    El frontend es responsable de enviar el SMS a la API externa (Infobip).
    """

    success: bool
    otp: str | None = None  # Código OTP de 4 dígitos
    phone_number: str | None = None  # Teléfono en formato internacional (+34...)
    otp_exempt: bool = False  # True si el usuario está exento de OTP


class RefreshTokenResponse(BaseModel):
    """Respuesta de renovación de tokens."""

    user_id: int
    organization_id: int
    access_token: str
    session_token: str
    access_expires_at: int
    session_expires_at: int


class ModelDownloadOtpRequest(BaseModel):
    """Request para solicitar OTP de descarga de modelo."""

    organization_id: int
    project_id: int
    version_id: int


class ModelDownloadOtpResponse(BaseModel):
    """Response con datos de OTP para descarga de modelo.

    El frontend/backoffice enviará el SMS con el OTP.
    """

    success: bool
    otp: str | None = None
    phone_number: str | None = None
    phone_masked: str | None = None
    message: str | None = None


class ModelDownloadValidateOtpRequest(BaseModel):
    """Request para validar OTP y obtener token de descarga."""

    organization_id: int
    project_id: int
    version_id: int
    otp: str


class ModelDownloadValidateOtpResponse(BaseModel):
    """Response con token de descarga de modelo."""

    success: bool
    download_token: str | None = None
    fmanagement_url: str | None = None
    expires_in: int | None = None
    expires_at: int | None = None
    message: str | None = None


class ModelListRequest(BaseModel):
    """Request para listar modelos disponibles."""

    organization_id: int | None = None  # None = todas las organizaciones (solo backoffice)


class ModelListResponse(BaseModel):
    """Response con lista de modelos disponibles."""

    success: bool
    models: list[dict[str, Any]] = Field(default_factory=list)
    message: str | None = None


class PermissionsResponse(BaseModel):
    """Respuesta con permisos del usuario."""

    user_id: int
    organization_id: int
    identity_type_id: int | None = None
    permissions: list[dict[str, Any]] = Field(default_factory=list)
    low_level_permissions: dict[str, Any] = Field(default_factory=dict)


class SecurityLogRequest(BaseModel):
    """Payload para registrar logs de seguridad."""

    action: str
    entity_id: int | None = None
    ip: str
    user_agent: str


class SecurityLogResponse(BaseModel):
    """Respuesta del log de seguridad."""

    success: bool


class LogoutResponse(BaseModel):
    """Respuesta del cierre de sesión."""

    success: bool


class LaimLoginRequest(BaseModel):
    """Payload de login LAIM."""

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LaimRegisterRequest(BaseModel):
    """Payload de registro LAIM."""

    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)
    password_confirm: str = Field(..., min_length=8)
    email: str = Field(..., min_length=5)
    full_name: str = Field(..., min_length=2)
    mobile: str | None = None
    hcaptcha_token: str = ""


class LaimContactScreenshotRequest(BaseModel):
    """Captura adjunta en base64."""

    file_name: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., min_length=3, max_length=100)
    data_base64: str = Field(..., min_length=1)


class LaimContactMessageRequest(BaseModel):
    """Payload del formulario de contacto LAIM."""

    usage_mode: str = Field(..., min_length=1, max_length=50)
    affected_user_info: str = Field(default="", max_length=500)
    message_body: str = Field(..., min_length=10, max_length=10000)
    reply_email: str = Field(..., min_length=5, max_length=255)
    screenshot: LaimContactScreenshotRequest | None = None


class OrganizationCheckRequest(BaseModel):
    """Payload para validar existencia de organización."""

    organization_name: str


class OrganizationCheckResponse(BaseModel):
    """Respuesta de existencia de organización."""

    exists: bool


class OrganizationCreateRequest(BaseModel):
    """Payload para crear organización."""

    organization_name: str
    organization_email: str
    organization_tlf: str | None = ""
    organization_address: str | None = ""
    organization_country: str | None = ""
    organization_state: str | None = ""


class OrganizationCreateResponse(BaseModel):
    """Respuesta de creación de organización."""

    organization_id: int
    organization_acronym: str = ""


class UserProfileUpdateRequest(BaseModel):
    """Payload para actualizar la ficha del usuario autenticado."""

    user_email: str
    user_mobile: str
    contact_info: dict[str, Any] = Field(default_factory=dict)
    billing_info: dict[str, Any] = Field(default_factory=dict)


class OrganizationProfileUpdateRequest(BaseModel):
    """Payload para actualizar datos de organización (sin acrónimo)."""

    organization_name: str
    organization_email: str = ""
    organization_tlf: str = ""
    organization_address: str = ""
    organization_country: str = ""
    organization_state: str = ""


class UserCreateRequest(BaseModel):
    """Payload para crear usuario."""

    organization_id: int = 0
    identity_type_id: int | None = None
    account_kind: str | None = None
    user_name: str
    user_password: str
    user_email: str
    user_mobile: str
    user_otp: str
    active: bool = True
    blocked: bool = False
    contact_info: dict[str, Any] = Field(default_factory=dict)
    billing_info: dict[str, Any] = Field(default_factory=dict)


class UserCreateResponse(BaseModel):
    """Respuesta de creación de usuario."""

    user_id: int
    organization_id: int
    identity_type_id: int


class OrganizationUserItem(BaseModel):
    """Usuario de una organización para listado."""

    user_id: int
    user_name: str
    active: bool


class OrganizationUsersResponse(BaseModel):
    """Respuesta de listado de usuarios de organización."""

    users: list[OrganizationUserItem]
    total: int


class UserStatusUpdateRequest(BaseModel):
    """Request para actualizar estado activo de un usuario."""

    active: bool


class UserStatusUpdateResponse(BaseModel):
    """Respuesta de actualización de estado de usuario."""

    user_id: int
    active: bool
    message: str


class UserExistsRequest(BaseModel):
    """Request para verificar existencia de usuario."""

    user_name: str


class UserExistsResponse(BaseModel):
    """Respuesta de verificación de existencia de usuario."""

    exists: bool
    user_name: str


class UserByEmailRequest(BaseModel):
    """Request para obtener usuario por email."""

    email: str


class UserByEmailResponse(BaseModel):
    """Respuesta con datos del usuario por email."""

    found: bool
    user_id: int | None = None
    user_name: str | None = None
    user_email: str | None = None
    user_mobile: str | None = None
    organization_id: int | None = None


class UpdatePasswordRequest(BaseModel):
    """Request para actualizar contraseña y OTP."""

    email: str
    new_password: str
    new_otp: str


class UpdatePasswordResponse(BaseModel):
    """Respuesta de actualización de contraseña."""

    success: bool
    message: str


def _configure_logging() -> None:
    """Configura el logging del middleware con salida a console.log."""

    logs_dir = Path(__file__).resolve().parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Archivo console.log unificado para soporte
    console_log_path = logs_dir / "console.log"

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    # Formato legible para técnicos de soporte
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | middleware      | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler para console.log (unificado)
    console_file_handler = logging.FileHandler(console_log_path, encoding="utf-8")
    console_file_handler.setFormatter(formatter)

    # Handler de consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_file_handler, console_handler],
    )


def _extract_bearer_token(raw_token: str | None) -> str:
    """Extrae el token sin el prefijo Bearer si es necesario."""

    if raw_token is None:
        raise TokenValidationError("Token de acceso no proporcionado")
    if raw_token.startswith("Bearer "):
        return raw_token.removeprefix("Bearer ").strip()
    return raw_token.strip()


def _get_request_metadata(request: Request) -> tuple[str, str]:
    """Extrae IP y user-agent del request."""

    ip_address = request.client.host if request.client else ""
    user_agent = request.headers.get("user-agent", "")
    return ip_address, user_agent


def get_client_app(
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> str:
    """Extrae el header X-Client-App de la petición."""

    return client_app or "unknown"


def get_session_context(
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    access_token: Annotated[str | None, Header(alias="Authorization")] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
    organization_override: Annotated[str | None, Header(alias="X-Organization-Id")] = None,
) -> SessionContext:
    """Valida la sesión y retorna el contexto.

    Si el header X-Organization-Id está presente (backoffice admin gestionando
    otra organización), se reemplaza el organization_id de la sesión.
    """
    from dataclasses import replace as _dc_replace

    try:
        access_value = _extract_bearer_token(access_token)
        if session_token is None:
            raise TokenValidationError(SESSION_TOKEN_NOT_PROVIDED_MSG)
        session = router.validate_session(access_value, session_token)

        # Override org_id para backoffice admin gestionando otra organización
        if organization_override:
            try:
                override_id = int(organization_override)
                if override_id > 0 and override_id != session.organization_id:
                    session = _dc_replace(session, organization_id=override_id)
            except (ValueError, TypeError):
                pass  # Header inválido, ignorar

        return session
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except TokenValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


async def get_http_client() -> AsyncIterator[httpx.AsyncClient]:
    """Provee un cliente HTTP asíncrono."""

    async with httpx.AsyncClient() as client:
        yield client


def get_interface_client(
    client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> InterfaceToBackend:
    """Inyecta la interfaz hacia el backend."""

    base_url = os.environ.get("BACKEND_BASE_URL", "http://localhost:8001")
    return InterfaceToBackend(client=client, base_url=base_url)


def _get_broker_base_url() -> str:
    """Obtiene la URL base del broker backend.
    
    Prioridad:
    1. Variable de entorno BROKER_BACKEND_BASE_URL
    2. Valor de env.yaml (broker_backend_base_url)
    3. Valor de protected_values.py
    4. Fallback a localhost:8008
    """

    env_settings = _load_env_settings_module("middleware_env_settings")
    # get_env_value carga env.yaml y lee de os.environ
    env_value = env_settings.get_env_value("BROKER_BACKEND_BASE_URL", "")
    if env_value:
        return env_value
    # Fallback a protected_values.py
    return env_settings.get_protected_value(
        "broker_backend_base_url", "http://localhost:8008"
    )


def _load_env_settings_module(module_name: str) -> Any:
    """Carga el módulo de configuración compartida."""

    module_path = (
        Path(__file__).resolve().parents[3]
        / "src/2_shared_application/config/env_settings.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar el módulo de configuración")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def get_broker_client() -> BrokerBackendClient:
    """Inyecta el cliente hacia el broker backend."""

    return BrokerBackendClient(base_url=_get_broker_base_url())


def get_router_middleware(
    interface: Annotated[InterfaceToBackend, Depends(get_interface_client)],
    broker_client: Annotated[BrokerBackendClient, Depends(get_broker_client)],
    client_app: Annotated[str, Depends(get_client_app)],
) -> RouterMiddleware:
    """Inyecta el orquestador de middleware."""

    broker_client.set_client_app(client_app)
    return RouterMiddleware(
        interface=interface,
        jwt_settings=get_jwt_settings(),
        broker_client=broker_client,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Gestiona el ciclo de vida de la aplicación."""

    _configure_logging()
    broker_client = get_broker_client()
    async with httpx.AsyncClient() as client:
        interface = InterfaceToBackend(
            client=client,
            base_url=os.environ.get("BACKEND_BASE_URL", "http://localhost:8001"),
        )
        router = RouterMiddleware(
            interface=interface,
            jwt_settings=get_jwt_settings(),
            broker_client=broker_client,
        )
        sync_task = asyncio.create_task(router.run_periodic_sync())
        try:
            yield
        finally:
            sync_task.cancel()
            with suppress(asyncio.CancelledError):
                await sync_task
            broker_client.close()


app = FastAPI(title="Middleware Frontend", lifespan=lifespan)


@app.post("/login/request-otp", response_model=LoginOtpResponse)
async def request_login_otp_endpoint(
    request: LoginOtpRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
) -> LoginOtpResponse:
    """Endpoint para obtener datos de OTP del usuario.
    
    El frontend recibe el OTP y teléfono, y es responsable de enviar el SMS
    directamente a la API externa (Infobip).
    
    Flujo: Frontend → Middleware → (valida credenciales) → devuelve OTP + teléfono
    """

    try:
        ip_address, user_agent = _get_request_metadata(http_request)
        result = router.request_login_otp(
            user_name=request.user_name,
            password=request.password,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        router.log_activity_action(
            action="Solicitar OTP",
            entity_id=None,
            ip=ip_address,
            user_agent=user_agent,
        )
        return LoginOtpResponse(
            success=result.get("success", False),
            otp=result.get("otp"),
            phone_number=result.get("phone_number"),
            otp_exempt=result.get("otp_exempt", False),
        )
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/login", response_model=LoginResponse)
async def login_endpoint(
    request: LoginRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
) -> LoginResponse:
    """Endpoint de autenticación con OTP."""

    try:
        ip_address, user_agent = _get_request_metadata(http_request)
        tokens = router.authenticate_user(
            user_name=request.user_name,
            password=request.password,
            otp=request.otp,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        router.log_activity_action(
            action="Login",
            entity_id=tokens.user_id,
            ip=ip_address,
            user_agent=user_agent,
        )
        return LoginResponse(
            user_id=tokens.user_id,
            organization_id=tokens.organization_id,
            identity_type_id=tokens.identity_type_id,
            access_token=tokens.access_token,
            session_token=tokens.session_token,
            access_expires_at=tokens.access_expires_at,
            session_expires_at=tokens.session_expires_at,
        )
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/refresh-token", response_model=RefreshTokenResponse)
async def refresh_token_endpoint(
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> RefreshTokenResponse:
    """Endpoint de renovación de tokens."""

    try:
        if session_token is None:
            raise TokenValidationError(SESSION_TOKEN_NOT_PROVIDED_MSG)
        ip_address, user_agent = _get_request_metadata(http_request)
        tokens = router.refresh_tokens(
            session_token, ip_address=ip_address, user_agent=user_agent
        )
        router.log_activity_action(
            action="Refresh token",
            entity_id=tokens.user_id,
            ip=ip_address,
            user_agent=user_agent,
        )
        return RefreshTokenResponse(
            user_id=tokens.user_id,
            organization_id=tokens.organization_id,
            access_token=tokens.access_token,
            session_token=tokens.session_token,
            access_expires_at=tokens.access_expires_at,
            session_expires_at=tokens.session_expires_at,
        )
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except TokenValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@app.post("/logout", response_model=LogoutResponse)
async def logout_endpoint(
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> LogoutResponse:
    """Endpoint para cerrar sesión."""

    try:
        ip_address, user_agent = _get_request_metadata(http_request)
        success = router.logout_session(
            session, ip_address=ip_address, user_agent=user_agent
        )
        router.log_activity_action(
            action="Logout",
            entity_id=session.user_id,
            ip=ip_address,
            user_agent=user_agent,
        )
        return LogoutResponse(success=success)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get("/permissions", response_model=PermissionsResponse)
async def permissions_endpoint(
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> PermissionsResponse:
    """Endpoint para consultar permisos del usuario."""

    try:
        permissions_data = router.get_permissions(session)
        ip_address, user_agent = _get_request_metadata(http_request)
        router.log_activity_action(
            action="Consultar permisos",
            entity_id=session.user_id,
            ip=ip_address,
            user_agent=user_agent,
        )
        return PermissionsResponse(**permissions_data)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/security/log", response_model=SecurityLogResponse)
async def security_log_endpoint(
    request: SecurityLogRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
) -> SecurityLogResponse:
    """Endpoint para registrar logs de seguridad."""

    success = router.log_security_action(
        action=request.action,
        entity_id=request.entity_id,
        ip=request.ip,
        user_agent=request.user_agent,
    )
    ip_address, user_agent = _get_request_metadata(http_request)
    router.log_activity_action(
        action="Log de seguridad",
        entity_id=request.entity_id,
        ip=ip_address,
        user_agent=user_agent,
    )
    return SecurityLogResponse(success=success)


@app.post("/organizations/check-name", response_model=OrganizationCheckResponse)
async def organization_check_endpoint(
    request: OrganizationCheckRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
) -> OrganizationCheckResponse:
    """Endpoint para validar el nombre de organización."""

    exists = router.check_organization_name_exists(request.organization_name)
    ip_address, user_agent = _get_request_metadata(http_request)
    router.log_activity_action(
        action="Validar organización",
        entity_id=None,
        ip=ip_address,
        user_agent=user_agent,
    )
    return OrganizationCheckResponse(exists=exists)


@app.post("/organizations", response_model=OrganizationCreateResponse)
async def organization_create_endpoint(
    request: OrganizationCreateRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
) -> OrganizationCreateResponse:
    """Endpoint para crear una organización."""

    try:
        organization_id = router.create_organization(request.model_dump())
        ip_address, user_agent = _get_request_metadata(http_request)
        router.log_activity_action(
            action="Crear organización",
            entity_id=organization_id,
            ip=ip_address,
            user_agent=user_agent,
        )
        return OrganizationCreateResponse(
            organization_id=organization_id,
            organization_acronym=router.get_organization_acronym(organization_id),
        )
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get("/users/me")
def get_my_profile_endpoint(
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> dict[str, Any]:
    """Devuelve la ficha del usuario autenticado."""
    try:
        return router.get_my_profile(session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch("/users/me")
def update_my_profile_endpoint(
    request: UserProfileUpdateRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> dict[str, Any]:
    """Actualiza email, móvil y contacto del usuario autenticado."""
    try:
        return router.update_my_profile(session, request.model_dump())
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch("/organizations/me")
def update_my_organization_endpoint(
    request: OrganizationProfileUpdateRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> dict[str, Any]:
    """Actualiza la organización. Solo el administrador (identity 2)."""
    try:
        return router.update_my_organization(session, request.model_dump())
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/users", response_model=UserCreateResponse)
async def user_create_endpoint(
    request: UserCreateRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
) -> UserCreateResponse:
    """Endpoint para crear usuarios."""

    try:
        result: UserCreationResult = router.create_user(request.model_dump())
        ip_address, user_agent = _get_request_metadata(http_request)
        router.log_activity_action(
            action="Crear usuario",
            entity_id=result.user_id,
            ip=ip_address,
            user_agent=user_agent,
        )
        return UserCreateResponse(
            user_id=result.user_id,
            organization_id=result.organization_id,
            identity_type_id=result.identity_type_id,
        )
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get("/organizations/{organization_id}/users", response_model=OrganizationUsersResponse)
async def get_organization_users_endpoint(
    organization_id: int,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
    identity_type_id: int | None = 5,
    active_only: bool = True,
) -> OrganizationUsersResponse:
    """
    Obtiene los usuarios de una organización filtrados por identity_type_id.
    
    Args:
        organization_id: ID de la organización
        identity_type_id: Filtrar por tipo de identidad (default: 5 = auditores)
        active_only: Si True, solo retorna usuarios activos (default: True)
                     El backoffice usa False para ver también usuarios inactivos
    
    Returns:
        Lista de usuarios con user_id, user_name y active
    """
    try:
        # Validar acceso:
        # - SuperAdmin (identity_type_id=1) puede ver cualquier organización
        # - Otros usuarios solo pueden ver su propia organización
        # Nota: El control de asignaciones se hace en el selector del backoffice,
        # aquí solo validamos que sea SuperAdmin o que esté viendo su org propia
        if session.identity_type_id != 1 and session.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para ver usuarios de esta organización",
            )

        users = router.get_organization_users(organization_id, identity_type_id, active_only)
        ip_address, user_agent = _get_request_metadata(http_request)
        router.log_activity_action(
            action="Listar usuarios organización",
            entity_id=organization_id,
            ip=ip_address,
            user_agent=user_agent,
        )
        return OrganizationUsersResponse(
            users=[
                OrganizationUserItem(
                    user_id=u["user_id"],
                    user_name=u["user_name"],
                    active=u["active"],
                )
                for u in users
            ],
            total=len(users),
        )
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch("/users/{user_id}/status", response_model=UserStatusUpdateResponse)
async def update_user_status_endpoint(
    user_id: int,
    request: UserStatusUpdateRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> UserStatusUpdateResponse:
    """
    Actualiza el estado activo/inactivo de un usuario.
    
    SEGURIDAD: Solo pueden modificar usuarios:
    - SuperAdmin (identity_type_id = 1)
    - Administrador de Organización (identity_type_id = 2)
    - Agente Admin del proyecto (identity_type_id = 10)
    
    Los editores (3), lectores (4), auditores (5) y otros agentes NO pueden.
    """
    # VALIDACIÓN DE SEGURIDAD: Verificar permisos por identity_type_id
    allowed_identity_types = (1, 2, 10)  # SuperAdmin, Admin Org, Agente Admin
    if session.identity_type_id not in allowed_identity_types:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Sin permisos para gestionar usuarios (identity_type_id={session.identity_type_id})",
        )
    
    try:
        # Validar que el usuario a modificar pertenece a la misma organización
        # (SuperAdmin puede modificar usuarios de cualquier organización)
        result = router.update_user_active_status(
            user_id=user_id,
            active=request.active,
            requester_org_id=session.organization_id,
            requester_identity_type_id=session.identity_type_id,
        )
        
        ip_address, user_agent = _get_request_metadata(http_request)
        action = "Habilitar usuario" if request.active else "Deshabilitar usuario"
        router.log_activity_action(
            action=action,
            entity_id=user_id,
            ip=ip_address,
            user_agent=user_agent,
        )
        
        return UserStatusUpdateResponse(
            user_id=result["user_id"],
            active=result["active"],
            message=result["message"],
        )
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@app.post("/users/check-exists", response_model=UserExistsResponse)
async def check_user_exists_endpoint(
    request: UserExistsRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
) -> UserExistsResponse:
    """Verifica si existe un usuario por nombre de usuario.
    
    Flujo: Frontend (aquí) → Middleware → Broker → Backend Core → JSON/MariaDB
    """
    try:
        result = router.check_user_exists(request.user_name)
        ip_address, user_agent = _get_request_metadata(http_request)
        router.log_activity_action(
            action="Verificar usuario existe",
            entity_id=0,
            ip=ip_address,
            user_agent=user_agent,
        )
        return UserExistsResponse(**result)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/users/by-email", response_model=UserByEmailResponse)
async def get_user_by_email_endpoint(
    request: UserByEmailRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
) -> UserByEmailResponse:
    """Obtiene datos de un usuario por email.
    
    Flujo: Frontend (aquí) → Middleware → Broker → Backend Core → JSON/MariaDB
    """
    try:
        result = router.get_user_by_email(request.email)
        ip_address, user_agent = _get_request_metadata(http_request)
        router.log_activity_action(
            action="Buscar usuario por email",
            entity_id=0,
            ip=ip_address,
            user_agent=user_agent,
        )
        return UserByEmailResponse(**result)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/users/update-password", response_model=UpdatePasswordResponse)
async def update_user_password_endpoint(
    request: UpdatePasswordRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
) -> UpdatePasswordResponse:
    """Actualiza contraseña y OTP de un usuario.
    
    Flujo: Frontend (aquí) → Middleware → Broker → Backend Core → JSON/MariaDB
    """
    try:
        result = router.update_user_password(
            email=request.email,
            new_password=request.new_password,
            new_otp=request.new_otp,
        )
        ip_address, user_agent = _get_request_metadata(http_request)
        router.log_activity_action(
            action="Actualizar contraseña",
            entity_id=0,
            ip=ip_address,
            user_agent=user_agent,
        )
        return UpdatePasswordResponse(**result)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/process-data", response_model=ProcessDataResponse)
async def process_data_endpoint(
    request: ProcessDataRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> ProcessDataResponse:
    """Endpoint que recibe peticiones del frontend."""

    try:
        backend_response = await router.process_data(request.payload, session)
        ip_address, user_agent = _get_request_metadata(http_request)
        router.log_activity_action(
            action="Procesar datos",
            entity_id=session.user_id,
            ip=ip_address,
            user_agent=user_agent,
        )
        return ProcessDataResponse(
            result=backend_response, message="Operación exitosa"
        )
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except BackendCommunicationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


# === Endpoints de Training (Backend IA) ===


class TrainerHealthResponse(BaseModel):
    """Respuesta del health check del trainer."""

    status: str
    service: str
    version: str


class VersionCloneRequest(BaseModel):
    """Payload para clonar versión para entrenamiento."""

    id_user: int
    id_organization: int
    id_project: int
    version_path: str


class VersionCloneResponse(BaseModel):
    """Respuesta de clonado de versión."""

    success: bool
    cloned_path: str = ""
    message: str = ""


class TrainingProgressNotification(BaseModel):
    """Notificación de progreso de entrenamiento desde el trainer."""

    id_entrenamiento: int
    phase_key: str          # Clave de la fase principal (ej: "3")
    subfase_key: str        # Clave de la subfase (ej: "3.2")
    subfase_name: str       # Nombre legible (ej: "Chunking")
    status: str             # "in_progress", "completed", "error"
    elapsed_time: str = ""  # Tiempo empleado (ej: "2m 15s")
    error_message: str = ""


class TrainingStartRequest(BaseModel):
    """Payload para iniciar entrenamiento."""

    id_user: int
    id_organization: int
    id_project: int
    version_path: str
    training_params: dict[str, Any] = Field(default_factory=dict)


class TrainingStartResponse(BaseModel):
    """Respuesta de inicio de entrenamiento."""

    success: bool
    training_id: int | None = None
    message: str = ""


class TrainingStopRequest(BaseModel):
    """Payload para detener entrenamiento."""

    training_id: int


class TrainingStopResponse(BaseModel):
    """Respuesta de detención de entrenamiento."""

    success: bool
    message: str = ""


class TrainingStatusResponse(BaseModel):
    """Respuesta con estado del entrenamiento."""

    training_id: int
    status: str
    progress: float = 0.0
    metrics: dict[str, Any] = Field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None


class ModelMetricsResponse(BaseModel):
    """Respuesta con métricas de un modelo."""

    model_id: int
    metrics: dict[str, Any] = Field(default_factory=dict)
    training_history: list[dict[str, Any]] = Field(default_factory=list)


class TrainingPermissionsResponse(BaseModel):
    """Respuesta con permisos de entrenamiento."""

    identity_type_id: int
    permissions: dict[str, bool] = Field(default_factory=dict)


class DocumentacionRequest(BaseModel):
    """Payload para análisis de documentación."""

    id_job: int = 0
    id_organizacion: int
    id_proyecto: int
    id_version: int
    id_user: int = 0
    nombre_job: str = ""
    descripcion_job: str = ""
    id_template: int = 0
    template_nombre: str = ""
    modelo_nombre: str = ""
    salida_nombre: str = ""
    estado_nombre: str = ""
    prompt_final: str = ""


class DocumentacionResponse(BaseModel):
    """Respuesta de análisis de documentación (ACK)."""

    success: bool
    message: str = ""
    received_at: str = ""


class EntrenamientoRequest(BaseModel):
    """Payload para solicitud de entrenamiento inicial."""

    id_organizacion: int
    id_proyecto: int
    id_version: int
    id_user: int = 0
    pat_version: str = ""
    # Parámetros opcionales de entrenamiento
    learning_rate: float | None = None
    batch_size: int | None = None
    epochs: int | None = None
    embedding_dimension: int | None = None
    sequence_length: int | None = None
    hidden_units: int | None = None
    dropout_rate: float | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    distance_metric: str | None = None
    top_k: int | None = None
    loss_function: str | None = None
    optimizer: str | None = None
    model_type: str | None = None


class EntrenamientoResponse(BaseModel):
    """Respuesta de solicitud de entrenamiento (ACK)."""

    success: bool
    message: str = ""
    received_at: str = ""
    id_entrenamiento: int = 0  # ID del entrenamiento creado en BD
    collection_name: str = ""  # Nombre de la colección en ChromaDB
    numero_secuencia: int = 0  # Número de secuencia del entrenamiento


class EntrenamientoCancelRequest(BaseModel):
    """Payload para cancelar entrenamiento."""

    id_entrenamiento: int
    motivo: str = "Cancelado por usuario"


class EntrenamientoCancelResponse(BaseModel):
    """Respuesta de cancelación de entrenamiento."""

    success: bool
    message: str = ""


class AutonomousTrainingRequest(BaseModel):
    """Payload para solicitud de entrenamiento autónomo (RAG + LoRA + GGUF)."""

    id_organizacion: int
    id_proyecto: int
    id_version: int
    id_entrenamiento: int  # ID del entrenamiento RAG previo
    id_user: int = 0
    pat_version: str = ""
    collection_name: str = ""  # Nombre de colección ChromaDB


class AutonomousTrainingResponse(BaseModel):
    """Respuesta de solicitud de entrenamiento autónomo (ACK)."""

    success: bool
    message: str = ""
    received_at: str = ""
    id_entrenamiento: int = 0
    training_mode: str = ""  # simulation, test o production


class MetadatosRequest(BaseModel):
    """Payload para análisis de metadatos de ficheros."""

    id_job: int = 0
    id_organizacion: int
    id_proyecto: int
    id_version: int
    id_user: int = 0
    nombre_job: str = ""
    descripcion_job: str = ""
    id_template: int = 0
    template_nombre: str = ""
    modelo_nombre: str = ""
    salida_nombre: str = ""
    estado_nombre: str = ""
    prompt_final: str = ""


class MetadatosResponse(BaseModel):
    """Respuesta de análisis de metadatos (ACK)."""

    success: bool
    message: str = ""
    received_at: str = ""


@app.get("/training/health", response_model=TrainerHealthResponse)
def trainer_health_check_endpoint(
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> TrainerHealthResponse:
    """Health check del servicio trainer."""

    try:
        response = router.trainer_health_check(session)
        return TrainerHealthResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/training/clone-version", response_model=VersionCloneResponse)
def clone_version_for_training_endpoint(
    payload: VersionCloneRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> VersionCloneResponse:
    """Clona una versión para entrenamiento."""

    try:
        response = router.clone_version_for_training(payload.model_dump(), session)
        ip_address, user_agent = _get_request_metadata(http_request)
        router.log_activity_action(
            action="Clonar versión para entrenamiento",
            entity_id=payload.id_project,
            ip=ip_address,
            user_agent=user_agent,
        )
        return VersionCloneResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN
            if "permisos" in str(exc).lower()
            else status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/training/start", response_model=TrainingStartResponse)
def start_training_endpoint(
    payload: TrainingStartRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> TrainingStartResponse:
    """Inicia un proceso de entrenamiento."""

    try:
        response = router.start_training(payload.model_dump(), session)
        ip_address, user_agent = _get_request_metadata(http_request)
        router.log_activity_action(
            action="Iniciar entrenamiento",
            entity_id=payload.id_project,
            ip=ip_address,
            user_agent=user_agent,
        )
        return TrainingStartResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN
            if "permisos" in str(exc).lower()
            else status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/training/stop", response_model=TrainingStopResponse)
def stop_training_endpoint(
    payload: TrainingStopRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> TrainingStopResponse:
    """Detiene un proceso de entrenamiento."""

    try:
        response = router.stop_training(payload.model_dump(), session)
        ip_address, user_agent = _get_request_metadata(http_request)
        router.log_activity_action(
            action="Detener entrenamiento",
            entity_id=payload.training_id,
            ip=ip_address,
            user_agent=user_agent,
        )
        return TrainingStopResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN
            if "permisos" in str(exc).lower()
            else status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get("/training/{training_id}/status", response_model=TrainingStatusResponse)
def get_training_status_endpoint(
    training_id: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> TrainingStatusResponse:
    """Obtiene el estado de un entrenamiento."""

    try:
        response = router.get_training_status(training_id, session)
        return TrainingStatusResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN
            if "permisos" in str(exc).lower()
            else status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@app.get("/training/models", response_model=ModelListResponse)
def list_models_endpoint(
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
    id_organization: int | None = None,
    id_project: int | None = None,
) -> ModelListResponse:
    """Lista modelos entrenados."""

    try:
        response = router.list_models(session, id_organization, id_project)
        return ModelListResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN
            if "permisos" in str(exc).lower()
            else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@app.get("/training/models/{model_id}/metrics", response_model=ModelMetricsResponse)
def get_model_metrics_endpoint(
    model_id: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> ModelMetricsResponse:
    """Obtiene métricas de un modelo."""

    try:
        response = router.get_model_metrics(model_id, session)
        return ModelMetricsResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN
            if "permisos" in str(exc).lower()
            else status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@app.get("/training/permissions", response_model=TrainingPermissionsResponse)
def get_training_permissions_endpoint(
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> TrainingPermissionsResponse:
    """Obtiene permisos de entrenamiento para el usuario actual."""

    try:
        response = router.get_training_permissions(session)
        return TrainingPermissionsResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@app.post("/training/documentacion", response_model=DocumentacionResponse)
def send_documentacion_endpoint(
    request: DocumentacionRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> DocumentacionResponse:
    """Envía solicitud de análisis de documentación al trainer."""

    try:
        response = router.send_documentacion(request.model_dump(), session)
        return DocumentacionResponse(**response)
    except BusinessRuleError as exc:
        # Distinguir error de permisos vs error de comunicación
        error_msg = str(exc).lower()
        if "permisos" in error_msg or "permiso" in error_msg:
            status_code = status.HTTP_403_FORBIDDEN
        else:
            status_code = status.HTTP_502_BAD_GATEWAY
        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc


@app.get("/training/params/{org_id}/{project_id}/{version_id}")
def get_training_params_endpoint(
    org_id: int,
    project_id: int,
    version_id: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
):
    """Endpoint inteligente que devuelve parámetros de entrenamiento.

    Devuelve defaults (primer entrenamiento) o último job (reentrenamiento),
    junto con flags informativos y lista de modelos disponibles.

    Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
    """
    try:
        result = router.get_training_params(
            org_id, project_id, version_id, session
        )
        return result
    except BusinessRuleError as exc:
        error_msg = str(exc).lower()
        if "permisos" in error_msg or "permiso" in error_msg:
            status_code = status.HTTP_403_FORBIDDEN
        else:
            status_code = status.HTTP_502_BAD_GATEWAY
        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc


@app.get("/models/active", tags=["models"])
def list_active_models_endpoint(
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> dict[str, Any]:
    """Lista modelos activos de la BD.

    Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
    """
    try:
        return router.list_active_models(session)
    except BusinessRuleError as exc:
        error_msg = str(exc).lower()
        if "permisos" in error_msg or "permiso" in error_msg:
            status_code = status.HTTP_403_FORBIDDEN
        else:
            status_code = status.HTTP_502_BAD_GATEWAY
        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc


@app.patch("/training/progress")
def update_training_progress_endpoint(
    payload: TrainingProgressNotification,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
) -> dict[str, Any]:
    """Recibe notificaciones de progreso desde el trainer.

    NO requiere validación de sesión ya que viene directamente del trainer.

    Flujo: Trainer → Middleware → Broker → Backend Core
    """
    try:
        return router.update_training_progress(payload.model_dump())
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/training/entrenamientos", response_model=EntrenamientoResponse)
def send_entrenamiento_endpoint(
    request: EntrenamientoRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> EntrenamientoResponse:
    """Envía solicitud de entrenamiento inicial al trainer."""

    try:
        response = router.send_entrenamiento(request.model_dump(), session)

        print("[MIDDLEWARE ENDPOINT] ===== RESPUESTA DEL BROKER =====")
        print(f"[MIDDLEWARE ENDPOINT] Response type: {type(response)}")
        print(f"[MIDDLEWARE ENDPOINT] Response: {response}")
        if isinstance(response, dict):
            print(f"[MIDDLEWARE ENDPOINT] id_entrenamiento: {response.get('id_entrenamiento', 'NO EXISTE')}")
            print(f"[MIDDLEWARE ENDPOINT] collection_name: {response.get('collection_name', 'NO EXISTE')}")
            print(f"[MIDDLEWARE ENDPOINT] numero_secuencia: {response.get('numero_secuencia', 'NO EXISTE')}")

        result = EntrenamientoResponse(**response)

        print("[MIDDLEWARE ENDPOINT] ===== RESPONSE MODEL CREADO =====")
        print(f"[MIDDLEWARE ENDPOINT] result.id_entrenamiento: {result.id_entrenamiento}")
        print(f"[MIDDLEWARE ENDPOINT] result.collection_name: {result.collection_name}")
        print(f"[MIDDLEWARE ENDPOINT] result.numero_secuencia: {result.numero_secuencia}")
        print("[MIDDLEWARE ENDPOINT] ==========================================")

        return result
    except BusinessRuleError as exc:
        error_msg = str(exc).lower()
        if "permisos" in error_msg or "permiso" in error_msg:
            status_code = status.HTTP_403_FORBIDDEN
        else:
            status_code = status.HTTP_502_BAD_GATEWAY
        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc


@app.patch("/training/entrenamientos/cancel", response_model=EntrenamientoCancelResponse)
def cancel_entrenamiento_endpoint(
    request: EntrenamientoCancelRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> EntrenamientoCancelResponse:
    """Cancela un entrenamiento en progreso."""

    try:
        response = router.cancel_entrenamiento(request.model_dump(), session)
        return EntrenamientoCancelResponse(**response)
    except BusinessRuleError as exc:
        error_msg = str(exc).lower()
        if "permisos" in error_msg or "permiso" in error_msg:
            status_code = status.HTTP_403_FORBIDDEN
        else:
            status_code = status.HTTP_502_BAD_GATEWAY
        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc


@app.post("/training/entrenamientos/autonomous", response_model=AutonomousTrainingResponse)
def send_autonomous_training_endpoint(
    request: AutonomousTrainingRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> AutonomousTrainingResponse:
    """Envía solicitud de entrenamiento autónomo al trainer.

    El entrenamiento autónomo ejecuta las fases 6-9:
        Fase 6: Generación de Dataset desde ChromaDB
        Fases 7-8: Fine-tuning con LoRA (solo test/production)
        Fase 9: Exportación a GGUF y empaquetado (solo test/production)
    """

    try:
        response = router.send_autonomous_training(request.model_dump(), session)

        print("[MIDDLEWARE ENDPOINT] ===== RESPUESTA AUTONOMOUS =====")
        print(f"[MIDDLEWARE ENDPOINT] Response: {response}")
        print("[MIDDLEWARE ENDPOINT] ====================================")

        return AutonomousTrainingResponse(**response)
    except BusinessRuleError as exc:
        error_msg = str(exc).lower()
        if "permisos" in error_msg or "permiso" in error_msg:
            status_code = status.HTTP_403_FORBIDDEN
        else:
            status_code = status.HTTP_502_BAD_GATEWAY
        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc


@app.get("/training/entrenamientos/{id_entrenamiento}/autonomous/progress")
def get_autonomous_training_progress_endpoint(
    id_entrenamiento: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> dict[str, Any]:
    """Consulta el progreso del entrenamiento autónomo (fases 6-9).

    Flujo: Backoffice → Middleware → Broker → Backend Core

    Args:
        id_entrenamiento: ID del entrenamiento autónomo a consultar

    Returns:
        Diccionario con success y data (subphases del entrenamiento autónomo)
    """
    try:
        response = router.get_autonomous_training_progress(id_entrenamiento, session)
        return response
    except BusinessRuleError as exc:
        error_msg = str(exc).lower()
        if "permisos" in error_msg or "permiso" in error_msg:
            status_code = status.HTTP_403_FORBIDDEN
        else:
            status_code = status.HTTP_502_BAD_GATEWAY
        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc


@app.get("/training/entrenamientos/{id_entrenamiento}/autonomous/package")
def download_autonomous_package_endpoint(
    id_entrenamiento: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> Response:
    """Descarga el paquete ZIP del modelo autónomo generado.

    Flujo: Backoffice → Middleware → Broker → Trainer

    Args:
        id_entrenamiento: ID del entrenamiento autónomo

    Returns:
        Response con el archivo ZIP
    """
    try:
        response = router.download_autonomous_package(id_entrenamiento, session)

        # Devolver el contenido como Response
        return Response(
            content=response.content,
            media_type=MEDIA_TYPE_ZIP,
            headers={
                "Content-Disposition": response.headers.get("Content-Disposition", "attachment"),
            },
        )
    except BusinessRuleError as exc:
        error_msg = str(exc).lower()
        if "permisos" in error_msg or "permiso" in error_msg:
            status_code = status.HTTP_403_FORBIDDEN
        else:
            status_code = status.HTTP_502_BAD_GATEWAY
        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc


@app.get("/training/entrenamientos/autonomous/packages")
def list_autonomous_packages_endpoint(
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
    id_organizacion: int | None = None,
    id_proyecto: int | None = None,
    id_version: int | None = None,
) -> dict[str, Any]:
    """Lista los paquetes autónomos disponibles para descargar.

    Flujo: Backoffice → Middleware → Broker → Trainer

    Args:
        id_organizacion: Filtrar por organización (opcional)
        id_proyecto: Filtrar por proyecto (opcional)
        id_version: Filtrar por versión (opcional)

    Returns:
        Diccionario con success y lista de paquetes
    """
    try:
        response = router.list_autonomous_packages(session, id_organizacion, id_proyecto, id_version)
        return response
    except BusinessRuleError as exc:
        error_msg = str(exc).lower()
        if "permisos" in error_msg or "permiso" in error_msg:
            status_code = status.HTTP_403_FORBIDDEN
        else:
            status_code = status.HTTP_502_BAD_GATEWAY
        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc


@app.get("/training/entrenamientos/{id_entrenamiento}/progress")
def get_training_progress_endpoint(
    id_entrenamiento: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> dict[str, Any]:
    """Consulta el progreso actual de un entrenamiento.

    Flujo: Backoffice → Middleware → Backend Core

    Args:
        id_entrenamiento: ID del entrenamiento a consultar

    Returns:
        Diccionario con success y data (phases, last_update)
    """
    try:
        response = router.get_training_progress(id_entrenamiento, session)
        return response
    except BusinessRuleError as exc:
        error_msg = str(exc).lower()
        if "permisos" in error_msg or "permiso" in error_msg:
            status_code = status.HTTP_403_FORBIDDEN
        else:
            status_code = status.HTTP_502_BAD_GATEWAY
        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc


@app.post("/training/metadatos", response_model=MetadatosResponse)
def send_metadatos_endpoint(
    request: MetadatosRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> MetadatosResponse:
    """Envía solicitud de análisis de metadatos al trainer."""

    try:
        response = router.send_metadatos(request.model_dump(), session)
        return MetadatosResponse(**response)
    except BusinessRuleError as exc:
        error_msg = str(exc).lower()
        if "permisos" in error_msg or "permiso" in error_msg:
            status_code = status.HTTP_403_FORBIDDEN
        else:
            status_code = status.HTTP_502_BAD_GATEWAY
        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc


# ============================================================================
# Modelos Pydantic para Proyectos
# ============================================================================


class ProjectCreateRequest(BaseModel):
    """Payload para crear un proyecto."""

    nombre: str = Field(..., min_length=1, max_length=200)
    descripcion: str | None = Field(default="", max_length=1000)
    id_organizacion: int
    active: bool = True
    id_flujo: int = 1


class ProjectCreateResponse(BaseModel):
    """Respuesta de creación de proyecto."""

    project_id: int
    nombre: str
    id_organizacion: int
    id_flujo: int


class ProjectUpdateRequest(BaseModel):
    """Payload para actualizar un proyecto.
    
    Campos:
        active: Estado activo/bloqueado (True=activo, False=bloqueado)
        existe: Existencia lógica (True=existe, False=borrado lógico)
    """

    nombre: str | None = None
    descripcion: str | None = None
    active: bool | None = None
    id_flujo: int | None = None
    existe: bool | None = None


class ProjectUpdateResponse(BaseModel):
    """Respuesta de actualización de proyecto."""

    success: bool
    updated: bool
    project_id: int


class ProjectDeleteResponse(BaseModel):
    """Respuesta de eliminación de proyecto."""

    success: bool
    deleted: bool
    project_id: int


class ProjectSupportRequest(BaseModel):
    """Payload para solicitud de soporte de proyecto."""

    project_id: int
    tipo_cambio: str = "Solicitud soporte proyecto"
    descripcion: str | None = "Solicitud de soporte técnico"


class ProjectSupportResponse(BaseModel):
    """Respuesta de solicitud de soporte."""

    success: bool
    cambio_id: int | None = None


# ============================================================================
# MODELOS PARA TICKETS DE SOPORTE
# ============================================================================


class TicketCreateRequest(BaseModel):
    """Payload para crear un ticket de soporte."""

    titulo: str
    consulta: str
    id_proyecto: int | None = None
    id_organizacion: int | None = None


class TicketUpdateRequest(BaseModel):
    """Payload para actualizar un ticket."""

    estado: str | None = None
    prioridad: str | None = None


class TicketRespuestaRequest(BaseModel):
    """Payload para añadir respuesta."""

    respuesta: str


class TicketDto(BaseModel):
    """DTO de ticket."""

    id: int
    titulo: str
    cliente_id: int
    estado: str
    prioridad: str
    fecha_creacion: str
    fecha_actualizacion: str | None = None
    consulta: str | None = None
    respuesta: str | None = None
    autor_consulta_id: int | None = None
    autor_respuesta_id: int | None = None
    fecha_consulta: str | None = None
    fecha_respuesta: str | None = None
    id_proyecto: int | None = None


class TicketCreateResponse(BaseModel):
    """Respuesta de creación de ticket."""

    success: bool
    ticket_id: int
    mensaje: str | None = None


class TicketUpdateResponse(BaseModel):
    """Respuesta de actualización de ticket."""

    success: bool
    updated: bool
    ticket_id: int


class TicketListResponse(BaseModel):
    """Respuesta con lista de tickets."""

    tickets: list[TicketDto]
    total: int


# ============================================================================
# MODELOS PARA CONVERSACIONES Y CAMBIOS
# ============================================================================


class ConversationCreateRequest(BaseModel):
    """Payload para crear una conversación."""

    id_organizacion: int
    id_usuario_cliente: int
    asunto: str = "Consulta sobre proyecto"
    prioridad: str = "media"


class ConversationMessageRequest(BaseModel):
    """Payload para enviar un mensaje."""

    id_usuario_emisor: int
    tipo_emisor: str
    texto_mensaje: str
    id_ticket_referenciado: int | None = None


class ConversationMarkReadRequest(BaseModel):
    """Payload para marcar mensajes como leídos."""

    tipo_lector: str


# ============================================================================
# DTOs para Tecnologías
# ============================================================================


class TecnologiaDto(BaseModel):
    """DTO de tecnología."""

    id: int
    name: str
    descripcion: str
    active: bool


class TecnologiasListResponse(BaseModel):
    """Respuesta con lista de tecnologías."""

    tecnologias: list[TecnologiaDto]
    total: int


class ProyectoTecnologiaDto(BaseModel):
    """DTO de asignación proyecto-tecnología."""

    id: int
    id_proyecto: int
    id_tecnologia: int
    coste_base: str | None = None
    tecnologia_name: str | None = None


class ProyectoTecnologiaResponse(BaseModel):
    """Respuesta de asignación de tecnología."""

    success: bool
    asignacion: ProyectoTecnologiaDto | None = None
    mensaje: str | None = None


class AsignarTecnologiaRequest(BaseModel):
    """Request para asignar tecnología a proyecto."""

    id_tecnologia: int
    coste_base: str = "17% sobre base"


class ProyectoTecnologiaAsignadaDto(BaseModel):
    """DTO para mostrar proyecto con su tecnología asignada."""

    project_id: int
    project_name: str
    tecnologia_id: int | None = None
    tecnologia_name: str | None = None


class TecnologiasAsignadasResponse(BaseModel):
    """Respuesta con lista de proyectos y sus tecnologías asignadas."""

    asignaciones: list[ProyectoTecnologiaAsignadaDto]
    total: int


# ========================================================================
# DTOs para Gestión de Versiones
# ========================================================================


class VersionDto(BaseModel):
    """DTO de versión de proyecto."""

    id_version: int
    id_proyecto: int
    id_organizacion: int
    version_folder: str  # Formato "v001", "v002", etc.


class VersionesListResponse(BaseModel):
    """Respuesta con lista de versiones de un proyecto."""

    versiones: list[VersionDto]
    total: int


class CrearVersionRequest(BaseModel):
    """Request para crear una nueva versión."""

    id_proyecto: int
    id_organizacion: int


class CrearVersionResponse(BaseModel):
    """Respuesta de creación de versión."""

    success: bool
    version: VersionDto | None = None
    mensaje: str | None = None


# ============================================================================
# DTOs de Estados de Versión y fmanagement
# ============================================================================


class VersionStateDto(BaseModel):
    """Estado de una versión de proyecto."""

    id: int
    id_organizacion: int
    id_proyecto: int
    id_version: int
    state: str  # "Abierta", "Bloqueada", "Protegida", "Final"
    state_internal: str | None = None
    protected: bool
    size: int  # Changed from size_bytes to match backend/broker
    final_c: bool
    final_i: bool
    revision_interna: bool = False
    propuesta_mejoras: bool = False
    entrenamiento_inicial_solicitado: bool = False
    entrenamiento_inicial_completado: bool = False
    entrenamiento_inicial_fecha: str | None = None
    evaluacion_entrenamiento: bool = False
    reentrenamiento: bool = False
    optimizacion: bool = False
    control_calidad_aprobado: bool = False
    generacion_llm_solicitada: bool = False
    generacion_llm_completada: bool = False
    generacion_llm_fecha: str | None = None
    ruta_fichero_modelo: str | None = None
    notificacion_descarga_enviada: bool = False
    notificacion_descarga_fecha: str | None = None
    updated_by: int | None = None
    created_at: str
    updated_at: str


class CreateVersionStateRequest(BaseModel):
    """Request para crear estado de versión."""

    id_organizacion: int
    id_proyecto: int
    id_version: int
    state: str = "Abierta"
    protected: bool = False
    size_bytes: int = 0
    final_c: bool = False
    final_i: bool = False
    updated_by_user_id: int | None = None


class UpdateVersionStateRequest(BaseModel):
    """Request para actualizar estado de versión."""

    state: str | None = None
    protected: bool | None = None
    size_bytes: int | None = None
    final_c: bool | None = None
    final_i: bool | None = None
    updated_by_user_id: int | None = None


class VersionStateResponse(BaseModel):
    """Response con estado de versión."""

    success: bool
    data: VersionStateDto | None = None
    message: str | None = None


class VersionEventDto(BaseModel):
    """Evento de versión para auditoría."""

    id: int
    id_organizacion: int
    id_proyecto: int
    id_version: int
    evento: str
    mensaje: str | None
    user_id: int
    user_name: str | None
    old_state: str | None
    new_state: str | None
    metadata: dict[str, Any] | None
    timestamp: str


class CreateVersionEventRequest(BaseModel):
    """Request para crear evento de versión."""

    id_organizacion: int
    id_proyecto: int
    id_version: int
    evento: str
    mensaje: str | None = None
    user_id: int
    user_name: str | None = None
    old_state: str | None = None
    new_state: str | None = None
    metadata: dict[str, Any] | None = None


class VersionEventsResponse(BaseModel):
    """Response con lista de eventos."""

    success: bool
    events: list[VersionEventDto]
    total: int
    mensaje: str | None = None


class FmanagementListRequest(BaseModel):
    """Request para listar estructura fmanagement."""

    org_folder: str
    prj_folder: str
    version_folder: str


class FmanagementItemDto(BaseModel):
    """Item de estructura fmanagement."""

    name: str
    is_dir: bool
    size_bytes: int | None = None
    size_kb: float | None = None
    items: list['FmanagementItemDto'] | None = None  # Estructura recursiva para carpetas

    # Campos opcionales para mantener compatibilidad
    type: str | None = None  # "folder" | "file"
    path: str | None = None
    size: int | None = None
    modified: str | None = None


class FmanagementListResponse(BaseModel):
    """Response de listado fmanagement."""

    success: bool
    items: list[FmanagementItemDto]
    mensaje: str | None = None


class FmanagementOperationRequest(BaseModel):
    """Request para operación genérica fmanagement."""

    operation: str  # "create_folder", "rename_folder", "delete_folder", etc.
    params: dict[str, Any]


class FmanagementOperationResponse(BaseModel):
    """Response de operación fmanagement."""

    success: bool
    data: dict[str, Any] | None = None
    mensaje: str | None = None


class CreateVersionFullRequest(BaseModel):
    """Request para crear versión completa (DB + fmanagement)."""

    id_organizacion: int
    nombre_version: str
    descripcion: str | None = None
    user_id: int
    user_name: str
    identity_type_id: int
    clone_from_version_id: int | None = None
    initial_state: str = "Abierta"
    protected: bool = False
    final_c: bool = False
    final_i: bool = False


class CreateVersionFullResponse(BaseModel):
    """Response de creación de versión completa."""

    success: bool
    version: VersionDto | None = None
    state: VersionStateDto | None = None
    mensaje: str | None = None


class GenerateFileTokenRequest(BaseModel):
    """Request para generar token de operación de archivo."""

    project_id: int
    version_id: int
    operation: str  # "upload" o "download"
    relative_path: str = ""  # Ruta relativa dentro de la versión
    organization_id: int = 0  # Override org (backoffice admin managing other orgs)


class GenerateFileTokenResponse(BaseModel):
    """Response con token de operación de archivo."""

    success: bool
    token: str
    fmanagement_url: str
    expires_in: int
    expires_at: int
    mensaje: str | None = None


class ProjectDto(BaseModel):
    """DTO de proyecto.
    
    Campos:
        active: Estado activo/bloqueado (True=activo, False=bloqueado)
        existe: Existencia lógica (True=existe, False=borrado lógico)
    """

    id: int
    nombre: str
    descripcion: str | None = ""
    id_organizacion: int
    active: bool = True
    id_flujo: int = 1
    flujo_nombre: str | None = None
    flujo_emoji: str | None = None
    existe: bool = True


class ProjectListResponse(BaseModel):
    """Respuesta de lista de proyectos."""

    projects: list[ProjectDto]
    total: int


# ============================================================================
# Endpoints de Proyectos
# ============================================================================


@app.get("/projects/organization/{organization_id}", response_model=ProjectListResponse)
def get_organization_projects_endpoint(
    organization_id: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
    include_deleted: bool = False,
) -> ProjectListResponse:
    """Obtiene los proyectos de una organización.

    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Args:
        organization_id: ID de la organización
        include_deleted: Si True, incluye proyectos con existe=false
    """
    try:
        response = router.get_organization_projects(
            organization_id, session, include_deleted=include_deleted
        )
        return ProjectListResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN
            if "permisos" in str(exc).lower()
            else status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/projects", response_model=ProjectCreateResponse)
def create_project_endpoint(
    request: ProjectCreateRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> ProjectCreateResponse:
    """Crea un nuevo proyecto.

    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Valida permiso: project_create
    """
    # SECURITY BY DESIGN: Validar permiso antes de ejecutar
    if not router.has_low_level_permission(session, "project_create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sin permisos para crear proyectos",
        )

    try:
        response = router.create_project(request.model_dump(), session)
        ip_address, user_agent = _get_request_metadata(http_request)
        router.log_activity_action(
            action="Crear proyecto",
            entity_id=response.get("project_id", 0),
            ip=ip_address,
            user_agent=user_agent,
        )
        return ProjectCreateResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch("/projects/{project_id}", response_model=ProjectUpdateResponse)
def update_project_endpoint(
    project_id: int,
    request: ProjectUpdateRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> ProjectUpdateResponse:
    """Actualiza un proyecto existente.

    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Valida permiso: project_update
    """
    # SECURITY BY DESIGN: Validar permiso antes de ejecutar
    if not router.has_low_level_permission(session, "project_update"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sin permisos para actualizar proyectos",
        )

    try:
        update_data = {k: v for k, v in request.model_dump().items() if v is not None}
        response = router.update_project(project_id, update_data, session)
        ip_address, user_agent = _get_request_metadata(http_request)
        router.log_activity_action(
            action="Actualizar proyecto",
            entity_id=project_id,
            ip=ip_address,
            user_agent=user_agent,
        )
        return ProjectUpdateResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.delete("/projects/{project_id}", response_model=ProjectDeleteResponse)
def delete_project_endpoint(
    project_id: int,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> ProjectDeleteResponse:
    """Elimina un proyecto.

    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Valida permiso: project_delete
    """
    # SECURITY BY DESIGN: Validar permiso antes de ejecutar
    if not router.has_low_level_permission(session, "project_delete"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sin permisos para eliminar proyectos",
        )

    try:
        response = router.delete_project(project_id, session)
        ip_address, user_agent = _get_request_metadata(http_request)
        router.log_activity_action(
            action="Eliminar proyecto",
            entity_id=project_id,
            ip=ip_address,
            user_agent=user_agent,
        )
        return ProjectDeleteResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/projects/{project_id}/support", response_model=ProjectSupportResponse)
def request_project_support_endpoint(
    project_id: int,
    request: ProjectSupportRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> ProjectSupportResponse:
    """Registra una solicitud de soporte para un proyecto.

    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    """
    try:
        response = router.request_project_support(
            project_id,
            request.tipo_cambio,
            request.descripcion or "",
            session,
        )
        ip_address, user_agent = _get_request_metadata(http_request)
        router.log_activity_action(
            action="Solicitud soporte proyecto",
            entity_id=project_id,
            ip=ip_address,
            user_agent=user_agent,
        )
        return ProjectSupportResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# MODELOS PARA GESTIÓN DE ROLES DE USUARIO EN PROYECTOS
# ============================================================================


class ProjectRoleDto(BaseModel):
    """DTO de rol de usuario en proyecto."""

    id: int | None = None
    id_usuario: int
    id_proyecto: int
    id_organizacion: int
    id_rol: int
    rol_nombre: str | None = None
    proyecto_nombre: str | None = None
    active: bool = True


class UserProjectRolesResponse(BaseModel):
    """Respuesta con roles de un usuario en proyectos."""

    user_id: int
    organization_id: int
    roles: list[ProjectRoleDto]
    total: int


class ProjectRoleBaseDto(BaseModel):
    """DTO de rol base para proyectos (catálogo maestro).
    
    Información reutilizable para selectores de roles y validaciones de seguridad.
    """

    id: int  # 0=Sin asignar, 3=Editor, 4=Lector, 5=Auditor
    nombre_rol: str
    descripcion: str | None = None


class ProjectRolesBaseResponse(BaseModel):
    """Respuesta con catálogo de roles base para proyectos."""

    roles: list[ProjectRoleBaseDto]
    total: int


class AssignUserToProjectRequest(BaseModel):
    """Payload para asignar usuario a proyecto."""

    id_usuario: int
    id_proyecto: int
    id_organizacion: int
    id_rol: int


class AssignUserToProjectResponse(BaseModel):
    """Respuesta de asignación de usuario a proyecto."""

    success: bool
    message: str
    id_usuario: int
    id_proyecto: int
    id_rol: int
    created: bool


class RemoveUserFromProjectRequest(BaseModel):
    """Payload para quitar usuario de proyecto."""

    id_usuario: int
    id_proyecto: int
    id_organizacion: int


class RemoveUserFromProjectResponse(BaseModel):
    """Respuesta de quitar usuario de proyecto."""

    success: bool
    message: str
    id_usuario: int
    id_proyecto: int


# ============================================================================
# ENDPOINTS DE GESTIÓN DE ROLES DE USUARIO EN PROYECTOS
# ============================================================================


@app.get(
    "/project-roles-base",
    response_model=ProjectRolesBaseResponse,
    tags=["project-roles"],
)
def get_project_roles_base_endpoint(
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: SessionContext = Depends(get_session_context),
) -> ProjectRolesBaseResponse:
    """Obtiene el catálogo maestro de roles base para proyectos.

    SECURITY: Requiere sesión activa.
    
    Información reutilizable para selectores de roles y validaciones de seguridad.
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Roles disponibles:
        - 0: Sin asignar
        - 3: Editor
        - 4: Lector
        - 5: Auditor
    """
    _logger = logging.getLogger(__name__)
    _logger.info("[middleware] Consultando catálogo de roles base")

    try:
        response = router.get_project_roles_base(session)
        return ProjectRolesBaseResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get(
    "/users/{user_id}/project-roles",
    response_model=UserProjectRolesResponse,
    tags=["project-roles"],
)
def get_user_project_roles_endpoint(
    user_id: int,
    organization_id: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: SessionContext = Depends(get_session_context),
) -> UserProjectRolesResponse:
    """Obtiene los roles de un usuario en proyectos de una organización.

    SECURITY: Requiere sesión activa.
    """
    _logger = logging.getLogger(__name__)
    _logger.info(
        "[middleware] Consultando roles de usuario %s en org %s",
        user_id,
        organization_id,
    )

    try:
        response = router.get_user_project_roles(user_id, organization_id, session)
        return UserProjectRolesResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post(
    "/project-roles/assign",
    response_model=AssignUserToProjectResponse,
    tags=["project-roles"],
)
def assign_user_to_project_endpoint(
    request: AssignUserToProjectRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: SessionContext = Depends(get_session_context),
) -> AssignUserToProjectResponse:
    """Asigna un usuario a un proyecto con un rol específico.

    SECURITY: Requiere permiso user_update (asignar usuarios).
    Solo identity_type_id < 3 (SuperAdmin, Admin) o 10 (Agent Admin) pueden asignar.
    """
    _logger = logging.getLogger(__name__)

    # Validación de permisos - Security by Design
    if not router.has_low_level_permission(session, "user_update"):
        _logger.warning(
            "[middleware] Intento de asignar usuario sin permiso user_id=%s",
            session.user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sin permiso para asignar usuarios a proyectos",
        )

    _logger.info(
        "[middleware] Asignando usuario %s a proyecto %s con rol %s",
        request.id_usuario,
        request.id_proyecto,
        request.id_rol,
    )

    try:
        response = router.assign_user_to_project(request.model_dump(), session)
        return AssignUserToProjectResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post(
    "/project-roles/remove",
    response_model=RemoveUserFromProjectResponse,
    tags=["project-roles"],
)
def remove_user_from_project_endpoint(
    request: RemoveUserFromProjectRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: SessionContext = Depends(get_session_context),
) -> RemoveUserFromProjectResponse:
    """Quita un usuario de un proyecto (desactiva la asignación).

    SECURITY: Requiere permiso user_update (gestionar usuarios).
    Solo identity_type_id < 3 (SuperAdmin, Admin) o 10 (Agent Admin) pueden quitar.
    """
    _logger = logging.getLogger(__name__)

    # Validación de permisos - Security by Design
    if not router.has_low_level_permission(session, "user_update"):
        _logger.warning(
            "[middleware] Intento de quitar usuario sin permiso user_id=%s",
            session.user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sin permiso para quitar usuarios de proyectos",
        )

    _logger.info(
        "[middleware] Quitando usuario %s de proyecto %s",
        request.id_usuario,
        request.id_proyecto,
    )

    try:
        response = router.remove_user_from_project(request.model_dump(), session)
        return RemoveUserFromProjectResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# ENDPOINTS DE TICKETS DE SOPORTE
# ============================================================================


@app.post("/tickets", response_model=TicketCreateResponse, tags=["tickets"])
def create_ticket_endpoint(
    request: TicketCreateRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> TicketCreateResponse:
    """Crea un nuevo ticket de soporte.

    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    """
    _logger = logging.getLogger(__name__)
    _logger.info(
        "[middleware] Creando ticket: titulo=%s user_id=%s",
        request.titulo,
        session.user_id,
    )

    try:
        response = router.create_ticket(request.model_dump(), session)
        return TicketCreateResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get(
    "/tickets/organization/{organization_id}",
    response_model=TicketListResponse,
    tags=["tickets"],
)
def get_organization_tickets_endpoint(
    organization_id: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> TicketListResponse:
    """Obtiene los tickets de una organización."""
    _logger = logging.getLogger(__name__)
    _logger.info(
        "[middleware] Consultando tickets org_id=%s",
        organization_id,
    )

    try:
        response = router.get_organization_tickets(organization_id, session)
        return TicketListResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get("/tickets/{ticket_id}", response_model=TicketDto, tags=["tickets"])
def get_ticket_detail_endpoint(
    ticket_id: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> TicketDto:
    """Obtiene el detalle de un ticket específico."""
    _logger = logging.getLogger(__name__)
    _logger.info("[middleware] Consultando ticket_id=%s", ticket_id)

    try:
        response = router.get_ticket_detail(ticket_id, session)
        return TicketDto(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch("/tickets/{ticket_id}", response_model=TicketUpdateResponse, tags=["tickets"])
def update_ticket_endpoint(
    ticket_id: int,
    request: TicketUpdateRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> TicketUpdateResponse:
    """Actualiza estado/prioridad de un ticket (solo Backoffice)."""
    _logger = logging.getLogger(__name__)
    _logger.info(
        "[middleware] Actualizando ticket_id=%s data=%s",
        ticket_id,
        request.model_dump(),
    )

    try:
        update_data = {k: v for k, v in request.model_dump().items() if v is not None}
        response = router.update_ticket(ticket_id, update_data, session)
        return TicketUpdateResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post(
    "/tickets/{ticket_id}/respuesta",
    response_model=TicketUpdateResponse,
    tags=["tickets"],
)
def add_ticket_response_endpoint(
    ticket_id: int,
    request: TicketRespuestaRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> TicketUpdateResponse:
    """Añade respuesta a un ticket (solo Backoffice)."""
    _logger = logging.getLogger(__name__)
    _logger.info("[middleware] Añadiendo respuesta a ticket_id=%s", ticket_id)

    try:
        response = router.add_ticket_response(ticket_id, request.respuesta, session)
        return TicketUpdateResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# ENDPOINTS DE CONVERSACIONES Y CAMBIOS
# ============================================================================


@app.get("/conversations/user/{user_id}", tags=["conversations"])
def get_user_conversation_endpoint(
    user_id: int,
    org_id: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> dict:
    """Busca conversación abierta de un usuario."""
    try:
        return router.get_user_conversation(user_id, org_id, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/conversations", tags=["conversations"])
def create_conversation_endpoint(
    request: ConversationCreateRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> dict:
    """Crea una nueva conversación."""
    try:
        return router.create_conversation(request.model_dump(), session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get("/conversations/{conversation_id}/messages", tags=["conversations"])
def get_conversation_messages_endpoint(
    conversation_id: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> list[dict]:
    """Obtiene los mensajes de una conversación."""
    try:
        return router.get_conversation_messages(conversation_id, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/conversations/{conversation_id}/messages", tags=["conversations"])
def send_conversation_message_endpoint(
    conversation_id: int,
    request: ConversationMessageRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> dict:
    """Envía un mensaje en una conversación."""
    try:
        return router.send_conversation_message(
            conversation_id, request.model_dump(), session
        )
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/conversations/{conversation_id}/mark-read", tags=["conversations"])
def mark_conversation_read_endpoint(
    conversation_id: int,
    request: ConversationMarkReadRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> dict:
    """Marca mensajes como leídos."""
    try:
        return router.mark_conversation_read(
            conversation_id, request.tipo_lector, session
        )
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get("/cambios/organization/{org_id}", tags=["cambios"])
def get_cambios_calendar_endpoint(
    org_id: int,
    mes: int | None = None,
    anio: int | None = None,
    proyecto_id: int | None = None,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)] = None,
    session: Annotated[SessionContext, Depends(get_session_context)] = None,
) -> list[dict]:
    """Obtiene eventos del calendario."""
    try:
        return router.get_cambios_calendar(
            org_id, session, mes=mes, anio=anio, proyecto_id=proyecto_id
        )
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# CONVERSACIONES - BACKOFFICE (gestión por organización)
# ============================================================================


class JoinConversationMwRequest(BaseModel):
    user_id: int


class UpdatePriorityMwRequest(BaseModel):
    prioridad: str


class UpdateStateMwRequest(BaseModel):
    estado: str
    user_id: int


class TicketInteractionMwRequest(BaseModel):
    user_id: int
    cliente_id: int
    respuesta: str = ""
    nuevo_estado: str = ""
    estado_actual: str = ""
    titulo_ticket: str = ""


@app.get(
    "/conversations/organization/{org_id}",
    tags=["conversations"],
)
def get_organization_conversations_endpoint(
    org_id: int,
    solo_activas: bool = True,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)] = None,
    session: Annotated[SessionContext, Depends(get_session_context)] = None,
) -> list[dict]:
    """Obtiene conversaciones de una organización (backoffice)."""
    try:
        return router.get_organization_conversations(
            org_id, session, solo_activas=solo_activas
        )
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc),
        ) from exc


@app.post(
    "/conversations/{conversation_id}/join",
    tags=["conversations"],
)
def join_conversation_endpoint(
    conversation_id: int,
    request: JoinConversationMwRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)] = None,
    session: Annotated[SessionContext, Depends(get_session_context)] = None,
) -> dict:
    """Un usuario interno se une a una conversación."""
    try:
        return router.join_conversation(
            conversation_id, request.model_dump(), session
        )
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc),
        ) from exc


@app.get(
    "/conversations/{conversation_id}/detail",
    tags=["conversations"],
)
def get_conversation_detail_endpoint(
    conversation_id: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)] = None,
    session: Annotated[SessionContext, Depends(get_session_context)] = None,
) -> dict:
    """Obtiene detalle de una conversación."""
    try:
        return router.get_conversation_detail(conversation_id, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc),
        ) from exc


@app.patch(
    "/conversations/{conversation_id}/priority",
    tags=["conversations"],
)
def update_conversation_priority_endpoint(
    conversation_id: int,
    request: UpdatePriorityMwRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)] = None,
    session: Annotated[SessionContext, Depends(get_session_context)] = None,
) -> dict:
    """Actualiza la prioridad de una conversación."""
    try:
        return router.update_conversation_priority(
            conversation_id, request.model_dump(), session
        )
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc),
        ) from exc


@app.patch(
    "/conversations/{conversation_id}/state",
    tags=["conversations"],
)
def update_conversation_state_endpoint(
    conversation_id: int,
    request: UpdateStateMwRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)] = None,
    session: Annotated[SessionContext, Depends(get_session_context)] = None,
) -> dict:
    """Actualiza el estado de una conversación."""
    try:
        return router.update_conversation_state(
            conversation_id, request.model_dump(), session
        )
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc),
        ) from exc


@app.get(
    "/tickets/{ticket_id}/details",
    tags=["tickets"],
)
def get_ticket_details_endpoint(
    ticket_id: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)] = None,
    session: Annotated[SessionContext, Depends(get_session_context)] = None,
) -> dict:
    """Obtiene detalles de un ticket."""
    try:
        return router.get_ticket_details(ticket_id, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc),
        ) from exc


@app.post(
    "/tickets/{ticket_id}/interactions",
    tags=["tickets"],
)
def save_ticket_interaction_endpoint(
    ticket_id: int,
    request: TicketInteractionMwRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)] = None,
    session: Annotated[SessionContext, Depends(get_session_context)] = None,
) -> dict:
    """Guarda interacción de ticket."""
    try:
        return router.save_ticket_interaction(
            ticket_id, request.model_dump(), session
        )
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc),
        ) from exc


# ============================================================================
# ENDPOINTS DE TECNOLOGÍAS
# ============================================================================


@app.get("/tecnologias", response_model=TecnologiasListResponse, tags=["tecnologias"])
def get_tecnologias_endpoint(
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> TecnologiasListResponse:
    """Obtiene todas las tecnologías disponibles."""
    _logger = logging.getLogger(__name__)
    _logger.info("[middleware] Consultando tecnologías")

    try:
        response = router.get_tecnologias(session)
        return TecnologiasListResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get(
    "/proyectos/{project_id}/tecnologia",
    response_model=ProyectoTecnologiaResponse,
    tags=["tecnologias"],
)
def get_proyecto_tecnologia_endpoint(
    project_id: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> ProyectoTecnologiaResponse:
    """Obtiene la tecnología asignada a un proyecto."""
    _logger = logging.getLogger(__name__)
    _logger.info("[middleware] Consultando tecnología de proyecto %s", project_id)

    try:
        response = router.get_proyecto_tecnologia(project_id, session)
        return ProyectoTecnologiaResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post(
    "/proyectos/{project_id}/tecnologia",
    response_model=ProyectoTecnologiaResponse,
    tags=["tecnologias"],
)
def asignar_tecnologia_endpoint(
    project_id: int,
    request: AsignarTecnologiaRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> ProyectoTecnologiaResponse:
    """Asigna una tecnología a un proyecto (primera asignación - Frontend)."""
    _logger = logging.getLogger(__name__)
    _logger.info(
        "[middleware] Asignando tecnología %s a proyecto %s",
        request.id_tecnologia,
        project_id,
    )

    try:
        response = router.asignar_tecnologia(project_id, request.model_dump(), session)
        return ProyectoTecnologiaResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch(
    "/proyectos/{project_id}/tecnologia",
    response_model=ProyectoTecnologiaResponse,
    tags=["tecnologias"],
)
def actualizar_tecnologia_endpoint(
    project_id: int,
    request: AsignarTecnologiaRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> ProyectoTecnologiaResponse:
    """Actualiza la tecnología de un proyecto (solo Backoffice)."""
    _logger = logging.getLogger(__name__)
    _logger.info(
        "[middleware] Actualizando tecnología de proyecto %s a %s",
        project_id,
        request.id_tecnologia,
    )

    try:
        response = router.actualizar_tecnologia(project_id, request.model_dump(), session)
        return ProyectoTecnologiaResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get(
    "/organizaciones/{org_id}/tecnologias-asignadas",
    response_model=TecnologiasAsignadasResponse,
    tags=["tecnologias"],
)
def get_tecnologias_asignadas_org_endpoint(
    org_id: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> TecnologiasAsignadasResponse:
    """Obtiene todas las tecnologías asignadas a proyectos de una organización."""
    _logger = logging.getLogger(__name__)
    _logger.info("[middleware] Consultando tecnologías asignadas para organización %s", org_id)

    # Validar que el usuario pertenece a la organización solicitada
    if session.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para ver tecnologías de esta organización",
        )

    try:
        response = router.get_tecnologias_asignadas_org(org_id, session)
        return TecnologiasAsignadasResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ========================================================================
# ENDPOINTS DE VERSIONES
# ========================================================================


@app.get(
    "/proyectos/{project_id}/versiones",
    response_model=VersionesListResponse,
    tags=["versiones"],
)
def get_project_versions_endpoint(
    project_id: int,
    org_id: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> VersionesListResponse:
    """Obtiene todas las versiones de un proyecto.

    Args:
        project_id: ID del proyecto
        org_id: ID de la organización (del selector en backoffice)
    """
    _logger = logging.getLogger(__name__)

    # Validación de permisos: SuperAdmin puede ver cualquier org, otros solo la suya
    if session.identity_type_id != 1 and org_id != session.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para ver versiones de esta organización",
        )

    _logger.info(
        "[middleware] Consultando versiones proyecto=%s org=%s (session_org=%s, identity=%s)",
        project_id,
        org_id,
        session.organization_id,
        session.identity_type_id,
    )

    try:
        response = router.get_project_versions(project_id, org_id, session)
        return VersionesListResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post(
    "/proyectos/{project_id}/versiones",
    response_model=CrearVersionResponse,
    tags=["versiones"],
)
def create_project_version_endpoint(
    project_id: int,
    request: CrearVersionRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> CrearVersionResponse:
    """Crea una nueva versión para un proyecto."""
    _logger = logging.getLogger(__name__)
    _logger.info(
        "[middleware] Creando versión proyecto=%s org=%s",
        project_id,
        session.organization_id,
    )

    # Validar que el proyecto pertenece a la organización del usuario
    # EXCEPCIÓN: SuperAdmin (identity_type_id=1) puede crear versiones en cualquier organización
    if session.identity_type_id != 1 and request.id_organizacion != session.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para crear versiones en esta organización",
        )

    try:
        response = router.create_project_version(project_id, session.organization_id, session)
        return CrearVersionResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# Endpoints de Estados de Versión
# ============================================================================


@app.get(
    "/proyectos/{project_id}/versiones/{version_id}/estado",
    response_model=VersionStateResponse,
    tags=["version-states"],
)
def get_version_state_endpoint(
    project_id: int,
    version_id: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> VersionStateResponse:
    """Obtiene el estado actual de una versión.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    """
    _logger = logging.getLogger(__name__)
    _logger.info(
        "[middleware] Obteniendo estado versión=%s proyecto=%s org=%s user=%s",
        version_id,
        project_id,
        session.organization_id,
        session.user_id,
    )

    try:
        response = router.get_version_state(
            project_id, version_id, session.organization_id, session
        )
        return VersionStateResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch(
    "/proyectos/{project_id}/versiones/{version_id}/estado",
    response_model=VersionStateResponse,
    tags=["version-states"],
)
def update_version_state_endpoint(
    project_id: int,
    version_id: int,
    request: UpdateVersionStateRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> VersionStateResponse:
    """Actualiza el estado de una versión.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    """
    _logger = logging.getLogger(__name__)
    _logger.info(
        "[middleware] Actualizando estado versión=%s proyecto=%s user=%s",
        version_id,
        project_id,
        session.user_id,
    )

    try:
        update_data = request.model_dump(exclude_unset=True)
        _logger.info(
            "[middleware] DEBUG update_data recibido en endpoint: %s",
            update_data,
        )
        response = router.update_version_state(
            project_id, version_id, session.organization_id, update_data, session
        )
        return VersionStateResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get(
    "/proyectos/{project_id}/versiones/{version_id}/eventos",
    response_model=VersionEventsResponse,
    tags=["version-states"],
)
def get_version_events_endpoint(
    project_id: int,
    version_id: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
    limit: int = 50,
) -> VersionEventsResponse:
    """Obtiene el historial de eventos de una versión.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    """
    _logger = logging.getLogger(__name__)
    _logger.info(
        "[middleware] Obteniendo eventos versión=%s proyecto=%s limit=%s",
        version_id,
        project_id,
        limit,
    )

    try:
        response = router.get_version_events(
            project_id, version_id, session.organization_id, session, limit
        )
        return VersionEventsResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post(
    "/proyectos/{project_id}/versiones/crear-completa",
    response_model=CreateVersionFullResponse,
    tags=["versiones"],
)
def create_version_full_endpoint(
    project_id: int,
    request: CreateVersionFullRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> CreateVersionFullResponse:
    """Crea una nueva versión completa (DB + fmanagement).
    
    Esta operación es atómica:
    1. Inserta en tabla versiones
    2. Inserta en tabla version_states
    3. Inserta en tabla version_events
    4. Crea carpeta física vía fmanagement (clonando si se especifica)
    
    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB + fmanagement
    """
    _logger = logging.getLogger(__name__)
    _logger.info(
        "[middleware] Creando versión completa proyecto=%s org=%s user=%s",
        project_id,
        request.id_organizacion,
        session.user_id,
    )

    # Validar que el proyecto pertenece a la organización del usuario
    # EXCEPCIÓN: SuperAdmin (identity_type_id=1) puede crear versiones en cualquier organización
    if session.identity_type_id != 1 and request.id_organizacion != session.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para crear versiones en esta organización",
        )

    try:
        request_data = request.model_dump()
        response = router.create_version_full(project_id, request_data, session)
        return CreateVersionFullResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# Endpoints de Integración con fmanagement
# ============================================================================


@app.post(
    "/fmanagement/list",
    response_model=FmanagementListResponse,
    tags=["fmanagement"],
)
def fmanagement_list_endpoint(
    request: FmanagementListRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> FmanagementListResponse:
    """Lista estructura de archivos vía fmanagement.
    
    Flujo: Frontend → Middleware → Broker → Backend Core → fmanagement
    """
    _logger = logging.getLogger(__name__)
    _logger.info(
        "[middleware] Listando fmanagement org=%s prj=%s version=%s",
        request.org_folder,
        request.prj_folder,
        request.version_folder,
    )

    try:
        request_data = request.model_dump()
        response = router.fmanagement_list(request_data, session)
        return FmanagementListResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post(
    "/fmanagement/operation",
    response_model=FmanagementOperationResponse,
    tags=["fmanagement"],
)
def fmanagement_operation_endpoint(
    request: FmanagementOperationRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> FmanagementOperationResponse:
    """Ejecuta una operación genérica en fmanagement.

    Operaciones soportadas:
    - create_folder, delete_folder, rename_folder
    - create_file, rename_file, delete_file, download_file
    - get_properties

    Flujo: Frontend → Middleware → Broker → Backend Core → fmanagement
    """
    _logger = logging.getLogger(__name__)
    _logger.info(
        "[middleware] Operación fmanagement: %s user=%s",
        request.operation,
        session.user_id,
    )

    try:
        request_data = request.model_dump()
        response = router.fmanagement_operation(request_data, session)
        return FmanagementOperationResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post(
    "/fmanagement/download",
    tags=["fmanagement"],
)
def fmanagement_download_endpoint(
    request: FmanagementOperationRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> Response:
    """Descarga un archivo vía fmanagement (binario)."""
    try:
        content = router.fmanagement_download(request.model_dump(), session)
        filename = request.params.get("filename", "download")
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except BusinessRuleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/fmanagement/diff",
    response_model=FmanagementOperationResponse,
    tags=["fmanagement"],
)
def fmanagement_diff_endpoint(
    request_data: dict[str, Any],
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> FmanagementOperationResponse:
    """Compara versiones vía fmanagement."""
    try:
        response = router.fmanagement_diff(request_data, session)
        return FmanagementOperationResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/fmanagement/transfer",
    response_model=FmanagementOperationResponse,
    tags=["fmanagement"],
)
def fmanagement_transfer_endpoint(
    request_data: dict[str, Any],
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> FmanagementOperationResponse:
    """Transfiere versiones vía fmanagement."""
    try:
        response = router.fmanagement_transfer(request_data, session)
        return FmanagementOperationResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/files/generate-token",
    response_model=GenerateFileTokenResponse,
    tags=["files"],
)
def generate_file_token_endpoint(
    request: GenerateFileTokenRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> GenerateFileTokenResponse:
    """Genera un token JWT temporal para operaciones de archivo (upload/download).

    Este endpoint valida los permisos del usuario y genera un token de corta duración
    (5 minutos) que permite realizar operaciones directas con fmanagement sin pasar
    por múltiples capas del sistema.

    Validaciones de seguridad:
    - Verifica que el usuario tenga permisos de archivo (file_create o file_read)
    - Valida que el usuario pertenezca a la organización del proyecto
    - Genera token con información de organización para validación en fmanagement
    """
    try:
        # Validar permisos según la operación
        permission_key = "file_create" if request.operation == "upload" else "file_read"
        if not router.has_low_level_permission(session, permission_key):
            raise HTTPException(
                status_code=403,
                detail=f"Usuario sin permiso para {request.operation}"
            )

        # Generar token temporal
        # Si se proporciona organization_id (backoffice admin), usar ese en vez del de sesión
        override_org_id = request.organization_id if request.organization_id > 0 else 0
        token_data = router.generate_file_operation_token(
            session=session,
            project_id=request.project_id,
            version_id=request.version_id,
            operation=request.operation,
            relative_path=request.relative_path,
            ttl_seconds=300,  # 5 minutos
            override_organization_id=override_org_id,
        )

        # URL de fmanagement para el navegador: usar proxy público según el cliente
        _client_app = http_request.headers.get("x-client-app", "frontend")
        if _client_app == "backoffice":
            _base_api = get_env_value("backoffice_api_url", "")
        else:
            _base_api = get_env_value("frontend_api_url", "")
        fmanagement_url = (
            f"{_base_api}/fmanagement"
            if _base_api
            else get_env_value("fmanagement_base_url", "http://localhost:1666")
        )

        return GenerateFileTokenResponse(
            success=True,
            token=token_data["token"],
            fmanagement_url=fmanagement_url,
            expires_in=token_data["expires_in"],
            expires_at=token_data["expires_at"],
            mensaje="Token generado exitosamente"
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error generando token de archivo")
        raise HTTPException(
            status_code=500,
            detail=f"Error generando token: {str(exc)}"
        ) from exc


# =============================================================================
# OLLAMA TRAINER PROXY ROUTES
# =============================================================================

@app.get("/trainer/ollama/health")
def ollama_health_proxy(
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
):
    """Proxy para health check de Ollama en el trainer."""
    try:
        return router.ollama_health(session)
    except BusinessRuleError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error en proxy ollama health")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/trainer/ollama/models")
def ollama_models_proxy(
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
):
    """Proxy para listar modelos de Ollama."""
    try:
        return router.ollama_list_models(session)
    except BusinessRuleError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error en proxy ollama models")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/trainer/ollama/generate")
def ollama_generate_proxy(
    request: dict,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
):
    """Proxy para generar texto con Ollama."""
    try:
        return router.ollama_generate(request, session)
    except BusinessRuleError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error en proxy ollama generate")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/trainer/ollama/chat")
def ollama_chat_proxy(
    request: dict,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
):
    """Proxy para chat con Ollama."""
    try:
        return router.ollama_chat(request, session)
    except BusinessRuleError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error en proxy ollama chat")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ============================================================================
# ASSIGNMENTS - Gestor de asignaciones (SuperAdmin only)
# ============================================================================

@app.get("/assignments/organizations", tags=["assignments"])
def list_organizations_endpoint(
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> list[dict[str, Any]]:
    """Lista todas las organizaciones para assignments."""
    try:
        return router.list_organizations(session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/assignments/accessible-organizations", tags=["assignments"])
def get_accessible_organizations_endpoint(
    user_id: int,
    identity_type_id: int,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> list[dict[str, Any]]:
    """Returns organizations accessible to a user based on identity type."""
    try:
        return router.get_accessible_organizations(
            user_id, identity_type_id, session
        )
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/assignments/internal-users", tags=["assignments"])
def get_internal_users_endpoint(
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> list[dict[str, Any]]:
    """Gets internal users."""
    try:
        return router.get_internal_users(session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/assignments/roles", tags=["assignments"])
def get_roles_for_assignments_endpoint(
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> list[dict[str, Any]]:
    """Gets roles for assignments."""
    try:
        return router.list_roles(session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/assignments/organizations/{organization_id}", tags=["assignments"])
def get_organization_assignments_endpoint(
    organization_id: int,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> list[dict[str, Any]]:
    """Gets organization assignments."""
    try:
        return router.get_organization_assignments(organization_id, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/assignments/organizations", tags=["assignments"])
def create_organization_assignment_endpoint(
    payload: dict[str, int],
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> dict[str, Any]:
    """Creates organization assignment."""
    try:
        return router.create_organization_assignment(
            payload["user_id"],
            payload["organization_id"],
            payload["role_id"],
            session
        )
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.patch("/assignments/organizations/{assignment_id}", tags=["assignments"])
def update_organization_assignment_endpoint(
    assignment_id: int,
    active: bool,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> dict[str, Any]:
    """Updates organization assignment active status."""
    try:
        return router.update_organization_assignment(
            assignment_id, active, session
        )
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.delete("/assignments/organizations/{assignment_id}", tags=["assignments"])
def delete_organization_assignment_endpoint(
    assignment_id: int,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> dict[str, Any]:
    """Deletes organization assignment permanently."""
    try:
        return router.delete_organization_assignment(assignment_id, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/assignments/validate-org-prerequisite", tags=["assignments"])
def validate_org_prerequisite_endpoint(
    user_id: int,
    organization_id: int,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> dict[str, Any]:
    """Validates if user has active org role (prerequisite)."""
    try:
        return router.validate_org_prerequisite(user_id, organization_id, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/assignments/projects/{project_id}", tags=["assignments"])
def get_project_assignments_endpoint(
    project_id: int,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> list[dict[str, Any]]:
    """Gets project assignments."""
    try:
        return router.get_project_assignments(project_id, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/assignments/projects", tags=["assignments"])
def create_project_assignment_endpoint(
    payload: dict[str, int],
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> dict[str, Any]:
    """Creates project assignment (with prerequisite validation)."""
    try:
        return router.create_project_assignment(
            payload["user_id"],
            payload["organization_id"],
            payload["project_id"],
            payload["role_id"],
            session
        )
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.patch("/assignments/projects/{assignment_id}", tags=["assignments"])
def update_project_assignment_endpoint(
    assignment_id: int,
    active: bool,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> dict[str, Any]:
    """Updates project assignment active status."""
    try:
        return router.update_project_assignment(assignment_id, active, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.delete("/assignments/projects/{assignment_id}", tags=["assignments"])
def delete_project_assignment_endpoint(
    assignment_id: int,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> dict[str, Any]:
    """Deletes project assignment permanently."""
    try:
        return router.delete_project_assignment(assignment_id, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


# ============================================================================
# Endpoints de Prompts
# ============================================================================


@app.get("/prompts/{category}", tags=["prompts"])
def get_prompts_endpoint(
    category: str,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> list[dict[str, Any]]:
    """Gets all prompts for a category."""
    try:
        return router.get_prompts(category, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/prompts/{category}/{id_prompt}", tags=["prompts"])
def get_prompt_endpoint(
    category: str,
    id_prompt: int,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> dict[str, Any]:
    """Gets a specific prompt by ID."""
    try:
        return router.get_prompt(category, id_prompt, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/prompts/{category}", tags=["prompts"])
def create_prompt_endpoint(
    category: str,
    payload: dict,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> dict[str, Any]:
    """Creates a new prompt."""
    try:
        return router.create_prompt(category, payload, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.put("/prompts/{category}/{id_prompt}", tags=["prompts"])
def update_prompt_endpoint(
    category: str,
    id_prompt: int,
    payload: dict,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> dict[str, Any]:
    """Updates an existing prompt."""
    try:
        return router.update_prompt(category, id_prompt, payload, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


# ============================================================================
# PROJECT VERSION STATES - Phase Updates
# ============================================================================

class UpdateProposalPhaseDto(BaseModel):
    """DTO for updating proposal phase."""
    aceptacion_cliente: bool
    aceptacion_interna: bool
    revision_interna: bool | None = None
    propuesta_mejoras: bool | None = None


class UpdateTrainingPhaseDto(BaseModel):
    """DTO for updating training phase."""
    completado: bool


class UpdateEvaluationPhaseDto(BaseModel):
    """DTO for updating evaluation phase."""
    evaluacion: bool | None = None
    reentrenamiento: bool
    optimizacion: bool
    calidad_aprobada: bool
    evaluacion_entrenamiento: bool | None = None


class UpdateGenerationPhaseDto(BaseModel):
    """DTO for updating generation phase."""
    generacion_completada: bool | None = None
    generacion_solicitada: bool | None = None


class UpdateNotificationPhaseDto(BaseModel):
    """DTO for updating notification phase."""
    notificacion_enviada: bool


@app.patch("/project-version-states/{state_id}/proposal", tags=["project-version-states"])
def update_proposal_phase_endpoint(
    state_id: int,
    payload: UpdateProposalPhaseDto,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> dict[str, Any]:
    """Updates proposal phase (client and internal acceptance)."""
    try:
        return router.update_proposal_phase(state_id, payload, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.patch("/project-version-states/{state_id}/training", tags=["project-version-states"])
def update_training_phase_endpoint(
    state_id: int,
    payload: UpdateTrainingPhaseDto,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> dict[str, Any]:
    """Updates training phase."""
    try:
        return router.update_training_phase(state_id, payload, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.patch("/project-version-states/{state_id}/evaluation", tags=["project-version-states"])
def update_evaluation_phase_endpoint(
    state_id: int,
    payload: UpdateEvaluationPhaseDto,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> dict[str, Any]:
    """Updates evaluation phase."""
    try:
        return router.update_evaluation_phase(state_id, payload, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.patch("/project-version-states/{state_id}/generation", tags=["project-version-states"])
def update_generation_phase_endpoint(
    state_id: int,
    payload: UpdateGenerationPhaseDto,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> dict[str, Any]:
    """Updates generation phase."""
    try:
        return router.update_generation_phase(state_id, payload, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.patch("/project-version-states/{state_id}/notification", tags=["project-version-states"])
def update_notification_phase_endpoint(
    state_id: int,
    payload: UpdateNotificationPhaseDto,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> dict[str, Any]:
    """Updates notification phase."""
    try:
        return router.update_notification_phase(state_id, payload, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


# ============================================================================
# PROMPTS
# ============================================================================

@app.patch("/prompts/{category}/{id_prompt}/toggle", tags=["prompts"])
def toggle_prompt_endpoint(
    category: str,
    id_prompt: int,
    payload: dict,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> dict[str, Any]:
    """Toggles prompt active status."""
    try:
        return router.toggle_prompt(category, id_prompt, payload, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


# ============================================================================
# Training - Versiones pendientes de entrenamiento
# ============================================================================


@app.get("/training/pending-versions", tags=["training"])
def get_pending_training_versions_endpoint(
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> dict[str, Any]:
    """Obtiene versiones con entrenamiento inicial solicitado.

    Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
    """
    try:
        return router.get_pending_training_versions(session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


# ============================================================================
# MODEL DOWNLOADS - Descargas de modelos con OTP
# ============================================================================


@app.get("/models/list", response_model=ModelListResponse, tags=["models"])
def list_available_model_packages_endpoint(
    organization_id: int | None = None,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> ModelListResponse:
    """Lista modelos disponibles para descarga.

    Args:
        organization_id: ID de organización (None = todas, solo para admins globales)

    Security:
        - Solo usuarios con identity_type_id (admin global o admin org)
        - Backoffice: puede ver todas las organizaciones (organization_id=None)
        - Frontend: solo puede ver su propia organización

    Returns:
        Lista de modelos con información de org/proyecto/versión/archivo
    """
    _logger = logging.getLogger(__name__)
    try:
        # Verificar que el usuario tiene identity_type_id (es admin)
        if session.identity_type_id is None:
            raise HTTPException(
                status_code=403,
                detail="Solo administradores pueden descargar modelos"
            )

        # Si no se especifica organización, usar la del usuario
        # (excepto para admins globales que pueden ver todas)
        if organization_id is None and session.identity_type_id != 1:
            organization_id = session.organization_id

        models = router.list_available_models(session, organization_id)
        return ModelListResponse(
            success=True,
            models=models,
            message=f"Se encontraron {len(models)} modelos disponibles"
        )
    except HTTPException:
        raise
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Error listando modelos")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al listar modelos"
        ) from exc


@app.post("/models/download/request-otp", response_model=ModelDownloadOtpResponse, tags=["models"])
def request_model_download_otp_endpoint(
    request: ModelDownloadOtpRequest,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> ModelDownloadOtpResponse:
    """Solicita OTP para descargar modelo.

    Security:
        - Solo usuarios con identity_type_id (admin global o admin org)
        - Valida que el usuario pertenezca a la organización del modelo
        - Genera OTP y devuelve datos para envío de SMS

    Flow:
        1. Frontend/Backoffice llama este endpoint
        2. Middleware valida permisos y genera OTP
        3. Middleware devuelve OTP + teléfono
        4. Frontend/Backoffice envía SMS con OTP via Infobip
        5. Usuario recibe SMS con código

    Returns:
        OTP y teléfono para envío de SMS
    """
    try:
        # SECURITY BY DESIGN: Solo SuperAdmin (1) y Admin Organización (2)
        if session.identity_type_id not in (1, 2):
            _logger.warning(
                "Intento de solicitar OTP descarga sin permisos: user_id=%s identity_type_id=%s",
                session.user_id, session.identity_type_id,
            )
            raise HTTPException(
                status_code=403,
                detail="Solo SuperAdmin y Administradores de Organización pueden descargar modelos"
            )

        # Verificar permisos de organización (solo SuperAdmin puede otras orgs)
        if session.identity_type_id == 2:
            if request.organization_id != session.organization_id:
                raise HTTPException(
                    status_code=403,
                    detail="No tiene permisos para descargar modelos de otra organización"
                )

        otp_data = router.request_model_download_otp(
            session=session,
            organization_id=request.organization_id,
            project_id=request.project_id,
            version_id=request.version_id
        )

        return ModelDownloadOtpResponse(
            success=True,
            otp=otp_data["otp"],
            phone_number=otp_data["phone_number"],
            phone_masked=otp_data.get("phone_masked", ""),
            message="OTP generado. Envíe el SMS al usuario."
        )
    except HTTPException:
        raise
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Error solicitando OTP")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al solicitar OTP"
        ) from exc


@app.post("/models/download/validate-otp", response_model=ModelDownloadValidateOtpResponse, tags=["models"])
def validate_model_download_otp_endpoint(
    request: ModelDownloadValidateOtpRequest,
    http_request: Request,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> ModelDownloadValidateOtpResponse:
    """Valida OTP y genera token de descarga de modelo.

    Security:
        - Solo SuperAdmin (1) y Admin Organización (2)
        - Valida el código OTP del usuario
        - Genera token JWT para descarga en fmanagement
        - Rota el OTP del usuario (como en login)

    Flow:
        1. Usuario introduce OTP recibido por SMS
        2. Frontend/Backoffice llama este endpoint con el OTP
        3. Middleware valida OTP
        4. Middleware genera token JWT con permisos de descarga
        5. Middleware rota OTP del usuario
        6. Frontend/Backoffice usa token para descargar desde fmanagement

    Returns:
        Token JWT para descarga directa desde fmanagement
    """
    try:
        # SECURITY BY DESIGN: Solo SuperAdmin (1) y Admin Organización (2)
        if session.identity_type_id not in (1, 2):
            _logger.warning(
                "Intento de validar OTP descarga sin permisos: user_id=%s identity_type_id=%s",
                session.user_id, session.identity_type_id,
            )
            raise HTTPException(
                status_code=403,
                detail="Solo SuperAdmin y Administradores de Organización pueden descargar modelos"
            )

        # Verificar permisos de organización
        if session.identity_type_id == 2:
            if request.organization_id != session.organization_id:
                raise HTTPException(
                    status_code=403,
                    detail="No tiene permisos para descargar modelos de otra organización"
                )

        token_data = router.validate_model_download_otp(
            session=session,
            organization_id=request.organization_id,
            project_id=request.project_id,
            version_id=request.version_id,
            otp=request.otp
        )

        # URL de fmanagement para el navegador: usar proxy público según el cliente
        _client_app = http_request.headers.get("x-client-app", "frontend")
        if _client_app == "backoffice":
            _base_api = get_env_value("backoffice_api_url", "")
        else:
            _base_api = get_env_value("frontend_api_url", "")
        fmanagement_url = (
            f"{_base_api}/fmanagement"
            if _base_api
            else get_env_value("fmanagement_base_url", "http://localhost:1666")
        )

        return ModelDownloadValidateOtpResponse(
            success=True,
            download_token=token_data["token"],
            fmanagement_url=fmanagement_url,
            expires_in=token_data["expires_in"],
            expires_at=token_data["expires_at"],
            message="OTP validado. Token generado para descarga."
        )
    except HTTPException:
        raise
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Error validando OTP")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al validar OTP"
        ) from exc


@app.get("/models/download/direct", tags=["models"])
def download_model_direct_endpoint(
    token: str,
    filename: str,
    router: RouterMiddleware = Depends(get_router_middleware),
):
    """Descarga de modelo autenticada por token JWT (sin headers de sesión).

    El token se genera tras validar OTP en /models/download/validate-otp.
    Se usa como query param para permitir descarga directa via <a href>.

    Flujo: Frontend/Backoffice → Middleware → Broker → Backend Core → Filesystem
    """
    import jwt as pyjwt

    _logger = logging.getLogger(__name__)

    try:
        # Validar el token JWT de descarga
        jwt_settings = get_jwt_settings()
        try:
            claims = pyjwt.decode(
                token,
                jwt_settings.access_secret,
                algorithms=[jwt_settings.algorithm],
            )
        except pyjwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token de descarga expirado")
        except pyjwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Token de descarga inválido")

        # Verificar que es un token de descarga de modelo
        if claims.get("operation") != "download_model":
            raise HTTPException(status_code=403, detail="Token no válido para descarga de modelo")

        organization_id = claims.get("organization_id")
        project_id = claims.get("project_id")
        version_id = claims.get("version_id")
        identity_type_id = claims.get("identity_type_id")

        _logger.info(
            "[MODELS DIRECT] Descarga con token: org=%s prj=%s ver=%s file=%s identity=%s",
            organization_id, project_id, version_id, filename, identity_type_id,
        )

        # SECURITY: Solo SuperAdmin (1) y Admin Organización (2)
        if identity_type_id not in (1, 2):
            raise HTTPException(status_code=403, detail="Sin permisos para descargar modelos")

        # Construir SessionContext mínimo para el broker
        session = SessionContext(
            user_id=claims.get("user_id", 0),
            organization_id=organization_id,
            identity_type_id=identity_type_id,
            access_payload=claims,
            session_payload=claims,
            access_token="",
            session_token="",
        )

        # Obtener archivo via cadena API: Middleware → Broker → Backend Core → Filesystem
        content = router.download_model_package(
            session, organization_id, project_id, version_id, filename
        )

        return Response(
            content=content,
            media_type=MEDIA_TYPE_ZIP,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except BusinessRuleError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        _logger.exception("[MODELS DIRECT] Error: %s: %s", type(exc).__name__, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/models/download/session", tags=["models"])
def download_model_session_endpoint(
    organization_id: int,
    project_id: int,
    version_id: int,
    filename: str,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
):
    """Descarga directa de modelo autenticada por sesión (sin OTP).

    Permite descargar ficheros de modelo (Modelfile, ZIP) directamente
    usando la autenticación de sesión estándar.

    Security:
        - Solo SuperAdmin (1) y Admin Organización (2)
    """
    _logger = logging.getLogger(__name__)

    try:
        if session.identity_type_id not in (1, 2):
            raise HTTPException(
                status_code=403,
                detail="Sin permisos para descargar modelos",
            )

        _logger.info(
            "[MODELS SESSION] Descarga: org=%s prj=%s ver=%s file=%s user=%s",
            organization_id, project_id, version_id, filename, session.user_id,
        )

        content = router.download_model_package(
            session, organization_id, project_id, version_id, filename
        )

        media = MEDIA_TYPE_ZIP if filename.endswith(".zip") else "application/octet-stream"

        return Response(
            content=content,
            media_type=media,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except BusinessRuleError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        _logger.exception("[MODELS SESSION] Error: %s: %s", type(exc).__name__, exc)
        raise HTTPException(status_code=500, detail="Error descargando modelo") from exc


# ========================================================================
# ENDPOINTS DE INFORMES
# ========================================================================


class InformeFileDto(BaseModel):
    """Archivo de informe."""

    filename: str
    display_name: str


class InformesListResponse(BaseModel):
    """Respuesta con lista de archivos de informes."""

    archivos: list[InformeFileDto]
    total: int


class InformeContentResponse(BaseModel):
    """Respuesta con el contenido de un informe."""

    content: str
    display_name: str


@app.get(
    "/informes/{org_id}/{project_id}/{version_id}/files",
    response_model=InformesListResponse,
    tags=["informes"],
)
def list_informe_files_endpoint(
    org_id: int,
    project_id: int,
    version_id: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> InformesListResponse:
    """Lista los archivos markdown de informes para una versión.

    Args:
        org_id: ID de la organización
        project_id: ID del proyecto
        version_id: ID de la versión
    """
    _logger = logging.getLogger(__name__)

    # Validación de permisos: SuperAdmin puede ver cualquier org, otros solo la suya
    if session.identity_type_id != 1 and org_id != session.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para ver informes de esta organización",
        )

    _logger.info(
        "[middleware] Listando informes org=%s proyecto=%s version=%s",
        org_id, project_id, version_id,
    )

    try:
        response = router.list_informe_files(org_id, project_id, version_id, session)
        return InformesListResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Error listando informes")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al listar informes",
        ) from exc


@app.get(
    "/informes/{org_id}/{project_id}/{version_id}/content",
    response_model=InformeContentResponse,
    tags=["informes"],
)
def get_informe_content_endpoint(
    org_id: int,
    project_id: int,
    version_id: int,
    file: str,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> InformeContentResponse:
    """Obtiene el contenido de un archivo markdown de informe.

    Args:
        org_id: ID de la organización
        project_id: ID del proyecto
        version_id: ID de la versión
        file: Nombre del archivo (display_name)
    """
    _logger = logging.getLogger(__name__)

    # Validación de permisos: SuperAdmin puede ver cualquier org, otros solo la suya
    if session.identity_type_id != 1 and org_id != session.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para ver informes de esta organización",
        )

    _logger.info(
        "[middleware] Obteniendo contenido informe org=%s proyecto=%s version=%s file=%s",
        org_id, project_id, version_id, file,
    )

    try:
        response = router.get_informe_content(org_id, project_id, version_id, file, session)
        return InformeContentResponse(**response)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Error obteniendo contenido informe")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener contenido del informe",
        ) from exc


# ============================================================================
# JOB TEMPLATES - Plantillas de jobs (SuperAdmin only)
# ============================================================================


@app.get(
    "/job-templates/catalogs",
    tags=["job-templates"],
)
def get_job_template_catalogs_endpoint(
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> dict[str, Any]:
    """Obtiene catálogos para plantillas de jobs."""
    _logger = logging.getLogger(__name__)

    if session.identity_type_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=JOB_TEMPLATES_SUPERADMIN_ONLY_MSG,
        )

    try:
        return router.get_job_template_catalogs(session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Error obteniendo catálogos job templates")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener catálogos",
        ) from exc


@app.get(
    "/job-templates",
    tags=["job-templates"],
)
def get_job_templates_endpoint(
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> list[dict[str, Any]]:
    """Lista plantillas de jobs."""
    _logger = logging.getLogger(__name__)

    if session.identity_type_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=JOB_TEMPLATES_SUPERADMIN_ONLY_MSG,
        )

    try:
        return router.get_job_templates(session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Error obteniendo plantillas de jobs")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener plantillas",
        ) from exc


class JobTemplateSaveRequest(BaseModel):
    """Payload para crear o actualizar una plantilla de job."""

    id: int | None = None
    nombre: str
    descripcion: str | None = ""
    id_tipo: int
    es_programable: bool = False
    id_estado_inicial: int | None = None
    id_modelo: int | None = None
    id_salida: int | None = None
    acepta_entrada: bool = False
    permite_hijos: bool = False


@app.post(
    "/job-templates",
    tags=["job-templates"],
)
def save_job_template_endpoint(
    data: JobTemplateSaveRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> dict[str, Any]:
    """Crea o actualiza una plantilla de job."""
    _logger = logging.getLogger(__name__)

    if session.identity_type_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=JOB_TEMPLATES_SUPERADMIN_ONLY_MSG,
        )

    try:
        return router.save_job_template(data.model_dump(), session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Error guardando plantilla de job")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al guardar plantilla",
        ) from exc


@app.patch(
    "/job-templates/{template_id}/toggle",
    tags=["job-templates"],
)
def toggle_job_template_endpoint(
    template_id: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> dict[str, Any]:
    """Activa o desactiva una plantilla de job."""
    _logger = logging.getLogger(__name__)

    if session.identity_type_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=JOB_TEMPLATES_SUPERADMIN_ONLY_MSG,
        )

    try:
        return router.toggle_job_template(template_id, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Error cambiando estado de plantilla")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al cambiar estado de plantilla",
        ) from exc


# ============================================================================
# JOBS - Gestión de jobs
# ============================================================================


@app.get(
    "/jobs",
    tags=["jobs"],
)
def get_jobs_endpoint(
    org_id: int,
    project_id: int,
    version_id: int,
    tipo_clave: str | None = None,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)] = None,
    session: Annotated[SessionContext, Depends(get_session_context)] = None,
) -> list[dict[str, Any]]:
    """Lista jobs filtrados por org/proyecto/versión."""
    _logger = logging.getLogger(__name__)

    try:
        return router.get_jobs(org_id, project_id, version_id, tipo_clave, session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Error obteniendo jobs")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener jobs",
        ) from exc


class JobCreateRequest(BaseModel):
    """Payload para crear un job."""

    id_template: int
    id_organizacion: int
    id_proyecto: int
    id_version: int
    nombre: str
    descripcion: str | None = ""
    id_tipo: int
    id_estado: int = 1
    id_modelo: int | None = None
    id_salida: int | None = None
    programado_para: str | None = None


@app.post(
    "/jobs",
    tags=["jobs"],
)
def create_job_endpoint(
    data: JobCreateRequest,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> dict[str, Any]:
    """Crea un nuevo job."""
    _logger = logging.getLogger(__name__)

    try:
        return router.create_job(data.model_dump(), session)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Error creando job")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear job",
        ) from exc


# ============================================================================
# LAIM AUTH
# ============================================================================


@app.post("/laim/login")
async def laim_login_endpoint(
    request: LaimLoginRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
) -> dict[str, Any]:
    """Autenticación LAIM (sin OTP)."""
    ip_address, user_agent = _get_request_metadata(http_request)
    try:
        result = router.laim_login(
            request.model_dump(),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=MSG_LAIM_INVALID_CREDENTIALS,
            )
        return result
    except BusinessRuleError as exc:
        detail = str(exc)
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if detail == MSG_LAIM_INVALID_CREDENTIALS
            else status.HTTP_502_BAD_GATEWAY
        )
        raise HTTPException(status_code=status_code, detail=detail) from exc


@app.post("/laim/register")
async def laim_register_endpoint(
    request: LaimRegisterRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
) -> dict[str, Any]:
    """Registro público LAIM."""
    ip_address, user_agent = _get_request_metadata(http_request)
    try:
        result = router.laim_register(
            request.model_dump(),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Error en registro"),
            )
        return result
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/laim/logout")
async def laim_logout_endpoint(
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Cierra sesión LAIM."""
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=SESSION_TOKEN_NOT_PROVIDED_MSG,
        )
    try:
        return router.laim_logout(session_token)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/laim/refresh-token")
async def laim_refresh_token_endpoint(
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Renueva tokens LAIM."""
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=SESSION_TOKEN_NOT_PROVIDED_MSG,
        )
    try:
        result = router.laim_refresh_token(session_token)
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result.get("error", "Sesión inválida"),
            )
        return result
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/laim/session/permissions")
async def laim_session_permissions_endpoint(
    identity_type_id: int,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
) -> dict[str, Any]:
    """Permisos LAIM para un rol."""
    try:
        return router.laim_session_permissions(identity_type_id)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/laim/status")
async def laim_status_endpoint(
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
) -> dict[str, Any]:
    """Estado del subsistema LAIM."""
    try:
        return router.laim_status()
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/laim/contact/messages")
async def laim_create_contact_message_endpoint(
    request: LaimContactMessageRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Registra un mensaje del formulario de contacto LAIM (público)."""
    ip_address, user_agent = _get_request_metadata(http_request)
    try:
        result = router.laim_create_contact_message(
            request.model_dump(),
            authorization=authorization or "",
            session_token=session_token or "",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "No se pudo registrar el mensaje"),
            )
        return result
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


# ============================================================================
# LAIM FORUM (proxy transparente hacia Backend Core)
# ============================================================================


def _laim_forum_proxy_response(proxy_result: dict[str, Any]) -> Any:
    """Convierte respuesta del proxy en Response HTTP de FastAPI."""
    status_code = int(proxy_result.get("status_code", 502))
    if proxy_result.get("is_binary"):
        return Response(
            content=proxy_result.get("body", b""),
            media_type=proxy_result.get("content_type", "application/octet-stream"),
            status_code=status_code,
        )
    body = proxy_result.get("body")
    if status_code >= 400:
        detail: Any = body
        if isinstance(body, dict):
            detail = body.get("detail", body)
        raise HTTPException(status_code=status_code, detail=detail)
    return body if body is not None else {}


@app.api_route(
    "/laim/forum/{forum_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    tags=["laim-forum"],
)
async def laim_forum_proxy_endpoint(
    forum_path: str,
    request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> Any:
    """Proxy transparente del foro LAIM hacia Backend Core."""
    ip_address, user_agent = _get_request_metadata(request)
    payload: dict[str, Any] | None = None
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        try:
            raw = await request.json()
            payload = raw if isinstance(raw, dict) else {}
        except Exception:
            payload = {}

    try:
        result = router.laim_forum_request(
            method=request.method,
            path=f"/laim/forum/{forum_path}",
            payload=payload,
            query_string=request.url.query,
            authorization=authorization or "",
            session_token=session_token or "",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return _laim_forum_proxy_response(result)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


# ============================================================================
# LAIM SITE (proxy público de assets hacia Backend Core)
# ============================================================================


@app.api_route(
    "/laim/site/{site_path:path}",
    methods=["GET"],
    tags=["laim-site"],
)
async def laim_site_proxy_endpoint(
    site_path: str,
    request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
) -> Any:
    """Proxy público de assets del sitio LAIM hacia Backend Core."""
    try:
        result = router.laim_forum_request(
            method="GET",
            path=f"/laim/site/{site_path}",
            payload=None,
            query_string=request.url.query,
            authorization="",
            session_token="",
            ip_address="",
            user_agent="",
        )
        return _laim_forum_proxy_response(result)
    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
