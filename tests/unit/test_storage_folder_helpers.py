"""Helpers de carpetas de storage en tests E2E."""

from tests.helpers import get_org_folder, get_prj_folder, get_ver_folder


def test_org_folder_uses_five_digits() -> None:
    """ORG#####, no ORG####."""
    assert get_org_folder(1) == "ORG00001"
    assert get_org_folder(25) == "ORG00025"


def test_project_and_version_folders() -> None:
    """PRJ##### y v###."""
    assert get_prj_folder(2) == "PRJ00002"
    assert get_ver_folder(17) == "v017"
