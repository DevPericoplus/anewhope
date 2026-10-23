"""Versión del portal LAIM Web leída de versions.yml (clave version_laimweb).

Se carga con el mismo version_reader compartido que web_frontend y
web_backoffice, para que la interfaz nunca muestre una versión escrita a mano.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_version_reader_path = Path(__file__).resolve().parents[3] / "2_shared_application" / "utils" / "version_reader.py"
_version_spec = importlib.util.spec_from_file_location("version_reader", _version_reader_path)
_version_module = importlib.util.module_from_spec(_version_spec)
_version_spec.loader.exec_module(_version_module)
get_version = _version_module.get_version

APP_VERSION = get_version("laimweb")
APP_VERSION_LABEL = f"LAIM Web v{APP_VERSION}"
