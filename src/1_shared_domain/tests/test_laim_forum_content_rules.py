"""Corte de palabras del foro: excepción de contexto, aviso y disculpa."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "laim_forum_content_rules.py"


def _rules():
    spec = importlib.util.spec_from_file_location("laim_forum_content_rules_test", ROOT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_word_without_exception_still_matches() -> None:
    rules = _rules()
    hit = rules.find_matching_rule("esto es un crack claro", [{"palabra": "crack", "activo": True}])
    assert hit is not None
    assert hit["palabra"] == "crack"


def test_word_is_allowed_when_the_message_has_the_required_context() -> None:
    rules = _rules()
    rule = {
        "palabra": "crack",
        "activo": True,
        "excepcion_tiene": "modelo, mlx",
        "excepcion_no_tiene": "",
    }
    assert rules.find_matching_rule("el modelo mlx no es un crack de disco", [rule]) is None
    assert rules.find_matching_rule("esto es un crack claro", [rule]) is not None


def test_exception_fails_when_a_forbidden_context_is_present() -> None:
    rules = _rules()
    rule = {
        "palabra": "crack",
        "activo": True,
        "excepcion_tiene": "modelo",
        "excepcion_no_tiene": "ilegal",
    }
    assert rules.find_matching_rule("el modelo es un crack ilegal", [rule]) is not None
    assert rules.find_matching_rule("el modelo mlx usa un crack de pesos", [rule]) is None


def test_custom_pattern_replaces_the_plain_word() -> None:
    rules = _rules()
    rule = {"palabra": "crack", "activo": True, "patron": r"(?i)crack\s+ilegal"}
    assert rules.find_matching_rule("un crack de disco", [rule]) is None
    assert rules.find_matching_rule("un crack ilegal de disco", [rule]) is not None


def test_invalid_pattern_does_not_raise() -> None:
    rules = _rules()
    rule = {"palabra": "crack", "activo": True, "patron": "("}
    assert rules.find_matching_rule("un crack claro", [rule]) is None


def test_excerpt_keeps_the_word_and_its_neighbors() -> None:
    rules = _rules()
    text = "antes " * 20 + "PALABRA" + " después" * 20
    span = rules.rule_hit(text, {"palabra": "palabra", "activo": True})
    assert span is not None
    fragment = rules.excerpt_around(text, *span, radius=12)
    assert "PALABRA" in fragment
    assert fragment.startswith("…")
    assert fragment.endswith("…")


def test_ban_notice_tells_the_reason_and_when_they_can_return() -> None:
    rules = _rules()
    notice = rules.ban_notice(
        motivo="Esa palabra no está permitida",
        expires_at=datetime(2026, 11, 10, 21, 18, tzinfo=timezone.utc),
        subcategory="general",
    )
    assert notice["titulo"] == "No puede publicar en el foro"
    assert notice["motivo"] == "Esa palabra no está permitida"
    assert "10 de noviembre de 2026" in notice["hasta"]
    assert "22:18" in notice["hasta"]


def test_ban_without_expiry_says_an_admin_must_lift_it() -> None:
    rules = _rules()
    notice = rules.ban_notice(motivo="", expires_at=None)
    assert "administrador" in notice["hasta"]
    assert "moderación automática" in notice["motivo"]


def test_apology_names_the_word_and_thanks_the_user() -> None:
    rules = _rules()
    letter = rules.false_positive_apology(
        user_name="Ana",
        palabra="crack",
        fragmento="el modelo mlx no es un crack de disco",
    )
    assert letter["asunto"].startswith("Hemos levantado")
    assert "Ana" in letter["cuerpo"]
    assert "crack" in letter["cuerpo"]
    assert "falso positivo" in letter["cuerpo"]
    assert "Gracias por la paciencia" in letter["cuerpo"]
    assert "el modelo mlx" in letter["cuerpo"]


def test_suggested_pattern_is_an_editable_expression() -> None:
    rules = _rules()
    assert rules.suggest_patron("crack") == r"(?i)\bcrack\b"
    summary = rules.exception_summary(
        {"excepcion_tiene": "modelo", "excepcion_no_tiene": "ilegal"}
    )
    assert "tiene «modelo»" in summary
    assert "no tiene «ilegal»" in summary
