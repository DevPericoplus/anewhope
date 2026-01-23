"""Tests de sincronización OTP entre JSON y MariaDB."""

from src.1_shared_domain.entities import user as user_domain


def test_validate_users_otp_sync_ok(monkeypatch):
    """Valida sincronización cuando los OTP coinciden."""

    monkeypatch.setattr(user_domain, "_should_sync_users_with_broker", lambda: True)
    monkeypatch.setattr(
        user_domain,
        "_load_users",
        lambda: [{"user_id": 1, "user_otp": "1234"}],
    )
    monkeypatch.setattr(
        user_domain,
        "_fetch_users_from_broker",
        lambda: [{"user_id": 1, "user_otp": "1234"}],
    )
    logs = []
    monkeypatch.setattr(
        user_domain, "_append_frontend_secure_log", lambda message: logs.append(message)
    )

    assert user_domain.validate_users_otp_sync() is True
    assert "Validacion OTP sincronizacion,OK" in logs


def test_validate_users_otp_sync_mismatch(monkeypatch):
    """Detecta discrepancias de OTP entre JSON y DB."""

    monkeypatch.setattr(user_domain, "_should_sync_users_with_broker", lambda: True)
    monkeypatch.setattr(
        user_domain,
        "_load_users",
        lambda: [{"user_id": 2, "user_otp": "1111"}],
    )
    monkeypatch.setattr(
        user_domain,
        "_fetch_users_from_broker",
        lambda: [{"user_id": 2, "user_otp": "2222"}],
    )
    logs = []
    monkeypatch.setattr(
        user_domain, "_append_frontend_secure_log", lambda message: logs.append(message)
    )

    assert user_domain.validate_users_otp_sync() is False
    assert any("DESALINEADO" in message for message in logs)
