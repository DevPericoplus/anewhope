"""Capa de API para el backend IA (trainer)."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated, Any, AsyncIterator

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

import importlib.util
import sys
from pathlib import Path


def _load_trainer_module(module_name: str, module_path: Path) -> Any:
    """Carga un módulo dinámicamente desde una ruta."""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar {module_name} desde {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Cargar routertrainer
_router_path = Path(__file__).resolve().parent / "routertrainer.py"
_routertrainer = _load_trainer_module("routertrainer_backend", _router_path)

BackendTrainerBusinessError = _routertrainer.BackendTrainerBusinessError
BackendTrainerPermissionError = _routertrainer.BackendTrainerPermissionError
BackendTrainerRouter = _routertrainer.BackendTrainerRouter

# Cargar fmanagement_client
_infra_path = Path(__file__).resolve().parent / "4_infrastructure"
_fmanagement_path = _infra_path / "web" / "fmanagement_client.py"
_fmanagement_module = _load_trainer_module("fmanagement_client_trainer", _fmanagement_path)
FmanagementClient = _fmanagement_module.FmanagementClient

# Cargar storage_adapter
_storage_adapter_path = _infra_path / "persistence" / "storage_adapter.py"
_storage_adapter = _load_trainer_module("storage_adapter_trainer", _storage_adapter_path)
load_fmanagement_settings = _storage_adapter.load_fmanagement_settings


# === Modelos de Request/Response ===


class HealthResponse(BaseModel):
    """Respuesta del health check."""

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


class VersionFilesResponse(BaseModel):
    """Respuesta con archivos de versión clonada."""

    files: list[dict[str, Any]] = Field(default_factory=list)
    total_files: int = 0


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


class PermissionsResponse(BaseModel):
    """Respuesta con permisos de entrenamiento."""

    identity_type_id: int
    permissions: dict[str, bool] = Field(default_factory=dict)


class DocumentacionRequest(BaseModel):
    """Payload para análisis de documentación."""

    id_job: int = 0
    id_organizacion: int
    id_proyecto: int
    id_version: int
    nombre_job: str = ""
    descripcion_job: str = ""
    id_template: int = 0
    template_nombre: str = ""
    modelo_nombre: str = ""
    salida_nombre: str = ""
    estado_nombre: str = ""
    prompt_final: str = ""
    identity_type_id: int | None = None


class DocumentacionResponse(BaseModel):
    """Respuesta de análisis de documentación (ACK)."""

    success: bool
    message: str = ""
    received_at: str = ""


class MetadatosRequest(BaseModel):
    """Payload para análisis de metadatos de ficheros."""

    id_job: int = 0
    id_organizacion: int
    id_proyecto: int
    id_version: int
    nombre_job: str = ""
    descripcion_job: str = ""
    id_template: int = 0
    template_nombre: str = ""
    modelo_nombre: str = ""
    salida_nombre: str = ""
    estado_nombre: str = ""
    prompt_final: str = ""
    identity_type_id: int | None = None


class MetadatosResponse(BaseModel):
    """Respuesta de análisis de metadatos (ACK)."""

    success: bool
    message: str = ""
    received_at: str = ""


# === Helpers ===


def _build_permission_headers(
    authorization: str | None,
    session_token: str | None,
    client_app: str | None = None,
) -> dict[str, str]:
    """Construye headers para validar permisos."""

    headers: dict[str, str] = {}
    if authorization:
        headers["Authorization"] = authorization
    if session_token:
        headers["X-Session-Token"] = session_token
    if client_app:
        headers["X-Client-App"] = client_app
    return headers


def get_client_app(
    client_app: Annotated[str | None, Header(alias="X-Client-App")] = None,
) -> str:
    """Extrae el header X-Client-App de la petición."""

    return client_app or "unknown"


def _configure_logging() -> None:
    """Configura logging del backend IA con salida a console.log."""

    logs_dir = Path(__file__).resolve().parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Archivo de actividad específico
    activity_log_path = os.environ.get(
        "TRAINER_ACTIVITY_LOG_PATH",
        str(logs_dir / "trainer_activity.log"),
    )

    # Archivo console.log unificado para soporte
    console_log_path = logs_dir / "console.log"

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    # Formato legible para técnicos de soporte
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | trainer         | %(message)s",
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


# === Dependencias ===


def get_fmanagement_client() -> FmanagementClient:
    """Inyecta el cliente de fmanagement."""

    settings = load_fmanagement_settings()
    return FmanagementClient(base_url=settings.base_url)


def get_router_trainer(
    fmanagement_client: FmanagementClient = Depends(get_fmanagement_client),
) -> BackendTrainerRouter:
    """Inyecta el orquestador de backend IA."""

    return BackendTrainerRouter(
        fmanagement_client=fmanagement_client,
    )


# === Aplicación FastAPI ===


# Cargar módulo de Ollama una sola vez y reutilizarlo
_ollama_module_path = Path(__file__).resolve().parent / "apitrainer_ollama.py"
_ollama_module = _load_trainer_module("apitrainer_ollama", _ollama_module_path)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Gestiona el ciclo de vida de la aplicación."""

    _configure_logging()

    # Inicializar adaptador de Ollama
    try:
        import os
        ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        _ollama_module.init_ollama_adapter(host=ollama_host)
        logging.info(f"Adaptador de Ollama inicializado con host: {ollama_host}")
    except Exception as e:
        logging.warning(f"No se pudo inicializar Ollama (puede no estar instalado): {e}")

    yield


