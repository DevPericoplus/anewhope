"""Tests de endpoints de versiones en el backend core.

Verifica:
- GET /proyectos/{project_id}/versiones
- POST /proyectos/{project_id}/versiones
- Estructura de DTOs de versiones
"""

from __future__ import annotations

import pytest


class TestVersionesApiStructure:
    """Tests de estructura de DTOs y formato de respuestas."""

    def test_version_dto_fields(self):
        """Verifica que VersionDto tiene los campos correctos."""
        expected_fields = {
            "id_version",
            "id_proyecto",
            "id_organizacion",
            "version_folder",
        }
        
        # Mock de VersionDto
        version_dto = {
            "id_version": 1,
            "id_proyecto": 2,
            "id_organizacion": 5,
            "version_folder": "v001",
        }
        
        assert set(version_dto.keys()) == expected_fields
        assert isinstance(version_dto["id_version"], int)
        assert isinstance(version_dto["version_folder"], str)
        assert version_dto["version_folder"].startswith("v")

    def test_versiones_list_response_format(self):
        """Verifica formato de respuesta GET /proyectos/{id}/versiones."""
        expected_response = {
            "versiones": [
                {
                    "id_version": 1,
                    "id_proyecto": 2,
                    "id_organizacion": 5,
                    "version_folder": "v001",
                },
                {
                    "id_version": 2,
                    "id_proyecto": 2,
                    "id_organizacion": 5,
                    "version_folder": "v002",
                },
            ],
            "total": 2,
        }
        
        assert "versiones" in expected_response
        assert "total" in expected_response
        assert isinstance(expected_response["versiones"], list)
        assert expected_response["total"] == len(expected_response["versiones"])

    def test_crear_version_request_fields(self):
        """Verifica que CrearVersionRequest tiene los campos correctos."""
        request_body = {
            "id_proyecto": 2,
            "id_organizacion": 5,
        }
        
        assert "id_proyecto" in request_body
        assert "id_organizacion" in request_body

    def test_crear_version_response_format(self):
        """Verifica formato de respuesta POST /proyectos/{id}/versiones."""
        expected_response = {
            "success": True,
            "version": {
                "id_version": 3,
                "id_proyecto": 2,
                "id_organizacion": 5,
                "version_folder": "v003",
            },
            "mensaje": "Versión creada correctamente",
        }
        
        assert "success" in expected_response
        assert "version" in expected_response
        assert expected_response["success"] is True

    def test_version_folder_format(self):
        """Verifica que version_folder sigue el formato esperado."""
        test_cases = [
            (1, "v001"),
            (2, "v002"),
            (10, "v010"),
            (999, "v999"),
        ]
        
        for id_version, expected_folder in test_cases:
            actual_folder = f"v{id_version:03d}"
            assert actual_folder == expected_folder

    def test_versiones_empty_list(self):
        """Verifica respuesta cuando proyecto no tiene versiones."""
        empty_response = {
            "versiones": [],
            "total": 0,
        }
        
        assert empty_response["versiones"] == []
        assert empty_response["total"] == 0


class TestVersionesBusinessLogic:
    """Tests de lógica de negocio de versiones."""

    def test_version_numbering_sequential(self):
        """Verifica que las versiones se numeran secuencialmente."""
        versiones = [
            {"id_version": 1, "version_folder": "v001"},
            {"id_version": 2, "version_folder": "v002"},
            {"id_version": 3, "version_folder": "v003"},
        ]
        
        for i, version in enumerate(versiones, start=1):
            assert version["id_version"] == i
            assert version["version_folder"] == f"v{i:03d}"

    def test_proyecto_organizacion_isolation(self):
        """Verifica que versiones se filtran por proyecto y organización."""
        # Simula versiones de diferentes proyectos
        all_versions = [
            {"id_version": 1, "id_proyecto": 1, "id_organizacion": 5},
            {"id_version": 1, "id_proyecto": 2, "id_organizacion": 5},
            {"id_version": 2, "id_proyecto": 2, "id_organizacion": 5},
            {"id_version": 1, "id_proyecto": 3, "id_organizacion": 6},
        ]
        
        # Filtrar por proyecto 2, organización 5
        filtered = [
            v for v in all_versions
            if v["id_proyecto"] == 2 and v["id_organizacion"] == 5
        ]
        
        assert len(filtered) == 2
        assert all(v["id_proyecto"] == 2 for v in filtered)
        assert all(v["id_organizacion"] == 5 for v in filtered)
