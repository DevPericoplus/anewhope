"""
Router para endpoints de análisis y optimización de entrenamientos.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Any
import logging

from database import get_db_connection
from training_analysis_service import TrainingAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["training-analysis"])


# ============================================================================
# Modelos Pydantic
# ============================================================================

class TrainingListResponse(BaseModel):
    """Respuesta de listado de entrenamientos."""
    id: int
    numero_secuencia: int
    id_organizacion: int
    id_proyecto: int
    id_version: int
    estado: str
    fase_actual: str
    fecha_inicio: Optional[str]
    fecha_fin: Optional[str]
    params_nombre: Optional[str]
    loss_final: Optional[float]
    accuracy_validacion: Optional[float]
    tiene_sugerencias: bool


class GenerateSuggestionsResponse(BaseModel):
    """Respuesta de generación de sugerencias."""
    id_sugerencia: int
    confianza_score: float
    mejora_esperada_pct: float
    mensaje: str


class SuggestionComparison(BaseModel):
    """Comparación de un parámetro."""
    parametro: str
    original: Any
    sugerido: Any
    cambio: str
    razon: str
    prioridad: int


class SuggestionsDetailResponse(BaseModel):
    """Detalle completo de sugerencias."""
    id: int
    id_entrenamiento: int
    nombre_sugerencia: str
    razon_sugerencia: str
    confianza_score: float
    mejora_esperada_pct: float
    comparaciones: list[SuggestionComparison]
    aplicado: bool
    id_entrenamiento_aplicado: Optional[int]
    created_at: str


class ApplySuggestionsRequest(BaseModel):
    """Request para aplicar sugerencias."""
    nombre_nuevo_job: str
    descripcion: Optional[str] = None


class ApplySuggestionsResponse(BaseModel):
    """Respuesta de aplicación de sugerencias."""
    id_job_entrenamientos: int
    nombre: str
    mensaje: str


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/trainings", response_model=list[TrainingListResponse])
def list_trainings_for_analysis(
    organization_id: Optional[int] = None,
    project_id: Optional[int] = None,
    version_id: Optional[int] = None
):
    """
    Lista entrenamientos completados con información de sugerencias.

    Query params:
        - organization_id: Filtrar por organización
        - project_id: Filtrar por proyecto
        - version_id: Filtrar por versión
    """
    try:
        db = get_db_connection()
        service = TrainingAnalysisService(db)

        trainings = service.get_trainings_for_analysis(
            id_organizacion=organization_id,
            id_proyecto=project_id,
            id_version=version_id
        )

        # Convertir a response model
        result = []
        for t in trainings:
            result.append(TrainingListResponse(
                id=t['id'],
                numero_secuencia=t['numero_secuencia'],
                id_organizacion=t['id_organizacion'],
                id_proyecto=t['id_proyecto'],
                id_version=t['id_version'],
                estado=t['estado'],
                fase_actual=t['fase_actual'],
                fecha_inicio=str(t['fecha_inicio']) if t['fecha_inicio'] else None,
                fecha_fin=str(t['fecha_fin']) if t['fecha_fin'] else None,
                params_nombre=t['params_nombre'],
                loss_final=float(t['loss_final']) if t['loss_final'] else None,
                accuracy_validacion=float(t['accuracy_validacion']) if t['accuracy_validacion'] else None,
                tiene_sugerencias=t['tiene_sugerencias'] is not None
            ))

        db.close()
        return result

    except Exception as e:
        logger.error(f"Error listando entrenamientos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trainings/{id_entrenamiento}/generate-suggestions", response_model=GenerateSuggestionsResponse)
def generate_suggestions_for_training(id_entrenamiento: int):
    """
    Genera sugerencias automáticas para un entrenamiento.

    Path params:
        - id_entrenamiento: ID del entrenamiento
    """
    try:
        db = get_db_connection()
        service = TrainingAnalysisService(db)

        # Verificar si ya tiene sugerencias
        existing = service.get_suggestions_for_training(id_entrenamiento)
        if existing:
            db.close()
            return GenerateSuggestionsResponse(
                id_sugerencia=existing['id'],
                confianza_score=float(existing['confianza_score']),
                mejora_esperada_pct=float(existing['mejora_esperada_pct']),
                mensaje="Las sugerencias ya existen. Se retornan las existentes."
            )

        # Generar nuevas sugerencias
        id_sugerencia = service.analyze_training_and_generate_suggestions(id_entrenamiento)

        if not id_sugerencia:
            db.close()
            raise HTTPException(status_code=400, detail="No se pudieron generar sugerencias")

        # Obtener las sugerencias creadas
        suggestions = service.get_suggestions_for_training(id_entrenamiento)
        db.close()

        return GenerateSuggestionsResponse(
            id_sugerencia=id_sugerencia,
            confianza_score=float(suggestions['confianza_score']),
            mejora_esperada_pct=float(suggestions['mejora_esperada_pct']),
            mensaje="Sugerencias generadas exitosamente"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando sugerencias: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trainings/{id_entrenamiento}/suggestions", response_model=SuggestionsDetailResponse)
def get_suggestions_for_training(id_entrenamiento: int):
    """
    Obtiene las sugerencias detalladas de un entrenamiento.

    Path params:
        - id_entrenamiento: ID del entrenamiento
    """
    try:
        db = get_db_connection()
        service = TrainingAnalysisService(db)

        suggestions = service.get_suggestions_for_training(id_entrenamiento)
        if not suggestions:
            db.close()
            raise HTTPException(status_code=404, detail="No hay sugerencias para este entrenamiento")

        # Obtener parámetros originales para comparación
        params_originales = service._get_training_params(suggestions['id_job_entrenamiento'])

        db.close()

        # Construir comparaciones
        comparaciones = []

        # Mapeo de parámetros
        param_map = [
            ('learning_rate', 'Learning Rate', 1),
            ('batch_size', 'Batch Size', 1),
            ('epochs', 'Epochs', 1),
            ('dropout_rate', 'Dropout Rate', 2),
            ('embedding_dimension', 'Embedding Dimension', 2),
            ('hidden_units', 'Hidden Units', 2),
            ('top_k', 'Top K (RAG)', 2),
            ('chunk_size', 'Chunk Size', 2),
            ('chunk_overlap', 'Chunk Overlap', 3),
            ('temperature', 'Temperature', 2),
            ('distance_metric', 'Distance Metric', 2),
            ('optimizer', 'Optimizer', 3),
        ]

        for param_key, param_label, default_priority in param_map:
            sugerido_key = f"{param_key}_sugerido"
            cambio_key = f"{param_key}_cambio"
            razon_key = f"{param_key}_razon"

            if suggestions.get(sugerido_key) is not None:
                original_value = getattr(params_originales, param_key)
                sugerido_value = suggestions[sugerido_key]
                cambio = suggestions.get(cambio_key, 'mantener')
                razon = suggestions.get(razon_key, '')

                # Determinar prioridad basada en el cambio
                if cambio == 'mantener':
                    prioridad = 3
                elif 'crítico' in razon.lower() or 'explosivo' in razon.lower():
                    prioridad = 1
                else:
                    prioridad = default_priority

                comparaciones.append(SuggestionComparison(
                    parametro=param_label,
                    original=original_value,
                    sugerido=sugerido_value,
                    cambio=cambio,
                    razon=razon,
                    prioridad=prioridad
                ))

        # Ordenar por prioridad
        comparaciones.sort(key=lambda x: x.prioridad)

        return SuggestionsDetailResponse(
            id=suggestions['id'],
            id_entrenamiento=id_entrenamiento,
            nombre_sugerencia=suggestions['nombre_sugerencia'],
            razon_sugerencia=suggestions['razon_sugerencia'],
            confianza_score=float(suggestions['confianza_score']),
            mejora_esperada_pct=float(suggestions['mejora_esperada_pct']),
            comparaciones=comparaciones,
            aplicado=bool(suggestions['aplicado']),
            id_entrenamiento_aplicado=suggestions['id_entrenamiento_aplicado'],
            created_at=str(suggestions['created_at'])
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo sugerencias: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggestions/{id_sugerencia}/apply", response_model=ApplySuggestionsResponse)
def apply_suggestions(id_sugerencia: int, request: ApplySuggestionsRequest):
    """
    Aplica las sugerencias creando un nuevo registro en jobs_entrenamientos.

    Path params:
        - id_sugerencia: ID de las sugerencias

    Body:
        - nombre_nuevo_job: Nombre para el nuevo job
        - descripcion: Descripción opcional
    """
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # 1. Obtener las sugerencias
        cursor.execute("""
            SELECT * FROM jobs_entrenamientos_sugeridos WHERE id = %s
        """, (id_sugerencia,))
        suggestions = cursor.fetchone()

        if not suggestions:
            cursor.close()
            db.close()
            raise HTTPException(status_code=404, detail="Sugerencias no encontradas")

        # 2. Obtener parámetros originales como base
        cursor.execute("""
            SELECT * FROM jobs_entrenamientos WHERE id = %s
        """, (suggestions['id_job_entrenamiento'],))
        original_params = cursor.fetchone()

        # 3. Construir nuevo registro con parámetros sugeridos
        new_params = {
            'nombre': request.nombre_nuevo_job,
            'descripcion': request.descripcion or f"Reentrenamiento con sugerencias aplicadas (ID sugerencia: {id_sugerencia})",
            'learning_rate': suggestions['learning_rate_sugerido'] or original_params['learning_rate'],
            'batch_size': suggestions['batch_size_sugerido'] or original_params['batch_size'],
            'epochs': suggestions['epochs_sugerido'] or original_params['epochs'],
            'embedding_dimension': suggestions['embedding_dimension_sugerido'] or original_params['embedding_dimension'],
            'sequence_length': suggestions['sequence_length_sugerido'] or original_params['sequence_length'],
            'hidden_units': suggestions['hidden_units_sugerido'] or original_params['hidden_units'],
            'dropout_rate': suggestions['dropout_rate_sugerido'] or original_params['dropout_rate'],
            'collection_name': original_params['collection_name'],
            'distance_metric': suggestions['distance_metric_sugerido'] or original_params['distance_metric'],
            'persist_directory': original_params['persist_directory'],
            'top_k': suggestions['top_k_sugerido'] or original_params['top_k'],
            'chunk_size': suggestions['chunk_size_sugerido'] or original_params['chunk_size'],
            'chunk_overlap': suggestions['chunk_overlap_sugerido'] or original_params['chunk_overlap'],
            'temperature': suggestions['temperature_sugerido'] or original_params['temperature'],
            'max_tokens': suggestions['max_tokens_sugerido'] or original_params['max_tokens'],
            'loss_function': suggestions['loss_function_sugerido'] or original_params['loss_function'],
            'optimizer': suggestions['optimizer_sugerido'] or original_params['optimizer'],
            'activo': 1
        }

        # 4. Insertar nuevo job_entrenamientos
        columns = ', '.join(new_params.keys())
        placeholders = ', '.join(['%s'] * len(new_params))

        cursor.execute(f"""
            INSERT INTO jobs_entrenamientos ({columns})
            VALUES ({placeholders})
        """, tuple(new_params.values()))

        id_nuevo_job = cursor.lastrowid
        db.commit()

        cursor.close()
        db.close()

        logger.info(f"Sugerencias {id_sugerencia} aplicadas → Nuevo job_entrenamientos: {id_nuevo_job}")

        return ApplySuggestionsResponse(
            id_job_entrenamientos=id_nuevo_job,
            nombre=request.nombre_nuevo_job,
            mensaje=f"Nuevo job de entrenamiento creado con parámetros optimizados"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error aplicando sugerencias: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions/{id_sugerencia}/params")
def get_suggested_params(id_sugerencia: int):
    """
    Obtiene los parámetros sugeridos en formato listo para cargar en el modal.

    Path params:
        - id_sugerencia: ID de las sugerencias
    """
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Obtener sugerencias
        cursor.execute("""
            SELECT js.*, je.*
            FROM jobs_entrenamientos_sugeridos js
            JOIN jobs_entrenamientos je ON js.id_job_entrenamiento = je.id
            WHERE js.id = %s
        """, (id_sugerencia,))
        data = cursor.fetchone()

        cursor.close()
        db.close()

        if not data:
            raise HTTPException(status_code=404, detail="Sugerencias no encontradas")

        # Construir respuesta con parámetros sugeridos (con fallback a originales)
        return {
            'learning_rate': float(data['learning_rate_sugerido'] or data['learning_rate']),
            'batch_size': int(data['batch_size_sugerido'] or data['batch_size']),
            'epochs': int(data['epochs_sugerido'] or data['epochs']),
            'embedding_dimension': int(data['embedding_dimension_sugerido'] or data['embedding_dimension']),
            'sequence_length': int(data['sequence_length_sugerido'] or data['sequence_length']),
            'hidden_units': int(data['hidden_units_sugerido'] or data['hidden_units']),
            'dropout_rate': float(data['dropout_rate_sugerido'] or data['dropout_rate']),
            'distance_metric': data['distance_metric_sugerido'] or data['distance_metric'],
            'top_k': int(data['top_k_sugerido'] or data['top_k']),
            'chunk_size': int(data['chunk_size_sugerido'] or data['chunk_size']),
            'chunk_overlap': int(data['chunk_overlap_sugerido'] or data['chunk_overlap']),
            'temperature': float(data['temperature_sugerido'] or data['temperature']),
            'max_tokens': int(data['max_tokens_sugerido'] or data['max_tokens']),
            'loss_function': data['loss_function_sugerido'] or data['loss_function'],
            'optimizer': data['optimizer_sugerido'] or data['optimizer'],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo parámetros sugeridos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trainings/{id_entrenamiento}/analyze")
def analyze_training_model(id_entrenamiento: int):
    """
    Analiza el modelo generado por un entrenamiento.

    Crea o actualiza registro en job_entrenamientos_analisis con métricas.
    """
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # 1. Verificar que el entrenamiento existe y está completado
        cursor.execute("""
            SELECT id, estado, modelo_path, numero_secuencia, id_job_entrenamientos
            FROM entrenamientos
            WHERE id = %s AND estado = 'completado'
        """, (id_entrenamiento,))

        training = cursor.fetchone()
        if not training:
            cursor.close()
            db.close()
            raise HTTPException(status_code=404, detail="Entrenamiento no encontrado o no completado")

        # 2. Verificar si ya existe análisis
        cursor.execute("""
            SELECT id, version_analisis FROM job_entrenamientos_analisis
            WHERE id_entrenamiento = %s
        """, (id_entrenamiento,))

        existing = cursor.fetchone()

        # 3. Ejecutar análisis del modelo (simulado por ahora)
        # TODO: Integrar con servicio real de análisis
        metricas = _simular_analisis_modelo(training)

        # 4. Insertar o actualizar
        if existing:
            # Actualizar
            cursor.execute("""
                UPDATE job_entrenamientos_analisis
                SET
                    rag_precision = %s,
                    rag_recall = %s,
                    rag_f1_score = %s,
                    response_relevance = %s,
                    response_coherence = %s,
                    bleu_score = %s,
                    perplexity = %s,
                    factual_accuracy = %s,
                    hallucination_rate = %s,
                    avg_inference_time_ms = %s,
                    overall_quality_score = %s,
                    fecha_analisis = NOW(),
                    version_analisis = version_analisis + 1,
                    updated_at = NOW()
                WHERE id_entrenamiento = %s
            """, (
                metricas['rag_precision'],
                metricas['rag_recall'],
                metricas['rag_f1_score'],
                metricas['response_relevance'],
                metricas['response_coherence'],
                metricas['bleu_score'],
                metricas['perplexity'],
                metricas['factual_accuracy'],
                metricas['hallucination_rate'],
                metricas['avg_inference_time_ms'],
                metricas['overall_quality_score'],
                id_entrenamiento
            ))
            db.commit()

            cursor.close()
            db.close()

            return {
                "mensaje": "Análisis actualizado exitosamente",
                "id_analisis": existing['id'],
                "version": existing['version_analisis'] + 1,
                "overall_quality_score": metricas['overall_quality_score']
            }
        else:
            # Insertar nuevo
            cursor.execute("""
                INSERT INTO job_entrenamientos_analisis (
                    id_entrenamiento,
                    id_job_entrenamientos,
                    numero_secuencia,
                    nombre_modelo,
                    ruta_modelo,
                    rag_precision,
                    rag_recall,
                    rag_f1_score,
                    response_relevance,
                    response_coherence,
                    bleu_score,
                    perplexity,
                    factual_accuracy,
                    hallucination_rate,
                    avg_inference_time_ms,
                    overall_quality_score,
                    fecha_analisis,
                    analisis_automatico
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), 1
                )
            """, (
                id_entrenamiento,
                training['id_job_entrenamientos'],
                training['numero_secuencia'],
                f"modelo_seq_{training['numero_secuencia']}",
                training['modelo_path'],
                metricas['rag_precision'],
                metricas['rag_recall'],
                metricas['rag_f1_score'],
                metricas['response_relevance'],
                metricas['response_coherence'],
                metricas['bleu_score'],
                metricas['perplexity'],
                metricas['factual_accuracy'],
                metricas['hallucination_rate'],
                metricas['avg_inference_time_ms'],
                metricas['overall_quality_score']
            ))

            id_analisis = cursor.lastrowid
            db.commit()

            cursor.close()
            db.close()

            return {
                "mensaje": "Análisis creado exitosamente",
                "id_analisis": id_analisis,
                "overall_quality_score": metricas['overall_quality_score']
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analizando modelo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _simular_analisis_modelo(training: dict) -> dict:
    """
    Simula análisis de modelo (temporal hasta integrar análisis real).

    En producción, esto debe:
    1. Cargar el modelo desde training['modelo_path']
    2. Ejecutar dataset de evaluación
    3. Calcular métricas reales
    """
    import random

    # Simular métricas (en prod: calcular reales)
    base_score = 0.65 + (random.random() * 0.25)  # 0.65-0.90

    return {
        'rag_precision': round(base_score + random.uniform(-0.05, 0.05), 4),
        'rag_recall': round(base_score + random.uniform(-0.05, 0.05), 4),
        'rag_f1_score': round(base_score, 4),
        'response_relevance': round(base_score + random.uniform(-0.03, 0.03), 4),
        'response_coherence': round(base_score + random.uniform(-0.03, 0.03), 4),
        'bleu_score': round(base_score * 0.8, 4),
        'perplexity': round(15.0 + random.uniform(-5, 5), 2),
        'factual_accuracy': round(base_score + random.uniform(-0.02, 0.02), 4),
        'hallucination_rate': round(1.0 - base_score + random.uniform(-0.05, 0.05), 4),
        'avg_inference_time_ms': int(150 + random.uniform(-50, 50)),
        'overall_quality_score': round(base_score, 4),
    }
