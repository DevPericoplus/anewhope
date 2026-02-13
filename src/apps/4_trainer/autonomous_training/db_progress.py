"""Gestión de progreso de entrenamiento autónomo en base de datos.

Este módulo maneja las actualizaciones de las tablas:
- entrenamientos_autonomos
- evoluciones_autonomas

Autor: Sistema anewhope
Fecha: 2026-02-13
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


logger = logging.getLogger(__name__)


class AutonomousProgressTracker:
    """Rastreador de progreso para fases autónomas (6-9).

    Actualiza las tablas de evolución autónoma en la base de datos
    durante el proceso de fine-tuning y exportación GGUF.
    """

    def __init__(
        self,
        db_url: str,
        id_entrenamiento: int,
    ):
        """Inicializa el tracker.

        Args:
            db_url: URL de conexión a MariaDB
            id_entrenamiento: ID del entrenamiento en curso
        """
        self.db_url = db_url
        self.id_entrenamiento = id_entrenamiento
        self.engine: Engine = create_engine(db_url, pool_pre_ping=True)

        logger.info(
            f"[Progress Tracker] Inicializado para entrenamiento {id_entrenamiento}"
        )

    def close(self):
        """Cierra la conexión a la base de datos."""
        self.engine.dispose()

    # =========================================================================
    # Tabla: entrenamientos_autonomos
    # =========================================================================

    def initialize_autonomous_training(
        self,
        training_mode: str,
    ) -> None:
        """Crea el registro inicial en entrenamientos_autonomos.

        Args:
            training_mode: Modo de entrenamiento (simulation/test/production)
        """
        logger.info(
            f"[Progress] Inicializando entrenamiento autónomo "
            f"(mode={training_mode})"
        )

        query = text("""
            INSERT INTO entrenamientos_autonomos
                (id_entrenamiento, training_mode, created_at, updated_at)
            VALUES
                (:id_ent, :mode, NOW(), NOW())
            ON DUPLICATE KEY UPDATE
                training_mode = :mode,
                updated_at = NOW()
        """)

        with self.engine.connect() as conn:
            conn.execute(
                query,
                {
                    "id_ent": self.id_entrenamiento,
                    "mode": training_mode,
                },
            )
            conn.commit()

        logger.info("[Progress] Registro autónomo inicializado")

    def update_dataset_info(
        self,
        dataset_path: str,
        dataset_size: int,
    ) -> None:
        """Actualiza información del dataset generado.

        Args:
            dataset_path: Ruta del archivo JSONL
            dataset_size: Número de ejemplos
        """
        logger.info(f"[Progress] Actualizando info dataset: {dataset_size} ejemplos")

        query = text("""
            UPDATE entrenamientos_autonomos
            SET
                dataset_path = :path,
                dataset_size = :size,
                dataset_generated_at = NOW(),
                updated_at = NOW()
            WHERE id_entrenamiento = :id_ent
        """)

        with self.engine.connect() as conn:
            conn.execute(
                query,
                {
                    "path": dataset_path,
                    "size": dataset_size,
                    "id_ent": self.id_entrenamiento,
                },
            )
            conn.commit()

    def update_lora_info(
        self,
        lora_path: str,
        lora_config: dict[str, Any],
        training_time: int,
        final_loss: float | None = None,
    ) -> None:
        """Actualiza información del entrenamiento LoRA.

        Args:
            lora_path: Ruta de los adaptadores LoRA
            lora_config: Configuración LoRA (dict)
            training_time: Tiempo de entrenamiento en segundos
            final_loss: Loss final (opcional)
        """
        logger.info(f"[Progress] Actualizando info LoRA: {training_time}s")

        query = text("""
            UPDATE entrenamientos_autonomos
            SET
                lora_adapters_path = :path,
                lora_config = :config,
                lora_training_time_seconds = :time,
                lora_final_loss = :loss,
                lora_completed_at = NOW(),
                updated_at = NOW()
            WHERE id_entrenamiento = :id_ent
        """)

        with self.engine.connect() as conn:
            conn.execute(
                query,
                {
                    "path": lora_path,
                    "config": json.dumps(lora_config),
                    "time": training_time,
                    "loss": final_loss,
                    "id_ent": self.id_entrenamiento,
                },
            )
            conn.commit()

    def update_gguf_info(
        self,
        gguf_path: str,
        gguf_size_mb: float,
        quantization: str = "q8_0",
    ) -> None:
        """Actualiza información del modelo GGUF exportado.

        Args:
            gguf_path: Ruta del archivo GGUF
            gguf_size_mb: Tamaño en MB
            quantization: Tipo de cuantización
        """
        logger.info(f"[Progress] Actualizando info GGUF: {gguf_size_mb} MB")

        query = text("""
            UPDATE entrenamientos_autonomos
            SET
                gguf_path = :path,
                gguf_size_mb = :size,
                gguf_quantization = :quant,
                gguf_generated_at = NOW(),
                updated_at = NOW()
            WHERE id_entrenamiento = :id_ent
        """)

        with self.engine.connect() as conn:
            conn.execute(
                query,
                {
                    "path": gguf_path,
                    "size": gguf_size_mb,
                    "quant": quantization,
                    "id_ent": self.id_entrenamiento,
                },
            )
            conn.commit()

    def update_package_info(
        self,
        package_path: str,
        package_size_mb: float,
    ) -> None:
        """Actualiza información del paquete entregable.

        Args:
            package_path: Ruta del ZIP
            package_size_mb: Tamaño en MB
        """
        logger.info(f"[Progress] Actualizando info paquete: {package_size_mb} MB")

        query = text("""
            UPDATE entrenamientos_autonomos
            SET
                package_path = :path,
                package_size_mb = :size,
                package_generated_at = NOW(),
                updated_at = NOW()
            WHERE id_entrenamiento = :id_ent
        """)

        with self.engine.connect() as conn:
            conn.execute(
                query,
                {
                    "path": package_path,
                    "size": package_size_mb,
                    "id_ent": self.id_entrenamiento,
                },
            )
            conn.commit()

    # =========================================================================
    # Tabla: evoluciones_autonomas
    # =========================================================================

    def start_subfase(
        self,
        subfase_key: str,
        subfase_name: str,
    ) -> None:
        """Marca el inicio de una subfase autónoma.

        Args:
            subfase_key: Clave de la subfase (ej: "6.1", "7.2")
            subfase_name: Nombre de la subfase
        """
        logger.info(f"[Progress] Iniciando subfase {subfase_key}: {subfase_name}")

        phase_key = subfase_key.split(".")[0]

        query = text("""
            INSERT INTO evoluciones_autonomas
                (id_entrenamiento, phase_key, subfase_key, subfase_name,
                 status, started_at, created_at, updated_at)
            VALUES
                (:id_ent, :phase, :subfase, :name,
                 'in_progress', NOW(), NOW(), NOW())
            ON DUPLICATE KEY UPDATE
                status = 'in_progress',
                started_at = NOW(),
                updated_at = NOW()
        """)

        with self.engine.connect() as conn:
            conn.execute(
                query,
                {
                    "id_ent": self.id_entrenamiento,
                    "phase": phase_key,
                    "subfase": subfase_key,
                    "name": subfase_name,
                },
            )
            conn.commit()

    def complete_subfase(
        self,
        subfase_key: str,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """Marca una subfase como completada.

        Args:
            subfase_key: Clave de la subfase
            metrics: Métricas opcionales (dict)
        """
        logger.info(f"[Progress] Completando subfase {subfase_key}")

        query = text("""
            UPDATE evoluciones_autonomas
            SET
                status = 'completed',
                completed_at = NOW(),
                duracion_segundos = TIMESTAMPDIFF(
                    SECOND,
                    started_at,
                    NOW()
                ),
                metrics = :metrics,
                updated_at = NOW()
            WHERE
                id_entrenamiento = :id_ent
                AND subfase_key = :subfase
        """)

        with self.engine.connect() as conn:
            conn.execute(
                query,
                {
                    "id_ent": self.id_entrenamiento,
                    "subfase": subfase_key,
                    "metrics": json.dumps(metrics) if metrics else None,
                },
            )
            conn.commit()

    def fail_subfase(
        self,
        subfase_key: str,
        error_message: str,
    ) -> None:
        """Marca una subfase como fallida.

        Args:
            subfase_key: Clave de la subfase
            error_message: Mensaje de error
        """
        logger.error(f"[Progress] Subfase {subfase_key} falló: {error_message}")

        query = text("""
            UPDATE evoluciones_autonomas
            SET
                status = 'failed',
                completed_at = NOW(),
                duracion_segundos = TIMESTAMPDIFF(
                    SECOND,
                    started_at,
                    NOW()
                ),
                error_message = :error,
                updated_at = NOW()
            WHERE
                id_entrenamiento = :id_ent
                AND subfase_key = :subfase
        """)

        with self.engine.connect() as conn:
            conn.execute(
                query,
                {
                    "id_ent": self.id_entrenamiento,
                    "subfase": subfase_key,
                    "error": error_message,
                },
            )
            conn.commit()

    # =========================================================================
    # Context manager
    # =========================================================================

    def __enter__(self):
        """Soporte para context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierra conexión al salir del context."""
        self.close()
