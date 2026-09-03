#!/usr/bin/env python3
"""Incrementa la versión de uno o más servicios en versions.yml.

Uso:
    python scripts/bump_service_version.py frontend --level fix
    python scripts/bump_service_version.py frontend backoffice --level minor
    python scripts/bump_service_version.py --from-git --level fix

Niveles: fix (patch), minor (subversion), major (version).
Con --from-git detecta servicios tocados desde --since (default HEAD~1).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VERSIONS_FILE = REPO_ROOT / "versions.yml"
MANIFEST_FILE = REPO_ROOT / "infrastructure" / "docker" / "service_manifest.yml"

VALID_LEVELS = ("fix", "minor", "major")


def _load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError:
        yaml = None
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text) or {}
    else:
        data = _load_yaml_simple(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path} no contiene un objeto YAML")
    return data


def _load_yaml_simple(text: str) -> dict:
    """Parser mínimo para YAML de claves/indentación usado en este repo."""
    root: dict = {}
    stack: list[tuple[int, dict | list]] = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if line.startswith("- "):
            if not isinstance(parent, list):
                continue
            parent.append(line[2:].strip().strip("\"'"))
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if not isinstance(parent, dict):
            continue
        if value == "":
            nxt: dict | list
            if key in {"paths", "shared_python_paths"}:
                nxt = []
            else:
                nxt = {}
            parent[key] = nxt
            stack.append((indent, nxt))
        else:
            parent[key] = value
    return root


def _write_versions(versions: dict) -> None:
    """Actualiza claves version_* in-place para conservar comentarios."""
    raw_lines = VERSIONS_FILE.read_text(encoding="utf-8").splitlines()
    written: set[str] = set()
    new_lines: list[str] = []
    for line in raw_lines:
        stripped = line.strip()
        updated = False
        if stripped and not stripped.startswith("#") and ":" in stripped:
            key = stripped.split(":", 1)[0].strip()
            if key in versions and key.startswith("version_"):
                new_lines.append(f"{key}: {versions[key]}")
                written.add(key)
                updated = True
        if not updated:
            new_lines.append(line)
    missing = [
        key
        for key, value in versions.items()
        if key.startswith("version_") and key not in written
    ]
    if missing:
        insert_at = len(new_lines)
        for idx, line in enumerate(new_lines):
            if line.startswith("version_"):
                insert_at = idx + 1
        for key in missing:
            new_lines.insert(insert_at, f"{key}: {versions[key]}")
            insert_at += 1
    VERSIONS_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _bump(version: str, level: str) -> str:
    parts = [int(p) for p in str(version).split(".")]
    while len(parts) < 3:
        parts.append(0)
    major, minor, patch = parts[0], parts[1], parts[2]
    if level == "major":
        major, minor, patch = major + 1, 0, 0
    elif level == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    return f"{major}.{minor}.{patch}"


def _manifest_services() -> dict[str, dict]:
    manifest = _load_yaml(MANIFEST_FILE)
    services = manifest.get("services", {})
    if not isinstance(services, dict):
        raise ValueError("service_manifest.yml: 'services' debe ser un objeto")
    return services


def _changed_files(since: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "diff", "--name-only", since],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr.strip() or "git diff falló", file=sys.stderr)
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _services_for_paths(changed: list[str], services: dict[str, dict]) -> list[str]:
    hit: set[str] = set()
    for name, spec in services.items():
        for prefix in spec.get("paths", []):
            prefix = str(prefix).lstrip("./")
            for path in changed:
                if path == prefix or path.startswith(prefix.rstrip("/") + "/"):
                    hit.add(name)
                    break
    return sorted(hit)


def main() -> int:
    parser = argparse.ArgumentParser(description="Incrementa versiones de servicios Docker")
    parser.add_argument("services", nargs="*", help="Nombres de servicio del manifiesto")
    parser.add_argument(
        "--level",
        choices=VALID_LEVELS,
        default="fix",
        help="Nivel a incrementar (default: fix)",
    )
    parser.add_argument(
        "--from-git",
        action="store_true",
        help="Detectar servicios desde git diff",
    )
    parser.add_argument(
        "--since",
        default="HEAD~1",
        help="Rango git para --from-git (default: HEAD~1)",
    )
    args = parser.parse_args()

    services = _manifest_services()
    versions = _load_yaml(VERSIONS_FILE)
    targets = list(args.services)

    if args.from_git:
        changed = _changed_files(args.since)
        detected = _services_for_paths(changed, services)
        targets.extend(detected)
        if detected:
            print(f"Servicios detectados desde {args.since}: {', '.join(detected)}")
        elif not targets:
            print("No hay servicios Docker afectados por el diff.")
            return 0

    targets = sorted(set(targets))
    if not targets:
        parser.error("Indica al menos un servicio o usa --from-git")

    unknown = [name for name in targets if name not in services]
    if unknown:
        print(f"Servicios desconocidos: {', '.join(unknown)}", file=sys.stderr)
        print(f"Válidos: {', '.join(sorted(services))}", file=sys.stderr)
        return 1

    for name in targets:
        key = services[name]["version_key"]
        current = str(versions.get(key, "0.0.0"))
        new = _bump(current, args.level)
        versions[key] = new
        print(f"{name}: {current} → {new} ({key})")

    _write_versions(versions)
    return 0


if __name__ == "__main__":
    sys.exit(main())
