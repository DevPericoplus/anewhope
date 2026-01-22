"""Capa de API para recibir peticiones del frontend."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, AsyncIterator

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

try:
    from .broker_backend_client import BrokerBackendClient
    from .interfacetobackend import BackendCommunicationError, InterfaceToBackend
    from .routermiddleware import (
        BusinessRuleError,
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
    access_token: str
    session_token: str
    access_expires_at: int
    session_expires_at: int


class LoginOtpResponse(BaseModel):
    """Respuesta de solicitud de OTP."""

    success: bool


class RefreshTokenResponse(BaseModel):
    """Respuesta de renovación de tokens."""

    user_id: int
    organization_id: int
    access_token: str
    session_token: str
    access_expires_at: int
    session_expires_at: int


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


class UserCreateRequest(BaseModel):
    """Payload para crear usuario."""

    organization_id: int
    identity_type_id: int | None = None
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


def _configure_logging() -> None:
    """Configura el logging base si no existe configuración previa."""

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
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


def get_session_context(
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    access_token: Annotated[str | None, Header(alias="Authorization")] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> SessionContext:
    """Valida la sesión y retorna el contexto."""

    try:
        access_value = _extract_bearer_token(access_token)
        if session_token is None:
            raise TokenValidationError("Token de sesión no proporcionado")
        return router.validate_session(access_value, session_token)
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
    """Obtiene la URL base del broker backend."""

    try:
        from protected_values import broker_backend_base_url  # type: ignore
    except Exception:
        broker_backend_base_url = "http://localhost:8008"
    return os.environ.get("BROKER_BACKEND_BASE_URL", broker_backend_base_url)


def get_broker_client() -> BrokerBackendClient:
    """Inyecta el cliente hacia el broker backend."""

    return BrokerBackendClient(base_url=_get_broker_base_url())


def get_router_middleware(
    interface: Annotated[InterfaceToBackend, Depends(get_interface_client)],
    broker_client: Annotated[BrokerBackendClient, Depends(get_broker_client)],
) -> RouterMiddleware:
    """Inyecta el orquestador de middleware."""

    return RouterMiddleware(
        interface=interface,
        jwt_settings=get_jwt_settings(),
        broker_client=broker_client,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Gestiona el ciclo de vida de la aplicación."""

    _configure_logging()
    yield


app = FastAPI(title="Middleware Frontend", lifespan=lifespan)


@app.post("/login/request-otp", response_model=LoginOtpResponse)
async def request_login_otp_endpoint(
    request: LoginOtpRequest,
    http_request: Request,
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
) -> LoginOtpResponse:
    """Endpoint para solicitar el envío del OTP."""

    try:
        ip_address, user_agent = _get_request_metadata(http_request)
        success = router.request_login_otp(
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
        return LoginOtpResponse(success=success)
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
            raise TokenValidationError("Token de sesión no proporcionado")
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
        return OrganizationCreateResponse(organization_id=organization_id)
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
