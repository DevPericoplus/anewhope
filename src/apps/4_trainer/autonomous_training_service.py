"""Servicio de entrenamiento autónomo completo.

Orquesta las Fases 6-9 del proceso de entrenamiento autónomo:
    Fase 6: Generación de Dataset (5 subfases)
    Fases 7-8: Preparación y Entrenamiento LoRA (10 subfases)
    Fase 9: Exportación GGUF y Empaquetado (5 subfases)

Este servicio se ejecuta en background thread y genera modelos GGUF
standalone que los clientes pueden usar con Ollama.

Arquitectura:
    Trainer (background) → Broker (8008) → Backend Core (8003) → MariaDB
    Trainer → ChromaDB (8100) → Recupera chunks para dataset
    Trainer → HuggingFace Hub → Descarga modelo base
    Trainer → llama.cpp → Conversión a GGUF

Uso:
    from autonomous_training_service import process_autonomous_training

    # Se ejecuta en background thread desde apitrainer.py
    threading.Thread(
        target=process_autonomous_training,
        args=(payload_dict,)
    ).start()

Autor: Sistema anewhope
Fecha: 2026-02-13
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import importlib.util
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("trainer_api")


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


# Cargar env_settings
_env_settings = _load_shared_module(
    "env_settings_auto",
    "2_shared_application/config/env_settings.py",
)
get_env_value = _env_settings.get_env_value
get_protected_value = _env_settings.get_protected_value

# Cargar fmanagement client para upload de paquetes
_fmanagement_module = _load_shared_module(
    "fmanagement_client_auto",
    "apps/4_trainer/4_infrastructure/web/fmanagement_client.py",
)
_FmanagementClient = _fmanagement_module.FmanagementClient

_storage_module = _load_shared_module(
    "storage_adapter_auto",
    "apps/4_trainer/4_infrastructure/persistence/storage_adapter.py",
)
_load_fmanagement_settings = _storage_module.load_fmanagement_settings

_storage_structure = _load_shared_module(
    "storage_structure_auto",
    "2_shared_application/storage_access_structure.py",
)
get_account_storage_folder = _storage_structure.get_account_storage_folder
get_folder_by_id_project = _storage_structure.get_folder_by_id_project
get_folder_by_id_version = _storage_structure.get_folder_by_id_version


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


def _get_training_mode() -> str:
    """Obtiene el training_mode del .envglobal.

    Returns:
        training_mode: simulation, test o production
    """
    # Leer .envglobal para obtener training_mode
    base_path = Path(__file__).resolve().parents[2]
    envglobal_path = base_path / ".envglobal"

    training_mode = "simulation"  # default

    if envglobal_path.exists():
        with open(envglobal_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("training_mode:"):
                    training_mode = line.split(":", 1)[1].strip()
                    break

    logger.info(f"[Autonomous] training_mode detectado: {training_mode}")
    return training_mode


def _base64url_encode(value: bytes) -> str:
    """Codifica bytes en base64url sin padding."""
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("utf-8")


def _generate_fmanagement_jwt(claims: dict[str, Any], secret: str) -> str:
    """Genera un JWT HS256 para autenticación con fmanagement.

    Mismo patrón que _encode_jwt en routermiddleware.py.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _base64url_encode(
        json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    payload_b64 = _base64url_encode(
        json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(
        secret.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    signature_b64 = _base64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def _upload_package_to_fmanagement(
    package_path: Path,
    id_org: int,
    id_prj: int,
    id_ver: int,
    id_ent: int,
    id_user: int = 0,
) -> bool:
    """Sube el paquete ZIP del modelo autónomo a fmanagement.

    Permite que el backoffice descargue el paquete directamente
    desde fmanagement, sin pasar por toda la cadena API.

    Args:
        package_path: Ruta local al archivo ZIP
        id_org: ID de la organización
        id_prj: ID del proyecto
        id_ver: ID de la versión
        id_ent: ID del entrenamiento

    Returns:
        True si el upload fue exitoso, False en caso contrario.
    """
    logger.info(f"[AUTONOMOUS] Subiendo paquete a fmanagement: {package_path}")

    jwt_secret = get_protected_value("jwt_access_secret_key")
    if not jwt_secret:
        logger.warning("[AUTONOMOUS] No se pudo obtener jwt_access_secret_key")
        return False

    now = int(time.time())
    claims = {
        "user_id": id_user,
        "organization_id": id_org,
        "identity_type_id": 0,
        "project_id": id_prj,
        "version_id": id_ver,
        "operation": "upload",
        "relative_path": "modelos",
        "exp": now + 300,
        "iat": now,
    }

    token = _generate_fmanagement_jwt(claims, jwt_secret)

    file_bytes = package_path.read_bytes()
    filename = package_path.name

    account_folder = get_account_storage_folder(id_org, id_user)
    logger.info(
        "[AUTONOMOUS] Upload: %s (%s bytes) -> %s/%s/%s/modelos/",
        filename,
        len(file_bytes),
        account_folder,
        get_folder_by_id_project(id_prj),
        get_folder_by_id_version(id_ver),
    )

    settings = _load_fmanagement_settings()
    client = _FmanagementClient(
        base_url=settings.base_url,
        timeout_seconds=600,
    )

    result = client.request_json(
        method="POST",
        path="/upload",
        headers={"Authorization": f"Bearer {token}"},
        form={"relative_path": "modelos"},
        file_payload={
            "filename": filename,
            "content": file_bytes,
            "content_type": "application/zip",
        },
    )

    if result.get("status") == "success":
        logger.info(
            f"[AUTONOMOUS] Upload exitoso: {result.get('filename')} "
            f"({result.get('size_bytes', 0)} bytes)"
        )
        return True

    logger.warning(f"[AUTONOMOUS] Upload fallo: {result}")
    return False


# ---------------------------------------------------------------------------
# Proceso principal de entrenamiento autónomo
# ---------------------------------------------------------------------------


def process_autonomous_training(data: dict[str, Any]) -> None:
    """Proceso principal de entrenamiento autónomo (ejecutado en background).

    Orquesta las fases 6-9 del entrenamiento autónomo:
        Fase 6: Generación de Dataset desde ChromaDB
        Fases 7-8: Fine-tuning con LoRA
        Fase 9: Exportación a GGUF y empaquetado

    El resultado es un ZIP con:
        - Modelo GGUF cuantizado
        - Modelfile para Ollama
        - README con instrucciones

    Args:
        data: Diccionario con:
            - id_organizacion: ID de la organización
            - id_proyecto: ID del proyecto
            - id_version: ID de la versión
            - id_entrenamiento: ID del entrenamiento (de fase RAG previa)
            - pat_version: Path de entrada (external)
            - collection_name: Nombre de colección ChromaDB
    """
    from autonomous_training import (
        PathManager,
        execute_phase6_generation,
        execute_phases78_training,
        execute_phase9_export,
    )
    from broker_client import TrainerBrokerClient

    start_time = time.time()

    # Extraer datos del payload
    from trainer_core_lookup import payload_owner_user_id

    id_org = data.get("id_organizacion", 0)
    id_prj = data.get("id_proyecto", 0)
    id_ver = data.get("id_version", 0)
    id_ent = data.get("id_entrenamiento", 0)
    id_user = payload_owner_user_id(data)
    pat_version = data.get("pat_version", "")
    collection_name = data.get("collection_name", "")

    logger.info(
        "[AUTONOMOUS] === INICIO ENTRENAMIENTO AUTÓNOMO === "
        f"org={id_org} prj={id_prj} ver={id_ver} ent={id_ent}"
    )
    logger.info(f"[AUTONOMOUS] collection_name: {collection_name}")
    logger.info(f"[AUTONOMOUS] pat_version (entrada): {pat_version}")

    # Obtener configuración
    training_mode = _get_training_mode()

    # Crear cliente HTTP para cadena API (Trainer → Broker → Backend Core → MariaDB)
    broker_client = TrainerBrokerClient()

    try:
        # Inicializar PathManager para gestionar rutas de salida
        path_mgr = PathManager(
            id_organizacion=id_org,
            id_proyecto=id_prj,
            id_version=id_ver,
            id_entrenamiento=id_ent,
            pat_version=pat_version,
            owner_user_id=id_user,
        )

        logger.info(f"[AUTONOMOUS] Jerarquía: {path_mgr.get_hierarchy_path()}")
        logger.info(f"[AUTONOMOUS] Base salida: {path_mgr.base_storage_path}")
        # =====================================================================
        # FASE 6: GENERACIÓN DE DATASET
        # =====================================================================
        logger.info("[AUTONOMOUS] ===== INICIANDO FASE 6: GENERACIÓN DATASET =====")
        phase6_start = time.time()

        dataset_summary = execute_phase6_generation(
            id_entrenamiento=id_ent,
            collection_name=collection_name,
            training_mode=training_mode,
            broker_client=broker_client,
            output_dir=str(path_mgr.get_dataset_path()),
        )

        phase6_duration = time.time() - phase6_start
        logger.info(
            f"[AUTONOMOUS] Fase 6 completada en {_format_elapsed_time(phase6_duration)}"
        )
        logger.info(
            f"[AUTONOMOUS] Dataset generado: {dataset_summary.get('dataset_size', 0)} ejemplos"
        )

        # =====================================================================
        # FASES 7-8: PREPARACIÓN Y ENTRENAMIENTO LORA
        # =====================================================================
        if training_mode == "simulation":
            logger.info(
                "[AUTONOMOUS] Modo simulation: omitiendo fases 7-8 y 9 "
                "(solo dataset, sin fine-tuning)"
            )

            total_time = time.time() - start_time
            logger.info(
                f"[AUTONOMOUS] === ENTRENAMIENTO AUTÓNOMO COMPLETADO === "
                f"Tiempo total: {_format_elapsed_time(total_time)}"
            )
            return

        logger.info("[AUTONOMOUS] ===== INICIANDO FASES 7-8: LORA TRAINING =====")
        phase78_start = time.time()

        # Obtener modelo base desde env
        base_model_name = get_env_value(
            "ollama_rag_base_model",
            "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
        )

        # Ejecutar fases 7-8
        lora_summary = execute_phases78_training(
            id_entrenamiento=id_ent,
            dataset_path=dataset_summary["dataset_path"],
            training_mode=training_mode,
            broker_client=broker_client,
            base_model_name=base_model_name,
            output_dir=str(path_mgr.get_lora_dir()),
        )

        phase78_duration = time.time() - phase78_start
        logger.info(
            f"[AUTONOMOUS] Fases 7-8 completadas en {_format_elapsed_time(phase78_duration)}"
        )
        logger.info(
            f"[AUTONOMOUS] Adaptadores LoRA: {lora_summary.get('lora_adapters_path', 'N/A')}"
        )

        # =====================================================================
        # FASE 9: EXPORTACIÓN GGUF Y EMPAQUETADO
        # =====================================================================
        logger.info("[AUTONOMOUS] ===== INICIANDO FASE 9: GGUF EXPORT =====")
        phase9_start = time.time()

        # Información del entrenamiento para el README
        training_info = {
            "dataset_size": dataset_summary.get("dataset_size", 0),
            "training_time_seconds": lora_summary.get("training_time_seconds", 0),
        }

        # Ejecutar fase 9
        package_summary = execute_phase9_export(
            id_entrenamiento=id_ent,
            lora_adapters_path=lora_summary["lora_adapters_path"],
            base_model_path=lora_summary["phase7"]["7.2"]["path"],
            training_mode=training_mode,
            broker_client=broker_client,
            output_dir=str(path_mgr.get_export_dir()),
            training_info=training_info,
        )

        phase9_duration = time.time() - phase9_start
        logger.info(
            f"[AUTONOMOUS] Fase 9 completada en {_format_elapsed_time(phase9_duration)}"
        )
        logger.info(
            f"[AUTONOMOUS] Paquete generado: {package_summary.get('package_path', 'N/A')}"
        )
        logger.info(
            f"[AUTONOMOUS] Tamaño: {package_summary.get('package_size_mb', 0):.2f} MB"
        )

        # =====================================================================
        # UPLOAD PAQUETE A FMANAGEMENT
        # =====================================================================
        package_path_str = package_summary.get("package_path", "")
        if package_path_str:
            try:
                _upload_package_to_fmanagement(
                    package_path=Path(package_path_str),
                    id_org=id_org,
                    id_prj=id_prj,
                    id_ver=id_ver,
                    id_ent=id_ent,
                    id_user=id_user,
                )
            except Exception as upload_exc:
                logger.warning(
                    f"[AUTONOMOUS] Upload a fmanagement fallo (non-blocking): "
                    f"{upload_exc}"
                )

        # =====================================================================
        # RESUMEN FINAL
        # =====================================================================
        total_time = time.time() - start_time

        logger.info("[AUTONOMOUS] ===== RESUMEN ENTRENAMIENTO AUTÓNOMO =====")
        logger.info(f"[AUTONOMOUS] Modo: {training_mode}")
        logger.info(f"[AUTONOMOUS] Jerarquía: {path_mgr.get_hierarchy_path()}")
        logger.info(f"[AUTONOMOUS] Fase 6: {_format_elapsed_time(phase6_duration)}")
        logger.info(f"[AUTONOMOUS] Fases 7-8: {_format_elapsed_time(phase78_duration)}")
        logger.info(f"[AUTONOMOUS] Fase 9: {_format_elapsed_time(phase9_duration)}")
        logger.info(f"[AUTONOMOUS] Tiempo total: {_format_elapsed_time(total_time)}")
        logger.info(
            f"[AUTONOMOUS] Dataset: {dataset_summary.get('dataset_size', 0)} ejemplos"
        )
        logger.info(
            f"[AUTONOMOUS] GGUF: {package_summary.get('gguf_size_mb', 0):.2f} MB"
        )
        logger.info(
            f"[AUTONOMOUS] Paquete: {package_summary.get('package_size_mb', 0):.2f} MB"
        )
        logger.info(
            f"[AUTONOMOUS] === ENTRENAMIENTO AUTÓNOMO COMPLETADO === "
            f"{_format_elapsed_time(total_time)}"
        )

    except Exception as e:
        logger.error(
            f"[AUTONOMOUS] Error en entrenamiento autónomo: {e}",
            exc_info=True,
        )

        # TODO: Notificar error al broker para actualizar estado en BD
        # broker.update_phase(id_ent, "error", error_message=str(e))

        raise
