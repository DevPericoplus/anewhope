"""Módulos de entrenamiento autónomo con fine-tuning LoRA.

Este paquete implementa las fases 6-9 del proceso de entrenamiento autónomo:
- Fase 6: Generación de dataset
- Fase 7: Preparación LoRA (próximamente)
- Fase 8: Entrenamiento LoRA (próximamente)
- Fase 9: Exportación GGUF (próximamente)

Autor: Sistema anewhope
Fecha: 2026-02-13
"""

from autonomous_training.dataset_generator import (
    DatasetGenerator,
    DatasetGenerationError,
    get_chunks_from_collection,
)
from autonomous_training.db_progress import AutonomousProgressTracker
from autonomous_training.phase6_executor import (
    Phase6Executor,
    execute_phase6_generation,
)

__all__ = [
    "DatasetGenerator",
    "DatasetGenerationError",
    "get_chunks_from_collection",
    "AutonomousProgressTracker",
    "Phase6Executor",
    "execute_phase6_generation",
]

__version__ = "0.1.0"
