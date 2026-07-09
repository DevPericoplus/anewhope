"""Punto de entrada del daemon del foro LAIM.

Expone la misma API REST que Backend Core (`/laim/forum/*`) como servicio
independiente en el host/puerto configurados en env.yaml, para que LAIM Web
pueda arrancarlo junto al portal (patrón Radikal).
"""

from __future__ import annotations

import argparse
import importlib.util
import logging
import sys
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


def main() -> None:
    """Arranca el servidor uvicorn."""
    parser = argparse.ArgumentParser(description="Daemon del foro LAIM Web")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | laim_forum_daemon | %(message)s",
    )

    host = str(get_env_value("laim_forum_api_host", "127.0.0.1"))
    port = int(get_env_value("laim_forum_api_port", "8766"))
    app = create_app()
    _logger.info("API Foro LAIM en http://%s:%s", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
