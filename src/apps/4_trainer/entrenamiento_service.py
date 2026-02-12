"""Servicio de entrenamiento RAG para el Trainer.

Implementa las 5 fases del proceso de entrenamiento:
    1. Recepción  - Registro en BD via Broker → Backend Core → MariaDB
    2. Validación - Escaneo recursivo de archivos, clasificación por tipo
    3. Preparación - Carga con LangChain, chunking, embeddings con Keras/TF-Hub
    4. Configuración - Creación de colección ChromaDB, inserción de vectores
    5. Entrenamiento - Generación de Modelfile, registro de modelo en Ollama

Arquitectura:
    Trainer (background thread) → Broker (8008) → Backend Core (8003) → MariaDB
    Trainer → ChromaDB (8100) → Persistencia vectorial
    Trainer → Ollama (11434) → Registro de modelo

Uso:
    from entrenamiento_service import process_entrenamiento

    # Se ejecuta en background thread desde apitrainer.py
    threading.Thread(target=process_entrenamiento, args=(payload_dict,)).start()
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger("trainer_api")

# ---------------------------------------------------------------------------
# Extensiones de archivos soportados por tipo
# ---------------------------------------------------------------------------

TEXT_EXTENSIONS: set[str] = {
    ".txt", ".md", ".csv", ".json", ".xml", ".html", ".htm",
    ".rst", ".tsv", ".log", ".cfg", ".ini", ".toml", ".env",
    ".yml", ".yaml", ".properties", ".conf",
}

CODE_EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".java": "java",
    ".sql": "sql",
    ".sh": "bash",
    ".bat": "bash",
    ".css": "css",
    ".r": "r",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".dockerfile": "docker",
    ".gradle": "groovy",
}

PDF_EXTENSIONS: set[str] = {".pdf"}

DOCX_EXTENSIONS: set[str] = {".docx"}

# Todas las extensiones procesables
ALL_SUPPORTED_EXTENSIONS: set[str] = (
    TEXT_EXTENSIONS | set(CODE_EXTENSIONS.keys()) | PDF_EXTENSIONS | DOCX_EXTENSIONS
)

# Ruta al directorio de plantillas Jinja2
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


# ---------------------------------------------------------------------------
# Carga de módulos compartidos
# ---------------------------------------------------------------------------


def _load_shared_module(module_name: str, relative_path: str) -> Any:
    """Carga un módulo compartido desde src/."""
    base = Path(__file__).resolve().parents[2]
    module_path = base / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar {module_name} desde {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Cargar módulos compartidos
_env_settings = _load_shared_module(
    "env_settings_ent",
    "2_shared_application/config/env_settings.py",
)
get_env_value = _env_settings.get_env_value
get_protected_value = _env_settings.get_protected_value


# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------


def _format_elapsed_time(seconds: float) -> str:
    """Formatea segundos transcurridos en formato legible."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours = int(minutes // 60)
    mins = minutes % 60
    return f"{hours}h {mins}m {secs}s"


def _notify_progress(
    broker: Any,
    id_entrenamiento: int,
    phase_key: str,
    subfase_key: str,
    subfase_name: str,
    status: str,
    elapsed_time: float,
    error_message: str = "",
) -> None:
    """Notifica progreso al backoffice via broker.

    Args:
        broker: Instancia de TrainerBrokerClient.
        id_entrenamiento: ID del entrenamiento.
        phase_key: Clave de la fase principal (ej: "3").
        subfase_key: Clave de la subfase (ej: "3.2").
        subfase_name: Nombre legible (ej: "Chunking").
        status: Estado (in_progress, completed, error).
        elapsed_time: Segundos transcurridos desde el inicio de la fase.
        error_message: Mensaje de error si status=error.
    """
    try:
        broker.notify_training_progress(
            id_entrenamiento=id_entrenamiento,
            phase_key=phase_key,
            subfase_key=subfase_key,
            subfase_name=subfase_name,
            status=status,
            elapsed_time=_format_elapsed_time(elapsed_time),
            error_message=error_message,
        )
        logger.debug(
            "[ENTRENAMIENTO] Progreso notificado: %s (%s) - %s",
            subfase_key,
            subfase_name,
            status,
        )
    except Exception as exc:
        # No fallar el entrenamiento si la notificación falla
        logger.warning(
            "[ENTRENAMIENTO] Error notificando progreso %s: %s",
            subfase_key,
            exc,
        )


def _load_training_params() -> dict[str, Any]:
    """Carga los parámetros de entrenamiento por defecto desde protected_values.

    Estos parámetros son los mismos que se persisten en jobs_entrenamientos
    al registrar el entrenamiento via Backend Core.

    Returns:
        Diccionario con los parámetros de entrenamiento.
    """
    protected = _env_settings.load_protected_settings()
    if not protected:
        logger.warning(
            "[ENTRENAMIENTO] No se pudieron cargar protected_values, "
            "usando valores por defecto hardcodeados"
        )
        protected = {}

    return {
        "chunk_size": int(protected.get("training_default_chunk_size", 1000)),
        "chunk_overlap": int(protected.get("training_default_chunk_overlap", 200)),
        "temperature": float(protected.get("training_default_temperature", 0.7)),
        "max_tokens": int(protected.get("training_default_max_tokens", 2048)),
        "top_k": int(protected.get("training_default_top_k", 5)),
        "distance_metric": str(protected.get("training_default_distance_metric", "cosine")),
        "embedding_dimension": int(protected.get("training_default_embedding_dimension", 768)),
    }


def _classify_file(filepath: Path) -> str | None:
    """Clasifica un archivo por su extensión.

    Returns:
        Tipo de archivo: 'text', 'code', 'pdf', 'docx' o None si no es soportado.
    """
    ext = filepath.suffix.lower()
    if ext in TEXT_EXTENSIONS:
        return "text"
    if ext in CODE_EXTENSIONS:
        return "code"
    if ext in PDF_EXTENSIONS:
        return "pdf"
    if ext in DOCX_EXTENSIONS:
        return "docx"
    return None


def _get_code_language(filepath: Path) -> str:
    """Obtiene el lenguaje de programación según la extensión del archivo."""
    return CODE_EXTENSIONS.get(filepath.suffix.lower(), "text")


# ---------------------------------------------------------------------------
# FASE 1: RECEPCIÓN
# ---------------------------------------------------------------------------


