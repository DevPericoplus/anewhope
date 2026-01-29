"""Capa de API para el backend core."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

import importlib.util
import sys
from pathlib import Path


def _load_backend_module(module_name: str, module_path: Path) -> Any:
    """Carga un módulo dinámicamente desde una ruta."""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar {module_name} desde {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Cargar routercore
_router_path = Path(__file__).resolve().parent / "routercore.py"
_routercore = _load_backend_module("routercore_backend", _router_path)

BackendCoreBusinessError = _routercore.BackendCoreBusinessError
BackendCoreRouter = _routercore.BackendCoreRouter
BasicPermissionDto = _routercore.BasicPermissionDto
JsonMockStorageAdapter = _routercore.JsonMockStorageAdapter
ManageRoleByOrgDto = _routercore.ManageRoleByOrgDto
OrganizationDto = _routercore.OrganizationDto
RoleDto = _routercore.RoleDto
UserDto = _routercore.UserDto

# Cargar fmanagement_client
_infra_path = Path(__file__).resolve().parent / "4_infrastructure"
_fmanagement_path = _infra_path / "web" / "fmanagement_client.py"
_fmanagement_module = _load_backend_module("fmanagement_client_backend", _fmanagement_path)
FmanagementClient = _fmanagement_module.FmanagementClient

# Cargar storage_adapter
_storage_adapter_path = _infra_path / "persistence" / "storage_adapter.py"
_storage_adapter = _load_backend_module("storage_adapter_backend", _storage_adapter_path)
load_fmanagement_settings = _storage_adapter.load_fmanagement_settings


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


class FileOperationRequest(BaseModel):
    """Parámetros para operaciones de ficheros/carpetas."""

    id_user: int
    id_organization: int
    id_project: int
    version_path: str
    operation: str
    subfolders: str = ""
    filename: str = ""
    ext_file: str = ""
    new_filename: str = ""
    new_extfile: str = ""
    compare_version_path: str = ""
    identity_type_id: int | None = None


class VersionOperationRequest(BaseModel):
    """Parámetros para operaciones de versiones."""

    id_user: int
    id_organization: int
    id_project: int
    version_path: str
    identity_type_id: int | None = None


class VersionTransferRequest(BaseModel):
    """Parámetros para transferencia de versiones entre servidores."""

    id_user: int
    id_organization: int
    id_project: int
    version_path: str
    target_type: str = Field(..., description="Destino: 'trainer' o 'core'")
    identity_type_id: int | None = None


class VersionTransferResponse(BaseModel):
    """Respuesta de transferencia de versiones."""

    status: str
    message: str
    source_path: str
    destination_path: str
    bytes_transferred: int = 0
    files_transferred: int = 0


class FileOperationResponse(BaseModel):
    """Respuesta genérica para operaciones de ficheros."""

    result: dict[str, Any] = Field(default_factory=dict)


def _build_permission_headers(
    authorization: str | None,
    session_token: str | None,
    client_app: str | None = None,
) -> dict[str, str]:
    """Construye headers para validar permisos en fmanagement."""

    headers: dict[str, str] = {}
    if authorization:
        headers["Authorization"] = authorization
    if session_token:
        headers["X-Session-Token"] = session_token
    if client_app:
        headers["X-Client-App"] = client_app
    return headers


def get_client_app(
    client_app: str | None = Header(default=None, alias="X-Client-App"),
) -> str:
    """Extrae el header X-Client-App de la petición."""

    return client_app or "unknown"


def _configure_logging() -> None:
    """Configura logging del backend core con salida a console.log."""

    logs_dir = Path(__file__).resolve().parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Archivo de actividad específico
    activity_log_path = os.environ.get(
        "CORE_ACTIVITY_LOG_PATH",
        str(logs_dir / "backend_core_activity.log"),
    )

    # Archivo console.log unificado para soporte
    console_log_path = logs_dir / "console.log"

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    # Formato legible para técnicos de soporte
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | backend_core    | %(message)s",
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
        "low_level_permissions": os.environ.get(
            "LOW_LEVEL_PERMISSIONS_PATH",
            f"{root}/src/2_shared_application/moks/low_level_permisions.json",
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
        low_level_permissions_path=Path(paths["low_level_permissions"]),
        manage_roles_path=Path(paths["manage_roles"]),
    )


def get_fmanagement_client() -> FmanagementClient:
    """Inyecta el cliente de fmanagement."""

    settings = load_fmanagement_settings()
    return FmanagementClient(base_url=settings.base_url)


def get_router_core(
    storage: JsonMockStorageAdapter = Depends(get_storage_adapter),
    fmanagement_client: FmanagementClient = Depends(get_fmanagement_client),
) -> BackendCoreRouter:
    """Inyecta el orquestador de backend core."""

    return BackendCoreRouter(
        storage=storage,
        fmanagement_client=fmanagement_client,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Gestiona el ciclo de vida de la aplicación."""

    _configure_logging()
    yield


app = FastAPI(title="Backend Core", lifespan=lifespan)


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


@app.get("/low-level-permissions")
def list_low_level_permissions(
    permission_id: int | None = None,
    router: BackendCoreRouter = Depends(get_router_core),
) -> list[dict[str, Any]] | dict[str, Any]:
    """Lista permisos de bajo nivel o retorna uno específico."""

    try:
        permissions = router.list_low_level_permissions()
        if permission_id is None:
            return [perm.model_dump() for perm in permissions]
        match = next(
            (perm for perm in permissions if perm.id_permissions == permission_id),
            None,
        )
        if match is None:
            raise BackendCoreBusinessError(
                "No se encontró el permiso de bajo nivel solicitado"
            )
        return match.model_dump()
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
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


