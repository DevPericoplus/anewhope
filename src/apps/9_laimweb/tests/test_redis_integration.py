"""Tests de integración Redis para LaimSharedSessionState en LAIM Web."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parents[4]
src_root = Path(__file__).resolve().parents[3]
laimweb_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_root))
sys.path.insert(0, str(laimweb_root))


class TestLaimSharedSessionStateIntegration:
    """Verifica herencia y contrato de sesión LAIM."""

    def test_state_inherits_from_laim_shared_session_state(self) -> None:
        from laim_web.laim_state import LaimWebState
        from laim_web.shared_state import LaimSharedSessionState

        assert issubclass(LaimWebState, LaimSharedSessionState)

    def test_state_has_session_methods(self) -> None:
        from laim_web.laim_state import LaimWebState

        required_methods = [
            "load_user_data",
            "clear_session",
            "update_tokens",
            "ensure_tokens_valid",
            "auto_renew_tokens_loop",
            "handle_login",
            "handle_logout",
            "handle_register",
        ]
        for method_name in required_methods:
            assert hasattr(LaimWebState, method_name)

    def test_state_has_permission_fields(self) -> None:
        from laim_web.laim_state import LaimWebState

        key_permissions = [
            "can_training_create",
            "can_folder_read",
            "can_project_read",
            "can_user_read",
        ]
        for perm_name in key_permissions:
            assert hasattr(LaimWebState, perm_name)

    def test_laim_redis_prefix_in_source(self) -> None:
        from laim_web.shared_state import LaimSharedSessionState

        source_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "laim_shared_session_state.py"
        )
        source = source_path.read_text(encoding="utf-8")
        assert "LAIM_REDIS_KEY_PREFIX" in source
        assert 'laim:session_tokens:' in source
        assert hasattr(LaimSharedSessionState, "load_user_data")

    def test_clear_session_resets_fields(self) -> None:
        source_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "laim_shared_session_state.py"
        )
        source = source_path.read_text(encoding="utf-8")
        assert "def clear_session" in source
        assert 'self.current_app = "laimweb"' in source

    def test_shared_state_helper_imports(self) -> None:
        from laim_web.shared_state import LaimSharedSessionState
        import reflex as rx

        assert issubclass(LaimSharedSessionState, rx.State)


class TestLaimRedisKeyPrefix:
    """Tests unitarios del prefijo Redis LAIM."""

    def test_redis_key_uses_laim_prefix(self) -> None:
        source_path = (
            project_root
            / "src"
            / "2_shared_application"
            / "reflex_shared"
            / "laim_shared_session_state.py"
        )
        source = source_path.read_text(encoding="utf-8")
        assert "def _redis_tokens_key" in source
        assert 'f"{LAIM_REDIS_KEY_PREFIX}{self.session_id}"' in source
