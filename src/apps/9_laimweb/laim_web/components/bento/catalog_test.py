"""Tests del catálogo Bento y de los glifos CRT."""

from __future__ import annotations

import unittest

from laim_web.components.bento.catalog import (
    CATALOG,
    decorate_sections,
    glyph_for,
    modal_cta_items,
    modal_cta_keys,
)
from laim_web.components.bento.glyphs import GLYPH_PATHS, glyph_ids, glyph_svg_markup
from pathlib import Path

from laim_web.static_pages_loader import load_static_page_markdown, split_markdown_h2_sections


class BentoCatalogTests(unittest.TestCase):
    def test_catalog_covers_inicio_titles_and_unique_glyphs(self) -> None:
        markdown = load_static_page_markdown("inicio")
        title, _, sections = split_markdown_h2_sections(markdown)
        self.assertEqual(title, "Bienvenido a LAIM")
        titles = [section["title"] for section in sections]
        self.assertEqual(titles, list(CATALOG.keys()))
        glyphs = [CATALOG[name]["glyph"] for name in titles]
        self.assertEqual(len(set(glyphs)), 9)
        self.assertEqual(set(glyphs), set(glyph_ids()))

    def test_decorate_sections_keeps_body_and_adds_markup(self) -> None:
        sections = [
            {"title": "El Alma de LAIM", "body": "cuerpo alma"},
            {"title": "Desconocida", "body": "x"},
        ]
        tiles = decorate_sections(sections)
        self.assertEqual(tiles[0]["body"], "cuerpo alma")
        self.assertEqual(tiles[0]["glyph"], "soul")
        self.assertIn("crt-bento-area-alma", tiles[0]["tile_class"])
        self.assertEqual(tiles[0]["title_index"], "0")
        self.assertIn("crt-neural-result", tiles[0]["tile_class"])
        self.assertIn("<svg", tiles[0]["glyph_html"])
        self.assertIn("#glyph-soul", tiles[0]["glyph_href"])
        self.assertEqual(tiles[1]["glyph"], "core")
        self.assertEqual(tiles[1]["body"], "x")

    def test_modal_ctas_detect_portal_pages(self) -> None:
        body = "Lee Presentación y luego Contacto. Documentación queda para después."
        self.assertEqual(modal_cta_keys(body), ["presentacion", "documentacion", "contacto"])
        labels = [item["label"] for item in modal_cta_items(body)]
        self.assertEqual(labels, ["Presentación", "Documentación", "Contacto"])
        self.assertEqual(modal_cta_keys("sin menús"), [])

    def test_each_glyph_has_distinct_paths(self) -> None:
        blobs = [glyph_svg_markup(gid) for gid in glyph_ids()]
        self.assertEqual(len(set(blobs)), 9)
        for blob in blobs:
            self.assertIn('stroke="currentColor"', blob)
            self.assertIn('fill="none"', blob)
        self.assertEqual(glyph_for("MOM: Mixture of Models"), "mesh")
        self.assertEqual(set(GLYPH_PATHS), set(glyph_ids()))

    def test_neural_script_polls_until_scene_is_ready(self) -> None:
        """El spinner no se queda eterno: el JS vigila hasta que la escena pinta."""
        here = Path(__file__).resolve().parent
        script = (here.parents[2] / "assets" / "crt" / "bento_neural.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("function scenePrepared()", script)
        self.assertIn("function pollUntilShown()", script)
        self.assertIn("function revealIfPrepared()", script)
        self.assertIn("homeShowsSpinner()", script)
        home = (here / "home.py").read_text(encoding="utf-8")
        self.assertIn("bento_neural.js?v=3d5", home)
        self.assertNotIn("LAIMBentoNeural.restart()", home)


if __name__ == "__main__":
    unittest.main()
