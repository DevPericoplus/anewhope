#!/usr/bin/env python3
"""
Script para parchar la configuración de Vite con hosts permitidos.
Esto es necesario porque Reflex regenera vite.config.js y no incluye
la configuración de allowedHosts por defecto.

Este script se ejecuta automáticamente después de `reflex init` o puede
ejecutarse manualmente cuando sea necesario.

Uso:
    python patch_vite_config.py
"""
import re
from pathlib import Path


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
    
    # Patrón para encontrar la sección server: { ... }
    # Buscamos "server: {" seguido de contenido hasta encontrar "port:"
    pattern = r'(server:\s*\{[^}]*?port:\s*process\.env\.PORT,)'
    
    # Reemplazo: añadimos allowedHosts después de port
    replacement = r'''\1
    allowedHosts: ['tfmmyllm.ai', '.tfmmyllm.ai', 'localhost'],'''
    
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    if new_content == content:
        # Intento alternativo: buscar solo "hmr: true," dentro de server
        pattern_alt = r'(server:\s*\{[^}]*?hmr:\s*true,)'
        replacement_alt = r'''\1
    allowedHosts: ['tfmmyllm.ai', '.tfmmyllm.ai', 'localhost'],'''
        new_content = re.sub(pattern_alt, replacement_alt, content, flags=re.DOTALL)
    
    if new_content == content:
        print("[WARN] No se pudo encontrar el patrón para parchar. Revisión manual necesaria.")
        print("[INFO] Añade manualmente a la sección 'server' en vite.config.js:")
        print("       allowedHosts: ['tfmmyllm.ai', '.tfmmyllm.ai', 'localhost'],")
        return False
    
    # Escribir el contenido modificado
    vite_config_path.write_text(new_content)
    print("[OK] vite.config.js parcheado exitosamente con allowedHosts")
    return True


if __name__ == "__main__":
    success = patch_vite_config()
    exit(0 if success else 1)