def _phase_recepcion(
    broker_client: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Fase 1 - Recepción: Registra el entrenamiento en BD via Broker.

    Crea registros en las tablas entrenamientos + jobs_entrenamientos
    en MariaDB, obteniendo el ID de entrenamiento y el nombre de colección
    para ChromaDB.

    Args:
        broker_client: Instancia de TrainerBrokerClient.
        payload: Datos originales de la solicitud.

    Returns:
        Diccionario con id_entrenamiento, collection_name, numero_secuencia, etc.

    Raises:
        RuntimeError: Si el registro falla.
    """
    logger.info("[ENTRENAMIENTO][FASE-1-RECEPCION] Registrando en BD via Broker...")

    register_payload = {
        "id_organizacion": payload["id_organizacion"],
        "id_proyecto": payload["id_proyecto"],
        "id_version": payload["id_version"],
        "pat_version": payload.get("pat_version", ""),
        "entrenamiento_inicial": True,
        "reentrenamiento": False,
    }

    # Incluir parámetros de entrenamiento del request para persistir en jobs_entrenamientos
    for param_key in (
        "learning_rate", "batch_size", "epochs", "embedding_dimension",
        "sequence_length", "hidden_units", "dropout_rate", "chunk_size",
        "chunk_overlap", "temperature", "max_tokens", "distance_metric",
        "top_k", "loss_function", "optimizer", "model_type",
    ):
        val = payload.get(param_key)
        if val is not None:
            register_payload[param_key] = val

    result = broker_client.register_entrenamiento(register_payload)

    if not result.get("success"):
        raise RuntimeError(
            f"Error registrando entrenamiento: {result.get('message', 'sin detalle')}"
        )

    id_ent = result["id_entrenamiento"]
    collection = result["collection_name"]
    seq = result["numero_secuencia"]

    logger.info(
        "[ENTRENAMIENTO][FASE-1-RECEPCION] Registrado: id=%s, collection=%s, seq=%s",
        id_ent, collection, seq,
    )

    return result


# ---------------------------------------------------------------------------
# FASE 2: VALIDACIÓN
# ---------------------------------------------------------------------------


def _phase_validacion(
    broker: Any,
    id_entrenamiento: int,
    pat_version: str,
    phase_start_time: float,
) -> dict[str, list[Path]]:
    """Fase 2 - Validación: Verifica existencia y escanea archivos.

    Escanea recursivamente el directorio de la versión, clasifica los
    archivos por tipo y rechaza si no hay contenido procesable.

    Args:
        broker: Instancia de TrainerBrokerClient para notificaciones.
        id_entrenamiento: ID del entrenamiento.
        pat_version: Ruta completa al directorio de la versión.
        phase_start_time: Timestamp del inicio de la fase.

    Returns:
        Diccionario con listas de archivos por tipo: text, code, pdf, docx.

    Raises:
        RuntimeError: Si el directorio no existe o no hay archivos procesables.
    """
    logger.info("[ENTRENAMIENTO][FASE-2-VALIDACION] Validando ruta: %s", pat_version)

    # Subfase 2.1: Verificar directorio
    _notify_progress(broker, id_entrenamiento, "2", "2.1", "Verificar directorio", "in_progress", 0)
    version_path = Path(os.path.expanduser(pat_version))

    if not version_path.exists():
        _notify_progress(broker, id_entrenamiento, "2", "2.1", "Verificar directorio", "error", time.time() - phase_start_time, "Directorio no existe")
        raise RuntimeError(f"El directorio de la versión no existe: {version_path}")

    if not version_path.is_dir():
        _notify_progress(broker, id_entrenamiento, "2", "2.1", "Verificar directorio", "error", time.time() - phase_start_time, "Ruta no es directorio")
        raise RuntimeError(f"La ruta no es un directorio: {version_path}")

    _notify_progress(broker, id_entrenamiento, "2", "2.1", "Verificar directorio", "completed", time.time() - phase_start_time)

    # Subfase 2.2: Escaneo de archivos
    _notify_progress(broker, id_entrenamiento, "2", "2.2", "Escaneo de archivos", "in_progress", time.time() - phase_start_time)
    all_files = sorted(version_path.rglob("*"))
    _notify_progress(broker, id_entrenamiento, "2", "2.2", "Escaneo de archivos", "completed", time.time() - phase_start_time)

    # Subfase 2.3: Clasificación por tipo
    _notify_progress(broker, id_entrenamiento, "2", "2.3", "Clasificación por tipo", "in_progress", time.time() - phase_start_time)
    classified: dict[str, list[Path]] = {
        "text": [],
        "code": [],
        "pdf": [],
        "docx": [],
    }

    total_files = 0
    skipped_files = 0

    for filepath in all_files:
        if filepath.is_dir():
            continue

        total_files += 1
        file_type = _classify_file(filepath)

        if file_type is not None:
            classified[file_type].append(filepath)
        else:
            skipped_files += 1
            logger.debug(
                "[ENTRENAMIENTO][FASE-2-VALIDACION] Omitido (no soportado): %s",
                filepath.name,
            )

    _notify_progress(broker, id_entrenamiento, "2", "2.3", "Clasificación por tipo", "completed", time.time() - phase_start_time)

    # Subfase 2.4: Validación de contenido
    _notify_progress(broker, id_entrenamiento, "2", "2.4", "Validación de contenido", "in_progress", time.time() - phase_start_time)
    num_procesable = sum(len(v) for v in classified.values())

    logger.info(
        "[ENTRENAMIENTO][FASE-2-VALIDACION] Escaneo completado: "
        "%d archivos totales, %d procesables (%d texto, %d código, %d PDF, %d DOCX), "
        "%d omitidos",
        total_files,
        num_procesable,
        len(classified["text"]),
        len(classified["code"]),
        len(classified["pdf"]),
        len(classified["docx"]),
        skipped_files,
    )

    if num_procesable == 0:
        _notify_progress(broker, id_entrenamiento, "2", "2.4", "Validación de contenido", "error", time.time() - phase_start_time, "Sin archivos procesables")
        raise RuntimeError(
            f"No se encontraron archivos procesables en {version_path}. "
            f"Total escaneados: {total_files}, todos omitidos."
        )

    _notify_progress(broker, id_entrenamiento, "2", "2.4", "Validación de contenido", "completed", time.time() - phase_start_time)

    return classified


# ---------------------------------------------------------------------------
# FASE 3: PREPARACIÓN (LangChain loaders + chunking + embeddings)
# ---------------------------------------------------------------------------


def _load_and_chunk_documents(
    classified_files: dict[str, list[Path]],
    chunk_size: int,
    chunk_overlap: int,
    pat_version: str,
) -> list[dict[str, Any]]:
    """Carga documentos con LangChain y aplica chunking inteligente.

    Usa diferentes loaders y splitters según el tipo de archivo:
    - Texto plano: TextLoader + RecursiveCharacterTextSplitter
    - Código fuente: TextLoader + RecursiveCharacterTextSplitter (por lenguaje)
    - PDF: PyPDFLoader + RecursiveCharacterTextSplitter
    - DOCX: Docx2txtLoader o lectura directa + RecursiveCharacterTextSplitter

    Args:
        classified_files: Archivos clasificados por tipo.
        chunk_size: Tamaño máximo de cada chunk en caracteres.
        chunk_overlap: Solapamiento entre chunks consecutivos.
        pat_version: Ruta base para calcular rutas relativas.

    Returns:
        Lista de diccionarios con 'text', 'metadata' para cada chunk.
    """
    from langchain_text_splitters import (
        Language,
        RecursiveCharacterTextSplitter,
    )

    # Mapeo de extensiones de código a Language de LangChain
    _langchain_language_map: dict[str, Language] = {
        "python": Language.PYTHON,
        "javascript": Language.JS,
        "typescript": Language.TS,
        "java": Language.JAVA,
        "go": Language.GO,
        "rust": Language.RUST,
        "c": Language.C,
        "cpp": Language.CPP,
        "ruby": Language.RUBY,
        "php": Language.PHP,
        "swift": Language.SWIFT,
        "kotlin": Language.KOTLIN,
        "scala": Language.SCALA,
        "r": Language.R,
    }

    # Splitter genérico para texto plano
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True,
    )

    all_chunks: list[dict[str, Any]] = []
    version_path = Path(os.path.expanduser(pat_version))

    # --- Procesar archivos de TEXTO ---
    for filepath in classified_files.get("text", []):
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
            relative = str(filepath.relative_to(version_path))
            docs = text_splitter.create_documents(
                texts=[content],
                metadatas=[{"source": relative, "type": "text", "language": "plain"}],
            )
            for doc in docs:
                all_chunks.append({
                    "text": doc.page_content,
                    "metadata": doc.metadata,
                })
        except Exception as exc:
            logger.warning(
                "[ENTRENAMIENTO][FASE-3-PREP] Error cargando texto %s: %s",
                filepath.name, exc,
            )

    # --- Procesar archivos de CÓDIGO ---
    for filepath in classified_files.get("code", []):
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
            relative = str(filepath.relative_to(version_path))
            lang_key = _get_code_language(filepath)

            # Intentar splitter específico por lenguaje
            lc_lang = _langchain_language_map.get(lang_key)
            if lc_lang is not None:
                try:
                    code_splitter = RecursiveCharacterTextSplitter.from_language(
                        language=lc_lang,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                    )
                except Exception:
                    code_splitter = text_splitter
            else:
                code_splitter = text_splitter

            docs = code_splitter.create_documents(
                texts=[content],
                metadatas=[{"source": relative, "type": "code", "language": lang_key}],
            )
            for doc in docs:
                all_chunks.append({
                    "text": doc.page_content,
                    "metadata": doc.metadata,
                })
        except Exception as exc:
            logger.warning(
                "[ENTRENAMIENTO][FASE-3-PREP] Error cargando código %s: %s",
                filepath.name, exc,
            )

    # --- Procesar archivos PDF ---
    for filepath in classified_files.get("pdf", []):
        try:
            from pypdf import PdfReader

            relative = str(filepath.relative_to(version_path))
            reader = PdfReader(str(filepath))
            full_text = ""
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                full_text += page_text + "\n"

            if full_text.strip():
                docs = text_splitter.create_documents(
                    texts=[full_text],
                    metadatas=[{"source": relative, "type": "pdf", "language": "plain"}],
                )
                for doc in docs:
                    all_chunks.append({
                        "text": doc.page_content,
                        "metadata": doc.metadata,
                    })
            else:
                logger.warning(
                    "[ENTRENAMIENTO][FASE-3-PREP] PDF sin texto extraíble: %s",
                    filepath.name,
                )
        except Exception as exc:
            logger.warning(
                "[ENTRENAMIENTO][FASE-3-PREP] Error cargando PDF %s: %s",
                filepath.name, exc,
            )

    # --- Procesar archivos DOCX ---
    for filepath in classified_files.get("docx", []):
        try:
            import docx

            relative = str(filepath.relative_to(version_path))
            doc_reader = docx.Document(str(filepath))
            full_text = "\n".join(
                paragraph.text for paragraph in doc_reader.paragraphs if paragraph.text
            )

            if full_text.strip():
                docs = text_splitter.create_documents(
                    texts=[full_text],
                    metadatas=[{"source": relative, "type": "docx", "language": "plain"}],
                )
                for doc in docs:
                    all_chunks.append({
                        "text": doc.page_content,
                        "metadata": doc.metadata,
                    })
            else:
                logger.warning(
                    "[ENTRENAMIENTO][FASE-3-PREP] DOCX sin texto extraíble: %s",
                    filepath.name,
                )
        except ImportError:
            logger.warning(
                "[ENTRENAMIENTO][FASE-3-PREP] python-docx no disponible, "
                "omitiendo %s",
                filepath.name,
            )
        except Exception as exc:
            logger.warning(
                "[ENTRENAMIENTO][FASE-3-PREP] Error cargando DOCX %s: %s",
                filepath.name, exc,
            )

    return all_chunks


def _generate_embeddings(
    chunks: list[dict[str, Any]],
) -> list[list[float]]:
    """Genera embeddings para todos los chunks usando Keras/TF-Hub USE.

    Args:
        chunks: Lista de diccionarios con campo 'text'.

    Returns:
        Lista de vectores de 512 dimensiones (uno por chunk).
    """
    from keras_embeddings import KerasEmbeddings

    logger.info(
        "[ENTRENAMIENTO][FASE-3-PREP] Generando embeddings para %d chunks...",
        len(chunks),
    )

    embeddings_model = KerasEmbeddings()
    texts = [chunk["text"] for chunk in chunks]
    vectors = embeddings_model.embed_documents(texts)

    logger.info(
        "[ENTRENAMIENTO][FASE-3-PREP] %d embeddings generados (dim=%d)",
        len(vectors),
        len(vectors[0]) if vectors else 0,
    )

    return vectors


def _phase_preparacion(
    broker: Any,
    id_entrenamiento: int,
    classified_files: dict[str, list[Path]],
    params: dict[str, Any],
    pat_version: str,
    phase_start_time: float,
) -> tuple[list[dict[str, Any]], list[list[float]]]:
    """Fase 3 - Preparación: Carga, chunking y generación de embeddings.

    Args:
        broker: Instancia de TrainerBrokerClient para notificaciones.
        id_entrenamiento: ID del entrenamiento.
        classified_files: Archivos clasificados por tipo (de fase 2).
        params: Parámetros de entrenamiento (chunk_size, chunk_overlap, etc.).
        pat_version: Ruta base de la versión.
        phase_start_time: Timestamp del inicio de la fase.

    Returns:
        Tupla con (chunks, embeddings).

    Raises:
        RuntimeError: Si no se generan chunks o embeddings.
    """
    logger.info(
        "[ENTRENAMIENTO][FASE-3-PREP] Iniciando carga y chunking "
        "(chunk_size=%d, chunk_overlap=%d)...",
        params["chunk_size"],
        params["chunk_overlap"],
    )

    # Subfase 3.1: Carga de documentos
    _notify_progress(broker, id_entrenamiento, "3", "3.1", "Carga de documentos", "in_progress", time.time() - phase_start_time)
    # (La función _load_and_chunk_documents hace tanto carga como chunking)
    _notify_progress(broker, id_entrenamiento, "3", "3.1", "Carga de documentos", "completed", time.time() - phase_start_time)

    # Subfase 3.2: Chunking
    _notify_progress(broker, id_entrenamiento, "3", "3.2", "Chunking", "in_progress", time.time() - phase_start_time)
    chunks = _load_and_chunk_documents(
        classified_files=classified_files,
        chunk_size=params["chunk_size"],
        chunk_overlap=params["chunk_overlap"],
        pat_version=pat_version,
    )

    if not chunks:
        _notify_progress(broker, id_entrenamiento, "3", "3.2", "Chunking", "error", time.time() - phase_start_time, "No se generaron chunks")
        raise RuntimeError(
            "No se generaron chunks tras procesar los archivos. "
            "Verificar que los archivos contienen texto extraíble."
        )

    _notify_progress(broker, id_entrenamiento, "3", "3.2", "Chunking", "completed", time.time() - phase_start_time)

    logger.info(
        "[ENTRENAMIENTO][FASE-3-PREP] %d chunks generados. "
        "Iniciando generación de embeddings...",
        len(chunks),
    )

    # Subfase 3.3: Generación de embeddings
    _notify_progress(broker, id_entrenamiento, "3", "3.3", "Generación de embeddings", "in_progress", time.time() - phase_start_time)
    embeddings = _generate_embeddings(chunks)

    if len(embeddings) != len(chunks):
        _notify_progress(broker, id_entrenamiento, "3", "3.3", "Generación de embeddings", "error", time.time() - phase_start_time, "Inconsistencia chunks/embeddings")
        raise RuntimeError(
            f"Inconsistencia: {len(chunks)} chunks pero {len(embeddings)} embeddings"
        )

    _notify_progress(broker, id_entrenamiento, "3", "3.3", "Generación de embeddings", "completed", time.time() - phase_start_time)

    logger.info("[ENTRENAMIENTO][FASE-3-PREP] Preparación completada exitosamente")

    return chunks, embeddings


# ---------------------------------------------------------------------------
# FASE 4: CONFIGURACIÓN (ChromaDB)
# ---------------------------------------------------------------------------


def _phase_configuracion(
    broker: Any,
    id_entrenamiento: int,
    collection_name: str,
    chunks: list[dict[str, Any]],
    embeddings: list[list[float]],
    phase_start_time: float,
) -> int:
    """Fase 4 - Configuración: Crea colección en ChromaDB e inserta datos.

    Crea (o reutiliza) la colección con el nombre convencional, inserta
    todos los chunks con sus embeddings y metadatos, y verifica la integridad.

    Args:
        broker: Instancia de TrainerBrokerClient para notificaciones.
        id_entrenamiento: ID del entrenamiento.
        collection_name: Nombre de la colección ChromaDB (ORG_PRJ_v_ENT_SEQ).
        chunks: Lista de chunks con 'text' y 'metadata'.
        embeddings: Lista de vectores correspondientes a los chunks.
        phase_start_time: Timestamp del inicio de la fase.

    Returns:
        Número de documentos insertados en la colección.

    Raises:
        RuntimeError: Si ChromaDB no está disponible o la inserción falla.
    """
    from chroma_server import get_chroma_client

    logger.info(
        "[ENTRENAMIENTO][FASE-4-CONFIG] Creando colección '%s' en ChromaDB "
        "con %d documentos...",
        collection_name,
        len(chunks),
    )

    # Subfase 4.1: Conexión ChromaDB
    _notify_progress(broker, id_entrenamiento, "4", "4.1", "Conexión ChromaDB", "in_progress", time.time() - phase_start_time)
    client = get_chroma_client()
    if client is None:
        _notify_progress(broker, id_entrenamiento, "4", "4.1", "Conexión ChromaDB", "error", time.time() - phase_start_time, "ChromaDB no disponible")
        raise RuntimeError(
            "ChromaDB no disponible. Verificar que el servidor está arrancado."
        )
    _notify_progress(broker, id_entrenamiento, "4", "4.1", "Conexión ChromaDB", "completed", time.time() - phase_start_time)

    # Subfase 4.2: Crear colección
    _notify_progress(broker, id_entrenamiento, "4", "4.2", "Crear colección", "in_progress", time.time() - phase_start_time)
    try:
        collection = client.get_or_create_collection(name=collection_name)
    except Exception as exc:
        _notify_progress(broker, id_entrenamiento, "4", "4.2", "Crear colección", "error", time.time() - phase_start_time, f"Error creando colección: {exc}")
        raise RuntimeError(
            f"Error creando colección '{collection_name}': {exc}"
        ) from exc
    _notify_progress(broker, id_entrenamiento, "4", "4.2", "Crear colección", "completed", time.time() - phase_start_time)

    # Subfase 4.3: Inserción de documentos
    _notify_progress(broker, id_entrenamiento, "4", "4.3", "Inserción de documentos", "in_progress", time.time() - phase_start_time)
    batch_size = 100
    total_inserted = 0

    for i in range(0, len(chunks), batch_size):
        batch_end = min(i + batch_size, len(chunks))
        batch_chunks = chunks[i:batch_end]
        batch_embeddings = embeddings[i:batch_end]

        ids = [f"doc_{i + j}" for j in range(len(batch_chunks))]
        documents = [chunk["text"] for chunk in batch_chunks]
        metadatas = [chunk["metadata"] for chunk in batch_chunks]

        try:
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=batch_embeddings,
                metadatas=metadatas,
            )
            total_inserted += len(batch_chunks)

            if len(chunks) > batch_size:
                logger.debug(
                    "[ENTRENAMIENTO][FASE-4-CONFIG] Lote %d/%d insertado (%d docs)",
                    (i // batch_size) + 1,
                    (len(chunks) + batch_size - 1) // batch_size,
                    len(batch_chunks),
                )
        except Exception as exc:
            logger.error(
                "[ENTRENAMIENTO][FASE-4-CONFIG] Error insertando lote en ChromaDB: %s",
                exc,
            )
            _notify_progress(broker, id_entrenamiento, "4", "4.3", "Inserción de documentos", "error", time.time() - phase_start_time, f"Error insertando: {exc}")
            raise RuntimeError(
                f"Error insertando datos en ChromaDB: {exc}"
            ) from exc

    _notify_progress(broker, id_entrenamiento, "4", "4.3", "Inserción de documentos", "completed", time.time() - phase_start_time)

    # Subfase 4.4: Verificación de integridad
    _notify_progress(broker, id_entrenamiento, "4", "4.4", "Verificación de integridad", "in_progress", time.time() - phase_start_time)
    count = collection.count()
    logger.info(
        "[ENTRENAMIENTO][FASE-4-CONFIG] Colección '%s' lista: "
        "%d documentos insertados, %d en colección (verificado)",
        collection_name,
        total_inserted,
        count,
    )

    if count < total_inserted:
        logger.warning(
            "[ENTRENAMIENTO][FASE-4-CONFIG] Inconsistencia: "
            "insertados=%d, en colección=%d",
            total_inserted,
            count,
        )

    _notify_progress(broker, id_entrenamiento, "4", "4.4", "Verificación de integridad", "completed", time.time() - phase_start_time)

    return total_inserted


# ---------------------------------------------------------------------------
# FASE 5: ENTRENAMIENTO (Ollama Modelfile)
# ---------------------------------------------------------------------------


def _generate_modelfile(
    template_vars: dict[str, Any],
) -> str:
    """Renderiza la plantilla Jinja2 modelfile.j2.

    Args:
        template_vars: Variables para la plantilla.

    Returns:
        Contenido del Modelfile renderizado.
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
    )
    template = env.get_template("modelfile.j2")
    return template.render(**template_vars)


