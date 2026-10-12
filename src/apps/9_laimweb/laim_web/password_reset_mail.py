"""Plantilla del correo de recuperación (laimweb, no el middleware)."""

from __future__ import annotations

RESET_ACCEPTED_MSG = (
    "Si el correo está registrado, recibirás instrucciones."
)
RESET_CHANGED_MSG = "La contraseña ha sido cambiada"
RESET_DEAD_MSG = "El enlace no es válido o ha caducado"


def build_reset_url(public_origin: str, token: str) -> str:
    """URL absoluta opaca del entorno. Sin enlace extra a laim.app."""
    origin = (public_origin or "").strip().rstrip("/")
    token = token.strip()
    if origin:
        return f"{origin}/r/{token}"
    return f"/r/{token}"


def build_reset_email(user_name: str, reset_url: str) -> tuple[str, str]:
    """Asunto y cuerpo en texto plano. Saludo con user_name de BD."""
    subject = "Restablecer contraseña de LAIM"
    body = (
        f"Hola {user_name},\n"
        "\n"
        "Hemos recibido una solicitud para restablecer la contraseña de tu cuenta LAIM.\n"
        "\n"
        "Abre este enlace en los próximos 15 minutos:\n"
        f"{reset_url}\n"
        "\n"
        "Si no pediste este cambio, ignora este correo.\n"
        "\n"
        "Departamento de soporte de LAIM\n"
    )
    return subject, body
