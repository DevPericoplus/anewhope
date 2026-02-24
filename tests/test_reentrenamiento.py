#!/usr/bin/env python3
"""
Test script para verificar el flujo de reentrenamiento.

Simula el flujo completo:
1. Obtener lista de entrenamientos con sugerencias
2. Obtener metadata de la sugerencia
3. Obtener parámetros sugeridos
4. Verificar que todos los datos necesarios están disponibles
"""

import httpx
import json
from typing import Dict, Any

from tests.helpers import get_service_urls
_urls = get_service_urls()

# Configuración
CORE_URL = _urls["backend_core"]

# Credenciales de ejemplo (ajustar según sea necesario)
ACCESS_TOKEN = "dummy_token"
SESSION_TOKEN = "dummy_session"

def print_section(title: str):
    """Imprime un separador de sección."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")

def test_get_trainings():
    """Test 1: Obtener lista de entrenamientos."""
    print_section("TEST 1: Obtener lista de entrenamientos con sugerencias")

    try:
        response = httpx.get(
            f"{CORE_URL}/analysis/trainings",
            headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}",
                "X-Session-Token": SESSION_TOKEN
            },
            timeout=10.0
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Entrenamientos encontrados: {len(data)}")

            # Buscar un entrenamiento con sugerencias
            training_with_suggestions = None
            for t in data:
                if t.get('tiene_sugerencias'):
                    training_with_suggestions = t
                    break

            if training_with_suggestions:
                print(f"\n✅ Entrenamiento con sugerencias encontrado:")
                print(f"   - ID: {training_with_suggestions['id']}")
                print(f"   - Secuencia: {training_with_suggestions['numero_secuencia']}")
                print(f"   - ID Sugerencia: {training_with_suggestions.get('id_sugerencia', 'NO DISPONIBLE')}")
                return training_with_suggestions
            else:
                print("⚠️  No hay entrenamientos con sugerencias disponibles")
                return None
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Excepción: {e}")
        return None

def test_get_suggestion_metadata(id_sugerencia: int):
    """Test 2: Obtener metadata de la sugerencia."""
    print_section(f"TEST 2: Obtener metadata de sugerencia ID={id_sugerencia}")

    try:
        response = httpx.get(
            f"{CORE_URL}/analysis/suggestions/{id_sugerencia}",
            headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}",
                "X-Session-Token": SESSION_TOKEN
            },
            timeout=10.0
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Metadata obtenida:")
            print(f"   - ID Entrenamiento: {data.get('id_entrenamiento')}")
            print(f"   - ID Organización: {data.get('id_organizacion')}")
            print(f"   - ID Proyecto: {data.get('id_proyecto')}")
            print(f"   - ID Versión: {data.get('id_version')}")
            print(f"   - Confianza: {data.get('confianza_score')}")
            print(f"   - Mejora esperada: {data.get('mejora_esperada_pct')}%")
            return data
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Excepción: {e}")
        return None

def test_get_suggested_params(id_sugerencia: int):
    """Test 3: Obtener parámetros sugeridos."""
    print_section(f"TEST 3: Obtener parámetros sugeridos ID={id_sugerencia}")

    try:
        response = httpx.get(
            f"{CORE_URL}/analysis/suggestions/{id_sugerencia}/params",
            headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}",
                "X-Session-Token": SESSION_TOKEN
            },
            timeout=10.0
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            params = response.json()
            print(f"✅ Parámetros obtenidos:")
            print(f"   - learning_rate: {params.get('learning_rate')}")
            print(f"   - batch_size: {params.get('batch_size')}")
            print(f"   - epochs: {params.get('epochs')}")
            print(f"   - temperature: {params.get('temperature')}")
            print(f"   - model_type: {params.get('model_type')}")
            print(f"   - chunk_size: {params.get('chunk_size')}")
            print(f"   - chunk_overlap: {params.get('chunk_overlap')}")

            # Verificar que todos los parámetros necesarios están presentes
            required_params = [
                'learning_rate', 'batch_size', 'epochs', 'embedding_dimension',
                'sequence_length', 'hidden_units', 'dropout_rate', 'distance_metric',
                'top_k', 'chunk_size', 'chunk_overlap', 'temperature', 'max_tokens',
                'loss_function', 'optimizer', 'model_type'
            ]

            missing_params = [p for p in required_params if p not in params]

            if missing_params:
                print(f"\n⚠️  Parámetros faltantes: {', '.join(missing_params)}")
            else:
                print(f"\n✅ Todos los parámetros requeridos están presentes")

            return params
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Excepción: {e}")
        return None

def verify_modal_data(metadata: Dict[str, Any], params: Dict[str, Any]):
    """Test 4: Verificar que todos los datos para el modal están disponibles."""
    print_section("TEST 4: Verificación de datos para modal de entrenamiento")

    print("Verificando datos de versión:")
    version_data_keys = ['id_organizacion', 'id_proyecto', 'id_version', 'id_entrenamiento']
    for key in version_data_keys:
        value = metadata.get(key)
        status = "✅" if value is not None else "❌"
        print(f"   {status} {key}: {value}")

    print("\nVerificando parámetros del modal:")
    param_keys = [
        'chunk_size', 'chunk_overlap', 'temperature', 'max_tokens',
        'distance_metric', 'top_k', 'learning_rate', 'batch_size',
        'epochs', 'embedding_dimension', 'sequence_length', 'hidden_units',
        'dropout_rate', 'loss_function', 'optimizer', 'model_type'
    ]

    all_present = True
    for key in param_keys:
        value = params.get(key)
        if value is None:
            print(f"   ❌ {key}: MISSING")
            all_present = False
        else:
            print(f"   ✅ {key}: {value}")

    if all_present:
        print("\n✅ RESULTADO: Todos los datos necesarios están disponibles")
        print("   El modal de entrenamiento debería abrirse correctamente")
        return True
    else:
        print("\n❌ RESULTADO: Faltan datos necesarios")
        print("   El modal puede no funcionar correctamente")
        return False

def main():
    """Ejecuta todos los tests."""
    print("\n" + "=" * 80)
    print("  TEST DE FLUJO DE REENTRENAMIENTO")
    print("=" * 80)

    # Test 1: Obtener entrenamientos
    training = test_get_trainings()
    if not training:
        print("\n❌ ABORT: No se pudo obtener un entrenamiento con sugerencias")
        return

    id_sugerencia = training.get('id_sugerencia')
    if not id_sugerencia:
        print("\n❌ ABORT: El entrenamiento no tiene id_sugerencia")
        return

    # Test 2: Obtener metadata
    metadata = test_get_suggestion_metadata(id_sugerencia)
    if not metadata:
        print("\n❌ ABORT: No se pudo obtener metadata de la sugerencia")
        return

    # Test 3: Obtener parámetros
    params = test_get_suggested_params(id_sugerencia)
    if not params:
        print("\n❌ ABORT: No se pudieron obtener los parámetros sugeridos")
        return

    # Test 4: Verificar completitud
    success = verify_modal_data(metadata, params)

    # Resumen final
    print_section("RESUMEN FINAL")
    if success:
        print("✅ ÉXITO: El flujo de reentrenamiento está funcionando correctamente")
        print("\nPasos que funcionan:")
        print("1. ✅ Obtener entrenamientos con sugerencias")
        print("2. ✅ Obtener metadata de la sugerencia")
        print("3. ✅ Obtener parámetros sugeridos")
        print("4. ✅ Todos los datos necesarios disponibles")
        print("\nEl botón 'Reentrenar' debería:")
        print("- Cargar los parámetros en el modal")
        print("- Abrir el modal de entrenamiento")
        print("- Permitir enviar el entrenamiento")
    else:
        print("❌ FALLO: El flujo tiene problemas")
        print("\nRevisar:")
        print("- Endpoints del backend")
        print("- Estructura de datos devuelta")
        print("- Campos faltantes en las respuestas")

if __name__ == "__main__":
    main()