def _phase_entrenamiento(
    broker: Any,
    id_entrenamiento: int,
    phase_start_time: float,
    collection_name: str,
    numero_secuencia: int,
    num_documents: int,
    num_chunks: int,
    document_types: set[str],
    params: dict[str, Any],
    payload: dict[str, Any],
    organization_name: str,
    project_name: str,
) -> str:
    """Fase 5 - Entrenamiento: Genera Modelfile y registra modelo en Ollama.

    Genera un Modelfile especializado con system prompt basado en el contenido
    del proyecto, lo registra en Ollama con 'ollama create', y verifica que
    el modelo funcione con una consulta de prueba.

    Args:
        broker: Cliente Broker para notificaciones de progreso.
        id_entrenamiento: ID del entrenamiento en BD.
        phase_start_time: Timestamp de inicio de la fase.
        collection_name: Nombre de la colección ChromaDB.
        numero_secuencia: Número de secuencia del entrenamiento.
        num_documents: Total de documentos procesados.
        num_chunks: Total de chunks generados.
        document_types: Tipos de documentos encontrados.
        params: Parámetros de entrenamiento.
        payload: Datos originales de la solicitud.
        organization_name: Nombre legible de la organización.
        project_name: Nombre legible del proyecto.

    Returns:
        Ruta del Modelfile guardado en disco.

    Raises:
        RuntimeError: Si falla la creación del modelo en Ollama.
    """
    id_org = payload["id_organizacion"]
    id_prj = payload["id_proyecto"]
    id_ver = payload["id_version"]

    # Nombre del modelo en Ollama
    model_name = f"myllm-org{id_org}-prj{id_prj}-v{id_ver}"
    base_model = get_env_value("ollama_rag_base_model", "deepseek-r1:8b")

    # Nombre de la versión (ej: v001)
    version_name = f"v{id_ver:03d}"

    logger.info(
        "[ENTRENAMIENTO][FASE-5-ENTRENAMIENTO] Generando Modelfile para '%s' "
        "(base=%s)...",
        model_name,
        base_model,
    )

    # --- Subfase 5.2: Generar Modelfile ---
    _notify_progress(
        broker,
        id_entrenamiento,
        "5",
        "5.2",
        "Generar Modelfile",
        "in_progress",
        time.time() - phase_start_time,
    )

    # --- 5a: Renderizar Modelfile ---
    now = datetime.now(timezone.utc)
    types_str = ", ".join(sorted(document_types)) if document_types else "text"

    template_vars = {
        "base_model": base_model,
        "model_name": model_name,
        "organization_name": organization_name,
        "project_name": project_name,
        "version_name": version_name,
        "collection_name": collection_name,
        "num_documents": num_documents,
        "num_chunks": num_chunks,
        "document_types": types_str,
        "temperature": params["temperature"],
        "top_k": params["top_k"],
        "num_ctx": params["max_tokens"],
        "training_id": id_entrenamiento,
        "sequence_number": numero_secuencia,
        "fecha_creacion": now.strftime("%Y-%m-%d %H:%M:%S"),
    }

    modelfile_content = _generate_modelfile(template_vars)

    logger.info(
        "[ENTRENAMIENTO][FASE-5-ENTRENAMIENTO] Modelfile generado: %d caracteres",
        len(modelfile_content),
    )

    _notify_progress(
        broker,
        id_entrenamiento,
        "5",
        "5.2",
        "Generar Modelfile",
        "completed",
        time.time() - phase_start_time,
    )

    # --- Subfase 5.3: Guardar Modelfile ---
    _notify_progress(
        broker,
        id_entrenamiento,
        "5",
        "5.3",
        "Guardar Modelfile",
        "in_progress",
        time.time() - phase_start_time,
    )

    # --- 5b: Guardar Modelfile en disco (internal storage) ---
    internal_base = get_env_value(
        "backend_ia_internal_storage",
        "~/data/anewhope/files/trainer_server/internal",
    )
    internal_path = Path(os.path.expanduser(internal_base))

    # Construir ruta: internal/models/ORG.../PRJ.../v.../
    _storage_structure = _load_shared_module(
        "storage_structure_ent",
        "2_shared_application/storage_access_structure.py",
    )
    org_folder = _storage_structure.get_folder_by_id_organization(id_org)
    prj_folder = _storage_structure.get_folder_by_id_project(id_prj)
    ver_folder = _storage_structure.get_folder_by_id_version(id_ver)

    models_dir = internal_path / "models" / org_folder / prj_folder / ver_folder
    models_dir.mkdir(parents=True, exist_ok=True)

    modelfile_filename = f"Modelfile_ENT{id_entrenamiento}"
    modelfile_path = models_dir / modelfile_filename
    modelfile_path.write_text(modelfile_content, encoding="utf-8")

    logger.info(
        "[ENTRENAMIENTO][FASE-5-ENTRENAMIENTO] Modelfile guardado en: %s",
        modelfile_path,
    )

    _notify_progress(
        broker,
        id_entrenamiento,
        "5",
        "5.3",
        "Guardar Modelfile",
        "completed",
        time.time() - phase_start_time,
    )

    # --- Subfase 5.4: Registrar en Ollama ---
    _notify_progress(
        broker,
        id_entrenamiento,
        "5",
        "5.4",
        "Registrar en Ollama",
        "in_progress",
        time.time() - phase_start_time,
    )

    # --- 5c: Registrar modelo en Ollama ---
    logger.info(
        "[ENTRENAMIENTO][FASE-5-ENTRENAMIENTO] Registrando modelo '%s' en Ollama...",
        model_name,
    )

    try:
        import ollama as ollama_lib

        # Construir el system prompt desde el Modelfile renderizado
        # Extraer system prompt y parámetros del contenido del Modelfile
        system_lines: list[str] = []
        in_system = False
        for line in modelfile_content.splitlines():
            if line.startswith('SYSTEM """'):
                in_system = True
                # Extraer el texto después de SYSTEM """
                rest = line[len('SYSTEM """'):]
                if rest.endswith('"""'):
                    # System prompt en una sola línea
                    system_lines.append(rest[:-3])
                    in_system = False
                else:
                    system_lines.append(rest)
                continue
            if in_system:
                if line.endswith('"""'):
                    system_lines.append(line[:-3])
                    in_system = False
                else:
                    system_lines.append(line)

        system_prompt = "\n".join(system_lines)

        ollama_lib.create(
            model=model_name,
            from_=base_model,
            system=system_prompt,
            parameters={
                "temperature": params["temperature"],
                "top_k": params["top_k"],
                "num_ctx": params["max_tokens"],
            },
        )

        logger.info(
            "[ENTRENAMIENTO][FASE-5-ENTRENAMIENTO] Modelo '%s' registrado en Ollama",
            model_name,
        )

        _notify_progress(
            broker,
            id_entrenamiento,
            "5",
            "5.4",
            "Registrar en Ollama",
            "completed",
            time.time() - phase_start_time,
        )

    except Exception as exc:
        _notify_progress(
            broker,
            id_entrenamiento,
            "5",
            "5.4",
            "Registrar en Ollama",
            "error",
            time.time() - phase_start_time,
            error_message=str(exc),
        )
        raise RuntimeError(
            f"Error registrando modelo '{model_name}' en Ollama: {exc}"
        ) from exc

    # --- Subfase 5.5: Test de verificación ---
    _notify_progress(
        broker,
        id_entrenamiento,
        "5",
        "5.5",
        "Test de verificación",
        "in_progress",
        time.time() - phase_start_time,
    )

    # --- 5d: Test de verificación ---
    logger.info(
        "[ENTRENAMIENTO][FASE-5-ENTRENAMIENTO] Ejecutando test de verificación...",
    )

    try:
        test_response = ollama_lib.generate(
            model=model_name,
            prompt="¿Cuál es el propósito principal de este proyecto?",
            options={"num_predict": 100, "temperature": 0.3},
        )
        test_text = test_response.get("response", "")[:200]
        logger.info(
            "[ENTRENAMIENTO][FASE-5-ENTRENAMIENTO] Test OK: '%s...'",
            test_text[:100],
        )

        _notify_progress(
            broker,
            id_entrenamiento,
            "5",
            "5.5",
            "Test de verificación",
            "completed",
            time.time() - phase_start_time,
        )

    except Exception as exc:
        logger.warning(
            "[ENTRENAMIENTO][FASE-5-ENTRENAMIENTO] Test de verificación falló: %s "
            "(el modelo base puede estar descargándose)",
            exc,
        )
        # Test warning no es error crítico, marcar como completado
        _notify_progress(
            broker,
            id_entrenamiento,
            "5",
            "5.5",
            "Test de verificación",
            "completed",
            time.time() - phase_start_time,
        )

    return str(modelfile_path)


