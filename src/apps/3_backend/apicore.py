"""Capa de API para el backend core."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated, Any, AsyncIterator

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile, status, Response
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
BackendCorePermissionError = _routercore.BackendCorePermissionError
BackendCoreRouter = _routercore.BackendCoreRouter
BasicPermissionDto = _routercore.BasicPermissionDto
JsonMockStorageAdapter = _routercore.JsonMockStorageAdapter
ManageRoleByOrgDto = _routercore.ManageRoleByOrgDto
OrganizationDto = _routercore.OrganizationDto
RoleDto = _routercore.RoleDto
UserDto = _routercore.UserDto

# Cargar assignments DTOs
_assignments_dtos_path = Path(__file__).resolve().parents[2] / "2_shared_application" / "dtos" / "assignments_dtos.py"
_assignments_dtos = _load_backend_module("assignments_dtos_backend", _assignments_dtos_path)

InternalUserDto = _assignments_dtos.InternalUserDto
OrganizationAssignmentDto = _assignments_dtos.OrganizationAssignmentDto
ProjectAssignmentDto = _assignments_dtos.ProjectAssignmentDto
CreateOrgAssignmentDto = _assignments_dtos.CreateOrgAssignmentDto
CreateProjectAssignmentDto = _assignments_dtos.CreateProjectAssignmentDto
UpdateAssignmentDto = _assignments_dtos.UpdateAssignmentDto
PrerequisiteValidationDto = _assignments_dtos.PrerequisiteValidationDto

# Cargar prompts DTOs
_prompts_dtos_path = Path(__file__).resolve().parents[2] / "2_shared_application" / "dtos" / "prompts_dtos.py"
_prompts_dtos = _load_backend_module("prompts_dtos_backend", _prompts_dtos_path)

PromptDto = _prompts_dtos.PromptDto
CreatePromptDto = _prompts_dtos.CreatePromptDto
UpdatePromptDto = _prompts_dtos.UpdatePromptDto
TogglePromptDto = _prompts_dtos.TogglePromptDto
PromptListItemDto = _prompts_dtos.PromptListItemDto

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
    requester_identity_type_id: int = 0


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


# ============================================================================
# PROJECT VERSION STATE DTOs - Estado de versiones de proyectos (DDD)
# ============================================================================


class UpdateProposalPhaseDto(BaseModel):
    """DTO para actualizar fase de propuesta."""

    aceptacion_cliente: bool
    aceptacion_interna: bool
    revision_interna: bool | None = None
    propuesta_mejoras: bool | None = None


class UpdateTrainingPhaseDto(BaseModel):
    """DTO para actualizar fase de entrenamiento."""

    completado: bool


class UpdateEvaluationPhaseDto(BaseModel):
    """DTO para actualizar fase de evaluación."""

    evaluacion: bool | None = None  # Alias de evaluacion_entrenamiento (deprecated)
    reentrenamiento: bool
    optimizacion: bool
    calidad_aprobada: bool
    evaluacion_entrenamiento: bool | None = None


class UpdateGenerationPhaseDto(BaseModel):
    """DTO para actualizar fase de generación."""

    generacion_completada: bool | None = None
    generacion_solicitada: bool | None = None


class UpdateNotificationPhaseDto(BaseModel):
    """DTO para actualizar fase de notificación."""

    notificacion_enviada: bool


class JobCompleteRequest(BaseModel):
    """Payload para completar un job desde el Trainer."""

    job_id: int
    id_organizacion: int
    id_proyecto: int
    id_version: int
    descripcion: str = ""
    referencia_salida: str = ""
    tipo_cambio: str = "evaluacion_documental"
    id_estado: int = 4  # 4=Finalizado, 3=Error


class JobCompleteResponse(BaseModel):
    """Respuesta de completado de job."""

    success: bool
    id_cambio: int | None = None
    message: str = ""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Gestiona el ciclo de vida de la aplicación."""

    _configure_logging()
    yield


app = FastAPI(title="Backend Core", lifespan=lifespan)

# Setup logger
logger = logging.getLogger(__name__)

# Importar y registrar router de análisis de entrenamientos
try:
    _backend_dir = str(Path(__file__).resolve().parent)
    if _backend_dir not in sys.path:
        sys.path.insert(0, _backend_dir)
    _analysis_router_path = Path(__file__).resolve().parent / "router_training_analysis.py"
    _analysis_module = _load_backend_module("router_training_analysis", _analysis_router_path)
    app.include_router(_analysis_module.router)
    logger.info("✅ Router de análisis de entrenamientos registrado")
except Exception as e:
    logger.warning(f"⚠️ No se pudo registrar router de análisis: {e}")


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
            requester_identity_type_id=payload.requester_identity_type_id,
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


@app.get("/accessible-organizations")
def get_accessible_organizations(
    user_id: int,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> list[dict[str, Any]]:
    """Returns organizations accessible to a user based on identity type."""

    try:
        return router.get_user_accessible_organizations(user_id, identity_type_id)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
    identity_type_id: int | None = None,
    user_id: int | None = None,
    router: BackendCoreRouter = Depends(get_router_core),
) -> PermissionsResponse:
    """Obtiene permisos asociados a un rol o a un usuario."""

    try:
        if user_id is not None and identity_type_id is None:
            identity_type_id = router.get_user_role(user_id)
            if identity_type_id is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Usuario {user_id} no encontrado",
                )

        if identity_type_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se requiere identity_type_id o user_id",
            )

        response = router.get_permissions(identity_type_id)
        response["identity_type_id"] = identity_type_id
        response["user_id"] = user_id
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


# DTOs para Estados de Versión
# ========================================================================


class VersionStateDto(BaseModel):
    """Estado completo de una versión."""

    id: int
    id_organizacion: int
    id_proyecto: int
    id_version: int
    state: str  # "Abierta", "Bloqueada", "Protegida", "Final"
    state_internal: str | None = None
    protected: bool
    size: int  # Tamaño en bytes (sin _bytes en el nombre)
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

    # Alias para mantener compatibilidad con código que usa clone_from_version
    @property
    def clone_from_version(self) -> int | None:
        return self.clone_from_version_id


class CreateVersionFullResponse(BaseModel):
    """Respuesta de creación completa de versión."""

    success: bool
    message: str
    version_id: int | None
    version_folder: str | None
    version: dict | None = None
    state: dict | None = None
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


