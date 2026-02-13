"""Generador de Dataset para Fine-Tuning LoRA.

Este módulo implementa la Fase 6 del proceso de entrenamiento autónomo:
- Recupera chunks procesados en la fase RAG
- Genera preguntas usando templates predefinidos
- Genera Q&A adicionales con LLM (Ollama)
- Formatea el dataset en JSONL para LoRA
- Actualiza progreso en base de datos

Autor: Sistema anewhope
Fecha: 2026-02-13
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class DatasetGenerationError(Exception):
    """Error durante la generación del dataset."""


class DatasetGenerator:
    """Generador de dataset Q&A para fine-tuning LoRA.

    Implementa estrategia híbrida:
    1. Templates predefinidos (control de calidad)
    2. Generación automática con LLM (diversidad)
    """

    # Templates de preguntas predefinidos
    QUESTION_TEMPLATES = [
        "¿Qué información contiene este documento sobre {topic}?",
        "Explica el concepto de {topic} según la documentación",
        "¿Cuál es el propósito de {topic} descrito en el documento?",
        "Describe las características de {topic}",
        "¿Cómo funciona {topic} según la documentación?",
        "Resume la información sobre {topic}",
        "¿Qué detalles importantes menciona el documento sobre {topic}?",
        "Define {topic} basándote en la documentación",
    ]

    # Prompt para generación automática con LLM
    QA_GENERATION_PROMPT = """Eres un experto en crear preguntas y respuestas educativas.

Dado el siguiente fragmento de documentación, genera 2 preguntas diferentes que un usuario podría hacer sobre este contenido.

FRAGMENTO:
{chunk_text}

INSTRUCCIONES:
1. Las preguntas deben ser naturales y variadas
2. Evita preguntas genéricas como "¿De qué trata esto?"
3. Enfócate en detalles específicos del fragmento
4. No repitas las preguntas que ya incluyo abajo

PREGUNTAS EXISTENTES (no repitas estas):
{existing_questions}

