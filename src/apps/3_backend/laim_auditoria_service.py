"""Servicio de auditoría de uso del portal laimweb."""

from __future__ import annotations

import importlib.util
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_logger = logging.getLogger("LaimAuditoriaService")


def _load_module(relative_path: str, module_name: str) -> Any:
    module_path = Path(__file__).resolve().parents[3] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_domain = _load_module(
    "src/2_shared_application/domain/laim_auditoria.py",
    "laim_auditoria_domain_svc",
)
_repo_mod = _load_module(
    "src/2_shared_application/adapters/laim_auditoria_repository.py",
    "laim_auditoria_repository_svc",
)
_session_repo_mod = _load_module(
    "src/2_shared_application/adapters/laim_mariadb_session_repository.py",
    "laim_auditoria_session_engine",
)
_storage = _load_module(
    "src/apps/3_backend/4_infrastructure/persistence/storage_adapter.py",
    "laim_auditoria_storage",
)

LaimAuditoriaRepository = _repo_mod.LaimAuditoriaRepository
create_laim_session_engine = _session_repo_mod.create_laim_session_engine
load_laim_mariadb_settings = _storage.load_laim_mariadb_settings

USUARIO_ACCIONES = _domain.USUARIO_ACCIONES
INSTALADOR_ACCIONES = _domain.INSTALADOR_ACCIONES
FORO_ACCIONES = _domain.FORO_ACCIONES
SECCIONES = _domain.SECCIONES
EDITIONS = _domain.EDITIONS
PLATFORMS = _domain.PLATFORMS
HEARTBEAT_MIN_INTERVAL_SECONDS = _domain.HEARTBEAT_MIN_INTERVAL_SECONDS
should_record_download = _domain.should_record_download
seccion_from_menu = _domain.seccion_from_menu


class LaimAuditoriaService:
    """Valida enums y orquesta el repositorio. Los hooks tragan errores."""

    def __init__(self, repository: Any | None = None) -> None:
        if repository is None:
            settings = load_laim_mariadb_settings()
            engine = create_laim_session_engine(settings)
            repository = LaimAuditoriaRepository(engine)
        self._repository = repository

    def record_usuario(
        self,
        accion: str,
        user_name: str,
        user_id: int | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        if accion not in USUARIO_ACCIONES:
            return {"success": False, "error": f"acción de usuario inválida: {accion}"}
        row_id = self._repository.record_usuario(
            accion, user_name, user_id=user_id, session_id=session_id
        )
        return {"success": True, "id": row_id}

    def record_instalador(
        self,
        accion: str,
        edition: str,
        platform: str,
        version: str = "",
        filename: str = "",
        user_id: int | None = None,
    ) -> dict[str, Any]:
        if accion not in INSTALADOR_ACCIONES:
            return {"success": False, "error": f"acción de instalador inválida: {accion}"}
        if edition not in EDITIONS:
            return {"success": False, "error": f"edición inválida: {edition}"}
        if platform not in PLATFORMS:
            return {"success": False, "error": f"plataforma inválida: {platform}"}
        row_id = self._repository.record_instalador(
            accion,
            edition,
            platform,
            version=version,
            filename=filename,
            user_id=user_id if user_id else None,
        )
        return {"success": True, "id": row_id}

    def record_download_if_source(
        self,
        source: str,
        edition: str,
        platform: str,
        version: str = "",
        filename: str = "",
        user_id: int | None = None,
    ) -> dict[str, Any]:
        if not should_record_download(source):
            return {"success": True, "skipped": True}
        return self.record_instalador(
            "descarga",
            edition,
            platform,
            version=version,
            filename=filename,
            user_id=user_id,
        )

    def record_foro(
        self,
        accion: str,
        user_id: int,
        thread_id: int,
        post_id: int | None = None,
        subcategory_id: str = "",
    ) -> dict[str, Any]:
        if accion not in FORO_ACCIONES:
            return {"success": False, "error": f"acción de foro inválida: {accion}"}
        row_id = self._repository.record_foro(
            accion,
            user_id,
            thread_id,
            post_id=post_id,
            subcategory_id=subcategory_id,
        )
        return {"success": True, "id": row_id}

    def heartbeat(
        self,
        user_id: int,
        session_id: str,
        seccion: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        if not user_id or not session_id:
            return {"success": False, "error": "Se requiere sesión"}
        moment = now or datetime.now(timezone.utc)
        latest = self._repository.get_latest_visita(session_id)
        if latest is not None and self._too_soon(latest.get("last_seen_at"), moment):
            return {"success": True, "skipped": True}
        visita = self._repository.upsert_visita(user_id, session_id, now=moment)
        pagina = None
        if seccion:
            if seccion not in SECCIONES:
                return {"success": False, "error": f"sección inválida: {seccion}"}
            pagina = self._repository.heartbeat_pagina(
                user_id, session_id, seccion, now=moment
            )
        return {"success": True, "visita": visita, "pagina": pagina}

    def change_seccion(
        self,
        user_id: int,
        session_id: str,
        seccion: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        if not user_id or not session_id:
            return {"success": False, "error": "Se requiere sesión"}
        if seccion not in SECCIONES:
            return {"success": False, "error": f"sección inválida: {seccion}"}
        moment = now or datetime.now(timezone.utc)
        self._repository.upsert_visita(user_id, session_id, now=moment)
        pagina = self._repository.heartbeat_pagina(
            user_id, session_id, seccion, now=moment
        )
        return {"success": True, "pagina": pagina}

    def close_session(self, session_id: str) -> dict[str, Any]:
        if not session_id:
            return {"success": False, "error": "session_id requerido"}
        self._repository.close_visita_and_pagina(session_id)
        return {"success": True}

    def safe_record_usuario(self, **kwargs: Any) -> None:
        try:
            self.record_usuario(**kwargs)
        except Exception as exc:
            _logger.warning("auditoría usuario no persistida: %s", exc)

    def safe_record_foro(self, **kwargs: Any) -> None:
        try:
            self.record_foro(**kwargs)
        except Exception as exc:
            _logger.warning("auditoría foro no persistida: %s", exc)

    def safe_record_instalador(self, **kwargs: Any) -> None:
        try:
            self.record_instalador(**kwargs)
        except Exception as exc:
            _logger.warning("auditoría instalador no persistida: %s", exc)

    def safe_close_session(self, session_id: str) -> None:
        try:
            self.close_session(session_id)
        except Exception as exc:
            _logger.warning("cierre de visita no persistido: %s", exc)

    @staticmethod
    def _too_soon(last_seen: Any, now: datetime) -> bool:
        if last_seen is None:
            return False
        if isinstance(last_seen, datetime):
            seen = last_seen
        else:
            seen = datetime.fromisoformat(str(last_seen).replace(" ", "T"))
        if seen.tzinfo is None:
            seen = seen.replace(tzinfo=timezone.utc)
        return (now - seen).total_seconds() < HEARTBEAT_MIN_INTERVAL_SECONDS
