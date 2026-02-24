#!/usr/bin/env python3
"""Script de prueba para verificar las versiones del proyecto con autenticación"""

import sys
import requests

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src/apps/5_web_frontend"))

# Importar las funciones
from adapters.api_client import get_project_versions

print("\n" + "="*60)
print("TEST: Verificando versiones del proyecto con auth")
print("="*60 + "\n")

# 1. Hacer login para obtener tokens
print("1. Haciendo login...")
MIDDLEWARE_URL = "http://localhost:8007"  # Puerto del middleware frontend (service_frontend)

try:
    login_response = requests.post(
        f"{MIDDLEWARE_URL}/login",
        json={
            "user_name": "adminone",
            "password": "password123"
        },
        timeout=10
    )

    if login_response.status_code == 200:
        login_data = login_response.json()
        access_token = login_data.get("access_token", "")
        session_token = login_data.get("session_token", "")
        print(f"✓ Login exitoso!")
        print(f"  Access token: {access_token[:50]}..." if access_token else "  No access token")
        print(f"  Session token: {session_token[:50]}..." if session_token else "  No session token")

        # 2. Obtener versiones del proyecto
        project_id = 1
        print(f"\n2. Llamando a get_project_versions(project_id={project_id})...")

        result = get_project_versions(
            project_id=project_id,
            access_token=access_token,
            session_token=session_token
        )

        print(f"\nRespuesta: {result}")
        print(f"\nNúmero de versiones: {len(result.get('versiones', []))}")

        if result.get('versiones'):
            print("\nDetalles de versiones encontradas:")
            for idx, ver in enumerate(result.get('versiones', [])):
                print(f"  Versión {idx+1}: {ver}")
        else:
            print("\n⚠️  No se encontraron versiones!")

    else:
        print(f"❌ Error en login: {login_response.status_code} - {login_response.text}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("FIN DEL TEST")
print("="*60 + "\n")
