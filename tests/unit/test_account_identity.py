"""Tests TDD del modelo de cuentas individuales vs organización."""

from __future__ import annotations

import pytest

from tests.helpers import load_module_from_path

_mod = load_module_from_path("account_identity", "src/1_shared_domain/account_identity.py")
IDENTITY_INDIVIDUAL = _mod.IDENTITY_INDIVIDUAL
IDENTITY_ORG_ADMIN = _mod.IDENTITY_ORG_ADMIN
LoginIdentifier = _mod.LoginIdentifier
AccountIdentityError = _mod.AccountIdentityError
build_login_identifier = _mod.build_login_identifier
generate_organization_acronym = _mod.generate_organization_acronym
is_individual_account = _mod.is_individual_account
match_user_record_for_login = _mod.match_user_record_for_login
parse_login_identifier = _mod.parse_login_identifier
reject_internal_identity_from_public_ui = _mod.reject_internal_identity_from_public_ui
resolve_public_registration_identity = _mod.resolve_public_registration_identity


def test_acronym_from_simple_name() -> None:
    """Usa los primeros tokens del slug hasta alcanzar 5 caracteres."""
    assert generate_organization_acronym("Spacio Ingeniería", set()) == "spacio"


def test_acronym_pads_short_name() -> None:
    """Un nombre corto se repite hasta alcanzar 5 caracteres."""
    assert generate_organization_acronym("ONG", set()) == "ongong"


def test_acronym_collision_appends_suffix() -> None:
    """Si el slug existe, se añade 2, 3, …"""
    existing = {"spacio"}
    assert generate_organization_acronym("Spacio Ingeniería", existing) == "spacio2"
    existing.add("spacio2")
    assert generate_organization_acronym("Spacio Ingeniería", existing) == "spacio3"


def test_acronym_skips_reserved() -> None:
    """Los acrónimos reservados no se asignan a una organización."""
    assert generate_organization_acronym("admin", set()) == "admin2"


def test_parse_individual_login() -> None:
    """Login sin @ es cuenta individual."""
    parsed = parse_login_identifier("jluis")
    assert parsed == LoginIdentifier(user_name="jluis", acronym=None)
    assert parsed.is_individual is True


def test_parse_organization_login() -> None:
    """Login cualificado usa usuario@acronimo."""
    parsed = parse_login_identifier("jluis@spacio")
    assert parsed.user_name == "jluis"
    assert parsed.acronym == "spacio"
    assert parsed.is_individual is False


def test_parse_rejects_empty_and_bad_acronym() -> None:
    """Identificadores vacíos o con acrónimo corto son inválidos."""
    with pytest.raises(AccountIdentityError):
        parse_login_identifier("")
    with pytest.raises(AccountIdentityError):
        parse_login_identifier("jluis@ab")


def test_build_login_identifier_roundtrip() -> None:
    """Reconstruir el texto de login es estable."""
    assert build_login_identifier("jluis", None) == "jluis"
    assert build_login_identifier("jluis", "spacio") == "jluis@spacio"


def test_public_registration_identities() -> None:
    """El alta pública solo puede crear 6 o 2."""
    assert resolve_public_registration_identity("individual") == IDENTITY_INDIVIDUAL
    assert resolve_public_registration_identity("organization") == IDENTITY_ORG_ADMIN
    with pytest.raises(AccountIdentityError):
        resolve_public_registration_identity("internal")
    with pytest.raises(AccountIdentityError):
        reject_internal_identity_from_public_ui(1)
    reject_internal_identity_from_public_ui(6)


def test_match_login_prefers_individual_without_at() -> None:
    """Sin @ solo entra el individual; el homónimo de org no."""
    users = [
        {"user_name": "jluis", "organization_id": 0, "identity_type_id": 6},
        {"user_name": "jluis", "organization_id": 4, "identity_type_id": 2},
    ]
    found = match_user_record_for_login(
        users, parse_login_identifier("jluis"), {4: "spacio"}
    )
    assert found is not None
    assert int(found["identity_type_id"]) == IDENTITY_INDIVIDUAL


def test_match_login_org_requires_acronym() -> None:
    """jluis@spacio y jluis@trace son cuentas distintas."""
    users = [
        {"user_name": "jluis", "organization_id": 4, "identity_type_id": 2},
        {"user_name": "jluis", "organization_id": 9, "identity_type_id": 2},
    ]
    acronyms = {4: "spacio", 9: "trace"}
    spacio = match_user_record_for_login(
        users, parse_login_identifier("jluis@spacio"), acronyms
    )
    trace = match_user_record_for_login(
        users, parse_login_identifier("jluis@trace"), acronyms
    )
    assert spacio is not None and int(spacio["organization_id"]) == 4
    assert trace is not None and int(trace["organization_id"]) == 9


def test_match_login_compat_unique_org_username() -> None:
    """Compatibilidad MVP: user_name único de org sigue autenticando sin @."""
    users = [{"user_name": "adminone", "organization_id": 1, "identity_type_id": 1}]
    found = match_user_record_for_login(
        users, parse_login_identifier("adminone"), {1: "myllm"}
    )
    assert found is not None
    assert str(found["user_name"]) == "adminone"


def test_is_individual_account() -> None:
    """Solo el tipo 6 sin org es cuenta individual."""
    assert is_individual_account(6, 0) is True
    assert is_individual_account(6, None) is True
    assert is_individual_account(2, 4) is False
    assert is_individual_account(6, 4) is False
