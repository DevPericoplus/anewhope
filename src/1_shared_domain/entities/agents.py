"""Entidades y utilidades de dominio para agentes automáticos."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentRoleSpec:
    """Define el rol y el identity_type_id asociado."""

    identity_type_id: int
    role_slug: str


AGENT_ROLE_SPECS: tuple[AgentRoleSpec, ...] = (
    AgentRoleSpec(identity_type_id=10, role_slug="administrador"),
    AgentRoleSpec(identity_type_id=11, role_slug="editor"),
    AgentRoleSpec(identity_type_id=12, role_slug="lector"),
    AgentRoleSpec(identity_type_id=13, role_slug="auditor"),
)


def build_agent_username(
    role_slug: str, organization_name: str, project_name: str
) -> str:
    """Construye el nombre de usuario del agente."""

    return (
        f"agente_{_normalize_slug(role_slug)}_"
        f"{_normalize_slug(organization_name)}_"
        f"{_normalize_slug(project_name)}"
    )


def build_agent_email(user_name: str) -> str:
    """Construye el email del agente."""

    return f"{user_name}@tfmmyllm.ai"


def build_agent_record(
    *,
    user_id: int,
    organization_id: int,
    role_spec: AgentRoleSpec,
    organization_name: str,
    project_name: str,
    password_encrypted: str,
    otp: str,
    contact_info_source: dict[str, str] | None = None,
) -> dict[str, object]:
    """Construye el registro JSON de un agente."""

    user_name = build_agent_username(
        role_spec.role_slug, organization_name, project_name
    )
    email = build_agent_email(user_name)
    contact_info_source = contact_info_source or {}
    cliente_value = organization_name
    country_value = contact_info_source.get("country", cliente_value)
    state_value = contact_info_source.get("state", cliente_value)
    zip_value = contact_info_source.get("zip_code", cliente_value)
    address_value = contact_info_source.get("address", cliente_value)
    return {
        "user_id": user_id,
        "organization_id": organization_id,
        "identity_type_id": role_spec.identity_type_id,
        "user_name": user_name,
        "user_password": password_encrypted,
        "user_email": email,
        "user_mobile": "+1500555001",
        "user_otp": otp,
        "active": True,
        "blocked": False,
        "contact_info": {
            "first_name": role_spec.role_slug,
            "sur_name": user_name,
            "country": country_value,
            "state": state_value,
            "zip_code": zip_value,
            "address": address_value,
        },
        "billing_info": {
            "first_name": role_spec.role_slug,
            "sur_name": user_name,
            "country": "España",
            "state": "Madrid",
            "zip_code": "28013",
            "address": "Prta del sol, centro",
        },
    }


def _normalize_slug(value: str) -> str:
    """Normaliza un texto para usarlo como slug en el nombre."""

    normalized = unicodedata.normalize("NFD", value.strip().lower())
    normalized = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return normalized.strip("_")
