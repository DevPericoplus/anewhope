"""Capa de API para el broker backend."""

from __future__ import annotations

import logging
import importlib.util
import os
import sys
from datetime import datetime
from pathlib import Path
from collections.abc import Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncIterator

from fastapi import Depends, FastAPI, Header, HTTPException, status, Response
from pydantic import BaseModel, Field
from typing import Annotated

try:
    from .interfacetocore import CoreBackendClient
    from .interfacetotrainer import TrainerBackendClient
    from .routerbroker import BrokerBackendRouter, BrokerBusinessError
except ImportError:  # pragma: no cover - soporte para ejecuciones fuera de paquete
    import importlib.util
    from pathlib import Path

    _base_path = Path(__file__).resolve().parent

    def _load_module(module_name: str, filename: str) -> Any:
        module_path = _base_path / filename
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    _interface_module = _load_module("interfacetocore", "interfacetocore.py")
    _trainer_module = _load_module("interfacetotrainer", "interfacetotrainer.py")
    _router_module = _load_module("routerbroker", "routerbroker.py")

    CoreBackendClient = _interface_module.CoreBackendClient
    TrainerBackendClient = _trainer_module.TrainerBackendClient
    BrokerBackendRouter = _router_module.BrokerBackendRouter
    BrokerBusinessError = _router_module.BrokerBusinessError


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


class UserStatusUpdateRequest(BaseModel):
    """Request para actualizar estado activo de un usuario."""

    user_id: int
    active: bool
    requester_org_id: int


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


class PermissionsResponse(BaseModel):
    """Respuesta con permisos del usuario."""

    user_id: int | None = None
    organization_id: int | None = None
    identity_type_id: int | None = None
    permissions: list[dict[str, Any]] = Field(default_factory=list)
    low_level_permissions: dict[str, Any] = Field(default_factory=dict)


class ProcessDataRequest(BaseModel):
    """Payload de entrada para el procesamiento."""

    payload: dict[str, Any] = Field(default_factory=dict)


class ProcessDataResponse(BaseModel):
    """Respuesta del backend procesada."""

    result: dict[str, Any]
    message: str


# === Modelos para Configuración de Entorno ===


class EnvironmentResponse(BaseModel):
    """Respuesta con el entorno activo del sistema.
    
    Este endpoint es consultado por Backend Core y fmanagement para
    configurar rutas y parámetros dinámicos según el entorno.
    
    Valores posibles: macbook, dev, pre, pro
    """

    environment: str
    source: str = "ENVIRONMENT"


# === Modelos para Training (Backend IA) ===


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
    identity_type_id: int | None = None


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
    identity_type_id: int | None = None


class TrainingStartResponse(BaseModel):
    """Respuesta de inicio de entrenamiento."""

    success: bool
    training_id: int | None = None
    message: str = ""


class TrainingStopRequest(BaseModel):
    """Payload para detener entrenamiento."""

    training_id: int
    identity_type_id: int | None = None


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


def _configure_logging() -> None:
    """Configura logging del broker backend con salida a console.log."""

    logs_dir = Path(__file__).resolve().parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Archivo de actividad específico
    activity_log_path = os.environ.get(
        "BROKER_ACTIVITY_LOG_PATH",
        str(logs_dir / "broker_backend_activity.log"),
    )

    # Archivo console.log unificado para soporte
    console_log_path = logs_dir / "console.log"

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    # Formato legible para técnicos de soporte
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | broker          | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler para activity log
    activity_handler = logging.FileHandler(activity_log_path, encoding="utf-8")
    activity_handler.setFormatter(formatter)

    # Handler para console.log (unificado)
    console_file_handler = logging.FileHandler(console_log_path, encoding="utf-8")
    console_file_handler.setFormatter(formatter)

    # Handler de consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[activity_handler, console_file_handler, console_handler],
    )


