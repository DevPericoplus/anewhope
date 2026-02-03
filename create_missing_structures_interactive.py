#!/usr/bin/env python3
"""Script interactivo para crear estructuras faltantes en fmanagement.

Este script:
1. Solicita OTP interactivamente
2. Autentica via middleware
3. Llama al backend para crear estructuras mediante create_version_full
4. Verifica las estructuras creadas
"""

import urllib.request
import urllib.error
import json
import sys
from getpass import getpass

# Configuración
MIDDLEWARE_URL = "http://localhost:8007"
BACKEND_URL = "http://localhost:8005"

# Credenciales base (OTP se solicita)
USER = "adminone"
PASSWORD = "adminone"

# Estructuras a crear (proyecto_id, version_id, org_id, nombre)
STRUCTURES_TO_CREATE = [
    (1, 1, 1, "dptocomercial"),
    (1, 2, 1, "dptocomercial"),
    (2, 1, 1, "botweb"),
    (3, 1, 1, "test"),
    (4, 1, 1, "presales"),
    (5, 1, 1, "test_updated"),
]


def login(otp: str):
    """Hace login y obtiene tokens.

    Args:
        otp: Código OTP actual

    Returns:
        tuple: (access_token, session_token) o (None, None) si falla
    """
    print("\n[1/4] Obteniendo tokens de autenticación...")

    data = json.dumps({
        "user_name": USER,
        "password": PASSWORD,
        "otp": otp,
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
            print(f"  Access token: {access_token[:20]}...")
            return access_token, session_token
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"  ❌ Error en login: {e.code}")
        print(f"     {error_body}")
        return None, None


def create_version_structure(
    project_id: int,
    version_id: int,
    org_id: int,
    nombre: str,
    access_token: str
):
    """Crea una estructura de versión completa via backend core.

    Usa el endpoint de fmanagement operations del backend core,
    que internamente maneja la autenticación con fmanagement.

    Args:
        project_id: ID del proyecto
        version_id: ID de la versión (1, 2, 3...)
        org_id: ID de la organización
        nombre: Nombre descriptivo
        access_token: Token de autenticación

    Returns:
        bool: True si se creó correctamente
    """
    version_str = f"v{version_id:03d}"
    org_folder = f"ORG{org_id:04d}"
    prj_folder = f"PRJ{project_id:04d}"

    path = f"{org_folder}/{prj_folder}/{version_str}"
    print(f"\n  Creando: {path} ({nombre})")

    # Parámetros para crear la estructura
    params = {
        "operation": "create_folder",
        "orgpath": org_folder,
        "prjpath": prj_folder,
        "versionpath": version_str,
        "subfolders": "",  # Raíz primero
        "identity_type_id": 1,
        "iduser": 1,
        "basepath": "default",
    }

    # Crear carpeta raíz de versión
    print(f"    Creando carpeta raíz: {path}")

    data = json.dumps(params).encode('utf-8')
    req = urllib.request.Request(
        f"{BACKEND_URL}/fmanagement",
        data=data,
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'X-User-ID': '1',
            'X-Identity-Type-ID': '1',
            'X-Client-App': 'create-structures-script',
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req) as response:
            print(f"      ✅ Carpeta raíz creada")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"      ⚠️  Error: {e.code} - {error_body}")
        return False

    # Crear subcarpetas base
    base_folders = ["datos", "modelos", "evaluaciones", "resultados"]
    success_count = 0

    for folder in base_folders:
        params["subfolders"] = folder
        print(f"    Creando subcarpeta: {folder}...")

        data = json.dumps(params).encode('utf-8')
        req = urllib.request.Request(
            f"{BACKEND_URL}/fmanagement",
            data=data,
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'X-User-ID': '1',
                'X-Identity-Type-ID': '1',
                'X-Client-App': 'create-structures-script',
            },
            method='POST'
        )

        try:
            with urllib.request.urlopen(req):
                print(f"      ✅ {folder}")
                success_count += 1
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            print(f"      ⚠️  Error en {folder}: {e.code} - {error_body}")

    return success_count == len(base_folders)


