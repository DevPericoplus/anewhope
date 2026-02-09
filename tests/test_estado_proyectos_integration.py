"""
Test de integración para página Estado Proyectos.

Simula actualizaciones de todos los switches y verifica persistencia en BD.
"""

import pytest
import requests
from typing import Any


# Configuración
BACKEND_CORE_URL = "http://localhost:8003"
BROKER_URL = "http://localhost:8008"
MIDDLEWARE_URL = "http://localhost:8007"

# Datos de prueba
TEST_ORG_ID = 1
TEST_PROJECT_ID = 1
TEST_VERSION_ID = 1
TEST_USER_ID = 1
TEST_IDENTITY_TYPE_ID = 1  # SuperAdmin


class TestEstadoProyectosIntegration:
    """Test de integración para Estado Proyectos."""

    @pytest.fixture(scope="class")
    def estado_id(self):
        """Obtiene o crea un estado_version de prueba."""
        import pymysql

        # Conectar a la base de datos
        conn = pymysql.connect(
            host="localhost",
            user="myllm_admin",
            password="Us3r@dminP@ss",
            database="myllm_projects_db",
            charset="utf8mb4",
        )

        try:
            with conn.cursor() as cursor:
                # Buscar estado existente
                cursor.execute(
                    """
                    SELECT id FROM estado_version
                    WHERE id_organizacion = %s
                      AND id_proyecto = %s
                      AND id_version = %s
                    LIMIT 1
                    """,
                    (TEST_ORG_ID, TEST_PROJECT_ID, TEST_VERSION_ID),
                )
                result = cursor.fetchone()

                if result:
                    estado_id = result[0]
                    print(f"✓ Usando estado_version existente: id={estado_id}")
                else:
                    # Crear nuevo estado
                    cursor.execute(
                        """
                        INSERT INTO estado_version (
                            id_organizacion, id_proyecto, id_version,
                            state, protected, size,
                            final_c, final_i,
                            revision_interna, propuesta_mejoras,
                            entrenamiento_inicial_solicitado,
                            entrenamiento_inicial_completado,
                            evaluacion_entrenamiento, reentrenamiento,
                            optimizacion, control_calidad_aprobado,
                            generacion_llm_solicitada, generacion_llm_completada,
                            notificacion_descarga_enviada
                        ) VALUES (
                            %s, %s, %s,
                            'Abierta', FALSE, 0,
                            FALSE, FALSE,
                            FALSE, FALSE,
                            FALSE, FALSE,
                            FALSE, FALSE,
                            FALSE, FALSE,
                            FALSE, FALSE,
                            FALSE
                        )
                        """,
                        (TEST_ORG_ID, TEST_PROJECT_ID, TEST_VERSION_ID),
                    )
                    conn.commit()
                    estado_id = cursor.lastrowid
                    print(f"✓ Creado nuevo estado_version: id={estado_id}")

                yield estado_id
        finally:
            conn.close()

    def _get_estado_from_db(self, estado_id: int) -> dict[str, Any]:
        """Lee el estado actual desde la base de datos."""
        import pymysql

        conn = pymysql.connect(
            host="localhost",
            user="myllm_admin",
            password="Us3r@dminP@ss",
            database="myllm_projects_db",
            charset="utf8mb4",
        )

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        state, protected,
                        final_c, final_i,
                        revision_interna, propuesta_mejoras,
                        entrenamiento_inicial_solicitado,
                        entrenamiento_inicial_completado,
                        evaluacion_entrenamiento, reentrenamiento,
                        optimizacion, control_calidad_aprobado,
                        generacion_llm_solicitada, generacion_llm_completada,
                        notificacion_descarga_enviada
                    FROM estado_version
                    WHERE id = %s
                    """,
                    (estado_id,),
                )
                row = cursor.fetchone()

                if not row:
                    raise ValueError(f"Estado {estado_id} no encontrado")

                return {
                    "state": row[0],
                    "protected": bool(row[1]),
                    "final_c": bool(row[2]),
                    "final_i": bool(row[3]),
                    "revision_interna": bool(row[4]),
                    "propuesta_mejoras": bool(row[5]),
                    "entrenamiento_inicial_solicitado": bool(row[6]),
                    "entrenamiento_inicial_completado": bool(row[7]),
                    "evaluacion_entrenamiento": bool(row[8]),
                    "reentrenamiento": bool(row[9]),
                    "optimizacion": bool(row[10]),
                    "control_calidad_aprobado": bool(row[11]),
                    "generacion_llm_solicitada": bool(row[12]),
                    "generacion_llm_completada": bool(row[13]),
                    "notificacion_descarga_enviada": bool(row[14]),
                }
        finally:
            conn.close()

    def test_01_fase_propuesta_aceptaciones(self, estado_id):
        """Test Fase 1: Aceptación Cliente e Interna."""
        print(f"\n{'='*70}")
        print("TEST 1: Fase Propuesta - Aceptaciones")
        print(f"{'='*70}")

        # 1. Activar Aceptación Cliente (final_c = True)
        print("\n[1/2] Activando Aceptación Cliente...")
        response = requests.patch(
            f"{BACKEND_CORE_URL}/project-version-states/{estado_id}/proposal",
            params={
                "user_id": TEST_USER_ID,
                "identity_type_id": TEST_IDENTITY_TYPE_ID,
            },
            json={
                "aceptacion_cliente": True,
                "aceptacion_interna": False,
            },
        )

        assert response.status_code == 200, f"Error: {response.status_code} - {response.text}"
        result = response.json()
        assert result["success"] is True
        print(f"  ✓ Response: {result['message']}")

        # Verificar en BD
        estado = self._get_estado_from_db(estado_id)
        assert estado["final_c"] is True, "final_c debe ser True"
        assert estado["final_i"] is False, "final_i debe ser False"
        assert estado["state"] == "Protegida", f"state debe ser 'Protegida', es '{estado['state']}'"
        assert estado["protected"] is True, "protected debe ser True"
        print("  ✓ Verificado en BD: final_c=True, state='Protegida', protected=True")

        # 2. Activar Aceptación Interna (final_i = True)
        print("\n[2/2] Activando Aceptación Interna...")
        response = requests.patch(
            f"{BACKEND_CORE_URL}/project-version-states/{estado_id}/proposal",
            params={
                "user_id": TEST_USER_ID,
                "identity_type_id": TEST_IDENTITY_TYPE_ID,
            },
            json={
                "aceptacion_cliente": True,
                "aceptacion_interna": True,
            },
        )

        assert response.status_code == 200, f"Error: {response.status_code} - {response.text}"
        result = response.json()
        assert result["success"] is True
        print(f"  ✓ Response: {result['message']}")

        # Verificar en BD
        estado = self._get_estado_from_db(estado_id)
        assert estado["final_c"] is True, "final_c debe ser True"
        assert estado["final_i"] is True, "final_i debe ser True"
        assert estado["state"] == "Final", f"state debe ser 'Final', es '{estado['state']}'"
        assert estado["protected"] is True, "protected debe ser True"
        print("  ✓ Verificado en BD: final_i=True, state='Final', protected=True")
        print(f"\n{'='*70}")
        print("✓ TEST 1 COMPLETADO")
        print(f"{'='*70}")

    def test_02_fase_entrenamiento(self, estado_id):
        """Test Fase 2: Entrenamiento Inicial."""
        print(f"\n{'='*70}")
        print("TEST 2: Fase Entrenamiento")
        print(f"{'='*70}")

        # Activar Entrenamiento Completado
        print("\n[1/1] Activando Entrenamiento Completado...")
        response = requests.patch(
            f"{BACKEND_CORE_URL}/project-version-states/{estado_id}/training",
            params={
                "user_id": TEST_USER_ID,
                "identity_type_id": TEST_IDENTITY_TYPE_ID,
            },
            json={
                "completado": True,
            },
        )

        assert response.status_code == 200, f"Error: {response.status_code} - {response.text}"
        result = response.json()
        assert result["success"] is True
        print(f"  ✓ Response: {result['message']}")

        # Verificar en BD
        estado = self._get_estado_from_db(estado_id)
        assert estado["entrenamiento_inicial_completado"] is True
        print("  ✓ Verificado en BD: entrenamiento_inicial_completado=True")
        print(f"\n{'='*70}")
        print("✓ TEST 2 COMPLETADO")
        print(f"{'='*70}")

    def test_03_fase_evaluacion(self, estado_id):
        """Test Fase 3: Evaluación y Reentrenamiento."""
        print(f"\n{'='*70}")
        print("TEST 3: Fase Evaluación")
        print(f"{'='*70}")

        # Activar todos los campos de evaluación
        print("\n[1/1] Activando campos de evaluación...")
        response = requests.patch(
            f"{BACKEND_CORE_URL}/project-version-states/{estado_id}/evaluation",
            params={
                "user_id": TEST_USER_ID,
                "identity_type_id": TEST_IDENTITY_TYPE_ID,
            },
            json={
                "evaluacion": True,
                "reentrenamiento": True,
                "optimizacion": True,
                "calidad_aprobada": True,
            },
        )

        assert response.status_code == 200, f"Error: {response.status_code} - {response.text}"
        result = response.json()
        assert result["success"] is True
        print(f"  ✓ Response: {result['message']}")

        # Verificar en BD
        estado = self._get_estado_from_db(estado_id)
        assert estado["evaluacion_entrenamiento"] is True
        assert estado["reentrenamiento"] is True
        assert estado["optimizacion"] is True
        assert estado["control_calidad_aprobado"] is True
        print("  ✓ Verificado en BD: todos los campos de evaluación=True")
        print(f"\n{'='*70}")
        print("✓ TEST 3 COMPLETADO")
        print(f"{'='*70}")

    def test_04_fase_generacion(self, estado_id):
        """Test Fase 4: Generación del Modelo."""
        print(f"\n{'='*70}")
        print("TEST 4: Fase Generación")
        print(f"{'='*70}")

        # Activar Generación Completada
        print("\n[1/1] Activando Generación Completada...")
        response = requests.patch(
            f"{BACKEND_CORE_URL}/project-version-states/{estado_id}/generation",
            params={
                "user_id": TEST_USER_ID,
                "identity_type_id": TEST_IDENTITY_TYPE_ID,
            },
            json={
                "generacion_completada": True,
            },
        )

        assert response.status_code == 200, f"Error: {response.status_code} - {response.text}"
        result = response.json()
        assert result["success"] is True
        print(f"  ✓ Response: {result['message']}")

        # Verificar en BD
        estado = self._get_estado_from_db(estado_id)
        assert estado["generacion_llm_completada"] is True
        print("  ✓ Verificado en BD: generacion_llm_completada=True")
        print(f"\n{'='*70}")
        print("✓ TEST 4 COMPLETADO")
        print(f"{'='*70}")

    def test_05_fase_notificacion(self, estado_id):
        """Test Fase 5: Notificación de Descarga."""
        print(f"\n{'='*70}")
        print("TEST 5: Fase Notificación")
        print(f"{'='*70}")

        # Activar Notificación Enviada
        print("\n[1/1] Activando Notificación Enviada...")
        response = requests.patch(
            f"{BACKEND_CORE_URL}/project-version-states/{estado_id}/notification",
            params={
                "user_id": TEST_USER_ID,
                "identity_type_id": TEST_IDENTITY_TYPE_ID,
            },
            json={
                "notificacion_enviada": True,
            },
        )

        assert response.status_code == 200, f"Error: {response.status_code} - {response.text}"
        result = response.json()
        assert result["success"] is True
        print(f"  ✓ Response: {result['message']}")

        # Verificar en BD
        estado = self._get_estado_from_db(estado_id)
        assert estado["notificacion_descarga_enviada"] is True
        print("  ✓ Verificado en BD: notificacion_descarga_enviada=True")
        print(f"\n{'='*70}")
        print("✓ TEST 5 COMPLETADO")
        print(f"{'='*70}")

    def test_06_resumen_final(self, estado_id):
        """Test final: Verificar estado completo."""
        print(f"\n{'='*70}")
        print("RESUMEN FINAL: Estado completo del registro")
        print(f"{'='*70}")

        estado = self._get_estado_from_db(estado_id)

        print("\n📋 Estado final del registro:")
        print(f"  ID: {estado_id}")
        print(f"  State: {estado['state']}")
        print(f"  Protected: {estado['protected']}")
        print("\n  Fase 1 - Propuesta:")
        print(f"    final_c (Aceptación Cliente): {estado['final_c']}")
        print(f"    final_i (Aceptación Interna): {estado['final_i']}")
        print("\n  Fase 2 - Entrenamiento:")
        print(f"    entrenamiento_inicial_completado: {estado['entrenamiento_inicial_completado']}")
        print("\n  Fase 3 - Evaluación:")
        print(f"    evaluacion_entrenamiento: {estado['evaluacion_entrenamiento']}")
        print(f"    reentrenamiento: {estado['reentrenamiento']}")
        print(f"    optimizacion: {estado['optimizacion']}")
        print(f"    control_calidad_aprobado: {estado['control_calidad_aprobado']}")
        print("\n  Fase 4 - Generación:")
        print(f"    generacion_llm_completada: {estado['generacion_llm_completada']}")
        print("\n  Fase 5 - Notificación:")
        print(f"    notificacion_descarga_enviada: {estado['notificacion_descarga_enviada']}")

        # Verificar que todo esté activado
        assert estado["final_c"] is True
        assert estado["final_i"] is True
        assert estado["entrenamiento_inicial_completado"] is True
        assert estado["evaluacion_entrenamiento"] is True
        assert estado["reentrenamiento"] is True
        assert estado["optimizacion"] is True
        assert estado["control_calidad_aprobado"] is True
        assert estado["generacion_llm_completada"] is True
        assert estado["notificacion_descarga_enviada"] is True

        print(f"\n{'='*70}")
        print("✓ TODOS LOS TESTS COMPLETADOS EXITOSAMENTE")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
