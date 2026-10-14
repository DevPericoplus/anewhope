#!/usr/bin/env python3
"""
Script para parchar la configuración de Vite con hosts permitidos.
Esto es necesario porque Reflex regenera vite.config.js y no incluye
la configuración de allowedHosts por defecto.

Este script lee el dominio público desde el archivo env.yaml del entorno
activo y configura automáticamente los hosts permitidos.

Uso:
    python patch_vite_config.py
"""
import re
import sys
from pathlib import Path

from laim_web.dynamic_import import load_module_from_path

# Add src/apps/9_laimweb to path for dynamic_import
project_root = Path(__file__).resolve().parents[3]
laimweb_root = Path(__file__).resolve().parent
sys.path.insert(0, str(laimweb_root))

try:
    env_settings_path = project_root / "src" / "2_shared_application" / "config" / "env_settings.py"
    env_settings = load_module_from_path(env_settings_path, "env_settings_patch_vite")
except ImportError:
    print("[ERROR] No se pudo importar env_settings. Verifica la estructura del proyecto.")
    sys.exit(1)


def get_public_domain() -> str:
    """
    Obtiene el dominio público LAIM del entorno activo desde env.yaml.
    Usa laim_public_name si existe, si no usa public_name como fallback.

    Returns:
        str: Dominio público (ej: 'laim.app')
    """
    try:
        public_name = env_settings.get_env_value("laim_public_name", "")
        if not public_name:
            public_name = env_settings.get_env_value("public_name", "localhost")
        return public_name
    except Exception as e:
        print(f"[WARN] Error al leer laim_public_name: {e}")
        print("[INFO] Usando 'laim.app' por defecto")
        return "laim.app"


# Chrome 141+: sin esto, un script (Cap/WebRTC) dispara
# «acceder a apps y servicios de este dispositivo» en www.laim.app.
_LNA_POLICY = (
    "local-network=(), loopback-network=(), local-network-access=()"
)
_LNA_HEADER_LINE = (
    f'    headers: {{ "Permissions-Policy": "{_LNA_POLICY}" }},'
)


def _ensure_allowed_hosts(content: str) -> str:
    """Añade allowedHosts si Reflex acaba de regenerar vite.config.js."""
    if "allowedHosts" in content:
        return content
    public_domain = get_public_domain()
    allowed_hosts = [public_domain, f".{public_domain}", "localhost"]
    allowed_hosts_str = ", ".join([f"'{host}'" for host in allowed_hosts])
    print(f"[INFO] Configurando allowedHosts con: {allowed_hosts_str}")
    pattern = r"(server:\s*\{[^}]*?port:\s*process\.env\.PORT,)"
    replacement = rf"""\1
    allowedHosts: [{allowed_hosts_str}],"""
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    if new_content == content:
        pattern_alt = r"(server:\s*\{[^}]*?hmr:\s*true,)"
        replacement_alt = rf"""\1
    allowedHosts: [{allowed_hosts_str}],"""
        new_content = re.sub(pattern_alt, replacement_alt, content, flags=re.DOTALL)
    return new_content


def _ensure_lna_header(content: str) -> str:
    """Niega LAN/loopback en el HTML que sirve Vite (sin prompt de Chrome)."""
    if "Permissions-Policy" in content:
        return content
    needle = "port: process.env.PORT,"
    if needle not in content:
        return content
    return content.replace(needle, needle + "\n" + _LNA_HEADER_LINE, 1)


def patch_vite_config():
    """Parcha vite.config.js: hosts permitidos y Permissions-Policy LNA."""
    vite_config_path = Path(__file__).parent / ".web" / "vite.config.js"

    if not vite_config_path.exists():
        print(f"[INFO] vite.config.js no encontrado en {vite_config_path}")
        print("[INFO] Ejecuta 'reflex init' primero para generar la configuración.")
        return False

    content = vite_config_path.read_text()
    new_content = _ensure_lna_header(_ensure_allowed_hosts(content))

    if new_content == content:
        if "allowedHosts" in content and "Permissions-Policy" in content:
            print("[INFO] vite.config.js ya tiene allowedHosts y Permissions-Policy")
            return True
        print("[WARN] No se pudo encontrar el patrón para parchar. Revisión manual necesaria.")
        return False

    vite_config_path.write_text(new_content)
    print("[OK] vite.config.js parcheado (allowedHosts / Permissions-Policy)")
    return True


if __name__ == "__main__":
    success = patch_vite_config()
    exit(0 if success else 1)