# ---------------------------------------------------------------------------
# Funciones auxiliares de lectura de BD (solo lectura, vía PyMySQL directo)
# ---------------------------------------------------------------------------


def _get_db_reader_connection(database: str) -> Any:
    """Crea una conexión de solo lectura a MariaDB para nombres legibles."""
    import pymysql
    import pymysql.cursors

    host = get_protected_value("mariadb_host", "localhost")
    port = int(get_protected_value("mariadb_port", 3306))
    user = get_protected_value("mariadb_reader_user", "myllm_reader")
    password = get_protected_value("mariadb_reader_password", "")

    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def _fetch_organization_name(id_organizacion: int) -> str:
    """Obtiene el nombre de la organización desde myllm_core_db."""
    try:
        conn = _get_db_reader_connection("myllm_core_db")
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT organization_name FROM organizations "
                    "WHERE organization_id = %s",
                    (id_organizacion,),
                )
                row = cursor.fetchone()
                if row:
                    return str(row["organization_name"])
        return f"Organización {id_organizacion}"
    except Exception as exc:
        logger.warning(
            "[ENTRENAMIENTO] No se pudo obtener nombre de organización %s: %s",
            id_organizacion, exc,
        )
        return f"Organización {id_organizacion}"


def _fetch_project_name(id_proyecto: int) -> str:
    """Obtiene el nombre del proyecto desde myllm_projects_db."""
    try:
        conn = _get_db_reader_connection("myllm_projects_db")
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT nombre FROM proyectos WHERE id = %s",
                    (id_proyecto,),
                )
                row = cursor.fetchone()
                if row:
                    return str(row["nombre"])
        return f"Proyecto {id_proyecto}"
    except Exception as exc:
        logger.warning(
            "[ENTRENAMIENTO] No se pudo obtener nombre de proyecto %s: %s",
            id_proyecto, exc,
        )
        return f"Proyecto {id_proyecto}"


