#!/usr/bin/env python3
"""
Script para verificar la sincronización de rutas de almacenamiento
entre Backend Core, fmanagement y el sistema de archivos.

Uso:
    python verify_storage_paths.py
"""

import os
import sys
from pathlib import Path

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


def expand_path(path_str: str) -> Path:
    """Expande ~ y variables de entorno en una ruta."""
    return Path(os.path.expanduser(os.path.expandvars(path_str)))


def verify_backend_core_config():
    """Verifica la configuración de Backend Core."""
    print_step("Verificando configuración de Backend Core...", "info")

    env_yaml_path = Path(__file__).parent.parent / "infrastructure" / "environments" / "macbook" / "env.yaml"

    if not env_yaml_path.exists():
        print_step(f"env.yaml no encontrado en {env_yaml_path}", "error")
        return None

    # Leer YAML manualmente (simple key: value)
    config = {}
    with open(env_yaml_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and ":" in line:
                key, value = line.split(":", 1)
                config[key.strip()] = value.strip()

    fmanagement_base_path = config.get("fmanagement_base_path")
    backend_core_base_storage = config.get("backend_core_base_storage")
    backend_ia_base_storage = config.get("backend_ia_base_storage")

    print(f"  • fmanagement_base_path: {fmanagement_base_path}")
    print(f"  • backend_core_base_storage: {backend_core_base_storage}")
    print(f"  • backend_ia_base_storage: {backend_ia_base_storage}")

    if not fmanagement_base_path:
        print_step("⚠ fmanagement_base_path no configurado en env.yaml", "warning")
        print_step("  Backend Core usará fallback: /data/external", "warning")
        fmanagement_base_path = "/data/external"

    return {
        "fmanagement_base_path": fmanagement_base_path,
        "backend_core_base_storage": backend_core_base_storage,
        "backend_ia_base_storage": backend_ia_base_storage,
    }


def verify_fmanagement_config():
    """Verifica la configuración de fmanagement."""
    print_step("\nVerificando configuración de fmanagement...", "info")

    fmanagement_env = Path.home() / "develop" / "fmanagement" / "env" / "macbook" / ".env"

    if not fmanagement_env.exists():
        print_step(f"fmanagement .env no encontrado en {fmanagement_env}", "error")
        return None

    config = {}
    with open(fmanagement_env) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()

    basepath = config.get("BASEPATH")
    backend_core_storage = config.get("BACKEND_CORE_BASE_STORAGE")
    backend_ia_storage = config.get("BACKEND_IA_BASE_STORAGE")
    permissions_source = config.get("PERMISSIONS_SOURCE")

    print(f"  • BASEPATH: {basepath}")
    print(f"  • BACKEND_CORE_BASE_STORAGE: {backend_core_storage}")
    print(f"  • BACKEND_IA_BASE_STORAGE: {backend_ia_storage}")
    print(f"  • PERMISSIONS_SOURCE: {permissions_source}")

    return {
        "basepath": basepath,
        "backend_core_storage": backend_core_storage,
        "backend_ia_storage": backend_ia_storage,
        "permissions_source": permissions_source,
    }


def verify_filesystem():
    """Verifica el sistema de archivos."""
    print_step("\nVerificando sistema de archivos...", "info")

    paths_to_check = [
        "~/data/anewhope/files/backend_server/external",
        "~/data/anewhope/files/trainer_server/external",
        "/data/external",
        "/data/internal",
    ]

    results = {}
    for path_str in paths_to_check:
        path = expand_path(path_str)
        exists = path.exists()
        status = "ok" if exists else "warning"
        symbol = "✓" if exists else "✗"

        results[path_str] = exists

        if exists:
            # Contar organizaciones/proyectos
            try:
                orgs = [d for d in path.iterdir() if d.is_dir() and d.name.startswith("ORG")]
                print(f"  {symbol} {path_str} → {path}")
                print(f"      Organizaciones: {len(orgs)}")
                for org in orgs[:3]:  # Mostrar máximo 3
                    projects = [d for d in org.iterdir() if d.is_dir() and d.name.startswith("PRJ")]
                    print(f"        • {org.name}/ ({len(projects)} proyectos)")
                    for project in projects[:2]:  # Mostrar máximo 2
                        versions = [d for d in project.iterdir() if d.is_dir() and d.name.startswith("v")]
                        print(f"            • {project.name}/ ({len(versions)} versiones)")
            except Exception as e:
                print(f"  {symbol} {path_str} → {path} (error: {e})")
        else:
            print_step(f"  {path_str} → NO EXISTE", "warning")

    return results


def check_path_consistency(backend_config, fmanagement_config, filesystem_results):
    """Verifica la consistencia entre configuraciones."""
    print_step("\n" + "="*70, "info")
    print_step("VERIFICACIÓN DE CONSISTENCIA", "info")
    print_step("="*70, "info")

    # Expandir rutas
    backend_fmo_path = expand_path(backend_config["fmanagement_base_path"])
    fmanagement_basepath = expand_path(fmanagement_config["basepath"]) if fmanagement_config["basepath"] else None

    print(f"\n1. Backend Core espera que fmanagement use:")
    print(f"   {backend_fmo_path}")

    print(f"\n2. fmanagement está configurado para usar:")
    print(f"   {fmanagement_basepath}")

    if backend_fmo_path == fmanagement_basepath:
        print_step("\n✅ Las rutas coinciden correctamente", "ok")
    else:
        print_step("\n❌ Las rutas NO coinciden - esto causará errores", "error")
        print_step("   Backend Core y fmanagement deben usar la misma ruta base", "error")

    # Verificar que la ruta existe
    print(f"\n3. Verificar que la ruta existe en el filesystem:")
    if fmanagement_basepath and fmanagement_basepath.exists():
        print_step(f"   ✓ {fmanagement_basepath} existe", "ok")
    else:
        print_step(f"   ✗ {fmanagement_basepath} NO existe", "error")
        print_step("   Las carpetas de proyectos no se podrán crear", "error")


def main():
    """Ejecuta todas las verificaciones."""
    print("\n" + "=" * 70)
    print("VERIFICACIÓN DE RUTAS DE ALMACENAMIENTO")
    print("Backend Core ↔ fmanagement ↔ Filesystem")
    print("=" * 70 + "\n")

    # Verificar configuraciones
    backend_config = verify_backend_core_config()
    fmanagement_config = verify_fmanagement_config()

    if not backend_config or not fmanagement_config:
        print_step("\n❌ No se pudieron leer las configuraciones", "error")
        return 1

    # Verificar filesystem
    filesystem_results = verify_filesystem()

    # Verificar consistencia
    check_path_consistency(backend_config, fmanagement_config, filesystem_results)

    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70 + "\n")

    # Expandir rutas para comparación
    backend_path = expand_path(backend_config["fmanagement_base_path"])
    fmanagement_path = expand_path(fmanagement_config["basepath"]) if fmanagement_config["basepath"] else None

    all_ok = (
        backend_path == fmanagement_path
        and fmanagement_path and fmanagement_path.exists()
        and fmanagement_config.get("permissions_source") == "db_only"
    )

    if all_ok:
        print_step("✅ TODAS LAS VERIFICACIONES PASARON", "ok")
        print("\nLas rutas están correctamente configuradas y sincronizadas.")
        return 0
    else:
        print_step("⚠ ALGUNAS VERIFICACIONES FALLARON", "warning")
        print("\nRevisa los errores anteriores para corregir la configuración.")

        print("\n" + "=" * 70)
        print("ACCIONES RECOMENDADAS")
        print("=" * 70 + "\n")

        if backend_path != fmanagement_path:
            print("1. Sincronizar rutas en:")
            print(f"   • infrastructure/environments/macbook/env.yaml")
            print(f"   • fmanagement/env/macbook/.env")
            print(f"\n   Usar la misma ruta base: {fmanagement_path}")

        if not (fmanagement_path and fmanagement_path.exists()):
            print("\n2. Crear el directorio de almacenamiento:")
            print(f"   mkdir -p {fmanagement_path}")

        if fmanagement_config.get("permissions_source") != "db_only":
            print("\n3. Configurar fmanagement para modo db_only:")
            print("   Editar fmanagement/env/macbook/.env")
            print("   PERMISSIONS_SOURCE=db_only")

        return 1


if __name__ == "__main__":
    sys.exit(main())
