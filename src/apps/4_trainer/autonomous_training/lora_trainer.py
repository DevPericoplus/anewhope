"""Entrenamiento con LoRA (Low-Rank Adaptation).

Este módulo implementa la Fase 8 del proceso de entrenamiento autónomo:
- Inicialización del trainer con dataset
- Ejecución de epochs con actualización de métricas
- Evaluación del modelo fine-tuned
- Guardado de adaptadores LoRA
- Validación de resultados

Autor: Sistema anewhope
Fecha: 2026-02-13
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import torch
from datasets import load_dataset
from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    TrainerCallback,
)


logger = logging.getLogger(__name__)


class LoRATrainingError(Exception):
    """Error durante el entrenamiento LoRA."""


class ProgressCallback(TrainerCallback):
    """Callback para reportar progreso durante el entrenamiento.

    Permite actualizar la base de datos con métricas en tiempo real.
    """

    def __init__(
        self,
        progress_handler: Callable[[dict[str, Any]], None] | None = None,
    ):
        """Inicializa el callback.

        Args:
            progress_handler: Función que recibe métricas y las procesa
        """
        self.progress_handler = progress_handler
        self.start_time = time.time()

    def on_log(self, args, state, control, logs=None, **kwargs):
        """Llamado cuando se registran métricas."""
        if logs and self.progress_handler:
            # Añadir timestamp y step
            logs["timestamp"] = datetime.now().isoformat()
            logs["current_step"] = state.global_step
            logs["total_steps"] = state.max_steps

            # Calcular progreso
            if state.max_steps > 0:
                logs["progress_pct"] = round(
                    (state.global_step / state.max_steps) * 100, 2
                )

            # Tiempo transcurrido
            elapsed = time.time() - self.start_time
            logs["elapsed_seconds"] = int(elapsed)

            self.progress_handler(logs)

    def on_epoch_end(self, args, state, control, **kwargs):
        """Llamado al finalizar cada epoch."""
        if self.progress_handler:
            self.progress_handler({
                "event": "epoch_completed",
                "epoch": state.epoch,
                "global_step": state.global_step,
            })


class LoRATrainer:
    """Entrenador con LoRA para fine-tuning eficiente.

    Implementa fine-tuning usando PEFT (Parameter-Efficient Fine-Tuning)
    con adaptadores LoRA para reducir uso de memoria y tiempo.
    """

    def __init__(
        self,
        id_entrenamiento: int,
        model_path: str,
        dataset_path: str,
        output_dir: Path,
        lora_config: dict[str, Any],
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ):
        """Inicializa el trainer LoRA.

        Args:
            id_entrenamiento: ID del entrenamiento
            model_path: Ruta del modelo base
            dataset_path: Ruta del dataset JSONL
            output_dir: Directorio de salida
            lora_config: Configuración LoRA
            progress_callback: Callback para reportar progreso
        """
        self.id_entrenamiento = id_entrenamiento
        self.model_path = model_path
        self.dataset_path = dataset_path
        self.output_dir = Path(output_dir)
        self.lora_config = lora_config
        self.progress_callback = progress_callback

        self.model = None
        self.tokenizer = None
        self.trainer = None

        logger.info(
            f"[LoRA Trainer] Inicializado para entrenamiento {id_entrenamiento}"
        )

    # =========================================================================
    # Subfase 8.1: Inicializar trainer
    # =========================================================================

    def initialize_trainer(self) -> dict[str, Any]:
        """Inicializa el trainer con modelo, tokenizer y dataset.

        Returns:
            Información de inicialización
        """
        logger.info("[8.1] Inicializando trainer...")

        # Cargar tokenizer
        logger.info(f"[8.1] Cargando tokenizer desde {self.model_path}")
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path,
            trust_remote_code=True,
        )

        # Configurar pad token si no existe
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Cargar modelo base
        logger.info(f"[8.1] Cargando modelo base desde {self.model_path}")

        # Configurar device según plataforma
        if torch.cuda.is_available():
            device_map = "auto"
            torch_dtype = torch.float16
        elif torch.backends.mps.is_available():
            device_map = "mps"
            torch_dtype = torch.float32
        else:
            device_map = "cpu"
            torch_dtype = torch.float32

        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            device_map=device_map,
            torch_dtype=torch_dtype,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )

        # Preparar modelo para LoRA
        if torch.cuda.is_available():
            self.model = prepare_model_for_kbit_training(self.model)

        # Configurar LoRA
        logger.info(f"[8.1] Configurando LoRA: rank={self.lora_config['r']}")

        peft_config = LoraConfig(
            r=self.lora_config["r"],
            lora_alpha=self.lora_config["lora_alpha"],
            lora_dropout=self.lora_config["lora_dropout"],
            target_modules=self.lora_config["target_modules"],
            bias=self.lora_config["bias"],
            task_type=self.lora_config["task_type"],
        )

        self.model = get_peft_model(self.model, peft_config)

        # Imprimir parámetros entrenables
        trainable_params = sum(
            p.numel() for p in self.model.parameters() if p.requires_grad
        )
        total_params = sum(p.numel() for p in self.model.parameters())
        trainable_pct = 100 * trainable_params / total_params

        logger.info(
            f"[8.1] Parámetros entrenables: {trainable_params:,} "
            f"({trainable_pct:.2f}% del total)"
        )

        # Cargar dataset
        logger.info(f"[8.1] Cargando dataset desde {self.dataset_path}")

        dataset = load_dataset("json", data_files=str(self.dataset_path))
        train_dataset = dataset["train"]

        # Tokenizar dataset
        logger.info("[8.1] Tokenizando dataset...")

        def tokenize_function(examples):
            """Tokeniza ejemplos del dataset."""
            # Combinar instruction + output
            prompts = []
            for inst, inp, out in zip(
                examples["instruction"],
                examples["input"],
                examples["output"],
            ):
                if inp:
                    prompt = f"Instrucción: {inst}\nEntrada: {inp}\nRespuesta: {out}"
                else:
                    prompt = f"Instrucción: {inst}\nRespuesta: {out}"
                prompts.append(prompt)

            # Tokenizar
            tokenized = self.tokenizer(
                prompts,
                padding="max_length",
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )

            # Labels = input_ids (para causal LM)
            tokenized["labels"] = tokenized["input_ids"].clone()

            return tokenized

        tokenized_dataset = train_dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=train_dataset.column_names,
        )

        # Configurar argumentos de entrenamiento
        training_args = TrainingArguments(
            output_dir=str(self.output_dir / "checkpoints"),
            num_train_epochs=self.lora_config["epochs"],
            per_device_train_batch_size=self.lora_config["batch_size"],
            learning_rate=self.lora_config["learning_rate"],
            max_steps=self.lora_config.get("max_steps", -1),
            save_steps=self.lora_config.get("save_steps", 100),
            logging_steps=self.lora_config.get("logging_steps", 10),
            logging_dir=str(self.output_dir / "logs"),
            save_total_limit=2,
            load_best_model_at_end=False,
            report_to="none",  # No usar wandb/tensorboard
            remove_unused_columns=False,
        )

        # Crear callback de progreso
        progress_cb = ProgressCallback(self.progress_callback)

        # Crear Trainer
        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=tokenized_dataset,
            callbacks=[progress_cb],
        )

        init_info = {
            "model_path": self.model_path,
            "dataset_size": len(train_dataset),
            "tokenized_size": len(tokenized_dataset),
            "trainable_params": trainable_params,
            "trainable_pct": round(trainable_pct, 2),
            "device": str(device_map),
            "dtype": str(torch_dtype),
        }

        logger.info("[8.1] Trainer inicializado ✓")

        return init_info

    # =========================================================================
    # Subfase 8.2-8.3: Ejecutar entrenamiento
    # =========================================================================

    def execute_training(self) -> dict[str, Any]:
        """Ejecuta el entrenamiento LoRA completo.

        Returns:
            Métricas del entrenamiento
        """
        logger.info("[8.2-8.3] Ejecutando entrenamiento LoRA...")

        start_time = time.time()

        try:
            # Entrenar
            train_result = self.trainer.train()

            elapsed = time.time() - start_time

            metrics = {
                "status": "completed",
                "elapsed_seconds": int(elapsed),
                "final_loss": train_result.training_loss,
                "steps": train_result.global_step,
                "epochs_completed": self.lora_config["epochs"],
            }

            logger.info(
                f"[8.3] Entrenamiento completado: "
                f"loss={metrics['final_loss']:.4f}, "
                f"tiempo={elapsed:.0f}s"
            )

            return metrics

        except Exception as e:
            logger.error(f"[8.2-8.3] Error en entrenamiento: {e}", exc_info=True)
            raise LoRATrainingError(f"Error en entrenamiento: {e}") from e

    # =========================================================================
    # Subfase 8.4: Evaluar modelo
    # =========================================================================

    def evaluate_model(self) -> dict[str, Any]:
        """Evalúa el modelo fine-tuned.

        Returns:
            Métricas de evaluación
        """
        logger.info("[8.4] Evaluando modelo fine-tuned...")

        # Para este sprint: evaluación básica
        # En producción: se podría usar un validation set

        eval_metrics = {
            "status": "evaluated",
            "method": "training_loss",
            "note": "Evaluación completa disponible con validation set",
        }

        logger.info("[8.4] Evaluación completada")

        return eval_metrics

    # =========================================================================
    # Subfase 8.5: Guardar adaptadores LoRA
    # =========================================================================

    def save_lora_adapters(self) -> dict[str, Any]:
        """Guarda los adaptadores LoRA entrenados.

        Returns:
            Información de los adaptadores guardados
        """
        logger.info("[8.5] Guardando adaptadores LoRA...")

        adapters_dir = self.output_dir / "lora_adapters"
        adapters_dir.mkdir(exist_ok=True)

        # Guardar adaptadores
        self.model.save_pretrained(adapters_dir)

        # Guardar tokenizer
        self.tokenizer.save_pretrained(adapters_dir)

        # Calcular tamaño
        total_size = sum(
            f.stat().st_size
            for f in adapters_dir.rglob("*")
            if f.is_file()
        )
        size_mb = total_size / (1024 * 1024)

        save_info = {
            "path": str(adapters_dir),
            "size_mb": round(size_mb, 2),
            "files": len(list(adapters_dir.rglob("*"))),
        }

        logger.info(
            f"[8.5] Adaptadores guardados: {size_mb:.2f} MB en {adapters_dir}"
        )

        return save_info

    # =========================================================================
    # Subfase 8.6: Validar resultados
    # =========================================================================

    def validate_results(self) -> dict[str, Any]:
        """Valida que el entrenamiento produjo resultados válidos.

        Returns:
            Estado de validación
        """
        logger.info("[8.6] Validando resultados...")

        adapters_dir = self.output_dir / "lora_adapters"

        # Verificar archivos esenciales
        required_files = [
            "adapter_config.json",
            "adapter_model.safetensors",
        ]

        validation = {
            "all_valid": True,
            "files_checked": [],
            "missing_files": [],
        }

        for filename in required_files:
            filepath = adapters_dir / filename
            if filepath.exists():
                validation["files_checked"].append(filename)
            else:
                validation["missing_files"].append(filename)
                validation["all_valid"] = False

        if not validation["all_valid"]:
            logger.error(
                f"[8.6] Validación fallida: archivos faltantes "
                f"{validation['missing_files']}"
            )
            raise LoRATrainingError(
                f"Archivos faltantes: {validation['missing_files']}"
            )

        logger.info("[8.6] Validación exitosa ✓")

        return validation

    # =========================================================================
    # Proceso completo
    # =========================================================================

    def train_complete(self) -> dict[str, Any]:
        """Ejecuta el proceso completo de entrenamiento (Fase 8).

        Returns:
            Resumen completo del entrenamiento
        """
        logger.info("[LoRA Trainer] Iniciando Fase 8: Entrenamiento LoRA")

        summary = {
            "id_entrenamiento": self.id_entrenamiento,
            "subfases": {},
        }

        # 8.1: Inicializar
        init_info = self.initialize_trainer()
        summary["subfases"]["8.1"] = init_info

        # 8.2-8.3: Entrenar
        training_metrics = self.execute_training()
        summary["subfases"]["8.2-8.3"] = training_metrics

        # 8.4: Evaluar
        eval_metrics = self.evaluate_model()
        summary["subfases"]["8.4"] = eval_metrics

        # 8.5: Guardar adaptadores
        save_info = self.save_lora_adapters()
        summary["subfases"]["8.5"] = save_info

        # 8.6: Validar
        validation = self.validate_results()
        summary["subfases"]["8.6"] = validation

        summary["status"] = "completed"
        summary["adapters_path"] = save_info["path"]
        summary["training_time"] = training_metrics["elapsed_seconds"]
        summary["final_loss"] = training_metrics["final_loss"]

        logger.info("[LoRA Trainer] Fase 8 completada ✓")

        return summary

    def cleanup(self):
        """Libera recursos del modelo."""
        if self.model is not None:
            del self.model
            self.model = None

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("[LoRA Trainer] Recursos liberados")