def verify_structure(org_id: int, project_id: int, version_id: int, access_token: str):
    """Verifica que la estructura existe en fmanagement.

    Args:
        org_id: ID de la organización
        project_id: ID del proyecto
        version_id: ID de la versión
        access_token: Token de autenticación

    Returns:
        bool: True si existe
    """
    version_str = f"v{version_id:03d}"
    org_folder = f"ORG{org_id:04d}"
    prj_folder = f"PRJ{project_id:04d}"

    params = {
        "operation": "list",
        "orgpath": org_folder,
        "prjpath": prj_folder,
        "versionpath": version_str,
        "iduser": 1,
        "basepath": "default",
    }

    # Codificar parámetros para GET
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])

    req = urllib.request.Request(
        f"{BACKEND_URL}/fmanagement?{query_string}",
        headers={
            'Authorization': f'Bearer {access_token}',
            'X-User-ID': '1',
            'X-Identity-Type-ID': '1',
            'X-Client-App': 'create-structures-script',
        },
        method='GET'
    )

    try:
        with urllib.request.urlopen(req) as response:
            return True
    except urllib.error.HTTPError:
        return False


def main():
    """Ejecuta el proceso de creación."""
    print("=" * 70)
    print("CREACIÓN DE ESTRUCTURAS FALTANTES EN FMANAGEMENT")
    print("=" * 70)

    # Solicitar OTP
    print("\nNota: El código OTP cambia con cada login exitoso.")
    print("Asegúrate de usar el OTP actual para el usuario 'adminone'.")
    otp = input("\nIngresa el código OTP actual: ").strip()

    if not otp:
        print("\n❌ OTP requerido")
        return 1

    # 1. Login
    access_token, session_token = login(otp)

    if not access_token:
        print("\n❌ No se pudo obtener token de autenticación")
        print("Verifica que:")
        print("  - El usuario y contraseña sean correctos")
        print("  - El OTP sea el actual (cambia con cada login)")
        print("  - El middleware esté corriendo en puerto 8007")
        return 1

    # 2. Crear estructuras
    print(f"\n[2/4] Creando {len(STRUCTURES_TO_CREATE)} estructuras...")

    success_count = 0
    for project_id, version_id, org_id, nombre in STRUCTURES_TO_CREATE:
        try:
            result = create_version_structure(
                project_id, version_id, org_id, nombre, access_token
            )
            if result:
                success_count += 1
        except Exception as e:
            print(f"    ❌ Excepción: {e}")

    # 3. Verificar estructuras creadas
    print(f"\n[3/4] Verificando estructuras creadas...")

    verified_count = 0
    for project_id, version_id, org_id, nombre in STRUCTURES_TO_CREATE:
        org_folder = f"ORG{org_id:04d}"
        prj_folder = f"PRJ{project_id:04d}"
        version_str = f"v{version_id:03d}"
        path = f"{org_folder}/{prj_folder}/{version_str}"

        exists = verify_structure(org_id, project_id, version_id, access_token)
        status = "✅" if exists else "❌"
        print(f"  {status} {path}")

        if exists:
            verified_count += 1

    # 4. Resumen
    print("\n[4/4] Resumen:")
    print(f"  Creadas:    {success_count}/{len(STRUCTURES_TO_CREATE)}")
    print(f"  Verificadas: {verified_count}/{len(STRUCTURES_TO_CREATE)}")

    print("\n" + "=" * 70)
    if verified_count == len(STRUCTURES_TO_CREATE):
        print("✅ PROCESO COMPLETADO EXITOSAMENTE")
    else:
        print("⚠️  PROCESO COMPLETADO CON ERRORES")
    print("=" * 70)

    return 0 if verified_count == len(STRUCTURES_TO_CREATE) else 1


if __name__ == "__main__":
    sys.exit(main())
