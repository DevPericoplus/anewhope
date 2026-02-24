"""Unit tests for assignments service methods."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from tests.helpers import load_module_from_path

_routercore = load_module_from_path("routercore", "src/apps/3_backend/routercore.py")
BackendCoreRouter = _routercore.BackendCoreRouter
BackendCorePermissionError = _routercore.BackendCorePermissionError
BackendCoreBusinessError = _routercore.BackendCoreBusinessError


class TestAssignmentsService:
    """Unit tests for assignment operations."""

    @pytest.fixture
    def mock_router(self):
        """Fixture for BackendCoreRouter with mocked dependencies."""
        storage = Mock()
        router = BackendCoreRouter(storage=storage)
        return router

    def test_get_internal_users_returns_filtered_list(self, mock_router):
        """Tests that only users with training_create=true are returned."""
        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_conn = MagicMock()
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn

            mock_conn.execute.return_value = [
                Mock(user_id=5, user_name="trainer1", user_email="t1@test.com"),
                Mock(user_id=6, user_name="trainer2", user_email="t2@test.com"),
            ]

            result = mock_router.get_internal_users()

            assert len(result) == 2
            assert result[0]["user_id"] == 5
            assert result[0]["user_name"] == "trainer1"
            assert result[0]["user_email"] == "t1@test.com"

    def test_create_org_assignment_checks_permission(self, mock_router):
        """Tests that non-SuperAdmin is denied."""
        with pytest.raises(BackendCorePermissionError):
            mock_router.create_organization_assignment(
                user_id=5,
                organization_id=2,
                role_id=3,
                identity_type_id=2,  # Not SuperAdmin
            )

    def test_create_org_assignment_prevents_duplicates(self, mock_router):
        """Tests that duplicate assignments are rejected."""
        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_conn = MagicMock()
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn

            # Mock existing assignment found
            mock_conn.execute.return_value.fetchone.return_value = Mock(id=1)

            with pytest.raises(BackendCoreBusinessError) as exc_info:
                mock_router.create_organization_assignment(
                    user_id=5,
                    organization_id=2,
                    role_id=3,
                    identity_type_id=1,  # SuperAdmin
                )

            assert "ya tiene una asignación" in str(exc_info.value).lower()

    def test_update_org_assignment_checks_permission(self, mock_router):
        """Tests that non-SuperAdmin cannot update assignments."""
        with pytest.raises(BackendCorePermissionError):
            mock_router.update_organization_assignment(
                assignment_id=1,
                active=False,
                identity_type_id=2,  # Not SuperAdmin
            )

    def test_delete_org_assignment_checks_permission(self, mock_router):
        """Tests that non-SuperAdmin cannot delete assignments."""
        with pytest.raises(BackendCorePermissionError):
            mock_router.delete_organization_assignment(
                assignment_id=1,
                identity_type_id=2,  # Not SuperAdmin
            )

    def test_validate_org_prerequisite_returns_true_when_active(self, mock_router):
        """Tests prerequisite validation with active org role."""
        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_conn = MagicMock()
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn

            # Mock active org role found
            mock_conn.execute.return_value.fetchone.return_value = Mock(id=1, id_rol=3)

            result = mock_router.validate_org_prerequisite(
                user_id=5,
                organization_id=2,
            )

            assert result["valid"] is True
            assert result["has_org_role"] is True
            assert result["org_role_id"] == 3

    def test_validate_org_prerequisite_returns_false_when_no_role(self, mock_router):
        """Tests prerequisite validation without org role."""
        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_conn = MagicMock()
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn

            # Mock no org role found
            mock_conn.execute.return_value.fetchone.return_value = None

            result = mock_router.validate_org_prerequisite(
                user_id=5,
                organization_id=2,
            )

            assert result["valid"] is False
            assert result["has_org_role"] is False
            assert result["org_role_id"] is None

    def test_create_project_assignment_validates_prerequisite(self, mock_router):
        """Tests prerequisite validation before project assignment."""
        with patch.object(
            mock_router, "validate_org_prerequisite"
        ) as mock_validate:

            mock_validate.return_value = {
                "valid": False,
                "has_org_role": False,
                "org_role_id": None,
            }

            with pytest.raises(BackendCoreBusinessError) as exc_info:
                mock_router.create_project_assignment(
                    user_id=5,
                    organization_id=2,
                    project_id=10,
                    role_id=4,
                    identity_type_id=1,  # SuperAdmin
                )

            assert "organización" in str(exc_info.value).lower()

    def test_create_project_assignment_prevents_duplicates(self, mock_router):
        """Tests that duplicate project assignments are rejected."""
        with patch.object(
            mock_router, "validate_org_prerequisite"
        ) as mock_validate, \
        patch("sqlalchemy.create_engine") as mock_engine:

            # Mock valid prerequisite
            mock_validate.return_value = {
                "valid": True,
                "has_org_role": True,
                "org_role_id": 3,
            }

            mock_conn = MagicMock()
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn

            # First fetchone: org validation (project belongs to org 2)
            # Second fetchone: existing assignment found (duplicate)
            mock_conn.execute.return_value.fetchone.side_effect = [
                Mock(id_organizacion=2),  # project org check
                Mock(id=1),              # existing assignment found
            ]

            with pytest.raises(BackendCoreBusinessError) as exc_info:
                mock_router.create_project_assignment(
                    user_id=5,
                    organization_id=2,
                    project_id=10,
                    role_id=4,
                    identity_type_id=1,  # SuperAdmin
                )

            assert "ya tiene una asignación" in str(exc_info.value).lower()

    def test_get_organization_assignments_checks_permission(self, mock_router):
        """Tests that non-SuperAdmin cannot list org assignments."""
        with pytest.raises(BackendCorePermissionError):
            mock_router.get_organization_assignments(
                organization_id=2,
                identity_type_id=2,  # Not SuperAdmin
            )

    def test_get_project_assignments_checks_permission(self, mock_router):
        """Tests that non-SuperAdmin cannot list project assignments."""
        with pytest.raises(BackendCorePermissionError):
            mock_router.get_project_assignments(
                project_id=10,
                identity_type_id=2,  # Not SuperAdmin
            )

    def test_update_project_assignment_checks_permission(self, mock_router):
        """Tests that non-SuperAdmin cannot update project assignments."""
        with pytest.raises(BackendCorePermissionError):
            mock_router.update_project_assignment(
                assignment_id=1,
                active=False,
                identity_type_id=2,  # Not SuperAdmin
            )

    def test_delete_project_assignment_checks_permission(self, mock_router):
        """Tests that non-SuperAdmin cannot delete project assignments."""
        with pytest.raises(BackendCorePermissionError):
            mock_router.delete_project_assignment(
                assignment_id=1,
                identity_type_id=2,  # Not SuperAdmin
            )
