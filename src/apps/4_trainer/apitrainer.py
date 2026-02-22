"""Capa de API para el backend IA (trainer)."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated, Any, AsyncIterator

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import FileResponse
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

# Cargar chroma_server
_chroma_server_path = Path(__file__).resolve().parent / "chroma_server.py"
_chroma_server = _load_trainer_module("chroma_server", _chroma_server_path)

# Cargar módulos del proceso de entrenamiento RAG
_entrenamiento_service_path = Path(__file__).resolve().parent / "entrenamiento_service.py"
_load_trainer_module("entrenamiento_service", _entrenamiento_service_path)

_broker_client_path = Path(__file__).resolve().parent / "broker_client.py"
_load_trainer_module("broker_client", _broker_client_path)

_keras_embeddings_path = Path(__file__).resolve().parent / "keras_embeddings.py"
_load_trainer_module("keras_embeddings", _keras_embeddings_path)

# Cargar módulo de análisis de documentación
_documentacion_service_path = Path(__file__).resolve().parent / "documentacion_service.py"
_load_trainer_module("documentacion_service", _documentacion_service_path)

# Cargar módulo de entrenamiento autónomo
_autonomous_training_service_path = Path(__file__).resolve().parent / "autonomous_training_service.py"
_load_trainer_module("autonomous_training_service", _autonomous_training_service_path)

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


class EntrenamientoRequest(BaseModel):
    """Payload para solicitud de entrenamiento inicial."""

    id_organizacion: int
    id_proyecto: int
    id_version: int
    pat_version: str = ""
    # Parámetros opcionales de entrenamiento (enviados desde modal del backoffice)
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


class EntrenamientoResponse(BaseModel):
    """Respuesta de solicitud de entrenamiento (ACK)."""

    success: bool
    message: str = ""
    received_at: str = ""
    id_entrenamiento: int = 0  # ID del entrenamiento creado en BD
    collection_name: str = ""  # Nombre de la colección en ChromaDB
    numero_secuencia: int = 0  # Número de secuencia del entrenamiento


class AutonomousTrainingRequest(BaseModel):
    """Payload para solicitud de entrenamiento autónomo (RAG + LoRA + GGUF)."""

    id_organizacion: int
    id_proyecto: int
    id_version: int
    id_entrenamiento: int  # ID del entrenamiento RAG previo (con ChromaDB)
    pat_version: str = ""
    collection_name: str = ""  # Nombre de colección ChromaDB con chunks


class AutonomousTrainingResponse(BaseModel):
    """Respuesta de solicitud de entrenamiento autónomo (ACK)."""

    success: bool
    message: str = ""
    received_at: str = ""
    id_entrenamiento: int = 0  # ID del entrenamiento (mismo que el RAG previo)
    training_mode: str = ""  # simulation, test o production


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

    # Inicializar servidor ChromaDB (base de datos vectorial)
    try:
        settings = _chroma_server.get_chroma_settings()
        logging.info(
            "[CHROMADB] Iniciando servidor ChromaDB en puerto %s (persist=%s)...",
            settings["port"],
            settings["persist_directory"],
        )
        chroma_ok = _chroma_server.start_chroma_server()
        if chroma_ok:
            logging.info("[CHROMADB] Servidor ChromaDB arrancado correctamente")
        else:
            logging.warning("[CHROMADB] No se pudo arrancar el servidor ChromaDB")
    except Exception as e:
        logging.warning(f"[CHROMADB] Error inicializando ChromaDB: {e}")

    yield

    # Detener servidor ChromaDB al cerrar el trainer
    try:
        logging.info("[CHROMADB] Deteniendo servidor ChromaDB...")
        _chroma_server.stop_chroma_server()
        logging.info("[CHROMADB] Servidor ChromaDB detenido")
    except Exception as e:
        logging.warning(f"[CHROMADB] Error deteniendo ChromaDB: {e}")


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


class ChromaHealthResponse(BaseModel):
    """Respuesta del health check de ChromaDB."""

    running: bool
    host: str = ""
    port: int = 0
    persist_directory: str = ""
    collection_name: str = ""
    pid: int | None = None
    authenticated: bool = False
    heartbeat: int | None = None
    collections: list[str] = Field(default_factory=list)
    version: str = ""
    error: str = ""


@app.get("/trainer/chroma/health", response_model=ChromaHealthResponse)
def chroma_health_check() -> ChromaHealthResponse:
    """Health check del servidor ChromaDB gestionado por el trainer."""

    try:
        info = _chroma_server.get_server_info()
        return ChromaHealthResponse(**info)
    except Exception as exc:
        return ChromaHealthResponse(
            running=False,
            error=str(exc),
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


# ============================================================================
# Entrenamientos - Solicitud de entrenamiento inicial
# ============================================================================


@app.post("/trainer/entrenamientos", response_model=EntrenamientoResponse)
def recibir_entrenamiento(
    request: EntrenamientoRequest,
    client_app: str = Depends(get_client_app),
) -> EntrenamientoResponse:
    """Recibe una solicitud de entrenamiento inicial desde el backoffice.

    Devuelve un ACK inmediato y lanza el proceso de entrenamiento RAG
    completo en un thread de background (5 fases: recepcion, validacion,
    preparacion, configuracion, entrenamiento).

    Flujo del thread:
        1. Registra entrenamiento en BD via Broker → Backend Core → MariaDB
        2. Escanea y clasifica archivos de la versión
        3. Carga documentos (LangChain), chunking, embeddings (Keras/TF-Hub)
        4. Inserta vectores en ChromaDB
        5. Genera Modelfile y registra modelo en Ollama
    """
    import threading
    from datetime import datetime, timezone

    logger = logging.getLogger("trainer_api")
    logger.info(
        "[ENTRENAMIENTO] Solicitud recibida: org=%s prj=%s ver=%s pat=%s client=%s",
        request.id_organizacion,
        request.id_proyecto,
        request.id_version,
        request.pat_version,
        client_app,
    )

    # PASO 1: Registrar entrenamiento en BD ANTES de lanzar el background thread
    from broker_client import TrainerBrokerClient

    broker_client = TrainerBrokerClient()
    payload_dict = request.model_dump()

    # Construir payload de registro
    register_payload = {
        "id_organizacion": payload_dict["id_organizacion"],
        "id_proyecto": payload_dict["id_proyecto"],
        "id_version": payload_dict["id_version"],
        "pat_version": payload_dict["pat_version"],
        "entrenamiento_inicial": True,
        "reentrenamiento": False,
        **{k: v for k, v in payload_dict.items() if k not in [
            "id_organizacion", "id_proyecto", "id_version", "pat_version"
        ]}
    }

    logger.info("[ENTRENAMIENTO] Registrando en BD via Broker...")
    try:
        result = broker_client.register_entrenamiento(register_payload)

        if not result.get("success"):
            error_msg = result.get("message", "Error desconocido al registrar")
            logger.error("[ENTRENAMIENTO] Error en registro: %s", error_msg)
            return EntrenamientoResponse(
                success=False,
                message=f"Error al registrar entrenamiento: {error_msg}",
                received_at=datetime.now(timezone.utc).isoformat(),
            )

        id_entrenamiento = result["id_entrenamiento"]
        collection_name = result["collection_name"]
        numero_secuencia = result["numero_secuencia"]

        logger.info(
            "[ENTRENAMIENTO] Registrado: id=%s, collection=%s, seq=%s",
            id_entrenamiento, collection_name, numero_secuencia
        )
    except Exception as exc:
        logger.error("[ENTRENAMIENTO] Excepción al registrar: %s", exc)
        return EntrenamientoResponse(
            success=False,
            message=f"Excepción al registrar: {str(exc)}",
            received_at=datetime.now(timezone.utc).isoformat(),
        )

    # PASO 2: Lanzar procesamiento en background thread CON el id_entrenamiento
    from entrenamiento_service import process_entrenamiento_with_id

    # Agregar el ID al payload
    payload_with_id = {
        **payload_dict,
        "id_entrenamiento": id_entrenamiento,
        "collection_name": collection_name,
        "numero_secuencia": numero_secuencia,
    }

    thread = threading.Thread(
        target=process_entrenamiento_with_id,
        args=(payload_with_id,),
        daemon=True,
        name=(
            f"training-org{request.id_organizacion}"
            f"-prj{request.id_proyecto}"
            f"-ver{request.id_version}-ent{id_entrenamiento}"
        ),
    )
    thread.start()
    logger.info(
        "[ENTRENAMIENTO] Thread background lanzado: %s (id=%s)",
        thread.name, id_entrenamiento,
    )

    received_at = datetime.now(timezone.utc).isoformat()

    return EntrenamientoResponse(
        success=True,
        message=(
            f"Entrenamiento {id_entrenamiento} registrado para "
            f"org={request.id_organizacion}, prj={request.id_proyecto}, ver={request.id_version}"
        ),
        received_at=received_at,
        id_entrenamiento=id_entrenamiento,
        collection_name=collection_name,
        numero_secuencia=numero_secuencia,
    )


@app.post("/trainer/entrenamientos/autonomous", response_model=AutonomousTrainingResponse)
def recibir_entrenamiento_autonomo(
    request: AutonomousTrainingRequest,
    client_app: str = Depends(get_client_app),
) -> AutonomousTrainingResponse:
    """Recibe una solicitud de entrenamiento autónomo desde el backoffice.

    El entrenamiento autónomo ejecuta las fases 6-9:
        Fase 6: Generación de Dataset desde ChromaDB
        Fases 7-8: Fine-tuning con LoRA (solo en test/production)
        Fase 9: Exportación a GGUF y empaquetado (solo en test/production)

    Requisitos previos:
        - Debe existir un entrenamiento RAG completado (fases 1-5)
        - La colección ChromaDB debe contener los chunks generados

    Resultado:
        - simulation: Solo dataset JSONL
        - test/production: Paquete ZIP con modelo GGUF + Modelfile + README

    Devuelve un ACK inmediato y lanza el proceso en background thread.
    """
    import threading
    from datetime import datetime, timezone

    logger = logging.getLogger("trainer_api")
    logger.info(
        "[AUTONOMOUS] Solicitud recibida: org=%s prj=%s ver=%s ent=%s collection=%s client=%s",
        request.id_organizacion,
        request.id_proyecto,
        request.id_version,
        request.id_entrenamiento,
        request.collection_name,
        client_app,
    )

    # Leer training_mode desde .envglobal
    from autonomous_training_service import _get_training_mode

    training_mode = _get_training_mode()

    logger.info(f"[AUTONOMOUS] training_mode: {training_mode}")

    # Construir payload para background thread
    payload_dict = {
        "id_organizacion": request.id_organizacion,
        "id_proyecto": request.id_proyecto,
        "id_version": request.id_version,
        "id_entrenamiento": request.id_entrenamiento,
        "pat_version": request.pat_version,
        "collection_name": request.collection_name,
    }

    # PASO: Lanzar procesamiento en background thread
    from autonomous_training_service import process_autonomous_training

    thread = threading.Thread(
        target=process_autonomous_training,
        args=(payload_dict,),
        daemon=True,
        name=(
            f"autonomous-org{request.id_organizacion}"
            f"-prj{request.id_proyecto}"
            f"-ver{request.id_version}-ent{request.id_entrenamiento}"
        ),
    )
    thread.start()
    logger.info(
        "[AUTONOMOUS] Thread background lanzado: %s (id=%s, mode=%s)",
        thread.name, request.id_entrenamiento, training_mode,
    )

    received_at = datetime.now(timezone.utc).isoformat()

    return AutonomousTrainingResponse(
        success=True,
        message=(
            f"Entrenamiento autónomo iniciado para ent={request.id_entrenamiento} "
            f"(modo: {training_mode}). "
            f"Se procesarán las fases 6-9 en background."
        ),
        received_at=received_at,
        id_entrenamiento=request.id_entrenamiento,
        training_mode=training_mode,
    )


@app.get("/trainer/entrenamientos/{id_entrenamiento}/autonomous/progress")
def consultar_progreso_autonomo(
    id_entrenamiento: int,
    client_app: str = Depends(get_client_app),
) -> dict[str, Any]:
    """Consulta el progreso del entrenamiento autónomo (fases 6-9).

    Redirige la consulta via Broker → Backend Core → MariaDB.

    Args:
        id_entrenamiento: ID del entrenamiento autónomo

    Returns:
        Diccionario con training_mode, subphases y summary
    """
    logger = logging.getLogger("trainer_api")
    logger.info(
        "[AUTONOMOUS PROGRESS] Consultando progreso para ent=%s client=%s",
        id_entrenamiento,
        client_app,
    )

    try:
        from broker_client import TrainerBrokerClient

        broker = TrainerBrokerClient()
        result = broker._request(
            "GET",
            f"/training/entrenamientos/{id_entrenamiento}/autonomous/progress",
        )

        logger.info(
            "[AUTONOMOUS PROGRESS] Progreso obtenido via broker para ent=%s",
            id_entrenamiento,
        )

        return result

    except Exception as exc:
        logger.error(
            "[AUTONOMOUS PROGRESS] Error consultando progreso: %s",
            exc,
            exc_info=True,
        )
        return {
            "success": False,
            "error": str(exc),
            "data": {
                "training_mode": "unknown",
                "subphases": [],
                "summary": {
                    "total": 0,
                    "completed": 0,
                    "in_progress": 0,
                    "failed": 0,
                    "progress_percent": 0,
                },
            },
        }


@app.get("/trainer/entrenamientos/{id_entrenamiento}/autonomous/package")
def descargar_paquete_autonomo(
    id_entrenamiento: int,
    client_app: str = Depends(get_client_app),
) -> FileResponse:
    """Descarga el paquete ZIP del modelo autónomo generado.

    Consulta package_path via Broker → Backend Core → MariaDB y luego
    sirve el archivo local.

    Args:
        id_entrenamiento: ID del entrenamiento autónomo

    Returns:
        FileResponse con el archivo ZIP del modelo
    """
    logger = logging.getLogger("trainer_api")
    logger.info(
        "[AUTONOMOUS DOWNLOAD] Descargando paquete para ent=%s client=%s",
        id_entrenamiento,
        client_app,
    )

    try:
        from broker_client import TrainerBrokerClient

        broker = TrainerBrokerClient()

        # Consultar progreso para obtener package_path via API chain
        progress_result = broker._request(
            "GET",
            f"/training/entrenamientos/{id_entrenamiento}/autonomous/progress",
        )

        # Obtener packages list para el id_entrenamiento
        packages_result = broker._request(
            "GET",
            f"/training/autonomous/packages?id_entrenamiento={id_entrenamiento}",
        )

        # Buscar package_path en los resultados
        package_path = None
        package_size_mb = 0

        packages = packages_result.get("packages", [])
        for pkg in packages:
            if pkg.get("id_entrenamiento") == id_entrenamiento:
                package_path = pkg.get("package_path")
                package_size_mb = pkg.get("package_size_mb", 0)
                break

        if not package_path:
            logger.error(
                "[AUTONOMOUS DOWNLOAD] No se encontró paquete para ent=%s",
                id_entrenamiento,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró paquete para entrenamiento {id_entrenamiento}",
            )

        # Verificar que el archivo existe localmente
        from pathlib import Path
        package_file = Path(package_path)

        if not package_file.exists():
            logger.error(
                "[AUTONOMOUS DOWNLOAD] Archivo no existe: %s",
                package_path,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El archivo del paquete no existe en el servidor",
            )

        logger.info(
            "[AUTONOMOUS DOWNLOAD] Enviando paquete: %s (%.2f MB)",
            package_file.name,
            package_size_mb,
        )

        # Devolver archivo para descarga
        return FileResponse(
            path=str(package_file),
            media_type="application/zip",
            filename=package_file.name,
            headers={
                "Content-Disposition": f'attachment; filename="{package_file.name}"',
            },
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "[AUTONOMOUS DOWNLOAD] Error descargando paquete: %s",
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error descargando paquete: {str(exc)}",
        ) from exc


@app.get("/trainer/entrenamientos/autonomous/packages")
def listar_paquetes_autonomos(
    id_organizacion: int | None = None,
    id_proyecto: int | None = None,
    id_version: int | None = None,
    client_app: str = Depends(get_client_app),
) -> dict[str, Any]:
    """Lista los paquetes autónomos disponibles para descargar.

    Redirige la consulta via Broker → Backend Core → MariaDB.

    Args:
        id_organizacion: Filtrar por organización (opcional)
        id_proyecto: Filtrar por proyecto (opcional)
        id_version: Filtrar por versión (opcional)

    Returns:
        Diccionario con success y lista de paquetes
    """
    logger = logging.getLogger("trainer_api")
    logger.info(
        "[PACKAGES LIST] Listando paquetes org=%s prj=%s ver=%s client=%s",
        id_organizacion,
        id_proyecto,
        id_version,
        client_app,
    )

    try:
        from broker_client import TrainerBrokerClient

        broker = TrainerBrokerClient()

        # Construir query string
        params = []
        if id_organizacion is not None:
            params.append(f"id_organizacion={id_organizacion}")
        if id_proyecto is not None:
            params.append(f"id_proyecto={id_proyecto}")
        if id_version is not None:
            params.append(f"id_version={id_version}")

        query_string = "&".join(params)
        path = "/training/entrenamientos/autonomous/packages"
        if query_string:
            path = f"{path}?{query_string}"

        result = broker._request("GET", path)

        # Enriquecer con información local de archivos
        packages = result.get("packages", [])
        for pkg in packages:
            package_path = pkg.get("package_path")
            if package_path:
                from pathlib import Path
                package_file = Path(package_path)
                pkg["package_filename"] = package_file.name
                pkg["package_exists"] = package_file.exists()
            else:
                pkg["package_filename"] = ""
                pkg["package_exists"] = False

        logger.info(
            "[PACKAGES LIST] Encontrados %s paquetes",
            len(packages),
        )

        return result

    except Exception as exc:
        logger.error(
            "[PACKAGES LIST] Error listando paquetes: %s",
            exc,
            exc_info=True,
        )
        return {
            "success": False,
            "error": str(exc),
            "packages": [],
            "total": 0,
        }
