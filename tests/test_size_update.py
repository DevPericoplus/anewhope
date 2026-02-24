#!/usr/bin/env python3
"""Test para verificar que se actualizan los tamaños en BD"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src/apps/5_web_frontend"))

import pymysql

# Obtener OTP y login
conn = pymysql.connect(
    host='localhost',
    user='myllm_admin',
    password='Us3r@dminP@ss',
    database='myllm_core_db',
    charset='utf8mb4'
)
cursor = conn.cursor(pymysql.cursors.DictCursor)
cursor.execute("SELECT user_otp FROM users WHERE user_name = 'adminone'")
result = cursor.fetchone()
cursor.close()
conn.close()
otp = result['user_otp']

import requests
login_response = requests.post(
    "http://localhost:8007/login",
    json={"user_name": "adminone", "password": "Password01", "otp": otp},
    timeout=10
)
tokens = login_response.json()
access_token = tokens["access_token"]
session_token = tokens["session_token"]

print("\n" + "="*80)
print("TEST: Verificar actualización de tamaños en BD")
print("="*80 + "\n")

# Llamar a la función que carga y actualiza
from adapters.api_client import fmanagement_list_all_project_versions

print("Llamando a fmanagement_list_all_project_versions para proyecto 2...")
response = fmanagement_list_all_project_versions(
    org_id=1,
    project_id=2,
    org_folder="ORG0001",
    prj_folder="PRJ00002",
    access_token=access_token,
    session_token=session_token,
)

print(f"\nRespuesta status: {response.get('status')}")

if response.get("status") == "success" and response.get("items"):
    project_item = response["items"][0]
    versions = project_item.get("items", [])
    print(f"Versiones encontradas: {len(versions)}\n")

    for v in versions[:3]:  # Solo primeras 3 para no saturar
        print(f"  → {v.get('name')}: {v.get('size_bytes', 0)} bytes")

# Verificar en BD
print("\n" + "="*80)
print("Verificando tamaños en BD...")
print("="*80 + "\n")

conn = pymysql.connect(
    host='localhost',
    user='myllm_admin',
    password='Us3r@dminP@ss',
    database='myllm_projects_db',
    charset='utf8mb4'
)
cursor = conn.cursor(pymysql.cursors.DictCursor)
cursor.execute("SELECT id_version, size_bytes, updated_at FROM version_states WHERE id_proyecto = 2 ORDER BY id_version LIMIT 5")
results = cursor.fetchall()
cursor.close()
conn.close()

for r in results:
    print(f"Versión {r['id_version']}: {r['size_bytes']} bytes (actualizado: {r['updated_at']})")

print("\n" + "="*80)
print("FIN DEL TEST")
print("="*80 + "\n")
