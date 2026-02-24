#!/usr/bin/env python3
"""Test completo del flujo de entrenamiento con monitorización de todos los mensajes."""

import time
import httpx
import json
from datetime import datetime


def log(message: str, data: dict | None = None):
    """Log con timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"\n[{timestamp}] {message}")
    if data:
        print(json.dumps(data, indent=2, ensure_ascii=False))


def test_training_flow():
    """Test completo del flujo de entrenamiento."""

    print("=" * 80)
    print("TEST FLUJO COMPLETO DE ENTRENAMIENTO")
    print("=" * 80)

    # Configuración
    MIDDLEWARE_URL = "http://localhost:8007"
    BACKEND_CORE_URL = "http://localhost:8003"

    # Credenciales del usuario admin
    auth_payload = {
        "user_name": "admin",
        "password": "Admin123!"
    }

    client = httpx.Client(timeout=30.0)

    try:
        # PASO 1: Autenticación
        log("🔐 PASO 1: Autenticando usuario...")
        auth_response = client.post(
            f"{MIDDLEWARE_URL}/auth/login",
            json=auth_payload
        )
        log(f"   Status: {auth_response.status_code}")

        if auth_response.status_code != 200:
            log("❌ Error en autenticación", auth_response.json())
            return

        auth_data = auth_response.json()
        log("✅ Autenticación exitosa", {
            "user_id": auth_data.get("user_id"),
            "organization_id": auth_data.get("organization_id"),
            "token_length": len(auth_data.get("access_token", ""))
        })

        # Headers para siguientes requests
        headers = {
            "Authorization": f"Bearer {auth_data['access_token']}",
            "X-Session-Token": auth_data.get("session_token", ""),
            "Content-Type": "application/json"
        }

        # PASO 2: Obtener versión para entrenar
        log("📦 PASO 2: Obteniendo versión más reciente...")
        versions_response = client.get(
            f"{BACKEND_CORE_URL}/core/versions",
            headers=headers,
            params={"id_project": 1}
        )
        log(f"   Status: {versions_response.status_code}")

        if versions_response.status_code != 200:
            log("❌ Error obteniendo versiones", versions_response.json())
            return

        versions = versions_response.json()
        if not versions:
            log("❌ No hay versiones disponibles")
            return

        version = versions[0]
        log("✅ Versión seleccionada", {
            "id_version": version["id"],
            "nombre": version["nombre"],
            "path": version.get("path_version")
        })

        # PASO 3: Enviar solicitud de entrenamiento
        log("🚀 PASO 3: Enviando solicitud de entrenamiento...")

        training_payload = {
            "id_user": auth_data["user_id"],
            "id_organization": auth_data["organization_id"],
            "id_project": 1,
            "id_version": version["id"],
            "path_version": version.get("path_version", ""),
            "chunk_size": 500,
            "chunk_overlap": 50,
            "model_type": "nomic-embed-text:latest"
        }

        log("   Payload enviado:", training_payload)

        training_response = client.post(
            f"{MIDDLEWARE_URL}/training/entrenamientos",
            json=training_payload,
            headers=headers
        )

        log(f"   Status: {training_response.status_code}")

        if training_response.status_code != 200:
            log("❌ Error enviando entrenamiento")
            log("   Response headers:", dict(training_response.headers))
            try:
                error_data = training_response.json()
                log("   Error data:", error_data)
            except:
                log("   Response text:", training_response.text)
            return

        training_data = training_response.json()
        log("✅ Respuesta del entrenamiento recibida:", training_data)

        # VERIFICAR CAMPOS CRÍTICOS
        id_entrenamiento = training_data.get("id_entrenamiento", 0)
        collection_name = training_data.get("collection_name", "")
        numero_secuencia = training_data.get("numero_secuencia", 0)

        log("🔍 CAMPOS CRÍTICOS RECIBIDOS:")
        print(f"   id_entrenamiento: {id_entrenamiento} (type: {type(id_entrenamiento).__name__})")
        print(f"   collection_name: {collection_name}")
        print(f"   numero_secuencia: {numero_secuencia}")

        if id_entrenamiento == 0:
            log("⚠️  WARNING: id_entrenamiento es 0 - El polling NO funcionará")
        else:
            log(f"✅ id_entrenamiento válido: {id_entrenamiento}")

        # PASO 4: Polling del progreso
        if id_entrenamiento > 0:
            log(f"📊 PASO 4: Iniciando polling del progreso (id={id_entrenamiento})...")

            max_polls = 120  # 120 polls * 2s = 4 minutos máximo
            poll_interval = 2
            completed = False

            for i in range(max_polls):
                time.sleep(poll_interval)

                poll_response = client.get(
                    f"{BACKEND_CORE_URL}/core/entrenamientos/{id_entrenamiento}/progress",
                    headers=headers
                )

                if poll_response.status_code != 200:
                    log(f"   Poll #{i+1}: Error {poll_response.status_code}")
                    continue

                progress = poll_response.json()

                # Log resumido del progreso
                estado = progress.get("estado", "unknown")
                fase_actual = progress.get("fase_actual", "unknown")
                subfases = progress.get("subfases", [])
                completed_count = sum(1 for s in subfases if s.get("status") == "completed")

                log(f"   Poll #{i+1}: estado={estado}, fase={fase_actual}, subfases={completed_count}/16")

                # Mostrar última subfase completada
                if subfases:
                    last_completed = None
                    for subfase in reversed(subfases):
                        if subfase.get("status") == "completed":
                            last_completed = subfase
                            break

                    if last_completed:
                        print(f"      Última completada: {last_completed.get('subfase_key')} - {last_completed.get('subfase_name')}")

                # Verificar si terminó
                if estado == "completed":
                    log("✅ ENTRENAMIENTO COMPLETADO")
                    log("   Progreso final:", progress)
                    completed = True
                    break
                elif estado == "failed":
                    log("❌ ENTRENAMIENTO FALLÓ")
                    log("   Progreso final:", progress)
                    break

            if not completed and estado not in ["completed", "failed"]:
                log("⏱️  Tiempo de polling agotado (entrenamiento aún en progreso)")
        else:
            log("❌ PASO 4 OMITIDO: No se puede hacer polling con id_entrenamiento=0")

        log("\n" + "=" * 80)
        log("TEST COMPLETADO")
        log("=" * 80)

    except Exception as e:
        log(f"❌ Error durante el test: {e}")
        import traceback
        traceback.print_exc()

    finally:
        client.close()


if __name__ == "__main__":
    test_training_flow()
