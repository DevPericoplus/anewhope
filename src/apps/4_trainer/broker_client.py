"""Cliente HTTP para que el Trainer opere via Broker → Backend Core.

El Trainer no accede directamente a MariaDB para escritura. Todas las
operaciones de persistencia (registro de entrenamientos, actualización
de fases, completado/error) se enrutan al Broker, que a su vez las
reenvía al Backend Core.

Flujo:
    Trainer → Broker (8008) → Backend Core (8003) → MariaDB

Uso:
    from broker_client import TrainerBrokerClient

    client = TrainerBrokerClient()
    result = client.register_entrenamiento({
        "id_organizacion": 1,
        "id_proyecto": 1,
        "id_version": 1,
        "pat_version": "/data/ORG00001/PRJ00001/v001",
        "entrenamiento_inicial": True,
        "reentrenamiento": False,
    })
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("trainer_api")


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


# Cargar configuración de entorno
_env_settings = _load_shared_module(
    "env_settings_broker_client",
    "2_shared_application/config/env_settings.py",
)
get_env_value = _env_settings.get_env_value
get_protected_value = _env_settings.get_protected_value


class TrainerBrokerClientError(Exception):
    """Error en la comunicación del Trainer con el Broker."""


class TrainerBrokerClient:
    """Cliente HTTP para que el Trainer opere via Broker → Backend Core.

    Encapsula las llamadas HTTP al Broker para operaciones de
    registro y seguimiento de entrenamientos en MariaDB.

    Attributes:
        _broker_url: URL base del Broker.
        _timeout: Timeout para peticiones HTTP en segundos.
        _client_app: Identificador del servicio origen para trazabilidad.
    """

    def __init__(
        self,
        broker_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Inicializa el cliente con la URL del Broker.

        Args:
            broker_url: URL base del Broker. Si no se proporciona,
                se lee de protected_values (broker_backend_base_url).
            timeout: Timeout para peticiones HTTP.
        """
        if broker_url:
            self._broker_url = broker_url.rstrip("/")
        else:
            self._broker_url = (
                get_env_value("BROKER_BACKEND_BASE_URL", "")
                or get_env_value("broker_backend_base_url", "")
                or get_protected_value(
                    "broker_backend_base_url", "http://localhost:8008"
                )
            )
            self._broker_url = str(self._broker_url).rstrip("/")
        self._timeout = timeout
        self._client_app = "trainer"
        logger.info(
            "[BROKER-CLIENT] Inicializado con broker_url=%s",
            self._broker_url,
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ejecuta una petición HTTP al Broker.

        Args:
            method: Método HTTP (POST, PATCH, GET, etc.).
            path: Ruta relativa del endpoint.
            payload: Cuerpo de la petición (JSON).

        Returns:
            Respuesta JSON como diccionario.

        Raises:
            TrainerBrokerClientError: Si la petición falla.
        """
        url = f"{self._broker_url}{path}"
        headers = {
            "Content-Type": "application/json",
            "X-Client-App": self._client_app,
        }

        logger.info(
            "[BROKER-CLIENT] %s %s payload=%s",
            method,
            url,
            payload,
        )

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.request(
                    method,
                    url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                result = response.json()
                logger.info(
                    "[BROKER-CLIENT] Respuesta %s: %s",
                    response.status_code,
                    result,
                )
                return dict(result)
        except httpx.HTTPStatusError as exc:
            detail = ""
            try:
                detail = exc.response.json().get("detail", str(exc))
            except Exception:
                detail = str(exc)
            logger.error(
                "[BROKER-CLIENT] Error HTTP %s: %s",
                exc.response.status_code,
                detail,
            )
            raise TrainerBrokerClientError(
                f"Error HTTP {exc.response.status_code}: {detail}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error(
                "[BROKER-CLIENT] Error de conexión con Broker: %s", exc,
            )
            raise TrainerBrokerClientError(
                f"Error de conexión con Broker: {exc}"
            ) from exc

    def get_job_context(
        self,
        organization_id: int = 0,
        project_id: int = 0,
        prompt_name: str = "",
    ) -> dict[str, Any]:
        """Obtiene nombres y prompt de fusión via Broker → Backend Core.

        Args:
            organization_id: ID de organización (0 para omitir).
            project_id: ID de proyecto (0 para omitir).
            prompt_name: Nombre del prompt en prompts_identidades.

        Returns:
            Diccionario con organization_name, project_name y prompt.
        """
        from urllib.parse import quote

        path = (
            f"/trainer/job-context?organization_id={organization_id}"
            f"&project_id={project_id}"
        )
        if prompt_name:
            path = f"{path}&prompt_name={quote(prompt_name)}"
        return self._request("GET", path)

    def complete_job(
        self,
        job_id: int,
        id_organizacion: int,
        id_proyecto: int,
        id_version: int,
        descripcion: str,
        referencia_salida: str = "",
        tipo_cambio: str = "evaluacion_documental",
        id_estado: int = 4,
    ) -> dict[str, Any]:
        """Completa un job via Broker → Backend Core → MariaDB.

        Args:
            job_id: ID del job.
            id_organizacion: ID de organización.
            id_proyecto: ID de proyecto.
            id_version: ID de versión.
            descripcion: Descripción del resultado.
            referencia_salida: Ruta del informe generado.
            tipo_cambio: Tipo para la tabla cambios.
            id_estado: 4=finalizado, 3=error.

        Returns:
            Diccionario con success, id_cambio y message.
        """
        return self._request(
            "PATCH",
            f"/jobs/{job_id}/complete",
            payload={
                "job_id": job_id,
                "id_organizacion": id_organizacion,
                "id_proyecto": id_proyecto,
                "id_version": id_version,
                "descripcion": descripcion,
                "referencia_salida": referencia_salida,
                "tipo_cambio": tipo_cambio,
                "id_estado": id_estado,
            },
        )

    # ================================================================
    # Operaciones de entrenamientos
    # ================================================================

    def register_entrenamiento(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Registra un nuevo entrenamiento via Broker → Backend Core → MariaDB.

        Crea registros en las tablas entrenamientos + jobs_entrenamientos
        con los parámetros por defecto del entorno.

        Args:
            payload: Diccionario con id_organizacion, id_proyecto,
                id_version, pat_version, entrenamiento_inicial, reentrenamiento.

        Returns:
            Diccionario con id_entrenamiento, id_job_entrenamientos,
            collection_name y numero_secuencia.
        """
        return self._request(
            "POST",
            "/training/entrenamientos/register",
            payload=payload,
        )

    def update_phase(
        self,
        id_entrenamiento: int,
        fase_actual: str,
    ) -> dict[str, Any]:
        """Actualiza la fase actual del entrenamiento.

        Fases válidas: validacion, preparacion, configuracion, entrenamiento.

        Args:
            id_entrenamiento: ID del entrenamiento en BD.
            fase_actual: Nueva fase del proceso.

        Returns:
            Diccionario con success y message.
        """
        return self._request(
            "PATCH",
            f"/training/entrenamientos/{id_entrenamiento}/phase",
            payload={"fase_actual": fase_actual},
        )

    def complete_entrenamiento(
        self,
        id_entrenamiento: int,
        modelo_path: str,
    ) -> dict[str, Any]:
        """Marca un entrenamiento como completado.

        Args:
            id_entrenamiento: ID del entrenamiento en BD.
            modelo_path: Ruta del modelo generado.

        Returns:
            Diccionario con success y message.
        """
        return self._request(
            "PATCH",
            f"/training/entrenamientos/{id_entrenamiento}/complete",
            payload={"modelo_path": modelo_path},
        )

    def error_entrenamiento(
        self,
        id_entrenamiento: int,
        error_mensaje: str,
    ) -> dict[str, Any]:
        """Marca un entrenamiento como error.

        Args:
            id_entrenamiento: ID del entrenamiento en BD.
            error_mensaje: Descripción del error ocurrido.

        Returns:
            Diccionario con success y message.
        """
        return self._request(
            "PATCH",
            f"/training/entrenamientos/{id_entrenamiento}/error",
            payload={"error_mensaje": error_mensaje},
        )

    def notify_training_progress(
        self,
        id_entrenamiento: int,
        phase_key: str,
        subfase_key: str,
        subfase_name: str,
        status: str,
        elapsed_time: str = "",
        error_message: str = "",
        metrics: str = "",
    ) -> dict[str, Any]:
        """Notifica progreso de una subfase al Broker.

        Funciona tanto para fases RAG (2-5) como autónomas (6-9).
        El Backend Core enruta automáticamente a la tabla correcta.

        Args:
            id_entrenamiento: ID del entrenamiento en BD.
            phase_key: Clave de la fase principal (ej: "3" o "6").
            subfase_key: Clave de la subfase (ej: "3.2" o "6.1").
            subfase_name: Nombre legible (ej: "Chunking").
            status: Estado (in_progress, completed, error, failed).
            elapsed_time: Tiempo empleado (ej: "2m 15s").
            error_message: Mensaje de error si status=error.
            metrics: JSON de métricas opcionales (fases autónomas).

        Returns:
            Diccionario con success y message.
        """
        payload = {
            "id_entrenamiento": id_entrenamiento,
            "phase_key": phase_key,
            "subfase_key": subfase_key,
            "subfase_name": subfase_name,
            "status": status,
            "elapsed_time": elapsed_time,
            "error_message": error_message,
            "metrics": metrics,
        }

        try:
            return self._request("PATCH", "/training/progress", payload=payload)
        except Exception as exc:
            # No fallar el entrenamiento si la notificación falla
            logger.warning(
                "[BROKER-CLIENT] Error notificando progreso %s: %s",
                subfase_key,
                exc,
            )
            return {"success": False, "message": str(exc)}

    # ================================================================
    # Operaciones de entrenamiento autónomo (fases 6-9)
    # ================================================================

    def initialize_autonomous_training(
        self,
        id_entrenamiento: int,
        training_mode: str,
    ) -> dict[str, Any]:
        """Inicializa registro de entrenamiento autónomo via Broker → Backend Core.

        Args:
            id_entrenamiento: ID del entrenamiento en BD.
            training_mode: Modo (simulation, test, production).

        Returns:
            Diccionario con success y message.
        """
        try:
            return self._request(
                "POST",
                "/training/autonomous/init",
                payload={
                    "id_entrenamiento": id_entrenamiento,
                    "training_mode": training_mode,
                },
            )
        except Exception as exc:
            logger.warning(
                "[BROKER-CLIENT] Error inicializando autónomo %s: %s",
                id_entrenamiento,
                exc,
            )
            return {"success": False, "message": str(exc)}

    def update_autonomous_metadata(
        self,
        id_entrenamiento: int,
        metadata_type: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Actualiza metadatos de entrenamiento autónomo via Broker → Backend Core.

        Args:
            id_entrenamiento: ID del entrenamiento en BD.
            metadata_type: Tipo ("dataset", "lora", "gguf", "package").
            data: Campos específicos según tipo.

        Returns:
            Diccionario con success y message.
        """
        try:
            return self._request(
                "PATCH",
                "/training/autonomous/metadata",
                payload={
                    "id_entrenamiento": id_entrenamiento,
                    "metadata_type": metadata_type,
                    "data": data,
                },
            )
        except Exception as exc:
            logger.warning(
                "[BROKER-CLIENT] Error actualizando metadata %s para %s: %s",
                metadata_type,
                id_entrenamiento,
                exc,
            )
            return {"success": False, "message": str(exc)}
