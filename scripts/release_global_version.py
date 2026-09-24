#!/usr/bin/env python3
"""Incrementa la versión global de anewhope y congela un release.

Uso:
    python scripts/release_global_version.py --level fix
    python scripts/release_global_version.py --level minor

Hace tres cosas, en este orden (ver AGENTS.md § Gestión de versiones):
1. Incrementa `version_global` en versions.yml.
2. Añade una entrada nueva a releases.yml con la foto exacta de todas
   las version_* de versions.yml en este momento (incluida la propia
   version_global).
3. En CHANGELOG.md, renombra la sección "## [Sin liberar]" (si existe)
   a "## [X.Y.Z] - YYYY-MM-DD" e inserta una "## [Sin liberar]" vacía
   encima para que el siguiente ciclo de cambios tenga dónde apuntar.

Reutiliza los helpers YAML de bump_service_version.py (mismo repo,
mismo directorio) en vez de duplicarlos.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bump_service_version import _bump, _load_yaml, _write_versions  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
VERSIONS_FILE = REPO_ROOT / "versions.yml"
RELEASES_FILE = REPO_ROOT / "releases.yml"
CHANGELOG_FILE = REPO_ROOT / "CHANGELOG.md"

VALID_LEVELS = ("fix", "minor", "major")

UNRELEASED_HEADER = "## [Sin liberar]"


def _append_release(new_version: str, versions: dict) -> None:
    """Añade una entrada a releases.yml con la foto actual de versions.yml.

    Escrito a mano (no con un dumper YAML genérico) para mantener el
    mismo estilo/orden que el resto del fichero — mismo criterio que
    _write_versions en bump_service_version.py.
    """
    components = {k: v for k, v in versions.items() if k.startswith("version_") and k != "version_global"}
    lines = [
        f'  - version: "{new_version}"',
        f'    date: "{date.today().isoformat()}"',
        "    components:",
    ]
    for key in sorted(components):
        lines.append(f'      {key}: "{components[key]}"')

    if RELEASES_FILE.exists():
        text = RELEASES_FILE.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            text += "\n"
        RELEASES_FILE.write_text(text + "\n".join(lines) + "\n", encoding="utf-8")
    else:
        header = (
            "# Historial de versiones globales de anewhope/LAIM.\n"
            "# Ver AGENTS.md § Gestión de versiones.\n\n"
            "releases:\n"
        )
        RELEASES_FILE.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def _update_changelog(new_version: str) -> None:
    if not CHANGELOG_FILE.exists():
        return
    text = CHANGELOG_FILE.read_text(encoding="utf-8")
    dated_header = f"## [{new_version}] - {date.today().isoformat()}"

    if UNRELEASED_HEADER in text:
        text = text.replace(UNRELEASED_HEADER, dated_header, 1)
        # Inserta un "[Sin liberar]" vacío justo antes de la sección que
        # acabamos de fechar, para que el próximo cambio tenga dónde ir.
        text = text.replace(dated_header, f"{UNRELEASED_HEADER}\n\n{dated_header}", 1)
    else:
        # No había bucket "[Sin liberar]" todavía (primer release tras
        # adoptar este formato) — solo aseguramos que exista uno vacío
        # al principio del fichero para el próximo cambio.
        lines = text.splitlines()
        insert_at = 1 if lines and lines[0].startswith("# ") else 0
        lines[insert_at:insert_at] = ["", UNRELEASED_HEADER, ""]
        text = "\n".join(lines) + "\n"

    CHANGELOG_FILE.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Libera una versión global de anewhope")
    parser.add_argument("--level", choices=VALID_LEVELS, default="fix", help="Nivel a incrementar (default: fix)")
    args = parser.parse_args()

    versions = _load_yaml(VERSIONS_FILE)
    current = str(versions.get("version_global", "0.0.0"))
    new_version = _bump(current, args.level)
    versions["version_global"] = new_version

    _write_versions(versions)
    _append_release(new_version, versions)
    _update_changelog(new_version)

    print(f"version_global: {current} → {new_version}")
    print(f"releases.yml: entrada añadida para {new_version}")
    print(f"CHANGELOG.md: '[Sin liberar]' → '[{new_version}] - {date.today().isoformat()}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
