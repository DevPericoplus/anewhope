"""Tests de almacenamiento de imágenes del foro LAIM."""

from __future__ import annotations

import base64
import importlib.util
import sys
from pathlib import Path


def _load_image_storage():
    module_path = (
        Path(__file__).resolve().parents[3]
        / "2_shared_application/adapters/laim_forum_image_storage.py"
    )
    spec = importlib.util.spec_from_file_location("laim_forum_image_storage_test", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["laim_forum_image_storage_test"] = module
    spec.loader.exec_module(module)
    return module


def test_save_and_read_post_attachment(tmp_path) -> None:
    module = _load_image_storage()
    storage = module.LaimForumImageStorage(base_path=tmp_path)

    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    encoded = base64.b64encode(png_bytes).decode("ascii")

    stored, error = storage.save_image(
        image_kind="post_attachment",
        file_name="captura.png",
        mime_type="image/png",
        data_base64=encoded,
        uploaded_by_user_id=5,
    )

    assert error is None
    assert stored is not None
    assert stored.file_size == len(png_bytes)
    assert stored.storage_key.startswith("attachments/")
    assert stored.absolute_path.is_file()

    read_back = storage.read_image_bytes(stored.storage_key)
    assert read_back == png_bytes


def test_rejects_invalid_mime_type(tmp_path) -> None:
    module = _load_image_storage()
    storage = module.LaimForumImageStorage(base_path=tmp_path)

    _, error = storage.save_image(
        image_kind="post_attachment",
        file_name="doc.pdf",
        mime_type="application/pdf",
        data_base64=base64.b64encode(b"pdf").decode("ascii"),
    )

    assert error is not None
    assert "Formato" in error


def test_path_traversal_blocked(tmp_path) -> None:
    module = _load_image_storage()
    storage = module.LaimForumImageStorage(base_path=tmp_path)

    try:
        storage.resolve_absolute_path("../../etc/passwd")
        raised = False
    except ValueError:
        raised = True

    assert raised is True