def _get_core_base_url() -> str:
    """Obtiene la URL base del backend core.
    
    Prioridad:
    1. Variable de entorno CORE_BACKEND_BASE_URL
    2. Valor de env.yaml (core_backend_base_url)
    3. Valor de protected_values.py
    4. Fallback a localhost:8003
    """

    env_settings = _load_env_settings_module("broker_env_settings")
    # get_env_value carga env.yaml y lee de os.environ
    env_value = env_settings.get_env_value("CORE_BACKEND_BASE_URL", "")
    if env_value:
        return env_value
    # Fallback a protected_values.py
    return env_settings.get_protected_value(
        "core_backend_base_url", "http://localhost:8003"
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


@contextmanager
def _http_client_context() -> Iterator[CoreBackendClient]:
    """Crea el cliente HTTP para backend core."""

    client = CoreBackendClient(base_url=_get_core_base_url())
    try:
        yield client
    finally:
        client.close()


def get_core_client() -> CoreBackendClient:
    """Inyecta el cliente hacia backend core."""

    return CoreBackendClient(base_url=_get_core_base_url())


def _get_trainer_base_url() -> str:
    """Obtiene la URL base del backend IA (trainer).
    
    Prioridad:
    1. Variable de entorno TRAINER_BACKEND_BASE_URL
    2. Valor de env.yaml (trainer_backend_base_url)
    3. Valor de protected_values.py
    4. Fallback a localhost:8004
    """

    env_settings = _load_env_settings_module("broker_env_settings_trainer")
    # get_env_value carga env.yaml y lee de os.environ
    env_value = env_settings.get_env_value("TRAINER_BACKEND_BASE_URL", "")
    if env_value:
        return env_value
    # Fallback a protected_values.py
    return env_settings.get_protected_value(
        "trainer_backend_base_url", "http://localhost:8004"
    )


def get_trainer_client() -> TrainerBackendClient:
    """Inyecta el cliente hacia backend IA (trainer)."""

    return TrainerBackendClient(base_url=_get_trainer_base_url())


def get_client_app(
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> str:
    """Extrae el header X-Client-App de la petición."""

    return client_app or "unknown"


def get_authorization(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> str | None:
    """Extrae el header Authorization (JWT) de la petición."""

    return authorization


def get_session_token(
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> str | None:
    """Extrae el header X-Session-Token de la petición."""

    return session_token


def get_router_broker(
    core_client: CoreBackendClient = Depends(get_core_client),
    trainer_client: TrainerBackendClient = Depends(get_trainer_client),
    client_app: str = Depends(get_client_app),
    authorization: str | None = Depends(get_authorization),
    session_token: str | None = Depends(get_session_token),
) -> BrokerBackendRouter:
    """Inyecta el orquestador del broker con contexto de seguridad.

    Propaga los headers de seguridad (Authorization, X-Session-Token) al router
    para que los clientes del Backend Core y Backend IA los reciban,
    manteniendo el contexto de sesión en todo el flujo (Security by Design).
    """

    router = BrokerBackendRouter(
        core_client=core_client,
        trainer_client=trainer_client,
    )
    router.set_client_app(client_app)
    router.set_security_context(authorization, session_token)
    return router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Gestiona el ciclo de vida de la aplicación."""

    _configure_logging()
    yield


app = FastAPI(title="Broker Backend", lifespan=lifespan)


@app.get("/users")
def list_users(
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> list[dict[str, Any]]:
    """Lista usuarios."""

    try:
        return router.fetch_users()
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.put("/users")
def store_users(
    payload: list[dict[str, Any]],
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Guarda usuarios con confirmación detallada."""

    try:
        router.store_users(payload)
        
        # Retornar respuesta más informativa
        return {
            "success": True,
            "users_count": len(payload),
            "timestamp": datetime.now().isoformat(),
        }
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/users", response_model=UserCreateResponse)
def create_user(
    payload: UserCreateRequest,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> UserCreateResponse:
    """Crea usuario."""

    try:
        response = router.create_user(payload.model_dump())
        return UserCreateResponse(**response)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.patch("/users/{user_id}/status", response_model=UserStatusUpdateResponse)
def update_user_status(
    user_id: int,
    payload: UserStatusUpdateRequest,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> UserStatusUpdateResponse:
    """Actualiza el estado activo/inactivo de un usuario.
    
    Este endpoint recibe peticiones del middleware y las reenvía al backend core
    para actualizar el estado en MariaDB.
    """
    try:
        response = router.update_user_status(
            user_id=user_id,
            active=payload.active,
            requester_org_id=payload.requester_org_id,
        )
        return UserStatusUpdateResponse(**response)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/users/check-exists", response_model=UserExistsResponse)
def check_user_exists(
    payload: UserExistsRequest,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> UserExistsResponse:
    """Verifica si existe un usuario por nombre de usuario.
    
    Flujo: Middleware → Broker (aquí) → Backend Core → JSON/MariaDB
    """
    try:
        result = router.check_user_exists(payload.user_name)
        return UserExistsResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/users/by-email", response_model=UserByEmailResponse)
def get_user_by_email(
    payload: UserByEmailRequest,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> UserByEmailResponse:
    """Obtiene datos de un usuario por email.
    
    Flujo: Middleware → Broker (aquí) → Backend Core → JSON/MariaDB
    """
    try:
        result = router.get_user_by_email(payload.email)
        return UserByEmailResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/users/update-password", response_model=UpdatePasswordResponse)
def update_user_password(
    payload: UpdatePasswordRequest,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> UpdatePasswordResponse:
    """Actualiza contraseña y OTP de un usuario.
    
    Flujo: Middleware → Broker (aquí) → Backend Core → JSON/MariaDB
    """
    try:
        result = router.update_user_password(
            email=payload.email,
            new_password=payload.new_password,
            new_otp=payload.new_otp,
        )
        return UpdatePasswordResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/organizations")
def list_organizations(
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> list[dict[str, Any]]:
    """Lista organizaciones."""

    try:
        return router.fetch_organizations()
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.put("/organizations")
def store_organizations(
    payload: list[dict[str, Any]],
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Guarda organizaciones."""

    try:
        router.store_organizations(payload)
        return {"success": True}
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/organizations/check-name", response_model=OrganizationCheckResponse)
def check_organization_name(
    payload: OrganizationCheckRequest,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> OrganizationCheckResponse:
    """Valida si la organización existe."""

    try:
        response = router.check_organization_name(payload.model_dump())
        return OrganizationCheckResponse(**response)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/organizations", response_model=OrganizationCreateResponse)
def create_organization(
    payload: OrganizationCreateRequest,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> OrganizationCreateResponse:
    """Crea organización."""

    try:
        response = router.create_organization(payload.model_dump())
        return OrganizationCreateResponse(**response)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/roles")
def list_roles(
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> list[dict[str, Any]]:
    """Lista roles."""

    try:
        return router.fetch_roles()
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/basic-permissions")
def list_basic_permissions(
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> list[dict[str, Any]]:
    """Lista permisos básicos."""

    try:
        return router.fetch_basic_permissions()
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/low-level-permissions")
def list_low_level_permissions(
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> list[dict[str, Any]]:
    """Lista permisos de bajo nivel."""

    try:
        return router.fetch_low_level_permissions()
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/manage-roles-by-org")
def list_manage_roles(
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> list[dict[str, Any]]:
    """Lista roles por organización."""

    try:
        return router.fetch_manage_roles()
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.put("/roles")
def store_roles(
    payload: list[dict[str, Any]],
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Guarda roles en MariaDB."""

    try:
        router.store_roles(payload)
        return {"success": True, "count": len(payload)}
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.put("/basic-permissions")
def store_basic_permissions(
    payload: list[dict[str, Any]],
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Guarda permisos básicos en MariaDB."""

    try:
        router.store_basic_permissions(payload)
        return {"success": True, "count": len(payload)}
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.put("/low-level-permissions")
def store_low_level_permissions(
    payload: list[dict[str, Any]],
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Guarda permisos de bajo nivel en MariaDB."""

    try:
        router.store_low_level_permissions(payload)
        return {"success": True, "count": len(payload)}
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.put("/manage-roles-by-org")
def store_manage_roles(
    payload: list[dict[str, Any]],
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Guarda roles por organización."""

    try:
        router.store_manage_roles(payload)
        return {"success": True}
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/permissions", response_model=PermissionsResponse)
def get_permissions(
    identity_type_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> PermissionsResponse:
    """Obtiene permisos asociados a un rol."""

    try:
        response = router.get_permissions(identity_type_id)
        return PermissionsResponse(**response)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/process-data", response_model=ProcessDataResponse)
def process_data(
    request: ProcessDataRequest,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> ProcessDataResponse:
    """Reenvía el procesamiento al backend core."""

    try:
        response = router.process_data(request.payload)
        return ProcessDataResponse(
            result=response,
            message="Procesamiento enviado al backend core",
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


# === Endpoints de Entrenamiento (Backend IA) ===


@app.get("/training/health", response_model=TrainerHealthResponse)
def trainer_health_check(
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> TrainerHealthResponse:
    """Health check del servicio trainer."""

    try:
        response = router.trainer_health_check()
        return TrainerHealthResponse(**response)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


# =============================================================================
# OLLAMA TRAINER ENDPOINTS
# =============================================================================

@app.get("/training/ollama/health")
def ollama_health(
    router: BrokerBackendRouter = Depends(get_router_broker),
):
    """Health check de Ollama en el trainer."""
    try:
        return router.ollama_health()
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/training/ollama/models")
def ollama_list_models(
    router: BrokerBackendRouter = Depends(get_router_broker),
):
    """Lista modelos disponibles en Ollama."""
    try:
        return router.ollama_list_models()
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/training/ollama/generate")
def ollama_generate(
    request: dict,
    router: BrokerBackendRouter = Depends(get_router_broker),
):
    """Genera texto con Ollama."""
    try:
        return router.ollama_generate(request)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/training/ollama/chat")
def ollama_chat(
    request: dict,
    router: BrokerBackendRouter = Depends(get_router_broker),
):
    """Chat con Ollama."""
    try:
        return router.ollama_chat(request)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/training/clone-version", response_model=VersionCloneResponse)
def clone_version_for_training(
    payload: VersionCloneRequest,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> VersionCloneResponse:
    """Clona una versión para entrenamiento."""

    try:
        response = router.clone_version_for_training(payload.model_dump())
        return VersionCloneResponse(**response)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/training/start", response_model=TrainingStartResponse)
def start_training(
    payload: TrainingStartRequest,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> TrainingStartResponse:
    """Inicia un proceso de entrenamiento."""

    try:
        response = router.start_training(payload.model_dump())
        return TrainingStartResponse(**response)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/training/stop", response_model=TrainingStopResponse)
def stop_training(
    payload: TrainingStopRequest,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> TrainingStopResponse:
    """Detiene un proceso de entrenamiento."""

    try:
        response = router.stop_training(payload.model_dump())
        return TrainingStopResponse(**response)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/training/{training_id}/status", response_model=TrainingStatusResponse)
def get_training_status(
    training_id: int,
    identity_type_id: int | None = None,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> TrainingStatusResponse:
    """Obtiene el estado de un entrenamiento."""

    try:
        response = router.get_training_status(training_id, identity_type_id)
        return TrainingStatusResponse(**response)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/training/models", response_model=ModelListResponse)
def list_models(
    id_organization: int | None = None,
    id_project: int | None = None,
    identity_type_id: int | None = None,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> ModelListResponse:
    """Lista modelos entrenados."""

    try:
        response = router.list_models(id_organization, id_project, identity_type_id)
        return ModelListResponse(**response)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/training/models/{model_id}/metrics", response_model=ModelMetricsResponse)
def get_model_metrics(
    model_id: int,
    identity_type_id: int | None = None,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> ModelMetricsResponse:
    """Obtiene métricas de un modelo."""

    try:
        response = router.get_model_metrics(model_id, identity_type_id)
        return ModelMetricsResponse(**response)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/training/permissions", response_model=TrainingPermissionsResponse)
def get_training_permissions(
    identity_type_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> TrainingPermissionsResponse:
    """Obtiene permisos de entrenamiento para un rol."""

    try:
        response = router.get_training_permissions(identity_type_id)
        return TrainingPermissionsResponse(**response)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
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
    id_organizacion: int
    cliente_id: int
    id_proyecto: int | None = None


class TicketUpdateRequest(BaseModel):
    """Payload para actualizar un ticket."""

    estado: str | None = None
    prioridad: str | None = None
    user_id: int | None = None


class TicketRespuestaRequest(BaseModel):
    """Payload para añadir respuesta."""

    respuesta: str
    user_id: int


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
    version_folder: str


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


# DTOs para Estados de Versión
# ========================================================================


class VersionStateDto(BaseModel):
    """Estado completo de una versión."""

    id: int
    id_organizacion: int
    id_proyecto: int
    id_version: int
    state: str
    protected: bool
    size: int  # Tamaño en bytes (sin _bytes en el nombre)
    final_c: bool
    final_i: bool
    created_at: str
    updated_at: str


class VersionStateResponse(BaseModel):
    """Respuesta con estado de versión."""

    success: bool
    message: str
    data: VersionStateDto | None


class UpdateVersionStateRequest(BaseModel):
    """Request para actualizar estado de versión."""

    state: str | None = None
    protected: bool | None = None
    size_bytes: int | None = None
    final_c: bool | None = None
    final_i: bool | None = None
    user_id: int


class VersionEventDto(BaseModel):
    """Evento de versión para auditoría."""

    id: int
    id_organizacion: int
    id_proyecto: int
    id_version: int
    evento: str
    mensaje: str
    user_id: int
    user_name: str | None
    old_state: str | None
    new_state: str | None
    metadata: dict | None
    timestamp: str


class VersionEventsResponse(BaseModel):
    """Respuesta con lista de eventos de versión."""

    success: bool
    message: str
    data: list[VersionEventDto]
    total: int


class CreateVersionFullRequest(BaseModel):
    """Request para crear versión completa (DB + fmanagement)."""

    id_organizacion: int
    nombre_version: str
    user_id: int
    user_name: str
    identity_type_id: int
    descripcion: str | None = None
    clone_from_version_id: int | None = None
    initial_state: str = "Abierta"
    protected: bool = False
    final_c: bool = False
    final_i: bool = False


class CreateVersionFullResponse(BaseModel):
    """Respuesta de creación completa de versión."""

    success: bool
    message: str
    version_id: int | None
    version_folder: str | None
    fmanagement_result: dict | None


class FmanagementListRequest(BaseModel):
    """Request para listar estructura vía fmanagement."""

    org_folder: str
    prj_folder: str
    version_folder: str
    user_id: int
    identity_type_id: int


class FmanagementListResponse(BaseModel):
    """Respuesta de listado de fmanagement."""

    success: bool
    items: list
    mensaje: str | None = None


class FmanagementOperationRequest(BaseModel):
    """Request genérico para operaciones fmanagement."""

    operation: str
    params: dict


class FmanagementOperationResponse(BaseModel):
    """Respuesta de operación fmanagement."""

    success: bool
    message: str
    data: dict | None


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
def get_organization_projects(
    organization_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
    include_deleted: bool = False,
) -> ProjectListResponse:
    """Obtiene los proyectos de una organización.

    Flujo: Middleware → Broker → Backend Core → MariaDB
    
    Args:
        include_deleted: Si True, incluye proyectos con existe=false
    """
    headers = {
        "Authorization": authorization or "",
        "X-Session-Token": session_token or "",
        "X-Client-App": client_app,
    }
    try:
        result = router.get_organization_projects(
            organization_id, headers, include_deleted=include_deleted
        )
        return ProjectListResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/projects", response_model=ProjectCreateResponse)
def create_project(
    request: ProjectCreateRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> ProjectCreateResponse:
    """Crea un nuevo proyecto.

    Flujo: Middleware → Broker → Backend Core → MariaDB (INSERT)
    """
    headers = {
        "Authorization": authorization or "",
        "X-Session-Token": session_token or "",
        "X-Client-App": client_app,
    }
    try:
        result = router.create_project(request.model_dump(), headers)
        return ProjectCreateResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch("/projects/{project_id}", response_model=ProjectUpdateResponse)
def update_project(
    project_id: int,
    request: ProjectUpdateRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> ProjectUpdateResponse:
    """Actualiza un proyecto existente.

    Flujo: Middleware → Broker → Backend Core → MariaDB (UPDATE)
    """
    headers = {
        "Authorization": authorization or "",
        "X-Session-Token": session_token or "",
        "X-Client-App": client_app,
    }
    try:
        update_data = {k: v for k, v in request.model_dump().items() if v is not None}
        result = router.update_project(project_id, update_data, headers)
        return ProjectUpdateResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.delete("/projects/{project_id}", response_model=ProjectDeleteResponse)
def delete_project(
    project_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> ProjectDeleteResponse:
    """Elimina un proyecto.

    Flujo: Middleware → Broker → Backend Core → MariaDB (DELETE)
    """
    headers = {
        "Authorization": authorization or "",
        "X-Session-Token": session_token or "",
        "X-Client-App": client_app,
    }
    try:
        result = router.delete_project(project_id, headers)
        return ProjectDeleteResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/projects/{project_id}/support", response_model=ProjectSupportResponse)
def request_project_support(
    project_id: int,
    request: ProjectSupportRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> ProjectSupportResponse:
    """Registra una solicitud de soporte para un proyecto.

    Flujo: Middleware → Broker → Backend Core → MariaDB (CALL sp_registrar_cambio_proyecto)
    """
    headers = {
        "Authorization": authorization or "",
        "X-Session-Token": session_token or "",
        "X-Client-App": client_app,
    }
    try:
        result = router.request_project_support(
            project_id,
            request.tipo_cambio,
            request.descripcion or "",
            headers,
        )
        return ProjectSupportResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# === Endpoints de Configuración del Sistema ===


@app.get("/config/environment", response_model=EnvironmentResponse)
def get_active_environment() -> EnvironmentResponse:
    """Obtiene el entorno activo del sistema.
    
    Lee la variable ENVIRONMENT del archivo .env del proyecto.
    Este endpoint es usado por:
    - Backend Core: para configuraciones dinámicas
    - fmanagement (via Backend Core): para determinar rutas base
    
    Flujo típico:
        fmanagement → Backend Core → Broker (este endpoint)
    
    Returns:
        EnvironmentResponse con el entorno activo (macbook, dev, pre, pro)
    """
    environment = os.environ.get("ENVIRONMENT", "unknown")
    
    logging.getLogger(__name__).info(
        "[config] Consulta de entorno activo: %s",
        environment,
    )
    
    return EnvironmentResponse(
        environment=environment,
        source="ENVIRONMENT",
    )


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
    """DTO de rol base para proyectos (catálogo maestro)."""

    id: int
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
def get_project_roles_base(
    router: BrokerBackendRouter = Depends(get_router_broker),
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> ProjectRolesBaseResponse:
    """Obtiene el catálogo maestro de roles base para proyectos.

    Enruta a Backend Core → MariaDB (proyectos_roles_base)
    """
    logger = logging.getLogger(__name__)
    logger.info("[%s] Consultando catálogo de roles base", client_app or "broker")

    headers = {"X-Client-App": client_app or "broker"}

    try:
        result = router.get_project_roles_base(headers)
        return ProjectRolesBaseResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error obteniendo roles base")
        raise HTTPException(
            status_code=500, detail=f"Error interno: {exc}"
        ) from exc


@app.get(
    "/users/{user_id}/project-roles",
    response_model=UserProjectRolesResponse,
    tags=["project-roles"],
)
def get_user_project_roles(
    user_id: int,
    organization_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> UserProjectRolesResponse:
    """Obtiene los roles de un usuario en proyectos.

    Enruta a Backend Core → MariaDB (proyectos_roles)
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[%s] Consultando roles de usuario %s en org %s",
        client_app or "broker",
        user_id,
        organization_id,
    )

    headers = {"X-Client-App": client_app or "broker"}

    try:
        result = router.get_user_project_roles(user_id, organization_id, headers)
        return UserProjectRolesResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error obteniendo roles de usuario")
        raise HTTPException(
            status_code=500, detail=f"Error interno: {exc}"
        ) from exc


@app.post(
    "/project-roles/assign",
    response_model=AssignUserToProjectResponse,
    tags=["project-roles"],
)
def assign_user_to_project(
    request: AssignUserToProjectRequest,
    router: BrokerBackendRouter = Depends(get_router_broker),
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> AssignUserToProjectResponse:
    """Asigna un usuario a un proyecto.

    Enruta a Backend Core → MariaDB (INSERT/UPDATE proyectos_roles)
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[%s] Asignando usuario %s a proyecto %s",
        client_app or "broker",
        request.id_usuario,
        request.id_proyecto,
    )

    headers = {"X-Client-App": client_app or "broker"}

    try:
        result = router.assign_user_to_project(request.model_dump(), headers)
        return AssignUserToProjectResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error asignando usuario a proyecto")
        raise HTTPException(
            status_code=500, detail=f"Error interno: {exc}"
        ) from exc


@app.post(
    "/project-roles/remove",
    response_model=RemoveUserFromProjectResponse,
    tags=["project-roles"],
)
def remove_user_from_project(
    request: RemoveUserFromProjectRequest,
    router: BrokerBackendRouter = Depends(get_router_broker),
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> RemoveUserFromProjectResponse:
    """Quita un usuario de un proyecto.

    Enruta a Backend Core → MariaDB (UPDATE proyectos_roles active=0)
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[%s] Quitando usuario %s de proyecto %s",
        client_app or "broker",
        request.id_usuario,
        request.id_proyecto,
    )

    headers = {"X-Client-App": client_app or "broker"}

    try:
        result = router.remove_user_from_project(request.model_dump(), headers)
        return RemoveUserFromProjectResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error quitando usuario de proyecto")
        raise HTTPException(
            status_code=500, detail=f"Error interno: {exc}"
        ) from exc


# ============================================================================
# ENDPOINTS DE TICKETS DE SOPORTE
# ============================================================================


@app.post("/tickets", response_model=TicketCreateResponse, tags=["tickets"])
def create_ticket(
    request: TicketCreateRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> TicketCreateResponse:
    """Crea un nuevo ticket de soporte.

    Enruta a Backend Core → MariaDB (INSERT tickets + ticket_interacciones)
    """
    headers = {
        "Authorization": authorization or "",
        "X-Session-Token": session_token or "",
        "X-Client-App": client_app,
    }
    try:
        result = router.create_ticket(request.model_dump(), headers)
        return TicketCreateResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(
    "/tickets/organization/{organization_id}",
    response_model=TicketListResponse,
    tags=["tickets"],
)
def get_organization_tickets(
    organization_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> TicketListResponse:
    """Obtiene los tickets de una organización."""
    headers = {
        "Authorization": authorization or "",
        "X-Session-Token": session_token or "",
        "X-Client-App": client_app,
    }
    try:
        result = router.get_organization_tickets(organization_id, headers)
        return TicketListResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/tickets/{ticket_id}", response_model=TicketDto, tags=["tickets"])
def get_ticket_detail(
    ticket_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> TicketDto:
    """Obtiene el detalle de un ticket específico."""
    headers = {
        "Authorization": authorization or "",
        "X-Session-Token": session_token or "",
        "X-Client-App": client_app,
    }
    try:
        result = router.get_ticket_detail(ticket_id, headers)
        return TicketDto(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/tickets/{ticket_id}", response_model=TicketUpdateResponse, tags=["tickets"])
def update_ticket(
    ticket_id: int,
    request: TicketUpdateRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> TicketUpdateResponse:
    """Actualiza estado/prioridad de un ticket."""
    headers = {
        "Authorization": authorization or "",
        "X-Session-Token": session_token or "",
        "X-Client-App": client_app,
    }
    try:
        update_data = {k: v for k, v in request.model_dump().items() if v is not None}
        result = router.update_ticket(ticket_id, update_data, headers)
        return TicketUpdateResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/tickets/{ticket_id}/respuesta",
    response_model=TicketUpdateResponse,
    tags=["tickets"],
)
def add_ticket_response(
    ticket_id: int,
    request: TicketRespuestaRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> TicketUpdateResponse:
    """Añade respuesta a un ticket."""
    headers = {
        "Authorization": authorization or "",
        "X-Session-Token": session_token or "",
        "X-Client-App": client_app,
    }
    try:
        result = router.add_ticket_response(
            ticket_id, request.respuesta, request.user_id, headers
        )
        return TicketUpdateResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ============================================================================
# ENDPOINTS DE TECNOLOGÍAS
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
    total: int = 0


class AsignarTecnologiaRequest(BaseModel):
    """Request para asignar/actualizar tecnología."""

    id_tecnologia: int
    coste_base: str = "17% sobre base"


@app.get("/tecnologias", response_model=TecnologiasListResponse, tags=["tecnologias"])
def get_tecnologias(
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> TecnologiasListResponse:
    """Obtiene todas las tecnologías disponibles.

    Enruta a Backend Core → MariaDB (SELECT tecnologia)
    """
    logger = logging.getLogger(__name__)
    logger.info("[broker] Consultando tecnologías")

    try:
        result = router.get_tecnologias()
        return TecnologiasListResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error obteniendo tecnologías")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get(
    "/proyectos/{project_id}/tecnologia",
    response_model=ProyectoTecnologiaResponse,
    tags=["tecnologias"],
)
def get_proyecto_tecnologia(
    project_id: int,
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> ProyectoTecnologiaResponse:
    """Obtiene la tecnología asignada a un proyecto.

    Enruta a Backend Core → MariaDB (SELECT proyectos_tecnologia)
    """
    logger = logging.getLogger(__name__)
    logger.info("[broker] Consultando tecnología de proyecto %s", project_id)

    try:
        result = router.get_proyecto_tecnologia(project_id)
        return ProyectoTecnologiaResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error obteniendo tecnología de proyecto")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post(
    "/proyectos/{project_id}/tecnologia",
    response_model=ProyectoTecnologiaResponse,
    tags=["tecnologias"],
)
def asignar_tecnologia(
    project_id: int,
    request: AsignarTecnologiaRequest,
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> ProyectoTecnologiaResponse:
    """Asigna una tecnología a un proyecto (primera asignación).

    Enruta a Backend Core → MariaDB (INSERT proyectos_tecnologia)
    """
    logger = logging.getLogger(__name__)
    logger.info("[broker] Asignando tecnología %s a proyecto %s", request.id_tecnologia, project_id)

    try:
        result = router.asignar_tecnologia(project_id, request.model_dump())
        return ProyectoTecnologiaResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error asignando tecnología")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.patch(
    "/proyectos/{project_id}/tecnologia",
    response_model=ProyectoTecnologiaResponse,
    tags=["tecnologias"],
)
def actualizar_tecnologia(
    project_id: int,
    request: AsignarTecnologiaRequest,
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> ProyectoTecnologiaResponse:
    """Actualiza la tecnología de un proyecto (solo Backoffice).

    Enruta a Backend Core → MariaDB (UPDATE proyectos_tecnologia)
    """
    logger = logging.getLogger(__name__)
    logger.info("[broker] Actualizando tecnología de proyecto %s a %s", project_id, request.id_tecnologia)

    try:
        result = router.actualizar_tecnologia(project_id, request.model_dump())
        return ProyectoTecnologiaResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error actualizando tecnología")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get(
    "/organizaciones/{org_id}/tecnologias-asignadas",
    response_model=TecnologiasAsignadasResponse,
    tags=["tecnologias"],
)
def get_tecnologias_asignadas_org(
    org_id: int,
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> TecnologiasAsignadasResponse:
    """Obtiene todas las tecnologías asignadas a proyectos de una organización.

    Enruta a Backend Core → MariaDB
    """
    logger = logging.getLogger(__name__)
    logger.info("[broker] Consultando tecnologías asignadas para organización %s", org_id)

    try:
        result = router.get_tecnologias_asignadas_org(org_id)
        return TecnologiasAsignadasResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error consultando tecnologías asignadas")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ========================================================================
# Endpoints de Gestión de Versiones
# ========================================================================


@app.get(
    "/proyectos/{project_id}/versiones",
    response_model=VersionesListResponse,
    tags=["versiones"],
)
def get_project_versions(
    project_id: int,
    org_id: int,
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> VersionesListResponse:
    """Obtiene todas las versiones de un proyecto.

    Enruta a Backend Core → MariaDB
    """
    logger = logging.getLogger(__name__)
    logger.info("[broker] Consultando versiones proyecto=%s org=%s", project_id, org_id)

    try:
        result = router.get_project_versions(project_id, org_id)
        return VersionesListResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error consultando versiones")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post(
    "/proyectos/{project_id}/versiones",
    response_model=CrearVersionResponse,
    tags=["versiones"],
)
def create_project_version(
    project_id: int,
    request: CrearVersionRequest,
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> CrearVersionResponse:
    """Crea una nueva versión para un proyecto.

    Enruta a Backend Core → MariaDB
    """
    logger = logging.getLogger(__name__)
    logger.info("[broker] Creando versión proyecto=%s org=%s", project_id, request.id_organizacion)

    try:
        result = router.create_project_version(project_id, request.id_organizacion)
        return CrearVersionResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error creando versión")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Endpoints de Estados de Versión
# ========================================================================


@app.get(
    "/proyectos/{project_id}/versiones/{version_id}/estado",
    response_model=VersionStateResponse,
    tags=["version-states"],
)
def get_version_state(
    project_id: int,
    version_id: int,
    org_id: int,
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> VersionStateResponse:
    """Obtiene el estado actual de una versión.
    
    Enruta a Backend Core → MariaDB
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[broker] [%s] Obteniendo estado versión=%s proyecto=%s org=%s",
        client_app,
        version_id,
        project_id,
        org_id,
    )

    try:
        result = router.get_version_state(project_id, version_id, org_id)
        return VersionStateResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error obteniendo estado versión")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.patch(
    "/proyectos/{project_id}/versiones/{version_id}/estado",
    response_model=VersionStateResponse,
    tags=["version-states"],
)
def update_version_state(
    project_id: int,
    version_id: int,
    org_id: int,
    request: UpdateVersionStateRequest,
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> VersionStateResponse:
    """Actualiza el estado de una versión.
    
    Enruta a Backend Core → MariaDB
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[broker] [%s] Actualizando estado versión=%s proyecto=%s",
        client_app,
        version_id,
        project_id,
    )

    try:
        update_data = request.model_dump(exclude_unset=True)
        logger.info(
            "[broker] DEBUG update_data desde request.model_dump(): %s",
            update_data,
        )
        result = router.update_version_state(project_id, version_id, org_id, update_data)
        return VersionStateResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error actualizando estado versión")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get(
    "/proyectos/{project_id}/versiones/{version_id}/eventos",
    response_model=VersionEventsResponse,
    tags=["version-states"],
)
def get_version_events(
    project_id: int,
    version_id: int,
    org_id: int,
    limit: int = 50,
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> VersionEventsResponse:
    """Obtiene el historial de eventos de una versión.
    
    Enruta a Backend Core → MariaDB
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[broker] [%s] Obteniendo eventos versión=%s proyecto=%s",
        client_app,
        version_id,
        project_id,
    )

    try:
        result = router.get_version_events(project_id, version_id, org_id, limit)
        return VersionEventsResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error obteniendo eventos versión")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post(
    "/proyectos/{project_id}/versiones/crear-completa",
    response_model=CreateVersionFullResponse,
    tags=["versiones"],
)
def create_version_full(
    project_id: int,
    request: CreateVersionFullRequest,
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> CreateVersionFullResponse:
    """Crea una nueva versión completa (DB + fmanagement).
    
    Enruta a Backend Core → MariaDB + fmanagement
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[broker] [%s] Creando versión completa proyecto=%s org=%s user=%s",
        client_app,
        project_id,
        request.id_organizacion,
        request.user_id,
    )

    try:
        result = router.create_version_full(project_id, request.model_dump())
        return CreateVersionFullResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error creando versión completa")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Endpoints de Integración con fmanagement
# ========================================================================


@app.post(
    "/fmanagement/list",
    response_model=FmanagementListResponse,
    tags=["fmanagement"],
)
def fmanagement_list(
    request: FmanagementListRequest,
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> FmanagementListResponse:
    """Lista estructura de archivos vía fmanagement.
    
    Enruta a Backend Core → fmanagement
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[broker] [%s] Listando fmanagement org=%s prj=%s version=%s",
        client_app,
        request.org_folder,
        request.prj_folder,
        request.version_folder,
    )

    try:
        result = router.fmanagement_list(request.model_dump())
        return FmanagementListResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error listando fmanagement")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post(
    "/fmanagement/operation",
    response_model=FmanagementOperationResponse,
    tags=["fmanagement"],
)
def fmanagement_operation(
    request: FmanagementOperationRequest,
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> FmanagementOperationResponse:
    """Ejecuta una operación genérica en fmanagement.
    
    Enruta a Backend Core → fmanagement
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[broker] [%s] Operación fmanagement: %s",
        client_app,
        request.operation,
    )

    try:
        result = router.fmanagement_operation(request.model_dump())
        return FmanagementOperationResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error en operación fmanagement")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Endpoints de Estados de Versión
# ========================================================================


@app.get(
    "/proyectos/{project_id}/versiones/{version_id}/estado",
    response_model=VersionStateResponse,
    tags=["version-states"],
)
def get_version_state(
    project_id: int,
    version_id: int,
    org_id: int,
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> VersionStateResponse:
    """Obtiene el estado actual de una versión.
    
    Enruta a Backend Core → MariaDB
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[broker] Obteniendo estado versión=%s proyecto=%s org=%s",
        version_id,
        project_id,
        org_id,
    )

    try:
        result = router.get_version_state(project_id, version_id, org_id)
        return VersionStateResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error obteniendo estado de versión")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.patch(
    "/proyectos/{project_id}/versiones/{version_id}/estado",
    response_model=VersionStateResponse,
    tags=["version-states"],
)
def update_version_state(
    project_id: int,
    version_id: int,
    org_id: int,
    request: UpdateVersionStateRequest,
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> VersionStateResponse:
    """Actualiza el estado de una versión.
    
    Enruta a Backend Core → MariaDB
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[broker] Actualizando estado versión=%s proyecto=%s",
        version_id,
        project_id,
    )

    try:
        result = router.update_version_state(
            project_id, version_id, org_id, request.model_dump(exclude_unset=True)
        )
        return VersionStateResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error actualizando estado de versión")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get(
    "/proyectos/{project_id}/versiones/{version_id}/eventos",
    response_model=VersionEventsResponse,
    tags=["version-states"],
)
def get_version_events(
    project_id: int,
    version_id: int,
    org_id: int,
    limit: int = 50,
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> VersionEventsResponse:
    """Obtiene el historial de eventos de una versión.
    
    Enruta a Backend Core → MariaDB
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[broker] Obteniendo eventos versión=%s proyecto=%s",
        version_id,
        project_id,
    )

    try:
        result = router.get_version_events(project_id, version_id, org_id, limit)
        return VersionEventsResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error obteniendo eventos de versión")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post(
    "/proyectos/{project_id}/versiones/crear-completa",
    response_model=CreateVersionFullResponse,
    tags=["versiones"],
)
def create_version_full(
    project_id: int,
    request: CreateVersionFullRequest,
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> CreateVersionFullResponse:
    """Crea una nueva versión completa (DB + fmanagement).
    
    Enruta a Backend Core → MariaDB + fmanagement
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[broker] Creando versión completa proyecto=%s org=%s user=%s",
        project_id,
        request.id_organizacion,
        request.user_id,
    )

    try:
        result = router.create_version_full(
            project_id,
            request.id_organizacion,
            request.user_id,
            request.identity_type_id,
            request.descripcion,
            request.clone_from_version,
        )
        return CreateVersionFullResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error creando versión completa")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Endpoints de Integración con fmanagement
# ========================================================================


@app.post(
    "/fmanagement/list",
    response_model=FmanagementListResponse,
    tags=["fmanagement"],
)
def fmanagement_list(
    request: FmanagementListRequest,
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> FmanagementListResponse:
    """Lista estructura de archivos vía fmanagement.
    
    Enruta a Backend Core → fmanagement
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[broker] Listando fmanagement org=%s prj=%s version=%s",
        request.org_folder,
        request.prj_folder,
        request.version_folder,
    )

    try:
        result = router.fmanagement_list(
            request.org_folder,
            request.prj_folder,
            request.version_folder,
            request.user_id,
            request.identity_type_id,
        )
        return FmanagementListResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error listando fmanagement")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post(
    "/fmanagement/operation",
    response_model=FmanagementOperationResponse,
    tags=["fmanagement"],
)
def fmanagement_operation(
    request: FmanagementOperationRequest,
    client_app: str = Depends(get_client_app),
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> FmanagementOperationResponse:
    """Ejecuta una operación genérica en fmanagement.
    
    Enruta a Backend Core → fmanagement
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[broker] Operación fmanagement: %s",
        request.operation,
    )

    try:
        result = router.fmanagement_operation(
            request.operation,
            request.params,
        )
        return FmanagementOperationResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error en operación fmanagement")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post(
    "/fmanagement/download",
    tags=["fmanagement"],
)
def fmanagement_download(
    request: FmanagementOperationRequest,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> Response:
    """Descarga un archivo vía fmanagement (binario)."""
    try:
        content = router.fmanagement_download(request.params)
        filename = request.params.get("filename", "download")
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/fmanagement/diff",
    response_model=FmanagementOperationResponse,
    tags=["fmanagement"],
)
def fmanagement_diff(
    request: dict[str, Any],
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> FmanagementOperationResponse:
    """Compara versiones vía fmanagement."""
    try:
        result = router.fmanagement_diff(request)
        return FmanagementOperationResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/fmanagement/transfer",
    response_model=FmanagementOperationResponse,
    tags=["fmanagement"],
)
def fmanagement_transfer(
    request: dict[str, Any],
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> FmanagementOperationResponse:
    """Transfiere versiones vía fmanagement."""
    try:
        result = router.fmanagement_transfer(request)
        return FmanagementOperationResponse(**result)
    except BrokerBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ============================================================================
# ASSIGNMENTS - Gestor de asignaciones (SuperAdmin only)
# ============================================================================

@app.get("/assignments/organizations", tags=["assignments"])
def list_organizations_for_assignments_endpoint(
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> list[dict[str, Any]]:
    """Lista todas las organizaciones para assignments."""
    try:
        return router.list_organizations()
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/assignments/roles", tags=["assignments"])
def list_roles_for_assignments_endpoint(
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> list[dict[str, Any]]:
    """Lista todos los roles para assignments."""
    try:
        return router.list_roles()
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/assignments/internal-users", tags=["assignments"])
def get_internal_users_endpoint(
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> list[dict[str, Any]]:
    """Gets internal users."""
    try:
        return router.get_internal_users()
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/assignments/organizations/{organization_id}", tags=["assignments"])
def get_organization_assignments_endpoint(
    organization_id: int,
    identity_type_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> list[dict[str, Any]]:
    """Gets organization assignments."""
    try:
        return router.get_organization_assignments(
            organization_id, identity_type_id
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/assignments/organizations", tags=["assignments"])
def create_organization_assignment_endpoint(
    payload: dict[str, int],
    identity_type_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Creates organization assignment."""
    try:
        return router.create_organization_assignment(
            payload["user_id"],
            payload["organization_id"],
            payload["role_id"],
            identity_type_id
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.patch("/assignments/organizations/{assignment_id}", tags=["assignments"])
def update_organization_assignment_endpoint(
    assignment_id: int,
    active: bool,
    identity_type_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Updates organization assignment active status."""
    try:
        return router.update_organization_assignment(
            assignment_id, active, identity_type_id
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.delete("/assignments/organizations/{assignment_id}", tags=["assignments"])
def delete_organization_assignment_endpoint(
    assignment_id: int,
    identity_type_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Deletes organization assignment permanently."""
    try:
        return router.delete_organization_assignment(
            assignment_id, identity_type_id
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/assignments/validate-org-prerequisite", tags=["assignments"])
def validate_org_prerequisite_endpoint(
    user_id: int,
    organization_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Validates if user has active org role (prerequisite)."""
    try:
        return router.validate_org_prerequisite(
            user_id, organization_id
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/assignments/projects/{project_id}", tags=["assignments"])
def get_project_assignments_endpoint(
    project_id: int,
    identity_type_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> list[dict[str, Any]]:
    """Gets project assignments."""
    try:
        return router.get_project_assignments(
            project_id, identity_type_id
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/assignments/projects", tags=["assignments"])
def create_project_assignment_endpoint(
    payload: dict[str, int],
    identity_type_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Creates project assignment (with prerequisite validation)."""
    try:
        return router.create_project_assignment(
            payload["user_id"],
            payload["organization_id"],
            payload["project_id"],
            payload["role_id"],
            identity_type_id
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.patch("/assignments/projects/{assignment_id}", tags=["assignments"])
def update_project_assignment_endpoint(
    assignment_id: int,
    active: bool,
    identity_type_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Updates project assignment active status."""
    try:
        return router.update_project_assignment(
            assignment_id, active, identity_type_id
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.delete("/assignments/projects/{assignment_id}", tags=["assignments"])
def delete_project_assignment_endpoint(
    assignment_id: int,
    identity_type_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Deletes project assignment permanently."""
    try:
        return router.delete_project_assignment(
            assignment_id, identity_type_id
        )
    except BrokerBusinessError as exc:
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
    identity_type_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> list[dict[str, Any]]:
    """Gets all prompts for a category."""
    try:
        return router.get_prompts(category, identity_type_id)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/prompts/{category}/{id_prompt}", tags=["prompts"])
def get_prompt_endpoint(
    category: str,
    id_prompt: int,
    identity_type_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Gets a specific prompt by ID."""
    try:
        return router.get_prompt(category, id_prompt, identity_type_id)
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/prompts/{category}", tags=["prompts"])
def create_prompt_endpoint(
    category: str,
    payload: dict,
    identity_type_id: int,
    user_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Creates a new prompt."""
    try:
        return router.create_prompt(
            category, payload, user_id, identity_type_id
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.put("/prompts/{category}/{id_prompt}", tags=["prompts"])
def update_prompt_endpoint(
    category: str,
    id_prompt: int,
    payload: dict,
    identity_type_id: int,
    user_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Updates an existing prompt."""
    try:
        return router.update_prompt(
            category, id_prompt, payload, user_id, identity_type_id
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.patch("/prompts/{category}/{id_prompt}/toggle", tags=["prompts"])
def toggle_prompt_endpoint(
    category: str,
    id_prompt: int,
    payload: dict,
    identity_type_id: int,
    user_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Toggles prompt active status."""
    try:
        return router.toggle_prompt(
            category, id_prompt, payload, user_id, identity_type_id
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


# ============================================================================
# PROJECT VERSION STATE - Estado de versiones de proyectos (DDD)
# ============================================================================


@app.get("/project-version-states/{state_id}", tags=["project-version-states"])
def get_project_version_state_by_id_endpoint(
    state_id: int,
    user_id: int,
    identity_type_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Gets project version state by ID."""
    try:
        return router.get_project_version_state_by_id(
            state_id, user_id, identity_type_id
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get(
    "/project-version-states/version/{organization_id}/{project_id}/{version_id}",
    tags=["project-version-states"],
)
def get_project_version_state_by_version_endpoint(
    organization_id: int,
    project_id: int,
    version_id: int,
    user_id: int,
    identity_type_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Gets project version state by version."""
    try:
        return router.get_project_version_state_by_version(
            organization_id, project_id, version_id, user_id, identity_type_id
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/project-version-states", tags=["project-version-states"])
def list_project_version_states_endpoint(
    user_id: int,
    identity_type_id: int,
    organization_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> list[dict[str, Any]]:
    """Lists project version states by user assignments."""
    try:
        return router.list_project_version_states(
            user_id, identity_type_id, organization_id, limit, offset
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.patch(
    "/project-version-states/{state_id}/proposal",
    tags=["project-version-states"],
)
def update_proposal_phase_endpoint(
    state_id: int,
    payload: dict,
    user_id: int,
    identity_type_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Updates proposal phase."""
    try:
        return router.update_proposal_phase(
            state_id,
            payload.get("aceptacion_cliente", False),
            payload.get("aceptacion_interna", False),
            user_id,
            identity_type_id,
            revision_interna=payload.get("revision_interna"),
            propuesta_mejoras=payload.get("propuesta_mejoras"),
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.patch(
    "/project-version-states/{state_id}/training",
    tags=["project-version-states"],
)
def update_training_phase_endpoint(
    state_id: int,
    payload: dict,
    user_id: int,
    identity_type_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Updates training phase."""
    try:
        return router.update_training_phase(
            state_id,
            payload.get("completado", False),
            user_id,
            identity_type_id,
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.patch(
    "/project-version-states/{state_id}/evaluation",
    tags=["project-version-states"],
)
def update_evaluation_phase_endpoint(
    state_id: int,
    payload: dict,
    user_id: int,
    identity_type_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Updates evaluation phase."""
    try:
        return router.update_evaluation_phase(
            state_id,
            payload.get("evaluacion", False),
            payload.get("reentrenamiento", False),
            payload.get("optimizacion", False),
            payload.get("calidad_aprobada", False),
            user_id,
            identity_type_id,
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.patch(
    "/project-version-states/{state_id}/generation",
    tags=["project-version-states"],
)
def update_generation_phase_endpoint(
    state_id: int,
    payload: dict,
    user_id: int,
    identity_type_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Updates generation phase."""
    try:
        return router.update_generation_phase(
            state_id,
            payload.get("generacion_completada", False),
            user_id,
            identity_type_id,
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.patch(
    "/project-version-states/{state_id}/notification",
    tags=["project-version-states"],
)
def update_notification_phase_endpoint(
    state_id: int,
    payload: dict,
    user_id: int,
    identity_type_id: int,
    router: BrokerBackendRouter = Depends(get_router_broker),
) -> dict[str, Any]:
    """Updates notification phase."""
    try:
        return router.update_notification_phase(
            state_id,
            payload.get("notificacion_enviada", False),
            user_id,
            identity_type_id,
        )
    except BrokerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
