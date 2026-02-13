"""Ejecutor de Fases 7-8: Preparación y Entrenamiento LoRA.

Este módulo orquesta las fases 7 y 8 completas del entrenamiento autónomo,
actualizando el progreso en la base de datos en tiempo real.

Autor: Sistema anewhope
Fecha: 2026-02-13
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from autonomous_training.db_progress import AutonomousProgressTracker
from autonomous_training.lora_preparation import (
    LoRAPreparation,
    LoRAPreparationError,
)
from autonomous_training.lora_trainer import LoRATrainer, LoRATrainingError


logger = logging.getLogger(__name__)


class Phases78Executor:
    """Ejecutor de Fases 7-8: Preparación + Entrenamiento LoRA.

    Coordina las 10 subfases:
    - Fase 7 (7.1-7.4): Preparación
    - Fase 8 (8.1-8.6): Entrenamiento
    """

    def __init__(
        self,
        id_entrenamiento: int,
        dataset_path: str,
        training_mode: str,
        db_url: str,
        base_model_name: str = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
        output_dir: Path | None = None,
    ):
        """Inicializa el ejecutor de Fases 7-8.

        Args:
            id_entrenamiento: ID del entrenamiento
            dataset_path: Ruta del dataset JSONL (de Fase 6)
            training_mode: Modo (simulation/test/production)
            db_url: URL de conexión a MariaDB
            base_model_name: Nombre del modelo base en HuggingFace
            output_dir: Directorio de salida (default: autonomous_training/lora_adapters/)
        """
        self.id_entrenamiento = id_entrenamiento
        self.dataset_path = dataset_path
        self.training_mode = training_mode

        # Progress tracker
        self.progress = AutonomousProgressTracker(db_url, id_entrenamiento)

        # Preparador LoRA
        self.preparation = LoRAPreparation(
            id_entrenamiento,
            training_mode,
            base_model_name=base_model_name,
        )

        # Output directory
        if output_dir is None:
            output_dir = (
                Path(__file__).parent / "lora_adapters" / f"ENT{id_entrenamiento}"
            )
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"[Phases 7-8] Inicializado para entrenamiento {id_entrenamiento} "
            f"(mode={training_mode})"
        )

    def execute(self) -> dict[str, Any]:
        """Ejecuta las Fases 7-8 completas con actualización de progreso.

        Returns:
            Resumen del proceso con todas las métricas

        Raises:
            LoRAPreparationError: Si hay error en Fase 7
            LoRATrainingError: Si hay error en Fase 8
        """
        logger.info("[Phases 7-8] Iniciando Fases 7-8: Preparación + Entrenamiento LoRA")

        summary = {
            "id_entrenamiento": self.id_entrenamiento,
            "training_mode": self.training_mode,
            "dataset_path": self.dataset_path,
            "phase7": {},
            "phase8": {},
        }

        # =====================================================================
        # VERIFICACIÓN PREVIA: Si mode=simulation, omitir todo
        # =====================================================================
        if self.training_mode == "simulation":
            logger.info(
                "[Phases 7-8] Modo simulation: omitiendo fases 7-8 "
                "(solo RAG, sin fine-tuning)"
            )

            summary["status"] = "skipped"
            summary["reason"] = "simulation mode - no fine-tuning"

            return summary

        try:
            # =================================================================
            # FASE 7: PREPARACIÓN LORA
            # =================================================================
            logger.info("[Phase 7] ===== INICIANDO FASE 7: PREPARACIÓN =====")

            # Subfase 7.1: Verificar dependencias
            self.progress.start_subfase("7.1", "Verificar dependencias")

            try:
                deps = self.preparation.verify_dependencies()
                summary["phase7"]["7.1"] = deps
                self.progress.complete_subfase("7.1", metrics=deps)
            except LoRAPreparationError as e:
                self.progress.fail_subfase("7.1", str(e))
                raise

            # Subfase 7.2: Obtener modelo base
            self.progress.start_subfase("7.2", "Obtener modelo base")

            try:
                model_info = self.preparation.obtain_base_model()
                summary["phase7"]["7.2"] = model_info
                self.progress.complete_subfase("7.2", metrics=model_info)
            except LoRAPreparationError as e:
                self.progress.fail_subfase("7.2", str(e))
                raise

            # Subfase 7.3: Configurar parámetros LoRA
            self.progress.start_subfase("7.3", "Configurar parámetros LoRA")

            try:
                lora_config = self.preparation.configure_lora_parameters()
                summary["phase7"]["7.3"] = lora_config
                self.progress.complete_subfase("7.3", metrics=lora_config)
            except LoRAPreparationError as e:
                self.progress.fail_subfase("7.3", str(e))
                raise

            # Subfase 7.4: Preparar entorno
            self.progress.start_subfase("7.4", "Preparar entorno de entrenamiento")

            try:
                env_info = self.preparation.prepare_training_environment(
                    self.output_dir
                )
                summary["phase7"]["7.4"] = env_info
                self.progress.complete_subfase("7.4", metrics=env_info)
            except LoRAPreparationError as e:
                self.progress.fail_subfase("7.4", str(e))
                raise

            logger.info("[Phase 7] ===== FASE 7 COMPLETADA =====")

            # =================================================================
            # FASE 8: ENTRENAMIENTO LORA
            # =================================================================
            logger.info("[Phase 8] ===== INICIANDO FASE 8: ENTRENAMIENTO =====")

            # Callback para reportar progreso durante training
            def training_progress_handler(metrics: dict):
                """Handler para métricas de entrenamiento."""
                # Log las métricas
                if "loss" in metrics:
                    logger.info(
                        f"[8.2] Step {metrics.get('current_step', 0)}: "
                        f"loss={metrics['loss']:.4f}"
                    )

            # Crear trainer
            trainer = LoRATrainer(
                id_entrenamiento=self.id_entrenamiento,
                model_path=model_info["path"],
                dataset_path=self.dataset_path,
                output_dir=self.output_dir,
                lora_config=lora_config,
                progress_callback=training_progress_handler,
            )

            # Subfase 8.1: Inicializar trainer
            self.progress.start_subfase("8.1", "Inicializar trainer")

            try:
                init_info = trainer.initialize_trainer()
                summary["phase8"]["8.1"] = init_info
                self.progress.complete_subfase("8.1", metrics=init_info)
            except LoRATrainingError as e:
                self.progress.fail_subfase("8.1", str(e))
                raise
            finally:
                pass  # No cleanup aquí, necesitamos el trainer

            # Subfase 8.2-8.3: Ejecutar entrenamiento
            self.progress.start_subfase("8.2", "Entrenamiento en progreso")

            try:
                training_metrics = trainer.execute_training()
                summary["phase8"]["8.2-8.3"] = training_metrics

                # Marcar 8.2 como completada
                self.progress.complete_subfase("8.2", metrics=training_metrics)

                # Marcar 8.3 como completada (finalización)
                self.progress.start_subfase("8.3", "Finalizar entrenamiento")
                self.progress.complete_subfase("8.3", metrics={"status": "completed"})

            except LoRATrainingError as e:
                self.progress.fail_subfase("8.2", str(e))
                raise
            finally:
                pass  # No cleanup aún

            # Subfase 8.4: Evaluar modelo
            self.progress.start_subfase("8.4", "Evaluar modelo")

            try:
                eval_metrics = trainer.evaluate_model()
                summary["phase8"]["8.4"] = eval_metrics
                self.progress.complete_subfase("8.4", metrics=eval_metrics)
            except LoRATrainingError as e:
                self.progress.fail_subfase("8.4", str(e))
                raise

            # Subfase 8.5: Guardar adaptadores LoRA
            self.progress.start_subfase("8.5", "Guardar adaptadores LoRA")

            try:
                save_info = trainer.save_lora_adapters()
                summary["phase8"]["8.5"] = save_info
                self.progress.complete_subfase("8.5", metrics=save_info)
            except LoRATrainingError as e:
                self.progress.fail_subfase("8.5", str(e))
                raise

            # Subfase 8.6: Validar resultados
            self.progress.start_subfase("8.6", "Validar resultados")

            try:
                validation = trainer.validate_results()
                summary["phase8"]["8.6"] = validation
                self.progress.complete_subfase("8.6", metrics=validation)
            except LoRATrainingError as e:
                self.progress.fail_subfase("8.6", str(e))
                raise
            finally:
                # Cleanup final del trainer
                trainer.cleanup()

            logger.info("[Phase 8] ===== FASE 8 COMPLETADA =====")

            # =================================================================
            # Actualizar tabla entrenamientos_autonomos
            # =================================================================
            self.progress.update_lora_info(
                lora_path=save_info["path"],
                lora_config=lora_config,
                training_time=training_metrics["elapsed_seconds"],
                final_loss=training_metrics.get("final_loss"),
            )

            # =================================================================
            # Resumen final
            # =================================================================
            summary["status"] = "completed"
            summary["lora_adapters_path"] = save_info["path"]
            summary["training_time_seconds"] = training_metrics["elapsed_seconds"]
            summary["final_loss"] = training_metrics.get("final_loss")

            logger.info(
                f"[Phases 7-8] Fases 7-8 completadas: "
                f"adaptadores en {save_info['path']}"
            )

            return summary

        except Exception as e:
            logger.error(f"[Phases 7-8] Error en Fases 7-8: {e}", exc_info=True)

            summary["status"] = "failed"
            summary["error"] = str(e)

            raise

        finally:
            # Cerrar conexión BD
            self.progress.close()

    def __enter__(self):
        """Soporte para context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Limpieza al salir."""
        self.progress.close()


# =============================================================================
# Función helper para uso desde el trainer
# =============================================================================

def execute_phases78_training(
    id_entrenamiento: int,
    dataset_path: str,
    training_mode: str,
    db_url: str,
    **kwargs,
) -> dict[str, Any]:
    """Función helper para ejecutar Fases 7-8 desde el trainer.

    Args:
        id_entrenamiento: ID del entrenamiento
        dataset_path: Ruta del dataset JSONL
        training_mode: Modo de entrenamiento
        db_url: URL de MariaDB
        **kwargs: Argumentos opcionales (base_model_name, output_dir, etc.)

    Returns:
        Resumen del proceso

    Raises:
        LoRAPreparationError: Si hay error en Fase 7
        LoRATrainingError: Si hay error en Fase 8
    """
    with Phases78Executor(
        id_entrenamiento,
        dataset_path,
        training_mode,
        db_url,
        **kwargs,
    ) as executor:
        return executor.execute()
