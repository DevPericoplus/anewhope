"""Contrato de los botones y modales de tickets en Soporte."""

from __future__ import annotations

from pathlib import Path

laimweb_root = Path(__file__).resolve().parents[1]


def test_soporte_buttons_and_email_navigate_to_contacto() -> None:
    actions = (laimweb_root / "laim_web" / "components" / "page_actions.py").read_text(
        encoding="utf-8"
    )
    assert 'PageAction("Abrir ticket de soporte", "support_ticket")' in actions
    assert 'PageAction("Estado de tickets", "support_status")' in actions
    assert 'PageAction("Contactar por email", "support_email")' in actions
    assert "mailto:" not in actions.split('"soporte"')[1].split("faq")[0]

    state = (laimweb_root / "laim_web" / "laim_state.py").read_text(encoding="utf-8")
    assert 'action_key == "support_email"' in state
    assert 'self.active_menu = "contacto"' in state
    assert "open_ticket_create" in state
    assert "open_ticket_status" in state
    assert "poll_ticket_notifications" in state
    assert "ack_ticket_notification" in state
    assert "laim_ticket_notifications_pending" in (
        laimweb_root / "laim_web" / "adapters" / "laim_api_client.py"
    ).read_text(encoding="utf-8")


def test_notification_modal_does_not_ack_on_poll() -> None:
    modal = (laimweb_root / "laim_web" / "components" / "tickets_modal.py").read_text(
        encoding="utf-8"
    )
    state = (laimweb_root / "laim_web" / "laim_state.py").read_text(encoding="utf-8")
    assert "Un ticket de soporte requiere su atención." in modal
    assert "Ir a soporte" in modal
    assert "poll_ticket_notifications" in state
    assert "No hace ack" in state or "no hace ack" in state.lower()
    assert "ticket_notification_modal()" in (
        laimweb_root / "laim_web" / "pages" / "index.py"
    ).read_text(encoding="utf-8")


def test_user_notification_routes_registered_before_id() -> None:
    router = (
        Path(__file__).resolve().parents[2]
        / "3_backend"
        / "router_laim_tickets.py"
    ).read_text(encoding="utf-8")
    pending = router.find("@router.get(\"/notifications/pending\")")
    by_id = router.find("@router.get(\"/{ticket_id}\")")
    assert pending != -1 and by_id != -1 and pending < by_id


def test_operator_notification_routes_registered_before_id() -> None:
    router = (
        Path(__file__).resolve().parents[2]
        / "3_backend"
        / "router_laim_tickets_ops.py"
    ).read_text(encoding="utf-8")
    pending = router.find('@router.get("/notifications")')
    by_id = router.find('@router.get("/{ticket_id}")')
    assert pending != -1 and by_id != -1 and pending < by_id
