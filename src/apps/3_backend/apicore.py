"""Capa de API para el backend core."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated, Any, AsyncIterator

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


class UserStatusUpdateRequest(BaseModel):
    """Request para actualizar estado activo de un usuario."""

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


class EnvironmentResponse(BaseModel):
    """Respuesta con el entorno activo del sistema.
    
    Este endpoint es consultado por fmanagement para determinar
    rutas base y configuraciones específicas del entorno.
    
    Valores posibles: macbook, dev, pre, pro
    """

    environment: str
    source: str = "ENVIRONMENT"


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


@app.patch("/users/{user_id}/status", response_model=UserStatusUpdateResponse)
def update_user_status(
    user_id: int,
    payload: UserStatusUpdateRequest,
    router: BackendCoreRouter = Depends(get_router_core),
) -> UserStatusUpdateResponse:
    """Actualiza el estado activo/inactivo de un usuario en MariaDB.
    
    Este es el destino final del flujo:
    Frontend → Middleware → Broker → Backend Core (aquí) → MariaDB
    """
    try:
        response = router.update_user_status(
            user_id=user_id,
            active=payload.active,
            requester_org_id=payload.requester_org_id,
        )
        return UserStatusUpdateResponse(**response)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/users/check-exists", response_model=UserExistsResponse)
def check_user_exists(
    payload: UserExistsRequest,
    router: BackendCoreRouter = Depends(get_router_core),
) -> UserExistsResponse:
    """Verifica si existe un usuario por nombre de usuario.
    
    Flujo: Frontend → Middleware → Broker → Backend Core (aquí) → JSON/MariaDB
    """
    try:
        exists = router.check_user_exists(payload.user_name)
        return UserExistsResponse(exists=exists, user_name=payload.user_name)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/users/by-email", response_model=UserByEmailResponse)
def get_user_by_email(
    payload: UserByEmailRequest,
    router: BackendCoreRouter = Depends(get_router_core),
) -> UserByEmailResponse:
    """Obtiene datos de un usuario por email.
    
    Flujo: Frontend → Middleware → Broker → Backend Core (aquí) → JSON/MariaDB
    """
    try:
        user_data = router.get_user_by_email(payload.email)
        if user_data is None:
            return UserByEmailResponse(found=False)
        return UserByEmailResponse(
            found=True,
            user_id=user_data.get("user_id"),
            user_name=user_data.get("user_name"),
            user_email=user_data.get("user_email"),
            user_mobile=user_data.get("user_mobile"),
            organization_id=user_data.get("organization_id"),
        )
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/users/update-password", response_model=UpdatePasswordResponse)
def update_user_password(
    payload: UpdatePasswordRequest,
    router: BackendCoreRouter = Depends(get_router_core),
) -> UpdatePasswordResponse:
    """Actualiza contraseña y OTP de un usuario.
    
    Flujo: Frontend → Middleware → Broker → Backend Core (aquí) → JSON/MariaDB
    """
    try:
        success = router.update_user_password(
            email=payload.email,
            new_password=payload.new_password,
            new_otp=payload.new_otp,
        )
        return UpdatePasswordResponse(
            success=success,
            message="Contraseña actualizada correctamente" if success else "Error al actualizar",
        )
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


# === Endpoints de Configuración del Sistema ===


# ============================================================================
# Modelos Pydantic para Proyectos
# ============================================================================


class ProjectCreateRequest(BaseModel):
    """Payload para crear un proyecto."""

    nombre: str = Field(..., min_length=1, max_length=200)
    descripcion: str | None = Field(default="", max_length=1000)
    id_organizacion: int
    active: bool = True
    id_flujo: int = 1  # Propuesta Cliente (primer paso)


class ProjectCreateResponse(BaseModel):
    """Respuesta de creación de proyecto."""

    project_id: int
    nombre: str
    id_organizacion: int
    id_flujo: int


class ProjectUpdateRequest(BaseModel):
    """Payload para actualizar un proyecto.
    
    Campos:
        nombre: Nombre del proyecto
        descripcion: Descripción del proyecto
        active: Estado activo/bloqueado (True=activo, False=bloqueado)
        id_flujo: ID del paso del flujo
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

    titulo: str  # "Motivo" en UI
    consulta: str  # Texto de la consulta
    id_organizacion: int  # Para registrar en cambios
    cliente_id: int  # ID del usuario que crea el ticket
    id_proyecto: int | None = None  # Proyecto relacionado (opcional)


