"""Preparación del entorno para Fine-Tuning LoRA.

Este módulo implementa la Fase 7 del proceso de entrenamiento autónomo:
- Verificación de dependencias
- Descarga/conversión del modelo base
- Configuración de parámetros LoRA
- Preparación del entorno de entrenamiento

Autor: Sistema anewhope
Fecha: 2026-02-13
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class LoRAPreparationError(Exception):
    """Error durante la preparación de LoRA."""


class LoRAPreparation:
    """Preparador del entorno para fine-tuning con LoRA.

    Maneja verificación de dependencias, descarga de modelos base
    y configuración de parámetros según training_mode.
    """

    # Dependencias requeridas según plataforma
    REQUIRED_PACKAGES = {
        "common": [
            "torch",
            "transformers",
            "peft",
            "datasets",
            "accelerate",
        ],
        "linux_gpu": [
            "bitsandbytes",  # Para cuantización en GPU
        ],
    }

    # Configuración de parámetros LoRA por modo
    LORA_CONFIGS = {
        "simulation": {
            # En simulation: no se usa LoRA, esto es placeholder
            "enabled": False,
        },
        "test": {
            "enabled": True,
            "r": 8,  # Rank bajo para rapidez
            "lora_alpha": 16,
            "lora_dropout": 0.05,
            "target_modules": ["q_proj", "v_proj"],
            "bias": "none",
            "task_type": "CAUSAL_LM",
            "epochs": 1,
            "batch_size": 2,
            "learning_rate": 2e-4,
            "max_steps": 100,  # Límite de steps
            "save_steps": 50,
            "logging_steps": 10,
        },
        "production": {
            "enabled": True,
            "r": 16,  # Rank más alto para mejor calidad
            "lora_alpha": 32,
            "lora_dropout": 0.1,
            "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
            "bias": "none",
            "task_type": "CAUSAL_LM",
            "epochs": 3,
            "batch_size": 4,
            "learning_rate": 1e-4,
            "max_steps": -1,  # Sin límite
            "save_steps": 100,
            "logging_steps": 20,
        },
    }

    def __init__(
        self,
        id_entrenamiento: int,
        training_mode: str,
        base_model_name: str = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
        models_dir: Path | None = None,
    ):
        """Inicializa el preparador LoRA.

        Args:
            id_entrenamiento: ID del entrenamiento
            training_mode: Modo (simulation/test/production)
            base_model_name: Nombre del modelo en HuggingFace Hub
            models_dir: Directorio para cachear modelos base
        """
        self.id_entrenamiento = id_entrenamiento
        self.training_mode = training_mode
        self.base_model_name = base_model_name

        if models_dir is None:
            models_dir = Path(__file__).parent.parent / "templates" / "models"
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"[LoRA Prep] Inicializado para entrenamiento {id_entrenamiento} "
            f"(mode={training_mode})"
        )

    # =========================================================================
    # Subfase 7.1: Verificar dependencias
    # =========================================================================

    def verify_dependencies(self) -> dict[str, Any]:
        """Verifica que las dependencias necesarias estén instaladas.

        Returns:
            Diccionario con estado de cada dependencia
        """
        logger.info("[7.1] Verificando dependencias...")

        results = {
            "all_installed": True,
            "packages": {},
            "missing": [],
            "platform": sys.platform,
        }

        # Verificar paquetes comunes
        for package in self.REQUIRED_PACKAGES["common"]:
            try:
                __import__(package)
                results["packages"][package] = "installed"
                logger.debug(f"[7.1] ✓ {package} instalado")
            except ImportError:
                results["packages"][package] = "missing"
                results["missing"].append(package)
                results["all_installed"] = False
                logger.warning(f"[7.1] ✗ {package} NO instalado")

        # Verificar paquetes específicos de plataforma
        if sys.platform.startswith("linux"):
            for package in self.REQUIRED_PACKAGES.get("linux_gpu", []):
                try:
                    __import__(package)
                    results["packages"][package] = "installed"
                except ImportError:
                    results["packages"][package] = "missing (optional)"
                    logger.warning(
                        f"[7.1] ⚠ {package} NO instalado (opcional para GPU)"
                    )

        if not results["all_installed"]:
            logger.error(
                f"[7.1] Dependencias faltantes: {', '.join(results['missing'])}"
            )
            raise LoRAPreparationError(
                f"Faltan dependencias requeridas: {', '.join(results['missing'])}"
            )

        logger.info("[7.1] Todas las dependencias están instaladas ✓")

        return results

    # =========================================================================
    # Subfase 7.2: Obtener modelo base
    # =========================================================================

    def obtain_base_model(
        self,
        force_download: bool = False,
    ) -> dict[str, Any]:
        """Obtiene el modelo base en formato HuggingFace.

        Args:
            force_download: Si True, fuerza descarga aunque exista cache

        Returns:
            Información del modelo obtenido
        """
        logger.info(f"[7.2] Obteniendo modelo base: {self.base_model_name}")

        model_cache_dir = self.models_dir / self.base_model_name.replace("/", "_")

        # Verificar si ya existe en cache
        if model_cache_dir.exists() and not force_download:
            logger.info(f"[7.2] Modelo encontrado en cache: {model_cache_dir}")

            # Verificar que tenga los archivos esenciales
            required_files = ["config.json", "pytorch_model.bin"]
            has_safetensors = (model_cache_dir / "model.safetensors").exists()
            has_pytorch = (model_cache_dir / "pytorch_model.bin").exists()

            if has_safetensors or has_pytorch:
                return {
                    "status": "cached",
                    "path": str(model_cache_dir),
                    "model_name": self.base_model_name,
                    "size_mb": self._get_dir_size_mb(model_cache_dir),
                }
            else:
                logger.warning(
                    "[7.2] Cache incompleto, descargando modelo completo..."
                )

        # Descargar modelo desde HuggingFace Hub
        logger.info(f"[7.2] Descargando modelo desde HuggingFace Hub...")

        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            # Descargar tokenizer
            logger.info("[7.2] Descargando tokenizer...")
            tokenizer = AutoTokenizer.from_pretrained(
                self.base_model_name,
                cache_dir=str(model_cache_dir),
                trust_remote_code=True,
            )

            # Descargar modelo (solo config y pesos, no cargar en memoria)
            logger.info("[7.2] Descargando pesos del modelo...")

            # En Intel Mac sin GPU, usar CPU
            if sys.platform == "darwin":
                device_map = "cpu"
                torch_dtype = "float32"
            else:
                device_map = "auto"
                torch_dtype = "auto"

            model = AutoModelForCausalLM.from_pretrained(
                self.base_model_name,
                cache_dir=str(model_cache_dir),
                device_map=device_map,
                torch_dtype=torch_dtype,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )

            # Guardar en directorio local
            model.save_pretrained(model_cache_dir)
            tokenizer.save_pretrained(model_cache_dir)

            logger.info(f"[7.2] Modelo descargado y guardado en {model_cache_dir}")

            return {
                "status": "downloaded",
                "path": str(model_cache_dir),
                "model_name": self.base_model_name,
                "size_mb": self._get_dir_size_mb(model_cache_dir),
            }

        except Exception as e:
            logger.error(f"[7.2] Error descargando modelo: {e}", exc_info=True)
            raise LoRAPreparationError(
                f"Error descargando modelo base: {e}"
            ) from e

    def _get_dir_size_mb(self, directory: Path) -> float:
        """Calcula el tamaño de un directorio en MB.

        Args:
            directory: Path del directorio

        Returns:
            Tamaño en MB
        """
        total_size = 0
        for file in directory.rglob("*"):
            if file.is_file():
                total_size += file.stat().st_size

        return round(total_size / (1024 * 1024), 2)

    # =========================================================================
    # Subfase 7.3: Configurar parámetros LoRA
    # =========================================================================

    def configure_lora_parameters(self) -> dict[str, Any]:
        """Configura parámetros LoRA según training_mode.

        Returns:
            Configuración LoRA completa
        """
        logger.info(
            f"[7.3] Configurando parámetros LoRA para mode={self.training_mode}"
        )

        config = self.LORA_CONFIGS.get(self.training_mode)

        if config is None:
            raise LoRAPreparationError(
                f"Modo de entrenamiento inválido: {self.training_mode}"
            )

        if not config.get("enabled", False):
            logger.info("[7.3] LoRA deshabilitado para modo simulation")
            return {"enabled": False, "reason": "simulation mode"}

        logger.info(
            f"[7.3] Configuración LoRA: rank={config['r']}, "
            f"alpha={config['lora_alpha']}, epochs={config['epochs']}"
        )

        return config

    # =========================================================================
    # Subfase 7.4: Preparar entorno de entrenamiento
    # =========================================================================

    def prepare_training_environment(
        self,
        output_dir: Path,
    ) -> dict[str, Any]:
        """Prepara el entorno para entrenamiento LoRA.

        Args:
            output_dir: Directorio de salida para adaptadores LoRA

        Returns:
            Información del entorno preparado
        """
        logger.info("[7.4] Preparando entorno de entrenamiento...")

        # Crear directorios necesarios
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        logs_dir = output_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        checkpoints_dir = output_dir / "checkpoints"
        checkpoints_dir.mkdir(exist_ok=True)

        # Verificar espacio en disco
        stat = shutil.disk_usage(output_dir)
        free_gb = stat.free / (1024 ** 3)

        if free_gb < 10:
            logger.warning(
                f"[7.4] ⚠ Poco espacio en disco: {free_gb:.2f} GB disponibles"
            )

        env_info = {
            "output_dir": str(output_dir),
            "logs_dir": str(logs_dir),
            "checkpoints_dir": str(checkpoints_dir),
            "free_disk_gb": round(free_gb, 2),
            "platform": sys.platform,
            "python_version": sys.version,
        }

        logger.info(
            f"[7.4] Entorno preparado: {free_gb:.2f} GB disponibles"
        )

        return env_info

    # =========================================================================
    # Proceso completo de preparación
    # =========================================================================

    def prepare_complete(
        self,
        output_dir: Path,
        force_download: bool = False,
    ) -> dict[str, Any]:
        """Ejecuta el proceso completo de preparación (Fase 7).

        Args:
            output_dir: Directorio de salida para LoRA
            force_download: Forzar descarga de modelo

        Returns:
            Resumen completo de la preparación
        """
        logger.info(f"[LoRA Prep] Iniciando Fase 7 (mode={self.training_mode})")

        summary = {
            "training_mode": self.training_mode,
            "subfases": {},
        }

        # 7.1: Verificar dependencias
        deps = self.verify_dependencies()
        summary["subfases"]["7.1"] = deps

        # 7.2: Obtener modelo base
        model_info = self.obtain_base_model(force_download=force_download)
        summary["subfases"]["7.2"] = model_info

        # 7.3: Configurar LoRA
        lora_config = self.configure_lora_parameters()
        summary["subfases"]["7.3"] = lora_config

        # 7.4: Preparar entorno
        env_info = self.prepare_training_environment(output_dir)
        summary["subfases"]["7.4"] = env_info

        summary["status"] = "completed"
        summary["model_path"] = model_info["path"]
        summary["lora_config"] = lora_config
        summary["output_dir"] = str(output_dir)

        logger.info("[LoRA Prep] Fase 7 completada ✓")

        return summary


# =============================================================================
# Helper: Verificar si Ollama tiene el modelo
# =============================================================================

def check_ollama_model_available(
    model_name: str,
    ollama_url: str = "http://localhost:11434",
) -> bool:
    """Verifica si un modelo está disponible en Ollama.

    Args:
        model_name: Nombre del modelo (ej: "deepseek-r1:8b")
        ollama_url: URL de Ollama

    Returns:
        True si el modelo está disponible
    """
    try:
        client = httpx.Client(timeout=10.0)
        response = client.get(f"{ollama_url}/api/tags")
        response.raise_for_status()

        data = response.json()
        models = [m["name"] for m in data.get("models", [])]

        return model_name in models

    except Exception as e:
        logger.warning(f"Error verificando modelo en Ollama: {e}")
        return False
    finally:
        client.close()
