"""Aplicación principal Reflex para LAIM Web."""

import importlib.util
from pathlib import Path

import reflex as rx
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from laim_web.forum_image_cache import fetch_forum_image
from laim_web.laim_state import LaimWebState
from laim_web.pages.forum import forum_page
from laim_web.pages.forum_admin import forum_admin_page
from laim_web.pages.forum_moderation import forum_moderation_page
from laim_web.pages.forum_profile import forum_profile_page
from laim_web.pages.index import index_page
from laim_web.pages.my_forum_posts import my_forum_posts_page
from laim_web.pages.my_forum_threads import my_forum_threads_page

_activity_logger_path = (
    Path(__file__).resolve().parents[3]
    / "2_shared_application"
    / "reflex_shared"
    / "activity_logger.py"
)
_activity_spec = importlib.util.spec_from_file_location(
    "activity_logger_laimweb", _activity_logger_path
)
if _activity_spec is not None and _activity_spec.loader is not None:
    _activity_module = importlib.util.module_from_spec(_activity_spec)
    _activity_spec.loader.exec_module(_activity_module)
    _activity_module.get_laimweb_logger().log_startup()

# Mismo patrón que frontend/backoffice: el root logger escribe en los
# ficheros montados en /data/frontend/laimweb/logs (console.log + activity.log).
import logging as std_logging
from logging.handlers import RotatingFileHandler

if not std_logging.getLogger().handlers:
    _logs_dir = Path(__file__).resolve().parent.parent / "logs"
    _logs_dir.mkdir(parents=True, exist_ok=True)
    _root_logger = std_logging.getLogger()
    _root_logger.setLevel(std_logging.INFO)
    _console_handler = RotatingFileHandler(
        _logs_dir / "console.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    _console_handler.setLevel(std_logging.INFO)
    _console_formatter = std_logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    _console_handler.setFormatter(_console_formatter)
    _root_logger.addHandler(_console_handler)
    _activity_handler = RotatingFileHandler(
        _logs_dir / "activity.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    _activity_handler.setLevel(std_logging.INFO)
    _activity_handler.setFormatter(_console_formatter)
    _root_logger.addHandler(_activity_handler)

app = rx.App(
    stylesheets=["/crt/crt_base.css", "/crt/crt_theme_green.css"],
    theme=rx.theme(
        appearance="dark",
    ),
)


async def _forum_image_proxy(request: Request) -> Response:
    """Proxy HTTP que sirve imágenes del foro con caché servidor."""
    image_id = int(request.path_params["image_id"])
    content, mime_type = fetch_forum_image(image_id)
    if not content:
        return Response(status_code=404, content=b"Not found")
    return Response(
        content=content,
        media_type=mime_type,
        headers={
            "Cache-Control": "public, max-age=3600, immutable",
            "X-Image-Cache": "hit-or-fetched",
        },
    )


app._api.routes.append(Route("/api/forum-img/{image_id:int}", _forum_image_proxy))

app.add_page(
    index_page,
    route="/",
    title="LAIM — Local AI Management",
    on_load=LaimWebState.on_page_load,
)

app.add_page(
    forum_page,
    route="/foro",
    title="Foro LAIM",
    on_load=LaimWebState.forum_on_page_load,
)

app.add_page(
    my_forum_threads_page,
    route="/mis-hilos-foro",
    title="Mis hilos — Foro LAIM",
    on_load=LaimWebState.forum_my_threads_on_load,
)

app.add_page(
    my_forum_posts_page,
    route="/mis-respuestas-foro",
    title="Mis respuestas — Foro LAIM",
    on_load=LaimWebState.forum_my_posts_on_load,
)

app.add_page(
    forum_admin_page,
    route="/config-foro",
    title="Config. foro — LAIM",
    on_load=LaimWebState.forum_admin_on_load,
)

app.add_page(
    forum_profile_page,
    route="/foro-perfil",
    title="Perfil foro — LAIM",
    on_load=LaimWebState.forum_profile_on_load,
)

app.add_page(
    forum_moderation_page,
    route="/foro-moderacion",
    title="Moderación foro — LAIM",
    on_load=LaimWebState.forum_mod_on_load,
)
