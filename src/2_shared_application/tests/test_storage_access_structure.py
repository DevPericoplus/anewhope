"""Tests para helpers de estructura de almacenamiento."""

from __future__ import annotations

from src.2_shared_application.storage_access_structure import (
    get_folder_by_id_organization,
    get_folder_by_id_project,
)


def test_get_folder_by_id_organization() -> None:
    """Valida formato ORG con relleno de ceros."""

    assert get_folder_by_id_organization(1) == "ORG0001"
    assert get_folder_by_id_organization(25) == "ORG0025"
    assert get_folder_by_id_organization(1234) == "ORG1234"


def test_get_folder_by_id_project() -> None:
    """Valida formato PRJ con relleno de ceros."""

    assert get_folder_by_id_project(1) == "PRJ0001"
    assert get_folder_by_id_project(7) == "PRJ0007"
    assert get_folder_by_id_project(9999) == "PRJ9999"
