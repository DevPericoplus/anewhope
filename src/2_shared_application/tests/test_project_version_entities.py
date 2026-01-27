"""Tests para las entidades Project y Version del dominio."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Agregar rutas al path
_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_root))

# Cargar entidades de dominio usando importlib
import importlib.util


def _load_project_module():
    """Carga el módulo de proyecto."""
    module_name = "test_project_entities"
    module_path = _root / "src/1_shared_domain/entities/project.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module  # Registrar en sys.modules antes de exec
    spec.loader.exec_module(module)
    return module


def _load_version_module():
    """Carga el módulo de versión."""
    module_name = "test_version_entities"
    module_path = _root / "src/1_shared_domain/entities/version.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module  # Registrar en sys.modules antes de exec
    spec.loader.exec_module(module)
    return module


_project = _load_project_module()
_version = _load_version_module()

Project = _project.Project
ProjectStatus = _project.ProjectStatus
Projects = _project.Projects
Version = _version.Version
VersionStatus = _version.VersionStatus
Versions = _version.Versions


class TestProjectEntity:
    """Tests para la entidad Project."""

    def test_create_valid_project(self):
        """Verifica que se puede crear un proyecto válido."""
        project = Project(
            project_id=1,
            organization_id=1,
            project_name="Test Project",
            project_description="A test project",
            created_by_user_id=1,
            status=ProjectStatus.DRAFT,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        assert project.project_id == 1
        assert project.organization_id == 1
        assert project.project_name == "Test Project"
        assert project.status == ProjectStatus.DRAFT

    def test_project_from_dict(self):
        """Verifica la creación desde diccionario."""
        data = {
            "project_id": 2,
            "organization_id": 1,
            "project_name": "Dict Project",
            "created_by_user_id": 1,
            "status": "active",
        }
        project = Project.from_dict(data)
        assert project.project_id == 2
        assert project.status == ProjectStatus.ACTIVE

    def test_project_to_dict(self):
        """Verifica la serialización a diccionario."""
        project = Project(
            project_id=3,
            organization_id=1,
            project_name="Serialize Test",
            project_description="",
            created_by_user_id=1,
            status=ProjectStatus.COMPLETED,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        data = project.to_dict()
        assert data["project_id"] == 3
        assert data["status"] == "completed"

    def test_project_invalid_id(self):
        """Verifica que falla con ID inválido."""
        with pytest.raises(ValueError, match="debe ser positivo"):
            Project(
                project_id=0,
                organization_id=1,
                project_name="Invalid",
                project_description="",
                created_by_user_id=1,
                status=ProjectStatus.DRAFT,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            )

    def test_project_is_active(self):
        """Verifica el método is_active."""
        project_active = Project(
            project_id=1,
            organization_id=1,
            project_name="Active",
            project_description="",
            created_by_user_id=1,
            status=ProjectStatus.ACTIVE,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        project_draft = Project(
            project_id=2,
            organization_id=1,
            project_name="Draft",
            project_description="",
            created_by_user_id=1,
            status=ProjectStatus.DRAFT,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        assert project_active.is_active() is True
        assert project_draft.is_active() is False

    def test_project_can_create_version(self):
        """Verifica el método can_create_version."""
        project = Project(
            project_id=1,
            organization_id=1,
            project_name="Test",
            project_description="",
            created_by_user_id=1,
            status=ProjectStatus.DRAFT,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        assert project.can_create_version() is True
        
        project_archived = Project(
            project_id=2,
            organization_id=1,
            project_name="Archived",
            project_description="",
            created_by_user_id=1,
            status=ProjectStatus.ARCHIVED,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        assert project_archived.can_create_version() is False


class TestProjectsContainer:
    """Tests para el contenedor Projects."""

    def test_projects_filter_by_organization(self):
        """Verifica el filtrado por organización."""
        projects = Projects([
            Project(
                project_id=1, organization_id=1, project_name="P1",
                project_description="", created_by_user_id=1,
                status=ProjectStatus.ACTIVE, created_at="", updated_at=""
            ),
            Project(
                project_id=2, organization_id=2, project_name="P2",
                project_description="", created_by_user_id=1,
                status=ProjectStatus.ACTIVE, created_at="", updated_at=""
            ),
            Project(
                project_id=3, organization_id=1, project_name="P3",
                project_description="", created_by_user_id=1,
                status=ProjectStatus.ACTIVE, created_at="", updated_at=""
            ),
        ])
        
        org1_projects = projects.filter_by_organization(1)
        assert len(org1_projects) == 2
        assert all(p.organization_id == 1 for p in org1_projects)

    def test_projects_get_by_id(self):
        """Verifica la obtención por ID."""
        projects = Projects([
            Project(
                project_id=1, organization_id=1, project_name="P1",
                project_description="", created_by_user_id=1,
                status=ProjectStatus.ACTIVE, created_at="", updated_at=""
            ),
        ])
        
        assert projects.get_by_id(1) is not None
        assert projects.get_by_id(999) is None


class TestVersionEntity:
    """Tests para la entidad Version."""

    def test_create_valid_version(self):
        """Verifica que se puede crear una versión válida."""
        version = Version(
            version_id=1,
            project_id=1,
            version_name="V001",
            version_description="First version",
            status=VersionStatus.DRAFT,
            created_by_user_id=1,
            approved_by_client_user_id=None,
            approved_by_myllm_user_id=None,
            storage_path="/storage/org001/prj001/V001",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        assert version.version_id == 1
        assert version.version_name == "V001"
        assert version.status == VersionStatus.DRAFT

    def test_version_approval_methods(self):
        """Verifica los métodos de aprobación."""
        version = Version(
            version_id=1, project_id=1, version_name="V001",
            version_description="", status=VersionStatus.IN_REVIEW,
            created_by_user_id=1,
            approved_by_client_user_id=None,
            approved_by_myllm_user_id=None,
            storage_path="", created_at="", updated_at=""
        )
        assert version.is_approved_by_client() is False
        assert version.is_approved_by_myllm() is False
        
        version_approved = Version(
            version_id=2, project_id=1, version_name="V002",
            version_description="", status=VersionStatus.READY_FOR_TRAINING,
            created_by_user_id=1,
            approved_by_client_user_id=10,
            approved_by_myllm_user_id=5,
            storage_path="", created_at="", updated_at=""
        )
        assert version_approved.is_approved_by_client() is True
        assert version_approved.is_approved_by_myllm() is True

    def test_version_can_start_training(self):
        """Verifica el método can_start_training."""
        version_ready = Version(
            version_id=1, project_id=1, version_name="V001",
            version_description="", status=VersionStatus.READY_FOR_TRAINING,
            created_by_user_id=1,
            approved_by_client_user_id=10,
            approved_by_myllm_user_id=5,
            storage_path="", created_at="", updated_at=""
        )
        assert version_ready.can_start_training() is True
        
        version_not_ready = Version(
            version_id=2, project_id=1, version_name="V002",
            version_description="", status=VersionStatus.DRAFT,
            created_by_user_id=1,
            approved_by_client_user_id=None,
            approved_by_myllm_user_id=None,
            storage_path="", created_at="", updated_at=""
        )
        assert version_not_ready.can_start_training() is False

    def test_version_can_be_modified(self):
        """Verifica el método can_be_modified."""
        version_draft = Version(
            version_id=1, project_id=1, version_name="V001",
            version_description="", status=VersionStatus.DRAFT,
            created_by_user_id=1,
            approved_by_client_user_id=None,
            approved_by_myllm_user_id=None,
            storage_path="", created_at="", updated_at=""
        )
        assert version_draft.can_be_modified() is True
        
        version_trained = Version(
            version_id=2, project_id=1, version_name="V002",
            version_description="", status=VersionStatus.TRAINED,
            created_by_user_id=1,
            approved_by_client_user_id=10,
            approved_by_myllm_user_id=5,
            storage_path="", created_at="", updated_at=""
        )
        assert version_trained.can_be_modified() is False


class TestVersionsContainer:
    """Tests para el contenedor Versions."""

    def test_versions_filter_by_project(self):
        """Verifica el filtrado por proyecto."""
        versions = Versions([
            Version(
                version_id=1, project_id=1, version_name="V001",
                version_description="", status=VersionStatus.DRAFT,
                created_by_user_id=1, approved_by_client_user_id=None,
                approved_by_myllm_user_id=None, storage_path="",
                created_at="", updated_at=""
            ),
            Version(
                version_id=2, project_id=2, version_name="V001",
                version_description="", status=VersionStatus.DRAFT,
                created_by_user_id=1, approved_by_client_user_id=None,
                approved_by_myllm_user_id=None, storage_path="",
                created_at="", updated_at=""
            ),
            Version(
                version_id=3, project_id=1, version_name="V002",
                version_description="", status=VersionStatus.DRAFT,
                created_by_user_id=1, approved_by_client_user_id=None,
                approved_by_myllm_user_id=None, storage_path="",
                created_at="", updated_at=""
            ),
        ])
        
        prj1_versions = versions.filter_by_project(1)
        assert len(prj1_versions) == 2

    def test_versions_get_latest_by_project(self):
        """Verifica la obtención de la versión más reciente."""
        versions = Versions([
            Version(
                version_id=1, project_id=1, version_name="V001",
                version_description="", status=VersionStatus.DRAFT,
                created_by_user_id=1, approved_by_client_user_id=None,
                approved_by_myllm_user_id=None, storage_path="",
                created_at="", updated_at=""
            ),
            Version(
                version_id=3, project_id=1, version_name="V002",
                version_description="", status=VersionStatus.DRAFT,
                created_by_user_id=1, approved_by_client_user_id=None,
                approved_by_myllm_user_id=None, storage_path="",
                created_at="", updated_at=""
            ),
        ])
        
        latest = versions.get_latest_by_project(1)
        assert latest is not None
        assert latest.version_id == 3
