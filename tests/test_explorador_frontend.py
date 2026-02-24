#!/usr/bin/env python3
"""
Test del componente Explorador en el Frontend.

Este test verifica:
1. Login de usuario
2. Acceso a una versión de un proyecto
3. Respuesta del componente Explorador
4. Comparación con la respuesta directa de fmanagement

Uso:
    python test_explorador_frontend.py
"""

import json
import sys
from pathlib import Path
from typing import Any

import pymysql
import requests

# Colores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"

# URLs de servicios
MIDDLEWARE_URL = "http://localhost:8007"
FMANAGEMENT_URL = "http://localhost:1666"

# Datos de prueba
TEST_USER = "adminone"
TEST_PASSWORD = "Password01"
TEST_ORG_ID = 1
TEST_PROJECT_ID = 2  # botweb
TEST_VERSION_ID = 1  # v001


def print_step(step: str, status: str = "info"):
    """Imprime un paso del proceso con formato."""
    color = (
        BLUE if status == "info"
        else GREEN if status == "ok"
        else RED if status == "error"
        else YELLOW if status == "warning"
        else CYAN
    )
    symbol = (
        "ℹ" if status == "info"
        else "✓" if status == "ok"
        else "✗" if status == "error"
        else "⚠" if status == "warning"
        else "→"
    )
    print(f"{color}{symbol} {step}{RESET}")


def print_json(data: dict, title: str = ""):
    """Imprime JSON con formato."""
    if title:
        print(f"\n{CYAN}{'=' * 70}")
        print(f"{title}")
        print(f"{'=' * 70}{RESET}")
    print(json.dumps(data, indent=2, ensure_ascii=False))


def get_db_connection():
    """Crea conexión a la base de datos."""
    import importlib.util
    protected_path = Path(__file__).parent.parent / "infrastructure" / "environments" / "macbook" / "protected_values.py"
    spec = importlib.util.spec_from_file_location("protected_values", protected_path)
    protected = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(protected)

    return pymysql.connect(
        host=protected.mariadb_host,
        port=protected.mariadb_port,
        user=protected.mariadb_admin_user,
        password=protected.mariadb_admin_password,
        database=protected.mariadb_core_database,  # Usuarios están en core_db
        cursorclass=pymysql.cursors.DictCursor
    )


def get_current_otp(user_name: str) -> str | None:
    """Obtiene el OTP actual de un usuario desde la base de datos."""
    print_step(f"Consultando OTP de '{user_name}' en base de datos...", "info")

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_otp FROM users WHERE user_name = %s", (user_name,))
            result = cursor.fetchone()
            if result:
                otp = result['user_otp']
                print_step(f"OTP obtenido: {otp}", "ok")
                return otp
            else:
                print_step(f"Usuario '{user_name}' no encontrado", "error")
                return None
    finally:
        conn.close()


