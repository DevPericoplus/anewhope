"""Repositorio MariaDB del foro LAIM Web.

Todo el contenido del foro (categorías, hilos, mensajes, ajustes, moderación,
etc.) se persiste exclusivamente en ``laim_core_db``. No hay ficheros JSON ni
adaptadores mock para datos del foro. Las imágenes adjuntas se guardan en
filesystem; sus metadatos están en ``laim_forum_images``.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

_logger = logging.getLogger("LaimForumRepository")

FORUM_IMAGE_URL_PREFIX = "/laim/forum/images"


def _bool_value(value: Any) -> bool:
    """Convierte valores MariaDB a bool."""
    if value is None:
        return False
    return bool(int(value)) if isinstance(value, (int, str)) else bool(value)


def _float_value(value: Any) -> float:
    """Convierte decimal/float a float Python."""
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _timestamp_value(value: Any) -> str:
    """Serializa timestamp para respuestas de la API."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _image_url(image_id: int) -> str:
    """Ruta pública relativa de imagen."""
    return f"{FORUM_IMAGE_URL_PREFIX}/{image_id}"


class LaimForumRepository:
    """Persistencia del subsistema foro en laim_core_db."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    # ------------------------------------------------------------------ imágenes
    def insert_image(
        self,
        *,
        image_kind: str,
        storage_key: str,
        file_name: str,
        mime_type: str,
        file_size: int,
        uploaded_by_user_id: int | None,
        checksum_sha256: str,
    ) -> int:
        """Inserta metadatos de imagen y retorna id."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO laim_forum_images (
                        image_kind, storage_key, file_name, mime_type,
                        file_size, uploaded_by_user_id, checksum_sha256, active
                    ) VALUES (
                        :image_kind, :storage_key, :file_name, :mime_type,
                        :file_size, :uploaded_by_user_id, :checksum_sha256, 1
                    )
                    """
                ),
                {
                    "image_kind": image_kind,
                    "storage_key": storage_key,
                    "file_name": file_name,
                    "mime_type": mime_type,
                    "file_size": file_size,
                    "uploaded_by_user_id": uploaded_by_user_id,
                    "checksum_sha256": checksum_sha256,
                },
            )
            image_id = int(result.lastrowid)
        _logger.info("Imagen foro registrada id=%s kind=%s", image_id, image_kind)
        return image_id

    def get_image_by_id(self, image_id: int) -> dict[str, Any] | None:
        """Obtiene metadatos de imagen activa."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, image_kind, storage_key, file_name, mime_type,
                           file_size, uploaded_by_user_id, checksum_sha256, active
                    FROM laim_forum_images
                    WHERE id = :id AND active = 1
                    """
                ),
                {"id": image_id},
            ).mappings().first()
        if row is None:
            return None
        data = dict(row)
        data["url_path"] = _image_url(int(data["id"]))
        return data

    def deactivate_image(self, image_id: int) -> bool:
        """Marca imagen como inactiva."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    "UPDATE laim_forum_images SET active = 0 WHERE id = :id AND active = 1"
                ),
                {"id": image_id},
            )
        return result.rowcount > 0

    def insert_avatar_catalog_item(
        self,
        *,
        image_id: int,
        label: str,
        is_default: bool = False,
        sort_order: int = 0,
    ) -> int:
        """Añade avatar al catálogo."""
        with self._engine.begin() as conn:
            if is_default:
                conn.execute(
                    text(
                        "UPDATE laim_forum_avatar_catalog SET is_default = 0 WHERE is_default = 1"
                    )
                )
            result = conn.execute(
                text(
                    """
                    INSERT INTO laim_forum_avatar_catalog (
                        image_id, label, is_default, sort_order, active
                    ) VALUES (:image_id, :label, :is_default, :sort_order, 1)
                    """
                ),
                {
                    "image_id": image_id,
                    "label": label,
                    "is_default": int(is_default),
                    "sort_order": sort_order,
                },
            )
            return int(result.lastrowid)

    def list_avatar_catalog(self, active_only: bool = True) -> list[dict[str, Any]]:
        """Lista catálogo de avatares con URL."""
        clause = "WHERE c.active = 1" if active_only else ""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT c.id, c.image_id, c.label, c.is_default, c.sort_order, c.active
                    FROM laim_forum_avatar_catalog c
                    {clause}
                    ORDER BY c.sort_order ASC, c.id ASC
                    """
                )
            ).mappings().all()
        items: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["is_default"] = _bool_value(item.get("is_default"))
            item["active"] = _bool_value(item.get("active"))
            item["url_path"] = _image_url(int(item["image_id"]))
            items.append(item)
        return items

    # -------------------------------------------------------------- perfil foro
    def get_user_forum(self, user_id: int) -> dict[str, Any] | None:
        """Obtiene perfil de foro del usuario."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT uf.user_id, u.user_name, uf.avatar_image_id,
                           uf.forum_display_name, uf.signature_md,
                           uf.reputation_avg, uf.reputation_votes,
                           uf.notify_mentions, uf.notify_replies
                    FROM laim_user_forum uf
                    INNER JOIN laim_users u ON u.user_id = uf.user_id
                    WHERE uf.user_id = :user_id
                    """
                ),
                {"user_id": user_id},
            ).mappings().first()
        if row is None:
            return None
        data = dict(row)
        data["reputation_avg"] = _float_value(data.get("reputation_avg"))
        data["notify_mentions"] = _bool_value(data.get("notify_mentions"))
        data["notify_replies"] = _bool_value(data.get("notify_replies"))
        avatar_id = data.get("avatar_image_id")
        data["avatar_url"] = _image_url(int(avatar_id)) if avatar_id else ""
        return data

    def ensure_user_forum(self, user_id: int) -> dict[str, Any]:
        """Crea perfil de foro si no existe y lo retorna."""
        existing = self.get_user_forum(user_id)
        if existing is not None:
            return existing
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO laim_user_forum (user_id)
                    VALUES (:user_id)
                    ON DUPLICATE KEY UPDATE user_id = user_id
                    """
                ),
                {"user_id": user_id},
            )
        profile = self.get_user_forum(user_id)
        if profile is None:
            raise RuntimeError(f"No se pudo crear perfil foro user_id={user_id}")
        return profile

    def update_user_forum(
        self,
        user_id: int,
        *,
        forum_display_name: str | None = None,
        signature_md: str | None = None,
        avatar_image_id: int | None = None,
        notify_mentions: bool | None = None,
        notify_replies: bool | None = None,
    ) -> dict[str, Any] | None:
        """Actualiza campos del perfil de foro."""
        self.ensure_user_forum(user_id)
        fields: list[str] = []
        params: dict[str, Any] = {"user_id": user_id}
        if forum_display_name is not None:
            fields.append("forum_display_name = :forum_display_name")
            params["forum_display_name"] = forum_display_name or None
        if signature_md is not None:
            fields.append("signature_md = :signature_md")
            params["signature_md"] = signature_md or None
        if avatar_image_id is not None:
            fields.append("avatar_image_id = :avatar_image_id")
            params["avatar_image_id"] = avatar_image_id if avatar_image_id > 0 else None
        if notify_mentions is not None:
            fields.append("notify_mentions = :notify_mentions")
            params["notify_mentions"] = int(notify_mentions)
        if notify_replies is not None:
            fields.append("notify_replies = :notify_replies")
            params["notify_replies"] = int(notify_replies)
        if not fields:
            return self.get_user_forum(user_id)
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    f"UPDATE laim_user_forum SET {', '.join(fields)} WHERE user_id = :user_id"
                ),
                params,
            )
        return self.get_user_forum(user_id)

    def recalculate_user_reputation(self, target_user_id: int) -> None:
        """Recalcula reputación media desde valoraciones."""
        with self._engine.begin() as conn:
            stats = conn.execute(
                text(
                    """
                    SELECT AVG(valoracion) AS avg_val, COUNT(*) AS total
                    FROM laim_forum_post_ratings
                    WHERE target_user_id = :user_id
                    """
                ),
                {"user_id": target_user_id},
            ).mappings().first()
            avg_val = _float_value(stats["avg_val"]) if stats else 0.0
            total = int(stats["total"] or 0) if stats else 0
            conn.execute(
                text(
                    """
                    INSERT INTO laim_user_forum (user_id, reputation_avg, reputation_votes)
                    VALUES (:user_id, :avg_val, :total)
                    ON DUPLICATE KEY UPDATE
                        reputation_avg = VALUES(reputation_avg),
                        reputation_votes = VALUES(reputation_votes)
                    """
                ),
                {"user_id": target_user_id, "avg_val": avg_val, "total": total},
            )

    # ------------------------------------------------------------ catálogo foro
    def list_categories(self, active_only: bool = True) -> list[dict[str, Any]]:
        """Lista categorías ordenadas."""
        clause = "WHERE activa = 1" if active_only else ""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT id, nombre, descripcion, orden, activa
                    FROM laim_forum_categories
                    {clause}
                    ORDER BY orden ASC, nombre ASC
                    """
                )
            ).mappings().all()
        return [
            {**dict(r), "activa": _bool_value(r["activa"])} for r in rows
        ]

    def upsert_category(
        self,
        *,
        category_id: str,
        nombre: str,
        descripcion: str = "",
        orden: int = 0,
        activa: bool = True,
    ) -> None:
        """Inserta o actualiza categoría."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO laim_forum_categories (id, nombre, descripcion, orden, activa)
                    VALUES (:id, :nombre, :descripcion, :orden, :activa)
                    ON DUPLICATE KEY UPDATE
                        nombre = VALUES(nombre),
                        descripcion = VALUES(descripcion),
                        orden = VALUES(orden),
                        activa = VALUES(activa)
                    """
                ),
                {
                    "id": category_id,
                    "nombre": nombre,
                    "descripcion": descripcion or None,
                    "orden": orden,
                    "activa": int(activa),
                },
            )

    def delete_category(self, category_id: str) -> bool:
        """Elimina categoría (cascade a subcategorías)."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text("DELETE FROM laim_forum_categories WHERE id = :id"),
                {"id": category_id},
            )
        return result.rowcount > 0

    def list_subcategories(
        self,
        *,
        category_id: str | None = None,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Lista subcategorías, opcionalmente filtradas por categoría."""
        conditions: list[str] = []
        params: dict[str, Any] = {}
        if category_id:
            conditions.append("categoria_id = :categoria_id")
            params["categoria_id"] = category_id
        if active_only:
            conditions.append("activa = 1")
        clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT id, categoria_id, nombre, descripcion, orden, activa,
                           ban_seconds, log_rotation
                    FROM laim_forum_subcategories
                    {clause}
                    ORDER BY orden ASC, nombre ASC
                    """
                ),
                params,
            ).mappings().all()
        return [
            {**dict(r), "activa": _bool_value(r["activa"])} for r in rows
        ]

    def upsert_subcategory(
        self,
        *,
        subcategory_id: str,
        categoria_id: str,
        nombre: str,
        descripcion: str = "",
        orden: int = 0,
        activa: bool = True,
        ban_seconds: int = 86400,
        log_rotation: str = "weekly",
    ) -> None:
        """Inserta o actualiza subcategoría."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO laim_forum_subcategories (
                        id, categoria_id, nombre, descripcion, orden, activa,
                        ban_seconds, log_rotation
                    ) VALUES (
                        :id, :categoria_id, :nombre, :descripcion, :orden, :activa,
                        :ban_seconds, :log_rotation
                    )
                    ON DUPLICATE KEY UPDATE
                        categoria_id = VALUES(categoria_id),
                        nombre = VALUES(nombre),
                        descripcion = VALUES(descripcion),
                        orden = VALUES(orden),
                        activa = VALUES(activa),
                        ban_seconds = VALUES(ban_seconds),
                        log_rotation = VALUES(log_rotation)
                    """
                ),
                {
                    "id": subcategory_id,
                    "categoria_id": categoria_id,
                    "nombre": nombre,
                    "descripcion": descripcion or None,
                    "orden": orden,
                    "activa": int(activa),
                    "ban_seconds": ban_seconds,
                    "log_rotation": log_rotation,
                },
            )

    def delete_subcategory(self, subcategory_id: str) -> bool:
        """Elimina subcategoría."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text("DELETE FROM laim_forum_subcategories WHERE id = :id"),
                {"id": subcategory_id},
            )
        return result.rowcount > 0

    def list_prefixes(self, active_only: bool = True) -> list[dict[str, Any]]:
        """Lista prefijos de hilo."""
        clause = "WHERE activo = 1" if active_only else ""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT id, texto, color_scheme, activo
                    FROM laim_forum_prefixes
                    {clause}
                    ORDER BY texto ASC
                    """
                )
            ).mappings().all()
        return [{**dict(r), "activo": _bool_value(r["activo"])} for r in rows]

    def upsert_prefix(
        self,
        *,
        prefix_id: str,
        texto: str,
        color_scheme: str = "green",
        activo: bool = True,
    ) -> None:
        """Inserta o actualiza prefijo."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO laim_forum_prefixes (id, texto, color_scheme, activo)
                    VALUES (:id, :texto, :color_scheme, :activo)
                    ON DUPLICATE KEY UPDATE
                        texto = VALUES(texto),
                        color_scheme = VALUES(color_scheme),
                        activo = VALUES(activo)
                    """
                ),
                {
                    "id": prefix_id,
                    "texto": texto,
                    "color_scheme": color_scheme,
                    "activo": int(activo),
                },
            )

    def delete_prefix(self, prefix_id: str) -> bool:
        """Elimina prefijo."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text("DELETE FROM laim_forum_prefixes WHERE id = :id"),
                {"id": prefix_id},
            )
        return result.rowcount > 0

    # ----------------------------------------------------------- hilos y posts
    def _link_thread_images(
        self, conn: Any, thread_id: int, image_ids: list[int]
    ) -> None:
        """Asocia imágenes a un hilo."""
        for index, image_id in enumerate(image_ids):
            conn.execute(
                text(
                    """
                    INSERT INTO laim_forum_thread_images (thread_id, image_id, sort_order)
                    VALUES (:thread_id, :image_id, :sort_order)
                    """
                ),
                {"thread_id": thread_id, "image_id": image_id, "sort_order": index},
            )

    def _link_post_images(self, conn: Any, post_id: int, image_ids: list[int]) -> None:
        """Asocia imágenes a una respuesta."""
        for index, image_id in enumerate(image_ids):
            conn.execute(
                text(
                    """
                    INSERT INTO laim_forum_post_images (post_id, image_id, sort_order)
                    VALUES (:post_id, :image_id, :sort_order)
                    """
                ),
                {"post_id": post_id, "image_id": image_id, "sort_order": index},
            )

    def create_thread(
        self,
        *,
        subcategory_id: str,
        prefix_id: str | None,
        titulo: str,
        user_id: int,
        user_name: str,
        cuerpo_md: str,
        image_ids: list[int] | None = None,
    ) -> int:
        """Crea hilo con adjuntos opcionales."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO laim_forum_threads (
                        subcategory_id, prefix_id, titulo, user_id, user_name, cuerpo_md
                    ) VALUES (
                        :subcategory_id, :prefix_id, :titulo, :user_id, :user_name, :cuerpo_md
                    )
                    """
                ),
                {
                    "subcategory_id": subcategory_id,
                    "prefix_id": prefix_id or None,
                    "titulo": titulo,
                    "user_id": user_id,
                    "user_name": user_name,
                    "cuerpo_md": cuerpo_md,
                },
            )
            thread_id = int(result.lastrowid)
            if image_ids:
                self._link_thread_images(conn, thread_id, image_ids)
        return thread_id

    def update_thread(
        self,
        thread_id: int,
        *,
        titulo: str | None = None,
        cuerpo_md: str | None = None,
        prefix_id: str | None = None,
        fijado: bool | None = None,
        cerrado: bool | None = None,
        image_ids: list[int] | None = None,
    ) -> bool:
        """Actualiza hilo y opcionalmente reemplaza adjuntos."""
        fields: list[str] = []
        params: dict[str, Any] = {"id": thread_id}
        if titulo is not None:
            fields.append("titulo = :titulo")
            params["titulo"] = titulo
        if cuerpo_md is not None:
            fields.append("cuerpo_md = :cuerpo_md")
            params["cuerpo_md"] = cuerpo_md
        if prefix_id is not None:
            fields.append("prefix_id = :prefix_id")
            params["prefix_id"] = prefix_id or None
        if fijado is not None:
            fields.append("fijado = :fijado")
            params["fijado"] = int(fijado)
        if cerrado is not None:
            fields.append("cerrado = :cerrado")
            params["cerrado"] = int(cerrado)
        with self._engine.begin() as conn:
            if fields:
                conn.execute(
                    text(
                        f"""
                        UPDATE laim_forum_threads
                        SET {', '.join(fields)}
                        WHERE id = :id AND deleted = 0
                        """
                    ),
                    params,
                )
            if image_ids is not None:
                conn.execute(
                    text("DELETE FROM laim_forum_thread_images WHERE thread_id = :id"),
                    {"id": thread_id},
                )
                if image_ids:
                    self._link_thread_images(conn, thread_id, image_ids)
        return True

    def soft_delete_thread(self, thread_id: int) -> bool:
        """Marca hilo como eliminado."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    "UPDATE laim_forum_threads SET deleted = 1 WHERE id = :id AND deleted = 0"
                ),
                {"id": thread_id},
            )
        return result.rowcount > 0

    def get_thread(self, thread_id: int, include_deleted: bool = False) -> dict[str, Any] | None:
        """Obtiene hilo con metadatos."""
        deleted_clause = "" if include_deleted else "AND t.deleted = 0"
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    f"""
                    SELECT t.id, t.subcategory_id, t.prefix_id, t.titulo,
                           t.user_id, t.user_name, t.cuerpo_md,
                           t.fijado, t.cerrado, t.deleted,
                           t.created_at, t.updated_at
                    FROM laim_forum_threads t
                    WHERE t.id = :id {deleted_clause}
                    """
                ),
                {"id": thread_id},
            ).mappings().first()
        if row is None:
            return None
        data = dict(row)
        data["fijado"] = _bool_value(data.get("fijado"))
        data["cerrado"] = _bool_value(data.get("cerrado"))
        data["deleted"] = _bool_value(data.get("deleted"))
        data["created_at"] = _timestamp_value(data.get("created_at"))
        data["updated_at"] = _timestamp_value(data.get("updated_at"))
        data["image_ids"] = self.list_thread_image_ids(thread_id)
        return data

    def list_threads_by_subcategory(
        self, subcategory_id: str, *, include_deleted: bool = False
    ) -> list[dict[str, Any]]:
        """Lista hilos de una subcategoría."""
        deleted_clause = "" if include_deleted else "AND deleted = 0"
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT id, subcategory_id, prefix_id, titulo, user_id, user_name,
                           fijado, cerrado, deleted, created_at, updated_at
                    FROM laim_forum_threads
                    WHERE subcategory_id = :subcategory_id {deleted_clause}
                    ORDER BY fijado DESC, updated_at DESC
                    """
                ),
                {"subcategory_id": subcategory_id},
            ).mappings().all()
        items: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["fijado"] = _bool_value(item.get("fijado"))
            item["cerrado"] = _bool_value(item.get("cerrado"))
            item["deleted"] = _bool_value(item.get("deleted"))
            item["created_at"] = _timestamp_value(item.get("created_at"))
            item["updated_at"] = _timestamp_value(item.get("updated_at"))
            items.append(item)
        return items

    def list_threads_by_user(
        self, user_id: int, *, include_deleted: bool = False
    ) -> list[dict[str, Any]]:
        """Lista hilos creados por un usuario."""
        deleted_clause = "" if include_deleted else "AND deleted = 0"
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT id, subcategory_id, prefix_id, titulo, user_id, user_name,
                           fijado, cerrado, deleted, created_at, updated_at
                    FROM laim_forum_threads
                    WHERE user_id = :user_id {deleted_clause}
                    ORDER BY updated_at DESC
                    """
                ),
                {"user_id": user_id},
            ).mappings().all()
        return [
            {
                **dict(r),
                "fijado": _bool_value(r.get("fijado")),
                "cerrado": _bool_value(r.get("cerrado")),
                "deleted": _bool_value(r.get("deleted")),
                "created_at": _timestamp_value(r.get("created_at")),
                "updated_at": _timestamp_value(r.get("updated_at")),
            }
            for r in rows
        ]

    def list_thread_image_ids(self, thread_id: int) -> list[int]:
        """IDs de imágenes adjuntas a un hilo."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT image_id FROM laim_forum_thread_images
                    WHERE thread_id = :thread_id
                    ORDER BY sort_order ASC
                    """
                ),
                {"thread_id": thread_id},
            ).all()
        return [int(r[0]) for r in rows]

    def create_post(
        self,
        *,
        thread_id: int,
        user_id: int,
        user_name: str,
        cuerpo_md: str,
        image_ids: list[int] | None = None,
    ) -> int:
        """Crea respuesta en un hilo."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO laim_forum_posts (thread_id, user_id, user_name, cuerpo_md)
                    VALUES (:thread_id, :user_id, :user_name, :cuerpo_md)
                    """
                ),
                {
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "user_name": user_name,
                    "cuerpo_md": cuerpo_md,
                },
            )
            post_id = int(result.lastrowid)
            conn.execute(
                text(
                    "UPDATE laim_forum_threads SET updated_at = CURRENT_TIMESTAMP WHERE id = :id"
                ),
                {"id": thread_id},
            )
            if image_ids:
                self._link_post_images(conn, post_id, image_ids)
        return post_id

    def update_post(
        self,
        post_id: int,
        *,
        cuerpo_md: str,
        image_ids: list[int] | None = None,
    ) -> bool:
        """Actualiza respuesta."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE laim_forum_posts
                    SET cuerpo_md = :cuerpo_md
                    WHERE id = :id AND deleted = 0
                    """
                ),
                {"id": post_id, "cuerpo_md": cuerpo_md},
            )
            if image_ids is not None:
                conn.execute(
                    text("DELETE FROM laim_forum_post_images WHERE post_id = :id"),
                    {"id": post_id},
                )
                if image_ids:
                    self._link_post_images(conn, post_id, image_ids)
        return True

    def soft_delete_post(self, post_id: int) -> bool:
        """Marca respuesta como eliminada."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    "UPDATE laim_forum_posts SET deleted = 1 WHERE id = :id AND deleted = 0"
                ),
                {"id": post_id},
            )
        return result.rowcount > 0

    def get_post(self, post_id: int, include_deleted: bool = False) -> dict[str, Any] | None:
        """Obtiene respuesta."""
        deleted_clause = "" if include_deleted else "AND deleted = 0"
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    f"""
                    SELECT id, thread_id, user_id, user_name, cuerpo_md, deleted,
                           created_at, updated_at
                    FROM laim_forum_posts
                    WHERE id = :id {deleted_clause}
                    """
                ),
                {"id": post_id},
            ).mappings().first()
        if row is None:
            return None
        data = dict(row)
        data["deleted"] = _bool_value(data.get("deleted"))
        data["created_at"] = _timestamp_value(data.get("created_at"))
        data["updated_at"] = _timestamp_value(data.get("updated_at"))
        data["image_ids"] = self.list_post_image_ids(post_id)
        return data

    def list_posts_by_thread(
        self, thread_id: int, *, include_deleted: bool = False
    ) -> list[dict[str, Any]]:
        """Lista respuestas de un hilo."""
        deleted_clause = "" if include_deleted else "AND deleted = 0"
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT id, thread_id, user_id, user_name, cuerpo_md, deleted,
                           created_at, updated_at
                    FROM laim_forum_posts
                    WHERE thread_id = :thread_id {deleted_clause}
                    ORDER BY created_at ASC
                    """
                ),
                {"thread_id": thread_id},
            ).mappings().all()
        return [
            {
                **dict(r),
                "deleted": _bool_value(r.get("deleted")),
                "created_at": _timestamp_value(r.get("created_at")),
                "updated_at": _timestamp_value(r.get("updated_at")),
                "image_ids": self.list_post_image_ids(int(r["id"])),
            }
            for r in rows
        ]

    def list_posts_by_user(
        self, user_id: int, *, include_deleted: bool = False
    ) -> list[dict[str, Any]]:
        """Lista respuestas de un usuario."""
        deleted_clause = "" if include_deleted else "AND deleted = 0"
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT id, thread_id, user_id, user_name, cuerpo_md, deleted,
                           created_at, updated_at
                    FROM laim_forum_posts
                    WHERE user_id = :user_id {deleted_clause}
                    ORDER BY created_at DESC
                    """
                ),
                {"user_id": user_id},
            ).mappings().all()
        return [
            {
                **dict(r),
                "deleted": _bool_value(r.get("deleted")),
                "created_at": _timestamp_value(r.get("created_at")),
                "updated_at": _timestamp_value(r.get("updated_at")),
            }
            for r in rows
        ]

    def list_post_image_ids(self, post_id: int) -> list[int]:
        """IDs de imágenes adjuntas a una respuesta."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT image_id FROM laim_forum_post_images
                    WHERE post_id = :post_id
                    ORDER BY sort_order ASC
                    """
                ),
                {"post_id": post_id},
            ).all()
        return [int(r[0]) for r in rows]

    # ---------------------------------------------------------- moderación/config
    def get_settings(self) -> dict[str, Any]:
        """Obtiene configuración singleton."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT anunciar_ban_en_log, plantilla_ban, plantilla_eliminacion
                    FROM laim_forum_settings WHERE id = 1
                    """
                )
            ).mappings().first()
        if row is None:
            return {
                "anunciar_ban_en_log": True,
                "plantilla_ban": "",
                "plantilla_eliminacion": "",
            }
        return {
            **dict(row),
            "anunciar_ban_en_log": _bool_value(row.get("anunciar_ban_en_log")),
        }

    def update_settings(
        self,
        *,
        anunciar_ban_en_log: bool | None = None,
        plantilla_ban: str | None = None,
        plantilla_eliminacion: str | None = None,
    ) -> dict[str, Any]:
        """Actualiza configuración singleton."""
        fields: list[str] = []
        params: dict[str, Any] = {"id": 1}
        if anunciar_ban_en_log is not None:
            fields.append("anunciar_ban_en_log = :anunciar_ban_en_log")
            params["anunciar_ban_en_log"] = int(anunciar_ban_en_log)
        if plantilla_ban is not None:
            fields.append("plantilla_ban = :plantilla_ban")
            params["plantilla_ban"] = plantilla_ban
        if plantilla_eliminacion is not None:
            fields.append("plantilla_eliminacion = :plantilla_eliminacion")
            params["plantilla_eliminacion"] = plantilla_eliminacion
        if fields:
            with self._engine.begin() as conn:
                conn.execute(
                    text(
                        f"""
                        UPDATE laim_forum_settings SET {', '.join(fields)} WHERE id = :id
                        """
                    ),
                    params,
                )
        return self.get_settings()

    def list_moderators(
        self, *, subcategory_id: str | None = None, active_only: bool = True
    ) -> list[dict[str, Any]]:
        """Lista moderadores."""
        conditions: list[str] = []
        params: dict[str, Any] = {}
        if subcategory_id:
            conditions.append("subcategory_id = :subcategory_id")
            params["subcategory_id"] = subcategory_id
        if active_only:
            conditions.append("activo = 1")
        clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT id, user_id, user_name, subcategory_id, activo
                    FROM laim_forum_moderators
                    {clause}
                    ORDER BY subcategory_id, user_name
                    """
                ),
                params,
            ).mappings().all()
        return [{**dict(r), "activo": _bool_value(r["activo"])} for r in rows]

    def assign_moderator(
        self, *, user_id: int, user_name: str, subcategory_id: str
    ) -> int:
        """Asigna moderador (reactiva si ya existía)."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO laim_forum_moderators (
                        user_id, user_name, subcategory_id, activo
                    ) VALUES (:user_id, :user_name, :subcategory_id, 1)
                    ON DUPLICATE KEY UPDATE
                        user_name = VALUES(user_name),
                        activo = 1
                    """
                ),
                {
                    "user_id": user_id,
                    "user_name": user_name,
                    "subcategory_id": subcategory_id,
                },
            )
            if result.lastrowid:
                return int(result.lastrowid)
            row = conn.execute(
                text(
                    """
                    SELECT id FROM laim_forum_moderators
                    WHERE user_id = :user_id AND subcategory_id = :subcategory_id
                    """
                ),
                {"user_id": user_id, "subcategory_id": subcategory_id},
            ).first()
        return int(row[0]) if row else 0

    def deactivate_moderator(self, moderator_id: int) -> bool:
        """Desactiva moderador."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    "UPDATE laim_forum_moderators SET activo = 0 WHERE id = :id AND activo = 1"
                ),
                {"id": moderator_id},
            )
        return result.rowcount > 0

    def is_moderator(self, user_id: int, subcategory_id: str) -> bool:
        """Indica si el usuario es moderador activo."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT 1 FROM laim_forum_moderators
                    WHERE user_id = :user_id AND subcategory_id = :subcategory_id AND activo = 1
                    LIMIT 1
                    """
                ),
                {"user_id": user_id, "subcategory_id": subcategory_id},
            ).first()
        return row is not None

    def list_word_rules(self, active_only: bool = True) -> list[dict[str, Any]]:
        """Lista reglas de palabras."""
        clause = "WHERE activo = 1" if active_only else ""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT id, palabra, accion, mensaje, activo
                    FROM laim_forum_word_rules
                    {clause}
                    ORDER BY palabra ASC
                    """
                )
            ).mappings().all()
        return [{**dict(r), "activo": _bool_value(r["activo"])} for r in rows]

    def upsert_word_rule(
        self,
        *,
        rule_id: int | None,
        palabra: str,
        accion: str,
        mensaje: str = "",
        activo: bool = True,
    ) -> int:
        """Inserta o actualiza regla de palabra."""
        with self._engine.begin() as conn:
            if rule_id and rule_id > 0:
                conn.execute(
                    text(
                        """
                        UPDATE laim_forum_word_rules
                        SET palabra = :palabra, accion = :accion,
                            mensaje = :mensaje, activo = :activo
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": rule_id,
                        "palabra": palabra,
                        "accion": accion,
                        "mensaje": mensaje or None,
                        "activo": int(activo),
                    },
                )
                return rule_id
            result = conn.execute(
                text(
                    """
                    INSERT INTO laim_forum_word_rules (palabra, accion, mensaje, activo)
                    VALUES (:palabra, :accion, :mensaje, :activo)
                    """
                ),
                {
                    "palabra": palabra,
                    "accion": accion,
                    "mensaje": mensaje or None,
                    "activo": int(activo),
                },
            )
            return int(result.lastrowid)

    def delete_word_rule(self, rule_id: int) -> bool:
        """Elimina regla de palabra."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text("DELETE FROM laim_forum_word_rules WHERE id = :id"),
                {"id": rule_id},
            )
        return result.rowcount > 0

    def list_allowed_urls(self, active_only: bool = True) -> list[dict[str, Any]]:
        """Lista dominios permitidos."""
        clause = "WHERE activo = 1" if active_only else ""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT id, dominio, descripcion, activo
                    FROM laim_forum_allowed_urls
                    {clause}
                    ORDER BY dominio ASC
                    """
                )
            ).mappings().all()
        return [{**dict(r), "activo": _bool_value(r["activo"])} for r in rows]

    def upsert_allowed_url(
        self,
        *,
        url_id: int | None,
        dominio: str,
        descripcion: str = "",
        activo: bool = True,
    ) -> int:
        """Inserta o actualiza dominio permitido."""
        with self._engine.begin() as conn:
            if url_id and url_id > 0:
                conn.execute(
                    text(
                        """
                        UPDATE laim_forum_allowed_urls
                        SET dominio = :dominio, descripcion = :descripcion, activo = :activo
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": url_id,
                        "dominio": dominio,
                        "descripcion": descripcion or None,
                        "activo": int(activo),
                    },
                )
                return url_id
            result = conn.execute(
                text(
                    """
                    INSERT INTO laim_forum_allowed_urls (dominio, descripcion, activo)
                    VALUES (:dominio, :descripcion, :activo)
                    ON DUPLICATE KEY UPDATE
                        descripcion = VALUES(descripcion),
                        activo = VALUES(activo)
                    """
                ),
                {
                    "dominio": dominio,
                    "descripcion": descripcion or None,
                    "activo": int(activo),
                },
            )
            if result.lastrowid:
                return int(result.lastrowid)
            row = conn.execute(
                text("SELECT id FROM laim_forum_allowed_urls WHERE dominio = :dominio"),
                {"dominio": dominio},
            ).first()
        return int(row[0]) if row else 0

    def delete_allowed_url(self, url_id: int) -> bool:
        """Elimina dominio permitido."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text("DELETE FROM laim_forum_allowed_urls WHERE id = :id"),
                {"id": url_id},
            )
        return result.rowcount > 0

    def is_user_banned(self, user_id: int, subcategory_id: str) -> bool:
        """Comprueba baneo activo (no expirado)."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT 1 FROM laim_forum_bans
                    WHERE user_id = :user_id
                      AND subcategory_id = :subcategory_id
                      AND activo = 1
                      AND (expires_at IS NULL OR expires_at > NOW())
                    LIMIT 1
                    """
                ),
                {"user_id": user_id, "subcategory_id": subcategory_id},
            ).first()
        return row is not None

    def create_ban(
        self,
        *,
        user_id: int,
        subcategory_id: str,
        motivo: str,
        moderador_user_id: int | None = None,
        moderador_user_name: str | None = None,
        expires_at: datetime | None = None,
        automatico: bool = False,
    ) -> int:
        """Registra baneo activo."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE laim_forum_bans
                    SET activo = 0, revocado_at = NOW()
                    WHERE user_id = :user_id
                      AND subcategory_id = :subcategory_id
                      AND activo = 1
                    """
                ),
                {"user_id": user_id, "subcategory_id": subcategory_id},
            )
            result = conn.execute(
                text(
                    """
                    INSERT INTO laim_forum_bans (
                        user_id, subcategory_id, motivo,
                        moderador_user_id, moderador_user_name,
                        expires_at, activo, automatico
                    ) VALUES (
                        :user_id, :subcategory_id, :motivo,
                        :moderador_user_id, :moderador_user_name,
                        :expires_at, 1, :automatico
                    )
                    """
                ),
                {
                    "user_id": user_id,
                    "subcategory_id": subcategory_id,
                    "motivo": motivo,
                    "moderador_user_id": moderador_user_id,
                    "moderador_user_name": moderador_user_name,
                    "expires_at": expires_at,
                    "automatico": int(automatico),
                },
            )
            return int(result.lastrowid)

    def revoke_ban(self, ban_id: int, revocado_por_user_id: int) -> bool:
        """Revoca baneo."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE laim_forum_bans
                    SET activo = 0, revocado_por_user_id = :revocado_por,
                        revocado_at = NOW()
                    WHERE id = :id AND activo = 1
                    """
                ),
                {"id": ban_id, "revocado_por": revocado_por_user_id},
            )
        return result.rowcount > 0

    def add_infraction(
        self, *, user_id: int, subcategory_id: str, tipo: str, strikes: int = 1
    ) -> int:
        """Registra infracción."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO laim_forum_infractions (
                        user_id, subcategory_id, tipo, strikes
                    ) VALUES (:user_id, :subcategory_id, :tipo, :strikes)
                    """
                ),
                {
                    "user_id": user_id,
                    "subcategory_id": subcategory_id,
                    "tipo": tipo,
                    "strikes": strikes,
                },
            )
            return int(result.lastrowid)

    def count_strikes(self, user_id: int, subcategory_id: str) -> int:
        """Suma strikes acumulados en subcategoría."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT COALESCE(SUM(strikes), 0) AS total
                    FROM laim_forum_infractions
                    WHERE user_id = :user_id AND subcategory_id = :subcategory_id
                    """
                ),
                {"user_id": user_id, "subcategory_id": subcategory_id},
            ).first()
        return int(row[0]) if row else 0

    # ---------------------------------------------------- notificaciones/ratings
    def create_notification(
        self,
        *,
        user_id: int,
        tipo: str,
        titulo: str,
        mensaje: str,
        category_id: str | None = None,
        subcategory_id: str | None = None,
        thread_id: int | None = None,
        post_id: int | None = None,
    ) -> int:
        """Crea notificación pendiente."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO laim_forum_notifications (
                        user_id, tipo, titulo, mensaje,
                        category_id, subcategory_id, thread_id, post_id, entregada
                    ) VALUES (
                        :user_id, :tipo, :titulo, :mensaje,
                        :category_id, :subcategory_id, :thread_id, :post_id, 0
                    )
                    """
                ),
                {
                    "user_id": user_id,
                    "tipo": tipo,
                    "titulo": titulo,
                    "mensaje": mensaje,
                    "category_id": category_id,
                    "subcategory_id": subcategory_id,
                    "thread_id": thread_id,
                    "post_id": post_id,
                },
            )
            return int(result.lastrowid)

    def list_pending_notifications(self, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        """Lista notificaciones no entregadas."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, tipo, titulo, mensaje, category_id, subcategory_id,
                           thread_id, post_id, created_at
                    FROM laim_forum_notifications
                    WHERE user_id = :user_id AND entregada = 0
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {"user_id": user_id, "limit": limit},
            ).mappings().all()
        return [
            {**dict(r), "created_at": _timestamp_value(r.get("created_at"))} for r in rows
        ]

    def mark_notifications_delivered(self, user_id: int, notification_ids: list[int]) -> int:
        """Marca notificaciones como entregadas."""
        if not notification_ids:
            return 0
        placeholders = ", ".join(f":id_{i}" for i in range(len(notification_ids)))
        params: dict[str, Any] = {"user_id": user_id}
        for index, notification_id in enumerate(notification_ids):
            params[f"id_{index}"] = notification_id
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    f"""
                    UPDATE laim_forum_notifications
                    SET entregada = 1
                    WHERE user_id = :user_id AND id IN ({placeholders})
                    """
                ),
                params,
            )
        return int(result.rowcount)

    def upsert_post_rating(
        self,
        *,
        post_id: int,
        user_id: int,
        target_user_id: int,
        valoracion: int,
    ) -> None:
        """Inserta o actualiza valoración 1-5."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO laim_forum_post_ratings (
                        post_id, user_id, target_user_id, valoracion
                    ) VALUES (:post_id, :user_id, :target_user_id, :valoracion)
                    ON DUPLICATE KEY UPDATE valoracion = VALUES(valoracion)
                    """
                ),
                {
                    "post_id": post_id,
                    "user_id": user_id,
                    "target_user_id": target_user_id,
                    "valoracion": valoracion,
                },
            )
        self.recalculate_user_reputation(target_user_id)

    def insert_moderation_log(
        self,
        *,
        subcategory_id: str,
        event_type: str,
        message: str,
        user_id: int | None = None,
        user_name: str | None = None,
        moderator_user_id: int | None = None,
        moderator_user_name: str | None = None,
        thread_id: int | None = None,
        post_id: int | None = None,
    ) -> int:
        """Registra evento en log de moderación."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO laim_forum_moderation_logs (
                        subcategory_id, event_type, user_id, user_name,
                        moderator_user_id, moderator_user_name,
                        thread_id, post_id, message
                    ) VALUES (
                        :subcategory_id, :event_type, :user_id, :user_name,
                        :moderator_user_id, :moderator_user_name,
                        :thread_id, :post_id, :message
                    )
                    """
                ),
                {
                    "subcategory_id": subcategory_id,
                    "event_type": event_type,
                    "user_id": user_id,
                    "user_name": user_name,
                    "moderator_user_id": moderator_user_id,
                    "moderator_user_name": moderator_user_name,
                    "thread_id": thread_id,
                    "post_id": post_id,
                    "message": message,
                },
            )
            return int(result.lastrowid)

    def list_moderation_logs(
        self, subcategory_id: str, *, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Lista logs recientes de una subcategoría."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, subcategory_id, event_type, user_id, user_name,
                           moderator_user_id, moderator_user_name,
                           thread_id, post_id, message, created_at
                    FROM laim_forum_moderation_logs
                    WHERE subcategory_id = :subcategory_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {"subcategory_id": subcategory_id, "limit": limit},
            ).mappings().all()
        return [
            {**dict(r), "created_at": _timestamp_value(r.get("created_at"))} for r in rows
        ]

    def get_health_stats(self) -> dict[str, int]:
        """Contadores básicos para health check."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM laim_forum_categories) AS categorias,
                        (SELECT COUNT(*) FROM laim_forum_subcategories) AS subcategorias,
                        (SELECT COUNT(*) FROM laim_forum_threads WHERE deleted = 0) AS hilos,
                        (SELECT COUNT(*) FROM laim_forum_posts WHERE deleted = 0) AS respuestas
                    """
                )
            ).mappings().first()
        if row is None:
            return {"categorias": 0, "subcategorias": 0, "hilos": 0, "respuestas": 0}
        return {key: int(row[key] or 0) for key in row.keys()}
