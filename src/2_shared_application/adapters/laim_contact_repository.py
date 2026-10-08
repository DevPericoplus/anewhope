"""Repositorio MariaDB para casos de contacto LAIM."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

ESTADO_CASO_ABIERTO_ID = 1
ESTADO_CASO_GESTIONANDO_ID = 2
ESTADO_CASO_ESCALADO_ID = 3
ESTADO_CASO_RESUELTO_ID = 4
ESTADO_CASO_DESCARTADO_ID = 5

ESTADO_CLAVE_TO_ID = {
    "abierto": ESTADO_CASO_ABIERTO_ID,
    "gestionando": ESTADO_CASO_GESTIONANDO_ID,
    "escalado": ESTADO_CASO_ESCALADO_ID,
    "resuelto": ESTADO_CASO_RESUELTO_ID,
    "descartado": ESTADO_CASO_DESCARTADO_ID,
}

CASOS_CONTACTO_TABLE = "casos_contacto"
CASOS_CONTACTO_IMAGENES_TABLE = "casos_contacto_imagenes"
CASOS_CONTACTO_AUDITORIA_TABLE = "casos_contacto_auditoria"
CASOS_CONTACTO_ETIQUETAS_TABLE = "casos_contacto_etiquetas"
CASOS_CONTACTO_RESPUESTAS_TABLE = "casos_contacto_respuestas"

_CASE_LIST_COLUMNS = """
    c.id, c.id_estado, e.clave AS estado_clave, e.nombre AS estado_nombre,
    c.usage_mode, c.affected_user_info,
    LEFT(c.message_body, 200) AS message_preview,
    c.reply_email, c.user_id, c.user_name, c.organization_id,
    u.user_mobile, c.created_at, c.updated_at,
    EXISTS(
        SELECT 1 FROM casos_contacto_imagenes i WHERE i.id_caso = c.id
    ) AS has_image
"""

_CASE_DETAIL_COLUMNS = """
    c.id, c.id_estado, e.clave AS estado_clave, e.nombre AS estado_nombre,
    c.usage_mode, c.affected_user_info, c.message_body,
    c.reply_email, c.user_id, c.user_name, c.organization_id,
    u.user_mobile, c.created_at, c.updated_at
