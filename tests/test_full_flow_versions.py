#!/usr/bin/env python3
"""Test del flujo completo Frontend → Middleware → Broker → Backend → fmanagement"""

import requests
import pymysql

from tests.helpers import (
    get_db_connection,
    get_org_folder,
    get_prj_folder,
    get_service_urls,
)
_urls = get_service_urls()

print("\n" + "="*80)
print("TEST DEL FLUJO COMPLETO: Verificando versiones del proyecto")
print("="*80 + "\n")

# Paso 0: Obtener OTP de la base de datos
print("0. OBTENER OTP desde base de datos...")
try:
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT user_otp FROM users WHERE user_name = 'adminone'")
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if not result:
        print("   ❌ Usuario adminone no encontrado en la base de datos")
        exit(1)

    otp = result['user_otp']
    print(f"   ✓ OTP obtenido de la base de datos: {otp}")

except Exception as e:
    print(f"   ❌ Error accediendo a la base de datos: {e}")
    exit(1)

# Paso 1: Login en middleware (7_service_frontend)
print("\n1. LOGIN en Middleware (puerto 8007)...")
try:
    login_response = requests.post(
        f"{_urls['middleware']}/login",
        json={
            "user_name": "adminone",
            "password": "Password01",
            "otp": otp
        },
        timeout=10
    )

    if login_response.status_code != 200:
        print(f"   ❌ Error en login: {login_response.status_code}")
        print(f"   Respuesta: {login_response.text}")
        exit(1)

    tokens = login_response.json()
    access_token = tokens.get("access_token")
    session_token = tokens.get("session_token")
    user_id = tokens.get("user_id")
    org_id = tokens.get("organization_id")
    identity_type_id = tokens.get("identity_type_id")

    print(f"   ✓ Login exitoso - user_id={user_id}, org_id={org_id}")

except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Paso 2: Obtener versiones del proyecto desde Backend Core (vía Middleware → Broker)
print(f"\n2. OBTENER VERSIONES desde Backend Core (puerto 8003)...")
try:
    versions_response = requests.get(
        f"{_urls['backend_core']}/proyectos/1/versiones?org_id={org_id}",
        headers={
            "X-Access-Token": access_token,
            "X-Session-Token": session_token,
            "X-Client-App": "test_script"
        },
        timeout=10
    )

    if versions_response.status_code != 200:
        print(f"   ❌ Error: {versions_response.status_code}")
        print(f"   Respuesta: {versions_response.text}")
        exit(1)

    versions_data = versions_response.json()
    versiones = versions_data.get("versiones", [])

    print(f"   ✓ Versiones encontradas en base de datos: {len(versiones)}")
    for ver in versiones:
        print(f"     - {ver.get('version_folder')} (ID: {ver.get('id_version')})")

except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Paso 3: Para cada versión, obtener su contenido desde fmanagement
print(f"\n3. OBTENER CONTENIDO de cada versión vía Middleware → Broker → Backend → fmanagement...")
for version_info in versiones:
    version_id = version_info.get("id_version")
    version_name = version_info.get("version_folder")

    print(f"\n   → Procesando {version_name} (ID: {version_id})...")

    try:
        # Llamar al middleware que llama al broker que llama al backend que llama a fmanagement
        fmanagement_response = requests.post(
            f"{_urls['middleware']}/fmanagement/list",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Session-Token": session_token
            },
            json={
                "org_folder": get_org_folder(int(org_id)),
                "prj_folder": get_prj_folder(1),
                "version_folder": version_name,
                "user_id": user_id,
                "identity_type_id": identity_type_id
            },
            timeout=10
        )

        if fmanagement_response.status_code != 200:
            print(f"     ❌ Error HTTP {fmanagement_response.status_code}")
            print(f"     Respuesta: {fmanagement_response.text}")
            continue

        fmo_data = fmanagement_response.json()

        if fmo_data.get("success"):
            items = fmo_data.get("items", [])
            print(f"     ✓ Éxito: {len(items)} items encontrados en fmanagement")
            for item in items[:3]:  # Mostrar primeros 3 items
                print(f"       - {item.get('name')} ({'folder' if item.get('is_dir') else 'file'})")
        else:
            print(f"     ❌ Falló: {fmo_data.get('mensaje', 'Sin mensaje')}")

    except Exception as e:
        print(f"     ❌ Excepción: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*80)
print("RESUMEN:")
print(f"  • Base de datos devolvió: {len(versiones)} versiones")
print(f"  • Flujo completo probado para cada versión")
print("="*80 + "\n")
