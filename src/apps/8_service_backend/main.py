"""Punto de entrada para ejecutar el broker backend."""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import uvicorn


# Asegurar que el path raíz esté disponible
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


APP_NAME = "broker"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5


def _load_console_logger() -> Any:
    """Carga el módulo de console_logger dinámicamente."""
    module_path = ROOT_DIR / "src" / "2_shared_application" / "console_logger.py"
    spec = importlib.util.spec_from_file_location("console_logger", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar console_logger desde {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _setup_unified_logging(logs_dir: Path) -> tuple[logging.Handler, logging.Handler]:
    """Configura logging unificado para consola y archivo."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "console.log"
    
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    return file_handler, console_handler


def _configure_uvicorn_logging(
    file_handler: logging.Handler,
    console_handler: logging.Handler,
) -> dict[str, Any]:
    """Configura los loggers de uvicorn para usar nuestros handlers."""
    
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv_logger = logging.getLogger(logger_name)
        uv_logger.handlers.clear()
        uv_logger.addHandler(file_handler)
        uv_logger.addHandler(console_handler)
        uv_logger.setLevel(logging.INFO)
        uv_logger.propagate = False
    
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {"format": LOG_FORMAT, "datefmt": LOG_DATE_FORMAT},
            "access": {"format": LOG_FORMAT, "datefmt": LOG_DATE_FORMAT},
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"level": "INFO"},
            "uvicorn.access": {"level": "INFO"},
            "uvicorn.error": {"level": "INFO"},
        },
    }


def main() -> None:
    """Inicia el servidor ASGI para el broker backend."""

    logs_dir = Path(__file__).parent / "logs"
    
    file_handler, console_handler = _setup_unified_logging(logs_dir)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    console_logger = _load_console_logger()
    logger = console_logger.create_console_logger(APP_NAME, logs_dir)
    
    log_config = _configure_uvicorn_logging(file_handler, console_handler)

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
        log_config=log_config,
    )


if __name__ == "__main__":
    main()
