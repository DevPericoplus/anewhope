"""Punto de entrada para ejecutar el broker backend."""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Any

import uvicorn


# Asegurar que el path raíz esté disponible
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _load_console_logger() -> Any:
    """Carga el módulo de console_logger dinámicamente."""
    module_path = ROOT_DIR / "src" / "2_shared_application" / "console_logger.py"
    spec = importlib.util.spec_from_file_location("console_logger", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar console_logger desde {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    """Inicia el servidor ASGI para el broker backend."""

    # Configurar logging de consola unificado
    console_logger = _load_console_logger()
    logs_dir = Path(__file__).parent / "logs"
    logger = console_logger.create_console_logger("broker", logs_dir)

    # Configurar logging básico para uvicorn y librerías
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    host = os.environ.get("SERVICE_HOST", "0.0.0.0")
    port = int(os.environ.get("SERVICE_PORT", "8008"))
    reload_enabled = os.environ.get("SERVICE_RELOAD", "false").lower() == "true"

    logger.startup(host=host, port=port)
    logger.config("SERVICE_HOST", host)
    logger.config("SERVICE_PORT", str(port))
    logger.config("SERVICE_RELOAD", str(reload_enabled))

    uvicorn.run(
        "src.apps.8_service_backend.brokerbe:app",
        host=host,
        port=port,
        reload=reload_enabled,
    )


if __name__ == "__main__":
    main()
