"""
Test específico para los 3 switches que están fallando:
- revision_interna
- propuesta_mejoras
- generacion_llm_solicitada

Este test valida el ciclo completo: API -> BD -> Refresco UI
"""

import pymysql
import requests
import time


# Configuración
BACKEND_CORE_URL = "http://localhost:8003"
TEST_USER_ID = 1
TEST_IDENTITY_TYPE_ID = 1
ESTADO_ID = 1  # Usar el estado existente


def get_db_connection():
    """Crea conexión a la base de datos."""
    return pymysql.connect(
        host="localhost",
        user="myllm_admin",
        password="Us3r@dminP@ss",
        database="myllm_projects_db",
        charset="utf8mb4",
    )


def get_estado_from_db(estado_id: int) -> dict:
    """Lee el estado actual desde la base de datos."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    revision_interna,
                    propuesta_mejoras,
                    generacion_llm_solicitada,
                    final_c,
                    final_i,
                    control_calidad_aprobado
                FROM estado_version
                WHERE id = %s
                """,
                (estado_id,),
            )
            row = cursor.fetchone()

            if not row:
                raise ValueError(f"Estado {estado_id} no encontrado")

            return {
                "revision_interna": bool(row[0]),
                "propuesta_mejoras": bool(row[1]),
                "generacion_llm_solicitada": bool(row[2]),
                "final_c": bool(row[3]),
                "final_i": bool(row[4]),
                "control_calidad_aprobado": bool(row[5]),
            }
    finally:
        conn.close()


def reset_estado_to_initial(estado_id: int):
    """Resetea el estado a valores iniciales para las pruebas."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE estado_version
                SET
                    revision_interna = 0,
                    propuesta_mejoras = 0,
                    generacion_llm_solicitada = 0,
                    final_c = 1,
                    final_i = 1,
                    control_calidad_aprobado = 1,
                    updated_at = NOW(),
                    updated_by = 1
                WHERE id = %s
                """,
                (estado_id,),
            )
            conn.commit()
            print(f"✓ Estado {estado_id} reseteado a valores iniciales")
    finally:
        conn.close()


def test_switch_revision_interna():
    """Test Switch 1: revision_interna"""
    print("\n" + "="*70)
    print("TEST 1: Switch 'Revisión Interna'")
    print("="*70)

    # Resetear estado
    reset_estado_to_initial(ESTADO_ID)

    # Leer estado inicial
    estado_antes = get_estado_from_db(ESTADO_ID)
    print(f"\n1️⃣  Estado ANTES: revision_interna = {estado_antes['revision_interna']}")
    assert estado_antes['revision_interna'] is False, "Debe empezar en False"

    # Llamar API para activar revision_interna
    print("\n2️⃣  Llamando API para activar revision_interna...")
    response = requests.patch(
        f"{BACKEND_CORE_URL}/project-version-states/{ESTADO_ID}/proposal",
        params={
            "user_id": TEST_USER_ID,
            "identity_type_id": TEST_IDENTITY_TYPE_ID,
        },
        json={
            "aceptacion_cliente": True,
            "aceptacion_interna": True,
            "revision_interna": True,  # ACTIVAR
            "propuesta_mejoras": False,
        },
        timeout=5,
    )

    print(f"   Status Code: {response.status_code}")
    print(f"   Response: {response.json()}")

    assert response.status_code == 200, f"Error HTTP: {response.status_code}"
    result = response.json()
    assert result.get("success") is True, f"API retornó error: {result}"

    # Esperar un momento para que se apliquen triggers
    time.sleep(0.5)

    # Verificar en BD
    print("\n3️⃣  Verificando en base de datos...")
    estado_despues = get_estado_from_db(ESTADO_ID)
    print(f"   Estado DESPUÉS: revision_interna = {estado_despues['revision_interna']}")

    if estado_despues['revision_interna']:
        print("\n✅ TEST 1 PASÓ: revision_interna se actualizó correctamente")
    else:
        print("\n❌ TEST 1 FALLÓ: revision_interna NO se actualizó en la BD")
        print(f"   Esperado: True")
        print(f"   Actual: {estado_despues['revision_interna']}")
        return False

    print("="*70)
    return True


def test_switch_propuesta_mejoras():
    """Test Switch 2: propuesta_mejoras"""
    print("\n" + "="*70)
    print("TEST 2: Switch 'Propuesta de Mejoras'")
    print("="*70)

    # Leer estado actual
    estado_antes = get_estado_from_db(ESTADO_ID)
    print(f"\n1️⃣  Estado ANTES: propuesta_mejoras = {estado_antes['propuesta_mejoras']}")

    # Llamar API para activar propuesta_mejoras
    print("\n2️⃣  Llamando API para activar propuesta_mejoras...")
    response = requests.patch(
        f"{BACKEND_CORE_URL}/project-version-states/{ESTADO_ID}/proposal",
        params={
            "user_id": TEST_USER_ID,
            "identity_type_id": TEST_IDENTITY_TYPE_ID,
        },
        json={
            "aceptacion_cliente": True,
            "aceptacion_interna": True,
            "revision_interna": True,  # Mantener el valor anterior
            "propuesta_mejoras": True,  # ACTIVAR
        },
        timeout=5,
    )

    print(f"   Status Code: {response.status_code}")
    print(f"   Response: {response.json()}")

    assert response.status_code == 200, f"Error HTTP: {response.status_code}"
    result = response.json()
    assert result.get("success") is True, f"API retornó error: {result}"

    # Esperar un momento para que se apliquen triggers
    time.sleep(0.5)

    # Verificar en BD
    print("\n3️⃣  Verificando en base de datos...")
    estado_despues = get_estado_from_db(ESTADO_ID)
    print(f"   Estado DESPUÉS: propuesta_mejoras = {estado_despues['propuesta_mejoras']}")

    if estado_despues['propuesta_mejoras']:
        print("\n✅ TEST 2 PASÓ: propuesta_mejoras se actualizó correctamente")
    else:
        print("\n❌ TEST 2 FALLÓ: propuesta_mejoras NO se actualizó en la BD")
        print(f"   Esperado: True")
        print(f"   Actual: {estado_despues['propuesta_mejoras']}")
        return False

    print("="*70)
    return True