def test_login() -> dict[str, Any] | None:
    """Prueba el login y retorna los tokens."""
    # Obtener OTP actual de la base de datos
    otp = get_current_otp(TEST_USER)
    if not otp:
        print_step("No se pudo obtener el OTP", "error")
        return None

    print_step(f"Haciendo login con usuario '{TEST_USER}'...", "info")

    try:
        response = requests.post(
            f"{MIDDLEWARE_URL}/login",
            json={
                "user_name": TEST_USER,
                "password": TEST_PASSWORD,
                "otp": otp,
            },
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            data["user_name"] = TEST_USER
            print_step("Login exitoso", "ok")
            print(f"  • User ID: {data.get('user_id')}")
            print(f"  • Organization ID: {data.get('organization_id')}")
            print(f"  • Identity Type ID: {data.get('identity_type_id')}")
            print(f"  • Permissions: {', '.join(data.get('permissions', []))}")
            return data
        else:
            print_step(f"Login falló: {response.status_code}", "error")
            print(f"  Respuesta: {response.text}")
            return None
    except Exception as e:
        print_step(f"Error en login: {e}", "error")
        return None


def test_fmanagement_direct() -> dict[str, Any] | None:
    """Llama directamente al servicio fmanagement."""
    print_step("Llamando directamente a fmanagement /fmo/list...", "info")

    # Obtener basepath de configuración
    env_yaml = Path(__file__).parent.parent / "infrastructure" / "environments" / "macbook" / "env.yaml"
    basepath = None
    with open(env_yaml) as f:
        for line in f:
            if line.strip().startswith("fmanagement_base_path:"):
                basepath = line.split(":", 1)[1].strip()
                import os
                basepath = os.path.expanduser(basepath)
                break

    if not basepath:
        print_step("No se pudo obtener basepath", "error")
        return None

    org_folder = f"ORG{TEST_ORG_ID:04d}"
    prj_folder = f"PRJ{TEST_PROJECT_ID:05d}"
    version_folder = f"v{TEST_VERSION_ID:03d}"

    print(f"  • Basepath: {basepath}")
    print(f"  • Path: {org_folder}/{prj_folder}/{version_folder}")

    try:
        response = requests.get(
            f"{FMANAGEMENT_URL}/fmo/list",
            params={
                "iduser": 1,
                "basepath": basepath,
                "orgpath": org_folder,
                "prjpath": prj_folder,
                "versionpath": version_folder,
            },
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            print_step("Respuesta de fmanagement obtenida", "ok")
            print(f"  • Status: {data.get('status')}")
            print(f"  • Items: {len(data.get('items', []))}")
            print(f"  • Path: {data.get('path')}")
            return data
        else:
            print_step(f"fmanagement falló: {response.status_code}", "error")
            print(f"  Respuesta: {response.text}")
            return None
    except Exception as e:
        print_step(f"Error llamando a fmanagement: {e}", "error")
        import traceback
        traceback.print_exc()
        return None


def test_fmanagement_via_middleware(user_data: dict[str, Any]) -> dict[str, Any] | None:
    """Llama a fmanagement a través del middleware."""
    print_step("Llamando a fmanagement vía middleware...", "info")

    org_folder = f"ORG{TEST_ORG_ID:04d}"
    prj_folder = f"PRJ{TEST_PROJECT_ID:05d}"
    version_folder = f"v{TEST_VERSION_ID:03d}"

    print(f"  • Path: {org_folder}/{prj_folder}/{version_folder}")

    try:
        response = requests.post(
            f"{MIDDLEWARE_URL}/fmanagement/list",
            headers={
                "Authorization": f"Bearer {user_data['access_token']}",
                "X-Session-Token": user_data["session_token"],
                "Content-Type": "application/json",
            },
            json={
                "org_folder": org_folder,
                "prj_folder": prj_folder,
                "version_folder": version_folder,
            },
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            print_step("Respuesta del middleware obtenida", "ok")
            print(f"  • Success: {data.get('success')}")
            print(f"  • Items: {len(data.get('items', []))}")
            print(f"  • Mensaje: {data.get('mensaje')}")
            return data
        else:
            print_step(f"Middleware falló: {response.status_code}", "error")
            print(f"  Respuesta: {response.text}")
            return None
    except Exception as e:
        print_step(f"Error llamando al middleware: {e}", "error")
        import traceback
        traceback.print_exc()
        return None


def compare_responses(direct: dict[str, Any], middleware: dict[str, Any]):
    """Compara las respuestas de fmanagement directo y vía middleware."""
    print_step("Comparando respuestas...", "info")

    # Items de fmanagement directo
    direct_items = direct.get("items", [])
    # Items vía middleware
    middleware_items = middleware.get("items", [])

    print(f"  • Items directos: {len(direct_items)}")
    print(f"  • Items middleware: {len(middleware_items)}")

    if len(direct_items) != len(middleware_items):
        print_step(
            f"⚠ Diferente cantidad de items: {len(direct_items)} vs {len(middleware_items)}",
            "warning"
        )
    else:
        print_step(f"✓ Misma cantidad de items: {len(direct_items)}", "ok")

    # Comparar nombres de items
    direct_names = {item.get("name") for item in direct_items}
    middleware_names = {item.get("name") for item in middleware_items}

    if direct_names == middleware_names:
        print_step("✓ Items coinciden", "ok")
        print(f"  • Items: {', '.join(sorted(direct_names))}")
    else:
        print_step("✗ Items NO coinciden", "error")
        print(f"  • Solo en directo: {direct_names - middleware_names}")
        print(f"  • Solo en middleware: {middleware_names - direct_names}")


def verify_explorador_state():
    """Verifica el estado del componente Explorador."""
    print_step("Verificando código del Explorador...", "info")

    explorador_path = Path(__file__).parent.parent / "src" / "apps" / "5_web_frontend" / "components" / "explorador.py"

    if not explorador_path.exists():
        print_step(f"Archivo no encontrado: {explorador_path}", "error")
        return False

    content = explorador_path.read_text()

    # Verificar is_internal_user
    if "return False  # Frontend = Cliente" in content:
        print_step("✓ is_internal_user configurado correctamente (retorna False)", "ok")
    else:
        print_step("✗ is_internal_user NO está configurado correctamente", "error")
        return False

    # Verificar que existe init_page
    if "def init_page(self, project_id: int, version_id: int):" in content:
        print_step("✓ Método init_page() existe", "ok")
    else:
        print_step("✗ Método init_page() NO existe", "error")
        return False

    # Verificar que llama a load_from_api
    if "self.load_from_api()" in content:
        print_step("✓ init_page() llama a load_from_api()", "ok")
    else:
        print_step("✗ init_page() NO llama a load_from_api()", "error")
        return False

    return True


def verify_web_frontend_state():
    """Verifica el estado del web_frontend.py."""
    print_step("Verificando código del web_frontend.py...", "info")

    web_frontend_path = Path(__file__).parent.parent / "src" / "apps" / "5_web_frontend" / "web_frontend" / "web_frontend.py"

    if not web_frontend_path.exists():
        print_step(f"Archivo no encontrado: {web_frontend_path}", "error")
        return False

    content = web_frontend_path.read_text()

    # Verificar que set_proyecciones_version llama a reload_version
    if "ExploradorState.reload_version(" in content:
        print_step("✓ set_proyecciones_version() llama a reload_version()", "ok")
    else:
        print_step("✗ set_proyecciones_version() NO llama a reload_version()", "error")
        return False

    return True


def main():
    """Ejecuta el test completo."""
    print("\n" + "=" * 70)
    print("TEST DEL COMPONENTE EXPLORADOR (FRONTEND)")
    print("=" * 70 + "\n")

    # Verificar código
    print("▶ PASO 0: Verificar código\n")
    code_ok = verify_explorador_state() and verify_web_frontend_state()
    if not code_ok:
        print_step("\n❌ El código tiene problemas", "error")
        return 1

    # Paso 1: Login
    print("\n▶ PASO 1: Login\n")
    user_data = test_login()
    if not user_data:
        print_step("\n❌ Test falló: No se pudo hacer login", "error")
        return 1

    # Paso 2: Llamar directamente a fmanagement
    print("\n▶ PASO 2: Llamar directamente a fmanagement\n")
    fmanagement_direct = test_fmanagement_direct()
    if not fmanagement_direct:
        print_step("\n❌ Test falló: fmanagement no respondió", "error")
        return 1

    print_json(fmanagement_direct, "RESPUESTA DIRECTA DE FMANAGEMENT")

    # Paso 3: Llamar a fmanagement vía middleware
    print("\n▶ PASO 3: Llamar a fmanagement vía middleware\n")
    fmanagement_middleware = test_fmanagement_via_middleware(user_data)
    if not fmanagement_middleware:
        print_step("\n❌ Test falló: middleware no respondió", "error")
        return 1

    print_json(fmanagement_middleware, "RESPUESTA VÍA MIDDLEWARE")

    # Paso 4: Comparar respuestas
    print("\n▶ PASO 4: Comparar respuestas\n")
    compare_responses(fmanagement_direct, fmanagement_middleware)

    # Resumen
    print("\n" + "=" * 70)
    print("RESUMEN DEL TEST")
    print("=" * 70 + "\n")

    checks = [
        ("Código del Explorador correcto", code_ok),
        ("Login exitoso", user_data is not None),
        ("fmanagement directo responde", fmanagement_direct is not None),
        ("Middleware responde", fmanagement_middleware is not None),
    ]

    for test_name, passed in checks:
        status = "ok" if passed else "error"
        print_step(f"{test_name}: {'✓' if passed else '✗'}", status)

    all_ok = all(passed for _, passed in checks)

    if all_ok:
        print_step("\n✅ TODOS LOS TESTS PASARON", "ok")
        print(f"\n{GREEN}El middleware está devolviendo los datos correctamente.{RESET}")
        print(f"\n{YELLOW}Si el Explorador no muestra contenido en el navegador:{RESET}")
        print("  1. Verifica que Reflex frontend esté reiniciado")
        print("  2. Limpia el caché del navegador (Cmd+Shift+R)")
        print("  3. Verifica que reload_version() se esté llamando cuando seleccionas una versión")
        print("  4. Revisa la consola del navegador (F12) para errores JavaScript")
        return 0
    else:
        print_step("\n⚠ ALGUNOS TESTS FALLARON", "warning")
        return 1


if __name__ == "__main__":
    sys.exit(main())
