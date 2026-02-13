"""Ejecutor de Fase 9: Exportación GGUF y Empaquetado.

Este módulo orquesta la fase 9 completa del entrenamiento autónomo,
actualizando el progreso en la base de datos en tiempo real.

Autor: Sistema anewhope
Fecha: 2026-02-13
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from autonomous_training.db_progress import AutonomousProgressTracker
from autonomous_training.gguf_exporter import GGUFExporter, GGUFExportError
from autonomous_training.package_generator import (
    PackageGenerator,
    PackageGenerationError,
)


logger = logging.getLogger(__name__)


class Phase9Executor:
    """Ejecutor de Fase 9: Exportación GGUF + Empaquetado.

    Coordina las 5 subfases:
    - Subfases 9.1-9.2: Exportación GGUF
    - Subfases 9.3-9.5: Generación de paquete
    """

    def __init__(
        self,
        id_entrenamiento: int,
        lora_adapters_path: str,
        base_model_path: str,
        training_mode: str,
        db_url: str,
        output_dir: Path | None = None,
        training_info: dict[str, Any] | None = None,
    ):
        """Inicializa el ejecutor de Fase 9.

        Args:
            id_entrenamiento: ID del entrenamiento
            lora_adapters_path: Ruta a adaptadores LoRA (de Fase 8)
            base_model_path: Ruta al modelo base
            training_mode: Modo (simulation/test/production)
            db_url: URL de conexión a MariaDB
            output_dir: Directorio de salida (default: autonomous_training/exports/)
            training_info: Información adicional del entrenamiento
        """
        self.id_entrenamiento = id_entrenamiento
        self.lora_adapters_path = lora_adapters_path
        self.base_model_path = base_model_path
        self.training_mode = training_mode
        self.training_info = training_info or {}

        # Progress tracker
        self.progress = AutonomousProgressTracker(db_url, id_entrenamiento)

        # Output directory
        if output_dir is None:
            output_dir = (
                Path(__file__).parent / "exports" / f"ENT{id_entrenamiento}"
            )
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"[Phase 9] Inicializado para entrenamiento {id_entrenamiento} "
            f"(mode={training_mode})"
        )

    def execute(self) -> dict[str, Any]:
        """Ejecuta la Fase 9 completa con actualización de progreso.

        Returns:
            Resumen del proceso con todas las métricas

        Raises:
            GGUFExportError: Si hay error en exportación GGUF
            PackageGenerationError: Si hay error en generación de paquete
        """
        logger.info("[Phase 9] Iniciando Fase 9: Exportación GGUF y Empaquetado")

        summary = {
            "id_entrenamiento": self.id_entrenamiento,
            "training_mode": self.training_mode,
            "lora_adapters_path": self.lora_adapters_path,
            "phase9": {},
        }

        # =====================================================================
        # VERIFICACIÓN PREVIA: Si mode=simulation, omitir todo
        # =====================================================================
        if self.training_mode == "simulation":
            logger.info(
                "[Phase 9] Modo simulation: omitiendo fase 9 "
                "(no hay modelo fine-tuned para exportar)"
            )

            summary["status"] = "skipped"
            summary["reason"] = "simulation mode - no GGUF export"

            return summary

        try:
            # =================================================================
            # SUBFASES 9.1-9.2: EXPORTACIÓN GGUF
            # =================================================================
            logger.info("[Phase 9] ===== SUBFASES 9.1-9.2: EXPORTACIÓN GGUF =====")

            # Crear exportador
            exporter = GGUFExporter(
                id_entrenamiento=self.id_entrenamiento,
                lora_adapters_path=self.lora_adapters_path,
                base_model_path=self.base_model_path,
                output_dir=self.output_dir,
                training_mode=self.training_mode,
            )

            # Subfase 9.1: Merge LoRA con modelo base
            self.progress.start_subfase("9.1", "Merge LoRA con modelo base")

            try:
                merge_info = exporter.merge_lora_with_base()
                summary["phase9"]["9.1"] = merge_info
                self.progress.complete_subfase("9.1", metrics=merge_info)
            except GGUFExportError as e:
                self.progress.fail_subfase("9.1", str(e))
                raise

            # Subfase 9.2: Convertir a GGUF
            self.progress.start_subfase("9.2", "Convertir a GGUF")

            try:
                conversion_info = exporter.convert_to_gguf()
                summary["phase9"]["9.2"] = conversion_info
                self.progress.complete_subfase("9.2", metrics=conversion_info)
            except GGUFExportError as e:
                self.progress.fail_subfase("9.2", str(e))
                raise

            # Cleanup del exporter (eliminar modelo merged)
            exporter.cleanup()

            logger.info("[Phase 9] ===== EXPORTACIÓN GGUF COMPLETADA =====")

            # =================================================================
            # SUBFASES 9.3-9.5: GENERACIÓN DE PAQUETE
            # =================================================================
            logger.info(
                "[Phase 9] ===== SUBFASES 9.3-9.5: GENERACIÓN DE PAQUETE ====="
            )

            # Crear generador de paquetes
            generator = PackageGenerator(
                id_entrenamiento=self.id_entrenamiento,
                gguf_path=conversion_info["path"],
                output_dir=self.output_dir,
                training_info=self.training_info,
            )

            # Subfase 9.3: Crear Modelfile
            self.progress.start_subfase("9.3", "Crear Modelfile para cliente")

            try:
                modelfile_info = generator.create_modelfile()
                summary["phase9"]["9.3"] = modelfile_info
                self.progress.complete_subfase("9.3", metrics=modelfile_info)
            except PackageGenerationError as e:
                self.progress.fail_subfase("9.3", str(e))
                raise

            # Subfase 9.4: Generar README
            self.progress.start_subfase("9.4", "Generar README")

            try:
                readme_info = generator.generate_readme()
                summary["phase9"]["9.4"] = readme_info
                self.progress.complete_subfase("9.4", metrics=readme_info)
            except PackageGenerationError as e:
                self.progress.fail_subfase("9.4", str(e))
                raise

            # Subfase 9.5: Empaquetar en ZIP
            self.progress.start_subfase("9.5", "Empaquetar entregable")

            try:
                package_info = generator.create_zip_package()
                summary["phase9"]["9.5"] = package_info
                self.progress.complete_subfase("9.5", metrics=package_info)
            except PackageGenerationError as e:
                self.progress.fail_subfase("9.5", str(e))
                raise

            logger.info("[Phase 9] ===== GENERACIÓN DE PAQUETE COMPLETADA =====")

            # =================================================================
            # Actualizar tabla entrenamientos_autonomos
            # =================================================================
            self.progress.update_gguf_info(
                gguf_path=conversion_info["path"],
                package_path=package_info["path"],
            )

            # =================================================================
            # Resumen final
            # =================================================================
            summary["status"] = "completed"
            summary["gguf_path"] = conversion_info["path"]
            summary["gguf_size_mb"] = conversion_info["size_mb"]
            summary["package_path"] = package_info["path"]
            summary["package_size_mb"] = package_info["size_mb"]

            logger.info(
                f"[Phase 9] Fase 9 completada: paquete en {package_info['path']}"
            )

            return summary

        except Exception as e:
            logger.error(f"[Phase 9] Error en Fase 9: {e}", exc_info=True)

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


def execute_phase9_export(
    id_entrenamiento: int,
    lora_adapters_path: str,
    base_model_path: str,
    training_mode: str,
    db_url: str,
    **kwargs,
) -> dict[str, Any]:
    """Función helper para ejecutar Fase 9 desde el trainer.

    Args:
        id_entrenamiento: ID del entrenamiento
        lora_adapters_path: Ruta a adaptadores LoRA
        base_model_path: Ruta al modelo base
        training_mode: Modo de entrenamiento
        db_url: URL de MariaDB
        **kwargs: Argumentos opcionales (output_dir, training_info, etc.)

    Returns:
        Resumen del proceso

    Raises:
        GGUFExportError: Si hay error en exportación
        PackageGenerationError: Si hay error en empaquetado
    """
    with Phase9Executor(
        id_entrenamiento,
        lora_adapters_path,
        base_model_path,
        training_mode,
        db_url,
        **kwargs,
    ) as executor:
        return executor.execute()
