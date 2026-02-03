#!/usr/bin/env python3
"""
Script para crear estructuras de carpetas en fmanagement para proyectos con v001.
"""
import sys
import json
import requests
from pathlib import Path

# Agregar rutas necesarias
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

# Cargar env_settings
import importlib.util
env_settings_path = project_root / "src" / "2_shared_application" / "config" / "env_settings.py"
spec = importlib.util.spec_from_file_location("env_settings", env_settings_path)
env_settings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env_settings)

# URL del middleware
MIDDLEWARE_URL = env_settings.get_env_value("MIDDLEWARE_BASE_URL", "http://localhost:8007")

# Proyectos a crear (organización acme)
PROJECTS = [
    {"org": "acme", "project": "dptocomercial"},
    {"org": "acme", "project": "botweb"},
    {"org": "acme", "project": "test"},
    {"org": "acme", "project": "presales"},
    {"org": "acme", "project": "test_updated"},
]

# Estructura base de carpetas
FOLDERS = [
    "datos",
    "modelos",
    "evaluaciones",
    "resultados",
]

# Archivos base
FILES = [
    {
        "path": "README.md",
        "content": "# Proyecto {project}\n\nVersión: v001\n\nProyecto de la organización {org}.\n"
    },
    {
        "path": "datos/datos_entrenamiento.txt",
        "content": "Datos de entrenamiento placeholder\n"
    },
    {
        "path": "modelos/config.json",
        "content": json.dumps({"model": "placeholder", "version": "v001"}, indent=2)
    },
]


def create_folder(org, project, version, folder_name):
    """Crea una carpeta en fmanagement vía middleware."""
    try:
        response = requests.post(
            f"{MIDDLEWARE_URL}/fmanagement/operation",
            json={
                "operation": "create_folder",
                "org": org,
                "prj": project,
                "version": version,
                "folder_name": folder_name,
            },
            timeout=10,
        )
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return True, "OK"
            else:
                return False, result.get("error", "Error desconocido")
        else:
            return False, f"HTTP {response.status_code}: {response.text[:100]}"
    except Exception as e:
        return False, str(e)


def write_file(org, project, version, file_path, content):
    """Escribe un archivo en fmanagement vía middleware."""
    try:
        response = requests.post(
            f"{MIDDLEWARE_URL}/fmanagement/operation",
            json={
                "operation": "write_file",
                "org": org,
                "prj": project,
                "version": version,
                "file_path": file_path,
                "content": content,
            },
            timeout=10,
        )
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return True, "OK"
            else:
                return False, result.get("error", "Error desconocido")
        else:
            return False, f"HTTP {response.status_code}: {response.text[:100]}"
    except Exception as e:
        return False, str(e)


def main():
    print("=" * 80)
    print("CREACIÓN DE ESTRUCTURAS EN FMANAGEMENT PARA v001")
    print("=" * 80)
    print(f"Middleware URL: {MIDDLEWARE_URL}")
    print()

    total_success = 0
    total_errors = 0

    for proj_info in PROJECTS:
        org = proj_info["org"]
        project = proj_info["project"]
        version = "v001"

        print(f"\n{'='*80}")
        print(f"📦 {org}/{project}/{version}")
        print(f"{'='*80}")

        # Crear carpetas
        print("📁 Creando carpetas...")
        for folder in FOLDERS:
            success, msg = create_folder(org, project, version, folder)
            if success:
                print(f"  ✓ {folder}")
                total_success += 1
            else:
                print(f"  ✗ {folder}: {msg}")
                total_errors += 1

        # Crear archivos
        print("\n📄 Creando archivos...")
        for file_info in FILES:
            file_path = file_info["path"]
            content = file_info["content"].format(org=org, project=project)
            success, msg = write_file(org, project, version, file_path, content)
            if success:
                print(f"  ✓ {file_path}")
                total_success += 1
            else:
                print(f"  ✗ {file_path}: {msg}")
                total_errors += 1

    print(f"\n{'='*80}")
    print("RESUMEN FINAL")
    print(f"{'='*80}")
    print(f"✅ Operaciones exitosas: {total_success}")
    print(f"❌ Operaciones fallidas: {total_errors}")
    print(f"📊 Total de operaciones: {total_success + total_errors}")
    print(f"{'='*80}\n")

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
