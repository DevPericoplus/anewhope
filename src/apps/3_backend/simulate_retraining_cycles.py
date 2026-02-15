#!/usr/bin/env python3
"""
Script para simular 5 ciclos de reentrenamiento con optimización de parámetros.

Flujo por cada ciclo:
1. Obtener último entrenamiento completado
2. Generar sugerencias de optimización
3. Aplicar sugerencias para crear nuevo job
4. Enviar entrenamiento al trainer
5. Esperar completación
6. Analizar modelo generado
"""

import requests
import time
import json
from datetime import datetime
import mysql.connector
from typing import Optional, Dict, Any

# Configuración
BACKEND_URL = "http://localhost:8003"
BROKER_URL = "http://localhost:8008"
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

def get_latest_completed_training() -> Optional[Dict[str, Any]]:
    """Obtiene el último entrenamiento completado."""
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            numero_secuencia,
            id_organizacion,
            id_proyecto,
            id_version,
            id_job_entrenamientos,
            estado
        FROM entrenamientos
        WHERE estado = 'completado'
        ORDER BY id DESC
        LIMIT 1
    """)

    result = cursor.fetchone()
    cursor.close()
    db.close()

    return result

def generate_suggestions(training_id: int) -> Optional[int]:
    """Genera sugerencias para un entrenamiento."""
    print(f"  📊 Generando sugerencias para entrenamiento {training_id}...")

    response = requests.post(
        f"{BACKEND_URL}/analysis/trainings/{training_id}/generate-suggestions",
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()
        print(f"    ✅ Sugerencias generadas (ID: {data['id_sugerencia']})")
        print(f"       Confianza: {data['confianza_score']:.1f}%")
        print(f"       Mejora esperada: {data['mejora_esperada_pct']:.1f}%")
        return data['id_sugerencia']
    else:
        print(f"    ❌ Error generando sugerencias: {response.status_code}")
        return None

def get_job_params(job_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene los parámetros de un job."""
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM jobs_entrenamientos WHERE id = %s
    """, (job_id,))

    result = cursor.fetchone()
    cursor.close()
    db.close()

    return result

def apply_suggestions(suggestion_id: int, training_number: int) -> Optional[int]:
    """Aplica sugerencias creando un nuevo job."""
    print(f"  🔧 Aplicando sugerencias {suggestion_id}...")

    response = requests.post(
        f"{BACKEND_URL}/analysis/suggestions/{suggestion_id}/apply",
        json={
            "nombre_nuevo_job": f"Optimizado Auto #{training_number}",
            "descripcion": f"Reentrenamiento automático {training_number} con parámetros optimizados"
        },
        timeout=10
    )

    if response.status_code == 200:
        data = response.json()
        print(f"    ✅ Nuevo job creado (ID: {data['id_job_entrenamientos']})")
        return data['id_job_entrenamientos']
    else:
        print(f"    ❌ Error aplicando sugerencias: {response.status_code}")
        return None

def send_training_to_trainer(training_data: Dict[str, Any]) -> Optional[int]:
    """Envía el entrenamiento al trainer vía broker."""
    print(f"  🚀 Enviando entrenamiento al trainer...")

    # Calcular el siguiente número de secuencia
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT COALESCE(MAX(numero_secuencia), 0) + 1 as next_seq
        FROM entrenamientos
        WHERE id_version = %s
    """, (training_data['id_version'],))

    next_seq = cursor.fetchone()['next_seq']

    # Construir pat_version y collection_name
    org_id = str(training_data['id_organizacion']).zfill(5)
    prj_id = str(training_data['id_proyecto']).zfill(5)
    ver_id = str(training_data['id_version']).zfill(3)

    pat_version = f"/Users/administrator/data/anewhope/files/trainer_server/external/ORG{org_id}/PRJ{prj_id}/v{ver_id}"

    # Insertar en BD (collection_name se construirá después de obtener el training_id)
    cursor.execute("""
        INSERT INTO entrenamientos (
            id_organizacion,
            id_proyecto,
            id_version,
            pat_version,
            id_job_entrenamientos,
            numero_secuencia,
            entrenamiento_inicial,
            reentrenamiento,
            estado,
            fase_actual,
            fecha_inicio
        ) VALUES (
            %s, %s, %s, %s, %s, %s, 0, 1, 'pendiente', 'inicializacion', NOW()
        )
    """, (
        training_data['id_organizacion'],
        training_data['id_proyecto'],
        training_data['id_version'],
        pat_version,
        training_data['id_job_entrenamientos'],
        next_seq
    ))

    training_id = cursor.lastrowid

    # Actualizar collection_name ahora que tenemos el ID
    collection_name = f"ORG{org_id}_PRJ{prj_id}_v{ver_id}_ENT{training_id}_SEQ{next_seq}"

    cursor.execute("""
        UPDATE entrenamientos
        SET collection_name = %s
        WHERE id = %s
    """, (collection_name, training_id))

    db.commit()
    cursor.close()
    db.close()

    print(f"    ✅ Entrenamiento registrado en BD (ID: {training_id}, Secuencia: {next_seq})")

    # Enviar al broker
    try:
        response = requests.post(
            f"{BROKER_URL}/training/entrenamientos",
            json={
                "id_entrenamiento": training_id,
                "id_organizacion": training_data['id_organizacion'],
                "id_proyecto": training_data['id_proyecto'],
                "id_version": training_data['id_version'],
                "id_job_entrenamientos": training_data['id_job_entrenamientos']
            },
            timeout=10
        )

        if response.status_code == 200:
            print(f"    ✅ Entrenamiento enviado al trainer")
            return training_id
        else:
            print(f"    ⚠️ Error enviando al broker: {response.status_code}")
            return training_id  # Aún así retornar el ID
    except Exception as e:
        print(f"    ⚠️ Error contactando broker: {e}")
        return training_id

