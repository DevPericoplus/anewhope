"""Capa de API para el broker backend."""

from __future__ import annotations

import logging
import importlib.util
import os
import sys
from pathlib import Path
from collections.abc import Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field

try:
    from .interfacetocore import CoreBackendClient
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
    _router_module = _load_module("routerbroker", "routerbroker.py")

    CoreBackendClient = _interface_module.CoreBackendClient
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


def _configure_logging() -> None:
    """Configura logging del broker backend."""

    log_path = os.environ.get(
        "BROKER_ACTIVITY_LOG_PATH",
        "src/apps/8_service_backend/logs/broker_backend_activity.log",
    )
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.FileHandler(log_path), logging.StreamHandler()],
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


def get_router_broker(
    core_client: CoreBackendClient = Depends(get_core_client),
) -> BrokerBackendRouter:
    """Inyecta el orquestador del broker."""

    return BrokerBackendRouter(core_client=core_client)


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
    """Guarda usuarios."""

    try:
        router.store_users(payload)
        return {"success": True}
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
