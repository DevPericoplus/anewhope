"""Alias de importación para carpetas numeradas y helpers de la raíz.

Los directorios ``1_shared_domain``, ``2_shared_application`` y ``3_backend``
no son identificadores Python válidos. El código y los tests históricos usan
``src.shared_application`` y ``src.apps.backend``. Este módulo registra esos
alias en ``sys.modules`` para que pytest y la carga dinámica coincidan.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def get_project_root() -> Path:
    """Raíz del repositorio (padre de tests/)."""
    return Path(__file__).resolve().parent.parent


def _ensure_namespace(name: str, directory: Path) -> None:
    """Crea o reutiliza un paquete namespace en sys.modules."""
    existing = sys.modules.get(name)
    resolved = str(directory)
    if existing is None:
        module = ModuleType(name)
        module.__path__ = [resolved]
        module.__package__ = name
        sys.modules[name] = module
        return
    pkg_path = getattr(existing, "__path__", None)
    if pkg_path is not None and resolved not in list(pkg_path):
        pkg_path.append(resolved)


def _register_package(alias: str, directory: Path) -> None:
    """Registra un paquete alias apuntando a un directorio real."""
    resolved = str(directory)
    existing = sys.modules.get(alias)
    if existing is not None:
        pkg_path = getattr(existing, "__path__", None)
        if pkg_path is not None and resolved in list(pkg_path):
            return
    module = ModuleType(alias)
    module.__path__ = [resolved]
    init_file = directory / "__init__.py"
    module.__file__ = str(init_file) if init_file.exists() else resolved
    module.__package__ = alias
    sys.modules[alias] = module


def register_repo_helpers() -> None:
    """Expone ``tests.helpers`` de la raíz aunque pytest use ``tests/`` de una app."""
    helpers_path = get_project_root() / "tests" / "helpers.py"
    if not helpers_path.is_file():
        return
    if "tests.helpers" in sys.modules and hasattr(sys.modules["tests.helpers"], "get_service_urls"):
        return
    spec = importlib.util.spec_from_file_location("tests.helpers", helpers_path)
    if spec is None or spec.loader is None:
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules["tests.helpers"] = module
    spec.loader.exec_module(module)
    tests_pkg = sys.modules.get("tests")
    if tests_pkg is not None:
        tests_pkg.helpers = module


def register_import_aliases() -> None:
    """Registra alias ``src.shared_*`` y ``src.apps.backend``."""
    root = get_project_root()
    src_dir = root / "src"
    apps_dir = src_dir / "apps"

    _ensure_namespace("src", src_dir)
    _register_package("src.shared_domain", src_dir / "1_shared_domain")
    _register_package("src.shared_application", src_dir / "2_shared_application")
    _ensure_namespace("src.apps", apps_dir)
    _register_package("src.apps.backend", apps_dir / "3_backend")
    _register_package("src.apps.trainer", apps_dir / "4_trainer")
    register_repo_helpers()


def bootstrap_test_imports(repo_root: Path | None = None) -> None:
    """Añade la raíz al ``sys.path`` y registra alias de importación."""
    root = Path(repo_root) if repo_root is not None else get_project_root()
    resolved = str(root.resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)
    register_import_aliases()