class TicketUpdateRequest(BaseModel):
    """Payload para actualizar un ticket (solo Backoffice)."""

    estado: str | None = None  # abierto/en_espera/resuelto/cerrado
    prioridad: str | None = None  # baja/media/alta/urgente
    user_id: int | None = None  # Usuario que realiza el cambio


class TicketRespuestaRequest(BaseModel):
    """Payload para añadir respuesta a un ticket."""

    respuesta: str  # Texto de la respuesta
    user_id: int  # Usuario que escribe la respuesta
    user_id: int  # ID del usuario que responde


class TicketDto(BaseModel):
    """DTO de ticket para respuestas."""

    id: int
    titulo: str
    cliente_id: int
    estado: str
    prioridad: str
    fecha_creacion: str
    fecha_actualizacion: str | None = None
    # Datos de la primera interacción
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
    """DTO de proyecto para respuestas.
    
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
    router: BackendCoreRouter = Depends(get_router_core),
    include_deleted: bool = False,
) -> ProjectListResponse:
    """Obtiene los proyectos de una organización.

    Flujo: Broker → Backend Core → MariaDB (myllm_projects_db)
    
    Args:
        include_deleted: Si True, incluye proyectos con existe=false
    """
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        projects = router.get_organization_projects(
            organization_id, headers, include_deleted=include_deleted
        )
        return ProjectListResponse(
            projects=[ProjectDto(**p) for p in projects],
            total=len(projects),
        )
    except BackendCoreBusinessError as exc:
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
    router: BackendCoreRouter = Depends(get_router_core),
) -> ProjectCreateResponse:
    """Crea un nuevo proyecto.

    Flujo: Broker → Backend Core → MariaDB (INSERT proyectos)
    
    El trigger tr_proyecto_after_insert crea automáticamente:
    - Registro en tabla estado (versión 1)
    - Registro en tabla cambios (tipo "Alta proyecto")
    """
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.create_project(request.model_dump(), headers)
        return ProjectCreateResponse(**result)
    except BackendCoreBusinessError as exc:
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
    router: BackendCoreRouter = Depends(get_router_core),
) -> ProjectUpdateResponse:
    """Actualiza un proyecto existente.

    Flujo: Broker → Backend Core → MariaDB (UPDATE proyectos)
    
    El trigger tr_proyecto_flujo_update registra automáticamente cambios en:
    - Tabla estado (si cambia id_flujo)
    - Tabla cambios (tipo según el campo modificado)
    """
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        # Filtrar campos None del request
        update_data = {k: v for k, v in request.model_dump().items() if v is not None}
        result = router.update_project(project_id, update_data, headers)
        return ProjectUpdateResponse(
            success=True,
            updated=result.get("updated", True),
            project_id=project_id,
        )
    except BackendCoreBusinessError as exc:
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
    router: BackendCoreRouter = Depends(get_router_core),
) -> ProjectDeleteResponse:
    """Elimina un proyecto.

    Flujo: Broker → Backend Core → MariaDB (DELETE proyectos)
    
    El trigger tr_proyecto_before_delete registra automáticamente:
    - Registro en tabla cambios (tipo "Borrado de proyecto")
    """
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.delete_project(project_id, headers)
        return ProjectDeleteResponse(
            success=True,
            deleted=result.get("deleted", True),
            project_id=project_id,
        )
    except BackendCoreBusinessError as exc:
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
    router: BackendCoreRouter = Depends(get_router_core),
) -> ProjectSupportResponse:
    """Registra una solicitud de soporte para un proyecto.

    Flujo: Broker → Backend Core → MariaDB (CALL sp_registrar_cambio_proyecto)
    
    Registra en tabla cambios:
    - tipo_cambio: "Solicitud soporte proyecto"
    - descripcion: descripción de la solicitud
    """
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.request_project_support(
            project_id,
            request.tipo_cambio,
            request.descripcion or "",
            headers,
        )
        return ProjectSupportResponse(
            success=True,
            cambio_id=result.get("cambio_id"),
        )
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# === Endpoints de Configuración del Sistema ===


@app.get("/config/environment", response_model=EnvironmentResponse)
def get_active_environment() -> EnvironmentResponse:
    """Obtiene el entorno activo del sistema.
    
    Lee la variable ENVIRONMENT del archivo .env del proyecto.
    Este endpoint es usado por fmanagement para determinar rutas base
    y configuraciones específicas del entorno en tiempo de inicialización.
    
    Flujo típico:
        fmanagement (Go) → Backend Core (este endpoint) → Lee .env
    
    Valores de entorno:
        - macbook: Desarrollo local en macOS
        - dev: Servidor de desarrollo
        - pre: Servidor de preproducción  
        - pro: Servidor de producción
    
    Returns:
        EnvironmentResponse con el entorno activo
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
    id_rol: int  # 3=Editor, 4=Lector, 5=Auditor
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
    
    Esta información es reutilizable por todas las aplicaciones
    para selectores de roles y validaciones de seguridad.
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
    id_rol: int  # 3=Editor, 4=Lector, 5=Auditor