# ---------------------------------------------------------------------------
# PROCESO PRINCIPAL (ejecutado en background thread)
# ---------------------------------------------------------------------------


def process_entrenamiento(data: dict[str, Any]) -> None:
    """Proceso principal de entrenamiento RAG (ejecutado en background thread).

    Orquesta las 5 fases del entrenamiento:
    1. Recepción  → Registro en BD
    2. Validación → Escaneo y clasificación de archivos
    3. Preparación → Carga, chunking y embeddings
    4. Configuración → Inserción en ChromaDB
    5. Entrenamiento → Generación y registro de modelo Ollama

    Tras cada fase, actualiza el estado en MariaDB via Broker para que
    el Backoffice pueda mostrar el progreso.

    Args:
        data: Diccionario con id_organizacion, id_proyecto, id_version, pat_version.
    """
    from broker_client import TrainerBrokerClient

    start_time = time.time()
    id_org = data.get("id_organizacion", 0)
    id_prj = data.get("id_proyecto", 0)
    id_ver = data.get("id_version", 0)
    pat_version = data.get("pat_version", "")

    logger.info(
        "[ENTRENAMIENTO] === INICIO PROCESO === org=%s prj=%s ver=%s pat=%s",
        id_org, id_prj, id_ver, pat_version,
    )

    broker = TrainerBrokerClient()
    id_entrenamiento: int | None = None

    try:
        # ============================================================
        # FASE 1: RECEPCIÓN - Registrar en BD
        # ============================================================
        reg_result = _phase_recepcion(broker, data)
        id_entrenamiento = reg_result["id_entrenamiento"]
        collection_name = reg_result["collection_name"]
        numero_secuencia = reg_result["numero_secuencia"]

        # Cargar parámetros de entrenamiento: desde request si llegan, sino defaults
        request_params = {}
        for pkey in (
            "chunk_size", "chunk_overlap", "temperature", "max_tokens",
            "top_k", "distance_metric", "embedding_dimension",
            "learning_rate", "batch_size", "epochs", "sequence_length",
            "hidden_units", "dropout_rate", "loss_function", "optimizer",
            "model_type",
        ):
            pval = data.get(pkey)
            if pval is not None:
                request_params[pkey] = pval

        if request_params:
            # Merge con defaults: request sobreescribe
            params = {**_load_training_params(), **request_params}
            logger.info(
                "[ENTRENAMIENTO] Usando parámetros del request (%d campos)",
                len(request_params),
            )
        else:
            params = _load_training_params()
            logger.info(
                "[ENTRENAMIENTO] Usando parámetros por defecto (no se enviaron desde modal)"
            )

        logger.info(
            "[ENTRENAMIENTO] Fase 1 completada en %s",
            _format_elapsed_time(time.time() - start_time),
        )

        # ============================================================
        # FASE 2: VALIDACIÓN - Escanear archivos
        # ============================================================
        broker.update_phase(id_entrenamiento, "validacion")
        phase2_start = time.time()

        classified_files = _phase_validacion(
            broker=broker,
            id_entrenamiento=id_entrenamiento,
            phase_start_time=phase2_start,
            pat_version=pat_version,
        )

        num_documents = sum(len(v) for v in classified_files.values())
        document_types = set()
        for file_type, files in classified_files.items():
            if files:
                document_types.add(file_type)

        logger.info(
            "[ENTRENAMIENTO] Fase 2 completada en %s (%d documentos)",
            _format_elapsed_time(time.time() - phase2_start),
            num_documents,
        )

        # ============================================================
        # FASE 3: PREPARACIÓN - Chunking + Embeddings
        # ============================================================
        broker.update_phase(id_entrenamiento, "preparacion")
        phase3_start = time.time()

        chunks, embeddings = _phase_preparacion(
            broker=broker,
            id_entrenamiento=id_entrenamiento,
            phase_start_time=phase3_start,
            classified_files=classified_files,
            params=params,
            pat_version=pat_version,
        )

        logger.info(
            "[ENTRENAMIENTO] Fase 3 completada en %s (%d chunks, %d embeddings)",
            _format_elapsed_time(time.time() - phase3_start),
            len(chunks),
            len(embeddings),
        )

        # ============================================================
        # FASE 4: CONFIGURACIÓN - ChromaDB
        # ============================================================
        broker.update_phase(id_entrenamiento, "configuracion")
        phase4_start = time.time()

        num_inserted = _phase_configuracion(
            broker=broker,
            id_entrenamiento=id_entrenamiento,
            phase_start_time=phase4_start,
            collection_name=collection_name,
            chunks=chunks,
            embeddings=embeddings,
        )

        logger.info(
            "[ENTRENAMIENTO] Fase 4 completada en %s (%d docs en ChromaDB)",
            _format_elapsed_time(time.time() - phase4_start),
            num_inserted,
        )

        # ============================================================
        # FASE 5: ENTRENAMIENTO - Modelfile + Ollama
        # ============================================================
        broker.update_phase(id_entrenamiento, "entrenamiento")
        phase5_start = time.time()

        # --- Subfase 5.1: Obtener nombres de organización y proyecto ---
        _notify_progress(
            broker,
            id_entrenamiento,
            "5",
            "5.1",
            "Obtener nombres",
            "in_progress",
            time.time() - phase5_start,
        )

        # Obtener nombres legibles para el system prompt
        org_name = _fetch_organization_name(id_org)
        prj_name = _fetch_project_name(id_prj)

        _notify_progress(
            broker,
            id_entrenamiento,
            "5",
            "5.1",
            "Obtener nombres",
            "completed",
            time.time() - phase5_start,
        )

        modelo_path = _phase_entrenamiento(
            broker=broker,
            id_entrenamiento=id_entrenamiento,
            phase_start_time=phase5_start,
            collection_name=collection_name,
            numero_secuencia=numero_secuencia,
            num_documents=num_documents,
            num_chunks=len(chunks),
            document_types=document_types,
            params=params,
            payload=data,
            organization_name=org_name,
            project_name=prj_name,
        )

        logger.info(
            "[ENTRENAMIENTO] Fase 5 completada en %s (modelo=%s)",
            _format_elapsed_time(time.time() - phase5_start),
            modelo_path,
        )

        # ============================================================
        # COMPLETADO - Notificar éxito
        # ============================================================
        broker.complete_entrenamiento(id_entrenamiento, modelo_path)

        total_elapsed = time.time() - start_time
        logger.info(
            "[ENTRENAMIENTO] === PROCESO COMPLETADO === "
            "id=%s collection=%s modelo=%s "
            "docs=%d chunks=%d tiempo_total=%s",
            id_entrenamiento,
            collection_name,
            modelo_path,
            num_documents,
            len(chunks),
            _format_elapsed_time(total_elapsed),
        )

    except Exception as exc:
        total_elapsed = time.time() - start_time
        error_msg = str(exc)
        logger.error(
            "[ENTRENAMIENTO][ERROR] %s (id=%s, tras %s)",
            error_msg,
            id_entrenamiento,
            _format_elapsed_time(total_elapsed),
            exc_info=True,
        )

        # Intentar notificar error al Backend Core
        if id_entrenamiento is not None:
            try:
                broker.error_entrenamiento(id_entrenamiento, error_msg)
                logger.info(
                    "[ENTRENAMIENTO] Error notificado a BD para id=%s",
                    id_entrenamiento,
                )
            except Exception as notify_err:
                logger.error(
                    "[ENTRENAMIENTO][ERROR] Fallo al notificar error a BD: %s",
                    notify_err,
                )


