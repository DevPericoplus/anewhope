"""Aplicación principal Reflex para LAIM Web."""

import importlib.util
from pathlib import Path

import reflex as rx
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from laim_web.forum_image_cache import fetch_forum_image
from laim_web.laim_state import LaimWebState
from laim_web.product_cache import FetchedArtifact, ProductCacheError, ProductFileCache
from laim_web.adapters.laim_api_client import ProductFetchError, fetch_laim_product_binary
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


# ============================================================================
# Caché de instaladores/parches de laim y sus plugins — ver
# anewhope/AGENTS.md § 37.3. LAIM_READER_DSN: mismas credenciales
# laim_reader de solo lectura ya desplegadas para middleware (ver
# routermiddleware.py._wrap_with_laim_session_repository) — si no está
# configurada, la caché sigue sirviendo (product_cache.py degrada a
# "siempre re-fetch"), nunca sirve una copia sin poder verificarla.
# ============================================================================

_product_cache_dir = Path(
    __import__("os").environ.get(
        "LAIM_PRODUCT_CACHE_DIR",
        str(Path(__file__).resolve().parent.parent / "product_cache"),
    )
)

_checksum_repo_for_cache = None
_checksum_repo_init_attempted = False


def _get_product_checksum_repo():
    """Repositorio de checksums de solo lectura, construido una sola vez.
    None si LAIM_READER_DSN no está configurada o la conexión falla —
    product_cache.py trata None como "no puedo verificar", nunca como luz
    verde implícita."""
    global _checksum_repo_for_cache, _checksum_repo_init_attempted
    if _checksum_repo_init_attempted:
        return _checksum_repo_for_cache
    _checksum_repo_init_attempted = True

    import os as _os
    reader_dsn = _os.environ.get("LAIM_READER_DSN", "").strip()
    if not reader_dsn:
        std_logging.getLogger(__name__).warning(
            "LAIM_READER_DSN no configurada — la caché de product_cache no podrá "
            "verificar copias existentes, siempre volverá a pedirlas a middleware."
        )
        return None
    try:
        _checksum_mod_path = (
            Path(__file__).resolve().parents[3]
            / "2_shared_application" / "adapters" / "product_file_checksum.py"
        )
        _checksum_spec = importlib.util.spec_from_file_location(
            "product_file_checksum_laimweb", _checksum_mod_path
        )
        _checksum_mod = importlib.util.module_from_spec(_checksum_spec)
        _checksum_spec.loader.exec_module(_checksum_mod)

        _session_repo_mod_path = (
            Path(__file__).resolve().parents[3]
            / "2_shared_application" / "adapters" / "laim_mariadb_session_repository.py"
        )
        _session_repo_spec = importlib.util.spec_from_file_location(
            "laim_mariadb_session_repository_laimweb", _session_repo_mod_path
        )
        _session_repo_mod = importlib.util.module_from_spec(_session_repo_spec)
        _session_repo_spec.loader.exec_module(_session_repo_mod)

        engine = _session_repo_mod.create_laim_session_engine(
            {"reader_dsn": reader_dsn}, role="reader"
        )
        _checksum_repo_for_cache = _checksum_mod.ProductFileChecksumRepository(engine)
        std_logging.getLogger(__name__).info(
            "[DDD] Repositorio de checksums de product_cache inicializado (solo lectura)"
        )
    except Exception as exc:  # noqa: BLE001 - degradar, nunca romper el arranque de laimweb
        std_logging.getLogger(__name__).warning(
            "No se pudo inicializar el repositorio de checksums de product_cache: %s", exc
        )
        _checksum_repo_for_cache = None
    return _checksum_repo_for_cache


_product_file_cache = ProductFileCache(_product_cache_dir, checksum_repo=None)


async def _product_cache_download(request: Request) -> Response:
    """Sirve un artefacto laim_product desde la caché en disco de laimweb,
    verificando su integridad antes de servirlo — ver product_cache.py."""
    params = request.query_params
    edition = params.get("edition", "")
    artifact_type = params.get("artifact_type", "")
    platform = params.get("platform", "")
    version = params.get("version", "")
    filename = params.get("filename", "")
    plugin_name = params.get("plugin_name", "")

    if not all([edition, artifact_type, platform, version, filename]):
        return Response(status_code=400, content=b"Parametros requeridos faltantes")

    _product_file_cache._checksum_repo = _get_product_checksum_repo()  # type: ignore[attr-defined]

    def fetch_fn() -> FetchedArtifact:
        content, sha256 = fetch_laim_product_binary(
            edition, artifact_type, platform, version, filename, plugin_name
        )
        return FetchedArtifact(content=content, sha256=sha256)

    try:
        cached_path = _product_file_cache.get_or_fetch(
            edition, artifact_type, platform, version, filename, fetch_fn, plugin_name
        )
    except ProductFetchError as exc:
        return Response(status_code=502, content=str(exc).encode("utf-8"))
    except ProductCacheError as exc:
        return Response(status_code=500, content=str(exc).encode("utf-8"))

    return Response(
        content=cached_path.read_bytes(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


app._api.routes.append(Route("/api/product-cache/download", _product_cache_download))

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
