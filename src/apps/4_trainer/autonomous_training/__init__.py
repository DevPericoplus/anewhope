"""Módulos de entrenamiento autónomo con fine-tuning LoRA.

Este paquete implementa las fases 6-9 del proceso de entrenamiento autónomo:
- Fase 6: Generación de dataset ✅
- Fase 7: Preparación LoRA ✅
- Fase 8: Entrenamiento LoRA ✅
- Fase 9: Exportación GGUF ✅

Autor: Sistema anewhope
Fecha: 2026-02-13
"""

from autonomous_training.dataset_generator import (
    DatasetGenerator,
    DatasetGenerationError,
    get_chunks_from_collection,
)
from autonomous_training.db_progress import AutonomousProgressTracker
from autonomous_training.gguf_exporter import GGUFExporter, GGUFExportError
from autonomous_training.lora_preparation import (
    LoRAPreparation,
    LoRAPreparationError,
)
from autonomous_training.lora_trainer import LoRATrainer, LoRATrainingError
from autonomous_training.package_generator import (
    PackageGenerator,
    PackageGenerationError,
)
from autonomous_training.path_manager import PathManager
from autonomous_training.phase6_executor import (
    Phase6Executor,
    execute_phase6_generation,
)
from autonomous_training.phase9_executor import Phase9Executor, execute_phase9_export
from autonomous_training.phases78_executor import (
    Phases78Executor,
    execute_phases78_training,
)

__all__ = [
    # Fase 6: Dataset
    "DatasetGenerator",
    "DatasetGenerationError",
    "get_chunks_from_collection",
    "Phase6Executor",
    "execute_phase6_generation",
    # Fases 7-8: LoRA
    "LoRAPreparation",
    "LoRAPreparationError",
    "LoRATrainer",
    "LoRATrainingError",
    "Phases78Executor",
    "execute_phases78_training",
    # Fase 9: GGUF Export
    "GGUFExporter",
    "GGUFExportError",
    "PackageGenerator",
    "PackageGenerationError",
    "Phase9Executor",
    "execute_phase9_export",
    # Común
    "AutonomousProgressTracker",
    "PathManager",
]

__version__ = "0.3.0"
