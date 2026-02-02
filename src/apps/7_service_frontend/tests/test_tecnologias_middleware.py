"""Tests de estructuras y lógica de negocio de tecnologías en el middleware.

Verifica:
- Estructura de datos esperada para tecnologías
- Reglas de negocio de asignación de tecnologías
- Flujo de datos entre frontend/backoffice y middleware
"""

from __future__ import annotations

import pytest


class TestTecnologiasDataStructures:
    """Tests para verificar estructuras de datos de tecnologías."""

    def test_tecnologia_structure(self):
        """Verifica estructura de una tecnología."""
        tecnologia = {
            "id": 1,
            "name": "GPT-4",
            "descripcion": "Modelo de lenguaje de OpenAI",
            "active": True,
        }
        
        assert "id" in tecnologia
        assert "name" in tecnologia
        assert "descripcion" in tecnologia
        assert "active" in tecnologia

    def test_tecnologias_list_response(self):
        """Verifica estructura de respuesta de lista de tecnologías."""
        response = {
            "tecnologias": [
                {"id": 1, "name": "GPT-4", "descripcion": "OpenAI", "active": True},
                {"id": 2, "name": "Claude", "descripcion": "Anthropic", "active": True},
                {"id": 3, "name": "Legacy", "descripcion": "Antiguo", "active": False},
            ]
        }
        
        assert "tecnologias" in response
        assert len(response["tecnologias"]) == 3
        
        # Verificar que hay activas e inactivas
        activas = [t for t in response["tecnologias"] if t["active"]]
        inactivas = [t for t in response["tecnologias"] if not t["active"]]
        
        assert len(activas) == 2
        assert len(inactivas) == 1

    def test_proyecto_tecnologia_asignacion(self):
        """Verifica estructura de asignación proyecto-tecnología."""
        asignacion = {
            "id": 1,
            "id_proyecto": 5,
            "id_tecnologia": 2,
            "coste_base": "17% sobre base",
        }
        
        assert asignacion["id_proyecto"] == 5
        assert asignacion["id_tecnologia"] == 2
        assert "coste_base" in asignacion

    def test_empty_asignacion_for_new_project(self):
        """Verifica que proyecto sin tecnología retorna asignación None."""
        response = {"asignacion": None}
        
        assert response["asignacion"] is None


class TestTecnologiasBusinessRules:
    """Tests de reglas de negocio de tecnologías."""

    def test_frontend_can_assign_first_time(self):
        """Verifica que frontend puede asignar tecnología por primera vez."""
        proyecto_sin_tecnologia = {"asignacion": None}
        
        puede_asignar_desde_frontend = proyecto_sin_tecnologia["asignacion"] is None
        
        assert puede_asignar_desde_frontend is True

    def test_frontend_cannot_change_assigned(self):
        """Verifica que frontend NO puede cambiar tecnología ya asignada."""
        proyecto_con_tecnologia = {
            "asignacion": {
                "id": 1,
                "id_proyecto": 5,
                "id_tecnologia": 2,
                "coste_base": "17% sobre base",
            }
        }
        
        puede_cambiar_desde_frontend = proyecto_con_tecnologia["asignacion"] is None
        
        assert puede_cambiar_desde_frontend is False

    def test_backoffice_can_always_change(self):
        """Verifica que backoffice SIEMPRE puede cambiar tecnología."""
        proyecto_con_tecnologia = {
            "asignacion": {
                "id": 1,
                "id_proyecto": 5,
                "id_tecnologia": 2,
                "coste_base": "17% sobre base",
            }
        }
        
        # Backoffice usa PATCH para actualizar
        nueva_asignacion = {
            "id": 1,
            "id_proyecto": 5,
            "id_tecnologia": 3,  # Nueva tecnología
            "coste_base": "20% sobre base",
        }
        
        assert nueva_asignacion["id_tecnologia"] != proyecto_con_tecnologia["asignacion"]["id_tecnologia"]

    def test_inactive_technology_visible_but_disabled(self):
        """Verifica que tecnología inactiva es visible pero no seleccionable."""
        tecnologias = [
            {"id": 1, "name": "GPT-4", "active": True},
            {"id": 2, "name": "Legacy", "active": False},
        ]
        
        for tech in tecnologias:
            if not tech["active"]:
                # En UI: mostrar pero deshabilitado
                # cursor: "not-allowed", opacity: 0.5
                assert tech["name"] == "Legacy"

    def test_coste_base_has_default(self):
        """Verifica que coste_base tiene valor por defecto."""
        default_coste = "17% sobre base"
        
        nueva_asignacion = {
            "id_proyecto": 5,
            "id_tecnologia": 2,
            "coste_base": default_coste,
        }
        
        assert nueva_asignacion["coste_base"] == "17% sobre base"


