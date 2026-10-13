"""Servicio de tickets de soporte LAIM."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)


def _load_module(relative_path: str, module_name: str) -> Any:
    module_path = Path(__file__).resolve().parents[3] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_states = _load_module(
    "src/2_shared_application/domain/laim_ticket_states.py",
    "laim_ticket_states_svc",
)
_dtos = _load_module(
    "src/2_shared_application/dtos/laim_tickets_dtos.py",
    "laim_tickets_dtos_svc",
)
_repo_mod = _load_module(
    "src/2_shared_application/adapters/laim_tickets_repository.py",
    "laim_tickets_repository_svc",
)
_session_repo_mod = _load_module(
    "src/2_shared_application/adapters/laim_mariadb_session_repository.py",
    "laim_session_repo_tickets",
)
_storage = _load_module(
    "src/apps/3_backend/4_infrastructure/persistence/storage_adapter.py",
    "laim_storage_tickets",
)

LaimTicketCreateDto = _dtos.LaimTicketCreateDto
LaimTicketsRepository = _repo_mod.LaimTicketsRepository
TicketStateError = _states.TicketStateError
DEFAULT_EDITION = _states.DEFAULT_EDITION
create_laim_session_engine = _session_repo_mod.create_laim_session_engine
load_laim_mariadb_settings = _storage.load_laim_mariadb_settings


class LaimTicketsService:
    """Orquesta validación, transiciones y persistencia de tickets."""

    def __init__(self, repository: LaimTicketsRepository | None = None) -> None:
        resolved = repository
        if resolved is None:
            settings = load_laim_mariadb_settings()
            engine = create_laim_session_engine(settings)
            resolved = LaimTicketsRepository(engine)
        self._repository = resolved

    def create_ticket(self, payload: dict[str, Any], user_context: dict[str, Any]) -> dict[str, Any]:
        """Alta de ticket por usuario autenticado."""
        user_id = int(user_context.get("user_id") or 0)
        user_name = str(user_context.get("user_name") or "").strip()
        user_email = str(user_context.get("user_email") or "").strip()
        organization_id = user_context.get("organization_id")
        if user_id <= 0 or not user_name or not user_email:
            return {"success": False, "error": "Se requiere una sesión de usuario."}
        try:
            dto = LaimTicketCreateDto.model_validate(payload)
        except Exception as exc:
            return {"success": False, "error": f"Datos inválidos: {exc}"}
        org = int(organization_id) if organization_id else None
        if org is not None and org <= 0:
            org = None
        try:
            ticket = self._repository.create_ticket(
                user_id=user_id,
                user_name=user_name,
                user_email=user_email,
                organization_id=org,
                edition=DEFAULT_EDITION,
                subject=dto.subject.strip(),
                body=dto.body.strip(),
            )
        except Exception as exc:
            _logger.exception("Error persistiendo ticket: %s", exc)
            return {"success": False, "error": "No se pudo crear el ticket. Inténtelo más tarde."}
        self._notify(ticket, destinatario="operador", tipo="ticket_created")
        return {"success": True, "ticket": self._public_ticket(ticket)}

    def list_my_tickets(self, user_id: int) -> dict[str, Any]:
        """Lista solo los tickets del usuario de sesión."""
        if user_id <= 0:
            return {"success": False, "error": "Se requiere una sesión de usuario.", "items": []}
        items = self._repository.list_tickets(user_id=user_id)
        return {"success": True, "items": [self._public_ticket(item) for item in items]}

    def get_my_ticket(self, ticket_id: int, user_id: int) -> dict[str, Any]:
        """Detalle si el ticket pertenece al usuario."""
        detail = self._load_detail(ticket_id)
        if detail is None:
            return {"success": False, "error": "Ticket no encontrado."}
        if int(detail["ticket"]["user_id"]) != int(user_id):
            return {"success": False, "error": "Ticket no encontrado."}
        return {"success": True, **detail}

    def reply_as_user(self, ticket_id: int, user_id: int, user_name: str, body: str) -> dict[str, Any]:
        """Respuesta del usuario; 404 si no es suyo."""
        ticket = self._repository.get_ticket(ticket_id)
        if ticket is None or int(ticket["user_id"]) != int(user_id):
            return {"success": False, "error": "Ticket no encontrado."}
        try:
            next_state = _states.next_state_after_user_reply(ticket["estado_clave"])
        except TicketStateError as exc:
            return {"success": False, "error": str(exc)}
        changed = next_state if next_state != ticket["estado_clave"] else None
        updated = self._repository.add_message_and_maybe_state(
            ticket_id,
            autor="usuario",
            actor_name=user_name or ticket["user_name"],
            cuerpo=body.strip(),
            new_estado_clave=changed,
            event_tipo="replied",
        )
        if updated is None:
            return {"success": False, "error": "Ticket no encontrado."}
        self._notify(updated, destinatario="operador", tipo="ticket_replied")
        detail = self._load_detail(ticket_id)
        return {"success": True, **(detail or {})}

    def list_operator_tickets(self, estado_clave: str | None = None, query: str | None = None, limit: int = 50) -> dict[str, Any]:
        """Listado de operador (todos los tickets del entorno)."""
        if estado_clave:
            try:
                _states.normalize_estado(estado_clave)
            except TicketStateError as exc:
                return {"success": False, "error": str(exc), "items": []}
        items = self._repository.list_tickets(
            estado_clave=estado_clave, query=query, limit=limit
        )
        return {"success": True, "items": [self._public_ticket(item) for item in items]}

    def get_operator_ticket(self, ticket_id: int) -> dict[str, Any]:
        """Detalle de operador."""
        detail = self._load_detail(ticket_id)
        if detail is None:
            return {"success": False, "error": "Ticket no encontrado."}
        return {"success": True, **detail}

    def dashboard(self) -> dict[str, Any]:
        """Conteos por estado."""
        counts = self._repository.count_by_estado()
        return {"success": True, "counts": counts}

    def reply_as_operator(self, ticket_id: int, actor: str, body: str) -> dict[str, Any]:
        """Respuesta pública del operador."""
        ticket = self._repository.get_ticket(ticket_id)
        if ticket is None:
            return {"success": False, "error": "Ticket no encontrado."}
        try:
            next_state = _states.next_state_after_operator_reply(ticket["estado_clave"])
        except TicketStateError as exc:
            return {"success": False, "error": str(exc)}
        changed = next_state if next_state != ticket["estado_clave"] else None
        updated = self._repository.add_message_and_maybe_state(
            ticket_id,
            autor="operador",
            actor_name=actor or "laim_maintenance",
            cuerpo=body.strip(),
            new_estado_clave=changed,
            event_tipo="replied",
        )
        if updated is None:
            return {"success": False, "error": "Ticket no encontrado."}
        self._notify(updated, destinatario="usuario", tipo="ticket_replied")
        detail = self._load_detail(ticket_id)
        return {"success": True, **(detail or {})}

    def change_status(self, ticket_id: int, estado_clave: str, actor: str) -> dict[str, Any]:
        """Transición explícita del operador."""
        ticket = self._repository.get_ticket(ticket_id)
        if ticket is None:
            return {"success": False, "error": "Ticket no encontrado."}
        try:
            target = _states.apply_operator_transition(ticket["estado_clave"], estado_clave)
        except TicketStateError as exc:
            return {"success": False, "error": str(exc)}
        updated = self._repository.change_estado(
            ticket_id, target, actor or "laim_maintenance", "status_changed"
        )
        if updated is None:
            return {"success": False, "error": "Ticket no encontrado."}
        self._notify(updated, destinatario="usuario", tipo="ticket_status")
        detail = self._load_detail(ticket_id)
        return {"success": True, **(detail or {})}

    def reopen(self, ticket_id: int, actor: str) -> dict[str, Any]:
        """Reabre un ticket cerrado."""
        ticket = self._repository.get_ticket(ticket_id)
        if ticket is None:
            return {"success": False, "error": "Ticket no encontrado."}
        try:
            target = _states.reopen(ticket["estado_clave"])
        except TicketStateError as exc:
            return {"success": False, "error": str(exc)}
        updated = self._repository.change_estado(
            ticket_id, target, actor or "laim_maintenance", "reopened"
        )
        if updated is None:
            return {"success": False, "error": "Ticket no encontrado."}
        self._notify(updated, destinatario="usuario", tipo="ticket_reopened")
        detail = self._load_detail(ticket_id)
        return {"success": True, **(detail or {})}

    def list_my_notifications(self, user_id: int) -> dict[str, Any]:
        """Pendientes del usuario. El poll no hace ack."""
        if user_id <= 0:
            return {"success": False, "error": "Se requiere una sesión de usuario.", "items": []}
        items = self._repository.list_pending_notifications(
            destinatario="usuario", user_id=user_id
        )
        return {"success": True, "items": [self._public_notification(item) for item in items]}

    def ack_my_notification(self, notif_id: int, user_id: int) -> dict[str, Any]:
        """Ack explícito; no se llama desde el poll."""
        if user_id <= 0 or notif_id <= 0:
            return {"success": False, "error": "Notificación no encontrada."}
        if not self._repository.ack_notification(
            notif_id, destinatario="usuario", user_id=user_id
        ):
            return {"success": False, "error": "Notificación no encontrada."}
        return {"success": True}

    def list_operator_notifications(self) -> dict[str, Any]:
        """Pendientes de operador (altas y respuestas de usuario)."""
        items = self._repository.list_pending_notifications(destinatario="operador")
        return {"success": True, "items": [self._public_notification(item) for item in items]}

    def ack_operator_notification(self, notif_id: int) -> dict[str, Any]:
        """Ack de operador al abrir/descartar el aviso."""
        if notif_id <= 0:
            return {"success": False, "error": "Notificación no encontrada."}
        if not self._repository.ack_notification(notif_id, destinatario="operador"):
            return {"success": False, "error": "Notificación no encontrada."}
        return {"success": True}

    def _notify(self, ticket: dict[str, Any], destinatario: str, tipo: str) -> None:
        """Aviso al otro lado. Un fallo no tumba la operación principal."""
        try:
            user_id = int(ticket.get("user_id") or 0) if destinatario == "usuario" else None
            self._repository.add_notification(
                ticket_id=int(ticket.get("id") or 0),
                destinatario=destinatario,
                user_id=user_id,
                tipo=tipo,
            )
        except Exception as exc:
            _logger.warning("No se pudo persistir aviso de ticket: %s", exc)

    def _load_detail(self, ticket_id: int) -> dict[str, Any] | None:
        ticket = self._repository.get_ticket(ticket_id)
        if ticket is None:
            return None
        return {
            "ticket": self._public_ticket(ticket),
            "messages": self._repository.list_messages(ticket_id),
            "events": self._repository.list_events(ticket_id),
        }

    @staticmethod
    def _public_ticket(ticket: dict[str, Any]) -> dict[str, Any]:
        estado = str(ticket.get("estado_clave") or "")
        return {
            "id": ticket.get("id"),
            "estado_clave": estado,
            "estado_nombre": ticket.get("estado_nombre"),
            "user_id": ticket.get("user_id"),
            "user_name": ticket.get("user_name"),
            "user_email": ticket.get("user_email"),
            "organization_id": ticket.get("organization_id"),
            "edition": ticket.get("edition"),
            "subject": ticket.get("subject"),
            "body": ticket.get("body"),
            "opened_at": str(ticket.get("opened_at") or ""),
            "closed_at": str(ticket.get("closed_at") or "") if ticket.get("closed_at") else "",
            "updated_at": str(ticket.get("updated_at") or ""),
            "readonly": estado == _states.ESTADO_CERRADO,
        }

    @staticmethod
    def _public_notification(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": item.get("id"),
            "ticket_id": item.get("ticket_id"),
            "tipo": item.get("tipo"),
            "subject": item.get("subject") or "",
            "estado_clave": item.get("estado_clave") or "",
            "created_at": str(item.get("created_at") or ""),
        }
