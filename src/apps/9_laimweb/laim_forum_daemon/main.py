"""Punto de entrada del daemon del foro LAIM.

Expone la misma API REST que Backend Core (`/laim/forum/*`) como servicio
independiente en el host/puerto configurados en env.yaml, para que LAIM Web
pueda arrancarlo junto al portal (patrón Radikal).
"""

from __future__ import annotations

import argparse
import importlib.util
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

_env_settings_path = ROOT_DIR / "src/2_shared_application/config/env_settings.py"
_spec = importlib.util.spec_from_file_location(
    "env_settings_laim_forum_daemon", _env_settings_path
)
if _spec is None or _spec.loader is None:
    raise ImportError("No se pudo cargar env_settings")
_env_settings = importlib.util.module_from_spec(_spec)
sys.modules["env_settings_laim_forum_daemon"] = _env_settings
_spec.loader.exec_module(_env_settings)

get_env_value = _env_settings.get_env_value

_router_path = ROOT_DIR / "src/apps/3_backend/router_laim_forum.py"
_router_spec = importlib.util.spec_from_file_location(
    "router_laim_forum_daemon", _router_path
)
if _router_spec is None or _router_spec.loader is None:
    raise ImportError("No se pudo cargar router_laim_forum")
_router_module = importlib.util.module_from_spec(_router_spec)
sys.modules["router_laim_forum_daemon"] = _router_module
_router_spec.loader.exec_module(_router_module)

_logger = logging.getLogger("laim_forum_daemon")


def create_app() -> FastAPI:
    """Construye la aplicación FastAPI del foro."""
    app = FastAPI(title="LAIM Forum API", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(_router_module.router)

    @app.get("/")
    def root() -> dict[str, str]:
        return {"service": "laim_forum", "status": "ok"}

    return app


def _attach_file_handler_to_runtime_loggers(logs_dir: Path, level: int) -> None:
    """Añade FileHandler a root y uvicorn para persistir console.log en el host."""
    log_file = logs_dir / "console.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    for name in ("", "uvicorn", "uvicorn.error", "uvicorn.access", "laim_forum_daemon"):
        logger = logging.getLogger(name)
        already = any(
            isinstance(handler, RotatingFileHandler)
            and getattr(handler, "baseFilename", "") == str(log_file)
            for handler in logger.handlers
        )
        if already:
            continue
        logger.addHandler(file_handler)
        if name:
            logger.setLevel(level)


def _uvicorn_log_config(logs_dir: Path) -> dict[str, object]:
    """Configura uvicorn para persistir en console.log además de stdout."""
    log_file = str((logs_dir / "console.log").resolve())
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "default",
                "filename": log_file,
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 5,
                "encoding": "utf-8",
            },
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["file", "console"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["file", "console"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["file", "console"],
                "level": "INFO",
                "propagate": False,
            },
        },
        "root": {"handlers": ["file", "console"], "level": "INFO"},
    }


def main() -> None:
    """Arranca el servidor uvicorn."""
    parser = argparse.ArgumentParser(description="Daemon del foro LAIM Web")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logs_override = os.environ.get("ANEWHOPE_LOGS_DIR", "").strip()
    logs_dir = Path(logs_override) if logs_override else Path(__file__).resolve().parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    console_logger_path = ROOT_DIR / "src/2_shared_application/console_logger.py"
    console_spec = importlib.util.spec_from_file_location(
        "console_logger_laim_forum", console_logger_path
    )
    if console_spec is not None and console_spec.loader is not None:
        console_module = importlib.util.module_from_spec(console_spec)
        console_spec.loader.exec_module(console_module)
        console_module.create_console_logger(
            "laim_forum", logs_dir, log_level=level
        )
    else:
        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(levelname)s | laim_forum_daemon | %(message)s",
        )

    _attach_file_handler_to_runtime_loggers(logs_dir, level)

    host = str(get_env_value("laim_forum_api_host", "127.0.0.1"))
    port = int(get_env_value("laim_forum_api_port", "8766"))
    app = create_app()
    _logger.info("API Foro LAIM en http://%s:%s", host, port)
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        log_config=_uvicorn_log_config(logs_dir),
    )


if __name__ == "__main__":
    main()
