#!/usr/bin/env python3
"""
Script de verificación del flujo de permisos entre Backend Core y fmanagement.

Este script verifica que:
1. Backend Core esté corriendo y responda
2. fmanagement esté corriendo y responda
3. El endpoint /permissions del Backend Core funcione correctamente
4. fmanagement pueda consultar permisos al Backend Core
5. El flujo completo de autenticación y permisos funcione

Uso:
    python verify_permissions_flow.py
"""

import json
import sys
from typing import Any

import requests

# Configuración de URLs
BACKEND_CORE_URL = "http://localhost:8003"
FMANAGEMENT_URL = "http://localhost:1666"

# Colores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_step(step: str, status: str = "info"):
    """Imprime un paso del proceso con formato."""
    color = BLUE if status == "info" else GREEN if status == "ok" else RED if status == "error" else YELLOW
    symbol = "ℹ" if status == "info" else "✓" if status == "ok" else "✗" if status == "error" else "⚠"
    print(f"{color}{symbol} {step}{RESET}")


def print_json(data: dict[str, Any]):
    """Imprime JSON con formato."""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def check_service_health(service_name: str, url: str) -> bool:
    """Verifica que un servicio esté corriendo."""
    print_step(f"Verificando {service_name} en {url}...", "info")
    try:
        response = requests.get(f"{url}/health", timeout=5)
        if response.status_code == 200:
            print_step(f"{service_name} está corriendo correctamente", "ok")
            return True
        else:
            print_step(
                f"{service_name} respondió con código {response.status_code}",
                "warning",
            )
            return False
    except requests.exceptions.ConnectionError:
        print_step(f"No se puede conectar a {service_name}", "error")
        return False
    except Exception as e:
        print_step(f"Error al verificar {service_name}: {e}", "error")
        return False


