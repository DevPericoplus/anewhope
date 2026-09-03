#!/usr/bin/env python3
"""Detecta qué servicios Docker deben reconstruirse.

Compara paths del git diff con infrastructure/docker/service_manifest.yml
y escribe un JSON para que Ansible / el plan de despliegue solo reconstruya
los servicios afectados.

Uso:
    python scripts/changed_docker_services.py
    python scripts/changed_docker_services.py --since origin/develop
    python scripts/changed_docker_services.py --server frontend --json
    python scripts/changed_docker_services.py --since HEAD~5 --bump fix
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VERSIONS_FILE = REPO_ROOT / "versions.yml"
MANIFEST_FILE = REPO_ROOT / "infrastructure" / "docker" / "service_manifest.yml"


def _load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError:
        yaml = None
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text) or {}
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from bump_service_version import _load_yaml_simple

        data = _load_yaml_simple(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path} no contiene un objeto YAML")
    return data


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


def _match_service(path: str, prefixes: list[str]) -> bool:
    for prefix in prefixes:
        clean = str(prefix).lstrip("./")
        if path == clean or path.startswith(clean.rstrip("/") + "/"):
            return True
    return False


def detect_services(since: str, server: str | None = None) -> list[dict]:
    manifest = _load_yaml(MANIFEST_FILE)
    versions = _load_yaml(VERSIONS_FILE)
    services = manifest.get("services", {})
    changed = _changed_files(since)
    rows: list[dict] = []
    for name, spec in services.items():
        if server and spec.get("server") != server:
            continue
        if not _match_service_any(changed, spec.get("paths", [])):
            continue
        version_key = spec["version_key"]
        version = str(versions.get(version_key, "unknown"))
        rows.append(
            {
                "service": name,
                "compose": spec.get("compose", name),
                "image": spec.get("image", ""),
                "tag": f"{spec.get('image', '')}:{version}",
                "version": version,
                "version_key": version_key,
                "server": spec.get("server", ""),
            }
        )
    return rows


def _match_service_any(changed: list[str], prefixes: list[str]) -> bool:
    return any(_match_service(path, prefixes) for path in changed)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lista servicios Docker afectados por un diff git"
    )
    parser.add_argument("--since", default="HEAD~1", help="Rango git (default: HEAD~1)")
    parser.add_argument(
        "--server",
        choices=("frontend", "backend", "trainer"),
        help="Filtrar por servidor de despliegue",
    )
    parser.add_argument("--json", action="store_true", help="Salida JSON")
    parser.add_argument(
        "--compose-names",
        action="store_true",
        help="Imprime solo nombres compose (para ansible)",
    )
    parser.add_argument(
        "--bump",
        choices=("fix", "minor", "major"),
        help="Incrementa versions.yml de los servicios detectados",
    )
    args = parser.parse_args()

    rows = detect_services(args.since, args.server)
    if args.bump and rows:
        bump = REPO_ROOT / "scripts" / "bump_service_version.py"
        names = [row["service"] for row in rows]
        subprocess.run(
            [sys.executable, str(bump), *names, "--level", args.bump],
            check=True,
        )
        rows = detect_services(args.since, args.server)

    if args.compose_names:
        print(" ".join(row["compose"] for row in rows))
        return 0

    if args.json:
        print(json.dumps({"since": args.since, "rebuild": rows}, indent=2))
        return 0

    if not rows:
        print("Ningún servicio Docker afectado.")
        return 0

    print(f"Servicios a reconstruir (desde {args.since}):")
    for row in rows:
        print(
            f"  {row['server']:10} {row['compose']:20} {row['tag']}  ({row['service']})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