class AssignUserToProjectResponse(BaseModel):
    """Respuesta de asignación de usuario a proyecto."""

    success: bool
    message: str
    id_usuario: int
    id_proyecto: int
    id_rol: int
    created: bool  # True si se creó, False si se actualizó


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
    router: BackendCoreRouter = Depends(get_router_core),
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> ProjectRolesBaseResponse:
    """Obtiene el catálogo maestro de roles base para proyectos.

    Esta información es reutilizable por todas las aplicaciones
    para poblar selectores de roles y validaciones de seguridad.

    Roles disponibles:
        - 0: Sin asignar (usuario no puede ver el proyecto)
        - 3: Editor (puede modificar contenido)
        - 4: Lector (solo lectura)
        - 5: Auditor (acceso limitado para auditoría)

    Returns:
        Lista de roles base disponibles
    """
    logger = logging.getLogger(__name__)
    logger.info("[%s] Consultando catálogo de roles base", client_app or "unknown")

    try:
        roles = router.get_project_roles_base()
        return ProjectRolesBaseResponse(
            roles=[ProjectRoleBaseDto(**r) for r in roles],
            total=len(roles),
        )
    except BackendCoreBusinessError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.exception("Error consultando roles base: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {e}",
        ) from e


@app.get(
    "/users/{user_id}/project-roles",
    response_model=UserProjectRolesResponse,
    tags=["project-roles"],
)
def get_user_project_roles(
    user_id: int,
    organization_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> UserProjectRolesResponse:
    """Obtiene los roles de un usuario en proyectos de una organización.

    Consulta la tabla proyectos_roles para obtener las asignaciones activas
    del usuario en los proyectos de su organización.

    Args:
        user_id: ID del usuario
        organization_id: ID de la organización

    Returns:
        Lista de roles del usuario en proyectos
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[%s] Consultando roles de usuario %s en org %s",
        client_app or "unknown",
        user_id,
        organization_id,
    )

    try:
        roles = router.get_user_project_roles(user_id, organization_id)
        return UserProjectRolesResponse(
            user_id=user_id,
            organization_id=organization_id,
            roles=[ProjectRoleDto(**r) for r in roles],
            total=len(roles),
        )
    except BackendCoreBusinessError as exc:
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
    router: BackendCoreRouter = Depends(get_router_core),
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> AssignUserToProjectResponse:
    """Asigna un usuario a un proyecto con un rol específico.

    Si el usuario ya tiene asignación en el proyecto:
        - Actualiza el rol y pone active=1
    Si no existe asignación:
        - Crea un nuevo registro

    Registra el cambio en la tabla cambios con tipo "Asignación usuario".

    Args:
        request: Datos de asignación (usuario, proyecto, organización, rol)

    Returns:
        Resultado de la operación
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[%s] Asignando usuario %s a proyecto %s con rol %s",
        client_app or "unknown",
        request.id_usuario,
        request.id_proyecto,
        request.id_rol,
    )

    try:
        result = router.assign_user_to_project(
            id_usuario=request.id_usuario,
            id_proyecto=request.id_proyecto,
            id_organizacion=request.id_organizacion,
            id_rol=request.id_rol,
        )
        return AssignUserToProjectResponse(**result)
    except BackendCoreBusinessError as exc:
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
    router: BackendCoreRouter = Depends(get_router_core),
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> RemoveUserFromProjectResponse:
    """Quita un usuario de un proyecto (desactiva la asignación).

    Busca el registro en proyectos_roles y pone active=0.
    Registra el cambio en la tabla cambios con tipo "Quitar usuario".

    Args:
        request: Datos de la operación (usuario, proyecto, organización)

    Returns:
        Resultado de la operación
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[%s] Quitando usuario %s de proyecto %s",
        client_app or "unknown",
        request.id_usuario,
        request.id_proyecto,
    )

    try:
        result = router.remove_user_from_project(
            id_usuario=request.id_usuario,
            id_proyecto=request.id_proyecto,
            id_organizacion=request.id_organizacion,
        )
        return RemoveUserFromProjectResponse(**result)
    except BackendCoreBusinessError as exc:
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
    router: BackendCoreRouter = Depends(get_router_core),
) -> TicketCreateResponse:
    """Crea un nuevo ticket de soporte.

    Flujo: Frontend → Middleware → Broker → Backend Core → MariaDB
    
    Crea registro en:
    - tickets (cabecera)
    - ticket_interacciones (consulta inicial)
    - cambios (registro de actividad)
    """
    logger = logging.getLogger(__name__)
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.create_ticket(request.model_dump(), headers)
        return TicketCreateResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error creando ticket")
        raise HTTPException(status_code=500, detail=f"Error interno: {exc}") from exc


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
    router: BackendCoreRouter = Depends(get_router_core),
) -> TicketListResponse:
    """Obtiene los tickets de una organización.

    Flujo: Frontend/Backoffice → Middleware → Broker → Backend Core → MariaDB
    """
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        tickets = router.get_organization_tickets(organization_id, headers)
        return TicketListResponse(
            tickets=[TicketDto(**t) for t in tickets],
            total=len(tickets),
        )
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/tickets/{ticket_id}", response_model=TicketDto, tags=["tickets"])
def get_ticket_detail(
    ticket_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> TicketDto:
    """Obtiene el detalle de un ticket específico."""
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        ticket = router.get_ticket_detail(ticket_id, headers)
        return TicketDto(**ticket)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/tickets/{ticket_id}", response_model=TicketUpdateResponse, tags=["tickets"])
def update_ticket(
    ticket_id: int,
    request: TicketUpdateRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> TicketUpdateResponse:
    """Actualiza estado/prioridad de un ticket (solo Backoffice).

    Solo actualiza los campos enviados (estado y/o prioridad).
    Registra el cambio en la tabla cambios.
    """
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        update_data = {k: v for k, v in request.model_dump().items() if v is not None}
        result = router.update_ticket(ticket_id, update_data, headers)
        return TicketUpdateResponse(**result)
    except BackendCoreBusinessError as exc:
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
    router: BackendCoreRouter = Depends(get_router_core),
) -> TicketUpdateResponse:
    """Añade respuesta a un ticket (solo Backoffice).

    Actualiza la primera interacción del ticket con la respuesta.
    Registra el cambio en la tabla cambios.
    """
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.add_ticket_response(ticket_id, request.model_dump(), headers)
        return TicketUpdateResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
