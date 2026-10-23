"""LAIM Web y web_frontend muestran la versión global (version_global de versions.yml), nunca una escrita a mano."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import yaml

APP = Path(__file__).resolve().parents[1]
REPO_ROOT = APP.parents[2]


def _load_app_version():
    spec = importlib.util.spec_from_file_location("laim_web_app_version", APP / "laim_web" / "app_version.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_app_version_is_version_global_from_versions_yml() -> None:
    versions = yaml.safe_load((REPO_ROOT / "versions.yml").read_text(encoding="utf-8"))
    module = _load_app_version()
    assert module.APP_VERSION == str(versions["version_global"])
    assert module.APP_VERSION_LABEL == f"LAIM v{versions['version_global']}"


def test_no_hardcoded_version_literal_in_the_ui() -> None:
    literal = re.compile(r"[\"']LAIM(?: Web)? v\d+\.\d+\.\d+")
    offenders = [
        f"{p.relative_to(APP)}:{n}"
        for p in (APP / "laim_web").rglob("*.py")
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if literal.search(line)
    ]
    assert offenders == []


def test_footers_use_the_version_label() -> None:
    for rel in ("components/portal_shell.py", "pages/index.py"):
        src = (APP / "laim_web" / rel).read_text(encoding="utf-8")
        assert "rx.text(APP_VERSION_LABEL" in src, rel


def test_web_frontend_shows_the_global_version() -> None:
    src = (REPO_ROOT / "src/apps/5_web_frontend/web_frontend/web_frontend.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = get_version("global")' in src
    assert 'f"Version: {APP_VERSION}"' in src
