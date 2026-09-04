"""Identidad de cuentas: individuales vs organización.

Reglas de negocio para el identificador de login, el acrónimo cosmético
de organización y los identity_type_id públicos. Sin I/O.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

class AccountIdentityError(Exception):
    """Error de reglas de identidad de cuentas."""


IDENTITY_SUPERADMIN = 1
IDENTITY_ORG_ADMIN = 2
IDENTITY_ORG_EDITOR = 3
IDENTITY_ORG_READER = 4
IDENTITY_ORG_AUDITOR = 5
IDENTITY_INDIVIDUAL = 6

INTERNAL_IDENTITY_TYPE_IDS = frozenset({1, 10, 11, 12, 13})
PUBLIC_ACCOUNT_KINDS = frozenset({"individual", "organization"})

ACRONYM_MIN_LENGTH = 5
RESERVED_ACRONYMS = frozenset(
    {
        "admin",
        "system",
        "internal",
        "laim",
        "personal",
        "www",
        "getmylllm",
    }
)

_USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,}$")
_ACRONYM_RE = re.compile(r"^[a-z0-9]{5,32}$")


@dataclass(frozen=True)
class LoginIdentifier:
    """Identificador de login parseado."""

    user_name: str
    acronym: str | None

    @property
    def is_individual(self) -> bool:
        """True si el login no incluye acrónimo de organización."""
        return self.acronym is None

    def as_text(self) -> str:
        """Reconstruye el texto de login."""
        if self.acronym:
            return f"{self.user_name}@{self.acronym}"
        return self.user_name


def normalize_acronym_source(name: str) -> str:
    """Normaliza un nombre de organización a slug [a-z0-9]."""
    return "".join(_tokenize_organization_name(name))


def _tokenize_organization_name(name: str) -> list[str]:
    """Parte el nombre en tokens alfanuméricos en minúsculas."""
    nfkd = unicodedata.normalize("NFKD", name or "")
    ascii_only = "".join(char for char in nfkd if not unicodedata.combining(char))
    return re.findall(r"[a-z0-9]+", ascii_only.lower())


def _pad_acronym_base(base: str) -> str:
    if not base:
        return "orgxx"
    padded = base
    while len(padded) < ACRONYM_MIN_LENGTH:
        padded += base
    return padded


def generate_organization_acronym(name: str, existing: set[str]) -> str:
    """Genera un acrónimo único (≥5) a partir del nombre de la organización.

    Concatena los primeros tokens del slug hasta alcanzar 5 caracteres
    (spacioingenieria → spacio). Si choca, añade 2, 3, …
    """
    taken = {item.lower() for item in existing}
    taken.update(RESERVED_ACRONYMS)
    accumulated = ""
    for token in _tokenize_organization_name(name):
        accumulated += token
        if len(accumulated) >= ACRONYM_MIN_LENGTH:
            break
    base = _pad_acronym_base(accumulated)
    if base not in taken:
        return base
    suffix = 2
    while True:
        candidate = f"{base}{suffix}"
        if candidate not in taken:
            return candidate
        suffix += 1


def parse_login_identifier(raw: str) -> LoginIdentifier:
    """Parsea `usuario` (individual) o `usuario@acronimo` (organización)."""
    text = (raw or "").strip()
    if not text:
        raise AccountIdentityError("El identificador de login no puede estar vacío")
    if "@" not in text:
        if not _USERNAME_RE.match(text):
            raise AccountIdentityError("Nombre de usuario inválido")
        return LoginIdentifier(user_name=text, acronym=None)
    local, _sep, realm = text.rpartition("@")
    if not local or not realm:
        raise AccountIdentityError("Identificador de login inválido")
    if not _USERNAME_RE.match(local):
        raise AccountIdentityError("Nombre de usuario inválido")
    acronym = realm.lower()
    if not _ACRONYM_RE.match(acronym):
        raise AccountIdentityError("Acrónimo de organización inválido")
    return LoginIdentifier(user_name=local, acronym=acronym)


def build_login_identifier(user_name: str, acronym: str | None) -> str:
    """Construye el texto de login a partir de usuario y acrónimo opcional."""
    identifier = LoginIdentifier(user_name=user_name.strip(), acronym=acronym)
    return identifier.as_text()


def resolve_public_registration_identity(account_kind: str) -> int:
    """Resuelve el identity_type_id de un alta pública.

    individual → 6. organization (primer admin) → 2.
    Nunca 1 ni 10-13.
    """
    kind = (account_kind or "").strip().lower()
    if kind == "individual":
        return IDENTITY_INDIVIDUAL
    if kind == "organization":
        return IDENTITY_ORG_ADMIN
    raise AccountIdentityError("Tipo de cuenta pública inválido")


def reject_internal_identity_from_public_ui(identity_type_id: int) -> None:
    """Impide que un alta pública solicite un rol interno."""
    if identity_type_id in INTERNAL_IDENTITY_TYPE_IDS:
        raise AccountIdentityError("No se puede asignar un rol interno desde la interfaz pública")


def is_individual_account(identity_type_id: int, organization_id: int | None) -> bool:
    """True si la cuenta es individual (sin organización)."""
    org_id = organization_id or 0
    return identity_type_id == IDENTITY_INDIVIDUAL and org_id == 0


def match_user_record_for_login(
    users: list[dict[str, object]],
    identifier: LoginIdentifier,
    org_acronyms: dict[int, str],
) -> dict[str, object] | None:
    """Selecciona el registro de usuario que corresponde al login.

    - Sin @: individuales (org 0/None). Compatibilidad MVP: si no hay
      individual y el user_name es único en todo el sistema, se acepta.
    - Con @: user_name + acrónimo de su organización.
    """
    name = identifier.user_name
    if identifier.acronym is None:
        individuals = [
            user
            for user in users
            if str(user.get("user_name", "")) == name
            and is_individual_account(
                int(user.get("identity_type_id") or 0),
                int(user.get("organization_id") or 0),
            )
        ]
        if individuals:
            return individuals[0]
        matches = [user for user in users if str(user.get("user_name", "")) == name]
        if len(matches) == 1:
            return matches[0]
        return None

    wanted = identifier.acronym.lower()
    for user in users:
        if str(user.get("user_name", "")) != name:
            continue
        org_id = int(user.get("organization_id") or 0)
        if org_id <= 0:
            continue
        if org_acronyms.get(org_id, "").lower() == wanted:
            return user
    return None
