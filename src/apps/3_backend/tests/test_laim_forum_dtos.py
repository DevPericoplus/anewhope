"""Tests de DTOs del foro LAIM."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_forum_dtos():
    module_path = (
        Path(__file__).resolve().parents[3]
        / "2_shared_application/dtos/laim_forum_dtos.py"
    )
    spec = importlib.util.spec_from_file_location("laim_forum_dtos_test", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["laim_forum_dtos_test"] = module
    spec.loader.exec_module(module)
    return module


def test_thread_create_dto_limits_attachments() -> None:
    module = _load_forum_dtos()

    dto = module.LaimForumThreadCreateDto(
        subcategory_id="general",
        titulo="Hilo de prueba",
        cuerpo_md="Contenido del hilo",
        image_ids=[1, 2, 3],
    )
    assert len(dto.image_ids) == 3

    with pytest.raises(Exception):
        module.LaimForumThreadCreateDto(
            subcategory_id="general",
            titulo="Hilo",
            cuerpo_md="Contenido",
            image_ids=[1, 2, 3, 4],
        )


def test_post_rating_dto_range() -> None:
    module = _load_forum_dtos()

    valid = module.LaimForumPostRatingDto(valoracion=5)
    assert valid.valoracion == 5

    with pytest.raises(Exception):
        module.LaimForumPostRatingDto(valoracion=0)
