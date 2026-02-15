"""
Sistema de Optimización Automática de Hiperparámetros de Entrenamiento

Este módulo analiza los resultados de entrenamientos y genera sugerencias
inteligentes de hiperparámetros para mejorar el rendimiento en la siguiente
iteración.

Estrategias implementadas:
- Análisis de convergencia y ajuste de learning rate
- Detección de overfitting/underfitting y ajuste de regularización
- Optimización de parámetros RAG según precision/recall
- Balance memoria vs calidad (embedding dimensions, batch size)
- Análisis de interacciones entre parámetros
"""

from dataclasses import dataclass
from typing import Any, Optional
from decimal import Decimal
import math


@dataclass
class TrainingMetrics:
    """Métricas observadas de un entrenamiento."""
    loss_inicial: Optional[float] = None
    loss_final: Optional[float] = None
    loss_promedio: Optional[float] = None
    loss_minimo: Optional[float] = None
    epoca_mejor_loss: Optional[int] = None

    accuracy_validacion: Optional[float] = None
    f1_score: Optional[float] = None
    precision_score: Optional[float] = None
    recall_score: Optional[float] = None

    retrieval_precision: Optional[float] = None
    retrieval_recall: Optional[float] = None
    avg_similarity_score: Optional[float] = None

    perplexity: Optional[float] = None
    bleu_score: Optional[float] = None
    rouge_l_score: Optional[float] = None

    tiempo_entrenamiento_seg: Optional[int] = None
    tokens_procesados: Optional[int] = None
    tokens_por_segundo: Optional[float] = None
    memoria_pico_mb: Optional[int] = None

    overfitting_detectado: bool = False
    underfitting_detectado: bool = False
    convergencia_lenta: bool = False
    gradientes_explosivos: bool = False


@dataclass
class TrainingParams:
    """Parámetros de entrenamiento actuales."""
    learning_rate: Decimal
    batch_size: int
    epochs: int
    embedding_dimension: int
    sequence_length: int
    hidden_units: int
    dropout_rate: Decimal

    distance_metric: str
    top_k: int
    chunk_size: int
    chunk_overlap: int

    temperature: Decimal
    max_tokens: int

    loss_function: str
    optimizer: str


@dataclass
class ParameterSuggestion:
    """Sugerencia de cambio en un parámetro."""
    valor_sugerido: Any
    cambio: str  # "aumentar", "disminuir", "mantener", "cambiar"
    razon: str
    impacto_esperado: str  # "alto", "medio", "bajo"
    prioridad: int  # 1=crítico, 2=importante, 3=opcional


