"""
Servicio de Análisis y Sugerencias de Entrenamientos

Conecta el motor de optimización (training_optimizer.py) con la base de datos
para generar sugerencias automáticas basadas en resultados reales.
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal
import logging

from training_optimizer import (
    TrainingOptimizer,
    TrainingMetrics,
    TrainingParams,
    ParameterSuggestion
)

logger = logging.getLogger(__name__)


class TrainingAnalysisService:
    """
    Servicio para analizar entrenamientos y generar sugerencias.
    """

    def __init__(self, db_connection):
        """
        Args:
            db_connection: Conexión a MariaDB
        """
        self.db = db_connection
        self.optimizer = TrainingOptimizer()

    def analyze_training_and_generate_suggestions(
        self,
        id_entrenamiento: int
    ) -> Optional[int]:
        """
        Analiza un entrenamiento y genera sugerencias en la BD.

        Args:
            id_entrenamiento: ID del entrenamiento a analizar

        Returns:
            ID del registro de sugerencias creado, o None si falla
        """
        try:
            # 1. Obtener datos del entrenamiento
            training_data = self._get_training_data(id_entrenamiento)
            if not training_data:
                logger.error(f"Entrenamiento {id_entrenamiento} no encontrado")
                return None

            # 2. Obtener métricas del entrenamiento
            metrics = self._get_training_metrics(id_entrenamiento)
            if not metrics:
                logger.warning(f"No hay métricas para entrenamiento {id_entrenamiento}")
                metrics = TrainingMetrics()  # Métricas vacías

            # 3. Obtener parámetros usados
            params = self._get_training_params(training_data['id_job_entrenamientos'])
            if not params:
                logger.error(f"No se pudieron obtener parámetros del job {training_data['id_job_entrenamientos']}")
                return None

            # 4. Generar sugerencias con el optimizador
            suggestions = self.optimizer.generate_suggestions(params, metrics)

            # 5. Calcular scores
            confidence = self.optimizer.calculate_confidence_score(suggestions, metrics)
            improvement = self.optimizer.estimate_improvement_percentage(suggestions, metrics)

            # 6. Guardar sugerencias en BD
            id_sugerencia = self._save_suggestions_to_db(
                id_job_entrenamiento=training_data['id_job_entrenamientos'],
                id_entrenamiento=id_entrenamiento,
                suggestions=suggestions,
                confidence=confidence,
                improvement=improvement
            )

            logger.info(f"Sugerencias generadas para entrenamiento {id_entrenamiento}: ID={id_sugerencia}")
            return id_sugerencia

        except Exception as e:
            logger.error(f"Error analizando entrenamiento {id_entrenamiento}: {e}", exc_info=True)
            return None

    def _get_training_data(self, id_entrenamiento: int) -> Optional[dict]:
        """Obtiene datos básicos del entrenamiento."""
        query = """
            SELECT id, id_job_entrenamientos, estado, fase_actual,
                   id_organizacion, id_proyecto, id_version, numero_secuencia
            FROM entrenamientos
            WHERE id = %s
        """
        cursor = self.db.cursor(dictionary=True)
        cursor.execute(query, (id_entrenamiento,))
        result = cursor.fetchone()
        cursor.close()
        return result

    def _get_training_metrics(self, id_entrenamiento: int) -> Optional[TrainingMetrics]:
        """Obtiene métricas del entrenamiento desde la BD."""
        query = """
            SELECT *
            FROM entrenamientos_metricas
            WHERE id_entrenamiento = %s
            ORDER BY created_at DESC
            LIMIT 1
        """
        cursor = self.db.cursor(dictionary=True)
        cursor.execute(query, (id_entrenamiento,))
        row = cursor.fetchone()
        cursor.close()

        if not row:
            return None

        # Convertir row de BD a TrainingMetrics
        return TrainingMetrics(
            loss_inicial=float(row['loss_inicial']) if row['loss_inicial'] else None,
            loss_final=float(row['loss_final']) if row['loss_final'] else None,
            loss_promedio=float(row['loss_promedio']) if row['loss_promedio'] else None,
            loss_minimo=float(row['loss_minimo']) if row['loss_minimo'] else None,
            epoca_mejor_loss=row['epoca_mejor_loss'],
            accuracy_validacion=float(row['accuracy_validacion']) if row['accuracy_validacion'] else None,
            f1_score=float(row['f1_score']) if row['f1_score'] else None,
            precision_score=float(row['precision_score']) if row['precision_score'] else None,
            recall_score=float(row['recall_score']) if row['recall_score'] else None,
            retrieval_precision=float(row['retrieval_precision']) if row['retrieval_precision'] else None,
            retrieval_recall=float(row['retrieval_recall']) if row['retrieval_recall'] else None,
            avg_similarity_score=float(row['avg_similarity_score']) if row['avg_similarity_score'] else None,
            perplexity=float(row['perplexity']) if row['perplexity'] else None,
            bleu_score=float(row['bleu_score']) if row['bleu_score'] else None,
            rouge_l_score=float(row['rouge_l_score']) if row['rouge_l_score'] else None,
            tiempo_entrenamiento_seg=row['tiempo_entrenamiento_seg'],
            tokens_procesados=row['tokens_procesados'],
            tokens_por_segundo=float(row['tokens_por_segundo']) if row['tokens_por_segundo'] else None,
            memoria_pico_mb=row['memoria_pico_mb'],
            overfitting_detectado=bool(row['overfitting_detectado']),
            underfitting_detectado=bool(row['underfitting_detectado']),
            convergencia_lenta=bool(row['convergencia_lenta']),
            gradientes_explosivos=bool(row['gradientes_explosivos'])
        )

    def _get_training_params(self, id_job_entrenamiento: int) -> Optional[TrainingParams]:
        """Obtiene parámetros del job de entrenamiento."""
        query = """
            SELECT *
            FROM jobs_entrenamientos
            WHERE id = %s
        """
        cursor = self.db.cursor(dictionary=True)
        cursor.execute(query, (id_job_entrenamiento,))
        row = cursor.fetchone()
        cursor.close()

        if not row:
            return None

        return TrainingParams(
            learning_rate=row['learning_rate'],
            batch_size=row['batch_size'],
            epochs=row['epochs'],
            embedding_dimension=row['embedding_dimension'],
            sequence_length=row['sequence_length'],
            hidden_units=row['hidden_units'],
            dropout_rate=row['dropout_rate'],
            distance_metric=row['distance_metric'] or 'cosine',
            top_k=row['top_k'],
            chunk_size=row['chunk_size'],
            chunk_overlap=row['chunk_overlap'],
            temperature=row['temperature'],
            max_tokens=row['max_tokens'],
            loss_function=row['loss_function'] or 'cross_entropy',
            optimizer=row['optimizer'] or 'adam'
        )

    def _save_suggestions_to_db(
        self,
        id_job_entrenamiento: int,
        id_entrenamiento: int,
        suggestions: dict[str, ParameterSuggestion],
        confidence: float,
        improvement: float
    ) -> Optional[int]:
        """Guarda las sugerencias en la BD."""

        # Preparar datos de inserción
        insert_data = {
            'id_job_entrenamiento': id_job_entrenamiento,
            'id_entrenamiento': id_entrenamiento,
            'nombre_sugerencia': f'Optimización automática - Entrenamiento #{id_entrenamiento}',
            'razon_sugerencia': self._build_summary_reason(suggestions),
            'confianza_score': Decimal(str(confidence)),
            'mejora_esperada_pct': Decimal(str(improvement)),
        }

        # Agregar cada parámetro sugerido
        param_mapping = {
            'learning_rate': ('learning_rate_sugerido', 'learning_rate_cambio', 'learning_rate_razon'),
            'batch_size': ('batch_size_sugerido', 'batch_size_cambio', 'batch_size_razon'),
            'epochs': ('epochs_sugerido', 'epochs_cambio', 'epochs_razon'),
            'embedding_dimension': ('embedding_dimension_sugerido', 'embedding_dimension_cambio', 'embedding_dimension_razon'),
            'sequence_length': ('sequence_length_sugerido', 'sequence_length_cambio', 'sequence_length_razon'),
            'hidden_units': ('hidden_units_sugerido', 'hidden_units_cambio', 'hidden_units_razon'),
            'dropout_rate': ('dropout_rate_sugerido', 'dropout_rate_cambio', 'dropout_rate_razon'),
            'distance_metric': ('distance_metric_sugerido', 'distance_metric_cambio', 'distance_metric_razon'),
            'top_k': ('top_k_sugerido', 'top_k_cambio', 'top_k_razon'),
            'chunk_size': ('chunk_size_sugerido', 'chunk_size_cambio', 'chunk_size_razon'),
            'chunk_overlap': ('chunk_overlap_sugerido', 'chunk_overlap_cambio', 'chunk_overlap_razon'),
            'temperature': ('temperature_sugerido', 'temperature_cambio', 'temperature_razon'),
            'max_tokens': ('max_tokens_sugerido', 'max_tokens_cambio', 'max_tokens_razon'),
            'loss_function': ('loss_function_sugerido', 'loss_function_cambio', 'loss_function_razon'),
            'optimizer': ('optimizer_sugerido', 'optimizer_cambio', 'optimizer_razon'),
        }

        for param_name, (col_value, col_change, col_reason) in param_mapping.items():
            if param_name in suggestions:
                suggestion = suggestions[param_name]
                insert_data[col_value] = suggestion.valor_sugerido
                insert_data[col_change] = suggestion.cambio
                insert_data[col_reason] = suggestion.razon

        # Construir query de inserción
        columns = ', '.join(insert_data.keys())
        placeholders = ', '.join(['%s'] * len(insert_data))
        query = f"""
            INSERT INTO jobs_entrenamientos_sugeridos
            ({columns})
            VALUES ({placeholders})
        """

        try:
            cursor = self.db.cursor()
            cursor.execute(query, tuple(insert_data.values()))
            self.db.commit()
            id_sugerencia = cursor.lastrowid
            cursor.close()
            return id_sugerencia

        except Exception as e:
            logger.error(f"Error guardando sugerencias: {e}", exc_info=True)
            self.db.rollback()
            return None

    def _build_summary_reason(self, suggestions: dict[str, ParameterSuggestion]) -> str:
        """Construye un resumen de las razones de cambio."""
        critical_changes = []
        important_changes = []

        for param_name, suggestion in suggestions.items():
            if suggestion.cambio != "mantener":
                if suggestion.prioridad == 1:
                    critical_changes.append(f"{param_name}: {suggestion.razon}")
                elif suggestion.prioridad == 2:
                    important_changes.append(f"{param_name}: {suggestion.razon}")

        summary_parts = []

        if critical_changes:
            summary_parts.append("CAMBIOS CRÍTICOS:\n" + "\n".join(f"• {c}" for c in critical_changes))

        if important_changes:
            summary_parts.append("CAMBIOS IMPORTANTES:\n" + "\n".join(f"• {c}" for c in important_changes))

        if not summary_parts:
            return "Los parámetros actuales muestran buen rendimiento. Mantener configuración."

        return "\n\n".join(summary_parts)

    def get_suggestions_for_training(self, id_entrenamiento: int) -> Optional[dict]:
        """Obtiene las sugerencias existentes para un entrenamiento."""
        query = """
            SELECT *
            FROM jobs_entrenamientos_sugeridos
            WHERE id_entrenamiento = %s
            ORDER BY created_at DESC
            LIMIT 1
        """
        cursor = self.db.cursor(dictionary=True)
        cursor.execute(query, (id_entrenamiento,))
        result = cursor.fetchone()
        cursor.close()
        return result

    def get_trainings_for_analysis(
        self,
        id_organizacion: Optional[int] = None,
        id_proyecto: Optional[int] = None,
        id_version: Optional[int] = None
    ) -> list[dict]:
        """
        Obtiene entrenamientos que están listos para análisis.

        Filtra por organización, proyecto y versión si se especifican.
        """
        query = """
            SELECT
                e.id,
                e.numero_secuencia,
                e.id_organizacion,
                e.id_proyecto,
                e.id_version,
                e.estado,
                e.fase_actual,
                e.fecha_inicio,
                e.fecha_fin,
                je.nombre AS params_nombre,
                em.loss_final,
                em.accuracy_validacion,
                js.id AS tiene_sugerencias
            FROM entrenamientos e
            LEFT JOIN jobs_entrenamientos je ON e.id_job_entrenamientos = je.id
            LEFT JOIN entrenamientos_metricas em ON e.id = em.id_entrenamiento
            LEFT JOIN jobs_entrenamientos_sugeridos js ON e.id = js.id_entrenamiento
            WHERE e.estado = 'completado'
        """

        params = []

        if id_organizacion:
            query += " AND e.id_organizacion = %s"
            params.append(id_organizacion)

        if id_proyecto:
            query += " AND e.id_proyecto = %s"
            params.append(id_proyecto)

        if id_version:
            query += " AND e.id_version = %s"
            params.append(id_version)

        query += " ORDER BY e.created_at DESC"

        cursor = self.db.cursor(dictionary=True)
        cursor.execute(query, tuple(params))
        results = cursor.fetchall()
        cursor.close()

        return results

    def mark_suggestions_as_applied(
        self,
        id_sugerencia: int,
        id_entrenamiento_aplicado: int
    ) -> bool:
        """Marca las sugerencias como aplicadas en un nuevo entrenamiento."""
        query = """
            UPDATE jobs_entrenamientos_sugeridos
            SET aplicado = 1,
                id_entrenamiento_aplicado = %s,
                updated_at = NOW()
            WHERE id = %s
        """
        try:
            cursor = self.db.cursor()
            cursor.execute(query, (id_entrenamiento_aplicado, id_sugerencia))
            self.db.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Error marcando sugerencias como aplicadas: {e}")
            self.db.rollback()
            return False