@app.put("/roles")
def store_roles(
    payload: list[dict[str, Any]],
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Guarda roles en MariaDB."""

    try:
        roles = [RoleDto.model_validate(record) for record in payload]
        router.store_roles(roles)
        return {"success": True, "count": len(roles)}
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@app.put("/basic-permissions")
def store_basic_permissions(
    payload: list[dict[str, Any]],
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Guarda permisos básicos en MariaDB."""

    try:
        permissions = [BasicPermissionDto.model_validate(record) for record in payload]
        router.store_basic_permissions(permissions)
        return {"success": True, "count": len(permissions)}
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@app.put("/low-level-permissions")
def store_low_level_permissions(
    payload: list[dict[str, Any]],
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Guarda permisos de bajo nivel en MariaDB."""

    try:
        permissions = [LowLevelPermissionDto.model_validate(record) for record in payload]
        router.store_low_level_permissions(permissions)
        return {"success": True, "count": len(permissions)}
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
        response = router.get_permissions(identity_type_id)
        response["identity_type_id"] = identity_type_id
        return PermissionsResponse(**response)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@app.get("/fmo", response_model=FileOperationResponse)
def fmo_operation(
    id_user: int,
    id_organization: int,
    id_project: int,
    version_path: str,
    operation: str,
    subfolders: str = "",
    filename: str = "",
    ext_file: str = "",
    new_filename: str = "",
    new_extfile: str = "",
    compare_version_path: str = "",
    identity_type_id: int | None = None,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> FileOperationResponse:
    """Delegación de operaciones de ficheros/carpetas a fmanagement."""

    payload = FileOperationRequest(
        id_user=id_user,
        id_organization=id_organization,
        id_project=id_project,
        version_path=version_path,
        operation=operation,
        subfolders=subfolders,
        filename=filename,
        ext_file=ext_file,
        new_filename=new_filename,
        new_extfile=new_extfile,
        compare_version_path=compare_version_path,
        identity_type_id=identity_type_id,
    ).model_dump()
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.fmo_operation(payload, headers)
        return FileOperationResponse(result=result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/fmo", response_model=FileOperationResponse)
async def fmo_upload(
    file: UploadFile = File(...),
    id_user: int = Form(...),
    id_organization: int = Form(...),
    id_project: int = Form(...),
    version_path: str = Form(...),
    operation: str = Form("upload"),
    subfolders: str = Form(""),
    filename: str = Form(""),
    ext_file: str = Form(""),
    identity_type_id: int | None = Form(None),
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> FileOperationResponse:
    """Delegación de carga de fichero a fmanagement."""

    payload = FileOperationRequest(
        id_user=id_user,
        id_organization=id_organization,
        id_project=id_project,
        version_path=version_path,
        operation=operation,
        subfolders=subfolders,
        filename=filename,
        ext_file=ext_file,
        identity_type_id=identity_type_id,
    ).model_dump()
    headers = _build_permission_headers(authorization, session_token, client_app)
    file_payload = {
        "filename": file.filename,
        "content": await file.read(),
        "content_type": file.content_type,
    }
    try:
        result = router.fmo_upload(payload, headers, file_payload)
        return FileOperationResponse(result=result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/fmo/list", response_model=FileOperationResponse)
def fmo_list(
    id_user: int,
    id_organization: int,
    id_project: int,
    version_path: str,
    subfolders: str = "",
    identity_type_id: int | None = None,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> FileOperationResponse:
    """Lista estructura de carpetas vía fmanagement."""

    payload = FileOperationRequest(
        id_user=id_user,
        id_organization=id_organization,
        id_project=id_project,
        version_path=version_path,
        operation="list",
        subfolders=subfolders,
        identity_type_id=identity_type_id,
    ).model_dump()
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.list_directory(payload, headers)
        return FileOperationResponse(result=result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/fmo/newversion", response_model=FileOperationResponse)
def fmo_newversion(
    payload: VersionOperationRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> FileOperationResponse:
    """Crea una nueva versión delegando en fmanagement."""

    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.create_new_version(payload.model_dump(), headers)
        return FileOperationResponse(result=result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/fmo/diffversion", response_model=FileOperationResponse)
def fmo_diffversion(
    id_user: int,
    id_organization: int,
    id_project: int,
    version_path: str,
    compare_version_path: str,
    identity_type_id: int | None = None,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> FileOperationResponse:
    """Compara versiones delegando en fmanagement."""

    payload = FileOperationRequest(
        id_user=id_user,
        id_organization=id_organization,
        id_project=id_project,
        version_path=version_path,
        compare_version_path=compare_version_path,
        operation="diffversion",
        identity_type_id=identity_type_id,
    ).model_dump()
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.diff_versions(payload, headers)
        return FileOperationResponse(result=result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post("/fmo/transferversion", response_model=VersionTransferResponse)
def fmo_transferversion(
    payload: VersionTransferRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> VersionTransferResponse:
    """Transfiere una versión entre servidores backend y trainer.

    Delega la operación en fmanagement que ejecutará la transferencia
    usando rsync over SSH (remoto) o copia local (desarrollo).
    """

    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.transfer_version(payload.model_dump(), headers)
        return VersionTransferResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
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
