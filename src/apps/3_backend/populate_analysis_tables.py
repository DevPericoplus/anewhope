#!/usr/bin/env python3
"""
Script para poblar las tablas de análisis y sugerencias con datos de prueba.
Usa entrenamientos ya completados y genera múltiples análisis y sugerencias.
"""

import requests
import time
from datetime import datetime
import mysql.connector

# Configuración
BACKEND_URL = "http://localhost:8003"
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'myllm_writer',
    'password': 'Us3r@wr1t3rP@ss',
    'database': 'myllm_projects_db',
}

def get_db_connection():
    """Obtiene conexión a la base de datos."""
    return mysql.connector.connect(**DB_CONFIG)

def get_completed_trainings():
    """Obtiene entrenamientos completados."""
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            numero_secuencia,
            id_organizacion,
            id_proyecto,
            id_version,
            id_job_entrenamientos
        FROM entrenamientos
        WHERE estado = 'completado'
        ORDER BY id DESC
        LIMIT 5
    """)

    results = cursor.fetchall()
    cursor.close()
    db.close()

    return results

def analyze_model(training_id: int) -> bool:
    """Analiza un modelo."""
    print(f"  🔬 Analizando modelo del entrenamiento {training_id}...")

    try:
        response = requests.post(
            f"{BACKEND_URL}/analysis/trainings/{training_id}/analyze",
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            score = data.get('overall_quality_score', 0)
            print(f"    ✅ Análisis completado - Quality Score: {score:.2%}")
            return True
        else:
            print(f"    ⚠️ Status: {response.status_code}")
            # Intentar de nuevo puede fallar si ya existe
            return False
    except Exception as e:
        print(f"    ⚠️ Error: {e}")
        return False

def generate_suggestions(training_id: int) -> bool:
    """Genera sugerencias para un entrenamiento."""
    print(f"  📊 Generando sugerencias para entrenamiento {training_id}...")

    try:
        response = requests.post(
            f"{BACKEND_URL}/analysis/trainings/{training_id}/generate-suggestions",
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            print(f"    ✅ Sugerencias generadas")
            print(f"       ID: {data['id_sugerencia']}")
            print(f"       Confianza: {data['confianza_score']:.1f}%")
            print(f"       Mejora esperada: {data['mejora_esperada_pct']:.1f}%")
            return True
        else:
            print(f"    ℹ️ Status: {response.status_code} (puede ya existir)")
            return False
    except Exception as e:
        print(f"    ⚠️ Error: {e}")
        return False

def check_existing_data():
    """Verifica datos existentes."""
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) as count FROM job_entrenamientos_analisis")
    analisis_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM jobs_entrenamientos_sugeridos")
    sugerencias_count = cursor.fetchone()['count']

    cursor.close()
    db.close()

    return analisis_count, sugerencias_count

def display_final_statistics():
    """Muestra estadísticas finales."""
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Análisis
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            AVG(overall_quality_score) as avg_score,
            MIN(overall_quality_score) as min_score,
            MAX(overall_quality_score) as max_score
        FROM job_entrenamientos_analisis
    """)
    analisis_stats = cursor.fetchone()

    # Sugerencias
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            AVG(confianza_score) as avg_confianza,
            AVG(mejora_esperada_pct) as avg_mejora
        FROM jobs_entrenamientos_sugeridos
    """)
    sugerencias_stats = cursor.fetchone()

    # Entrenamientos con análisis completo
    cursor.execute("""
        SELECT COUNT(*) as total
        FROM entrenamientos e
        INNER JOIN job_entrenamientos_analisis ja ON e.id = ja.id_entrenamiento
        INNER JOIN jobs_entrenamientos_sugeridos js ON e.id = js.id_entrenamiento
        WHERE e.estado = 'completado'
    """)
    completos = cursor.fetchone()

    cursor.close()
    db.close()

    print("\n" + "="*60)
    print("📊 ESTADÍSTICAS FINALES")
    print("="*60)

    print(f"\n🔬 Análisis de Modelos:")
    print(f"   Total: {analisis_stats['total']}")
    if analisis_stats['avg_score']:
        print(f"   Score promedio: {analisis_stats['avg_score']:.2%}")
        print(f"   Score mínimo: {analisis_stats['min_score']:.2%}")
        print(f"   Score máximo: {analisis_stats['max_score']:.2%}")

    print(f"\n📈 Sugerencias de Optimización:")
    print(f"   Total: {sugerencias_stats['total']}")
    if sugerencias_stats['avg_confianza']:
        print(f"   Confianza promedio: {sugerencias_stats['avg_confianza']:.1f}%")
        print(f"   Mejora esperada promedio: {sugerencias_stats['avg_mejora']:.1f}%")

    print(f"\n✅ Entrenamientos con análisis completo: {completos['total']}")
    print("="*60 + "\n")

def main():
    """Función principal."""
    print("\n" + "="*60)
    print("🎯 POBLACIÓN DE TABLAS DE ANÁLISIS")
    print("="*60)
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Verificar datos existentes
    print("📋 Verificando datos existentes...")
    analisis_inicial, sugerencias_inicial = check_existing_data()
    print(f"   Análisis actuales: {analisis_inicial}")
    print(f"   Sugerencias actuales: {sugerencias_inicial}\n")

    # Obtener entrenamientos completados
    print("🔍 Buscando entrenamientos completados...")
    trainings = get_completed_trainings()
    print(f"   Encontrados: {len(trainings)} entrenamientos\n")

    if not trainings:
        print("❌ No hay entrenamientos completados")
        return

    # Procesar cada entrenamiento
    analisis_creados = 0
    sugerencias_creadas = 0

    for idx, training in enumerate(trainings, 1):
        print(f"\n{'='*60}")
        print(f"Entrenamiento {idx}/{len(trainings)}")
        print(f"{'='*60}")
        print(f"ID: {training['id']}, Secuencia: {training['numero_secuencia']}")

        # Analizar modelo
        if analyze_model(training['id']):
            analisis_creados += 1
            time.sleep(1)  # Pausa breve

        # Generar sugerencias
        if generate_suggestions(training['id']):
            sugerencias_creadas += 1
            time.sleep(1)  # Pausa breve

        print()

    # Resumen
    print("\n" + "="*60)
    print("✅ PROCESO COMPLETADO")
    print("="*60)
    print(f"Nuevos análisis creados: {analisis_creados}")
    print(f"Nuevas sugerencias creadas: {sugerencias_creadas}")

    # Estadísticas finales
    display_final_statistics()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