# ============================================================================
# MODELOS PARA CONVERSACIONES Y CAMBIOS
# ============================================================================


class ConversationSearchResponse(BaseModel):
    """Respuesta de búsqueda de conversación."""

    found: bool
    id_conversacion: int = 0


class ConversationCreateRequest(BaseModel):
    """Payload para crear una conversación."""

    id_organizacion: int
    id_usuario_cliente: int
    asunto: str = "Consulta sobre proyecto"
    prioridad: str = "media"


class ConversationCreateResponse(BaseModel):
    """Respuesta de creación de conversación."""

    success: bool
    id_conversacion: int


class ConversationMessageRequest(BaseModel):
    """Payload para enviar un mensaje."""

    id_usuario_emisor: int
    tipo_emisor: str
    texto_mensaje: str
    id_ticket_referenciado: int | None = None


class ConversationMessageResponse(BaseModel):
    """Respuesta de envío de mensaje."""

    success: bool
    id_mensaje: int | None = None


class ConversationMarkReadRequest(BaseModel):
    """Payload para marcar mensajes como leídos."""

    tipo_lector: str


class GenericSuccessResponse(BaseModel):
    """Respuesta genérica de éxito."""

    success: bool


# ============================================================================
# ENDPOINTS DE CONVERSACIONES
# ============================================================================


