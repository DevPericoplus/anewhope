#!/usr/bin/env python3
"""
Script para verificar que todos los entornos virtuales tengan instalados
los módulos necesarios según los requirements.txt de cada aplicación.
"""
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Mapeo de entornos virtuales a aplicaciones
VENV_APP_MAPPING = {
    ".venv_backend313": "3_backend",
    ".venv_trainer312": "4_trainer",
    ".venv_frontend313": "5_web_frontend",
    ".venv_backoffice313": "6_web_backoffice",
    ".venv_middleware313": "7_service_frontend",
    ".venv_broker313": "8_service_backend",
}

def parse_requirements(requirements_file: Path) -> List[str]:
    """
    Parse requirements.txt y extrae los nombres de paquetes.
    Ignora comentarios y líneas vacías.
    """
    if not requirements_file.exists():
        return []

    packages = []
    with open(requirements_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Ignorar comentarios y líneas vacías
            if not line or line.startswith("#"):
                continue
            # Extraer solo el nombre del paquete (antes de ==, >=, etc.)
            package_name = line.split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0].strip()
            if package_name:
                packages.append(package_name)

    return packages


def get_installed_packages(venv_path: Path) -> Dict[str, str]:
    """
    Obtiene la lista de paquetes instalados en un entorno virtual.
    Retorna un diccionario {package_name: version}
    """
    pip_executable = venv_path / "bin" / "pip"
    if not pip_executable.exists():
        return {}

    try:
        result = subprocess.run(
            [str(pip_executable), "freeze"],
            capture_output=True,
            text=True,
            check=True,
        )

        installed = {}
        for line in result.stdout.splitlines():
            if "==" in line:
                package, version = line.split("==", 1)
                # Normalizar nombre del paquete (pip normaliza _ a -)
                installed[package.lower().replace("_", "-")] = version

        return installed
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Error al ejecutar pip freeze: {e}")
        return {}


def normalize_package_name(name: str) -> str:
    """
    Normaliza el nombre del paquete para comparación.
    pip normaliza guiones bajos a guiones y todo a minúsculas.
    """
    return name.lower().replace("_", "-")


def verify_venv(project_root: Path, venv_name: str, app_name: str) -> Tuple[bool, List[str]]:
    """
    Verifica si un entorno virtual tiene todos los módulos requeridos.
    Retorna (todo_ok, lista_de_faltantes)
    """
    venv_path = project_root / venv_name
    app_path = project_root / "src" / "apps" / app_name
    requirements_file = app_path / "requirements.txt"

    print(f"\n{'='*70}")
    print(f"🔍 Verificando: {venv_name} ← {app_name}")
    print(f"{'='*70}")

    # Verificar que el venv existe
    if not venv_path.exists():
        print(f"❌ ERROR: Entorno virtual no encontrado: {venv_path}")
        return False, []

    # Verificar que el requirements.txt existe
    if not requirements_file.exists():
        print(f"⚠️  WARNING: requirements.txt no encontrado: {requirements_file}")
        return True, []

    # Parsear requirements
    required_packages = parse_requirements(requirements_file)
    print(f"📦 Paquetes requeridos: {len(required_packages)}")

    # Obtener paquetes instalados
    installed_packages = get_installed_packages(venv_path)
    print(f"✅ Paquetes instalados: {len(installed_packages)}")

    # Verificar cada paquete requerido
    missing_packages = []
    for package in required_packages:
        normalized_package = normalize_package_name(package)
        if normalized_package not in installed_packages:
            missing_packages.append(package)

    if missing_packages:
        print(f"\n❌ FALTAN {len(missing_packages)} PAQUETES:")
        for pkg in missing_packages:
            print(f"   - {pkg}")
        return False, missing_packages
    else:
        print(f"\n✅ TODOS LOS PAQUETES ESTÁN INSTALADOS")
        return True, []


def main():
    project_root = Path(__file__).parent

    print("="*70)
    print("VERIFICACIÓN DE ENTORNOS VIRTUALES Y DEPENDENCIAS")
    print("="*70)
    print(f"Proyecto: {project_root}")
    print(f"Entornos a verificar: {len(VENV_APP_MAPPING)}")

    all_ok = True
    summary = []

    for venv_name, app_name in VENV_APP_MAPPING.items():
        venv_ok, missing = verify_venv(project_root, venv_name, app_name)
        summary.append({
            "venv": venv_name,
            "app": app_name,
            "ok": venv_ok,
            "missing": missing,
        })
        if not venv_ok:
            all_ok = False

    # Resumen final
    print("\n" + "="*70)
    print("RESUMEN FINAL")
    print("="*70)

    for item in summary:
        status = "✅" if item["ok"] else "❌"
        print(f"{status} {item['venv']:25} ← {item['app']:20} ", end="")
        if not item["ok"] and item["missing"]:
            print(f"(Faltan: {len(item['missing'])} paquetes)")
        else:
            print()

    print("="*70)

    if all_ok:
        print("✅ TODOS LOS ENTORNOS VIRTUALES ESTÁN CORRECTOS")
        return 0
    else:
        print("❌ HAY ENTORNOS VIRTUALES CON PAQUETES FALTANTES")
        print("\nPara instalar los paquetes faltantes, ejecuta:")
        print()
        for item in summary:
            if not item["ok"] and item["missing"]:
                venv_path = project_root / item["venv"]
                app_path = project_root / "src" / "apps" / item["app"]
                print(f"  source {venv_path}/bin/activate")
                print(f"  pip install -r {app_path}/requirements.txt")
                print(f"  deactivate")
                print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