Genera SOLO 2 preguntas nuevas, una por línea, sin numeración ni formato adicional.
"""

    def __init__(
        self,
        id_entrenamiento: int,
        ollama_base_url: str = "http://localhost:11434",
        ollama_model: str = "deepseek-r1:8b",
    ):
        """Inicializa el generador de dataset.

        Args:
            id_entrenamiento: ID del entrenamiento en curso
            ollama_base_url: URL base del servidor Ollama
            ollama_model: Modelo a usar para generación automática
        """
        self.id_entrenamiento = id_entrenamiento
        self.ollama_base_url = ollama_base_url.rstrip("/")
        self.ollama_model = ollama_model
        self.http_client = httpx.Client(timeout=60.0)

        logger.info(
            f"[Dataset Generator] Inicializado para entrenamiento {id_entrenamiento}"
        )

    def close(self):
        """Cierra el cliente HTTP."""
        self.http_client.close()

    # =========================================================================
    # Subfase 6.1: Analizar chunks disponibles
    # =========================================================================

    def analyze_chunks(self, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        """Analiza los chunks disponibles para el dataset.

        Args:
            chunks: Lista de chunks con formato:
                    [{"id": str, "text": str, "metadata": dict}, ...]

        Returns:
            Estadísticas de los chunks:
            {
                "total_chunks": int,
                "total_chars": int,
                "avg_chunk_size": float,
                "topics_detected": list[str],
            }
        """
        logger.info("[6.1] Analizando chunks disponibles...")

        if not chunks:
            raise DatasetGenerationError("No hay chunks disponibles para análisis")

        total_chars = sum(len(chunk.get("text", "")) for chunk in chunks)
        avg_size = total_chars / len(chunks) if chunks else 0

        # Detectar topics básicos (primeras palabras de cada chunk)
        topics = []
        for chunk in chunks[:10]:  # Limitar análisis a primeros 10
            text = chunk.get("text", "")
            words = text.split()[:5]  # Primeras 5 palabras
            if words:
                topics.append(" ".join(words))

        stats = {
            "total_chunks": len(chunks),
            "total_chars": total_chars,
            "avg_chunk_size": round(avg_size, 2),
            "topics_detected": topics[:5],  # Top 5
        }

        logger.info(
            f"[6.1] Análisis completo: {stats['total_chunks']} chunks, "
            f"{stats['avg_chunk_size']} chars promedio"
        )

        return stats

    # =========================================================================
    # Subfase 6.2: Generar plantillas de preguntas
    # =========================================================================

    def generate_template_questions(
        self,
        chunks: list[dict[str, Any]],
        max_per_chunk: int = 2,
    ) -> list[dict[str, str]]:
        """Genera preguntas usando templates predefinidos.

        Args:
            chunks: Lista de chunks
            max_per_chunk: Máximo de preguntas por chunk

        Returns:
            Lista de ejemplos Q&A:
            [{"instruction": str, "input": "", "output": str}, ...]
        """
        logger.info("[6.2] Generando preguntas desde templates...")

        examples = []

        for chunk in chunks:
            chunk_text = chunk.get("text", "").strip()
            if not chunk_text:
                continue

            # Extraer topic del chunk (primeras palabras significativas)
            words = [w for w in chunk_text.split() if len(w) > 3]
            topic = " ".join(words[:3]) if words else "el contenido"

            # Generar preguntas con templates (máximo max_per_chunk)
            templates_used = 0
            for template in self.QUESTION_TEMPLATES:
                if templates_used >= max_per_chunk:
                    break

                question = template.format(topic=topic)

                examples.append({
                    "instruction": question,
                    "input": "",
                    "output": chunk_text,
                })

                templates_used += 1

        logger.info(f"[6.2] Generadas {len(examples)} preguntas desde templates")

        return examples

    # =========================================================================
    # Subfase 6.3: Generar Q&A con LLM
    # =========================================================================

    def generate_llm_questions(
        self,
        chunks: list[dict[str, Any]],
        existing_questions: list[str],
        max_per_chunk: int = 2,
    ) -> list[dict[str, str]]:
        """Genera preguntas automáticamente usando Ollama.

        Args:
            chunks: Lista de chunks
            existing_questions: Preguntas ya generadas (para evitar duplicados)
            max_per_chunk: Máximo de preguntas nuevas por chunk

        Returns:
            Lista de ejemplos Q&A adicionales
        """
        logger.info("[6.3] Generando preguntas con LLM (Ollama)...")

        examples = []

        for i, chunk in enumerate(chunks):
            chunk_text = chunk.get("text", "").strip()
            if not chunk_text:
                continue

            # Limitar a un subconjunto para no sobrecargar
            if i >= 50:  # Máximo 50 chunks con LLM
                logger.info("[6.3] Límite de chunks alcanzado (50), continuando...")
                break

            try:
                # Crear prompt con preguntas existentes
                existing_str = "\n".join(existing_questions[-5:])  # Últimas 5
                prompt = self.QA_GENERATION_PROMPT.format(
                    chunk_text=chunk_text[:500],  # Limitar tamaño
                    existing_questions=existing_str,
                )

                # Llamar a Ollama
                questions = self._call_ollama_generate(prompt)

                # Parsear respuesta (cada línea es una pregunta)
                new_questions = [
                    q.strip()
                    for q in questions.split("\n")
                    if q.strip() and not q.strip().startswith("#")
                ][:max_per_chunk]

                # Crear ejemplos Q&A
                for question in new_questions:
                    examples.append({
                        "instruction": question,
                        "input": "",
                        "output": chunk_text,
                    })
                    existing_questions.append(question)

            except Exception as e:
                logger.warning(
                    f"[6.3] Error generando preguntas para chunk {i}: {e}"
                )
                continue

        logger.info(f"[6.3] Generadas {len(examples)} preguntas con LLM")

        return examples

    def _call_ollama_generate(self, prompt: str) -> str:
        """Llama a Ollama para generar texto.

        Args:
            prompt: Prompt para el modelo

        Returns:
            Texto generado
        """
        url = f"{self.ollama_base_url}/api/generate"
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": 200,
            },
        }

        response = self.http_client.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        return data.get("response", "").strip()

    # =========================================================================
    # Subfase 6.4: Validar y formatear dataset
    # =========================================================================

    def validate_and_format_dataset(
        self,
        examples: list[dict[str, str]],
    ) -> tuple[list[dict[str, str]], dict[str, Any]]:
        """Valida y formatea el dataset para LoRA.

        Args:
            examples: Lista de ejemplos Q&A

        Returns:
            Tuple (ejemplos_validados, estadísticas)
        """
        logger.info("[6.4] Validando y formateando dataset...")

        validated = []
        errors = []

        for i, example in enumerate(examples):
            # Validar estructura
            if not all(k in example for k in ["instruction", "input", "output"]):
                errors.append(f"Ejemplo {i}: falta campos requeridos")
                continue

            # Validar contenido no vacío
            if not example["instruction"].strip():
                errors.append(f"Ejemplo {i}: instruction vacío")
                continue

            if not example["output"].strip():
                errors.append(f"Ejemplo {i}: output vacío")
                continue

            # Validar longitud mínima
            if len(example["output"]) < 50:
                errors.append(f"Ejemplo {i}: output muy corto (<50 chars)")
                continue

            validated.append(example)

        stats = {
            "total_examples": len(examples),
            "valid_examples": len(validated),
            "invalid_examples": len(errors),
            "errors": errors[:10],  # Primeros 10 errores
        }

        if errors:
            logger.warning(
                f"[6.4] {len(errors)} ejemplos inválidos encontrados"
            )

        logger.info(
            f"[6.4] Validación completa: {len(validated)}/{len(examples)} válidos"
        )

        return validated, stats

    # =========================================================================
    # Subfase 6.5: Guardar dataset
    # =========================================================================

    def save_dataset(
        self,
        examples: list[dict[str, str]],
        output_path: Path,
    ) -> dict[str, Any]:
        """Guarda el dataset en formato JSONL.

        Args:
            examples: Ejemplos validados
            output_path: Ruta del archivo JSONL de salida

        Returns:
            Metadatos del archivo guardado
        """
        logger.info(f"[6.5] Guardando dataset en {output_path}...")

        # Crear directorio si no existe
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Escribir JSONL (una línea por ejemplo)
        with open(output_path, "w", encoding="utf-8") as f:
            for example in examples:
                json_line = json.dumps(example, ensure_ascii=False)
                f.write(json_line + "\n")

        # Calcular metadatos
        file_size = output_path.stat().st_size

        metadata = {
            "path": str(output_path),
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "num_examples": len(examples),
            "created_at": datetime.now().isoformat(),
        }

        logger.info(
            f"[6.5] Dataset guardado: {metadata['num_examples']} ejemplos, "
            f"{metadata['size_mb']} MB"
        )

        return metadata

    # =========================================================================
    # Proceso completo
    # =========================================================================

    def generate_complete_dataset(
        self,
        chunks: list[dict[str, Any]],
        output_path: Path,
        training_mode: str = "simulation",
    ) -> dict[str, Any]:
        """Ejecuta el proceso completo de generación de dataset.

        Args:
            chunks: Chunks desde ChromaDB/BD
            output_path: Ruta del dataset JSONL
            training_mode: Modo de entrenamiento (simulation/test/production)

        Returns:
            Resumen completo del proceso
        """
        logger.info(
            f"[Dataset Generation] Iniciando proceso completo "
            f"(mode={training_mode})"
        )

        # 6.1: Analizar chunks
        chunk_stats = self.analyze_chunks(chunks)

        # 6.2: Generar con templates
        if training_mode == "simulation":
            # En simulation: solo 1 pregunta por chunk
            template_examples = self.generate_template_questions(chunks, max_per_chunk=1)
            llm_examples = []  # No usar LLM en simulation
        elif training_mode == "test":
            # En test: 2 templates + 1 LLM
            template_examples = self.generate_template_questions(chunks, max_per_chunk=2)
            existing_questions = [ex["instruction"] for ex in template_examples]
            llm_examples = self.generate_llm_questions(
                chunks[:50],  # Máximo 50 chunks
                existing_questions,
                max_per_chunk=1,
            )
        else:  # production
            # En production: 3 templates + 2 LLM
            template_examples = self.generate_template_questions(chunks, max_per_chunk=3)
            existing_questions = [ex["instruction"] for ex in template_examples]
            llm_examples = self.generate_llm_questions(
                chunks,  # Todos los chunks
                existing_questions,
                max_per_chunk=2,
            )

        # Combinar ejemplos
        all_examples = template_examples + llm_examples

        # 6.4: Validar y formatear
        validated_examples, validation_stats = self.validate_and_format_dataset(
            all_examples
        )

        # 6.5: Guardar dataset
        file_metadata = self.save_dataset(validated_examples, output_path)

        # Resumen completo
        summary = {
            "training_mode": training_mode,
            "chunk_stats": chunk_stats,
            "generation_stats": {
                "template_examples": len(template_examples),
                "llm_examples": len(llm_examples),
                "total_generated": len(all_examples),
            },
            "validation_stats": validation_stats,
            "file_metadata": file_metadata,
        }

        logger.info(
            f"[Dataset Generation] Proceso completo: "
            f"{file_metadata['num_examples']} ejemplos válidos generados"
        )

        return summary


# =============================================================================
# Helper: Recuperar chunks desde ChromaDB/BD
# =============================================================================

def get_chunks_from_collection(
    collection_name: str,
    chroma_host: str = "localhost",
    chroma_port: int = 8100,
) -> list[dict[str, Any]]:
    """Recupera todos los chunks de una colección de ChromaDB.

    Args:
        collection_name: Nombre de la colección
        chroma_host: Host de ChromaDB
        chroma_port: Puerto de ChromaDB

    Returns:
        Lista de chunks con formato:
        [{"id": str, "text": str, "metadata": dict}, ...]
    """
    import chromadb

    logger.info(f"Recuperando chunks de colección: {collection_name}")

    client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
    collection = client.get_collection(name=collection_name)

    # Obtener todos los documentos
    results = collection.get(include=["documents", "metadatas"])

    chunks = []
    for i, doc in enumerate(results["documents"]):
        chunks.append({
            "id": results["ids"][i] if "ids" in results else str(i),
            "text": doc,
            "metadata": results["metadatas"][i] if "metadatas" in results else {},
        })

    logger.info(f"Recuperados {len(chunks)} chunks de ChromaDB")

    return chunks