def test_login(username: str = "admin", password: str = "admin123") -> dict[str, str] | None:
    """Prueba el login y retorna los tokens."""
    print_step(f"Intentando login con usuario '{username}'...", "info")
    try:
        response = requests.post(
            f"{BACKEND_CORE_URL}/login",
            json={
                "user_name": username,
                "password": password,
                "otp": "",
            },
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            print_step("Login exitoso", "ok")
            print(f"  • User ID: {data.get('id_user')}")
            print(f"  • Organization ID: {data.get('id_organization')}")
            print(f"  • Identity Type ID: {data.get('identity_type_id')}")
            return {
                "access_token": data.get("access_token"),
                "session_token": data.get("session_token"),
                "user_id": str(data.get("id_user")),
                "identity_type_id": str(data.get("identity_type_id")),
                "organization_id": str(data.get("id_organization")),
            }
        else:
            print_step(f"Login falló: {response.status_code}", "error")
            print(f"  Respuesta: {response.text}")
            return None
    except Exception as e:
        print_step(f"Error en login: {e}", "error")
        return None


def test_permissions_endpoint(
    identity_type_id: str, access_token: str, session_token: str
) -> dict[str, Any] | None:
    """Prueba el endpoint de permisos del Backend Core."""
    print_step(
        f"Consultando permisos para identity_type_id={identity_type_id}...", "info"
    )
    try:
        response = requests.get(
            f"{BACKEND_CORE_URL}/permissions",
            params={"identity_type_id": identity_type_id},
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Session-Token": session_token,
            },
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            print_step("Permisos obtenidos correctamente", "ok")
            print(f"  • Identity Type ID: {data.get('identity_type_id')}")
            print(f"  • Permisos básicos: {len(data.get('permissions', []))}")
            low_level = data.get("low_level_permissions", {})
            if low_level:
                print(f"  • Permisos de bajo nivel:")
                # Mostrar algunos permisos de ejemplo
                for key in list(low_level.keys())[:5]:
                    print(f"    - {key}: {low_level[key]}")
                if len(low_level) > 5:
                    print(f"    ... y {len(low_level) - 5} más")
            return data
        else:
            print_step(f"Error al obtener permisos: {response.status_code}", "error")
            print(f"  Respuesta: {response.text}")
            return None
    except Exception as e:
        print_step(f"Error al consultar permisos: {e}", "error")
        return None


def test_fmanagement_permission_query(
    identity_type_id: str, access_token: str, session_token: str
) -> bool:
    """Simula cómo fmanagement consulta permisos al Backend Core."""
    print_step("Simulando consulta de fmanagement → Backend Core...", "info")
    try:
        # Esta es la misma llamada que hace fmanagement en main.go:280-287
        response = requests.get(
            f"{BACKEND_CORE_URL}/permissions",
            params={"identity_type_id": identity_type_id},
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Session-Token": session_token,
            },
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            low_level = data.get("low_level_permissions", {})

            # Verificar permisos clave para operaciones de archivos
            required_permissions = [
                "folder_create",
                "folder_read",
                "file_create",
                "file_read",
            ]

            all_granted = True
            print_step("Verificando permisos clave:", "info")
            for perm in required_permissions:
                has_perm = low_level.get(perm, False)
                status = "ok" if has_perm else "warning"
                print_step(f"  {perm}: {'✓ Concedido' if has_perm else '✗ Denegado'}", status)
                if not has_perm:
                    all_granted = False

            if all_granted:
                print_step("fmanagement puede validar permisos correctamente", "ok")
            else:
                print_step(
                    "Algunos permisos están denegados (esto puede ser normal según el rol)",
                    "warning",
                )
            return True
        else:
            print_step(
                f"fmanagement no pudo obtener permisos: {response.status_code}", "error"
            )
            return False
    except Exception as e:
        print_step(f"Error en consulta de fmanagement: {e}", "error")
        return False


def test_fmanagement_operation(
    user_id: str,
    identity_type_id: str,
    organization_id: str,
    access_token: str,
    session_token: str,
) -> bool:
    """Prueba una operación de fmanagement con validación de permisos."""
    print_step("Probando operación de fmanagement (readfolder)...", "info")
    try:
        # Simular una operación de lectura de carpeta
        response = requests.get(
            f"{FMANAGEMENT_URL}/fmo/readfolder",
            params={
                "iduser": user_id,
                "identity_type_id": identity_type_id,
                "basepath": "/Users/administrator/data/anewhope/files/backend_server/external",
                "orgpath": f"org_{organization_id}",
                "prjpath": "prj_1",
                "versionpath": "v001",
                "subfolders": "",
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Session-Token": session_token,
            },
            timeout=10,
        )

        if response.status_code == 200:
            print_step("Operación ejecutada correctamente", "ok")
            data = response.json()
            print(f"  • Carpetas: {len(data.get('folders', []))}")
            print(f"  • Archivos: {len(data.get('files', []))}")
            return True
        elif response.status_code == 403:
            print_step("Operación denegada por permisos (403 Forbidden)", "warning")
            print(
                "  Esto es normal si el usuario no tiene permisos folder_read/folder_list"
            )
            return True  # Es un comportamiento esperado
        elif response.status_code == 404:
            print_step("Carpeta no encontrada (404)", "warning")
            print("  Esto es normal si la estructura de carpetas no existe todavía")
            return True  # Es un comportamiento esperado
        else:
            print_step(f"Error inesperado: {response.status_code}", "error")
            print(f"  Respuesta: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print_step("No se puede conectar a fmanagement", "error")
        print(
            "  ¿Está fmanagement corriendo en puerto 1666? Ejecuta: cd /Users/administrator/develop/fmanagement && ./run.sh"
        )
        return False
    except Exception as e:
        print_step(f"Error en operación de fmanagement: {e}", "error")
        return False


def main():
    """Ejecuta todas las verificaciones."""
    print("\n" + "=" * 70)
    print("VERIFICACIÓN DEL FLUJO DE PERMISOS")
    print("Backend Core ← → fmanagement")
    print("=" * 70 + "\n")

    # Paso 1: Verificar que los servicios estén corriendo
    print("▶ PASO 1: Verificar servicios\n")
    backend_ok = check_service_health("Backend Core", BACKEND_CORE_URL)
    fmanagement_ok = check_service_health("fmanagement", FMANAGEMENT_URL)

    if not backend_ok:
        print_step("\n❌ Backend Core no está corriendo. Inicia el servicio primero.", "error")
        print("   Comando: cd src/apps/3_backend && python main.py")
        sys.exit(1)

    if not fmanagement_ok:
        print_step("\n⚠ fmanagement no está corriendo (opcional para esta prueba)", "warning")
        print("   Comando: cd /Users/administrator/develop/fmanagement && ./run.sh")

    # Paso 2: Hacer login y obtener tokens
    print("\n▶ PASO 2: Autenticación\n")
    tokens = test_login()
    if not tokens:
        print_step("\n❌ No se pudo hacer login. Verifica las credenciales.", "error")
        sys.exit(1)

    # Paso 3: Probar endpoint de permisos
    print("\n▶ PASO 3: Consultar permisos al Backend Core\n")
    permissions = test_permissions_endpoint(
        tokens["identity_type_id"], tokens["access_token"], tokens["session_token"]
    )
    if not permissions:
        print_step("\n❌ No se pudieron obtener permisos.", "error")
        sys.exit(1)

    # Paso 4: Simular consulta de fmanagement
    print("\n▶ PASO 4: Simular consulta de fmanagement\n")
    fmanagement_query_ok = test_fmanagement_permission_query(
        tokens["identity_type_id"], tokens["access_token"], tokens["session_token"]
    )

    # Paso 5: Probar operación completa (solo si fmanagement está corriendo)
    if fmanagement_ok:
        print("\n▶ PASO 5: Probar operación de fmanagement\n")
        operation_ok = test_fmanagement_operation(
            tokens["user_id"],
            tokens["identity_type_id"],
            tokens["organization_id"],
            tokens["access_token"],
            tokens["session_token"],
        )
    else:
        operation_ok = True  # Skip if fmanagement is not running

    # Resumen final
    print("\n" + "=" * 70)
    print("RESUMEN DE VERIFICACIÓN")
    print("=" * 70 + "\n")

    results = [
        ("Backend Core corriendo", backend_ok),
        ("fmanagement corriendo", fmanagement_ok),
        ("Login exitoso", tokens is not None),
        ("Permisos obtenidos", permissions is not None),
        ("Consulta de fmanagement simulada", fmanagement_query_ok),
    ]

    if fmanagement_ok:
        results.append(("Operación de fmanagement", operation_ok))

    for test_name, result in results:
        status = "ok" if result else "error"
        print_step(f"{test_name}: {'✓' if result else '✗'}", status)

    all_ok = all(result for _, result in results)

    if all_ok:
        print_step("\n✅ TODAS LAS VERIFICACIONES PASARON", "ok")
        print(
            "\nEl flujo de permisos está configurado correctamente y funcionando."
        )
        print("Frontend/Backoffice → Backend Core → fmanagement")
        return 0
    else:
        print_step("\n⚠ ALGUNAS VERIFICACIONES FALLARON", "warning")
        print("\nRevisa los errores anteriores para diagnosticar el problema.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