class TrainingOptimizer:
    """
    Optimizador de hiperparámetros basado en análisis de resultados.

    Implementa heurísticas y reglas para sugerir mejoras en los parámetros
    de entrenamiento basándose en las métricas observadas.
    """

    def __init__(self):
        # Rangos válidos para cada parámetro
        self.param_ranges = {
            'learning_rate': (1e-6, 1e-1),
            'batch_size': (1, 512),
            'epochs': (1, 1000),
            'embedding_dimension': (64, 2048),
            'sequence_length': (64, 4096),
            'hidden_units': (32, 2048),
            'dropout_rate': (0.0, 0.9),
            'top_k': (1, 50),
            'chunk_size': (100, 5000),
            'chunk_overlap': (0, 500),
            'temperature': (0.0, 2.0),
            'max_tokens': (128, 8192),
        }

    def generate_suggestions(
        self,
        params: TrainingParams,
        metrics: TrainingMetrics
    ) -> dict[str, ParameterSuggestion]:
        """
        Genera sugerencias de optimización basadas en métricas.

        Returns:
            Dict con nombre del parámetro como key y ParameterSuggestion como value
        """
        suggestions = {}

        # Analizar cada grupo de parámetros
        suggestions.update(self._analyze_learning_rate(params, metrics))
        suggestions.update(self._analyze_batch_size(params, metrics))
        suggestions.update(self._analyze_epochs(params, metrics))
        suggestions.update(self._analyze_regularization(params, metrics))
        suggestions.update(self._analyze_model_capacity(params, metrics))
        suggestions.update(self._analyze_rag_params(params, metrics))
        suggestions.update(self._analyze_generation_params(params, metrics))
        suggestions.update(self._analyze_optimizer(params, metrics))

        return suggestions

    def _analyze_learning_rate(
        self,
        params: TrainingParams,
        metrics: TrainingMetrics
    ) -> dict[str, ParameterSuggestion]:
        """
        Analiza y sugiere cambios en learning rate.

        Estrategia:
        - Gradientes explosivos → reducir LR significativamente
        - Convergencia lenta → aumentar LR moderadamente
        - Loss oscilante → reducir LR ligeramente
        - Convergencia rápida pero loss alto → puede estar en mínimo local, aumentar LR
        """
        lr = float(params.learning_rate)
        suggestions = {}

        # Caso 1: Gradientes explosivos
        if metrics.gradientes_explosivos:
            new_lr = max(lr * 0.1, self.param_ranges['learning_rate'][0])
            suggestions['learning_rate'] = ParameterSuggestion(
                valor_sugerido=Decimal(str(new_lr)),
                cambio="disminuir",
                razon="Gradientes explosivos detectados. Reducir LR 10x para estabilizar.",
                impacto_esperado="alto",
                prioridad=1
            )

        # Caso 2: Convergencia muy lenta
        elif metrics.convergencia_lenta:
            new_lr = min(lr * 2.0, self.param_ranges['learning_rate'][1])
            suggestions['learning_rate'] = ParameterSuggestion(
                valor_sugerido=Decimal(str(new_lr)),
                cambio="aumentar",
                razon="Convergencia lenta. Duplicar LR para acelerar aprendizaje.",
                impacto_esperado="alto",
                prioridad=1
            )

        # Caso 3: Mejora mínima entre épocas (posible estancamiento)
        elif metrics.loss_inicial and metrics.loss_final:
            mejora_pct = (metrics.loss_inicial - metrics.loss_final) / metrics.loss_inicial * 100
            if mejora_pct < 5 and not metrics.underfitting_detectado:
                # Poco progreso, puede estar en plateau
                new_lr = min(lr * 1.5, self.param_ranges['learning_rate'][1])
                suggestions['learning_rate'] = ParameterSuggestion(
                    valor_sugerido=Decimal(str(new_lr)),
                    cambio="aumentar",
                    razon=f"Mejora mínima ({mejora_pct:.1f}%). Aumentar LR 1.5x para salir del plateau.",
                    impacto_esperado="medio",
                    prioridad=2
                )

        # Caso 4: Loss final muy alto (no convergió bien)
        elif metrics.loss_final and metrics.loss_final > 2.0:
            # Probar con LR ligeramente mayor
            new_lr = min(lr * 1.2, self.param_ranges['learning_rate'][1])
            suggestions['learning_rate'] = ParameterSuggestion(
                valor_sugerido=Decimal(str(new_lr)),
                cambio="aumentar",
                razon=f"Loss final alto ({metrics.loss_final:.4f}). Aumentar LR 20% para mejor convergencia.",
                impacto_esperado="medio",
                prioridad=2
            )

        # Caso 5: Overfitting → reducir LR para aprendizaje más fino
        elif metrics.overfitting_detectado:
            new_lr = max(lr * 0.7, self.param_ranges['learning_rate'][0])
            suggestions['learning_rate'] = ParameterSuggestion(
                valor_sugerido=Decimal(str(new_lr)),
                cambio="disminuir",
                razon="Overfitting detectado. Reducir LR 30% para aprendizaje más controlado.",
                impacto_esperado="medio",
                prioridad=2
            )

        # Si no hay problemas evidentes, mantener
        if not suggestions:
            suggestions['learning_rate'] = ParameterSuggestion(
                valor_sugerido=params.learning_rate,
                cambio="mantener",
                razon="Learning rate actual muestra buen balance convergencia/estabilidad.",
                impacto_esperado="bajo",
                prioridad=3
            )

        return suggestions

    def _analyze_batch_size(
        self,
        params: TrainingParams,
        metrics: TrainingMetrics
    ) -> dict[str, ParameterSuggestion]:
        """
        Analiza y sugiere cambios en batch size.

        Estrategia:
        - Memoria insuficiente → reducir batch size
        - Entrenamiento muy lento → aumentar batch size
        - Gradientes ruidosos → aumentar batch size para mayor estabilidad
        - Generalización pobre → reducir batch size (batches más pequeños = más ruido = mejor generalización)
        """
        bs = params.batch_size
        suggestions = {}

        # Caso 1: Problemas de memoria
        if metrics.memoria_pico_mb and metrics.memoria_pico_mb > 14000:  # >14GB
            new_bs = max(bs // 2, self.param_ranges['batch_size'][0])
            suggestions['batch_size'] = ParameterSuggestion(
                valor_sugerido=new_bs,
                cambio="disminuir",
                razon=f"Uso alto de memoria ({metrics.memoria_pico_mb}MB). Reducir batch size 50%.",
                impacto_esperado="alto",
                prioridad=1
            )

        # Caso 2: Entrenamiento muy lento y hay margen de memoria
        elif metrics.tiempo_entrenamiento_seg and metrics.tiempo_entrenamiento_seg > 3600:  # >1 hora
            if not metrics.memoria_pico_mb or metrics.memoria_pico_mb < 8000:  # <8GB
                new_bs = min(bs * 2, self.param_ranges['batch_size'][1])
                suggestions['batch_size'] = ParameterSuggestion(
                    valor_sugerido=new_bs,
                    cambio="aumentar",
                    razon=f"Entrenamiento lento ({metrics.tiempo_entrenamiento_seg}s) con memoria disponible. Duplicar batch size.",
                    impacto_esperado="medio",
                    prioridad=2
                )

        # Caso 3: Overfitting → batches más pequeños para más ruido/regularización
        elif metrics.overfitting_detectado and bs > 16:
            new_bs = max(bs // 2, 8)
            suggestions['batch_size'] = ParameterSuggestion(
                valor_sugerido=new_bs,
                cambio="disminuir",
                razon="Overfitting detectado. Reducir batch size para añadir ruido regularizador.",
                impacto_esperado="medio",
                prioridad=2
            )

        # Caso 4: Convergencia inestable → aumentar batch size
        elif metrics.gradientes_explosivos:
            new_bs = min(bs * 2, self.param_ranges['batch_size'][1])
            suggestions['batch_size'] = ParameterSuggestion(
                valor_sugerido=new_bs,
                cambio="aumentar",
                razon="Gradientes explosivos. Aumentar batch size para mayor estabilidad.",
                impacto_esperado="medio",
                prioridad=2
            )

        if not suggestions:
            suggestions['batch_size'] = ParameterSuggestion(
                valor_sugerido=params.batch_size,
                cambio="mantener",
                razon="Batch size actual muestra buen balance eficiencia/rendimiento.",
                impacto_esperado="bajo",
                prioridad=3
            )

        return suggestions

    def _analyze_epochs(
        self,
        params: TrainingParams,
        metrics: TrainingMetrics
    ) -> dict[str, ParameterSuggestion]:
        """
        Analiza y sugiere cambios en número de épocas.

        Estrategia:
        - Si mejor loss fue en época temprana → reducir épocas (early stopping efectivo)
        - Si loss seguía bajando al final → aumentar épocas
        - Si overfitting en últimas épocas → reducir épocas
        """
        epochs = params.epochs
        suggestions = {}

        # Caso 1: Mejor loss en época temprana (overfitting después)
        if metrics.epoca_mejor_loss and metrics.epoca_mejor_loss < epochs * 0.6:
            new_epochs = int(metrics.epoca_mejor_loss * 1.2)  # 20% más que el mejor
            suggestions['epochs'] = ParameterSuggestion(
                valor_sugerido=new_epochs,
                cambio="disminuir",
                razon=f"Mejor loss en época {metrics.epoca_mejor_loss}/{epochs}. Reducir épocas para evitar overfitting.",
                impacto_esperado="medio",
                prioridad=2
            )

        # Caso 2: Loss seguía bajando al final
        elif metrics.loss_final and metrics.loss_minimo and metrics.loss_final <= metrics.loss_minimo * 1.02:
            # El loss al final es similar al mínimo → aún estaba mejorando
            new_epochs = min(int(epochs * 1.5), self.param_ranges['epochs'][1])
            suggestions['epochs'] = ParameterSuggestion(
                valor_sugerido=new_epochs,
                cambio="aumentar",
                razon="Loss seguía bajando al final. Aumentar épocas 50% para mayor convergencia.",
                impacto_esperado="medio",
                prioridad=2
            )

        # Caso 3: Convergencia muy lenta
        elif metrics.convergencia_lenta:
            new_epochs = min(int(epochs * 1.8), self.param_ranges['epochs'][1])
            suggestions['epochs'] = ParameterSuggestion(
                valor_sugerido=new_epochs,
                cambio="aumentar",
                razon="Convergencia lenta. Aumentar épocas 80% para permitir más aprendizaje.",
                impacto_esperado="alto",
                prioridad=1
            )

        if not suggestions:
            suggestions['epochs'] = ParameterSuggestion(
                valor_sugerido=params.epochs,
                cambio="mantener",
                razon="Número de épocas apropiado para la convergencia observada.",
                impacto_esperado="bajo",
                prioridad=3
            )

        return suggestions

    def _analyze_regularization(
        self,
        params: TrainingParams,
        metrics: TrainingMetrics
    ) -> dict[str, ParameterSuggestion]:
        """
        Analiza y sugiere cambios en dropout (regularización).

        Estrategia:
        - Overfitting → aumentar dropout
        - Underfitting → reducir dropout
        - Alta capacidad del modelo + overfitting → aumentar dropout agresivamente
        """
        dropout = float(params.dropout_rate)
        suggestions = {}

        # Caso 1: Overfitting fuerte
        if metrics.overfitting_detectado:
            if dropout < 0.3:
                new_dropout = min(dropout + 0.15, 0.5)
                suggestions['dropout_rate'] = ParameterSuggestion(
                    valor_sugerido=Decimal(str(new_dropout)),
                    cambio="aumentar",
                    razon=f"Overfitting detectado. Aumentar dropout de {dropout:.2f} a {new_dropout:.2f}.",
                    impacto_esperado="alto",
                    prioridad=1
                )
            else:
                # Ya tiene dropout alto, mantener pero considerar otras estrategias
                suggestions['dropout_rate'] = ParameterSuggestion(
                    valor_sugerido=params.dropout_rate,
                    cambio="mantener",
                    razon=f"Dropout ya alto ({dropout:.2f}). Considerar reducir capacidad del modelo.",
                    impacto_esperado="bajo",
                    prioridad=3
                )

        # Caso 2: Underfitting
        elif metrics.underfitting_detectado and dropout > 0.05:
            new_dropout = max(dropout - 0.1, 0.0)
            suggestions['dropout_rate'] = ParameterSuggestion(
                valor_sugerido=Decimal(str(new_dropout)),
                cambio="disminuir",
                razon=f"Underfitting detectado. Reducir dropout de {dropout:.2f} a {new_dropout:.2f}.",
                impacto_esperado="medio",
                prioridad=2
            )

        # Caso 3: Buen rendimiento pero accuracy baja → puede necesitar menos dropout
        elif metrics.accuracy_validacion and metrics.accuracy_validacion < 0.7 and dropout > 0.2:
            new_dropout = max(dropout - 0.05, 0.1)
            suggestions['dropout_rate'] = ParameterSuggestion(
                valor_sugerido=Decimal(str(new_dropout)),
                cambio="disminuir",
                razon=f"Accuracy baja ({metrics.accuracy_validacion:.2f}). Reducir dropout a {new_dropout:.2f}.",
                impacto_esperado="medio",
                prioridad=2
            )

        if not suggestions:
            suggestions['dropout_rate'] = ParameterSuggestion(
                valor_sugerido=params.dropout_rate,
                cambio="mantener",
                razon="Tasa de dropout actual muestra buen balance regularización/capacidad.",
                impacto_esperado="bajo",
                prioridad=3
            )

        return suggestions

    def _analyze_model_capacity(
        self,
        params: TrainingParams,
        metrics: TrainingMetrics
    ) -> dict[str, ParameterSuggestion]:
        """
        Analiza capacidad del modelo (embedding_dimension, hidden_units).

        Estrategia:
        - Underfitting con buen tiempo de entrenamiento → aumentar capacidad
        - Overfitting → reducir capacidad
        - Memoria excesiva → reducir dimensiones
        """
        suggestions = {}

        # Analizar embedding_dimension
        emb_dim = params.embedding_dimension

        if metrics.underfitting_detectado and (not metrics.memoria_pico_mb or metrics.memoria_pico_mb < 10000):
            new_emb = min(emb_dim + 256, self.param_ranges['embedding_dimension'][1])
            suggestions['embedding_dimension'] = ParameterSuggestion(
                valor_sugerido=new_emb,
                cambio="aumentar",
                razon=f"Underfitting con memoria disponible. Aumentar embedding_dimension a {new_emb}.",
                impacto_esperado="alto",
                prioridad=1
            )
        elif metrics.overfitting_detectado and emb_dim > 512:
            new_emb = max(emb_dim - 256, 256)
            suggestions['embedding_dimension'] = ParameterSuggestion(
                valor_sugerido=new_emb,
                cambio="disminuir",
                razon=f"Overfitting detectado. Reducir embedding_dimension a {new_emb}.",
                impacto_esperado="medio",
                prioridad=2
            )
        else:
            suggestions['embedding_dimension'] = ParameterSuggestion(
                valor_sugerido=params.embedding_dimension,
                cambio="mantener",
                razon="Dimensión de embeddings apropiada para el problema.",
                impacto_esperado="bajo",
                prioridad=3
            )

        # Analizar hidden_units (similar lógica)
        hidden = params.hidden_units

        if metrics.underfitting_detectado:
            new_hidden = min(hidden + 128, self.param_ranges['hidden_units'][1])
            suggestions['hidden_units'] = ParameterSuggestion(
                valor_sugerido=new_hidden,
                cambio="aumentar",
                razon=f"Underfitting. Aumentar hidden_units a {new_hidden}.",
                impacto_esperado="medio",
                prioridad=2
            )
        elif metrics.overfitting_detectado and hidden > 256:
            new_hidden = max(hidden - 128, 128)
            suggestions['hidden_units'] = ParameterSuggestion(
                valor_sugerido=new_hidden,
                cambio="disminuir",
                razon=f"Overfitting. Reducir hidden_units a {new_hidden}.",
                impacto_esperado="medio",
                prioridad=2
            )
        else:
            suggestions['hidden_units'] = ParameterSuggestion(
                valor_sugerido=params.hidden_units,
                cambio="mantener",
                razon="Unidades ocultas apropiadas.",
                impacto_esperado="bajo",
                prioridad=3
            )

        return suggestions

    def _analyze_rag_params(
        self,
        params: TrainingParams,
        metrics: TrainingMetrics
    ) -> dict[str, ParameterSuggestion]:
        """
        Analiza parámetros RAG (chunk_size, chunk_overlap, top_k).

        Estrategia:
        - Baja retrieval precision → ajustar chunk_size o top_k
        - Baja retrieval recall → aumentar top_k
        - Balance precision/recall subóptimo → ajustar chunking
        """
        suggestions = {}

        # Analizar top_k
        top_k = params.top_k

        if metrics.retrieval_recall and metrics.retrieval_recall < 0.6:
            # Recall bajo → recuperar más documentos
            new_top_k = min(top_k + 3, self.param_ranges['top_k'][1])
            suggestions['top_k'] = ParameterSuggestion(
                valor_sugerido=new_top_k,
                cambio="aumentar",
                razon=f"Retrieval recall bajo ({metrics.retrieval_recall:.2f}). Aumentar top_k a {new_top_k}.",
                impacto_esperado="alto",
                prioridad=1
            )
        elif metrics.retrieval_precision and metrics.retrieval_precision < 0.6 and top_k > 5:
            # Precisión baja con muchos resultados → reducir ruido
            new_top_k = max(top_k - 2, 3)
            suggestions['top_k'] = ParameterSuggestion(
                valor_sugerido=new_top_k,
                cambio="disminuir",
                razon=f"Retrieval precision bajo ({metrics.retrieval_precision:.2f}). Reducir top_k a {new_top_k}.",
                impacto_esperado="medio",
                prioridad=2
            )
        else:
            suggestions['top_k'] = ParameterSuggestion(
                valor_sugerido=params.top_k,
                cambio="mantener",
                razon="Top-k actual muestra buen balance precision/recall.",
                impacto_esperado="bajo",
                prioridad=3
            )

        # Analizar chunk_size
        chunk_size = params.chunk_size

        if metrics.avg_similarity_score and metrics.avg_similarity_score < 0.5:
            # Similaridad baja → chunks pueden ser muy grandes o muy pequeños
            if chunk_size > 1500:
                new_chunk = max(chunk_size - 500, 800)
                suggestions['chunk_size'] = ParameterSuggestion(
                    valor_sugerido=new_chunk,
                    cambio="disminuir",
                    razon=f"Similaridad baja ({metrics.avg_similarity_score:.2f}). Reducir chunk_size a {new_chunk}.",
                    impacto_esperado="medio",
                    prioridad=2
                )
            elif chunk_size < 800:
                new_chunk = min(chunk_size + 300, 1200)
                suggestions['chunk_size'] = ParameterSuggestion(
                    valor_sugerido=new_chunk,
                    cambio="aumentar",
                    razon=f"Similaridad baja. Aumentar chunk_size a {new_chunk} para más contexto.",
                    impacto_esperado="medio",
                    prioridad=2
                )
        else:
            suggestions['chunk_size'] = ParameterSuggestion(
                valor_sugerido=params.chunk_size,
                cambio="mantener",
                razon="Tamaño de chunk actual es apropiado.",
                impacto_esperado="bajo",
                prioridad=3
            )

        # Analizar chunk_overlap
        overlap = params.chunk_overlap
        overlap_ratio = overlap / chunk_size if chunk_size > 0 else 0

        if overlap_ratio < 0.1:
            # Muy poco overlap → puede perder contexto
            new_overlap = int(chunk_size * 0.15)
            suggestions['chunk_overlap'] = ParameterSuggestion(
                valor_sugerido=new_overlap,
                cambio="aumentar",
                razon=f"Overlap muy bajo ({overlap_ratio:.1%}). Aumentar a {new_overlap} (15% del chunk).",
                impacto_esperado="medio",
                prioridad=2
            )
        elif overlap_ratio > 0.4:
            # Demasiado overlap → redundancia excesiva
            new_overlap = int(chunk_size * 0.2)
            suggestions['chunk_overlap'] = ParameterSuggestion(
                valor_sugerido=new_overlap,
                cambio="disminuir",
                razon=f"Overlap alto ({overlap_ratio:.1%}). Reducir a {new_overlap} (20% del chunk).",
                impacto_esperado="bajo",
                prioridad=3
            )
        else:
            suggestions['chunk_overlap'] = ParameterSuggestion(
                valor_sugerido=params.chunk_overlap,
                cambio="mantener",
                razon="Overlap actual es apropiado (10-40% del chunk).",
                impacto_esperado="bajo",
                prioridad=3
            )

        return suggestions

    def _analyze_generation_params(
        self,
        params: TrainingParams,
        metrics: TrainingMetrics
    ) -> dict[str, ParameterSuggestion]:
        """
        Analiza parámetros de generación (temperature, max_tokens).

        Estrategia:
        - BLEU/ROUGE bajos → ajustar temperature
        - Perplexity alto → reducir temperature para más determinismo
        """
        suggestions = {}

        temp = float(params.temperature)

        if metrics.perplexity and metrics.perplexity > 50:
            # Perplejidad alta → modelo confuso, reducir temperature
            new_temp = max(temp - 0.15, self.param_ranges['temperature'][0])
            suggestions['temperature'] = ParameterSuggestion(
                valor_sugerido=Decimal(str(new_temp)),
                cambio="disminuir",
                razon=f"Perplexity alto ({metrics.perplexity:.1f}). Reducir temperature a {new_temp:.2f}.",
                impacto_esperado="medio",
                prioridad=2
            )
        elif metrics.bleu_score and metrics.bleu_score < 0.3:
            # BLEU bajo → generación pobre
            if temp > 0.8:
                new_temp = 0.7
                suggestions['temperature'] = ParameterSuggestion(
                    valor_sugerido=Decimal(str(new_temp)),
                    cambio="disminuir",
                    razon=f"BLEU score bajo ({metrics.bleu_score:.2f}). Reducir temperature a {new_temp}.",
                    impacto_esperado="medio",
                    prioridad=2
                )
            elif temp < 0.5:
                new_temp = 0.7
                suggestions['temperature'] = ParameterSuggestion(
                    valor_sugerido=Decimal(str(new_temp)),
                    cambio="aumentar",
                    razon=f"BLEU score bajo. Aumentar temperature a {new_temp} para más diversidad.",
                    impacto_esperado="medio",
                    prioridad=2
                )
        else:
            suggestions['temperature'] = ParameterSuggestion(
                valor_sugerido=params.temperature,
                cambio="mantener",
                razon="Temperature actual genera buen balance calidad/diversidad.",
                impacto_esperado="bajo",
                prioridad=3
            )

        # max_tokens - generalmente mantener a menos que haya problemas específicos
        suggestions['max_tokens'] = ParameterSuggestion(
            valor_sugerido=params.max_tokens,
            cambio="mantener",
            razon="Max tokens actual es apropiado.",
            impacto_esperado="bajo",
            prioridad=3
        )

        return suggestions

    def _analyze_optimizer(
        self,
        params: TrainingParams,
        metrics: TrainingMetrics
    ) -> dict[str, ParameterSuggestion]:
        """
        Analiza optimizador y función de pérdida.

        Estrategia:
        - Convergencia lenta con Adam → probar AdamW
        - Overfitting → considerar función de pérdida con regularización
        """
        suggestions = {}

        # Optimizador
        if metrics.convergencia_lenta and params.optimizer == 'adam':
            suggestions['optimizer'] = ParameterSuggestion(
                valor_sugerido='adamw',
                cambio="cambiar",
                razon="Convergencia lenta con Adam. Probar AdamW con weight decay.",
                impacto_esperado="medio",
                prioridad=2
            )
        else:
            suggestions['optimizer'] = ParameterSuggestion(
                valor_sugerido=params.optimizer,
                cambio="mantener",
                razon="Optimizador actual funciona adecuadamente.",
                impacto_esperado="bajo",
                prioridad=3
            )

        # Loss function - generalmente mantener a menos que haya problemas específicos
        suggestions['loss_function'] = ParameterSuggestion(
            valor_sugerido=params.loss_function,
            cambio="mantener",
            razon="Función de pérdida apropiada para el problema.",
            impacto_esperado="bajo",
            prioridad=3
        )

        # Distance metric
        if metrics.retrieval_precision and metrics.retrieval_precision < 0.5:
            if params.distance_metric == 'cosine':
                suggestions['distance_metric'] = ParameterSuggestion(
                    valor_sugerido='euclidean',
                    cambio="cambiar",
                    razon=f"Retrieval precision bajo ({metrics.retrieval_precision:.2f}). Probar métrica euclidiana.",
                    impacto_esperado="medio",
                    prioridad=2
                )
            else:
                suggestions['distance_metric'] = ParameterSuggestion(
                    valor_sugerido='cosine',
                    cambio="cambiar",
                    razon=f"Retrieval precision bajo. Probar métrica cosine.",
                    impacto_esperado="medio",
                    prioridad=2
                )
        else:
            suggestions['distance_metric'] = ParameterSuggestion(
                valor_sugerido=params.distance_metric,
                cambio="mantener",
                razon="Métrica de distancia actual funciona bien.",
                impacto_esperado="bajo",
                prioridad=3
            )

        return suggestions

    def calculate_confidence_score(
        self,
        suggestions: dict[str, ParameterSuggestion],
        metrics: TrainingMetrics
    ) -> float:
        """
        Calcula score de confianza de las sugerencias (0-100).

        Más confianza cuando:
        - Hay métricas completas disponibles
        - Los problemas son claros (overfitting, underfitting, etc.)
        - Las sugerencias son críticas (prioridad 1)
        """
        confidence = 50.0  # Base

        # +20 si hay métricas de loss completas
        if metrics.loss_inicial and metrics.loss_final and metrics.loss_minimo:
            confidence += 20

        # +15 si hay métricas de validación
        if metrics.accuracy_validacion or metrics.f1_score:
            confidence += 15

        # +10 si hay métricas RAG
        if metrics.retrieval_precision or metrics.retrieval_recall:
            confidence += 10

        # +5 por cada sugerencia crítica (prioridad 1)
        critical_suggestions = sum(1 for s in suggestions.values() if s.prioridad == 1)
        confidence += min(critical_suggestions * 5, 15)

        # -10 si faltan métricas clave
        if not metrics.loss_final:
            confidence -= 10

        return min(max(confidence, 0), 100)

    def estimate_improvement_percentage(
        self,
        suggestions: dict[str, ParameterSuggestion],
        metrics: TrainingMetrics
    ) -> float:
        """
        Estima mejora esperada en porcentaje.

        Basado en:
        - Número y prioridad de cambios sugeridos
        - Magnitud de los problemas actuales
        """
        improvement = 0.0

        # Impacto por cambios críticos
        for suggestion in suggestions.values():
            if suggestion.cambio != "mantener":
                if suggestion.prioridad == 1:
                    if suggestion.impacto_esperado == "alto":
                        improvement += 15
                    elif suggestion.impacto_esperado == "medio":
                        improvement += 8
                elif suggestion.prioridad == 2:
                    if suggestion.impacto_esperado == "alto":
                        improvement += 10
                    elif suggestion.impacto_esperado == "medio":
                        improvement += 5

        # Bonus por problemas graves que se están atacando
        if metrics.overfitting_detectado:
            improvement += 10
        if metrics.underfitting_detectado:
            improvement += 12
        if metrics.gradientes_explosivos:
            improvement += 20
        if metrics.convergencia_lenta:
            improvement += 8

        return min(improvement, 50)  # Cap en 50%


def test_optimizer():
    """Test básico del optimizador."""
    # Simular entrenamiento con overfitting
    params = TrainingParams(
        learning_rate=Decimal('0.001'),
        batch_size=32,
        epochs=50,
        embedding_dimension=768,
        sequence_length=512,
        hidden_units=512,
        dropout_rate=Decimal('0.1'),
        distance_metric='cosine',
        top_k=5,
        chunk_size=1000,
        chunk_overlap=200,
        temperature=Decimal('0.7'),
        max_tokens=2048,
        loss_function='cross_entropy',
        optimizer='adam'
    )

    metrics = TrainingMetrics(
        loss_inicial=2.5,
        loss_final=0.8,
        loss_promedio=1.2,
        loss_minimo=0.75,
        epoca_mejor_loss=35,
        accuracy_validacion=0.85,
        overfitting_detectado=True,
        convergencia_lenta=False
    )

    optimizer = TrainingOptimizer()
    suggestions = optimizer.generate_suggestions(params, metrics)

    print("=== SUGERENCIAS DE OPTIMIZACIÓN ===\n")
    for param_name, suggestion in suggestions.items():
        if suggestion.cambio != "mantener":
            print(f"{param_name}:")
            print(f"  Cambio: {suggestion.cambio}")
            print(f"  Valor sugerido: {suggestion.valor_sugerido}")
            print(f"  Razón: {suggestion.razon}")
            print(f"  Impacto: {suggestion.impacto_esperado} (prioridad {suggestion.prioridad})")
            print()

    confidence = optimizer.calculate_confidence_score(suggestions, metrics)
    improvement = optimizer.estimate_improvement_percentage(suggestions, metrics)

    print(f"Confianza: {confidence:.1f}%")
    print(f"Mejora esperada: {improvement:.1f}%")


if __name__ == "__main__":
    test_optimizer()
