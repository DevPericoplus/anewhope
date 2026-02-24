#!/usr/bin/env python3
"""Test que simula exactamente lo que hace el explorador al cargar un proyecto"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src/apps/5_web_frontend"))

from tests.helpers import get_service_urls, get_db_connection

# Obtener OTP
conn = get_db_connection(database="myllm_core_db")
cursor = conn.cursor()
cursor.execute("SELECT user_otp FROM users WHERE user_name = 'adminone'")
result = cursor.fetchone()
cursor.close()
conn.close()
otp = result['user_otp']

# Login
import requests
_urls = get_service_urls()
login_response = requests.post(
    f"{_urls['middleware']}/login",
    json={"user_name": "adminone", "password": "Password01", "otp": otp},
    timeout=10
)
tokens = login_response.json()
access_token = tokens["access_token"]
session_token = tokens["session_token"]

print("\n" + "="*80)
print("TEST: Simulando carga del explorador")
print("="*80 + "\n")

# Simular lo que hace ExploradorState.load_from_api()
from adapters.api_client import fmanagement_list_all_project_versions

org_id = 1
project_id = 1
org_folder = f"ORG{str(org_id).zfill(4)}"
prj_folder = f"PRJ{str(project_id).zfill(5)}"

print(f"Llamando a fmanagement_list_all_project_versions...")
print(f"  org_id: {org_id}")
print(f"  project_id: {project_id}")
print(f"  org_folder: {org_folder}")
print(f"  prj_folder: {prj_folder}\n")

response = fmanagement_list_all_project_versions(
    org_id=org_id,
    project_id=project_id,
    org_folder=org_folder,
    prj_folder=prj_folder,
    access_token=access_token,
    session_token=session_token,
)

print("Respuesta:")
print(f"  status: {response.get('status')}")
print(f"  path: {response.get('path')}")

items = response.get("items", [])
print(f"  items (nivel raíz): {len(items)}\n")

if items:
    project_item = items[0]
    print(f"Proyecto: {project_item.get('name')}")

    versions = project_item.get("items", [])
    print(f"  Versiones encontradas: {len(versions)}\n")

    for ver in versions:
        print(f"  → {ver.get('name')}")
        print(f"     is_dir: {ver.get('is_dir')}")
        print(f"     size_bytes: {ver.get('size_bytes')}")
        print(f"     sub-items: {len(ver.get('items', []))}")

print("\n" + "="*80)
print("FIN DEL TEST")
print("="*80 + "\n")