def wait_for_training_completion(training_id: int, timeout_minutes: int = 5) -> bool:
    """Espera a que el entrenamiento se complete."""
    print(f"  ⏳ Esperando completación del entrenamiento {training_id}...")

    start_time = time.time()
    timeout_seconds = timeout_minutes * 60

    while time.time() - start_time < timeout_seconds:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT estado, fase_actual
            FROM entrenamientos
            WHERE id = %s
        """, (training_id,))

        result = cursor.fetchone()
        cursor.close()
        db.close()

        if result:
            estado = result['estado']
            fase = result['fase_actual']

            if estado == 'completado':
                print(f"    ✅ Entrenamiento completado!")
                return True
            elif estado == 'error':
                print(f"    ❌ Entrenamiento falló")
                return False
            else:
                # Mostrar progreso cada 30 segundos
                elapsed = int(time.time() - start_time)
                if elapsed % 30 == 0 and elapsed > 0:
                    print(f"    ⏱️ {elapsed}s - Estado: {estado}, Fase: {fase}")

        time.sleep(2)  # Polling cada 2 segundos

    print(f"    ⏰ Timeout esperando completación")
    return False

def analyze_trained_model(training_id: int) -> bool:
    """Analiza el modelo entrenado."""
    print(f"  🔬 Analizando modelo del entrenamiento {training_id}...")

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
        print(f"    ❌ Error analizando modelo: {response.status_code}")
        return False

def run_retraining_cycle(cycle_number: int) -> bool:
    """Ejecuta un ciclo completo de reentrenamiento."""
    print(f"\n{'='*60}")
    print(f"🔄 CICLO {cycle_number}/5 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # 1. Obtener último entrenamiento
    training = get_latest_completed_training()
    if not training:
        print("❌ No se encontró entrenamiento completado")
        return False

    print(f"📌 Último entrenamiento: ID {training['id']} (secuencia {training['numero_secuencia']})")

    # 2. Generar sugerencias
    suggestion_id = generate_suggestions(training['id'])
    if not suggestion_id:
        return False

    # 3. Aplicar sugerencias
    new_job_id = apply_suggestions(suggestion_id, cycle_number)
    if not new_job_id:
        return False

    # 4. Obtener parámetros del job original para contexto
    original_params = get_job_params(training['id_job_entrenamientos'])
    if not original_params:
        print("❌ No se pudo obtener job original")
        return False

    # 5. Enviar nuevo entrenamiento
    training_data = {
        'id_organizacion': training['id_organizacion'],
        'id_proyecto': training['id_proyecto'],
        'id_version': training['id_version'],
        'id_job_entrenamientos': new_job_id
    }

    new_training_id = send_training_to_trainer(training_data)
    if not new_training_id:
        return False

    # 6. Esperar completación
    if not wait_for_training_completion(new_training_id):
        print(f"⚠️ Continuando con siguiente ciclo...")
        return False

    # 7. Analizar modelo
    analyze_trained_model(new_training_id)

    print(f"\n✅ Ciclo {cycle_number} completado exitosamente!")
    return True

def main():
    """Función principal."""
    print("\n" + "="*60)
    print("🚀 SIMULACIÓN DE 5 CICLOS DE REENTRENAMIENTO")
    print("="*60)
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    successful_cycles = 0

    for i in range(1, 6):
        success = run_retraining_cycle(i)
        if success:
            successful_cycles += 1

        # Pausa entre ciclos (excepto en el último)
        if i < 5:
            print(f"\n⏸️ Pausa de 5 segundos antes del siguiente ciclo...")
            time.sleep(5)

    print("\n" + "="*60)
    print(f"📊 RESUMEN FINAL")
    print("="*60)
    print(f"Ciclos completados exitosamente: {successful_cycles}/5")
    print(f"Finalización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")

    # Mostrar estadísticas finales
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT COUNT(*) as total
        FROM jobs_entrenamientos_sugeridos
    """)
    sugerencias = cursor.fetchone()

    cursor.execute("""
        SELECT COUNT(*) as total
        FROM job_entrenamientos_analisis
    """)
    analisis = cursor.fetchone()

    cursor.close()
    db.close()

    print(f"📈 Registros en BD:")
    print(f"   - Sugerencias: {sugerencias['total']}")
    print(f"   - Análisis: {analisis['total']}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
