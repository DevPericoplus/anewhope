"""Adaptadores de persistencia para la capa de aplicación."""

from .json_user_repository import JsonUserRepository
from .json_organization_repository import JsonOrganizationRepository

__all__ = [
    "JsonUserRepository",
    "JsonOrganizationRepository",
]
