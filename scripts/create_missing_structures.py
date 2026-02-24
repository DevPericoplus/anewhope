#!/usr/bin/env python3
"""Script para crear estructuras faltantes en fmanagement usando autenticación."""

import urllib.request
import urllib.error
import json

# Configuración
MIDDLEWARE_URL = "http://localhost:8007"
BACKEND_URL = "http://localhost:8005"

# Credenciales
USER = "adminone"
PASSWORD = "adminone"
OTP = "0268"

# Estructuras a crear (proyecto_id, version_id, org_id, nombre)
STRUCTURES_TO_CREATE = [
    (1, 1, 1, "dptocomercial"),
    (1, 2, 1, "dptocomercial"),
    (2, 1, 1, "botweb"),
    (3, 1, 1, "test"),
    (4, 1, 1, "presales"),
    (5, 1, 1, "test_updated"),
]


def login():
    """Hace login y obtiene tokens."""
    print("[1/3] Obteniendo tokens de autenticación...")

    data = json.dumps({
        "user_name": USER,
        "password": PASSWORD,
        "otp": OTP,
    }).encode('utf-8')

    req = urllib.request.Request(
        f"{MIDDLEWARE_URL}/login",
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            access_token = result.get("access_token")
            session_token = result.get("session_token")
            print(f"  ✅ Login exitoso")
            return access_token, session_token
    except urllib.error.HTTPError as e:
        print(f"  ❌ Error en login: {e.code}")
        print(f"     {e.read().decode('utf-8')}")
        return None, None


def create_folder_structure(project_id, version_id, org_id, nombre, access_token):
    """Crea una estructura de carpetas via backend core.

    Usa el endpoint de fmanagement operations del backend core.
    """
    org_folder = f"ORG{org_id:04d}"
    prj_folder = f"PRJ{project_id:04d}"
    version_folder = f"v{version_id:03d}"

    path = f"{org_folder}/{prj_folder}/{version_folder}"
    print(f"\n  Creando: {path} ({nombre})")

    # Crear carpeta raíz de versión
    params = {
        "operation": "create_folder",
        "orgpath": org_folder,
        "prjpath": prj_folder,
        "versionpath": version_folder,
        "subfolders": "",  # Raíz
        "identity_type_id": 1,
        "iduser": 1,
        "basepath": "default",
    }

    print(f"    Creando carpeta raíz...")

    data = json.dumps(params).encode('utf-8')
    req = urllib.request.Request(
        f"{BACKEND_URL}/fmanagement",
        data=data,
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req) as response:
            print(f"    ✅ Carpeta raíz creada")
    except urllib.error.HTTPError as e:
        print(f"    ⚠️  Error: {e.code} - {e.read().decode('utf-8')}")
        return False

    # Crear subcarpetas base
    base_folders = ["datos", "modelos", "evaluaciones", "resultados"]
    for folder in base_folders:
        params["subfolders"] = folder

        print(f"    Creando subcarpeta: {folder}...")

        data = json.dumps(params).encode('utf-8')
        req = urllib.request.Request(
            f"{BACKEND_URL}/fmanagement",
            data=data,
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            method='POST'
        )

        try:
            with urllib.request.urlopen(req):
                print(f"      ✅ {folder}")
        except urllib.error.HTTPError as e:
            print(f"      ⚠️  Error en {folder}: {e.code}")

    return True


def main():
    """Ejecuta el proceso de creación."""
    print("="*70)
    print("CREACIÓN DE ESTRUCTURAS FALTANTES EN FMANAGEMENT")
    print("="*70)

    # 1. Login
    access_token, session_token = login()

    if not access_token:
        print("\n❌ No se pudo obtener token de autenticación")
        return

    # 2. Crear estructuras
    print(f"\n[2/3] Creando {len(STRUCTURES_TO_CREATE)} estructuras...")

    success_count = 0
    for project_id, version_id, org_id, nombre in STRUCTURES_TO_CREATE:
        try:
            result = create_folder_structure(
                project_id, version_id, org_id, nombre, access_token
            )
            if result:
                success_count += 1
        except Exception as e:
            print(f"    ❌ Excepción: {e}")

    # 3. Resumen
    print("\n[3/3] Resumen:")
    print(f"  ✅ {success_count}/{len(STRUCTURES_TO_CREATE)} estructuras creadas")
    print("\n" + "="*70)
    print("PROCESO COMPLETADO")
    print("="*70)


if __name__ == "__main__":
    main()
