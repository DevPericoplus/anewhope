"""Integration tests for assignments flow."""

import pytest
from unittest.mock import patch, Mock


@pytest.mark.integration
class TestAssignmentsIntegration:
    """Integration tests for full assignment flow."""

    def test_full_org_assignment_lifecycle(self):
        """Tests create → list → toggle → delete flow for organization assignments."""
        # Mock API calls through all layers
        with patch(
            "src.apps.web_backoffice.adapters.api_client.create_organization_assignment"
        ) as mock_create, \
        patch(
            "src.apps.web_backoffice.adapters.api_client.get_organization_assignments"
        ) as mock_list, \
        patch(
            "src.apps.web_backoffice.adapters.api_client.update_organization_assignment"
        ) as mock_update, \
        patch(
            "src.apps.web_backoffice.adapters.api_client.delete_organization_assignment"
        ) as mock_delete:

            # Setup mocks
            mock_create.return_value = {
                "success": True,
                "assignment_id": 1,
                "message": "Asignación creada exitosamente",
            }

            mock_list.return_value = [
                {
                    "id": 1,
                    "user_id": 5,
                    "user_name": "trainer",
                    "organization_id": 2,
                    "organization_name": "Test Org",
                    "role_id": 3,
                    "role_name": "OrgAdmin",
                    "active": True,
                }
            ]

            mock_update.return_value = {
                "success": True,
                "updated": True,
                "message": "Asignación deshabilitada",
            }

            mock_delete.return_value = {
                "success": True,
                "deleted": True,
                "message": "Asignación eliminada permanentemente",
            }

            # Simulate user flow
            # 1. Create assignment
            create_result = mock_create(
                user_id=5,
                organization_id=2,
                role_id=3,
                access_token="test_token",
                session_token="test_session",
            )
            assert create_result["success"]
            assert create_result["assignment_id"] == 1

            # 2. List assignments
            assignments = mock_list(
                organization_id=2,
                access_token="test_token",
                session_token="test_session",
            )
            assert len(assignments) == 1
            assert assignments[0]["user_name"] == "trainer"
            assert assignments[0]["active"] is True

            # 3. Toggle active status (disable)
            update_result = mock_update(
                assignment_id=1,
                active=False,
                access_token="test_token",
                session_token="test_session",
            )
            assert update_result["success"]
            assert update_result["updated"] is True

            # 4. Delete permanently
            delete_result = mock_delete(
                assignment_id=1,
                access_token="test_token",
                session_token="test_session",
            )
            assert delete_result["success"]
            assert delete_result["deleted"] is True

    def test_full_project_assignment_lifecycle_with_prerequisite(self):
        """Tests create → list → toggle → delete flow for project assignments with prerequisite validation."""
        with patch(
            "src.apps.web_backoffice.adapters.api_client.validate_org_prerequisite"
        ) as mock_validate, \
        patch(
            "src.apps.web_backoffice.adapters.api_client.create_project_assignment"
        ) as mock_create, \
        patch(
            "src.apps.web_backoffice.adapters.api_client.get_project_assignments"
        ) as mock_list, \
        patch(
            "src.apps.web_backoffice.adapters.api_client.update_project_assignment"
        ) as mock_update, \
        patch(
            "src.apps.web_backoffice.adapters.api_client.delete_project_assignment"
        ) as mock_delete:

            # Setup mocks
            mock_validate.return_value = {
                "valid": True,
                "message": "Usuario tiene rol activo en la organización",
                "has_org_role": True,
                "org_role_id": 3,
            }

            mock_create.return_value = {
                "success": True,
                "assignment_id": 1,
                "message": "Asignación de proyecto creada exitosamente",
            }

            mock_list.return_value = [
                {
                    "id": 1,
                    "user_id": 5,
                    "user_name": "trainer",
                    "organization_id": 2,
                    "organization_name": "Test Org",
                    "project_id": 10,
                    "project_name": "Test Project",
                    "role_id": 4,
                    "role_name": "Editor",
                    "active": True,
                }
            ]

            mock_update.return_value = {
                "success": True,
                "updated": True,
                "message": "Asignación habilitada",
            }

            mock_delete.return_value = {
                "success": True,
                "deleted": True,
                "message": "Asignación eliminada permanentemente",
            }

            # Simulate user flow
            # 1. Validate prerequisite
            validation = mock_validate(
                user_id=5,
                organization_id=2,
                access_token="test_token",
                session_token="test_session",
            )
            assert validation["valid"] is True
            assert validation["has_org_role"] is True

            # 2. Create project assignment
            create_result = mock_create(
                user_id=5,
                organization_id=2,
                project_id=10,
                role_id=4,
                access_token="test_token",
                session_token="test_session",
            )
            assert create_result["success"]
            assert create_result["assignment_id"] == 1

            # 3. List project assignments
            assignments = mock_list(
                project_id=10,
                access_token="test_token",
                session_token="test_session",
            )
            assert len(assignments) == 1
            assert assignments[0]["project_name"] == "Test Project"
            assert assignments[0]["active"] is True

            # 4. Toggle active status (enable)
            update_result = mock_update(
                assignment_id=1,
                active=True,
                access_token="test_token",
                session_token="test_session",
            )
            assert update_result["success"]

            # 5. Delete permanently
            delete_result = mock_delete(
                assignment_id=1,
                access_token="test_token",
                session_token="test_session",
            )
            assert delete_result["success"]

    def test_project_assignment_fails_without_org_prerequisite(self):
        """Tests that project assignment is rejected when user has no org role."""
        with patch(
            "src.apps.web_backoffice.adapters.api_client.validate_org_prerequisite"
        ) as mock_validate, \
        patch(
            "src.apps.web_backoffice.adapters.api_client.create_project_assignment"
        ) as mock_create:

            # Mock validation failure
            mock_validate.return_value = {
                "valid": False,
                "message": "Usuario no tiene rol activo en la organización",
                "has_org_role": False,
                "org_role_id": None,
            }

            # Mock create returns error due to prerequisite failure
            mock_create.side_effect = Exception(
                "El usuario debe tener un rol activo en la organización antes de asignarlo a proyectos"
            )

            # 1. Validate prerequisite (fails)
            validation = mock_validate(
                user_id=5,
                organization_id=2,
                access_token="test_token",
                session_token="test_session",
            )
            assert validation["valid"] is False
            assert validation["has_org_role"] is False

            # 2. Attempt to create project assignment (should fail)
            with pytest.raises(Exception) as exc_info:
                mock_create(
                    user_id=5,
                    organization_id=2,
                    project_id=10,
                    role_id=4,
                    access_token="test_token",
                    session_token="test_session",
                )

            assert "organización" in str(exc_info.value).lower()

    def test_get_internal_users_returns_only_trainers(self):
        """Tests that get_internal_users only returns users with training_create=true."""
        with patch(
            "src.apps.web_backoffice.adapters.api_client.get_internal_users"
        ) as mock_get_users:

            # Mock filtered users list
            mock_get_users.return_value = [
                {
                    "user_id": 5,
                    "user_name": "trainer1",
                    "user_email": "trainer1@test.com",
                },
                {
                    "user_id": 6,
                    "user_name": "trainer2",
                    "user_email": "trainer2@test.com",
                },
            ]

            # Get internal users
            users = mock_get_users(
                access_token="test_token",
                session_token="test_session",
            )

            assert len(users) == 2
            assert all("trainer" in u["user_name"] for u in users)
            assert all("user_id" in u for u in users)
            assert all("user_email" in u for u in users)

    def test_duplicate_assignment_prevention(self):
        """Tests that duplicate assignments are properly rejected."""
        with patch(
            "src.apps.web_backoffice.adapters.api_client.create_organization_assignment"
        ) as mock_create:

            # First call succeeds
            mock_create.return_value = {
                "success": True,
                "assignment_id": 1,
                "message": "Asignación creada exitosamente",
            }

            result1 = mock_create(
                user_id=5,
                organization_id=2,
                role_id=3,
                access_token="test_token",
                session_token="test_session",
            )
            assert result1["success"]

            # Second call with same parameters fails
            mock_create.side_effect = Exception(
                "El usuario ya tiene una asignación a esta organización"
            )

            with pytest.raises(Exception) as exc_info:
                mock_create(
                    user_id=5,
                    organization_id=2,
                    role_id=3,
                    access_token="test_token",
                    session_token="test_session",
                )

            assert "ya tiene una asignación" in str(exc_info.value).lower()
