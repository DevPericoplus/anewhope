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

from fastapi import Depends, FastAPI, Header, HTTPException, status
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
    """Obtiene la URL base del backend core."""

    env_settings = _load_env_settings_module("broker_env_settings")
    protected_base_url = env_settings.get_protected_value(
        "core_backend_base_url", "http://localhost:8003"
    )
    return os.environ.get("CORE_BACKEND_BASE_URL", protected_base_url)


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
    """Obtiene la URL base del backend IA (trainer)."""

    env_settings = _load_env_settings_module("broker_env_settings_trainer")
    protected_base_url = env_settings.get_protected_value(
        "trainer_backend_base_url", "http://localhost:8004"
    )
    return os.environ.get("TRAINER_BACKEND_BASE_URL", protected_base_url)


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
