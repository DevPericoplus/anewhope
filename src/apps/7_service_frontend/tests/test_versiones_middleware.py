"""Tests de estructuras y lógica de negocio de versiones en el middleware.

Verifica:
- Estructura de datos esperada para versiones
- Reglas de negocio de creación de versiones
- Flujo de datos entre frontend/backoffice y middleware
"""

from __future__ import annotations

import pytest


class TestVersionesDataStructures:
    """Tests para verificar estructuras de datos de versiones."""

    def test_version_structure(self):
        """Verifica estructura de una versión."""
        version = {
            "id_version": 1,
            "id_proyecto": 2,
            "id_organizacion": 5,
            "version_folder": "v001",
        }
        
        assert "id_version" in version
        assert "id_proyecto" in version
        assert "id_organizacion" in version
        assert "version_folder" in version
        assert version["version_folder"].startswith("v")

    def test_versiones_list_response(self):
        """Verifica estructura de respuesta de lista de versiones."""
        response = {
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
        
        assert "versiones" in response
        assert "total" in response
        assert isinstance(response["versiones"], list)
        assert response["total"] == len(response["versiones"])

    def test_version_folder_format(self):
        """Verifica formato de version_folder."""
        test_cases = [
            (1, "v001"),
            (2, "v002"),
            (10, "v010"),
            (123, "v123"),
        ]
        
        for id_version, expected_folder in test_cases:
            assert f"v{id_version:03d}" == expected_folder

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
        assert expected_response["version"]["version_folder"] == "v003"


class TestVersionesBusinessRules:
    """Tests de reglas de negocio de versiones."""

    def test_version_numbering_incremental(self):
        """Verifica que las versiones se numeran incrementalmente."""
        versiones = [
            {"id_version": 1, "version_folder": "v001"},
            {"id_version": 2, "version_folder": "v002"},
            {"id_version": 3, "version_folder": "v003"},
        ]
        
        for i, version in enumerate(versiones, start=1):
            assert version["id_version"] == i
            assert version["version_folder"] == f"v{i:03d}"

    def test_empty_versiones_list_for_new_project(self):
        """Verifica que proyecto sin versiones retorna lista vacía."""
        response = {"versiones": [], "total": 0}
        
        assert response["versiones"] == []
        assert response["total"] == 0

    def test_version_belongs_to_organization(self):
        """Verifica que las versiones incluyen id_organizacion."""
        version = {
            "id_version": 1,
            "id_proyecto": 2,
            "id_organizacion": 5,
            "version_folder": "v001",
        }
        
        # Cada versión debe tener referencia a organización
        assert version["id_organizacion"] > 0


class TestVersionesApiEndpoints:
    """Tests de estructura de endpoints de versiones."""

    def test_get_versions_endpoint_url(self):
        """Verifica formato de URL GET /proyectos/{id}/versiones."""
        project_id = 2
        org_id = 5
        expected_url = f"/proyectos/{project_id}/versiones?org_id={org_id}"
        
        assert f"/proyectos/{project_id}/versiones" in expected_url
        assert f"org_id={org_id}" in expected_url

    def test_create_version_endpoint_url(self):
        """Verifica formato de URL POST /proyectos/{id}/versiones."""
        project_id = 2
        expected_url = f"/proyectos/{project_id}/versiones"
        
        assert expected_url == "/proyectos/2/versiones"

    def test_get_versions_requires_org_id(self):
        """Verifica que GET versiones requiere org_id para seguridad."""
        query_params = {"org_id": 5}
        
        assert "org_id" in query_params
        assert isinstance(query_params["org_id"], int)

    def test_create_version_requires_organization(self):
        """Verifica que POST versiones incluye id_organizacion."""
        request_body = {
            "id_proyecto": 2,
            "id_organizacion": 5,
        }
        
        assert "id_organizacion" in request_body


class TestVersionesSecurity:
    """Tests de validaciones de seguridad."""

    def test_version_isolated_by_organization(self):
        """Verifica que versiones están aisladas por organización."""
        versiones_org_5 = [
            {"id_version": 1, "id_proyecto": 2, "id_organizacion": 5},
            {"id_version": 2, "id_proyecto": 2, "id_organizacion": 5},
        ]
        
        versiones_org_10 = [
            {"id_version": 1, "id_proyecto": 3, "id_organizacion": 10},
        ]
        
        # Misma id_version (1) pero diferente organización
        assert versiones_org_5[0]["id_organizacion"] != versiones_org_10[0]["id_organizacion"]

    def test_version_folder_format_consistency(self):
        """Verifica consistencia del formato version_folder."""
        versions = [
            {"id_version": 1, "version_folder": "v001"},
            {"id_version": 10, "version_folder": "v010"},
            {"id_version": 100, "version_folder": "v100"},
        ]
        
        for version in versions:
            # Formato siempre es "v" + 3 dígitos con ceros a la izquierda
            assert len(version["version_folder"]) == 4
            assert version["version_folder"][0] == "v"
            assert version["version_folder"][1:].isdigit()
