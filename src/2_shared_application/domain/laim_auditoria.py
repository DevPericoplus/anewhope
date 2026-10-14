"""Constantes de auditoría de uso del portal laimweb."""

from __future__ import annotations

USUARIO_ACCIONES = frozenset({"alta", "login", "logout", "login_fallido", "bloqueo"})
INSTALADOR_ACCIONES = frozenset({"copia_script", "script_http", "descarga"})
FORO_ACCIONES = frozenset({"crear_hilo", "crear_respuesta"})
SECCIONES = frozenset(
    {
        "home",
        "instaladores",
        "foro",
        "faq",
        "tickets",
        "contacto",
        "share",
        "login",
        "registro",
        "config",
        "otros",
    }
)
EDITIONS = frozenset({"community_edition", "advance"})
PLATFORMS = frozenset(
    {"windows", "mac_intel", "mac_silicon", "linux_deb", "linux_rpm"}
)

DOWNLOAD_SOURCE_INSTALL_SCRIPT = "install-script"
VISITA_IDLE_SECONDS = 90
HEARTBEAT_MIN_INTERVAL_SECONDS = 25

MENU_TO_SECCION = {
    "inicio": "home",
    "home": "home",
    "presentacion": "home",
    "servicios": "home",
    "documentacion": "home",
    "escenarios": "home",
    "instaladores": "instaladores",
    "foro": "foro",
    "faq": "faq",
    "preguntas-frecuentes": "faq",
    "tickets": "tickets",
    "estado-de-tickets": "tickets",
    "soporte": "tickets",
    "contacto": "contacto",
    "share": "share",
    "connect": "share",
    "login": "login",
    "registro": "registro",
}


def seccion_from_menu(item: str) -> str:
    """Mapea la clave de menú del portal a una sección de auditoría."""
    raw = (item or "").strip().lower()
    if raw in SECCIONES:
        return raw
    if raw.startswith("config"):
        return "config"
    if raw.startswith("foro") or raw.startswith("forum"):
        return "foro"
    return MENU_TO_SECCION.get(raw, "otros")


def should_record_download(source: str) -> bool:
    """Solo la descarga del script (curl|bash) cuenta; el prefetch de caché no."""
    return (source or "").strip() == DOWNLOAD_SOURCE_INSTALL_SCRIPT
