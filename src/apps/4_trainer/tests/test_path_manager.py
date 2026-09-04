"""Tests del PathManager de entrenamiento autónomo (ORG vs USER)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_TRAINER_DIR = Path(__file__).resolve().parent.parent
if str(_TRAINER_DIR) not in sys.path:
    sys.path.insert(0, str(_TRAINER_DIR))


@pytest.fixture
def mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aísla el Trainer de MariaDB."""
    monkeypatch.setenv("STORAGE_MODE", "mock")


def test_path_manager_org_folder_from_ids(mock_env: None) -> None:
    """Proyecto de organización usa ORG#####."""
    from autonomous_training.path_manager import PathManager

    manager = PathManager(
        id_organizacion=1,
        id_proyecto=2,
        id_version=3,
        id_entrenamiento=4,
        owner_user_id=9,
    )
    assert manager.org_folder == "ORG00001"
    assert manager.prj_folder == "PRJ00002"
    assert manager.ver_folder == "v003"


def test_path_manager_user_folder_when_no_org(mock_env: None) -> None:
    """Cuenta individual usa USER#####."""
    from autonomous_training.path_manager import PathManager

    manager = PathManager(
        id_organizacion=0,
        id_proyecto=2,
        id_version=3,
        id_entrenamiento=4,
        owner_user_id=9,
    )
    assert manager.org_folder == "USER00009"


def test_path_manager_parses_user_pat_version(mock_env: None) -> None:
    """pat_version con USER##### se respeta."""
    from autonomous_training.path_manager import PathManager

    manager = PathManager(
        id_organizacion=0,
        id_proyecto=2,
        id_version=3,
        id_entrenamiento=4,
        owner_user_id=1,
        pat_version="~/data/external/USER00015/PRJ00002/v003",
    )
    assert manager.org_folder == "USER00015"
    assert manager.prj_folder == "PRJ00002"
    assert manager.ver_folder == "v003"
