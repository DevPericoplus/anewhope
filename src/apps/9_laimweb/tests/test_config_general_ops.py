"""Contrato de General: puente support_ops y dashboard de Registro."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from laim_web.config_ops import support_admin_call, users_list_path, visible_account
from laim_web.install_dashboard import build_dashboard, mask_serial

_LAIMWEB = Path(__file__).resolve().parents[1]


def test_mask_serial_hides_middle_groups() -> None:
    assert mask_serial("2-ABCD-EFGH-IJKL-MNOPQRS-TUVWXYZ") == "2-••••-••••-••••-••••-TUVWXYZ"
    assert mask_serial("corto") == "••••"


def test_build_dashboard_matches_maintenance_contract() -> None:
    dashboard = build_dashboard(
        "silicon",
        {
            "totals": {
                "registered": 4,
                "windows": 1,
                "mac": 2,
                "linux": 1,
                "this_month": 4,
                "licenses": 4,
            },
            "monthly": [
                {"month": "2026-09", "windows": 1, "mac": 0, "linux": 0, "total": 1, "cumulative": 1},
                {"month": "2026-10", "windows": 0, "mac": 2, "linux": 1, "total": 3, "cumulative": 4},
            ],
        },
        [
            {
                "installation_id": 1,
                "user_id": 9,
                "serial_number": "2-AAAA-BBBB-CCCC-DDDDDDD-EEEEEEE",
                "hostname": "box",
                "display_name": "Taller",
                "operating_system": "linux",
                "edition": "community_edition",
                "origin": "manual",
                "status": "registered",
            }
        ],
    )
    assert dashboard["environment"] == "silicon"
    assert dashboard["totals"]["mac"] == 2
    assert dashboard["totals"]["licenses"] == 4
    assert "polyline" in dashboard["svg_trend"]
    assert "<rect" in dashboard["svg_monthly"]
    assert "2026-09" in dashboard["svg_trend"]
    assert len(dashboard["highlights"]) >= 3
    assert dashboard["highlights"][0]["spark_svg"]
    assert dashboard["highlights"][0]["delta"]
    assert "path" in dashboard["svg_gauge"]
    assert "%" in dashboard["svg_mix"]
    assert "<circle" in dashboard["svg_scatter"]
    assert "<rect" in dashboard["svg_os"]
    assert "#6b7280" not in dashboard["svg_monthly"]
    assert INK_OR_MUTED(dashboard["svg_monthly"])
    assert dashboard["channels"]
    assert dashboard["highlights"][3]["title"] == "Cuota principal"
    item = dashboard["items"][0]
    assert item["alias"] == "Taller"
    assert "••••" in item["serial_masked"]
    assert item["serial_masked"] != item["hostname"]
    assert "master_key" not in dashboard["svg_trend"]
    assert "master_key" not in json.dumps(dashboard["items"])


def INK_OR_MUTED(svg: str) -> bool:
    return "#111827" in svg or "#1f2937" in svg


def test_empty_dashboard_names_environment() -> None:
    dashboard = build_dashboard("pre", {}, None)
    assert "pre" in dashboard["subtitle"]
    assert dashboard["svg_trend"] == ""


def test_visible_account_drops_secrets_and_keeps_missing_estado_empty() -> None:
    row = visible_account(
        {
            "user_id": 6,
            "user_name": "david",
            "user_password": "no-debe-viajar",
            "user_otp": "123",
            "master_key": "sek",
        }
    )
    assert row["estado"] == ""
    assert row["blocked"] is False
    blob = json.dumps(row)
    assert "no-debe-viajar" not in blob
    assert "user_password" not in row
    assert "master_key" not in row


def test_lector_does_not_mint_support_ops(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_forward(*_args, **_kwargs):
        raise AssertionError("un lector no puede reenviar support_ops")

    monkeypatch.setattr("laim_web.config_ops.laim_support_forward", fail_forward)
    result = support_admin_call(4, "GET", "/laim/support/users")
    assert result["success"] is False


def test_admin_mints_support_ops_without_session_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LAIM_SUPPORT_SECRET", "config-general-test-secret")
    seen: dict[str, object] = {}

    def capture(method, endpoint, authorization, payload=None, timeout=30.0):
        seen["method"] = method
        seen["endpoint"] = endpoint
        seen["authorization"] = authorization
        seen["payload"] = payload
        return {"success": True, "items": [{"user_id": 1, "user_name": "ana", "estado": "activo"}]}

    monkeypatch.setattr("laim_web.config_ops.laim_support_forward", capture)
    result = support_admin_call(2, "GET", users_list_path("ana"))
    assert result["success"] is True
    assert seen["endpoint"] == "/laim/support/users?query=ana"
    authorization = str(seen["authorization"])
    assert authorization.startswith("Bearer ")
    assert "session" not in authorization.lower()
    payload = authorization.split(".", 2)[1]
    payload += "=" * (-len(payload) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload))
    assert claims["operation"] == "support_ops"
    assert claims["caller"] == "laim_maintenance"
    assert seen["payload"] is None


def test_general_ui_reuses_support_paths_and_admin_gate() -> None:
    panel = (_LAIMWEB / "laim_web" / "components" / "config_general_panel.py").read_text(encoding="utf-8")
    page = (_LAIMWEB / "laim_web" / "pages" / "index.py").read_text(encoding="utf-8")
    ops = (_LAIMWEB / "laim_web" / "config_ops.py").read_text(encoding="utf-8")
    mixin = (_LAIMWEB / "laim_web" / "laim_config_mixin.py").read_text(encoding="utf-8")
    assert '("config_general"' in page
    assert "config_general_panel()" in page
    assert "Usuarios" in panel and "Registro" in panel
    assert "is_laim_admin" in panel
    assert "/api/support/" not in panel
    assert "session_token" not in ops
    assert "mint_support_token" in ops
    assert 'item["estado"] == ""' in panel
    assert "/laim/support/users/" in mixin
    assert "/password" in mixin
    assert "/status" in mixin
    assert "/laim/support/installations/metrics" in mixin
    assert "build_dashboard" in mixin