@app.get(
    "/conversations/user/{user_id}",
    response_model=ConversationSearchResponse,
    tags=["conversations"],
)
def get_user_conversation(
    user_id: int,
    org_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> ConversationSearchResponse:
    """Busca conversación abierta de un usuario en una organización."""
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.get_user_conversation(user_id, org_id, headers)
        return ConversationSearchResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/conversations",
    response_model=ConversationCreateResponse,
    tags=["conversations"],
)
def create_conversation(
    request: ConversationCreateRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> ConversationCreateResponse:
    """Crea una nueva conversación."""
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.create_conversation(request.model_dump(), headers)
        return ConversationCreateResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(
    "/conversations/{conversation_id}/messages",
    tags=["conversations"],
)
def get_conversation_messages(
    conversation_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> list[dict]:
    """Obtiene los mensajes de una conversación."""
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        return router.get_conversation_messages(conversation_id, headers)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationMessageResponse,
    tags=["conversations"],
)
def send_conversation_message(
    conversation_id: int,
    request: ConversationMessageRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> ConversationMessageResponse:
    """Envía un mensaje en una conversación."""
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.send_conversation_message(
            conversation_id, request.model_dump(), headers
        )
        return ConversationMessageResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/conversations/{conversation_id}/mark-read",
    response_model=GenericSuccessResponse,
    tags=["conversations"],
)
def mark_conversation_read(
    conversation_id: int,
    request: ConversationMarkReadRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> GenericSuccessResponse:
    """Marca mensajes de una conversación como leídos."""
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.mark_conversation_read(
            conversation_id, request.model_dump(), headers
        )
        return GenericSuccessResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ============================================================================
# ENDPOINTS DE CAMBIOS / CALENDARIO
# ============================================================================


@app.get(
    "/cambios/organization/{org_id}",
    tags=["cambios"],
)
def get_cambios_calendar(
    org_id: int,
    mes: int | None = None,
    anio: int | None = None,
    proyecto_id: int | None = None,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> list[dict]:
    """Obtiene eventos del calendario agrupados por día."""
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        return router.get_cambios_calendar(
            org_id, headers, mes=mes, anio=anio, proyecto_id=proyecto_id
        )
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ============================================================================
# CONVERSACIONES - BACKOFFICE (gestión por organización)
# ============================================================================


class JoinConversationRequest(BaseModel):
    user_id: int


class UpdateConversationPriorityRequest(BaseModel):
    prioridad: str


class UpdateConversationStateRequest(BaseModel):
    estado: str
    user_id: int


class TicketInteractionRequest(BaseModel):
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
def get_organization_conversations(
    org_id: int,
    solo_activas: bool = True,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> list[dict]:
    """Obtiene conversaciones de una organización (backoffice)."""
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        return router.get_organization_conversations(
            org_id, headers, solo_activas=solo_activas
        )
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/conversations/{conversation_id}/join",
    response_model=GenericSuccessResponse,
    tags=["conversations"],
)
def join_conversation(
    conversation_id: int,
    request: JoinConversationRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> GenericSuccessResponse:
    """Un usuario interno se une a una conversación."""
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.join_conversation(
            conversation_id, request.user_id, headers
        )
        return GenericSuccessResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(
    "/conversations/{conversation_id}/detail",
    tags=["conversations"],
)
def get_conversation_detail(
    conversation_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict:
    """Obtiene detalle de una conversación."""
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        return router.get_conversation_detail(conversation_id, headers)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch(
    "/conversations/{conversation_id}/priority",
    response_model=GenericSuccessResponse,
    tags=["conversations"],
)
def update_conversation_priority(
    conversation_id: int,
    request: UpdateConversationPriorityRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> GenericSuccessResponse:
    """Actualiza la prioridad de una conversación."""
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.update_conversation_priority(
            conversation_id, request.prioridad, headers
        )
        return GenericSuccessResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch(
    "/conversations/{conversation_id}/state",
    response_model=GenericSuccessResponse,
    tags=["conversations"],
)
def update_conversation_state(
    conversation_id: int,
    request: UpdateConversationStateRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> GenericSuccessResponse:
    """Actualiza el estado de una conversación."""
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.update_conversation_state(
            conversation_id, request.estado, request.user_id, headers
        )
        return GenericSuccessResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ============================================================================
# TICKETS - BACKOFFICE (gestión interna)
# ============================================================================


@app.get(
    "/tickets/{ticket_id}/details",
    tags=["tickets"],
)
def get_ticket_details(
    ticket_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict:
    """Obtiene detalles de un ticket con su última interacción."""
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        return router.get_ticket_details(ticket_id, headers)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/tickets/{ticket_id}/interactions",
    response_model=GenericSuccessResponse,
    tags=["tickets"],
)
def save_ticket_interaction(
    ticket_id: int,
    request: TicketInteractionRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> GenericSuccessResponse:
    """Guarda interacción de ticket con mensaje automático."""
    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.save_ticket_interaction(
            ticket_id=ticket_id,
            user_id=request.user_id,
            cliente_id=request.cliente_id,
            respuesta=request.respuesta,
            nuevo_estado=request.nuevo_estado,
            estado_actual=request.estado_actual,
            titulo_ticket=request.titulo_ticket,
            headers=headers,
        )
        return GenericSuccessResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ============================================================================
# ENDPOINTS DE TECNOLOGÍAS
# ============================================================================


@app.get("/tecnologias", response_model=TecnologiasListResponse, tags=["tecnologias"])
def get_tecnologias(
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> TecnologiasListResponse:
    """Obtiene todas las tecnologías disponibles.

    Incluye tecnologías activas e inactivas para mostrar en UI.
    """
    try:
        result = router.get_tecnologias()
        return TecnologiasListResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(
    "/proyectos/{project_id}/tecnologia",
    response_model=ProyectoTecnologiaResponse,
    tags=["tecnologias"],
)
def get_proyecto_tecnologia(
    project_id: int,
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> ProyectoTecnologiaResponse:
    """Obtiene la tecnología asignada a un proyecto."""
    try:
        result = router.get_proyecto_tecnologia(project_id)
        return ProyectoTecnologiaResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/proyectos/{project_id}/tecnologia",
    response_model=ProyectoTecnologiaResponse,
    tags=["tecnologias"],
)
def asignar_tecnologia(
    project_id: int,
    request: AsignarTecnologiaRequest,
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> ProyectoTecnologiaResponse:
    """Asigna una tecnología a un proyecto (primera asignación)."""
    try:
        result = router.asignar_tecnologia(project_id, request.model_dump())
        return ProyectoTecnologiaResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch(
    "/proyectos/{project_id}/tecnologia",
    response_model=ProyectoTecnologiaResponse,
    tags=["tecnologias"],
)
def actualizar_tecnologia(
    project_id: int,
    request: AsignarTecnologiaRequest,
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> ProyectoTecnologiaResponse:
    """Actualiza la tecnología de un proyecto (solo Backoffice)."""
    try:
        result = router.actualizar_tecnologia(project_id, request.model_dump())
        return ProyectoTecnologiaResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(
    "/organizaciones/{org_id}/tecnologias-asignadas",
    response_model=TecnologiasAsignadasResponse,
    tags=["tecnologias"],
)
def get_tecnologias_asignadas_org(
    org_id: int,
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> TecnologiasAsignadasResponse:
    """Obtiene todas las tecnologías asignadas a proyectos de una organización.

    Retorna lista de proyectos con su tecnología asignada (o None si no tiene).
    Solo incluye proyectos existentes (existe=1).
    """
    try:
        result = router.get_tecnologias_asignadas_org(org_id)
        return TecnologiasAsignadasResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    router: BackendCoreRouter = Depends(get_router_core),
) -> VersionesListResponse:
    """Obtiene todas las versiones de un proyecto.

    Args:
        project_id: ID del proyecto
        org_id: ID de la organización (para validar pertenencia)
    """
    logger = logging.getLogger(__name__)
    logger.info("[backend-core] Consultando versiones proyecto=%s org=%s", project_id, org_id)

    try:
        result = router.get_project_versions(project_id, org_id)
        return VersionesListResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/proyectos/{project_id}/versiones",
    response_model=CrearVersionResponse,
    tags=["versiones"],
)
def create_project_version(
    project_id: int,
    request: CrearVersionRequest,
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> CrearVersionResponse:
    """Crea una nueva versión para un proyecto.

    La versión se crea con el siguiente id_version disponible.
    """
    logger = logging.getLogger(__name__)
    logger.info("[backend-core] Creando versión proyecto=%s org=%s", project_id, request.id_organizacion)

    try:
        result = router.create_project_version(project_id, request.id_organizacion)
        return CrearVersionResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    router: BackendCoreRouter = Depends(get_router_core),
) -> VersionStateResponse:
    """Obtiene el estado actual de una versión.
    
    Args:
        project_id: ID del proyecto
        version_id: Número de versión
        org_id: ID de la organización
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[backend-core] [%s] Obteniendo estado versión=%s proyecto=%s org=%s",
        client_app,
        version_id,
        project_id,
        org_id,
    )

    try:
        result = router.get_version_state(project_id, version_id, org_id)
        return VersionStateResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    router: BackendCoreRouter = Depends(get_router_core),
) -> VersionStateResponse:
    """Actualiza el estado de una versión.
    
    Args:
        project_id: ID del proyecto
        version_id: Número de versión
        org_id: ID de la organización
        request: Datos a actualizar
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[backend-core] [%s] Actualizando estado versión=%s proyecto=%s",
        client_app,
        version_id,
        project_id,
    )

    try:
        update_data = request.model_dump(exclude_unset=True)
        result = router.update_version_state(
            project_id, version_id, org_id, update_data
        )
        return VersionStateResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    router: BackendCoreRouter = Depends(get_router_core),
) -> VersionEventsResponse:
    """Obtiene el historial de eventos de una versión.
    
    Args:
        project_id: ID del proyecto
        version_id: Número de versión
        org_id: ID de la organización
        limit: Máximo número de eventos (default: 50)
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[backend-core] [%s] Obteniendo eventos versión=%s proyecto=%s",
        client_app,
        version_id,
        project_id,
    )

    try:
        result = router.get_version_events(project_id, version_id, org_id, limit)
        return VersionEventsResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/proyectos/{project_id}/versiones/crear-completa",
    response_model=CreateVersionFullResponse,
    tags=["versiones"],
)
def create_version_full(
    project_id: int,
    request: CreateVersionFullRequest,
    authorization: str | None = Header(None, alias="Authorization"),
    session_token: str | None = Header(None, alias="X-Session-Token"),
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> CreateVersionFullResponse:
    """Crea una nueva versión completa (DB + fmanagement).
    
    Este endpoint ejecuta:
    1. Cálculo de siguiente id_version
    2. Inserción en tabla versiones
    3. Creación de carpeta física vía fmanagement (opcional: clonación)
    4. Creación de estado inicial en version_states
    5. Registro de evento VERSION_CREADA
    
    Args:
        project_id: ID del proyecto
        request: Datos para crear la versión
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[backend-core] [%s] Creando versión completa proyecto=%s org=%s user=%s",
        client_app,
        project_id,
        request.id_organizacion,
        request.user_id,
    )

    try:
        result = router.create_version_full(
            project_id=project_id,
            org_id=request.id_organizacion,
            user_id=request.user_id,
            identity_type_id=request.identity_type_id,
            descripcion=request.descripcion,
            clone_from_version=request.clone_from_version,
            access_token=authorization.replace("Bearer ", "") if authorization else None,
            session_token=session_token,
        )
        return CreateVersionFullResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    router: BackendCoreRouter = Depends(get_router_core),
) -> FmanagementListResponse:
    """Lista estructura de archivos vía fmanagement.
    
    Args:
        request: Parámetros para el listado
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[backend-core] [%s] Listando fmanagement org=%s prj=%s version=%s",
        client_app,
        request.org_folder,
        request.prj_folder,
        request.version_folder,
    )

    try:
        result = router.fmanagement_list(
            org_folder=request.org_folder,
            prj_folder=request.prj_folder,
            version_folder=request.version_folder,
            user_id=request.user_id,
            identity_type_id=request.identity_type_id,
        )
        return FmanagementListResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/fmanagement/operation",
    response_model=FmanagementOperationResponse,
    tags=["fmanagement"],
)
def fmanagement_operation(
    request: FmanagementOperationRequest,
    client_app: str = Depends(get_client_app),
    router: BackendCoreRouter = Depends(get_router_core),
) -> FmanagementOperationResponse:
    """Ejecuta una operación genérica en fmanagement.

    Operaciones soportadas:
    - create_folder: Crea una carpeta
    - rename_folder: Renombra una carpeta
    - delete_folder: Elimina una carpeta
    - create_file: Crea/sube un archivo
    - rename_file: Renombra un archivo
    - delete_file: Elimina un archivo
    - download_file: Descarga un archivo
    - create_version: Crea una nueva versión
    - get_properties: Obtiene propiedades de un archivo/carpeta

    Args:
        request: Operación y parámetros
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "[backend-core] [%s] Operación fmanagement: %s",
        client_app,
        request.operation,
    )

    try:
        result = router.fmanagement_operation(
            operation=request.operation,
            params=request.params,
        )
        
        # Si el resultado contiene datos binarios (caso descarga), retornamos Response directo
        if result.get("success") and isinstance(result.get("data"), dict) and result["data"].get("is_binary"):
            data = result["data"]
            return Response(
                content=data["_raw_data"],
                media_type=data["content_type"],
                headers={
                    "Content-Disposition": f'attachment; filename="{request.params.get("filename", "download")}"'
                }
            )

        return FmanagementOperationResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ============================================================================
# ASSIGNMENTS - Gestor de asignaciones (SuperAdmin only)
# ============================================================================

@app.get("/assignments/internal-users", response_model=list[InternalUserDto])
def get_internal_users_endpoint(
    router: BackendCoreRouter = Depends(get_router_core),
) -> list[InternalUserDto]:
    """Gets internal users for assignment selectors."""
    try:
        users = router.get_internal_users()
        return [InternalUserDto(**user) for user in users]
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get(
    "/assignments/organizations/{organization_id}",
    response_model=list[OrganizationAssignmentDto],
)
def get_organization_assignments_endpoint(
    organization_id: int,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> list[OrganizationAssignmentDto]:
    """Gets organization assignments."""
    try:
        assignments = router.get_organization_assignments(
            organization_id, identity_type_id
        )
        return [OrganizationAssignmentDto(**a) for a in assignments]
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        import traceback
        error_detail = f"{type(exc).__name__}: {str(exc)}\n{traceback.format_exc()}"
        print(f"[ERROR] get_organization_assignments: {error_detail}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {type(exc).__name__}: {str(exc)}",
        ) from exc


@app.post("/assignments/organizations")
def create_organization_assignment_endpoint(
    payload: CreateOrgAssignmentDto,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Creates organization assignment."""
    try:
        return router.create_organization_assignment(
            user_id=payload.user_id,
            organization_id=payload.organization_id,
            role_id=payload.role_id,
            identity_type_id=identity_type_id,
        )
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch("/assignments/organizations/{assignment_id}")
def update_organization_assignment_endpoint(
    assignment_id: int,
    payload: UpdateAssignmentDto,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Updates organization assignment active status."""
    try:
        return router.update_organization_assignment(
            assignment_id=assignment_id,
            active=payload.active,
            identity_type_id=identity_type_id,
        )
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.delete("/assignments/organizations/{assignment_id}")
def delete_organization_assignment_endpoint(
    assignment_id: int,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Deletes organization assignment permanently."""
    try:
        return router.delete_organization_assignment(
            assignment_id=assignment_id,
            identity_type_id=identity_type_id,
        )
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get(
    "/assignments/validate-org-prerequisite",
    response_model=PrerequisiteValidationDto,
)
def validate_org_prerequisite_endpoint(
    user_id: int,
    organization_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> PrerequisiteValidationDto:
    """Validates if user has active org role (prerequisite)."""
    try:
        result = router.validate_org_prerequisite(user_id, organization_id)
        return PrerequisiteValidationDto(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get(
    "/assignments/projects/{project_id}",
    response_model=list[ProjectAssignmentDto],
)
def get_project_assignments_endpoint(
    project_id: int,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> list[ProjectAssignmentDto]:
    """Gets project assignments."""
    try:
        assignments = router.get_project_assignments(
            project_id, identity_type_id
        )
        return [ProjectAssignmentDto(**a) for a in assignments]
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/assignments/projects")
def create_project_assignment_endpoint(
    payload: CreateProjectAssignmentDto,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Creates project assignment (with prerequisite validation)."""
    try:
        return router.create_project_assignment(
            user_id=payload.user_id,
            organization_id=payload.organization_id,
            project_id=payload.project_id,
            role_id=payload.role_id,
            identity_type_id=identity_type_id,
        )
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch("/assignments/projects/{assignment_id}")
def update_project_assignment_endpoint(
    assignment_id: int,
    payload: UpdateAssignmentDto,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Updates project assignment active status."""
    try:
        return router.update_project_assignment(
            assignment_id=assignment_id,
            active=payload.active,
            identity_type_id=identity_type_id,
        )
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.delete("/assignments/projects/{assignment_id}")
def delete_project_assignment_endpoint(
    assignment_id: int,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Deletes project assignment permanently."""
    try:
        return router.delete_project_assignment(
            assignment_id=assignment_id,
            identity_type_id=identity_type_id,
        )
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# PROMPTS MANAGEMENT - Gestión de Prompts (SuperAdmin only)
# ============================================================================


@app.get("/prompts/{category}", response_model=list[PromptDto], tags=["prompts"])
def get_prompts_endpoint(
    category: str,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> list[PromptDto]:
    """Gets all prompts from a category.
    
    Args:
        category: One of 'identidades', 'contexto', 'solicitudes', 'modalidad'
        identity_type_id: User's identity type (from session)
        
    Returns:
        List of prompts
        
    Security:
        Only SuperAdmin (identity_type_id=1) can access
    """
    try:
        prompts = router.get_prompts(category, identity_type_id)
        return [PromptDto(**p) for p in prompts]
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get("/prompts/{category}/{id_prompt}", response_model=PromptDto, tags=["prompts"])
def get_prompt_endpoint(
    category: str,
    id_prompt: int,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> PromptDto:
    """Gets a specific prompt by ID."""
    try:
        prompt = router.get_prompt(category, id_prompt, identity_type_id)
        return PromptDto(**prompt)
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@app.post("/prompts/{category}", tags=["prompts"])
def create_prompt_endpoint(
    category: str,
    payload: CreatePromptDto,
    user_id: int,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Creates a new prompt.
    
    Args:
        category: Prompt category
        payload: Prompt data (name, description, prompt text)
        user_id: User ID (for audit)
        identity_type_id: User's identity type
        
    Returns:
        Success response with new prompt ID
    """
    try:
        return router.create_prompt(
            category=category,
            name=payload.name,
            description=payload.description,
            prompt=payload.prompt,
            user_id=user_id,
            identity_type_id=identity_type_id,
        )
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.put("/prompts/{category}/{id_prompt}", tags=["prompts"])
def update_prompt_endpoint(
    category: str,
    id_prompt: int,
    payload: UpdatePromptDto,
    user_id: int,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Updates an existing prompt."""
    try:
        return router.update_prompt(
            category=category,
            id_prompt=id_prompt,
            name=payload.name,
            description=payload.description,
            prompt=payload.prompt,
            user_id=user_id,
            identity_type_id=identity_type_id,
        )
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch("/prompts/{category}/{id_prompt}/toggle", tags=["prompts"])
def toggle_prompt_endpoint(
    category: str,
    id_prompt: int,
    payload: TogglePromptDto,
    user_id: int,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Toggles prompt active status (enable/disable)."""
    try:
        return router.toggle_prompt(
            category=category,
            id_prompt=id_prompt,
            active=payload.active,
            user_id=user_id,
            identity_type_id=identity_type_id,
        )
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
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
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Obtiene estado de versión por ID."""
    try:
        result = router.get_project_version_state_by_id(
            state_id, user_id, identity_type_id
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Estado no encontrado",
            )
        return result
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
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
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Obtiene estado de una versión específica."""
    try:
        result = router.get_project_version_state_by_version(
            organization_id, project_id, version_id, user_id, identity_type_id
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Estado no encontrado",
            )
        return result
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@app.get("/project-version-states", tags=["project-version-states"])
def list_project_version_states_endpoint(
    user_id: int,
    identity_type_id: int,
    organization_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
    router: BackendCoreRouter = Depends(get_router_core),
) -> list[dict[str, Any]]:
    """Lista estados según asignaciones del usuario."""
    try:
        return router.list_project_version_states_by_user(
            user_id, identity_type_id, organization_id, limit, offset
        )
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@app.patch(
    "/project-version-states/{state_id}/proposal",
    tags=["project-version-states"],
)
def update_proposal_phase_endpoint(
    state_id: int,
    payload: UpdateProposalPhaseDto,
    user_id: int,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Actualiza fase de propuesta (aceptaciones)."""
    try:
        return router.update_proposal_phase(
            state_id,
            payload.aceptacion_cliente,
            payload.aceptacion_interna,
            user_id,
            identity_type_id,
            revision_interna=payload.revision_interna,
            propuesta_mejoras=payload.propuesta_mejoras,
        )
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch(
    "/project-version-states/{state_id}/training",
    tags=["project-version-states"],
)
def update_training_phase_endpoint(
    state_id: int,
    payload: UpdateTrainingPhaseDto,
    user_id: int,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Actualiza fase de entrenamiento."""
    try:
        return router.update_training_phase(
            state_id, payload.completado, user_id, identity_type_id
        )
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch(
    "/project-version-states/{state_id}/evaluation",
    tags=["project-version-states"],
)
def update_evaluation_phase_endpoint(
    state_id: int,
    payload: UpdateEvaluationPhaseDto,
    user_id: int,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Actualiza fase de evaluación/reentrenamiento."""
    try:
        # Usar evaluacion_entrenamiento si está presente, sino evaluacion (compatibilidad)
        evaluacion_value = payload.evaluacion_entrenamiento if payload.evaluacion_entrenamiento is not None else payload.evaluacion
        if evaluacion_value is None:
            evaluacion_value = False

        return router.update_evaluation_phase(
            state_id,
            evaluacion_value,
            payload.reentrenamiento,
            payload.optimizacion,
            payload.calidad_aprobada,
            user_id,
            identity_type_id,
        )
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch(
    "/project-version-states/{state_id}/generation",
    tags=["project-version-states"],
)
def update_generation_phase_endpoint(
    state_id: int,
    payload: UpdateGenerationPhaseDto,
    user_id: int,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Actualiza fase de generación LLM."""
    try:
        return router.update_generation_phase(
            state_id,
            generacion_completada=payload.generacion_completada,
            user_id=user_id,
            identity_type_id=identity_type_id,
            generacion_solicitada=payload.generacion_solicitada,
        )
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch(
    "/project-version-states/{state_id}/notification",
    tags=["project-version-states"],
)
def update_notification_phase_endpoint(
    state_id: int,
    payload: UpdateNotificationPhaseDto,
    user_id: int,
    identity_type_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Actualiza fase de notificación."""
    try:
        return router.update_notification_phase(
            state_id, payload.notificacion_enviada, user_id, identity_type_id
        )
    except BackendCorePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# Jobs - Actualización de estado desde Trainer
# ============================================================================


@app.patch("/jobs/{job_id}/complete", response_model=JobCompleteResponse, tags=["jobs"])
def complete_job_endpoint(
    job_id: int,
    payload: JobCompleteRequest,
    router: BackendCoreRouter = Depends(get_router_core),
) -> JobCompleteResponse:
    """Actualiza el estado de un job y registra un evento en la tabla cambios.

    Llamado por el Trainer al completar (o fallar) un procesamiento asíncrono.
    Ejecuta INSERT en cambios + UPDATE en jobs dentro de una transacción.
    """
    try:
        result = router.complete_job(
            job_id=job_id,
            id_organizacion=payload.id_organizacion,
            id_proyecto=payload.id_proyecto,
            id_version=payload.id_version,
            descripcion=payload.descripcion,
            referencia_salida=payload.referencia_salida,
            tipo_cambio=payload.tipo_cambio,
            id_estado=payload.id_estado,
        )
        return JobCompleteResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# Training - Versiones pendientes de entrenamiento
# ============================================================================


@app.get("/training/pending-versions", tags=["training"])
def get_pending_training_versions_endpoint(
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Obtiene versiones con entrenamiento inicial solicitado.

    Flujo: Broker → Backend Core → MariaDB (myllm_projects_db + myllm_core_db)
    """
    try:
        versions = router.get_pending_training_versions()
        return {"versions": versions, "total": len(versions)}
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# Training - Registro y seguimiento de entrenamientos
# ============================================================================


class TrainingParamsResponse(BaseModel):
    """Respuesta del endpoint inteligente de parámetros de entrenamiento.

    Devuelve defaults (primer entrenamiento) o los parámetros del último job
    (reentrenamiento), junto con flags informativos y lista de modelos.
    """

    success: bool = True
    es_primer_entrenamiento: bool = True
    es_reentrenamiento: bool = False
    # Parámetros de preparación de datos
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embedding_dimension: int = 768
    sequence_length: int = 512
    distance_metric: str = "cosine"
    # Parámetros de modelo y generación
    model_type: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    top_k: int = 5
    # Parámetros de optimización
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 10
    hidden_units: int = 256
    dropout_rate: float = 0.1
    loss_function: str = "cross_entropy"
    optimizer: str = "adam"
    # Modelos disponibles
    modelos_disponibles: list[dict] = []
    message: str = ""


class TrainingProgressNotification(BaseModel):
    """Notificación de progreso de entrenamiento desde el trainer."""

    id_entrenamiento: int
    phase_key: str          # Clave de la fase principal (ej: "3" o "6")
    subfase_key: str        # Clave de la subfase (ej: "3.2" o "6.1")
    subfase_name: str       # Nombre legible (ej: "Chunking")
    status: str             # "in_progress", "completed", "error", "failed"
    elapsed_time: str = ""  # Tiempo empleado (ej: "2m 15s")
    error_message: str = ""
    metrics: str = ""       # JSON de métricas opcionales (fases autónomas)


class AutonomousInitRequest(BaseModel):
    """Payload para inicializar entrenamiento autónomo."""

    id_entrenamiento: int
    training_mode: str = "simulation"  # simulation, test, production


class AutonomousMetadataUpdate(BaseModel):
    """Payload para actualizar metadatos de entrenamiento autónomo."""

    id_entrenamiento: int
    metadata_type: str    # "dataset", "lora", "gguf", "package"
    data: dict[str, Any]  # Campos específicos según tipo


class EntrenamientoRegisterRequest(BaseModel):
    """Payload para registrar un nuevo entrenamiento."""

    id_organizacion: int
    id_proyecto: int
    id_version: int
    pat_version: str = ""
    entrenamiento_inicial: bool = True
    reentrenamiento: bool = False
    # Parámetros opcionales de entrenamiento (si llegan, se usan; si no, defaults)
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


class EntrenamientoRegisterResponse(BaseModel):
    """Respuesta al registrar un entrenamiento."""

    success: bool
    id_entrenamiento: int | None = None
    id_job_entrenamientos: int | None = None
    collection_name: str = ""
    numero_secuencia: int = 0
    message: str = ""


class EntrenamientoPhaseRequest(BaseModel):
    """Payload para actualizar fase de un entrenamiento."""

    fase_actual: str = Field(
        ...,
        description="Fase: validacion, preparacion, configuracion, entrenamiento",
    )


class EntrenamientoPhaseResponse(BaseModel):
    """Respuesta de actualización de fase."""

    success: bool
    message: str = ""


class EntrenamientoCompleteRequest(BaseModel):
    """Payload para marcar entrenamiento como completado."""

    modelo_path: str = ""


class EntrenamientoCompleteResponse(BaseModel):
    """Respuesta de completado de entrenamiento."""

    success: bool
    message: str = ""


class EntrenamientoCancelRequest(BaseModel):
    """Payload para cancelar entrenamiento."""

    motivo: str = "Cancelado por usuario"


class EntrenamientoCancelResponse(BaseModel):
    """Respuesta de cancelación de entrenamiento."""

    success: bool
    message: str = ""


class EntrenamientoErrorRequest(BaseModel):
    """Payload para marcar entrenamiento como error."""

    error_mensaje: str = ""


class EntrenamientoErrorResponse(BaseModel):
    """Respuesta de error de entrenamiento."""

    success: bool
    message: str = ""


@app.post(
    "/entrenamientos/register",
    response_model=EntrenamientoRegisterResponse,
    tags=["training"],
)
def register_entrenamiento_endpoint(
    payload: EntrenamientoRegisterRequest,
    router: BackendCoreRouter = Depends(get_router_core),
) -> EntrenamientoRegisterResponse:
    """Registra un nuevo entrenamiento en la BD.

    Crea registro en jobs_entrenamientos (parámetros) + entrenamientos (proceso).
    Calcula numero_secuencia y genera collection_name para ChromaDB.

    Flujo: Trainer → Broker → Backend Core → MariaDB
    """
    # Extraer parámetros opcionales del request
    training_params = {}
    for key in (
        "learning_rate", "batch_size", "epochs", "embedding_dimension",
        "sequence_length", "hidden_units", "dropout_rate", "chunk_size",
        "chunk_overlap", "temperature", "max_tokens", "distance_metric",
        "top_k", "loss_function", "optimizer", "model_type",
    ):
        val = getattr(payload, key, None)
        if val is not None:
            training_params[key] = val

    try:
        result = router.register_entrenamiento(
            id_organizacion=payload.id_organizacion,
            id_proyecto=payload.id_proyecto,
            id_version=payload.id_version,
            pat_version=payload.pat_version,
            entrenamiento_inicial=payload.entrenamiento_inicial,
            reentrenamiento=payload.reentrenamiento,
            training_params=training_params if training_params else None,
        )
        return EntrenamientoRegisterResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch(
    "/entrenamientos/{id_entrenamiento}/phase",
    response_model=EntrenamientoPhaseResponse,
    tags=["training"],
)
def update_entrenamiento_phase_endpoint(
    id_entrenamiento: int,
    payload: EntrenamientoPhaseRequest,
    router: BackendCoreRouter = Depends(get_router_core),
) -> EntrenamientoPhaseResponse:
    """Actualiza la fase actual de un entrenamiento.

    Si es la primera fase activa, establece fecha_inicio y estado=en_progreso.

    Flujo: Trainer → Broker → Backend Core → MariaDB
    """
    try:
        result = router.update_entrenamiento_phase(
            id_entrenamiento=id_entrenamiento,
            fase_actual=payload.fase_actual,
        )
        return EntrenamientoPhaseResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch(
    "/entrenamientos/{id_entrenamiento}/complete",
    response_model=EntrenamientoCompleteResponse,
    tags=["training"],
)
def complete_entrenamiento_endpoint(
    id_entrenamiento: int,
    payload: EntrenamientoCompleteRequest,
    router: BackendCoreRouter = Depends(get_router_core),
) -> EntrenamientoCompleteResponse:
    """Marca un entrenamiento como completado.

    Actualiza estado=completado, fecha_fin=NOW(), modelo_path.

    Flujo: Trainer → Broker → Backend Core → MariaDB
    """
    try:
        result = router.complete_entrenamiento(
            id_entrenamiento=id_entrenamiento,
            modelo_path=payload.modelo_path,
        )
        return EntrenamientoCompleteResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch(
    "/entrenamientos/{id_entrenamiento}/error",
    response_model=EntrenamientoErrorResponse,
    tags=["training"],
)
def error_entrenamiento_endpoint(
    id_entrenamiento: int,
    payload: EntrenamientoErrorRequest,
    router: BackendCoreRouter = Depends(get_router_core),
) -> EntrenamientoErrorResponse:
    """Marca un entrenamiento como error.

    Actualiza estado=error, fecha_fin=NOW(), error_mensaje.

    Flujo: Trainer → Broker → Backend Core → MariaDB
    """
    try:
        result = router.error_entrenamiento(
            id_entrenamiento=id_entrenamiento,
            error_mensaje=payload.error_mensaje,
        )
        return EntrenamientoErrorResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch(
    "/entrenamientos/{id_entrenamiento}/cancel",
    response_model=EntrenamientoCancelResponse,
    tags=["training"],
)
def cancel_entrenamiento_endpoint(
    id_entrenamiento: int,
    payload: EntrenamientoCancelRequest,
    router: BackendCoreRouter = Depends(get_router_core),
) -> EntrenamientoCancelResponse:
    """Cancela un entrenamiento en progreso.

    Actualiza estado=cancelado, fecha_fin=NOW(), registra motivo en cambios.

    Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
    """
    try:
        result = router.cancel_entrenamiento(
            id_entrenamiento=id_entrenamiento,
            motivo=payload.motivo,
        )
        return EntrenamientoCancelResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# Endpoint inteligente de parámetros de entrenamiento
# ============================================================================


@app.get(
    "/training/params/{org_id}/{project_id}/{version_id}",
    response_model=TrainingParamsResponse,
    tags=["training"],
)
def get_training_params_endpoint(
    org_id: int,
    project_id: int,
    version_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> TrainingParamsResponse:
    """Endpoint inteligente que devuelve parámetros de entrenamiento.

    Si nunca se ha entrenado la versión → devuelve defaults de protected_values.
    Si ya se ha entrenado → devuelve los parámetros del último jobs_entrenamientos.
    Incluye flags es_primer_entrenamiento/es_reentrenamiento y lista de modelos.

    Flujo: Backoffice → Middleware → Broker → Backend Core → MariaDB
    """
    try:
        result = router.get_training_params(org_id, project_id, version_id)
        return TrainingParamsResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch("/training/progress", tags=["training"])
async def update_training_progress_endpoint(
    payload: TrainingProgressNotification,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Recibe notificaciones de progreso desde el trainer.

    El trainer envía actualizaciones de cada subfase durante el entrenamiento
    para que el backoffice pueda actualizar el panel de evolución en tiempo real.

    Flujo: Trainer → Broker → Backend Core → Almacena progreso
    """
    try:
        result = await router.update_training_progress(payload.model_dump())
        return result
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get("/training/entrenamientos/{id_entrenamiento}/progress", tags=["training"])
async def get_training_progress_endpoint(
    id_entrenamiento: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Consulta el progreso actual de un entrenamiento.

    El backoffice usa este endpoint para polling y actualizar la UI en tiempo real.

    Flujo: Backoffice → Middleware → Backend Core → Devuelve progreso en caché

    Args:
        id_entrenamiento: ID del entrenamiento a consultar.

    Returns:
        Diccionario con el progreso de todas las fases y subfases.
    """
    try:
        result = await router.get_training_progress(id_entrenamiento)
        return result
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# Entrenamiento Autónomo (fases 6-9)
# ============================================================================


@app.post("/training/autonomous/init", tags=["training"])
async def initialize_autonomous_training_endpoint(
    payload: AutonomousInitRequest,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Inicializa registro de entrenamiento autónomo.

    Crea el registro en entrenamientos_autonomos vinculado al entrenamiento
    existente.

    Flujo: Trainer → Broker → Backend Core → MariaDB
    """
    try:
        result = await router.initialize_autonomous_training(payload.model_dump())
        return result
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.patch("/training/autonomous/metadata", tags=["training"])
async def update_autonomous_metadata_endpoint(
    payload: AutonomousMetadataUpdate,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Actualiza metadatos de entrenamiento autónomo.

    Recibe actualizaciones de dataset_info, lora_info, gguf_info o package_info
    según el metadata_type.

    Flujo: Trainer → Broker → Backend Core → MariaDB
    """
    try:
        result = await router.update_autonomous_metadata(payload.model_dump())
        return result
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get("/training/autonomous/{id_entrenamiento}/progress", tags=["training"])
async def get_autonomous_progress_endpoint(
    id_entrenamiento: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Consulta el progreso del entrenamiento autónomo (fases 6-9).

    Args:
        id_entrenamiento: ID del entrenamiento a consultar.

    Returns:
        Diccionario con training_mode, subphases y summary.
    """
    try:
        result = await router.get_autonomous_progress(id_entrenamiento)
        return result
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get("/training/autonomous/packages", tags=["training"])
async def list_autonomous_packages_endpoint(
    id_organizacion: int | None = None,
    id_proyecto: int | None = None,
    id_version: int | None = None,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Lista paquetes autónomos disponibles para descargar.

    Args:
        id_organizacion: Filtrar por organización (opcional).
        id_proyecto: Filtrar por proyecto (opcional).
        id_version: Filtrar por versión (opcional).

    Returns:
        Diccionario con success y lista de paquetes.
    """
    try:
        filters = {}
        if id_organizacion is not None:
            filters["id_organizacion"] = id_organizacion
        if id_proyecto is not None:
            filters["id_proyecto"] = id_proyecto
        if id_version is not None:
            filters["id_version"] = id_version

        result = await router.list_autonomous_packages(filters)
        return result
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get("/analysis/metrics", tags=["analysis"])
async def get_analysis_metrics_endpoint(
    organization_id: int | None = None,
    project_id: int | None = None,
    version_id: int | None = None,
    router: BackendCoreRouter = Depends(get_router_core),
) -> list[dict[str, Any]]:
    """Obtiene las métricas de análisis de entrenamientos filtradas.

    Args:
        organization_id: ID de la organización (opcional).
        project_id: ID del proyecto (opcional).
        version_id: ID de la versión (opcional).

    Returns:
        Lista de análisis con métricas agregadas por categorías.
    """
    try:
        result = await router.get_analysis_metrics(
            organization_id=organization_id,
            project_id=project_id,
            version_id=version_id
        )
        return result
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# Informes - Archivos markdown de reportes
# ============================================================================


class InformeFileDto(BaseModel):
    """Información de un archivo de informe."""

    filename: str
    display_name: str


class InformesListResponse(BaseModel):
    """Respuesta con lista de archivos de informes."""

    archivos: list[InformeFileDto]
    total: int


class InformeContentResponse(BaseModel):
    """Respuesta con contenido de un informe."""

    content: str
    display_name: str


@app.get(
    "/informes/{org_id}/{project_id}/{version_id}/files",
    response_model=InformesListResponse,
    tags=["informes"],
)
def list_informe_files(
    org_id: int,
    project_id: int,
    version_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> InformesListResponse:
    """Lista archivos markdown de informes para una versión.

    Flujo: Frontend/Backoffice → Middleware → Broker → Backend Core → Filesystem
    """
    try:
        result = router.list_informe_files(org_id, project_id, version_id)
        return InformesListResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get(
    "/informes/{org_id}/{project_id}/{version_id}/content",
    response_model=InformeContentResponse,
    tags=["informes"],
)
def get_informe_content(
    org_id: int,
    project_id: int,
    version_id: int,
    file: str = "",
    router: BackendCoreRouter = Depends(get_router_core),
) -> InformeContentResponse:
    """Obtiene el contenido de un archivo markdown de informe.

    Args:
        file: display_name del archivo (sin extensión .md)

    Flujo: Frontend/Backoffice → Middleware → Broker → Backend Core → Filesystem
    """
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parámetro 'file' es requerido",
        )
    try:
        result = router.get_informe_content(org_id, project_id, version_id, file)
        return InformeContentResponse(**result)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# Model Packages - Paquetes ZIP de modelos para descarga
# ============================================================================


@app.get(
    "/models/packages",
    tags=["models"],
)
def list_model_packages(
    org_id: int | None = None,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Lista paquetes ZIP de modelos disponibles para descarga.

    Flujo: Frontend/Backoffice → Middleware → Broker → Backend Core → Filesystem
    """
    try:
        return router.list_model_packages(org_id)
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get(
    "/models/packages/download",
    tags=["models"],
)
def download_model_package(
    org_id: int,
    project_id: int,
    version_id: int,
    filename: str,
    router: BackendCoreRouter = Depends(get_router_core),
):
    """Descarga un paquete ZIP de modelo desde el filesystem del backend core.

    Flujo: Frontend/Backoffice → Middleware → Broker → Backend Core → Filesystem
    """
    from fastapi.responses import FileResponse

    try:
        file_path = router.get_model_package_path(org_id, project_id, version_id, filename)
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/zip",
        )
    except BackendCoreBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# ========================================================================
# JOB TEMPLATES
# ========================================================================


@app.get("/job-templates/catalogs")
def get_job_template_catalogs(
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Obtiene catálogos para plantillas de jobs."""
    try:
        return router.get_job_template_catalogs()
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/job-templates")
def get_job_templates(
    router: BackendCoreRouter = Depends(get_router_core),
) -> list[dict[str, Any]]:
    """Lista plantillas de jobs."""
    try:
        return router.get_job_templates()
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/job-templates")
def save_job_template(
    data: dict[str, Any],
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Crea o actualiza una plantilla de job."""
    try:
        return router.save_job_template(data)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/job-templates/{template_id}/toggle")
def toggle_job_template(
    template_id: int,
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Activa/desactiva una plantilla de job."""
    try:
        return router.toggle_job_template(template_id)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ============================================================================
# JOBS - Gestión de jobs
# ============================================================================


@app.get("/jobs")
def get_jobs(
    org_id: int,
    project_id: int,
    version_id: int,
    tipo_clave: str | None = None,
    router: BackendCoreRouter = Depends(get_router_core),
) -> list[dict[str, Any]]:
    """Lista jobs filtrados por org/proyecto/versión."""
    try:
        return router.get_jobs(org_id, project_id, version_id, tipo_clave)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/jobs")
def create_job(
    data: dict[str, Any],
    router: BackendCoreRouter = Depends(get_router_core),
) -> dict[str, Any]:
    """Crea un nuevo job."""
    try:
        return router.create_job(data)
    except BackendCoreBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
