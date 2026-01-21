"""Capa de API para el backend core."""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field

try:
    from .routercore import (
        BackendCoreBusinessError,
        BackendCoreRouter,
        BasicPermissionDto,
        JsonMockStorageAdapter,
        ManageRoleByOrgDto,
        OrganizationDto,
        RoleDto,
        UserDto,
    )
except ImportError:  # pragma: no cover - soporte para ejecuciones fuera de paquete
    import importlib.util
    from pathlib import Path

    _router_path = Path(__file__).resolve().parent / "routercore.py"
    _spec = importlib.util.spec_from_file_location("routercore", _router_path)
    if _spec is None or _spec.loader is None:
        raise
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)

    BackendCoreBusinessError = _module.BackendCoreBusinessError
    BackendCoreRouter = _module.BackendCoreRouter
    BasicPermissionDto = _module.BasicPermissionDto
    JsonMockStorageAdapter = _module.JsonMockStorageAdapter
    ManageRoleByOrgDto = _module.ManageRoleByOrgDto
    OrganizationDto = _module.OrganizationDto
    RoleDto = _module.RoleDto
    UserDto = _module.UserDto


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


class ProcessDataRequest(BaseModel):
    """Payload de entrada para el procesamiento."""

    payload: dict[str, Any] = Field(default_factory=dict)


class ProcessDataResponse(BaseModel):
    """Respuesta del backend procesada."""

    result: dict[str, Any]
    message: str


def _configure_logging() -> None:
    """Configura logging del backend core."""

    log_path = os.environ.get(
        "CORE_ACTIVITY_LOG_PATH",
        "src/apps/3_backend/logs/backend_core_activity.log",
    )
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.FileHandler(log_path), logging.StreamHandler()],
    )


def _get_mock_paths() -> dict[str, str]:
    """Obtiene rutas de mocks desde entorno."""

    root = os.environ.get("PROJECT_ROOT", os.getcwd())
    return {
        "users": os.environ.get(
            "USERS_DATA_PATH",
            f"{root}/src/2_shared_application/moks/users.json",
        ),
        "organizations": os.environ.get(
            "ORGANIZATIONS_DATA_PATH",
            f"{root}/src/2_shared_application/moks/organizations.json",
        ),
        "roles": os.environ.get(
            "ROLES_DATA_PATH",
            f"{root}/src/2_shared_application/moks/roles.json",
        ),
        "basic_permissions": os.environ.get(
            "BASIC_PERMISSIONS_PATH",
            f"{root}/src/2_shared_application/moks/basic_permissions.json",
        ),
        "manage_roles": os.environ.get(
            "MANAGE_ROLES_BY_ORG_PATH",
            f"{root}/src/2_shared_application/moks/manage_roles_by_org.json",
        ),
    }


def get_storage_adapter() -> JsonMockStorageAdapter:
    """Inyecta adaptador de almacenamiento."""

    from pathlib import Path

    paths = _get_mock_paths()
    return JsonMockStorageAdapter(
        users_path=Path(paths["users"]),
        organizations_path=Path(paths["organizations"]),
        roles_path=Path(paths["roles"]),
        basic_permissions_path=Path(paths["basic_permissions"]),
        manage_roles_path=Path(paths["manage_roles"]),
    )


def get_router_core(
    storage: JsonMockStorageAdapter = Depends(get_storage_adapter),
) -> BackendCoreRouter:
    """Inyecta el orquestador de backend core."""

    return BackendCoreRouter(storage=storage)


app = FastAPI(title="Backend Core", lifespan=None)


@app.on_event("startup")
def _startup() -> None:
    _configure_logging()


@app.get("/users")
def list_users(
    router: BackendCoreRouter = Depends(get_router_core),
) -> list[dict[str, Any]]:
    """Lista usuarios."""

    try:
        users = router.list_users()
        return [user.model_dump() for user in users]
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@app.put("/users")
def store_users(
    payload: list[dict[str, Any]],
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Guarda usuarios."""

    try:
        users = [UserDto.model_validate(record) for record in payload]
        router.store_users(users)
        return {"success": True}
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@app.post("/users", response_model=UserCreateResponse)
def create_user(
    payload: UserCreateRequest,
    router: BackendCoreRouter = Depends(get_router_core),
) -> UserCreateResponse:
    """Crea usuario."""

    try:
        response = router.create_user(payload.model_dump())
        return UserCreateResponse(**response)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get("/organizations")
def list_organizations(
    router: BackendCoreRouter = Depends(get_router_core),
) -> list[dict[str, Any]]:
    """Lista organizaciones."""

    try:
        organizations = router.list_organizations()
        return [org.model_dump() for org in organizations]
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@app.put("/organizations")
def store_organizations(
    payload: list[dict[str, Any]],
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Guarda organizaciones."""

    try:
        organizations = [OrganizationDto.model_validate(record) for record in payload]
        router.store_organizations(organizations)
        return {"success": True}
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@app.post("/organizations/check-name", response_model=OrganizationCheckResponse)
def check_organization_name(
    payload: OrganizationCheckRequest,
    router: BackendCoreRouter = Depends(get_router_core),
) -> OrganizationCheckResponse:
    """Valida si la organización existe."""

    try:
        exists = router.check_organization_name(payload.organization_name)
        return OrganizationCheckResponse(exists=exists)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@app.post("/organizations", response_model=OrganizationCreateResponse)
def create_organization(
    payload: OrganizationCreateRequest,
    router: BackendCoreRouter = Depends(get_router_core),
) -> OrganizationCreateResponse:
    """Crea organización."""

    try:
        organization_id = router.create_organization(payload.model_dump())
        return OrganizationCreateResponse(organization_id=organization_id)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get("/roles")
def list_roles(
    router: BackendCoreRouter = Depends(get_router_core),
) -> list[dict[str, Any]]:
    """Lista roles."""

    try:
        roles = router.list_roles()
        return [role.model_dump() for role in roles]
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@app.get("/basic-permissions")
def list_basic_permissions(
    router: BackendCoreRouter = Depends(get_router_core),
) -> list[dict[str, Any]]:
    """Lista permisos básicos."""

    try:
        permissions = router.list_basic_permissions()
        return [perm.model_dump(by_alias=True) for perm in permissions]
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@app.get("/manage-roles-by-org")
def list_manage_roles(
    router: BackendCoreRouter = Depends(get_router_core),
) -> list[dict[str, Any]]:
    """Lista roles por organización."""

    try:
        roles = router.list_manage_roles()
        return [entry.model_dump() for entry in roles]
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@app.put("/manage-roles-by-org")
def store_manage_roles(
    payload: list[dict[str, Any]],
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Guarda roles por organización."""

    try:
        entries = [ManageRoleByOrgDto.model_validate(record) for record in payload]
        router.store_manage_roles(entries)
        return {"success": True}
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@app.get("/permissions", response_model=PermissionsResponse)
def get_permissions(
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> PermissionsResponse:
    """Obtiene permisos asociados a un rol."""

    try:
        permissions = router.get_permissions(identity_type_id)
        return PermissionsResponse(
            identity_type_id=identity_type_id,
            permissions=permissions,
        )
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@app.post("/process-data", response_model=ProcessDataResponse)
def process_data(
    request: ProcessDataRequest,
    router: BackendCoreRouter = Depends(get_router_core),
) -> ProcessDataResponse:
    """Procesa los datos enviados."""

    try:
        response = router.process_data(request.payload)
        return ProcessDataResponse(
            result=response,
            message="Procesamiento realizado en backend core",
        )
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
