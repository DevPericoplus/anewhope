"""
Test simple para los 3 switches problemáticos usando urllib.
"""

import pymysql
import urllib.request
import urllib.error
import json
import time

from tests.helpers import get_service_urls, get_db_connection as _get_db_connection, row_value


# Configuración
_urls = get_service_urls()
BACKEND_CORE_URL = _urls["backend_core"]
TEST_USER_ID = 1
TEST_IDENTITY_TYPE_ID = 1
ESTADO_ID = 1


def get_db_connection():
    """Crea conexión a la base de datos."""
    return _get_db_connection(database="myllm_projects_db")


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
                "revision_interna": bool(row_value(row, "revision_interna", 0)),
                "propuesta_mejoras": bool(row_value(row, "propuesta_mejoras", 1)),
                "generacion_llm_solicitada": bool(
                    row_value(row, "generacion_llm_solicitada", 2)
                ),
                "final_c": bool(row_value(row, "final_c", 3)),
                "final_i": bool(row_value(row, "final_i", 4)),
                "control_calidad_aprobado": bool(
                    row_value(row, "control_calidad_aprobado", 5)
                ),
            }
    finally:
        conn.close()


def reset_estado_to_initial(estado_id: int):
    """Resetea el estado a valores iniciales."""
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
                    state = 'Final',
                    protected = 1,
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
            print(f"✓ Estado {estado_id} reseteado")
    finally:
        conn.close()


def make_api_request(endpoint: str, payload: dict) -> dict:
    """Hace una petición PATCH a la API."""
    url = f"{BACKEND_CORE_URL}{endpoint}?user_id={TEST_USER_ID}&identity_type_id={TEST_IDENTITY_TYPE_ID}"

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={'Content-Type': 'application/json'},
        method='PATCH'
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return {"error": True, "status_code": e.code, "detail": error_body}
    except urllib.error.URLError as e:
        return {"error": True, "detail": f"Connection error: {e}"}


print("\n" + "="*70)
print("TEST DE LOS 3 SWITCHES PROBLEMÁTICOS")
print("="*70)

# Resetear estado
print("\n📝 Reseteando estado a valores iniciales...")
reset_estado_to_initial(ESTADO_ID)

# Leer estado inicial
estado_inicial = get_estado_from_db(ESTADO_ID)
print(f"\n📊 Estado inicial en BD:")
print(f"   revision_interna: {estado_inicial['revision_interna']}")
print(f"   propuesta_mejoras: {estado_inicial['propuesta_mejoras']}")
print(f"   generacion_llm_solicitada: {estado_inicial['generacion_llm_solicitada']}")

# TEST 1: revision_interna
print("\n" + "-"*70)
print("TEST 1: Activando revision_interna")
print("-"*70)

result = make_api_request(
    f"/project-version-states/{ESTADO_ID}/proposal",
    {
        "aceptacion_cliente": True,
        "aceptacion_interna": True,
        "revision_interna": True,
        "propuesta_mejoras": False,
    }
)

print(f"API Response: {result}")

time.sleep(0.5)
estado_test1 = get_estado_from_db(ESTADO_ID)
print(f"BD después: revision_interna = {estado_test1['revision_interna']}")

if estado_test1['revision_interna']:
    print("✅ TEST 1 PASÓ")
else:
    print("❌ TEST 1 FALLÓ - NO se actualizó en BD")

# TEST 2: propuesta_mejoras
print("\n" + "-"*70)
print("TEST 2: Activando propuesta_mejoras")
print("-"*70)

result = make_api_request(
    f"/project-version-states/{ESTADO_ID}/proposal",
    {
        "aceptacion_cliente": True,
        "aceptacion_interna": True,
        "revision_interna": True,
        "propuesta_mejoras": True,
    }
)

print(f"API Response: {result}")

time.sleep(0.5)
estado_test2 = get_estado_from_db(ESTADO_ID)
print(f"BD después: propuesta_mejoras = {estado_test2['propuesta_mejoras']}")

if estado_test2['propuesta_mejoras']:
    print("✅ TEST 2 PASÓ")
else:
    print("❌ TEST 2 FALLÓ - NO se actualizó en BD")

# TEST 3: generacion_llm_solicitada
print("\n" + "-"*70)
print("TEST 3: Activando generacion_llm_solicitada")
print("-"*70)

result = make_api_request(
    f"/project-version-states/{ESTADO_ID}/generation",
    {
        "generacion_solicitada": True,
    }
)

print(f"API Response: {result}")

time.sleep(0.5)
estado_test3 = get_estado_from_db(ESTADO_ID)
print(f"BD después: generacion_llm_solicitada = {estado_test3['generacion_llm_solicitada']}")

if estado_test3['generacion_llm_solicitada']:
    print("✅ TEST 3 PASÓ")
else:
    print("❌ TEST 3 FALLÓ - NO se actualizó en BD")

# RESUMEN FINAL
print("\n" + "="*70)
print("RESUMEN FINAL")
print("="*70)

estado_final = get_estado_from_db(ESTADO_ID)
print(f"\n📋 Estado final en BD (id={ESTADO_ID}):")
print(f"   revision_interna: {estado_final['revision_interna']}")
print(f"   propuesta_mejoras: {estado_final['propuesta_mejoras']}")
print(f"   generacion_llm_solicitada: {estado_final['generacion_llm_solicitada']}")

all_ok = (
    estado_final['revision_interna'] and
    estado_final['propuesta_mejoras'] and
    estado_final['generacion_llm_solicitada']
)

if all_ok:
    print("\n🎉 TODOS LOS TESTS PASARON")
else:
    print("\n💥 ALGUNOS TESTS FALLARON")

print("="*70 + "\n")
