"""Gestión de progreso de entrenamiento autónomo via API chain.

Este módulo envía las actualizaciones de progreso de las fases 6-9
a través de la cadena API:
    Trainer → Broker (8008) → Backend Core (8003) → MariaDB

Tablas destino (gestionadas por Backend Core):
- entrenamientos_autonomos
- evoluciones_autonomas

Autor: Sistema anewhope
Fecha: 2026-02-13
Refactorizado: 2026-02-22 (SQLAlchemy → broker_client HTTP)
"""

from __future__ import annotations

import json
import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from broker_client import TrainerBrokerClient


logger = logging.getLogger(__name__)


class AutonomousProgressTracker:
    """Rastreador de progreso para fases autónomas (6-9).

    Envía actualizaciones de progreso a través de la cadena API
    (Trainer → Broker → Backend Core → MariaDB) en vez de acceder
    directamente a la base de datos.
    """

    def __init__(
        self,
        broker_client: TrainerBrokerClient,
        id_entrenamiento: int,
    ):
        """Inicializa el tracker.

        Args:
            broker_client: Cliente HTTP para comunicarse con el Broker
            id_entrenamiento: ID del entrenamiento en curso
        """
        self.broker_client = broker_client
        self.id_entrenamiento = id_entrenamiento

        logger.info(
            f"[Progress Tracker] Inicializado para entrenamiento {id_entrenamiento}"
        )

    def close(self):
        """Noop - no hay conexión BD que cerrar."""

    # =========================================================================
    # Tabla: entrenamientos_autonomos (via API)
    # =========================================================================

    def initialize_autonomous_training(
        self,
        training_mode: str,
    ) -> None:
        """Crea el registro inicial en entrenamientos_autonomos via API.

        Args:
            training_mode: Modo de entrenamiento (simulation/test/production)
        """
        logger.info(
            f"[Progress] Inicializando entrenamiento autónomo "
            f"(mode={training_mode})"
        )

        result = self.broker_client.initialize_autonomous_training(
            self.id_entrenamiento,
            training_mode,
        )

        if result.get("success"):
            logger.info("[Progress] Registro autónomo inicializado")
        else:
            logger.warning(
                "[Progress] Error inicializando registro autónomo: %s",
                result.get("message", ""),
            )

    def update_dataset_info(
        self,
        dataset_path: str,
        dataset_size: int,
    ) -> None:
        """Actualiza información del dataset generado via API.

        Args:
            dataset_path: Ruta del archivo JSONL
            dataset_size: Número de ejemplos
        """
        logger.info(f"[Progress] Actualizando info dataset: {dataset_size} ejemplos")

        self.broker_client.update_autonomous_metadata(
            self.id_entrenamiento,
            "dataset",
            {
                "dataset_path": dataset_path,
                "dataset_size": dataset_size,
            },
        )

    def update_lora_info(
        self,
        lora_path: str,
        lora_config: dict[str, Any],
        training_time: int,
        final_loss: float | None = None,
    ) -> None:
        """Actualiza información del entrenamiento LoRA via API.

        Args:
            lora_path: Ruta de los adaptadores LoRA
            lora_config: Configuración LoRA (dict)
            training_time: Tiempo de entrenamiento en segundos
            final_loss: Loss final (opcional)
        """
        logger.info(f"[Progress] Actualizando info LoRA: {training_time}s")

        self.broker_client.update_autonomous_metadata(
            self.id_entrenamiento,
            "lora",
            {
                "lora_path": lora_path,
                "lora_config": lora_config,
                "training_time": training_time,
                "final_loss": final_loss,
            },
        )

    def update_gguf_info(
        self,
        gguf_path: str,
        gguf_size_mb: float,
        quantization: str = "q8_0",
    ) -> None:
        """Actualiza información del modelo GGUF exportado via API.

        Args:
            gguf_path: Ruta del archivo GGUF
            gguf_size_mb: Tamaño en MB
            quantization: Tipo de cuantización
        """
        logger.info(f"[Progress] Actualizando info GGUF: {gguf_size_mb} MB")

        self.broker_client.update_autonomous_metadata(
            self.id_entrenamiento,
            "gguf",
            {
                "gguf_path": gguf_path,
                "gguf_size_mb": gguf_size_mb,
                "quantization": quantization,
            },
        )

    def update_package_info(
        self,
        package_path: str,
        package_size_mb: float,
    ) -> None:
        """Actualiza información del paquete entregable via API.

        Args:
            package_path: Ruta del ZIP
            package_size_mb: Tamaño en MB
        """
        logger.info(f"[Progress] Actualizando info paquete: {package_size_mb} MB")

        self.broker_client.update_autonomous_metadata(
            self.id_entrenamiento,
            "package",
            {
                "package_path": package_path,
                "package_size_mb": package_size_mb,
            },
        )

    # =========================================================================
    # Tabla: evoluciones_autonomas (via PATCH /training/progress)
    # =========================================================================

    def start_subfase(
        self,
        subfase_key: str,
        subfase_name: str,
    ) -> None:
        """Marca el inicio de una subfase autónoma via API.

        Args:
            subfase_key: Clave de la subfase (ej: "6.1", "7.2")
            subfase_name: Nombre de la subfase
        """
        logger.info(f"[Progress] Iniciando subfase {subfase_key}: {subfase_name}")

        phase_key = subfase_key.split(".")[0]

        self.broker_client.notify_training_progress(
            id_entrenamiento=self.id_entrenamiento,
            phase_key=phase_key,
            subfase_key=subfase_key,
            subfase_name=subfase_name,
            status="in_progress",
        )

    def complete_subfase(
        self,
        subfase_key: str,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """Marca una subfase como completada via API.

        Args:
            subfase_key: Clave de la subfase
            metrics: Métricas opcionales (dict)
        """
        logger.info(f"[Progress] Completando subfase {subfase_key}")

        phase_key = subfase_key.split(".")[0]
        metrics_json = json.dumps(metrics) if metrics else ""

        self.broker_client.notify_training_progress(
            id_entrenamiento=self.id_entrenamiento,
            phase_key=phase_key,
            subfase_key=subfase_key,
            subfase_name="",  # Ya registrado en start_subfase
            status="completed",
            metrics=metrics_json,
        )

    def fail_subfase(
        self,
        subfase_key: str,
        error_message: str,
    ) -> None:
        """Marca una subfase como fallida via API.

        Args:
            subfase_key: Clave de la subfase
            error_message: Mensaje de error
        """
        logger.error(f"[Progress] Subfase {subfase_key} falló: {error_message}")

        phase_key = subfase_key.split(".")[0]

        self.broker_client.notify_training_progress(
            id_entrenamiento=self.id_entrenamiento,
            phase_key=phase_key,
            subfase_key=subfase_key,
            subfase_name="",  # Ya registrado en start_subfase
            status="failed",
            error_message=error_message,
        )

    # =========================================================================
    # Context manager
    # =========================================================================

    def __enter__(self):
        """Soporte para context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Noop al salir del context."""
        self.close()