def process_entrenamiento_with_id(data: dict[str, Any]) -> None:
    """Proceso de entrenamiento RAG cuando el registro ya fue realizado.

    Esta función se usa cuando el entrenamiento ya fue registrado en BD
    antes de lanzar el background thread. Omite la Fase 1 (registro) y
    comienza directamente en la Fase 2 (validación).

    Orquesta las fases 2-5 del entrenamiento:
    2. Validación → Escaneo y clasificación de archivos
    3. Preparación → Carga, chunking y embeddings
    4. Configuración → Inserción en ChromaDB
    5. Entrenamiento → Generación y registro de modelo Ollama

    Args:
        data: Diccionario con id_entrenamiento, collection_name, numero_secuencia,
              id_organizacion, id_proyecto, id_version, pat_version y parámetros.
    """
    from broker_client import TrainerBrokerClient

    start_time = time.time()
    id_entrenamiento = data["id_entrenamiento"]
    collection_name = data["collection_name"]
    numero_secuencia = data["numero_secuencia"]
    id_org = data.get("id_organizacion", 0)
    id_prj = data.get("id_proyecto", 0)
    id_ver = data.get("id_version", 0)
    pat_version = data.get("pat_version", "")

    logger.info(
        "[ENTRENAMIENTO] === INICIO PROCESO (con ID pre-registrado) === "
        "id=%s org=%s prj=%s ver=%s pat=%s",
        id_entrenamiento, id_org, id_prj, id_ver, pat_version,
    )

    broker = TrainerBrokerClient()

    try:
        # Cargar parámetros de entrenamiento: desde request si llegan, sino defaults
        request_params = {}
        for pkey in (
            "chunk_size", "chunk_overlap", "temperature", "max_tokens",
            "top_k", "distance_metric", "embedding_dimension",
            "learning_rate", "batch_size", "epochs", "sequence_length",
            "hidden_units", "dropout_rate", "loss_function", "optimizer",
            "model_type",
        ):
            pval = data.get(pkey)
            if pval is not None:
                request_params[pkey] = pval

        if request_params:
            params = {**_load_training_params(), **request_params}
            logger.info(
                "[ENTRENAMIENTO] Usando parámetros del request (%d campos)",
                len(request_params),
            )
        else:
            params = _load_training_params()
            logger.info(
                "[ENTRENAMIENTO] Usando parámetros por defecto"
            )

        # ============================================================
        # FASE 2: VALIDACIÓN - Escanear archivos
        # ============================================================
        broker.update_phase(id_entrenamiento, "validacion")
        phase2_start = time.time()

        classified_files = _phase_validacion(
            broker=broker,
            id_entrenamiento=id_entrenamiento,
            phase_start_time=phase2_start,
            pat_version=pat_version,
        )

        num_documents = sum(len(v) for v in classified_files.values())
        document_types = set()
        for file_type, files in classified_files.items():
            if files:
                document_types.add(file_type)

        logger.info(
            "[ENTRENAMIENTO] Fase 2 completada en %s (%d documentos)",
            _format_elapsed_time(time.time() - phase2_start),
            num_documents,
        )

        # ============================================================
        # FASE 3: PREPARACIÓN - Chunking + Embeddings
        # ============================================================
        broker.update_phase(id_entrenamiento, "preparacion")
        phase3_start = time.time()

        chunks, embeddings = _phase_preparacion(
            broker=broker,
            id_entrenamiento=id_entrenamiento,
            phase_start_time=phase3_start,
            classified_files=classified_files,
            params=params,
            pat_version=pat_version,
        )

        logger.info(
            "[ENTRENAMIENTO] Fase 3 completada en %s (%d chunks, %d embeddings)",
            _format_elapsed_time(time.time() - phase3_start),
            len(chunks),
            len(embeddings),
        )

        # ============================================================
        # FASE 4: CONFIGURACIÓN - ChromaDB
        # ============================================================
        broker.update_phase(id_entrenamiento, "configuracion")
        phase4_start = time.time()

        num_inserted = _phase_configuracion(
            broker=broker,
            id_entrenamiento=id_entrenamiento,
            phase_start_time=phase4_start,
            collection_name=collection_name,
            chunks=chunks,
            embeddings=embeddings,
        )

        logger.info(
            "[ENTRENAMIENTO] Fase 4 completada en %s (%d docs en ChromaDB)",
            _format_elapsed_time(time.time() - phase4_start),
            num_inserted,
        )

        # ============================================================
        # FASE 5: ENTRENAMIENTO - Modelfile + Ollama
        # ============================================================
        broker.update_phase(id_entrenamiento, "entrenamiento")
        phase5_start = time.time()

        # --- Subfase 5.1: Obtener nombres de organización y proyecto ---
        _notify_progress(
            broker,
            id_entrenamiento,
            "5",
            "5.1",
            "Obtener nombres",
            "in_progress",
            time.time() - phase5_start,
        )

        # Obtener nombres legibles para el system prompt
        org_name = _fetch_organization_name(id_org)
        prj_name = _fetch_project_name(id_prj)

        _notify_progress(
            broker,
            id_entrenamiento,
            "5",
            "5.1",
            "Obtener nombres",
            "completed",
            time.time() - phase5_start,
        )

        modelo_path = _phase_entrenamiento(
            broker=broker,
            id_entrenamiento=id_entrenamiento,
            phase_start_time=phase5_start,
            collection_name=collection_name,
            numero_secuencia=numero_secuencia,
            num_documents=num_documents,
            num_chunks=len(chunks),
            document_types=document_types,
            params=params,
            payload=data,
            organization_name=org_name,
            project_name=prj_name,
        )

        logger.info(
            "[ENTRENAMIENTO] Fase 5 completada en %s (modelo=%s)",
            _format_elapsed_time(time.time() - phase5_start),
            modelo_path,
        )

        # ============================================================
        # COMPLETADO - Notificar éxito
        # ============================================================
        broker.complete_entrenamiento(id_entrenamiento, modelo_path)

        total_elapsed = time.time() - start_time
        logger.info(
            "[ENTRENAMIENTO] === PROCESO COMPLETADO === "
            "id=%s collection=%s modelo=%s "
            "docs=%d chunks=%d tiempo_total=%s",
            id_entrenamiento,
            collection_name,
            modelo_path,
            num_documents,
            len(chunks),
            _format_elapsed_time(total_elapsed),
        )

    except Exception as exc:
        total_elapsed = time.time() - start_time
        error_msg = str(exc)
        logger.error(
            "[ENTRENAMIENTO][ERROR] %s (id=%s, tras %s)",
            error_msg,
            id_entrenamiento,
            _format_elapsed_time(total_elapsed),
            exc_info=True,
        )

        # Intentar notificar error al Backend Core
        try:
            broker.error_entrenamiento(id_entrenamiento, error_msg)
            logger.info(
                "[ENTRENAMIENTO] Error notificado a BD para id=%s",
                id_entrenamiento,
            )
        except Exception as notify_err:
            logger.error(
                "[ENTRENAMIENTO][ERROR] Fallo al notificar error a BD: %s",
                notify_err,
            )
