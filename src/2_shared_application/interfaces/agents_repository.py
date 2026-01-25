"""Contrato de acceso a agentes para la capa de aplicación."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.1_shared_domain.entities.agents import AgentRoleSpec


class AgentsRepository(Protocol):
    """Contrato para gestionar agentes automáticos."""

    def list_agents_by_org_project(
        self, organization_id: int, project_name: str
    ) -> list[dict[str, object]]:
        """Lista agentes por organización y proyecto."""

    def save_agents(
        self, organization_id: int, project_name: str, agents: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        """Persiste agentes y retorna los registros guardados."""

    def list_agent_roles(self) -> tuple[AgentRoleSpec, ...]:
        """Retorna los roles de agentes disponibles."""
