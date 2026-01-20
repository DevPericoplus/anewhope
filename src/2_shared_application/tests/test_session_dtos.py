"""Tests de DTOs de sesión."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_module(module_path: Path, module_name: str) -> Any:
    """Carga un módulo desde ruta absoluta."""

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar el módulo {module_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_ROOT_PATH = Path(__file__).resolve().parents[2]
_session_dtos = _load_module(
    _ROOT_PATH / "2_shared_application/dtos/session_dtos.py",
    "shared_session_dtos_tests",
)

SessionDto = _session_dtos.SessionDto
SessionTokenBinding = _session_dtos.SessionTokenBinding
Session = _session_dtos.Session
SessionStatus = _session_dtos.SessionStatus


def test_session_dto_to_domain_maps_fields() -> None:
    """Verifica el mapeo correcto de DTO a dominio."""

    now = datetime.now(timezone.utc)
    dto = SessionDto(
        session_id="session-123",
        user_id=1,
        organization_id=2,
        identity_type_id=3,
        status=SessionStatus.ACTIVE,
        created_at=now,
        last_activity=now,
        expires_at=now,
        access_token_jti="access-jti",
        session_token_jti="session-jti",
        ip_address="127.0.0.1",
        user_agent="pytest",
    )

    domain = dto.to_domain()

    assert isinstance(domain, Session)
    assert domain.session_id == "session-123"
    assert domain.user_id == 1
    assert domain.organization_id == 2
    assert domain.identity_type_id == 3
    assert domain.tokens.access_token_jti == "access-jti"
    assert domain.tokens.session_token_jti == "session-jti"
    assert domain.status == SessionStatus.ACTIVE
    assert domain.ip_address == "127.0.0.1"
    assert domain.user_agent == "pytest"


def test_session_dto_from_domain_maps_fields() -> None:
    """Verifica el mapeo correcto de dominio a DTO."""

    now = datetime.now(timezone.utc)
    domain = Session(
        session_id="session-999",
        user_id=9,
        organization_id=8,
        identity_type_id=7,
        tokens=SessionTokenBinding(
            access_token_jti="access-999",
            session_token_jti="session-999",
        ),
        status=SessionStatus.INACTIVE,
        created_at=now,
        last_activity=now,
        expires_at=now,
        ip_address="10.0.0.1",
        user_agent="pytest-agent",
    )

    dto = SessionDto.from_domain(domain)

    assert dto.session_id == "session-999"
    assert dto.user_id == 9
    assert dto.organization_id == 8
    assert dto.identity_type_id == 7
    assert dto.status == SessionStatus.INACTIVE
    assert dto.access_token_jti == "access-999"
    assert dto.session_token_jti == "session-999"
    assert dto.ip_address == "10.0.0.1"
    assert dto.user_agent == "pytest-agent"