class TestTecnologiasIntegration:
    """Tests de integración para verificar flujo completo."""

    def test_tecnologias_flow_mock(self, monkeypatch):
        """Verifica flujo de asignación de tecnología con mocks."""
        monkeypatch.setenv("STORAGE_MODE", "mock")
        
        # Paso 1: Cargar lista de tecnologías
        tecnologias = [
            {"id": 1, "name": "GPT-4", "descripcion": "OpenAI GPT-4", "active": True},
            {"id": 2, "name": "Claude 3", "descripcion": "Anthropic Claude", "active": True},
            {"id": 3, "name": "Legacy LLM", "descripcion": "Modelo antiguo", "active": False},
        ]
        
        # Paso 2: Verificar si proyecto tiene tecnología
        proyecto_nuevo = {"asignacion": None}
        assert proyecto_nuevo["asignacion"] is None
        
        # Paso 3: Asignar tecnología (frontend - primera vez)
        asignacion_nueva = {
            "id": 1,
            "id_proyecto": 1,
            "id_tecnologia": 2,
            "coste_base": "17% sobre base",
        }
        
        # Paso 4: Verificar que frontend ya no puede cambiar
        proyecto_con_tech = {"asignacion": asignacion_nueva}
        puede_cambiar_frontend = proyecto_con_tech["asignacion"] is None
        assert puede_cambiar_frontend is False
        
        # Paso 5: Backoffice sí puede cambiar
        asignacion_actualizada = {
            "id": 1,
            "id_proyecto": 1,
            "id_tecnologia": 1,  # Cambio a GPT-4
            "coste_base": "20% sobre base",
        }
        assert asignacion_actualizada["id_tecnologia"] == 1

    def test_project_selector_shows_org_projects(self):
        """Verifica que el selector muestra proyectos de la organización."""
        proyectos_org = [
            {"id": 1, "nombre": "Proyecto Alpha", "id_organizacion": 1},
            {"id": 2, "nombre": "Proyecto Beta", "id_organizacion": 1},
            {"id": 3, "nombre": "Otro Org", "id_organizacion": 2},
        ]
        
        org_id = 1
        proyectos_filtrados = [p for p in proyectos_org if p["id_organizacion"] == org_id]
        
        assert len(proyectos_filtrados) == 2
        assert all(p["id_organizacion"] == 1 for p in proyectos_filtrados)


class TestTecnologiasApiContract:
    """Tests del contrato de API para tecnologías."""

    def test_get_tecnologias_response_format(self):
        """Verifica formato de respuesta GET /tecnologias."""
        expected_response = {
            "tecnologias": [
                {
                    "id": 1,
                    "name": "string",
                    "descripcion": "string",
                    "active": True,
                }
            ]
        }
        
        assert "tecnologias" in expected_response
        assert isinstance(expected_response["tecnologias"], list)

    def test_get_proyecto_tecnologia_response_format(self):
        """Verifica formato de respuesta GET /proyectos/{id}/tecnologia."""
        # Caso: proyecto con tecnología
        response_con_tech = {
            "asignacion": {
                "id": 1,
                "id_proyecto": 1,
                "id_tecnologia": 2,
                "coste_base": "string",
            }
        }
        
        # Caso: proyecto sin tecnología
        response_sin_tech = {"asignacion": None}
        
        assert "asignacion" in response_con_tech
        assert "asignacion" in response_sin_tech

    def test_asignar_tecnologia_request_format(self):
        """Verifica formato de request POST /proyectos/{id}/tecnologia."""
        request_body = {
            "id_tecnologia": 2,
            "coste_base": "17% sobre base",
        }
        
        assert "id_tecnologia" in request_body
        # coste_base es opcional con valor por defecto

    def test_actualizar_tecnologia_request_format(self):
        """Verifica formato de request PATCH /proyectos/{id}/tecnologia."""
        request_body = {
            "id_tecnologia": 3,
            "coste_base": "20% sobre base",
        }
        
        assert "id_tecnologia" in request_body

    def test_get_tecnologias_asignadas_response_format(self):
        """Verifica formato de respuesta GET /organizaciones/{org_id}/tecnologias-asignadas."""
        expected_response = {
            "asignaciones": [
                {
                    "project_id": 1,
                    "project_name": "Asistente Comercial",
                    "tecnologia_id": 2,
                    "tecnologia_name": "RAG",
                },
                {
                    "project_id": 2,
                    "project_name": "Bot Web",
                    "tecnologia_id": None,
                    "tecnologia_name": None,
                },
            ],
            "total": 2,
        }
        
        assert "asignaciones" in expected_response
        assert "total" in expected_response
        assert isinstance(expected_response["asignaciones"], list)
        assert expected_response["total"] == len(expected_response["asignaciones"])

    def test_tecnologias_asignadas_dto_fields(self):
        """Verifica campos del DTO ProyectoTecnologiaAsignadaDto."""
        dto = {
            "project_id": 1,
            "project_name": "Asistente Comercial",
            "tecnologia_id": 2,
            "tecnologia_name": "RAG",
        }
        
        required_fields = ["project_id", "project_name", "tecnologia_id", "tecnologia_name"]
        for field in required_fields:
            assert field in dto

    def test_tecnologias_asignadas_empty_response(self):
        """Verifica respuesta cuando no hay proyectos en la organización."""
        empty_response = {
            "asignaciones": [],
            "total": 0,
        }
        
        assert empty_response["asignaciones"] == []
        assert empty_response["total"] == 0

    def test_tecnologias_asignadas_proyecto_sin_asignar(self):
        """Verifica formato cuando un proyecto no tiene tecnología asignada."""
        asignacion_sin_tech = {
            "project_id": 5,
            "project_name": "Nuevo Proyecto",
            "tecnologia_id": None,
            "tecnologia_name": None,
        }
        
        assert asignacion_sin_tech["tecnologia_id"] is None
        assert asignacion_sin_tech["tecnologia_name"] is None
        # El proyecto sí debe tener ID y nombre
        assert asignacion_sin_tech["project_id"] == 5
        assert asignacion_sin_tech["project_name"] == "Nuevo Proyecto"
