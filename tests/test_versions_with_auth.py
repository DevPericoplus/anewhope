#!/usr/bin/env python3
"""Script de prueba para verificar las versiones del proyecto con autenticación"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
from tests.helpers import fetch_user_otp, get_service_urls, install_requests_shim
from tests.import_aliases import register_repo_helpers

register_repo_helpers()
install_requests_shim()
import requests

sys.path.insert(0, str(_ROOT / "src/apps/5_web_frontend"))
from adapters.api_client import get_project_versions

print("\n" + "="*60)
print("TEST: Verificando versiones del proyecto con auth")
print("="*60 + "\n")

print("1. Haciendo login...")
_urls = get_service_urls()
MIDDLEWARE_URL = _urls["middleware"]

try:
    otp = fetch_user_otp("adminone")
    login_response = requests.post(
        f"{MIDDLEWARE_URL}/login",
        json={
            "user_name": "adminone",
            "password": "Password01",
            "otp": otp,
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
        sys.exit(1)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("FIN DEL TEST")
print("="*60 + "\n")
