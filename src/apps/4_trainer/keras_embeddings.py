"""Wrapper Keras/TF-Hub para generar embeddings compatibles con LangChain.

Implementa la interfaz ``langchain_core.embeddings.Embeddings`` usando el
modelo Universal Sentence Encoder (USE) de TensorFlow Hub, generando vectores
de 512 dimensiones.

Arquitectura:
    LangChain → KerasEmbeddings → TensorFlow Hub (USE) → Vectores 512-d

Uso:
    from keras_embeddings import KerasEmbeddings

    embeddings = KerasEmbeddings()
    vectors = embeddings.embed_documents(["Hola mundo", "Otro texto"])
    query_vec = embeddings.embed_query("Pregunta de búsqueda")
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import tensorflow_hub as hub
from langchain_core.embeddings import Embeddings

logger = logging.getLogger("trainer_api")

# URL del modelo Universal Sentence Encoder v4 en TF Hub
_DEFAULT_MODEL_URL = "https://tfhub.dev/google/universal-sentence-encoder/4"

# Dimensión de salida del modelo USE v4
USE_EMBEDDING_DIMENSION = 512

# Tamaño de lote para procesar documentos largos
_DEFAULT_BATCH_SIZE = 64


class KerasEmbeddings(Embeddings):
    """Generador de embeddings basado en Keras/TF-Hub Universal Sentence Encoder.

    Envuelve el modelo USE de TensorFlow Hub para generar vectores de 512
    dimensiones compatibles con la interfaz ``Embeddings`` de LangChain.

    Attributes:
        _model: Modelo USE cargado desde TF Hub.
        _model_url: URL del modelo en TF Hub.
        _batch_size: Tamaño de lote para embed_documents.
    """

    def __init__(
        self,
        model_url: str = _DEFAULT_MODEL_URL,
        batch_size: int = _DEFAULT_BATCH_SIZE,
    ) -> None:
        """Inicializa el wrapper cargando el modelo USE desde TF Hub.

        Args:
            model_url: URL del modelo en TensorFlow Hub.
            batch_size: Tamaño de lote para procesar documentos.
        """
        self._model_url = model_url
        self._batch_size = batch_size
        self._model: Any = None

        logger.info(
            "[KERAS-EMB] Cargando modelo USE desde %s (batch_size=%d)",
            model_url,
            batch_size,
        )

        try:
            self._model = hub.load(model_url)
            logger.info(
                "[KERAS-EMB] Modelo USE cargado correctamente (dim=%d)",
                USE_EMBEDDING_DIMENSION,
            )
        except Exception as exc:
            logger.error(
                "[KERAS-EMB] Error cargando modelo USE: %s",
                exc,
                exc_info=True,
            )
            raise RuntimeError(
                f"No se pudo cargar el modelo USE desde {model_url}: {exc}"
            ) from exc

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Genera embeddings para una lista de documentos.

        Procesa los textos en lotes para evitar problemas de memoria
        con listas muy largas.

        Args:
            texts: Lista de textos a vectorizar.

        Returns:
            Lista de vectores (cada uno de 512 dimensiones).
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        # Procesar en lotes para gestionar memoria
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            batch_embeddings = self._model(batch).numpy()
            all_embeddings.extend(batch_embeddings.tolist())

            if len(texts) > self._batch_size:
                logger.debug(
                    "[KERAS-EMB] Lote %d/%d procesado (%d textos)",
                    (i // self._batch_size) + 1,
                    (len(texts) + self._batch_size - 1) // self._batch_size,
                    len(batch),
                )

        logger.info(
            "[KERAS-EMB] %d documentos vectorizados (dim=%d)",
            len(all_embeddings),
            USE_EMBEDDING_DIMENSION,
        )

        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        """Genera un embedding para una consulta de búsqueda.

        Args:
            text: Texto de la consulta.

        Returns:
            Vector de 512 dimensiones.
        """
        embedding: np.ndarray = self._model([text]).numpy()[0]
        return embedding.tolist()

    @property
    def dimension(self) -> int:
        """Retorna la dimensión de los embeddings generados."""
        return USE_EMBEDDING_DIMENSION

    def __repr__(self) -> str:
        return (
            f"KerasEmbeddings(model_url='{self._model_url}', "
            f"dim={USE_EMBEDDING_DIMENSION}, batch_size={self._batch_size})"
        )
