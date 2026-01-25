"""Contrato de acceso a usuarios para la capa de aplicación."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.1_shared_domain.entities.domain_models import User


class UserRepository(Protocol):
    """Contrato para acceder a usuarios desde cualquier fuente de datos."""

    def get_by_id(self, user_id: int) -> User | None:
        """Obtiene un usuario por su identificador."""

    def get_by_email(self, user_email: str) -> User | None:
        """Obtiene un usuario por su email."""

    def get_by_name(self, user_name: str) -> User | None:
        """Obtiene un usuario por su nombre de usuario."""

    def exists_by_email(self, user_email: str) -> bool:
        """Verifica si existe un usuario por email."""

    def exists_by_mobile(self, user_mobile: str) -> bool:
        """Verifica si existe un usuario por teléfono."""

    def exists_by_name(self, user_name: str) -> bool:
        """Verifica si existe un usuario por nombre de usuario."""

    def save(self, user: User) -> User:
        """Crea un usuario y devuelve la entidad persistida."""

    def update_password_and_otp(
        self, user_email: str, new_password: str, new_otp: str
    ) -> bool:
        """Actualiza contraseña y OTP del usuario identificado por email."""
