"""Ejecutor de la Fase 6: Generación de Dataset.

Este módulo orquesta las 5 subfases de generación de dataset y
actualiza el progreso en la base de datos en tiempo real.

Autor: Sistema anewhope
Fecha: 2026-02-13
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from autonomous_training.dataset_generator import (
    DatasetGenerator,
    DatasetGenerationError,
    get_chunks_from_collection,
)
from autonomous_training.db_progress import AutonomousProgressTracker


logger = logging.getLogger(__name__)


class Phase6Executor:
    """Ejecutor de la Fase 6: Generación de Dataset.

    Coordina las 5 subfases:
    - 6.1: Analizar chunks
    - 6.2: Generar plantillas
    - 6.3: Generar Q&A con LLM
    - 6.4: Validar y formatear
    - 6.5: Guardar dataset
    """

    def __init__(
        self,
        id_entrenamiento: int,
        collection_name: str,
        training_mode: str,
        broker_client: Any,
        ollama_url: str = "http://localhost:11434",
        chroma_host: str = "localhost",
        chroma_port: int = 8100,
        output_dir: Path | None = None,
    ):
        """Inicializa el ejecutor de la Fase 6.

        Args:
            id_entrenamiento: ID del entrenamiento
            collection_name: Nombre de la colección ChromaDB
            training_mode: Modo (simulation/test/production)
            broker_client: Cliente HTTP del Broker (TrainerBrokerClient)
            ollama_url: URL de Ollama
            chroma_host: Host de ChromaDB
            chroma_port: Puerto de ChromaDB
            output_dir: Directorio de salida (default: autonomous_training/datasets/)
        """
        self.id_entrenamiento = id_entrenamiento
        self.collection_name = collection_name
        self.training_mode = training_mode

        # Progress tracker (via cadena API)
        self.progress = AutonomousProgressTracker(broker_client, id_entrenamiento)

        # Dataset generator
        self.generator = DatasetGenerator(
            id_entrenamiento,
            ollama_base_url=ollama_url,
        )

        # ChromaDB config
        self.chroma_host = chroma_host
        self.chroma_port = chroma_port

        # Output directory
        if output_dir is None:
            output_dir = Path(__file__).parent / "datasets"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"[Phase 6] Inicializado para entrenamiento {id_entrenamiento} "
            f"(mode={training_mode})"
        )

    def execute(self) -> dict[str, Any]:
        """Ejecuta la Fase 6 completa con actualización de progreso.

        Returns:
            Resumen del proceso con todas las métricas

        Raises:
            DatasetGenerationError: Si hay error en el proceso
        """
        logger.info("[Phase 6] Iniciando Fase 6: Generación de Dataset")

        summary = {
            "id_entrenamiento": self.id_entrenamiento,
            "training_mode": self.training_mode,
            "collection_name": self.collection_name,
            "subfases": {},
        }

        try:
            # ================================================================
            # Subfase 6.1: Analizar chunks disponibles
            # ================================================================
            self.progress.start_subfase("6.1", "Analizar chunks disponibles")

            logger.info("[6.1] Recuperando chunks desde ChromaDB...")
            chunks = get_chunks_from_collection(
                self.collection_name,
                self.chroma_host,
                self.chroma_port,
            )

            chunk_stats = self.generator.analyze_chunks(chunks)
            summary["subfases"]["6.1"] = chunk_stats

            self.progress.complete_subfase("6.1", metrics=chunk_stats)

            # ================================================================
            # Subfase 6.2: Generar plantillas de preguntas
            # ================================================================
            self.progress.start_subfase("6.2", "Generar plantillas de preguntas")

            logger.info("[6.2] Generando preguntas desde templates...")

            # Configurar según training_mode
            if self.training_mode == "simulation":
                max_per_chunk = 1
            elif self.training_mode == "test":
                max_per_chunk = 2
            else:  # production
                max_per_chunk = 3

            template_examples = self.generator.generate_template_questions(
                chunks,
                max_per_chunk=max_per_chunk,
            )

            template_stats = {
                "total_examples": len(template_examples),
                "max_per_chunk": max_per_chunk,
            }
            summary["subfases"]["6.2"] = template_stats

            self.progress.complete_subfase("6.2", metrics=template_stats)

            # ================================================================
            # Subfase 6.3: Generar Q&A con LLM
            # ================================================================
            if self.training_mode == "simulation":
                # En simulation: omitir generación con LLM
                logger.info("[6.3] Omitiendo generación LLM (mode=simulation)")
                llm_examples = []
                llm_stats = {
                    "total_examples": 0,
                    "skipped": True,
                    "reason": "simulation mode",
                }
                summary["subfases"]["6.3"] = llm_stats
            else:
                # En test/production: generar con LLM
                self.progress.start_subfase("6.3", "Generar Q&A con LLM")

                logger.info("[6.3] Generando preguntas con Ollama...")

                existing_questions = [ex["instruction"] for ex in template_examples]

                if self.training_mode == "test":
                    chunk_limit = 50
                    max_per_chunk_llm = 1
                else:  # production
                    chunk_limit = None
                    max_per_chunk_llm = 2

                llm_examples = self.generator.generate_llm_questions(
                    chunks[:chunk_limit] if chunk_limit else chunks,
                    existing_questions,
                    max_per_chunk=max_per_chunk_llm,
                )

                llm_stats = {
                    "total_examples": len(llm_examples),
                    "max_per_chunk": max_per_chunk_llm,
                    "chunk_limit": chunk_limit,
                }
                summary["subfases"]["6.3"] = llm_stats

                self.progress.complete_subfase("6.3", metrics=llm_stats)

            # ================================================================
            # Subfase 6.4: Validar y formatear dataset
            # ================================================================
            self.progress.start_subfase("6.4", "Validar y formatear dataset")

            logger.info("[6.4] Validando dataset...")

            all_examples = template_examples + llm_examples

            validated_examples, validation_stats = (
                self.generator.validate_and_format_dataset(all_examples)
            )

            summary["subfases"]["6.4"] = validation_stats

            self.progress.complete_subfase("6.4", metrics=validation_stats)

            # ================================================================
            # Subfase 6.5: Guardar dataset
            # ================================================================
            self.progress.start_subfase("6.5", "Guardar dataset")

            logger.info("[6.5] Guardando dataset...")

            output_path = (
                self.output_dir
                / f"ENT{self.id_entrenamiento}_dataset.jsonl"
            )

            file_metadata = self.generator.save_dataset(
                validated_examples,
                output_path,
            )

            summary["subfases"]["6.5"] = file_metadata

            self.progress.complete_subfase("6.5", metrics=file_metadata)

            # ================================================================
            # Actualizar tabla entrenamientos_autonomos
            # ================================================================
            self.progress.update_dataset_info(
                dataset_path=str(output_path),
                dataset_size=len(validated_examples),
            )

            # ================================================================
            # Resumen final
            # ================================================================
            summary["status"] = "completed"
            summary["output_file"] = str(output_path)
            summary["total_examples"] = len(validated_examples)

            logger.info(
                f"[Phase 6] Fase 6 completada: {len(validated_examples)} ejemplos "
                f"generados en {output_path}"
            )

            return summary

        except Exception as e:
            logger.error(f"[Phase 6] Error en Fase 6: {e}", exc_info=True)

            # Marcar última subfase como fallida
            # (intentar detectar cuál era la subfase activa)
            summary["status"] = "failed"
            summary["error"] = str(e)

            raise DatasetGenerationError(f"Error en Fase 6: {e}") from e

        finally:
            # Cerrar conexiones
            self.progress.close()
            self.generator.close()

    def __enter__(self):
        """Soporte para context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Limpieza al salir."""
        self.progress.close()
        self.generator.close()


# =============================================================================
# Función helper para uso desde el trainer
# =============================================================================

def execute_phase6_generation(
    id_entrenamiento: int,
    collection_name: str,
    training_mode: str,
    broker_client: Any,
    **kwargs,
) -> dict[str, Any]:
    """Función helper para ejecutar la Fase 6 desde el trainer.

    Args:
        id_entrenamiento: ID del entrenamiento
        collection_name: Nombre de la colección ChromaDB
        training_mode: Modo de entrenamiento
        broker_client: Cliente HTTP del Broker (TrainerBrokerClient)
        **kwargs: Argumentos opcionales (ollama_url, chroma_host, etc.)

    Returns:
        Resumen del proceso

    Raises:
        DatasetGenerationError: Si hay error
    """
    with Phase6Executor(
        id_entrenamiento,
        collection_name,
        training_mode,
        broker_client,
        **kwargs,
    ) as executor:
        return executor.execute()