def test_switch_generacion_solicitada():
    """Test Switch 3: generacion_llm_solicitada"""
    print("\n" + "="*70)
    print("TEST 3: Switch 'Generación Solicitada'")
    print("="*70)

    # Leer estado actual
    estado_antes = get_estado_from_db(ESTADO_ID)
    print(f"\n1️⃣  Estado ANTES:")
    print(f"   generacion_llm_solicitada = {estado_antes['generacion_llm_solicitada']}")
    print(f"   control_calidad_aprobado = {estado_antes['control_calidad_aprobado']}")

    # Verificar prerrequisito
    if not estado_antes['control_calidad_aprobado']:
        print("\n⚠️  WARNING: control_calidad_aprobado debe ser True para activar generacion_llm_solicitada")
        print("   Activando control_calidad_aprobado primero...")

        response = requests.patch(
            f"{BACKEND_CORE_URL}/project-version-states/{ESTADO_ID}/evaluation",
            params={
                "user_id": TEST_USER_ID,
                "identity_type_id": TEST_IDENTITY_TYPE_ID,
            },
            json={
                "evaluacion": False,
                "reentrenamiento": False,
                "optimizacion": False,
                "calidad_aprobada": True,
            },
            timeout=5,
        )
        assert response.status_code == 200
        time.sleep(0.5)

    # Llamar API para activar generacion_llm_solicitada
    print("\n2️⃣  Llamando API para activar generacion_llm_solicitada...")
    response = requests.patch(
        f"{BACKEND_CORE_URL}/project-version-states/{ESTADO_ID}/generation",
        params={
            "user_id": TEST_USER_ID,
            "identity_type_id": TEST_IDENTITY_TYPE_ID,
        },
        json={
            "generacion_solicitada": True,  # ACTIVAR
        },
        timeout=5,
    )

    print(f"   Status Code: {response.status_code}")
    print(f"   Response: {response.json()}")

    assert response.status_code == 200, f"Error HTTP: {response.status_code}"
    result = response.json()
    assert result.get("success") is True, f"API retornó error: {result}"

    # Esperar un momento para que se apliquen triggers
    time.sleep(0.5)

    # Verificar en BD
    print("\n3️⃣  Verificando en base de datos...")
    estado_despues = get_estado_from_db(ESTADO_ID)
    print(f"   Estado DESPUÉS: generacion_llm_solicitada = {estado_despues['generacion_llm_solicitada']}")

    if estado_despues['generacion_llm_solicitada']:
        print("\n✅ TEST 3 PASÓ: generacion_llm_solicitada se actualizó correctamente")
    else:
        print("\n❌ TEST 3 FALLÓ: generacion_llm_solicitada NO se actualizó en la BD")
        print(f"   Esperado: True")
        print(f"   Actual: {estado_despues['generacion_llm_solicitada']}")
        return False

    print("="*70)
    return True


def test_resumen_final():
    """Muestra el estado final de los 3 campos."""
    print("\n" + "="*70)
    print("RESUMEN FINAL")
    print("="*70)

    estado = get_estado_from_db(ESTADO_ID)

    print(f"\n📋 Estado final en BD (id={ESTADO_ID}):")
    print(f"   revision_interna: {estado['revision_interna']}")
    print(f"   propuesta_mejoras: {estado['propuesta_mejoras']}")
    print(f"   generacion_llm_solicitada: {estado['generacion_llm_solicitada']}")

    all_true = (
        estado['revision_interna'] and
        estado['propuesta_mejoras'] and
        estado['generacion_llm_solicitada']
    )

    if all_true:
        print("\n✅ TODOS LOS CAMPOS ESTÁN ACTIVADOS CORRECTAMENTE")
    else:
        print("\n❌ ALGUNOS CAMPOS NO SE ACTIVARON:")
        if not estado['revision_interna']:
            print("   ❌ revision_interna = False")
        if not estado['propuesta_mejoras']:
            print("   ❌ propuesta_mejoras = False")
        if not estado['generacion_llm_solicitada']:
            print("   ❌ generacion_llm_solicitada = False")

    print("="*70 + "\n")
    return all_true


if __name__ == "__main__":
    print("\n🔬 EJECUTANDO TESTS PARA LOS 3 SWITCHES PROBLEMÁTICOS\n")

    try:
        # Ejecutar tests
        test1_ok = test_switch_revision_interna()
        test2_ok = test_switch_propuesta_mejoras()
        test3_ok = test_switch_generacion_solicitada()
        all_ok = test_resumen_final()

        # Resultado final
        if test1_ok and test2_ok and test3_ok and all_ok:
            print("\n🎉 TODOS LOS TESTS PASARON - Los switches funcionan correctamente")
            exit(0)
        else:
            print("\n💥 ALGUNOS TESTS FALLARON - Revisar logs arriba")
            exit(1)

    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ ERROR: No se pudo conectar al backend core en {BACKEND_CORE_URL}")
        print("   Asegúrate de que el servicio esté corriendo")
        print(f"   Error: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
