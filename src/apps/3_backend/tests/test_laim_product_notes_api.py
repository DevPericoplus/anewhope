"""Tests de "Notas del parche" en el backend core (apicore.py).

Fase 3 de la cadena laimweb -> middleware -> broker -> backend_core: este
nivel solo necesita servir el fichero <version>.md ya escrito en el
filesystem compartido con fmanagement (igual que download_laim_product, pero
sin dimensión de plataforma/tipo de artefacto/plugin). Ver AGENTS.md
§ "Página Parches y Notas del parche".
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


def _load_module(module_name: str, module_path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar el módulo {module_name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_apicore() -> Any:
    module_path = Path(__file__).resolve().parents[1] / "apicore.py"
    return _load_module("apicore_notes", module_path)


def test_download_laim_product_notes_serves_existing_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LAIM_PRODUCT_STORAGE", str(tmp_path))
    apicore = _load_apicore()

    notes_dir = tmp_path / "community_edition" / "patches" / "notes"
    notes_dir.mkdir(parents=True)
    (notes_dir / "2.0.1.md").write_text("## 2.0.1\n\nContenido de prueba.\n", encoding="utf-8")

    client = TestClient(apicore.app)
    response = client.get(
        "/product/notes/download", params={"edition": "community_edition", "version": "2.0.1"}
    )

    assert response.status_code == 200
    assert response.text == "## 2.0.1\n\nContenido de prueba.\n"
    assert response.headers["content-type"] == "text/markdown; charset=utf-8"


def test_download_laim_product_notes_unknown_version_404s(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LAIM_PRODUCT_STORAGE", str(tmp_path))
    apicore = _load_apicore()

    client = TestClient(apicore.app)
    response = client.get(
        "/product/notes/download", params={"edition": "community_edition", "version": "9.9.9"}
    )

    assert response.status_code == 404


def test_download_laim_product_notes_rejects_invalid_edition(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LAIM_PRODUCT_STORAGE", str(tmp_path))
    apicore = _load_apicore()

    client = TestClient(apicore.app)
    response = client.get(
        "/product/notes/download", params={"edition": "../../etc", "version": "2.0.1"}
    )

    assert response.status_code == 400


def test_download_laim_product_notes_rejects_path_traversal_in_version(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("LAIM_PRODUCT_STORAGE", str(tmp_path))
    apicore = _load_apicore()

    # Plant a sensitive file just outside the edition root to prove it stays unreachable.
    secret = tmp_path / "secret.md"
    secret.write_text("should never be served", encoding="utf-8")

    client = TestClient(apicore.app)
    response = client.get(
        "/product/notes/download",
        params={"edition": "community_edition", "version": "../../secret"},
    )

    assert response.status_code == 400
