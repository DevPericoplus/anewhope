"""Catálogo ilustrado del foro enriquecido con alohe/avatars (MIT).

Las ilustraciones de ``https://github.com/alohe/avatars`` se sirven como
assets estáticos de LAIM Web y se registran en el catálogo de MariaDB
mediante el seed. Los retratos originales LAIM (Terminal, Cipher, …)
siguen siendo la colección por defecto.
"""

from __future__ import annotations

from typing import Any, Final

COLLECTION_LAIM: Final[str] = "laim"
COLLECTION_ALL: Final[str] = "all"
STATIC_VERSION: Final[str] = "1"
ALOHE_STATIC_PREFIX: Final[str] = "/forum_avatars/alohe"

# (id, etiqueta UI, prefijo de fichero, cantidad)
ALOHE_COLLECTIONS: Final[tuple[tuple[str, str, str, int], ...]] = (
    ("vibrent", "Vibrent", "vibrent", 27),
    ("3d", "3D", "3d", 5),
    ("bluey", "Bluey", "bluey", 10),
    ("memo", "Memo", "memo", 35),
    ("notion", "Notion", "notion", 15),
    ("teams", "Teams", "teams", 9),
    ("toon", "Toon", "toon", 10),
    ("upstream", "Upstream", "upstream", 22),
)

LAIM_AVATAR_STATIC_URLS: Final[dict[str, str]] = {
    "Terminal": "/forum_avatars/avatar_01_terminal.png?v=2",
    "Cipher": "/forum_avatars/avatar_02_cipher.png?v=2",
    "Node": "/forum_avatars/avatar_03_node.png?v=2",
    "Pulse": "/forum_avatars/avatar_04_pulse.png?v=2",
    "Signal": "/forum_avatars/avatar_05_signal.png?v=2",
    "Vector": "/forum_avatars/avatar_06_vector.png?v=2",
    "Matrix": "/forum_avatars/avatar_07_matrix.png?v=2",
    "Proxy": "/forum_avatars/avatar_08_proxy.png?v=2",
}

COLLECTION_SORT_BASE: Final[dict[str, int]] = {
    COLLECTION_LAIM: 0,
    "vibrent": 100,
    "3d": 200,
    "bluey": 300,
    "memo": 400,
    "notion": 500,
    "teams": 600,
    "toon": 700,
    "upstream": 800,
}

COLLECTION_LABELS: Final[dict[str, str]] = {
    COLLECTION_LAIM: "LAIM",
    "vibrent": "Vibrent",
    "3d": "3D",
    "bluey": "Bluey",
    "memo": "Memo",
    "notion": "Notion",
    "teams": "Teams",
    "toon": "Toon",
    "upstream": "Upstream",
    COLLECTION_ALL: "Todos",
}


def alohe_label(collection_label: str, index: int) -> str:
    """Etiqueta visible de un retrato alohe (ej. ``Vibrent 3``)."""
    return f"{collection_label} {index}"


def alohe_filename(file_prefix: str, index: int) -> str:
    """Nombre de fichero en el repo alohe/avatars."""
    return f"{file_prefix}_{index}.png"


def alohe_static_url(file_prefix: str, index: int) -> str:
    """URL estática empaquetada en LAIM Web."""
    return f"{ALOHE_STATIC_PREFIX}/{alohe_filename(file_prefix, index)}?v={STATIC_VERSION}"


def list_alohe_specs() -> list[dict[str, Any]]:
    """Especificaciones de todos los retratos alohe (orden estable)."""
    specs: list[dict[str, Any]] = []
    for collection_id, collection_label, file_prefix, count in ALOHE_COLLECTIONS:
        base = COLLECTION_SORT_BASE[collection_id]
        for index in range(1, count + 1):
            specs.append(
                {
                    "collection": collection_id,
                    "collection_label": collection_label,
                    "label": alohe_label(collection_label, index),
                    "filename": alohe_filename(file_prefix, index),
                    "static_url": alohe_static_url(file_prefix, index),
                    "sort_order": base + index - 1,
                    "is_default": False,
                }
            )
    return specs


def build_static_url_map() -> dict[str, str]:
    """Mapa label → URL estática (LAIM + alohe)."""
    mapping = dict(LAIM_AVATAR_STATIC_URLS)
    for spec in list_alohe_specs():
        mapping[str(spec["label"])] = str(spec["static_url"])
    return mapping


def collection_for_label(label: str) -> str:
    """Devuelve el id de colección de una etiqueta del catálogo."""
    clean = label.strip()
    if not clean:
        return ""
    if clean in LAIM_AVATAR_STATIC_URLS:
        return COLLECTION_LAIM
    for collection_id, collection_label, _prefix, _count in ALOHE_COLLECTIONS:
        if clean.startswith(f"{collection_label} "):
            return collection_id
    return ""


def static_url_for_label(label: str) -> str:
    """URL estática para un label conocido; vacío si no está en el mapa."""
    return build_static_url_map().get(label.strip(), "")


def build_collection_options() -> list[dict[str, str]]:
    """Chips de filtro: LAIM, colecciones alohe y Todos."""
    options = [{"id": COLLECTION_LAIM, "label": COLLECTION_LABELS[COLLECTION_LAIM]}]
    for collection_id, collection_label, _prefix, _count in ALOHE_COLLECTIONS:
        options.append({"id": collection_id, "label": collection_label})
    options.append({"id": COLLECTION_ALL, "label": COLLECTION_LABELS[COLLECTION_ALL]})
    return options


def resolve_collection(collection_id: str) -> str:
    """Normaliza el filtro de colección; desconocido cae a LAIM."""
    clean = collection_id.strip().lower()
    if clean == COLLECTION_ALL:
        return COLLECTION_ALL
    if clean == COLLECTION_LAIM:
        return COLLECTION_LAIM
    known = {item[0] for item in ALOHE_COLLECTIONS}
    if clean in known:
        return clean
    return COLLECTION_LAIM


def filter_catalog_items(
    items: list[dict[str, Any]],
    collection_id: str,
) -> list[dict[str, Any]]:
    """Filtra entradas del catálogo por colección."""
    chosen = resolve_collection(collection_id)
    if chosen == COLLECTION_ALL:
        return list(items)
    filtered: list[dict[str, Any]] = []
    for item in items:
        row_collection = str(item.get("collection") or "")
        if not row_collection:
            row_collection = collection_for_label(str(item.get("label") or ""))
        if row_collection == chosen:
            filtered.append(item)
    return filtered


def expected_alohe_count() -> int:
    """Número total de ilustraciones alohe esperadas."""
    return sum(count for _cid, _label, _prefix, count in ALOHE_COLLECTIONS)
