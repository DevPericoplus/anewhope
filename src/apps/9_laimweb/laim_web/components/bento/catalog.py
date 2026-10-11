"""Catálogo Bento de las secciones de Inicio — spans, glifos y pausas."""

from __future__ import annotations

from typing import Final

from laim_web.components.bento.glyphs import glyph_svg_markup

# Claves = título exacto del ## en static_pages/inicio.md
CATALOG: Final[dict[str, dict[str, str]]] = {
    "Local Artificial Intelligence Management": {
        "glyph": "core",
        "span": "2x1",
        "area": "pitch",
        "short": "LAIM",
        "pause_ms": "2200",
    },
    "¿Qué problema resuelve?": {
        "glyph": "shield",
        "span": "1x2",
        "area": "problem",
        "short": "Problema",
        "pause_ms": "2000",
    },
    "MOM: Mixture of Models": {
        "glyph": "mesh",
        "span": "1x1",
        "area": "mom",
        "short": "MOM",
        "pause_ms": "1600",
    },
    "El Alma de LAIM": {
        "glyph": "soul",
        "span": "1x1",
        "area": "alma",
        "short": "Alma",
        "pause_ms": "1600",
    },
    "Qué puedes hacer con LAIM": {
        "glyph": "tools",
        "span": "1x1",
        "area": "puedes",
        "short": "Puedes",
        "pause_ms": "1600",
    },
    "En qué equipos funciona": {
        "glyph": "hardware",
        "span": "1x1",
        "area": "equipos",
        "short": "Equipos",
        "pause_ms": "1600",
    },
    "Cómo te proponemos empezar": {
        "glyph": "steps",
        "span": "2x1",
        "area": "start",
        "short": "Empezar",
        "pause_ms": "2200",
    },
    "Acaricia al jerbo": {
        "glyph": "gerbil",
        "span": "1x1",
        "area": "jerbo",
        "short": "Jerbo",
        "pause_ms": "1600",
    },
    "Una última idea para llevarte": {
        "glyph": "idea",
        "span": "1x1",
        "area": "ultima",
        "short": "Idea",
        "pause_ms": "1600",
    },
}

INICIO_MODAL_MENUS: Final[tuple[tuple[str, str], ...]] = (
    ("presentacion", "Presentación"),
    ("servicios", "Servicios"),
    ("documentacion", "Documentación"),
    ("contacto", "Contacto"),
)

FALLBACK_TILE: Final[dict[str, str]] = {
    "glyph": "core",
    "span": "1x1",
    "area": "unknown",
    "short": "",
    "pause_ms": "1600",
}


def glyph_for(title: str) -> str:
    """Id de glifo CRT para un título de sección."""
    return CATALOG.get(title, FALLBACK_TILE)["glyph"]


def decorate_sections(sections: list[dict[str, str]]) -> list[dict[str, str]]:
    """Añade span, glifo y clase CSS a cada sección hidratada."""
    tiles: list[dict[str, str]] = []
    for section in sections:
        title = section.get("title", "")
        meta = CATALOG.get(title, FALLBACK_TILE)
        short = meta["short"] or title
        area = meta["area"]
        tiles.append(
            {
                "title": title,
                "body": section.get("body", ""),
                "glyph": meta["glyph"],
                "glyph_html": glyph_svg_markup(meta["glyph"]),
                "glyph_href": f"/crt/bento_glyphs.svg#glyph-{meta['glyph']}",
                "span": meta["span"],
                "area": area,
                "short": short,
                "pause_ms": meta["pause_ms"],
                "tile_class": (
                    f"crt-bento-tile crt-bento-area-{area} "
                    f"crt-bento-span-{meta['span']}"
                ),
            }
        )
    return tiles


def modal_cta_keys(body: str) -> list[str]:
    """Claves de menú citadas en el cuerpo (Presentación, Contacto, …)."""
    text = body.lower()
    keys: list[str] = []
    for key, label in INICIO_MODAL_MENUS:
        if label.lower() in text:
            keys.append(key)
    return keys


def modal_cta_items(body: str) -> list[dict[str, str]]:
    """Botones de menú para el modal, en el orden del catálogo."""
    wanted = set(modal_cta_keys(body))
    return [
        {"key": key, "label": label}
        for key, label in INICIO_MODAL_MENUS
        if key in wanted
    ]