"""


@dataclass(frozen=True)
class LaimContactImageRecord:
    """Datos de imagen adjunta."""

    file_name: str
    mime_type: str
    file_size: int
    image_data: bytes


class LaimContactRepository:
    """Persistencia en casos_contacto y casos_contacto_imagenes."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._logger = logging.getLogger("LaimContactRepository")

    def create_message_with_image(
        self,
        usage_mode: str,
        affected_user_info: str,
        message_body: str,
        reply_email: str,
        user_id: int | None,
        user_name: str | None,
        organization_id: int | None,
        ip_address: str,
        user_agent: str,
        image: LaimContactImageRecord | None = None,
        id_estado: int = ESTADO_CASO_ABIERTO_ID,
    ) -> tuple[int, int | None]:
        """Inserta un caso (id = número de caso) y opcionalmente una imagen."""
        estado_id = id_estado if id_estado > 0 else ESTADO_CASO_ABIERTO_ID
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    f"""
                    INSERT INTO {CASOS_CONTACTO_TABLE} (
                        id_estado,
                        usage_mode,
                        affected_user_info,
                        message_body,
                        reply_email,
                        user_id,
                        user_name,
                        organization_id,
                        ip_address,
                        user_agent
                    ) VALUES (
                        :id_estado,
                        :usage_mode,
                        :affected_user_info,
                        :message_body,
                        :reply_email,
                        :user_id,
                        :user_name,
                        :organization_id,
                        :ip_address,
                        :user_agent
                    )
                    """
                ),
                {
                    "id_estado": estado_id,
                    "usage_mode": usage_mode,
                    "affected_user_info": affected_user_info or None,
                    "message_body": message_body,
                    "reply_email": reply_email,
                    "user_id": user_id,
                    "user_name": user_name,
                    "organization_id": organization_id,
                    "ip_address": ip_address or None,
                    "user_agent": user_agent or None,
                },
            )
            case_id = int(result.lastrowid)
            image_id: int | None = None

            if image is not None:
                img_result = conn.execute(
                    text(
                        f"""
                        INSERT INTO {CASOS_CONTACTO_IMAGENES_TABLE} (
                            id_caso,
                            file_name,
                            mime_type,
                            file_size,
                            image_data
                        ) VALUES (
                            :id_caso,
                            :file_name,
                            :mime_type,
                            :file_size,
                            :image_data
                        )
                        """
                    ),
                    {
                        "id_caso": case_id,
                        "file_name": image.file_name,
                        "mime_type": image.mime_type,
                        "file_size": image.file_size,
                        "image_data": image.image_data,
                    },
                )
                image_id = int(img_result.lastrowid)

            self._logger.info(
                "Caso de contacto creado numero_caso=%s id_estado=%s image_id=%s email=%s",
                case_id,
                estado_id,
                image_id,
                reply_email,
            )
            return case_id, image_id

    def get_message_by_id(self, message_id: int) -> dict[str, Any] | None:
        """Obtiene un caso por número (id)."""
        with self._engine.connect() as conn:
            row = self._fetch_case(conn, message_id, include_mobile=False)
        return row

    def list_messages(
        self,
        estado_clave: str | None = None,
        query: str | None = None,
        usage_mode: str | None = None,
        has_image: bool | None = None,
        has_user: bool | None = None,
        cursor_created_at: str | None = None,
        cursor_id: int | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Lista casos sin BLOB de captura, más recientes primero."""
        clauses = ["1=1"]
        params: dict[str, Any] = {"limit": max(1, min(int(limit), 200))}
        if estado_clave:
            estado_id = ESTADO_CLAVE_TO_ID.get(estado_clave.strip().lower())
            if estado_id is None:
                return []
            clauses.append("c.id_estado = :id_estado")
            params["id_estado"] = estado_id
        if usage_mode:
            clauses.append("c.usage_mode = :usage_mode")
            params["usage_mode"] = usage_mode
        if has_image is True:
            clauses.append(
                "EXISTS (SELECT 1 FROM casos_contacto_imagenes i WHERE i.id_caso = c.id)"
            )
        elif has_image is False:
            clauses.append(
                "NOT EXISTS (SELECT 1 FROM casos_contacto_imagenes i WHERE i.id_caso = c.id)"
            )
        if has_user is True:
            clauses.append("c.user_id IS NOT NULL")
        elif has_user is False:
            clauses.append("c.user_id IS NULL")
        if query:
            clauses.append(
                "("
                "c.reply_email LIKE :query OR "
                "c.user_name LIKE :query OR "
                "c.affected_user_info LIKE :query OR "
                "u.user_mobile LIKE :query"
                ")"
            )
            params["query"] = f"%{query.strip()}%"
        if cursor_created_at and cursor_id:
            clauses.append(
                "(c.created_at < :cursor_created_at OR "
                "(c.created_at = :cursor_created_at AND c.id < :cursor_id))"
            )
            params["cursor_created_at"] = cursor_created_at
            params["cursor_id"] = int(cursor_id)

        sql = f"""
            SELECT {_CASE_LIST_COLUMNS}
            FROM {CASOS_CONTACTO_TABLE} c
            INNER JOIN estados_casos_contacto e ON e.id = c.id_estado
            LEFT JOIN laim_users u ON u.user_id = c.user_id
            WHERE {' AND '.join(clauses)}
            ORDER BY c.created_at DESC, c.id DESC
            LIMIT :limit
        """
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().fetchall()
        return [dict(row) for row in rows]

    def get_with_image(self, message_id: int) -> dict[str, Any] | None:
        """Detalle de un caso incluyendo la captura si existe."""
        with self._engine.connect() as conn:
            case = self._fetch_case(conn, message_id, include_mobile=True)
            if case is None:
                return None
            image = conn.execute(
                text(
                    f"""
                    SELECT id, file_name, mime_type, file_size, image_data
                    FROM {CASOS_CONTACTO_IMAGENES_TABLE}
                    WHERE id_caso = :message_id
                    ORDER BY id ASC
                    LIMIT 1
                    """
                ),
                {"message_id": message_id},
            ).mappings().fetchone()
        if image:
            case["image"] = dict(image)
        else:
            case["image"] = None
        return case

    def update_estado(
        self, message_id: int, id_estado: int, actor: str
    ) -> dict[str, Any] | None:
        """Cambia el estado y registra auditoría. None si el caso no existe."""
        if id_estado not in ESTADO_CLAVE_TO_ID.values():
            raise ValueError(f"id_estado no válido: {id_estado}")
        actor_name = (actor or "").strip() or "laim_maintenance"
        with self._engine.begin() as conn:
            current = self._fetch_case(conn, message_id, include_mobile=False)
            if current is None:
                return None
            conn.execute(
                text(
                    f"""
                    UPDATE {CASOS_CONTACTO_TABLE}
                    SET id_estado = :id_estado
                    WHERE id = :message_id
                    """
                ),
                {"id_estado": id_estado, "message_id": message_id},
            )
            conn.execute(
                text(
                    f"""
                    INSERT INTO {CASOS_CONTACTO_AUDITORIA_TABLE} (
                        id_caso, estado_desde, estado_hasta, actor
                    ) VALUES (
                        :id_caso, :estado_desde, :estado_hasta, :actor
                    )
                    """
                ),
                {
                    "id_caso": message_id,
                    "estado_desde": current["id_estado"],
                    "estado_hasta": id_estado,
                    "actor": actor_name[:128],
                },
            )
            return self._fetch_case(conn, message_id, include_mobile=False)

    def replace_keywords(
        self, message_id: int, keywords: list[str], fuente: str = "ia"
    ) -> None:
        """Sustituye las etiquetas de un caso."""
        source = fuente if fuente in {"ia", "manual"} else "ia"
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in keywords:
            keyword = str(raw).strip().lower()[:80]
            if not keyword or keyword in seen:
                continue
            seen.add(keyword)
            cleaned.append(keyword)
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    f"DELETE FROM {CASOS_CONTACTO_ETIQUETAS_TABLE} WHERE id_caso = :id_caso"
                ),
                {"id_caso": message_id},
            )
            for keyword in cleaned:
                conn.execute(
                    text(
                        f"""
                        INSERT INTO {CASOS_CONTACTO_ETIQUETAS_TABLE} (
                            id_caso, keyword, fuente
                        ) VALUES (
                            :id_caso, :keyword, :fuente
                        )
                        """
                    ),
                    {"id_caso": message_id, "keyword": keyword, "fuente": source},
                )

    def list_audit(self, message_id: int) -> list[dict[str, Any]]:
        """Historial de cambios de estado de un caso."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT id, id_caso, estado_desde, estado_hasta, actor, creado_en
                    FROM {CASOS_CONTACTO_AUDITORIA_TABLE}
                    WHERE id_caso = :id_caso
                    ORDER BY creado_en ASC, id ASC
                    """
                ),
                {"id_caso": message_id},
            ).mappings().fetchall()
        return [dict(row) for row in rows]

    def list_replies(self, message_id: int) -> list[dict[str, Any]]:
        """Borradores y respuestas asociadas a un caso."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT id, id_caso, cuerpo, origen, estado, kb_candidata, creado_en
                    FROM {CASOS_CONTACTO_RESPUESTAS_TABLE}
                    WHERE id_caso = :id_caso
                    ORDER BY creado_en ASC, id ASC
                    """
                ),
                {"id_caso": message_id},
            ).mappings().fetchall()
        return [dict(row) for row in rows]

    def list_keywords(self, message_id: int) -> list[str]:
        """Keywords persistidas para un caso."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT keyword FROM {CASOS_CONTACTO_ETIQUETAS_TABLE}
                    WHERE id_caso = :id_caso
                    ORDER BY id ASC
                    """
                ),
                {"id_caso": message_id},
            ).mappings().fetchall()
        return [str(row["keyword"]) for row in rows]

    def _fetch_case(
        self, conn: Any, message_id: int, *, include_mobile: bool
    ) -> dict[str, Any] | None:
        columns = _CASE_DETAIL_COLUMNS if include_mobile else """
            c.id, c.id_estado, e.clave AS estado_clave, e.nombre AS estado_nombre,
            c.usage_mode, c.affected_user_info, c.message_body,
            c.reply_email, c.user_id, c.user_name, c.organization_id,
            c.created_at, c.updated_at
        """
        join_users = "LEFT JOIN laim_users u ON u.user_id = c.user_id" if include_mobile else ""
        row = conn.execute(
            text(
                f"""
                SELECT {columns}
                FROM {CASOS_CONTACTO_TABLE} c
                INNER JOIN estados_casos_contacto e ON e.id = c.id_estado
                {join_users}
                WHERE c.id = :message_id
                LIMIT 1
                """
            ),
            {"message_id": message_id},
        ).mappings().fetchone()
        return dict(row) if row else None
