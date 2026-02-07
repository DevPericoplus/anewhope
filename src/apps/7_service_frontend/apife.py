"""Capa de API para recibir peticiones del frontend."""

from __future__ import annotations

import asyncio
import logging
import importlib.util
import os
import sys
from pathlib import Path
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
        # Validar que el usuario pertenece a la organización solicitada
        if session.organization_id != organization_id:
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
        result = router.update_user_active_status(
            user_id=user_id,
            active=request.active,
            requester_org_id=session.organization_id,
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


class ModelListResponse(BaseModel):
    """Respuesta con lista de modelos."""

    models: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class ModelMetricsResponse(BaseModel):
    """Respuesta con métricas de un modelo."""

    model_id: int
    metrics: dict[str, Any] = Field(default_factory=dict)
    training_history: list[dict[str, Any]] = Field(default_factory=list)


class TrainingPermissionsResponse(BaseModel):
    """Respuesta con permisos de entrenamiento."""

    identity_type_id: int
    permissions: dict[str, bool] = Field(default_factory=dict)


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
    protected: bool
    size: int  # Changed from size_bytes to match backend/broker
    final_c: bool
    final_i: bool
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
    router: Annotated[RouterMiddleware, Depends(get_router_middleware)],
    session: Annotated[SessionContext, Depends(get_session_context)],
) -> VersionesListResponse:
    """Obtiene todas las versiones de un proyecto."""
    _logger = logging.getLogger(__name__)
    _logger.info(
        "[middleware] Consultando versiones proyecto=%s org=%s",
        project_id,
        session.organization_id,
    )

    try:
        response = router.get_project_versions(project_id, session.organization_id, session)
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
    if request.id_organizacion != session.organization_id:
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
    if request.id_organizacion != session.organization_id:
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
        token_data = router.generate_file_operation_token(
            session=session,
            project_id=request.project_id,
            version_id=request.version_id,
            operation=request.operation,
            relative_path=request.relative_path,
            ttl_seconds=300,  # 5 minutos
        )

        # Obtener URL de fmanagement desde configuración del entorno
        fmanagement_url = get_env_value("fmanagement_base_url", "http://localhost:1666")

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
        logger.error(f"Error generando token de archivo: {exc}")
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
        logger.error(f"Error en proxy ollama health: {exc}")
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
        logger.error(f"Error en proxy ollama models: {exc}")
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
        logger.error(f"Error en proxy ollama generate: {exc}")
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
        logger.error(f"Error en proxy ollama chat: {exc}")
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
    user_id: int,
    organization_id: int,
    project_id: int,
    role_id: int,
    session: SessionContext = Depends(get_session_context),
    router: RouterMiddleware = Depends(get_router_middleware),
) -> dict[str, Any]:
    """Creates project assignment (with prerequisite validation)."""
    try:
        return router.create_project_assignment(
            user_id, organization_id, project_id, role_id, session
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
