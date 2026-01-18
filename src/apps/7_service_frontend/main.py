"""Punto de entrada para ejecutar el servicio frontend de forma independiente."""

from __future__ import annotations

import logging
import os

import uvicorn


def main() -> None:
    """Inicia el servidor ASGI para el servicio frontend."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    host = os.environ.get("SERVICE_HOST", "0.0.0.0")
    port = int(os.environ.get("SERVICE_PORT", "8002"))
    reload_enabled = os.environ.get("SERVICE_RELOAD", "false").lower() == "true"

    uvicorn.run(
        "src.apps.7_service_frontend.middlewarefe:app",
        host=host,
        port=port,
        reload=reload_enabled,
    )


if __name__ == "__main__":
    main()
