"""Exportador GGUF para modelos fine-tuned con LoRA.

Este módulo implementa las subfases 9.1-9.2 de la Fase 9:
- Merge de adaptadores LoRA con modelo base
- Conversión a formato GGUF usando llama.cpp

Autor: Sistema anewhope
Fecha: 2026-02-13
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

import torch


logger = logging.getLogger(__name__)


class GGUFExportError(Exception):
    """Error durante la exportación a GGUF."""


class GGUFExporter:
    """Exportador de modelos LoRA a formato GGUF.

    Maneja el merge de adaptadores LoRA con el modelo base y la conversión
    al formato GGUF usando scripts de llama.cpp.
    """

    def __init__(
        self,
        id_entrenamiento: int,
        lora_adapters_path: str,
        base_model_path: str,
        output_dir: Path,
        training_mode: str,
    ):
        """Inicializa el exportador GGUF.

        Args:
            id_entrenamiento: ID del entrenamiento
            lora_adapters_path: Ruta a los adaptadores LoRA
            base_model_path: Ruta al modelo base
            output_dir: Directorio de salida para GGUF
            training_mode: Modo de entrenamiento (simulation/test/production)
        """
        self.id_entrenamiento = id_entrenamiento
        self.lora_adapters_path = Path(lora_adapters_path)
        self.base_model_path = Path(base_model_path)
        self.output_dir = Path(output_dir)
        self.training_mode = training_mode

        self.merged_model_path = None
        self.gguf_path = None

        # Ruta a llama.cpp
        self.llama_cpp_dir = Path(__file__).parent.parent / "lib" / "llama.cpp"

        logger.info(
            f"[GGUF Exporter] Inicializado para entrenamiento {id_entrenamiento}"
        )

    # =========================================================================
    # Subfase 9.1: Merge LoRA con modelo base
    # =========================================================================

    def merge_lora_with_base(self) -> dict[str, Any]:
        """Merge adaptadores LoRA con el modelo base.

        Returns:
            Información del merge (path del modelo merged, tamaño, etc.)

        Raises:
            GGUFExportError: Si hay error durante el merge
        """
        logger.info("[9.1] Iniciando merge de LoRA con modelo base...")

        try:
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer

            # Crear directorio de salida
            merged_dir = self.output_dir / "merged_model"
            merged_dir.mkdir(parents=True, exist_ok=True)

            # Cargar modelo base
            logger.info(f"[9.1] Cargando modelo base desde {self.base_model_path}")

            # Configurar device según plataforma
            if torch.cuda.is_available():
                device_map = "auto"
                torch_dtype = torch.float16
            else:
                device_map = "cpu"
                torch_dtype = torch.float32

            base_model = AutoModelForCausalLM.from_pretrained(
                str(self.base_model_path),
                device_map=device_map,
                torch_dtype=torch_dtype,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )

            # Cargar adaptadores LoRA
            logger.info(
                f"[9.1] Cargando adaptadores LoRA desde {self.lora_adapters_path}"
            )

            model_with_lora = PeftModel.from_pretrained(
                base_model,
                str(self.lora_adapters_path),
            )

            # Merge de LoRA con el modelo base
            logger.info("[9.1] Mergeando LoRA con modelo base...")
            merged_model = model_with_lora.merge_and_unload()

            # Guardar modelo merged
            logger.info(f"[9.1] Guardando modelo merged en {merged_dir}")
            merged_model.save_pretrained(
                merged_dir,
                safe_serialization=True,  # Usar safetensors
            )

            # Guardar tokenizer
            tokenizer = AutoTokenizer.from_pretrained(
                str(self.lora_adapters_path),
                trust_remote_code=True,
            )
            tokenizer.save_pretrained(merged_dir)

            # Calcular tamaño
            total_size = sum(
                f.stat().st_size for f in merged_dir.rglob("*") if f.is_file()
            )
            size_mb = total_size / (1024 * 1024)

            self.merged_model_path = merged_dir

            merge_info = {
                "status": "merged",
                "path": str(merged_dir),
                "size_mb": round(size_mb, 2),
                "files": len(list(merged_dir.rglob("*"))),
            }

            logger.info(
                f"[9.1] Merge completado: {size_mb:.2f} MB en {merged_dir}"
            )

            # Liberar memoria
            del base_model
            del model_with_lora
            del merged_model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            return merge_info

        except Exception as e:
            logger.error(f"[9.1] Error en merge LoRA: {e}", exc_info=True)
            raise GGUFExportError(f"Error mergeando LoRA: {e}") from e

    # =========================================================================
    # Subfase 9.2: Convertir a GGUF
    # =========================================================================

    def convert_to_gguf(
        self,
        quantization: str | None = None,
    ) -> dict[str, Any]:
        """Convierte el modelo merged a formato GGUF.

        Args:
            quantization: Tipo de cuantización (None=F16, Q4_K_M, Q8_0, etc.)

        Returns:
            Información de la conversión (path GGUF, tamaño, etc.)

        Raises:
            GGUFExportError: Si hay error durante la conversión
        """
        logger.info("[9.2] Iniciando conversión a GGUF...")

        if self.merged_model_path is None:
            raise GGUFExportError("Debe ejecutar merge_lora_with_base() primero")

        # Verificar que llama.cpp esté disponible
        convert_script = self.llama_cpp_dir / "convert_hf_to_gguf.py"
        if not convert_script.exists():
            raise GGUFExportError(
                f"Script de conversión no encontrado: {convert_script}"
            )

        try:
            # Determinar quantización según training_mode
            if quantization is None:
                quantization_map = {
                    "simulation": "F16",  # No cuantizar en simulation
                    "test": "Q4_K_M",     # Cuantización media para test
                    "production": "Q8_0", # Alta calidad para production
                }
                quantization = quantization_map.get(self.training_mode, "F16")

            logger.info(f"[9.2] Usando cuantización: {quantization}")

            # Crear directorio de salida
            gguf_dir = self.output_dir / "gguf"
            gguf_dir.mkdir(parents=True, exist_ok=True)

            # Nombre del archivo GGUF
            gguf_filename = f"ENT{self.id_entrenamiento}_model_{quantization.lower()}.gguf"
            gguf_path = gguf_dir / gguf_filename

            # Comando de conversión
            cmd = [
                "python3",
                str(convert_script),
                str(self.merged_model_path),
                "--outfile", str(gguf_path),
                "--outtype", quantization,
            ]

            logger.info(f"[9.2] Ejecutando conversión: {' '.join(cmd)}")

            # Ejecutar conversión
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutos max
            )

            if result.returncode != 0:
                logger.error(f"[9.2] Error en conversión:\n{result.stderr}")
                raise GGUFExportError(
                    f"Conversión a GGUF falló con código {result.returncode}"
                )

            # Verificar que el archivo GGUF existe
            if not gguf_path.exists():
                raise GGUFExportError(f"Archivo GGUF no generado: {gguf_path}")

            # Calcular tamaño
            gguf_size_mb = gguf_path.stat().st_size / (1024 * 1024)

            self.gguf_path = gguf_path

            conversion_info = {
                "status": "converted",
                "path": str(gguf_path),
                "size_mb": round(gguf_size_mb, 2),
                "quantization": quantization,
                "filename": gguf_filename,
            }

            logger.info(
                f"[9.2] Conversión completada: {gguf_size_mb:.2f} MB "
                f"({quantization})"
            )

            return conversion_info

        except subprocess.TimeoutExpired:
            logger.error("[9.2] Timeout en conversión a GGUF")
            raise GGUFExportError("Conversión a GGUF excedió tiempo límite")
        except Exception as e:
            logger.error(f"[9.2] Error en conversión: {e}", exc_info=True)
            raise GGUFExportError(f"Error convirtiendo a GGUF: {e}") from e

    # =========================================================================
    # Proceso completo de exportación
    # =========================================================================

    def export_complete(self) -> dict[str, Any]:
        """Ejecuta el proceso completo de exportación (subfases 9.1-9.2).

        Returns:
            Resumen completo de la exportación

        Raises:
            GGUFExportError: Si hay error en alguna subfase
        """
        logger.info("[GGUF Exporter] Iniciando exportación a GGUF...")

        summary = {
            "id_entrenamiento": self.id_entrenamiento,
            "subfases": {},
        }

        # 9.1: Merge LoRA
        merge_info = self.merge_lora_with_base()
        summary["subfases"]["9.1"] = merge_info

        # 9.2: Convertir a GGUF
        conversion_info = self.convert_to_gguf()
        summary["subfases"]["9.2"] = conversion_info

        summary["status"] = "completed"
        summary["gguf_path"] = conversion_info["path"]
        summary["gguf_size_mb"] = conversion_info["size_mb"]
        summary["quantization"] = conversion_info["quantization"]

        logger.info("[GGUF Exporter] Exportación completada ✓")

        return summary

    def cleanup(self):
        """Libera recursos y limpia archivos temporales."""
        # Opcionalmente eliminar modelo merged para ahorrar espacio
        # (solo mantener GGUF final)
        if self.merged_model_path and self.merged_model_path.exists():
            logger.info(
                f"[GGUF Exporter] Limpiando modelo merged: {self.merged_model_path}"
            )
            shutil.rmtree(self.merged_model_path, ignore_errors=True)

        logger.info("[GGUF Exporter] Cleanup completado")