app = FastAPI(title="Backend IA (Trainer)", lifespan=lifespan)


# Registrar endpoints de Ollama usando el mismo módulo
try:
    _ollama_module.register_ollama_routes(app)
    logging.info("Endpoints de Ollama registrados correctamente")
except Exception as e:
    logging.warning(f"No se pudieron registrar endpoints de Ollama: {e}")


# === Endpoints ===


@app.get("/trainer/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Health check del servicio."""

    return HealthResponse(
        status="healthy",
        service="backend-ia-trainer",
        version="1.0.0",
    )


@app.post("/trainer/version/clone", response_model=VersionCloneResponse)
def clone_version_for_training(
    payload: VersionCloneRequest,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
    client_app: str = Depends(get_client_app),
    router: BackendTrainerRouter = Depends(get_router_trainer),
) -> VersionCloneResponse:
    """Clona una versión para entrenamiento."""

    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.clone_version_for_training(payload.model_dump(), headers)
        return VersionCloneResponse(**result)
    except BackendTrainerPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendTrainerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get("/trainer/version/{version_id}/files", response_model=VersionFilesResponse)
def get_version_files(
    version_id: int,
    identity_type_id: int | None = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
    client_app: str = Depends(get_client_app),
    router: BackendTrainerRouter = Depends(get_router_trainer),
) -> VersionFilesResponse:
    """Lista archivos de una versión clonada."""

    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.get_version_files(version_id, identity_type_id, headers)
        return VersionFilesResponse(**result)
    except BackendTrainerPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendTrainerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@app.post("/trainer/training/start", response_model=TrainingStartResponse)
def start_training(
    payload: TrainingStartRequest,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
    client_app: str = Depends(get_client_app),
    router: BackendTrainerRouter = Depends(get_router_trainer),
) -> TrainingStartResponse:
    """Inicia un proceso de entrenamiento."""

    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.start_training(payload.model_dump(), headers)
        return TrainingStartResponse(**result)
    except BackendTrainerPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendTrainerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/trainer/training/stop", response_model=TrainingStopResponse)
def stop_training(
    payload: TrainingStopRequest,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
    client_app: str = Depends(get_client_app),
    router: BackendTrainerRouter = Depends(get_router_trainer),
) -> TrainingStopResponse:
    """Detiene un proceso de entrenamiento."""

    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.stop_training(payload.model_dump(), headers)
        return TrainingStopResponse(**result)
    except BackendTrainerPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendTrainerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.get("/trainer/training/{training_id}/status", response_model=TrainingStatusResponse)
def get_training_status(
    training_id: int,
    identity_type_id: int | None = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
    client_app: str = Depends(get_client_app),
    router: BackendTrainerRouter = Depends(get_router_trainer),
) -> TrainingStatusResponse:
    """Obtiene el estado de un entrenamiento."""

    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.get_training_status(training_id, identity_type_id, headers)
        return TrainingStatusResponse(**result)
    except BackendTrainerPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendTrainerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@app.get("/trainer/models", response_model=ModelListResponse)
def list_models(
    id_organization: int | None = None,
    id_project: int | None = None,
    identity_type_id: int | None = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
    client_app: str = Depends(get_client_app),
    router: BackendTrainerRouter = Depends(get_router_trainer),
) -> ModelListResponse:
    """Lista modelos entrenados."""

    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.list_models(id_organization, id_project, identity_type_id, headers)
        return ModelListResponse(**result)
    except BackendTrainerPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendTrainerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@app.get("/trainer/models/{model_id}/metrics", response_model=ModelMetricsResponse)
def get_model_metrics(
    model_id: int,
    identity_type_id: int | None = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
    client_app: str = Depends(get_client_app),
    router: BackendTrainerRouter = Depends(get_router_trainer),
) -> ModelMetricsResponse:
    """Obtiene métricas de un modelo."""

    headers = _build_permission_headers(authorization, session_token, client_app)
    try:
        result = router.get_model_metrics(model_id, identity_type_id, headers)
        return ModelMetricsResponse(**result)
    except BackendTrainerPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except BackendTrainerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@app.get("/trainer/permissions", response_model=PermissionsResponse)
def get_training_permissions(
    identity_type_id: int,
    router: BackendTrainerRouter = Depends(get_router_trainer),
) -> PermissionsResponse:
    """Obtiene permisos de entrenamiento para un rol."""

    try:
        result = router.get_training_permissions(identity_type_id)
        return PermissionsResponse(**result)
    except BackendTrainerBusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


# ============================================================================
# Análisis de Documentación
# ============================================================================


@app.post("/trainer/documentacion", response_model=DocumentacionResponse)
def recibir_documentacion(
    request: DocumentacionRequest,
    client_app: str = Depends(get_client_app),
) -> DocumentacionResponse:
    """Recibe una solicitud de análisis de documentación desde el backoffice.

    Devuelve un ACK inmediato y lanza el procesamiento real en un thread de background.
    """

    import threading
    from datetime import datetime, timezone

    logger = logging.getLogger("trainer_api")
    logger.info(
        "[DOCUMENTACION] Solicitud recibida: job_id=%s org=%s prj=%s ver=%s job='%s' template='%s'",
        request.id_job,
        request.id_organizacion,
        request.id_proyecto,
        request.id_version,
        request.nombre_job,
        request.template_nombre,
    )
    logger.info(
        "[DOCUMENTACION] Prompt final (%d chars): %s...",
        len(request.prompt_final),
        request.prompt_final[:200] if request.prompt_final else "(vacío)",
    )

    # Lanzar procesamiento en background thread
    from documentacion_service import process_documentacion

    thread = threading.Thread(
        target=process_documentacion,
        args=(request.model_dump(),),
        daemon=True,
        name=f"doc-analysis-job-{request.id_job}",
    )
    thread.start()
    logger.info("[DOCUMENTACION] Thread background lanzado para job_id=%s", request.id_job)

    received_at = datetime.now(timezone.utc).isoformat()

    return DocumentacionResponse(
        success=True,
        message=(
            f"Solicitud de análisis recibida para org={request.id_organizacion}, "
            f"prj={request.id_proyecto}, ver={request.id_version}"
        ),
        received_at=received_at,
    )


# ============================================================================
# Análisis de Metadatos de Ficheros (flujo paralelo a documentación)
# ============================================================================


@app.post("/trainer/metadatos", response_model=MetadatosResponse)
def recibir_metadatos(
    request: MetadatosRequest,
    client_app: str = Depends(get_client_app),
) -> MetadatosResponse:
    """Recibe una solicitud de análisis de metadatos desde el backoffice.

    Devuelve un ACK inmediato y lanza el procesamiento real en un thread de background.
    Flujo paralelo e independiente al de documentación.
    """

    import threading
    from datetime import datetime, timezone

    logger = logging.getLogger("trainer_api")
    logger.info(
        "[METADATOS] Solicitud recibida: job_id=%s org=%s prj=%s ver=%s job='%s' template='%s'",
        request.id_job,
        request.id_organizacion,
        request.id_proyecto,
        request.id_version,
        request.nombre_job,
        request.template_nombre,
    )
    logger.info(
        "[METADATOS] Prompt final (%d chars): %s...",
        len(request.prompt_final),
        request.prompt_final[:200] if request.prompt_final else "(vacío)",
    )

    # Lanzar procesamiento en background thread
    from metadatos_service import process_metadatos

    thread = threading.Thread(
        target=process_metadatos,
        args=(request.model_dump(),),
        daemon=True,
        name=f"metadata-analysis-job-{request.id_job}",
    )
    thread.start()
    logger.info("[METADATOS] Thread background lanzado para job_id=%s", request.id_job)

    received_at = datetime.now(timezone.utc).isoformat()

    return MetadatosResponse(
        success=True,
        message=(
            f"Solicitud de análisis de metadatos recibida para org={request.id_organizacion}, "
            f"prj={request.id_proyecto}, ver={request.id_version}"
        ),
        received_at=received_at,
    )
