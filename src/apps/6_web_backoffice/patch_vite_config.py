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

# Add src/2_shared_application to path to import env_settings
project_root = Path(__file__).resolve().parents[3]
shared_app_path = project_root / "src" / "2_shared_application"
sys.path.insert(0, str(shared_app_path))

try:
    from config import env_settings
except ImportError:
    print("[ERROR] No se pudo importar env_settings. Verifica la estructura del proyecto.")
    sys.exit(1)


def get_public_domain() -> str:
    """
    Obtiene el dominio público del entorno activo desde env.yaml.

    Returns:
        str: Dominio público (ej: 'tfmmyllm.ai', 'house.loc', 'getmylllm.com')
    """
    try:
        public_name = env_settings.get_env_value("public_name", "localhost")
        return public_name
    except Exception as e:
        print(f"[WARN] Error al leer public_name: {e}")
        print("[INFO] Usando 'localhost' por defecto")
        return "localhost"


def patch_vite_config():
    """
    Parcha el archivo vite.config.js para añadir los hosts permitidos.
    """
    vite_config_path = Path(__file__).parent / ".web" / "vite.config.js"
    
    if not vite_config_path.exists():
        print(f"[INFO] vite.config.js no encontrado en {vite_config_path}")
        print("[INFO] Ejecuta 'reflex init' primero para generar la configuración.")
        return False
    
    # Leer el contenido actual
    content = vite_config_path.read_text()
    
    # Verificar si ya tiene allowedHosts configurado
    if "allowedHosts" in content:
        print("[INFO] allowedHosts ya está configurado en vite.config.js")
        return True

    # Obtener el dominio público del entorno activo
    public_domain = get_public_domain()

    # Construir lista de hosts permitidos
    # Incluimos: el dominio público, subdominio wildcard (.dominio), y localhost
    allowed_hosts = [public_domain, f".{public_domain}", "localhost"]
    allowed_hosts_str = ", ".join([f"'{host}'" for host in allowed_hosts])

    print(f"[INFO] Configurando allowedHosts con: {allowed_hosts_str}")

    # Patrón para encontrar la sección server: { ... }
    # Buscamos "server: {" seguido de contenido hasta encontrar "port:"
    pattern = r'(server:\s*\{[^}]*?port:\s*process\.env\.PORT,)'

    # Reemplazo: añadimos allowedHosts después de port
    replacement = rf'''\1
    allowedHosts: [{allowed_hosts_str}],'''

    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    if new_content == content:
        # Intento alternativo: buscar solo "hmr: true," dentro de server
        pattern_alt = r'(server:\s*\{[^}]*?hmr:\s*true,)'
        replacement_alt = rf'''\1
    allowedHosts: [{allowed_hosts_str}],'''
        new_content = re.sub(pattern_alt, replacement_alt, content, flags=re.DOTALL)
    
    if new_content == content:
        print("[WARN] No se pudo encontrar el patrón para parchar. Revisión manual necesaria.")
        print("[INFO] Añade manualmente a la sección 'server' en vite.config.js:")
        print(f"       allowedHosts: [{allowed_hosts_str}],")
        return False
    
    # Escribir el contenido modificado
    vite_config_path.write_text(new_content)
    print("[OK] vite.config.js parcheado exitosamente con allowedHosts")
    return True


if __name__ == "__main__":
    success = patch_vite_config()
    exit(0 if success else 1)
